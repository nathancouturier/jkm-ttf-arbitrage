"""EU ETS allowance prices, monthly, from the European Commission's auction reports.

The study needs the price of an EU emission allowance (EUA) for the carbon cost
of a voyage into Northwest Europe from 2024, when the EU ETS began to cover
shipping. The Commission publishes, for the auctions held on the common auction
platform, quarterly reports whose Table 1 gives, month by month over the last
fifteen months, the "Average auction clearing price" of general allowances,
weighted by each auction's volume. The Commission licenses its content under CC
BY 4.0. EEX, which runs the auctions, publishes every auction's result too, but
its terms forbid redistribution; its figures reproduce the Commission's monthly
averages exactly, and are kept privately for that check only.

The reports lag: on 30 September 2026 the latest covers April to June 2025.
Months after it are missing here, and the gap is an open question.

Reports from the first quarter of 2024 onward are read. A month printed in more
than one report is taken from the latest report that prints it; a disagreement
between reports is recorded in the anomaly column.
"""

from __future__ import annotations

import io
import re
import sys
from urllib.parse import urljoin

import pandas as pd
import pdfplumber

from ..config import BOUNDS_EUA_EUR_T
from .base import Adapter, SourceError, http_get

__all__ = ["PAGE_URL", "FIRST_REPORT", "report_links", "parse_report", "combine", "EcEuaAuctionMonthly"]

PAGE_URL = "https://climate.ec.europa.eu/areas-action/carbon-markets/eu-emissions-trading-system-eu-ets/auctioning-allowances_en"
BASE_URL = "https://climate.ec.europa.eu"
#: The first quarterly report read, the quarter ending March 2024.
FIRST_REPORT = "202403"

_LINK = re.compile(r'href="([^"]*filename=cap_report_(\d{6})_en\.pdf)"')
_MONTH_ROW = re.compile(
    r"^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) (\d{2}) "
    r"([\d,]+) ([\d,]+) ([\d,]+) ([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)$"
)
_NO_AUCTION = re.compile(r"^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) (\d{2}) - - -")


def report_links(page_html: bytes | str) -> dict[str, str]:
    """report id (YYYYMM, the quarter's last month) -> absolute URL, from the page."""
    if isinstance(page_html, bytes):
        page_html = page_html.decode("utf-8", errors="replace")
    links = {}
    for href, report in _LINK.findall(page_html):
        links.setdefault(report, urljoin(BASE_URL, href.replace("&amp;", "&")))
    if not links:
        raise SourceError("the auctioning page links no common auction platform report")
    return links


def parse_report(pdf: bytes, *, report: str) -> pd.DataFrame:
    """Table 1 of one report: one row per month, the average clearing price in EUR."""
    with pdfplumber.open(io.BytesIO(pdf)) as document:
        text = "\n".join((page.extract_text() or "") for page in document.pages)
    start = text.find("Table 1: General allowances")
    if start == -1:
        raise SourceError("report %s has no Table 1 of general allowances" % report)
    table = text[start:text.find("total", start) + 200]
    rows = []
    for line in table.splitlines():
        line = line.strip()
        match = _MONTH_ROW.match(line)
        if match:
            month = pd.to_datetime("%s %s" % (match.group(1), match.group(2)), format="%b %y")
            rows.append({"date": month, "eua_eur_t": float(match.group(9)), "report": report})
        elif _NO_AUCTION.match(line):
            parts = _NO_AUCTION.match(line)
            month = pd.to_datetime("%s %s" % (parts.group(1), parts.group(2)), format="%b %y")
            rows.append({"date": month, "eua_eur_t": float("nan"), "report": report})
    if len(rows) < 3:
        raise SourceError("report %s: Table 1 gives %d month rows" % (report, len(rows)))
    return pd.DataFrame(rows)


def combine(frames: list[pd.DataFrame]) -> pd.DataFrame:
    """One row per month, from the latest report printing it, disagreements noted."""
    stacked = pd.concat(frames, ignore_index=True).sort_values(["date", "report"])
    rows = []
    for month, group in stacked.groupby("date", sort=True):
        latest = group.iloc[-1]
        values = group.dropna(subset=["eua_eur_t"])
        distinct = sorted(set(values["eua_eur_t"]))
        note = None
        if len(distinct) > 1:
            note = "reports disagree: " + ", ".join(
                "%s gives %.2f" % (r, v) for r, v in zip(values["report"], values["eua_eur_t"])
            )
        rows.append(
            {
                "date": month,
                "eua_eur_t": latest["eua_eur_t"],
                "report": latest["report"],
                "reports_printing_it": len(group),
                "anomaly": note,
            }
        )
    return pd.DataFrame(rows)


class EcEuaAuctionMonthly(Adapter):
    """Average auction clearing price of EU general allowances, monthly, EUR per tonne of CO2."""

    name = "ec_eua_auction_monthly"
    source = "European Commission, Auctions by the Common Auction Platform, Table 1"
    url = PAGE_URL
    page_url = PAGE_URL
    unit = "EUR per tonne of CO2"
    frequency = "monthly"
    method = "parsed"
    required_cols = ("date", "eua_eur_t", "report")
    bounds = {"eua_eur_t": BOUNDS_EUA_EUR_T}
    min_observations = {"eua_eur_t": 12}
    observation_column = "eua_eur_t"

    def __init__(self, *, reports: dict[str, bytes] | None = None):
        # reports maps a report id to its PDF, for a run with no network
        self.reports = reports

    def fetch(self) -> pd.DataFrame:
        if self.reports is None:
            links = report_links(http_get(PAGE_URL).content)
            wanted = sorted(r for r in links if r >= FIRST_REPORT)
            reports = {r: http_get(links[r], timeout=120).content for r in wanted}
        else:
            reports = self.reports
        frames = [parse_report(pdf, report=report) for report, pdf in sorted(reports.items())]
        frame = combine(frames)
        latest = max(reports)
        self.vintage = "reports %s to %s" % (min(reports), latest)
        self.note = (
            "%d quarterly reports read, the latest for the quarter ending %s-%s. The "
            "Commission publishes each month's volume weighted average clearing price of "
            "general allowances; months after the latest report are missing. Source: "
            "European Commission, CC BY 4.0; months combined from several reports by "
            "this study." % (len(reports), latest[:4], latest[4:])
        )
        return frame


def main() -> int:
    try:
        entry = EcEuaAuctionMonthly().run()
    except Exception as exc:
        print("FAILED ec_eua_auction_monthly: %s" % exc)
        return 1
    print("ok     %s: %d months, %s to %s" % (entry["series"], entry["observations"], entry["first_date"], entry["last_date"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())

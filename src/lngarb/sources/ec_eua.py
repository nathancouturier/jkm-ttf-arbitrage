"""EU ETS allowance prices, monthly, from the European Commission's auction reports.

The study needs the price of an EU emission allowance (EUA) for the carbon cost
of a voyage into Northwest Europe from 2024, when the EU ETS began to cover
shipping, and holds the price from the start of the third trading period for
the record. The Commission publishes, for the auctions held on the common
auction platform, reports whose Table 1 gives, month by month, the "Average
auction clearing price" of general allowances, weighted by each auction's
volume. The Commission licenses its content under CC BY 4.0. EEX, which runs
the auctions, publishes every auction's result too, but its terms forbid
redistribution; its figures reproduce the Commission's monthly averages
exactly, and are kept privately for that check only.

The reports and their Table 1, as the Commission's auctioning page links them:

    2013 to 2014      one report a month, or for a longer period at the start;
                      no monthly table, the period's weighted average is in the
                      text and the auctions are listed one by one in an annex
    March 2015        the first report with Table 1, fifteen months to
                      January 2014; then one report a month to December 2016,
                      each with the months since January 2015
    from March 2017   one report a quarter, each with fifteen months

The months a report prints are written "March 2015", "Dec. 2014", "Sept. 2014"
or "Mar 23", with thousands separated by spaces or commas; every spelling is
read. Reports from March 2015 are read, so the series runs from January 2014.
The reports lag: on 30 September 2026 the latest covers April to June 2025.
Months after it are missing here, and the gap is an open question.

A month printed in more than one report is taken from the latest report that
prints it; a disagreement between reports is recorded in the anomaly column.
Once a cache is committed, only reports newer than the latest it holds are
fetched; the committed rows stand for the reports already read.
"""

from __future__ import annotations

import io
import math
import re
import sys
from urllib.parse import urljoin

import pandas as pd
import pdfplumber

from ..config import BOUNDS_EUA_EUR_T
from .base import Adapter, SourceError, http_get, read_cache

__all__ = ["PAGE_URL", "FIRST_REPORT", "report_links", "parse_report", "combine", "EcEuaAuctionMonthly"]

PAGE_URL = "https://climate.ec.europa.eu/areas-action/carbon-markets/eu-emissions-trading-system-eu-ets/auctioning-allowances_en"
BASE_URL = "https://climate.ec.europa.eu"
#: The first report read: the report for January to March 2015, the first
#: with a monthly Table 1, which reaches back to January 2014.
FIRST_REPORT = "201503"

_LINK = re.compile(r'href="([^"]*filename=cap_report_(\d{6})_en\.pdf)"')
_MONTH_TOKENS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}
#: A month row: the month as the report spells it, the year in two or four
#: digits, three volumes or revenues with spaces or commas inside them, then
#: four decimals, the last the average auction clearing price.
_MONTH_ROW = re.compile(
    r"^([A-Z][a-z]{2,8}\.?) ((?:20)?\d{2}) "
    r"([\d][\d ,]*?) ([\d][\d ,]*?) ([\d][\d ,]*?) ([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)$"
)
_NO_AUCTION = re.compile(r"^([A-Z][a-z]{2,8}\.?) ((?:20)?\d{2}) - - -")
_TOTAL_ROW = re.compile(r"^20\d\d total\b", re.IGNORECASE)


def report_links(page_html: bytes | str) -> dict[str, str]:
    """report id (YYYYMM, the period's last month) -> absolute URL, from the page."""
    if isinstance(page_html, bytes):
        page_html = page_html.decode("utf-8", errors="replace")
    links = {}
    for href, report in _LINK.findall(page_html):
        links.setdefault(report, urljoin(BASE_URL, href.replace("&amp;", "&")))
    if not links:
        raise SourceError("the auctioning page links no common auction platform report")
    return links


def _month(token: str, year: str, *, report: str) -> pd.Timestamp:
    key = token.rstrip(".").lower()[:3]
    if key not in _MONTH_TOKENS:
        raise SourceError("report %s: %r is not a month" % (report, token))
    full_year = int(year) if len(year) == 4 else 2000 + int(year)
    return pd.Timestamp(full_year, _MONTH_TOKENS[key], 1)


def parse_report(pdf: bytes, *, report: str) -> pd.DataFrame:
    """Table 1 of one report: one row per month, the average clearing price in EUR."""
    with pdfplumber.open(io.BytesIO(pdf)) as document:
        text = "\n".join((page.extract_text() or "") for page in document.pages)
    start = text.find("Table 1: General allowances")
    if start == -1:
        raise SourceError("report %s has no Table 1 of general allowances" % report)
    rows = []
    for line in text[start:].splitlines():
        line = line.strip()
        if rows and _TOTAL_ROW.match(line):
            break
        match = _MONTH_ROW.match(line)
        if match:
            month = _month(match.group(1), match.group(2), report=report)
            rows.append({"date": month, "eua_eur_t": float(match.group(9)), "report": "cap_report_%s" % report})
            continue
        match = _NO_AUCTION.match(line)
        if match:
            month = _month(match.group(1), match.group(2), report=report)
            rows.append({"date": month, "eua_eur_t": float("nan"), "report": "cap_report_%s" % report})
    if len(rows) < 3:
        raise SourceError("report %s: Table 1 gives %d month rows" % (report, len(rows)))
    frame = pd.DataFrame(rows)
    if frame["date"].duplicated().any():
        raise SourceError("report %s: Table 1 prints a month twice" % report)
    return frame


def combine(frames: list[pd.DataFrame]) -> pd.DataFrame:
    """One row per month, from the latest report printing it, disagreements noted.

    A frame may carry reports_printing_it and anomaly columns, as the committed
    cache does: its rows then stand for the reports already read, and the count
    and the note carry forward when no later report prints the month.
    """
    stacked = pd.concat(frames, ignore_index=True)
    if "reports_printing_it" not in stacked.columns:
        stacked["reports_printing_it"] = 1
    if "anomaly" not in stacked.columns:
        stacked["anomaly"] = None
    stacked["reports_printing_it"] = stacked["reports_printing_it"].fillna(1).astype(int)
    stacked = stacked.sort_values(["date", "report"], kind="stable")
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
        elif len(group) == 1:
            prior = latest["anomaly"]
            note = None if prior is None or (isinstance(prior, float) and math.isnan(prior)) else str(prior)
        rows.append(
            {
                "date": month,
                "eua_eur_t": latest["eua_eur_t"],
                "report": latest["report"],
                "reports_printing_it": int(group["reports_printing_it"].sum()),
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
        existing = read_cache(self.name, directory=self.directory())
        prior: pd.DataFrame | None = None
        if existing is not None and len(existing):
            prior = existing[["date", "eua_eur_t", "report", "reports_printing_it", "anomaly"]].copy()
            prior["date"] = pd.to_datetime(prior["date"])
            latest_held = max(str(r).replace("cap_report_", "") for r in prior["report"])
        else:
            latest_held = ""
        if self.reports is None:
            links = report_links(http_get(PAGE_URL).content)
            wanted = sorted(r for r in links if r >= FIRST_REPORT and r > latest_held)
            reports = {r: http_get(links[r], timeout=120).content for r in wanted}
        else:
            reports = self.reports
        frames = [parse_report(pdf, report=report) for report, pdf in sorted(reports.items())]
        if prior is not None:
            frames = [prior] + frames
        if not frames:
            raise SourceError("no report to read and nothing committed")
        frame = combine(frames)
        held = sorted(set(str(r).replace("cap_report_", "") for r in frame["report"]))
        self.vintage = "reports %s to %s" % (held[0], held[-1])
        self.note = (
            "%d report(s) read this run; the months stand as %d reports last printed them, the "
            "latest for the period ending %s-%s. "
            "The Commission publishes each month's volume weighted average clearing price of "
            "general allowances on the common auction platform, monthly in its reports of 2015 "
            "and 2016 and quarterly since; the series starts with January 2014, the first month "
            "of the first Table 1; months after the latest report are missing. Source: European "
            "Commission, CC BY 4.0; months combined from several reports by this study."
            % (len(reports), len(held), held[-1][:4], held[-1][4:])
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

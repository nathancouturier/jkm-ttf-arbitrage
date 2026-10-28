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

    February 2013 to  one report a month, or for a longer period at the start;
    November 2013     no monthly table, the period's weighted average is in the
                      text and the auctions are listed one by one in an annex
    December 2013 to  one report a month, each with an overview table of the
    December 2014     months since November 2012 (to March 2014) or the latest
                      twelve, the clearing price a volume weighted average of
                      the month's auctions, or a simple average, which the
                      report marks, where every auction sold the same volume
    March 2015        the first report with Table 1, fifteen months to
                      January 2014; then one report a month to December 2016,
                      each with the months since January 2015
    from March 2017   one report a quarter, each with fifteen months

The months a report prints are written "March 2015", "Dec. 2014", "Sept. 2014"
or "Mar 23", with thousands separated by spaces or commas; every spelling is
read. Reports from December 2013 are read, so the series runs from November
2012, the first month of the common auction platform; the overview tables
list their months upwards or downwards and print the year on the first row
of each year only, which the parser follows.
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
#: The first report read: the report for December 2013, the first with a
#: monthly table, an overview that reaches back to November 2012.
FIRST_REPORT = "201312"

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
#: The overview tables of December 2013 to December 2014: a month, its year on
#: the first row of a year only, the auction and bid volumes, the cover ratio,
#: the bidders and the successful bidders, then the price and the revenue in
#: euros, the averages marked with one asterisk (simple) or two (weighted).
_OVERVIEW_HEAD = re.compile(r"^Table \d:? [Oo]verview$")
_OVERVIEW_ROW = re.compile(
    r"^([A-Z][a-z]+)(?: (20\d\d))? ([\d][\d ]*?) ([\d][\d ]*?) ([\d.]+)\*{0,2} ([\d.]+)\*{0,2} ([\d.]+)\*{0,2} "
    r"\u20ac ([\d.]+)(\*{0,2}) \u20ac ([\d][\d ]*)$"
)


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


def _parse_overview(text: str, *, report: str) -> pd.DataFrame:
    """The overview table of a report of December 2013 to December 2014: one row per month.

    The months run upwards or downwards and carry their year on the first row
    of each year only; the year of the other rows follows from the direction.
    A price marked with one asterisk is the report's simple average, which it
    says equals the weighted one where every auction sold the same volume;
    the row's anomaly says so.
    """
    lines = text.splitlines()
    heads = [i for i, line in enumerate(lines) if _OVERVIEW_HEAD.match(line.strip())]
    rows: list[dict] = []
    for head in heads:
        found = []
        for line in lines[head + 1:]:
            stripped = line.strip()
            if found and (stripped.startswith("* average") or stripped.startswith("Total") or stripped.startswith("Table")):
                break
            match = _OVERVIEW_ROW.match(stripped)
            if match:
                found.append(match)
        if found:
            break
    else:
        raise SourceError("report %s has no overview table with month rows" % report)
    months = [(_MONTH_TOKENS[m.group(1).lower()[:3]], m.group(2), float(m.group(8)), m.group(9)) for m in found]
    if any(key not in _MONTH_TOKENS for key in (m.group(1).lower()[:3] for m in found)):
        raise SourceError("report %s: a row of the overview table names no month" % report)
    years: list[int | None] = [int(y) if y else None for _, y, _, _ in months]
    if years[0] is None:
        raise SourceError("report %s: the overview table's first row carries no year" % report)
    upwards = len(months) < 2 or (months[1][0] - months[0][0]) % 12 < 6
    for index in range(1, len(months)):
        if years[index] is None:
            previous_month, this_month = months[index - 1][0], months[index][0]
            years[index] = years[index - 1] + (1 if upwards and this_month < previous_month else 0) \
                - (1 if not upwards and this_month > previous_month else 0)
    for (month, _, price, marks), year in zip(months, years):
        rows.append({"date": pd.Timestamp(year, month, 1), "eua_eur_t": price, "report": "cap_report_%s" % report,
                     "anomaly": None if marks == "**" else
                     "a simple average of the month's auctions, which the report says equals the volume weighted "
                     "average where every auction sold the same volume"})
    frame = pd.DataFrame(rows)
    if frame["date"].duplicated().any():
        raise SourceError("report %s: the overview table prints a month twice" % report)
    return frame


def parse_report(pdf: bytes, *, report: str) -> pd.DataFrame:
    """Table 1 of one report, or the overview table of a report of 2013 to 2014: one row per month, the average clearing price in EUR."""
    with pdfplumber.open(io.BytesIO(pdf)) as document:
        text = "\n".join((page.extract_text() or "") for page in document.pages)
    start = text.find("Table 1: General allowances")
    if start == -1:
        return _parse_overview(text, report=report)
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
            # The prints of each value, as a span of reports where several agree.
            parts = []
            for value in distinct:
                printing = [r for r, v in zip(values["report"], values["eua_eur_t"]) if v == value]
                who = printing[0] if len(printing) == 1 else "%s to %s, %d reports" % (printing[0], printing[-1], len(printing))
                parts.append("%s in %s" % (format(value, "g"), who))
            note = "reports disagree: " + "; ".join(parts)
        else:
            # A note a print carries (a simple average, marked) stands while the prints agree.
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
            "and 2016 and quarterly since, in their Table 1; its reports of December 2013 to "
            "December 2014 print the same in an overview table, from November 2012, the first "
            "month of the platform, the months whose auctions sold equal volumes as a simple "
            "average the report marks; months after the latest report are missing. Source: "
            "European Commission, CC BY 4.0; months combined from several reports by this study."
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

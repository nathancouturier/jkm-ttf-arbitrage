"""EU allowance prices, monthly, from the German auctions DEHSt reports.

The Commission's reports on the common auction platform stop in June 2025
(ec_eua). Germany auctions its own share of allowances on EEX, weekly, and the
German Emissions Trading Authority (DEHSt) at the German Environment Agency
reports each month's average price in its auctioning reports: each report's
"Overview of the entire year" table gives every month of the year so far, with
the auction volume, the average price and the revenue. The study reads, for
each year from 2024, the latest report of that year, so one PDF per year.

The German auctions are not the common platform: the series is a proxy for
the EU price, labelled as such, and the months both cover are compared in the
documentation. A month marked "*" is a simple average of the month's auctions,
"**" a volume weighted one; the mark is kept.

DEHSt's editorial information puts its own texts and objects under CC BY-NC-ND
4.0 unless otherwise indicated. The table read names "Source: EEX, DEHSt";
other tables and figures of the reports credit market data vendors too, and
none of them is read or kept. The figures are kept as printed, credited to EEX
and DEHSt, for non-commercial use; no report is kept, even as a test fixture.
robots.txt asks for thirty seconds between requests, and closes /EN/Service/,
where the terms are; nothing there is fetched.
"""

from __future__ import annotations

import io
import re
import sys
from datetime import date

import pandas as pd
import pdfplumber

from ..config import BOUNDS_AUCTION_REVENUE_EUR, BOUNDS_AUCTION_VOLUME_EUA, BOUNDS_EUA_EUR_T
from .base import Adapter, SourceError, http_get, read_cache

__all__ = [
    "PAGE_URL", "FIRST_YEAR", "report_links", "latest_per_year", "parse_year_table", "parse_report",
    "DehstEuaGermanAuctionMonthly",
]

PAGE_URL = (
    "https://www.dehst.de/EN/Topics/EU-ETS-1/EU-ETS-1-Information/Analyses-and-Reports/"
    "analysis-and-reports_node.html"
)
#: The first year read: 2019, the first year whose reports the page links under
#: the file names read here. Shipping enters the EU ETS in 2024; the earlier
#: years measure the German average against the Commission's over every month
#: both cover.
FIRST_YEAR = 2019
#: robots.txt asks for "Crawl-delay: 30".
DELAY_SECONDS = 31.0

CREDIT = "Source: EEX, DEHSt"

_LINK = re.compile(
    r'href="(https://www\.dehst\.de/SharedDocs/downloads/EN/auctioning/(\d{4})/'
    r'(\d{4})_report_(\d{2}|Q[1-4])\.pdf[^"]*)"'
)
_MONTHS = ("January", "February", "March", "April", "May", "June", "July",
           "August", "September", "October", "November", "December")
#: One row of the year table. Reports to 2024 add a type column, EUA or EUAA
#: (aviation allowances), and a space after the euro sign; a month auctioning
#: both types prints its name on a line of its own, between the two rows. The
#: reports of 2019 to 2023 also print a space after the asterisks that mark an
#: average, a comma for the decimal point now and then, and once, December
#: 2019, the price as "25,02" followed by two euro signs; every such row is
#: read and the odd spelling is noted.
_ROW = re.compile(
    r"^(?:(?P<month>" + "|".join(_MONTHS) + r") )?(?:(?P<type>EUAA?) )?(?P<volume>[\d,]+) (?P<bid>[\d,]+) "
    r"\*{0,2} ?[\d.,]+ \*{0,2} ?\d+ \*{0,2} ?\d+ (?P<mark>\*{0,2}) ?(?:" + chr(0x20AC) + r" ?)?"
    r"(?P<price>[\d,]+[.,]\d{2})(?: ?" + chr(0x20AC) + r"){1,2} ?(?P<revenue>[\d,]+)$"
)
_PRICE_AS_PRINTED = re.compile(r"^[\d,]+\.\d{2}$")
_LONE_MONTH = re.compile(r"^(" + "|".join(_MONTHS) + r")$")
_TOTAL = re.compile(r"^Total ([\d,]+) ")
_TABLE = re.compile(r"Table \d+: Overview of the entire year (\d{4})")


def report_links(page_html: bytes | str) -> dict[tuple[int, str], str]:
    """(year, report id) -> absolute URL, for every monthly or quarterly report the page links.

    A report id is the month ("08") or the quarter ("Q4"). Annual reports and
    the older file names before 2019 are not taken.
    """
    if isinstance(page_html, bytes):
        page_html = page_html.decode("utf-8", errors="replace")
    links: dict[tuple[int, str], str] = {}
    for href, folder, year, report in _LINK.findall(page_html):
        if folder != year:
            continue
        links.setdefault((int(year), report), href.replace("&amp;", "&"))
    if not links:
        raise SourceError("the reports page links no auctioning report")
    return links


def _last_month(report: str) -> int:
    """The last month a report covers: its month, or the quarter's third month."""
    return 3 * int(report[1]) if report.startswith("Q") else int(report)


def latest_per_year(links: dict[tuple[int, str], str], *, first_year: int = FIRST_YEAR) -> dict[int, tuple[str, str]]:
    """year -> (report id, URL) of the report covering the most months of that year."""
    chosen: dict[int, tuple[str, str]] = {}
    for (year, report), url in links.items():
        if year < first_year:
            continue
        if year not in chosen or _last_month(report) > _last_month(chosen[year][0]):
            chosen[year] = (report, url)
    return chosen


def parse_report(pdf: bytes, *, year: int, report: str) -> pd.DataFrame:
    """The year table of one report, from the PDF's text (parse_year_table)."""
    with pdfplumber.open(io.BytesIO(pdf)) as document:
        text = "\n".join((page.extract_text() or "") for page in document.pages)
    return parse_year_table(text, year=year, report=report)


def parse_year_table(text: str, *, year: int, report: str) -> pd.DataFrame:
    """The year table of one report: one row per month, the average price in EUR per allowance.

    The table must be the one for the year named, and end with DEHSt's source
    line. Only general allowances (EUA) are read; aviation allowances (EUAA),
    auctioned in some months to 2024, are left out. The months' volumes must add
    up to the table's total of general allowances (its EUA row with no month, or
    its Total row when no aviation allowance was auctioned). A month's volume times its price that misses the revenue by more than
    half a cent per allowance is noted: the printed average is then not the
    month's average over every allowance sold.
    """
    tables = [m for m in _TABLE.finditer(text) if int(m.group(1)) == year]
    if len(tables) != 1:
        raise SourceError("report %d_%s has %d year tables for %d" % (year, report, len(tables), year))
    start = tables[0].end()
    end = text.find(CREDIT, start)
    if end == -1:
        raise SourceError("report %d_%s: the year table does not end with %r" % (year, report, CREDIT))
    rows = []
    lines = [line.strip() for line in text[start:end].splitlines()]
    used: set[int] = set()
    eua_total: int | None = None
    aviation = 0
    for i, line in enumerate(lines):
        match = _ROW.match(line)
        if not match:
            continue
        if match.group("type") == "EUAA":
            # aviation allowances: counted, to take them out of the Total
            # row, and never read as a month's price
            aviation += int(match.group("volume").replace(",", ""))
            continue
        month = match.group("month")
        if month is None:
            # A month name alone on the next line, or failing that the line
            # before, each serving one row; a row with neither is a total.
            beside = [j for j in (i + 1, i - 1)
                      if 0 <= j < len(lines) and j not in used and _LONE_MONTH.match(lines[j])]
            if not beside:
                if match.group("type") == "EUA":
                    eua_total = int(match.group("volume").replace(",", ""))
                continue
            used.add(beside[0])
            month = lines[beside[0]]
        volume = int(match.group("volume").replace(",", ""))
        printed = match.group("price")
        if _PRICE_AS_PRINTED.match(printed):
            price = float(printed.replace(",", ""))
            note = None
        else:
            # a comma for the decimal point: the last comma is the point
            head, _, cents = printed.rpartition(",")
            price = float(head.replace(",", "") + "." + cents)
            note = "price printed as %r" % printed
        revenue = int(match.group("revenue").replace(",", ""))
        if abs(volume * price - revenue) > 0.005 * volume + 0.5:
            gap = "volume times price misses the revenue by %.0f EUR" % (volume * price - revenue)
            note = gap if note is None else note + "; " + gap
        rows.append({
            "date": pd.Timestamp(date(year, _MONTHS.index(month) + 1, 1)),
            "eua_eur_t": price,
            "average": "volume weighted" if match.group("mark") == "**" else "simple",
            "auction_volume": volume,
            "revenue_eur": revenue,
            "report": "%d_report_%s" % (year, report),
            "anomaly": note,
        })
    totals = [_TOTAL.match(line) for line in lines]
    total = next((int(m.group(1).replace(",", "")) for m in totals if m), None)
    # The Total row counts every allowance, aviation ones included, unless the
    # table gives general allowances a total row of their own.
    expected = eua_total if eua_total is not None else (None if total is None else total - aviation)
    if expected is not None and sum(row["auction_volume"] for row in rows) != expected:
        raise SourceError(
            "report %d_%s: the months' volumes add up to %d, the year table's total of general allowances "
            "to %d" % (year, report, sum(row["auction_volume"] for row in rows), expected))
    months = [row["date"].month for row in rows]
    # Consecutive months; a year may start late, as 2019 did, when the German
    # auctions began on 1 February after the cancelled auctions of late 2018.
    if not rows or months != list(range(months[0], months[0] + len(rows))):
        raise SourceError("report %d_%s: the year table's months are %s, not consecutive" % (year, report, months))
    if months[-1] < _last_month(report):
        raise SourceError(
            "report %d_%s covers to month %d but its table stops at %d" % (year, report, _last_month(report), months[-1])
        )
    return pd.DataFrame(rows)


class DehstEuaGermanAuctionMonthly(Adapter):
    """Average price of EU allowances in Germany's auctions, monthly, EUR per tonne of CO2."""

    name = "dehst_eua_german_auction_monthly"
    source = "German Emissions Trading Authority (DEHSt) at the German Environment Agency, auctioning reports; source EEX, DEHSt"
    url = PAGE_URL
    page_url = PAGE_URL
    unit = "EUR per tonne of CO2"
    frequency = "monthly"
    method = "parsed"
    required_cols = ("date", "eua_eur_t", "average", "report")
    bounds = {
        "eua_eur_t": BOUNDS_EUA_EUR_T,
        "auction_volume": BOUNDS_AUCTION_VOLUME_EUA,
        "revenue_eur": BOUNDS_AUCTION_REVENUE_EUR,
    }
    min_observations = {"eua_eur_t": 12, "auction_volume": 12, "revenue_eur": 12}
    observation_column = "eua_eur_t"

    def __init__(self, *, page: bytes | None = None, reports: dict[tuple[int, str], bytes | str] | None = None):
        # page and reports stand in for the network in a run without it; a
        # report is its PDF, or the text of its year table
        self.page = page
        self.reports = reports

    def fetch(self) -> pd.DataFrame:
        page = self.page if self.page is not None else http_get(PAGE_URL, delay=DELAY_SECONDS).content
        chosen = latest_per_year(report_links(page))
        if not chosen:
            raise SourceError("the reports page links no report from %d" % FIRST_YEAR)
        # A year whose latest report the committed cache already read is kept
        # from the cache; only a year with a later report, or none held, is
        # fetched, with the thirty seconds DEHSt asks for between requests.
        existing = read_cache(self.name, directory=self.directory())
        held: dict[int, str] = {}
        if existing is not None and len(existing):
            existing["date"] = pd.to_datetime(existing["date"])
            for year, group in existing.groupby(existing["date"].dt.year):
                held[int(year)] = str(group["report"].iloc[-1])
        frames = []
        read = []
        for year, (report, url) in sorted(chosen.items()):
            name = "%d_report_%s" % (year, report)
            if held.get(year) == name:
                frames.append(existing[existing["date"].dt.year == year])
                continue
            if self.reports is not None:
                payload = self.reports[(year, report)]
            else:
                payload = http_get(url, timeout=120, delay=DELAY_SECONDS).content
            if isinstance(payload, str):
                frames.append(parse_year_table(payload, year=year, report=report))
            else:
                frames.append(parse_report(payload, year=year, report=report))
            read.append(name)
        frame = pd.concat(frames, ignore_index=True).sort_values("date").reset_index(drop=True)
        self.vintage = ", ".join("%d_report_%s" % (year, report) for year, (report, _url) in sorted(chosen.items()))
        self.note = (
            "German auctions on EEX only, a proxy for the EU price: each month's average "
            "price as DEHSt's latest report of each year prints it (%s); %s. Source: EEX, DEHSt; "
            "DEHSt's texts are licensed CC BY-NC-ND 4.0, and the figures are kept unchanged "
            "for non-commercial use." % (
                self.vintage,
                ("%d report(s) read this run, %s" % (len(read), ", ".join(read))) if read
                else "no report newer than the committed cache holds, nothing read this run",
            )
        )
        return frame


def main() -> int:
    try:
        entry = DehstEuaGermanAuctionMonthly().run()
    except Exception as exc:
        print("FAILED dehst_eua_german_auction_monthly: %s" % exc)
        return 1
    print("ok     %s: %d months, %s to %s" % (entry["series"], entry["observations"], entry["first_date"], entry["last_date"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())

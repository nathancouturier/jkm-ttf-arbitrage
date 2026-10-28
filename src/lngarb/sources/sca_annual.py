"""LNG carriers through the Suez Canal each year, from the Suez Canal Authority's annual navigation reports.

The Authority publishes one report a year, "Suez Canal Statistics for Y
Compared to Y-1", a PDF of a few pages with a text layer, in the Downloads
section of its site. Table 3, "NO & Net Ton by Ship Type", gives for the
report's year and the year before the number of ships of each type and their
Suez Canal net tonnage in thousands; the LNG row is labelled "LNG" to the
2013 report, "L N G" in the 2014 to 2016 reports and "LNG Ships" from the
2017 report. The reports run from 2008,
so the series starts with 2007, the earlier year of the first report. Each
year is printed twice, in its own report and in the next; the adapter keeps
the later print and checks the earlier against it, the counts exactly and
the tonnage to the rounding the Authority restates.

The counts are both directions and every voyage, deliveries to Egypt and
Jordan and ballast legs included; they are not a count of US Gulf cargoes
bound for Asia. The site carries no licence and no terms page, only the
footer "All Right Reserved Suez Canal Authority"; the figures are facts,
restated here with attribution, and the reports themselves are not kept
(docs/sources.md, section 2.18).
"""

from __future__ import annotations

import io
import re
import sys

import pandas as pd
import pdfplumber

from ..config import BOUNDS_ANNUAL_LNG_TRANSITS, BOUNDS_ANNUAL_NET_TON_THOUSAND
from .base import Adapter, SourceError, http_get, read_cache

__all__ = ["REPORT_URL", "PAGE_URL", "FIRST_REPORT_YEAR", "parse_report_text", "combine", "ScaLngTransitsAnnual"]

#: The folder's name ends in three zero width spaces, which the address carries percent encoded.
REPORT_URL = ("https://www.suezcanal.gov.eg/English/Downloads/DownloadsDocLibrary/Navigation%20Reports/"
              "Annual%20Reports%E2%80%8B%E2%80%8B%E2%80%8B/{year}.pdf")
PAGE_URL = ("https://www.suezcanal.gov.eg/English/Downloads/Pages/default.aspx?folder=Navigation%20Reports/"
            "Annual%20Reports%E2%80%8B%E2%80%8B%E2%80%8B")
FIRST_REPORT_YEAR = 2008
#: thousands of net tons by which two prints of a year may differ, the Authority's own rounding
TONNAGE_RESTATEMENT = 3.0

# The two years, parted by a comma or, in the 2016 report, an Arabic comma.
_TITLE = re.compile(r"NO\s*&\s*Net\s*Ton\s*by\s*Ship\s*Type\s*\(\s*(\d{4})\s*[,\u060c]\s*(\d{4})\s*\)", re.I)
# "LNG" to 2013, "L N G" with spaces in the 2014 to 2016 reports, "LNG Ships" since 2017.
_ROW = re.compile(r"^\s*L\s?N\s?G(?:\s+Ships)?\s+([\d,]+)\s+([\d,]+)\s+-?[\d.]+\s+([\d,]+)\s+([\d,]+)\s+-?[\d.]+\s*$",
                  re.I | re.M)


def _int(text: str) -> int:
    return int(text.replace(",", ""))


def parse_report_text(text: str, *, year: int) -> list[dict]:
    """The LNG row of Table 3 as two rows, the year before and the report's year.

    Raises SourceError when the table's title does not name the two years, or
    the LNG row is missing or printed more than once.
    """
    title = _TITLE.search(text)
    if not title:
        raise SourceError("the %d report has no 'NO & Net Ton by Ship Type' table" % year)
    before, current = int(title.group(1)), int(title.group(2))
    if (before, current) != (year - 1, year):
        raise SourceError("the %d report's table is for %d and %d" % (year, before, current))
    rows = _ROW.findall(text[title.end():])
    if len(rows) != 1:
        raise SourceError("the %d report prints the LNG row %d times" % (year, len(rows)))
    n_before, n_current, t_before, t_current = rows[0]
    return [
        {"date": pd.Timestamp(year=before, month=1, day=1), "lng_ships": _int(n_before),
         "net_ton_thousand": _int(t_before), "report": year},
        {"date": pd.Timestamp(year=current, month=1, day=1), "lng_ships": _int(n_current),
         "net_ton_thousand": _int(t_current), "report": year},
    ]


def parse_report(pdf: bytes, *, year: int) -> list[dict]:
    with pdfplumber.open(io.BytesIO(pdf)) as document:
        text = "\n".join((page.extract_text() or "") for page in document.pages)
    return parse_report_text(text, year=year)


def combine(rows: list[dict]) -> tuple[pd.DataFrame, list[str]]:
    """One row a year from its latest print, and the restatements between prints, in words."""
    frame = pd.DataFrame(rows).sort_values(["date", "report"], kind="mergesort")
    restated = []
    for day, group in frame.groupby("date", sort=True):
        if len(group) < 2:
            continue
        earlier, later = group.iloc[0], group.iloc[-1]
        if earlier["lng_ships"] != later["lng_ships"]:
            raise SourceError("%d LNG ships in the %d report, %d in the %d report, for %d"
                              % (earlier["lng_ships"], earlier["report"], later["lng_ships"], later["report"], day.year))
        if abs(earlier["net_ton_thousand"] - later["net_ton_thousand"]) > TONNAGE_RESTATEMENT:
            raise SourceError("the net tonnage of %d is restated beyond rounding, %d then %d thousand"
                              % (day.year, earlier["net_ton_thousand"], later["net_ton_thousand"]))
        if earlier["net_ton_thousand"] != later["net_ton_thousand"]:
            restated.append("%d, %s then %s thousand tons" % (day.year, format(earlier["net_ton_thousand"], ","),
                                                             format(later["net_ton_thousand"], ",")))
    kept = frame.drop_duplicates("date", keep="last").reset_index(drop=True)
    return kept[["date", "lng_ships", "net_ton_thousand", "report"]], restated


class ScaLngTransitsAnnual(Adapter):
    """LNG carriers through the Suez Canal a year, both directions, and their net tonnage, from 2007."""

    name = "sca_lng_transits_annual"
    source = "Suez Canal Authority, annual navigation reports, Table 3, NO & Net Ton by Ship Type"
    url = REPORT_URL.format(year="{year}")
    page_url = PAGE_URL
    unit = "ships a year, and thousands of Suez Canal net tons"
    frequency = "annual"
    method = "parsed"
    required_cols = ("date", "lng_ships", "net_ton_thousand", "report")
    bounds = {"lng_ships": BOUNDS_ANNUAL_LNG_TRANSITS, "net_ton_thousand": BOUNDS_ANNUAL_NET_TON_THOUSAND}
    min_observations = {"lng_ships": 15, "net_ton_thousand": 15}
    observation_column = "lng_ships"
    licence_note = (
        "The Authority's site carries no licence and no terms page, only 'All Right Reserved'; the counts and "
        "tonnages are facts restated with attribution, and the reports are not kept."
    )

    def __init__(self, *, reports: dict[int, bytes] | None = None):
        # reports maps a report year to its PDF, for a run with no network
        self.reports = reports

    def fetch(self) -> pd.DataFrame:
        existing = read_cache(self.name, directory=self.directory())
        rows: list[dict] = []
        latest_held = FIRST_REPORT_YEAR - 1
        if existing is not None and len(existing):
            for record in existing.to_dict("records"):
                rows.append({"date": pd.Timestamp(record["date"]), "lng_ships": int(record["lng_ships"]),
                             "net_ton_thousand": int(record["net_ton_thousand"]), "report": int(record["report"])})
            latest_held = max(r["report"] for r in rows)
        read = []
        if self.reports is not None:
            for year in sorted(y for y in self.reports if y > latest_held):
                rows.extend(parse_report(self.reports[year], year=year))
                read.append(year)
        else:
            year = latest_held + 1
            while True:
                try:
                    pdf = http_get(REPORT_URL.format(year=year), timeout=120).content
                except SourceError as exc:
                    if "404" in str(exc) and year > FIRST_REPORT_YEAR:
                        break
                    raise
                rows.extend(parse_report(pdf, year=year))
                read.append(year)
                year += 1
        if not rows:
            raise SourceError("no report to read and nothing committed")
        frame, restated = combine(rows)
        years = sorted(set(int(r["report"]) for r in rows))
        self.vintage = "reports %d to %d" % (years[0], years[-1])
        self.note = (
            "%d report(s) read this run; the years stand as the latest of %d reports prints them, %d to %d. Each "
            "year's LNG ships and their Suez Canal net tonnage, both directions, every voyage, from Table 3 of the "
            "Authority's report for the year, checked against the next year's report: the counts agree in every "
            "pair and the tonnage is restated by rounding in %s. Source: Suez Canal Authority; facts restated "
            "with attribution."
            % (len(read), len(years), years[0], years[-1],
               ("%d year(s) (%s)" % (len(restated), "; ".join(restated))) if restated else "none")
        )
        return frame


def main() -> int:
    try:
        entry = ScaLngTransitsAnnual().run()
    except Exception as exc:
        print("FAILED sca_lng_transits_annual: %s" % exc)
        return 1
    print("ok     %s: %d years, %s to %s" % (entry["series"], entry["observations"], entry["first_date"], entry["last_date"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())

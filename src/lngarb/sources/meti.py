"""Japan's spot LNG prices from METI's survey, monthly, USD/MMBtu, March 2014 to March 2021.

METI's Spot LNG Price Statistics are simple averages of fixed price spot cargoes
bought by companies that consume them in Japan, converted to a DES basis, in two
forms: contract-based, from March 2014, and arrival-based, from April 2014. METI
discontinued the survey with the figures for March 2021, released on 14 May
2021, and JOGMEC's survey continues it from April 2021. METI does not publish a
month when fewer than two reporters imported spot LNG; such a month is a gap,
never a zero.

Where it is read from. METI publishes a PDF for every month and one historical
workbook with every month's latest figure, labelled "Detailed", or "Fixed" for
the one month METI corrected again the following March. The workbook is the
source here: it holds the whole series, and it agrees with every monthly PDF
this study could read. METI's site answers automated requests with a bot
challenge after a handful of files, and the series is frozen, so nothing here
refetches it: the workbook fetched once is kept in data/private/meti/ and
committed as a test fixture, and the parsed series is committed. The monthly
PDFs, which alone carry the preliminary figures, are a manual step.
"""

from __future__ import annotations

import io
import math
import sys
from pathlib import Path
from typing import Any

import pandas as pd

from ..config import BOUNDS_LNG_USD_MMBTU
from . import base
from .base import Adapter, SourceError

__all__ = ["PAGE_URL", "WORKBOOK_URL", "parse_workbook", "MetiSpotLngMonthly", "workbook_path"]

PAGE_URL = "https://www.meti.go.jp/english/statistics/sho/slng/index.html"
WORKBOOK_URL = "https://www.meti.go.jp/english/statistics/sho/slng/historical-data-e.xlsx"
SHEET = "historical data"

#: METI marks a month it did not publish with a multiplication sign.
NOT_PUBLISHED = chr(0x00D7)


def workbook_path() -> Path:
    """Where the workbook fetched once from METI is kept, gitignored."""
    return base.PRIVATE / "meti" / "historical-data-e.xlsx"


def _number(cell: Any, *, where: str) -> float:
    if cell is None:
        raise SourceError("%s is empty; METI marks an unpublished month with %r" % (where, NOT_PUBLISHED))
    if isinstance(cell, (int, float)) and not isinstance(cell, bool):
        return float(cell)
    if str(cell).strip() == NOT_PUBLISHED:
        return math.nan
    raise SourceError("%s holds %r, neither a price nor METI's gap marker" % (where, cell))


def parse_workbook(payload: bytes) -> pd.DataFrame:
    """Every month in METI's historical workbook, with METI's label for its figure."""
    import openpyxl

    book = openpyxl.load_workbook(io.BytesIO(payload), read_only=True, data_only=True)
    try:
        if SHEET not in book.sheetnames:
            raise SourceError("no %r sheet; sheets are %s" % (SHEET, book.sheetnames))
        rows = [list(r) for r in book[SHEET].iter_rows(values_only=True)]
    finally:
        book.close()

    header = [str(c).strip() if c is not None else "" for c in rows[0]]
    if header[:2] != ["Year", "Month"] or header[3:5] != ["Contract-based", "Arrival-based"]:
        raise SourceError("the header row reads %r, not the layout this parser knows" % (header,))
    if "USD/MMBtu" not in header[5]:
        raise SourceError("the unit cell reads %r, expected USD/MMBtu" % (header[5],))

    records = []
    year = None
    for number, row in enumerate(rows[1:], start=2):
        if all(c is None for c in row):
            continue
        if row[0] is not None:
            year = int(row[0])
        if year is None or row[1] is None:
            raise SourceError("row %d has no year or month" % number)
        label = str(row[2]).strip() if row[2] is not None else ""
        if label not in ("Detailed", "Fixed"):
            raise SourceError("row %d labels its figure %r" % (number, label))
        records.append(
            {
                "date": pd.Timestamp(year, int(row[1]), 1),
                "contract_based_usd_mmbtu": _number(row[3], where="row %d contract-based" % number),
                "arrival_based_usd_mmbtu": _number(row[4], where="row %d arrival-based" % number),
                "figure": label,
            }
        )
    frame = pd.DataFrame(records)
    if not frame["date"].is_monotonic_increasing or frame["date"].duplicated().any():
        raise SourceError("the months are not in order or repeat")
    return frame


class MetiSpotLngMonthly(Adapter):
    """METI spot LNG prices, contract-based and arrival-based, March 2014 to March 2021."""

    name = "meti_spot_lng_monthly"
    source = "Ministry of Economy, Trade and Industry of Japan, Spot LNG Price Statistics"
    url = WORKBOOK_URL
    page_url = PAGE_URL
    unit = "USD per MMBtu, DES"
    frequency = "monthly"
    method = "published"
    required_cols = ("date", "contract_based_usd_mmbtu", "arrival_based_usd_mmbtu", "figure")
    bounds = {
        "contract_based_usd_mmbtu": BOUNDS_LNG_USD_MMBTU,
        "arrival_based_usd_mmbtu": BOUNDS_LNG_USD_MMBTU,
    }
    min_observations = {"contract_based_usd_mmbtu": 70, "arrival_based_usd_mmbtu": 70}
    observation_column = "contract_based_usd_mmbtu"

    def __init__(self, *, from_file: Path | None = None, fetched_at: str = "2026-09-30T16:56:44Z"):
        self.from_file = from_file
        self.fetched_at = fetched_at

    def fetch(self) -> pd.DataFrame:
        path = Path(self.from_file) if self.from_file is not None else workbook_path()
        if not path.exists():
            raise SourceError(
                "%s is not on this machine. METI's site challenges automated requests "
                "and the series is frozen, so the workbook is saved once by hand, not "
                "fetched by this pipeline" % path
            )
        frame = parse_workbook(path.read_bytes())
        gaps_c = int(frame["contract_based_usd_mmbtu"].isna().sum())
        gaps_a = int(frame["arrival_based_usd_mmbtu"].isna().sum())
        self.vintage = "historical workbook, series discontinued with March 2021"
        self.note = (
            "Read from METI's historical workbook, fetched from %s at %s and not "
            "refetched. %d months; METI did not publish %d contract-based and %d "
            "arrival-based months, when fewer than two reporters imported spot LNG. "
            "Created by processing the information in the Spot LNG Price Statistics "
            "(Ministry of Economy, Trade and Industry of Japan)."
            % (WORKBOOK_URL, self.fetched_at, len(frame), gaps_c, gaps_a)
        )
        return frame

    def _entry(self, *, status: str, frame, note: str) -> dict:
        # Read from a file fetched once, so the fetch time is that fetch's, not
        # this run's.
        entry = super()._entry(status=status, frame=frame, note=note)
        entry["fetched_at"] = self.fetched_at
        return entry


def main() -> int:
    try:
        entry = MetiSpotLngMonthly().run()
    except Exception as exc:
        print("FAILED meti_spot_lng_monthly: %s" % exc)
        return 1
    print("ok     %s: %d months, %s to %s" % (entry["series"], entry["observations"], entry["first_date"], entry["last_date"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())

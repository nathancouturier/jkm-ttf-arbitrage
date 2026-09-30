"""EIA data tables: US LNG exports by destination country, and the Henry Hub spot price.

Exports by destination
----------------------
EIA's table "U.S. Natural Gas Exports and Re-Exports by Country" is published
as a legacy .xls workbook, monthly, in MMcf. Its sheet "Data 1" holds 77 series
in blocks: pipeline, LNG exports by vessel (one column per destination), LNG
by truck, LNG re-exports of previously imported cargoes, and compressed gas.
The study reads the LNG blocks only, identifies every series by its source key
(never by its name or its position, both of which vary), and maps every
destination code to a region through lngarb.config.EIA_DESTINATIONS. A code
that is not mapped stops the parse, so a new destination can never drop out of
a regional total unnoticed.

EIA revises the table, at least fourteen months back and including the China
column, and does not keep old releases online. Each release is therefore a
vintage. The cache holds the latest vintage in full, each row carrying the
release date it came from, and every value a later release changes is appended
to a revisions log with both vintages side by side, so any earlier vintage can
be rebuilt from the two files. The workbook of each release is also kept in
data/private/eia_exports/.

The LNG total, N9133US2, includes re-exports. The by vessel block does not.
Months are dated on the 15th, as EIA dates them.

Henry Hub
---------
The daily Henry Hub spot price, series RNGWHHD, from EIA's history workbook.
EIA's definitions page credits the spot price to "Refinitiv, an LSEG business".
EIA's NYMEX futures series on the same page stop on 5 April 2024, which is why
the study uses the spot price, averaged by month, as its proxy for the monthly
Henry Hub settlement an SPA refers to.
"""

from __future__ import annotations

import math
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import xlrd

from ..config import (
    BOUNDS_EXPORTS_MMCF,
    BOUNDS_HENRY_HUB_USD_MMBTU,
    EIA_DESTINATIONS,
)
from . import base
from .base import Adapter, SourceError, http_get, read_cache

__all__ = [
    "EXPORTS_PAGE_URL",
    "EXPORTS_XLS_URL",
    "HENRY_HUB_PAGE_URL",
    "HENRY_HUB_XLS_URL",
    "EXPORTS_FIRST_MONTH",
    "parse_exports_workbook",
    "parse_henry_hub_workbook",
    "compare_vintages",
    "LngExportsMonthly",
    "LngExportsRevisions",
    "HenryHubDaily",
]

EXPORTS_PAGE_URL = "https://www.eia.gov/dnav/ng/ng_move_expc_s1_m.htm"
EXPORTS_XLS_URL = "https://www.eia.gov/dnav/ng/xls/NG_MOVE_EXPC_S1_M.xls"
HENRY_HUB_PAGE_URL = "https://www.eia.gov/dnav/ng/hist/rngwhhdd.htm"
HENRY_HUB_XLS_URL = "https://www.eia.gov/dnav/ng/hist_xls/RNGWHHDd.xls"

#: The first month kept. Shale era exports from Sabine Pass start in February
#: 2016; January 2016 is kept so the first cargo is visible as a change.
EXPORTS_FIRST_MONTH = pd.Timestamp("2016-01-15")

#: Source key patterns of the LNG blocks. Anything else in the workbook is
#: pipeline or compressed gas and is not read.
_LNG_KEY = re.compile(r"^NGM_EPG0_(EVE|ETR|ERE|EVT)_NUS-(Z00|N[A-Z0-9]{2})_MMCF$")
_LNG_TOTAL_KEY = "N9133US2"
_BLOCKS = {
    "EVE": "exports by vessel",
    "ETR": "exports by truck",
    "ERE": "re-exports",
    "EVT": "exports by vessel and truck",
}


class ParseError(SourceError):
    """A workbook is not laid out the way this module expects."""


def _release_dates(contents: xlrd.sheet.Sheet) -> tuple[date, date | None]:
    """The release date and next release date printed on the Contents sheet."""
    found: dict[str, str] = {}
    for row in range(contents.nrows):
        cells = [str(v).strip() for v in contents.row_values(row)]
        for i, cell in enumerate(cells[:-1]):
            if cell in ("Release Date:", "Next Release Date:"):
                found[cell] = cells[i + 1]
    if "Release Date:" not in found:
        raise ParseError("the Contents sheet does not print a release date")
    released = datetime.strptime(found["Release Date:"], "%m/%d/%Y").date()
    upcoming = found.get("Next Release Date:")
    following = datetime.strptime(upcoming, "%m/%d/%Y").date() if upcoming else None
    return released, following


def _data_sheet(book: xlrd.book.Book, name: str) -> tuple[list[str], list[str], xlrd.sheet.Sheet]:
    sheet = book.sheet_by_name(name)
    keys = [str(v).strip() for v in sheet.row_values(1)]
    names = [str(v) for v in sheet.row_values(2)]
    if keys[0] != "Sourcekey" or str(names[0]).strip() != "Date":
        raise ParseError(
            "%s: expected 'Sourcekey' and 'Date' in the first column of rows 2 and 3, "
            "found %r and %r" % (name, keys[0], names[0])
        )
    return keys, names, sheet


def _cell_date(sheet: xlrd.sheet.Sheet, row: int, datemode: int) -> pd.Timestamp:
    value = sheet.cell_value(row, 0)
    if sheet.cell_type(row, 0) != xlrd.XL_CELL_DATE:
        raise ParseError("row %d of %s has %r where a date belongs" % (row + 1, sheet.name, value))
    return pd.Timestamp(xlrd.xldate_as_datetime(value, datemode))


def _cell_number(sheet: xlrd.sheet.Sheet, row: int, col: int) -> float:
    """A numeric cell as a float, an empty cell as NaN. Anything else is an error."""
    kind = sheet.cell_type(row, col)
    if kind in (xlrd.XL_CELL_EMPTY, xlrd.XL_CELL_BLANK):
        return math.nan
    if kind == xlrd.XL_CELL_NUMBER:
        return float(sheet.cell_value(row, col))
    raise ParseError(
        "row %d, column %d of %s holds %r, not a number"
        % (row + 1, col + 1, sheet.name, sheet.cell_value(row, col))
    )


def parse_exports_workbook(payload: bytes) -> tuple[pd.DataFrame, date, date | None]:
    """The LNG blocks of EIA's exports by country workbook, one row per month and series.

    Returns the long frame, the release date and the next release date.
    Columns: date, vintage, series_id, block, code, country, region, mmcf.
    """
    book = xlrd.open_workbook(file_contents=payload)
    released, following = _release_dates(book.sheet_by_name("Contents"))
    keys, names, sheet = _data_sheet(book, "Data 1")

    columns: list[tuple[int, dict[str, str]]] = []
    for col, key in enumerate(keys):
        if col == 0:
            continue
        if key == _LNG_TOTAL_KEY:
            columns.append(
                (col, {"series_id": key, "block": "LNG total including re-exports",
                       "code": "Z00", "country": "", "region": ""})
            )
            continue
        match = _LNG_KEY.match(key)
        if not match:
            continue
        block, code = match.groups()
        entry = {"series_id": key, "block": _BLOCKS[block], "code": code,
                 "country": "", "region": ""}
        if code != "Z00":
            destination = EIA_DESTINATIONS.get(code)
            if destination is None:
                raise ParseError(
                    "series %s (%r) names destination code %s, which "
                    "lngarb.config.EIA_DESTINATIONS does not map to a region"
                    % (key, names[col].strip(), code)
                )
            if destination.country.lower() not in re.sub(r"\s+", " ", names[col]).lower():
                raise ParseError(
                    "series %s is mapped to %s but EIA names it %r"
                    % (key, destination.country, names[col].strip())
                )
            entry["country"] = destination.country
            entry["region"] = destination.region
        columns.append((col, entry))

    required_blocks = {"exports by vessel", "re-exports", "LNG total including re-exports"}
    missing = required_blocks - {entry["block"] for _, entry in columns}
    if missing:
        raise ParseError("the workbook lacks the %s block(s)" % ", ".join(sorted(missing)))

    rows: list[dict[str, Any]] = []
    for row in range(3, sheet.nrows):
        when = _cell_date(sheet, row, book.datemode)
        if when < EXPORTS_FIRST_MONTH:
            continue
        for col, entry in columns:
            rows.append({"date": when, "vintage": released.isoformat(), **entry,
                         "mmcf": _cell_number(sheet, row, col)})
    frame = pd.DataFrame(rows)
    frame = frame.sort_values(["date", "series_id"], kind="stable").reset_index(drop=True)
    return frame, released, following


def parse_henry_hub_workbook(payload: bytes) -> tuple[pd.DataFrame, date, date | None]:
    """EIA's daily Henry Hub spot price. Returns the frame, release and next release."""
    book = xlrd.open_workbook(file_contents=payload)
    released, following = _release_dates(book.sheet_by_name("Contents"))
    keys, names, sheet = _data_sheet(book, "Data 1")
    if keys[1:] != ["RNGWHHD"]:
        raise ParseError("expected the one series RNGWHHD, found %r" % (keys[1:],))
    rows = [
        {"date": _cell_date(sheet, row, book.datemode),
         "henry_hub_usd_mmbtu": _cell_number(sheet, row, 1)}
        for row in range(3, sheet.nrows)
    ]
    return pd.DataFrame(rows), released, following


def compare_vintages(before: pd.DataFrame, after: pd.DataFrame) -> pd.DataFrame:
    """Every value a later vintage changed, with both vintages side by side.

    A month the earlier vintage did not yet have is new data, not a revision,
    and is not listed. A value that was present and became empty, or the
    reverse, is a revision.
    """
    key = ["date", "series_id"]
    old = before[key + ["vintage", "country", "mmcf"]].rename(
        columns={"vintage": "vintage_before", "mmcf": "mmcf_before"}
    )
    new = after[key + ["vintage", "country", "mmcf"]].rename(
        columns={"vintage": "vintage_after", "mmcf": "mmcf_after", "country": "country_after"}
    )
    old = old.assign(date=pd.to_datetime(old["date"]))
    new = new.assign(date=pd.to_datetime(new["date"]))
    both = old.merge(new, on=key, how="left")
    before_value = both["mmcf_before"]
    after_value = both["mmcf_after"]
    same = (before_value == after_value) | (before_value.isna() & after_value.isna())
    changed = both[~same].copy()
    changed["vintage_after"] = changed["vintage_after"].fillna(after["vintage"].iloc[0])
    changed = changed[
        ["date", "series_id", "country", "vintage_before", "mmcf_before",
         "vintage_after", "mmcf_after"]
    ]
    return changed.sort_values(["date", "series_id"], kind="stable").reset_index(drop=True)


def private_dir() -> Path:
    """Where the workbook of each release is kept, gitignored."""
    return base.PRIVATE / "eia_exports"


class LngExportsRevisions(Adapter):
    """Every value a release of the exports table changed, vintage against vintage."""

    name = "eia_lng_exports_revisions"
    source = "U.S. Energy Information Administration, U.S. Natural Gas Exports and Re-Exports by Country, compared release by release"
    url = EXPORTS_XLS_URL
    page_url = EXPORTS_PAGE_URL
    unit = "MMcf"
    frequency = "monthly"
    method = "derived"
    unique_dates = False
    required_cols = ("date", "series_id", "vintage_before", "vintage_after")
    observation_column = "vintage_after"

    def __init__(self, additions: pd.DataFrame):
        self.additions = additions

    def fetch(self) -> pd.DataFrame:
        existing = read_cache(self.name, directory=self.directory())
        frames = [self.additions] if existing is None else [existing, self.additions]
        merged = pd.concat(frames, ignore_index=True)
        merged["date"] = pd.to_datetime(merged["date"])
        merged = merged.drop_duplicates(
            subset=["date", "series_id", "vintage_before", "vintage_after"], keep="first"
        )
        return merged.sort_values(["date", "series_id", "vintage_after"], kind="stable").reset_index(drop=True)


class LngExportsMonthly(Adapter):
    """US LNG exports and re-exports by destination, the latest release, in MMcf."""

    name = "eia_lng_exports_monthly"
    source = "U.S. Energy Information Administration, U.S. Natural Gas Exports and Re-Exports by Country"
    url = EXPORTS_XLS_URL
    page_url = EXPORTS_PAGE_URL
    unit = "MMcf per month"
    frequency = "monthly"
    method = "published"
    unique_dates = False
    required_cols = ("date", "vintage", "series_id", "block", "country", "region", "mmcf")
    bounds = {"mmcf": BOUNDS_EXPORTS_MMCF}
    min_observations = {"mmcf": 1000}
    observation_column = "mmcf"
    min_rows = 1000

    def __init__(self, *, from_file: Path | None = None, fetched_at: str | None = None):
        # from_file reads a workbook already fetched, with the time it was
        # fetched, so a release collected before this adapter existed can be
        # recorded as the vintage it is.
        self.from_file = from_file
        self.fetched_at = fetched_at
        self.revisions: pd.DataFrame | None = None

    def fetch(self) -> pd.DataFrame:
        if self.from_file is not None:
            payload = Path(self.from_file).read_bytes()
            how = "read from a copy fetched from %s at %s" % (EXPORTS_XLS_URL, self.fetched_at)
        else:
            payload = http_get(EXPORTS_XLS_URL, timeout=60).content
            how = "fetched from %s" % EXPORTS_XLS_URL
        frame, released, following = parse_exports_workbook(payload)

        existing = read_cache(self.name, directory=self.directory())
        if existing is not None and len(existing):
            existing_vintage = str(existing["vintage"].iloc[-1])
            if released.isoformat() < existing_vintage:
                raise SourceError(
                    "the workbook is the release of %s, older than the committed "
                    "release of %s" % (released, existing_vintage)
                )
            if released.isoformat() != existing_vintage:
                self.revisions = compare_vintages(existing, frame)
        folder = private_dir()
        folder.mkdir(parents=True, exist_ok=True)
        (folder / ("NG_MOVE_EXPC_S1_M_release_%s.xls" % released.isoformat())).write_bytes(payload)

        self.vintage = "release of %s, next release %s" % (released, following)
        self.note = (
            "%s. Months are dated on the 15th as EIA dates them, kept from %s. "
            "The LNG total N9133US2 includes re-exports; the by vessel block does not."
            % (how, EXPORTS_FIRST_MONTH.date())
        )
        return frame

    def run(self) -> dict:
        entry = super().run()
        if self.revisions is not None and len(self.revisions):
            LngExportsRevisions(self.revisions).run()
        return entry


class HenryHubDaily(Adapter):
    """EIA's daily Henry Hub spot price, USD/MMBtu."""

    name = "eia_henry_hub_daily"
    source = "U.S. Energy Information Administration, Henry Hub Natural Gas Spot Price, credited by EIA to Refinitiv, an LSEG business"
    url = HENRY_HUB_XLS_URL
    page_url = HENRY_HUB_PAGE_URL
    unit = "USD per MMBtu"
    frequency = "daily"
    method = "published"
    required_cols = ("date", "henry_hub_usd_mmbtu")
    bounds = {"henry_hub_usd_mmbtu": BOUNDS_HENRY_HUB_USD_MMBTU}
    min_observations = {"henry_hub_usd_mmbtu": 5000}
    observation_column = "henry_hub_usd_mmbtu"

    def __init__(self, *, from_file: Path | None = None, fetched_at: str | None = None):
        self.from_file = from_file
        self.fetched_at = fetched_at

    def fetch(self) -> pd.DataFrame:
        if self.from_file is not None:
            payload = Path(self.from_file).read_bytes()
            how = "read from a copy fetched from %s at %s" % (HENRY_HUB_XLS_URL, self.fetched_at)
        else:
            payload = http_get(HENRY_HUB_XLS_URL, timeout=60).content
            how = "fetched from %s" % HENRY_HUB_XLS_URL
        frame, released, following = parse_henry_hub_workbook(payload)
        self.vintage = "release of %s, next release %s" % (released, following)
        self.note = (
            "%s. Holidays are omitted except from July 2015 to November 2017, when "
            "EIA's rows repeat the previous business day; 1997 to 2006 are sparse." % how
        )
        return frame


def main(argv: list[str] | None = None) -> int:
    failed = 0
    for adapter in (LngExportsMonthly(), HenryHubDaily()):
        try:
            entry = adapter.run()
        except Exception as exc:
            failed += 1
            print("FAILED %s: %s" % (adapter.name, exc))
        else:
            print(
                "ok     %s: %d observations, %s to %s, %s"
                % (entry["series"], entry["observations"], entry["first_date"],
                   entry["last_date"], entry["vintage"])
            )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

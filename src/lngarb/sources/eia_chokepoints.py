"""LNG through the world's maritime chokepoints, as EIA estimates it from tanker tracking.

Two pages of the U.S. Energy Information Administration carry the figures,
in billion cubic feet a day, as "EIA analysis based on Vortexa tanker
tracking data":

* "World Oil Transit Chokepoints", an analysis page revised about yearly,
  with a table per chokepoint for the calendar years from 2020 and the first
  half of the latest year: the Strait of Hormuz, the Strait of Malacca, the
  Suez Canal, the Bab el-Mandeb Strait, the Danish Straits, the Turkish
  Straits and the Cape of Good Hope.
* The Short-Term Energy Outlook's "Global Energy Security" article, revised
  with each monthly Outlook, with the same tables by quarter for the latest
  six quarters, the Panama Canal among them.

Each table holds a row "LNG flows through ..." that the adapter keeps; the
oil rows are not. The pages are US government publications in the public
domain, to be acknowledged with their publication date; the analysis rests
on Vortexa's data, which EIA credits and this study credits in turn. A cell
printed as a dash is kept missing: EIA does not say whether it is zero or
not available.
"""

from __future__ import annotations

import io
import re
import sys

import pandas as pd

from ..config import BOUNDS_LNG_BCF_PER_DAY
from .base import Adapter, SourceError, http_get

__all__ = ["CHOKEPOINTS_URL", "STEO_URL", "CHOKEPOINT_WORDS", "parse_annual", "parse_quarterly",
           "EiaChokepointLngAnnual", "EiaSteoChokepointLngQuarterly"]

CHOKEPOINTS_URL = "https://www.eia.gov/international/content/analysis/special_topics/World_Oil_Transit_Chokepoints/"
STEO_URL = "https://www.eia.gov/outlooks/steo/report/energysecurity/article.php"

#: the chokepoint each LNG row names, keyed by a word its label carries
CHOKEPOINT_WORDS = (
    ("hormuz", "Strait of Hormuz"),
    ("malacca", "Strait of Malacca"),
    ("suez", "Suez Canal"),
    ("mandeb", "Bab el-Mandeb Strait"),
    ("danish", "Danish Straits"),
    ("dardanelles", "Turkish Straits"),
    ("turkish", "Turkish Straits"),
    ("panama", "Panama Canal"),
    ("cape", "Cape of Good Hope"),
)
_DATE = r"([A-Z][a-z]+ \d{1,2}, \d{4})"
_LAST_UPDATED = re.compile(r"Last Updated:(?:</strong>)?\s*" + _DATE)
#: the article's own release date, printed in plain text under its heading
_RELEASE_ARTICLE = re.compile(r"Release Date:\s*" + _DATE)
#: the Outlook's release date, in the page's header
_RELEASE_OUTLOOK = re.compile(r"Release Date:</strong>\s*" + _DATE)


def _chokepoint(label: str) -> str:
    low = label.lower()
    for word, name in CHOKEPOINT_WORDS:
        if word in low:
            return name
    raise SourceError("an LNG row names a chokepoint the adapter does not know: %r" % label)


def _value(cell) -> float:
    text = "" if cell is None else str(cell).strip()
    if text in ("", "-", "nan", "NaN", "None"):
        return float("nan")
    return float(text)


def _lng_rows(page: bytes | str) -> list[tuple[str, dict[str, float]]]:
    text = page.decode("utf-8", errors="replace") if isinstance(page, bytes) else page
    tables = pd.read_html(io.StringIO(text))
    out = []
    for table in tables:
        for record in table.itertuples(index=False):
            label = str(record[0])
            if not label.lower().startswith("lng flows"):
                continue
            # A table whose header has a units row above the years reads as a two level column.
            values = {str(col[-1] if isinstance(col, tuple) else col).strip(): _value(cell)
                      for col, cell in zip(table.columns[1:], record[1:])}
            out.append((_chokepoint(label), values))
    if not out:
        raise SourceError("the page carries no 'LNG flows' row")
    return out


def _annual_date(column: str) -> tuple[pd.Timestamp, str]:
    if re.fullmatch(r"\d{4}", column):
        return pd.Timestamp(year=int(column), month=1, day=1), "year"
    half = re.fullmatch(r"1H(\d{2})", column)
    if half:
        return pd.Timestamp(year=2000 + int(half.group(1)), month=1, day=1), "first_half"
    raise SourceError("a column of the chokepoints table is neither a year nor a first half: %r" % column)


def parse_annual(page: bytes | str) -> tuple[pd.DataFrame, str]:
    """The annual table's LNG rows as a long frame, and the page's 'Last Updated' date."""
    text = page.decode("utf-8", errors="replace") if isinstance(page, bytes) else page
    updated = _LAST_UPDATED.search(text)
    if not updated:
        raise SourceError("the chokepoints page carries no 'Last Updated' date")
    rows = []
    for chokepoint, values in _lng_rows(text):
        for column, value in values.items():
            day, period = _annual_date(column)
            rows.append({"date": day, "period": period, "chokepoint": chokepoint, "bcf_per_day": value})
    frame = pd.DataFrame(rows).sort_values(["date", "period", "chokepoint"], kind="mergesort").reset_index(drop=True)
    return frame, updated.group(1)


def _quarter_date(column: str) -> pd.Timestamp:
    found = re.fullmatch(r"([1-4])Q(\d{2})", column)
    if not found:
        raise SourceError("a column of the Outlook's table is not a quarter: %r" % column)
    return pd.Timestamp(year=2000 + int(found.group(2)), month=3 * (int(found.group(1)) - 1) + 1, day=1)


def parse_quarterly(page: bytes | str) -> tuple[pd.DataFrame, dict[str, str]]:
    """The Outlook article's LNG rows as a long frame, and the article's and the Outlook's release dates."""
    text = page.decode("utf-8", errors="replace") if isinstance(page, bytes) else page
    release = _RELEASE_ARTICLE.search(text)
    outlook = _RELEASE_OUTLOOK.search(text)
    if not release or not outlook:
        raise SourceError("the Outlook article carries no release date of its own, or the page none of the Outlook")
    rows = []
    for chokepoint, values in _lng_rows(text):
        for column, value in values.items():
            rows.append({"date": _quarter_date(column), "chokepoint": chokepoint, "bcf_per_day": value})
    frame = pd.DataFrame(rows).sort_values(["date", "chokepoint"], kind="mergesort").reset_index(drop=True)
    return frame, {"article": release.group(1), "outlook": outlook.group(1)}


_LICENCE = (
    "US government publication in the public domain, acknowledged with its publication date as EIA asks; the "
    "figures are EIA's analysis based on Vortexa tanker tracking data, which EIA credits."
)


class EiaChokepointLngAnnual(Adapter):
    """LNG through each chokepoint, billion cubic feet a day, by calendar year from 2020 and the latest first half."""

    name = "eia_chokepoint_lng_annual"
    source = "U.S. Energy Information Administration, World Oil Transit Chokepoints, analysis based on Vortexa tanker tracking data"
    url = CHOKEPOINTS_URL
    page_url = CHOKEPOINTS_URL
    unit = "billion cubic feet per day"
    frequency = "annual"
    method = "published"
    required_cols = ("date", "period", "chokepoint", "bcf_per_day")
    unique_dates = False
    bounds = {"bcf_per_day": BOUNDS_LNG_BCF_PER_DAY}
    min_observations = {"bcf_per_day": 30}
    observation_column = "bcf_per_day"
    licence_note = _LICENCE

    def __init__(self, *, from_file=None, fetched_at: str | None = None):
        self.from_file = from_file
        self.fetched_at = fetched_at

    def fetch(self) -> pd.DataFrame:
        if self.from_file is not None:
            page = open(self.from_file, "rb").read()
        else:
            page = http_get(CHOKEPOINTS_URL, timeout=120).content
        frame, updated = parse_annual(page)
        years = sorted(set(frame["date"].dt.year))
        self.vintage = "page last updated %s" % updated
        self.note = (
            "LNG through each chokepoint in billion cubic feet a day, by calendar year %d to %d and the first "
            "half of %d, the rows 'LNG flows through ...' of EIA's tables, page last updated %s. EIA's analysis "
            "based on Vortexa tanker tracking data; volumes, not transits, and not split by origin. Source: "
            "U.S. Energy Information Administration (%s)."
            % (years[0], years[-2] if len(years) > 1 else years[0], years[-1], updated, updated)
        )
        return frame


class EiaSteoChokepointLngQuarterly(Adapter):
    """LNG through each chokepoint, billion cubic feet a day, by quarter, from the Short-Term Energy Outlook."""

    name = "eia_steo_chokepoint_lng_quarterly"
    source = "U.S. Energy Information Administration, Short-Term Energy Outlook, Global Energy Security, analysis based on Vortexa tanker tracking data"
    url = STEO_URL
    page_url = STEO_URL
    unit = "billion cubic feet per day"
    frequency = "quarterly"
    method = "published"
    required_cols = ("date", "chokepoint", "bcf_per_day")
    unique_dates = False
    bounds = {"bcf_per_day": BOUNDS_LNG_BCF_PER_DAY}
    min_observations = {"bcf_per_day": 30}
    observation_column = "bcf_per_day"
    licence_note = _LICENCE

    def __init__(self, *, from_file=None, fetched_at: str | None = None):
        self.from_file = from_file
        self.fetched_at = fetched_at

    def fetch(self) -> pd.DataFrame:
        if self.from_file is not None:
            page = open(self.from_file, "rb").read()
        else:
            page = http_get(STEO_URL, timeout=120).content
        frame, released = parse_quarterly(page)
        first, last = frame["date"].iloc[0], frame["date"].iloc[-1]
        vintage = "article released %s, on the page of the Outlook released %s" % (released["article"], released["outlook"])
        self.vintage = vintage
        self.note = (
            "LNG through each chokepoint in billion cubic feet a day by quarter, %s to %s, the rows 'LNG flows "
            "through ...' of the article's tables, %s; the article is revised with the Outlook and the "
            "quarters it shows move with it, so an earlier quarter drops out of the page and stays only in the "
            "committed cache's history. A cell EIA prints as a dash is missing: EIA does not say whether it is "
            "zero or not available. EIA's analysis based on Vortexa tanker tracking data; volumes, not transits. "
            "Source: U.S. Energy Information Administration (%s)."
            % ("Q%d %d" % ((first.month - 1) // 3 + 1, first.year), "Q%d %d" % ((last.month - 1) // 3 + 1, last.year),
               vintage, released["article"])
        )
        return frame


def main() -> int:
    failed = 0
    for adapter in (EiaChokepointLngAnnual(), EiaSteoChokepointLngQuarterly()):
        try:
            entry = adapter.run()
        except Exception as exc:
            print("FAILED %s: %s" % (adapter.name, exc))
            failed = 1
            continue
        print("ok     %s: %d observations, %s to %s" % (entry["series"], entry["observations"], entry["first_date"], entry["last_date"]))
    return failed


if __name__ == "__main__":
    sys.exit(main())

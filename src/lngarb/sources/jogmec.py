"""Japan's spot LNG prices from JOGMEC's survey, monthly, USD/MMBtu, from April 2021. Private.

JOGMEC continues METI's survey: simple averages of fixed price spot cargoes for
delivery to Japan, reported by companies that consume them, converted to a DES
basis, in a contract-based and an arrival-based form. JOGMEC writes the unit as
"USD/MBtu"; the same pages quote Henry Hub in the same unit at a level that only
makes sense per million Btu, so it is read as USD/MMBtu, an inference recorded
in docs/sources.md.

Each month has one page, printed first as preliminary. The confirmed figure has
no page of its own: it is printed in the first column of the next month's page.
A month JOGMEC does not disclose, because fewer than two companies imported spot
LNG, is printed as a horizontal bar and kept as missing; a month undisclosed at
the preliminary stage can be disclosed when confirmed.

The arrival-based definition changed with the April 2023 release, from cargoes
contracted and delivered in the month to cargoes delivered in the month whenever
contracted. Every arrival-based figure for a month before April 2023 is marked
with the old definition.

JOGMEC's terms permit use beyond private use, education and quotation only with
its permission, which has not been requested yet. Until it is granted this series is
not committable: it is written to data/private/ and nothing derived from it is
published.
"""

from __future__ import annotations

import math
import re
import sys
from pathlib import Path
from typing import Any

import pandas as pd
from bs4 import BeautifulSoup

from ..config import BOUNDS_LNG_USD_MMBTU
from . import base
from .base import Adapter, SourceError, http_get

__all__ = ["LIST_URL", "parse_page", "assemble", "JogmecSpotLngMonthly", "pages_dir"]

LIST_URL = "https://journal.jogmec.go.jp/oilgas/nglng-en/spotprice/index.html"
PAGE_URL = "https://journal.jogmec.go.jp/oilgas/nglng-en/spotprice/{month}-preliminary.html"

#: The horizontal bar JOGMEC prints for a month it does not disclose.
NOT_DISCLOSED = chr(0x2015)

#: The first month whose arrival-based figure uses the new definition.
ARRIVAL_NEW_DEFINITION_FROM = pd.Timestamp("2023-04-01")

_HEADER = re.compile(r"^([A-Z][a-z]+) (\d{4}) \((Preliminary|Confirmed)\)$")


def pages_dir() -> Path:
    """Where JOGMEC's monthly pages are kept, gitignored."""
    return base.PRIVATE / "jogmec" / "pages"


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace(chr(0x00A0), " ")).strip()


def _value(cell: str, *, where: str) -> float:
    if cell == NOT_DISCLOSED:
        return math.nan
    try:
        return float(cell)
    except ValueError as exc:
        raise SourceError("%s holds %r, neither a price nor JOGMEC's bar" % (where, cell)) from exc


def parse_page(html: bytes | str, *, where: str) -> list[dict[str, Any]]:
    """The figures on one monthly page: one record per month shown, with its vintage."""
    soup = BeautifulSoup(html, "lxml")
    if "USD/MBtu" not in soup.get_text():
        raise SourceError("%s does not state its unit as USD/MBtu" % where)
    tables = soup.find_all("table")
    if len(tables) != 1:
        raise SourceError("%s carries %d tables, expected one" % (where, len(tables)))
    rows = [[_clean(c.get_text(" ")) for c in tr.find_all(["th", "td"])] for tr in tables[0].find_all("tr")]
    if len(rows) != 3 or rows[0][0] != "Contracted Month":
        raise SourceError("%s has a table this parser does not know: %r" % (where, rows))
    labels = {rows[1][0]: rows[1][1:], rows[2][0]: rows[2][1:]}
    if set(labels) != {"Contract-based price", "Arrival-based price"}:
        raise SourceError("%s labels its rows %r" % (where, list(labels)))

    records = []
    for index, header in enumerate(rows[0][1:]):
        match = _HEADER.match(header)
        if not match:
            raise SourceError("%s has a column headed %r" % (where, header))
        month = pd.to_datetime("%s %s" % (match.group(1), match.group(2)), format="%B %Y")
        records.append(
            {
                "date": month,
                "vintage": match.group(3).lower(),
                "contract": _value(labels["Contract-based price"][index], where="%s %s contract" % (where, header)),
                "arrival": _value(labels["Arrival-based price"][index], where="%s %s arrival" % (where, header)),
            }
        )
    return records


def assemble(records: list[dict[str, Any]]) -> pd.DataFrame:
    """One row per month: the preliminary and the confirmed figure of each basis, and the latest."""
    frame = pd.DataFrame(records)
    months = sorted(frame["date"].unique())
    rows = []
    for month in months:
        this = frame[frame["date"] == month]
        prelim = this[this["vintage"] == "preliminary"]
        confirmed = this[this["vintage"] == "confirmed"]
        if len(prelim) != 1 or len(confirmed) > 1:
            raise SourceError("%s is printed %d time(s) as preliminary and %d as confirmed"
                              % (pd.Timestamp(month).strftime("%Y-%m"), len(prelim), len(confirmed)))
        row = {"date": pd.Timestamp(month)}
        for basis in ("contract", "arrival"):
            p = float(prelim[basis].iloc[0])
            c = float(confirmed[basis].iloc[0]) if len(confirmed) else math.nan
            row["%s_preliminary_usd_mmbtu" % basis] = p
            row["%s_confirmed_usd_mmbtu" % basis] = c
            row["%s_usd_mmbtu" % basis] = c if len(confirmed) else p
        row["vintage"] = "confirmed" if len(confirmed) else "preliminary"
        row["arrival_definition"] = (
            "delivered in the month, whenever contracted"
            if pd.Timestamp(month) >= ARRIVAL_NEW_DEFINITION_FROM
            else "contracted and delivered in the month"
        )
        rows.append(row)
    return pd.DataFrame(rows)


class JogmecSpotLngMonthly(Adapter):
    """JOGMEC spot LNG prices for delivery to Japan, monthly, from April 2021. Not committable."""

    name = "jogmec_spot_lng_monthly"
    source = "Japan Organization for Metals and Energy Security, monthly spot LNG prices for delivery to Japan"
    url = LIST_URL
    page_url = LIST_URL
    unit = "USD per MMBtu, DES (JOGMEC writes USD/MBtu)"
    frequency = "monthly"
    method = "parsed"
    committable = False
    # licence_note: the registry's, in lngarb.config.SOURCES
    required_cols = ("date", "contract_usd_mmbtu", "arrival_usd_mmbtu", "vintage", "arrival_definition")
    bounds = {
        "contract_usd_mmbtu": BOUNDS_LNG_USD_MMBTU,
        "arrival_usd_mmbtu": BOUNDS_LNG_USD_MMBTU,
        "contract_preliminary_usd_mmbtu": BOUNDS_LNG_USD_MMBTU,
        "contract_confirmed_usd_mmbtu": BOUNDS_LNG_USD_MMBTU,
        "arrival_preliminary_usd_mmbtu": BOUNDS_LNG_USD_MMBTU,
        "arrival_confirmed_usd_mmbtu": BOUNDS_LNG_USD_MMBTU,
    }
    min_observations = {name: 10 for name in bounds}
    observation_column = "contract_usd_mmbtu"

    def __init__(self, *, offline: bool = False):
        # offline reads only the pages already saved; the pipeline passes it in
        # tests and wherever the network must not be used.
        self.offline = offline

    def _refresh_pages(self) -> None:
        """Save any month the list page names that is not saved yet, and the two latest again.

        The two latest are refetched because a confirmed figure appears on the
        next month's page and JOGMEC edits pages in place.
        """
        listing = http_get(LIST_URL).text
        months = sorted(set(re.findall(r"spotprice/(\d{6})-preliminary\.html", listing)))
        if not months:
            raise SourceError("the list page links no monthly page")
        folder = pages_dir()
        folder.mkdir(parents=True, exist_ok=True)
        latest = set(months[-2:])
        for month in months:
            path = folder / ("%s.html" % month)
            if path.exists() and month not in latest:
                continue
            path.write_bytes(http_get(PAGE_URL.format(month=month)).content)

    def _entry(self, *, status: str, frame: pd.DataFrame | None, note: str) -> dict:
        entry = super()._entry(status=status, frame=frame, note=note)
        if self.offline:
            # Reading the saved pages again is not a fetch: the entry keeps the
            # time of the last run that did fetch.
            previous = next(
                (e for e in base.manifest_read().get("series", []) if e.get("series") == self.name),
                None,
            )
            entry["fetched_at"] = previous.get("fetched_at") if previous else None
        return entry

    def fetch(self) -> pd.DataFrame:
        if not self.offline:
            self._refresh_pages()
        folder = pages_dir()
        paths = sorted(folder.glob("*.html")) if folder.exists() else []
        if not paths:
            raise SourceError("no JOGMEC page is saved in %s" % folder)
        records = []
        for path in paths:
            records.extend(parse_page(path.read_bytes(), where=path.name))
        frame = assemble(records)
        confirmed = int((frame["vintage"] == "confirmed").sum())
        self.provisional_from = frame.loc[frame["vintage"] == "preliminary", "date"].min().strftime("%Y-%m-%d")
        self.vintage = "%d pages, %d months confirmed" % (len(paths), confirmed)
        self.note = (
            "%d monthly pages read. The latest figure of each month is the confirmed one "
            "where the next month's page exists, else the preliminary one. Undisclosed "
            "months are missing. Arrival-based figures before April 2023 use JOGMEC's "
            "old definition." % len(paths)
        )
        return frame


def main() -> int:
    try:
        entry = JogmecSpotLngMonthly().run()
    except Exception as exc:
        print("FAILED jogmec_spot_lng_monthly: %s" % exc)
        return 1
    print("ok     %s: %d months with a contract-based figure, %s to %s, private" % (
        entry["series"], entry["observations"], entry["first_date"], entry["last_date"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())

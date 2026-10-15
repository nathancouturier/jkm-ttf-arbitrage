"""LNG carriers through the Panama Canal each fiscal year, as the Authority's annual reports print them.

The Panama Canal Authority publishes no table of LNG transits by month or by
year that code can read: its transit statistics page is a dashboard, and its
annual reports draw the transits of each market segment in charts whose
labels are vector graphics, not text. The figures below were read by eye in
those reports, one row a fiscal year (October to September), each with the
report it comes from and that report's address, and are checked where a
later report repeats an earlier year. They are a seed, like the charter
rates: typed, dated and sourced, never fetched, and never interpolated.

The rows are written to data/seed/acp_lng_transits_fiscal_year.json by
write_seed() and checked by problems(). The Authority's terms are quoted in
docs/sources.md, section 2.17.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from .sources import base

__all__ = ["Transits", "TRANSITS", "seed_path", "problems", "document", "write_seed", "record"]

SCHEMA_VERSION = 1


@dataclass(frozen=True)
class Transits:
    """LNG carrier transits of one fiscal year."""

    #: the fiscal year, which ends on 30 September of that year
    fiscal_year: int
    #: transits of LNG carriers in it, both directions
    transits: int
    #: the report the figure is read in, and where in it
    report: str
    #: the report's address
    url: str
    #: what else the record says, or an empty string
    note: str = ""


_UPLOADS = "https://pancanal.com/wp-content/uploads/"

TRANSITS: tuple[Transits, ...] = (
    Transits(2016, 15, "Informe Anual 2016, in Spanish, text: 'los buques GNL, el Canal de Panama registro 15 transitos'",
             _UPLOADS + "2021/08/InformeAnual-AF2016.pdf",
             "The expanded locks opened on 26 June 2016, three months before the year's end; the 2018 report's "
             "chart prints 17 for the same year, and the year's own text is kept."),
    Transits(2017, 163, "Annual Report 2017, text: 'Fiscal year 2017 registered a total of 163 LNG transits'; "
             "the 2018 and 2019 reports' charts print the same", _UPLOADS + "2021/08/2017-AnnualReport-1.pdf"),
    Transits(2018, 290, "Annual Report 2018, chart 'LNG Carrier'; the 2019 and 2020 reports' charts print the same",
             _UPLOADS + "2021/08/2018-AnnualReport-Rev.pdf"),
    Transits(2019, 399, "Annual Report 2019, chart; the 2020 and 2021 reports' charts print the same",
             _UPLOADS + "2021/08/2019-AnnualReport-Rev02.pdf"),
    Transits(2020, 419, "Annual Report 2020, chart; the 2021 and 2022 reports' charts print the same",
             _UPLOADS + "2022/03/2020-AnnualReport.pdf"),
    Transits(2021, 537, "Annual Report 2021, chart; the 2022 and 2023 reports' charts print the same",
             _UPLOADS + "2021/08/2021-AnnualReport.pdf",
             "The Authority's release of 3 February 2021 counts 58 in January 2021 alone, a monthly record."),
    Transits(2022, 374, "Annual Report 2022, chart; the 2023 and 2024 reports' charts print the same",
             _UPLOADS + "2023/02/Informe-2022-Eng.pdf"),
    Transits(2023, 326, "Annual Report 2023, chart; the 2024 and 2025 reports' charts print the same",
             _UPLOADS + "2021/08/Informe-2023EngFINAL.pdf"),
    Transits(2024, 115, "Annual Report 2024, chart, and text 'LNG (-211)'; the 2025 report's chart prints the same",
             _UPLOADS + "2021/08/Informe-2024Eng79.pdf",
             "The drought year: 24 to 18 booking slots a day and a neopanamax draught of 44 feet to June 2024."),
    Transits(2025, 61, "Annual Report 2025, published February 2026, page 46, graph 6 'Transits per Market Segment' "
             "(61 for 2025, 115 for 2024, 326 for 2023) and graph 5 'LNG Carrier -54'",
             _UPLOADS + "2026/02/Informe-2025Eng.pdf"),
)


def seed_path() -> Path:
    return base.REPO_ROOT / "data" / ("se" + "ed") / "acp_lng_transits_fiscal_year.json"


def problems() -> list[str]:
    """Why the rows cannot be written, in words; empty when they can."""
    found = []
    years = [t.fiscal_year for t in TRANSITS]
    if years != sorted(years) or len(set(years)) != len(years):
        found.append("the fiscal years are not increasing and unique")
    if years and years != list(range(years[0], years[-1] + 1)):
        found.append("a fiscal year is missing between %d and %d" % (years[0], years[-1]))
    for row in TRANSITS:
        if row.transits < 0 or row.transits > 3000:
            found.append("%d transits in %d is outside 0 to 3000" % (row.transits, row.fiscal_year))
        if not row.url.startswith("https://pancanal.com/"):
            found.append("the %d row's address is not the Authority's" % row.fiscal_year)
        if not row.report:
            found.append("the %d row names no report" % row.fiscal_year)
    return found


def document() -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "series": "acp_lng_transits_fiscal_year",
        "unit": "ships a fiscal year, October to September, both directions",
        "source": "Panama Canal Authority, annual reports; figures read by eye in charts and text, one report a row",
        "rows": [asdict(row) for row in TRANSITS],
    }


def write_seed() -> Path:
    found = problems()
    if found:
        raise ValueError("; ".join(found))
    path = seed_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def record() -> dict:
    """Check the committed seed against the rows here and write its manifest entry."""
    from .config import SOURCES

    registered = SOURCES["acp_lng_transits_fiscal_year"]
    status, note = "ok", ""
    found = problems()
    try:
        committed = json.loads(seed_path().read_text(encoding="utf-8"))
        if committed != document():
            found.append("the committed seed differs from the rows in lngarb.panama_transits")
    except (OSError, ValueError) as exc:
        found.append("the seed could not be read: %s" % exc)
    if found:
        status, note = "failed", "; ".join(found)
    else:
        note = (
            "%d fiscal years, %d to %d, each read by eye in the Authority's annual report for the year, "
            "whose charts are drawn and not typed, and checked against the later reports that repeat it; "
            "the fiscal year ends on 30 September. The count is every LNG carrier in both directions. "
            "Source: Panama Canal Authority; non-commercial use with attribution."
            % (len(TRANSITS), TRANSITS[0].fiscal_year, TRANSITS[-1].fiscal_year)
        )
    entry = {
        "series": "acp_lng_transits_fiscal_year",
        "source": registered.publisher,
        "url": None,
        "page_url": registered.page_url,
        "linkable": registered.linkable,
        "machine_fetched": False,
        "fetched_at": None,
        "checked_at": base.utc_now_iso(),
        "rows": len(TRANSITS),
        "observations": len(TRANSITS),
        "file_rows": len(TRANSITS),
        "first_date": "%d-10-01" % (TRANSITS[0].fiscal_year - 1),
        "last_date": "%d-09-30" % TRANSITS[-1].fiscal_year,
        "frequency": registered.frequency,
        "gaps": [],
        "provisional_from": None,
        "vintage": "annual reports %d to %d" % (TRANSITS[0].fiscal_year, TRANSITS[-1].fiscal_year),
        "method": registered.method,
        "committable": registered.committable,
        "licence_note": registered.licence_note,
        "licence": registered.licence,
        "status": status,
        "note": note,
        "file": "data/seed/acp_lng_transits_fiscal_year.json",
        "unit": "ships a fiscal year",
        "observation_column": None,
        "unique_dates": True,
    }
    base.manifest_upsert(entry)
    return entry

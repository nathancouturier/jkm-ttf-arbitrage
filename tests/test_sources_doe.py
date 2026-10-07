"""DOE's cargo by cargo file of US LNG exports, parsed with no network.

The workbooks here are built inside the tests, with DOE's header and a few
rows of its layout; their numbers test the parser and are not data. The
anchors are tested against the workbook kept in data/private/ when it exists
on the machine running the tests, and skipped otherwise.
"""

from __future__ import annotations

import io
from datetime import datetime

import openpyxl
import pandas as pd
import pytest

from lngarb.sources import base, doe


def workbook(rows, header=doe.HEADER, sheet=doe.SHEET):
    book = openpyxl.Workbook()
    book.active.title = "Cover Page"
    ws = book.create_sheet(sheet)
    ws.append(list(header))
    for row in rows:
        ws.append(list(row))
    out = io.BytesIO()
    book.save(out)
    return out.getvalue()


ROW = (datetime(2026, 6, 3), "A Company", "2020-1-LNG", "Long-Term", "Exports", "LNG",
       "A Supplier", "Vessel", "A Ship", "Sabine Pass, LA", "Japan", 3500.5, "Yes")


def test_rows_are_read_with_their_region_and_an_undated_row_is_counted():
    undated = (None,) + ROW[1:]
    korea = (datetime(2026, 6, 1),) + ROW[1:10] + ("South Korea", 3400.0, "Yes")
    frame, left_out = doe.parse_cargo_workbook(workbook([ROW, undated, korea]))
    assert left_out == 1
    assert frame["date"].tolist() == [pd.Timestamp("2026-06-01"), pd.Timestamp("2026-06-03")]
    assert frame["region"].tolist() == ["jkm_markets", "jkm_markets"]
    assert frame["volume_mmcf"].tolist() == [3400.0, 3500.5]


def test_a_destination_with_no_region_stops_the_parse():
    nowhere = ROW[:10] + ("Atlantis", 3500.0, "Yes")
    with pytest.raises(base.SourceError) as caught:
        doe.parse_cargo_workbook(workbook([nowhere]))
    assert "Atlantis" in str(caught.value)


def test_a_changed_header_or_a_missing_sheet_stops_the_parse():
    with pytest.raises(base.SourceError):
        doe.parse_cargo_workbook(workbook([ROW], header=doe.HEADER[:-2] + ("Volume (Bcf)", "U.S. Contiguous")))
    with pytest.raises(base.SourceError):
        doe.parse_cargo_workbook(workbook([ROW], sheet="Another sheet"))


def test_a_volume_that_is_not_a_number_stops_the_parse():
    with pytest.raises(base.SourceError):
        doe.parse_cargo_workbook(workbook([ROW[:11] + ("n/a", "Yes")]))


def test_the_report_page_and_the_workbook_are_found_by_their_links():
    listing = (
        '<a href="/hgeo/articles/natural-gas-imports-and-exports-monthly-2025">2025</a>'
        '<a href="/hgeo/articles/natural-gas-imports-and-exports-monthly-2026">2026</a>'
    )
    assert doe.discover_report_page(listing) == (
        "https://www.energy.gov/hgeo/articles/natural-gas-imports-and-exports-monthly-2026"
    )
    page = (
        '<a href="/sites/default/files/2026-09/1.xlsx">1. U.S. Natural Gas Imports Exports and Re-Exports Summary</a>'
        '<a href="/sites/default/files/2026-09/3.xlsx">3. U.S. LNG Exports and Re-Exports Details (Jan 2016 - Jul 2026).xlsx</a>'
    )
    url, period = doe.discover_workbook_url(page, base_url="https://www.energy.gov/hgeo/articles/x")
    assert url == "https://www.energy.gov/sites/default/files/2026-09/3.xlsx"
    assert period == "Jul 2026"
    with pytest.raises(base.SourceError):
        doe.discover_workbook_url(page.replace("Details", "Summary"), base_url="https://www.energy.gov/")


SAVED = sorted((base.PRIVATE / "doe").glob("US_LNG_Exports_ReExports_Details_to_*.xlsx"))


@pytest.mark.skipif(not SAVED, reason="the DOE workbook is kept in data/private/ and is not on this machine")
def test_the_june_2026_china_cargoes_and_eia_s_country_totals():
    frame, _ = doe.parse_cargo_workbook(SAVED[-1].read_bytes())
    china = frame[(frame["country"] == "China") & (frame["date"].dt.strftime("%Y-%m") == "2026-06")]
    assert sorted(china["tanker"]) == ["Al Fat'h", "Clean Mistral"]
    assert round(china["volume_mmcf"].sum(), 2) == 4575.58
    exports = frame[frame["activity"] == "Exports"]
    japan = exports[(exports["country"] == "Japan") & (exports["date"].dt.strftime("%Y-%m") == "2026-06")]
    assert round(japan["volume_mmcf"].sum()) == 28827

"""World Bank Pink Sheet gas prices, parsed from committed workbooks.

Fixtures: the monthly workbook released on 2 September 2026, the release of 2
July 2026 as the Internet Archive captured it on 10 July 2026, and the commodity
markets page as served on 30 September 2026. The World Bank publishes the
dataset under CC BY 4.0.
"""

from __future__ import annotations

import math

import pandas as pd
import pytest

from lngarb.sources import base, worldbank

FIXTURES = base.REPO_ROOT / "tests" / "fixtures"
SEPTEMBER = (FIXTURES / "worldbank_monthly_release_2026-09-02.xlsx").read_bytes()
JULY = (FIXTURES / "worldbank_monthly_release_2026-07-02_wayback.xlsx").read_bytes()
LANDING = (FIXTURES / "worldbank_commodity_markets_2026-09-30.html").read_bytes()


def at(frame, month, column):
    return frame.loc[frame["date"] == pd.Timestamp(month), column].item()


def test_the_workbook_link_is_read_from_the_page():
    url = worldbank.discover_workbook_url(LANDING)
    assert url == (
        "https://thedocs.worldbank.org/en/doc/74e8be41ceb20fa0da750cda2f6b9e4e-0050012026/"
        "related/CMO-Historical-Data-Monthly.xlsx"
    )


def test_a_page_without_the_link_is_refused():
    with pytest.raises(base.SourceError):
        worldbank.discover_workbook_url(b"<html><a href='/other.xlsx'>x</a></html>")


def test_the_september_release_values_and_range():
    frame, vintage = worldbank.parse_workbook(SEPTEMBER)
    assert vintage == "Updated on September 02, 2026"
    assert worldbank.release_date(vintage) == "2026-09-02"
    assert frame["date"].iloc[0] == pd.Timestamp("2015-01-01")
    assert frame["date"].iloc[-1] == pd.Timestamp("2026-08-01")
    assert len(frame) == 140
    expected = {
        "2016-01-01": (4.4, 2.27, 8.4),
        "2020-05-01": (1.58, 1.75, 10.08),
        "2022-08-01": (70.04, 8.79, 21.21),
        "2026-06-01": (15.17, 3.15, 11.79),
        "2026-08-01": (21.11, 2.77, 13.94),
    }
    for month, (europe, us, japan) in expected.items():
        assert at(frame, month, "europe_gas_usd_mmbtu") == europe
        assert at(frame, month, "henry_hub_usd_mmbtu") == us
        assert at(frame, month, "japan_lng_import_usd_mmbtu") == japan


def test_the_ttf_definition_break_falls_inside_the_kept_window():
    frame, _ = worldbank.parse_workbook(SEPTEMBER)
    assert at(frame, "2015-03-01", "europe_gas_usd_mmbtu") == 8.27
    assert at(frame, "2015-04-01", "europe_gas_usd_mmbtu") == 6.77


def test_the_japan_revision_between_july_and_september_is_found():
    july, july_vintage = worldbank.parse_workbook(JULY)
    september, september_vintage = worldbank.parse_workbook(SEPTEMBER)
    july.insert(1, "release", worldbank.release_date(july_vintage))
    september.insert(1, "release", worldbank.release_date(september_vintage))
    revisions = worldbank.compare_releases(july, september)
    assert revisions[["series", "value_before", "value_after"]].values.tolist() == [
        ["japan_lng_import_usd_mmbtu", 12.83, 11.79]
    ]
    assert revisions["date"].tolist() == [pd.Timestamp("2026-06-01")]
    assert revisions["release_before"].item() == "2026-07-02"


def test_the_adapter_marks_japan_provisional_and_logs_the_revision(sandbox, tmp_path):
    july_file = tmp_path / "july.xlsx"
    july_file.write_bytes(JULY)
    september_file = tmp_path / "september.xlsx"
    september_file.write_bytes(SEPTEMBER)

    first = worldbank.WorldBankGasMonthly(from_file=july_file, fetched_at="2026-09-30T12:41:25Z").run()
    assert first["provisional_from"] == "2026-05-01"
    second = worldbank.WorldBankGasMonthly(from_file=september_file, fetched_at="2026-09-30T12:35:30Z").run()
    assert second["status"] == "ok"
    assert second["provisional_from"] == "2026-07-01"
    assert second["vintage"] == "Updated on September 02, 2026"
    revisions = base.read_cache("worldbank_gas_revisions")
    assert len(revisions) == 1


def test_an_unknown_token_in_a_price_cell_is_refused_not_coerced():
    with pytest.raises(base.SourceError):
        worldbank._number("n.a.", where="test")
    assert math.isnan(worldbank._number(chr(0x2026), where="test"))

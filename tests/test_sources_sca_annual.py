"""The Suez Canal Authority's annual reports, with no network and no report.

The reports are the Authority's, all rights reserved, so none is committed:
the parser is tested on text built here with the rows the reports' text
layers give, in each of the three spellings of the LNG row.
"""

from __future__ import annotations

import pandas as pd
import pytest

from lngarb.sources import sca_annual
from lngarb.sources.base import SourceError


def _report(year, title, row):
    return "\n".join([
        "Suez Canal Statistics for %d Compared to %d" % (year, year - 1),
        "Table ( 3 )", title, "NO ( Vessel ) Net Ton ( 1000 )", "Ship Type",
        "%d %d %% %d %d %%" % (year - 1, year, year - 1, year),
        "Tankers 4,954 4,991 0.7 243,315 246,851 1.5", row,
        "Bulk Carr. 4,106 3,423 -16.6 161,250 131,914 -18.2",
        "Total 13,213 12,758 -3.4 524,527 522,084 -0.5",
    ])


def test_the_three_spellings_of_the_row_read_the_same_way():
    for year, title, row in (
        (2008, "NO & Net Ton by Ship Type (2007, 2008)", "LNG 358 429 19.8 32776 38987 18.9"),
        (2016, "NO & Net Ton by Ship Type ( 2015 ، 2016 )", "L N G 670 575 -14.2 72,996 61,242 -16.1"),
        (2025, "NO & Net Ton by Ship Type ( 2024 , 2025 )", "LNG Ships 119 282 137.0 13,176 30,627 132.4"),
    ):
        rows = sca_annual.parse_report_text(_report(year, title, row), year=year)
        assert [r["date"].year for r in rows] == [year - 1, year]
        assert all(r["report"] == year for r in rows)
    assert rows[1] == {"date": pd.Timestamp("2025-01-01"), "lng_ships": 282, "net_ton_thousand": 30627, "report": 2025}


def test_a_report_for_the_wrong_years_or_without_the_row_is_refused():
    with pytest.raises(SourceError, match="table is for 2023 and 2024"):
        sca_annual.parse_report_text(_report(2025, "NO & Net Ton by Ship Type ( 2023 , 2024 )", "LNG Ships 1 2 3 4 5 6"), year=2025)
    with pytest.raises(SourceError, match="LNG row 0 times"):
        sca_annual.parse_report_text(_report(2025, "NO & Net Ton by Ship Type ( 2024 , 2025 )", "Container Ships 1 2 3 4 5 6"), year=2025)


def test_combine_keeps_the_later_print_and_names_the_rounding():
    rows = sca_annual.parse_report_text(_report(2024, "NO & Net Ton by Ship Type ( 2023 , 2024 )", "LNG Ships 819 119 -85.5 91,849 13,176 -85.7"), year=2024)
    rows += sca_annual.parse_report_text(_report(2023, "NO & Net Ton by Ship Type ( 2022 , 2023 )", "LNG Ships 901 819 -9.1 100,614 91,850 -8.7"), year=2023)
    frame, restated = sca_annual.combine(rows)
    assert frame["date"].dt.year.tolist() == [2022, 2023, 2024]
    assert frame.loc[frame["date"].dt.year == 2023, "net_ton_thousand"].item() == 91849
    assert restated == ["2023, 91,850 then 91,849 thousand tons"]


def test_a_count_that_changes_between_prints_is_refused():
    rows = sca_annual.parse_report_text(_report(2024, "NO & Net Ton by Ship Type ( 2023 , 2024 )", "LNG Ships 820 119 -85.5 91,849 13,176 -85.7"), year=2024)
    rows += sca_annual.parse_report_text(_report(2023, "NO & Net Ton by Ship Type ( 2022 , 2023 )", "LNG Ships 901 819 -9.1 100,614 91,850 -8.7"), year=2023)
    with pytest.raises(SourceError, match="819 LNG ships in the 2023 report, 820 in the 2024 report"):
        sca_annual.combine(rows)


def test_the_committed_series_runs_from_2007_and_holds_the_collapse_of_2024():
    from lngarb.sources.base import read_cache
    frame = read_cache("sca_lng_transits_annual")
    assert frame is not None and frame["date"].iloc[0] == pd.Timestamp("2007-01-01")
    by_year = frame.set_index(frame["date"].dt.year)["lng_ships"]
    assert by_year[2023] == 819 and by_year[2024] == 119 and by_year[2025] == 282

"""METI's spot LNG prices, parsed from the historical workbook as METI served it.

METI's terms are compatible with CC BY 4.0, which permits committing the file.
The anchors: contract-based 12.7 in February 2021 and 6.6 in March 2021,
arrival-based 16.3 and 9.3, the contract-based record 18.5 in January 2021 and
low 2.2 in May 2020.
"""

from __future__ import annotations

import math

import pandas as pd
import pytest

from lngarb.sources import base, meti

WORKBOOK = (base.REPO_ROOT / "tests" / "fixtures" / "meti_historical_data_e.xlsx").read_bytes()


@pytest.fixture(scope="module")
def frame():
    return meti.parse_workbook(WORKBOOK).set_index("date")


def test_the_anchors_reproduce_exactly(frame):
    assert frame.at[pd.Timestamp("2021-02-01"), "contract_based_usd_mmbtu"] == 12.7
    assert frame.at[pd.Timestamp("2021-03-01"), "contract_based_usd_mmbtu"] == 6.6
    assert frame.at[pd.Timestamp("2021-02-01"), "arrival_based_usd_mmbtu"] == 16.3
    assert frame.at[pd.Timestamp("2021-03-01"), "arrival_based_usd_mmbtu"] == 9.3
    assert frame["contract_based_usd_mmbtu"].max() == 18.5
    assert frame["contract_based_usd_mmbtu"].idxmax() == pd.Timestamp("2021-01-01")
    assert frame["contract_based_usd_mmbtu"].min() == 2.2
    assert frame["contract_based_usd_mmbtu"].idxmin() == pd.Timestamp("2020-05-01")


def test_the_range_and_the_one_fixed_month(frame):
    assert frame.index[0] == pd.Timestamp("2014-03-01")
    assert frame.index[-1] == pd.Timestamp("2021-03-01")
    assert len(frame) == 85
    assert frame.index[frame["figure"] == "Fixed"].tolist() == [pd.Timestamp("2019-02-01")]


def test_unpublished_months_are_gaps_never_zeros(frame):
    contract_gaps = frame.index[frame["contract_based_usd_mmbtu"].isna()].strftime("%Y-%m").tolist()
    arrival_gaps = frame.index[frame["arrival_based_usd_mmbtu"].isna()].strftime("%Y-%m").tolist()
    assert contract_gaps == ["2015-05", "2016-03", "2016-06", "2016-08", "2017-06", "2019-11"]
    assert arrival_gaps == [
        "2014-03", "2015-05", "2015-07", "2016-01", "2016-05", "2016-09", "2018-11", "2020-03",
    ]
    assert not (frame[["contract_based_usd_mmbtu", "arrival_based_usd_mmbtu"]] == 0).any().any()


def test_a_cell_that_is_neither_a_price_nor_the_gap_marker_is_refused():
    with pytest.raises(base.SourceError):
        meti._number("x", where="test")
    assert math.isnan(meti._number(chr(0x00D7), where="test"))


def test_the_adapter_records_the_workbook_fetch_time_not_the_run_time(sandbox, tmp_path):
    workbook = tmp_path / "historical-data-e.xlsx"
    workbook.write_bytes(WORKBOOK)
    entry = meti.MetiSpotLngMonthly(from_file=workbook).run()
    assert entry["status"] == "ok"
    assert entry["fetched_at"] == "2026-09-30T16:56:44Z"
    assert entry["observations"] == 79
    assert "Created by processing the information" in entry["note"]


def test_the_adapter_never_fetches_meti(sandbox, monkeypatch):
    monkeypatch.setattr(base, "http_get", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no fetch")))
    with pytest.raises(base.SourceError) as caught:
        meti.MetiSpotLngMonthly(from_file=sandbox / "absent.xlsx").run()
    assert "not fetched by this pipeline" in str(caught.value)

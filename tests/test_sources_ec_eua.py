"""The EU allowance price from the European Commission's auction reports.

Fixture: the report for April to June 2025, published under CC BY 4.0. Its
fifteen monthly averages were reproduced to the cent from EEX's own auction
results during reconnaissance; four of them are anchors here.
"""

from __future__ import annotations

import math

import pandas as pd

from lngarb.sources import base, ec_eua

REPORT = (base.REPO_ROOT / "tests" / "fixtures" / "ec_cap_report_202506.pdf").read_bytes()


def test_table_1_gives_fifteen_months_and_the_anchors():
    frame = ec_eua.parse_report(REPORT, report="202506").set_index("date")["eua_eur_t"]
    assert len(frame) == 15
    assert frame[pd.Timestamp("2025-06-01")] == 72.06
    assert frame[pd.Timestamp("2025-05-01")] == 70.23
    assert frame[pd.Timestamp("2025-04-01")] == 64.17
    assert frame[pd.Timestamp("2024-04-01")] == 63.59


def test_the_annual_rows_are_not_read_as_months():
    frame = ec_eua.parse_report(REPORT, report="202506")
    assert frame["date"].min() == pd.Timestamp("2024-04-01")
    assert (frame["date"].dt.year >= 2024).all()


def test_the_latest_report_wins_and_a_disagreement_is_recorded():
    older = pd.DataFrame({"date": [pd.Timestamp("2024-04-01")], "eua_eur_t": [63.00], "report": ["202503"]})
    newer = pd.DataFrame({"date": [pd.Timestamp("2024-04-01")], "eua_eur_t": [63.59], "report": ["202506"]})
    combined = ec_eua.combine([older, newer])
    assert combined["eua_eur_t"].item() == 63.59
    assert combined["report"].item() == "202506"
    assert "202503 gives 63.00" in combined["anomaly"].item()


def test_a_month_without_auction_is_missing_not_zero():
    blank = pd.DataFrame({"date": [pd.Timestamp("2021-01-01")], "eua_eur_t": [math.nan], "report": ["202112"]})
    combined = ec_eua.combine([blank])
    assert math.isnan(combined["eua_eur_t"].item())


def test_the_adapter_reads_given_reports_without_the_network(sandbox):
    entry = ec_eua.EcEuaAuctionMonthly(reports={"202506": REPORT}).run()
    assert entry["status"] == "ok"
    assert entry["first_date"] == "2024-04-01" and entry["last_date"] == "2025-06-01"

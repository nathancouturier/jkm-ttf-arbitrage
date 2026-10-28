"""The EU allowance price from the European Commission's auction reports.

Fixtures: the report for April to June 2025, published under CC BY 4.0, whose
fifteen monthly averages were reproduced to the cent from EEX's own auction
results when the source was assessed, four of them anchors here; and the report
for January to March 2015, the first with a monthly Table 1, which spells its
months three ways and reaches back to January 2014; and the report for
December 2013, the first with a monthly table at all, an overview from
November 2012 whose months the later reports of 2014 repeat.
"""

from __future__ import annotations

import math

import pandas as pd

from lngarb.sources import base, ec_eua

REPORT = (base.REPO_ROOT / "tests" / "fixtures" / "ec_cap_report_202506.pdf").read_bytes()
FIRST = (base.REPO_ROOT / "tests" / "fixtures" / "ec_cap_report_201503.pdf").read_bytes()
OVERVIEW = (base.REPO_ROOT / "tests" / "fixtures" / "ec_cap_report_201312.pdf").read_bytes()


def test_the_december_2013_overview_reaches_back_to_november_2012_and_marks_the_simple_averages():
    frame = ec_eua.parse_report(OVERVIEW, report="201312").set_index("date")
    assert len(frame) == 14
    assert frame.index.min() == pd.Timestamp("2012-11-01") and frame.index.max() == pd.Timestamp("2013-12-01")
    assert frame.loc[pd.Timestamp("2012-11-01"), "eua_eur_t"] == 7.01
    assert frame.loc[pd.Timestamp("2013-01-01"), "eua_eur_t"] == 5.05
    assert frame.loc[pd.Timestamp("2013-12-01"), "eua_eur_t"] == 4.61
    # May to August 2013 are simple averages, which the report marks with one asterisk.
    simple = frame[frame["anomaly"].notna()].index
    assert list(simple) == [pd.Timestamp("2013-%02d-01" % m) for m in (5, 6, 7, 8)]
    assert frame.loc[pd.Timestamp("2013-05-01"), "eua_eur_t"] == 3.40
    assert frame.loc[pd.Timestamp("2013-11-01"), "anomaly"] is None


def test_an_overview_listed_downwards_gets_its_years_from_the_direction():
    text = "\n".join([
        "Table 2: Overview",
        "Month Auction Bid volume Cover Bidders Successful Price Revenue",
        "April 2014 23 130 000 177 597 500 7.68 17.67* 10.83* \u20ac 5.19* \u20ac 119 948 325",
        "March 42 048 500 280 163 000 6.66** 17.35** 11.75** \u20ac 6.42** \u20ac 269 929 405",
        "February 52 667 000 216 991 500 4.12** 19.68** 14.30** \u20ac 6.38** \u20ac 336 162 075",
        "January 2014 48 648 500 178 198 500 3.66 21.92** 13.17** \u20ac 4.96** \u20ac 241 181 405",
        "December 39 078 000 130 983 000 3.35** 21.48** 16.09** \u20ac 4.61** \u20ac 180 068 050",
        "November 56 161 000 225 489 500 4.01** 19.91** 15.01** \u20ac 4.50** \u20ac 252 482 700",
        "* average",
    ])
    frame = ec_eua._parse_overview(text, report="201404").sort_values("date")
    assert [d.strftime("%Y-%m") for d in frame["date"]] == ["2013-11", "2013-12", "2014-01", "2014-02", "2014-03", "2014-04"]
    assert frame.set_index("date").loc[pd.Timestamp("2013-11-01"), "eua_eur_t"] == 4.50


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


def test_the_first_report_with_a_monthly_table_reads_every_spelling_of_a_month():
    frame = ec_eua.parse_report(FIRST, report="201503").set_index("date")["eua_eur_t"]
    assert len(frame) == 15
    assert frame.index.min() == pd.Timestamp("2014-01-01")
    assert frame.index.max() == pd.Timestamp("2015-03-01")
    assert frame[pd.Timestamp("2015-03-01")] == 6.76   # "March 2015"
    assert frame[pd.Timestamp("2014-12-01")] == 6.76   # "Dec. 2014"
    assert frame[pd.Timestamp("2014-09-01")] == 6.01   # "Sept. 2014"
    assert frame[pd.Timestamp("2014-01-01")] == 4.96   # "Jan. 2014"
    # the "2014 total" and "2013 total" rows under the table are not months
    assert (frame.index.year >= 2014).all()


def test_the_committed_rows_carry_forward_and_only_newer_reports_are_fetched(sandbox):
    first = ec_eua.EcEuaAuctionMonthly(reports={"201503": FIRST}).run()
    assert (first["first_date"], first["last_date"]) == ("2014-01-01", "2015-03-01")
    again = ec_eua.EcEuaAuctionMonthly(reports={"202506": REPORT}).run()
    assert (again["first_date"], again["last_date"]) == ("2014-01-01", "2025-06-01")
    held = base.read_cache("ec_eua_auction_monthly")
    assert len(held) == 30
    assert held.loc[held["date"] == "2014-01-01", "report"].item() == "cap_report_201503"
    assert held.loc[held["date"] == "2025-06-01", "report"].item() == "cap_report_202506"
    assert "1 report(s) read this run" in again["note"]


def test_the_latest_report_wins_and_a_disagreement_is_recorded():
    older = pd.DataFrame({"date": [pd.Timestamp("2024-04-01")], "eua_eur_t": [63.00], "report": ["cap_report_202503"]})
    newer = pd.DataFrame({"date": [pd.Timestamp("2024-04-01")], "eua_eur_t": [63.59], "report": ["cap_report_202506"]})
    combined = ec_eua.combine([older, newer])
    assert combined["eua_eur_t"].item() == 63.59
    assert combined["report"].item() == "cap_report_202506"
    assert combined["anomaly"].item() == "reports disagree: 63 in cap_report_202503; 63.59 in cap_report_202506"


def test_a_month_without_auction_is_missing_not_zero():
    blank = pd.DataFrame({"date": [pd.Timestamp("2021-01-01")], "eua_eur_t": [math.nan], "report": ["cap_report_202112"]})
    combined = ec_eua.combine([blank])
    assert math.isnan(combined["eua_eur_t"].item())


def test_the_adapter_reads_given_reports_without_the_network(sandbox):
    entry = ec_eua.EcEuaAuctionMonthly(reports={"202506": REPORT}).run()
    assert entry["status"] == "ok"
    assert entry["first_date"] == "2024-04-01" and entry["last_date"] == "2025-06-01"
    assert "0 report(s) read" not in entry["note"]

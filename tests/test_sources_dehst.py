"""DEHSt's monthly averages of the German allowance auctions, with no network.

The fixture is DEHSt's reports page as served on 7 October 2026. The reports
themselves are not committed: their other tables and figures carry third
party data and a licensed cover photo. The year tables are tested on text
built here with the rows the reports' text layers give; the PDF reading itself
is tested when the private copy of the 2024 report is present.
"""

from __future__ import annotations

import pandas as pd
import pytest

from lngarb.sources import base, dehst
from lngarb.sources.base import SourceError

FIXTURES = base.REPO_ROOT / "tests" / "fixtures"
PAGE = (FIXTURES / "dehst_reports_page_2026-10-07.html").read_bytes()
PRIVATE_2024 = base.REPO_ROOT / "data" / "private" / "recon" / "raw" / "dehst" / "2024_report_Q4_20261008.pdf"
EURO = chr(0x20AC)

# The year table of the fourth quarter 2024 report, as its text layer reads:
# a type column, aviation allowances in October, and October's name on a line
# of its own between its two rows.
TABLE_2024 = "\n".join([
    "Table 2: Overview of the entire year 2024",
    "Auction Cover Successful",
    "Month Type Bid volume Bidders Price Revenue",
    "volume ratio bidders",
    "January EUA 3,592,000 7,586,000 *2.11 *26 *9 *{e} 61.94 {e} 222,488,480",
    "February EUA 7,184,000 12,874,000 *1.79 *23 *21 *{e} 55.70 {e} 400,112,880",
    "March EUA 7,184,000 14,021,000 *1.95 *24 *17 *{e} 56.60 {e} 406,578,480",
    "April EUA 7,184,000 14,477,000 *2.02 *27 *17 *{e} 64.65 {e} 464,463,560",
    "May EUA 7,184,000 14,492,000 *2.02 *24 *14 *{e} 71.98 {e} 517,122,280",
    "June EUA 7,184,000 13,068,000 *1.82 *23 *18 *{e} 67.67 {e} 486,141,280",
    "July EUA 7,184,000 13,844,000 *1.93 *24 *18 *{e} 66.70 {e} 479,172,800",
    "August EUA 8,994,000 18,068,500 **2.01 *22 *16 **{e} 70.40 {e} 633,208,900",
    "September EUA 7,546,000 14,641,000 *1.94 *24 *16 *{e} 65.13 {e} 491,470,980",
    "EUA 7,546,000 14,893,000 *1.97 *22 *17 *{e} 63.24 {e} 477,209,040",
    "October",
    "EUAA 1,061,000 3,212,000 3.03 15 6 {e} 64.14 {e} 68,052,540",
    "November EUA 9,432,500 18,342,000 *1.94 *22 *19 *{e} 66.89 {e} 630,939,925",
    "December EUA 3,777,000 7,194,500 **1.91 24 20 **{e} 66.66 {e} 251,772,460",
    "EUA 83,991,500 163,501,000 **1.95 *24 *17 **{e} 65.01 {e} 5,460,681,065",
    "EUAA 1,061,000 3,212,000 3.03 15 6 {e} 64.14 {e} 68,052,540",
    "Total 85,052,500 166,713,000 **1.96 *23 *17 **{e} 65.00 {e} 5,528,733,605",
    "Source: EEX, DEHSt",
]).format(e=EURO)

# The year table of the August 2026 report, as its text layer reads.
TABLE_2026 = "\n".join([
    "Table 2: Overview of the entire year 2026",
    "Auction Bid Cover Successful",
    "Month Bidders Price Revenue",
    "volume volume ratio bidders",
    "January 4,372,000 11,692,000 *2.68 *25 *10 *{e}86.88 {e}379,850,290",
    "February 4,372,000 11,429,000 *2.62 *26 *13 *{e}72.47 {e}316,816,980",
    "March 4,372,000 9,620,500 *2.20 *22 *11 *{e}68.49 {e}299,449,210",
    "April 3,279,000 6,353,000 *1.94 *20 *14 *{e}73.98 {e}242,569,490",
    "May 3,279,000 6,464,000 *1.97 *18 *13 *{e}75.98 {e}249,127,490",
    "June 4,000,000 8,387,000 *2.10 *17 *11 *{e}77.99 {e}311,960,000",
    "July 5,000,000 9,897,000 *1.98 *18 *13 *{e}79.66 {e}398,320,000",
    "August 3,717,500 8,295,000 **2.23 *18 *11 **{e}82.31 {e}305,992,000",
    "Total 32,391,500 72,137,500 **2.23 *21 *12 **{e}77.31 {e}2,504,085,460",
    "Source: EEX, DEHSt",
]).format(e=EURO)


def test_the_latest_report_of_each_year_is_chosen():
    links = dehst.report_links(PAGE)
    chosen = dehst.latest_per_year(links)
    assert {year: report for year, (report, _url) in chosen.items()} == {2024: "Q4", 2025: "Q4", 2026: "08"}
    assert chosen[2026][1].startswith("https://www.dehst.de/SharedDocs/downloads/EN/auctioning/2026/2026_report_08.pdf")
    # A quarter counts to its third month: the report for August beats the second quarter.
    assert dehst.latest_per_year({(2026, "Q2"): "a", (2026, "08"): "b", (2026, "07"): "c"}) == {2026: ("08", "b")}


def test_the_2024_table_reads_general_allowances_only():
    frame = dehst.parse_year_table(TABLE_2024, year=2024, report="Q4").set_index("date")
    assert len(frame) == 12
    assert frame.loc[pd.Timestamp("2024-01-01"), "eua_eur_t"] == 61.94
    # October prints its name on a line of its own, between its EUA and EUAA rows;
    # the aviation allowances, at 64.14, are left out.
    assert frame.loc[pd.Timestamp("2024-10-01"), "eua_eur_t"] == 63.24
    assert frame.loc[pd.Timestamp("2024-10-01"), "auction_volume"] == 7_546_000
    assert frame.loc[pd.Timestamp("2024-12-01"), "average"] == "volume weighted"
    assert frame.loc[pd.Timestamp("2024-11-01"), "average"] == "simple"
    assert frame["anomaly"].isna().all()


@pytest.mark.skipif(not PRIVATE_2024.exists(), reason="the private copy of the 2024 report is not here")
def test_the_2024_report_reads_from_its_pdf_as_from_its_text():
    from_pdf = dehst.parse_report(PRIVATE_2024.read_bytes(), year=2024, report="Q4")
    from_text = dehst.parse_year_table(TABLE_2024, year=2024, report="Q4")
    pd.testing.assert_frame_equal(from_pdf, from_text)


def test_months_that_do_not_add_up_to_the_total_are_refused():
    # December's name printed after both of its rows would hand it the year's EUA total.
    shifted = TABLE_2024.replace(
        "December EUA 3,777,000 7,194,500 **1.91 24 20 **{e} 66.66 {e} 251,772,460".format(e=EURO),
        "EUA 3,777,000 7,194,500 **1.91 24 20 **{e} 66.66 {e} 251,772,460\n"
        "EUAA 1,000 2,000 2.00 2 2 {e} 66.00 {e} 66,000\nDecember".format(e=EURO))
    with pytest.raises(SourceError) as caught:
        dehst.parse_year_table(shifted, year=2024, report="Q4")
    assert "add up to" in str(caught.value)
    with pytest.raises(SourceError):
        dehst.parse_year_table(TABLE_2026.replace("Total 32,391,500", "Total 32,391,501"), year=2026, report="08")


def test_the_later_layout_and_the_total_row():
    frame = dehst.parse_year_table(TABLE_2026, year=2026, report="08")
    assert frame["date"].dt.month.tolist() == list(range(1, 9))
    assert frame["eua_eur_t"].tolist() == [86.88, 72.47, 68.49, 73.98, 75.98, 77.99, 79.66, 82.31]
    assert frame.iloc[-1]["average"] == "volume weighted"


def test_a_table_for_another_year_or_without_its_source_line_is_refused():
    with pytest.raises(SourceError):
        dehst.parse_year_table(TABLE_2026, year=2025, report="Q4")
    with pytest.raises(SourceError):
        dehst.parse_year_table(TABLE_2026.replace("Source: EEX, DEHSt", ""), year=2026, report="08")


def test_a_table_shorter_than_its_report_is_refused():
    with pytest.raises(SourceError) as caught:
        dehst.parse_year_table(TABLE_2026, year=2026, report="Q3")
    assert "stops at 8" in str(caught.value)
    missing = "\n".join(line for line in TABLE_2026.splitlines() if not line.startswith("March"))
    with pytest.raises(SourceError):
        dehst.parse_year_table(missing, year=2026, report="08")


def test_a_price_that_does_not_give_the_revenue_is_noted():
    edited = TABLE_2026.replace("*{e}72.47".format(e=EURO), "*{e}74.27".format(e=EURO))
    frame = dehst.parse_year_table(edited, year=2026, report="08")
    assert "misses the revenue" in frame.iloc[1]["anomaly"]


# The year table of the fourth quarter 2025 report, as its text layer reads.
TABLE_2025 = "\n".join([
    "Table 2: Overview of the entire year 2025",
    "January 6,428,000 13,736,500 *2.14 *25 *18 *{e}76.87 {e}494,104,290",
    "February 6,428,000 14,872,000 *2.32 *25 *14 *{e}75.05 {e}482,437,470",
    "March 6,428,000 14,856,500 *2.31 *24 *14 *{e}68.84 {e}442,471,380",
    "April 4,821,000 10,464,000 *2.17 *24 *14 *{e}63.57 {e}306,454,900",
    "May 4,821,000 10,394,000 *2.15 *23 *13 *{e}71.42 {e}344,299,750",
    "June 6,428,000 11,936,500 *1.86 *20 *14 *{e}72.26 {e}464,471,210",
    "July 6,428,000 13,758,500 *2.14 *21 *14 *{e}70.01 {e}450,040,350",
    "August 8,042,500 14,539,500 **1.81 *20 *13 **{e}71.35 {e}573,848,070",
    "September 6,764,000 12,833,000 *1.90 *23 *16 *{e}75.55 {e}511,020,200",
    "October 6,764,000 13,266,500 *1.96 *22 *13 *{e}78.59 {e}531,548,940",
    "November 6,764,000 13,316,000 *1.97 *22 *15 *{e}80.92 {e}547,342,880",
    "December 3,387,000 6,986,500 **2.07 *25 *13 **{e}82.95 {e}280,955,150",
    "Source: EEX, DEHSt",
]).format(e=EURO)


def test_the_adapter_reads_one_report_per_year(sandbox):
    adapter = dehst.DehstEuaGermanAuctionMonthly(page=PAGE, reports={
        (2024, "Q4"): TABLE_2024, (2025, "Q4"): TABLE_2025, (2026, "08"): TABLE_2026,
    })
    entry = adapter.run()
    assert entry["status"] == "ok" and entry["observations"] == 32
    assert entry["vintage"] == "2024_report_Q4, 2025_report_Q4, 2026_report_08"
    assert "proxy for the EU price" in adapter.note and "non-commercial" in adapter.note
    frame = base.read_cache("dehst_eua_german_auction_monthly")
    assert frame["report"].value_counts().to_dict() == {"2024_report_Q4": 12, "2025_report_Q4": 12, "2026_report_08": 8}


def test_the_committed_series_and_its_overlap_with_the_commission():
    german = base.read_cache("dehst_eua_german_auction_monthly").set_index("date")["eua_eur_t"]
    assert german.index.min() == pd.Timestamp("2024-01-01")
    assert german[pd.Timestamp("2025-07-01")] == 70.01
    common = base.read_cache("ec_eua_auction_monthly").set_index("date")["eua_eur_t"].dropna()
    both = pd.concat([common.rename("eu"), german.rename("de")], axis=1).dropna()
    gap = (both["de"] - both["eu"]).round(2)
    assert len(both) == 18
    assert round(gap.mean(), 2) == 0.10 and round(gap.abs().mean(), 2) == 0.64 and gap.abs().max() == 1.40

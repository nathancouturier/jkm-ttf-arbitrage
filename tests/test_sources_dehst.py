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


# The year table of the fourth quarter 2019 report, as its text layer reads.
TABLE_2019 = "\n".join([
    "Table 2: Overview of the entire year 2019",
    "Auction Cover Successful",
    "Month Type Bid volume Bidders Price Revenue",
    "volume ratio bidders",
    "February EUA 12,836,000 26,410,500 *2.06 *27 *22 *{e} 20.75 {e} 266,347,000",
    "March EUA 16,045,000 28,360,000 *1.77 *23 *17 *{e} 21.89 {e} 351,160,870",
    "April EUA 9,627,000 14,028,500 *1.46 *19 *16 *{e} 25.89 {e} 249,275,120",
    "May EUA 12,836,000 21,749,500 *1.70 *25 *20 *{e} 25.32 {e} 325,039,610",
    "June EUA 12,836,000 22,891,500 *1.78 *21 *16 *{e} 25.05 {e} 321,477,620",
    "July EUA 12,836,000 27,407,000 *2.14 *24 *17 *{e} 27.69 {e} 355,396,750",
    "August EUA 8,022,500 19,342,500 *2.41 *23 *16 *{e} 27.14 {e} 217,762,740",
    "September EUA 11,338,000 21,900,000 *1.93 *22 *17 *{e} 25.79 {e} 292,378,675",
    "EUA 11,338,000 17,177,000 *1.51 *19 *16 *{e} 24.38 {e} 276,448,785",
    "October",
    "EUAA 801,500 2,377,000 *2.97 *9 *5 *{e} 22.32 {e} 17,889,480",
    "November EUA 14,172,500 25,107,500 *1.77 *19 *14 *{e} 24.62 {e} 348,898,605",
    "December EUA 5,674,500 9,652,000 ** 1.70 * 20 * 15 ** 25,02 {e} {e} 141,949,350",
    "Total 128,363,000 236,403,000 **1.84 *22 *17 **{e} 24.65 {e} 3,164,024,605",
    "Source: EEX, DEHSt",
]).format(e=EURO, r=chr(0xFFFD))

# The year table of the fourth quarter 2020 report, as its text layer reads.
TABLE_2020 = "\n".join([
    "Table 2: Overview of the entire year 2020",
    "Auction Successful",
    "Month Type Bid volume Cover ratio Bidders Price Revenue",
    "volume bidders",
    "January EUA 9,452,000 19,601,500 *2.07 *25 *19 *{e} 24.36 {e} 230,274,350",
    "February EUA 9,452,000 22,171,500 *2.35 *25 *15 *{e} 24.01 {e} 226,966,150",
    "March EUA 9,452,000 19,980,000 *2.12 *21 *15 *{e} 19.76 {e} 186,771,520",
    "April EUA 7,089,000 13,023,500 *1.84 *21 *14 *{e} 20.09 {e} 142,394,380",
    "May EUA 7,089,000 12,611,500 *1.78 *21 *12 *{e} 20.03 {e} 142,016,300",
    "June EUA 9,452,000 16,015,000 *1.69 *18 *13 *{e} 23.43 {e} 221,483,990",
    "July EUA 11,815,000 22,225,500 *1.88 *21 *13 *{e} 26.88 {e} 317,539,940",
    "August EUA 4,731,500 10,316,500 *2.18 *20 *15 *{e} 26.57 {e} 125,720,255",
    "September EUA 10,372,000 18,885,000 *1.82 *27 *20 *{e} 27.85 {e} 288,886,130",
    "EUA 12,965,000 23,554,000 *1.82 24 18 *{e} 25.19 {e} 326,562,420",
    "October",
    "EUAA 769,000 2,307,000 3.00 10 5 *{e} 26.76 {e} 20,578,440",
    "November EUA 10,372,000 21,889,000 *2.11 *27 *17 *{e} 26.64 {e} 276,258,220",
    "December EUA 5,191,500 8,759,500 **1.69 *25 *15 **{e} 30.23 {e} 156,914,325",
    "Total 108,202,000 211,339,500 **1{r}95 *22 *15 **{e} 24{r}61 {e} 2,662,366,420",
    "Source: EEX, DEHSt",
]).format(e=EURO, r=chr(0xFFFD))

# The year table of the fourth quarter 2021 report, as its text layer reads.
TABLE_2021 = "\n".join([
    "Table 2: Overview of the entire year 2021",
    "Auction Cover Successful",
    "Month Type Bid volume Bidders Price Revenue",
    "volume ratio bidders",
    "January EUA 2,651,000 4,208,000 1.59 27 19 {e} 33.51 {e} 88,835,010",
    "February EUA 10,604,000 19,908,500 *1.88 *26 *20 *{e} 37.82 {e} 401,043,280",
    "March EUA 10,604,000 17,754,500 *1.67 *24 *20 *{e} 40.59 {e} 430,442,870",
    "April EUA 10,604,000 16,994,000 *1.60 *24 *19 *{e} 45.44 {e} 481,872,270",
    "May EUA 7,953,000 13,982,000 *1.76 *25 *19 *{e} 51.08 {e} 406,265,750",
    "June EUA 10,604,000 17,539,500 *1.66 *26 *19 *{e} 52.47 {e} 556,365,370",
    "July EUA 13,255,000 19,514,000 *1.47 *23 *17 *{e} 53.48 {e} 708,930,420",
    "August EUA 5,305,000 11,509,500 **2.17 *20 *15 **{e} 56.06 {e} 297,389,395",
    "September EUA 7,220,000 12,426,500 *1.72 *22 *15 *{e} 60.99 {e} 440,311,700",
    "EUA 9,025,000 17,563,500 *1.95 *21 *14 *{e} 60.37 {e} 544,875,350",
    "October",
    "EUAA 600,000 1,785,000 2,98 8 4 {e} 58.75 {e} 35,250,000",
    "November EUA 7,220,000 12,178,000 *1.69 *20 *16 *{e} 66.44 {e} 479,660,700",
    "December EUA 5,417,500 8,310,000 **1.53 *22 *16 **{e} 80.28 {e} 434,921,825",
    "Total 101,062,500 173,673,000 **1{r}72 *23 *17 **{e} 52{r}50 {e} 5{r}306{r}163{r}940",
    "Source: EEX, DEHSt",
]).format(e=EURO, r=chr(0xFFFD))

# The year table of the fourth quarter 2022 report, as its text layer reads.
TABLE_2022 = "\n".join([
    "Table 2: Overview of the entire year 2022",
    "Auction Successful",
    "Month Type Bid volume Cover ratio Bidders Price Revenue",
    "volume bidders",
    "January EUA 5,832,000 7,951,500 *1.36 *21 *19 *{e} 84.93 {e} 495,331,200",
    "February EUA 7,776,000 12,599,000 *1.62 *21 *16 *{e} 89.80 {e} 698,245,920",
    "March EUA 7,776,000 20,001,500 *2.57 *21 *13 *{e} 75.36 {e} 585,979,920",
    "April EUA 7,776,000 20,026,000 *2.58 *21 *16 *{e} 82.12 {e} 638,545,680",
    "May EUA 5,832,000 15,149,000 *2.60 *20 *17 *{e} 86.89 {e} 506,742,480",
    "June EUA 5,832,000 13,969,500 *2.40 *19 *14 *{e} 82.21 {e} 479,448,720",
    "July EUA 9,720,000 20,459,500 *2.11 *19 *16 *{e} 82.12 {e} 798,167,520",
    "August EUA 3,898,000 10,337,000 **2.65 *16 *8 **{e} 89.56 {e} 349,095,160",
    "September EUA 9,307,500 16,174,500 *1.74 *16 *13 *{e} 69.81 {e} 649,756,575",
    "EUA 7,446,000 19,061,500 *2.56 *17 *14 *{e} 70.97 {e} 528,442,620",
    "October",
    "EUAA 586,500 1,178,000 2.01 6 4 {e} 68.62 {e} 40,245,630",
    "November EUA 7,446,000 17,010,000 *2.29 *19 *14 *{e} 75.76 {e} 564,127,575",
    "December EUA 5,588,500 12,830,500 **2.30 *18 *15 **{e} 85.63 {e} 478,515,760",
    "Total 84,816,500 186,747,500 **2{r}20 *19 *14 **{e} 80{r}32 {e} 6,812,644,760",
    "Source: EEX, DEHSt",
]).format(e=EURO, r=chr(0xFFFD))

# The year table of the fourth quarter 2023 report, as its text layer reads.
TABLE_2023 = "\n".join([
    "Table 2: Overview of the entire year 2023",
    "Auction Cover Successful",
    "Month Type Bid volume Bidders Price Revenue",
    "volume ratio bidders",
    "January EUA 5,818,500 12,115,000 *2.08 *22 *18 *{e} 81.38 {e} 473,509,530",
    "February EUA 7,758,000 16,890,500 *2.18 *19 *14 *{e} 92.59 {e} 718,332,615",
    "March EUA 9,697,500 21,638,500 *2.23 *19 *15 *{e} 89.43 {e} 867,286,215",
    "April EUA 5,818,500 12,986,000 *2.23 *21 *16 *{e} 88.30 {e} 513,773,550",
    "May EUA 5,818,500 14,379,000 *2.47 *21 *12 *{e} 84.05 {e} 489,064,320",
    "June EUA 9,697,500 20,552,500 *2.12 *21 *12 *{e} 84.96 {e} 823,938,390",
    "July EUA 7,758,000 16,591,000 *2.14 *19 *13 *{e} 86.76 {e} 673,045,290",
    "August EUA 3,886,500 11,816,000 **3.04 *18 *9 **{e} 84.93 {e} 330,074,450",
    "September EUA 10,735,000 23,176,000 *2.16 *20 *15 *{e} 82.82 {e} 889,072,700",
    "EUA 8,588,000 16,723,000 *1.95 *21 *16 *{e} 81.29 {e} 698,118,520",
    "October",
    "EUAA 907,000 1,950,500 2.15 13 12 {e} 81.72 {e} 74,120,040",
    "November EUA 8,588,000 14,467,500 *1.68 *22 *17 *{e} 76.82 {e} 659,687,220",
    "December EUA 6,445,000 11,742,500 **1.82 *20 *17 **{e} 69.30 {e} 446,606,230",
    "Total 91,516,000 195,028,000 **2.13 *20 *14 **{e} 83.66 {e} 7,656,629,070",
    "Source: EEX, DEHSt",
]).format(e=EURO, r=chr(0xFFFD))


EARLIER = {(2019, "Q4"): TABLE_2019, (2020, "Q4"): TABLE_2020, (2021, "Q4"): TABLE_2021,
           (2022, "Q4"): TABLE_2022, (2023, "Q4"): TABLE_2023}


def test_the_latest_report_of_each_year_is_chosen():
    links = dehst.report_links(PAGE)
    chosen = dehst.latest_per_year(links)
    assert {year: report for year, (report, _url) in chosen.items()} == {
        2019: "Q4", 2020: "Q4", 2021: "Q4", 2022: "Q4", 2023: "Q4", 2024: "Q4", 2025: "Q4", 2026: "08"}
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
    reports = {**EARLIER, (2024, "Q4"): TABLE_2024, (2025, "Q4"): TABLE_2025, (2026, "08"): TABLE_2026}
    adapter = dehst.DehstEuaGermanAuctionMonthly(page=PAGE, reports=reports)
    entry = adapter.run()
    assert entry["status"] == "ok" and entry["observations"] == 11 + 12 * 6 + 8
    assert entry["vintage"] == ("2019_report_Q4, 2020_report_Q4, 2021_report_Q4, 2022_report_Q4, "
                                "2023_report_Q4, 2024_report_Q4, 2025_report_Q4, 2026_report_08")
    assert "proxy for the EU price" in adapter.note and "non-commercial" in adapter.note
    assert "8 report(s) read this run" in adapter.note
    frame = base.read_cache("dehst_eua_german_auction_monthly")
    assert frame["report"].value_counts().to_dict() == {
        "2019_report_Q4": 11, "2020_report_Q4": 12, "2021_report_Q4": 12, "2022_report_Q4": 12,
        "2023_report_Q4": 12, "2024_report_Q4": 12, "2025_report_Q4": 12, "2026_report_08": 8}
    # a second run reads only a year with a later report than the cache holds
    again = dehst.DehstEuaGermanAuctionMonthly(page=PAGE, reports={(2026, "08"): TABLE_2026})
    again.reports = {}  # nothing may be asked for
    entry = again.run()
    assert entry["observations"] == 11 + 12 * 6 + 8
    assert "nothing read this run" in again.note


def test_the_2019_table_starts_in_february_and_reads_the_odd_december_row():
    frame = dehst.parse_year_table(TABLE_2019, year=2019, report="Q4").set_index("date")
    assert len(frame) == 11
    assert frame.index.min() == pd.Timestamp("2019-02-01")
    assert frame.loc[pd.Timestamp("2019-02-01"), "eua_eur_t"] == 20.75
    # October's aviation allowances are left out, and taken out of the Total row
    assert frame.loc[pd.Timestamp("2019-10-01"), "eua_eur_t"] == 24.38
    assert frame.loc[pd.Timestamp("2019-10-01"), "auction_volume"] == 11338000
    assert frame["auction_volume"].sum() == 127561500
    # December's price is printed "25,02" with two euro signs
    assert frame.loc[pd.Timestamp("2019-12-01"), "eua_eur_t"] == 25.02
    assert frame.loc[pd.Timestamp("2019-12-01"), "anomaly"] == "price printed as '25,02'"
    assert frame.loc[pd.Timestamp("2019-12-01"), "average"] == "volume weighted"


def test_the_2020_to_2023_tables_read_twelve_months_each():
    for year, table in ((2020, TABLE_2020), (2021, TABLE_2021), (2022, TABLE_2022), (2023, TABLE_2023)):
        frame = dehst.parse_year_table(table, year=year, report="Q4")
        assert len(frame) == 12 and frame["date"].dt.month.tolist() == list(range(1, 13))
    assert dehst.parse_year_table(TABLE_2021, year=2021, report="Q4").set_index("date").loc[pd.Timestamp("2021-12-01"), "eua_eur_t"] == 80.28


def test_the_committed_series_and_its_overlap_with_the_commission():
    german = base.read_cache("dehst_eua_german_auction_monthly").set_index("date")["eua_eur_t"]
    assert german.index.min() == pd.Timestamp("2019-02-01")
    assert german[pd.Timestamp("2025-07-01")] == 70.01
    common = base.read_cache("ec_eua_auction_monthly").set_index("date")["eua_eur_t"].dropna()
    both = pd.concat([common.rename("eu"), german.rename("de")], axis=1).dropna()
    gap = (both["de"] - both["eu"]).round(2)
    assert len(both) == 76
    assert both.index.min() == pd.Timestamp("2019-02-01") and both.index.max() == pd.Timestamp("2025-06-01")
    assert round(gap.mean(), 2) == 0.29 and round(gap.abs().mean(), 2) == 0.61 and gap.abs().max() == 2.41
    assert gap.abs().idxmax() == pd.Timestamp("2022-08-01")
    recent = gap[gap.index >= pd.Timestamp("2024-01-01")]
    assert len(recent) == 18
    assert round(recent.mean(), 2) == 0.10 and round(recent.abs().mean(), 2) == 0.64 and recent.abs().max() == 1.40

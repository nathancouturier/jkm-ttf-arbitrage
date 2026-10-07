"""EIA's weekly JKM and TTF items, parsed from committed fixtures with no network.

The fixtures are EIA's own bytes: the final Natural Gas Weekly Update as the
landing page served it on 2026-09-30 (the only issue code may read from
eia.gov), the archive index, the WNGSR Supplement's current issue, and eleven
archived issues as the Internet Archive's earliest captures hold them. The
strings built inside this file test forms the parser must refuse or flag; they
are never used as data.
"""

from __future__ import annotations

import pandas as pd
import pytest

from lngarb.sources import base, eia_ngwu
from lngarb.sources.eia_ngwu import NoItem, ParseError, parse_ngwu_item, parse_ngwu_page

FIXTURES = base.REPO_ROOT / "tests" / "fixtures"
FINAL = (FIXTURES / "eia_ngwu_final_issue_2026-01-22.html").read_bytes()
INDEX = (FIXTURES / "eia_ngwu_archive_index_2026-09-30.html").read_bytes()
SUPPLEMENT = (
    (FIXTURES / "eia_wngsr_bullets_lng_2_2026-09-24.html").read_bytes(),
    (FIXTURES / "eia_wngsr_source_lng_2_2026-09-24.html").read_bytes(),
    (FIXTURES / "eia_wngsr_release_dates_2026-09-24.json").read_bytes(),
)


def issue(release: str) -> bytes:
    """An archived issue by its release date, as the Internet Archive captured it."""
    if release == "2026-01-22":
        return FINAL
    return (FIXTURES / ("eia_ngwu_issue_%s_wayback.html" % release)).read_bytes()


def read(release: str) -> tuple[dict, dict]:
    page = parse_ngwu_page(issue(release), where=release)
    return page, parse_ngwu_item(page["item_text"], where=release)


# --------------------------------------------------------------------------
# The anchors: seven weeks, every figure exactly, from the pages themselves
# --------------------------------------------------------------------------

ANCHORS = [
    # release, week ending, East Asia, TTF, year-earlier week, its East Asia and TTF, bases
    ("2021-12-16", "2021-12-15", 35.29, 38.10, "2020-12-16", 8.00, 5.81, "swap, balance of the month", "day-ahead"),
    ("2022-04-07", "2022-04-06", 34.05, 36.17, "2021-04-07", 6.95, 6.84, "swap, month not named", "day-ahead"),
    ("2023-08-10", "2023-08-09", 10.98, 10.35, "2022-08-10", 44.61, 59.16, "front-month futures", "futures, month not named"),
    ("2023-12-07", "2023-12-06", 16.10, 12.91, "2022-12-07", 32.98, 42.95, "front-month futures", "futures, month not named"),
    ("2023-12-21", "2023-12-20", 13.30, 10.89, "2022-12-21", 34.42, 34.99, "front-month futures", "futures, month not named"),
    ("2024-05-30", "2024-05-29", 12.00, 10.86, "2023-05-31", 9.31, 7.98, "front-month futures", "futures, month not named"),
    ("2026-01-22", "2026-01-21", 10.73, 12.40, "2025-01-22", 14.01, 14.57, "front-month futures", "futures, month not named"),
]


@pytest.mark.parametrize("release,week,asia,ttf,prior_week,prior_asia,prior_ttf,asia_basis,ttf_basis", ANCHORS)
def test_every_weekly_anchor_reproduces_exactly(release, week, asia, ttf, prior_week, prior_asia, prior_ttf, asia_basis, ttf_basis):
    page, item = read(release)
    assert page["release_date"].isoformat() == release
    assert page["week_ending"].isoformat() == week
    assert item["east_asia_usd_mmbtu"] == asia
    assert item["ttf_usd_mmbtu"] == ttf
    assert item["prior_year_week_ending"] == prior_week
    assert item["prior_year_east_asia_usd_mmbtu"] == prior_asia
    assert item["prior_year_ttf_usd_mmbtu"] == prior_ttf
    assert item["east_asia_basis"] == asia_basis
    assert item["ttf_basis"] == ttf_basis
    assert item["credit"] == "Bloomberg Finance, L.P."


def test_the_typo_of_december_2023_is_kept_as_printed_and_flagged():
    _, item = read("2023-12-21")
    assert item["prior_year_east_asia_printed"] == "$34.420MBtu"
    assert "printed as '$34.420MBtu'" in item["anomaly"]


def test_the_final_issue_prints_its_changes_and_its_definitions_word_for_word():
    _, item = read("2026-01-22")
    assert item["east_asia_printed"] == "$10.73/MMBtu"
    assert item["ttf_printed"] == "$12.40/MMBtu"
    assert item["east_asia_change_printed"] == "increased $1.14/MMBtu"
    assert item["ttf_change_printed"] == "increased $2.18/MMBtu"
    assert item["east_asia_definition"] == (
        "weekly average front-month futures prices for liquefied natural gas "
        "(LNG) cargoes in East Asia"
    )
    # "front-month" is not in the TTF sentence. The definition says only what
    # the sentence says.
    assert item["ttf_definition"] == (
        "Natural gas futures for delivery at the Title Transfer Facility (TTF) "
        "in the Netherlands"
    )


def test_the_storage_sentence_in_the_final_issue_is_flagged_not_dropped_silently():
    page, item = read("2026-01-22")
    assert item["anomaly"] == "1 further sentence(s) not about the two prices"
    assert "AGSI+" in page["item_text"]


# --------------------------------------------------------------------------
# The forms the item took, each from an issue that prints it
# --------------------------------------------------------------------------

def test_the_first_issue_carries_the_prices_inside_the_spot_item_with_no_heading():
    page, item = read("2021-09-16")
    assert page["item_text"].startswith("Natural gas spot prices rose at most locations")
    assert item["east_asia_usd_mmbtu"] == 18.69
    assert item["ttf_usd_mmbtu"] == 17.96
    assert item["east_asia_definition"] == "swap prices for October liquefied natural gas (LNG) cargos in East Asia"
    assert item["east_asia_basis"] == "swap, delivery month named"
    assert item["ttf_basis"] == "spot, product not named"
    # "respectively": the year-earlier prices follow the order the markets are named in.
    assert (item["prior_year_week_ending"], item["prior_year_east_asia_usd_mmbtu"], item["prior_year_ttf_usd_mmbtu"]) == ("2020-09-16", 4.34, 3.11)
    # The Henry Hub sentence carries prices but no East Asia or TTF level.
    assert item["anomaly"] == "3 further sentence(s) not about the two prices"


def test_a_level_restated_as_the_weekly_average_belongs_to_the_market_named_before_it():
    _, item = read("2021-11-04")
    assert item["east_asia_usd_mmbtu"] == 31.59
    assert item["east_asia_basis"] == "swap, prompt month"
    assert item["east_asia_definition"].startswith("swap prices for prompt month (December)")
    assert item["ttf_usd_mmbtu"] == 23.43


def test_a_ttf_sentence_that_also_names_east_asia_is_read_as_ttf():
    page, item = read("2022-02-24")
    assert page["item_text"].startswith("International Spot Prices:")
    assert "bringing the TTF price back above the price in East Asia" in page["item_text"]
    assert item["ttf_usd_mmbtu"] == 25.72
    assert item["east_asia_usd_mmbtu"] == 24.39
    assert item["east_asia_basis"] == "swap, balance of the month"


def test_one_sentence_giving_both_levels_is_split_and_no_year_earlier_is_none():
    _, item = read("2022-07-14")
    assert item["east_asia_usd_mmbtu"] == 39.13
    assert item["ttf_usd_mmbtu"] == 51.88
    assert item["east_asia_basis"] == item["ttf_basis"] == "futures, month not named"
    assert item["prior_year_week_ending"] is None
    assert item["prior_year_east_asia_usd_mmbtu"] is None


def test_an_issue_without_the_item_raises_no_item():
    with pytest.raises(NoItem) as caught:
        parse_ngwu_page(issue("2025-03-27"), where="2025/03_27")
    assert "2025/03_27" in str(caught.value)


def test_a_header_date_printed_without_its_comma_is_read():
    # Two 2020 issues print "April 16 2020" and "June 24 2020" in their header.
    edited = FINAL.replace(b"January 21, 2026", b"January 21 2026", 1)
    assert edited != FINAL
    assert parse_ngwu_page(edited, where="edited copy")["week_ending"].isoformat() == "2026-01-21"


# --------------------------------------------------------------------------
# Forms the parser must flag or refuse
# --------------------------------------------------------------------------

LEGS = (
    "According to Bloomberg Finance, L.P., weekly average front-month futures prices "
    "for liquefied natural gas (LNG) cargoes in East Asia decreased 47 cents to a "
    "weekly average of $16.10/MMBtu. Natural gas futures for delivery at the Title "
    "Transfer Facility (TTF) in the Netherlands decreased $1.06 to a weekly average "
    "of $12.91/MMBtu."
)
TTF_LEG = LEGS.split(". ")[1]


def test_a_change_in_cents_and_in_dollars_without_a_unit_both_parse():
    item = parse_ngwu_item(LEGS, where="cents case")
    assert item["east_asia_change_printed"] == "decreased 47 cents"
    assert item["ttf_change_printed"] == "decreased $1.06"
    assert item["prior_year_week_ending"] is None


def test_only_the_opening_sentence_is_taken_as_the_summary():
    opening = "International natural gas futures prices decreased this report week. "
    assert parse_ngwu_item(opening + LEGS, where="opening")["anomaly"] is None
    later = " International natural gas prices in Australia rose as supplies tightened."
    assert parse_ngwu_item(opening + LEGS + later, where="later")["anomaly"] == (
        "1 further sentence(s) not about the two prices"
    )


def test_a_market_named_without_a_level_stops_the_parse():
    text = "East Asia LNG swaps for the balance of the month averaged a weekly average of $35.29/MMBtu."
    with pytest.raises(ParseError) as caught:
        parse_ngwu_item(text + " " + TTF_LEG, where="swap case")
    assert "swap case" in str(caught.value)
    assert "no east_asia level" in str(caught.value)


def test_a_price_whose_product_is_not_named_stops_the_parse():
    text = "Bloomberg Finance, L.P. reports prices for LNG cargoes in East Asia rose to a weekly average of $9.10/MMBtu."
    with pytest.raises(ParseError) as caught:
        parse_ngwu_item(text + " " + TTF_LEG, where="no product")
    assert "product is not named" in str(caught.value)


def test_two_levels_for_one_market_stop_the_parse():
    with pytest.raises(ParseError) as caught:
        parse_ngwu_item(LEGS + " " + TTF_LEG, where="twice")
    assert "two ttf levels" in str(caught.value)


def test_a_missing_market_stops_the_parse():
    with pytest.raises(ParseError) as caught:
        parse_ngwu_item(LEGS.split(". ")[0] + ".", where="one leg")
    assert "no ttf level" in str(caught.value)


def test_a_year_earlier_sentence_with_one_price_stops_the_parse():
    text = LEGS + " In the same week last year (week ending December 7, 2022), the price was $32.98/MMBtu in East Asia."
    with pytest.raises(ParseError) as caught:
        parse_ngwu_item(text, where="one price")
    assert "1 prices" in str(caught.value)


def test_dashes_are_stored_as_code_points_and_abbreviations_do_not_split():
    assert eia_ngwu.normalise_text("2022" + chr(0x2012) + "23 winter " + chr(0x2014) + " mild") == "2022[U+2012]23 winter [U+2014] mild"
    sentences = eia_ngwu.split_sentences("Credit to Bloomberg Finance, L.P. Prices fell. U.S. exports rose.")
    assert sentences == ["Credit to Bloomberg Finance, L.P. Prices fell.", "U.S. exports rose."]


# --------------------------------------------------------------------------
# Checks that need more than one issue
# --------------------------------------------------------------------------

def _two_weeks(first_text: str, second_text: str) -> pd.DataFrame:
    return pd.DataFrame({
        "date": pd.to_datetime(["2023-09-06", "2023-09-13"]),
        "folder": ["2023/09_07", "2023/09_14"],
        "item_text": [first_text, second_text],
    })


def test_an_item_repeated_from_an_earlier_issue_has_its_values_left_empty():
    text = LEGS + (
        " In the same week last year (week ending September 7, 2022), the prices "
        "were $56.07/MMBtu in East Asia and $66.49/MMBtu at TTF."
    )
    frame = eia_ngwu.read_items(_two_weeks(text, text))
    first, second = frame.iloc[0], frame.iloc[1]
    assert first["east_asia_usd_mmbtu"] == 16.10
    for column in eia_ngwu.VALUE_COLUMNS:
        assert pd.isna(second[column]), column
    assert second["east_asia_printed"] == "$16.10/MMBtu"
    assert "repeats the one of issue 2023/09_07 word for word" in second["anomaly"]
    assert "371 days before this week's end" in second["anomaly"]


def test_reading_the_items_again_changes_nothing():
    committed = base.read_cache("eia_ngwu_international_weekly")
    again = eia_ngwu.read_items(committed)
    for column in committed.columns:
        left = committed[column].astype(object).where(committed[column].notna(), None).tolist()
        right = again[column].astype(object).where(again[column].notna(), None).tolist()
        if column == "date":
            left = [str(pd.Timestamp(v).date()) for v in left]
            right = [str(pd.Timestamp(v).date()) for v in right]
        assert left == right, column


def test_the_committed_weeks_and_the_two_repeated_issues():
    committed = base.read_cache("eia_ngwu_international_weekly")
    assert len(committed) == 207
    assert committed["folder"].iloc[0] == "2021/09_16"
    assert committed["folder"].iloc[-1] == "2026/01_22"
    empty = committed[committed["east_asia_usd_mmbtu"].isna()]["folder"].tolist()
    assert empty == ["2023/09_14", "2024/03_07"]


def test_the_year_earlier_figures_differ_wherever_the_basis_changed():
    committed = base.read_cache("eia_ngwu_international_weekly")
    check = eia_ngwu.year_earlier_check(committed)
    swaps_and_day_ahead = check[check["basis"].str.startswith("swap") | (check["basis"] == "day-ahead")]
    assert len(swaps_and_day_ahead) == 52
    assert (swaps_and_day_ahead["difference"] != 0).all()
    futures = check[~check.index.isin(swaps_and_day_ahead.index) & check["difference"].notna()]
    differ = futures[futures["difference"] != 0]
    assert sorted(zip(differ["week_ending"], differ["market"], differ["difference"])) == [
        ("2022-08-03", "east_asia", -0.6),
        ("2024-07-10", "east_asia", -0.09),
        ("2024-07-10", "ttf", -0.39),
    ]


# --------------------------------------------------------------------------
# The archive index
# --------------------------------------------------------------------------

def test_the_index_lists_every_issue_by_folder_and_the_week_nothing_was_released():
    index = eia_ngwu.parse_index(INDEX)
    assert index["date"].is_monotonic_increasing
    assert not index["date"].duplicated().any()
    assert index["date"].iloc[0] == pd.Timestamp("2016-01-07")
    assert index["date"].iloc[-1] == pd.Timestamp("2026-01-22")
    assert index.loc[index["date"] == pd.Timestamp("2026-01-22"), "folder"].item() == "2026/01_22"

    gap = index[index["status"] == "no report released"]
    assert gap["date"].tolist() == [pd.Timestamp("2024-06-20")]
    assert gap["folder"].isna().all()

    published = index[index["status"] == "published"]
    assert len(published) == 488
    from_2020 = published[published["date"] >= pd.Timestamp("2020-01-01")]
    assert len(from_2020) == 292
    assert len(published[published["date"] >= pd.Timestamp("2018-01-01")]) == 389


def test_the_index_reads_every_link_a_plain_scan_of_the_markup_finds():
    index = eia_ngwu.parse_index(INDEX)
    read = set(index["folder"].dropna())
    assert read == eia_ngwu.listed_folders(INDEX)
    assert len(read) == 488


def test_the_rows_with_no_opening_tr_are_read_with_their_printed_days():
    # 35 rows of the page have no <tr>; these are three of them.
    index = eia_ngwu.parse_index(INDEX).set_index("folder")
    assert index.at["2016/02_11", "release_day_printed"] == "11"
    assert index.at["2016/02_11", "week_ending_day_printed"] == "10"
    assert index.at["2017/12_07", "week_ending_day_printed"] == "6"
    assert index.at["2025/03_13", "release_day_printed"] == "13"


def test_the_index_ignores_the_rows_inside_html_comments():
    # The 2026 tab carries a commented copy of 43 rows of 2025.
    index = eia_ngwu.parse_index(INDEX)
    in_2025 = index[(index["date"].dt.year == 2025) & (index["status"] == "published")]
    assert len(in_2025) == 47


def test_the_friday_release_and_the_march_2025_weeks_are_as_listed():
    index = eia_ngwu.parse_index(INDEX)
    dates = set(index["date"].dt.strftime("%Y-%m-%d"))
    assert "2025-01-10" in dates and "2025-01-09" not in dates
    assert {"2025-03-06", "2025-03-13", "2025-03-20", "2025-03-27"} <= dates


def test_a_link_the_table_walk_cannot_place_fails_the_parse():
    stray = b'<p><a href="/naturalgas/weekly/archivenew_ngwu/2017/01_01">stray</a></p>'
    with pytest.raises(ParseError) as caught:
        eia_ngwu.parse_index(INDEX + stray)
    assert "2017/01_01" in str(caught.value)


# --------------------------------------------------------------------------
# The Supplement
# --------------------------------------------------------------------------

def test_the_supplement_issue_of_24_september_2026():
    row = eia_ngwu.parse_supplement(*SUPPLEMENT)
    assert row["date"].isoformat() == "2026-09-23"
    assert row["release_date"].isoformat() == "2026-09-24"
    assert row["jkm_usd_mmbtu"] == 26.41
    assert row["ttf_usd_mmbtu"] == 25.15
    assert row["jkm_change_printed"] == "97 cents higher than the previous week"
    assert row["ttf_change_printed"] == "$2.11 lower than the previous week"
    assert row["jkm_definition"] == "The Japan-Korea Marker (JKM) price"
    assert row["ttf_definition"] == "The price at the Title Transfer Facility (TTF) in Europe"
    assert row["credit"] == "Bloomberg Finance, L.P."
    assert row["anomaly"] == "1 further bullet(s) not about the two prices"


def test_a_supplement_whose_two_dates_disagree_is_refused():
    prices, source, dates = SUPPLEMENT
    edited = prices.replace(b"September 23", b"September 16")
    with pytest.raises(ParseError) as caught:
        eia_ngwu.parse_supplement(edited, source, dates)
    assert "release_dates.json" in str(caught.value)


def supplement_capture(release: str) -> tuple[bytes, bytes, bytes]:
    """A past Supplement issue as the Internet Archive captured its three files."""
    return tuple(
        (FIXTURES / ("eia_wngsr_%s_%s_wayback.%s" % (name, release, ext))).read_bytes()
        for name, ext in (("bullets_lng_2", "html"), ("source_lng_2", "html"), ("release_dates", "json"))
    )


def test_the_supplement_of_2_april_2026_names_neither_abbreviation():
    row = eia_ngwu.parse_supplement(*supplement_capture("2026-04-02"))
    assert row["date"].isoformat() == "2026-04-01"
    assert (row["jkm_usd_mmbtu"], row["ttf_usd_mmbtu"]) == (20.28, 17.74)
    assert row["jkm_definition"] == "The Japan-Korea Marker price"
    assert row["ttf_definition"] == "The price at the Title Transfer Facility in Europe"
    assert row["anomaly"] is None


def test_the_supplement_of_6_august_2026_and_its_comparison_bullet():
    row = eia_ngwu.parse_supplement(*supplement_capture("2026-08-06"))
    assert row["date"].isoformat() == "2026-08-05"
    assert (row["jkm_usd_mmbtu"], row["ttf_usd_mmbtu"]) == (21.23, 19.14)
    assert row["ttf_change_printed"] == "$1.03/MMBtu lower than the previous week"
    # "this week's TTF and JKM prices are up by 74% and 99%" is about both
    # markets and gives neither level.
    assert row["anomaly"] == "1 further bullet(s) not about the two prices"


SUPPLEMENT_HEADER = ["original", "timestamp", "statuscode", "mimetype", "digest"]
CONTENT = "https://www.eia.gov/naturalgas/weekly/supplement/content//"


def test_each_distinct_prices_fragment_is_one_issue_with_the_files_captured_beside_it():
    rows = [
        SUPPLEMENT_HEADER,
        [CONTENT + "bullets_lng_2.html", "20260811051259", "200", "text/html", "D1"],
        [CONTENT + "bullets_lng_2.html", "20260811222538", "200", "text/html", "D1"],
        [CONTENT + "source_lng_2.html", "20260811051259", "200", "text/html", "S1"],
        [CONTENT + "release_dates.json", "20260811051259", "200", "application/json", "R1"],
        [CONTENT + "release_dates.json", "20260811222537", "200", "application/json", "R2"],
        # A fragment whose source file was captured an hour away has no source.
        [CONTENT + "bullets_lng_2.html", "20260901100000", "200", "text/html", "D2"],
        [CONTENT + "source_lng_2.html", "20260901110000", "200", "text/html", "S1"],
        [CONTENT + "release_dates.json", "20260901100001", "200", "application/json", "R3"],
        # The archive path is never taken for the current issue's files.
        ["https://www.eia.gov/naturalgas/weekly/supplement/archive/2026/03/05/bullets_lng_2.html", "20260314000000", "200", "text/html", "D3"],
    ]
    sets = eia_ngwu.supplement_captures(rows)
    assert len(sets) == 2
    assert sets[0] == {
        "bullets_lng_2.html": ("20260811051259", CONTENT + "bullets_lng_2.html"),
        "source_lng_2.html": ("20260811051259", CONTENT + "source_lng_2.html"),
        "release_dates.json": ("20260811051259", CONTENT + "release_dates.json"),
    }
    assert set(sets[1]) == {"bullets_lng_2.html", "release_dates.json"}


def test_a_fragment_is_read_from_its_earliest_capture_that_has_both_other_files():
    rows = [
        SUPPLEMENT_HEADER,
        # Captured alone first, then again with its two siblings.
        [CONTENT + "bullets_lng_2.html", "20260701000000", "200", "text/html", "D1"],
        [CONTENT + "bullets_lng_2.html", "20260702000000", "200", "text/html", "D1"],
        [CONTENT + "source_lng_2.html", "20260702000001", "200", "text/html", "S1"],
        [CONTENT + "release_dates.json", "20260702000002", "200", "application/json", "R1"],
    ]
    assert eia_ngwu.supplement_captures(rows) == [{
        "bullets_lng_2.html": ("20260702000000", CONTENT + "bullets_lng_2.html"),
        "source_lng_2.html": ("20260702000001", CONTENT + "source_lng_2.html"),
        "release_dates.json": ("20260702000002", CONTENT + "release_dates.json"),
    }]


def _save_supplement_capture(sandbox, release, stamp, *, spoil=False):
    import hashlib
    import json
    folder = sandbox / "private" / "wngsr" / stamp
    folder.mkdir(parents=True)
    records = []
    for name, payload in zip(eia_ngwu.SUPPLEMENT_FILES, supplement_capture(release)):
        (folder / name).write_bytes(payload)
        records.append({
            "issue": stamp, "file": name, "capture_timestamp": stamp,
            "capture_url": "https://web.archive.org/web/%sid_/%s%s" % (stamp, CONTENT, name),
            "sha256": "0" * 64 if spoil else hashlib.sha256(payload).hexdigest(),
        })
    log = sandbox / "private" / "wngsr" / eia_ngwu.CAPTURES_LOG
    with open(log, "a", encoding="utf-8") as handle:
        handle.write("".join(json.dumps(r) + chr(10) for r in records))


def test_past_supplement_issues_saved_from_captures_join_the_current_one(sandbox, monkeypatch):
    prices, source, dates = SUPPLEMENT
    serve(monkeypatch, {
        eia_ngwu.SUPPLEMENT_PRICES_URL: prices,
        eia_ngwu.SUPPLEMENT_SOURCE_URL: source,
        eia_ngwu.SUPPLEMENT_DATES_URL: dates,
    })
    _save_supplement_capture(sandbox, "2026-04-02", "20260405021115")
    _save_supplement_capture(sandbox, "2026-08-06", "20260811051259")
    adapter = eia_ngwu.WngsrInternationalWeekly()
    entry = adapter.run()
    assert entry["observations"] == 3
    cache = base.read_cache("eia_wngsr_international_weekly")
    assert cache["date"].dt.strftime("%Y-%m-%d").tolist() == ["2026-04-01", "2026-08-05", "2026-09-23"]
    assert cache["how_read"].tolist() == [
        "Internet Archive capture of 20260405021115",
        "Internet Archive capture of 20260811051259",
        "current issue",
    ]
    assert "2 read from the Internet Archive's captures" in adapter.note


def test_a_bad_saved_capture_is_set_aside_and_never_stops_the_current_issue(sandbox, monkeypatch):
    prices, source, dates = SUPPLEMENT
    serve(monkeypatch, {
        eia_ngwu.SUPPLEMENT_PRICES_URL: prices,
        eia_ngwu.SUPPLEMENT_SOURCE_URL: source,
        eia_ngwu.SUPPLEMENT_DATES_URL: dates,
    })
    _save_supplement_capture(sandbox, "2026-04-02", "20260405021115", spoil=True)
    # What an interrupted batch leaves: one file of three.
    partial = sandbox / "private" / "wngsr" / "20260811051259"
    partial.mkdir(parents=True)
    (partial / "bullets_lng_2.html").write_bytes(supplement_capture("2026-08-06")[0])
    # A copy saved by hand is not a capture and is not read as one.
    (sandbox / "private" / "wngsr" / "by_hand").mkdir()
    rows, problems = eia_ngwu.WngsrInternationalWeekly().read_saved_captures()
    assert rows == []
    assert problems == [
        "20260405021115/bullets_lng_2.html is not the capture its log records",
        # Its one file has no log line yet.
        "20260811051259/bullets_lng_2.html is not the capture its log records",
    ]
    adapter = eia_ngwu.WngsrInternationalWeekly()
    entry = adapter.run()
    assert entry["status"] == "ok" and entry["observations"] == 1
    assert "Not read this run: 20260405021115/bullets_lng_2.html" in adapter.note
    assert str(sandbox) not in adapter.note


# --------------------------------------------------------------------------
# The adapters, with http replaced by the fixtures
# --------------------------------------------------------------------------

class Served:
    def __init__(self, content):
        self.content = content
        self.status_code = 200


def serve(monkeypatch, pages):
    requested = []

    def fake_get(url, **_kwargs):
        requested.append(url)
        if url not in pages:
            raise AssertionError("unexpected request for %s" % url)
        return Served(pages[url])

    monkeypatch.setattr(eia_ngwu, "http_get", fake_get)
    return requested


def test_the_international_adapter_reads_the_landing_page_and_saved_issues(sandbox, monkeypatch):
    requested = serve(monkeypatch, {eia_ngwu.LANDING_URL: FINAL})
    saved = sandbox / "private" / "ngwu" / "2026"
    saved.mkdir(parents=True)
    # The final issue saved by hand under its folder name reads the same week,
    # so the merge keeps one row and the texts must agree.
    (saved / "01_22.html").write_bytes(FINAL)

    entry = eia_ngwu.NgwuInternationalWeekly().run()
    assert requested == [eia_ngwu.LANDING_URL]
    assert entry["status"] == "ok"
    assert entry["observations"] == 1
    assert entry["first_date"] == entry["last_date"] == "2026-01-21"

    cache = base.read_cache("eia_ngwu_international_weekly")
    assert cache["how_read"].tolist() == ["saved by hand"]
    assert cache["east_asia_usd_mmbtu"].tolist() == [10.73]
    assert cache["east_asia_basis"].tolist() == ["front-month futures"]


def test_a_saved_issue_without_the_item_gives_no_row_and_is_counted(sandbox, monkeypatch):
    serve(monkeypatch, {eia_ngwu.LANDING_URL: FINAL})
    saved = sandbox / "private" / "ngwu" / "2025"
    saved.mkdir(parents=True)
    (saved / "03_27.html").write_bytes(issue("2025-03-27"))
    base.write_cache("eia_ngwu_issue_index", pd.DataFrame({
        "date": pd.to_datetime(["2025-03-27", "2026-01-22"]),
        "folder": ["2025/03_27", "2026/01_22"],
        "status": ["published", "published"],
    }))
    adapter = eia_ngwu.NgwuInternationalWeekly()
    entry = adapter.run()
    assert entry["observations"] == 1
    assert adapter.without_item == ["2025/03_27"]
    # The note is built from the committed index, not from the saved pages.
    assert "Of the 2 issues the index lists from 2016, the 1 before 2026/01_22" in adapter.note


def test_a_saved_page_matching_its_capture_log_is_labelled_with_the_capture(sandbox, monkeypatch):
    import hashlib
    import json
    serve(monkeypatch, {eia_ngwu.LANDING_URL: FINAL})
    saved = sandbox / "private" / "ngwu"
    (saved / "2021").mkdir(parents=True)
    (saved / "2022").mkdir(parents=True)
    page = issue("2021-12-16")
    (saved / "2021" / "12_16.html").write_bytes(page)
    (saved / "2022" / "04_07.html").write_bytes(issue("2022-04-07"))
    capture = "https://web.archive.org/web/20211216224644id_/https://www.eia.gov/naturalgas/weekly/archivenew_ngwu/2021/12_16/"
    records = [
        {"folder": "2021/12_16", "capture_timestamp": "20211216224644", "capture_url": capture,
         "sha256": hashlib.sha256(page).hexdigest()},
        # A record whose checksum is not the saved page's does not label it.
        {"folder": "2022/04_07", "capture_timestamp": "20220408103209", "capture_url": "x",
         "sha256": "0" * 64},
    ]
    log = saved / eia_ngwu.CAPTURES_LOG
    log.write_text("".join(json.dumps(r) + chr(10) for r in records), encoding="utf-8")
    eia_ngwu.NgwuInternationalWeekly().run()
    cache = base.read_cache("eia_ngwu_international_weekly").set_index("folder")
    assert cache.at["2021/12_16", "how_read"] == "Internet Archive capture of 20211216224644"
    assert cache.at["2021/12_16", "page_url"] == capture
    assert cache.at["2022/04_07", "how_read"] == "saved by hand"
    assert cache.at["2022/04_07", "page_url"].endswith("archivenew_ngwu/2022/04_07/")


def test_a_saved_issue_whose_name_disagrees_with_its_page_is_refused(sandbox, monkeypatch):
    serve(monkeypatch, {eia_ngwu.LANDING_URL: FINAL})
    saved = sandbox / "private" / "ngwu" / "2026"
    saved.mkdir(parents=True)
    (saved / "01_15.html").write_bytes(FINAL)
    with pytest.raises(ParseError) as caught:
        eia_ngwu.NgwuInternationalWeekly().run()
    assert "01_15" in str(caught.value)


def test_the_supplement_adapter_appends_a_week_and_keeps_what_is_committed(sandbox, monkeypatch):
    prices, source, dates = SUPPLEMENT
    serve(
        monkeypatch,
        {
            eia_ngwu.SUPPLEMENT_PRICES_URL: prices,
            eia_ngwu.SUPPLEMENT_SOURCE_URL: source,
            eia_ngwu.SUPPLEMENT_DATES_URL: dates,
        },
    )
    first = eia_ngwu.WngsrInternationalWeekly().run()
    second = eia_ngwu.WngsrInternationalWeekly().run()
    assert first["observations"] == second["observations"] == 1
    assert second["last_date"] == "2026-09-23"


def test_nothing_in_this_module_can_request_the_disallowed_archive(monkeypatch):
    """The archive URL is only ever a label for a file saved by hand."""
    rules = base.parse_robots(
        (FIXTURES / "eia_robots_2026-09-30.txt").read_text(encoding="utf-8"), "Mozilla"
    )
    assert not base.robots_allows(rules, eia_ngwu.ARCHIVE_URL.format(folder="2023/12_07"))
    for url in (
        eia_ngwu.LANDING_URL,
        eia_ngwu.INDEX_URL,
        eia_ngwu.SUPPLEMENT_PRICES_URL,
        eia_ngwu.SUPPLEMENT_SOURCE_URL,
        eia_ngwu.SUPPLEMENT_DATES_URL,
    ):
        assert base.robots_allows(rules, url), url


# --------------------------------------------------------------------------
# Archived issues from the Internet Archive's copies
# --------------------------------------------------------------------------

HEADER = ["original", "timestamp", "statuscode", "mimetype"]


def test_the_earliest_html_capture_of_each_issue_is_chosen():
    rows = [
        HEADER,
        ["https://www.eia.gov/naturalgas/weekly/archivenew_ngwu/2023/12_07/", "20231210000000", "200", "text/html"],
        ["http://www.eia.gov/naturalgas/weekly/archivenew_ngwu/2023/12_07/index.php", "20231208000000", "200", "text/html"],
        ["https://www.eia.gov/naturalgas/weekly/archivenew_ngwu/2023/12_07/img/x.png", "20231201000000", "200", "image/png"],
        ["https://www.eia.gov/naturalgas/weekly/archivenew_ngwu/2023/12_14/", "20231201000000", "302", "text/html"],
    ]
    captures = eia_ngwu.internet_archive_captures(rows)
    assert captures == {
        "2023/12_07": ("20231208000000", "http://www.eia.gov/naturalgas/weekly/archivenew_ngwu/2023/12_07/index.php")
    }
    assert eia_ngwu.capture_url(*captures["2023/12_07"]) == (
        "https://web.archive.org/web/20231208000000id_/"
        "http://www.eia.gov/naturalgas/weekly/archivenew_ngwu/2023/12_07/index.php"
    )


def test_a_capture_index_without_its_header_is_refused():
    with pytest.raises(base.SourceError):
        eia_ngwu.internet_archive_captures([["a", "b", "c", "d"]])


class _Answer:
    def __init__(self, status, body):
        self.status_code = status
        self.content = body

    def json(self):
        import json
        return json.loads(self.content)


def _index_cache(folders):
    frame = pd.DataFrame({
        "date": pd.to_datetime(["2023-12-07", "2023-12-14"][: len(folders)]),
        "folder": folders,
        "status": ["published"] * len(folders),
    })
    base.write_cache("eia_ngwu_issue_index", frame)


def test_issues_are_saved_with_their_provenance_and_read_back_as_captures(sandbox, monkeypatch):
    import json
    _index_cache(["2023/12_07"])
    cdx = json.dumps([HEADER, ["https://www.eia.gov/naturalgas/weekly/archivenew_ngwu/2023/12_07/", "20231208000000", "200", "text/html"]]).encode()
    page = b"<html><title>Natural Gas Weekly Update</title></html>"
    answers = {eia_ngwu.CDX_URL: _Answer(200, cdx)}
    monkeypatch.setattr(eia_ngwu, "http_get", lambda url, **kw: answers.get(url, _Answer(200, page)))
    summary = eia_ngwu.collect_from_internet_archive(delay=0)
    assert summary["saved"] == 1
    saved = sandbox / "private" / "ngwu" / "2023" / "12_07.html"
    assert saved.read_bytes() == page
    record = json.loads((sandbox / "private" / "ngwu" / eia_ngwu.CAPTURES_LOG).read_text())
    assert record["capture_timestamp"] == "20231208000000"
    # A second run finds nothing left to fetch and sends nothing.
    monkeypatch.setattr(eia_ngwu, "http_get", lambda url, **kw: pytest.fail("nothing should be fetched"))
    assert eia_ngwu.collect_from_internet_archive(delay=0)["wanted"] == 0


def test_an_answer_that_is_not_an_issue_stops_the_batch(sandbox, monkeypatch):
    import json
    _index_cache(["2023/12_07", "2023/12_14"])
    cdx = json.dumps([HEADER] + [
        ["https://www.eia.gov/naturalgas/weekly/archivenew_ngwu/%s/" % f, "20231220000000", "200", "text/html"]
        for f in ("2023/12_07", "2023/12_14")
    ]).encode()
    answers = {eia_ngwu.CDX_URL: _Answer(200, cdx)}
    monkeypatch.setattr(eia_ngwu, "http_get", lambda url, **kw: answers.get(url, _Answer(200, b"")))
    with pytest.raises(base.SourceError) as caught:
        eia_ngwu.collect_from_internet_archive(delay=0)
    assert "batch stopped" in str(caught.value)
    assert not (sandbox / "private" / "ngwu" / "2023" / "12_14.html").exists()


def test_the_year_earlier_check_lists_the_weeks_only_a_later_issue_prints():
    committed = base.read_cache("eia_ngwu_international_weekly")
    check = eia_ngwu.year_earlier_check(committed)
    empty = check[check["value"].isna()]
    assert sorted(zip(empty["week_ending"], empty["market"], empty["value_year_later"])) == [
        ("2023-09-13", "east_asia", 13.36),
        ("2023-09-13", "ttf", 10.99),
        ("2024-03-06", "east_asia", 8.36),
        ("2024-03-06", "ttf", 8.38),
    ]
    assert empty["difference"].isna().all()

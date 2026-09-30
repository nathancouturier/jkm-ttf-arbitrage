"""EIA's weekly JKM and TTF items, parsed from committed fixtures with no network.

The fixtures are EIA's own bytes as served on 2026-09-30: the final Natural Gas
Weekly Update (the only issue code may read), the archive index, and the WNGSR
Supplement's current issue. The strings built inside this file test forms the
parser must refuse or flag; they are never used as data.
"""

from __future__ import annotations

import pandas as pd
import pytest

from lngarb.sources import base, eia_ngwu
from lngarb.sources.eia_ngwu import ParseError, parse_ngwu_item, parse_ngwu_page

FIXTURES = base.REPO_ROOT / "tests" / "fixtures"
FINAL = (FIXTURES / "eia_ngwu_final_issue_2026-01-22.html").read_bytes()
INDEX = (FIXTURES / "eia_ngwu_archive_index_2026-09-30.html").read_bytes()
SUPPLEMENT = (
    (FIXTURES / "eia_wngsr_bullets_lng_2_2026-09-24.html").read_bytes(),
    (FIXTURES / "eia_wngsr_source_lng_2_2026-09-24.html").read_bytes(),
    (FIXTURES / "eia_wngsr_release_dates_2026-09-24.json").read_bytes(),
)


# --------------------------------------------------------------------------
# The anchor: week ending 21 January 2026, the final NGWU issue
# --------------------------------------------------------------------------

def test_the_final_issue_reproduces_its_anchor_exactly():
    page = parse_ngwu_page(FINAL, where="final issue")
    assert page["week_ending"].isoformat() == "2026-01-21"
    assert page["release_date"].isoformat() == "2026-01-22"

    item = parse_ngwu_item(page["item_text"], where="final issue")
    assert item["east_asia_usd_mmbtu"] == 10.73
    assert item["ttf_usd_mmbtu"] == 12.40
    assert item["prior_year_week_ending"] == "2025-01-22"
    assert item["prior_year_east_asia_usd_mmbtu"] == 14.01
    assert item["prior_year_ttf_usd_mmbtu"] == 14.57
    assert item["east_asia_printed"] == "$10.73/MMBtu"
    assert item["ttf_printed"] == "$12.40/MMBtu"
    assert item["east_asia_change_printed"] == "increased $1.14/MMBtu"
    assert item["ttf_change_printed"] == "increased $2.18/MMBtu"
    assert item["credit"] == "Bloomberg Finance, L.P."


def test_the_final_issue_definitions_are_stored_word_for_word():
    page = parse_ngwu_page(FINAL, where="final issue")
    item = parse_ngwu_item(page["item_text"], where="final issue")
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
    page = parse_ngwu_page(FINAL, where="final issue")
    item = parse_ngwu_item(page["item_text"], where="final issue")
    assert item["anomaly"] == "1 further sentence(s) not about the two prices"
    assert "AGSI+" in page["item_text"]


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


def test_a_price_printed_with_a_typo_is_kept_as_printed_and_flagged():
    text = (
        LEGS + " In the same week last year (week ending December 21, 2022), the prices "
        "were $34.420MBtu in East Asia and $34.99/MMBtu at TTF."
    )
    item = parse_ngwu_item(text, where="typo case")
    assert item["prior_year_east_asia_printed"] == "$34.420MBtu"
    assert item["prior_year_east_asia_usd_mmbtu"] == 34.42
    assert "printed as '$34.420MBtu'" in item["anomaly"]
    assert item["prior_year_ttf_usd_mmbtu"] == 34.99


def test_a_change_in_cents_and_in_dollars_without_a_unit_both_parse():
    item = parse_ngwu_item(LEGS, where="cents case")
    assert item["east_asia_change_printed"] == "decreased 47 cents"
    assert item["ttf_change_printed"] == "decreased $1.06"
    assert item["prior_year_week_ending"] is None


def test_an_unrecognised_price_sentence_stops_the_parse():
    text = "East Asia LNG swaps for the balance of the month averaged a weekly average of $35.29/MMBtu."
    with pytest.raises(ParseError) as caught:
        parse_ngwu_item(text + " " + LEGS.split(". ")[1], where="swap case")
    assert "swap case" in str(caught.value)
    assert "does not recognise" in str(caught.value)


def test_a_missing_leg_stops_the_parse():
    with pytest.raises(ParseError) as caught:
        parse_ngwu_item(LEGS.split(". ")[0] + ".", where="one leg")
    assert "no ttf price sentence" in str(caught.value)


def test_a_page_without_the_item_stops_the_parse():
    html = FINAL.replace(b"International futures prices:", b"International prices were:")
    with pytest.raises(ParseError) as caught:
        parse_ngwu_page(html, where="edited copy")
    assert "no 'International futures prices' item" in str(caught.value)


def test_dashes_are_stored_as_code_points_and_abbreviations_do_not_split():
    assert eia_ngwu.normalise_text("2022" + chr(0x2012) + "23 winter " + chr(0x2014) + " mild") == "2022[U+2012]23 winter [U+2014] mild"
    sentences = eia_ngwu.split_sentences("Credit to Bloomberg Finance, L.P. Prices fell. U.S. exports rose.")
    assert sentences == ["Credit to Bloomberg Finance, L.P. Prices fell.", "U.S. exports rose."]


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
    from_2020 = published[published["date"] >= pd.Timestamp("2020-01-01")]
    assert len(from_2020) == 290
    assert len(published[published["date"] >= pd.Timestamp("2018-01-01")]) == 377


def test_the_index_ignores_the_rows_inside_html_comments():
    index = eia_ngwu.parse_index(INDEX)
    in_2025 = index[(index["date"].dt.year == 2025) & (index["status"] == "published")]
    assert len(in_2025) == 45


def test_the_friday_release_and_the_missing_march_2025_weeks_are_as_listed():
    index = eia_ngwu.parse_index(INDEX)
    dates = set(index["date"].dt.strftime("%Y-%m-%d"))
    assert "2025-01-10" in dates and "2025-01-09" not in dates
    assert "2025-03-06" in dates and "2025-03-27" in dates
    assert "2025-03-13" not in dates and "2025-03-20" not in dates


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

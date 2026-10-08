"""ACER's daily LNG values, from the two documents ACER publishes on its main site.

Fixtures: the correction notice of 20 December 2024 and the assessment and
benchmark methodology, version 1.1. ACER authorises reproduction of its
documents provided the source is acknowledged. Nothing here reads TERMINAL:
its historical download, saved by hand, is stood in for by rows built here
with the values the download of 8 October 2026 holds.
"""

from __future__ import annotations

import pandas as pd
import pytest

from lngarb.sources import acer, base

FIXTURES = base.REPO_ROOT / "tests" / "fixtures"
NOTICE = (FIXTURES / "acer_correction_notice_2024-12-20.pdf").read_bytes()
METHODOLOGY = (FIXTURES / "acer_methodology_1.1.pdf").read_bytes()


def test_the_roll_dates_run_from_march_2023_to_december_2024():
    rolls = acer.parse_roll_dates(METHODOLOGY)
    assert rolls[0] == (pd.Timestamp("2023-03-31"), "H2 APR 23")
    assert rolls[-1] == (pd.Timestamp("2024-12-24"), "H2 JAN 25")
    assert len(rolls) == 43


def test_the_period_assessed_on_a_day_is_the_last_roll_before_it():
    rolls = acer.parse_roll_dates(METHODOLOGY)
    assert acer.period_for(pd.Timestamp("2024-11-04"), rolls) == "H2 NOV 24"
    assert acer.period_for(pd.Timestamp("2024-11-08"), rolls) == "H1 DEC 24"
    assert acer.period_for(pd.Timestamp("2024-02-08"), rolls) == "H1 MAR 24"
    assert acer.period_for(pd.Timestamp("2024-02-22"), rolls) == "H2 MAR 24"
    # outside the published table the period is unknown, never guessed
    assert acer.period_for(pd.Timestamp("2026-02-18"), rolls) is None
    # The table's last roll is 24 December 2024, H2 JAN 25; the next one could
    # have come within the table's shortest gap, so the period is held no longer.
    assert acer.period_for(pd.Timestamp("2024-12-30"), rolls) == "H2 JAN 25"
    assert acer.period_for(pd.Timestamp("2025-01-13"), rolls) is None


def test_the_correction_notice_gives_26_days_with_published_and_correct_values():
    notice = acer.parse_correction_notice(NOTICE)
    assert len(notice) == 26
    first = notice.iloc[0]
    assert first["date"] == pd.Timestamp("2024-11-04")
    assert first["eu"] == (38.044, 37.677, -0.367)
    assert first["nwe"] == (41.384, 41.126, -0.258)
    assert first["benchmark"] == (-2.257, -2.624, -0.367)
    assert notice["date"].iloc[-1] == pd.Timestamp("2024-12-09")


def test_only_acers_inconsistent_row_is_flagged(sandbox):
    entry = acer.AcerLngDaily(notice_pdf=NOTICE, methodology_pdf=METHODOLOGY).run()
    assert entry["status"] == "ok"
    assert entry["observations"] == 26
    cache = base.read_cache("acer_lng_daily")
    flagged = cache[cache["anomaly"].notna()]
    assert flagged["date"].tolist() == [pd.Timestamp("2024-11-18")]
    assert "moved by 0.475" in flagged["anomaly"].item()
    row = cache.set_index("date").loc[pd.Timestamp("2024-11-04")]
    assert row["eu_benchmark_spread_eur_mwh"] == -2.624
    assert row["revised_from"].startswith("first published EU 38.044")


def test_no_ttf_level_is_ever_derived(sandbox):
    acer.AcerLngDaily(notice_pdf=NOTICE, methodology_pdf=METHODOLOGY).run()
    columns = set(base.read_cache("acer_lng_daily").columns)
    assert not any("ttf" in c and "spread" not in c for c in columns)


def test_nothing_here_can_reach_terminal():
    for url in (acer.PAGE_URL, acer.NOTICE_URL, acer.METHODOLOGY_URL):
        assert url.startswith("https://www.acer.europa.eu/")



HEADER = ",".join('"%s"' % h for h in acer.TERMINAL_HEADER)


def terminal(*rows: str, bom: bool = False) -> bytes:
    """A TERMINAL download, newest day first as TERMINAL writes it; the file saved had no byte order mark."""
    return ((chr(0xFEFF) if bom else "") + "\n".join([HEADER, *rows]) + "\n").encode("utf-8")


DOWNLOAD = terminal(
    '"2026-10-08","73.687","74.724","74.242",""',
    '"2026-02-23","28.181","27.875","28.339","-3.495"',
    '"2026-02-18","28.232","27.295","28.154","-3.327"',
    '"2024-11-05","39.762","37.765","38.568","-1.924"',
    '"2024-11-04","41.126","37.080","37.677","-2.624"',
    '"2023-01-19","56.770","","",""',
)


def test_the_download_is_read_by_column_with_missing_cells_kept_missing():
    history = acer.parse_terminal_history(DOWNLOAD).set_index("date")
    assert acer.parse_terminal_history(terminal('"2026-02-18","28.232","27.295","28.154","-3.327"', bom=True)).shape == (1, 5)
    day = history.loc[pd.Timestamp("2026-02-18")]
    assert (day["eu_des_eur_mwh"], day["nwe_des_eur_mwh"], day["se_des_eur_mwh"]) == (28.154, 28.232, 27.295)
    assert day["eu_benchmark_spread_eur_mwh"] == -3.327
    assert history.loc[pd.Timestamp("2026-02-23"), "eu_benchmark_spread_eur_mwh"] == -3.495
    # A value not published that day is missing, never zero.
    assert pd.isna(history.loc[pd.Timestamp("2026-10-08"), "eu_benchmark_spread_eur_mwh"])
    assert pd.isna(history.loc[pd.Timestamp("2023-01-19"), "eu_des_eur_mwh"])


def test_a_download_in_another_layout_or_with_a_weekend_is_refused():
    from lngarb.sources.base import SourceError
    with pytest.raises(SourceError):
        acer.parse_terminal_history(DOWNLOAD.replace(b"LNG BENCHMARK", b"BENCHMARK"))
    with pytest.raises(SourceError):
        acer.parse_terminal_history(terminal('"2026-02-21","28.181","27.875","28.339","-3.495"'))


def test_the_nwe_spread_is_the_benchmark_plus_nwe_less_eu():
    history = acer.parse_terminal_history(DOWNLOAD).set_index("date")
    spread = acer.nwe_spread(history)
    assert spread[pd.Timestamp("2026-02-18")] == round(-3.327 + 28.232 - 28.154, 3)
    assert pd.isna(spread[pd.Timestamp("2026-10-08")])


def test_the_download_joins_the_notice_and_agrees_with_its_corrected_days(sandbox):
    adapter = acer.AcerLngDaily(notice_pdf=NOTICE, methodology_pdf=METHODOLOGY, terminal_csv=(DOWNLOAD, "2026-10-08"))
    entry = adapter.run()
    assert entry["status"] == "ok"
    cache = base.read_cache("acer_lng_daily").set_index("date")
    # The notice's days keep the notice's values and its first published ones.
    assert cache.loc[pd.Timestamp("2024-11-04"), "revised_from"].startswith("first published EU 38.044")
    assert pd.isna(cache.loc[pd.Timestamp("2024-11-04"), "anomaly"])
    assert cache.loc[pd.Timestamp("2026-02-18"), "source_document"].startswith("ACER TERMINAL")
    assert cache.loc[pd.Timestamp("2026-02-18"), "nwe_benchmark_spread_eur_mwh"] == round(-3.327 + 28.232 - 28.154, 3)
    # The notice days the download here leaves out are kept and say so.
    assert "not in TERMINAL's download" in cache.loc[pd.Timestamp("2024-11-06"), "anomaly"]
    assert "saved by hand on 2026-10-08" in adapter.note


def test_a_download_that_disagrees_with_the_notice_is_flagged(sandbox):
    wrong = DOWNLOAD.replace(b'"2024-11-04","41.126"', b'"2024-11-04","41.384"')
    acer.AcerLngDaily(notice_pdf=NOTICE, methodology_pdf=METHODOLOGY, terminal_csv=(wrong, "2026-10-08")).run()
    cache = base.read_cache("acer_lng_daily").set_index("date")
    assert "differs from the notice's corrected value" in cache.loc[pd.Timestamp("2024-11-04"), "anomaly"]
    assert cache.loc[pd.Timestamp("2024-11-04"), "nwe_des_eur_mwh"] == 41.126


def test_the_committed_history_and_the_regas_assumption():
    cache = base.read_cache("acer_lng_daily").set_index("date")
    spread = cache["nwe_benchmark_spread_eur_mwh"].dropna()
    assert spread.index.min() == pd.Timestamp("2023-03-31")
    # ACER's monitoring report put the EU spread at about 2 EUR/MWh from January
    # to August 2023; the NWE spread computed here averages -2.33 from April.
    assert round(spread.loc["2023-04-01":"2023-08-31"].mean(), 2) == -2.33
    # The download gives the notice's corrected values but one, by a thousandth.
    noted = cache[cache["anomaly"].fillna("").str.contains("differs from the notice")]
    assert noted.index.tolist() == [pd.Timestamp("2024-12-04")]

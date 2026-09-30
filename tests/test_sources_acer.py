"""ACER's daily LNG values, from the two documents ACER publishes on its main site.

Fixtures: the correction notice of 20 December 2024 and the assessment and
benchmark methodology, version 1.1. ACER authorises reproduction of its
documents provided the source is acknowledged. Nothing here reads TERMINAL.
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

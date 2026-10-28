"""The fresh water surcharge at Gatun Lake's level, held only in a private run."""

from __future__ import annotations

import pytest

from lngarb import canals, config, export


def test_without_levels_the_share_is_the_parameter():
    toll = 400_000.0
    fixed = config.PARAMETERS["panama_fresh_water_fixed_usd"].value
    assert canals.panama_fresh_water_surcharge("2024-03-01", toll) == pytest.approx(fixed + 0.05 * toll)
    assert not canals.gatun_levels_held()


def test_inside_the_block_the_curve_runs_at_the_level_of_the_day_before():
    toll = 400_000.0
    fixed = config.PARAMETERS["panama_fresh_water_fixed_usd"].value
    with canals.gatun_levels({"2023-09-07": 79.7, "2023-09-09": float("nan")}):
        assert canals.gatun_levels_held()
        share = canals.panama_fresh_water_share_at_level(79.7, "2023-09-08")
        assert canals.panama_fresh_water_surcharge("2023-09-08", toll) == pytest.approx(fixed + share * toll)
        # A missing level, or a blank one, keeps the 5 percent assumption.
        assert canals.panama_fresh_water_surcharge("2023-09-10", toll) == pytest.approx(fixed + 0.05 * toll)
        assert canals.panama_fresh_water_surcharge("2023-09-12", toll) == pytest.approx(fixed + 0.05 * toll)
        # Before the surcharge, nothing.
        assert canals.panama_fresh_water_surcharge("2020-01-01", toll) == 0.0
    assert not canals.gatun_levels_held()


def test_the_site_is_not_written_while_levels_are_held():
    with canals.gatun_levels({"2024-01-01": 80.0}):
        with pytest.raises(RuntimeError, match="question 54"):
            export.write_all()


def test_the_level_series_is_declared_private():
    source = config.SOURCES["acp_gatun_level_daily"]
    assert source.committable is False and source.frequency == "daily"
    assert "question 54" in source.licence_note

"""The analysis: its observations, its statistics and its breakevens, on the committed data."""

from __future__ import annotations

import math
from dataclasses import replace
from datetime import date

import numpy as np
import pandas as pd
import pytest

from lngarb import analysis, cases, worked
from lngarb.sources import base


@pytest.fixture(scope="module")
def obs():
    return analysis.observations()


@pytest.fixture(scope="module")
def rows(obs):
    # The weeks and months of 2026 to September, enough to check every identity quickly.
    subset = obs[(obs["day"] >= "2026-01-01") & (obs["day"] <= "2026-09-30")]
    worked_rows, missing = analysis.work(subset)
    assert missing.empty
    return worked_rows


# --------------------------------------------------------------------------
# Newey-West
# --------------------------------------------------------------------------

def _series(n=60, seed=7):
    rng = np.random.default_rng(seed)
    x = np.cumsum(rng.normal(size=n)) * 0.3
    e = np.zeros(n)
    for t in range(1, n):
        e[t] = 0.6 * e[t - 1] + rng.normal(scale=0.5)
    return 0.4 + 0.05 * x + e, x


def _newey_west_by_matrix(y, x, months, lags):
    """The same estimator written the other way: X' diag(u) W diag(u) X with a Bartlett weight matrix."""
    design = np.column_stack([np.ones(len(y)), x])
    beta = np.linalg.lstsq(design, y, rcond=None)[0]
    u = y - design @ beta
    distance = np.abs(np.subtract.outer(months, months))
    weights = np.where(distance <= lags, 1.0 - distance / (lags + 1.0), 0.0)
    meat = design.T @ (u[:, None] * weights * u[None, :]) @ design
    bread = np.linalg.inv(design.T @ design)
    return np.sqrt(np.diag(bread @ meat @ bread))


def test_newey_west_matches_its_matrix_form_with_and_without_gaps():
    y, x = _series()
    for months in (np.arange(len(y)), np.r_[np.arange(30), np.arange(30, len(y)) + 12]):
        ours = analysis.newey_west(y, x, months, lags=4)
        se = _newey_west_by_matrix(y, x, months, 4)
        assert ours["se_intercept"] == pytest.approx(se[0], rel=1e-10)
        assert ours["se_slope"] == pytest.approx(se[1], rel=1e-10)


def test_newey_west_matches_statsmodels_without_a_small_sample_correction():
    linear_model = pytest.importorskip("statsmodels.regression.linear_model", exc_type=ImportError)
    y, x = _series()
    ours = analysis.newey_west(y, x, np.arange(len(y)), lags=4)
    design = np.column_stack([np.ones(len(y)), x])
    fit = linear_model.OLS(y, design).fit(cov_type="HAC", cov_kwds={"maxlags": 4, "use_correction": False})
    assert ours["slope"] == pytest.approx(fit.params[1], abs=1e-12)
    assert ours["se_slope"] == pytest.approx(fit.bse[1], rel=1e-10)
    assert ours["se_intercept"] == pytest.approx(fit.bse[0], rel=1e-10)


def test_with_no_lag_newey_west_is_the_heteroskedasticity_robust_error():
    y, x = _series()
    design = np.column_stack([np.ones(len(y)), x])
    beta = np.linalg.lstsq(design, y, rcond=None)[0]
    u = y - design @ beta
    bread = np.linalg.inv(design.T @ design)
    white = bread @ (design.T * u ** 2) @ design @ bread
    ours = analysis.newey_west(y, x, np.arange(len(y)), lags=0)
    assert ours["se_slope"] == pytest.approx(math.sqrt(white[1, 1]), rel=1e-12)


def test_a_gap_in_the_months_is_not_taken_for_adjacency():
    y, x = _series()
    months = np.arange(len(y))
    months[30:] += 12  # a year left out in the middle
    gapped = analysis.newey_west(y, x, months, lags=2)
    joined = analysis.newey_west(y, x, np.arange(len(y)), lags=2)
    assert gapped["slope"] == joined["slope"]
    assert gapped["se_slope"] != joined["se_slope"]


def test_the_default_lag_rule():
    y, x = _series(n=115)
    assert analysis.newey_west(y, x, np.arange(115))["lags"] == 4
    y, x = _series(n=84)
    assert analysis.newey_west(y, x, np.arange(84))["lags"] == 3


# --------------------------------------------------------------------------
# The observations
# --------------------------------------------------------------------------

def test_the_monthly_history_and_its_gap(obs):
    monthly = obs[obs["frequency"] == "monthly"].set_index("day")
    meti = monthly[monthly["series"] == "meti_worldbank"]
    assert meti.index.min() == pd.Timestamp("2016-01-15")
    assert meti.index.max() == pd.Timestamp("2021-03-15")
    # April to August 2021: METI has ended and JOGMEC's continuation stays private.
    assert not any(pd.Timestamp(2021, m, 15) in monthly.index for m in range(4, 9))
    assert monthly.loc[pd.Timestamp("2021-09-15"), "series"] == "weekly_mean_ngwu"


def test_a_monthly_mean_is_the_mean_of_its_weeks(obs):
    weekly = obs[(obs["frequency"] == "weekly") & (obs["day"].dt.to_period("M") == pd.Period("2026-03"))]
    month = obs[(obs["frequency"] == "monthly") & (obs["day"] == pd.Timestamp("2026-03-15"))].iloc[0]
    assert month["weeks"] == len(weekly) == 4
    assert month["jkm"] == pytest.approx(weekly["jkm"].mean(), abs=1e-12)
    assert month["ttf"] == pytest.approx(weekly["ttf"].mean(), abs=1e-12)


def test_every_week_is_tagged_by_its_delivery_months(obs):
    weekly = obs[obs["frequency"] == "weekly"]
    assert set(weekly["alignment"]) <= {"aligned", "mixed", "misaligned"}
    assert weekly["alignment"].notna().all()
    assert obs[obs["frequency"] == "monthly"]["alignment"].isna().all()


def test_the_breaks_are_found_in_the_data(obs):
    found = analysis.breaks(obs)
    days = {(d.strftime("%Y-%m-%d"), kind) for d, kind in zip(found["day"], found["kind"])}
    assert ("2022-07-13", "definition") in days
    assert ("2026-01-28", "definition") in days
    assert ("2021-09-15", "definition") in days
    assert ("2024-01-02", "vessel") in days
    assert ("2024-01-13", "route") in days
    # The Supplement's one issue naming near-month futures, and back, and the
    # Weekly Update's TTF named from 29 September 2021: the levels run on.
    assert ("2026-02-25", "naming") in days and ("2026-03-04", "naming") in days
    assert ("2021-09-29", "naming") in days
    assert ("2021-11-03", "definition") in days
    # A parenthesised abbreviation added or dropped is wording, not a definition.
    assert ("2026-04-15", "definition") not in days and ("2026-08-19", "definition") not in days
    # The allowance price's changes of source follow the two caches.
    assert ("2025-07-01", "carbon") in days


def test_the_months_without_an_observation_and_why(obs):
    missing = analysis.months_without_observation(obs).set_index("month")["reason"]
    assert "METI published no" in missing[pd.Timestamp("2016-03-01")]
    assert all("no public JKM" in missing[pd.Timestamp(2021, m, 1)] for m in range(4, 9))
    assert missing[pd.Timestamp("2021-11-01")].startswith("2 weekly average")


# --------------------------------------------------------------------------
# Every observation through the engine
# --------------------------------------------------------------------------

def test_the_arb_and_the_breakeven_spread_agree_in_sign(rows):
    for route in analysis.ROUTES.values():
        open_ = rows[rows[route + "_open"] == True]  # noqa: E712
        gap = open_["spread"] - open_[route + "_s_star"]
        assert ((gap > 0) == (open_[route + "_arb"] > 0)).all()
        parts = open_[route + "_boil_off"] + open_[route + "_regas"] + open_[route + "_voyage"]
        assert np.allclose(parts, open_[route + "_s_star"], atol=1e-12)


def test_each_observation_is_worked_at_the_three_levels_and_at_a_reported_hire(rows):
    week = rows[(rows["frequency"] == "weekly") & (rows["day"] == pd.Timestamp("2026-09-30"))]
    assert sorted(week["hire_level"]) == ["central", "high", "low", "reported"]
    assert week.set_index("hire_level").loc["reported", "hire_usd_day"] == 31_500.0
    # The breakeven hire does not depend on the hire.
    assert week["panama_h_star"].nunique() == 1


def test_reading_once_puts_the_reader_back():
    original = base.read_cache
    with pytest.raises(RuntimeError):
        with analysis.reading_once():
            assert base.read_cache is not original
            raise RuntimeError("leave the block")
    assert base.read_cache is original and worked.read_cache is original


# --------------------------------------------------------------------------
# The flows
# --------------------------------------------------------------------------

def test_the_export_shares_reproduce_the_published_figures():
    shares = analysis.export_shares().set_index("month")
    vintage = set(base.read_cache("eia_lng_exports_monthly")["vintage"].astype(str))
    if vintage == {"2026-09-30"}:
        # Japan, South Korea, Taiwan and China over the LNG total of the release
        # of 31 August 2026: 4.5, 25.2 and 20.8 percent, unrevised in the next.
        assert round(100 * shares.loc[pd.Timestamp("2026-01-01"), "share_jkm"], 1) == 4.5
        assert round(100 * shares.loc[pd.Timestamp("2026-05-01"), "share_jkm"], 1) == 25.2
        assert round(100 * shares.loc[pd.Timestamp("2026-06-01"), "share_jkm"], 1) == 20.8
    # In the release of 30 September 2026, the United Kingdom's February 2024
    # figure was revised by 607 MMcf and the total was not, so the countries add
    # up to more than the total. A later release may settle it.
    noted = shares[shares["anomaly"].notna()]
    vintage = set(base.read_cache("eia_lng_exports_monthly")["vintage"].astype(str))
    if vintage == {"2026-09-30"}:
        assert noted.index.tolist() == [pd.Timestamp("2024-02-01")]
    assert ((shares["share_jkm"] >= 0) & (shares["share_jkm"] <= shares["share_asia"]) & (shares["share_asia"] <= 1)).all()


def test_the_flows_test_runs_each_share_level_and_sample(rows):
    result = analysis.flows_test(rows)
    assert len(result) == 2 * 3 * 2
    assert set(result["sample"]) == {"all months", "without 2020, 2022, 2026"}
    # The rows here are of 2026 alone, so the sample without 2026 is empty and left so.
    without = result[result["sample"] != "all months"]
    assert (without["n"] == 0).all() and without["slope"].isna().all()


# --------------------------------------------------------------------------
# 2020 and the route
# --------------------------------------------------------------------------

def test_the_notice_date_uses_what_was_published_by_then():
    margins = analysis.lift_margins_2020()
    june = margins[(margins["month"] == pd.Timestamp("2020-06-01")) & (margins["hire_level"] == "central")]
    at_notice = june[june["prices"] == "at the notice date"].iloc[0]
    # A cargo loading in June 2020 is cancelled by 20 April 2020, when METI and
    # the World Bank had published March 2020.
    assert at_notice["priced_on"] == date(2020, 4, 20)
    meti = base.read_cache("meti_spot_lng_monthly").set_index("date")["contract_based_usd_mmbtu"]
    wb = base.read_cache("worldbank_gas_monthly").set_index("date")["europe_gas_usd_mmbtu"]
    assert at_notice["jkm"] == meti[pd.Timestamp("2020-03-01")]
    assert at_notice["ttf"] == wb[pd.Timestamp("2020-03-01")]
    hh = base.read_cache("eia_henry_hub_daily")
    april = hh[(hh["date"] >= "2020-04-01") & (hh["date"] <= "2020-04-20")]["henry_hub_usd_mmbtu"].dropna()
    assert at_notice["henry_hub"] == pytest.approx(april.mean(), abs=1e-12)
    # February 2020 is cancelled by 20 December 2019, when METI's November 2019
    # price is missing: listed with the reason, not dropped.
    february = margins[(margins["month"] == pd.Timestamp("2020-02-01")) & (margins["prices"] == "at the notice date")]
    assert len(february) == 1 and "November 2019" in february.iloc[0]["note"]


def test_panama_and_the_cape_net_the_same_at_the_breakeven_wait_and_premium():
    inputs = worked.inputs_on(date(2024, 3, 27), 9.6, 8.9, {"jkm": "test", "ttf": "test"}, hire_usd_day=45_500.0)
    wait = analysis.panama_wait_breakeven(inputs)
    routes = dict(inputs.routes)
    routes["nea_panama"] = replace(routes["nea_panama"], wait_days=wait)
    out = cases.evaluate(replace(inputs, routes=routes))
    assert out["east"]["nea_panama"]["netback"] == pytest.approx(out["east"]["nea_cape"]["netback"], abs=1e-9)
    plain = cases.evaluate(inputs)
    lead = plain["east"]["nea_panama"]["netback"] - plain["east"]["nea_cape"]["netback"]
    q_load = plain["east"]["nea_panama"]["q_load_mmbtu"]
    routes = dict(inputs.routes)
    routes["nea_panama"] = replace(routes["nea_panama"], slot_premium_usd=lead * q_load)
    out = cases.evaluate(replace(inputs, routes=routes))
    assert out["east"]["nea_panama"]["netback"] == pytest.approx(out["east"]["nea_cape"]["netback"], abs=1e-9)


def test_the_reported_waits_are_applied_only_in_their_months():
    obs = analysis.observations()
    months = obs[(obs["frequency"] == "monthly") & obs["day"].isin([pd.Timestamp("2023-07-15"), pd.Timestamp("2023-12-15")])]
    rows, _ = analysis.work(months)
    waits = analysis.reported_waits(rows)
    assert set(waits["month"]) == {pd.Timestamp("2023-07-01"), pd.Timestamp("2023-12-01")}
    assert set(waits["wait_days_reported"]) == {12.0, 15.0}
    # A wait beyond the breakeven turns Panama's lead into a deficit, and the reverse.
    for r in waits.itertuples(index=False):
        assert (r.panama_minus_cape_with_wait < 0) == (r.wait_days_reported > r.wait_days_breakeven)


def test_the_reported_figures_are_kept_with_their_sources():
    from lngarb.reported import REPORTED, reported
    assert len(reported("cancellations")) == 4
    assert all(r.url.startswith("https://") and r.publisher and r.read_on for r in REPORTED)
    assert {r.period for r in reported("arb_assessment")} == {"2026-04-28"}
    assert {r.figure for r in reported("cape_use")} == {27.0, 31.0}


def test_no_wait_breakeven_while_panama_is_closed():
    inputs = worked.inputs_on(date(2016, 2, 15), 6.0, 5.0, {"jkm": "test", "ttf": "test"}, hire_usd_day=45_500.0)
    assert not inputs.routes["nea_panama"].open
    assert math.isnan(analysis.panama_wait_breakeven(inputs))

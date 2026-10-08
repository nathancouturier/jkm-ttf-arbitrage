"""One date worked through: the lines add up, closed routes are never chosen, carbon goes west only."""

from __future__ import annotations

import dataclasses
from datetime import date

import pytest

from lngarb import cases, engine
from lngarb.cases import Inputs, RouteInput

VESSEL = engine.Vessel("174k two-stroke", 174_000.0, 0.985, 0.00085, 17.0, 1.0, 1.0)


def inputs(**overrides) -> Inputs:
    base = dict(
        day=date(2026, 9, 30),
        vessel=VESSEL,
        mmbtu_per_m3=23.0,
        jkm=12.0,
        ttf=11.0,
        delta_nwe=-0.5,
        hire_usd_day=40_000.0,
        henry_hub=3.0,
        hh_multiple=1.15,
        liquefaction_fee=2.5,
        routes={
            "nwe_direct": RouteInput(4979.2),
            "nea_panama": RouteInput(9305.9, canal_laden_usd=656_700.0, canal_ballast_usd=558_195.0),
            "nea_suez": RouteInput(14624.2, open=False, why_closed="Red Sea"),
            "nea_cape": RouteInput(15824.8),
        },
        port_west_usd=308_947.0,
        port_east_usd=273_184.0,
        rate_percent=4.0,
        spread_bp=150.0,
        eua_usd_t=80.0,
        ets_phase=1.0,
        tco2_per_t_lng=2.75,
        mmbtu_per_t_lng=52.0,
    )
    base.update(overrides)
    return Inputs(**base)


def test_every_cost_line_adds_up_to_the_route_cost():
    result = cases.evaluate(inputs())
    for lines in [result["west"], *result["east"].values()]:
        parts = sum(lines[k] for k in ("hire_usd", "port_usd", "canal_laden_usd", "canal_ballast_usd",
                                       "slot_premium_usd", "ets_usd", "financing_usd"))
        assert lines["cost_usd"] == pytest.approx(parts, rel=1e-12)
        assert lines["cost_usd"] - lines["hire_usd"] == pytest.approx(lines["cost_without_hire_usd"], rel=1e-12)


def test_the_arb_is_the_spread_less_the_breakeven_scaled_by_delivered_over_loaded():
    result = cases.evaluate(inputs())
    for lines in result["east"].values():
        expected = (12.0 - 11.0 - lines["s_star"]) * lines["q_delivered_mmbtu"] / lines["q_load_mmbtu"]
        assert lines["arb"] == pytest.approx(expected, abs=1e-12)
        assert lines["boil_off"] + lines["regas"] + lines["voyage"] == pytest.approx(lines["s_star"], abs=1e-12)


def test_hire_at_the_breakeven_hire_closes_each_arb():
    first = cases.evaluate(inputs())
    for route_id, lines in first["east"].items():
        again = cases.evaluate(inputs(hire_usd_day=lines["h_star_usd_day"]))
        assert again["east"][route_id]["arb"] == pytest.approx(0.0, abs=1e-9)


def test_carbon_is_charged_on_the_european_voyage_only():
    result = cases.evaluate(inputs())
    assert result["west"]["ets_usd"] > 0
    assert all(lines["ets_usd"] == 0 for lines in result["east"].values())
    before_2024 = cases.evaluate(inputs(ets_phase=0.0))
    assert before_2024["west"]["ets_usd"] == 0


def test_financing_is_on_the_variable_price_for_the_laden_days():
    # The fixed fee, owed whether or not the cargo is lifted, is not financed.
    result = cases.evaluate(inputs())
    west = result["west"]
    fob = 1.15 * 3.0
    expected = fob * west["q_load_mmbtu"] * (4.0 + 1.5) / 100 * west["days_laden"] / 365.0
    assert west["financing_usd"] == pytest.approx(expected, rel=1e-12)


def test_each_year_of_emissions_takes_its_own_phase():
    # A cargo loaded on 20 December 2023 reaches Gate in January 2024: its berth
    # day and ballast leg are 2024 emissions, at 40 percent.
    by_year = {2023: (0.0, 2.75), 2024: (0.40, 2.75)}
    result = cases.evaluate(inputs(day=date(2023, 12, 20), ets_by_year=by_year, eua_usd_t=80.0))
    west = result["west"]
    assert west["ets_usd"] > 0
    every_day_2024 = cases.evaluate(inputs(day=date(2024, 3, 1), ets_by_year=by_year, eua_usd_t=80.0))["west"]["ets_usd"]
    assert west["ets_usd"] < every_day_2024
    # Wholly in one year, the split equals the single phase.
    single = cases.evaluate(inputs(day=date(2024, 3, 1), ets_phase=0.40, tco2_per_t_lng=2.75, eua_usd_t=80.0))
    assert every_day_2024 == pytest.approx(single["west"]["ets_usd"], rel=1e-12)


def test_a_closed_route_is_computed_but_never_chosen():
    # Make Suez the best route east by far, then close it.
    routes = dict(inputs().routes)
    routes["nea_suez"] = RouteInput(5000.0, open=False, why_closed="Red Sea")
    result = cases.evaluate(inputs(routes=routes, jkm=30.0))
    assert result["east"]["nea_suez"]["netback"] > result["east"]["nea_panama"]["netback"]
    assert result["best_route_east"] != "nea_suez"
    assert result["best_route"] != "nea_suez"


def test_the_fixed_fee_moves_no_netback_and_no_lift_margin():
    low, high = cases.evaluate(inputs(liquefaction_fee=2.25)), cases.evaluate(inputs(liquefaction_fee=3.5))
    assert low["best_netback"] == high["best_netback"]
    assert low["lift_margin"] == high["lift_margin"]
    assert low["full_margin"] - high["full_margin"] == pytest.approx(1.25, abs=1e-12)


def test_the_lift_test_never_counts_the_fixed_fee():
    result = cases.evaluate(inputs())
    assert result["lift_margin"] == pytest.approx(result["best_netback"] - 1.15 * 3.0, abs=1e-12)
    assert result["full_margin"] == pytest.approx(result["lift_margin"] - 2.5, abs=1e-12)
    assert result["cancel"] is (result["lift_margin"] < 0)


def test_with_nothing_but_prices_the_netbacks_are_the_prices():
    zero = inputs(
        hire_usd_day=0.0, delta_nwe=0.0, port_west_usd=0.0, port_east_usd=0.0, ets_phase=0.0,
        rate_percent=0.0, spread_bp=0.0,
        vessel=dataclasses.replace(VESSEL, boil_off_per_day=0.0),
        routes={k: RouteInput(v.distance_nm) for k, v in inputs().routes.items()},
    )
    result = cases.evaluate(zero)
    assert result["west"]["netback"] == pytest.approx(11.0, abs=1e-12)
    for lines in result["east"].values():
        assert lines["netback"] == pytest.approx(12.0, abs=1e-12)
        assert lines["s_star"] == pytest.approx(0.0, abs=1e-12)
        # With no other cost, the ship is worth the spread on the cargo per extra day.
        extra_days = lines["days_total"] - result["west"]["days_total"]
        assert lines["h_star_usd_day"] == pytest.approx(1.0 * lines["q_load_mmbtu"] / extra_days, rel=1e-12)

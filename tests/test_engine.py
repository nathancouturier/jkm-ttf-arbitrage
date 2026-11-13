"""The model's arithmetic: units, identities and the published figures it must reproduce."""

import json
import math
from pathlib import Path

import pytest

from arb import engine, params

CROSS = json.loads((Path(__file__).resolve().parents[1] / "data" / "params.json").read_text())["cross_checks"]


def sample(**changes) -> dict:
    """A complete cargo: the 174,000 m3 two-stroke with round prices."""
    inputs = {
        "ship": params.ship_by_id("two_stroke_174k"),
        "port_days": {"load": 1.0, "discharge": 1.0},
        "jkm": 12.0, "ttf": 11.0, "des_discount": -0.5, "henry_hub": 3.0, "hire": 45000.0,
        "carbon": {"eua_usd_t": 85.0, "phase_in": 1.0, "tco2e_per_t_lng": 3.2, "mmbtu_per_t_lng": 51.56,
                   "voyage_share": 0.5, "berth_share": 1.0},
        "finance": {"rate": 0.04, "spread": 0.015, "day_count": 360.0},
        "contract": {"hh_multiple": 1.15, "fee": 3.0},
        "routes": {
            "europe": {"market": "nwe", "distance_nm": 4979.2, "port_cost": 308947.0, "open": True},
            "panama": {"market": "nea", "distance_nm": 9305.9, "canal_days": 1.0, "wait_days": 0.0,
                       "toll_laden": 799535.0, "toll_ballast": 696105.0, "port_cost": 273184.0, "open": True},
            "suez": {"market": "nea", "distance_nm": 14624.2, "canal_days": 1.0, "wait_days": 0.0,
                     "toll_laden": 342000.0, "toll_ballast": 291000.0, "port_cost": 273184.0, "open": False},
            "cape": {"market": "nea", "distance_nm": 15824.8, "port_cost": 273184.0, "open": True},
        },
    }
    inputs.update(changes)
    return inputs


# -- units and volumes --------------------------------------------------------

def test_ttf_in_dollars():
    assert engine.eur_mwh_to_usd_mmbtu(30.0, 1.10) == pytest.approx(9.671344, abs=5e-7)
    assert engine.usd_mmbtu_to_eur_mwh(9.671344, 1.10) == pytest.approx(30.0, abs=1e-5)


def test_the_benchmark_ship_loads_and_boils_off_what_spark_states():
    v = engine.voyage(params.ship_by_id("two_stroke_174k"), {"distance_nm": 4979.2}, {"load": 1.0, "discharge": 1.0})
    assert v["loaded"] == pytest.approx(3_941_970.0)
    assert v["boil_off_per_day"] == pytest.approx(3_350.6745)
    assert v["round_trip_days"] == pytest.approx(2 * 4979.2 / (17 * 24) + 2)
    assert v["delivered"] == pytest.approx(v["loaded"] - v["boil_off_per_day"] * v["round_trip_days"])


def test_the_ship_changes_with_the_freight_benchmark():
    assert params.ship_on("2024-01-01")["capacity_m3"] == 160_000
    assert params.ship_on("2024-01-02")["capacity_m3"] == 174_000
    assert params.ship_on("2024-01-02")["boil_off"] == 0.00085


# -- canal tariffs --------------------------------------------------------------

def test_panama_tolls_for_the_benchmark_ship():
    assert params.panama_toll("2025-01-01", 174_000) == pytest.approx((656_700.0, 558_195.0))
    assert params.panama_toll("2026-11-04", 174_000) == pytest.approx((656_700.0, 558_195.0))
    assert params.panama_toll("2024-06-01", 174_000) == pytest.approx((595_800.0, 506_430.0))
    # the Authority's worked example for the 2016 bands
    assert params.panama_toll("2016-07-01", 174_000)[0] == pytest.approx(382_440.0)
    booked = params.panama_charges("2026-11-04", 174_000)
    assert booked["laden"] == pytest.approx(656_700 * 1.05 + 10_000 + 100_000)


def test_suez_toll_applies_surcharge_and_rebate_to_normal_dues():
    s = params.suez_charges("2026-11-04", 174_000, 1.35)
    assert s["scnt"] == pytest.approx(102_000, rel=1e-6)
    assert s["laden_sdr"] == pytest.approx(575_950 * (1 + 0.19 - 0.75))
    assert s["ballast"] < s["laden"]


# -- identities -------------------------------------------------------------------

def test_no_costs_and_no_boil_off_give_the_price():
    free = sample(hire=0.0, des_discount=0.0, henry_hub=0.0)
    free["ship"] = dict(free["ship"], boil_off=0.0)
    free["carbon"] = dict(free["carbon"], eua_usd_t=0.0)
    for route in free["routes"].values():
        route.update(port_cost=0.0, toll_laden=0.0, toll_ballast=0.0)
    out = engine.price_cargo(free)["routes"]
    assert out["europe"]["netback"] == pytest.approx(11.0)
    for rid in ("panama", "suez", "cape"):
        assert out[rid]["netback"] == pytest.approx(12.0)
        assert out[rid]["breakeven_spread"] == pytest.approx(0.0, abs=1e-12)


@pytest.mark.parametrize("route", ["panama", "suez", "cape"])
def test_the_breakeven_spread_and_the_breakeven_hire_close_the_arb(route):
    base = sample()
    r = engine.price_cargo(base)["routes"][route]
    at_spread = engine.price_cargo(sample(jkm=base["ttf"] + r["breakeven_spread"]))["routes"]
    assert at_spread[route]["netback"] == pytest.approx(at_spread["europe"]["netback"], abs=1e-9)
    at_hire = engine.price_cargo(sample(hire=r["breakeven_hire"]))["routes"]
    assert at_hire[route]["netback"] == pytest.approx(at_hire["europe"]["netback"], abs=1e-9)


@pytest.mark.parametrize("route", ["panama", "suez", "cape"])
def test_the_drivers_add_up_and_the_arb_follows_the_spread(route):
    out = engine.price_cargo(sample())
    r = out["routes"][route]
    assert sum(r["drivers"].values()) == pytest.approx(r["breakeven_spread"], abs=1e-12)
    assert r["drivers"]["des_discount"] == -0.5
    assert r["arb"] == pytest.approx((out["spread"] - r["breakeven_spread"]) * r["delivered"] / r["loaded"], abs=1e-12)


def test_the_breakeven_is_a_straight_line_in_hire():
    base = sample()
    a, b = engine.breakeven_line(base, "cape")
    for hire in (0.0, 31_500.0, 120_000.0):
        s = engine.price_cargo(sample(hire=hire))["routes"]["cape"]["breakeven_spread"]
        assert s == pytest.approx(a + b * hire, abs=1e-12)
    assert b > engine.breakeven_line(base, "panama")[1] > 0


def test_a_longer_voyage_a_dearer_ship_and_dearer_gas_raise_the_breakeven():
    base = engine.price_cargo(sample())["routes"]
    assert base["cape"]["breakeven_spread"] > base["panama"]["breakeven_spread"]
    dearer_gas = engine.price_cargo(sample(ttf=30.0, jkm=31.0))["routes"]
    assert dearer_gas["cape"]["drivers"]["boil_off"] > 2.5 * base["cape"]["drivers"]["boil_off"]
    wider_discount = engine.price_cargo(sample(des_discount=-1.5))["routes"]
    assert wider_discount["panama"]["breakeven_spread"] < base["panama"]["breakeven_spread"] - 0.9


def test_only_the_european_voyage_pays_for_carbon():
    out = engine.price_cargo(sample())["routes"]
    assert out["europe"]["cost"]["carbon"] > 0
    assert out["panama"]["cost"]["carbon"] == out["cape"]["cost"]["carbon"] == 0.0
    v = out["europe"]
    days = 0.5 * (v["round_trip_days"] - 2) + 1.0
    assert v["cost"]["carbon"] == pytest.approx(85.0 * 3.2 * v["boil_off_per_day"] / 51.56 * days)


def test_the_lift_test_ignores_the_fixed_fee():
    out = engine.price_cargo(sample())
    lift = out["lift"]
    assert lift["threshold"] == pytest.approx(3.45)
    assert lift["margin"] == pytest.approx(out["routes"][out["best"]]["netback"] - 3.45)
    assert lift["margin_after_fee"] == pytest.approx(lift["margin"] - 3.0)
    assert lift["lifts"] is True
    assert engine.price_cargo(sample(jkm=2.0, ttf=1.6))["lift"]["lifts"] is False


def test_a_closed_route_is_priced_and_never_chosen():
    out = engine.price_cargo(sample(jkm=11.6))
    assert math.isfinite(out["routes"]["suez"]["netback"])
    assert out["best_east"] in ("panama", "cape")
    shut = sample()
    for rid in ("panama", "suez", "cape"):
        shut["routes"][rid]["open"] = False
    assert engine.price_cargo(shut)["best"] == "europe" and engine.price_cargo(shut)["best_east"] is None


def test_the_canal_question_is_exact():
    base = sample()
    q = engine.canal_question(base)
    paid = engine.with_route(base, "panama", toll_laden=base["routes"]["panama"]["toll_laden"] + q["premium_usd"])
    r = engine.price_cargo(paid)["routes"]
    assert r["panama"]["netback"] == pytest.approx(r["cape"]["netback"], abs=1e-9)
    waited = engine.price_cargo(engine.with_route(base, "panama", wait_days=q["wait_days"]))["routes"]
    assert waited["panama"]["netback"] == pytest.approx(waited["cape"]["netback"], abs=1e-9)


# -- Spark's worked freight example -----------------------------------------------

def test_sparks_worked_example_within_a_dollar():
    x = CROSS["spark_example"]
    fuel_day = 160_000 * 0.985 * 0.001 * 23 * x["fuel_price_usd_mmbtu"]
    full = engine.spark_rate(x["hire_usd_day"], x["laden_days"], x["ballast_days"], fuel_day)
    assert abs(full["ballast_fuel"] - x["ballast_fuel_usd"]) < 1
    assert abs(full["laden_fuel"] - x["laden_fuel_usd"]) < 1
    assert abs(full["charterer_payment"] - x["full_ballast_bonus"]["charterer_payment_usd"]) < 1
    assert full["rate"] == pytest.approx(x["full_ballast_bonus"]["spark_rate_usd_day"])

    half = engine.spark_rate(x["hire_usd_day"], x["laden_days"], x["ballast_days"], fuel_day, ballast_bonus_share=0.5)
    assert abs(half["ballast_bonus"] - x["half_ballast_bonus"]["ballast_bonus_usd"]) < 1
    assert abs(half["charterer_payment"] - x["half_ballast_bonus"]["charterer_payment_usd"]) < 1
    # Spark prints -751.23, computed from its lines rounded to the dollar; unrounded it is -751.26.
    assert half["rate"] == pytest.approx(x["half_ballast_bonus"]["spark_rate_usd_day"], abs=0.05)
    assert half["rate_rounded"] == x["half_ballast_bonus"]["spark_rate_rounded"]
    total = half["charterer_payment"] + x["port_cost_usd"] + half["laden_fuel"]
    assert abs(total - x["half_ballast_bonus"]["total_cost_usd"]) < 1
    assert round(total / x["half_ballast_bonus"]["discharge_mmbtu"], 2) == x["half_ballast_bonus"]["freight_usd_mmbtu"]

    fee = engine.spark_rate(x["hire_usd_day"], x["laden_days"], x["ballast_days"], fuel_day,
                            positioning_fee=x["positioning_fee"]["fee_usd"])
    assert abs(fee["charterer_payment"] - x["positioning_fee"]["charterer_payment_usd"]) < 1
    assert fee["rate_rounded"] == x["positioning_fee"]["spark_rate_rounded"]


def test_the_model_costs_sparks_voyage_as_spark_does():
    """Round-trip hire at Spark's rate plus the gas burnt at the fuel price is Spark's total."""
    x = CROSS["spark_example"]
    fuel_day = 160_000 * 0.985 * 0.001 * 23 * x["fuel_price_usd_mmbtu"]
    half = engine.spark_rate(x["hire_usd_day"], x["laden_days"], x["ballast_days"], fuel_day, ballast_bonus_share=0.5)
    ship = params.ship_by_id("tfde_160k")
    assert ship["capacity_m3"] * ship["fill"] * ship["mmbtu_per_m3"] * ship["boil_off"] * x["fuel_price_usd_mmbtu"] == pytest.approx(fuel_day)
    ours = half["rate"] * x["round_trip_days"] + x["port_cost_usd"] + fuel_day * x["round_trip_days"]
    assert abs(ours - x["half_ballast_bonus"]["total_cost_usd"]) < 1

"""The engine's arithmetic, pinned by constructions whose answers are known.

Each test is one of the checks docs/methodology.md lists for the engine. The
vessels and prices here are test inputs, not the study's parameters: the
parameters, with their sources, are in lngarb.config.
"""

from __future__ import annotations

import math

import pytest

from lngarb import engine
from lngarb.engine import CostStack, Leg, Vessel, Voyage

K = 23.0  # MMBtu per m3, the convention the freight benchmarks use

TWO_STROKE = Vessel("174k two-stroke", 174_000, 0.985, 0.00085, 17, 1, 1)
TFDE = Vessel("160k TFDE", 160_000, 0.985, 0.001, 17, 1, 1)


def voyage(distance, vessel=TWO_STROKE, **kw):
    return Voyage(vessel, Leg(distance), Leg(distance), K, **kw)


# --------------------------------------------------------------------------
# Volumes
# --------------------------------------------------------------------------

def test_volumes_and_the_boil_off_basis():
    v = voyage(5_000)
    assert v.q_load == pytest.approx(3_941_970, abs=1e-6)
    assert v.boil_off_per_day == pytest.approx(3_350.6745, abs=1e-9)


def test_days_and_gas_used_follow_distance_speed_and_port_days():
    v = Voyage(TWO_STROKE, Leg(4_080, canal_days=1, wait_days=2), Leg(4_080), K, flex_days=3)
    assert v.sea_days(v.laden) == pytest.approx(10.0)
    assert v.t_laden == pytest.approx(10 + 1 + 2 + 1 + 1 + 3)
    assert v.t_ballast == pytest.approx(10.0)
    assert v.gas_used == pytest.approx(v.boil_off_per_day * 28.0)
    assert v.q_delivered == pytest.approx(v.q_load - v.gas_used)


# --------------------------------------------------------------------------
# Null, symmetry, linearity, round trip, parts, convention, monotonicity
# --------------------------------------------------------------------------

FREE = Vessel("free", 174_000, 0.985, 0.0, 17, 1, 1)


def test_null_costs_return_the_hub_prices_and_a_zero_breakeven():
    west, east = voyage(5_000, FREE), voyage(9_000, FREE)
    assert engine.netback(11.0, west, 0.0) == pytest.approx(11.0)
    assert engine.netback(12.5, east, 0.0) == pytest.approx(12.5)
    assert engine.breakeven_spread(11.0, 0.0, west, 0.0, east, 0.0)["s_star"] == pytest.approx(0.0, abs=1e-12)


def test_symmetric_voyages_break_even_at_the_regas_discount():
    west = east = voyage(5_000)
    s = engine.breakeven_spread(11.0, -0.6, west, 2.0e6, east, 2.0e6)
    assert s["s_star"] == pytest.approx(-0.6, abs=1e-12)


def test_netback_and_breakeven_are_linear_in_hire():
    west, east = voyage(5_000), voyage(9_300)
    costs = CostStack(port=300_000, canal_laden=650_000)
    h1, h2 = 40_000.0, 41_000.0
    nb1 = engine.netback(12.0, east, engine.voyage_cost(h1, east, costs))
    nb2 = engine.netback(12.0, east, engine.voyage_cost(h2, east, costs))
    assert (nb2 - nb1) / (h2 - h1) == pytest.approx(-east.t_total / east.q_load, rel=1e-12)

    def s_star(h):
        return engine.breakeven_spread(
            11.0, -0.5,
            west, engine.voyage_cost(h, west, CostStack(port=300_000)),
            east, engine.voyage_cost(h, east, costs),
        )["s_star"]

    slope = (s_star(h2) - s_star(h1)) / (h2 - h1)
    assert slope == pytest.approx((east.t_total - west.t_total) / east.q_delivered, rel=1e-9)


def test_jkm_at_ttf_plus_the_breakeven_and_hire_at_the_breakeven_hire_both_close_the_arb():
    west, east = voyage(5_000), voyage(9_300)
    cw, ce = CostStack(port=300_000), CostStack(port=280_000, canal_laden=650_000, canal_ballast=550_000)
    ttf, delta, hire = 11.0, -0.5, 45_000.0
    cost_w, cost_e = engine.voyage_cost(hire, west, cw), engine.voyage_cost(hire, east, ce)
    s_star = engine.breakeven_spread(ttf, delta, west, cost_w, east, cost_e)["s_star"]
    jkm = ttf + s_star
    arb = engine.netback(jkm, east, cost_e) - engine.netback(ttf + delta, west, cost_w)
    assert arb == pytest.approx(0.0, abs=1e-9)

    jkm = 13.0
    h_star = engine.breakeven_hire(jkm, ttf, delta, west, cw, east, ce)
    arb = (engine.netback(jkm, east, engine.voyage_cost(h_star, east, ce))
           - engine.netback(ttf + delta, west, engine.voyage_cost(h_star, west, cw)))
    assert arb == pytest.approx(0.0, abs=1e-9)


def test_the_three_parts_add_up_to_the_breakeven():
    west, east = voyage(5_000), voyage(15_800)
    s = engine.breakeven_spread(14.0, -0.7, west, 2.1e6, east, 4.4e6)
    assert s["boil_off"] + s["regas"] + s["voyage"] == pytest.approx(s["s_star"], abs=1e-12)


def test_the_conventional_netback_differs_by_the_second_order_term():
    v = voyage(9_300)
    p, c = 12.0, 3.5e6
    nb = engine.netback(p, v, c)
    _, nb_conv = engine.conventional_netback(p, p, v, c)
    g, ql, qd = v.gas_used, v.q_load, v.q_delivered
    assert nb - nb_conv == pytest.approx(g * (p * g + c) / (ql * qd), abs=1e-9)


@pytest.mark.parametrize("change", ["hire", "boil_off", "distance", "delta"])
def test_the_breakeven_moves_the_right_way(change):
    def s_star(hire=40_000.0, bor=0.00085, distance=9_300.0, delta=-0.5):
        vessel = Vessel("v", 174_000, 0.985, bor, 17, 1, 1)
        west, east = voyage(5_000, vessel), voyage(distance, vessel)
        cw = engine.voyage_cost(hire, west, CostStack(port=300_000))
        ce = engine.voyage_cost(hire, east, CostStack(port=280_000))
        return engine.breakeven_spread(11.0, delta, west, cw, east, ce)["s_star"]

    base_value = s_star()
    if change == "hire":
        assert s_star(hire=50_000.0) > base_value
    elif change == "boil_off":
        assert s_star(bor=0.0012) > base_value
    elif change == "distance":
        assert s_star(distance=15_800.0) > base_value
    else:
        assert s_star(delta=-1.5) < base_value


def test_a_breakeven_hire_between_voyages_of_equal_length_is_not_a_number():
    v = voyage(5_000)
    assert math.isnan(engine.breakeven_hire(12.0, 11.0, 0.0, v, CostStack(), v, CostStack()))


# --------------------------------------------------------------------------
# Lift, carbon, financing
# --------------------------------------------------------------------------

def test_the_fixed_fee_never_decides_the_lift():
    out = engine.lift_test(4.0, 3.0, 2.5, hh_multiple=1.15)
    assert out["lift_margin"] == pytest.approx(0.55)
    assert out["full_margin"] == pytest.approx(-1.95)
    assert out["cancel"] is False
    assert engine.lift_test(3.0, 3.0, 0.0, hh_multiple=1.15)["cancel"] is True


def test_carbon_counts_the_voyages_at_their_share_and_the_berth_in_full():
    kw = dict(eua_usd_per_t=80.0, tco2_per_t_lng=2.75, mmbtu_per_t_lng=52.0,
              boil_off_mmbtu_per_day=3_350.0, voyage_share=0.5, berth_share=1.0)
    full = engine.ets_cost(phase_in=1.0, laden_days=12, ballast_days=12, berth_days=1, **kw)
    expected = 80.0 * 2.75 * 3_350.0 * (0.5 * 24 + 1.0 * 1) / 52.0
    assert full == pytest.approx(expected)
    assert engine.ets_cost(phase_in=0.4, laden_days=12, ballast_days=12, berth_days=1, **kw) == pytest.approx(0.4 * expected)
    assert engine.ets_cost(phase_in=0.0, laden_days=12, ballast_days=12, berth_days=1, **kw) == 0.0
    berth_only = engine.ets_cost(phase_in=1.0, laden_days=0, ballast_days=0, berth_days=1, **kw)
    assert berth_only == pytest.approx(80.0 * 2.75 * 3_350.0 / 52.0)


def test_financing_is_interest_on_the_fob_cost_for_the_days_carried():
    cost = engine.financing_cost(fob_usd_per_mmbtu=5.0, q_load=3_941_970, rate_percent=4.0, spread_bp=150, days=20)
    assert cost == pytest.approx(5.0 * 3_941_970 * 0.055 * 20 / 365)


# --------------------------------------------------------------------------
# Spark's worked example, from its note on negative freight rates
# --------------------------------------------------------------------------

def spark_inputs():
    fuel_per_day = 160_000 * 0.985 * 0.001 * 23 * 26.679
    return fuel_per_day, 12.5 * fuel_per_day, 17.5 * fuel_per_day


def test_spark_example_1_full_ballast_bonus():
    _, ballast_fuel, _ = spark_inputs()
    out = engine.spark_charterer_payment(hire_usd_day=24_500, laden_days=17.5, ballast_days=12.5,
                                         ballast_share_of_hire=1.0, ballast_share_of_fuel=1.0,
                                         ballast_fuel_usd=ballast_fuel)
    assert abs(ballast_fuel - 1_208_825) < 1
    assert out["hire"] == pytest.approx(428_750)
    assert abs(out["ballast_bonus"] - 1_515_075) < 1
    assert abs(out["charterer_payment"] - 1_943_825) < 1
    rate = engine.spark_rate(1_943_825, 1_208_825, 30)
    assert engine.spark_round(rate, 250) == 24_500


def test_spark_example_2_half_ballast_bonus_gives_minus_750():
    _, ballast_fuel, laden_fuel = spark_inputs()
    out = engine.spark_charterer_payment(hire_usd_day=24_500, laden_days=17.5, ballast_days=12.5,
                                         ballast_share_of_hire=0.5, ballast_share_of_fuel=0.5,
                                         ballast_fuel_usd=ballast_fuel)
    assert abs(out["ballast_bonus"] - 757_538) < 1
    assert abs(out["charterer_payment"] - 1_186_288) < 1
    rate = engine.spark_rate(1_186_288, 1_208_825, 30)
    assert rate == pytest.approx(-751.23, abs=0.01)
    assert engine.spark_round(rate, 250) == -750
    assert abs(laden_fuel - 1_692_355) < 1
    total = out["charterer_payment"] + 308_947 + laden_fuel
    assert abs(total - 3_187_591) < 1
    # The printed total is the sum of its printed parts with the laden fuel rounded.
    assert 1_186_288 + 308_947 + round(laden_fuel) == 3_187_591
    assert round(3_187_591 / 3_501_428, 2) == 0.91


def test_spark_example_3_positioning_fee_and_the_rounding_step():
    _, ballast_fuel, _ = spark_inputs()
    out = engine.spark_charterer_payment(hire_usd_day=24_500, laden_days=17.5, ballast_days=12.5,
                                         ballast_share_of_hire=1.0, ballast_share_of_fuel=1.0,
                                         ballast_fuel_usd=ballast_fuel, positioning_usd=500_000)
    assert abs(out["charterer_payment"] - 2_443_825) < 1
    assert engine.spark_round(engine.spark_rate(2_443_825, 1_208_825, 30), 250) == 41_250


def test_spark_discharge_volume_follows_its_2022_definition_with_fifteen_laden_days():
    loaded = 160_000 * 0.985 * 23
    per_day = loaded * 0.001
    assert loaded - 15 * per_day - 3_000 * 23 == pytest.approx(3_501_428, abs=1e-6)


def test_days_at_sea_typed_directly_win_over_the_distance():
    vessel = engine.Vessel("test", 160_000, 0.985, 0.001, 19.5, 1.0, 1.0)
    typed = engine.Voyage(vessel, laden=engine.Leg(9_000.0, sea_days=15.5), ballast=engine.Leg(9_000.0, sea_days=12.5),
                          mmbtu_per_m3=23.0)
    assert typed.t_laden == pytest.approx(15.5 + 2.0)
    assert typed.t_ballast == pytest.approx(12.5)
    computed = engine.Voyage(vessel, laden=engine.Leg(9_000.0), ballast=engine.Leg(9_000.0), mmbtu_per_m3=23.0)
    assert computed.t_ballast == pytest.approx(9_000.0 / (19.5 * 24))

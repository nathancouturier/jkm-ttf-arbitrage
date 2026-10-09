"""The cargo economics: volumes, voyage days, the cost stack, netbacks and breakevens.

Every function here is pure arithmetic on the inputs it is given. No number
that is a market price, a tariff or an assumption lives in this module: those
are named parameters in lngarb.config, each with its source, and data series in
data/. docs/methodology.md, sections 9 to 11, states every formula below in
words and gives the tests that pin it.

Units throughout: volumes in MMBtu, prices in USD per MMBtu, costs in USD,
durations in days, distances in nautical miles, speeds in knots.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping

__all__ = [
    "Vessel",
    "Leg",
    "Voyage",
    "CostStack",
    "voyage_cost",
    "netback",
    "conventional_netback",
    "breakeven_spread",
    "breakeven_hire",
    "lift_test",
    "ets_cost",
    "financing_cost",
    "spark_charterer_payment",
    "spark_rate",
    "spark_round",
]

HOURS_PER_DAY = 24.0
DAYS_PER_YEAR_FOR_INTEREST = 365.0


@dataclass(frozen=True)
class Vessel:
    """An LNG carrier as the freight benchmarks describe it."""

    name: str
    #: cargo tank capacity, m3
    capacity_m3: float
    #: share of capacity loaded
    fill: float
    #: boil-off, share of the loaded volume per day, on laden and ballast days alike
    boil_off_per_day: float
    #: knots
    speed_kn: float
    load_days: float
    discharge_days: float


@dataclass(frozen=True)
class Leg:
    """One direction of a voyage: the sea distance and any time not at sea."""

    distance_nm: float
    canal_days: float = 0.0
    wait_days: float = 0.0
    #: days at sea typed directly, used instead of the distance over the speed
    sea_days: float | None = None


@dataclass(frozen=True)
class Voyage:
    """A round trip: laden from the load port, ballast back to it."""

    vessel: Vessel
    laden: Leg
    ballast: Leg
    mmbtu_per_m3: float
    flex_days: float = 0.0

    @property
    def q_load(self) -> float:
        """MMBtu loaded."""
        v = self.vessel
        return v.capacity_m3 * v.fill * self.mmbtu_per_m3

    @property
    def boil_off_per_day(self) -> float:
        """MMBtu boiled off or burnt per day, laden and ballast alike."""
        return self.q_load * self.vessel.boil_off_per_day

    def sea_days(self, leg: Leg) -> float:
        if leg.sea_days is not None:
            return leg.sea_days
        return leg.distance_nm / (self.vessel.speed_kn * HOURS_PER_DAY)

    @property
    def t_laden(self) -> float:
        v = self.vessel
        return (self.sea_days(self.laden) + self.laden.canal_days + self.laden.wait_days
                + v.load_days + v.discharge_days + self.flex_days)

    @property
    def t_ballast(self) -> float:
        return self.sea_days(self.ballast) + self.ballast.canal_days + self.ballast.wait_days

    @property
    def t_total(self) -> float:
        return self.t_laden + self.t_ballast

    @property
    def gas_used(self) -> float:
        """MMBtu boiled off or burnt over the round trip, G."""
        return self.boil_off_per_day * self.t_total

    @property
    def q_delivered(self) -> float:
        """MMBtu delivered: loaded less the round trip's gas, the ballast heel staying aboard."""
        return self.q_load - self.gas_used


@dataclass(frozen=True)
class CostStack:
    """Every voyage cost in USD except hire, which scales with days."""

    port: float = 0.0
    canal_laden: float = 0.0
    canal_ballast: float = 0.0
    slot_premium: float = 0.0
    ets: float = 0.0
    financing: float = 0.0

    @property
    def without_hire(self) -> float:
        """C0, the cost stack less hire."""
        return (self.port + self.canal_laden + self.canal_ballast + self.slot_premium
                + self.ets + self.financing)

    def lines(self) -> Mapping[str, float]:
        return {
            "port": self.port,
            "canal_laden": self.canal_laden,
            "canal_ballast": self.canal_ballast,
            "slot_premium": self.slot_premium,
            "ets": self.ets,
            "financing": self.financing,
        }


def voyage_cost(hire_usd_day: float, voyage: Voyage, costs: CostStack) -> float:
    """C = hire x T_total + C0, in USD. Hire runs for the whole round trip."""
    return hire_usd_day * voyage.t_total + costs.without_hire


def netback(p_des: float, voyage: Voyage, cost_usd: float) -> float:
    """NB = (P_des x Q_del - C) / Q_load, USD per MMBtu loaded at the load port.

    The gas used on the way is not sold, so it is valued at the delivered price
    without a separate fuel line.
    """
    return (p_des * voyage.q_delivered - cost_usd) / voyage.q_load


def conventional_netback(p_des: float, p_ref: float, voyage: Voyage, cost_usd: float) -> tuple[float, float]:
    """The market's quoting convention: freight per delivered MMBtu, fuel valued at p_ref.

    Returns (F_conv, NB_conv) with F_conv = (C + p_ref x G) / Q_del and
    NB_conv = P_des - F_conv.
    """
    f_conv = (cost_usd + p_ref * voyage.gas_used) / voyage.q_delivered
    return f_conv, p_des - f_conv


def breakeven_spread(
    ttf: float,
    delta_nwe: float,
    west: Voyage,
    cost_west: float,
    east: Voyage,
    cost_east: float,
) -> dict[str, float]:
    """The JKM - TTF spread at which a cargo east and a cargo west net back the same.

    S* = (TTF + delta) Q_del(W) / Q_del(E) + (C(E) - C(W)) / Q_del(E) - TTF, and its
    three parts: boil-off, regas and voyage. The same vessel loads both, so
    Q_load cancels.
    """
    qw, qe = west.q_delivered, east.q_delivered
    boil_off = ttf * (qw / qe - 1.0)
    regas = delta_nwe * qw / qe
    voyage = (cost_east - cost_west) / qe
    total = (ttf + delta_nwe) * qw / qe + (cost_east - cost_west) / qe - ttf
    return {"s_star": total, "boil_off": boil_off, "regas": regas, "voyage": voyage}


def breakeven_hire(
    jkm: float,
    ttf: float,
    delta_nwe: float,
    west: Voyage,
    costs_west: CostStack,
    east: Voyage,
    costs_east: CostStack,
) -> float:
    """The hire at which east and west net back the same, USD per day.

    H* = [JKM Q_del(E) - (TTF + delta) Q_del(W) - (C0(E) - C0(W))] / (T(E) - T(W)).
    A negative H* means the route east does not pay even with a free ship.
    NaN when the two voyages take the same time, where no hire separates them.
    """
    days = east.t_total - west.t_total
    if days == 0:
        return math.nan
    return (jkm * east.q_delivered - (ttf + delta_nwe) * west.q_delivered
            - (costs_east.without_hire - costs_west.without_hire)) / days


def lift_test(best_netback: float, henry_hub: float, liquefaction_fee: float, *, hh_multiple: float) -> dict[str, float | bool]:
    """The US lift decision. The fixed fee is sunk, so it never decides.

    lift_margin = best_netback - multiple x HH; full_margin also deducts the fee;
    the cargo is cancelled when lift_margin is negative.
    """
    lift = best_netback - hh_multiple * henry_hub
    return {
        "lift_margin": lift,
        "full_margin": lift - liquefaction_fee,
        "cancel": lift < 0,
    }


def ets_cost(
    *,
    eua_usd_per_t: float,
    phase_in: float,
    tco2_per_t_lng: float,
    mmbtu_per_t_lng: float,
    boil_off_mmbtu_per_day: float,
    laden_days: float,
    ballast_days: float,
    berth_days: float,
    voyage_share: float,
    berth_share: float,
) -> float:
    """EU ETS cost of a voyage to or from an EU port, USD.

    Tonnes of LNG burnt are boil-off days over MMBtu per tonne; the voyage into
    the EU port and the ballast leg out of it count at voyage_share, the time at
    berth in the EU port at berth_share, and the whole is scaled by the year's
    phase-in share.
    """
    weighted_days = voyage_share * (laden_days + ballast_days) + berth_share * berth_days
    tonnes_lng = boil_off_mmbtu_per_day * weighted_days / mmbtu_per_t_lng
    return eua_usd_per_t * phase_in * tco2_per_t_lng * tonnes_lng


def financing_cost(*, fob_usd_per_mmbtu: float, q_load: float, rate_percent: float, spread_bp: float, days: float) -> float:
    """Interest on the FOB purchase cost of the cargo for the days it is carried, USD.

    The rate is a percentage per year plus a spread in basis points, on an
    actual over 365 day basis, the convention of the study's copper sibling.
    """
    rate = (rate_percent + spread_bp / 100.0) / 100.0
    return fob_usd_per_mmbtu * q_load * rate * days / DAYS_PER_YEAR_FOR_INTEREST


# --------------------------------------------------------------------------
# Spark's freight assessment, as its note on negative rates works it through
# --------------------------------------------------------------------------

def spark_charterer_payment(
    *,
    hire_usd_day: float,
    laden_days: float,
    ballast_days: float,
    ballast_share_of_hire: float,
    ballast_share_of_fuel: float,
    ballast_fuel_usd: float,
    positioning_usd: float = 0.0,
) -> dict[str, float]:
    """Spark's charterer payment: hire for the laden days, the ballast bonus, the positioning fee."""
    hire = laden_days * hire_usd_day
    bonus = ballast_days * hire_usd_day * ballast_share_of_hire + ballast_fuel_usd * ballast_share_of_fuel
    return {"hire": hire, "ballast_bonus": bonus, "positioning": positioning_usd,
            "charterer_payment": hire + bonus + positioning_usd}


def spark_rate(charterer_payment: float, ballast_fuel_usd: float, duration_days: float) -> float:
    """Spark's rate before rounding: (charterer payment - ballast fuel) / duration."""
    return (charterer_payment - ballast_fuel_usd) / duration_days


def spark_round(rate_usd_day: float, step: float) -> float:
    """Spark publishes its rate rounded to the nearest step, half away from zero."""
    return math.copysign(math.floor(abs(rate_usd_day) / step + 0.5) * step, rate_usd_day)

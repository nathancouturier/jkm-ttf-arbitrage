"""One loading date worked through: every line of the cost stack east and west, and the result.

evaluate() takes every input of one date explicitly, prices, hire, tolls,
carbon, financing and the routes open that day, and returns every line the
engine computes from them: days, volumes, each cost, the netback per
destination and route, the arb, the breakeven spread and its three parts, the
breakeven hire and the lift test. It is pure arithmetic over lngarb.engine;
where the inputs of a date come from is lngarb.worked's business, so that the
same arithmetic serves a worked date, a test and the Model view's presets.

Units: prices in USD per MMBtu, costs in USD, hire in USD per day, days in days,
volumes in MMBtu.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Mapping

from . import engine
from .engine import CostStack, Leg, Vessel, Voyage

__all__ = ["WEST", "EAST", "RouteInput", "Inputs", "evaluate"]

#: The route to Northwest Europe and the three to Northeast Asia, as the routes seed names them.
WEST = "nwe_direct"
EAST = ("nea_panama", "nea_suez", "nea_cape")


@dataclass(frozen=True)
class RouteInput:
    """What one route needs on the day: whether it is open, how far, and its canal charges."""

    distance_nm: float
    open: bool = True
    why_closed: str = ""
    canal_laden_usd: float = 0.0
    canal_ballast_usd: float = 0.0
    canal_days: float = 0.0
    wait_days: float = 0.0
    slot_premium_usd: float = 0.0
    #: what the canal charges are made of, for the table
    canal_note: str = ""


@dataclass(frozen=True)
class Inputs:
    """Every input of one loading date."""

    day: date
    vessel: Vessel
    mmbtu_per_m3: float
    jkm: float
    ttf: float
    #: the DES discount in Northwest Europe, USD per MMBtu, zero or negative
    delta_nwe: float
    hire_usd_day: float
    henry_hub: float
    hh_multiple: float
    liquefaction_fee: float
    routes: Mapping[str, RouteInput]
    port_west_usd: float
    port_east_usd: float
    #: overnight rate, percent per year, and the spread over it in basis points
    rate_percent: float
    spread_bp: float
    #: EU ETS on the voyage to Northwest Europe; a phase of zero means not covered.
    #: ets_by_year, when given, maps a calendar year to (phase, t CO2e per t of
    #: LNG) and the emissions of each day are priced under their own year; the
    #: two scalars apply otherwise.
    eua_usd_t: float = 0.0
    ets_phase: float = 0.0
    tco2_per_t_lng: float = 0.0
    ets_by_year: Mapping[int, tuple[float, float]] | None = None
    mmbtu_per_t_lng: float = 1.0
    ets_voyage_share: float = 0.5
    ets_berth_share: float = 1.0
    #: labels shown beside the numbers, input by input
    sources: Mapping[str, str] = field(default_factory=dict)


def _voyage(inputs: Inputs, route: RouteInput) -> Voyage:
    leg = Leg(route.distance_nm, canal_days=route.canal_days, wait_days=route.wait_days)
    return Voyage(inputs.vessel, laden=leg, ballast=leg, mmbtu_per_m3=inputs.mmbtu_per_m3)


def _year_days(start: float, end: float, day: date) -> dict[int, float]:
    """The days between start and end, counted from the loading day, split by calendar year."""
    out: dict[int, float] = {}
    t = start
    while t < end:
        when = day + timedelta(days=t)
        next_year = (date(when.year + 1, 1, 1) - day).days
        stop = min(end, float(next_year))
        out[when.year] = out.get(when.year, 0.0) + (stop - t)
        t = stop
    return out


def _ets(inputs: Inputs, voyage: Voyage, *, to_europe: bool) -> float:
    """EU ETS on one round trip: the voyages into and out of the EU port at their share, berth in full.

    The load day at Sabine Pass is outside the scheme. With ets_by_year, each
    stretch of the voyage is split by calendar year and priced at that year's
    phase and gases, since a year's surrender covers that year's emissions.
    """
    if not to_europe:
        return 0.0
    laden_sea = voyage.sea_days(voyage.laden) + voyage.laden.canal_days + voyage.laden.wait_days
    if inputs.ets_by_year is None:
        if inputs.ets_phase == 0:
            return 0.0
        return engine.ets_cost(
            eua_usd_per_t=inputs.eua_usd_t,
            phase_in=inputs.ets_phase,
            tco2_per_t_lng=inputs.tco2_per_t_lng,
            mmbtu_per_t_lng=inputs.mmbtu_per_t_lng,
            boil_off_mmbtu_per_day=voyage.boil_off_per_day,
            laden_days=laden_sea,
            ballast_days=voyage.t_ballast,
            berth_days=inputs.vessel.discharge_days,
            voyage_share=inputs.ets_voyage_share,
            berth_share=inputs.ets_berth_share,
        )
    load = inputs.vessel.load_days
    arrive = load + laden_sea
    leave = arrive + inputs.vessel.discharge_days
    back = leave + voyage.t_ballast
    stretches = ((load, arrive, inputs.ets_voyage_share), (arrive, leave, inputs.ets_berth_share),
                 (leave, back, inputs.ets_voyage_share))
    weighted = 0.0
    for start, end, share in stretches:
        for year, days in _year_days(start, end, inputs.day).items():
            phase, factor = inputs.ets_by_year.get(year, (0.0, 0.0))
            weighted += share * days * phase * factor
    tonnes_per_day = voyage.boil_off_per_day / inputs.mmbtu_per_t_lng
    return inputs.eua_usd_t * tonnes_per_day * weighted


def _costs(inputs: Inputs, route: RouteInput, voyage: Voyage, *, to_europe: bool) -> CostStack:
    # Only the part of the price paid when the cargo is lifted is financed: the
    # fixed fee, and its carrying cost, are owed whether or not it is.
    fob = inputs.hh_multiple * inputs.henry_hub
    return CostStack(
        port=inputs.port_west_usd if to_europe else inputs.port_east_usd,
        canal_laden=route.canal_laden_usd,
        canal_ballast=route.canal_ballast_usd,
        slot_premium=route.slot_premium_usd,
        ets=_ets(inputs, voyage, to_europe=to_europe),
        financing=engine.financing_cost(
            fob_usd_per_mmbtu=fob, q_load=voyage.q_load, rate_percent=inputs.rate_percent,
            spread_bp=inputs.spread_bp, days=voyage.t_laden,
        ),
    )


def _route_lines(inputs: Inputs, route_id: str, *, to_europe: bool) -> dict[str, Any]:
    route = inputs.routes[route_id]
    voyage = _voyage(inputs, route)
    costs = _costs(inputs, route, voyage, to_europe=to_europe)
    hire = inputs.hire_usd_day * voyage.t_total
    total = engine.voyage_cost(inputs.hire_usd_day, voyage, costs)
    p_des = inputs.ttf + inputs.delta_nwe if to_europe else inputs.jkm
    f_conv, nb_conv = engine.conventional_netback(p_des, p_des, voyage, total)
    return {
        "route": route_id,
        "open": route.open,
        "why_closed": route.why_closed,
        "distance_nm": route.distance_nm,
        "days_laden": voyage.t_laden,
        "days_ballast": voyage.t_ballast,
        "days_total": voyage.t_total,
        "q_load_mmbtu": voyage.q_load,
        "gas_used_mmbtu": voyage.gas_used,
        "q_delivered_mmbtu": voyage.q_delivered,
        "hire_usd": hire,
        **{line + "_usd": value for line, value in costs.lines().items()},
        "canal_note": route.canal_note,
        "cost_without_hire_usd": costs.without_hire,
        "cost_usd": total,
        "p_des": p_des,
        "netback": engine.netback(p_des, voyage, total),
        "freight_conventional": f_conv,
        "netback_conventional": nb_conv,
        "_voyage": voyage,
        "_costs": costs,
    }


def evaluate(inputs: Inputs) -> dict[str, Any]:
    """Every line of one date. Closed routes are computed too, and flagged, never chosen."""
    west = _route_lines(inputs, WEST, to_europe=True)
    east = {r: _route_lines(inputs, r, to_europe=False) for r in EAST if r in inputs.routes}
    for route_id, lines in east.items():
        lines["arb"] = lines["netback"] - west["netback"]
        lines.update(engine.breakeven_spread(
            inputs.ttf, inputs.delta_nwe, west["_voyage"], west["cost_usd"],
            lines["_voyage"], lines["cost_usd"],
        ))
        lines["h_star_usd_day"] = engine.breakeven_hire(
            inputs.jkm, inputs.ttf, inputs.delta_nwe, west["_voyage"], west["_costs"],
            lines["_voyage"], lines["_costs"],
        )
    open_east = {r: lines for r, lines in east.items() if lines["open"]}
    best_east = max(open_east, key=lambda r: open_east[r]["netback"]) if open_east else None
    candidates = [("NWE", WEST, west["netback"])] + [("NEA", r, l["netback"]) for r, l in open_east.items()]
    destination, best_route, best = max(candidates, key=lambda c: c[2])
    lift = engine.lift_test(best, inputs.henry_hub, inputs.liquefaction_fee, hh_multiple=inputs.hh_multiple)
    for lines in [west, *east.values()]:
        lines.pop("_voyage")
        lines.pop("_costs")
    return {
        "day": inputs.day.isoformat(),
        "spread": inputs.jkm - inputs.ttf,
        "west": west,
        "east": east,
        "best_route_east": best_east,
        "best_destination": destination,
        "best_route": best_route,
        "best_netback": best,
        **lift,
    }

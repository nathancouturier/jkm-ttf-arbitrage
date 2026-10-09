"""The Model view's presets: whole sets of engine inputs, each from the data of one date.

Nothing here is typed. Each preset is a date the study works through, its
prices from the series that cover that date, every other input read from the
committed data and the parameter table by lngarb.worked. An input the data do
not hold for the date is shown as missing, never filled: the hire, where no
charter rate was reported within the parameter table's 14 days, is the one
that happens (April 2020); the page then offers the low, central and high
levels of the reported rates, which the analysis runs, for the visitor to
choose. The inputs that are this study's assumptions rather than the data's
are named, in the preset's lead and under each field: the liquefaction fee,
the port costs and the funding spread always; Europe's DES spread where ACER
published too little; the allowance price where it is held.

Spark's worked example takes the week of its note: its ship, its rate of -750
$/day, reported for 8 February 2022, and its 17.5 laden and 12.5 ballast days
to Northwest Europe, read through Spark30's own composition of 30 days: 25
sailing, a day to load, a day to discharge and 3 flex days.

model.json carries, per preset, the engine's inputs in the contract
src/engine.js reads, the source of each input, what is missing and why, the
canal tolls for either ship (the tolls are priced on capacity), the engine's
full output for the inputs (so the page can show an untouched preset exactly)
and, where every figure it needs is there, the landing sentence's clauses,
which the page's own sentence must match.

THE EDITS. apply_edits is the Python reading of src/model-calc.js applyEdits,
step for step: the same order, the same limits, the same refusals, the same
rules for a ballast leg by another route. NAMED_EDITS are worked through both,
and tools/validate-engine.mjs holds the page to the Python on each.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, replace
from datetime import date
from typing import Any, Callable, Mapping, Sequence

from . import canals, config, reader, units, worked
from .cases import WEST, Inputs, evaluate
from .engine import Vessel

__all__ = ["PRESETS", "Preset", "LIMITS", "NAMED_EDITS", "preset_inputs", "route_tolls", "refusal", "apply_edits",
           "complete", "model_document", "named_edits"]


@dataclass(frozen=True)
class Preset:
    id: str
    label: str
    #: the loading day; None for the latest week, given by the caller
    day: str | None
    #: where the two prices come from: "ngwu", "wngsr" or "monthly"
    prices: str
    #: one sentence of what the preset is, in words
    about: str


#: Spark's worked example, in its note on negative freight rates: a 160,000 m3
#: TFDE carrier, 17.5 laden days and 12.5 ballast days between the US Gulf and
#: Northwest Europe. Spark30's 30 days are 25 sailing, a day to load, a day to
#: discharge and 3 flex days, so the 17.5 laden days are read as 12.5 at sea,
#: the engine's day to load and day to discharge, and the 3 flex days; the 12.5
#: ballast days are at sea.
SPARK_LADEN_SEA_DAYS = 12.5
SPARK_BALLAST_SEA_DAYS = 12.5

#: What the form accepts, so that a typed figure cannot send the engine
#: somewhere it has no meaning (a ship that does not move, a voyage of a
#: century, a euro worth nothing). Limits of the calculator, not market data:
#: [low, high], inclusive. A figure that is not finite is refused whatever its
#: key. The exchange rate's range brackets every H.10 rate since 1999.
LIMITS: Mapping[str, tuple[float, float]] = {
    "usd_per_eur": (0.5, 2.0),
    "speed_kn": (5.0, 25.0),
    "boil_off_percent": (0.0, 1.0),
    "fill_percent": (50.0, 100.0),
    "load_days": (0.0, 10.0),
    "discharge_days": (0.0, 10.0),
    "sea_days": (0.0, 120.0),
    "flex_days": (0.0, 30.0),
    "canal_days": (0.0, 30.0),
    "wait_days": (0.0, 60.0),
    "ets_phase": (0.0, 1.0),
    "eua_eur_t": (0.0, 1000.0),
    "ets_voyage_share": (0.0, 1.0),
    "ets_berth_share": (0.0, 1.0),
    "mmbtu_per_m3": (15.0, 30.0),
    "mmbtu_per_t_lng": (40.0, 60.0),
    "hh_multiple_percent": (0.0, 200.0),
}

PRESETS: tuple[Preset, ...] = (
    Preset("latest", "Latest week", None, "wngsr", "The latest week EIA's supplement prints"),
    Preset("april_2020", "April 2020", "2020-04-15", "monthly",
           "The month US cargoes were cancelled: METI's contract-based price for JKM and the World Bank's TTF"),
    Preset("october_2022", "October 2022", "2022-10-12", "ngwu",
           "The autumn of record charter rates, with Europe paying more than Asia"),
    Preset("march_2024", "March 2024", "2024-03-27", "ngwu",
           "A week with Suez treated as closed and Panama's booking slots cut; no wait at Panama was reported for "
           "LNG that month, so the engine adds none"),
    Preset("march_2026", "March 2026", "2026-03-25", "wngsr",
           "A week with Panama under water conservation measures and Suez treated as closed"),
    Preset("spark_example", "Spark's worked example", "2022-02-09", "ngwu",
           "Spark's ship, negative charter rate and days to Northwest Europe from its note on negative freight "
           "rates, at that week's prices"),
)

#: The inputs whose figure is a parameter of the study rather than market data,
#: by the key the page uses, with the parameter it comes from.
PARAMETER_SOURCES: Mapping[str, str] = {
    "liquefaction_fee": "liquefaction_fee_usd_mmbtu",
    "port_west_usd": "port_cost_west_usd",
    "port_east_usd": "port_cost_east_usd",
    "spread_bp": "funding_spread_bp",
    "hh_multiple_percent": "spa_henry_hub_multiple",
    "mmbtu_per_m3": "mmbtu_per_m3_lng",
    "mmbtu_per_t_lng": "mmbtu_per_t_lng",
    "ets_voyage_share": "ets_voyage_share",
    "ets_berth_share": "ets_berth_share",
}

#: The ship's own parameters, per ship, by the key the page uses.
SHIP_SOURCES: Mapping[str, Mapping[str, str]] = {
    "tfde_160k": {"speed_kn": "vessel_160k_speed_kn", "boil_off_percent": "vessel_160k_boil_off_per_day",
                  "fill_percent": "fill", "load_days": "load_days", "discharge_days": "discharge_days"},
    "two_stroke_174k": {"speed_kn": "vessel_174k_speed_kn", "boil_off_percent": "vessel_174k_boil_off_per_day",
                        "fill_percent": "fill", "load_days": "load_days", "discharge_days": "discharge_days"},
}

#: How the lead names each assumption.
ASSUMPTION_WORDS: Mapping[str, str] = {
    "delta_nwe": "Europe's DES spread to TTF",
    "eua": "the allowance price",
    "liquefaction_fee": "the liquefaction fee",
    "ports": "the port costs",
    "spread_bp": "the funding spread",
    "days": "the split of Spark's laden days",
}

#: How the lead names each input missing for the date, by lngarb.worked's key.
MISSING_WORDS: Mapping[str, str] = {
    "jkm": "JKM", "ttf": "TTF", "fx": "the exchange rate", "henry_hub": "Henry Hub", "rate": "the overnight rate",
    "hire": "the hire", "delta_nwe": "Europe's DES spread", "eua": "the allowance price",
    "panama_toll": "the Panama toll",
}


def preset_inputs(preset: Preset, latest_day: date) -> tuple[Inputs, dict[str, str]]:
    """The engine's inputs for a preset, and what the data do not hold for it.

    A missing input is NaN in the inputs, with its source in words beginning
    "missing: ", and its key and reason in the mapping returned."""
    day = latest_day.isoformat() if preset.day is None else preset.day
    item = worked.WorkedDate(preset.label, day, preset.prices)
    missing: dict[str, str] = {}
    inputs = worked.inputs_for(item, missing=missing)
    sources = dict(inputs.sources)
    if preset.id == "spark_example":
        west = replace(inputs.routes[WEST], laden_sea_days=SPARK_LADEN_SEA_DAYS,
                       ballast_sea_days=SPARK_BALLAST_SEA_DAYS,
                       flex_days=config.PARAMETERS["spark30_flex_days"].value)
        inputs = replace(inputs, routes={**inputs.routes, WEST: west})
        sources["days"] = ("this study's reading of Spark's worked example: its 17.5 laden days as 12.5 at sea, a "
                           "day to load, a day to discharge and 3 flex days, from Spark30's 30 days (25 sailing, "
                           "1 load, 1 discharge, 3 flex); its 12.5 ballast days at sea, Sabine Pass to Gate")
    return replace(inputs, sources=sources), missing


def _vessels() -> dict[str, Any]:
    """Both ships the benchmark rates use, for the form's ship choice."""
    small = worked.vessel_on("2023-12-31")
    big = worked.vessel_on("2024-01-02")
    return {"tfde_160k": asdict(small), "two_stroke_174k": asdict(big)}


def _vessel_key(vessel: Vessel, vessels: Mapping[str, Any]) -> str:
    return next(key for key, value in vessels.items() if value["name"] == vessel.name)


def _parameter_words(name: str) -> str:
    parameter = config.PARAMETERS[name]
    return reader.dates_in_words(("assumption: " if parameter.status == "assumption" else "") + parameter.source)


def _finite(value: float | None) -> float | None:
    return value if value is not None and math.isfinite(value) else None


def route_tolls(day: date, vessels: Mapping[str, Any]) -> dict[str, dict[str, dict[str, float | None]]]:
    """Each route's canal tolls on the day for either ship, in USD.

    The laden and ballast tolls of a round trip through the route's canal, as
    lngarb.worked prices them for that ship, and the toll of a ballast transit
    alone, for a ship whose laden leg went another way: at Panama the ballast
    table without the round trip discount of 2016 to 2022, priced on the day
    of the route's own ballast transit; at Suez the ballast toll, which has no
    round trip rate. None where the route is closed for want of a price, or
    where no table covers the day."""
    out: dict[str, dict[str, dict[str, float | None]]] = {}
    for key, fields in vessels.items():
        vessel = Vessel(**fields)
        routes = worked.routes_on(day, vessel, missing={})
        tolls: dict[str, dict[str, float | None]] = {}
        for route_id, route in routes.items():
            priced = route.open or bool(route.canal_note) and not route.canal_note.startswith("no ")
            laden = _finite(route.canal_laden_usd) if priced else None
            ballast = _finite(route.canal_ballast_usd) if priced else None
            alone = ballast
            if route_id == "nea_panama" and priced:
                _, ballast_after = worked.transit_days(route_id, vessel)
                ballast_day = worked._on(day, ballast_after)
                toll = canals.panama_toll(ballast_day, vessel.capacity_m3, laden=False, roundtrip_ballast=False)
                alone = None if toll is None else toll + canals.panama_fresh_water_surcharge(ballast_day, toll)
            tolls[route_id] = {"canal_laden_usd": laden, "canal_ballast_usd": ballast, "canal_ballast_alone_usd": alone}
        out[key] = tolls
    return out


def _unpriced_tolls_missing(inputs: Inputs, own: Mapping[str, Mapping[str, float | None]]) -> Inputs:
    """A route closed for want of a price carries no toll: missing, never zero."""
    routes = dict(inputs.routes)
    for route_id, tolls in own.items():
        if route_id in routes and tolls["canal_laden_usd"] is None and route_id not in (WEST, "nea_cape"):
            routes[route_id] = replace(routes[route_id], canal_laden_usd=float("nan"),
                                       canal_ballast_usd=float("nan"))
    return replace(inputs, routes=routes)


def _source_words(inputs: Inputs) -> dict[str, str]:
    """Each input's source, in words, by the key the page reads."""
    words = {key: reader.dates_in_words(text) for key, text in inputs.sources.items()}
    for key, name in PARAMETER_SOURCES.items():
        words[key] = _parameter_words(name)
    phases = config.PARAMETERS["ets_phase_in_by_year"]
    words["ets_phase"] = reader.dates_in_words(
        phases.source + "; the voyage's days in each calendar year at that year's share, until a share is typed")
    return words


def _assumed(inputs: Inputs) -> list[str]:
    """The inputs of a preset that are this study's assumptions, in the lead's order."""
    out = []
    for key in ("delta_nwe", "eua"):
        if inputs.sources.get(key, "").startswith("assumption"):
            out.append(key)
    out += ["liquefaction_fee", "ports", "spread_bp"]
    if "days" in inputs.sources:
        out.append("days")
    return out


def _lead(preset: Preset, inputs: Inputs, missing: Mapping[str, str]) -> list[dict[str, Any]]:
    assumed = [ASSUMPTION_WORDS[key] for key in _assumed(inputs)]
    segments = [
        reader.T(preset.about + ", loading on "), reader.D("day", inputs.day),
        reader.T(". Prices, rates and canal tolls are the data's for that date; "),
        reader.W("assumed", reader.listed(assumed)),
        reader.T(" are this study's assumptions, each named under its field."),
    ]
    if missing:
        names = [MISSING_WORDS[key] for key in MISSING_WORDS if key in missing]
        segments += [
            reader.T(" The data hold no figure of "), reader.W("missing", reader.listed(names)),
            reader.T(" for this date, so every output that needs it waits for one to be typed."),
        ]
    segments.append(reader.T(" Change any input."))
    return segments


def complete(result: Mapping[str, Any]) -> bool:
    """Whether the landing sentence has every figure it compares: the page's
    compose() in src/model.js asks the same."""
    def ok(value: Any) -> bool:
        return isinstance(value, float) and math.isfinite(value)

    lines = [result["west"], *result["east"].values()]
    return (ok(result["best_netback"]) and ok(result["lift_margin"]) and ok(result["full_margin"])
            and ok(result["spread"]) and all(not l["open"] or ok(l["netback"]) for l in result["east"].values())
            and not any((l is result["west"] or l["open"]) and ok(l["q_delivered_mmbtu"])
                        and l["q_delivered_mmbtu"] <= 0 for l in lines))


def model_document(latest_day: date, latest_prices: str,
                   inputs_json: Callable[[Inputs], dict[str, Any]]) -> dict[str, Any]:
    """model.json's body: the presets, the ships, the words the form uses."""
    from .freight_anchors import hire_levels

    vessels = _vessels()
    presets, unavailable = [], []
    for preset in PRESETS:
        if preset.day is None:
            preset = replace(preset, prices=latest_prices)
        try:
            inputs, missing = preset_inputs(preset, latest_day)
        except worked.MissingInput as exc:
            unavailable.append({"id": preset.id, "label": preset.label, "why": reader.dates_in_words(str(exc))})
            continue
        tolls = route_tolls(inputs.day, vessels)
        vessel_key = _vessel_key(inputs.vessel, vessels)
        inputs = _unpriced_tolls_missing(inputs, tolls[vessel_key])
        result = evaluate(inputs)
        fx = worked.usd_per_eur_detail(inputs.day)[0]
        presets.append({
            "id": preset.id,
            "label": preset.label,
            "day": inputs.day,
            "prices": preset.prices,
            "about": preset.about,
            "lead_segments": _lead(preset, inputs, missing),
            "inputs": inputs_json(inputs),
            "vessel_key": vessel_key,
            "route_tolls": tolls,
            "source_words": _source_words(inputs),
            "assumed": _assumed(inputs),
            "missing": [{"key": key, "why": reader.dates_in_words(why)} for key, why in missing.items()],
            "closed_words": {route: reader.closed_words(r.why_closed) for route, r in inputs.routes.items() if not r.open},
            "usd_per_eur": fx,
            "eua_eur_t": None if inputs.eua_usd_t is None or not math.isfinite(inputs.eua_usd_t)
            else inputs.eua_usd_t / fx,
            "result": result,
            "verdict_segments": reader.verdict(result, inputs.day, inputs.hh_multiple, delta_nwe=inputs.delta_nwe,
                                               liquefaction_fee=inputs.liquefaction_fee, weekly=False)["segments"]
            if complete(result) else None,
        })
    levels = hire_levels()
    return {
        "presets": presets,
        "unavailable": unavailable,
        "vessels": vessels,
        "vessel_sources": {key: {field: _parameter_words(name) for field, name in fields.items()}
                           for key, fields in SHIP_SOURCES.items()},
        "hire_levels": {**levels, "words": "the lowest, the median and the highest of the charter rates reported, "
                                           "the three levels the analysis runs where a date has no rate of its own"},
        "route_names": dict(reader.ROUTE_NAMES),
        "route_short": dict(reader.ROUTE_SHORT),
        "patterns": dict(reader.ROUTE_PATTERNS),
        "part_words": dict(reader.PART_WORDS),
        "part_words_premium": reader.regas_words(1.0)["part"],
        "units": {"mmbtu_per_mwh": units.MMBTU_PER_MWH, "percent_per_one": 100.0},
        "limits": dict(LIMITS),
        "checks": named_edits(latest_day, latest_prices, [p["id"] for p in presets]),
        "title_segments": [reader.T("The calculator: every input of a cargo loading at Sabine Pass, and what it nets "
                                    "at Gate and at Futtsu by each route")],
    }


# ---------------------------------------------------------------------------
# The edits: what a visitor types, laid over a preset as the page lays them
# (src/model-calc.js applyEdits), and named edits worked through both.
# ---------------------------------------------------------------------------

#: An edit is {"key", "value"} or, for a route, {"key", "route", "value"}. A
#: value of None is an input left empty: missing, except for the days at sea,
#: where an empty field means the days from the distance.
NAMED_EDITS: tuple[tuple[str, str, tuple[dict[str, Any], ...]], ...] = (
    ("a hire of 300,000 $/day", "latest", ({"key": "hire_usd_day", "value": 300_000.0},)),
    ("Panama closed", "latest", ({"key": "open", "route": "nea_panama", "value": False},)),
    ("laden via Panama, back by the Cape", "march_2024",
     ({"key": "ballast_route", "route": "nea_panama", "value": "nea_cape"},)),
    ("days at sea typed for the Cape", "spark_example",
     ({"key": "laden_sea_days", "route": "nea_cape", "value": 30.0},
      {"key": "ballast_sea_days", "route": "nea_cape", "value": 28.0})),
    ("TTF in euros at a dollar per euro", "october_2022",
     ({"key": "usd_per_eur", "value": 1.0}, {"key": "ttf_eur_mwh", "value": 150.0})),
    ("an allowance of 100 EUR/t, seven tenths surrendered", "latest",
     ({"key": "eua_eur_t", "value": 100.0}, {"key": "ets_phase", "value": 0.7})),
    ("the smaller ship at 19.5 knots, with its own tolls", "latest",
     ({"key": "vessel", "value": "tfde_160k"}, {"key": "speed_kn", "value": 19.5})),
    ("Gate's laden days at sea emptied, so taken from the distance", "spark_example",
     ({"key": "laden_sea_days", "route": "nwe_direct", "value": None},)),
    ("a ballast toll typed for Panama, then back by the Cape", "march_2024",
     ({"key": "canal_ballast_usd", "route": "nea_panama", "value": 100_000.0},
      {"key": "ballast_route", "route": "nea_panama", "value": "nea_cape"})),
    ("a speed of 40 knots, refused", "latest", ({"key": "speed_kn", "value": 40.0},)),
    ("the Cape back by Suez, which is closed", "latest",
     ({"key": "ballast_route", "route": "nea_cape", "value": "nea_suez"},)),
    ("the Cape back by Panama, a ballast transit alone", "spark_example",
     ({"key": "ballast_route", "route": "nea_cape", "value": "nea_panama"},)),
    ("twelve days of waiting at Panama, the Cape back by Panama", "latest",
     ({"key": "wait_days", "route": "nea_panama", "value": 12.0},
      {"key": "ballast_route", "route": "nea_cape", "value": "nea_panama"})),
    ("every emission surrendered in April 2020, at no price read", "april_2020",
     ({"key": "hire_usd_day", "value": 45_500.0}, {"key": "ets_phase", "value": 1.0})),
    ("a new exchange rate and every emission surrendered, with no allowance price read", "october_2022",
     ({"key": "usd_per_eur", "value": 1.2}, {"key": "ets_phase", "value": 1.0})),
    ("three flex days on the Panama route", "latest", ({"key": "flex_days", "route": "nea_panama", "value": 3.0},)),
    ("the hire left empty", "march_2026", ({"key": "hire_usd_day", "value": None},)),
    ("a hire typed where the data hold none", "april_2020", ({"key": "hire_usd_day", "value": 45_500.0},)),
    ("an exchange rate of zero, refused", "latest", ({"key": "usd_per_eur", "value": 0.0},)),
    ("the lift test at 120 percent of Henry Hub", "latest", ({"key": "hh_multiple_percent", "value": 120.0},)),
    ("a fill of 95 percent and two days to load", "latest",
     ({"key": "fill_percent", "value": 95.0}, {"key": "load_days", "value": 2.0})),
    ("22 MMBtu per m3 and 50 MMBtu per tonne", "march_2024",
     ({"key": "mmbtu_per_m3", "value": 22.0}, {"key": "mmbtu_per_t_lng", "value": 50.0})),
    ("every voyage emission counted and none at berth", "latest",
     ({"key": "ets_voyage_share", "value": 1.0}, {"key": "ets_berth_share", "value": 0.0})),
)

_SCALARS = ("jkm", "ttf", "delta_nwe", "henry_hub", "liquefaction_fee", "hire_usd_day", "port_west_usd",
            "port_east_usd", "rate_percent", "spread_bp", "mmbtu_per_m3", "mmbtu_per_t_lng", "ets_voyage_share",
            "ets_berth_share")


def refusal(key: str, value: float) -> str | None:
    """Why a figure cannot be used, in words, or None (src/model-calc.js refusal)."""
    if math.isnan(value):
        return None
    if math.isinf(value):
        return "is too large to use"
    if key in LIMITS:
        low, high = LIMITS[key]
        if value < low or value > high:
            return "must lie between %g and %g" % (low, high)
    return None


def _number(value: Any) -> float:
    return float("nan") if value is None else float(value)


def apply_edits(inputs: Inputs, edits: Sequence[Mapping[str, Any]], *, usd_per_eur: float, eua_eur_t: float | None,
                vessels: Mapping[str, Any], vessel_key: str,
                tolls: Mapping[str, Mapping[str, Mapping[str, float | None]]]) -> tuple[Inputs, list[dict[str, Any]]]:
    """The Python reading of the page's applyEdits: the inputs and what was refused."""
    refused: list[dict[str, Any]] = []

    def usable(edit: Mapping[str, Any], limit_key: str | None = None) -> float:
        value = _number(edit["value"])
        why = refusal(limit_key or edit["key"], value)
        if why:
            refused.append({"key": edit["key"], "route": edit.get("route"), "why": why})
            return float("nan")
        return value

    def toll(value: float | None) -> float:
        return float("nan") if value is None else value

    out = inputs
    routes = dict(out.routes)
    vessel_edit = next((e for e in edits if e["key"] == "vessel" and e["value"] in vessels), None)
    ship = vessel_edit["value"] if vessel_edit else vessel_key
    ship_tolls = tolls.get(ship, {})
    if vessel_edit:
        out = replace(out, vessel=Vessel(**vessels[ship]))
        for route_id in routes:
            if route_id in ship_tolls:
                routes[route_id] = replace(routes[route_id],
                                           canal_laden_usd=toll(ship_tolls[route_id]["canal_laden_usd"]),
                                           canal_ballast_usd=toll(ship_tolls[route_id]["canal_ballast_usd"]))

    for edit in edits:
        key = edit["key"]
        if "route" in edit and edit["route"] is not None:
            continue
        if key in _SCALARS:
            out = replace(out, **{key: usable(edit)})
        elif key == "hh_multiple_percent":
            out = replace(out, hh_multiple=usable(edit) / 100.0)
        elif key == "speed_kn":
            out = replace(out, vessel=replace(out.vessel, speed_kn=usable(edit)))
        elif key == "boil_off_percent":
            out = replace(out, vessel=replace(out.vessel, boil_off_per_day=usable(edit) / 100.0))
        elif key == "fill_percent":
            out = replace(out, vessel=replace(out.vessel, fill=usable(edit) / 100.0))
        elif key in ("load_days", "discharge_days"):
            out = replace(out, vessel=replace(out.vessel, **{key: usable(edit)}))
        elif key == "ets_phase":
            out = replace(out, ets_by_year=None, ets_phase=usable(edit))

    fx_edit = next((e for e in edits if e["key"] == "usd_per_eur"), None)
    fx = usable(fx_edit) if fx_edit else usd_per_eur
    eua_typed = False
    for edit in edits:
        if edit["key"] == "ttf_eur_mwh":
            out = replace(out, ttf=usable(edit) * fx / units.MMBTU_PER_MWH)
        if edit["key"] == "eua_eur_t":
            out = replace(out, eua_usd_t=usable(edit) * fx)
            eua_typed = True
    if fx_edit and not eua_typed:
        out = replace(out, eua_usd_t=None if eua_eur_t is None else eua_eur_t * fx)

    for edit in edits:
        route_id = edit.get("route")
        if route_id is None or route_id not in routes or edit["key"] == "ballast_route":
            continue
        route = routes[route_id]
        key = edit["key"]
        if key == "open":
            route = replace(route, open=edit["value"] is True,
                            why_closed=route.why_closed if edit["value"] is True or route.why_closed
                            else "closed by hand in the calculator")
        elif key in ("laden_sea_days", "ballast_sea_days"):
            route = replace(route, **{key: None if edit["value"] is None else usable(edit, "sea_days")})
        elif key in ("flex_days", "canal_days", "wait_days", "canal_laden_usd", "canal_ballast_usd",
                     "slot_premium_usd"):
            route = replace(route, **{key: usable(edit)})
        routes[route_id] = route

    for edit in edits:
        route_id = edit.get("route")
        if edit["key"] != "ballast_route" or route_id not in routes:
            continue
        route = routes[route_id]
        if edit["value"] == route_id or edit["value"] not in routes:
            routes[route_id] = replace(route, ballast_distance_nm=None, ballast_canal_days=None, ballast_wait_days=None)
            continue
        other = routes[edit["value"]]

        def typed(key: str) -> bool:
            return any(e["key"] == key and e.get("route") == route_id for e in edits)

        route = replace(route, ballast_distance_nm=other.distance_nm, ballast_canal_days=other.canal_days,
                        ballast_wait_days=other.wait_days)
        if not typed("canal_ballast_usd"):
            alone = ship_tolls.get(edit["value"], {}).get("canal_ballast_alone_usd")
            route = replace(route, canal_ballast_usd=toll(alone))
        if not other.open:
            route = replace(route, open=False, why_closed="back by %s, which is closed" % reader.ROUTE_SHORT[edit["value"]])
        routes[route_id] = route
    return replace(out, routes=routes), refused


def named_edits(latest_day: date, latest_prices: str, offered: Sequence[str]) -> list[dict[str, Any]]:
    """Each named edit with the Python engine's output for it, and what it refuses."""
    out = []
    vessels = _vessels()
    by_id = {p.id: p for p in PRESETS}
    for name, preset_id, edits in NAMED_EDITS:
        if preset_id not in offered:
            continue
        preset = by_id[preset_id]
        if preset.day is None:
            preset = replace(preset, prices=latest_prices)
        inputs, _ = preset_inputs(preset, latest_day)
        tolls = route_tolls(inputs.day, vessels)
        vessel_key = _vessel_key(inputs.vessel, vessels)
        inputs = _unpriced_tolls_missing(inputs, tolls[vessel_key])
        fx = worked.usd_per_eur_detail(inputs.day)[0]
        eua = None if inputs.eua_usd_t is None or not math.isfinite(inputs.eua_usd_t) else inputs.eua_usd_t / fx
        edited, refused = apply_edits(inputs, edits, usd_per_eur=fx, eua_eur_t=eua, vessels=vessels,
                                      vessel_key=vessel_key, tolls=tolls)
        out.append({"name": name, "preset": preset_id, "edits": list(edits),
                    "refused": [{"key": r["key"], "route": r["route"]} for r in refused],
                    "result": evaluate(edited)})
    return out

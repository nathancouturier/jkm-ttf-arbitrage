"""Write data/fixtures/engine-cases.json: random inputs and the Python engine's full output.

src/engine.js prices the Model view in the browser; tools/validate-engine.mjs
runs it on these cases with plain node and requires every output to agree with
lngarb.cases.evaluate to 1e-9. The cases cover both ship presets, every route,
a ballast leg by another route, closed routes, zero and negative hire, a zero
regas discount, carbon split across a year end and none at all. The seed is
fixed, so the file is the same on every run.

After the random cases come fixed edge cases, each named in its "edge" field,
for the paths random draws never reach: a loading day on 30 or 31 December with
a fractional load time, so the year split starts part way through a day; a year
missing from ets_by_year; hire exactly at H*; three identical routes east, and
a route east identical to the west one, so that netbacks tie and H* is null;
every route east closed; a route east absent; the west route returning another
way; and an input object that leaves out every optional field, so the browser
engine's defaults are held to the Python dataclasses'.

    PYTHONPATH=src python scripts/gen_fixtures.py
"""

from __future__ import annotations

import json
import math
import random
import sys
from dataclasses import asdict, replace
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lngarb import config, worked  # noqa: E402
from lngarb.cases import EAST, WEST, Inputs, RouteInput, evaluate  # noqa: E402

SCHEMA_VERSION = 1
CASES = 240
SEED = 20261008
OUT = ROOT / "data" / "fixtures" / "engine-cases.json"


def _clean(value):
    """JSON has no NaN: a breakeven hire with no days between the routes is null, as the browser reads it."""
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, dict):
        return {k: _clean(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_clean(v) for v in value]
    return value


def _vessels():
    big = worked.vessel_on(date(2024, 6, 1))
    small = worked.vessel_on(date(2022, 6, 1))
    return [big, small]


def _case(rng: random.Random, number: int) -> Inputs:
    vessel = rng.choice(_vessels())
    distances = worked.distances()
    # A late December day now and then, so that carbon splits across a year end.
    day = date(2024, 1, 1) + timedelta(days=rng.randrange(0, 1000))
    if number % 7 == 0:
        day = date(rng.choice([2023, 2024, 2025]), 12, rng.randrange(1, 32))
    # Days typed on the route west as well now and then, with carbon below, so
    # that typed days drive the year split of the allowances; flex days too.
    typed = number % 5 == 1
    routes = {WEST: RouteInput(
        distances[WEST],
        laden_sea_days=rng.uniform(8, 20) if typed else None,
        ballast_sea_days=rng.uniform(8, 20) if typed and rng.random() > 0.3 else None,
        flex_days=rng.uniform(0, 4) if number % 4 == 2 else 0.0,
    )}
    for route in EAST:
        other = rng.choice(EAST)
        returns_other_way = number % 3 == 0 and other != route
        routes[route] = RouteInput(
            distance_nm=distances[route] * rng.uniform(0.95, 1.05),
            open=rng.random() > 0.15,
            why_closed="",
            canal_laden_usd=0.0 if route == "nea_cape" else rng.uniform(0, 1_200_000),
            canal_ballast_usd=0.0 if route == "nea_cape" else rng.uniform(0, 1_000_000),
            canal_days=0.0 if route == "nea_cape" else rng.uniform(0, 2),
            wait_days=rng.choice([0.0, 0.0, rng.uniform(0, 20)]),
            slot_premium_usd=rng.choice([0.0, 0.0, rng.uniform(0, 4_000_000)]),
            canal_note="",
            ballast_distance_nm=distances[other] if returns_other_way else None,
            ballast_canal_days=rng.uniform(0, 2) if returns_other_way else None,
            ballast_wait_days=rng.uniform(0, 10) if returns_other_way and rng.random() > 0.5 else None,
            laden_sea_days=rng.uniform(8, 45) if typed else None,
            ballast_sea_days=rng.uniform(8, 45) if typed and rng.random() > 0.5 else None,
            flex_days=rng.uniform(0, 4) if number % 4 == 2 else 0.0,
        )
    hire = rng.choice([0.0, -750.0, rng.uniform(-10_000, 0), rng.uniform(0, 400_000), rng.uniform(20_000, 120_000)])
    carbon = rng.random()
    if carbon < 0.3:
        # No surrender: the price may be one not read (None), which costs nothing.
        ets_by_year, phase, factor, eua = None, 0.0, 0.0, rng.choice([0.0, None])
    elif carbon < 0.35:
        # A surrender at a price not read: the carbon cost, and with it the
        # netback west, is unknown.
        ets_by_year = {day.year: (1.0, 2.75), day.year + 1: (1.0, 2.75)}
        phase, factor, eua = 1.0, 2.75, None
    elif carbon < 0.5:
        ets_by_year, phase, factor, eua = None, rng.choice([0.4, 0.7, 1.0]), 2.75, rng.uniform(50, 120)
    else:
        ets_by_year = {
            day.year: (rng.choice([0.4, 0.7, 1.0]), 2.75),
            day.year + 1: (1.0, 2.75 + rng.uniform(0, 0.1)),
        }
        phase, factor, eua = ets_by_year[day.year][0], ets_by_year[day.year][1], rng.uniform(50, 120)
    ttf = rng.uniform(1.5, 60)
    return Inputs(
        day=day,
        vessel=vessel,
        mmbtu_per_m3=config.PARAMETERS["mmbtu_per_m3_lng"].value,
        jkm=ttf + rng.uniform(-8, 8),
        ttf=ttf,
        delta_nwe=rng.choice([0.0, rng.uniform(-3, 0.5)]),
        hire_usd_day=hire,
        henry_hub=rng.uniform(1.5, 9),
        hh_multiple=1.15,
        liquefaction_fee=rng.uniform(2.25, 3.5),
        routes=routes,
        port_west_usd=rng.uniform(150_000, 400_000),
        port_east_usd=rng.uniform(150_000, 400_000),
        rate_percent=rng.uniform(0, 6),
        spread_bp=150.0,
        eua_usd_t=eua,
        ets_phase=phase,
        tco2_per_t_lng=factor,
        ets_by_year=ets_by_year,
        mmbtu_per_t_lng=51.56,
        ets_voyage_share=0.5,
        ets_berth_share=1.0,
    )


def _inputs_json(inputs: Inputs) -> dict:
    out = {
        "day": inputs.day.isoformat(),
        "vessel": asdict(inputs.vessel),
        "routes": {k: asdict(v) for k, v in inputs.routes.items()},
        "ets_by_year": None if inputs.ets_by_year is None else {
            str(year): [phase, factor] for year, (phase, factor) in inputs.ets_by_year.items()},
    }
    for name in ("mmbtu_per_m3", "jkm", "ttf", "delta_nwe", "hire_usd_day", "henry_hub", "hh_multiple",
                 "liquefaction_fee", "port_west_usd", "port_east_usd", "rate_percent", "spread_bp", "eua_usd_t",
                 "ets_phase", "tco2_per_t_lng", "mmbtu_per_t_lng", "ets_voyage_share", "ets_berth_share"):
        out[name] = getattr(inputs, name)
    return out


#: The optional fields of RouteInput and Inputs, with their defaults: the
#: "optional_fields_omitted" case leaves out every one that holds its default.
ROUTE_DEFAULTS = {"open": True, "why_closed": "", "canal_laden_usd": 0.0, "canal_ballast_usd": 0.0, "canal_days": 0.0,
                  "wait_days": 0.0, "slot_premium_usd": 0.0, "canal_note": "", "ballast_distance_nm": None,
                  "ballast_canal_days": None, "ballast_wait_days": None, "laden_sea_days": None,
                  "ballast_sea_days": None, "flex_days": 0.0}
INPUT_DEFAULTS = {"eua_usd_t": 0.0, "ets_phase": 0.0, "tco2_per_t_lng": 0.0, "ets_by_year": None,
                  "mmbtu_per_t_lng": 1.0, "ets_voyage_share": 0.5, "ets_berth_share": 1.0}


def _plain(inputs: Inputs) -> Inputs:
    """A case with every route open, no canal, no wait, no carbon and the same port cost both ways."""
    routes = {name: RouteInput(route.distance_nm) for name, route in inputs.routes.items()}
    return replace(inputs, routes=routes, eua_usd_t=0.0, ets_phase=0.0, tco2_per_t_lng=0.0, ets_by_year=None,
                   mmbtu_per_t_lng=1.0, ets_voyage_share=0.5, ets_berth_share=1.0,
                   port_east_usd=inputs.port_west_usd)


def _edges() -> list[tuple[str, Inputs]]:
    base = _case(random.Random(SEED + 1), 1)
    plain = _plain(base)
    out = []
    by_year = {2024: (0.4, 2.75), 2025: (0.7, 2.8), 2026: (1.0, 2.9)}
    for day, load in ((date(2024, 12, 31), 0.5), (date(2024, 12, 30), 2.5), (date(2024, 12, 31), 0.9999999999999999),
                      (date(2025, 1, 1), 0.5)):
        out.append(("year_end_fraction", replace(base, day=day, vessel=replace(base.vessel, load_days=load),
                                                 ets_by_year=by_year, ets_phase=0.4, tco2_per_t_lng=2.75,
                                                 eua_usd_t=80.0)))
    out.append(("ets_year_missing", replace(base, day=date(2025, 12, 20), ets_by_year={2025: (0.7, 2.8)},
                                            ets_phase=0.7, tco2_per_t_lng=2.8, eua_usd_t=80.0)))
    first = evaluate(base)
    h_star = first["east"]["nea_cape"]["h_star_usd_day"]
    out.append(("hire_at_h_star", replace(base, hire_usd_day=h_star)))
    same = RouteInput(plain.routes["nea_cape"].distance_nm)
    out.append(("identical_east_routes", replace(plain, routes={**plain.routes, **{r: same for r in EAST}})))
    west = plain.routes[WEST]
    out.append(("east_equals_west", replace(plain, jkm=plain.ttf + plain.delta_nwe,
                                            routes={**plain.routes, **{r: west for r in EAST}})))
    out.append(("all_east_closed", replace(base, routes={**base.routes, **{
        r: replace(base.routes[r], open=False, why_closed="closed for the test") for r in EAST}})))
    out.append(("east_route_absent", replace(base, routes={k: v for k, v in base.routes.items() if k != "nea_suez"})))
    out.append(("west_returns_other_way", replace(base, routes={**base.routes, WEST: replace(
        base.routes[WEST], ballast_distance_nm=base.routes["nea_cape"].distance_nm, ballast_canal_days=0.5)})))
    out.append(("optional_fields_omitted", plain))
    return out


def _omit_defaults(inputs_json: dict) -> dict:
    out = {k: v for k, v in inputs_json.items() if not (k in INPUT_DEFAULTS and v == INPUT_DEFAULTS[k])}
    out["routes"] = {name: {k: v for k, v in route.items() if not (k in ROUTE_DEFAULTS and v == ROUTE_DEFAULTS[k])}
                     for name, route in inputs_json["routes"].items()}
    return out


def build() -> dict:
    rng = random.Random(SEED)
    cases = []
    for number in range(CASES):
        inputs = _case(rng, number)
        cases.append({"inputs": _inputs_json(inputs), "output": _clean(evaluate(inputs))})
    for name, inputs in _edges():
        given = _inputs_json(inputs)
        if name == "optional_fields_omitted":
            given = _omit_defaults(given)
        cases.append({"edge": name, "inputs": given, "output": _clean(evaluate(inputs))})
    return {
        "schema_version": SCHEMA_VERSION,
        "what": "Random inputs and lngarb.cases.evaluate's output, for tools/validate-engine.mjs",
        "seed": SEED,
        "cases": cases,
    }


def render(document: dict) -> str:
    """The file's text: one case per line, so that a diff shows which cases moved."""
    head = {k: v for k, v in document.items() if k != "cases"}
    lines = ["{"]
    for key, value in head.items():
        lines.append("%s: %s," % (json.dumps(key), json.dumps(value, ensure_ascii=True)))
    lines.append('"cases": [')
    cases = [json.dumps(c, ensure_ascii=True, allow_nan=False, separators=(",", ":")) for c in document["cases"]]
    lines.append(",\n".join(cases))
    lines.append("]}")
    return "\n".join(lines) + "\n"


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    text = render(build())
    OUT.write_text(text, encoding="utf-8", newline="\n")
    print("wrote %d random cases and %d edge cases to %s" % (CASES, len(_edges()), OUT.relative_to(ROOT).as_posix()))
    return 0


if __name__ == "__main__":
    sys.exit(main())

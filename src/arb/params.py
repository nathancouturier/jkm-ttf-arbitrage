"""The dated parameter tables of data/params.json, applied to a ship and a day.

Canal tariffs are taken as in force on the loading day for both transits.
"""

from __future__ import annotations

import json
from datetime import date
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"


@lru_cache(maxsize=None)
def load() -> dict:
    return json.loads((DATA / "params.json").read_text(encoding="utf-8"))


def _day(when) -> date:
    return when if isinstance(when, date) else date.fromisoformat(str(when)[:10])


def _in_force(rows: list[dict], when) -> dict | None:
    """The last row whose 'from' is on or before the day."""
    day, found = _day(when), None
    for row in rows:
        if _day(row["from"]) <= day:
            found = row
    return found


def _banded(quantity: float, sizes: list[float], rates: list[float]) -> float:
    total, left = 0.0, quantity
    for size, rate in zip(sizes, rates):
        step = min(left, size)
        total += step * rate
        left -= step
    return total + max(left, 0.0) * rates[len(sizes)]


# ---------------------------------------------------------------------------
# Ship
# ---------------------------------------------------------------------------

def ship_on(when) -> dict:
    """The freight benchmark's ship on a day, as engine inputs."""
    p = load()
    row = _in_force(p["ships"], when) or p["ships"][0]
    return {
        "id": row["id"],
        "name": row["name"],
        "capacity_m3": float(row["capacity_m3"]),
        "fill": p["voyage"]["fill"]["value"],
        "mmbtu_per_m3": p["units"]["mmbtu_per_m3_lng"]["value"],
        "boil_off": row["boil_off_per_day"],
        "speed_kn": p["voyage"]["speed_kn"]["value"],
    }


def ship_by_id(ship_id: str) -> dict:
    row = next(s for s in load()["ships"] if s["id"] == ship_id)
    return ship_on(row["from"])


# ---------------------------------------------------------------------------
# Panama
# ---------------------------------------------------------------------------

def panama_toll(when, capacity_m3: float) -> tuple[float, float]:
    """The toll alone for a laden transit and for the ballast transit back, USD."""
    p = load()["panama"]
    row = _in_force(p["tolls"], when) or p["tolls"][0]
    if "fixed_usd" in row:
        laden = row["fixed_usd"] + row["per_m3"] * capacity_m3
        return laden, laden * row["ballast_share"]
    sizes = p["band_sizes_m3"]
    # A ship back through the canal in ballast within 60 days paid the round-trip table.
    return _banded(capacity_m3, sizes, row["laden_per_m3"]), _banded(capacity_m3, sizes, row["round_trip_ballast_per_m3"])


def panama_charges(when, capacity_m3: float, booked: bool = True) -> dict:
    """Everything a round trip pays at Panama: toll, fresh water surcharge and booking fee."""
    p = load()["panama"]
    laden, ballast = panama_toll(when, capacity_m3)
    water = p["fresh_water"]
    fresh = (lambda toll: water["fixed_usd"] + water["share_of_toll"] * toll) if _day(when) >= _day(water["from"]) else (lambda toll: 0.0)
    fee_row = _in_force(p["booking_fee"], when)
    fee = float(fee_row["usd"]) if (booked and fee_row) else 0.0
    return {
        "toll_laden": laden, "toll_ballast": ballast,
        "fresh_water_laden": fresh(laden), "fresh_water_ballast": fresh(ballast),
        "booking_fee": fee,
        "laden": laden + fresh(laden) + fee,
        "ballast": ballast + fresh(ballast) + fee,
    }


# ---------------------------------------------------------------------------
# Suez
# ---------------------------------------------------------------------------

def suez_charges(when, capacity_m3: float, usd_per_sdr: float) -> dict:
    """Laden and ballast Suez tolls in USD for a US Gulf cargo to Japan."""
    p = load()["suez"]
    scnt = p["scnt_per_m3"]["value"] * capacity_m3
    dues = _in_force(p["dues_sdr_per_scnt"], when) or p["dues_sdr_per_scnt"][0]
    surcharge = (_in_force(p["lng_surcharge"], when) or {"share": 0.0})["share"]
    rebate = max((_in_force(p["us_gulf_to_asia_rebate"], when) or {"share": 0.0})["share"],
                 (_in_force(p["general_lng_reduction"], when) or {"share": 0.0})["share"])
    factor = 1.0 + surcharge - rebate
    laden = _banded(scnt, p["band_sizes_scnt"], dues["laden"]) * factor
    ballast = _banded(scnt, p["band_sizes_scnt"], dues["ballast"]) * factor
    return {"scnt": scnt, "surcharge": surcharge, "rebate": rebate, "usd_per_sdr": usd_per_sdr,
            "laden_sdr": laden, "ballast_sdr": ballast,
            "laden": laden * usd_per_sdr, "ballast": ballast * usd_per_sdr}


# ---------------------------------------------------------------------------
# EU ETS
# ---------------------------------------------------------------------------

def ets_on(when, ship_id: str) -> dict:
    """The share of emissions surrendered and the tonnes of CO2 equivalent per tonne of LNG burnt."""
    e = load()["ets"]
    year = _day(when).year
    phase = 0.0
    for row in e["phase_in"]:
        if row["year"] <= year:
            phase = row["share"]
    factor = e["tco2_per_t_lng"]
    if year >= e["methane_and_n2o_from_year"]:
        slip = e["methane_slip"][ship_id]
        factor = (1.0 - slip) * (e["tco2_per_t_lng"] + e["tn2o_per_t_lng"] * e["gwp_n2o"]) + slip * e["gwp_ch4"]
    return {"phase_in": phase, "tco2e_per_t_lng": factor,
            "mmbtu_per_t_lng": load()["units"]["mmbtu_per_tonne_lng"]["value"],
            "voyage_share": e["voyage_share"], "berth_share": e["berth_share"]}


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

def route_status(route: str, when) -> dict:
    """open, restricted or closed on a day, with the reason."""
    if route == "europe":
        return {"route": route, "status": "open", "note": "", "source": "", "url": None}
    rows = [r for r in load()["route_status"] if r["route"] == route]
    return _in_force(rows, when) or rows[0]


@lru_cache(maxsize=None)
def routes() -> dict:
    """Distances and lines of the four routes, by id."""
    raw = json.loads((DATA / "routes.json").read_text(encoding="utf-8"))
    return {r["id"]: r for r in raw["routes"]}


MARKET = {"europe": "nwe", "panama": "nea", "suez": "nea", "cape": "nea"}
ROUTE_ORDER = ("europe", "panama", "suez", "cape")
EAST = ("panama", "suez", "cape")

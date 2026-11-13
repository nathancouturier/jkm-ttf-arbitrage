"""The cargo model.

One LNG cargo is loaded at Sabine Pass and sold either in Northwest Europe
(at TTF less the DES discount) or in Northeast Asia (at JKM) by one of three
routes. Everything here is arithmetic on plain dictionaries: no dates, no
files, no network. Netbacks are in USD per MMBtu loaded.

site/js/engine.js is the same model for the browser, and
tests/test_js_port.py holds the two together on a fixture.

Conventions
    Hire runs for the whole round trip, back to the load port.
    The ship boils off the same share of the loaded cargo on every day of the
    round trip, and that gas is its fuel: the heel left on board pays for the
    ballast leg. This is how Spark defines the rate it publishes (the
    charterer's payment less the ballast fuel, over the round trip's days), so
    a Spark rate used as round-trip hire counts nothing twice.
    The gas burnt is simply not sold. It is valued at the delivered price with
    no separate fuel line.
"""

from __future__ import annotations

MMBTU_PER_MWH = 3.412142
EUROPE = "europe"


def eur_mwh_to_usd_mmbtu(eur_mwh: float, usd_per_eur: float) -> float:
    """30 EUR/MWh at 1.10 USD/EUR is 9.671344 USD/MMBtu."""
    return eur_mwh * usd_per_eur / MMBTU_PER_MWH


def usd_mmbtu_to_eur_mwh(usd_mmbtu: float, usd_per_eur: float) -> float:
    return usd_mmbtu * MMBTU_PER_MWH / usd_per_eur


# ---------------------------------------------------------------------------
# One voyage
# ---------------------------------------------------------------------------

def voyage(ship: dict, route: dict, port_days: dict) -> dict:
    """Days and volumes of a round trip on one route."""
    sea = route["distance_nm"] / (ship["speed_kn"] * 24.0)
    canal = route.get("canal_days", 0.0) + route.get("wait_days", 0.0)
    laden = port_days["load"] + sea + canal + port_days["discharge"]
    ballast = sea + canal
    loaded = ship["capacity_m3"] * ship["fill"] * ship["mmbtu_per_m3"]
    per_day = loaded * ship["boil_off"]
    round_trip = laden + ballast
    return {
        "sea_days": sea,
        "laden_days": laden,
        "ballast_days": ballast,
        "round_trip_days": round_trip,
        "loaded": loaded,
        "boil_off_per_day": per_day,
        "boil_off": per_day * round_trip,
        "delivered": loaded - per_day * round_trip,
    }


def carbon_cost(v: dict, carbon: dict, port_days: dict) -> float:
    """EU ETS on a voyage into the EU and back: half of the sea legs, all of the berth."""
    tonnes_per_day = v["boil_off_per_day"] / carbon["mmbtu_per_t_lng"]
    at_sea = v["round_trip_days"] - port_days["load"] - port_days["discharge"]
    days = carbon["voyage_share"] * at_sea + carbon["berth_share"] * port_days["discharge"]
    return carbon["eua_usd_t"] * carbon["phase_in"] * carbon["tco2e_per_t_lng"] * tonnes_per_day * days


def financing_cost(v: dict, finance: dict, contract: dict, henry_hub: float) -> float:
    """Interest on what is paid when the cargo is lifted, from loading to discharge."""
    paid = contract["hh_multiple"] * henry_hub * v["loaded"]
    return paid * (finance["rate"] + finance["spread"]) * v["laden_days"] / finance["day_count"]


def price_route(inputs: dict, route_id: str) -> dict:
    """Volumes, cost lines and netback of one route."""
    route = inputs["routes"][route_id]
    v = voyage(inputs["ship"], route, inputs["port_days"])
    to_europe = route["market"] == "nwe"
    price = inputs["ttf"] + inputs["des_discount"] if to_europe else inputs["jkm"]
    cost = {
        "hire": inputs["hire"] * v["round_trip_days"],
        "ports": route["port_cost"],
        "tolls": route.get("toll_laden", 0.0) + route.get("toll_ballast", 0.0),
        "carbon": carbon_cost(v, inputs["carbon"], inputs["port_days"]) if to_europe else 0.0,
        "financing": financing_cost(v, inputs["finance"], inputs["contract"], inputs["henry_hub"]),
    }
    cost["total"] = sum(cost.values())
    out = dict(v)
    out.update({
        "market": route["market"],
        "open": bool(route.get("open", True)),
        "price": price,
        "cost": cost,
        "netback": (price * v["delivered"] - cost["total"]) / v["loaded"],
    })
    return out


# ---------------------------------------------------------------------------
# East against west
# ---------------------------------------------------------------------------

def breakeven(inputs: dict, west: dict, east: dict) -> dict:
    """S*, its drivers, H* and the arb of one route east against Europe.

    S* is the JKM minus TTF spread at which the two netbacks are equal:

        S* = (TTF + d) x D_w / D_e + (C_e - C_w) / D_e - TTF

    with d the DES discount, D the MMBtu delivered and C the voyage cost. It
    splits exactly into five drivers, each in USD per MMBtu delivered east:

        hire          hire x extra days / D_e
        tolls         canal tolls / D_e
        boil_off      (TTF + d) x extra gas burnt / D_e
        des_discount  d
        other         extra ports, carbon and financing / D_e
    """
    d_e, d_w = east["delivered"], west["delivered"]
    extra_days = east["round_trip_days"] - west["round_trip_days"]
    cw, ce = west["cost"], east["cost"]
    drivers = {
        "hire": inputs["hire"] * extra_days / d_e,
        "tolls": (ce["tolls"] - cw["tolls"]) / d_e,
        "boil_off": west["price"] * (d_w - d_e) / d_e,
        "des_discount": inputs["des_discount"],
        "other": (ce["ports"] - cw["ports"] + ce["carbon"] - cw["carbon"]
                  + ce["financing"] - cw["financing"]) / d_e,
    }
    s_star = sum(drivers.values())
    # H*: the hire at which the two netbacks are equal at today's prices.
    no_hire = (ce["total"] - ce["hire"]) - (cw["total"] - cw["hire"])
    margin = inputs["jkm"] * d_e - west["price"] * d_w - no_hire
    h_star = margin / extra_days if extra_days else float("nan")
    return {
        "breakeven_spread": s_star,
        "drivers": drivers,
        "spread_slope_per_usd_day": extra_days / d_e,
        "breakeven_hire": h_star,
        "arb": east["netback"] - west["netback"],
    }


def price_cargo(inputs: dict) -> dict:
    """Every route, the breakevens east, the best destination and the lift test."""
    routes = {rid: price_route(inputs, rid) for rid in inputs["routes"]}
    west = routes[EUROPE]
    for rid, r in routes.items():
        if r["market"] == "nea":
            r.update(breakeven(inputs, west, r))
    open_ids = [rid for rid, r in routes.items() if r["open"]]
    east_open = [rid for rid in open_ids if routes[rid]["market"] == "nea"]
    best = max(open_ids, key=lambda rid: routes[rid]["netback"])
    best_east = min(east_open, key=lambda rid: routes[rid]["breakeven_spread"]) if east_open else None
    contract = inputs["contract"]
    threshold = contract["hh_multiple"] * inputs["henry_hub"]
    margin = routes[best]["netback"] - threshold
    return {
        "spread": inputs["jkm"] - inputs["ttf"],
        "routes": routes,
        "best": best,
        "best_east": best_east,
        "lift": {
            "best_netback": routes[best]["netback"],
            "threshold": threshold,
            "margin": margin,
            "margin_after_fee": margin - contract["fee"],
            "lifts": margin >= 0.0,
        },
    }


def with_changes(inputs: dict, **changes) -> dict:
    """A copy of the inputs with top-level values replaced, for scenarios."""
    out = dict(inputs)
    out.update(changes)
    return out


def with_route(inputs: dict, route_id: str, **changes) -> dict:
    """A copy of the inputs with one route's values replaced."""
    routes = dict(inputs["routes"])
    routes[route_id] = dict(routes[route_id], **changes)
    return with_changes(inputs, routes=routes)


def breakeven_line(inputs: dict, route_id: str) -> tuple[float, float]:
    """S* is linear in hire: returns (S* at zero hire, USD/MMBtu per USD a day)."""
    r = price_cargo(with_changes(inputs, hire=0.0))["routes"][route_id]
    return r["breakeven_spread"], r["spread_slope_per_usd_day"]


def canal_question(inputs: dict, canal: str = "panama", long_way: str = "cape") -> dict:
    """What a canal slot is worth against the long way round.

    premium_usd: the extra a ship can pay for its two transits before the long
    way nets the same. wait_days: the days it can wait at each transit instead.
    Both are exact because the netback is linear in cost and in waiting days.
    """
    base = price_cargo(inputs)["routes"]
    lead = base[canal]["netback"] - base[long_way]["netback"]
    wait0 = inputs["routes"][canal].get("wait_days", 0.0)
    one_more = price_cargo(with_route(inputs, canal, wait_days=wait0 + 1.0))["routes"][canal]["netback"]
    per_wait_day = base[canal]["netback"] - one_more
    return {
        "premium_usd": lead * base[canal]["loaded"],
        "wait_days": lead / per_wait_day,
        "cost_of_a_waiting_day_usd": per_wait_day * base[canal]["loaded"],
    }


# ---------------------------------------------------------------------------
# How Spark defines the rate it publishes
# ---------------------------------------------------------------------------

def spark_rate(hire: float, laden_days: float, ballast_days: float, fuel_usd_day: float,
               ballast_bonus_share: float = 1.0, positioning_fee: float = 0.0) -> dict:
    """A charter fixture turned into Spark's round-trip rate.

    The charterer pays hire for the laden days and a ballast bonus: a share of
    the hire and of the fuel of the ballast leg, plus any positioning fee. Spark
    publishes that payment less the ballast fuel, per day of the round trip,
    rounded to 250 USD.
    """
    ballast_fuel = fuel_usd_day * ballast_days
    bonus = ballast_bonus_share * (hire * ballast_days + ballast_fuel)
    payment = hire * laden_days + bonus + positioning_fee
    rate = (payment - ballast_fuel) / (laden_days + ballast_days)
    return {
        "ballast_fuel": ballast_fuel,
        "laden_fuel": fuel_usd_day * laden_days,
        "ballast_bonus": bonus,
        "charterer_payment": payment,
        "rate": rate,
        "rate_rounded": round(rate / 250.0) * 250.0,
    }

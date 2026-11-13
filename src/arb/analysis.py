"""The study's results: the history of the arb, whether cargoes followed, and the lift test.

Nothing is fitted and nothing is forecast. Every observation is one cargo
priced through the engine on its day.
"""

from __future__ import annotations

from datetime import date

import pandas as pd

from . import engine, params
from .inputs import Market

EAST = params.EAST


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------

def price_observation(market: Market, obs: dict) -> dict:
    """One week or month as a cargo: the spread, each route's breakeven line and the lift test."""
    inputs, meta = market.cargo(obs["date"], obs["jkm"], obs["ttf"], obs["period"])
    out = engine.price_cargo(inputs)
    routes = {}
    for rid in EAST:
        r = out["routes"][rid]
        slope = r["spread_slope_per_usd_day"]
        routes[rid] = {
            "at_zero_hire": r["breakeven_spread"] - slope * inputs["hire"],
            "per_usd_day": slope,
            "breakeven": r["breakeven_spread"],
            "status": meta["route_status"][rid]["status"],
            "netback": r["netback"],
        }
    return {
        "date": obs["date"], "period": obs["period"], "basis": obs["basis"],
        "jkm": obs["jkm"], "ttf": obs["ttf"], "spread": out["spread"],
        "hire": inputs["hire"], "hire_status": meta["hire"]["status"], "hire_date": meta["hire"]["date"],
        "des_discount": inputs["des_discount"], "des_status": meta["des_discount_eur_mwh"]["status"],
        "henry_hub": inputs["henry_hub"], "usd_per_eur": meta["usd_per_eur"]["value"],
        "ship": meta["ship"]["id"],
        "routes": routes,
        "netback_europe": out["routes"]["europe"]["netback"],
        "best": out["best"], "best_east": out["best_east"],
        "lift_margin": out["lift"]["margin"], "lift_threshold": out["lift"]["threshold"],
        "best_netback": out["lift"]["best_netback"],
    }


def cheapest_open(row: dict, hire: float | None = None) -> tuple[str | None, float | None]:
    """The open route east with the lowest breakeven at a hire (the row's own by default)."""
    h = row["hire"] if hire is None else hire
    levels = {rid: r["at_zero_hire"] + r["per_usd_day"] * h for rid, r in row["routes"].items() if r["status"] == "open"}
    if not levels:
        return None, None
    rid = min(levels, key=levels.get)
    return rid, levels[rid]


def history(market: Market, period: str) -> list[dict]:
    observations = market.weekly_observations() if period == "week" else market.monthly_observations()
    rows = []
    for obs in observations:
        row = price_observation(market, obs)
        row["route"], row["breakeven"] = cheapest_open(row)
        row["open"] = row["breakeven"] is not None and row["spread"] > row["breakeven"]
        rows.append(row)
    return rows


def spells(rows: list[dict], key: str = "open") -> list[dict]:
    """Runs of consecutive observations where the arb was open."""
    out, start, last = [], None, None
    for row in rows:
        if row[key]:
            start = start or row["date"]
            last = row["date"]
        elif start:
            out.append({"from": start, "to": last})
            start = None
    if start:
        out.append({"from": start, "to": last})
    return out


def history_summary(rows: list[dict], market: Market) -> dict:
    """Counts a sentence can state: how often the arb was open, by hire case and by route."""
    n = len(rows)
    by_route = {}
    for rid in EAST:
        open_rows = [r for r in rows if r["routes"][rid]["status"] == "open"]
        by_route[rid] = {"weeks_route_open": len(open_rows),
                         "arb_open": sum(1 for r in open_rows if r["spread"] > r["routes"][rid]["breakeven"])}
    sunk = 0
    for r in rows:
        _, level = cheapest_open(r, 0.0)
        sunk += level is not None and r["spread"] > level
    return {
        "observations": n, "first": rows[0]["date"], "last": rows[-1]["date"],
        "arb_open": sum(1 for r in rows if r["open"]),
        "arb_open_sunk": sunk,
        "by_route": by_route,
        "mean_breakeven": sum(r["breakeven"] for r in rows if r["breakeven"] is not None) / n,
        "hire_assumed": sum(1 for r in rows if r["hire_status"] == "assumed"),
        "des_assumed": sum(1 for r in rows if r["des_status"] == "assumed"),
    }


# ---------------------------------------------------------------------------
# Flows: did cargoes follow?
# ---------------------------------------------------------------------------

def monthly_flows(market: Market) -> pd.DataFrame:
    """US LNG exports by vessel each departure month, by destination region, from the DOE record."""
    p = market.p["flows"]
    region = {c: "JKM markets" for c in p["jkm_markets"]}
    for name, countries in p["regions"].items():
        region.update({c: name for c in countries})
    cargoes = pd.read_csv(params.DATA / "us_lng_cargoes_doe.csv", parse_dates=["date"])
    cargoes["region"] = cargoes["country"].map(region).fillna("Other")
    cargoes["month"] = cargoes["date"].dt.strftime("%Y-%m")
    table = cargoes.pivot_table(index="month", columns="region", values="mmcf", aggfunc="sum", fill_value=0.0)
    for name in ["JKM markets", "Europe", "Other Asia", "Middle East and Africa", "Americas", "Other"]:
        if name not in table:
            table[name] = 0.0
    table["total"] = table.sum(axis=1)
    table["cargoes"] = cargoes.groupby("month").apply(lambda g: len(g[["date", "tanker"]].drop_duplicates()), include_groups=False)
    table["share_jkm"] = table["JKM markets"] / table["total"]
    table["share_europe"] = table["Europe"] / table["total"]
    table["share_asia"] = (table["JKM markets"] + table["Other Asia"]) / table["total"]
    return table


def flows_test(monthly: list[dict], flows: pd.DataFrame, lag: int) -> dict:
    """Share of cargoes to JKM markets in the months after an open arb and after a closed one.

    The rule is fixed in data/params.json before any result: the verdict of
    month m is set against the cargoes that left in month m + lag.
    """
    pairs = []
    for row in monthly:
        month = pd.Period(row["date"].strftime("%Y-%m"), freq="M") + lag
        key = month.strftime("%Y-%m")
        if key in flows.index and flows.loc[key, "total"] > 0:
            pairs.append({"arb_month": row["date"].strftime("%Y-%m"), "flow_month": key, "open": bool(row["open"]),
                          "margin": row["spread"] - row["breakeven"], "share": float(flows.loc[key, "share_jkm"])})
    frame = pd.DataFrame(pairs)
    open_, closed = frame[frame["open"]], frame[~frame["open"]]
    return {
        "lag": lag, "months": len(frame),
        "open": {"months": len(open_), "mean_share": float(open_["share"].mean()), "median_share": float(open_["share"].median())},
        "closed": {"months": len(closed), "mean_share": float(closed["share"].mean()), "median_share": float(closed["share"].median())},
        "difference": float(open_["share"].mean() - closed["share"].mean()),
        "correlation": float(frame["margin"].corr(frame["share"])),
        "pairs": pairs,
    }


# ---------------------------------------------------------------------------
# The lift test
# ---------------------------------------------------------------------------

def lift_history(monthly: list[dict], flows: pd.DataFrame, cancelled: dict, first: str = "2019-01", last: str = "2021-03") -> list[dict]:
    """Each month: the netback sold in Europe and sold in Asia less 115 percent of Henry Hub,
    with the cargoes that left and those cancelled. A month with no price keeps its cargoes."""
    priced = {row["date"].strftime("%Y-%m"): row for row in monthly}
    out = []
    for month in pd.period_range(first, last, freq="M").strftime("%Y-%m"):
        row = priced.get(month)
        east = [x["netback"] for x in row["routes"].values() if x["status"] == "open"] if row else []
        out.append({
            "month": month,
            "threshold": row["lift_threshold"] if row else None,
            "margin": row["lift_margin"] if row else None,
            "margin_europe": row["netback_europe"] - row["lift_threshold"] if row else None,
            "margin_asia": max(east) - row["lift_threshold"] if east else None,
            "cargoes": int(flows.loc[month, "cargoes"]) if month in flows.index else 0,
            "cancelled": cancelled.get(month, 0),
        })
    return out


# ---------------------------------------------------------------------------
# The canal question
# ---------------------------------------------------------------------------

def canal_curve(inputs: dict, hires: list[float]) -> list[dict]:
    """What a Panama slot is worth against the Cape at each charter rate."""
    out = []
    for h in hires:
        q = engine.canal_question(engine.with_changes(inputs, hire=float(h)))
        out.append({"hire": float(h), "premium_usd": q["premium_usd"], "wait_days": q["wait_days"]})
    return out


def reroute_table(inputs: dict, scenarios: dict) -> list[dict]:
    """The reroute level of each route east at zero, low, central and high hire, and its breakeven hire."""
    base = engine.price_cargo(inputs)["routes"]
    rows = []
    for rid in EAST:
        a, b = engine.breakeven_line(inputs, rid)
        rows.append({"route": rid, "open": base[rid]["open"], "sunk": a,
                     "low": a + b * scenarios["low"], "central": a + b * scenarios["central"], "high": a + b * scenarios["high"],
                     "today": base[rid]["breakeven_spread"], "breakeven_hire": base[rid]["breakeven_hire"]})
    return rows


def iso(value):
    """Dates to text, for JSON."""
    if isinstance(value, (date, pd.Timestamp)):
        return str(value)[:10]
    if isinstance(value, dict):
        return {k: iso(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [iso(v) for v in value]
    return value

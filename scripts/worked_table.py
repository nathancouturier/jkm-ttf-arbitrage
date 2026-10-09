"""Print the worked dates: every input with its source, every cost line east and west, the result.

Usage, from the repository root:

    PYTHONPATH=src python scripts/worked_table.py

Reads only the committed data and the parameter table; fetches nothing and
writes nothing. A date with no reported charter rate within
two weeks is shown at the low, central and high hire the freight anchors give.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from datetime import date  # noqa: E402

from lngarb import cases, config, delivery, worked  # noqa: E402
from lngarb.freight_anchors import hire_levels  # noqa: E402

ROUTES = (cases.WEST,) + cases.EAST
NAMES = {"nwe_direct": "Gate, direct", "nea_panama": "Futtsu, Panama", "nea_suez": "Futtsu, Suez",
         "nea_cape": "Futtsu, Cape"}


def money(value: float) -> str:
    return format(value, ",.0f")


def price(value: float) -> str:
    return format(value, ",.3f")


def lines_table(result: dict) -> list[str]:
    columns = [result["west"]] + [result["east"][r] for r in cases.EAST]
    out = ["| line | " + " | ".join(NAMES[c["route"]] for c in columns) + " |",
           "|---|" + "---|" * len(columns)]

    def row(label, fn):
        out.append("| %s | %s |" % (label, " | ".join(fn(c) for c in columns)))

    row("open", lambda c: "yes" if c["open"] else "no: " + c["why_closed"])
    row("distance, nm, each way", lambda c: format(c["distance_nm"], ",.1f"))
    row("days laden", lambda c: format(c["days_laden"], ".2f"))
    row("days ballast", lambda c: format(c["days_ballast"], ".2f"))
    row("days, round trip", lambda c: format(c["days_total"], ".2f"))
    row("loaded, MMBtu", lambda c: money(c["q_load_mmbtu"]))
    row("boiled off or burnt, MMBtu", lambda c: money(c["gas_used_mmbtu"]))
    row("delivered, MMBtu", lambda c: money(c["q_delivered_mmbtu"]))
    row("hire, $", lambda c: money(c["hire_usd"]))
    row("ports, $", lambda c: money(c["port_usd"]))
    row("canal laden, $", lambda c: money(c["canal_laden_usd"]))
    row("canal ballast, $", lambda c: money(c["canal_ballast_usd"]))
    row("EU ETS, $", lambda c: money(c["ets_usd"]))
    row("financing, $", lambda c: money(c["financing_usd"]))
    row("total cost, $", lambda c: money(c["cost_usd"]))
    row("DES price, $/MMBtu", lambda c: price(c["p_des"]))
    row("netback at Sabine Pass, $/MMBtu", lambda c: price(c["netback"]))
    row("freight, market convention, $/MMBtu delivered", lambda c: price(c["freight_conventional"]))
    row("netback, market convention, $/MMBtu", lambda c: price(c["netback_conventional"]))
    row("arb against Gate, $/MMBtu", lambda c: price(c["arb"]) if "arb" in c else "")
    row("breakeven spread S*, $/MMBtu", lambda c: price(c["s_star"]) if "s_star" in c else "")
    row("of which boil-off", lambda c: price(c["boil_off"]) if "boil_off" in c else "")
    row("of which regas", lambda c: price(c["regas"]) if "regas" in c else "")
    row("of which voyage", lambda c: price(c["voyage"]) if "voyage" in c else "")
    row("breakeven hire H*, $/day", lambda c: money(c["h_star_usd_day"]) if "h_star_usd_day" in c else "")
    return out


def summary(result: dict) -> str:
    return (
        "JKM - TTF %s $/MMBtu. Best: %s via %s, %s $/MMBtu at Sabine Pass. Lift margin %s $/MMBtu "
        "(cancel: %s); full margin %s." % (
            price(result["spread"]), result["best_destination"], NAMES[result["best_route"]],
            price(result["best_netback"]), price(result["lift_margin"]),
            "yes" if result["cancel"] else "no", price(result["full_margin"]))
    )


def one_date(item: worked.WorkedDate) -> list[str]:
    out = ["## %s, %s" % (item.label, item.day), ""]
    reported, _ = worked.nearest_hire(item.day)
    hire = None if reported is not None else hire_levels()["central"]
    inputs = worked.inputs_for(item, hire_usd_day=hire)
    out.append("Inputs:")
    out.append("")
    out.append("* JKM %s $/MMBtu: %s" % (price(inputs.jkm), inputs.sources["jkm"]))
    out.append("* TTF %s $/MMBtu: %s" % (price(inputs.ttf), inputs.sources["ttf"]))
    out.append("* regas discount %s $/MMBtu: %s" % (price(inputs.delta_nwe), inputs.sources["delta_nwe"]))
    out.append("* hire %s $/day: %s" % (money(inputs.hire_usd_day), inputs.sources["hire"] if reported is not None
                                         else "no reported rate within two weeks; the central of the freight anchors"))
    out.append("* Henry Hub %s $/MMBtu: %s" % (price(inputs.henry_hub), inputs.sources["henry_hub"]))
    out.append("* ship: %s" % inputs.vessel.name)
    if item.prices != "monthly":
        tag, share = delivery.week_alignment(date.fromisoformat(item.day))
        out.append("* delivery months of the week's front-month prices: %s (%s of the trading days name "
                   "the same month for JKM and TTF)" % (tag, format(share, ".0%")))
    else:
        out.append("* delivery months: monthly averages, no front-month alignment applies")
    out.append("* EUR/USD: %s" % inputs.sources["fx"])
    out.append("* overnight rate %s %% plus %s bp: %s" % (inputs.rate_percent, inputs.spread_bp, inputs.sources["rate"]))
    out.append("* EU ETS phase %s, %s $/t, %s t CO2e per t of LNG: %s" % (
        inputs.ets_phase, "no price read" if inputs.eua_usd_t is None else format(inputs.eua_usd_t, ",.2f"),
        format(inputs.tco2_per_t_lng, ".5f"), inputs.sources["eua"]))
    for route_id in cases.EAST:
        note = inputs.routes[route_id].canal_note
        if note:
            out.append("* %s: %s" % (NAMES[route_id], note))
    out.append("")
    result = cases.evaluate(inputs)
    out.extend(lines_table(result))
    out.append("")
    out.append(summary(result))
    out.append("")
    out.append("Sensitivity:")
    out.append("")
    if reported is None:
        for level, value in hire_levels().items():
            r = cases.evaluate(worked.inputs_for(item, hire_usd_day=value))
            out.append("* hire %s (%s $/day): %s" % (level, money(value), summary(r)))
    deltas = [-3.0, 0.0] + ([-35.0] if worked.wide_regas_discount_on(item.day) else [])
    for delta in deltas:
        r = cases.evaluate(worked.inputs_for(item, hire_usd_day=hire, delta_nwe_eur_mwh=delta))
        s_star = ", ".join("%s S* %s" % (NAMES[k], price(v["s_star"])) for k, v in r["east"].items())
        out.append("* regas discount %s EUR/MWh: %s. %s" % (delta, s_star, summary(r)))
    for name in ("liquefaction_fee_low_usd_mmbtu", "liquefaction_fee_high_usd_mmbtu"):
        fee = config.PARAMETERS[name].value
        r = cases.evaluate(worked.inputs_for(item, hire_usd_day=hire, liquefaction_fee=fee))
        out.append("* fixed fee %s $/MMBtu: lift margin %s, full margin %s $/MMBtu" % (
            fee, price(r["lift_margin"]), price(r["full_margin"])))
    if inputs.routes["nea_suez"].canal_laden_usd:
        for scnt in (85_000.0, 112_148.0):
            r = cases.evaluate(worked.inputs_for(item, hire_usd_day=hire, suez_scnt=scnt))
            suez = r["east"]["nea_suez"]
            out.append("* Suez tonnage %s SCNT: Suez canal cost %s $, S* %s" % (
                money(scnt), money(suez["canal_laden_usd"] + suez["canal_ballast_usd"]), price(suez["s_star"])))
        r = cases.evaluate(worked.inputs_for(item, hire_usd_day=hire, suez_rebate_on_surcharge=True))
        suez = r["east"]["nea_suez"]
        out.append("* Suez rebate also on the surcharge: Suez canal cost %s $, S* %s" % (
            money(suez["canal_laden_usd"] + suez["canal_ballast_usd"]), price(suez["s_star"])))
    out.append("")
    return out


def main() -> int:
    out = ["# Worked dates", ""]
    for item in worked.WORKED_DATES:
        out.extend(one_date(item))
    sys.stdout.write("\n".join(out) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

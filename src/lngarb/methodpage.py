"""The Method view's data: how a cargo is priced, every parameter with its source, and what the study cannot see.

The view is the short form of docs/methodology.md, which it links: the engine
as formulas, each with what it means; the table of every parameter in
lngarb.config.PARAMETERS, in words, with its value, status, source, link, the
day it was read and its note; the units and conversions; the delivery months
of the front-month prices; exact against conventional freight; the limits of
the study; and the credits. Figures in sentences are value segments, so the
page formats them as everywhere else; a parameter's value is shown as the
table's own words, built here from the value and its unit.
"""

from __future__ import annotations

import math
from datetime import date
from typing import Any, Callable, Mapping

from . import config, freight_anchors, reader, units

__all__ = ["page", "PARAMETER_WORDS", "value_words", "REPOSITORY"]

#: The repository, where the licence and the notices show as documents: as
#: files without an extension, the site itself would hand them over as
#: downloads.
REPOSITORY = "https://github.com/nathancouturier/jkm-ttf-arbitrage"

#: Each parameter in words, by its name in the table.
PARAMETER_WORDS: Mapping[str, str] = {
    "mmbtu_per_m3_lng": "Energy of a cubic metre of LNG",
    "vessel_174k_capacity_m3": "Capacity of the two-stroke carrier",
    "vessel_174k_boil_off_per_day": "Boil-off of the two-stroke carrier",
    "vessel_174k_speed_kn": "Speed of the two-stroke carrier",
    "vessel_160k_capacity_m3": "Capacity of the TFDE carrier",
    "vessel_160k_boil_off_per_day": "Boil-off of the TFDE carrier",
    "vessel_160k_speed_kn": "Speed of the TFDE carrier",
    "fill": "Cargo loaded, share of capacity",
    "load_days": "Days to load",
    "discharge_days": "Days to discharge",
    "spark30_flex_days": "Flex days in Spark30, used only for Spark's example",
    "funding_spread_bp": "Funding spread over the overnight rate",
    "panama_capacity_is_nominal": "Panama tolls on the nominal capacity",
    "panama_fresh_water_fixed_usd": "Panama fresh water surcharge, fixed part",
    "panama_fresh_water_variable_share": "Panama fresh water surcharge, share of tolls",
    "vessel_174k_from": "First day of the two-stroke benchmark carrier",
    "port_cost_west_usd": "Port costs, Sabine Pass and Gate",
    "port_cost_east_usd": "Port costs, Sabine Pass and Futtsu",
    "delta_nwe_eur_mwh": "Europe's DES spread to TTF where ACER published too little",
    "delta_nwe_min_coverage": "Least share of a span's weekdays ACER must cover",
    "hire_anchor_max_days": "Furthest a reported charter rate may lie from a date",
    "delta_nwe_wide_window": "Weeks of 2022 when Europe's DES spread ran wide",
    "panama_open_to_lng_from": "First day Panama's expanded locks were open to LNG carriers",
    "suez_closed_to_us_cargo_from": "First day Suez is treated as closed to a US cargo",
    "spa_henry_hub_multiple": "Contract price, multiple of Henry Hub",
    "liquefaction_fee_usd_mmbtu": "Liquefaction fee",
    "liquefaction_fee_low_usd_mmbtu": "Liquefaction fee, lowest in the contracts read",
    "liquefaction_fee_high_usd_mmbtu": "Liquefaction fee, highest in the contracts read",
    "cancellation_notice_day": "Day of the notice to cancel a cargo",
    "ets_voyage_share": "EU ETS share of a voyage between an EU and a non-EU port",
    "ets_berth_share": "EU ETS share of emissions at an EU berth",
    "ets_phase_in_by_year": "EU ETS share of verified emissions surrendered, by year",
    "tco2_per_t_lng": "Carbon dioxide per tonne of LNG burnt",
    "tn2o_per_t_lng": "Nitrous oxide per tonne of LNG burnt",
    "ets_ch4_n2o_from": "First day methane and nitrous oxide count in the EU ETS",
    "gwp_ch4": "Global warming potential of methane",
    "gwp_n2o": "Global warming potential of nitrous oxide",
    "methane_slip_174k": "Methane slip of the two-stroke carrier",
    "methane_slip_160k": "Methane slip of the TFDE carrier",
    "methane_slip_on": "Methane slip counted",
    "mmbtu_per_t_lng": "Energy of a tonne of LNG",
    "eua_eur_t_after_published": "EU allowance price after the last month published",
    "suez_scnt_per_m3": "Suez Canal net tonnage per cubic metre of capacity",
    "panama_booking_fee_usd": "Panama booking fee",
    "panama_waits_reported": "Waits reported at Panama for LNG",
    "analysis_monthly_loading_day": "Loading day of a monthly observation",
    "analysis_min_weeks_per_month": "Least weekly averages for a monthly observation",
    "analysis_first_month": "First month of the monthly history",
    "analysis_excluded_years": "Years left out of the second sample",
}


def _number(value: float) -> str:
    """A figure with thousands grouped and no trailing zeros."""
    if float(value).is_integer():
        return format(int(value), ",")
    text = format(value, ",.6f").rstrip("0").rstrip(".")
    return text


def _day(value: str) -> str:
    return reader.day_label(date.fromisoformat(value)) if len(value) == 10 else reader.month_label(
        date.fromisoformat(value + "-01"))


def value_words(value: Any, unit: str) -> str:
    """A parameter's value as the table shows it, from its value and unit."""
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, dict):
        if unit.startswith("share"):
            return "; ".join("%s percent from %s" % (_number(float(v) * 100.0), k) for k, v in sorted(value.items()))
        return "; ".join("%s days in %s" % (_number(float(v)), _day(k)) for k, v in sorted(value.items()))
    if isinstance(value, (tuple, list)):
        if all(isinstance(v, str) for v in value):
            return " to ".join(_day(v) for v in value)
        return reader.listed([str(v) for v in value])
    if isinstance(value, str):
        try:
            return _day(value)
        except ValueError:
            return "the price of " + value + ", held" if unit.startswith("EUR per") else value
    if unit.startswith("share") and "percent" not in unit:
        return _number(float(value) * 100.0) + " percent " + unit[len("share"):].strip()
    if unit == "flag":
        return "yes" if value else "no"
    if unit == "days" and float(value) == 1.0:
        return "1 day"
    if unit.startswith("day of the month"):
        number = int(value)
        suffix = "th" if 10 <= number % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
        return "the %d%s of the month%s" % (number, suffix, unit[len("day of the month"):])
    return _number(float(value)) + " " + unit


def _formulas() -> list[dict[str, Any]]:
    """The engine, formula by formula, each with what it means."""
    multiple = config.PARAMETERS["spa_henry_hub_multiple"].value
    return [
        {"formula": "Q_load = V x fill x K",
         "segments": [reader.T("The MMBtu loaded: a carrier of capacity V cubic metres, loaded to the share fill, at K "
                               "MMBtu a cubic metre.")]},
        {"formula": "G = Q_load x BOR x T_total;  Q_del = Q_load - G",
         "segments": [reader.T("The gas used, boiled off or burnt every day of the round trip at the rate BOR, and the "
                               "cargo delivered; the heel for the way back stays on board. Spark's rate, the hire "
                               "below, is what a charterer pays less the ballast fuel over the round trip, an "
                               "owner's earnings rate, so taking it as hire with the heel in G counts the ballast "
                               "fuel once, never twice.")]},
        {"formula": "C(d, r) = hire x T_total + port(d) + canal(r) + slot premium(r) + ets(d, r) + financing(r)",
         "segments": [reader.T("The voyage's cost to destination d by route r: hire for the whole round trip, the "
                               "ports, the canal both ways, any slot premium, the EU ETS on a voyage into Northwest "
                               "Europe and the financing of the cargo for the laden days.")]},
        {"formula": "NB(d, r) = (P_des(d) x Q_del(r) - C(d, r)) / Q_load",
         "segments": [reader.T("The netback at Sabine Pass per MMBtu loaded, with P_des the delivered price: TTF "
                               "plus Europe's DES spread, delta_nwe, at Gate, and JKM at Futtsu.")]},
        {"formula": "arb(r) = NB(NEA, r) - NB(NWE)",
         "segments": [reader.T("How much more a cargo nets in Northeast Asia by route r than at Gate.")]},
        {"formula": "S*(r) = boil-off + regas + voyage",
         "segments": [reader.T("The spread of JKM over TTF at which route r nets what Gate does, in three parts: the "
                               "gas the longer voyage burns, valued at TTF; Europe's DES spread, which a cargo sold "
                               "east escapes; and the extra cost of the voyage per MMBtu delivered.")]},
        {"formula": "H*(r) = [JKM x Q_del(r) - (TTF + delta_nwe) x Q_del(NWE) - (C_x(r) - C_x(NWE))] / (T_total(r) - T_total(NWE))",
         "segments": [reader.T("The hire at which the two net the same; C_x is the cost without hire. A reported hire "
                               "below it means the arb was open at the market's own freight.")]},
        {"formula": "lift margin = best netback - m x HH",
         "segments": [reader.T("The lift test: a cargo is lifted while the best netback covers the contract price, "
                               "m times Henry Hub, with m at "), reader.N("hh_multiple", multiple, "share"),
                      reader.T("; the liquefaction fee is owed either way, so it never decides.")]},
        {"formula": "NB_conv = P_des - (C + P_ref x G) / Q_del",
         "segments": [reader.T("The conventional netback, freight quoted per MMBtu delivered with the fuel at a "
                               "reference price; the study uses the exact form and shows both for the latest week.")]},
    ]


#: The energy of a cubic metre of LNG the sensitivity runs: the market's range
#: for a lean to a rich cargo, the study's value in the middle.
K_SENSITIVITY = (22.0, 23.0, 24.0)

ROUTE_ORDER = ("nea_panama", "nea_suez", "nea_cape")


def k_sensitivity(day: date, evaluate_at: Callable[[float], Mapping[str, Any]]) -> dict[str, Any]:
    """The latest week at 22, 23 and 24 MMBtu a cubic metre: the best netback,
    and the arb and S* of each open route east, so the reader sees how much
    the convention moves the answer."""
    rows = []
    for k in K_SENSITIVITY:
        out = evaluate_at(k)
        rows.append({
            "k": k, "best_netback": out["best_netback"],
            "routes": {r: {"arb": out["east"][r]["arb"], "s_star": out["east"][r]["s_star"]}
                       for r in ROUTE_ORDER if r in out["east"] and out["east"][r]["open"]},
        })
    open_routes = list(rows[0]["routes"])
    spread_s = [max(abs(rows[-1]["routes"][r]["s_star"] - rows[0]["routes"][r]["s_star"]) for r in open_routes)] \
        if open_routes else []
    caption = [reader.T("The week to "), reader.D("as_of", day),
               reader.T(" at each energy content: the best netback, and the arb and S* of each open route east, "
                        "in $/MMBtu.")]
    if spread_s:
        caption += [reader.T(" From the lean end to the rich, S* moves by "),
                    reader.N("k_s_star_range", spread_s[0], "usd_mmbtu"), reader.T(" at most.")]
    return {"rows": rows, "routes": open_routes, "route_names": {r: reader.ROUTE_SHORT[r] for r in open_routes},
            "caption_segments": caption}


def conventional(day: date, result: Mapping[str, Any]) -> dict[str, Any]:
    """The exact netback against the conventional one, route by route, for the latest week."""
    rows = []
    lines = {"nwe_direct": result["west"], **result["east"]}
    for route, line in lines.items():
        if route != "nwe_direct" and not line["open"]:
            continue
        rows.append({"route": route, "name": reader.ROUTE_NAMES[route], "exact": line["netback"],
                     "conventional": line["netback_conventional"],
                     "difference": line["netback"] - line["netback_conventional"]})
    return {"rows": rows, "caption_segments": [
        reader.T("The week to "), reader.D("as_of", day),
        reader.T(": the netback per MMBtu loaded, the exact form the study uses, against the conventional one per "
                 "MMBtu delivered, and the difference, in $/MMBtu.")]}


def page(latest: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """The Method view's whole document body. latest, when given, carries the
    week's tables: the energy content sensitivity and the two netbacks."""
    parameters = []
    for name, parameter in config.PARAMETERS.items():
        parameters.append({
            "key": name,
            "name": PARAMETER_WORDS[name],
            "value_words": value_words(parameter.value, parameter.unit),
            "status": parameter.status,
            "source": reader.dates_in_words(parameter.source),
            "url": parameter.url,
            "read_on": parameter.read_on,
            "note": reader.dates_in_words(parameter.note) if parameter.note else None,
        })
    assumed = sum(p["status"] == "assumption" for p in parameters)
    return {
        "title_segments": [
            reader.T("How a cargo is priced: the engine in "), reader.N("formulas", len(_formulas()), "count"),
            reader.T(" formulas, its "), reader.N("parameters", len(parameters), "count"),
            reader.T(" parameters, "), reader.N("assumed", assumed, "count"),
            reader.T(" of them this study's assumptions, each with its source, and what the study cannot see"),
        ],
        "formulas": _formulas(),
        **({"k_sensitivity": latest["k_sensitivity"], "conventional": latest["conventional"]} if latest else {}),
        "parameters": parameters,
        "parameters_caption": "Every parameter of the engine that is not market data or a canal tariff: its "
                              "value, whether it is published or this study's assumption, the document it is "
                              "read in, the day it was read, and its note. The tariffs behind the tolls are set "
                              "out in the methodology's sections on Suez and Panama. The Model view lets a reader "
                              "type over every one that is an input of a cargo, methane slip included; the "
                              "gas factors, the canals' readings and the analysis's settings are rules or choices "
                              "of the study, not inputs a cargo chooses, and are fixed there.",
        "units": [
            {"words": "MMBtu in a megawatt hour", "value": units.MMBTU_PER_MWH, "format": "mmbtu_per_mwh"},
            {"words": "MMBtu in a cubic metre of LNG", "value": config.PARAMETERS["mmbtu_per_m3_lng"].value,
             "format": "mmbtu_per_m3"},
            {"words": "MMBtu in a tonne of LNG", "value": config.PARAMETERS["mmbtu_per_t_lng"].value,
             "format": "mmbtu_per_t"},
        ],
        "units_segments": [
            reader.T("A price in euros a megawatt hour becomes dollars an MMBtu at the day's rate in the Federal "
                     "Reserve's "), reader.W("fx_release", "H.10"),
            reader.T(": USD/MMBtu = EUR/MWh x USD per EUR / MMBtu per MWh. Every price is in dollars an MMBtu, "
                     "every cost in dollars, every hire in dollars a day."),
        ],
        "delivery_segments": [
            reader.T("JKM futures for a month stop trading in the middle of the month before, and Dutch TTF futures "
                     "two UK business days before the month begins, so from the middle of a month to TTF's last "
                     "trading day the two front months name different delivery months, and after it they agree "
                     "again. A week is aligned when every trading day of "
                     "it names the same month for both, misaligned when none does, and mixed otherwise; the History "
                     "view marks the misaligned and the mixed weeks."),
            reader.T(" A cargo loading on the first of a month reaches Gate in about two weeks and Futtsu via the Cape in "
                     "about six, so the right comparison is each basin's price for its own arrival period; with front "
                     "months only, the study compares the two front months and names them where a price is shown."),
        ],
        "limits": [
            [reader.T("A spread is an association, not a decision: long term contracts with Asian buyers move "
                      "their cargoes whatever the spot economics.")],
            [reader.T("Charter rates are the "), reader.N("anchors", len(freight_anchors.ANCHORS), "count"),
             reader.T(" that Spark and the trade press reported; the study runs every date at the lowest, the "
                      "median and the highest of them, and at the one reported nearest it where one lies within "),
             reader.N("hire_window", config.PARAMETERS["hire_anchor_max_days"].value, "count"),
             reader.T(" days.")],
            [reader.T("Panama's queues enter only the Flows view's comparison of Panama with the Cape, in the "
                      "two months a wait was reported for LNG, and its slots and auctions never; the slot premium "
                      "and the waiting days are inputs the reader can type.")],
            [reader.T("Port costs are Spark's figures of "), reader.D("port_costs", "2022-02-01", "month"),
             reader.T(", held for every year and both ships.")],
            [reader.T("Before "), reader.D("meti_end", "2021-04-01", "month"),
             reader.T(" the monthly JKM is a Japanese spot price, a proxy; from then to "),
             reader.D("weekly_from", "2021-08-01", "month"), reader.T(" no public JKM is held.")],
            [reader.T("The month of the export data is coarser than the decisions, taken weeks before a cargo "
                      "loads.")],
            [reader.T("The pilot fuel a dual fuel engine burns with the gas is left out of the voyage's cost and "
                      "of its emissions.")],
            [reader.T("Panama's booking fee is not an input of its own: the slot premium a reader types carries it, "
                      "with the methodology's cited figures as scenarios.")],
            [reader.T("Futtsu stands for the JKM delivery area and Gate for Northwest Europe; Sabine Pass stands for "
                      "every US Gulf terminal, and the others are out of scope.")],
        ],
        "documents": [
            {"label": "The full methodology", "href": "docs/methodology.md"},
            {"label": "Every source and its terms", "href": "docs/sources.md"},
            {"label": "The questions left open", "href": "docs/open-questions.md"},
            {"label": "The licence of the code", "href": REPOSITORY + "/blob/main/LICENSE"},
            {"label": "The notices of the data", "href": REPOSITORY + "/blob/main/NOTICE"},
            {"label": "The vendored typefaces and map", "href": "vendor/README.md"},
        ],
        "type_words": "The portfolio sets body text in Satoshi, whose licence forbids serving it from a repository; "
                      "this site sets it in Figtree, the openly licensed face closest to it, served from this "
                      "repository with every other file.",
    }

"""The reader's layer of the site's data: the sentences, labels and scales the page prints.

export.py writes the files; this module composes what a reader sees in them.
A sentence is a list of segments, so the page formats every figure itself, with
the decimals the artifact declares, and can trace each one back to the field it
came from:

    T(text)                          words, never a digit
    N(field, value, format)          a number, formatted by the page
    D(field, iso, kind)              a date, ISO for the machine, a label to read
    W(field, word)                   a word that is data: a route, a status

Every clause of the verdict and of each section's summary is chosen by the
values, never by hand: which destination, which route, which part of the
breakeven is largest, whether the lift test passes. The pattern is the sibling
crack-spread-study's.
"""

from __future__ import annotations

import math
import re
from datetime import date
from typing import Any, Callable, Mapping, Sequence

import pandas as pd

__all__ = ["DECIMALS", "T", "N", "D", "W", "header", "conventions", "nice_domain", "ROUTE_NAMES"]

SCHEMA_VERSION = 1
GENERATED_BY = "src/lngarb/export.py"

#: Decimals per format, the one place the page's precision is decided.
DECIMALS: Mapping[str, int] = {
    "usd_mmbtu": 2,
    "eur_mwh": 2,
    "usd_day": 0,
    "usd_per_eur": 4,
    "eur_t": 2,
    "rate_percent": 2,
    "share_percent": 0,
    "pp": 1,
    "days": 1,
    "nm": 0,
    "count": 0,
    "year": 0,
    "t_stat": 2,
    "r2": 2,
}

#: Formats whose values are whole numbers and are written as JSON integers.
INTEGER_FORMATS = ("count", "year")

MONTH_NAMES = (
    "January", "February", "March", "April", "May", "June", "July", "August",
    "September", "October", "November", "December",
)
MONTH_SHORT = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")

#: Every route by its name on the page. The destinations are the ports the
#: distances run to: Gate, Rotterdam, and Futtsu, Tokyo Bay.
ROUTE_NAMES: Mapping[str, str] = {
    "nwe_direct": "Gate",
    "nea_panama": "Futtsu via Panama",
    "nea_suez": "Futtsu via Suez",
    "nea_cape": "Futtsu via the Cape",
}
ROUTE_SHORT: Mapping[str, str] = {"nea_panama": "Panama", "nea_suez": "Suez", "nea_cape": "the Cape"}
#: Line patterns of the routes east, on every chart that draws them.
ROUTE_PATTERNS: Mapping[str, str] = {"nea_panama": "solid", "nea_suez": "dash", "nea_cape": "dot"}

#: The three parts of S*, in words.
PART_WORDS: Mapping[str, str] = {
    "boil_off": "the gas boiled off on the longer voyage",
    "regas": "Europe's regasification discount",
    "voyage": "the longer voyage's hire, canals, ports, carbon and financing",
}


# ---------------------------------------------------------------------------
# Leaves
# ---------------------------------------------------------------------------


def _missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float):
        return math.isnan(value) or math.isinf(value)
    return False


def _iso(value: Any) -> str:
    return pd.Timestamp(value).strftime("%Y-%m-%d")


def day_label(value: Any) -> str:
    stamp = pd.Timestamp(value)
    return "%d %s %d" % (stamp.day, MONTH_NAMES[stamp.month - 1], stamp.year)


def month_label(value: Any) -> str:
    stamp = pd.Timestamp(value)
    return "%s %d" % (MONTH_NAMES[stamp.month - 1], stamp.year)


def short_month_label(value: Any) -> str:
    stamp = pd.Timestamp(value)
    return "%s %d" % (MONTH_SHORT[stamp.month - 1], stamp.year)


def T(text: str) -> dict[str, Any]:
    """Words. Never a figure: a digit in a text segment raises."""
    if any(ch.isdigit() for ch in text):
        raise ValueError("a text segment holds a digit, make it a value segment: %r" % text)
    return {"text": text}


def N(field: str, value: Any, fmt: str, *, signed: bool = False, missing: str | None = None,
      accent: bool = False) -> dict[str, Any]:
    """A number, named by the field it came from, formatted by DECIMALS[fmt]."""
    if fmt not in DECIMALS:
        raise KeyError("no decimals declared for format %r" % fmt)
    number = None if _missing(value) else float(value)
    if number is not None and fmt in INTEGER_FORMATS:
        number = int(round(number))
    out: dict[str, Any] = {"field": field, "value": number, "format": fmt}
    if signed:
        out["signed"] = True
    if missing:
        out["missing"] = missing
    if accent:
        out["accent"] = True
    return out


def D(field: str, value: Any, kind: str = "day") -> dict[str, Any]:
    """A date, ISO for the machine and a label for the sentence."""
    label = {"day": day_label, "month": month_label, "short_month": short_month_label}[kind](value)
    return {"field": field, "value": _iso(value), "label": label}


def W(field: str, word: str) -> dict[str, Any]:
    """A word that is data: a route, a status, a publisher."""
    return {"field": field, "value": word, "label": word}


def plural(count: int, one: str, many: str) -> str:
    return one if count == 1 else many


def header(artifact: str, data_date: Any, describes: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact": artifact,
        "generated_by": GENERATED_BY,
        "data_date": _iso(data_date),
        "describes": describes,
        "source": "the committed caches in data/cache and data/seed and the manifest, nothing from data/private; no network",
    }


def conventions() -> dict[str, Any]:
    return {
        "missing": "A missing value is JSON null. null never means zero and is never drawn as zero or bridged; the page shows a gap and says why.",
        "decimals": dict(DECIMALS),
        "rounding": "now.json keeps full precision, because the browser engine recomputes from its inputs; history.json and flows.json store floats to 6 places. The page prints the decimals of the format a value names.",
        "segments": "A sentence is a list of segments. A text segment holds words only. A value segment names its field and holds a value with a format, or an ISO date or a word with its label.",
    }


# ---------------------------------------------------------------------------
# Scales
# ---------------------------------------------------------------------------

LADDER = (1.0, 2.0, 5.0, 10.0)


def tick_step(low: float, high: float, count: int) -> float:
    """The round step for about `count` intervals across a span: the page's own rule."""
    if not high > low or count <= 0:
        return 0.0
    rough = (high - low) / count
    magnitude = 10.0 ** math.floor(math.log10(rough))
    for rung in LADDER:
        if magnitude * rung >= rough:
            return magnitude * rung
    return magnitude * LADDER[-1]


def nice_domain(values: Sequence[float], count: int, *, zero: bool = True) -> tuple[float, float, float]:
    """[low, high] widened outward to the tick step, zero inside when asked, and
    the step. The page ticks on this step (src/charts.js), so both ends of an
    axis fall on a tick."""
    finite = [v for v in values if not _missing(v)]
    if zero:
        finite.append(0.0)
    low, high = min(finite), max(finite)
    if high == low:
        high = low + 1.0
    step = tick_step(low, high, count)
    return math.floor(low / step) * step, math.ceil(high / step) * step, step


def regas_words(delta: float) -> dict[str, str]:
    """The words for Europe's DES spread to TTF by its sign: a discount a cargo
    sold at Gate bears and one sold east escapes, or, when ACER prices a cargo
    in Northwest Europe above TTF, a premium a cargo sold at Gate earns and one
    sold east forgoes."""
    if delta > 0:
        return {"name": "DES premium in Northwest Europe", "part": "the DES premium Europe pays",
                "step": "Europe's DES premium, forgone", "short": "Europe's DES premium",
                "gate": "a cargo sold at Gate earns it"}
    return {"name": "Regasification discount", "part": "Europe's regasification discount",
            "step": "Europe's regasification discount, escaped", "short": "Europe's regasification discount",
            "gate": "a cargo sold at Gate bears it"}


def capitalised(words: str) -> str:
    return words[:1].upper() + words[1:]


def listed(words: Sequence[str]) -> str:
    """"a", "a and b", "a, b and c"."""
    words = list(words)
    if len(words) < 2:
        return "".join(words)
    return ", ".join(words[:-1]) + " and " + words[-1]


# ---------------------------------------------------------------------------
# The Now view
# ---------------------------------------------------------------------------


def _closed_reason(why: str) -> str:
    """The reason a route is closed, without the engine's transit date."""
    return why.split(": ", 1)[1] if ": " in why else why


def _cheapest_open(result: Mapping[str, Any]) -> str | None:
    """The open route east that needs the least premium; on a tie, the first."""
    best = None
    for route, lines in result["east"].items():
        if lines["open"] and not _missing(lines["s_star"]):
            if best is None or lines["s_star"] < result["east"][best]["s_star"]:
                best = route
    return best


def _dominant_part(lines: Mapping[str, Any]) -> str:
    parts = {name: lines[name] for name in ("boil_off", "regas", "voyage")}
    return max(parts, key=lambda name: (abs(parts[name]), -list(parts).index(name)))


def verdict(result: Mapping[str, Any], day: date, hh_multiple: float, *, delta_nwe: float,
            liquefaction_fee: float) -> dict[str, Any]:
    """The landing sentence: where the cargo nets more and by how much, JKM
    against TTF against the spread at which the cheapest open route east breaks
    even and the part that dominates it, and the lift test, then the margin net
    of the liquefaction fee too."""
    west, east = result["west"], result["east"]
    best_route = result["best_route"]
    segments = [
        T("A cargo loading at Sabine Pass in the week to "), D("as_of", day),
        T(" nets "), N("best_netback", result["best_netback"], "usd_mmbtu"),
        T(" $/MMBtu delivered to "), W("best_route_name", ROUTE_NAMES[best_route]),
    ]
    values: dict[str, Any] = {"best_route": best_route, "best_netback": result["best_netback"]}
    if result["best_destination"] == "NEA":
        gap = result["best_netback"] - west["netback"]
        values["gap"] = gap
        segments += [T(", "), N("gap_to_gate", gap, "usd_mmbtu"), T(" more than at Gate. ")]
    elif result["best_route_east"]:
        other = result["best_route_east"]
        gap = west["netback"] - east[other]["netback"]
        values["gap"] = gap
        segments += [T(", "), N("gap_to_east", gap, "usd_mmbtu"), T(" more than at "),
                     W("best_east_name", ROUTE_NAMES[other]), T(", the best open route east. ")]
    else:
        segments += [T("; no route east is open to a US cargo. ")]

    cheapest = _cheapest_open(result)
    spread = result["spread"]
    segments += [T("JKM is "), N("spread", abs(spread), "usd_mmbtu"), T(" above TTF" if spread >= 0 else " below TTF")]
    if cheapest:
        lines = east[cheapest]
        part = _dominant_part(lines)
        words = dict(PART_WORDS, regas=regas_words(delta_nwe)["part"])
        values.update({"cheapest_route": cheapest, "s_star": lines["s_star"], "dominant_part": part,
                       "dominant_value": lines[part]})
        segments += [
            T(", and the cheapest open route east, via "), W("cheapest_route", ROUTE_SHORT[cheapest]),
            T(", breaks even at a spread of "), N("s_star", lines["s_star"], "usd_mmbtu", signed=True),
            T("; the largest part of that is "), W("dominant_part", words[part]), T(", "),
            N("dominant_value", lines[part], "usd_mmbtu", signed=True), T(". "),
        ]
    else:
        segments += [T(". ")]

    margin = result["lift_margin"]
    values["lift_margin"] = margin
    percent = N("hh_multiple_percent", hh_multiple * 100.0, "count")
    if margin >= 0:
        values["full_margin"] = result["full_margin"]
        segments += [T("The best destination clears "), percent, T(" percent of Henry Hub by "),
                     N("lift_margin", margin, "usd_mmbtu"), T("; net of the liquefaction fee of "),
                     N("liquefaction_fee", liquefaction_fee, "usd_mmbtu"), T(" as well, its margin is "),
                     N("full_margin", result["full_margin"], "usd_mmbtu", signed=True), T(".")]
    else:
        segments += [T("The best destination falls short of "), percent, T(" percent of Henry Hub by "),
                     N("lift_margin", -margin, "usd_mmbtu"), T(", so a cargo would not be lifted.")]
    return {"values": values, "segments": segments}


def _weekly_series_words(series: str) -> str:
    return {
        "wngsr": "EIA's Weekly Natural Gas Storage Report, international supplement",
        "ngwu": "EIA's Natural Gas Weekly Update",
    }[series]


def data_dates(*, day: date, week: Mapping[str, Any], inputs, usd_per_eur: tuple[float, date],
               hh: Mapping[str, Any], hire: Mapping[str, Any], delta: Mapping[str, Any] | None,
               delta_window: tuple[date, date], eua: Mapping[str, Any], rate: tuple[float, date, str],
               fronts: Mapping[str, date], eur_mwh: Callable[[float], float],
               not_priced: Sequence[Mapping[str, Any]] = ()) -> list[dict[str, Any]]:
    """One sentence per input, each with its figure, date and source, and the
    status word where the input is preliminary, inferred or held. A later week
    the data cannot price yet comes first, named with what it lacks."""
    source = _weekly_series_words(week["series"])
    rows = []
    for later in not_priced:
        rows.append({"id": "not_priced", "segments": [
            T("The week to "), D("not_priced_week", later["week_ending"]), T(" is "),
            W("not_priced_status_word", "not priced yet"), T(": "), W("not_priced_reason", later["reason"]),
            T(". Every figure here is for the week to "), D("as_of", day), T("."),
        ]})
    rows.append({"id": "jkm", "segments": [
        T("JKM "), N("jkm", inputs.jkm, "usd_mmbtu"), T(" $/MMBtu, the week ending "), D("jkm_date", day),
        T(", from "), W("jkm_source", source), T("."),
    ]})
    ttf = [
        T("TTF "), N("ttf", inputs.ttf, "usd_mmbtu"), T(" $/MMBtu, or "),
        N("ttf_eur_mwh", eur_mwh(inputs.ttf), "eur_mwh"), T(" EUR/MWh, the same week and source"),
    ]
    if week["alignment"] == "aligned":
        ttf += [T("; both front months were for "), D("delivery_month", fronts["ttf"], "month"),
                T(" delivery every day of the week.")]
    else:
        ttf += [T("; the two front months named the same delivery month on "),
                N("aligned_share", (week["aligned_share"] or 0.0) * 100.0, "share_percent"),
                T(" percent of the week's days, so the week is "), W("alignment_status_word", week["alignment"]),
                T(".")]
    rows.append({"id": "ttf", "segments": ttf})

    hh_segments = [
        T("Henry Hub "), N("henry_hub", hh["value"], "usd_mmbtu"), T(" $/MMBtu, the average of "),
        N("hh_days", hh["days"], "count"), T(plural(hh["days"], " day of ", " days of ")),
        D("hh_month", hh["month"], "month"),
    ]
    if hh["incomplete"]:
        hh_segments += [T(" to "), D("hh_last", hh["last_held"]), T(", "),
                        W("hh_status_word", "an incomplete month"), T(", of EIA's daily spot price, ")]
    else:
        hh_segments += [T(", of EIA's daily spot price, ")]
    hh_segments += [W("hh_proxy_status_word", "a proxy"), T(" for the NYMEX settlement the contracts name.")]
    rows.append({"id": "henry_hub", "segments": hh_segments})

    anchor = hire["anchor"]
    if hire["reported"]:
        hire_segments = [
            T("Hire "), N("hire", hire["value"], "usd_day"), T(" $/day, "), W("assessment", anchor.assessment),
            T(" for a "), W("vessel", anchor.vessel), T(" carrier, "),
        ]
        if anchor.rate_date:
            hire_segments += [T("the rate for "), D("hire_date", hire["date"]), T(" as reported by "),
                              W("publisher", anchor.publisher)]
        else:
            hire_segments += [T("reported by "), W("publisher", anchor.publisher), T(", in an article of "),
                              D("hire_date", hire["date"])]
        inferred = [what for what, stated in (("the assessment", anchor.assessment_stated),
                                              ("the ship", anchor.vessel_stated)) if not stated]
        if inferred:
            hire_segments += [T("; "), W("hire_status_word", " and ".join(inferred) + " inferred"),
                              T(" from the article")]
        hire_segments += [T(".")]
    else:
        hire_segments = [
            T("Hire "), N("hire", hire["value"], "usd_day"),
            T(" $/day, the central level of the reported rates, "),
            W("hire_status_word", "an assumption"), T(": no rate was reported within "),
            N("hire_max_days", hire["max_days"], "count"), T(" days of "), D("hire_day", day),
            T("; the nearest is dated "), D("hire_nearest_date", hire["date"]), T(", "),
            N("hire_gap_days", hire["gap"], "count"), T(" days away."),
        ]
    rows.append({"id": "hire", "segments": hire_segments})

    words = regas_words(inputs.delta_nwe)
    if delta is not None:
        regas = [
            T(words["name"] + " "), N("delta_nwe", inputs.delta_nwe, "usd_mmbtu", signed=True),
            T(" $/MMBtu, or "), N("delta_nwe_eur_mwh", delta["value"], "eur_mwh", signed=True),
            T(" EUR/MWh: ACER's DES Northwest Europe assessment less the TTF front month, the mean of "),
            N("delta_days", delta["days"], "count"), T(" of the "), N("delta_weekdays", delta["weekdays"], "count"),
            T(" weekdays from "), D("delta_first", delta["start"]), T(" to "), D("delta_last", delta["end"]),
            T("; " + words["gate"] + "."),
        ]
    else:
        regas = [
            T(words["name"] + " "), N("delta_nwe", inputs.delta_nwe, "usd_mmbtu", signed=True),
            T(" $/MMBtu, "), W("regas_status_word", "an assumption"),
            T(": ACER published its assessment on too few weekdays from "), D("delta_first", delta_window[0]),
            T(" to "), D("delta_last", delta_window[1]), T("; " + words["gate"] + "."),
        ]
    rows.append({"id": "regas_discount", "segments": regas})

    eua_words = {
        "commission": [T(", the European Commission's auction average for "), D("eua_month", eua["price_month"], "month")],
        "german": [T(", the average of Germany's auctions on EEX for "), D("eua_month", eua["price_month"], "month"),
                   T(", a proxy for the EU price")],
        "held": [T(", the average of Germany's auctions on EEX for "), D("eua_month", eua["price_month"], "month"),
                 T(", "), W("eua_status_word", "held"), T(" as no later month is published")],
    }[eua["kind"]]
    rows.append({"id": "also", "segments": [
        T("Also used: "), N("usd_per_eur", usd_per_eur[0], "usd_per_eur"), T(" USD per EUR, the Federal Reserve's "),
        W("fx_release", "H.10"), T(" rate of "),
        D("fx_date", usd_per_eur[1]), T("; an EU allowance at "), N("eua", eua["value"], "eur_t"), T(" EUR/t"),
        *eua_words, T("; "), W("rate_name", rate[2]), T(" at "), N("rate", rate[0], "rate_percent"),
        T(" percent on "), D("rate_date", rate[1]), T("."),
    ]})
    return rows


def netbacks_section(result: Mapping[str, Any], *, day: date, threshold: float, hh_multiple: float) -> dict[str, Any]:
    """The netback at Sabine Pass of every destination and route, a row each:
    the route and what sets it apart, a bar from zero, the figure. The best is
    the accent; a closed route is an outline; a dashed rule in every bar marks
    115 percent of Henry Hub."""
    west = result["west"]
    best = result["best_route"]
    rows = [{
        "id": "nwe_direct", "name": ROUTE_NAMES["nwe_direct"], "open": True, "accent": best == "nwe_direct",
        "value": west["netback"],
        "detail_segments": [T("Direct to Northwest Europe, the reference for every gap below.")],
    }]
    values = [west["netback"]]
    for route, lines in result["east"].items():
        values.append(lines["netback"])
        gap = lines["netback"] - west["netback"]
        if lines["open"]:
            detail = [N("gap", abs(gap), "usd_mmbtu"), T(" $/MMBtu more than Gate." if gap >= 0 else " $/MMBtu less than Gate.")]
        else:
            detail = [T("Closed: "), W("why_closed", _closed_reason(lines["why_closed"])),
                      T(". Priced as if it were open, "), N("gap", gap, "usd_mmbtu", signed=True), T(" on Gate.")]
        rows.append({"id": route, "name": ROUTE_NAMES[route], "open": lines["open"], "accent": route == best,
                     "value": lines["netback"], "detail_segments": detail})
    low, high, _ = nice_domain(values + [threshold], 4)
    open_east = [r for r, l in result["east"].items() if l["open"]]
    if result["best_destination"] == "NEA":
        heading = [W("best_route_name", ROUTE_NAMES[best]), T(" pays most, "),
                   N("gap", result["best_netback"] - west["netback"], "usd_mmbtu"),
                   T(" $/MMBtu more than Gate at Sabine Pass")]
    elif open_east:
        best_east = result["best_route_east"]
        heading = [T("Gate pays most, "), N("gap", west["netback"] - result["east"][best_east]["netback"], "usd_mmbtu"),
                   T(" $/MMBtu more than "), W("best_east_name", ROUTE_NAMES[best_east])]
    else:
        heading = [T("Gate is the only open destination")]
    closed = [r for r, l in result["east"].items() if not l["open"]]
    if closed:
        heading += [T("; "), W("closed_routes", listed(ROUTE_SHORT[r] for r in closed)),
                    T(" is closed to a US cargo" if len(closed) == 1 else " are closed to a US cargo")]
    heading += [T(".")]
    percent = N("hh_multiple_percent", hh_multiple * 100.0, "count")
    clears = all(v >= threshold for v in values if not _missing(v))
    return {
        "heading_segments": heading,
        "scale": {"low": low, "high": high},
        "scale_segments": [
            T("Each bar is the value at Sabine Pass of a cargo loading in the week to "), D("as_of", day),
            T(", net of freight, boil-off, canals, ports, carbon, financing and, at Gate, Europe's DES spread to "
              "TTF; the scale runs from zero to "), N("scale_high", high, "usd_mmbtu"),
            T(" $/MMBtu. The dashed rule is "), percent,
            T(" percent of Henry Hub, "), N("threshold", threshold, "usd_mmbtu"),
            T(" $/MMBtu, the price below which a cargo is not worth lifting"),
            T("; every route clears it." if clears else "."),
        ],
        "threshold": threshold,
        "rows": rows,
        "table_caption": "The netback at Sabine Pass of each destination and route, $/MMBtu loaded.",
        "source_segments": [
            T("Prices from EIA's weekly international prices; costs from the parameter table and the routes seed; "
              "data to "), D("as_of", day), T("."),
        ],
    }


STEP_NAMES: Mapping[str, str] = {
    "spread": "JKM over TTF, on the cargo delivered east",
    "boil_off": "Gas boiled off on the longer voyage, at TTF",
    "regas": "Europe's regasification discount, escaped",
    "hire": "Hire for the longer round trip",
    "canals": "Canal tolls",
    "slot_premium": "Canal slot premium",
    "ports": "Port costs, Futtsu against Gate",
    "carbon": "EU allowances",
    "financing": "Financing the cargo for longer",
}


#: The steps a sentence names in the plural, for the verb that follows.
PLURAL_STEPS = frozenset({"canals", "ports", "carbon"})

#: The same steps, as a sentence names them.
STEP_SHORT: Mapping[str, str] = {
    "spread": "the spread on the cargo delivered",
    "boil_off": "boil-off on the longer voyage",
    "regas": "Europe's regasification discount",
    "hire": "hire",
    "canals": "the canal tolls",
    "slot_premium": "the slot premium",
    "ports": "port costs",
    "carbon": "EU allowances",
    "financing": "financing",
}


def step_name(step: str, delta: float) -> str:
    return regas_words(delta)["step"] if step == "regas" else STEP_NAMES[step]


def step_short(step: str, delta: float) -> str:
    return regas_words(delta)["short"] if step == "regas" else STEP_SHORT[step]


def _step_detail(step: str, inputs, west: Mapping[str, Any], east: Mapping[str, Any], route: str, *,
                 delta_observed: bool) -> list[dict[str, Any]]:
    if step == "spread":
        return [N("spread", inputs.jkm - inputs.ttf, "usd_mmbtu", signed=True),
                T(" $/MMBtu on the gas left after the voyage east, per MMBtu loaded.")]
    if step == "boil_off":
        return [N("days_east", east["days_total"], "days"), T(" days for the round trip east against "),
                N("days_west", west["days_total"], "days"), T(" to Gate.")]
    if step == "regas":
        gate = regas_words(inputs.delta_nwe)["gate"]
        if delta_observed:
            return [T("ACER's DES Northwest Europe less TTF, "), N("delta_nwe", inputs.delta_nwe, "usd_mmbtu", signed=True),
                    T(" $/MMBtu: " + gate + ".")]
        return [T("The parameter table's assumption, "), N("delta_nwe", inputs.delta_nwe, "usd_mmbtu", signed=True),
                T(" $/MMBtu, as ACER published on too few days: " + gate + ".")]
    if step == "hire":
        return [N("hire", inputs.hire_usd_day, "usd_day"), T(" $/day over the longer round trip.")]
    if step == "canals":
        if route == "nea_cape":
            return [T("None round the Cape.")]
        return [T("Laden and in ballast, through "), W("canal", ROUTE_SHORT[route]), T(".")]
    if step == "slot_premium":
        return [T("Paid only when a booking slot is bought at auction.")]
    if step == "ports":
        return [T("Sabine Pass and Futtsu against Sabine Pass and Gate.")]
    if step == "carbon":
        return [T("A voyage to Gate surrenders them; one to Futtsu does not.")]
    if step == "financing":
        return [T("The cargo's price at Sabine Pass carried for the longer laden voyage.")]
    raise KeyError(step)


def cost_section(result: Mapping[str, Any], inputs, *, day: date, steps: Sequence[str],
                 delta_observed: bool) -> dict[str, Any]:
    """The arb of the best open route east as steps from the Gate netback."""
    delta = inputs.delta_nwe
    west = result["west"]
    route = result["best_route_east"]
    if route is None:
        return {"route": None, "rows": [], "heading_segments": [T("No route east is open to a US cargo, so there is no long way to cost.")]}
    lines = result["east"][route]
    fall = lines["waterfall"]
    rows = []
    running = 0.0
    for step in steps:
        value = fall[step]
        rows.append({"id": step, "kind": "step", "name": step_name(step, delta),
                     "detail_segments": _step_detail(step, inputs, west, lines, route, delta_observed=delta_observed),
                     "value": value, "start": running, "end": running + value, "accent": False})
        running += value
    arb = lines["arb"]
    rows.append({"id": "arb", "kind": "total", "name": "The arb, " + ROUTE_NAMES[route] + " over Gate",
                 "detail_segments": None, "value": arb, "start": 0.0, "end": arb, "accent": True})
    low, high, _ = nice_domain([r["start"] for r in rows] + [r["end"] for r in rows], 4)
    gains = [(fall[s], s) for s in steps if fall[s] > 0]
    losses = [(fall[s], s) for s in steps if fall[s] < 0]
    heading = [T("Via "), W("route", ROUTE_SHORT[route]), T(" the arb is "), N("arb", arb, "usd_mmbtu", signed=True),
               T(" $/MMBtu")]
    if gains:
        top_gain = max(gains)[1]
        heading += [T(": "), W("largest_gain", step_short(top_gain, delta)), T(" add most, " if top_gain in PLURAL_STEPS else " adds most, "),
                    N("largest_gain_value", fall[top_gain], "usd_mmbtu", signed=True)]
    if losses:
        top_loss = min(losses)[1]
        heading += [T(", and " if gains else ": "), W("largest_loss", step_short(top_loss, delta)), T(" take most, " if top_loss in PLURAL_STEPS else " takes most, "),
                    N("largest_loss_value", fall[top_loss], "usd_mmbtu", signed=True)]
    heading += [T(".")]
    others = [r for r in result["east"]]
    return {
        "route": route,
        "heading_segments": heading,
        "start_segments": [T("From the netback at Gate, "), N("start", fall["start"], "usd_mmbtu"),
                           T(" $/MMBtu, each step below adds or takes away, per MMBtu loaded:")],
        "end_segments": [T("So the netback at "), W("route_name", ROUTE_NAMES[route]), T(" is "),
                         N("end", fall["end"], "usd_mmbtu"), T(" $/MMBtu, "),
                         N("arb", abs(arb), "usd_mmbtu"), T(" more than at Gate." if arb >= 0 else " less than at Gate.")],
        "scale": {"low": low, "high": high},
        "rows": rows,
        "table_caption": "The steps from the Gate netback to the " + ROUTE_NAMES[route] + " netback, $/MMBtu loaded.",
        "source_segments": [T("Each step is the cost east less the cost west, over the cargo loaded; the steps add up to the arb exactly. Data to "),
                            D("as_of", day), T(".")],
        "others": {
            "button": "The same steps for every route east",
            "caption": "The steps for each route east, $/MMBtu loaded; a closed route is priced as if it were open.",
            "routes": [{"route": r, "name": ROUTE_SHORT[r] + ("" if result["east"][r]["open"] else ", closed")} for r in others],
            "rows": [{"id": s, "kind": "step", "name": step_name(s, delta), "values": {r: result["east"][r]["waterfall"][s] for r in others}} for s in steps]
                    + [{"id": "arb", "kind": "total", "name": "The arb over Gate", "values": {r: result["east"][r]["arb"] for r in others}}],
        },
    }


def breakeven_section(result: Mapping[str, Any], inputs, *, day: date, levels: Mapping[str, float],
                      hire: Mapping[str, Any], evaluate_at: Callable[[float], Mapping[str, Any]]) -> dict[str, Any]:
    """S* against hire per route east: two points per route, since S* is linear
    in hire, from the engine at each end of the axis.

    H* is where a route's line crosses today's spread: a route east pays more
    than Gate at any hire below it, the voyage east being the longer. A negative
    H* means the route does not pay even with a free ship, and the heading says
    so rather than quoting a hire no market reaches."""
    # From zero: the low level, a few hundred dollars below it, is a figure of a
    # glutted market and would spend a fifth of the axis on nothing.
    candidates = [max(0.0, levels["low"]), levels["high"], max(0.0, hire["value"])]
    x_low, x_high, x_step = nice_domain(candidates, 4)
    at_low, at_high = evaluate_at(x_low), evaluate_at(x_high)
    spread = result["spread"]
    lines, ys = [], [spread]
    for route, lines_now in result["east"].items():
        if not lines_now["open"]:
            continue
        y0, y1 = at_low["east"][route]["s_star"], at_high["east"][route]["s_star"]
        ys += [y0, y1]
        h_star = lines_now["h_star_usd_day"]
        lines.append({"route": route, "name": ROUTE_SHORT[route], "pattern": ROUTE_PATTERNS[route],
                      "points": [[x_low, y0], [x_high, y1]], "h_star": None if _missing(h_star) else h_star,
                      "label": capitalised(ROUTE_SHORT[route])})
    y_low, y_high, y_step = nice_domain(ys, 5)
    closed = [r for r, l in result["east"].items() if not l["open"]]

    paying = sorted((l for l in lines if l["h_star"] is not None and l["h_star"] > 0), key=lambda l: -l["h_star"])
    never = [l for l in lines if l["h_star"] is not None and l["h_star"] <= 0]
    at_spread = [T("At today's spread of "), N("spread", spread, "usd_mmbtu", signed=True), T(" $/MMBtu, ")]
    if paying:
        heading = at_spread + [T("the voyage via "), W("route", paying[0]["name"]), T(" pays more than Gate at any hire below "),
                               N("h_star", paying[0]["h_star"], "usd_day"), T(" $/day")]
        for line in paying[1:]:
            heading += [T(", via "), W("route", line["name"]), T(" below "), N("h_star", line["h_star"], "usd_day"),
                        T(" $/day")]
        if never:
            heading += [T("; via "), W("routes_never", listed(l["name"] for l in never)),
                        T(" no hire is low enough, not even a free ship")]
        heading += [T(".")]
    elif never:
        heading = at_spread + [T("no open route east pays more than Gate, not even with a free ship.")]
    elif lines:
        heading = [T("No open route east has a breakeven hire today.")]
    else:
        heading = [T("No route east is open to a US cargo today.")]

    caption = [T("H*, where a route's line crosses today's spread, is the hire above which that route pays less "
                 "than Gate.")]
    for line in lines:
        if line["h_star"] is not None and not (x_low <= line["h_star"] <= x_high):
            caption += [T(" Via "), W("route", line["name"]), T(" it is "),
                        N("h_star", line["h_star"], "usd_day", signed=True), T(" $/day, off this axis.")]
    for route in closed:
        caption += [T(" "), W("route", capitalised(ROUTE_SHORT[route])),
                    T(" is not drawn: closed, "), W("why_closed", _closed_reason(result["east"][route]["why_closed"])),
                    T(".")]
    reported = None
    if hire["reported"] and x_low <= hire["value"] <= x_high:
        reported = {"hire": hire["value"], "label_segments": [
            T("Reported "), D("hire_date", hire["date"], "day"), T(", "), N("hire", hire["value"], "usd_day"),
            T(" $/day")]}
    elif hire["reported"]:
        caption += [T(" The reported hire, "), N("hire", hire["value"], "usd_day", signed=True),
                    T(" $/day, lies off this axis.")]
    desc = [T("Lines of S*, the spread of JKM over TTF at which a route east pays as much as Gate, against the "
              "charter rate, for the week to "), D("as_of", day), T(". Today's spread, "),
            N("spread", spread, "usd_mmbtu", signed=True), T(" $/MMBtu, is the accent line")]
    if reported is not None:
        desc += [T("; the hire reported nearest the week, "), N("hire", hire["value"], "usd_day"),
                 T(" $/day, is a dashed rule.")]
    else:
        desc += [T("; no hire reported near the week is drawn.")]
    columns = [
        {"id": "at_hire", "head": "S* at " + ("the reported " if hire["reported"] else "the central ") + "hire",
         "format": "usd_mmbtu", "signed": True},
        {"id": "low", "head": "S* at the low level", "format": "usd_mmbtu", "signed": True},
        {"id": "central", "head": "S* at the central level", "format": "usd_mmbtu", "signed": True},
        {"id": "high", "head": "S* at the high level", "format": "usd_mmbtu", "signed": True},
        {"id": "h_star", "head": "H*", "format": "usd_day", "signed": False},
    ]
    at_levels = {name: evaluate_at(value) for name, value in levels.items()}
    table_rows = []
    for route, lines_now in result["east"].items():
        table_rows.append({
            "route": route,
            "name": capitalised(ROUTE_SHORT[route]) + ("" if lines_now["open"] else ", closed"),
            "values": {
                "at_hire": lines_now["s_star"],
                **{name: at_levels[name]["east"][route]["s_star"] for name in levels},
                "h_star": None if _missing(lines_now["h_star_usd_day"]) else lines_now["h_star_usd_day"],
            },
            "missing_words": "no crossing",
        })
    level_segments = []
    for index, (name, value) in enumerate(levels.items()):
        level_segments += [T(", " if index else ""), W("level_name", name), T(" "),
                           N("level_" + name, value, "usd_day", signed=value < 0)]
    return {
        "heading_segments": heading,
        "desc_segments": desc,
        "caption_segments": caption,
        "x": {"low": x_low, "high": x_high, "step": x_step, "divisor": 1000.0, "axis": "Hire, thousand $/day"},
        "y": {"low": y_low, "high": y_high, "step": y_step, "axis": "S*, $/MMBtu"},
        "lines": lines,
        "spread": {"value": spread, "label_segments": [T("JKM over TTF, "), N("spread", spread, "usd_mmbtu", signed=True)]},
        "reported": reported,
        "table": {"columns": columns, "rows": table_rows,
                  "caption_segments": [T("S* for each route east at the hire used today and at the three levels the "
                                         "history uses (")] + level_segments + [T(" $/day), and H*.")]},
        "source_segments": [T("Computed by the engine at each end of the axis, S* being linear in hire; data to "),
                            D("as_of", day), T(".")],
    }


def sections(result: Mapping[str, Any], *, netbacks: Mapping[str, Any], cost: Mapping[str, Any],
             breakeven: Mapping[str, Any], flows_heading: Sequence[Mapping[str, Any]],
             provenance_summary: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"id": "netbacks", "name": "Netbacks", "summary_segments": netbacks["heading_segments"]},
        {"id": "cost", "name": "Why the long way costs more", "summary_segments": cost["heading_segments"]},
        {"id": "breakeven", "name": "Breakeven", "summary_segments": breakeven["heading_segments"]},
        {"id": "flows", "name": "Where the cargoes went", "summary_segments": list(flows_heading)},
        {"id": "provenance", "name": "Provenance", "summary_segments": list(provenance_summary)},
    ]


# ---------------------------------------------------------------------------
# Where the cargoes went
# ---------------------------------------------------------------------------

#: How many of the latest months the Now view draws.
FLOWS_MONTHS = 24


def _months_between(first: str, last: str) -> int:
    """Calendar months from first to last, both counted, for yyyy-mm strings."""
    a, b = pd.Period(first, "M"), pd.Period(last, "M")
    return (b - a).n + 1


def flows_panel(months: Sequence[Mapping[str, Any]], regressions: Sequence[Mapping[str, Any]],
                excluded_years: Sequence[int], central_hire: float) -> dict[str, Any]:
    """The latest months of exports by vessel, the share to the JKM markets and
    to Asia against the arb at loading at the central hire, and the regression
    on every month, in words. The latest month is the chart's accent."""
    held = [m for m in months if not _missing(m["share_asia"])]
    latest = held[-FLOWS_MONTHS:]
    rows = []
    for m in latest:
        rows.append({
            "month": _iso(m["month"]), "label": short_month_label(m["month"]),
            "share_jkm": None if _missing(m["share_jkm"]) else m["share_jkm"] * 100.0,
            "share_asia": m["share_asia"] * 100.0,
            "arb": None if _missing(m["arb"]["central"]) else m["arb"]["central"],
        })
    last = latest[-1]["month"]
    priced = [r for r in rows if r["arb"] is not None]
    open_months = [r for r in priced if r["arb"] > 0]
    closed_months = [r for r in priced if r["arb"] <= 0]
    count = len(rows)
    if closed_months and open_months:
        mean_open = sum(r["share_asia"] for r in open_months) / len(open_months)
        mean_closed = sum(r["share_asia"] for r in closed_months) / len(closed_months)
        heading = [
            T("In the "), N("months", count, "count"), T(" months to "), D("last_month", last, "month"),
            T(" the arb at loading was open in "), N("open_months", len(open_months), "count"),
            T("; Asia took "), N("share_open", mean_open, "share_percent"),
            T(" percent of US exports in those months and "), N("share_closed", mean_closed, "share_percent"),
            T(" percent in the others."),
        ]
    else:
        shares = [r["share_asia"] for r in rows]
        state = "open" if open_months else "closed"
        heading = [
            T("The arb at loading was "), W("arb_state", state), T(" in every one of the "),
            N("months", len(priced), "count"), T(" months priced to "), D("last_month", last, "month"),
            T("; Asia's share of US exports moved between "), N("share_low", min(shares), "share_percent"),
            T(" and "), N("share_high", max(shares), "share_percent"), T(" percent all the same."),
        ]

    def regression(share: str, sample: str) -> Mapping[str, Any]:
        (row,) = [r for r in regressions if r["share"] == share and r["hire_level"] == "central" and r["sample"] == sample]
        return row

    everything = regression("share_jkm", "all months")
    excluded = [r for r in regressions if r["sample"] != "all months"][0]["sample"]
    without = regression("share_jkm", excluded)
    span = _months_between(everything["first_month"], everything["last_month"])
    years_words = listed([str(y) for y in excluded_years])
    notes = [
        [
            T("Over "), N("n", everything["n"], "count"), T(" of the "), N("span", span, "count"),
            T(" months from "), D("first_month", everything["first_month"] + "-01", "month"), T(" to "),
            D("last_month", everything["last_month"] + "-01", "month"), T(" (the others have no price), a dollar "
              "more of arb at loading went with "), N("slope", everything["slope"] * 100.0, "pp"),
            T(" points more of US exports to the JKM markets (t "), N("t", everything["t_slope"], "t_stat"),
            T(", Newey West errors with "), N("lags", everything["lags"], "count"),
            T(" lags); without "), W("excluded_years", years_words), T(", over "),
            N("n_without", without["n"], "count"), T(" months, "),
            N("slope_without", without["slope"] * 100.0, "pp"), T(" points (t "),
            N("t_without", without["t_slope"], "t_stat"), T(", "), N("lags_without", without["lags"], "count"),
            T(" lags). R squared is "), N("r2", everything["r2"], "r2"), T(" on all months and "),
            N("r2_without", without["r2"], "r2"),
            T(" without those years, so most of the share moves with something other than the arb."
              if max(everything["r2"], without["r2"]) < 0.5 else " without those years."),
        ],
        [
            T("What this cannot separate: long term contracts with Asian buyers, whose cargoes move whatever the spot "
              "economics; the slot constraints at Panama; China's tariff on US LNG from "),
            D("china_tariff_from", "2025-02-10", "month"),
            T("; the gap between spot hire and the cost of a ship already on term charter; and the month itself, "
              "coarser than the decisions, which are taken weeks before a cargo loads."),
        ],
    ]
    ticks = [i for i, r in enumerate(rows) if r["month"][5:7] in ("01", "07")]
    ticks_narrow = [i for i, r in enumerate(rows) if r["month"][5:7] == "01"]
    share_low, share_high, share_step = nice_domain([r["share_asia"] for r in rows] + [r["share_jkm"] for r in rows], 5)
    arb_low, arb_high, arb_step = nice_domain([r["arb"] for r in rows], 4)
    latest_row = rows[-1]
    return {
        "first": rows[0]["month"], "last": rows[-1]["month"],
        "heading_segments": heading,
        "desc_segments": [
            T("Two panels on one month axis: above, the share of US LNG exports by vessel to the JKM markets, Japan, "
              "South Korea, China and Taiwan, as a solid line and to all Asia as a dashed one; below, the model's arb at "
              "loading at the central hire, as bars from zero, filled when Asia paid more and outlined when Gate did. "
              "The latest month, "), D("last_month", last, "month"),
            T(", is the accent: Asia took "), N("latest_share", latest_row["share_asia"], "share_percent"),
            T(" percent, with an arb of "), N("latest_arb", latest_row["arb"], "usd_mmbtu", signed=True,
                                               missing="no price"), T(" $/MMBtu."),
        ],
        "source_segments": [
            T("Exports from EIA's US natural gas exports by country, by vessel; the arb from this study's engine at the "
              "central hire, "), N("central_hire", central_hire, "usd_day"), T(" $/day. Data to "),
            D("last_month", last, "month"), T("."),
        ],
        "months": rows,
        "shares": [
            {"key": "share_jkm", "pattern": "solid", "label": "JKM markets"},
            {"key": "share_asia", "pattern": "dash", "label": "All Asia"},
        ],
        "share_domain": {"low": share_low, "high": share_high, "step": share_step},
        "arb_domain": {"low": arb_low, "high": arb_high, "step": arb_step},
        "share_axis": "Share of exports, percent",
        "arb_axis": "Arb at loading, $/MMBtu",
        "ticks": ticks or [0],
        "ticks_narrow": ticks_narrow or [0],
        "notes": notes,
        "missing_words": "not published",
        "arb_missing_words": "not priced",
        "table_caption": "US LNG exports by vessel: the share to the JKM markets and to Asia, and the arb at loading at the central hire.",
    }


# ---------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------

PROVENANCE_COLUMNS = (
    {"id": "series", "head": "Series", "short": "series"},
    {"id": "status_words", "head": "Status", "short": "status"},
    {"id": "range_words", "head": "Range", "short": "range"},
    {"id": "gaps_words", "head": "Missing dates", "short": "missing dates"},
    {"id": "provisional_words", "head": "Provisional", "short": "provisional"},
    {"id": "fetch_words", "head": "Last fetch", "short": "last fetch"},
    {"id": "vintage_words", "head": "Vintage", "short": "vintage"},
    {"id": "source", "head": "Source", "short": "source"},
    {"id": "terms_words", "head": "Terms", "short": "terms"},
)

FREQUENCY_WORDS = {"daily": "daily", "weekly": "weekly", "monthly": "monthly", "annual": "yearly"}

ORDINALS = {"1": "first", "2": "second", "3": "third", "4": "fourth"}


def _utc_words(stamp: str | None) -> str | None:
    if not stamp:
        return None
    moment = pd.Timestamp(stamp)
    return "%s at %02d:%02d UTC" % (day_label(moment), moment.hour, moment.minute)


def _period_label(value: Any, frequency: str) -> str:
    return month_label(value) if frequency == "monthly" else day_label(value)


def vintage_words(text: str | None) -> str:
    """A manifest vintage in words: dates as a reader writes them, no file stem,
    no machine timestamp."""
    if not text:
        return "not recorded"
    out = re.sub(r"(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2}):\d{2}",
                 lambda m: "%s at %s:%s" % (day_label("%s-%s-%s" % m.group(1, 2, 3)), m.group(4), m.group(5)), text)
    out = re.sub(r"\b(\d{4})-(\d{2})-(\d{2})\b", lambda m: day_label(m.group(0)), out)
    out = re.sub(r"\b(\d{4})_report_Q(\d)\b", lambda m: "the %s quarter report of %s" % (ORDINALS[m.group(2)], m.group(1)), out)
    out = re.sub(r"\b(\d{4})_report_(\d{2})\b", lambda m: "the report of %s" % month_label("%s-%s-01" % m.group(1, 2)), out)
    out = re.sub(r"\b(20\d{2})(0[1-9]|1[0-2])\b", lambda m: month_label("%s-%s-01" % m.group(1, 2)), out)
    out = re.sub(r"\b(January|February|March|April|May|June|July|August|September|October|November|December) 0?(\d{1,2}), (\d{4})",
                 lambda m: "%s %s %s" % (int(m.group(2)), m.group(1), m.group(3)), out)
    out = re.sub(r"\b(Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b(?= \d{4})",
                 lambda m: MONTH_NAMES[MONTH_SHORT.index(m.group(1))], out)
    out = out.replace("_", " ")
    return out[:1].lower() + out[1:] if out[:1].isupper() and not out[:2].isupper() and out.split(" ")[0] not in MONTH_NAMES else out


def provenance(manifest: Mapping[str, Any], sources: Mapping[str, Any], credits: Sequence[str]) -> dict[str, Any]:
    """The manifest in words. A status is what the last run found ("checked",
    "stale", "failed"): a series that has ended is checked too, and its range
    says where it stops."""
    rows = []
    for entry in manifest["series"]:
        source = sources.get(entry["series"])
        frequency = entry.get("frequency") or ""
        frequency_words = FREQUENCY_WORDS.get(frequency, frequency)
        rows_count = entry.get("rows")
        if entry.get("first_date") and entry.get("last_date"):
            range_words = "%s to %s, %s" % (_period_label(entry["first_date"], frequency),
                                            _period_label(entry["last_date"], frequency), frequency_words)
        elif entry.get("method") == "seed":
            range_words = "%s %s typed from cited articles, not a time series" % (
                rows_count, plural(rows_count or 0, "figure", "figures"))
        elif entry.get("method") == "derived":
            range_words = "%s %s computed by this study, not a time series" % (
                rows_count, plural(rows_count or 0, "row", "rows"))
        else:
            range_words = "no dated rows"
        gaps = entry.get("gaps") or []
        if gaps:
            unit = "month" if frequency == "monthly" else "date"
            gaps_words = "%d %s, from %s to %s" % (len(gaps), plural(len(gaps), unit, unit + "s"),
                                                   _period_label(gaps[0], frequency), _period_label(gaps[-1], frequency))
        else:
            gaps_words = "none"
        provisional = entry.get("provisional_from")
        provisional_words = ("preliminary from %s" % _period_label(provisional, frequency)) if provisional else "none"
        if entry.get("machine_fetched") is False:
            fetch_words = ("computed by this study, not fetched" if entry.get("method") == "derived"
                           else "typed by hand from cited documents, not fetched")
        else:
            fetch_words = _utc_words(entry.get("fetched_at")) or "no fetch recorded"
        status = entry.get("status") or "unknown"
        status_words = {"ok": "checked", "stale": "stale", "failed": "failed"}.get(status, status)
        if entry.get("committable"):
            terms = (source.licence if source is not None else "") or "published with credit"
        else:
            terms = "kept private: its terms do not allow publishing it"
        rows.append({
            "id": entry["series"],
            "label": source.label if source is not None else entry["series"],
            "publisher": source.publisher if source is not None else entry.get("source", ""),
            "page_url": entry.get("page_url") or (source.page_url if source is not None else ""),
            "status": status,
            "status_words": status_words,
            "range_words": range_words,
            "gaps_words": gaps_words,
            "provisional_words": provisional_words,
            "fetch_words": fetch_words,
            "vintage_words": vintage_words(entry.get("vintage")),
            "terms_words": terms,
        })
    trouble = [r for r in rows if r["status"] in ("failed", "stale")]
    private = [r for r in rows if r["terms_words"].startswith("kept private")]
    preliminary = [r for r in rows if r["provisional_words"] != "none"]
    steps = manifest.get("manual_steps") or []
    summary = [N("series_count", len(rows), "count"), T(" series")]
    if trouble:
        summary += [T(", "), N("trouble", len(trouble), "count"), T(" of them stale or failed on the last run")]
    else:
        summary += [T(", every one checked on the last run")]
    if preliminary:
        summary += [T("; "), N("preliminary", len(preliminary), "count"),
                    T(plural(len(preliminary), " holds", " hold")), T(" preliminary figures")]
    if private:
        summary += [T("; "), N("private", len(private), "count"), T(plural(len(private), " is", " are")),
                    T(" kept private under its terms")]
    summary += [T("; "), N("manual_steps", len(steps), "count"), T(plural(len(steps), " step", " steps")),
                T(" done by hand.")]
    return {
        "summary_segments": summary,
        "columns": list(PROVENANCE_COLUMNS),
        "series": rows,
        "table_caption": "Every series the study reads, as the manifest records it; stale and failed series first. "
                         "Each range ends where the series ends, whether the publisher stopped it or it is current.",
        "manual_heading": "Work done by hand",
        "manual_intro": "What the pipeline cannot do for itself, why, and what skipping it would cost.",
        "manual_steps": [{"id": s["id"], "what": s["what"], "why": s["why"], "cost_if_skipped": s["cost_if_skipped"]}
                         for s in steps],
        "credits_heading": "Credits",
        "credits": list(credits),
        "manifest_words": "The full record, with every gap and licence note, is",
    }

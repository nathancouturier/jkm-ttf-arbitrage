"""The History view's data: JKM's premium over TTF against what the cheapest route east needs, over time.

Three panels, each computed here and drawn by the page as it is given:

* WEEKLY, from the week ending 15 September 2021: the spread, and the
  breakeven spread S* of the cheapest open route east at the low, central and
  high hire (a band, its middle the central hire). A week whose spread lies
  above the central S* is a week the arb east was open: a cargo netted more at
  Futtsu than at Gate. Weeks whose two front months name different delivery
  months are marked.
* BREAKEVEN HIRE, the same weeks: H*, the hire at which the cheapest route
  east nets what Gate does, against the charter rates reported, each a point.
  A reported rate below H* is a week the arb was open at the market's own
  freight.
* MONTHLY, from January 2016: the spread and the band as above, a Japanese
  spot price (METI's contract-based, a proxy for JKM) to March 2021 and the
  mean of the weekly JKM after, a change of definition the chart marks.

Named ranges cut the weekly panels: every week, 2021 to 2023, 2024 on, the
last 52 weeks; each carries its own domains, ticks and sentences, so the page
computes nothing. The breaks lngarb.analysis finds (docs/methodology.md,
section 12.1) that change a price's definition, a route, the ship or the EU
ETS are numbered rules, listed in a table under the charts; the dated events
of lngarb.events that explain a regime are lettered marks, listed in a second
table with what was left out. Every sentence is computed from the rows:
nothing here is typed but words.
"""

from __future__ import annotations

import math
from datetime import date, timedelta
from typing import Any, Mapping, Sequence

import pandas as pd

from . import analysis, config, reader

__all__ = ["page", "ticks"]

#: The routes east by the short names analysis.work gives their columns.
SHORT = tuple(analysis.ROUTES.values())
SHORT_NAMES = {"panama": "Panama", "suez": "Suez", "cape": "the Cape"}

#: The kinds of break drawn as a rule; a naming change is listed, not drawn,
#: since the price runs on across it (methodology section 5).
DRAWN = ("definition", "route", "vessel", "carbon")

#: The named ranges of the weekly panels: id, label, first day, last day (None:
#: the series' own end). "last_52" is the 52 weeks to the last.
RANGES = (
    ("all", "Every week", None, None),
    ("to_2023", "2021 to 2023", None, "2023-12-31"),
    ("from_2024", "2024 on", "2024-01-01", None),
    ("last_52", "The last 52 weeks", None, None),
)

#: Ticks on a time axis: about this many, on years, else on months.
X_TICKS = 6
Y_TICKS = 5
#: The breakeven hire's axis is drawn in thousands of dollars a day.
HSTAR_DIVISOR = 1000.0
#: The axis spans the middle of its values: a week beyond this share at either
#: end is drawn at the edge, and counted, so that 2022's breakevens of minus
#: millions do not flatten every other year.
HSTAR_TAIL = 0.05
#: How the table names each kind of break.
KIND_WORDS = {"definition": "price definition", "route": "route", "vessel": "ship", "carbon": "EU ETS"}


def _finite(value: Any) -> float | None:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    return float(value)


def _cheapest(row: Mapping[str, Any]) -> tuple[str | None, float | None, float | None]:
    """The cheapest open route east of a row: its short name, S* and H*."""
    best = None
    for short in SHORT:
        s_star = _finite(row.get(short + "_s_star"))
        if row.get(short + "_open") and s_star is not None and (best is None or s_star < best[1]):
            best = (short, s_star, _finite(row.get(short + "_h_star")))
    return best if best else (None, None, None)


def _points(rows: pd.DataFrame, frequency: str) -> list[dict[str, Any]]:
    """One point per observation of the frequency, at every hire level."""
    frame = rows[rows["frequency"] == frequency]
    out = []
    for day, group in frame.groupby("day"):
        by = {r["hire_level"]: r for r in group.to_dict("records")}
        central = by.get("central")
        if central is None:
            continue
        route, s_central, h_star = _cheapest(central)
        point = {
            "day": day.date(),
            "spread": _finite(central["spread"]),
            "s_low": _cheapest(by["low"])[1] if "low" in by else None,
            "s_central": s_central,
            "s_high": _cheapest(by["high"])[1] if "high" in by else None,
            "route": route,
            "h_star": h_star,
            "series": central["series"],
            "alignment": central.get("alignment") if isinstance(central.get("alignment"), str) else None,
        }
        reported = by.get("reported")
        if reported is not None:
            point["reported_hire"] = _finite(reported["hire_usd_day"])
            point["reported_open"] = bool(_finite(reported["arb"]) is not None and reported["arb"] > 0)
        out.append(point)
    return out


def _open(point: Mapping[str, Any]) -> bool | None:
    if point["spread"] is None or point["s_central"] is None:
        return None
    return point["spread"] > point["s_central"]


def _by_year(points: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    years: dict[int, list[int]] = {}
    for point in points:
        state = _open(point)
        if state is None:
            continue
        counts = years.setdefault(point["day"].year, [0, 0, 0])
        counts[0] += int(state)
        counts[1] += 1
        counts[2] += int(point["spread"] < 0)
    return [{"year": year, "open": c[0], "count": c[1], "ttf_above": c[2]} for year, c in sorted(years.items())]


def _with_gaps(points: Sequence[Mapping[str, Any]], step_days: int) -> list[dict[str, Any] | None]:
    """The points with a None wherever a step is longer than the series' own, so a line breaks there."""
    out: list[dict[str, Any] | None] = []
    for point in points:
        if out and out[-1] is not None and (point["day"] - out[-1]["day"]).days > step_days:
            out.append(None)
        out.append(point)
    return out


def ticks(first: date, last: date) -> list[dict[str, Any]]:
    """Year starts, or every few months over a span shorter than three years."""
    if (last - first).days > 3 * 365:
        return [{"day": date(y, 1, 1), "label": str(y)} for y in range(first.year + 1, last.year + 1)]
    out = []
    month = date(first.year, first.month, 1)
    step = max(1, round(((last - first).days / 30.44) / X_TICKS))
    while month <= last:
        if month > first:
            out.append({"day": month, "label": reader.MONTH_SHORT[month.month - 1] + " " + str(month.year)})
        index = month.month - 1 + step
        month = date(month.year + index // 12, index % 12 + 1, 1)
    return out


def _domain(values: Sequence[float | None], *, zero: bool = True) -> dict[str, float]:
    low, high, step = reader.nice_domain([v for v in values if v is not None], Y_TICKS, zero=zero)
    return {"low": low, "high": high, "step": step}


def _hstar_domain(points: Sequence[Mapping[str, Any]], anchors: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """The breakeven hire's axis over the middle of its values and every reported rate, and what falls off it."""
    values = sorted(p["h_star"] for p in points if p["h_star"] is not None)
    if not values:
        return {"low": 0.0, "high": 1.0, "step": 1.0, "below": 0, "above": 0}
    cut = int(len(values) * HSTAR_TAIL)
    middle = values[cut:len(values) - cut] or values
    shown = list(middle) + [a["hire_usd_day"] for a in anchors]
    low, high, step = reader.nice_domain([v / HSTAR_DIVISOR for v in shown], Y_TICKS, zero=True)
    low, high, step = low * HSTAR_DIVISOR, high * HSTAR_DIVISOR, step * HSTAR_DIVISOR
    return {"low": low, "high": high, "step": step,
            "below": sum(v < low for v in values), "above": sum(v > high for v in values)}


def _weekly_heading(points: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    years = _by_year(points)
    opened = sum(y["open"] for y in years)
    count = sum(y["count"] for y in years)
    first = next(p["day"] for p in points)
    last = points[-1]["day"]
    segments = [
        reader.T("From the week ending "), reader.D("first", first), reader.T(" to the week ending "),
        reader.D("last", last), reader.T(", JKM's premium over TTF was above what the cheapest route east needs "
                                         "at the central hire, so the arb east was open, in "),
        reader.N("weeks_open", opened, "count"), reader.T(" of "), reader.N("weeks", count, "count"),
        reader.T(" weeks"),
    ]
    full = [y for y in years if y["count"] >= 4]
    if len(full) > 1:
        worst = min(full, key=lambda y: y["open"] / y["count"])
        segments += [
            reader.T("; the smallest share in "), reader.N("worst_year", worst["year"], "year"), reader.T(", "),
            reader.N("worst_open", worst["open"], "count"), reader.T(" of "),
            reader.N("worst_weeks", worst["count"], "count"), reader.T(", when TTF stood above JKM in "),
            reader.N("worst_ttf_above", worst["ttf_above"], "count"), reader.T(" of them"),
        ]
    return segments + [reader.T(".")]


def _hstar_heading(points: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    near = [p for p in points if p.get("reported_hire") is not None]
    opened = sum(p["reported_open"] for p in near)
    days = reader.N("max_days", config.PARAMETERS["hire_anchor_max_days"].value, "count")
    if not near:
        return [reader.T("No charter rate was reported within "), days, reader.T(" days of any of these weeks.")]
    return [
        reader.T("In the "), reader.N("weeks_near", len(near), "count"), reader.T(" weeks within "), days,
        reader.T(" days of a reported charter rate, the rate was below the hire the cheapest route east could "
                 "pay and still net what Gate does in "),
        reader.N("weeks_near_open", opened, "count"), reader.T(" of them."),
    ]


def _monthly_heading(points: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    years = _by_year(points)
    opened = sum(y["open"] for y in years)
    count = sum(y["count"] for y in years)
    segments = [
        reader.T("Month by month from "), reader.D("first_month", points[0]["day"], "month"),
        reader.T(", the arb east was open at the central hire in "), reader.N("months_open", opened, "count"),
        reader.T(" of "), reader.N("months", count, "count"), reader.T(" months"),
    ]
    every = [y["year"] for y in years if y["count"] >= 6 and y["open"] == y["count"]]
    if every:
        segments += [reader.T(", every month observed of "),
                     reader.W("years_every_month", reader.listed([str(y) for y in every]))]
    full = [y for y in years if y["count"] >= 6]
    if full:
        worst = min(full, key=lambda y: y["open"] / y["count"])
        segments += [reader.T("; the smallest share in "), reader.N("worst_year_month", worst["year"], "year"),
                     reader.T(", "), reader.N("worst_months_open", worst["open"], "count"), reader.T(" of "),
                     reader.N("worst_months", worst["count"], "count")]
    return segments + [reader.T(".")]


def _levels_segments(levels: Mapping[str, float]) -> list[dict[str, Any]]:
    return [reader.N("hire_low", levels["low"], "usd_day"), reader.T(", "),
            reader.N("hire_central", levels["central"], "usd_day"), reader.T(" and "),
            reader.N("hire_high", levels["high"], "usd_day"), reader.T(" $/day")]


def _routes_words(points: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Which route was the cheapest open one east, and in how many points each."""
    counts: dict[str, int] = {}
    for point in points:
        if point["route"]:
            counts[point["route"]] = counts.get(point["route"], 0) + 1
    if len(counts) == 1:
        (route,) = counts
        return [reader.T("The cheapest open route east was "), reader.W("cheapest", SHORT_NAMES[route]),
                reader.T(" in every one. ")]
    ordered = sorted(counts.items(), key=lambda item: -item[1])
    out = [reader.T("The cheapest open route east was ")]
    for index, (route, count) in enumerate(ordered):
        if index:
            out.append(reader.T(", and " if index == len(ordered) - 1 else ", "))
        out += [reader.W("cheapest_" + route, SHORT_NAMES[route]), reader.T(" in "),
                reader.N("cheapest_count_" + route, count, "count")]
    return out + [reader.T(" of them. ")]


def _weekly_desc(points: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        reader.T("A line of JKM's premium over TTF for each week from "), reader.D("first", points[0]["day"]),
        reader.T(" to "), reader.D("last", points[-1]["day"]),
        reader.T(", over a shaded band of the breakeven spread S* of the cheapest open route east, from the low "
                 "to the high hire, with a dashed line at the central hire. Where the line runs above the dashed "
                 "line the arb east was open. Rings mark the weeks in which, by the futures calendars, the JKM and "
                 "TTF front months name different delivery months every day, solid dots the weeks in which they "
                 "differ on some days; lettered marks at the foot are events, and numbered rules mark the breaks "
                 "listed under the charts."),
    ]


def _weekly_caption(points: Sequence[Mapping[str, Any]], levels: Mapping[str, float]) -> list[dict[str, Any]]:
    rings = sum(p["alignment"] == "misaligned" for p in points)
    mixed = sum(p["alignment"] == "mixed" for p in points)
    return [
        *_routes_words(points),
        reader.T("The hire levels are the lowest, the median and the highest charter rate reported: "),
        *_levels_segments(levels), reader.T(". Rings: the "), reader.N("misaligned", rings, "count"),
        reader.T(" weeks in which, by the futures calendars, the JKM and TTF front months name different delivery "
                 "months every day; solid dots: the "), reader.N("mixed", mixed, "count"),
        reader.T(" weeks in which they differ on some days. Where the prices drawn were swaps, spot or day-ahead, "
                 "as before the futures of mid "),
        reader.D("futures_from", "2022-07-13", "month"),
        reader.T(", a mark shows the calendar, not the prices."),
    ]


def _hstar_desc(points: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        reader.T("A line of H*, the hire at which the cheapest open route east nets what Gate does, for each "
                 "week from "), reader.D("first", points[0]["day"]), reader.T(" to "),
        reader.D("last", points[-1]["day"]),
        reader.T(", with each charter rate reported as a point, the latest in the accent. A rate below the line "
                 "is a week the arb east was open at the market's own freight."),
    ]


def _hstar_caption(domain: Mapping[str, Any], anchors: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    out = [reader.T("In thousands of dollars a day. ")]
    sides = [(key, words) for key, words in (("below", " below it"), ("above", " above it")) if domain[key]]
    if sides:
        out.append(reader.T("The scale shows the middle of the values: "))
        for index, (key, words) in enumerate(sides):
            if index:
                out.append(reader.T(" and "))
            out += [reader.N(key, domain[key], "count"),
                    reader.T((" week lies" if domain[key] == 1 else " weeks lie") + words)]
        out.append(reader.T(", each a short tick at the edge, its figure in history.json. "))
    out.append(reader.T("The points are the charter rates the study holds, each dated by the day it refers to "
                        "or, where its article gives none, by the article's date"))
    if anchors:
        latest = max(anchors, key=lambda a: a["date"])
        out += [reader.T("; the latest, "), reader.N("latest_hire", latest["hire_usd_day"], "usd_day"),
                reader.T(" $/day on "), reader.D("latest_hire_day", latest["date"]), reader.T(", is in the accent")]
    return out + [reader.T(".")]


def _monthly_desc(points: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        reader.T("A line of JKM's premium over TTF for each month from "),
        reader.D("first_month", points[0]["day"], "month"), reader.T(" to "),
        reader.D("last_month", points[-1]["day"], "month"),
        reader.T(", over the band of S* of the cheapest open route east from the low to the high hire, with a "
                 "dashed line at the central hire. A month with no observation is a gap in the line."),
    ]


def _monthly_caption(points: Sequence[Mapping[str, Any]], change: date, without: int) -> list[dict[str, Any]]:
    last_meti = max(p["day"] for p in points if p["series"].startswith("meti"))
    return [
        *_routes_words(points),
        reader.T("To "), reader.D("last_meti", last_meti, "month"),
        reader.T(" the JKM is METI's contract-based spot price for Japan, a proxy; from "),
        reader.D("first_weekly_month", change, "month"),
        reader.T(" it is the mean of the month's weekly JKM, a change of definition the chart's rules mark. "),
        reader.N("months_without", without, "count"),
        reader.T(" months have no observation, each a gap in the line; the methodology lists why."),
    ]


def _columns(points: Sequence[Mapping[str, Any] | None], keys: Sequence[str]) -> dict[str, list[Any]]:
    """The points as columns, a gap as null in every one."""
    return {key: [None if p is None else p.get(key) for p in points] for key in keys}


def _event_marks(items: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """The events as the charts draw them: a lettered mark, or a bar for a period."""
    return [{"day": item["day"], "end": item["end"], "letter": item["letter"]} for item in items]


def _events_lead(items: Sequence[Mapping[str, Any]], left_out: Sequence[tuple[str, str]]) -> list[dict[str, Any]]:
    return [
        reader.T("The lettered marks under the charts are events that explain a regime, not breaks in the data: "),
        reader.N("events", len(items), "count"),
        reader.T(" events, each from one document read, and "),
        reader.N("left_out", len(left_out), "count"),
        reader.T(" left out, listed after the table, each with the reason."),
    ]


def page(rows: pd.DataFrame, breaks: pd.DataFrame, anchors: Sequence[Mapping[str, Any]],
         months_without: pd.DataFrame, levels: Mapping[str, float],
         events: Sequence[Mapping[str, Any]] = (), left_out: Sequence[tuple[str, str]] = ()) -> dict[str, Any]:
    """The History view's layer of history.json."""
    weekly = _points(rows, "weekly")
    monthly = _points(rows, "monthly")
    last = weekly[-1]["day"]
    drawn = breaks[breaks["kind"].isin(DRAWN)].reset_index(drop=True)
    numbered = [{"number": i + 1, "day": r["day"].date(), "kind": r["kind"], "what": r["what"], "source": r["source"]}
                for i, r in drawn.iterrows()]
    # Breaks on the same day share one rule, labelled with their numbers; the
    # page merges the labels of rules too close to print apart.
    rules: list[dict[str, Any]] = []
    for item in numbered:
        if rules and item["day"] == rules[-1]["day"]:
            rules[-1]["numbers"].append(item["number"])
        else:
            rules.append({"day": item["day"], "numbers": [item["number"]]})

    ranges = []
    for range_id, label, first, end in RANGES:
        if range_id == "last_52":
            start = last - timedelta(weeks=51)
            stop = last
        else:
            start = date.fromisoformat(first) if first else weekly[0]["day"]
            stop = date.fromisoformat(end) if end else last
        chosen = [p for p in weekly if start <= p["day"] <= stop]
        if not chosen:
            continue
        in_range = [a for a in anchors if start - timedelta(days=14) <= a["date"] <= stop + timedelta(days=14)]
        hstar = _hstar_domain(chosen, in_range)
        ranges.append({
            "id": range_id, "label": label, "first": chosen[0]["day"], "last": chosen[-1]["day"],
            "y": _domain([v for p in chosen for v in (p["spread"], p["s_low"], p["s_high"])]),
            "hstar": hstar,
            "ticks": ticks(chosen[0]["day"], chosen[-1]["day"]),
            "heading_segments": _weekly_heading(chosen),
            "desc_segments": _weekly_desc(chosen),
            "caption_segments": _weekly_caption(chosen, levels),
            "hstar_heading_segments": _hstar_heading(chosen),
            "hstar_desc_segments": _hstar_desc(chosen),
            "hstar_caption_segments": _hstar_caption(hstar, [a for a in anchors if start <= a["date"] <= stop]),
            # The point in the accent: the latest rate reported inside the range.
            "accent_day": max((a["date"] for a in anchors if start <= a["date"] <= stop), default=None),
            "years": _by_year(chosen),
        })

    weekly_gaps = _with_gaps(weekly, 7)
    keys = ("day", "spread", "s_low", "s_central", "s_high", "route", "h_star", "alignment", "reported_hire",
            "reported_open")
    monthly_full = []
    observed = {p["day"].replace(day=1): p for p in monthly}
    month = monthly[0]["day"].replace(day=1)
    while month <= monthly[-1]["day"].replace(day=1):
        monthly_full.append(observed.get(month))
        month = date(month.year + month.month // 12, month.month % 12 + 1, 1)
    first_weekly_series = next(p for p in monthly if not p["series"].startswith("meti"))
    # The months with no observation inside the line: a month after its last
    # one, still in progress, is not a gap in it.
    without = [{"month": r["month"].date(), "reason": r["reason"]} for r in months_without.to_dict("records")
               if r["month"].date() <= monthly[-1]["day"]]
    latest = max(a["date"] for a in anchors)
    meti_end = max(p["day"] for p in monthly if p["series"].startswith("meti"))
    return {
        "words": {
            "spread": "JKM over TTF", "reference": "S*, central hire", "band": "S*, low to high hire",
            "h_star": "H*, cheapest route", "reported": "Reported", "y_axis": "$/MMBtu",
            "hstar_axis": "thousand $/day",
            "legend": "The ink line is JKM over TTF; the dashed line, S* at the central hire; the shaded band, S* "
                      "from the low to the high hire.",
            "hstar_legend": "The ink line is H* of the cheapest open route east; the rings are the charter rates "
                            "reported.",
            "weeks": {"caption": "Each year's weeks: how many, in how many the arb east was open at the central "
                                 "hire, and in how many TTF stood above JKM.",
                      "count": "Weeks", "open": "Arb east open", "ttf_above": "TTF above JKM"},
            "months": {"caption": "Each year's months: how many, in how many the arb east was open at the "
                                  "central hire, and in how many TTF stood above JKM.",
                       "count": "Months", "open": "Arb east open", "ttf_above": "TTF above JKM"},
            "anchors_caption": "Every charter rate reported that the study holds: the day it refers to, the rate, "
                               "the assessment and who reported it.",
            "breaks_caption": "Every break drawn as a numbered rule: the day it takes effect, its kind, what "
                              "changes and the source.",
            "events_caption": "Every event drawn as a lettered mark: the day it began, the day it ended where it "
                              "ran for a period, what happened and the document it was read in.",
            "events_heading": "The events behind the regimes",
            "left_out_heading": "Left out, and why",
        },
        "weekly": {**_columns(weekly_gaps, keys), "ranges": ranges},
        "monthly": {
            **_columns(monthly_full, ("day", "spread", "s_low", "s_central", "s_high", "route", "series")),
            "first": monthly[0]["day"], "last": monthly[-1]["day"],
            "y": _domain([v for p in monthly for v in (p["spread"], p["s_low"], p["s_high"])]),
            "ticks": ticks(monthly[0]["day"], monthly[-1]["day"]),
            "heading_segments": _monthly_heading(monthly),
            "desc_segments": _monthly_desc(monthly),
            "caption_segments": _monthly_caption(monthly, first_weekly_series["day"], len(without)),
            "years": _by_year(monthly),
            "without": without,
        },
        "breaks": [{**item, "kind_words": KIND_WORDS[item["kind"]]} for item in numbered],
        "rules": rules,
        "breaks_lead_segments": [
            reader.T("The numbered rules on the charts mark a change of price definition, of route, of ship or "
                     "of the EU ETS. A change of name alone, where the price runs on across it, is listed in the "
                     "methodology and not drawn."),
        ],
        "events": [{"letter": e["letter"], "day": date.fromisoformat(e["day"]),
                    "end": date.fromisoformat(e["end"]) if e["end"] else None, "what": e["what"],
                    "publisher": e["publisher"], "url": e["url"]} for e in events],
        "event_marks": _event_marks([{**e, "day": date.fromisoformat(e["day"]),
                                      "end": date.fromisoformat(e["end"]) if e["end"] else None} for e in events]),
        "events_lead_segments": _events_lead(events, left_out),
        "events_left_out": [{"what": what, "reason": reason} for what, reason in left_out],
        "anchors": [{"day": a["date"], "hire_usd_day": a["hire_usd_day"], "publisher": a["publisher"],
                     "assessment": a["assessment"], "accent": a["date"] == latest} for a in anchors],
        "divisor": HSTAR_DIVISOR,
        "source_segments": [
            reader.T("Prices: EIA's Natural Gas Weekly Update and its WNGSR Supplement each week; METI's spot LNG "
                     "survey and the World Bank's Pink Sheet each month to "),
            reader.D("meti_end", meti_end, "month"),
            reader.T(". Every other input of a date, and the engine, as the study's methodology sets out "
                     "(docs/methodology.md). Data to "), reader.D("as_of", last), reader.T("."),
        ],
    }

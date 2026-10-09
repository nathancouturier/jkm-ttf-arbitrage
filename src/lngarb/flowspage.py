"""The Flows view's data: did US cargoes follow the arb, and what the test cannot tell.

Five parts, each computed here from lngarb.analysis and the figures others
reported (lngarb.reported), drawn by the page as given:

* THE WHOLE PERIOD: the monthly share of US LNG exports by vessel to the JKM
  markets and to Asia, over the arb at loading at the central hire, every
  month from 2016 (the Now view shows the latest two years).
* THE TEST: the regression of each share on the arb, at the three hires and
  on two samples, with Newey-West errors, and the table of months by the sign
  of the arb against the share above or below its median.
* 2020: the lift margin of each loading month, at loading and at the notice
  date two months before, against the cargoes EIA reported cancelled.
* 2026: the weekly spread against the breakeven of Panama and of the Cape, set
  beside what Platts reported of the route US cargoes took and its own
  assessment of the arb.
* THE WAITS AT PANAMA: the waiting days reported in 2023, against the days at
  which Panama stops netting more than the Cape.

Every count in a sentence is computed from the rows; nothing is fitted but
the regression of docs/methodology.md section 12.2.
"""

from __future__ import annotations

import math
from datetime import date
from typing import Any, Mapping, Sequence

import pandas as pd

from . import analysis, config, reader, worked
from .freight_anchors import ANCHORS
from .spreadhistory import ticks
from .reported import reported

__all__ = ["page"]

SHARE_WORDS = {"share_jkm": "the JKM markets", "share_asia": "all Asia"}
LEVEL_WORDS = {"low": "low", "central": "central", "high": "high"}
#: The 2026 panel starts with the first week of the Supplement's predecessor's
#: last winter: the weeks Platts' route counts and assessment speak to.
FROM_2026 = date(2025, 12, 1)


def _finite(value: Any) -> float | None:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    return float(value)


def _iso(value: Any) -> str:
    return pd.Timestamp(value).date().isoformat()


def _whole(months: Sequence[Mapping[str, Any]], regressions: Sequence[Mapping[str, Any]], excluded: Sequence[int],
           central: float) -> dict[str, Any]:
    panel = reader.flows_panel(months, regressions, excluded, central, window=None)
    rows = panel["months"]
    panel["ticks"] = [i for i, r in enumerate(rows) if r["month"][5:7] == "01"] or [0]
    panel["ticks_narrow"] = [i for i, r in enumerate(rows) if r["month"][5:7] == "01" and int(r["month"][:4]) % 2 == 0] or [0]
    return panel


def _test(regressions: Sequence[Mapping[str, Any]], excluded: Sequence[int]) -> dict[str, Any]:
    rows = []
    for r in regressions:
        if "slope" not in r or _finite(r.get("slope")) is None:
            continue
        n, opened = int(r["n"]), int(r["months_open"])
        rows.append({
            "share": r["share"], "share_words": SHARE_WORDS[r["share"]],
            "sample": r["sample"], "hire_level": r["hire_level"],
            "n": n, "slope_pp": r["slope"] * 100.0, "t": r["t_slope"], "r2": r["r2"], "lags": int(r["lags"]),
            "first_month": r["first_month"] + "-01", "last_month": r["last_month"] + "-01",
            "open_above": int(r["open_above"]), "open_below": opened - int(r["open_above"]),
            "closed_below": int(r["closed_below"]), "closed_above": n - opened - int(r["closed_below"]),
            "median_share": r["median_share"] * 100.0,
        })
    by = {(r["share"], r["sample"], r["hire_level"]): r for r in rows}
    everything = by[("share_asia", "all months", "central")]
    without_sample = next(r["sample"] for r in rows if r["sample"] != "all months")
    without = by[("share_asia", without_sample, "central")]
    significant = [r for r in rows if abs(r["t"]) >= 2.0]
    heading = [
        reader.T("Asia took more of US exports in months the arb was open, but loosely: at the central hire a "
                 "dollar more of arb went with "), reader.N("slope", everything["slope_pp"], "pp"),
        reader.T(" points more to Asia over "), reader.N("n", everything["n"], "count"),
        reader.T(" months, with R squared "), reader.N("r2", everything["r2"], "r2"), reader.T(", and "),
        reader.N("slope_without", without["slope_pp"], "pp"), reader.T(" points without "),
        reader.W("excluded", reader.listed([str(y) for y in excluded])), reader.T(", R squared "),
        reader.N("r2_without", without["r2"], "r2"), reader.T(". The slope's t statistic is two or more in "),
        reader.N("significant", len(significant), "count"), reader.T(" of the "), reader.N("fits", len(rows), "count"),
        reader.T(" fits."),
    ]
    sign = by[("share_asia", "all months", "central")]
    sign_words = [
        reader.T("At the central hire, over all months: the arb was open in "),
        reader.N("sign_open", sign["open_above"] + sign["open_below"], "count"), reader.T(" months, "),
        reader.N("sign_open_above", sign["open_above"], "count"),
        reader.T(" of them with Asia's share above its median of "),
        reader.N("sign_median", sign["median_share"], "share_percent"), reader.T(" percent; it was closed in "),
        reader.N("sign_closed", sign["closed_above"] + sign["closed_below"], "count"), reader.T(", "),
        reader.N("sign_closed_below", sign["closed_below"], "count"), reader.T(" of them with the share at or below it."),
    ]
    return {"heading_segments": heading, "sign_segments": sign_words, "rows": rows,
            "caption": "The regression of each share on the arb at loading, at each hire and on each sample: months, "
                       "slope in points of share per dollar, its t statistic with Newey-West errors and their lags, "
                       "R squared, and the months by the sign of the arb against the share above or below its "
                       "median."}


def _y2020(levels: Mapping[str, float]) -> dict[str, Any]:
    frame = analysis.lift_margins_2020(levels=levels)
    cancelled = {r.period: r for r in reported("cancellations")}
    months = []
    for month in sorted(frame["month"].unique()):
        rows = frame[frame["month"] == month]

        def margin(prices: str, level: str) -> float | None:
            hit = rows[(rows["prices"] == prices) & (rows.get("hire_level") == level)]
            return None if hit.empty else _finite(hit.iloc[0]["lift_margin"])

        key = pd.Timestamp(month).strftime("%Y-%m")
        report = cancelled.get(key)
        notice_rows = rows[rows["prices"] == "at the notice date"]
        months.append({
            "month": _iso(month), "label": reader.MONTH_NAMES[pd.Timestamp(month).month - 1],
            "loading": {level: margin("at loading", level) for level in ("low", "central", "high")},
            "notice": {level: margin("at the notice date", level) for level in ("low", "central", "high")},
            "notice_day": None if notice_rows.empty else _iso(notice_rows.iloc[0]["priced_on"]),
            "cancelled": None if report is None else report.figure,
            "cancelled_words": None if report is None else report.what,
            "cancelled_source": None if report is None else report.publisher,
            "cancelled_url": None if report is None else report.url,
        })
    reported_months = [m for m in months if m["cancelled"] is not None]
    below = [m for m in reported_months if m["notice"]["central"] is not None and m["notice"]["central"] < 0]
    above = [m for m in reported_months if m not in below]
    high_below = [m for m in months if m["notice"]["high"] is not None and m["notice"]["high"] < 0]
    heading = [
        reader.T("By the notice date, two months ahead, the prices then published put the lift margin at the "
                 "central hire below zero for "), reader.W("below", reader.listed([m["label"] for m in below]) or "no month"),
        reader.T(" of the "), reader.N("reported_months", len(reported_months), "count"),
        reader.T(" months of "), reader.N("year", pd.Timestamp(months[0]["month"]).year, "year"),
        reader.T(" for which EIA reported cargoes cancelled"),
    ]
    if above:
        heading += [reader.T("; for "), reader.W("above", reader.listed([m["label"] for m in above])),
                    reader.T(" it was above zero at the central hire")]
    heading += [reader.T(". At the high hire it was below zero in "), reader.N("high_below", len(high_below), "count"),
                reader.T(" of the "), reader.N("months_2020", len(months), "count"), reader.T(" months.")]
    domain_values = [v for m in months for side in ("loading", "notice") for v in m[side].values() if v is not None]
    low, high, step = reader.nice_domain(domain_values, 5)
    return {
        "heading_segments": heading,
        "months": months,
        "y": {"low": low, "high": high, "step": step},
        "ticks": ticks(date.fromisoformat(months[0]["month"]), date.fromisoformat(months[-1]["month"])),
        "desc": "Two lines over the loading months of 2020: the lift margin at the central hire with the prices "
                "published by the notice date, in ink over the band from the low to the high hire, and with the "
                "month's own prices, dashed.",
        "caption_segments": [
            reader.T("The notice date is the day two months before loading that Sabine Pass's agreement with "
                     "Centrica sets; the prices then published are METI's latest month by then, usually the month "
                     "three before, the World Bank's TTF for that same month, and Henry Hub's spot since the month "
                     "two before. "
                     "Cancellations: EIA, Today in Energy, "), reader.D("eia_note", "2020-08-11"),
            reader.T(", about the cargoes cancelled for June to September."),
        ],
    }


def _y2026(rows: pd.DataFrame, months: Sequence[Mapping[str, Any]] = (),
           regas: pd.DataFrame | None = None) -> dict[str, Any]:
    weekly = rows[(rows["frequency"] == "weekly") & (rows["hire_level"] == "central")
                  & (rows["day"] >= pd.Timestamp(FROM_2026))].sort_values("day")
    points = []
    for r in weekly.to_dict("records"):
        points.append({"day": _iso(r["day"]), "spread": _finite(r["spread"]),
                       "panama": _finite(r["panama_s_star"]) if r["panama_open"] else None,
                       "cape": _finite(r["cape_s_star"]) if r["cape_open"] else None})
    cape_counts = reported("cape_use")
    latest_cape = max(cape_counts, key=lambda r: r.period)
    (asia,) = [r for r in reported("asia_use") if r.period == latest_cape.period]
    assessments = {("panama" if "Panama" in r.what else "cape"): r for r in reported("arb_assessment")}
    day = pd.Timestamp(latest_cape.period)
    near = rows[(rows["frequency"] == "weekly") & (rows["day"] >= day - pd.Timedelta(days=3))].sort_values("day")
    week = near["day"].iloc[0]
    at = rows[(rows["frequency"] == "weekly") & (rows["day"] == week)].set_index("hire_level")
    both = [p for p in points if p["spread"] is not None and p["day"] <= _iso(week)]
    panama_open = sum(p["panama"] is not None and p["spread"] > p["panama"] for p in both)
    cape_open = sum(p["cape"] is not None and p["spread"] > p["cape"] for p in both)
    heading = [
        reader.T("From "), reader.D("first", points[0]["day"], "month"), reader.T(" to the week ending "),
        reader.D("assessment_week", week), reader.T(", the spread covered Panama's breakeven at the central hire "
                                                    "in "), reader.N("panama_open", panama_open, "count"),
        reader.T(" of "), reader.N("weeks", len(both), "count"), reader.T(" weeks and the Cape's in "),
        reader.N("cape_open", cape_open, "count"),
        reader.T(", while Platts counted "), reader.N("cape_cargoes", latest_cape.figure, "count"),
        reader.T(" of "), reader.N("asia_cargoes", asia.figure, "count"),
        reader.T(" US cargoes to Asia-Pacific destinations round the Cape in data to "),
        reader.D("cape_day", latest_cape.period),
        reader.T(", when, by Platts' sources, auctioned slots had made Panama impractical for spot cargoes."),
    ]
    compare = [
        {"route": route, "platts": assessments[route].figure,
         "study": {level: _finite(at.loc[level, route + "_arb"]) for level in ("low", "central", "high")
                   if level in at.index},
         "reported": _finite(at.loc["reported", route + "_arb"]) if "reported" in at.index else None}
        for route in ("panama", "cape")
    ]
    low, high, step = reader.nice_domain([v for p in points for v in (p["spread"], p["panama"], p["cape"])
                                          if v is not None], 5)
    return {
        "heading_segments": heading,
        "story_segments": _y2026_story(rows, points, _iso(week), months, regas),
        # The point in the accent: the week the arb east first opened via the cheaper route.
        "accent": _accent_2026(points, _iso(week)),
        "source_segments": [
            reader.T("Prices: EIA's Natural Gas Weekly Update and, from its end, the WNGSR Supplement, each week; S* "
                     "by the engine at the central hire, as the methodology sets out; data to "),
            reader.D("y2026_last", points[-1]["day"]), reader.T("."),
        ],
        "days": [p["day"] for p in points],
        "spread": [p["spread"] for p in points],
        "panama": [p["panama"] for p in points],
        "cape": [p["cape"] for p in points],
        "y": {"low": low, "high": high, "step": step},
        "ticks": ticks(date.fromisoformat(points[0]["day"]), date.fromisoformat(points[-1]["day"])),
        "desc": "A line of JKM's premium over TTF for each week, over the breakeven spread S* of Panama, a thin "
                "line, and of the Cape, a dotted one, both at the central hire. Where the ink line runs above "
                "a route's line, that route netted more than Gate.",
        "assessment_day": latest_cape.period,
        "assessment_week": _iso(week),
        "compare_caption_segments": [
            reader.T("Platts' arbitrage of US cargoes to North Asia against the Atlantic, in $/MMBtu, on "),
            reader.D("assessment_day", latest_cape.period),
            reader.T(", beside this study's arb at the three hires for the week ending "),
            reader.D("assessment_week", week), reader.T("."),
        ],
        "compare": compare,
        "reported": [{"period": r.period, "figure": r.figure, "what": r.what, "publisher": r.publisher, "url": r.url,
                      "format": "count" if r.unit == "cargoes" else "usd_mmbtu", "signed": r.unit != "cargoes"}
                     for r in (asia, *cape_counts, *reported("panama_use"), *assessments.values())],
    }


def _opening(points: Sequence[Mapping[str, Any]], route: str, last: str) -> Mapping[str, Any] | None:
    """The first week of the run of weeks, up to the last, in which the spread
    covered the route's breakeven: the week the arb east opened via that route."""
    first = None
    for p in points:
        if p["day"] > last:
            break
        covered = p[route] is not None and p["spread"] is not None and p["spread"] > p[route]
        first = (first or p) if covered else None
    return first


def _accent_2026(points: Sequence[Mapping[str, Any]], week: str) -> dict[str, Any] | None:
    found = [o for o in (_opening(points, "panama", week), _opening(points, "cape", week)) if o is not None]
    if not found:
        return None
    first = min(found, key=lambda o: o["day"])
    return {"day": first["day"], "value": first["spread"]}


def _y2026_story(rows: pd.DataFrame, points: Sequence[Mapping[str, Any]], week: str,
                 months: Sequence[Mapping[str, Any]], regas: pd.DataFrame | None) -> list[dict[str, Any]]:
    """When the arb east opened in 2026, at what hire, and whether flows followed:
    sentences computed from the weekly rows, the freight anchors and the
    monthly shares."""
    T, N, D, W = reader.T, reader.N, reader.D, reader.W
    panama, cape = _opening(points, "panama", week), _opening(points, "cape", week)
    if panama is None and cape is None:
        return [T("The spread covered neither route's breakeven in the weeks to the assessment.")]
    opened = min((o for o in (panama, cape) if o is not None), key=lambda o: o["day"])
    out = [T("At the central hire the arb east opened")]
    if panama is not None:
        out += [T(" via Panama in the week ending "), D("panama_opened", panama["day"]), T(", JKM over TTF "),
                N("panama_spread", panama["spread"], "usd_mmbtu", signed=True), T(" $/MMBtu against a breakeven of "),
                N("panama_s_star", panama["panama"], "usd_mmbtu", signed=True)]
    if cape is not None:
        out += [T(" and" if panama is not None else ""), T(" round the Cape in the week ending "),
                D("cape_opened", cape["day"])]
    out += [T(", and stayed open to the week Platts assessed.")]

    # The weeks before that run that read open only through ACER's spread.
    if regas is not None and not regas.empty:
        lagged = regas[(regas["day"] >= pd.Timestamp(FROM_2026)) & (regas["day"] < pd.Timestamp(opened["day"]))
                       & regas["data_open"] & ~regas["zero_open"]]
        if not lagged.empty:
            out += [T(" The weeks ending "), W("lagged", reader.listed([reader.day_label(d) for d in lagged["day"]])),
                    T(" read open before it only through Europe's DES spread, ACER's assessment of a half month "
                      "ahead lagging TTF's jump; with that spread at zero they were closed.")]

    # The breakeven hire in the opening week against the rates reported around it.
    at = rows[(rows["frequency"] == "weekly") & (rows["hire_level"] == "central")
              & (rows["day"] == pd.Timestamp(opened["day"]))]
    h_panama = None
    spot_above = False
    if not at.empty:
        r = at.iloc[0]
        h_panama, h_cape = _finite(r["panama_h_star"]), _finite(r["cape_h_star"])
        day = date.fromisoformat(opened["day"])
        near = sorted((a for a in ANCHORS if abs((worked._anchor_day(a) - day).days) <= 31),
                      key=lambda a: worked._anchor_day(a))
        if h_panama is not None and h_cape is not None:
            out += [T(" In the week ending "), D("h_week", opened["day"]),
                    T(" a ship paid its way east at any hire below "), N("h_panama", h_panama, "usd_day"),
                    T(" $/day via Panama and "), N("h_cape", h_cape, "usd_day"), T(" $/day round the Cape")]
            for index, a in enumerate(near):
                above = sum(a.hire_usd_day > h for h in (h_panama, h_cape))
                spot_above = spot_above or above == 2
                where = {2: "above both", 1: "between the two", 0: "below both"}[above]
                out += [T("; " if index else "; the rates reported nearest were "),
                        N("near_hire", a.hire_usd_day, "usd_day"), T(" $/day on "),
                        D("near_day", worked._anchor_day(a)), T(", " + where)]
            out += [T(".")]

    # Did flows follow: the share of the JKM markets month by month.
    year = int(opened["day"][:4])
    by_month = [m for m in months if m["month"][:4] == str(year) and m.get("share_jkm") is not None]
    open_month = opened["day"][:7]
    before = [m for m in by_month if m["month"][:7] < open_month]
    after = [m for m in by_month if m["month"][:7] >= open_month]
    if before and after:
        peak = max(after, key=lambda m: m["share_jkm"])
        out += [T(" The JKM markets took "), N("share_first", before[0]["share_jkm"] * 100.0, "share_percent"),
                T(" percent of US exports by vessel in "), D("share_first_month", before[0]["month"], "month")]
        if len(before) > 1:
            out += [T(" and "), N("share_before", before[-1]["share_jkm"] * 100.0, "share_percent"),
                    T(" in "), D("share_before_month", before[-1]["month"], "month")]
        out += [T(", "), N("share_open", after[0]["share_jkm"] * 100.0, "share_percent"), T(" in "),
                D("share_open_month", after[0]["month"], "month"), T(" and "),
                N("share_peak", peak["share_jkm"] * 100.0, "share_percent"), T(" at the highest, in "),
                D("share_peak_month", peak["month"], "month"), T(".")]
        rose_first = len(before) > 1 and before[-1]["share_jkm"] > before[0]["share_jkm"]
        rose = after[0]["share_jkm"] > before[-1]["share_jkm"]
        if rose_first:
            out += [T(" The rise began before the arb opened.")]
        if rose and not at.empty and h_panama is not None and spot_above:
            out += [T(" Cargoes moved east while a spot hire reported nearby sat above both breakevens: spot hire is "
                      "not the marginal cost of a cargo on a ship already chartered.")]
    return out


def _waits(rows: pd.DataFrame) -> dict[str, Any]:
    frame = analysis.reported_waits(rows)
    out = []
    for r in frame.to_dict("records"):
        out.append({"month": _iso(r["month"]), "label": reader.month_label(r["month"]), "hire_level": r["hire_level"],
                    "hire_usd_day": _finite(r["hire_usd_day"]),
                    "wait_reported": r["wait_days_reported"],
                    "wait_breakeven": _finite(r["wait_days_breakeven"]),
                    "lead_no_wait": _finite(r["panama_minus_cape_no_wait"]),
                    "lead_with_wait": _finite(r["panama_minus_cape_with_wait"])})
    central = [r for r in out if r["hire_level"] == "central"]
    longer = all(r["wait_breakeven"] is not None and r["wait_reported"] > r["wait_breakeven"] for r in central)
    heading = [reader.T("Where waits at Panama were reported for LNG, "
                        + ("each was longer than" if longer else "set beside")
                        + " the wait at which Panama stops netting more than the Cape: ")]
    for index, r in enumerate(central):
        if index:
            heading.append(reader.T("; "))
        heading += [reader.N("reported_" + r["month"][:7], r["wait_reported"], "days"), reader.T(" days in "),
                    reader.D("month_" + r["month"][:7], r["month"], "month"), reader.T(" against "),
                    reader.N("breakeven_" + r["month"][:7], r["wait_breakeven"], "days", missing="none"),
                    reader.T(" at the central hire")]
    waits = config.PARAMETERS["panama_waits_reported"]
    return {"heading_segments": heading + [reader.T(".")], "rows": out,
            "source": reader.dates_in_words("Waits reported: " + waits.source)}


def page(rows: pd.DataFrame, months: Sequence[Mapping[str, Any]], regressions: Sequence[Mapping[str, Any]],
         excluded: Sequence[int], levels: Mapping[str, float], regas: pd.DataFrame | None = None) -> dict[str, Any]:
    """The Flows view's layer of flows.json."""
    return {
        "whole": _whole(months, regressions, excluded, levels["central"]),
        "test": _test(regressions, excluded),
        "y2020": _y2020(levels),
        "y2026": _y2026(rows, months, regas),
        "waits": _waits(rows),
        "limits_segments": [
            reader.T("What the test cannot separate: long term contracts with Asian buyers, whose cargoes move "
                     "whatever the spot economics; the slot constraints at Panama; China's tariff on US LNG from "),
            reader.D("china_tariff_from", "2025-02-10", "month"),
            reader.T("; the gap between spot hire and the cost of a ship already on term charter; the month, "
                     "coarser than the decisions, which are taken weeks before a cargo loads; and, before "),
            reader.D("meti_end", "2021-04-01", "month"),
            reader.T(", a Japanese spot price standing in for JKM. An association is all it can show."),
        ],
        "words": {
            "test_heading": "The test: each share against the arb",
            "y2020_heading": "2020: the lift margin when the notice was due",
            "y2026_heading": "2026: the breakeven against the route taken",
            "waits_heading": "The waits at Panama",
            "spread": "JKM over TTF", "panama": "S*, Panama", "cape": "S*, the Cape",
            "notice": "At the notice date", "loading": "At loading", "band": "Low to high hire",
            "y_axis": "$/MMBtu",
            "panama_route": "To North Asia via Panama", "cape_route": "To North Asia round the Cape",
            "y2026_legend": "The ink line is JKM over TTF; the thin line, S* via Panama; the dotted line, S* round "
                            "the Cape; both at the central hire. The dot in the accent is the week the arb east "
                            "opened.",
            "y2020_legend": "The ink line is the lift margin at the notice date at the central hire, over the "
                            "band from the low to the high hire; the dashed line, the margin with the month's own "
                            "prices.",
            "y2020_caption": "The lift margin of each loading month of the year, at the notice date at each hire "
                             "and at loading at the central hire, and the cargoes reported cancelled.",
            "waits_caption": "Panama against the Cape in the months a wait was reported for LNG: the wait "
                             "reported, the wait at which the two routes net the same, and Panama's lead over the "
                             "Cape without and with the wait, in $/MMBtu.",
        },
    }

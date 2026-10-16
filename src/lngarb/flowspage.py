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

import json
import math
from datetime import date
from typing import Any, Mapping, Sequence

import pandas as pd

from . import analysis, config, freight_anchors, panama_transits, reader
from .sources import base
from .spreadhistory import ticks
from .reported import reported

__all__ = ["page"]

SHARE_WORDS = {"share_jkm": "the JKM markets", "share_asia": "all Asia"}
LEVEL_WORDS = {"low": "low", "central": "central", "high": "high"}
#: The 2026 panel starts with the first week of the Supplement's predecessor's
#: last winter: the weeks Platts' route counts and assessment speak to.
#: percent in one
PERCENT = 100.0
FROM_2026 = date(2025, 12, 1)


def _finite(value: Any) -> float | None:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    return float(value)


def _iso(value: Any) -> str:
    return pd.Timestamp(value).date().isoformat()


def _whole(months: Sequence[Mapping[str, Any]], regressions: Sequence[Mapping[str, Any]], excluded: Sequence[int],
           levels_by_ship: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    panel = reader.flows_panel(months, regressions, excluded, levels_by_ship, window=None)
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


def _spring_2026(rows: pd.DataFrame, months: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Did the arb east open in 2026, at what hire, and did the cargoes follow: the weeks
    of 2026 that a reported charter rate stands for, worked at that rate and at the
    central hire, and EIA's share of exports to Asia in the months around them."""
    year = rows[(rows["frequency"] == "weekly") & (rows["day"].dt.year == 2026)].sort_values("day")
    reported = year[year["hire_level"] == "reported"]
    central = year[year["hire_level"] == "central"].set_index("day")
    if reported.empty:
        return [reader.T("No charter rate reported in the latest year stands for a week of the data, so the arb "
                         "at the market's own freight cannot be read for it.")]
    # The weeks of the first half of the year a reported rate stood for: the
    # spring, when the question of the year was whether the arb opened and at
    # what hire.
    weeks = [w for w in reported.to_dict("records") if w["day"].month <= 6]
    if not weeks:
        weeks = reported.to_dict("records")[:1]
    opened = [w for w in weeks if _finite(w["arb"]) is not None and w["arb"] > 0]
    at_central = [w for w in weeks if _finite(central.at[w["day"], "arb"]) is not None and central.at[w["day"], "arb"] > 0]
    hires = sorted({float(w["hire_usd_day"]) for w in weeks})
    segments = [reader.T("In the first half of the latest year a reported charter rate stands for "),
                reader.N("weeks_reported", len(weeks), "count"),
                reader.T(" weeks, ending "), reader.D("first_reported", weeks[0]["day"]), reader.T(" to "),
                reader.D("last_reported", weeks[-1]["day"]), reader.T(", at ")]
    for index, hire in enumerate(hires):
        segments += [reader.T(" and " if index else ""), reader.N("hire_%d" % index, hire, "usd_day"), reader.T(" $/day")]
    segments += [reader.T(". At those rates the arb east was open in "), reader.N("open_reported", len(opened), "count"),
                 reader.T(" of them")]
    if opened:
        segments += [reader.T(", first in the week ending "), reader.D("first_open", opened[0]["day"]),
                     reader.T(" and last in the week ending "), reader.D("last_open", opened[-1]["day"]),
                     reader.T(", via "), reader.W("route_open", reader.ROUTE_SHORT["nea_" + str(opened[-1]["best_route_east"])])]
    segments += [reader.T("; at the central hire, in "), reader.N("open_central", len(at_central), "count"), reader.T(".")]
    by_month = {m["month"][:7]: m for m in months}
    spans = [w["day"].strftime("%Y-%m") for w in weeks]
    first_month = pd.Timestamp(spans[0] + "-01")
    before = (first_month - pd.DateOffset(months=1)).strftime("%Y-%m")
    after = (pd.Timestamp(spans[-1] + "-01") + pd.DateOffset(months=1)).strftime("%Y-%m")
    named = [before] + sorted(set(spans)) + [after]
    held = [(key, by_month[key]) for key in named if key in by_month and by_month[key].get("share_asia") is not None]
    if len(held) < 2:
        segments += [reader.T(" EIA's exports by destination do not yet reach the months after, so whether the cargoes "
                              "followed cannot be read.")]
        return segments
    segments += [reader.T(" By EIA's exports by destination, the share of US exports by vessel going to Asia was ")]
    for index, (key, month) in enumerate(held):
        segments += [reader.T(", " if 0 < index < len(held) - 1 else (" and " if index else "")),
                     reader.N("share_" + key, PERCENT * month["share_asia"], "share_percent"),
                     reader.T(" percent in "), reader.D("month_" + key, key + "-01", "month")]
    first_share, last_share = held[0][1]["share_asia"], held[-1][1]["share_asia"]
    rose = last_share > first_share
    segments += [reader.T(": the cargoes "), reader.W("followed", "followed" if (rose and opened) or (not rose and not opened) else "did not follow"),
                 reader.T(" the arb, the share "), reader.W("direction", "rising" if rose else "falling"),
                 reader.T(" over the months the open weeks fell in" if opened else " over those months"),
                 reader.T(", with the share's other movers, the contracts, the slots and the tariff, unseparated.")]
    return segments


def _y2026(rows: pd.DataFrame, months: Sequence[Mapping[str, Any]] = ()) -> dict[str, Any]:
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
        "spring_segments": _spring_2026(rows, months),
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


#: Where the neopanamax locks opened: the summaries print their transits from this month.
NEOPANAMAX_FROM = "2016-07-01"
#: The chokepoints the tables print, in the order the page shows them.
CHOKEPOINT_ORDER = ("Panama Canal", "Suez Canal", "Bab el-Mandeb Strait", "Cape of Good Hope", "Strait of Hormuz",
                    "Strait of Malacca", "Danish Straits", "Turkish Straits")


def _cwt_figure(ops: pd.DataFrame, wait_months: Sequence[str]) -> dict[str, Any]:
    """Canal Waters Time by month, the average as the line, the high and low as references."""
    ops = ops.sort_values("date")
    days = [_iso(d) for d in ops["date"]]
    avg = [_finite(v) for v in ops["cwt_hours_avg"]]
    high = [_finite(v) for v in ops["cwt_hours_high"]]
    low = [_finite(v) for v in ops["cwt_hours_low"]]
    y_low, y_high, step = reader.nice_domain([v for v in avg + high + low if v is not None], 5)
    peak = ops.loc[ops["cwt_hours_avg"].idxmax()]
    recent = ops[ops["date"] >= pd.Timestamp(NEOPANAMAX_FROM)]
    heading = [
        reader.T("Canal Waters Time at Panama, the hours from a ship's arrival to its departure, waiting included, "
                 "averaged over every ship in the month: "),
        reader.N("cwt_median", float(recent["cwt_hours_avg"].median()), "hours"),
        reader.T(" hours in the median month since the neopanamax locks opened in "),
        reader.D("neopanamax_from", NEOPANAMAX_FROM, "month"),
        reader.T(", "), reader.N("cwt_peak", float(peak["cwt_hours_avg"]), "hours"),
        reader.T(" in "), reader.D("cwt_peak_month", _iso(peak["date"]), "month"),
        reader.T(", the highest month, when the day's high reached "),
        reader.N("cwt_peak_high", float(peak["cwt_hours_high"]), "hours"),
        reader.T(" hours. The Authority counts every ship and does not split the figure by segment or by "
                 "booked and unbooked ships, so a month's average bounds what an LNG carrier without a slot "
                 "waited rather than measures it."),
    ]
    return {
        "heading_segments": heading,
        "days": days, "avg": avg, "high": high, "low": low,
        "y": {"low": y_low, "high": y_high, "step": step},
        "ticks": ticks(date.fromisoformat(days[0]), date.fromisoformat(days[-1])),
        "wait_months": [m for m in wait_months if m in days],
        "desc": "A line of the month's average Canal Waters Time in hours, between a thin line of the month's "
                "highest day and a dotted line of its lowest. The months with a wait reported for LNG carriers "
                "are marked in the accent.",
    }


def _years_table(sca: pd.DataFrame) -> list[dict[str, Any]]:
    panama = {t.fiscal_year: t.transits for t in panama_transits.TRANSITS}
    out = []
    for r in sca.sort_values("date").to_dict("records"):
        year = pd.Timestamp(r["date"]).year
        out.append({"year": year, "suez_ships": int(r["lng_ships"]), "suez_net_ton_thousand": int(r["net_ton_thousand"]),
                    "panama_transits": panama.get(year)})
    return out


def _chokepoint_rows(frame: pd.DataFrame, *, period: bool) -> list[dict[str, Any]]:
    out = []
    keys = ["date", "period"] if period else ["date"]
    for key, group in frame.groupby(keys, sort=True):
        day = key[0]
        label = (str(pd.Timestamp(day).year) + (" first half" if period and key[1] == "first_half" else "")) if period \
            else ("Q%d %d" % ((pd.Timestamp(day).month - 1) // 3 + 1, pd.Timestamp(day).year))
        values = {r["chokepoint"]: _finite(r["bcf_per_day"]) for r in group.to_dict("records")}
        out.append({"date": _iso(day), "label": label, "values": values})
    return out


def _quarter_segments(field: str, day: str) -> list[dict[str, Any]]:
    """A quarter in words and a year as a value: 'first quarter of 2025'."""
    when = pd.Timestamp(day)
    return [reader.W(field + "_quarter", reader.ORDINALS[str((when.month - 1) // 3 + 1)]), reader.T(" quarter of "),
            reader.N(field + "_year", when.year, "year")]


def _canals(wait_months: Sequence[str]) -> dict[str, Any]:
    """What the canal authorities and EIA count: transits by year, Canal Waters Time by month, LNG by chokepoint."""
    ops = base.read_cache("acp_canal_operations_monthly")
    sca = base.read_cache("sca_lng_transits_annual")
    annual = base.read_cache("eia_chokepoint_lng_annual")
    quarterly = base.read_cache("eia_steo_chokepoint_lng_quarterly")
    for name, frame in (("acp_canal_operations_monthly", ops), ("sca_lng_transits_annual", sca),
                        ("eia_chokepoint_lng_annual", annual), ("eia_steo_chokepoint_lng_quarterly", quarterly)):
        if frame is None or not len(frame):
            raise ValueError("the Flows view needs the committed cache %s" % name)
    years = _years_table(sca)
    latest = years[-1]
    before = years[-2]
    peak = max(years, key=lambda r: r["suez_ships"])
    fiscal = panama_transits.TRANSITS
    fiscal_peak = max(fiscal, key=lambda t: t.transits)
    chokepoints = [c for c in CHOKEPOINT_ORDER if c in set(annual["chokepoint"]) | set(quarterly["chokepoint"])]
    heading = [
        reader.T("What the canal authorities count: "), reader.N("suez_latest", latest["suez_ships"], "count"),
        reader.T(" LNG carriers through Suez in "), reader.N("suez_latest_year", latest["year"], "year"),
        reader.T(" after "), reader.N("suez_before", before["suez_ships"], "count"), reader.T(" in "),
        reader.N("suez_before_year", before["year"], "year"), reader.T(" and "),
        reader.N("suez_peak", peak["suez_ships"], "count"), reader.T(" in "),
        reader.N("suez_peak_year", peak["year"], "year"), reader.T(", the most; "),
        reader.N("panama_latest", fiscal[-1].transits, "count"),
        reader.T(" through Panama in the fiscal year to September "),
        reader.N("panama_latest_year", fiscal[-1].fiscal_year, "year"), reader.T(" after "),
        reader.N("panama_peak", fiscal_peak.transits, "count"), reader.T(" in fiscal "),
        reader.N("panama_peak_year", fiscal_peak.fiscal_year, "year"),
        reader.T(". Both count every LNG carrier in both directions, Suez's deliveries to Egypt and Jordan and "
                 "ballast legs included, so neither is a count of US cargoes bound for Asia."),
    ]
    annual_rows = _chokepoint_rows(annual, period=True)
    quarterly_rows = _chokepoint_rows(quarterly, period=False)
    manifest = json.loads((base.DATA / "manifest.json").read_text(encoding="utf-8"))
    ops_entry = next((e for e in manifest["series"] if e["series"] == "acp_canal_operations_monthly"), {})
    return {
        "heading_segments": heading,
        "years": years,
        "cwt": _cwt_figure(ops, wait_months),
        "chokepoints": chokepoints,
        "annual": annual_rows,
        "quarterly": quarterly_rows,
        "annual_caption_segments": [
            reader.T("LNG through each chokepoint in billion cubic feet a day, EIA's analysis of Vortexa's tanker "
                     "tracking, by calendar year and the first half of "),
            reader.N("annual_last_year", pd.Timestamp(annual_rows[-1]["date"]).year, "year"),
            reader.T("; volumes in both directions, not split by origin."),
        ],
        "quarterly_caption_segments": [
            reader.T("The same by quarter, from the Short-Term Energy Outlook's energy security article, the "),
            *_quarter_segments("quarterly_first", quarterly_rows[0]["date"]), reader.T(" to the "),
            *_quarter_segments("quarterly_last", quarterly_rows[-1]["date"]),
            reader.T("; a cell EIA prints as a dash is left empty, since EIA does not say whether it is zero or "
                     "not available."),
        ],
        "years_caption": ("LNG carriers through the two canals a year, as their authorities count them: Suez by "
                          "calendar year with their Suez Canal net tonnage in thousands of tons, Panama by fiscal "
                          "year ending on 30 September, from the neopanamax locks' first full fiscal year."),
        "words": {
            "heading": "The canals, as their authorities count them",
            "cwt_legend": ("Ink: the month's average Canal Waters Time. Thin: the month's highest day. Dotted: its "
                           "lowest. Accent: the months with a wait reported for LNG carriers. Source: Panama "
                           "Canal Authority, Monthly Canal Operations Summary, " + str(ops_entry.get("vintage") or "")
                           + "; non-commercial use, and the Authority's figures may vary with traffic audits."),
            "years_source": ("Sources: Suez Canal Authority, annual navigation reports, Table 3; Panama Canal "
                             "Authority, annual reports, read by eye in their charts and text."),
            "chokepoints_source": ("Source: U.S. Energy Information Administration, World Oil Transit Chokepoints "
                                   "and Short-Term Energy Outlook, analysis based on Vortexa tanker tracking data, "
                                   "with the vintages the Provenance view records."),
            "suez_head": "Suez, LNG carriers", "suez_tons_head": "Suez, net tons, thousands",
            "panama_head": "Panama, LNG carriers, fiscal year", "year_head": "Year",
            "chokepoint_head": "Period", "cwt_y_axis": "hours",
        },
    }


def page(rows: pd.DataFrame, months: Sequence[Mapping[str, Any]], regressions: Sequence[Mapping[str, Any]],
         excluded: Sequence[int], levels: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    """The Flows view's layer of flows.json; levels are the hire levels by ship."""
    return {
        "whole": _whole(months, regressions, excluded, levels),
        "test": _test(regressions, excluded),
        # 2020 is priced with the TFDE, so its three levels are that ship's.
        "y2020": _y2020(freight_anchors.hire_levels(when=date(2020, 1, 1))),
        "y2026": _y2026(rows, months),
        "waits": _waits(rows),
        "canals": _canals([r["month"] for r in _waits(rows)["rows"]]),
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
                            "the Cape; both at the central hire.",
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

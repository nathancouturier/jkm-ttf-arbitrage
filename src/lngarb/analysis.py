"""When a US cargo goes east: the study's analysis, from the committed data.

Every price observation the study holds, weekly and monthly, is worked through
the engine as a cargo loading on its day: lngarb.worked builds each input the
data give for that day, and lngarb.cases prices every line. Each observation is
worked at the low, central and high hire the freight anchors give, and at the
hire reported nearest its date where one lies within the window the parameter
table sets. From those rows come:

* the breakeven spread S* of each route east, its three parts and the breakeven
  hire H*, against the observed JKM - TTF spread, with the structural breaks
  that separate the series (breaks);
* the monthly share of US LNG exports by vessel going to the JKM markets and to
  Asia, against the arb at the best open route east: a regression with
  Newey-West standard errors and a table of months by the sign of the arb
  (flows_test);
* the lift margin of 2020 month by month, with the prices of the loading month
  and with those published by the cancellation notice date
  (lift_margins_2020), beside the cancellations reported (lngarb.reported);
* the route the model picks, the waiting days or slot premium at which Panama
  stops paying against the Cape (route_choice), and Panama against the Cape
  with the waits reported in the months they were reported (reported_waits);
* the weeks whose verdict rests on Europe's regasification discount: each
  week at the discount the data give, at zero and at the assumption
  (regas_sensitivity).

Nothing here is fitted to an outcome: no parameter is searched and nothing is
forecast. A date the data cannot price is listed with the input it lacks.
"""

from __future__ import annotations

import math
from contextlib import contextmanager
from dataclasses import replace
from datetime import date
from typing import Any, Iterator, Mapping

import numpy as np
import pandas as pd

from . import cases, config, delivery, units, worked
from .cases import EAST, Inputs, evaluate
from .freight_anchors import hire_levels
from .sources import base

__all__ = [
    "ROUTES", "observations", "months_without_observation", "window", "work", "breaks", "export_shares",
    "monthly_arb", "newey_west", "flows_test", "sign_table", "lift_margins_2020", "route_choice",
    "panama_wait_breakeven", "reported_waits", "published_jkm_proxy", "regas_sensitivity",
]

#: The three routes east, by the short name the result columns use.
ROUTES = {route: route.split("_", 1)[1] for route in EAST}


def _p(name: str) -> Any:
    return config.PARAMETERS[name].value


# --------------------------------------------------------------------------
# Reading each cache once
# --------------------------------------------------------------------------

@contextmanager
def reading_once() -> Iterator[None]:
    """Read each cache file once for a whole run, not once per date and input.

    lngarb.worked reads the caches it needs for every date it prices; a run
    over several hundred dates would parse the same files thousands of times.
    Within this block each file is parsed once and every caller gets a copy.
    """
    seen: dict[tuple[str, str, str], pd.DataFrame | None] = {}
    original = base.read_cache

    def cached(name: str, *, date_col: str = "date", directory: str = "cache") -> pd.DataFrame | None:
        key = (name, date_col, directory)
        if key not in seen:
            seen[key] = original(name, date_col=date_col, directory=directory)
        frame = seen[key]
        return None if frame is None else frame.copy()

    saved = (base.read_cache, worked.read_cache)
    base.read_cache = cached
    worked.read_cache = cached
    try:
        yield
    finally:
        base.read_cache, worked.read_cache = saved


# --------------------------------------------------------------------------
# The observations
# --------------------------------------------------------------------------

OBSERVATION_COLUMNS = [
    "day", "frequency", "series", "jkm", "ttf", "jkm_source", "ttf_source", "basis",
    "alignment", "aligned_share", "weeks", "jkm_month", "ttf_month",
]


def _supplement_basis(definition: str) -> str:
    """The product a Supplement sentence names: near-month futures in one issue, none in the others."""
    return "near-month futures" if "near-month futures" in str(definition) else "product not named"


def _weekly() -> pd.DataFrame:
    rows = []
    ngwu = base.read_cache("eia_ngwu_international_weekly")
    for r in ngwu.itertuples(index=False):
        if pd.isna(r.east_asia_usd_mmbtu) or pd.isna(r.ttf_usd_mmbtu):
            continue
        day = r.date.date()
        rows.append({
            "day": r.date, "frequency": "weekly", "series": "ngwu",
            "jkm": float(r.east_asia_usd_mmbtu), "ttf": float(r.ttf_usd_mmbtu),
            "jkm_source": "EIA Natural Gas Weekly Update, East Asia, %s, week ending %s" % (r.east_asia_basis, day),
            "ttf_source": "EIA Natural Gas Weekly Update, TTF, %s, week ending %s" % (r.ttf_basis, day),
            "basis": "East Asia %s; TTF %s" % (r.east_asia_basis, r.ttf_basis),
        })
    wngsr = base.read_cache("eia_wngsr_international_weekly")
    for r in wngsr.itertuples(index=False):
        if pd.isna(r.jkm_usd_mmbtu) or pd.isna(r.ttf_usd_mmbtu):
            continue
        day = r.date.date()
        rows.append({
            "day": r.date, "frequency": "weekly", "series": "wngsr",
            "jkm": float(r.jkm_usd_mmbtu), "ttf": float(r.ttf_usd_mmbtu),
            "jkm_source": "EIA WNGSR Supplement, JKM, week ending %s" % day,
            "ttf_source": "EIA WNGSR Supplement, TTF, week ending %s" % day,
            "basis": "Supplement: JKM %s; TTF %s" % (_supplement_basis(r.jkm_definition),
                                                      _supplement_basis(r.ttf_definition)),
        })
    frame = pd.DataFrame(rows)
    tags = [delivery.week_alignment(d.date()) for d in frame["day"]]
    frame["alignment"] = [tag for tag, _ in tags]
    frame["aligned_share"] = [share for _, share in tags]
    frame["weeks"] = 1
    # The delivery month each front month named on the week's last day.
    frame["jkm_month"] = [delivery.jkm_front_month(d.date()).isoformat()[:7] for d in frame["day"]]
    frame["ttf_month"] = [delivery.ttf_front_month(d.date()).isoformat()[:7] for d in frame["day"]]
    return frame


def _monthly(weekly: pd.DataFrame) -> pd.DataFrame:
    rows = []
    loading_day = int(_p("analysis_monthly_loading_day"))
    first = pd.Timestamp(_p("analysis_first_month") + "-01")
    meti = base.read_cache("meti_spot_lng_monthly").set_index("date")["contract_based_usd_mmbtu"]
    wb = base.read_cache("worldbank_gas_monthly").set_index("date")["europe_gas_usd_mmbtu"]
    for month, jkm in meti.items():
        ttf = wb.get(month)
        if month < first or pd.isna(jkm) or ttf is None or pd.isna(ttf):
            continue
        rows.append({
            "day": month.replace(day=loading_day), "frequency": "monthly", "series": "meti_worldbank",
            "jkm": float(jkm), "ttf": float(ttf),
            "jkm_source": "METI spot LNG, contract-based, %s, a proxy for JKM" % month.strftime("%B %Y"),
            "ttf_source": "World Bank Pink Sheet, Europe gas (TTF), %s" % month.strftime("%B %Y"),
            "basis": "METI contract-based (a proxy for JKM); World Bank TTF",
            "weeks": None,
        })
    minimum = int(_p("analysis_min_weeks_per_month"))
    by_month = weekly.groupby(weekly["day"].dt.to_period("M"))
    for period, group in by_month:
        if len(group) < minimum:
            continue
        month = period.to_timestamp()
        series = "+".join(sorted(set(group["series"])))
        names = {"ngwu": "Natural Gas Weekly Update", "wngsr": "WNGSR Supplement"}
        source = " and ".join(names[s] for s in sorted(set(group["series"])))
        rows.append({
            "day": month.replace(day=loading_day), "frequency": "monthly", "series": "weekly_mean_" + series,
            "jkm": float(group["jkm"].mean()), "ttf": float(group["ttf"].mean()),
            "jkm_source": "mean of %d weekly averages, EIA %s, %s" % (len(group), source, month.strftime("%B %Y")),
            "ttf_source": "mean of %d weekly averages, EIA %s, %s" % (len(group), source, month.strftime("%B %Y")),
            "basis": "mean of the month's weekly averages: " + "; ".join(sorted(set(group["basis"]))),
            "weeks": len(group),
            # The share of the month's trading days, over its weeks, on which the
            # two front months named the same delivery month.
            "aligned_share": float(group["aligned_share"].mean()),
            "alignment": ("aligned" if group["aligned_share"].mean() == 1 else
                          "misaligned" if group["aligned_share"].mean() == 0 else "mixed"),
        })
    return pd.DataFrame(rows)


def observations() -> pd.DataFrame:
    """Every weekly and monthly observation, each with its loading day and price sources.

    Weekly: the Weekly Update's East Asia and TTF averages, then the
    Supplement's JKM and TTF, loading on the week's last day and tagged by how
    the two front months' delivery months line up over the week. Monthly, from
    the parameter table's first month: METI's contract-based price, a proxy for
    JKM, with the World Bank's TTF, to March 2021; then the mean of each month's
    weekly averages, for a month holding enough weeks. Each loads on the
    parameter table's day of the month.
    """
    weekly = _weekly()
    monthly = _monthly(weekly)
    frame = pd.concat([weekly, monthly], ignore_index=True)
    return frame.sort_values(["frequency", "day"]).reset_index(drop=True)[OBSERVATION_COLUMNS]


def months_without_observation(obs: pd.DataFrame | None = None) -> pd.DataFrame:
    """Each month from the first of the monthly history to the last week held that has no monthly observation, and why."""
    obs = observations() if obs is None else obs
    monthly = set(obs.loc[obs["frequency"] == "monthly", "day"].dt.to_period("M"))
    weekly = obs[obs["frequency"] == "weekly"]
    weeks = weekly.groupby(weekly["day"].dt.to_period("M")).size()
    meti = base.read_cache("meti_spot_lng_monthly")
    meti_last = meti.loc[meti["contract_based_usd_mmbtu"].notna(), "date"].max().to_period("M")
    first_weekly = weekly["day"].min().to_period("M")
    rows = []
    for period in pd.period_range(_p("analysis_first_month"), weekly["day"].max().to_period("M"), freq="M"):
        if period in monthly:
            continue
        if period <= meti_last:
            reason = "METI published no contract-based price for the month, or the World Bank no TTF"
        elif period < first_weekly:
            reason = "no public JKM: METI's survey has ended and JOGMEC's continuation stays private"
        else:
            reason = "%d weekly average(s) in the month, fewer than %d" % (
                int(weeks.get(period, 0)), int(_p("analysis_min_weeks_per_month")))
        rows.append({"month": period.to_timestamp(), "reason": reason})
    return pd.DataFrame(rows, columns=["month", "reason"])


# --------------------------------------------------------------------------
# Every observation through the engine
# --------------------------------------------------------------------------

def _flatten(out: Mapping[str, Any], inputs: Inputs) -> dict[str, Any]:
    west = out["west"]
    row: dict[str, Any] = {
        "vessel": inputs.vessel.name,
        "henry_hub": inputs.henry_hub,
        "delta_nwe": inputs.delta_nwe,
        "delta_nwe_source": inputs.sources.get("delta_nwe"),
        "spread": out["spread"],
        "west_netback": west["netback"],
        "west_days": west["days_total"],
        "best_route_east": ROUTES.get(out["best_route_east"]),
        "best_destination": out["best_destination"],
        "best_netback": out["best_netback"],
        "lift_margin": out["lift_margin"],
        "full_margin": out["full_margin"],
        "cancel": out["cancel"],
    }
    best = out["best_route_east"]
    row["arb"] = out["east"][best]["arb"] if best else math.nan
    row["s_star_best"] = out["east"][best]["s_star"] if best else math.nan
    for route, short in ROUTES.items():
        lines = out["east"].get(route)
        if lines is None:
            continue
        row.update({
            short + "_open": lines["open"],
            short + "_netback": lines["netback"],
            short + "_arb": lines["arb"],
            short + "_s_star": lines["s_star"],
            short + "_boil_off": lines["boil_off"],
            short + "_regas": lines["regas"],
            short + "_voyage": lines["voyage"],
            short + "_h_star": lines["h_star_usd_day"],
            short + "_days": lines["days_total"],
        })
    return row


def window(day: pd.Timestamp, frequency: str) -> tuple[date, date]:
    """The days a price of the frequency spans: the week to its last day, or its calendar month."""
    if frequency == "weekly":
        return (day - pd.Timedelta(days=6)).date(), day.date()
    first = day.replace(day=1)
    return first.date(), (first + pd.offsets.MonthEnd(0)).date()


def _hires(day: date, levels: Mapping[str, float]) -> list[tuple[str, float, str]]:
    out = [(name, float(value), "%s of the freight anchors" % name) for name, value in levels.items()]
    reported, source = worked.nearest_hire(day)
    if reported is not None:
        out.append(("reported", float(reported), source))
    return out


def work(obs: pd.DataFrame | None = None, *, levels: Mapping[str, float] | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Every observation through the engine at each hire level: (rows, missing).

    rows holds one row per observation and hire level: the three anchor levels,
    plus "reported" where a charter rate was reported near the date. missing
    lists each observation the data cannot price, with the input it lacks.
    """
    levels = dict(hire_levels() if levels is None else levels)
    with reading_once():
        obs = observations() if obs is None else obs
        rows, missing = [], []
        for o in obs.itertuples(index=False):
            day = o.day.date()
            try:
                inputs = worked.inputs_on(
                    day, o.jkm, o.ttf, {"jkm": o.jkm_source, "ttf": o.ttf_source},
                    hire_usd_day=levels["central"], delta_window=window(o.day, o.frequency),
                )
            except worked.MissingInput as exc:
                missing.append({"day": o.day, "frequency": o.frequency, "series": o.series, "reason": str(exc)})
                continue
            for level, hire, hire_source in _hires(day, levels):
                out = evaluate(replace(inputs, hire_usd_day=hire))
                row = {column: getattr(o, column) for column in OBSERVATION_COLUMNS}
                row.update({"hire_level": level, "hire_usd_day": hire, "hire_source": hire_source})
                row.update(_flatten(out, inputs))
                rows.append(row)
    return pd.DataFrame(rows), pd.DataFrame(missing, columns=["day", "frequency", "series", "reason"])


# --------------------------------------------------------------------------
# The breaks
# --------------------------------------------------------------------------

def _change_kind(before: str, after: str) -> str:
    """"naming" when every leg that changed names its product on one side only, "definition" otherwise."""
    strip = lambda basis: basis.replace("Supplement: ", "").split("; ")  # noqa: E731
    changed = [(b, a) for b, a in zip(strip(before), strip(after)) if b != a]
    if changed and all("product not named" in b or "product not named" in a for b, a in changed):
        return "naming"
    return "definition"


def breaks(obs: pd.DataFrame | None = None) -> pd.DataFrame:
    """The structural breaks that separate the series: definitions, the ship, routes, carbon.

    Definition changes are found in the data, as the week a stored basis
    changes (for the Supplement, the product it names, not its wording). A
    change where the product is named on one side only (the Weekly Update's TTF
    before 29 September 2021, the Supplement's one week of near-month futures)
    is kept with kind "naming": the levels run on across it (docs/methodology.md
    section 5). The allowance price's changes of source come from the two
    allowance caches, the others from the parameter table.
    """
    obs = observations() if obs is None else obs
    rows = []
    weekly = obs[obs["frequency"] == "weekly"].sort_values("day")
    previous = None
    for r in weekly.itertuples(index=False):
        if previous is not None and (r.series != previous.series or r.basis != previous.basis):
            if r.series != previous.series:
                kind, what = "definition", "the Natural Gas Weekly Update ends and the WNGSR Supplement begins"
            else:
                kind, what = _change_kind(previous.basis, r.basis), "from %s to %s" % (previous.basis, r.basis)
            rows.append({"day": r.day, "kind": kind, "what": what,
                         "source": "the stored item text of each issue"})
        previous = r
    monthly = obs[obs["frequency"] == "monthly"].sort_values("day")
    previous = None
    for r in monthly.itertuples(index=False):
        if previous is not None and r.series.split("_")[0] != previous.series.split("_")[0]:
            gap = (r.day.to_period("M") - previous.day.to_period("M")).n - 1
            rows.append({"day": r.day, "kind": "definition",
                         "what": "monthly JKM from %s to %s, after %d month(s) with no public JKM"
                                 % (previous.basis, r.basis, gap),
                         "source": "METI ends in March 2021; JOGMEC's continuation stays private"})
        previous = r
    parameters = config.PARAMETERS
    rows += [
        {"day": pd.Timestamp(_p("panama_open_to_lng_from")), "kind": "route",
         "what": "Panama open to LNG carriers (the neopanamax locks)",
         "source": parameters["panama_open_to_lng_from"].source},
        {"day": pd.Timestamp(_p("suez_closed_to_us_cargo_from")), "kind": "route",
         "what": "Suez closed to a US cargo: the first laden transit day not offered",
         "source": parameters["suez_closed_to_us_cargo_from"].source},
        {"day": pd.Timestamp(_p("vessel_174k_from")), "kind": "vessel",
         "what": "benchmark ship from the 160,000 m3 TFDE to the 174,000 m3 two-stroke",
         "source": parameters["vessel_174k_from"].source},
    ]
    phases = _p("ets_phase_in_by_year")
    for year, phase in sorted(phases.items()):
        rows.append({"day": pd.Timestamp(int(year), 1, 1), "kind": "carbon",
                     "what": "EU ETS on voyages into Northwest Europe at %d percent of emissions"
                             % round(100 * float(phase)),
                     "source": parameters["ets_phase_in_by_year"].source})
    rows.append({"day": pd.Timestamp(_p("ets_ch4_n2o_from")), "kind": "carbon",
                 "what": "methane and nitrous oxide counted in the EU ETS",
                 "source": parameters["ets_ch4_n2o_from"].source})
    common = base.read_cache("ec_eua_auction_monthly")
    german = base.read_cache("dehst_eua_german_auction_monthly")
    after_common = common.loc[common["eua_eur_t"].notna(), "date"].max() + pd.DateOffset(months=1)
    after_german = german.loc[german["eua_eur_t"].notna(), "date"].max() + pd.DateOffset(months=1)
    rows.append({"day": after_common, "kind": "carbon",
                 "what": "allowance price from the Commission's reports to DEHSt's average of the German "
                         "auctions, a proxy",
                 "source": "docs/sources.md 2.23"})
    rows.append({"day": after_german, "kind": "carbon",
                 "what": "allowance price held at the last month published, an assumption",
                 "source": parameters["eua_eur_t_after_published"].source})
    acer = base.read_cache("acer_lng_daily")
    if acer is not None:
        held = acer.loc[acer["nwe_benchmark_spread_eur_mwh"].notna(), "date"]
        if not held.empty:
            rows.append({"day": held.min(), "kind": "regas",
                         "what": "Europe's DES spread to TTF observed from ACER's assessments; the parameter "
                                 "table's assumption before",
                         "source": "ACER, LNG price assessments and benchmark (docs/sources.md 2.7)"})
    frame = pd.DataFrame(rows).sort_values(["day", "kind"]).reset_index(drop=True)
    return frame


# --------------------------------------------------------------------------
# Did the cargoes follow
# --------------------------------------------------------------------------

def export_shares() -> pd.DataFrame:
    """US LNG exports by vessel each month, and the shares going to the JKM markets and to Asia.

    From EIA's exports by destination, the block of exports by vessel: its own
    total row, and its countries summed by the region config.py gives each.
    Trucks to Canada and Mexico and re-exports of foreign LNG are left out. A
    month whose countries do not add up to the total within half an MMcf per
    country, the rounding of the figures, is noted; the shares use the total.
    """
    frame = base.read_cache("eia_lng_exports_monthly")
    vessel = frame[frame["block"] == "exports by vessel"]
    rows = []
    for day, group in vessel.groupby("date"):
        total = group.loc[group["code"] == "Z00", "mmcf"]
        countries = group[group["code"] != "Z00"]
        if total.empty or pd.isna(total.iloc[0]) or total.iloc[0] <= 0:
            continue
        total = float(total.iloc[0])
        jkm = float(countries.loc[countries["region"] == "jkm_markets", "mmcf"].sum())
        asia = float(countries.loc[countries["region"].isin(["jkm_markets", "other_asia"]), "mmcf"].sum())
        summed = float(countries["mmcf"].sum())
        by_region = {region: float(countries.loc[countries["region"] == region, "mmcf"].sum())
                     for region in ("europe", "middle_east_africa", "americas")}
        rows.append({
            "month": day.to_period("M").to_timestamp(),
            "total_mmcf": total, "jkm_markets_mmcf": jkm, "asia_mmcf": asia,
            "share_jkm": jkm / total, "share_asia": asia / total,
            **{"share_" + region: value / total for region, value in by_region.items()},
            "anomaly": None if abs(summed - total) <= 0.5 * len(countries) else
            "the countries add up to %.0f MMcf against a total of %.0f" % (summed, total),
        })
    return pd.DataFrame(rows)


def monthly_arb(rows: pd.DataFrame) -> pd.DataFrame:
    """The arb at the best open route east, month by month, one column per hire level."""
    monthly = rows[(rows["frequency"] == "monthly") & rows["hire_level"].isin(["low", "central", "high"])]
    table = monthly.pivot_table(index="day", columns="hire_level", values="arb", aggfunc="first")
    table.index = table.index.to_period("M").to_timestamp()
    table.index.name = "month"
    return table[["low", "central", "high"]]


def newey_west(y: np.ndarray, x: np.ndarray, months: np.ndarray, lags: int | None = None) -> dict[str, float]:
    """Ordinary least squares of y on a constant and x, with Newey-West standard errors.

    months gives each observation's month as an integer count, so that a gap in
    the sample (a year left out, a month with no price) is not taken for
    adjacency: a pair of residuals enters the lag l term only when the two
    months are l apart. The Bartlett kernel weights lag l by 1 - l / (L + 1),
    with L = floor(4 (n / 100) ^ (2/9)) unless given, and no small sample
    correction is applied.
    """
    y = np.asarray(y, dtype=float)
    x = np.asarray(x, dtype=float)
    months = np.asarray(months, dtype=int)
    n = len(y)
    if lags is None:
        lags = int(math.floor(4 * (n / 100.0) ** (2.0 / 9.0)))
    design = np.column_stack([np.ones(n), x])
    xtx_inv = np.linalg.inv(design.T @ design)
    beta = xtx_inv @ design.T @ y
    u = y - design @ beta
    scores = design * u[:, None]
    meat = scores.T @ scores
    position = {m: i for i, m in enumerate(months)}
    for lag in range(1, lags + 1):
        weight = 1.0 - lag / (lags + 1.0)
        gamma = np.zeros((2, 2))
        for i, m in enumerate(months):
            j = position.get(m - lag)
            if j is not None:
                gamma += np.outer(scores[i], scores[j])
        meat += weight * (gamma + gamma.T)
    cov = xtx_inv @ meat @ xtx_inv
    se = np.sqrt(np.diag(cov))
    r2 = 1.0 - (u @ u) / ((y - y.mean()) @ (y - y.mean()))
    return {
        "n": n, "lags": lags, "intercept": float(beta[0]), "slope": float(beta[1]),
        "se_intercept": float(se[0]), "se_slope": float(se[1]),
        "t_slope": float(beta[1] / se[1]), "r2": float(r2),
    }


def sign_table(arb: pd.Series, share: pd.Series) -> pd.DataFrame:
    """Months by the sign of the arb against the share above or below its median over the same months."""
    median = share.median()
    open_east = np.where(arb > 0, "arb east open", "arb east closed")
    above = np.where(share > median, "share above median", "share at or below median")
    table = pd.crosstab(pd.Series(open_east, name="arb"), pd.Series(above, name="share"))
    table.attrs["median"] = float(median)
    return table


def flows_test(rows: pd.DataFrame, shares: pd.DataFrame | None = None) -> pd.DataFrame:
    """The regression of each share on the arb, at each hire level, with and without the excluded years.

    One row per share (JKM markets, Asia), hire level and sample. The arb is the
    one at loading: the month's observation, at the best open route east.
    """
    shares = export_shares() if shares is None else shares
    arb = monthly_arb(rows)
    joined = shares.set_index("month").join(arb, how="inner")
    excluded = {int(y) for y in _p("analysis_excluded_years")}
    out = []
    for sample in ("all months", "without " + ", ".join(str(y) for y in sorted(excluded))):
        data = joined if sample == "all months" else joined[~joined.index.year.isin(excluded)]
        for share in ("share_jkm", "share_asia"):
            for level in ("low", "central", "high"):
                usable = data[[share, level]].dropna()
                if len(usable) < 3:
                    out.append({"share": share, "hire_level": level, "sample": sample, "n": len(usable)})
                    continue
                m = (usable.index.year * 12 + usable.index.month).to_numpy()
                result = newey_west(usable[share].to_numpy(), usable[level].to_numpy(), m)
                table = sign_table(usable[level], usable[share])
                result.update({
                    "share": share, "hire_level": level, "sample": sample,
                    "first_month": usable.index.min().strftime("%Y-%m"),
                    "last_month": usable.index.max().strftime("%Y-%m"),
                    "months_open": int((usable[level] > 0).sum()),
                    "open_above": int(table.get("share above median", pd.Series()).get("arb east open", 0)),
                    "closed_below": int(table.get("share at or below median", pd.Series()).get("arb east closed", 0)),
                    "median_share": table.attrs["median"],
                })
                out.append(result)
    return pd.DataFrame(out)


# --------------------------------------------------------------------------
# 2020: the lift margin, at loading and at the notice date
# --------------------------------------------------------------------------

def notice_day(month: pd.Timestamp) -> date:
    """The cancellation notice day of a cargo loading in the month: the parameter table's day of month M-2."""
    before = month - pd.DateOffset(months=2)
    return date(before.year, before.month, int(_p("cancellation_notice_day")))


def published_jkm_proxy(day: date) -> tuple[pd.Timestamp, float, str] | None:
    """METI's latest contract-based figure published by the day: its month, the figure and a label.

    From the monthly releases saved by hand (meti_spot_lng_releases): the latest
    release on or before the day, and in it the latest month with a figure, the
    preliminary one first. None when no release before the day is held.
    """
    releases = base.read_cache("meti_spot_lng_releases")
    if releases is None:
        return None
    releases["release_date"] = pd.to_datetime(releases["release_date"])
    out = releases[releases["release_date"] <= pd.Timestamp(day)]
    if out.empty:
        return None
    released = out["release_date"].max()
    latest = out[out["release_date"] == released].dropna(subset=["contract_based_usd_mmbtu"])
    if latest.empty:
        return None
    row = latest.sort_values("date").iloc[-1]
    return row["date"], float(row["contract_based_usd_mmbtu"]), (
        "METI spot LNG, contract-based, %s figure for %s, released on %s, the latest published by %s" % (
            row["figure"].lower(), row["date"].strftime("%B %Y"), released.date(), day))


def _notice_prices(month: pd.Timestamp) -> tuple[float, float, float, dict[str, str]] | None:
    """The prices published by the cancellation notice day of a cargo loading in month M.

    The JKM proxy is METI's figure as its latest release before the 20th of M-2
    printed it (published_jkm_proxy): usually the preliminary figure for M-3,
    released around the 12th of M-2, which can differ from the figure METI
    finalised later (for July 2020, 5.2 against 4.2). Where no release before
    the notice day is held, the figure finalised later for M-3, labelled so.
    The World Bank's TTF is for the same month, published early in the next,
    and Henry Hub's daily spot is held to the notice day.
    """
    notice = notice_day(month)
    published = published_jkm_proxy(notice)
    if published is not None:
        priced, jkm, jkm_label = published
    else:
        priced = month - pd.DateOffset(months=3)
        meti = base.read_cache("meti_spot_lng_monthly").set_index("date")["contract_based_usd_mmbtu"]
        jkm = meti.get(priced)
        jkm_label = ("METI spot LNG, contract-based, %s, at the figure finalised later: no release before %s "
                     "is held" % (priced.strftime("%B %Y"), notice))
    wb = base.read_cache("worldbank_gas_monthly").set_index("date")["europe_gas_usd_mmbtu"]
    ttf = wb.get(priced)
    if jkm is None or ttf is None or pd.isna(jkm) or pd.isna(ttf):
        return None
    hh = base.read_cache("eia_henry_hub_daily")
    days = hh[(hh["date"] >= pd.Timestamp(notice.year, notice.month, 1)) & (hh["date"] <= pd.Timestamp(notice))]
    days = days["henry_hub_usd_mmbtu"].dropna()
    if days.empty:
        return None
    return float(jkm), float(ttf), float(days.mean()), {
        "jkm": jkm_label,
        "ttf": "World Bank Pink Sheet, Europe gas (TTF), %s, published by %s" % (priced.strftime("%B %Y"), notice),
        "henry_hub": "EIA Henry Hub spot, average of the %d days of %s to %s, in place of the futures for "
                     "the loading month" % (len(days), notice.strftime("%B %Y"), notice),
    }


def lift_margins_2020(year: int = 2020, *, levels: Mapping[str, float] | None = None) -> pd.DataFrame:
    """The lift margin of each loading month of the year, at loading and at the notice date.

    At loading: the month's own prices, as every monthly observation. At the
    notice date, the parameter table's day two months before: the prices
    published by then (_notice_prices), METI's contract-based figure as its
    latest release had printed it and the World Bank's TTF of the same month,
    and Henry Hub's spot averaged over month M-2 to the notice day, in place of
    the futures for month M, which this study does not hold. On the notice day the JKM front month names M itself, since
    JKM futures for M stop trading in M-1; METI's price stands in for it. The
    ship, routes, euro rate and overnight rate are those of the loading day.
    """
    levels = dict(hire_levels() if levels is None else levels)
    loading_day = int(_p("analysis_monthly_loading_day"))
    rows = []
    with reading_once():
        for m in range(1, 13):
            month = pd.Timestamp(year, m, 1)
            day = month.replace(day=loading_day).date()
            meti = base.read_cache("meti_spot_lng_monthly").set_index("date")["contract_based_usd_mmbtu"]
            wb = base.read_cache("worldbank_gas_monthly").set_index("date")["europe_gas_usd_mmbtu"]
            cases_ = {}
            if month in meti.index and month in wb.index and not pd.isna(meti[month]) and not pd.isna(wb[month]):
                inputs = worked.inputs_on(day, float(meti[month]), float(wb[month]),
                                          {"jkm": "METI contract-based, %s" % month.strftime("%B %Y"),
                                           "ttf": "World Bank TTF, %s" % month.strftime("%B %Y")},
                                          hire_usd_day=levels["central"],
                                          delta_window=window(pd.Timestamp(day), "monthly"))
                cases_["at loading"] = inputs
            notice = _notice_prices(month)
            if notice is None:
                rows.append({"month": month, "prices": "at the notice date", "priced_on": notice_day(month),
                             "note": "no price published by the notice day in the data held: METI's "
                                     "contract-based figure or the World Bank's TTF is missing"})
            else:
                jkm, ttf, hh, sources = notice
                inputs = worked.inputs_on(day, jkm, ttf, sources, hire_usd_day=levels["central"])
                cases_["at the notice date"] = replace(
                    inputs, henry_hub=hh, sources={**inputs.sources, "henry_hub": sources["henry_hub"]})
            for when, inputs in cases_.items():
                for level, hire in levels.items():
                    out = evaluate(replace(inputs, hire_usd_day=hire))
                    rows.append({
                        "month": month, "prices": when,
                        "priced_on": notice_day(month) if when == "at the notice date" else day,
                        "hire_level": level, "hire_usd_day": hire,
                        "jkm": inputs.jkm, "ttf": inputs.ttf, "henry_hub": inputs.henry_hub,
                        "jkm_source": inputs.sources.get("jkm"),
                        "best_destination": out["best_destination"],
                        "best_route": ROUTES.get(out["best_route"], out["best_route"]),
                        "best_netback": out["best_netback"], "lift_margin": out["lift_margin"],
                        "cancel": out["cancel"],
                        "note": None,
                    })
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# Route choice
# --------------------------------------------------------------------------

def panama_wait_breakeven(inputs: Inputs, *, limit_days: float = 120.0) -> float:
    """The waiting days per Panama transit, laden and ballast alike, at which Panama nets what the Cape does.

    Found by bisection on the engine itself; NaN when either route is closed,
    when Panama already nets less with no wait, or when no wait up to the limit
    closes the gap.
    """
    panama, cape = "nea_panama", "nea_cape"
    if not (inputs.routes[panama].open and inputs.routes[cape].open):
        return math.nan

    def gap(wait: float) -> float:
        routes = dict(inputs.routes)
        routes[panama] = replace(routes[panama], wait_days=routes[panama].wait_days + wait)
        out = evaluate(replace(inputs, routes=routes))
        return out["east"][panama]["netback"] - out["east"][cape]["netback"]

    lo, hi = 0.0, limit_days
    if gap(lo) <= 0 or gap(hi) > 0:
        return math.nan
    for _ in range(100):
        mid = (lo + hi) / 2
        if gap(mid) > 0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def route_choice(rows: pd.DataFrame, *, level: str = "central") -> pd.DataFrame:
    """Month by month: the route east the model picks, and what it would take for the Cape to win.

    For each monthly observation at one hire level: the best open route east;
    Panama's lead over the Cape in USD/MMBtu and as a slot premium in USD for
    the round trip, the premium at which the two net the same; and the waiting
    days per Panama transit, laden and ballast alike, at which they net the same.
    """
    monthly = rows[(rows["frequency"] == "monthly") & (rows["hire_level"] == level)]
    out = []
    with reading_once():
        for r in monthly.itertuples(index=False):
            day = r.day.date()
            inputs = worked.inputs_on(day, r.jkm, r.ttf, {"jkm": r.jkm_source, "ttf": r.ttf_source},
                                      hire_usd_day=r.hire_usd_day, delta_window=window(r.day, "monthly"))
            row = {"month": r.day.to_period("M").to_timestamp(), "best_route_east": r.best_route_east,
                   "panama_open": r.panama_open, "cape_open": r.cape_open}
            if r.panama_open and r.cape_open:
                lead = r.panama_netback - r.cape_netback
                q_load = cases._voyage(inputs, inputs.routes["nea_panama"]).q_load
                row.update({
                    "panama_lead_usd_mmbtu": lead,
                    "slot_premium_breakeven_usd_round_trip": lead * q_load,
                    "wait_days_breakeven": panama_wait_breakeven(inputs),
                })
            out.append(row)
    return pd.DataFrame(out)


def reported_waits(rows: pd.DataFrame) -> pd.DataFrame:
    """Panama against the Cape with the waiting days reported, in the months they were reported.

    The parameter table holds each reported wait by month; it is added to both
    Panama transits of that month's observation, at each hire level the month
    was worked at.
    """
    waits = _p("panama_waits_reported")
    out = []
    with reading_once():
        for month, days in sorted(waits.items()):
            day = pd.Timestamp(month + "-%02d" % int(_p("analysis_monthly_loading_day")))
            chosen = rows[(rows["frequency"] == "monthly") & (rows["day"] == day)]
            for r in chosen.itertuples(index=False):
                inputs = worked.inputs_on(day.date(), r.jkm, r.ttf, {"jkm": r.jkm_source, "ttf": r.ttf_source},
                                          hire_usd_day=r.hire_usd_day, delta_window=window(day, "monthly"))
                routes = dict(inputs.routes)
                routes["nea_panama"] = replace(routes["nea_panama"], wait_days=float(days))
                waited = evaluate(replace(inputs, routes=routes))
                out.append({
                    "month": day.to_period("M").to_timestamp(), "hire_level": r.hire_level,
                    "hire_usd_day": r.hire_usd_day, "wait_days_reported": float(days),
                    "wait_days_breakeven": panama_wait_breakeven(inputs),
                    "panama_minus_cape_no_wait": r.panama_netback - r.cape_netback,
                    "panama_minus_cape_with_wait": (waited["east"]["nea_panama"]["netback"]
                                                    - waited["east"]["nea_cape"]["netback"]),
                })
    return pd.DataFrame(out)


# --------------------------------------------------------------------------
# How much the verdict rests on Europe's regasification discount
# --------------------------------------------------------------------------

def _cheapest_open(out: Mapping[str, Any]) -> tuple[str | None, float]:
    """The open route east with the lowest S*, and that S*; (None, nan) when none is open."""
    best, s_star = None, math.nan
    for route, lines in out["east"].items():
        if lines["open"] and not math.isnan(lines["s_star"]) and (best is None or lines["s_star"] < s_star):
            best, s_star = route, lines["s_star"]
    return best, s_star


def regas_sensitivity(obs: pd.DataFrame | None = None, *, hire: float | None = None) -> pd.DataFrame:
    """Every weekly observation at the central hire, with Europe's DES spread to TTF
    as the data give it, at zero and at the parameter table's assumption.

    For each: the spread, the S* of the cheapest open route east and whether
    the spread lay above it (the arb east open). ACER's spread enters S* and
    nothing else, so the three cases differ only through it. The assumption is
    converted at the week's own exchange rate.
    """
    hire = hire_levels()["central"] if hire is None else hire
    assumed_eur = float(_p("delta_nwe_eur_mwh"))
    rows = []
    with reading_once():
        obs = observations() if obs is None else obs
        for o in obs[obs["frequency"] == "weekly"].itertuples(index=False):
            day = o.day.date()
            try:
                inputs = worked.inputs_on(day, o.jkm, o.ttf, {"jkm": o.jkm_source, "ttf": o.ttf_source},
                                          hire_usd_day=hire, delta_window=window(o.day, "weekly"))
                usd_per_eur = worked.usd_per_eur_on(day)[0]
            except worked.MissingInput:
                continue
            row = {"day": o.day, "spread": inputs.jkm - inputs.ttf, "delta_nwe": inputs.delta_nwe,
                   "assumed_delta_nwe": units.eur_mwh_to_usd_mmbtu(assumed_eur, usd_per_eur),
                   "delta_observed": not inputs.sources["delta_nwe"].startswith("assumption")}
            cases_ = {"data": inputs.delta_nwe, "zero": 0.0,
                      "assumed": units.eur_mwh_to_usd_mmbtu(assumed_eur, usd_per_eur)}
            for name, delta in cases_.items():
                out = evaluate(replace(inputs, delta_nwe=delta))
                route, s_star = _cheapest_open(out)
                row[name + "_s_star"] = s_star
                row[name + "_route"] = ROUTES.get(route) if route else None
                row[name + "_open"] = (not math.isnan(s_star)) and out["spread"] > s_star
            rows.append(row)
    return pd.DataFrame(rows)

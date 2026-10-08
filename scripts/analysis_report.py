"""Print the study's analysis: the breakeven through time, the flows, 2020, the route, 2026, the parts of S*.

Reads only the committed data and the parameter table, through lngarb.analysis;
fetches nothing. With --out PATH it also writes the text there.

    PYTHONPATH=src python scripts/analysis_report.py [--out PATH]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lngarb import analysis, cases, worked  # noqa: E402
from lngarb.freight_anchors import ANCHORS  # noqa: E402
from lngarb.reported import reported  # noqa: E402

LINES: list[str] = []


def say(text: str = "") -> None:
    LINES.append(text)


def table(frame: pd.DataFrame, floatfmt: str = "{:,.2f}") -> None:
    if frame.empty:
        say("(none)")
        return
    columns = list(frame.columns)
    say("| " + " | ".join(str(c) for c in columns) + " |")
    say("|" + "---|" * len(columns))
    for row in frame.itertuples(index=False):
        cells = []
        for value in row:
            if isinstance(value, float):
                cells.append("" if pd.isna(value) else floatfmt.format(value))
            elif isinstance(value, pd.Timestamp):
                cells.append(value.strftime("%Y-%m-%d"))
            else:
                cells.append(str(value))
        say("| " + " | ".join(cells) + " |")
    say()


def section_observations(obs: pd.DataFrame, rows: pd.DataFrame, missing: pd.DataFrame) -> None:
    say("## The observations")
    say()
    counts = obs.groupby(["frequency", "series"]).agg(first=("day", "min"), last=("day", "max"), n=("day", "size")).reset_index()
    table(counts)
    weekly = obs[obs["frequency"] == "weekly"]
    say("Weekly alignment of the two front months: %s." % ", ".join(
        "%s %d" % (tag, n) for tag, n in weekly["alignment"].value_counts().items()))
    say()
    say("Observations the data cannot price: %d." % len(missing))
    if len(missing):
        table(missing)
    say("Months from the first of the monthly history with no monthly observation:")
    say()
    table(analysis.months_without_observation(obs))


def _open_only(frame: pd.DataFrame) -> pd.DataFrame:
    """The per-route columns of a closed route emptied, so that no aggregate counts them."""
    out = frame.copy()
    for route in analysis.ROUTES.values():
        closed = out[route + "_open"] != True  # noqa: E712
        for column in [c for c in out.columns if c.startswith(route + "_") and c != route + "_open"]:
            out.loc[closed, column] = float("nan")
    return out


def section_breakeven(rows: pd.DataFrame, breaks: pd.DataFrame) -> None:
    say("## The breakeven through time")
    say()
    rows = _open_only(rows)
    weekly = rows[(rows["frequency"] == "weekly") & rows["hire_level"].isin(["low", "central", "high"])].copy()
    weekly["year"] = weekly["day"].dt.year
    weekly["open"] = weekly["arb"] > 0
    weekly["cape_open_arb"] = weekly["cape_arb"] > 0
    summary = weekly.groupby(["year", "hire_level"]).agg(
        weeks=("day", "size"), spread=("spread", "mean"), s_star_panama=("panama_s_star", "mean"),
        s_star_cape=("cape_s_star", "mean"), weeks_open_best=("open", "sum"),
        weeks_open_cape=("cape_open_arb", "sum"),
        h_star_panama_median=("panama_h_star", "median"), h_star_cape_median=("cape_h_star", "median"),
    ).reset_index()
    order = {"low": 0, "central": 1, "high": 2}
    summary = summary.sort_values(["year", "hire_level"], key=lambda s: s.map(order) if s.name == "hire_level" else s)
    say("Weekly, by year and hire level: mean spread and mean S* by route (USD/MMBtu), weeks in which the best open route east nets more than Northwest Europe and weeks in which the Cape does, median H* by route (USD/day).")
    say()
    table(summary)
    central = weekly[(weekly["hire_level"] == "central")]
    rows_ = []
    for label, subset in (("aligned weeks only", central[central["alignment"] == "aligned"]),
                          ("aligned and mixed", central[central["alignment"].isin(["aligned", "mixed"])]),
                          ("every week", central)):
        rows_.append({"weeks": label, "n": len(subset), "spread": subset["spread"].mean(),
                      "s_star_best": subset["s_star_best"].mean(), "weeks_open_best": int(subset["open"].sum()),
                      "share_open": subset["open"].mean(),
                      "corr_spread_s_star": subset["spread"].corr(subset["s_star_best"])})
    say("At the central hire, aligned weeks first, then the others added:")
    say()
    table(pd.DataFrame(rows_), "{:,.3f}")
    monthly = rows[(rows["frequency"] == "monthly") & (rows["hire_level"] == "central")].copy()
    monthly["year"] = monthly["day"].dt.year
    say("(Per-route figures of a closed route are left out of every mean.)")
    say()
    monthly["open"] = monthly["arb"] > 0
    say("Monthly, central hire, by year:")
    say()
    table(monthly.groupby("year").agg(months=("day", "size"), spread=("spread", "mean"),
                                      s_star_best=("s_star_best", "mean"), months_open=("open", "sum"),
                                      h_star_panama=("panama_h_star", "mean")).reset_index())
    say("Structural breaks:")
    say()
    table(breaks)


def section_flows(rows: pd.DataFrame) -> None:
    say("## Did the cargoes follow")
    say()
    shares = analysis.export_shares()
    arb = analysis.monthly_arb(rows)
    joined = shares.set_index("month").join(arb, how="left")
    say("Monthly share of US LNG exports by vessel to the JKM markets and to Asia, and the arb east at loading (USD/MMBtu):")
    say()
    show = joined.reset_index()[["month", "total_mmcf", "share_jkm", "share_asia", "low", "central", "high"]]
    table(show, "{:,.3f}")
    result = analysis.flows_test(rows, shares)
    say("Regressions of each share on the arb, Newey-West standard errors:")
    say()
    table(result[["share", "sample", "hire_level", "n", "first_month", "last_month", "slope", "se_slope",
                  "t_slope", "r2", "lags", "months_open", "open_above", "closed_below", "median_share"]], "{:,.4f}")


def section_2020(rows: pd.DataFrame) -> None:
    say("## 2020: when the export arb closed")
    say()
    say("Cancellations reported:")
    say()
    table(pd.DataFrame([{"month": r.period, "cargoes": r.figure, "what": r.what, "source": r.publisher}
                        for r in reported("cancellations")]), "{:,.0f}")
    shares = analysis.export_shares().set_index("month")
    exports = shares.loc["2019-10-01":"2020-12-01", ["total_mmcf", "share_jkm", "share_asia"]].reset_index()
    say("US LNG exports by vessel, October 2019 to December 2020 (MMcf, and shares):")
    say()
    table(exports, "{:,.3f}")
    say("Lift margin, USD/MMBtu: at loading, with the month's own prices; at the notice date, with the prices published by the 20th of month M-2:")
    say()
    margins = analysis.lift_margins_2020()
    pivot = margins.pivot_table(index="month", columns=["prices", "hire_level"], values="lift_margin")
    pivot.columns = ["%s, %s" % c for c in pivot.columns]
    table(pivot.reset_index(), "{:,.3f}")
    say("Prices, best destination and route at the central hire, at loading and at the notice date:")
    say()
    central = margins[(margins["hire_level"] == "central")]
    table(central[["month", "prices", "priced_on", "jkm", "ttf", "henry_hub", "best_destination", "best_route",
                   "best_netback", "lift_margin"]], "{:,.3f}")
    unpriced = margins[margins["note"].notna()]
    if len(unpriced):
        say("Not priced at the notice date:")
        say()
        table(unpriced[["month", "priced_on", "note"]])


def section_routes(rows: pd.DataFrame) -> None:
    say("## Route choice")
    say()
    say("Route use reported:")
    say()
    table(pd.DataFrame([{"period": r.period, "topic": r.topic, "cargoes": r.figure, "what": r.what,
                         "source": r.publisher} for r in reported("cape_use") + reported("panama_use")]), "{:,.0f}")
    say("Panama against the Cape with the waits reported, in the months they were reported (USD/MMBtu):")
    say()
    table(analysis.reported_waits(rows), "{:,.3f}")
    for level in ("high", "reported"):
        extra = analysis.route_choice(rows, level=level)
        if extra.empty:
            continue
        say("At the %s hire, the waiting days per transit at which the Cape nets as much as Panama:" % level)
        say()
        table(extra[["month", "best_route_east", "panama_lead_usd_mmbtu", "slot_premium_breakeven_usd_round_trip",
                     "wait_days_breakeven"]], "{:,.3f}")
    choice = analysis.route_choice(rows)
    say("Best route east by year, monthly observations at the central hire:")
    say()
    choice["year"] = choice["month"].dt.year
    table(choice.groupby(["year", "best_route_east"]).size().rename("months").reset_index())
    say("Panama against the Cape, month by month (lead in USD/MMBtu, the slot premium for the round trip and the waiting days per transit at which the Cape nets as much):")
    say()
    table(choice.drop(columns=["year"]), "{:,.3f}")


def section_2026(rows: pd.DataFrame) -> None:
    say("## 2026")
    say()
    weekly = rows[(rows["frequency"] == "weekly") & (rows["day"] >= "2025-12-01")]
    pivot = weekly.pivot_table(index="day", columns="hire_level", values="arb")
    base_ = weekly[weekly["hire_level"] == "central"].set_index("day")[
        ["jkm", "ttf", "spread", "panama_s_star", "cape_s_star", "panama_h_star", "cape_h_star", "best_route_east", "alignment"]]
    table(base_.join(pivot).reset_index(), "{:,.2f}")


def section_parts(rows: pd.DataFrame) -> None:
    say("## What the long way costs: the parts of S*")
    say()
    weekly = rows[rows["frequency"] == "weekly"]
    reported = weekly[weekly["hire_level"] == "reported"]
    say("Every week with a reported hire near it, best route east:")
    say()
    show = []
    for r in reported.itertuples(index=False):
        route = r.best_route_east or "panama"
        show.append({"day": r.day, "hire": r.hire_usd_day, "route": route, "spread": r.spread,
                     "s_star": getattr(r, route + "_s_star"), "boil_off": getattr(r, route + "_boil_off"),
                     "regas": getattr(r, route + "_regas"), "voyage": getattr(r, route + "_voyage")})
    table(pd.DataFrame(show))
    for level in ("low", "central", "high"):
        at = weekly[weekly["hire_level"] == level].copy()
        at["route"] = at["best_route_east"].fillna("panama")
        at["dominant"] = ["boil_off" if getattr(r, r.route + "_boil_off") > getattr(r, r.route + "_voyage") else "voyage"
                          for r in at.itertuples(index=False)]
        at["regas"] = [getattr(r, r.route + "_regas") for r in at.itertuples(index=False)]
        at["year"] = at["day"].dt.year
        say("The larger of the two costs of the long way, boil-off or voyage, by year, %s hire (weeks), and the mean regas part:" % level)
        say()
        counts = at.groupby(["year", "dominant"]).size().unstack(fill_value=0).reset_index()
        counts = counts.merge(at.groupby("year")["regas"].mean().rename("regas_mean").reset_index(), on="year")
        table(counts, "{:,.3f}")


def section_checks(rows: pd.DataFrame) -> None:
    say("## Against an assessment published")
    say()
    say("Platts' arbitrage of US to North Asia against US to the Atlantic on 28 April 2026:")
    say()
    table(pd.DataFrame([{"route": r.what, "usd_mmbtu": r.figure, "source": r.publisher}
                        for r in reported("arb_assessment")]), "{:,.3f}")
    week = rows[(rows["frequency"] == "weekly") & (rows["day"] == pd.Timestamp("2026-04-29"))]
    r = week.iloc[0]
    day = r["day"].date()
    nearest = min(ANCHORS, key=lambda a: abs((worked._anchor_day(a) - day).days))
    gap = abs((worked._anchor_day(nearest) - day).days)
    say("This study, the week ending 29 April 2026, at each hire level; the nearest reported charter rate is "
        "%s USD/day of %s, %d days away:" % (format(nearest.hire_usd_day, ",.0f"), worked._anchor_day(nearest), gap))
    say()
    table(week[["hire_level", "hire_usd_day", "panama_arb", "cape_arb", "panama_h_star", "cape_h_star"]])
    inputs = worked.inputs_on(day, r["jkm"], r["ttf"], {"jkm": r["jkm_source"], "ttf": r["ttf_source"]},
                              hire_usd_day=nearest.hire_usd_day)
    out = cases.evaluate(inputs)
    say("At that nearest reported charter rate:")
    say()
    table(pd.DataFrame([{"hire_usd_day": nearest.hire_usd_day, "panama_arb": out["east"]["nea_panama"]["arb"],
                         "cape_arb": out["east"]["nea_cape"]["arb"]}]))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    obs = analysis.observations()
    rows, missing = analysis.work(obs)
    say("# The analysis, from the committed data")
    say()
    section_observations(obs, rows, missing)
    section_breakeven(rows, analysis.breaks(obs))
    section_flows(rows)
    section_2020(rows)
    section_routes(rows)
    section_2026(rows)
    section_parts(rows)
    section_checks(rows)
    text = "\n".join(LINES) + "\n"
    sys.stdout.write(text)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

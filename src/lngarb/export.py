"""Write the site's data: the six JSON files in data/, five the page reads now and history.json for the History view.

The site draws nothing it does not read from these files (and from
data/manifest.json, which the Provenance section links): every number in the
browser comes from here, every label beside it names its source. The page
never reads the routes seed or the land outlines; routes.json carries the
map drawn from them. Each file carries schema_version and the day of the data
it holds, never the time it was written, so that writing it twice gives the
same bytes.

    now.json      the latest weekly observation: each input with its source and
                  date, the engine's full inputs (so the browser can move the
                  hire or the routes and recompute with src/engine.js) and the
                  engine's full output, at the reported hire nearest the day
                  or, where none is reported, the central level, with the three
                  levels beside it.
    history.json  every weekly and monthly observation at each hire level: the
                  spread, S* and its parts and H* per route, the best route
                  east and its arb; the breaks; the freight anchors.
    flows.json    the monthly export shares against the arb at loading, the
                  regressions and sign tables, the months with no observation.
    model.json    the calculator's presets, each a whole set of engine inputs
                  with the source of each, the tolls for either ship, the
                  engine's output and the landing sentence; the named edits
                  worked in Python (lngarb.presets).
    routes.json   the map, the table of the four routes and when each was open
                  to a US cargo, band by band with its source (lngarb.routemap).
    provenance.json  every series: its publisher, page, licence and state.

    PYTHONPATH=src python -m lngarb.export
"""

from __future__ import annotations

import json
import math
import sys
from dataclasses import asdict, replace
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

from . import analysis, config, delivery, presets, reader, routemap, spreadhistory, units, worked
from .cases import WATERFALL_STEPS, evaluate
from .freight_anchors import ANCHORS, hire_levels
from .sources import base

__all__ = ["SCHEMA_VERSION", "now", "model", "routes", "history", "flows", "provenance", "write_all", "inputs_json", "CREDITS"]

#: Who each source is credited to on the page, in the words their terms ask
#: for where they ask for any (NOTICE holds the same notices).
CREDITS = (
    "Weekly JKM and TTF prices, the Henry Hub spot price and US LNG exports: U.S. Energy Information "
    "Administration, which credits the weekly prices to Bloomberg Finance L.P. and the Henry Hub spot price to "
    "Refinitiv, an LSEG business.",
    "The regasification discount: European Union Agency for the Cooperation of Energy Regulators (ACER).",
    "The Japanese spot price before the weekly series: created by processing the information in the Spot LNG Price "
    "Statistics (Ministry of Economy, Trade and Industry of Japan).",
    "TTF before the weekly series: The World Bank, Commodity Price Data (The Pink Sheet), under the Creative Commons "
    "Attribution 4.0 licence. The World Bank does not endorse this study.",
    "EU allowances: European Commission auction reports, under the Creative Commons Attribution 4.0 licence; after "
    "the last month they cover, Source: EEX, DEHSt, under the Creative Commons Attribution NonCommercial "
    "NoDerivatives 4.0 licence, the monthly averages reproduced unchanged.",
    "The Secured Overnight Financing Rate (SOFR) and the Effective Federal Funds Rate (EFFR) are subject to the "
    "Terms of Use posted at newyorkfed.org. The New York Fed is not responsible for publication of the SOFR or the "
    "EFFR by Nathan Couturier, does not sanction or endorse any particular republication, and has no liability for "
    "your use.",
    "Dollars per euro: Board of Governors of the Federal Reserve System, H.10. Dollars per SDR: International "
    "Monetary Fund, read through the Deutsche Bundesbank.",
    "Charter rates: as reported by the publishers each figure names, listed with the history.",
    "Sea distances: this study's computation from the searoute library (Apache License 2.0) over Eurostat's "
    "Searoute network (European Union Public Licence 1.2).",
    "Land outlines: Natural Earth, public domain, through the world-atlas package (ISC licence).",
    "Typefaces: Fraunces, Figtree and JetBrains Mono, under the SIL Open Font License 1.1. Figtree stands in for "
    "the portfolio's Satoshi, whose licence does not allow a copy in a public repository.",
)

SCHEMA_VERSION = 1

#: history.json and flows.json store every float to this many places: far below
#: any decimals the page prints, and the files stay a fifth of their size.
#: now.json keeps full precision, because the browser engine recomputes from
#: its inputs.
ROUND_DP = 6


def _clean(value: Any, places: int | None = None) -> Any:
    """JSON has no NaN: a missing figure is null, never zero; dates are ISO days.

    A missing date is null too. pd.NaT is an instance of datetime.date, so it is
    tested before the date branch, which would otherwise write it as "NaT".
    """
    if value is None or value is pd.NaT:
        return None
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        if places is None:
            return value
        out = round(value, places)
        return 0.0 if out == 0.0 else out  # no negative zero in a file
    if isinstance(value, (pd.Timestamp, date)):
        return value.isoformat()[:10]
    if isinstance(value, dict):
        return {str(k): _clean(v, places) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean(v, places) for v in value]
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(value, "item"):
        return _clean(value.item(), places)
    return value


def inputs_json(inputs) -> dict[str, Any]:
    """The engine's inputs as src/engine.js reads them (the same contract as data/fixtures/engine-cases.json)."""
    out = {
        "day": inputs.day.isoformat(),
        "vessel": asdict(inputs.vessel),
        "routes": {k: asdict(v) for k, v in inputs.routes.items()},
        "ets_by_year": None if inputs.ets_by_year is None else {
            str(year): [phase, factor] for year, (phase, factor) in inputs.ets_by_year.items()},
        "sources": dict(inputs.sources),
    }
    for name in ("mmbtu_per_m3", "jkm", "ttf", "delta_nwe", "hire_usd_day", "henry_hub", "hh_multiple",
                 "liquefaction_fee", "port_west_usd", "port_east_usd", "rate_percent", "spread_bp", "eua_usd_t",
                 "ets_phase", "tco2_per_t_lng", "mmbtu_per_t_lng", "ets_voyage_share", "ets_berth_share"):
        out[name] = getattr(inputs, name)
    return out


def now(obs: pd.DataFrame | None = None, *, flows_document: dict[str, Any] | None = None,
        provenance_document: dict[str, Any] | None = None) -> dict[str, Any]:
    """The latest weekly observation, worked at the reported hire nearest it, or the central level.

    Besides the engine's inputs and output, the reader's layer of the Now view:
    the verdict, one sentence per input with its date, and the content of the
    five sections, whose summaries for the flows and the provenance are those
    of flows.json and provenance.json.
    """
    with analysis.reading_once():
        obs = analysis.observations() if obs is None else obs
        if flows_document is None:
            flows_document = flows(analysis.work(obs)[0])
        if provenance_document is None:
            provenance_document = provenance()
        weekly = obs[obs["frequency"] == "weekly"].sort_values("day", ascending=False)
        levels = hire_levels()
        not_priced = []
        for latest in weekly.to_dict("records"):
            day = latest["day"].date()
            reported, reported_source = worked.nearest_hire(day)
            hire = reported if reported is not None else levels["central"]
            try:
                inputs = worked.inputs_on(
                    day, float(latest["jkm"]), float(latest["ttf"]),
                    {"jkm": latest["jkm_source"], "ttf": latest["ttf_source"]},
                    hire_usd_day=hire, delta_window=analysis.window(latest["day"], "weekly"),
                )
                break
            except worked.MissingInput as exc:
                # The latest week cannot always be priced yet: a month of Henry
                # Hub not begun in EIA's data. It is named, and the week before
                # is shown.
                not_priced.append({"week_ending": day, "reason": str(exc)})
        else:
            raise worked.MissingInput("no weekly observation can be priced")
        result = evaluate(inputs)
        usd_per_eur = worked.usd_per_eur_on(day)[0]
        eua_eur = None
        if inputs.eua_usd_t:
            eua_eur = inputs.eua_usd_t / usd_per_eur
        anchor, gap = worked.nearest_anchor(day)
        window = analysis.window(latest["day"], "weekly")

        def at_hire(value: float) -> dict[str, Any]:
            return evaluate(replace(inputs, hire_usd_day=value))

        hire_info = {"value": hire, "reported": reported is not None, "anchor": anchor,
                     "date": worked._anchor_day(anchor), "gap": gap,
                     "max_days": config.PARAMETERS["hire_anchor_max_days"].value}
        hh_multiple = inputs.hh_multiple
        threshold = hh_multiple * inputs.henry_hub
        netbacks = reader.netbacks_section(result, day=day, threshold=threshold, hh_multiple=hh_multiple)
        delta = worked.delta_nwe_detail(*window)
        cost = reader.cost_section(result, inputs, day=day, steps=WATERFALL_STEPS, delta_observed=delta is not None)
        breakeven = reader.breakeven_section(result, inputs, day=day, levels=levels, hire=hire_info,
                                             evaluate_at=at_hire)
        document = {
            **reader.header("now", day, "the landing sentence, the date of every input, the netbacks, the steps "
                                        "of the arb and the breakeven lines for the latest week, with the engine's "
                                        "inputs and output"),
            "conventions": reader.conventions(),
            "as_of": day,
            "verdict": reader.verdict(result, day, hh_multiple, delta_nwe=inputs.delta_nwe,
                                      liquefaction_fee=inputs.liquefaction_fee),
            "data_dates": reader.data_dates(
                day=day, week={"series": latest["series"], "alignment": latest["alignment"],
                               "aligned_share": latest["aligned_share"]},
                inputs=inputs, usd_per_eur=worked.usd_per_eur_detail(day), hh=worked.henry_hub_detail(day),
                hire=hire_info, delta=delta, delta_window=window, eua=worked.eua_detail(day),
                rate=worked.overnight_rate_detail(day),
                fronts={"jkm": delivery.jkm_front_month(day), "ttf": delivery.ttf_front_month(day)},
                eur_mwh=lambda usd: units.usd_mmbtu_to_eur_mwh(usd, usd_per_eur), not_priced=not_priced),
            "sections": reader.sections(result, netbacks=netbacks, cost=cost, breakeven=breakeven,
                                        flows_heading=flows_document["panel"]["heading_segments"],
                                        provenance_summary=provenance_document["summary_segments"]),
            "netbacks": netbacks,
            "cost": cost,
            "breakeven": breakeven,
            "not_priced": not_priced,
            "week": {"first": analysis.window(latest["day"], "weekly")[0], "last": day,
                     "alignment": latest["alignment"], "aligned_share": latest["aligned_share"],
                     "series": latest["series"], "basis": latest["basis"]},
            "inputs": {
                "jkm": {"value": inputs.jkm, "unit": "USD/MMBtu", "source": inputs.sources["jkm"], "date": day},
                "ttf": {"value": inputs.ttf, "unit": "USD/MMBtu", "source": inputs.sources["ttf"], "date": day,
                        "eur_mwh": units.usd_mmbtu_to_eur_mwh(inputs.ttf, usd_per_eur)},
                "henry_hub": {"value": inputs.henry_hub, "unit": "USD/MMBtu", "source": inputs.sources["henry_hub"],
                              "incomplete_month": "incomplete month" in inputs.sources["henry_hub"]},
                "hire": {"value": hire, "unit": "USD/day",
                         "source": reported_source if reported is not None else
                         "central level of the freight anchors; %s" % reported_source,
                         "reported": reported is not None,
                         "nearest_reported": {"value": anchor.hire_usd_day,
                                              "date": worked._anchor_day(anchor), "publisher": anchor.publisher},
                         "levels": levels},
                "regas_discount": {"value": inputs.delta_nwe, "unit": "USD/MMBtu",
                                   "eur_mwh": units.usd_mmbtu_to_eur_mwh(inputs.delta_nwe, usd_per_eur),
                                   "source": inputs.sources["delta_nwe"],
                                   "observed": not inputs.sources["delta_nwe"].startswith("assumption")},
                "usd_per_eur": {"value": usd_per_eur, "source": inputs.sources["fx"]},
                "eua": {"value": eua_eur, "unit": "EUR/t", "source": inputs.sources["eua"],
                        "assumption": inputs.sources["eua"].startswith("assumption")},
                "overnight_rate": {"value": inputs.rate_percent, "unit": "percent", "source": inputs.sources["rate"]},
                "vessel": {"value": inputs.vessel.name},
            },
            "engine_inputs": inputs_json(inputs),
            "result": result,
            "at_levels": {},
        }
        for name, value in levels.items():
            out = at_hire(value)
            document["at_levels"][name] = {
                "hire_usd_day": value, "best_route_east": out["best_route_east"],
                "best_destination": out["best_destination"], "best_netback": out["best_netback"],
                "lift_margin": out["lift_margin"],
                "arb": {r: lines["arb"] for r, lines in out["east"].items()},
                "s_star": {r: lines["s_star"] for r, lines in out["east"].items()},
            }
        return _clean(document)


HISTORY_COLUMNS = [
    "day", "frequency", "series", "basis", "alignment", "aligned_share", "hire_level", "hire_usd_day",
    "jkm", "ttf", "spread", "delta_nwe", "henry_hub", "vessel", "west_netback", "best_route_east", "arb",
    "s_star_best", "lift_margin", "cancel",
]


def history(rows: pd.DataFrame | None = None, obs: pd.DataFrame | None = None) -> dict[str, Any]:
    """Every observation at each hire level, the breaks and the freight anchors."""
    obs = analysis.observations() if obs is None else obs
    if rows is None:
        rows, _ = analysis.work(obs)
    columns = HISTORY_COLUMNS + [c for r in analysis.ROUTES.values() for c in (
        r + "_open", r + "_s_star", r + "_boil_off", r + "_regas", r + "_voyage", r + "_h_star", r + "_arb")]
    frame = rows.sort_values(["frequency", "day", "hire_level"])[columns]
    records = [list(r) for r in frame.itertuples(index=False, name=None)]
    anchors = [{"date": worked._anchor_day(a), "hire_usd_day": a.hire_usd_day, "assessment": a.assessment,
                "vessel": a.vessel, "publisher": a.publisher, "url": a.url} for a in ANCHORS]
    breaks = analysis.breaks(obs)
    without = analysis.months_without_observation(obs)
    return _clean({
        **reader.header("history", frame["day"].max(), "every weekly and monthly observation at each hire level, "
                                                         "the breaks and the freight anchors"),
        "conventions": reader.conventions(),
        "first": frame["day"].min(), "last": frame["day"].max(),
        "hire_levels": hire_levels(),
        "columns": list(frame.columns),
        "rows": records,
        "breaks": breaks.to_dict("records"),
        "months_without_observation": without.to_dict("records"),
        "freight_anchors": anchors,
        # The History view's layer: what the page draws and says, computed here.
        "page": spreadhistory.page(rows, breaks, anchors, without, hire_levels()),
    }, ROUND_DP)


def flows(rows: pd.DataFrame | None = None) -> dict[str, Any]:
    """The monthly export shares against the arb at loading, and the tests of 12.2."""
    if rows is None:
        rows, _ = analysis.work()
    shares = analysis.export_shares().set_index("month")
    arb = analysis.monthly_arb(rows)
    joined = shares.join(arb, how="left").reset_index()
    months = [{
        "month": r["month"], "total_mmcf": r["total_mmcf"], "jkm_markets_mmcf": r["jkm_markets_mmcf"],
        "asia_mmcf": r["asia_mmcf"], "share_jkm": r["share_jkm"], "share_asia": r["share_asia"],
        "anomaly": r["anomaly"], "arb": {"low": r["low"], "central": r["central"], "high": r["high"]},
    } for r in joined.to_dict("records")]
    tests = analysis.flows_test(rows).to_dict("records")
    excluded = list(config.PARAMETERS["analysis_excluded_years"].value)
    clean_months = _clean(months, ROUND_DP)
    return _clean({
        **reader.header("flows", joined["month"].max(), "the monthly share of US exports to Asia against the arb "
                                                         "at loading, and the regressions"),
        "conventions": reader.conventions(),
        "first": joined["month"].min(), "last": joined["month"].max(),
        "panel": reader.flows_panel(clean_months, _clean(tests), excluded, hire_levels()["central"]),
        "months": months,
        "regressions": tests,
        "excluded_years": excluded,
    }, ROUND_DP)


def provenance(manifest: dict[str, Any] | None = None) -> dict[str, Any]:
    """The reader's layer over data/manifest.json: every series in words, the
    work done by hand, the credits."""
    if manifest is None:
        manifest = json.loads((base.DATA / "manifest.json").read_text(encoding="utf-8"))
    last = max(e["last_date"] for e in manifest["series"] if e.get("last_date"))
    return _clean({
        **reader.header("provenance", last, "the manifest of every series in words, the work done by hand and "
                                            "the credits"),
        "conventions": reader.conventions(),
        **reader.provenance(manifest, config.SOURCES, CREDITS),
    })


NEWLINE = chr(10)


def _text(document: dict[str, Any]) -> str:
    """The file's text. A table held as "columns" and "rows" is written one row
    per line, so the file stays small and a diff shows which rows moved."""
    def dump(value: Any, **options: Any) -> str:
        return json.dumps(value, ensure_ascii=True, allow_nan=False, **options)

    if not isinstance(document.get("rows"), list) or "columns" not in document:
        return dump(document, indent=1) + NEWLINE
    head = dump({k: v for k, v in document.items() if k != "rows"}, indent=1)
    rows = ("," + NEWLINE).join(" " + dump(row, separators=(",", ":")) for row in document["rows"])
    body = head[: -len(NEWLINE + "}")] + "," + NEWLINE + ' "rows": [' + NEWLINE + rows + NEWLINE + " ]" + NEWLINE + "}"
    return body + NEWLINE


def _write(name: str, document: dict[str, Any]) -> Path:
    path = base.DATA / name
    path.write_bytes(_text(document).encode("utf-8"))
    return path


def model(now_document: dict[str, Any]) -> dict[str, Any]:
    """The Model view's presets, the latest week being the Now view's."""
    day = date.fromisoformat(now_document["as_of"])
    body = presets.model_document(day, now_document["week"]["series"], inputs_json)
    count = len(body["presets"])
    return _clean({
        **reader.header("model", day, "the calculator's presets: every engine input of %s with its source, "
                                      "the engine's output and the landing sentence for each" % (
                                          "one date" if count == 1 else "%d dates" % count)),
        "conventions": reader.conventions(),
        **body,
    })


def routes(now_document: dict[str, Any]) -> dict[str, Any]:
    """The Routes view: the map, the table and the timeline for the latest week."""
    body = routemap.routes_document(now_document)
    return _clean({
        **reader.header("routes", body["as_of"], "the map of the four routes from Sabine Pass, their distances, days "
                                                 "and tolls, and when each was open to a US cargo"),
        "conventions": reader.conventions(),
        **body,
    })


def write_all() -> list[Path]:
    """Write the site's files from the committed data.

    Every document is built before any file is written, so a failure in one
    leaves all six as they were and the site's data always belong to one run.
    """
    with analysis.reading_once():
        obs = analysis.observations()
        rows, _ = analysis.work(obs)
        flows_document = flows(rows)
        provenance_document = provenance()
        now_document = now(obs, flows_document=flows_document, provenance_document=provenance_document)
        documents = {
            "now.json": now_document,
            "model.json": model(now_document),
            "routes.json": routes(now_document),
            "history.json": history(rows, obs),
            "flows.json": flows_document,
            "provenance.json": provenance_document,
        }
    return [_write(name, document) for name, document in documents.items()]


def main() -> int:
    for path in write_all():
        print("wrote %s, %d bytes" % (path.relative_to(base.REPO_ROOT).as_posix(), path.stat().st_size))
    return 0


if __name__ == "__main__":
    sys.exit(main())

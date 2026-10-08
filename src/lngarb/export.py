"""Write the site's data: data/now.json, data/history.json and data/flows.json.

The site draws nothing it does not read from these files (and from
data/manifest.json and the routes seed): every number in the browser comes
from here, every label beside it names its source. Each file carries
schema_version and the day of the data it holds, never the time it was
written, so that writing it twice gives the same bytes.

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

    PYTHONPATH=src python -m lngarb.export
"""

from __future__ import annotations

import json
import math
import sys
from dataclasses import asdict
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

from . import analysis, config, units, worked
from .cases import evaluate
from .freight_anchors import ANCHORS, hire_levels
from .sources import base

__all__ = ["SCHEMA_VERSION", "now", "history", "flows", "write_all", "inputs_json"]

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


def now(obs: pd.DataFrame | None = None) -> dict[str, Any]:
    """The latest weekly observation, worked at the reported hire nearest it, or the central level."""
    with analysis.reading_once():
        obs = analysis.observations() if obs is None else obs
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
        anchor = min(ANCHORS, key=lambda a: abs((worked._anchor_day(a) - day).days))
        document = {
            "schema_version": SCHEMA_VERSION,
            "as_of": day,
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
            from dataclasses import replace
            out = evaluate(replace(inputs, hire_usd_day=value))
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
    return _clean({
        "schema_version": SCHEMA_VERSION,
        "first": frame["day"].min(), "last": frame["day"].max(),
        "hire_levels": hire_levels(),
        "columns": list(frame.columns),
        "rows": records,
        "breaks": analysis.breaks(obs).to_dict("records"),
        "months_without_observation": analysis.months_without_observation(obs).to_dict("records"),
        "freight_anchors": anchors,
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
    tests = analysis.flows_test(rows)
    return _clean({
        "schema_version": SCHEMA_VERSION,
        "first": joined["month"].min(), "last": joined["month"].max(),
        "months": months,
        "regressions": tests.to_dict("records"),
        "excluded_years": list(config.PARAMETERS["analysis_excluded_years"].value),
    }, ROUND_DP)


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


def write_all() -> list[Path]:
    """Write the three files from the committed data.

    Every document is built before any file is written, so a failure in one
    leaves all three as they were and the site's data always belong to one run.
    """
    with analysis.reading_once():
        obs = analysis.observations()
        rows, _ = analysis.work(obs)
        documents = {
            "now.json": now(obs),
            "history.json": history(rows, obs),
            "flows.json": flows(rows),
        }
    return [_write(name, document) for name, document in documents.items()]


def main() -> int:
    for path in write_all():
        print("wrote %s, %d bytes" % (path.relative_to(base.REPO_ROOT).as_posix(), path.stat().st_size))
    return 0


if __name__ == "__main__":
    sys.exit(main())

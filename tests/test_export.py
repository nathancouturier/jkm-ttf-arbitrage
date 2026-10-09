"""The site's data: what export.py writes, and that the committed files are what it writes today."""

from __future__ import annotations

import json
import math

import pytest

from lngarb import export
from lngarb.sources import base

DATA = base.REPO_ROOT / "data"


@pytest.fixture(scope="module")
def written():
    return {name: json.loads((DATA / name).read_text(encoding="utf-8"))
            for name in ("now.json", "model.json", "routes.json", "history.json", "flows.json", "provenance.json")}


def _numbers(value):
    if isinstance(value, dict):
        for v in value.values():
            yield from _numbers(v)
    elif isinstance(value, list):
        for v in value:
            yield from _numbers(v)
    elif isinstance(value, float):
        yield value


def test_every_file_is_versioned_and_holds_no_nan(written):
    for name, document in written.items():
        assert document["schema_version"] == export.SCHEMA_VERSION, name
        assert all(math.isfinite(x) for x in _numbers(document)), name


def test_the_committed_files_are_what_export_writes_today(written):
    with export.analysis.reading_once():
        obs = export.analysis.observations()
        rows, _ = export.analysis.work(obs)
        flows = export.flows(rows)
        provenance = export.provenance()
        now = export.now(obs, flows_document=flows, provenance_document=provenance)
        fresh = {"now.json": now, "model.json": export.model(now), "routes.json": export.routes(now),
                 "history.json": export.history(rows, obs), "flows.json": flows, "provenance.json": provenance}
    for name, document in fresh.items():
        assert json.loads(json.dumps(document)) == written[name], (
            "%s is stale: run PYTHONPATH=src python -m lngarb.export" % name)


def test_now_carries_each_input_with_its_source_and_the_engine_inputs(written):
    now = written["now.json"]
    for name in ("jkm", "ttf", "henry_hub", "hire", "regas_discount", "usd_per_eur", "eua", "overnight_rate"):
        assert now["inputs"][name]["source"], name
    assert now["engine_inputs"]["day"] == now["as_of"]
    assert set(now["at_levels"]) == {"low", "central", "high"}
    assert now["result"]["best_netback"] == pytest.approx(
        max([now["result"]["west"]["netback"]]
            + [r["netback"] for r in now["result"]["east"].values() if r["open"]]), abs=1e-12)


def test_history_and_flows_hold_what_the_views_need(written):
    history = written["history.json"]
    rows = [dict(zip(history["columns"], row)) for row in history["rows"]]
    assert {r["frequency"] for r in rows} == {"weekly", "monthly"}
    assert {r["hire_level"] for r in rows} >= {"low", "central", "high"}
    assert history["breaks"] and history["freight_anchors"]
    flows = written["flows.json"]
    assert flows["months"][0]["month"] == "2016-02-01"
    assert {r["sample"] for r in flows["regressions"]} == {"all months", "without 2020, 2022, 2026"}


def test_a_missing_date_is_null_never_the_word_nat():
    import numpy as np
    import pandas as pd

    assert export._clean(pd.NaT) is None
    assert export._clean({"a": pd.NaT, "b": [np.nan, pd.Timestamp("2026-01-02")]}) == {"a": None, "b": [None, "2026-01-02"]}

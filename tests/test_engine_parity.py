"""The engine twice: the committed cases are the Python engine's, and the JavaScript agrees with them."""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess

import pytest

from lngarb.sources import base

ROOT = base.REPO_ROOT
CASES = ROOT / "data" / "fixtures" / "engine-cases.json"


def _generator():
    spec = importlib.util.spec_from_file_location("gen_fixtures", ROOT / "scripts" / "gen_fixtures.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_committed_cases_are_what_the_python_engine_gives_today():
    generator = _generator()
    assert CASES.read_text(encoding="utf-8") == generator.render(generator.build()), (
        "the engine changed: run PYTHONPATH=src python scripts/gen_fixtures.py and commit the cases")


def test_the_cases_cover_what_the_parity_check_must_see():
    cases = json.loads(CASES.read_text(encoding="utf-8"))["cases"]
    assert len(cases) >= 200
    vessels = {c["inputs"]["vessel"]["name"] for c in cases}
    assert len(vessels) == 2
    hires = [c["inputs"]["hire_usd_day"] for c in cases]
    assert 0.0 in hires and min(hires) < 0
    assert any(c["inputs"]["delta_nwe"] == 0.0 for c in cases)
    routes = [r for c in cases for r in c["inputs"]["routes"].values()]
    assert any(r["ballast_distance_nm"] is not None for r in routes)
    assert any(not r["open"] for r in routes)
    assert any(r["laden_sea_days"] is not None for r in routes)
    assert any(r["ballast_sea_days"] is not None for r in routes)
    assert any(c["inputs"]["ets_by_year"] is not None and c["inputs"]["day"][5:7] == "12" for c in cases)
    assert {c["output"]["best_route"] for c in cases} >= {"nwe_direct", "nea_panama"}
    # Typed days on the route west, where the allowances read them, with a
    # carbon cost that is not zero; flex days; and an allowance price not read,
    # costing nothing without a surrender and unknown with one.
    west_typed = [c for c in cases if c["inputs"]["routes"]["nwe_direct"].get("laden_sea_days") is not None]
    assert any(c["inputs"]["ets_by_year"] is not None and c["output"]["west"]["ets_usd"] not in (0.0, None)
               for c in west_typed)
    assert any(r.get("flex_days", 0.0) > 0.0 for r in routes)
    unread = [c for c in cases if "eua_usd_t" in c["inputs"] and c["inputs"]["eua_usd_t"] is None]
    assert any(c["output"]["west"]["ets_usd"] == 0.0 for c in unread)
    assert any(c["output"]["west"]["ets_usd"] is None and c["output"]["west"]["netback"] is None for c in unread)


def test_the_edge_cases_reach_the_paths_random_draws_miss():
    cases = json.loads(CASES.read_text(encoding="utf-8"))["cases"]
    edges = {}
    for case in cases:
        if "edge" in case:
            edges.setdefault(case["edge"], []).append(case)
    assert set(edges) == {
        "year_end_fraction", "ets_year_missing", "hire_at_h_star", "identical_east_routes", "east_equals_west",
        "all_east_closed", "east_route_absent", "west_returns_other_way", "optional_fields_omitted"}
    loads = {c["inputs"]["vessel"]["load_days"] for c in edges["year_end_fraction"]}
    assert any(load != int(load) for load in loads)
    assert all(c["inputs"]["day"][5:] in ("12-30", "12-31", "01-01") for c in edges["year_end_fraction"])
    (missing,) = edges["ets_year_missing"]
    assert len(missing["inputs"]["ets_by_year"]) == 1
    (at_h_star,) = edges["hire_at_h_star"]
    assert at_h_star["output"]["east"]["nea_cape"]["arb"] == pytest.approx(0.0, abs=1e-9)
    (same,) = edges["identical_east_routes"]
    netbacks = {lines["netback"] for lines in same["output"]["east"].values()}
    assert len(netbacks) == 1 and same["output"]["best_route_east"] == "nea_panama"
    (tie,) = edges["east_equals_west"]
    assert all(lines["h_star_usd_day"] is None for lines in tie["output"]["east"].values())
    assert tie["output"]["best_route"] == "nwe_direct"
    (closed,) = edges["all_east_closed"]
    assert closed["output"]["best_route_east"] is None
    (absent,) = edges["east_route_absent"]
    assert "nea_suez" not in absent["inputs"]["routes"]
    (other,) = edges["west_returns_other_way"]
    assert other["inputs"]["routes"]["nwe_direct"]["ballast_distance_nm"] is not None
    (bare,) = edges["optional_fields_omitted"]
    assert "ets_phase" not in bare["inputs"] and all("open" not in r for r in bare["inputs"]["routes"].values())


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_an_infinity_from_the_javascript_is_a_disagreement(tmp_path):
    # A copy of the engine that divides by zero where Python would raise: the
    # validator must not let the infinity through as a match.
    (tmp_path / "src").mkdir()
    (tmp_path / "tools").mkdir()
    (tmp_path / "data" / "fixtures").mkdir(parents=True)
    source = (ROOT / "src" / "engine.js").read_text(encoding="utf-8")
    assert source.count("freight_conventional: f_conv,") == 1
    (tmp_path / "src" / "engine.js").write_text(
        source.replace("freight_conventional: f_conv,", "freight_conventional: f_conv / 0,"), encoding="utf-8")
    shutil.copy(ROOT / "tools" / "validate-engine.mjs", tmp_path / "tools" / "validate-engine.mjs")
    shutil.copy(ROOT / "src" / "model-calc.js", tmp_path / "src" / "model-calc.js")
    document = json.loads(CASES.read_text(encoding="utf-8"))
    document["cases"] = document["cases"][:2]
    (tmp_path / "data" / "fixtures" / "engine-cases.json").write_text(json.dumps(document), encoding="utf-8")
    run = subprocess.run([shutil.which("node"), str(tmp_path / "tools" / "validate-engine.mjs")],
                         capture_output=True, text=True)
    assert run.returncode == 1
    assert "case 0.west.freight_conventional: expected" in run.stdout and "Infinity" in run.stdout


node = shutil.which("node")


@pytest.mark.skipif(node is None, reason="node is not installed")
def test_the_javascript_engine_agrees_to_1e_9():
    run = subprocess.run([node, str(ROOT / "tools" / "validate-engine.mjs")], capture_output=True, text=True)
    assert run.returncode == 0, run.stdout + run.stderr


@pytest.mark.skipif(node is None, reason="node is not installed")
def test_a_disagreement_is_caught(tmp_path):
    document = json.loads(CASES.read_text(encoding="utf-8"))
    document["cases"] = document["cases"][:3]
    document["cases"][1]["output"]["east"]["nea_cape"]["s_star"] += 1e-6
    wrong = tmp_path / "cases.json"
    wrong.write_text(json.dumps(document), encoding="utf-8")
    run = subprocess.run([node, str(ROOT / "tools" / "validate-engine.mjs"), str(wrong)], capture_output=True, text=True)
    assert run.returncode == 1
    assert "case 1.east.nea_cape.s_star" in run.stdout

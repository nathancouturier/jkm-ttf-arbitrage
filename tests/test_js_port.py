"""The browser's engine gives the Python engine's numbers on every fixture case."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from arb import engine

HERE = Path(__file__).resolve().parent


def test_the_fixture_is_what_the_python_engine_gives_today():
    cases = json.loads((HERE / "fixtures" / "engine_cases.json").read_text())
    assert len(cases) >= 40
    for case in cases[:10]:
        assert engine.price_cargo(case["inputs"])["routes"]["cape"]["netback"] == pytest.approx(
            case["expected"]["routes"]["cape"]["netback"], abs=1e-12)


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_the_javascript_engine_matches_the_python_engine():
    run = subprocess.run(["node", str(HERE / "check_engine.mjs")], capture_output=True, text=True)
    assert run.returncode == 0, run.stdout + run.stderr

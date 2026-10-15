"""The README's figures are the artifacts' own: a drift fails here by name."""

from __future__ import annotations

import json
import re

from lngarb import config, freight_anchors
from lngarb.sources import base

ROOT = base.REPO_ROOT
README = re.sub(r"\s+", " ", (ROOT / "README.md").read_text(encoding="utf-8"))


def _regression(flows, *, share, hire_level, sample):
    (found,) = [r for r in flows["regressions"] if r["share"] == share and r["hire_level"] == hire_level
                and r["sample"] == sample]
    return found


def test_the_readme_s_regression_figures_are_the_flows_artifact_s():
    flows = json.loads((ROOT / "data" / "flows.json").read_text(encoding="utf-8"))
    whole = _regression(flows, share="share_asia", hire_level="central", sample="all months")
    without = [r for r in flows["regressions"] if r["share"] == "share_asia" and r["hire_level"] == "central"
               and r["sample"].startswith("without")]
    (without,) = without
    match = re.search(r"Over (\d+) months from (\w+ \d{4}) to (\w+ \d{4}), a dollar more of arb east at loading "
                      r"went with ([\d.]+) points more of US exports by vessel going to Asia, at a t statistic of "
                      r"([\d.]+) with Newey-West errors, and an R squared of ([\d.]+)\. Without ([\d, ]+) and (\d{4}) "
                      r"the slope is ([\d.]+) points and R squared ([\d.]+)\.", README)
    assert match, "the README's regression sentence has moved"
    assert int(match.group(1)) == whole["n"]
    assert float(match.group(4)) == round(whole["slope"] * 100, 1)
    assert float(match.group(5)) == round(whole["t_slope"], 1)
    assert float(match.group(6)) == round(whole["r2"], 2)
    years = [int(y) for y in re.findall(r"\d{4}", match.group(7) + " " + match.group(8))]
    assert years == list(flows["excluded_years"])
    assert float(match.group(9)) == round(without["slope"] * 100, 1)
    assert float(match.group(10)) == round(without["r2"], 2)
    assert flows["months"][0]["month"].startswith(str(whole["first_month"]))


def test_the_readme_s_counts_are_the_repository_s():
    words = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine",
             10: "ten", 11: "eleven", 12: "twelve"}
    held = len(freight_anchors.ANCHORS)
    assert "The study holds %s rates" % words.get(held, str(held)) in README
    waits = config.PARAMETERS["panama_waits_reported"].value
    assert "with the %s, %s and %s days reported for July, August and December 2023" % tuple(
        int(v) for v in waits.values()) in README
    cases = json.loads((ROOT / "data" / "fixtures" / "engine-cases.json").read_text(encoding="utf-8"))
    count = len(cases["cases"]) if isinstance(cases, dict) and "cases" in cases else len(cases)
    assert "1e-9 on %d cases" % count in README
    model = json.loads((ROOT / "data" / "model.json").read_text(encoding="utf-8"))
    assert "on %d named edits" % len(model["checks"]) in README
    assert "%s views:" % words[6].capitalize() in README

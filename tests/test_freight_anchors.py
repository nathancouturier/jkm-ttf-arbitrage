"""The reported charter rates: kept to their rules, and the committed seed matches them."""

from __future__ import annotations

import dataclasses
import json

from lngarb import freight_anchors
from lngarb.freight_anchors import ANCHORS


def test_the_rows_keep_their_rules():
    assert freight_anchors.problems() == []
    assert len(ANCHORS) == 51
    assert [a.month for a in ANCHORS][0] == "2021-01"
    assert [a.month for a in ANCHORS][-1] == "2026-10"
    # One figure a month at most, the first reported in the month; the rule of question 37.
    assert len({a.month for a in ANCHORS}) == len(ANCHORS)


def test_the_committed_seed_is_the_rows_here():
    committed = json.loads(freight_anchors.seed_path().read_text(encoding="utf-8"))
    assert committed == freight_anchors.document()


def test_the_figures_used_by_the_worked_dates():
    by_month = {a.month: a for a in ANCHORS}
    assert by_month["2022-10"].hire_usd_day == 374_000
    assert by_month["2022-10"].rate_date == "2022-10-10"
    assert by_month["2024-03"].hire_usd_day == 46_500
    assert by_month["2024-03"].vessel == "174,000 m3 two-stroke" and by_month["2024-03"].vessel_stated
    assert by_month["2026-10"].hire_usd_day == 31_500
    assert not by_month["2026-10"].assessment_stated


def test_no_row_rests_on_a_source_the_study_dropped_or_links_spark():
    for a in ANCHORS:
        assert a.url is None or "lloydslist" not in a.url
        assert a.url is None or "sparkcommodities" not in a.url


def test_low_central_and_high_hire_are_the_lowest_median_and_highest():
    assert freight_anchors.hire_levels() == {"low": -750.0, "central": 55_750.0, "high": 447_000.0}
    # By ship: the figures of each ship's own days, the two-stroke from 2 January 2024.
    by_ship = freight_anchors.hire_levels_by_ship()
    assert list(by_ship) == ["tfde_160k", "two_stroke_174k"]
    assert by_ship["tfde_160k"]["count"] + by_ship["two_stroke_174k"]["count"] == len(ANCHORS)
    assert by_ship["tfde_160k"]["last"] < "2024-01-02" <= by_ship["two_stroke_174k"]["first"]
    assert freight_anchors.hire_levels(when="2023-12-31") == {k: by_ship["tfde_160k"][k] for k in ("low", "central", "high")}
    assert freight_anchors.hire_levels(when="2024-01-02")["central"] == by_ship["two_stroke_174k"]["central"]
    assert by_ship["two_stroke_174k"]["central"] < by_ship["tfde_160k"]["central"]


def test_a_row_dated_in_another_month_or_out_of_range_is_reported():
    bad = dataclasses.replace(ANCHORS[1], rate_date="2022-11-01")
    worse = dataclasses.replace(ANCHORS[2], hire_usd_day=600_000.0)
    found = freight_anchors.problems((ANCHORS[0], bad, worse))
    assert any("another month" in p for p in found)
    assert any("outside" in p for p in found)

"""The History view's layer of history.json: every count recounted from the rows it summarises."""

from __future__ import annotations

import json
import re
from datetime import date

import pytest

from lngarb import spreadhistory
from lngarb.sources import base

DATA = base.REPO_ROOT / "data"


@pytest.fixture(scope="module")
def history():
    return json.loads((DATA / "history.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def rows(history):
    return [dict(zip(history["columns"], row)) for row in history["rows"]]


def _cheapest(row):
    best = None
    for short in ("panama", "suez", "cape"):
        value = row[short + "_s_star"]
        if row[short + "_open"] and value is not None and (best is None or value < best):
            best = value
    return best


def _values(segments):
    return {s["field"]: s["value"] for s in segments if "field" in s}


def test_every_range_s_count_is_the_rows_own(history, rows):
    central = {r["day"]: r for r in rows if r["frequency"] == "weekly" and r["hire_level"] == "central"}
    for chart_range in history["page"]["weekly"]["ranges"]:
        days = [d for d in sorted(central) if chart_range["first"] <= d <= chart_range["last"]]
        both = [central[d] for d in days if central[d]["spread"] is not None and _cheapest(central[d]) is not None]
        opened = sum(r["spread"] > _cheapest(r) for r in both)
        values = _values(chart_range["heading_segments"])
        assert values["weeks"] == len(both) and values["weeks_open"] == opened, chart_range["id"]
        assert sum(y["count"] for y in chart_range["years"]) == len(both)


def test_the_monthly_count_is_the_rows_own(history, rows):
    central = [r for r in rows if r["frequency"] == "monthly" and r["hire_level"] == "central"]
    both = [r for r in central if r["spread"] is not None and _cheapest(r) is not None]
    values = _values(history["page"]["monthly"]["heading_segments"])
    assert values["months"] == len(both)
    assert values["months_open"] == sum(r["spread"] > _cheapest(r) for r in both)


def test_the_weeks_near_a_reported_rate_are_counted_from_the_reported_rows(history, rows):
    reported = {r["day"]: r for r in rows if r["frequency"] == "weekly" and r["hire_level"] == "reported"}
    (every,) = [r for r in history["page"]["weekly"]["ranges"] if r["id"] == "all"]
    values = _values(every["hstar_heading_segments"])
    assert values["weeks_near"] == len(reported)
    assert values["weeks_near_open"] == sum(r["arb"] is not None and r["arb"] > 0 for r in reported.values())


def test_the_columns_line_up_and_a_gap_is_null_in_every_one(history):
    weekly = history["page"]["weekly"]
    columns = ("day", "spread", "s_low", "s_central", "s_high", "route", "h_star", "alignment")
    assert len({len(weekly[c]) for c in columns}) == 1
    for index, day in enumerate(weekly["day"]):
        if day is None:
            assert all(weekly[c][index] is None for c in columns)
    days = [date.fromisoformat(d) for d in weekly["day"] if d is not None]
    assert days == sorted(days)
    monthly = history["page"]["monthly"]
    missing = {m["month"][:7] for m in monthly["without"]}
    shown = [d for d in monthly["day"] if d is not None]
    gaps = monthly["day"].count(None)
    first, last = date.fromisoformat(monthly["first"]), date.fromisoformat(monthly["last"])
    months = (last.year - first.year) * 12 + last.month - first.month + 1
    assert len(monthly["day"]) == months and len(shown) + gaps == months
    assert not missing & {d[:7] for d in shown}


def test_each_range_s_domain_holds_its_points(history):
    weekly = history["page"]["weekly"]
    for chart_range in weekly["ranges"]:
        y = chart_range["y"]
        for index, day in enumerate(weekly["day"]):
            if day is None or not chart_range["first"] <= day <= chart_range["last"]:
                continue
            for column in ("spread", "s_low", "s_high"):
                value = weekly[column][index]
                assert value is None or y["low"] <= value <= y["high"], (chart_range["id"], day, column)
        hstar = chart_range["hstar"]
        values = [weekly["h_star"][i] for i, d in enumerate(weekly["day"])
                  if d is not None and chart_range["first"] <= d <= chart_range["last"] and weekly["h_star"][i] is not None]
        assert hstar["below"] == sum(v < hstar["low"] for v in values)
        assert hstar["above"] == sum(v > hstar["high"] for v in values)
        assert hstar["below"] + hstar["above"] <= len(values) * 2 * spreadhistory.HSTAR_TAIL + 2


def test_the_rules_number_the_drawn_breaks_in_order(history):
    page = history["page"]
    numbers = [n for rule in page["rules"] for n in rule["numbers"]]
    assert numbers == [b["number"] for b in page["breaks"]] == list(range(1, len(page["breaks"]) + 1))
    by_number = {b["number"]: b for b in page["breaks"]}
    for rule in page["rules"]:
        assert {by_number[n]["day"] for n in rule["numbers"]} == {rule["day"]}
    assert {b["kind"] for b in page["breaks"]} <= set(spreadhistory.DRAWN)


def test_the_latest_charter_rate_is_the_one_accent(history):
    anchors = history["page"]["anchors"]
    accents = [a for a in anchors if a["accent"]]
    assert len(accents) == 1 and accents[0]["day"] == max(a["day"] for a in anchors)


def test_no_sentence_holds_a_machine_date_or_a_figure_in_its_words(history):
    page = history["page"]
    sentences = [page["monthly"][k] for k in ("heading_segments", "desc_segments", "caption_segments")]
    sentences += [page["breaks_lead_segments"], page["source_segments"]]
    for chart_range in page["weekly"]["ranges"]:
        sentences += [chart_range[k] for k in chart_range if k.endswith("_segments")]
    for segments in sentences:
        for segment in segments:
            if "text" in segment:
                assert not re.search(r"\d", segment["text"]), segment["text"]


def test_the_ticks_fall_inside_their_range(history):
    page = history["page"]
    for chart_range in page["weekly"]["ranges"]:
        assert all(chart_range["first"] <= t["day"] <= chart_range["last"] for t in chart_range["ticks"])
    assert all(page["monthly"]["first"] <= t["day"] <= page["monthly"]["last"] for t in page["monthly"]["ticks"])

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


def test_each_range_s_accent_is_the_rate_its_caption_names(history):
    for chart_range in history["page"]["weekly"]["ranges"]:
        values = {s["field"]: s["value"] for s in chart_range["hstar_caption_segments"] if "field" in s}
        assert values.get("latest_hire_day") == chart_range["accent_day"], chart_range["id"]


def test_the_monthly_caption_counts_the_gaps_in_the_line(history):
    monthly = history["page"]["monthly"]
    values = {s["field"]: s["value"] for s in monthly["caption_segments"] if "field" in s}
    assert values["months_without"] == monthly["day"].count(None) == len(monthly["without"])


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


def test_the_parts_of_s_star_add_up_to_it_on_every_week_with_an_open_route(history):
    weekly = history["page"]["weekly"]
    counted = 0
    for index, day in enumerate(weekly["day"]):
        if day is None or weekly["route"][index] is None:
            assert weekly["boil_off"][index] is None and weekly["regas"][index] is None and weekly["voyage"][index] is None
            continue
        total = weekly["boil_off"][index] + weekly["regas"][index] + weekly["voyage"][index]
        assert abs(total - weekly["s_central"][index]) < 1e-5
        counted += 1
    assert counted > 200
    for item in weekly["ranges"]:
        values = _values(item["parts_heading_segments"])
        assert abs(values["mean_boil_off"] + values["mean_regas"] + values["mean_voyage"] - values["mean_s"]) < 1e-5
        assert item["parts_y"]["low"] <= values["mean_regas"] and values["mean_voyage"] <= item["parts_y"]["high"]


def test_the_mixed_and_misaligned_weeks_of_each_range_are_counted_from_the_columns(history):
    weekly = history["page"]["weekly"]
    for item in weekly["ranges"]:
        inside = [i for i, day in enumerate(weekly["day"]) if day is not None and item["first"] <= day <= item["last"]]
        assert item["mixed_weeks"] == sum(weekly["alignment"][i] == "mixed" for i in inside)
        assert item["misaligned_weeks"] == sum(weekly["alignment"][i] == "misaligned" for i in inside)
    assert sum(a == "mixed" for a in weekly["alignment"]) > 0


def test_the_events_are_lettered_in_order_of_day_and_each_has_a_source(history):
    events = history["page"]["events"]
    # A to Z, then AA, AB and on, as the events module letters them.
    def letter(index):
        out = ""
        while True:
            out = chr(ord("A") + index % 26) + out
            index = index // 26 - 1
            if index < 0:
                return out
    assert [e["letter"] for e in events] == [letter(i) for i in range(len(events))]
    assert [e["day"] for e in events] == sorted(e["day"] for e in events)
    for event in events:
        assert event["what"].endswith(".") and event["source"]
        assert event["dated_to"] in ("day", "month")
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", event["day"])
    rules = history["page"]["event_rules"]
    assert [r["day"] for r in rules] == [e["day"] for e in events]
    assert all(r["letters"] == [e["letter"]] for r, e in zip(rules, events))

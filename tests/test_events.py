"""The dated events: kept to their rules, one document each, and the committed seed matches them."""

from __future__ import annotations

import dataclasses
import json

from lngarb import events
from lngarb.events import EVENTS, LEFT_OUT


def test_the_rows_keep_their_rules():
    assert events.problems() == []
    assert EVENTS[0].day == "2016-02-24"
    assert all(e.url.startswith("https://") for e in EVENTS)


def test_the_committed_seed_is_the_rows_here():
    committed = json.loads(events.seed_path().read_text(encoding="utf-8"))
    assert committed == events.document()


def test_no_row_rests_on_a_source_the_study_does_not_request():
    for e in EVENTS:
        for host in ("spglobal", "lloydslist", "sparkcommodities", "jogmec", "acer.europa.eu"):
            assert host not in e.url


def test_what_is_left_out_says_why():
    assert LEFT_OUT
    assert all(what.strip() and reason.strip() for what, reason in LEFT_OUT)


def test_letters_follow_the_days():
    rows = events.lettered()
    assert [r["letter"] for r in rows[:3]] == ["A", "B", "C"]
    assert [r["day"] for r in rows] == sorted(r["day"] for r in rows)


def test_a_row_out_of_order_or_ending_before_it_begins_is_reported():
    late = dataclasses.replace(EVENTS[1], end="2020-05-01")
    found = events.problems((EVENTS[2], late))
    assert any("not in order" in p for p in found)
    assert any("before it begins" in p for p in found)


def test_the_history_view_carries_every_event_its_mark_and_what_was_left_out():
    from lngarb.sources import base

    page = json.loads((base.REPO_ROOT / "data" / "history.json").read_text(encoding="utf-8"))["page"]
    letters = [e["letter"] for e in page["events"]]
    assert letters == [r["letter"] for r in events.lettered()]
    assert [m["letter"] for m in page["event_marks"]] == letters
    # a one day event has no end; a period has one, after its first day
    ends = {m["letter"]: m["end"] for m in page["event_marks"]}
    assert any(end is None for end in ends.values())
    assert all(end is None or end > m["day"] for m, end in zip(page["event_marks"], ends.values()))
    assert len(page["events_left_out"]) == len(LEFT_OUT)


def test_a_row_without_https_or_words_is_reported():
    bare = dataclasses.replace(EVENTS[0], url="http://example.org/", what=" ")
    found = events.problems((bare,))
    assert any("not https" in p for p in found)
    assert any("no what" in p for p in found)

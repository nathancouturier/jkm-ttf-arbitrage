"""The dated events: kept to their rules, each with its document, and the committed seed matches them."""

from __future__ import annotations

import dataclasses
import json

from lngarb import events
from lngarb.events import EVENTS, LEFT_OUT


def test_the_rows_keep_their_rules():
    assert events.problems() == []
    assert events.lettered()[0]["day"] == "2016-02-24"
    assert all(e.url is None or e.url.startswith("https://") for e in EVENTS)


def test_the_committed_seed_is_the_rows_here():
    committed = json.loads(events.seed_path().read_text(encoding="utf-8"))
    assert committed == events.document()


def test_no_row_rests_on_a_source_the_study_does_not_request():
    for e in EVENTS:
        for host in ("spglobal", "lloydslist", "sparkcommodities", "jogmec", "acer.europa.eu"):
            assert host not in (e.url or "")


def test_what_is_left_out_says_why():
    assert LEFT_OUT
    assert all(what.strip() and reason.strip() for what, reason in LEFT_OUT)


def test_letters_follow_the_days():
    rows = events.lettered()
    assert [r["letter"] for r in rows[:3]] == ["A", "B", "C"]
    assert [r["day"] for r in rows] == sorted(r["day"] for r in rows)
    assert rows[26]["letter"] == "AA" and rows[27]["letter"] == "AB"


def test_a_row_ending_before_it_begins_is_reported():
    late = dataclasses.replace(EVENTS[1], end="2015-05-01")
    found = events.problems((EVENTS[0], late))
    assert any("before it begins" in p for p in found)


def test_the_history_view_carries_every_event_its_rule_and_what_was_left_out():
    from lngarb.sources import base

    page = json.loads((base.REPO_ROOT / "data" / "history.json").read_text(encoding="utf-8"))["page"]
    letters = [e["letter"] for e in page["events"]]
    assert letters == [r["letter"] for r in events.lettered()]
    # one rule a day, with the letters of every event of that day
    assert [letter for r in page["event_rules"] for letter in r["letters"]] == letters
    assert [r["day"] for r in page["event_rules"]] == sorted({e["day"] for e in page["events"]})
    # a one day event has no end; a period has one, after its first day
    assert any(e["end"] is None for e in page["events"])
    assert all(e["end"] is None or e["end"] > e["day"] for e in page["events"])
    assert len(page["events_left_out"]) == len(LEFT_OUT)


def test_a_row_without_https_or_words_is_reported():
    bare = dataclasses.replace(EVENTS[0], url="http://example.org/", what=" ")
    found = events.problems((bare,))
    assert any("not https" in p for p in found)
    assert any("no what" in p for p in found)

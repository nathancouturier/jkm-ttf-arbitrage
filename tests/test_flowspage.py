"""The Flows view's layer of flows.json: every count recounted from what it summarises."""

from __future__ import annotations

import json
import re

import pytest

from lngarb.reported import reported
from lngarb.sources import base

DATA = base.REPO_ROOT / "data"


@pytest.fixture(scope="module")
def flows():
    return json.loads((DATA / "flows.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def history():
    return json.loads((DATA / "history.json").read_text(encoding="utf-8"))


def _values(segments):
    return {s["field"]: s["value"] for s in segments if "field" in s}


def test_the_whole_period_counts_every_month_priced(flows):
    panel = flows["page"]["whole"]
    priced = [m for m in panel["months"] if m["arb"] is not None]
    values = _values(panel["heading_segments"])
    assert values["months"] == len(priced)
    assert values["open_months"] == sum(m["arb"] > 0 for m in priced)
    # Asia's share of the exports of the open months, pooled from the volumes.
    volumes = {m["month"]: m for m in flows["months"]}
    opened = [volumes[m["month"]] for m in priced if m["arb"] > 0]
    pooled = sum(m["asia_mmcf"] for m in opened) / sum(m["total_mmcf"] for m in opened) * 100.0
    assert values["share_open"] == pytest.approx(pooled, abs=1e-6)
    held = [m for m in flows["months"] if m["share_asia"] is not None]
    assert len(panel["months"]) == len(held)


def test_the_test_rows_are_the_regressions_and_the_sign_tables_add_up(flows):
    rows = flows["page"]["test"]["rows"]
    fitted = [r for r in flows["regressions"] if r.get("slope") is not None]
    assert len(rows) == len(fitted)
    for row in rows:
        assert row["open_above"] + row["open_below"] + row["closed_above"] + row["closed_below"] == row["n"]
        assert min(row["open_above"], row["open_below"], row["closed_above"], row["closed_below"]) >= 0
    values = _values(flows["page"]["test"]["heading_segments"])
    assert values["fits"] == len(rows)
    assert values["significant"] == sum(abs(r["t"]) >= 2.0 for r in rows)


def test_2020_names_the_months_with_cancellations_reported(flows):
    y2020 = flows["page"]["y2020"]
    cancelled = {r.period for r in reported("cancellations")}
    assert {m["month"][:7] for m in y2020["months"] if m["cancelled"] is not None} == cancelled
    values = _values(y2020["heading_segments"])
    for month in y2020["months"]:
        if month["cancelled"] is not None and month["notice"]["central"] is not None:
            named_below = month["label"] in values["below"]
            assert named_below == (month["notice"]["central"] < 0), month["label"]
            assert (month["label"] in values.get("above", "")) == (month["notice"]["central"] >= 0), month["label"]
    assert values["high_below"] == sum(m["notice"]["high"] is not None and m["notice"]["high"] < 0 for m in y2020["months"])


def test_2026_counts_the_weeks_from_the_history_rows(flows, history):
    y2026 = flows["page"]["y2026"]
    columns = history["columns"]
    rows = [dict(zip(columns, r)) for r in history["rows"]]
    weeks = {r["day"]: r for r in rows if r["frequency"] == "weekly" and r["hire_level"] == "central"
             and r["day"] >= y2026["days"][0]}
    assert sorted(weeks) == y2026["days"]
    values = _values(y2026["heading_segments"])
    both = [r for r in weeks.values() if r["spread"] is not None and r["day"] <= y2026["assessment_week"]]
    assert values["weeks"] == len(both)
    assert values["panama_open"] == sum(r["panama_open"] and r["spread"] > r["panama_s_star"] for r in both)
    assert values["cape_open"] == sum(r["cape_open"] and r["spread"] > r["cape_s_star"] for r in both)
    (asia,) = reported("asia_use")
    assert values["asia_cargoes"] == asia.figure


def test_the_waits_compare_the_reported_wait_with_its_breakeven(flows):
    waits = flows["page"]["waits"]
    central = [r for r in waits["rows"] if r["hire_level"] == "central"]
    assert central and all(r["wait_reported"] > 0 for r in central)
    words = "".join(s.get("text", "") for s in waits["heading_segments"])
    longer = all(r["wait_breakeven"] is not None and r["wait_reported"] > r["wait_breakeven"] for r in central)
    assert ("each was longer than" in words) == longer


def test_no_sentence_holds_a_figure_in_its_words(flows):
    page = flows["page"]
    sentences = [page["test"]["heading_segments"], page["test"]["sign_segments"], page["y2020"]["heading_segments"],
                 page["y2020"]["caption_segments"], page["y2026"]["heading_segments"],
                 page["y2026"]["compare_caption_segments"], page["waits"]["heading_segments"], page["limits_segments"],
                 page["whole"]["heading_segments"]]
    for segments in sentences:
        for segment in segments:
            if "text" in segment:
                assert not re.search(r"\d", segment["text"]), segment["text"]


def test_the_2020_sentence_names_where_the_notice_test_fails_and_the_marks_carry_the_counts(flows):
    y2020 = flows["page"]["y2020"]
    failing = [m for m in y2020["months"] if m["cancelled"] is not None and m["notice"]["central"] >= 0]
    named = [s["value"] for s in y2020["heading_segments"] if s.get("field") == "why_month"]
    assert named == [m["label"] for m in failing]
    for m in failing:
        jkm = next(s["value"] for s in y2020["heading_segments"] if s.get("field") == "why_jkm_" + m["month"][:7])
        assert jkm == m["notice_jkm"]
    reported = [m for m in y2020["months"] if m["cancelled"] is not None]
    assert [mark["letter"] for mark in y2020["cancelled_marks"]] == [str(int(m["cancelled"])) for m in reported]


def test_the_2020_sentence_names_meti_s_month_and_the_months_below_zero_with_none_reported(flows):
    y2020 = flows["page"]["y2020"]
    words = {s["field"]: s.get("value") for s in y2020["heading_segments"] if "field" in s}
    june = next(m for m in y2020["months"] if m["month"] == "2020-06-01")
    assert "March 2020" in words["why_source_2020-06"]
    unreported = [m["label"] for m in y2020["months"]
                  if m["cancelled"] is None and m["notice"]["central"] is not None and m["notice"]["central"] < 0]
    if unreported:
        assert all(label in words["unreported"] for label in unreported)
    assert june["notice_jkm"] == words["why_jkm_2020-06"]

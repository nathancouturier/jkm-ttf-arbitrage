"""The reader's layer: what the Now view says is what the engine computed."""

from __future__ import annotations

import json
import math

import pytest

from lngarb import reader
from lngarb.cases import WATERFALL_STEPS
from lngarb.sources import base

DATA = base.REPO_ROOT / "data"


@pytest.fixture(scope="module")
def now():
    return json.loads((DATA / "now.json").read_text(encoding="utf-8"))


def _values(segments):
    return {s["field"]: s["value"] for s in segments if "field" in s}


def test_a_text_segment_never_holds_a_figure():
    with pytest.raises(ValueError):
        reader.T("nets 23.96")
    assert reader.T("nets ") == {"text": "nets "}
    with pytest.raises(KeyError):
        reader.N("x", 1.0, "no_such_format")


def test_the_verdict_names_the_best_route_and_its_gap(now):
    result = now["result"]
    values = _values(now["verdict"]["segments"])
    assert values["best_netback"] == pytest.approx(result["best_netback"], abs=1e-12)
    assert values["best_route_name"] == reader.ROUTE_NAMES[result["best_route"]]
    if result["best_destination"] == "NEA":
        assert values["gap_to_gate"] == pytest.approx(result["best_netback"] - result["west"]["netback"], abs=1e-12)
    open_east = {r: l for r, l in result["east"].items() if l["open"]}
    cheapest = min(open_east, key=lambda r: open_east[r]["s_star"])
    assert values["cheapest_route"] == reader.ROUTE_SHORT[cheapest]
    assert values["s_star"] == pytest.approx(open_east[cheapest]["s_star"], abs=1e-12)
    parts = {name: open_east[cheapest][name] for name in ("boil_off", "regas", "voyage")}
    dominant = max(parts, key=lambda name: abs(parts[name]))
    assert values["dominant_part"] == reader.PART_WORDS[dominant]
    assert values["lift_margin"] == pytest.approx(abs(result["lift_margin"]), abs=1e-12)


def test_every_input_has_its_sentence(now):
    assert [row["id"] for row in now["data_dates"]] == ["jkm", "ttf", "henry_hub", "hire", "regas_discount", "also"]
    inputs = now["engine_inputs"]
    assert _values(now["data_dates"][0]["segments"])["jkm"] == inputs["jkm"]
    assert _values(now["data_dates"][1]["segments"])["ttf"] == inputs["ttf"]
    assert _values(now["data_dates"][2]["segments"])["henry_hub"] == inputs["henry_hub"]
    assert _values(now["data_dates"][3]["segments"])["hire"] == inputs["hire_usd_day"]
    assert _values(now["data_dates"][4]["segments"])["delta_nwe"] == inputs["delta_nwe"]


def test_the_netbacks_have_one_accent_the_best_route(now):
    rows = now["netbacks"]["rows"]
    assert [r["id"] for r in rows] == ["nwe_direct", "nea_panama", "nea_suez", "nea_cape"]
    assert [r["id"] for r in rows if r["accent"]] == [now["result"]["best_route"]]
    for row in rows[1:]:
        lines = now["result"]["east"][row["id"]]
        assert row["open"] == lines["open"]
        assert row["value"] == lines["netback"]
    scale = now["netbacks"]["scale"]
    assert scale["low"] <= 0 <= scale["high"]
    assert scale["high"] >= max(r["value"] for r in rows)


def test_the_steps_of_the_arb_add_up_to_it(now):
    cost = now["cost"]
    route = now["result"]["best_route_east"]
    assert cost["route"] == route
    steps = [r for r in cost["rows"] if r["kind"] == "step"]
    (total,) = [r for r in cost["rows"] if r["kind"] == "total"]
    assert [r["id"] for r in steps] == list(WATERFALL_STEPS)
    assert math.fsum(r["value"] for r in steps) == pytest.approx(total["value"], abs=1e-12)
    assert total["value"] == pytest.approx(now["result"]["east"][route]["arb"], abs=1e-12)
    running = 0.0
    for row in steps:
        assert row["start"] == pytest.approx(running, abs=1e-12)
        running += row["value"]
        assert row["end"] == pytest.approx(running, abs=1e-12)
    assert cost["scale"]["low"] <= min(min(r["start"], r["end"]) for r in cost["rows"])
    assert cost["scale"]["high"] >= max(max(r["start"], r["end"]) for r in cost["rows"])


def test_the_breakeven_lines_are_the_engines(now):
    from dataclasses import replace

    import pandas as pd

    from lngarb import analysis, worked
    from lngarb.cases import evaluate

    section = now["breakeven"]
    inputs = now["engine_inputs"]
    day = inputs["day"]
    rebuilt = worked.inputs_on(day, inputs["jkm"], inputs["ttf"], {"jkm": "test", "ttf": "test"},
                               hire_usd_day=inputs["hire_usd_day"],
                               delta_window=analysis.window(pd.Timestamp(day), "weekly"))
    assert rebuilt.delta_nwe == pytest.approx(inputs["delta_nwe"], abs=1e-12)
    for line in section["lines"]:
        for hire, s_star in line["points"]:
            out = evaluate(replace(rebuilt, hire_usd_day=hire))
            assert s_star == pytest.approx(out["east"][line["route"]]["s_star"], abs=1e-9)
        assert line["h_star"] == pytest.approx(now["result"]["east"][line["route"]]["h_star_usd_day"], rel=1e-12)
        assert now["result"]["east"][line["route"]]["open"]
    assert section["x"]["low"] == 0.0
    assert section["spread"]["value"] == pytest.approx(now["result"]["spread"], abs=1e-12)


def test_the_flows_panel_says_what_its_months_show():
    flows = json.loads((DATA / "flows.json").read_text(encoding="utf-8"))
    panel = flows["panel"]
    months = panel["months"]
    assert len(months) == reader.FLOWS_MONTHS
    values = _values(panel["heading_segments"])
    priced = [m for m in months if m["arb"] is not None]
    opened = [m for m in priced if m["arb"] > 0]
    if "open_months" in values:
        assert values["open_months"] == len(opened)
        assert values["share_open"] == pytest.approx(sum(m["share_asia"] for m in opened) / len(opened), abs=1e-6)
    for month in months:
        assert 0 <= month["share_asia"] <= 100


def test_provenance_lists_every_series_of_the_manifest():
    manifest = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))
    provenance = json.loads((DATA / "provenance.json").read_text(encoding="utf-8"))
    assert [r["id"] for r in provenance["series"]] == [e["series"] for e in manifest["series"]]
    private = [r for r in provenance["series"] if r["terms_words"].startswith("kept private")]
    assert {r["id"] for r in private} == {e["series"] for e in manifest["series"] if not e["committable"]}
    assert len(provenance["manual_steps"]) == len(manifest["manual_steps"])
    assert any("New York Fed is not responsible" in credit for credit in provenance["credits"])


# ---------------------------------------------------------------- branches ---
# Sentences the data of today do not reach, built from today's inputs with one
# figure changed, so every branch of the wording is held to the engine.


def _today(now, **changes):
    from dataclasses import replace

    import pandas as pd

    from lngarb import analysis, worked

    inputs = now["engine_inputs"]
    built = worked.inputs_on(inputs["day"], inputs["jkm"], inputs["ttf"], {"jkm": "test", "ttf": "test"},
                             hire_usd_day=inputs["hire_usd_day"],
                             delta_window=analysis.window(pd.Timestamp(inputs["day"]), "weekly"))
    return replace(built, **changes)


def _hire(value, reported=True):
    from lngarb import worked

    anchor, gap = worked.nearest_anchor("2026-10-07")
    return {"value": value, "reported": reported, "anchor": anchor, "date": worked._anchor_day(anchor), "gap": gap,
            "max_days": 14}


def _text(segments):
    out = []
    for s in segments:
        out.append(s.get("text", s.get("label", "" if s.get("value") is None else str(s.get("value")))))
    return "".join(out)


def _breakeven(inputs, hire):
    from dataclasses import replace
    from datetime import date

    from lngarb.cases import evaluate
    from lngarb.freight_anchors import hire_levels

    result = evaluate(inputs)
    return result, reader.breakeven_section(
        result, inputs, day=date(2026, 10, 7), levels=hire_levels(), hire=hire,
        evaluate_at=lambda value: evaluate(replace(inputs, hire_usd_day=value)))


def test_no_route_pays_when_every_breakeven_hire_is_negative(now):
    inputs = _today(now)
    inputs = _today(now, jkm=inputs.ttf - 3.0)
    result, section = _breakeven(inputs, _hire(inputs.hire_usd_day))
    open_east = [l for l in result["east"].values() if l["open"]]
    assert all(l["h_star_usd_day"] < 0 for l in open_east)
    heading = _text(section["heading_segments"])
    assert "no open route east pays more than Gate, not even with a free ship" in heading
    assert "covers" not in heading and "at any hire below" not in heading


def test_a_route_that_never_pays_is_named_apart_from_one_that_does(now):
    from dataclasses import replace

    from lngarb.cases import evaluate

    base = _today(now)
    free = evaluate(replace(base, hire_usd_day=0.0))
    panama, cape = free["east"]["nea_panama"]["s_star"], free["east"]["nea_cape"]["s_star"]
    assert panama < cape
    inputs = _today(now, jkm=base.ttf + (panama + cape) / 2)
    result, section = _breakeven(inputs, _hire(inputs.hire_usd_day))
    assert result["east"]["nea_panama"]["h_star_usd_day"] > 0 > result["east"]["nea_cape"]["h_star_usd_day"]
    heading = _text(section["heading_segments"])
    assert "via Panama pays more than Gate at any hire below" in heading
    assert "via the Cape no hire is low enough, not even a free ship" in heading


def test_the_chart_description_claims_a_reported_hire_only_when_one_is_drawn(now):
    inputs = _today(now)
    _, drawn = _breakeven(inputs, _hire(inputs.hire_usd_day, reported=True))
    _, central = _breakeven(inputs, _hire(45_500.0, reported=False))
    _, off_axis = _breakeven(inputs, _hire(-750.0, reported=True))
    assert drawn["reported"] is not None and "dashed rule" in _text(drawn["desc_segments"])
    assert central["reported"] is None and "dashed rule" not in _text(central["desc_segments"])
    assert off_axis["reported"] is None and "lies off this axis" in _text(off_axis["caption_segments"])


def test_a_positive_des_spread_is_a_premium_a_gate_cargo_earns(now):
    from datetime import date

    from lngarb.cases import WATERFALL_STEPS, evaluate

    inputs = _today(now, delta_nwe=1.29)
    result = evaluate(inputs)
    words = reader.regas_words(inputs.delta_nwe)
    assert words["gate"] == "a cargo sold at Gate earns it"
    cost = reader.cost_section(result, inputs, day=date(2026, 10, 7), steps=WATERFALL_STEPS, delta_observed=True)
    (regas,) = [r for r in cost["rows"] if r["id"] == "regas"]
    assert regas["name"] == "Europe's DES premium, forgone" and regas["value"] < 0
    assert "earns it" in _text(regas["detail_segments"])
    assumed = reader.cost_section(result, inputs, day=date(2026, 10, 7), steps=WATERFALL_STEPS, delta_observed=False)
    (regas,) = [r for r in assumed["rows"] if r["id"] == "regas"]
    assert _text(regas["detail_segments"]).startswith("The parameter table's assumption")
    sentence = _text(reader.verdict(result, date(2026, 10, 7), 1.15, delta_nwe=inputs.delta_nwe,
                                    liquefaction_fee=inputs.liquefaction_fee)["segments"])
    assert "regasification discount" not in sentence


def test_a_week_not_priced_yet_is_named_first(now):
    from datetime import date

    from lngarb import worked

    inputs = _today(now)
    rows = reader.data_dates(
        day=date(2026, 10, 7), week={"series": "wngsr", "alignment": "aligned", "aligned_share": 1.0},
        inputs=inputs, usd_per_eur=worked.usd_per_eur_detail("2026-10-07"),
        hh=worked.henry_hub_detail("2026-10-07"), hire=_hire(45_500.0, reported=False), delta=None,
        delta_window=(date(2026, 10, 1), date(2026, 10, 7)), eua=worked.eua_detail("2026-10-07"),
        rate=worked.overnight_rate_detail("2026-10-07"), fronts={"jkm": date(2026, 11, 1), "ttf": date(2026, 11, 1)},
        eur_mwh=lambda usd: usd, not_priced=[{"week_ending": date(2026, 10, 14), "reason": "no Henry Hub spot price"}])
    assert rows[0]["id"] == "not_priced"
    assert "is not priced yet: no Henry Hub spot price" in _text(rows[0]["segments"])
    assert "Every figure here is for the week to 7 October 2026." in _text(rows[0]["segments"])
    (hire,) = [r for r in rows if r["id"] == "hire"]
    hire_text = _text(hire["segments"])
    assert "no rate was reported within 14 days of 7 October 2026" in hire_text and "days away" in hire_text
    (regas,) = [r for r in rows if r["id"] == "regas_discount"]
    assert "an assumption" in _text(regas["segments"])


def test_provenance_words_hold_no_identifier_and_no_machine_date():
    import re

    provenance = json.loads((DATA / "provenance.json").read_text(encoding="utf-8"))
    for row in provenance["series"]:
        for column in provenance["columns"]:
            if column["id"] in ("series", "source"):
                continue
            words = row[column["id"]]
            assert "_" not in words, (row["id"], column["id"], words)
            assert not re.search(r"\d{4}-\d{2}-\d{2}", words), (row["id"], column["id"], words)
    assert {r["status_words"] for r in provenance["series"]} <= {"checked", "stale", "failed"}


def test_a_plural_step_takes_a_plural_verb():
    assert {"canals", "ports", "carbon"} <= reader.PLURAL_STEPS
    for step in reader.PLURAL_STEPS:
        assert not reader.STEP_SHORT[step].endswith("fee")

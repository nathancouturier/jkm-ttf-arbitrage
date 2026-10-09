"""The calculator's presets: each from the data of its date, nothing typed but Spark's cited days."""

from __future__ import annotations

import json

import pytest

from lngarb import presets
from lngarb.sources import base

DATA = base.REPO_ROOT / "data"


@pytest.fixture(scope="module")
def model():
    return json.loads((DATA / "model.json").read_text(encoding="utf-8"))


def test_the_six_presets_are_there(model):
    assert [p["id"] for p in model["presets"]] == [
        "latest", "april_2020", "october_2022", "march_2024", "march_2026", "spark_example"]
    days = {p["id"]: p["day"] for p in model["presets"]}
    assert days["april_2020"] == "2020-04-15" and days["spark_example"] == "2022-02-09"
    assert days["march_2026"] == "2026-03-25"


def test_the_latest_preset_is_the_now_view_s_week(model):
    now = json.loads((DATA / "now.json").read_text(encoding="utf-8"))
    (latest,) = [p for p in model["presets"] if p["id"] == "latest"]
    assert latest["day"] == now["as_of"]
    for key in ("jkm", "ttf", "delta_nwe", "henry_hub", "hire_usd_day"):
        assert latest["inputs"][key] == now["engine_inputs"][key], key


def test_spark_s_example_carries_its_ship_rate_and_days(model):
    (spark,) = [p for p in model["presets"] if p["id"] == "spark_example"]
    assert spark["inputs"]["vessel"]["capacity_m3"] == 160_000
    assert spark["inputs"]["hire_usd_day"] == -750.0 and spark["missing"] == []
    west = spark["inputs"]["routes"]["nwe_direct"]
    assert west["laden_sea_days"] == presets.SPARK_LADEN_SEA_DAYS
    assert west["ballast_sea_days"] == presets.SPARK_BALLAST_SEA_DAYS
    assert west["flex_days"] == 3.0
    # 12.5 days at sea, a day each to load and discharge and 3 flex days:
    # Spark's 17.5 laden days, read through Spark30's composition.
    assert spark["result"]["west"]["days_laden"] == pytest.approx(17.5)
    assert spark["result"]["west"]["days_ballast"] == pytest.approx(12.5)
    assert "this study's reading" in spark["source_words"]["days"] and "days" in spark["assumed"]


def test_a_figure_the_data_do_not_hold_is_shown_missing_not_filled(model):
    by_id = {p["id"]: p for p in model["presets"]}
    april = by_id["april_2020"]
    assert april["inputs"]["hire_usd_day"] is None
    assert [m["key"] for m in april["missing"]] == ["hire"]
    assert april["source_words"]["hire"].startswith("missing: no reported charter rate within 14 days")
    assert april["result"]["west"]["netback"] is None and april["verdict_segments"] is None
    lead = "".join(s.get("text", s.get("label", "")) for s in april["lead_segments"])
    assert "The data hold no figure of the hire for this date" in lead
    for preset in model["presets"]:
        if preset["id"] != "april_2020":
            assert preset["missing"] == [] and preset["verdict_segments"], preset["id"]
            assert preset["inputs"]["hire_usd_day"] is not None
    levels = model["hire_levels"]
    assert levels["low"] < levels["central"] < levels["high"]


def test_the_lead_names_every_assumption_and_each_field_says_it(model):
    for preset in model["presets"]:
        lead = "".join(s.get("text", s.get("label", "")) for s in preset["lead_segments"])
        assert "Every input below is the data's" not in lead
        for key in preset["assumed"]:
            assert presets.ASSUMPTION_WORDS[key] in lead, (preset["id"], key)
        for key in ("liquefaction_fee", "port_west_usd", "port_east_usd", "spread_bp"):
            assert preset["source_words"][key].startswith("assumption: "), key


def test_no_allowance_price_is_written_as_zero(model):
    """Before 2024 no price is read: null, never zero, and it costs nothing at a share of zero."""
    for preset in model["presets"]:
        if preset["day"] < "2024-01-01":
            assert preset["eua_eur_t"] is None and preset["inputs"]["eua_usd_t"] is None
            assert preset["result"]["west"]["ets_usd"] == 0.0
        else:
            assert preset["eua_eur_t"] > 0


def test_each_ship_s_tolls_are_the_preset_s_for_its_own_ship(model):
    for preset in model["presets"]:
        own = preset["route_tolls"][preset["vessel_key"]]
        for route, tolls in own.items():
            stored = preset["inputs"]["routes"][route]
            if tolls["canal_laden_usd"] is not None:
                assert tolls["canal_laden_usd"] == stored["canal_laden_usd"], (preset["id"], route)
                assert tolls["canal_ballast_usd"] == stored["canal_ballast_usd"], (preset["id"], route)
        other = next(key for key in preset["route_tolls"] if key != preset["vessel_key"])
        assert preset["route_tolls"][other]["nea_panama"]["canal_laden_usd"] != own["nea_panama"]["canal_laden_usd"]


def test_a_ballast_transit_alone_at_panama_pays_the_full_ballast_table_before_2023(model):
    by_id = {p["id"]: p for p in model["presets"]}
    panama = by_id["october_2022"]["route_tolls"]["tfde_160k"]["nea_panama"]
    assert panama["canal_ballast_alone_usd"] > panama["canal_ballast_usd"]
    panama = by_id["march_2026"]["route_tolls"]["two_stroke_174k"]["nea_panama"]
    assert panama["canal_ballast_alone_usd"] == panama["canal_ballast_usd"]


def test_refusal_mirrors_the_page():
    assert presets.refusal("speed_kn", 40.0) == "must lie between 5 and 25"
    assert presets.refusal("speed_kn", float("inf")) == "is too large to use"
    assert presets.refusal("hire_usd_day", float("nan")) is None
    assert presets.refusal("hire_usd_day", -750.0) is None


def test_a_missing_input_on_a_preset_s_date_drops_the_preset_and_says_why(monkeypatch):
    from datetime import date

    from lngarb import export, worked

    real = presets.preset_inputs

    def failing(preset, latest_day):
        if preset.id == "april_2020":
            raise worked.MissingInput("no Henry Hub spot price in April 2020")
        return real(preset, latest_day)

    monkeypatch.setattr(presets, "preset_inputs", failing)
    monkeypatch.setattr(presets, "named_edits", lambda *args: [])
    body = presets.model_document(date(2026, 10, 7), "wngsr", export.inputs_json)
    assert "april_2020" not in [p["id"] for p in body["presets"]]
    assert body["unavailable"] == [{"id": "april_2020", "label": "April 2020",
                                    "why": "no Henry Hub spot price in April 2020"}]


def test_no_source_in_words_holds_a_machine_date(model):
    import re

    for preset in model["presets"]:
        for words in preset["source_words"].values():
            assert not re.search(r"\d{4}-\d{2}-\d{2}", words), words


#: For each named edit, the line it must move and how, against its preset.
MOVES = {
    "a hire of 300,000 $/day": lambda r, b: r["west"]["hire_usd"] > b["west"]["hire_usd"],
    "Panama closed": lambda r, b: not r["east"]["nea_panama"]["open"] and b["east"]["nea_panama"]["open"],
    "laden via Panama, back by the Cape": lambda r, b: r["east"]["nea_panama"]["days_ballast"] > b["east"]["nea_panama"]["days_ballast"],
    "days at sea typed for the Cape": lambda r, b: r["east"]["nea_cape"]["days_total"] == pytest.approx(30.0 + 28.0 + 2.0),
    "TTF in euros at a dollar per euro": lambda r, b: r["spread"] != b["spread"],
    "an allowance of 100 EUR/t, seven tenths surrendered": lambda r, b: r["west"]["ets_usd"] != b["west"]["ets_usd"],
    "the smaller ship at 19.5 knots, with its own tolls": lambda r, b: (
        r["east"]["nea_panama"]["canal_laden_usd"] < b["east"]["nea_panama"]["canal_laden_usd"]
        and r["west"]["days_total"] < b["west"]["days_total"]),
    "Gate's laden days at sea emptied, so taken from the distance": lambda r, b: r["west"]["days_laden"] < b["west"]["days_laden"],
    "a ballast toll typed for Panama, then back by the Cape": lambda r, b: r["east"]["nea_panama"]["canal_ballast_usd"] == 100_000.0,
    "a speed of 40 knots, refused": lambda r, b: r["west"]["days_total"] is None,
    "the Cape back by Suez, which is closed": lambda r, b: not r["east"]["nea_cape"]["open"],
    "the Cape back by Panama, a ballast transit alone": lambda r, b: r["east"]["nea_cape"]["canal_ballast_usd"] > 0,
    # The Cape's ballast leg is Panama's as edited, the twelve days of waiting included.
    "twelve days of waiting at Panama, the Cape back by Panama": lambda r, b: (
        r["east"]["nea_cape"]["days_ballast"] == pytest.approx(r["east"]["nea_panama"]["days_ballast"])
        and r["east"]["nea_panama"]["days_ballast"] == pytest.approx(b["east"]["nea_panama"]["days_ballast"] + 12.0)),
    "every emission surrendered in April 2020, at no price read": lambda r, b: r["west"]["ets_usd"] is None,
    "a new exchange rate and every emission surrendered, with no allowance price read": lambda r, b: r["west"]["ets_usd"] is None,
    "three flex days on the Panama route": lambda r, b: r["east"]["nea_panama"]["days_laden"] == pytest.approx(
        b["east"]["nea_panama"]["days_laden"] + 3.0),
    "the hire left empty": lambda r, b: r["west"]["netback"] is None and b["west"]["netback"] is not None,
    "a hire typed where the data hold none": lambda r, b: r["west"]["netback"] is not None and b["west"]["netback"] is None,
    # Refused, the rate is missing, and with it the allowance in dollars.
    "an exchange rate of zero, refused": lambda r, b: r["west"]["ets_usd"] is None and r["spread"] == b["spread"],
    "the lift test at 120 percent of Henry Hub": lambda r, b: r["lift_margin"] < b["lift_margin"],
    "a fill of 95 percent and two days to load": lambda r, b: (
        r["west"]["q_load_mmbtu"] < b["west"]["q_load_mmbtu"] and r["west"]["days_laden"] == pytest.approx(b["west"]["days_laden"] + 1.0)),
    "22 MMBtu per m3 and 50 MMBtu per tonne": lambda r, b: r["west"]["q_load_mmbtu"] < b["west"]["q_load_mmbtu"],
    "every voyage emission counted and none at berth": lambda r, b: r["west"]["ets_usd"] != b["west"]["ets_usd"],
}


def test_the_named_edits_move_what_they_name(model):
    by_preset = {p["id"]: p for p in model["presets"]}
    assert {c["name"] for c in model["checks"]} == set(MOVES)
    for check in model["checks"]:
        base_result = by_preset[check["preset"]]["result"]
        assert MOVES[check["name"]](check["result"], base_result), check["name"]
    refused = {c["name"]: c["refused"] for c in model["checks"]}
    assert refused["an exchange rate of zero, refused"] == [{"key": "usd_per_eur", "route": None}]


def test_the_named_edits_reach_the_rules_the_page_applies(model):
    checks = {c["name"]: c for c in model["checks"]}
    assert checks["a speed of 40 knots, refused"]["refused"] == [{"key": "speed_kn", "route": None}]
    cape = checks["the Cape back by Suez, which is closed"]["result"]["east"]["nea_cape"]
    assert not cape["open"] and cape["why_closed"] == "back by Suez, which is closed"
    spark = {p["id"]: p for p in model["presets"]}["spark_example"]
    alone = spark["route_tolls"]["tfde_160k"]["nea_panama"]["canal_ballast_alone_usd"]
    cape = checks["the Cape back by Panama, a ballast transit alone"]["result"]["east"]["nea_cape"]
    assert cape["canal_ballast_usd"] == alone
    typed = checks["a ballast toll typed for Panama, then back by the Cape"]["result"]["east"]["nea_panama"]
    assert typed["canal_ballast_usd"] == 100_000.0
    assert checks["every emission surrendered in April 2020, at no price read"]["result"]["west"]["netback"] is None
    unread = checks["a new exchange rate and every emission surrendered, with no allowance price read"]
    assert unread["result"]["west"]["ets_usd"] is None
    emptied = checks["Gate's laden days at sea emptied, so taken from the distance"]["result"]["west"]
    assert emptied["days_laden"] < 17.5 and emptied["netback"] is not None

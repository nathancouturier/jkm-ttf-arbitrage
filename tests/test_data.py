"""The committed data load, are in range and are recent; the refresh reads EIA's page as printed and survives ordinary events."""

import io
import json
from datetime import date

import numpy as np
import pandas as pd
import pytest
import requests

from arb import analysis, build, engine, fetch, note, params
from arb.inputs import Market

DATA = params.DATA
RANGES = {
    "prices_weekly.csv": ("week_ending", {"jkm_usd_mmbtu": (0.5, 150), "ttf_usd_mmbtu": (0.5, 150)}, "2020-09-16"),
    "henry_hub_daily.csv": ("date", {"usd_mmbtu": (0.3, 60)}, "2015-01-02"),
    "usd_per_eur_daily.csv": ("date", {"usd_per_eur": (0.8, 1.7)}, "2015-01-02"),
    "usd_per_sdr_daily.csv": ("date", {"usd_per_sdr": (0.9, 2.0)}, "2015-01-05"),
    "sofr_daily.csv": ("date", {"sofr_percent": (-1, 15)}, "2015-01-02"),
    "des_nwe_acer_daily.csv": ("date", {"nwe_des_eur_mwh": (1, 400), "nwe_spread_to_ttf_eur_mwh": (-40, 20)}, "2023-01-19"),
    "charter_rates.csv": ("date", {"usd_per_day": (-10_000, 500_000)}, "2019-10-10"),
    "us_lng_cargoes_doe.csv": ("date", {"mmcf": (0, 10_000)}, "2016-02-24"),
}


@pytest.mark.parametrize("name", sorted(RANGES))
def test_each_series_loads_in_order_and_in_range(name):
    column, ranges, first = RANGES[name]
    frame = pd.read_csv(DATA / name)
    assert frame[column].iloc[0] == first
    assert frame[column].is_monotonic_increasing
    for value, (low, high) in ranges.items():
        series = frame[value].dropna()
        assert len(series) > 20 and series.between(low, high).all(), value


def test_the_weekly_prices_are_weekly_and_current():
    weeks = pd.to_datetime(pd.read_csv(DATA / "prices_weekly.csv")["week_ending"])
    assert not weeks.duplicated().any() and weeks.is_monotonic_increasing
    assert weeks.iloc[-1] >= pd.Timestamp("2026-11-11")
    # What is pinned is the record as committed: report weeks ending on a Wednesday, whole weeks apart.
    # Weeks to come are only asked to follow in order, so that nothing EIA does later can stop the refresh.
    held = weeks[weeks <= pd.Timestamp("2026-11-11")]
    assert (held.dt.dayofweek == 2).all() and (held.diff().dt.days.dropna() % 7 == 0).all()


def test_every_json_file_parses_and_every_event_and_rate_has_a_source():
    for name in ("params.json", "events.json", "routes.json", "canal_lng_traffic.json"):
        json.loads((DATA / name).read_text())
    events = json.loads((DATA / "events.json").read_text())["events"]
    assert all(e["source"] and e["url"].startswith("https://") for e in events)
    for chart in ("weekly", "monthly"):
        assert sum(1 for e in events if chart in e.get("on", [])) <= 8
    rates = pd.read_csv(DATA / "charter_rates.csv")
    assert rates["publisher"].notna().all() and rates["url"].notna().sum() >= len(rates) - 1


def test_every_date_since_2016_prices_with_no_missing_input():
    market = Market()
    for obs in market.monthly_observations() + market.weekly_observations()[-60:]:
        inputs, meta = market.cargo(obs["date"], obs["jkm"], obs["ttf"], obs["period"])
        out = engine.price_cargo(inputs)
        for route in out["routes"].values():
            assert route["netback"] == route["netback"]         # not a NaN
        assert meta["hire"]["status"] in ("reported", "held", "assumed")


def test_route_status_follows_the_record():
    assert params.route_status("panama", "2016-06-01")["status"] == "closed"
    assert params.route_status("panama", "2023-12-15")["status"] == "restricted"
    assert params.route_status("panama", "2026-11-04")["status"] == "open"
    assert params.route_status("suez", "2023-12-15")["status"] == "open"
    assert params.route_status("suez", "2026-11-04")["status"] == "closed"
    assert params.route_status("cape", "2020-01-01")["status"] == "open"


def test_platts_arbitrage_of_28_april_2026_same_order_similar_gap():
    """Platts put the arb to North Asia at +0.533 via Panama and -0.677 via the Cape, 1.21 apart."""
    platts = params.load()["cross_checks"]["platts_arbitrage_2026_04_28"]
    market = Market()
    obs = next(o for o in market.weekly_observations() if o["date"] == date(2026, 4, 29))
    inputs, _ = market.cargo(obs["date"], obs["jkm"], obs["ttf"])
    routes = engine.price_cargo(inputs)["routes"]
    assert routes["panama"]["arb"] > 0 > routes["cape"]["arb"]      # open via Panama, shut via the Cape, as Platts had it
    gap = routes["panama"]["arb"] - routes["cape"]["arb"]
    theirs = platts["via_panama_usd_mmbtu"] - platts["via_cape_usd_mmbtu"]
    assert 0.5 * theirs < gap < 1.5 * theirs


def test_unknown_destinations_are_counted_under_other():
    market = Market()
    flows = analysis.monthly_flows(market)
    assert (flows["share_jkm"].between(0, 1)).all()
    assert flows.loc["2026-07", "cargoes"] > 100
    new = pd.DataFrame([{"date": pd.Timestamp("2026-07-20"), "tanker": "Test", "port": "Sabine Pass, LA", "country": "Atlantis", "mmcf": 3500.0}])
    market.cargoes = pd.concat([market.cargoes, new], ignore_index=True)
    after = analysis.monthly_flows(market)
    assert after.loc["2026-07", "Other"] == flows.loc["2026-07", "Other"] + 3500.0
    assert after.loc["2026-07", "total"] == pytest.approx(flows.loc["2026-07", "total"] + 3500.0)
    assert after.loc["2026-07", "share_jkm"] < flows.loc["2026-07", "share_jkm"]


def test_the_des_discount_is_measured_against_ttf_over_the_days_the_assessment_covers():
    """The evidence the parameter note states: steadier than ACER's own spread, and no longer following TTF's move."""
    market = Market()
    acer = market.acer.dropna(subset=["nwe_spread_to_ttf_eur_mwh"])
    acer = acer[acer["date"] <= "2026-10-27"]                      # the days the note speaks of; later downloads do not move this test
    ttf = acer["nwe_des_eur_mwh"] - acer["nwe_spread_to_ttf_eur_mwh"]
    move = (ttf - ttf.shift(5)).iloc[5:]
    raw, ours = acer["nwe_spread_to_ttf_eur_mwh"].iloc[5:], market.discount["discount"].iloc[:len(acer)].iloc[5:]
    assert ours.std() < 0.7 * raw.std()
    assert abs(np.corrcoef(ours, move)[0, 1]) < 0.2 < 0.5 < abs(np.corrcoef(raw, move)[0, 1])
    assert ours.median() == pytest.approx(market.p["des_discount"]["before_acer_eur_mwh"]["value"], abs=0.1)


def test_the_refresh_survives_ordinary_events():
    """A skipped EIA week, a destination nobody has listed, no charter rate for half a year and a closed canal:
    the study still builds, and the note and the README still say something true."""
    market = Market()
    market.weekly = market.weekly.drop(market.weekly.index[-2]).reset_index(drop=True)
    new = pd.DataFrame([{"date": market.cargoes["date"].max(), "tanker": "Test", "port": "Sabine Pass, LA", "country": "Atlantis", "mmcf": 3500.0}])
    market.cargoes = pd.concat([market.cargoes, new], ignore_index=True)
    market.rates = market.rates[market.rates["date"] < market.weekly["date"].iloc[-1] - pd.Timedelta(days=200)]
    market.p["route_status"].append({"route": "panama", "from": "2026-09-01", "status": "restricted", "note": "test", "source": "test", "url": None})
    try:
        study = build.build(market, write=False)
    finally:
        market.p["route_status"].pop()                             # the parameters are shared: leave them as they were
    assert study["now"]["preset"]["sources"]["hire"]["status"] == "assumed"
    assert not study["now"]["result"]["routes"]["panama"]["open"]
    words = note.headline(study)
    assert "low scenario" in words["rate"] and "via Panama" not in words["levels"] and "via the Cape" in words["levels"]
    text = note.readme_finding(study)
    assert "None" not in text and "nan" not in text.lower()
    assert len(note.compose(io.BytesIO(), study)) == 2


def test_a_failed_fetch_is_reported_in_plain_words():
    request = requests.Request("GET", "https://markets.newyorkfed.org/api/rates").prepare()
    assert fetch._why(requests.ConnectionError("tunnel refused", request=request)) == "markets.newyorkfed.org could not be reached"
    assert fetch._why(ValueError("2 sentences give an average for JKM")) == "2 sentences give an average for JKM"
    assert fetch._why(requests.exceptions.JSONDecodeError("Expecting value", "<html>", 0), "sofr") == "sofr answered with something that is not the data file"


def test_the_refresh_reads_the_supplement_as_printed():
    bullets = """<ul><li>For the week ending November 4:</li><ul>
      <li>The price at the Title Transfer Facility (TTF) in Europe averaged $31.31/MMBtu, 3 cents higher than the previous week.</li>
      <li>The Japan-Korea Marker (JKM) price averaged $31.99/MMBtu, 32 cents higher than the previous week.</li>
      <li>EU natural gas inventories were 74% full as of November 4.</li></ul></ul>"""
    release = {"release-date": "November 5, 2026", "data-week-ending": "November 4, 2026"}
    row = fetch.parse_supplement(bullets, release)
    assert (row["week_ending"], row["jkm_usd_mmbtu"], row["ttf_usd_mmbtu"]) == ("2026-11-04", 31.99, 31.31)
    with pytest.raises(ValueError):
        fetch.parse_supplement(bullets, {"release-date": "November 13, 2026", "data-week-ending": "November 11, 2026"})
    with pytest.raises(ValueError):
        fetch.parse_supplement(bullets.replace("The Japan-Korea Marker (JKM) price averaged $31.99/MMBtu", "JKM rose"), release)
    with pytest.raises(ValueError, match="no line that begins"):
        fetch.parse_supplement(bullets.replace("For the week ending November 4", "For the two weeks to November 4"), release)
    assert fetch.parse_supplement(bullets.replace("$31.99/MMBtu", "$32/MMBtu"), release)["jkm_usd_mmbtu"] == 32.0


def test_the_site_json_is_complete_and_its_history_recomputes():
    """Nothing blank at default settings, and a level drawn from the stored line is the level the build computed."""
    study = json.loads((params.ROOT / "site" / "data" / "study.json").read_text())
    now = study["now"]
    for row in now["table"]:
        assert all(isinstance(row[k], float) for k in ("sunk", "low", "central", "high", "today", "breakeven_hire"))
    assert study["data_date"] == pd.read_csv(DATA / "prices_weekly.csv")["week_ending"].iloc[-1]
    for series in ("weekly", "monthly"):
        for row in study["history"][series]:
            levels = [a + b * row["hire"] / 1e5 for a, b, status in row["routes"].values() if status == "open"]
            assert row["breakeven"] == pytest.approx(min(levels), abs=1e-4)
    assert len(study["presets"]) == 5 and all(p["inputs"]["hire"] is not None for p in study["presets"])

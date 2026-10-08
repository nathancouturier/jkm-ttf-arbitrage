"""The inputs of a date, read from the committed data; test 12, the EU ETS by year."""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from lngarb import canals, cases, config, worked
from lngarb.sources import base
from lngarb.worked import WORKED_DATES, MissingInput


@pytest.fixture
def sdr_rate(monkeypatch):
    """An SDR rate on every day, so that no test depends on the private series."""
    monkeypatch.setattr(canals, "_usd_per_sdr", lambda day: (1.35, day))


# --------------------------------------------------------------------------
# Test 12: the EU ETS on shipping
# --------------------------------------------------------------------------

@pytest.mark.parametrize("day,phase", [
    (date(2023, 12, 31), 0.0), (date(2024, 1, 1), 0.40), (date(2024, 12, 31), 0.40),
    (date(2025, 6, 30), 0.70), (date(2026, 1, 1), 1.00), (date(2030, 5, 1), 1.00),
])
def test_the_phase_is_zero_before_2024_then_forty_seventy_and_a_hundred_percent(day, phase):
    assert worked.ets_phase(day) == phase


def test_carbon_goes_west_only_with_the_berth_in_full_and_the_voyages_at_half():
    item = next(w for w in WORKED_DATES if w.day == "2024-03-27")
    inputs = worked.inputs_for(item)
    result = cases.evaluate(inputs)
    assert all(lines["ets_usd"] == 0 for lines in result["east"].values())
    west = result["west"]
    tonnes_per_day = inputs.vessel.capacity_m3 * inputs.vessel.fill * inputs.mmbtu_per_m3 \
        * inputs.vessel.boil_off_per_day / inputs.mmbtu_per_t_lng
    laden_sea = west["days_laden"] - inputs.vessel.load_days - inputs.vessel.discharge_days
    weighted = 0.5 * (laden_sea + west["days_ballast"]) + 1.0 * inputs.vessel.discharge_days
    expected = inputs.eua_usd_t * 0.40 * 2.750 * tonnes_per_day * weighted
    assert west["ets_usd"] == pytest.approx(expected, rel=1e-12)


def test_methane_and_nitrous_oxide_count_from_2026():
    assert worked.ets_tco2e_per_t(date(2025, 12, 31)) == 2.750
    assert worked.ets_tco2e_per_t(date(2026, 1, 1)) == pytest.approx(2.750 + 0.00011 * 265, abs=1e-12)
    # With slip, the slipped share leaves CO2 and N2O and counts as methane.
    slipped = worked.ets_tco2e_per_t(date(2026, 1, 1), 0.002)
    assert slipped == pytest.approx(0.998 * 2.750 + 0.002 * 28 + 0.998 * 0.00011 * 265, abs=1e-12)
    assert worked.ets_tco2e_per_t(date(2025, 1, 1), 0.002) == pytest.approx(0.998 * 2.750, abs=1e-12)


def test_the_allowance_price_after_the_last_report_is_the_labelled_assumption():
    german = base.read_cache("dehst_eua_german_auction_monthly").dropna(subset=["eua_eur_t"])
    last = german.iloc[-1]
    after = (last["date"] + pd.DateOffset(months=1)).date()
    value, source = worked.eua_eur_t_in(after)
    assert value == last["eua_eur_t"]
    assert source.startswith("assumption") and "German auctions" in source
    assert last["date"].strftime("%B %Y") in source
    assert config.PARAMETERS["eua_eur_t_after_published"].value == "the last published month"
    value, source = worked.eua_eur_t_in(date(2024, 3, 27))
    assert value == 57.7 and source.startswith("European Commission")
    with pytest.raises(MissingInput):
        worked.eua_eur_t_in(date(2022, 6, 1))


def test_the_german_auctions_follow_the_commission_reports():
    # June 2025 is the Commission's last month; the German average stands in after it.
    value, source = worked.eua_eur_t_in(date(2025, 6, 30))
    assert value == 72.06 and source.startswith("European Commission")
    value, source = worked.eua_eur_t_in(date(2025, 7, 1))
    assert value == 70.01 and source.startswith("German auctions on EEX, July 2025")
    assert "proxy" in source and "EEX, DEHSt" in source
    value, _ = worked.eua_eur_t_in(date(2026, 8, 31))
    assert value == 82.31


# --------------------------------------------------------------------------
# The ship, the routes and the rates on a day
# --------------------------------------------------------------------------

def test_the_ship_changes_on_2_january_2024():
    assert worked.vessel_on(date(2024, 1, 1)).capacity_m3 == 160_000
    assert worked.vessel_on(date(2024, 1, 1)).boil_off_per_day == 0.001
    assert worked.vessel_on(date(2024, 1, 2)).capacity_m3 == 174_000
    assert worked.vessel_on(date(2024, 1, 2)).boil_off_per_day == 0.00085


def test_the_canals_are_offered_by_the_day_of_the_laden_transit(sdr_rate):
    vessel = worked.vessel_on(date(2016, 3, 1))
    laden, ballast = worked.transit_days("nea_panama", vessel)
    assert 3 < laden < 5 and ballast > 40
    laden, ballast = worked.transit_days("nea_suez", vessel)
    assert 16 < laden < 19 and 55 < ballast < 60
    # The expanded locks opened on 26 June 2016: a cargo loading four days
    # before transits that day.
    assert not worked.routes_on(date(2016, 6, 21), vessel)["nea_panama"].open
    assert worked.routes_on(date(2016, 6, 22), vessel)["nea_panama"].open
    # No laden US cargo through Suez from 13 January 2024: a cargo loading on
    # 26 December 2023 transits on 12 January, one loading a day later on 13 January.
    assert worked.routes_on(date(2023, 12, 26), vessel)["nea_suez"].open
    closed = worked.routes_on(date(2023, 12, 27), vessel)["nea_suez"]
    assert not closed.open and "2024-01-13" in closed.why_closed
    assert worked.routes_on(date(2023, 12, 27), vessel)["nea_cape"].open


def test_suez_without_an_sdr_rate_is_shown_and_never_offered(monkeypatch):
    monkeypatch.setattr(canals, "_usd_per_sdr", lambda day: None)
    item = next(w for w in WORKED_DATES if w.day == "2022-10-12")
    inputs = worked.inputs_for(item)
    suez = inputs.routes["nea_suez"]
    assert not suez.open and suez.canal_laden_usd == 0
    result = cases.evaluate(inputs)
    assert result["best_route_east"] != "nea_suez" and result["best_route"] != "nea_suez"


def test_the_overnight_rate_is_effr_before_sofr():
    assert "effective federal funds" in worked.overnight_rate_on(date(2017, 6, 1))[1]
    assert worked.overnight_rate_on(date(2016, 1, 4))[0] == 0.36
    assert "SOFR" in worked.overnight_rate_on(date(2018, 4, 2))[1]


def test_henry_hub_is_the_loading_month_average():
    value, source = worked.henry_hub_month(date(2020, 4, 15))
    assert "21 days in April 2020" in source and "incomplete" not in source
    assert 1.0 < value < 2.5


def test_a_month_the_data_do_not_finish_says_so():
    _, source = worked.henry_hub_month(date(2026, 9, 30))
    assert "an incomplete month: the data end on 2026-09-29" in source


# --------------------------------------------------------------------------
# The worked dates
# --------------------------------------------------------------------------

def test_the_reported_hire_is_the_nearest_within_two_weeks():
    assert worked.nearest_hire(date(2022, 10, 12))[0] == 374_000
    assert worked.nearest_hire(date(2024, 3, 27))[0] == 46_500
    # 2 October 2026 is two days after the week, 18 September twelve days before.
    assert worked.nearest_hire(date(2026, 9, 30))[0] == 31_500
    value, why = worked.nearest_hire(date(2020, 4, 15))
    assert value is None and "within 14 days" in why


def test_every_worked_date_reads_its_prices_and_its_hire():
    for item in WORKED_DATES:
        hire = None if worked.nearest_hire(item.day)[0] is not None else 45_500.0
        inputs = worked.inputs_for(item, hire_usd_day=hire)
        assert inputs.jkm > 0 and inputs.ttf > 0
    october = worked.inputs_for(next(w for w in WORKED_DATES if w.day == "2022-10-12"))
    assert (october.jkm, october.ttf, october.hire_usd_day) == (34.81, 45.83, 374_000.0)
    latest = worked.inputs_for(next(w for w in WORKED_DATES if w.day == "2026-09-30"))
    assert (latest.jkm, latest.ttf, latest.hire_usd_day) == (25.89, 24.18, 31_500.0)


def test_the_wide_regas_discount_is_shown_only_in_its_span():
    assert worked.wide_regas_discount_on("2022-10-12")
    assert not worked.wide_regas_discount_on("2022-03-02")
    assert not worked.wide_regas_discount_on("2022-10-20")


def test_no_parameter_links_a_spark_document():
    for parameter in config.PARAMETERS.values():
        assert parameter.url is None or "sparkcommodities" not in parameter.url, parameter.name


def test_a_date_with_no_reported_hire_asks_for_one():
    april = next(w for w in WORKED_DATES if w.day == "2020-04-15")
    with pytest.raises(MissingInput):
        worked.inputs_for(april)

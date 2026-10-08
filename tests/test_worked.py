"""The inputs of a date, read from the committed data; test 12, the EU ETS by year."""

from __future__ import annotations

from datetime import date

import pytest

from lngarb import cases, worked
from lngarb.worked import WORKED_DATES, MissingInput


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
    value, source = worked.eua_eur_t_in(date(2026, 9, 30))
    assert value == 72.06
    assert source.startswith("assumption")
    value, source = worked.eua_eur_t_in(date(2024, 3, 27))
    assert value == 57.7 and source.startswith("European Commission")
    with pytest.raises(MissingInput):
        worked.eua_eur_t_in(date(2022, 6, 1))


# --------------------------------------------------------------------------
# The ship, the routes and the rates on a day
# --------------------------------------------------------------------------

def test_the_ship_changes_on_2_january_2024():
    assert worked.vessel_on(date(2024, 1, 1)).capacity_m3 == 160_000
    assert worked.vessel_on(date(2024, 1, 1)).boil_off_per_day == 0.001
    assert worked.vessel_on(date(2024, 1, 2)).capacity_m3 == 174_000
    assert worked.vessel_on(date(2024, 1, 2)).boil_off_per_day == 0.00085


def test_panama_opens_in_june_2016_and_suez_closes_after_12_january_2024():
    vessel = worked.vessel_on(date(2016, 3, 1))
    assert not worked.routes_on(date(2016, 3, 1), vessel)["nea_panama"].open
    assert worked.routes_on(date(2016, 7, 1), vessel)["nea_panama"].open
    assert worked.routes_on(date(2024, 1, 12), vessel)["nea_suez"].open
    assert not worked.routes_on(date(2024, 1, 13), vessel)["nea_suez"].open
    assert worked.routes_on(date(2024, 1, 13), vessel)["nea_cape"].open


def test_the_overnight_rate_is_effr_before_sofr():
    assert "effective federal funds" in worked.overnight_rate_on(date(2017, 6, 1))[1]
    assert worked.overnight_rate_on(date(2016, 1, 4))[0] == 0.36
    assert "SOFR" in worked.overnight_rate_on(date(2018, 4, 2))[1]


def test_henry_hub_is_the_loading_month_average():
    value, source = worked.henry_hub_month(date(2020, 4, 15))
    assert "21 days in April 2020" in source
    assert 1.0 < value < 2.5


# --------------------------------------------------------------------------
# The worked dates
# --------------------------------------------------------------------------

def test_every_worked_date_reads_its_prices_and_its_hire():
    for item in WORKED_DATES:
        hire = None if item.hire_month else 38_000.0
        inputs = worked.inputs_for(item, hire_usd_day=hire)
        assert inputs.jkm > 0 and inputs.ttf > 0
    october = worked.inputs_for(next(w for w in WORKED_DATES if w.day == "2022-10-12"))
    assert (october.jkm, october.ttf, october.hire_usd_day) == (34.81, 45.83, 374_000.0)
    latest = worked.inputs_for(next(w for w in WORKED_DATES if w.day == "2026-09-30"))
    assert (latest.jkm, latest.ttf, latest.hire_usd_day) == (25.89, 24.18, 31_500.0)


def test_a_date_with_no_reported_hire_asks_for_one():
    april = next(w for w in WORKED_DATES if w.day == "2020-04-15")
    with pytest.raises(MissingInput):
        worked.inputs_for(april)

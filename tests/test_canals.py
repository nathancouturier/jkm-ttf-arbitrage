"""Canal tolls from the authorities' tables, reproduced for known ships and dates."""

from __future__ import annotations

import pytest

from lngarb import canals, config


@pytest.mark.parametrize(
    "when, laden, ballast",
    [
        ("2016-07-25", 382_440, 336_540),
        ("2018-06-01", 439_800, 386_880),
        ("2021-01-31", 476_760, 421_800),
        ("2023-06-01", 534_900, 454_665),
        ("2024-06-01", 595_800, 506_430),
        ("2025-01-01", 656_700, 558_195),
        ("2026-09-30", 656_700, 558_195),
    ],
)
def test_the_toll_for_174000_m3_in_each_period(when, laden, ballast):
    assert canals.panama_toll(when, 174_000, laden=True) == pytest.approx(laden, abs=0.005)
    assert canals.panama_toll(when, 174_000, laden=False) == pytest.approx(ballast, abs=0.005)


def test_the_authority_s_2016_worked_example_and_the_roundtrip_ballast_table():
    # The Authority's own example of April 2016 gives 382,440.00 laden and
    # 336,540.00 in ballast for 174,000 m3; the roundtrip table gives less.
    assert canals.panama_toll("2016-04-01", 174_000, laden=False, roundtrip_ballast=True) == pytest.approx(301_500)
    assert canals.panama_toll("2023-06-01", 174_000, laden=False, roundtrip_ballast=True) == pytest.approx(454_665)


def test_160000_m3_and_the_days_before_the_first_table():
    assert canals.panama_toll("2025-03-01", 160_000, laden=True) == pytest.approx(628_000)
    assert canals.panama_toll("2025-03-01", 160_000, laden=False) == pytest.approx(533_800)
    assert canals.panama_toll("2016-03-31", 174_000, laden=True) is None


def test_the_fresh_water_surcharge_starts_on_15_february_2020():
    assert canals.panama_fresh_water_surcharge("2020-02-14", 476_760) == 0.0
    assert canals.panama_fresh_water_surcharge("2025-06-01", 656_700, variable_share=0.10) == pytest.approx(75_670)
    assert canals.panama_fresh_water_surcharge("2025-06-01", 656_700, variable_share=0.0) == pytest.approx(10_000)


# --------------------------------------------------------------------------
# Suez
# --------------------------------------------------------------------------

@pytest.mark.parametrize("scnt,laden,normal,net", [
    # The schedule of 15 January 2024 with the surcharge of 19 percent and the
    # rebate of 75 percent on normal dues only, at three tonnages.
    (85_000, True, 494_350, 217_514), (85_000, False, 420_000, 184_800),
    (108_606, True, 607_659, 267_370), (108_606, False, 516_312, 227_177),
    (112_148, True, 624_660, 274_851), (112_148, False, 530_764, 233_536),
])
def test_the_suez_toll_in_sdr_after_15_july_2026(scnt, laden, normal, net):
    toll = canals.suez_toll_sdr("2026-07-20", scnt, laden=laden)
    assert round(toll["normal_sdr"]) == normal
    assert round(toll["toll_sdr"]) == net


def test_the_surcharge_rebate_and_reduction_follow_their_dates():
    assert canals.suez_rate_on(config.SUEZ_LNG_SURCHARGE, "2022-02-28")[0] == 0.0
    assert canals.suez_rate_on(config.SUEZ_LNG_SURCHARGE, "2022-03-01")[0] == 0.07
    assert canals.suez_rate_on(config.SUEZ_LNG_SURCHARGE, "2026-07-15")[0] == 0.19
    assert canals.suez_rate_on(config.SUEZ_US_GULF_JAPAN_REBATE, "2017-09-30")[0] == 0.0
    assert canals.suez_rate_on(config.SUEZ_US_GULF_JAPAN_REBATE, "2020-04-15")[0] == 0.75
    assert canals.suez_rate_on(config.SUEZ_US_GULF_JAPAN_REBATE, "2022-10-12")[0] == 0.70
    assert canals.suez_rate_on(config.SUEZ_US_GULF_JAPAN_REBATE, "2023-07-01")[0] == 0.75
    # October 2022: the rebate of 70 percent, the surcharge of 7, no general reduction.
    toll = canals.suez_toll_sdr("2022-10-12", 100_000, laden=True)
    assert toll["toll_sdr"] == pytest.approx(toll["normal_sdr"] * (1 + 0.07 - 0.70), rel=1e-12)


def test_a_day_no_schedule_covers_is_not_priced(monkeypatch):
    # With a rate held, only the missing schedule can leave the toll unpriced.
    monkeypatch.setattr(canals, "_usd_per_sdr", lambda day: (1.4, day))
    assert canals.suez_toll_sdr("2015-04-30", 100_000, laden=True) is None
    assert canals.suez_round_trip("2015-04-30", 174_000) is None
    assert canals.suez_round_trip("2015-05-01", 174_000) is not None


def test_the_other_reading_takes_the_rebate_off_the_surcharge_too():
    plain = canals.suez_toll_sdr("2026-07-20", 100_000, laden=True)
    other = canals.suez_toll_sdr("2026-07-20", 100_000, laden=True, rebate_on_surcharge=True)
    assert other["toll_sdr"] == pytest.approx(plain["normal_sdr"] * 1.19 * 0.25, rel=1e-12)
    assert plain["toll_sdr"] - other["toll_sdr"] == pytest.approx(plain["normal_sdr"] * 0.19 * 0.75, rel=1e-12)


def test_each_transit_is_priced_on_its_own_day(monkeypatch):
    monkeypatch.setattr(canals, "_usd_per_sdr", lambda day: (1.0 if day.year == 2022 else 2.0, day))
    laden, ballast, note = canals.suez_transits("2022-12-20", "2023-01-30", 174_000)
    assert laden == pytest.approx(canals.suez_toll_sdr("2022-12-20", 102_000, laden=True)["toll_sdr"], rel=1e-12)
    assert ballast == pytest.approx(2.0 * canals.suez_toll_sdr("2023-01-30", 102_000, laden=False)["toll_sdr"], rel=1e-12)


def test_the_schedule_of_2023_is_the_one_before_raised_fifteen_percent():
    before = canals.suez_schedule("2022-12-31")
    after = canals.suez_schedule("2023-01-01")
    for old, new in zip(before.laden + before.ballast, after.laden + after.ballast):
        assert abs(new - 1.15 * old) <= 0.01
    assert canals.suez_schedule("2016-06-01") is before
    assert canals.suez_schedule("2024-01-15").laden[0] == 10.42


def test_in_april_2020_the_route_rebate_replaces_the_larger_general_reduction():
    assert canals.suez_rate_on(config.SUEZ_LNG_GENERAL_REDUCTION, "2020-04-15")[0] == 0.30
    assert canals.suez_rate_on(config.SUEZ_LNG_GENERAL_REDUCTION, "2020-07-01")[0] == 0.25
    toll = canals.suez_toll_sdr("2020-04-15", 100_000, laden=True)
    assert toll["toll_sdr"] == pytest.approx(toll["normal_sdr"] * (1 - 0.75), rel=1e-12)
    assert "periodical of 31 March 2020" in toll["rebate"]
    assert "periodical of 18 December 2022" in canals.suez_toll_sdr("2023-03-01", 100_000, laden=True)["rebate"]
    # Before the route rebate began, only the general reduction applies.
    early = canals.suez_toll_sdr("2017-06-01", 100_000, laden=True)
    assert early["toll_sdr"] == pytest.approx(early["normal_sdr"] * 0.75, rel=1e-12)


def test_the_round_trip_is_converted_at_the_rate_of_the_day(monkeypatch):
    monkeypatch.setattr(canals, "_usd_per_sdr", lambda day: (1.25, day))
    laden, ballast, note = canals.suez_round_trip("2022-10-12", 145_000)
    expected = canals.suez_toll_sdr("2022-10-12", 85_000, laden=True)["toll_sdr"] * 1.25
    assert laden == pytest.approx(expected, rel=1e-12)
    assert "85,000 SCNT" in note and "1.25 USD per SDR" in note


def test_without_an_sdr_rate_suez_is_not_priced(monkeypatch):
    monkeypatch.setattr(canals, "_usd_per_sdr", lambda day: None)
    assert canals.suez_round_trip("2022-10-12", 160_000) is None

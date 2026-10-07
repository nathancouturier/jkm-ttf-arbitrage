"""Canal tolls from the authorities' tables, reproduced for known ships and dates."""

from __future__ import annotations

import pytest

from lngarb import canals


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

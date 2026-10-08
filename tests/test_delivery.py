"""Test 13: the delivery months a front-month JKM and TTF name, and the weekly tag."""

from __future__ import annotations

from datetime import date

from lngarb import delivery


def test_18_september_2026_gives_november_against_october():
    day = date(2026, 9, 18)
    assert delivery.jkm_front_month(day) == date(2026, 11, 1)
    assert delivery.ttf_front_month(day) == date(2026, 10, 1)
    assert not delivery.aligned_on(day)


def test_the_two_agree_from_the_1st_to_the_15th():
    for d in range(1, 16):
        day = date(2026, 9, d)
        if delivery.is_business_day(day):
            assert delivery.aligned_on(day), day


def test_the_two_disagree_from_the_16th_until_the_ttf_expiry_then_agree_again():
    # October 2026 TTF futures expire two business days before 1 October 2026, a
    # Thursday: on Tuesday 29 September.
    assert delivery.ttf_expiry(date(2026, 10, 1)) == date(2026, 9, 29)
    for d in range(16, 30):
        day = date(2026, 9, d)
        if delivery.is_business_day(day):
            assert not delivery.aligned_on(day), day
    assert delivery.aligned_on(date(2026, 9, 30))
    assert delivery.ttf_front_month(date(2026, 9, 30)) == date(2026, 11, 1)


def test_the_jkm_roll_moves_to_the_next_business_day_when_the_16th_is_not_one():
    # 16 May 2026 is a Saturday: the roll is on Monday 18 May.
    assert delivery.jkm_roll_day(date(2026, 5, 1)) == date(2026, 5, 18)
    assert delivery.jkm_front_month(date(2026, 5, 15)) == date(2026, 6, 1)
    assert delivery.jkm_front_month(date(2026, 5, 18)) == date(2026, 7, 1)


def test_a_holiday_moves_the_ttf_expiry_back():
    plain = delivery.ttf_expiry(date(2026, 1, 1))
    assert plain == date(2025, 12, 30)
    assert delivery.ttf_expiry(date(2026, 1, 1), holidays=[date(2025, 12, 30)]) == date(2025, 12, 29)


def test_weeks_are_tagged_by_the_share_of_their_trading_days():
    # Thursday 3 to Wednesday 9 September 2026: all before the 16th.
    assert delivery.week_alignment(date(2026, 9, 9)) == ("aligned", 1.0)
    # Thursday 17 to Wednesday 23 September 2026: all between the roll and the expiry.
    assert delivery.week_alignment(date(2026, 9, 23)) == ("misaligned", 0.0)
    # Thursday 10 to Wednesday 16 September 2026: four days before the roll, one on it.
    tag, share = delivery.week_alignment(date(2026, 9, 16))
    assert tag == "mixed" and share == 0.8

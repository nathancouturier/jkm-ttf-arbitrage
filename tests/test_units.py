"""Test 1, units. Written before any other test or module in this repository.

30 EUR/MWh at 1.10 USD per EUR is 9.671344 USD/MMBtu. A wrong conversion factor,
or an exchange rate passed the wrong way up, is the most common error in a
study that compares TTF with JKM, and this is the test that catches both.
"""

from __future__ import annotations

import math

from lngarb import units


def test_30_eur_mwh_at_1_10_is_9_671344_usd_mmbtu():
    assert round(units.eur_mwh_to_usd_mmbtu(30.0, 1.10), 6) == 9.671344


def test_the_factor_is_the_rounded_nist_value():
    """3.412142 is 3.6e9 J over 1,055.05585262 J per Btu, rounded to six places.

    The test above depends on the rounding: with the unrounded factor the same
    price is 9.671345. Pinning the constant here means a change to it fails by
    name instead of as a mystery in the sixth decimal.
    """
    joules_per_btu_it = 2326.0 * 0.45359237
    exact = 3.6e9 / (joules_per_btu_it * 1e6)
    assert units.MMBTU_PER_MWH == 3.412142
    assert round(exact, 6) == units.MMBTU_PER_MWH


def test_an_inverted_exchange_rate_gives_a_different_answer():
    """Passing EUR per USD instead of USD per EUR must not go unnoticed."""
    right = units.eur_mwh_to_usd_mmbtu(30.0, 1.10)
    wrong = units.eur_mwh_to_usd_mmbtu(30.0, 1.0 / 1.10)
    assert abs(right - wrong) > 1.0


def test_the_two_directions_round_trip():
    for eur_mwh in (0.0, 4.5, 30.0, 339.2):
        for rate in (0.83, 1.10, 1.60):
            back = units.usd_mmbtu_to_eur_mwh(units.eur_mwh_to_usd_mmbtu(eur_mwh, rate), rate)
            assert math.isclose(back, eur_mwh, rel_tol=0, abs_tol=1e-12)

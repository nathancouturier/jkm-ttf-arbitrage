"""Unit conversions. The only place in the pipeline where a price changes unit.

TTF is quoted in euros per megawatt hour. JKM and Henry Hub are quoted in US
dollars per million British thermal units. All three are on a gross calorific
value basis, so converting between them is a change of energy unit and currency
and nothing else. Every conversion goes through eur_mwh_to_usd_mmbtu, so a wrong
factor can only be wrong in one place, and tests/test_units.py pins that place.

The energy factor
-----------------
One megawatt hour is 3.6e9 joules. One British thermal unit (International
Table) is 2,326 J/kg times 0.45359237 kg, which is 1,055.05585262 J exactly
(NIST Special Publication 811, appendix B.9, both factors exact). One MWh is
therefore 3.41214163 MMBtu. This study uses 3.412142, rounded to six decimal
places. The rounding moves a price by about one part in ten million, far below
the second decimal a gas price is quoted to, and it is stated here rather than
hidden.

    https://www.nist.gov/pml/special-publication-811/nist-guide-si-appendix-b-conversion-factors/nist-guide-si-appendix-b9
"""

from __future__ import annotations

__all__ = ["MMBTU_PER_MWH", "eur_mwh_to_usd_mmbtu", "usd_mmbtu_to_eur_mwh"]

#: MMBtu in one MWh, gross calorific value on both sides. See the module
#: docstring for the derivation and the rounding.
MMBTU_PER_MWH: float = 3.412142


def eur_mwh_to_usd_mmbtu(eur_mwh: float, usd_per_eur: float) -> float:
    """A price in EUR/MWh expressed in USD/MMBtu.

    usd_per_eur is the exchange rate quoted as US dollars per euro, the way the
    Federal Reserve Board's H.10 release quotes it. Passing the rate the other
    way up is the most common error in this study, so the argument is named for
    its direction.
    """
    return eur_mwh * usd_per_eur / MMBTU_PER_MWH


def usd_mmbtu_to_eur_mwh(usd_mmbtu: float, usd_per_eur: float) -> float:
    """The inverse of eur_mwh_to_usd_mmbtu, for showing TTF as a desk quotes it."""
    return usd_mmbtu * MMBTU_PER_MWH / usd_per_eur

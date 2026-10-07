"""Canal charges for an LNG carrier, from the canal authorities' own tables.

The tables, their periods and their sources are in lngarb.config
(PANAMA_TOLLS and the Suez tables). This module only applies them to a ship
and a date. docs/methodology.md, sections 6 and 8, describes both canals.
"""

from __future__ import annotations

from datetime import date

from . import config
from .config import PANAMA_BAND_SIZES_M3, PANAMA_TOLLS, PanamaTollPeriod

__all__ = ["panama_period", "panama_toll", "panama_fresh_water_surcharge"]


def _as_date(when: date | str) -> date:
    return when if isinstance(when, date) else date.fromisoformat(str(when)[:10])


def panama_period(when: date | str) -> PanamaTollPeriod | None:
    """The toll period in force on a day, or None before the first one read."""
    day = _as_date(when)
    for period in PANAMA_TOLLS:
        start = date.fromisoformat(period.start)
        end = date.fromisoformat(period.end) if period.end else None
        if day >= start and (end is None or day <= end):
            return period
    return None


def _banded(capacity_m3: float, rates: tuple[float, ...]) -> float:
    toll, left = 0.0, capacity_m3
    for size, rate in zip(PANAMA_BAND_SIZES_M3, rates):
        step = min(left, size)
        toll += step * rate
        left -= step
    return toll + max(left, 0.0) * rates[len(PANAMA_BAND_SIZES_M3)]


def panama_toll(when: date | str, capacity_m3: float, *, laden: bool, roundtrip_ballast: bool = False) -> float | None:
    """The toll in USD for one transit of a neopanamax LNG carrier, or None when no table covers the day.

    roundtrip_ballast applies the lower ballast table of 2016 to 2022 to a ship
    returning through the canal in ballast within 60 days; from 2023 there is no
    such table and the flag has no effect.
    """
    period = panama_period(when)
    if period is None:
        return None
    if period.laden_bands:
        if laden:
            return _banded(capacity_m3, period.laden_bands)
        table = period.roundtrip_bands if roundtrip_ballast else period.ballast_bands
        return _banded(capacity_m3, table)
    laden_toll = period.fixed_usd + period.rate_usd_m3 * capacity_m3
    return laden_toll if laden else laden_toll * period.ballast_share


def panama_fresh_water_surcharge(when: date | str, toll_usd: float, *, variable_share: float | None = None) -> float:
    """The fresh water surcharge on one transit, USD: zero before 15 February 2020.

    The fixed part per transit plus a share of the tolls; the share is a
    parameter, since the daily lake level that sets it is not collected.
    """
    if _as_date(when) < date(2020, 2, 15):
        return 0.0
    share = config.PARAMETERS["panama_fresh_water_variable_share"].value if variable_share is None else variable_share
    return config.PARAMETERS["panama_fresh_water_fixed_usd"].value + share * toll_usd

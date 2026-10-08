"""Canal charges for an LNG carrier, from the canal authorities' own tables.

The tables, their periods and their sources are in lngarb.config
(PANAMA_TOLLS and the Suez tables). This module only applies them to a ship
and a date. docs/methodology.md, sections 6 and 8, describes both canals.
"""

from __future__ import annotations

from datetime import date

from . import config
from .config import (
    PANAMA_BAND_SIZES_M3,
    PANAMA_TOLLS,
    SUEZ_BAND_SIZES_SCNT,
    SUEZ_LNG_GENERAL_REDUCTION,
    SUEZ_LNG_SURCHARGE,
    SUEZ_SCHEDULES,
    SUEZ_US_GULF_JAPAN_REBATE,
    SUEZ_US_GULF_JAPAN_REBATE_END,
    PanamaTollPeriod,
    SuezSchedule,
)

__all__ = ["panama_period", "panama_toll", "panama_fresh_water_surcharge", "suez_schedule", "suez_rate_on",
           "suez_toll_sdr", "suez_round_trip"]


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


# --------------------------------------------------------------------------
# Suez
# --------------------------------------------------------------------------

def suez_schedule(when: date | str) -> SuezSchedule | None:
    """The normal dues schedule in force on a day, or None where none has been read."""
    day = _as_date(when)
    for schedule in SUEZ_SCHEDULES:
        start = date.fromisoformat(schedule.start)
        end = date.fromisoformat(schedule.end) if schedule.end else None
        if day >= start and (end is None or day <= end):
            return schedule
    return None


def suez_rate_on(table: tuple[tuple[str, float, str], ...], when: date | str) -> tuple[float, str]:
    """The rate of a dated table in force on a day, and its instrument; zero before the first."""
    day = _as_date(when)
    rate, instrument = 0.0, ""
    for start, value, name in table:
        if day >= date.fromisoformat(start):
            rate, instrument = value, name
    return rate, instrument


def suez_toll_sdr(when: date | str, scnt: float, *, laden: bool) -> dict | None:
    """One transit's Suez toll in SDR for an LNG carrier from the US Gulf to Japan, line by line.

    normal dues by band; the surcharge on normal dues, paid in full (open question
    26); the rebate for the US Gulf to Japan on normal dues, which cannot be
    combined with the general reduction, so the larger of the two is taken.
    None where no schedule covers the day.
    """
    schedule = suez_schedule(when)
    if schedule is None:
        return None
    rates = schedule.laden if laden else schedule.ballast
    normal, left = 0.0, scnt
    for size, rate in zip(SUEZ_BAND_SIZES_SCNT, rates):
        step = min(left, size)
        normal += step * rate
        left -= step
    normal += max(left, 0.0) * rates[len(SUEZ_BAND_SIZES_SCNT)]
    surcharge, surcharge_from = suez_rate_on(SUEZ_LNG_SURCHARGE, when)
    general, general_from = suez_rate_on(SUEZ_LNG_GENERAL_REDUCTION, when)
    route, route_from = suez_rate_on(SUEZ_US_GULF_JAPAN_REBATE, when)
    if _as_date(when) > date.fromisoformat(SUEZ_US_GULF_JAPAN_REBATE_END):
        route, route_from = 0.0, "no rebate text covers the day"
    rebate, rebate_from = (route, route_from) if route >= general else (general, general_from)
    return {
        "normal_sdr": normal,
        "surcharge_sdr": normal * surcharge,
        "rebate_sdr": normal * rebate,
        "toll_sdr": normal * (1.0 + surcharge - rebate),
        "schedule": schedule.source,
        "surcharge": "%s percent, %s" % (round(surcharge * 100, 1), surcharge_from or "none"),
        "rebate": "%s percent, %s" % (round(rebate * 100, 1), rebate_from or "none"),
    }


def _usd_per_sdr(day: date) -> tuple[float, date] | None:
    from .sources.base import read_cache

    frame = read_cache("imf_usd_per_sdr_daily", directory="private")
    if frame is None:
        return None
    import pandas as pd

    rows = frame[(frame["date"] <= pd.Timestamp(day)) & frame["usd_per_sdr"].notna()]
    if rows.empty:
        return None
    return float(rows.iloc[-1]["usd_per_sdr"]), rows.iloc[-1]["date"].date()


def suez_round_trip(when: date | str, capacity_m3: float, *, scnt: float | None = None) -> tuple[float, float, str] | None:
    """Laden and ballast Suez tolls in USD for a round trip through the canal, and what they are made of.

    None where no schedule covers the day or no SDR rate is held: the route is
    then shown without a toll and flagged, never priced at zero.
    """
    day = _as_date(when)
    if scnt is None:
        scnt = config.PARAMETERS["suez_scnt_per_m3"].value * capacity_m3
    laden = suez_toll_sdr(day, scnt, laden=True)
    ballast = suez_toll_sdr(day, scnt, laden=False)
    rate = _usd_per_sdr(day)
    if laden is None or ballast is None or rate is None:
        return None
    usd_per_sdr, seen = rate
    note = (
        "Suez toll for %s SCNT, %s; surcharge %s; rebate %s; laden %s SDR and ballast %s SDR at %s "
        "USD per SDR of %s (IMF, through the Bundesbank)" % (
            format(scnt, ",.0f"), laden["schedule"], laden["surcharge"], laden["rebate"],
            format(laden["toll_sdr"], ",.0f"), format(ballast["toll_sdr"], ",.0f"), usd_per_sdr, seen))
    return laden["toll_sdr"] * usd_per_sdr, ballast["toll_sdr"] * usd_per_sdr, note


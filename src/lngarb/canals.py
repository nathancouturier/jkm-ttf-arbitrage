"""Canal charges for an LNG carrier, from the canal authorities' own tables.

The tables, their periods and their sources are in lngarb.config
(PANAMA_TOLLS and the Suez tables). This module only applies them to a ship
and a date. docs/methodology.md, sections 6 and 8, describes both canals.
"""

from __future__ import annotations

import math

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from datetime import date, timedelta

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

__all__ = ["panama_period", "panama_toll", "panama_fresh_water_surcharge", "panama_fresh_water_share_at_level",
           "gatun_levels", "gatun_levels_held",
           "suez_schedule", "suez_rate_on",
           "suez_toll_sdr", "suez_round_trip", "suez_transits"]


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


def panama_fresh_water_share_at_level(level_ft: float, when: date | str) -> float | None:
    """The variable share of tolls the Authority's curve gives at a lake level on a day, or None before the surcharge.

    The Authority's curve, max / (1 + e^(slope (level - centre))), with the
    centre of the day: 82.0 feet from 15 February 2020, 79.0 from 1 October
    2023, and the share held between 1 and 10 percent to September 2023, 0
    and 10 since. The level is rounded to a tenth of a foot, as the Authority
    reads it at noon the day before a transit.
    """
    day = _as_date(when)
    centres = config.PARAMETERS["panama_fresh_water_curve_centre_ft"].value
    starts = sorted(centres)
    if day < date.fromisoformat(starts[0]):
        return None
    centre = centres[max(s for s in starts if date.fromisoformat(s) <= day)]
    slope = config.PARAMETERS["panama_fresh_water_curve_slope_per_ft"].value
    top = config.PARAMETERS["panama_fresh_water_curve_max_share"].value
    floor = config.PARAMETERS["panama_fresh_water_min_share_to_sep_2023"].value if day < date.fromisoformat(starts[-1]) else 0.0
    share = top / (1.0 + math.exp(slope * (round(level_ft, 1) - centre)))
    return min(top, max(floor, share))


#: The owner's daily Gatun Lake levels, day to feet, held only inside gatun_levels().
_GATUN_LEVELS: dict[date, float] = {}


@contextmanager
def gatun_levels(levels: Mapping[date | str, float]) -> Iterator[None]:
    """Within the block, price the fresh water surcharge at the lake level of each transit.

    For a private run only: the levels are the owner's series, which stays in
    data/private/ until open question 54 is settled, and lngarb.export refuses
    to write the site while levels are held. A transit whose level is missing
    keeps the 5 percent assumption.
    """
    held = {_as_date(day): float(level) for day, level in levels.items() if level == level}
    if _GATUN_LEVELS:
        raise RuntimeError("Gatun Lake levels are already held")
    _GATUN_LEVELS.update(held)
    try:
        yield
    finally:
        _GATUN_LEVELS.clear()


def gatun_levels_held() -> bool:
    """True inside gatun_levels(), with at least one level held."""
    return bool(_GATUN_LEVELS)


def panama_fresh_water_surcharge(when: date | str, toll_usd: float, *, variable_share: float | None = None) -> float:
    """The fresh water surcharge on one transit, USD: zero before 15 February 2020.

    The fixed part per transit plus a share of the tolls. The share is the
    parameter, 5 percent, unless a private run holds the lake's levels
    (gatun_levels): then it is the Authority's curve at the level of the day
    before the transit, the Authority reading it at noon that day, and the
    parameter where that day's level is missing.
    """
    day = _as_date(when)
    if day < date(2020, 2, 15):
        return 0.0
    share = variable_share
    if share is None and _GATUN_LEVELS:
        level = _GATUN_LEVELS.get(day - timedelta(days=1))
        share = None if level is None else panama_fresh_water_share_at_level(level, day)
    if share is None:
        share = config.PARAMETERS["panama_fresh_water_variable_share"].value
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


def suez_toll_sdr(when: date | str, scnt: float, *, laden: bool, rebate_on_surcharge: bool = False) -> dict | None:
    """One transit's Suez toll in SDR for an LNG carrier from the US Gulf to Japan, line by line.

    normal dues by band; the surcharge on normal dues, paid in full (open question
    26), or with rebate_on_surcharge, reduced by the rebate too, the other
    reading; the rebate for the US Gulf to Japan on normal dues, which cannot be
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
    rebated = normal * (1.0 + surcharge) if rebate_on_surcharge else normal
    return {
        "normal_sdr": normal,
        "surcharge_sdr": normal * surcharge,
        "rebate_sdr": rebated * rebate,
        "toll_sdr": normal * (1.0 + surcharge) - rebated * rebate,
        "schedule": schedule.source,
        "surcharge": "%s percent, %s" % (round(surcharge * 100, 1), surcharge_from or "none"),
        "rebate": "%s percent, %s" % (round(rebate * 100, 1), rebate_from or "none"),
    }


def _usd_per_sdr(day: date) -> tuple[float, date] | None:
    from .sources.base import read_cache

    frame = read_cache("imf_usd_per_sdr_daily")
    if frame is None:
        return None
    import pandas as pd

    rows = frame[(frame["date"] <= pd.Timestamp(day)) & frame["usd_per_sdr"].notna()]
    if rows.empty:
        return None
    return float(rows.iloc[-1]["usd_per_sdr"]), rows.iloc[-1]["date"].date()


def suez_transits(laden_day: date | str, ballast_day: date | str, capacity_m3: float, *, scnt: float | None = None,
                  rebate_on_surcharge: bool = False) -> tuple[float, float, str] | None:
    """Laden and ballast Suez tolls in USD, each priced on its own transit day, and what they are made of.

    Each transit takes the schedule, surcharge, rebate and SDR rate of its day.
    None where no schedule covers a day or no SDR rate is held: the route is
    then not offered, never priced at zero.
    """
    laden_day, ballast_day = _as_date(laden_day), _as_date(ballast_day)
    if scnt is None:
        scnt = config.PARAMETERS["suez_scnt_per_m3"].value * capacity_m3
    laden = suez_toll_sdr(laden_day, scnt, laden=True, rebate_on_surcharge=rebate_on_surcharge)
    ballast = suez_toll_sdr(ballast_day, scnt, laden=False, rebate_on_surcharge=rebate_on_surcharge)
    laden_rate, ballast_rate = _usd_per_sdr(laden_day), _usd_per_sdr(ballast_day)
    if laden is None or ballast is None or laden_rate is None or ballast_rate is None:
        return None
    note = (
        "Suez toll for %s SCNT%s. Laden transit %s: %s; surcharge %s; rebate %s; %s SDR at %s USD per "
        "SDR of %s. Ballast transit %s: surcharge %s; rebate %s; %s SDR at %s USD per SDR of %s. SDR "
        "rates of the IMF, through the Bundesbank" % (
            format(scnt, ",.0f"), ", the rebate also on the surcharge" if rebate_on_surcharge else "",
            laden_day, laden["schedule"], laden["surcharge"], laden["rebate"], format(laden["toll_sdr"], ",.0f"),
            laden_rate[0], laden_rate[1], ballast_day, ballast["surcharge"], ballast["rebate"],
            format(ballast["toll_sdr"], ",.0f"), ballast_rate[0], ballast_rate[1]))
    return laden["toll_sdr"] * laden_rate[0], ballast["toll_sdr"] * ballast_rate[0], note


def suez_round_trip(when: date | str, capacity_m3: float, *, scnt: float | None = None) -> tuple[float, float, str] | None:
    """Laden and ballast Suez tolls in USD with both transits priced on one day; see suez_transits."""
    return suez_transits(when, when, capacity_m3, scnt=scnt)


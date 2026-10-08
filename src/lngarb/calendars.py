"""Business day calendars for the exchanges whose expiry rules the study applies.

ICE Endex's Dutch TTF futures stop trading "two UK Business Days prior to the
first calendar day of the delivery month", and ICE Futures Europe's JKM futures
on the 15th of the month before, or the preceding business day. Both are London
markets, so both count UK business days: weekdays that are not bank holidays in
England and Wales.

The bank holidays are built from their rule, which gives every year, with the
exceptions the government announced: 8 May 2020 moved from 4 May, 2 June 2022
moved from 30 May and 3 June 2022 added, 19 September 2022 and 8 May 2023. The
rule and the exceptions reproduce every day gov.uk publishes for 2019 to 2028.
"""

from __future__ import annotations

from datetime import date, timedelta
from functools import lru_cache

__all__ = ["easter_sunday", "uk_bank_holidays", "uk_holidays_between"]

#: Holidays the government moved, from the rule's day to the day observed.
_MOVED = {date(2020, 5, 4): date(2020, 5, 8), date(2022, 5, 30): date(2022, 6, 2)}
#: Holidays the government added for one year.
_ADDED = (date(2022, 6, 3), date(2022, 9, 19), date(2023, 5, 8))


def easter_sunday(year: int) -> date:
    """Easter Sunday in the Gregorian calendar (the anonymous Gregorian algorithm)."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month, day = divmod(h + l - 7 * m + 114, 31)
    return date(year, month, day + 1)


def _first_monday(year: int, month: int) -> date:
    first = date(year, month, 1)
    return first + timedelta(days=(7 - first.weekday()) % 7)


def _last_monday(year: int, month: int) -> date:
    last = (date(year + (month == 12), month % 12 + 1, 1)) - timedelta(days=1)
    return last - timedelta(days=last.weekday())


@lru_cache(maxsize=None)
def uk_bank_holidays(year: int) -> frozenset[date]:
    """The bank holidays of England and Wales in a year, substitute days included."""
    days = set()
    new_year = date(year, 1, 1)
    days.add(new_year if new_year.weekday() < 5 else new_year + timedelta(days=7 - new_year.weekday()))
    easter = easter_sunday(year)
    days |= {easter - timedelta(days=2), easter + timedelta(days=1)}
    days |= {_first_monday(year, 5), _last_monday(year, 5), _last_monday(year, 8)}
    christmas = date(year, 12, 25)
    weekday = christmas.weekday()
    if weekday < 4:
        days |= {christmas, christmas + timedelta(days=1)}
    elif weekday == 4:
        days |= {christmas, date(year, 12, 28)}
    elif weekday == 5:
        days |= {date(year, 12, 27), date(year, 12, 28)}
    else:
        days |= {date(year, 12, 26), date(year, 12, 27)}
    days = {_MOVED.get(day, day) for day in days}
    days |= {day for day in _ADDED if day.year == year}
    return frozenset(days)


def uk_holidays_between(first_year: int, last_year: int) -> frozenset[date]:
    """Every England and Wales bank holiday from first_year to last_year inclusive."""
    out: set[date] = set()
    for year in range(first_year, last_year + 1):
        out |= uk_bank_holidays(year)
    return frozenset(out)

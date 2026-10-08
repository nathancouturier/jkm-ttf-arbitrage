"""Which delivery month a front-month JKM and a front-month TTF name on a day, and whether they agree.

JKM front month. ICE Futures Europe's JKM (Platts) futures for month M stop
trading "on the 15th calendar day of the calendar month prior to the contract
month", or the preceding business day, and settle on Platts' JKM from the 16th
of M-2 to the 15th of M-1; Platts rolls its JKM assessment on the 16th to the
month after next. So until the 15th the front month is the next month, and
after it the month after next.

TTF front month. ICE Endex's Dutch TTF futures stop trading "two UK Business
Days prior to the first calendar day of the delivery month". So until that
expiry the front month is the next month, and after it the month after next.

The two therefore name the same month from the 1st to the 15th, and again
after the TTF expiry at the end of the month, and different months from the
16th until the TTF expiry. A week's prices are tagged aligned when every trading
day of it names the same month for both, misaligned when none does, and mixed
otherwise. Both exchanges count UK business days (lngarb.calendars); a holiday
list can be passed instead, and an empty one gives weekdays only.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Iterable

from .calendars import uk_holidays_between

__all__ = ["add_months", "is_business_day", "jkm_roll_day", "jkm_last_trading_day", "ttf_expiry",
           "jkm_front_month", "ttf_front_month", "aligned_on", "week_alignment"]


def _calendar(holidays: Iterable[date] | None, around: date) -> frozenset[date]:
    """The holidays to use: those given, or the UK bank holidays of the years around the day."""
    if holidays is None:
        return uk_holidays_between(around.year - 1, around.year + 1)
    return frozenset(holidays)


def add_months(month: date, n: int) -> date:
    """The first day of the month n months after the month of the given day."""
    index = month.year * 12 + (month.month - 1) + n
    return date(index // 12, index % 12 + 1, 1)


def is_business_day(day: date, holidays: Iterable[date] = ()) -> bool:
    return day.weekday() < 5 and day not in set(holidays)


def _next_business_day(day: date, holidays: Iterable[date]) -> date:
    holidays = set(holidays)
    while not is_business_day(day, holidays):
        day += timedelta(days=1)
    return day


def _business_days_before(day: date, n: int, holidays: Iterable[date]) -> date:
    holidays = set(holidays)
    while n:
        day -= timedelta(days=1)
        if is_business_day(day, holidays):
            n -= 1
    return day


def jkm_roll_day(month: date, holidays: Iterable[date] | None = None) -> date:
    """The day in the month JKM rolls to the month after next: the 16th, or the next business day."""
    return _next_business_day(date(month.year, month.month, 16), _calendar(holidays, month))


def jkm_last_trading_day(contract_month: date, holidays: Iterable[date] | None = None) -> date:
    """The last trading day of the JKM futures for a contract month: the 15th of the month
    before, or the preceding business day."""
    before = add_months(contract_month, -1)
    day = date(before.year, before.month, 15)
    calendar = _calendar(holidays, day)
    while not is_business_day(day, calendar):
        day -= timedelta(days=1)
    return day


def ttf_expiry(delivery_month: date, holidays: Iterable[date] | None = None) -> date:
    """The last trading day of the TTF futures for a delivery month: two UK business days before it."""
    first = date(delivery_month.year, delivery_month.month, 1)
    return _business_days_before(first, 2, _calendar(holidays, first))


def jkm_front_month(day: date, holidays: Iterable[date] | None = None) -> date:
    """The delivery month a front-month JKM names on a day: the next month until its futures
    stop trading on the 15th, the month after next from then."""
    next_month = add_months(day, 1)
    if day <= jkm_last_trading_day(next_month, holidays):
        return next_month
    return add_months(day, 2)


def ttf_front_month(day: date, holidays: Iterable[date] | None = None) -> date:
    """The delivery month a front-month TTF names on a day."""
    next_month = add_months(day, 1)
    if day <= ttf_expiry(next_month, holidays):
        return next_month
    return add_months(day, 2)


def aligned_on(day: date, *, jkm_holidays: Iterable[date] | None = None,
               ttf_holidays: Iterable[date] | None = None) -> bool:
    return jkm_front_month(day, jkm_holidays) == ttf_front_month(day, ttf_holidays)


def week_alignment(week_ending: date, *, days: int = 7, jkm_holidays: Iterable[date] | None = None,
                   ttf_holidays: Iterable[date] | None = None) -> tuple[str, float]:
    """aligned, mixed or misaligned, and the share of the week's trading days aligned.

    The week is the days days ending on week_ending, Thursday to Wednesday for
    EIA's weeks; a trading day is a business day on both calendars.
    """
    jkm_holidays = _calendar(jkm_holidays, week_ending)
    ttf_holidays = _calendar(ttf_holidays, week_ending)
    trading = [
        week_ending - timedelta(days=k) for k in range(days)
        if is_business_day(week_ending - timedelta(days=k), jkm_holidays | ttf_holidays)
    ]
    if not trading:
        raise ValueError("no trading day in the week ending %s" % week_ending)
    share = sum(aligned_on(d, jkm_holidays=jkm_holidays, ttf_holidays=ttf_holidays) for d in trading) / len(trading)
    tag = "aligned" if share == 1 else "misaligned" if share == 0 else "mixed"
    return tag, share

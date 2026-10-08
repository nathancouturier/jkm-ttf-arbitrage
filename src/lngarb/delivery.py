"""Which delivery month a front-month JKM and a front-month TTF name on a day, and whether they agree.

JKM front month. Platts rolls its JKM assessment on the 16th of the month to
the month after next ("The Platts JKM rolls on the 16th of each calendar
month", Platts' press release of 16 June 2015, whose July window starts on
Monday 18 May 2015, the next business day). A futures contract on JKM for
month M settles on the assessments from the 16th of M-2 to the 15th of M-1 and
stops trading on the 15th of M-1 (JPX's LNG (Platts JKM) futures). So until the
roll the front month is the next month, and from it the month after next.

TTF front month. ICE Endex's Dutch TTF futures stop trading two business days
before their delivery month: the rule the study applies, not read in ICE's own
documents, whose terms forbid reading them by code. So until that expiry the
front month is the next month, and after it the month after next.

The two therefore name the same month from the 1st to the 15th, and again
after the TTF expiry at the end of the month, and different months from the
16th until the TTF expiry. A week's prices are tagged aligned when every trading
day of it names the same month for both, misaligned when none does, and mixed
otherwise. The business day calendars are parameters (lngarb.config), so a
holiday list can be added without changing the rules.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Iterable

__all__ = ["add_months", "is_business_day", "jkm_roll_day", "ttf_expiry", "jkm_front_month",
           "ttf_front_month", "aligned_on", "week_alignment"]


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


def jkm_roll_day(month: date, holidays: Iterable[date] = ()) -> date:
    """The day in the month JKM rolls to the month after next: the 16th, or the next business day."""
    return _next_business_day(date(month.year, month.month, 16), holidays)


def ttf_expiry(delivery_month: date, holidays: Iterable[date] = ()) -> date:
    """The last trading day of the TTF futures for a delivery month: two business days before it."""
    first = date(delivery_month.year, delivery_month.month, 1)
    return _business_days_before(first, 2, holidays)


def jkm_front_month(day: date, holidays: Iterable[date] = ()) -> date:
    """The delivery month a front-month JKM names on a day."""
    if day < jkm_roll_day(day, holidays):
        return add_months(day, 1)
    return add_months(day, 2)


def ttf_front_month(day: date, holidays: Iterable[date] = ()) -> date:
    """The delivery month a front-month TTF names on a day."""
    next_month = add_months(day, 1)
    if day <= ttf_expiry(next_month, holidays):
        return next_month
    return add_months(day, 2)


def aligned_on(day: date, *, jkm_holidays: Iterable[date] = (), ttf_holidays: Iterable[date] = ()) -> bool:
    return jkm_front_month(day, jkm_holidays) == ttf_front_month(day, ttf_holidays)


def week_alignment(week_ending: date, *, days: int = 7, jkm_holidays: Iterable[date] = (),
                   ttf_holidays: Iterable[date] = ()) -> tuple[str, float]:
    """aligned, mixed or misaligned, and the share of the week's trading days aligned.

    The week is the days days ending on week_ending, Thursday to Wednesday for
    EIA's weeks; a trading day is a business day on both calendars.
    """
    jkm_holidays, ttf_holidays = set(jkm_holidays), set(ttf_holidays)
    trading = [
        week_ending - timedelta(days=k) for k in range(days)
        if is_business_day(week_ending - timedelta(days=k), jkm_holidays | ttf_holidays)
    ]
    if not trading:
        raise ValueError("no trading day in the week ending %s" % week_ending)
    share = sum(aligned_on(d, jkm_holidays=jkm_holidays, ttf_holidays=ttf_holidays) for d in trading) / len(trading)
    tag = "aligned" if share == 1 else "misaligned" if share == 0 else "mixed"
    return tag, share

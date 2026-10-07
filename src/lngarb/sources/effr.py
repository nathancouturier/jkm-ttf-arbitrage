"""The effective federal funds rate, daily, from the Federal Reserve Bank of New York, before SOFR.

The financing line needs an overnight dollar rate for every loading date from
February 2016, and SOFR's first value date is 2 April 2018. The effective
federal funds rate (EFFR) is the New York Fed's overnight unsecured rate over
the whole span, on the same markets API and under the same Terms of Use as
SOFR, so it stands in before SOFR, labelled as a different rate: unsecured where
SOFR is secured. The two are never joined into one line without the change
marked.

One window is read, from FIRST_VALUE_DATE to LAST_VALUE_DATE, the month after
SOFR began, so that both rates are on record side by side at the change. The
series is closed. Rows come newest first and in two layouts: the 39 rows before
1 March 2016 carry intraday figures, the rest percentiles and volume, because
the New York Fed changed the rate's source and method on that day, from a
volume weighted mean of brokered trades to a volume weighted median of FR 2420
transactions. Only percentRate is read. A day with no publication has no row.
"""

from __future__ import annotations

import json
import sys

import pandas as pd

from ..config import BOUNDS_SOFR_PERCENT
from .base import Adapter, SourceError, http_get

__all__ = ["API_URL", "FIRST_VALUE_DATE", "LAST_VALUE_DATE", "METHOD_CHANGE", "parse_effr_json", "EffrDaily"]

FIRST_VALUE_DATE = "2016-01-01"
LAST_VALUE_DATE = "2018-04-30"
API_URL = (
    "https://markets.newyorkfed.org/api/rates/unsecured/effr/search.json?startDate=%s&endDate=%s"
    % (FIRST_VALUE_DATE, LAST_VALUE_DATE)
)
PAGE_URL = "https://www.newyorkfed.org/markets/reference-rates/effr"
#: The first value date of the rate's new source and method.
METHOD_CHANGE = "2016-03-01"


def parse_effr_json(payload: bytes | str) -> pd.DataFrame:
    """The daily EFFR from one API response, ascending by value date.

    Raises SourceError on a row of another type, a duplicate date, or a rate
    that is not a number. The method column says which of the New York Fed's
    two methods the day's rate was calculated by.
    """
    body = json.loads(payload)
    rows = body.get("refRates")
    if not isinstance(rows, list) or not rows:
        raise SourceError("the EFFR response carries no refRates list")
    records = []
    for row in rows:
        if row.get("type") != "EFFR":
            raise SourceError("a row of type %r in the EFFR response" % (row.get("type"),))
        rate = row.get("percentRate")
        if not isinstance(rate, (int, float)) or isinstance(rate, bool):
            raise SourceError("EFFR on %s is %r, not a number" % (row.get("effectiveDate"), rate))
        day = pd.Timestamp(row["effectiveDate"])
        records.append({
            "date": day,
            "effr_percent": float(rate),
            "method": (
                "volume weighted median of FR 2420 transactions"
                if day >= pd.Timestamp(METHOD_CHANGE)
                else "volume weighted mean of brokered trades"
            ),
        })
    frame = pd.DataFrame(records).sort_values("date", kind="mergesort").reset_index(drop=True)
    if frame["date"].duplicated().any():
        raise SourceError("the EFFR response repeats a date")
    return frame


class EffrDaily(Adapter):
    """EFFR, daily, percent per year, from 2016 to the month after SOFR began."""

    name = "nyfed_effr_daily"
    source = "Federal Reserve Bank of New York, Effective Federal Funds Rate"
    url = API_URL
    page_url = PAGE_URL
    unit = "percent per year"
    frequency = "daily"
    method = "published"
    required_cols = ("date", "effr_percent", "method")
    bounds = {"effr_percent": BOUNDS_SOFR_PERCENT}
    min_observations = {"effr_percent": 500}
    observation_column = "effr_percent"

    def __init__(self, *, from_file=None, fetched_at: str | None = None):
        self.from_file = from_file
        self.fetched_at = fetched_at

    def fetch(self) -> pd.DataFrame:
        if self.from_file is not None:
            payload = open(self.from_file, "rb").read()
            how = "read from a copy fetched at %s" % self.fetched_at
        else:
            payload = http_get(API_URL).content
            how = "fetched from the New York Fed markets API"
        frame = parse_effr_json(payload)
        first, last = frame["date"].iloc[0], frame["date"].iloc[-1]
        if first > pd.Timestamp("2016-01-08") or last < pd.Timestamp(LAST_VALUE_DATE) - pd.Timedelta(days=7):
            raise SourceError(
                "the EFFR window runs from %s to %s, not %s to %s"
                % (first.date(), last.date(), FIRST_VALUE_DATE, LAST_VALUE_DATE)
            )
        self.vintage = "value dates %s to %s" % (first.strftime("%Y-%m-%d"), last.strftime("%Y-%m-%d"))
        self.note = (
            "%s, %s to %s. Days with no publication have no row. The rate's source and "
            "method changed on %s, which the method column records. It stands in for "
            "SOFR, an unsecured rate for a secured one, before SOFR's first value date of "
            "2 April 2018. The Effective Federal Funds Rate is subject to the Terms of Use "
            "posted at newyorkfed.org; the New York Fed is not responsible for its "
            "publication here, does not sanction or endorse any particular republication, "
            "and has no liability for its use." % (how, FIRST_VALUE_DATE, LAST_VALUE_DATE, METHOD_CHANGE)
        )
        return frame


def main() -> int:
    try:
        entry = EffrDaily().run()
    except Exception as exc:
        print("FAILED nyfed_effr_daily: %s" % exc)
        return 1
    print("ok     %s: %d observations, %s to %s" % (
        entry["series"], entry["observations"], entry["first_date"], entry["last_date"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())

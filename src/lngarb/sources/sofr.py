"""The Secured Overnight Financing Rate, daily, from the Federal Reserve Bank of New York.

Read from the New York Fed's markets API, not through FRED. SOFR's first value
date is 2 April 2018; the API returns rows newest first, dated by value date,
and has no row at all for a day with no publication. The rate for a business
day is published at about 8:00 a.m. Eastern the next business day and may be
revised the same day by about 2:30 p.m. Eastern.

SOFR is licensed, not public domain. The New York Fed's Terms of Use allow
content to be copied and distributed on conditions, among them a notice and
disclaimer wherever reference rate data are shown. The committed cache travels
under those terms, and the site shows the notice beside the financing line
that uses it.

The study uses SOFR only for the cost of financing a cargo during the voyage.
Before 2 April 2018 there is no SOFR, and nothing is filled in here.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone

import pandas as pd

from ..config import BOUNDS_SOFR_PERCENT
from .base import Adapter, SourceError, http_get

__all__ = ["API_URL", "FIRST_VALUE_DATE", "parse_sofr_json", "SofrDaily"]

API_URL = "https://markets.newyorkfed.org/api/rates/secured/sofr/search.json?startDate={start}&endDate={end}"
PAGE_URL = "https://www.newyorkfed.org/markets/reference-rates/additional-information-about-reference-rates"
FIRST_VALUE_DATE = "2018-04-02"


def parse_sofr_json(payload: bytes | str) -> pd.DataFrame:
    """The daily SOFR from one API response, ascending by value date.

    Only percentRate is read; the percentiles can be the string "NA" and are
    not needed. Raises SourceError on a row of another type, a duplicate date,
    or a rate that is not a number.
    """
    body = json.loads(payload)
    rows = body.get("refRates")
    if not isinstance(rows, list) or not rows:
        raise SourceError("the SOFR response carries no refRates list")
    records = []
    for row in rows:
        if row.get("type") != "SOFR":
            raise SourceError("a row of type %r in the SOFR response" % (row.get("type"),))
        rate = row.get("percentRate")
        if not isinstance(rate, (int, float)) or isinstance(rate, bool):
            raise SourceError("SOFR on %s is %r, not a number" % (row.get("effectiveDate"), rate))
        records.append({"date": pd.Timestamp(row["effectiveDate"]), "sofr_percent": float(rate)})
    frame = pd.DataFrame(records).sort_values("date", kind="mergesort").reset_index(drop=True)
    if frame["date"].duplicated().any():
        raise SourceError("the SOFR response repeats a date")
    return frame


class SofrDaily(Adapter):
    """SOFR, daily, percent per year, from its first value date."""

    name = "nyfed_sofr_daily"
    source = "Federal Reserve Bank of New York, Secured Overnight Financing Rate"
    url = API_URL.format(start=FIRST_VALUE_DATE, end="today")
    page_url = PAGE_URL
    unit = "percent per year"
    frequency = "daily"
    method = "published"
    required_cols = ("date", "sofr_percent")
    bounds = {"sofr_percent": BOUNDS_SOFR_PERCENT}
    min_observations = {"sofr_percent": 2000}
    observation_column = "sofr_percent"

    def __init__(self, *, from_file=None, fetched_at: str | None = None):
        self.from_file = from_file
        self.fetched_at = fetched_at

    def fetch(self) -> pd.DataFrame:
        if self.from_file is not None:
            payload = open(self.from_file, "rb").read()
            how = "read from a copy fetched at %s" % self.fetched_at
        else:
            end = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            self.url = API_URL.format(start=FIRST_VALUE_DATE, end=end)
            payload = http_get(self.url).content
            how = "fetched from the New York Fed markets API"
        frame = parse_sofr_json(payload)
        if frame["date"].iloc[0] != pd.Timestamp(FIRST_VALUE_DATE):
            raise SourceError(
                "the first SOFR value date is %s, expected %s"
                % (frame["date"].iloc[0].date(), FIRST_VALUE_DATE)
            )
        self.vintage = "value dates to %s" % frame["date"].iloc[-1].strftime("%Y-%m-%d")
        self.note = (
            "%s. Days with no publication have no row. The SOFR is subject to the Terms "
            "of Use posted at newyorkfed.org; the New York Fed is not responsible for "
            "its publication here, does not sanction or endorse any particular "
            "republication, and has no liability for its use." % how
        )
        return frame


def main() -> int:
    try:
        entry = SofrDaily().run()
    except Exception as exc:
        print("FAILED nyfed_sofr_daily: %s" % exc)
        return 1
    print("ok     %s: %d observations, %s to %s" % (
        entry["series"], entry["observations"], entry["first_date"], entry["last_date"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())

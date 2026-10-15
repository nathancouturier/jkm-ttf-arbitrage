"""The effective federal funds rate, daily, from the Federal Reserve Board's H.15 release, from 1954.

The financing line needs an overnight dollar rate on every loading date, and
SOFR's first value date is 2 April 2018. Before it the effective federal funds
rate (EFFR) stands in, labelled as a different rate: unsecured where SOFR is
secured. The New York Fed calculates the rate and publishes it under its Terms
of Use; the Board republishes the same figures in its H.15 release, in the
public domain, from 1 July 1954. The Board's package is read here, so that the
whole history is held under one set of terms and any date since 1954 can be
priced. On the 585 days the New York Fed's API served for 2016 to April 2018,
the two agree on every day.

The route is the H.15 release page package, releases/h15/data/FRB_h15_xml.zip,
an SDMX file holding every H.15 series, of which this module keeps
RIFSPFF_N.B, "Federal funds effective rate", business days. A day with no rate
carries OBS_STATUS "ND" and OBS_VALUE "-9999", a sentinel that must never
become a rate; it is read as missing. The release is daily; the rate for a
business day is in the package the next business day.
"""

from __future__ import annotations

import sys

import pandas as pd

from ..config import BOUNDS_EFFR_PERCENT
from .base import Adapter, http_get
from .frb import parse_release_series

__all__ = ["ZIP_URL", "PAGE_URL", "SERIES_NAME", "FIRST_DAY", "parse_release_zip", "EffrDaily"]

ZIP_URL = "https://www.federalreserve.gov/releases/h15/data/FRB_h15_xml.zip"
PAGE_URL = "https://www.federalreserve.gov/releases/h15/"
DATA_MEMBER = "H15_data.xml"
SERIES_NAME = "RIFSPFF_N.B"
DESCRIPTION = "Federal funds effective rate"
#: The series' own first day. Nothing before it exists, so the whole series is kept.
FIRST_DAY = pd.Timestamp("1954-07-01")


def parse_release_zip(payload: bytes) -> tuple[pd.DataFrame, str]:
    """The daily EFFR from the release XML, whole, and the time the package was prepared."""
    return parse_release_series(
        payload,
        member=DATA_MEMBER,
        series_name=SERIES_NAME,
        description=DESCRIPTION,
        first_day=FIRST_DAY,
        value_column="effr_percent",
    )


class EffrDaily(Adapter):
    """The effective federal funds rate, daily, percent per year, H.15, from 1954."""

    name = "frb_h15_effr_daily"
    source = "Board of Governors of the Federal Reserve System, H.15 Selected Interest Rates"
    url = ZIP_URL
    page_url = PAGE_URL
    unit = "percent per year"
    frequency = "daily"
    method = "published"
    required_cols = ("date", "effr_percent", "obs_status")
    bounds = {"effr_percent": BOUNDS_EFFR_PERCENT}
    min_observations = {"effr_percent": 17000}
    observation_column = "effr_percent"

    def __init__(self, *, from_file=None, fetched_at: str | None = None):
        self.from_file = from_file
        self.fetched_at = fetched_at

    def fetch(self) -> pd.DataFrame:
        if self.from_file is not None:
            payload = open(self.from_file, "rb").read()
            how = "read from a copy fetched from %s at %s" % (ZIP_URL, self.fetched_at)
        else:
            payload = http_get(ZIP_URL, timeout=180).content
            how = "fetched from %s" % ZIP_URL
        frame, prepared = parse_release_zip(payload)
        missing = int(frame["effr_percent"].isna().sum())
        self.vintage = "prepared %s" % prepared
        self.note = (
            "%s, series %s, the effective federal funds rate, percent per year, from %s, "
            "the first day the Board publishes. %d business days carry no rate (status ND) "
            "and are kept as rows with no value. The rate stands in for SOFR, an unsecured "
            "rate for a secured one, before SOFR's first value date of 2 April 2018; the New "
            "York Fed calculates it and the Board republishes it in the public domain."
            % (how, SERIES_NAME, FIRST_DAY.date(), missing)
        )
        return frame


def main() -> int:
    try:
        entry = EffrDaily().run()
    except Exception as exc:
        print("FAILED frb_h15_effr_daily: %s" % exc)
        return 1
    print("ok     %s: %d observations, %s to %s" % (
        entry["series"], entry["observations"], entry["first_date"], entry["last_date"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())

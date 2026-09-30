"""US dollars per euro, daily, from the Federal Reserve Board's H.10 release.

The rate is the noon buying rate in New York for cable transfers payable in
euros, certified by the Federal Reserve Bank of New York for customs purposes.
It is quoted in US dollars per euro, the direction every conversion in this
study needs, and it is read from the Board directly rather than through FRED.

The Board is retiring its Data Download Program: the "Build Your Package"
option goes the week of 9 November 2026, with the rest of the program to follow,
and long date ranges already come back as an empty body. The Board says
historical data will remain on the release pages as XML, so that is the route
read here: releases/h10/data/FRB_h10_xml.zip, an SDMX file holding every H.10
series, of which this module keeps RXI$US_N.B.EU.

Every weekday has an observation. A day with no rate carries OBS_STATUS "ND"
and OBS_VALUE "-9999", a sentinel that must never become a price; it is read as
missing. The release is weekly, on Mondays, so the latest rate is up to about
ten days old. Past releases are not revised, but the series is corrected: the
Board corrected the rate for 3 August 2026 on 12 August 2026.
"""

from __future__ import annotations

import io
import math
import sys
import zipfile
from xml.etree import ElementTree

import pandas as pd

from ..config import BOUNDS_USD_PER_EUR
from .base import Adapter, SourceError, http_get

__all__ = ["ZIP_URL", "PAGE_URL", "SERIES_NAME", "parse_release_zip", "UsdPerEurDaily"]

ZIP_URL = "https://www.federalreserve.gov/releases/h10/data/FRB_h10_xml.zip"
PAGE_URL = "https://www.federalreserve.gov/releases/h10/hist/dat00_eu.htm"
DATA_MEMBER = "H10_data.xml"
SERIES_NAME = "RXI$US_N.B.EU"
FIRST_DAY = pd.Timestamp("2015-01-01")

#: OBS_STATUS codes the release's structure file defines: A normal, NA not
#: available, ND no data, NC not calculable. Only A carries a rate.
_NOT_A_RATE = {"NA", "ND", "NC"}


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def parse_release_zip(payload: bytes) -> tuple[pd.DataFrame, str]:
    """The euro series from the release XML, from FIRST_DAY, and the time it was prepared.

    Raises SourceError when the series is missing, appears twice, is not quoted
    as US dollars per euro, or carries a status this module does not know.
    """
    try:
        archive = zipfile.ZipFile(io.BytesIO(payload))
        handle = archive.open(DATA_MEMBER)
    except (zipfile.BadZipFile, KeyError) as exc:
        raise SourceError("the download is not the H.10 XML package: %s" % exc) from exc

    prepared = None
    found = 0
    in_series = False
    description = None
    rows: list[dict] = []
    with handle:
        for event, element in ElementTree.iterparse(handle, events=("start", "end")):
            name = _local(element.tag)
            if event == "end" and name == "Prepared" and prepared is None:
                prepared = (element.text or "").strip()
            if name == "Series":
                if event == "start":
                    in_series = element.attrib.get("SERIES_NAME") == SERIES_NAME
                    if in_series:
                        found += 1
                        if element.attrib.get("UNIT_MULT") != "1":
                            raise SourceError("%s has UNIT_MULT %r" % (SERIES_NAME, element.attrib.get("UNIT_MULT")))
                else:
                    in_series = False
                    element.clear()
                continue
            if not in_series or event != "end":
                continue
            if name == "AnnotationText" and (element.text or "").startswith("EMU Members Euro"):
                description = element.text.strip()
            elif name == "Obs":
                status = element.attrib.get("OBS_STATUS")
                day = pd.Timestamp(element.attrib["TIME_PERIOD"])
                if day >= FIRST_DAY:
                    if status == "A":
                        value = float(element.attrib["OBS_VALUE"])
                    elif status in _NOT_A_RATE:
                        value = math.nan
                    else:
                        raise SourceError("%s on %s has unknown OBS_STATUS %r" % (SERIES_NAME, day.date(), status))
                    rows.append({"date": day, "usd_per_eur": value, "obs_status": status})
                element.clear()

    if found != 1:
        raise SourceError("%s appears %d times in %s" % (SERIES_NAME, found, DATA_MEMBER))
    if description != "EMU Members Euro (USD per EUR)":
        raise SourceError(
            "%s is described as %r, not as US dollars per euro; the direction of the "
            "quote cannot be assumed" % (SERIES_NAME, description)
        )
    if not prepared:
        raise SourceError("the XML carries no Prepared time")
    frame = pd.DataFrame(rows).sort_values("date", kind="mergesort").reset_index(drop=True)
    return frame, prepared


class UsdPerEurDaily(Adapter):
    """US dollars per euro, daily noon buying rate, H.10, from 2015."""

    name = "h10_usd_per_eur_daily"
    source = "Board of Governors of the Federal Reserve System, H.10 Foreign Exchange Rates"
    url = ZIP_URL
    page_url = PAGE_URL
    unit = "US dollars per euro"
    frequency = "daily"
    method = "published"
    required_cols = ("date", "usd_per_eur", "obs_status")
    bounds = {"usd_per_eur": BOUNDS_USD_PER_EUR}
    min_observations = {"usd_per_eur": 2500}
    observation_column = "usd_per_eur"

    def __init__(self, *, from_file=None, fetched_at: str | None = None):
        self.from_file = from_file
        self.fetched_at = fetched_at

    def fetch(self) -> pd.DataFrame:
        if self.from_file is not None:
            payload = open(self.from_file, "rb").read()
            how = "read from a copy fetched from %s at %s" % (ZIP_URL, self.fetched_at)
        else:
            payload = http_get(ZIP_URL, timeout=120).content
            how = "fetched from %s" % ZIP_URL
        frame, prepared = parse_release_zip(payload)
        missing = int(frame["usd_per_eur"].isna().sum())
        self.vintage = "prepared %s" % prepared
        self.note = (
            "%s, series %s, US dollars per euro, noon buying rate in New York. %d "
            "weekdays from %s carry no rate (status ND) and are kept as rows with "
            "no value." % (how, SERIES_NAME, missing, FIRST_DAY.date())
        )
        return frame


def main() -> int:
    try:
        entry = UsdPerEurDaily().run()
    except Exception as exc:
        print("FAILED h10_usd_per_eur_daily: %s" % exc)
        return 1
    print("ok     %s: %d observations, %s to %s" % (
        entry["series"], entry["observations"], entry["first_date"], entry["last_date"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())

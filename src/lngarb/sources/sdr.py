"""US dollars per special drawing right, daily: the IMF's rate as the Deutsche Bundesbank republishes it.

The Suez Canal Authority sets its tolls in special drawing rights (SDR), so a
toll in dollars needs the rate of the day. The IMF publishes the rate, but its
hosts refuse automated requests, even for robots.txt; the Bundesbank
republishes the series, naming the IMF as its source, on an API its robots.txt
allows. The IMF's terms, read in a browser on 8 October 2026, let its exchange
rate data be copied and published with the IMF credited, "whether obtained
directly from the IMF or another party", so the cache is committed with that
credit. On the 41 days of October 2022 and September 2026 compared with the
IMF's own monthly tables, every rate is the same to the sixth decimal.

The file is a CSV with nine header rows (title, decimals, source, unit, last
update) before one row per calendar day. A day with no rate carries "." and the
flag "No value available": weekends and the IMF's own closing days, which are
not the US or German bank holidays. They are kept as rows with no value, never
as zero.
"""

from __future__ import annotations

import csv
import io
import re
import sys

import pandas as pd

from ..config import BOUNDS_USD_PER_SDR
from .base import Adapter, SourceError, http_get

__all__ = ["API_URL", "FIRST_DAY", "parse_bbk_csv", "UsdPerSdrDaily"]

API_URL = "https://api.statistiken.bundesbank.de/rest/download/BBEX3/D.USD.XDR.DA.AC.000?format=csv&lang=en"
#: The IMF's own page for the rates, where a reader can check any day.
PAGE_URL = "https://www.imf.org/external/np/fin/data/param_rms_mth.aspx"
FIRST_DAY = pd.Timestamp("2016-01-01")
SERIES = "BBEX3.D.USD.XDR.DA.AC.000"

_DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def parse_bbk_csv(payload: bytes | str) -> tuple[pd.DataFrame, str]:
    """Every day from FIRST_DAY with its rate, or none, and the file's last update.

    Raises SourceError when the file is not the series named, its unit is not
    dollars per SDR, its source is not the IMF, or a value is neither a number
    nor ".".
    """
    text = payload.decode("utf-8-sig") if isinstance(payload, bytes) else payload.lstrip(chr(0xFEFF))
    rows = list(csv.reader(io.StringIO(text)))
    if not rows or len(rows[0]) < 2 or rows[0][1] != SERIES:
        raise SourceError("the file does not hold %s" % SERIES)
    header = {row[0]: row[1] for row in rows[1:] if row and not _DAY.match(row[0]) and len(row) > 1}
    if not header.get("", "").startswith("Value of the special drawing right / XDR 1 = USD"):
        raise SourceError("the series is described as %r, not as US dollars per SDR" % header.get(""))
    if header.get("unit") != "USD" or "International Monetary Fund" not in header.get("Source (in english)", ""):
        raise SourceError("unexpected unit or source: %r, %r" % (header.get("unit"), header.get("Source (in english)")))
    records = []
    for row in rows:
        if not row or not _DAY.match(row[0]):
            continue
        day = pd.Timestamp(row[0])
        if day < FIRST_DAY:
            continue
        value = row[1].strip()
        if value == ".":
            records.append({"date": day, "usd_per_sdr": float("nan"), "flag": row[2] if len(row) > 2 else ""})
        else:
            try:
                records.append({"date": day, "usd_per_sdr": float(value), "flag": ""})
            except ValueError:
                raise SourceError("the rate on %s is %r" % (row[0], value)) from None
    frame = pd.DataFrame(records)
    if frame.empty or frame["date"].duplicated().any():
        raise SourceError("the file holds no rows from %s, or repeats a day" % FIRST_DAY.date())
    return frame, header.get("last update", "")


class UsdPerSdrDaily(Adapter):
    """US dollars per SDR, daily from 2016, the IMF's rate through the Bundesbank."""

    name = "imf_usd_per_sdr_daily"
    source = "International Monetary Fund, exchange rate data, as republished by the Deutsche Bundesbank"
    url = API_URL
    page_url = PAGE_URL
    unit = "US dollars per SDR"
    frequency = "daily"
    method = "published"
    required_cols = ("date", "usd_per_sdr", "flag")
    bounds = {"usd_per_sdr": BOUNDS_USD_PER_SDR}
    min_observations = {"usd_per_sdr": 2500}
    observation_column = "usd_per_sdr"

    def __init__(self, *, from_file=None, fetched_at: str | None = None):
        self.from_file = from_file
        self.fetched_at = fetched_at

    def fetch(self) -> pd.DataFrame:
        if self.from_file is not None:
            payload = open(self.from_file, "rb").read()
            how = "read from a copy fetched at %s" % self.fetched_at
        else:
            payload = http_get(API_URL, timeout=120, delay=11.0).content
            how = "fetched from the Bundesbank's statistics API"
        frame, updated = parse_bbk_csv(payload)
        self.vintage = "last update %s" % updated
        self.note = (
            "%s, series %s, the IMF's US dollars per SDR. %d days from %s carry no rate "
            "(weekends and the IMF's closing days) and are kept as rows with no value."
            % (how, SERIES, int(frame["usd_per_sdr"].isna().sum()), FIRST_DAY.date())
        )
        return frame


def main() -> int:
    try:
        entry = UsdPerSdrDaily().run()
    except Exception as exc:
        print("FAILED imf_usd_per_sdr_daily: %s" % exc)
        return 1
    print("ok     %s: %d observations, %s to %s" % (
        entry["series"], entry["observations"], entry["first_date"], entry["last_date"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())

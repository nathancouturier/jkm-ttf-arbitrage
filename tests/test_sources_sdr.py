"""The IMF's SDR rate through the Bundesbank, from a file built here: the series itself is private."""

from __future__ import annotations

import math

import pandas as pd
import pytest

from lngarb.sources import base, sdr

# The layout of the Bundesbank's file, with made up rates: the real series may
# not be committed until the IMF's terms are read.
HEADER = (
    '"",BBEX3.D.USD.XDR.DA.AC.000,BBEX3.D.USD.XDR.DA.AC.000_FLAGS\n'
    '"",Value of the special drawing right / XDR 1 = USD ...,\n'
    "Decimals,6,\n"
    'Source (in english),"International Monetary Fund (IMF), Washington",\n'
    "Time format code,P1D,\n"
    "category,WEDE,\n"
    "unit,USD,\n"
    "unit multiplier,One,\n"
    "last update,2026-10-06 11:34:41,\n"
)
ROWS = (
    "2015-12-31,1.400000,\n"
    "2016-01-01,.,No value available\n"
    "2016-01-04,1.500000,\n"
)


def test_days_from_2016_with_no_rate_kept_as_missing():
    frame, updated = sdr.parse_bbk_csv((HEADER + ROWS).encode("utf-8-sig"))
    assert updated == "2026-10-06 11:34:41"
    assert frame["date"].tolist() == [pd.Timestamp("2016-01-01"), pd.Timestamp("2016-01-04")]
    assert math.isnan(frame["usd_per_sdr"].iloc[0])
    assert frame["flag"].iloc[0] == "No value available"
    assert frame["usd_per_sdr"].iloc[1] == 1.5


def test_a_file_of_another_series_or_unit_is_refused():
    with pytest.raises(base.SourceError):
        sdr.parse_bbk_csv((HEADER.replace("XDR 1 = USD", "USD 1 = XDR") + ROWS).encode())
    with pytest.raises(base.SourceError):
        sdr.parse_bbk_csv((HEADER.replace("unit,USD,", "unit,EUR,") + ROWS).encode())


def test_the_series_is_private():
    adapter = sdr.UsdPerSdrDaily()
    assert adapter.committable is False
    assert adapter.directory() == "private"

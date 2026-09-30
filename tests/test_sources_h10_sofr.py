"""The euro rate from the Federal Reserve Board's H.10 and SOFR from the New York Fed.

Fixtures: the H.10 release page XML package prepared on 28 September 2026, and the
New York Fed's SOFR response for 1 January 2018 to 30 September 2026.
"""

from __future__ import annotations

import io
import math
import zipfile

import pandas as pd
import pytest

from lngarb.sources import base, h10, sofr

FIXTURES = base.REPO_ROOT / "tests" / "fixtures"
H10_ZIP = (FIXTURES / "h10_release_2026-09-28.zip").read_bytes()
SOFR_JSON = (FIXTURES / "nyfed_sofr_2018-01-01_to_2026-09-30.json").read_bytes()


# --------------------------------------------------------------------------
# H.10
# --------------------------------------------------------------------------

def test_the_euro_rate_on_dates_checked_against_the_history_page():
    frame, prepared = h10.parse_release_zip(H10_ZIP)
    assert prepared == "2026-09-28T13:35:00"
    rate = frame.set_index("date")["usd_per_eur"]
    assert rate[pd.Timestamp("2016-01-04")] == 1.0803
    assert rate[pd.Timestamp("2020-03-23")] == 1.0760
    assert rate[pd.Timestamp("2022-09-27")] == 0.9616
    assert rate[pd.Timestamp("2026-09-01")] == 1.1593
    assert rate[pd.Timestamp("2026-09-25")] == 1.1400


def test_no_data_days_are_missing_and_never_the_sentinel():
    frame, _ = h10.parse_release_zip(H10_ZIP)
    rate = frame.set_index("date")["usd_per_eur"]
    assert math.isnan(rate[pd.Timestamp("2016-01-01")])
    assert math.isnan(rate[pd.Timestamp("2026-09-07")])
    assert (frame["usd_per_eur"].dropna() > 0).all()
    assert not (frame["usd_per_eur"] == -9999).any()
    assert set(frame.loc[frame["usd_per_eur"].isna(), "obs_status"]) == {"ND"}


def test_every_weekday_from_2015_has_a_row():
    frame, _ = h10.parse_release_zip(H10_ZIP)
    assert frame["date"].iloc[0] == pd.Timestamp("2015-01-01")
    weekdays = pd.bdate_range(frame["date"].iloc[0], frame["date"].iloc[-1])
    assert list(frame["date"]) == list(weekdays)
    assert len(frame) == 3062


def test_a_package_that_lacks_the_euro_series_is_refused():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(
            "H10_data.xml",
            '<?xml version="1.0"?><root><Prepared>2026-01-01T00:00:00</Prepared>'
            '<Series SERIES_NAME="RXI_N.B.CA" UNIT_MULT="1"></Series></root>',
        )
    with pytest.raises(base.SourceError) as caught:
        h10.parse_release_zip(buffer.getvalue())
    assert "appears 0 times" in str(caught.value)


def test_the_adapter_writes_the_rate_with_its_no_data_days(sandbox, tmp_path):
    package = tmp_path / "h10.zip"
    package.write_bytes(H10_ZIP)
    entry = h10.UsdPerEurDaily(from_file=package, fetched_at="2026-09-30T15:54:50Z").run()
    assert entry["status"] == "ok"
    assert entry["file_rows"] == 3062
    assert entry["observations"] == 3062 - 129
    assert entry["vintage"] == "prepared 2026-09-28T13:35:00"


# --------------------------------------------------------------------------
# SOFR
# --------------------------------------------------------------------------

def test_sofr_starts_on_its_first_value_date_and_ends_the_day_before_the_fetch():
    frame = sofr.parse_sofr_json(SOFR_JSON)
    assert len(frame) == 2122
    assert frame["date"].iloc[0] == pd.Timestamp("2018-04-02")
    assert frame["sofr_percent"].iloc[0] == 1.80
    assert frame["date"].iloc[-1] == pd.Timestamp("2026-09-29")
    assert frame["sofr_percent"].iloc[-1] == 3.88
    assert frame["date"].is_monotonic_increasing


def test_rows_with_na_percentiles_still_give_their_rate():
    frame = sofr.parse_sofr_json(SOFR_JSON)
    rate = frame.set_index("date")["sofr_percent"]
    assert rate[pd.Timestamp("2019-05-31")] == 2.49
    assert rate[pd.Timestamp("2021-08-05")] == 0.05


def test_a_rate_that_is_not_a_number_is_refused():
    with pytest.raises(base.SourceError):
        sofr.parse_sofr_json(b'{"refRates": [{"effectiveDate": "2026-01-02", "type": "SOFR", "percentRate": "NA"}]}')


def test_the_sofr_adapter_carries_the_new_york_fed_notice(sandbox, tmp_path):
    response = tmp_path / "sofr.json"
    response.write_bytes(SOFR_JSON)
    entry = sofr.SofrDaily(from_file=response, fetched_at="2026-09-30T15:58:59Z").run()
    assert entry["status"] == "ok"
    assert entry["first_date"] == "2018-04-02"
    assert "subject to the Terms of Use posted at newyorkfed.org" in entry["note"]
    assert "not public domain" in entry["licence_note"]

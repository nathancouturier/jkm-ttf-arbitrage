"""The euro rate from the Board's H.10, SOFR from the New York Fed, and the effective
federal funds rate from the Board's H.15.

Fixtures: the H.10 release page XML package prepared on 28 September 2026, the
New York Fed's SOFR response for 1 January 2018 to 30 September 2026, and the
H.15 release page XML package prepared on 14 October 2026.
"""

from __future__ import annotations

import io
import math
import zipfile

import pandas as pd
import pytest

from lngarb.sources import base, h10, h15, sofr, sofr_indicative

FIXTURES = base.REPO_ROOT / "tests" / "fixtures"
H10_ZIP = (FIXTURES / "h10_release_2026-09-28.zip").read_bytes()
SOFR_JSON = (FIXTURES / "nyfed_sofr_2018-01-01_to_2026-09-30.json").read_bytes()
H15_ZIP = (FIXTURES / "h15_release_2026-10-14.zip").read_bytes()


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


def test_every_weekday_from_the_euros_first_day_has_a_row():
    frame, _ = h10.parse_release_zip(H10_ZIP)
    assert frame["date"].iloc[0] == pd.Timestamp("1999-01-04")
    assert frame["date"].iloc[-1] == pd.Timestamp("2026-09-25")
    weekdays = pd.bdate_range(frame["date"].iloc[0], frame["date"].iloc[-1])
    assert list(frame["date"]) == list(weekdays)
    assert len(frame) == 7235
    # the first day's rate, and the one the history page prints for 2015
    rate = frame.set_index("date")["usd_per_eur"]
    assert rate[pd.Timestamp("1999-01-04")] == 1.1812
    assert rate[pd.Timestamp("2015-01-02")] == 1.2015


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
    assert entry["file_rows"] == 7235
    assert entry["observations"] == 7235 - 280
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


# --------------------------------------------------------------------------
# EFFR, before SOFR: the Board's H.15, from 1954
# --------------------------------------------------------------------------

def test_effr_runs_from_july_1954_and_agrees_with_the_new_york_fed_on_checked_days():
    frame, prepared = h15.parse_release_zip(H15_ZIP)
    assert prepared == "2026-10-14T15:40:02"
    assert frame["date"].iloc[0] == pd.Timestamp("1954-07-01")
    assert frame["date"].iloc[-1] == pd.Timestamp("2026-10-13")
    assert len(frame) == 18859
    weekdays = pd.bdate_range(frame["date"].iloc[0], frame["date"].iloc[-1])
    assert list(frame["date"]) == list(weekdays)
    rate = frame.set_index("date")["effr_percent"]
    assert rate[pd.Timestamp("1954-07-01")] == 1.13
    # the New York Fed's API served these for 2016 to April 2018, and the two agree on all 585 days
    assert rate[pd.Timestamp("2016-01-04")] == 0.36
    assert rate[pd.Timestamp("2017-05-31")] == 0.83
    assert rate[pd.Timestamp("2018-04-30")] == 1.69
    assert rate[pd.Timestamp("2026-10-13")] == 3.88


def test_effr_holidays_are_missing_and_never_the_sentinel():
    frame, _ = h15.parse_release_zip(H15_ZIP)
    rate = frame.set_index("date")["effr_percent"]
    assert math.isnan(rate[pd.Timestamp("2016-07-04")])
    assert not (frame["effr_percent"] == -9999).any()
    assert set(frame.loc[frame["effr_percent"].isna(), "obs_status"]) == {"ND"}
    assert int(frame["effr_percent"].isna().sum()) == 680


def test_a_package_that_lacks_the_effr_series_is_refused():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(
            "H15_data.xml",
            '<?xml version="1.0"?><root><Prepared>2026-01-01T00:00:00</Prepared>'
            '<Series SERIES_NAME="RIFSPFF_N.D" UNIT_MULT="1"></Series></root>',
        )
    with pytest.raises(base.SourceError) as caught:
        h15.parse_release_zip(buffer.getvalue())
    assert "appears 0 times" in str(caught.value)


def test_a_series_described_as_something_else_is_refused():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(
            "H15_data.xml",
            '<?xml version="1.0"?><root><Prepared>2026-01-01T00:00:00</Prepared>'
            '<Series SERIES_NAME="RIFSPFF_N.B" UNIT_MULT="1"><AnnotationText>Something else</AnnotationText>'
            '<Obs OBS_STATUS="A" OBS_VALUE="1.0" TIME_PERIOD="2000-01-03"/></Series></root>',
        )
    with pytest.raises(base.SourceError) as caught:
        h15.parse_release_zip(buffer.getvalue())
    assert "not described as" in str(caught.value)


def test_the_h15_adapter_writes_the_rate_in_the_public_domain(sandbox, tmp_path):
    package = tmp_path / "h15.zip"
    package.write_bytes(H15_ZIP)
    entry = h15.EffrDaily(from_file=package, fetched_at="2026-10-15T10:54:07Z").run()
    assert entry["status"] == "ok"
    assert (entry["first_date"], entry["last_date"]) == ("1954-07-01", "2026-10-13")
    assert entry["file_rows"] == 18859
    assert entry["observations"] == 18859 - 680
    assert entry["vintage"] == "prepared 2026-10-14T15:40:02"
    assert "public domain" in entry["licence_note"]
    assert "stands in for SOFR" in entry["note"]


# --------------------------------------------------------------------------
# The indicative SOFR, August 2014 to March 2018
# --------------------------------------------------------------------------

INDICATIVE_XLSX = (FIXTURES / "nyfed_sofr_indicative_2014-08-22_to_2018-03-29.xlsx").read_bytes()


def test_the_indicative_sofr_runs_over_its_closed_window_in_percent():
    frame = sofr_indicative.parse_workbook(INDICATIVE_XLSX)
    assert len(frame) == 899
    assert frame["date"].iloc[0] == pd.Timestamp("2014-08-22")
    assert frame["date"].iloc[-1] == pd.Timestamp("2018-03-29")
    rate = frame.set_index("date")["sofr_percent"]
    # 6 and 180 basis points in the workbook
    assert rate[pd.Timestamp("2014-08-22")] == 0.06
    assert rate[pd.Timestamp("2018-03-29")] == 1.80
    assert frame["date"].is_monotonic_increasing and not frame["date"].duplicated().any()


def test_a_workbook_without_the_rates_sheet_or_the_units_is_refused(tmp_path):
    import openpyxl

    book = openpyxl.Workbook()
    book.active.title = "Other"
    path = tmp_path / "other.xlsx"
    book.save(path)
    with pytest.raises(base.SourceError):
        sofr_indicative.parse_workbook(path.read_bytes())


def test_the_indicative_adapter_carries_the_new_york_fed_notice(sandbox, tmp_path):
    path = tmp_path / "indicative.xlsx"
    path.write_bytes(INDICATIVE_XLSX)
    entry = sofr_indicative.SofrIndicativeDaily(from_file=path, fetched_at="2026-10-15T12:05:40Z").run()
    assert entry["status"] == "ok"
    assert (entry["first_date"], entry["last_date"]) == ("2014-08-22", "2018-03-29")
    assert "subject to the Terms of Use posted at newyorkfed.org" in entry["note"]
    assert "not public domain" in entry["licence_note"]

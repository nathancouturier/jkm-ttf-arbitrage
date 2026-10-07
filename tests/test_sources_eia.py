"""EIA's exports by destination and Henry Hub spot, parsed from committed workbooks.

Three fixtures, EIA's own bytes: the exports workbook released on 31 August 2026,
the release of 30 April 2026 as the Internet Archive captured it on 5 May 2026,
and the Henry Hub history workbook released on 23 September 2026.
"""

from __future__ import annotations

import math

import pandas as pd
import pytest

from lngarb import config
from lngarb.sources import base, eia

FIXTURES = base.REPO_ROOT / "tests" / "fixtures"
AUGUST = (FIXTURES / "eia_exports_release_2026-08-31.xls").read_bytes()
APRIL = (FIXTURES / "eia_exports_release_2026-04-30_wayback.xls").read_bytes()
HENRY_HUB = (FIXTURES / "eia_henry_hub_release_2026-09-23.xls").read_bytes()


def value(frame, when, series_id):
    row = frame[(frame["date"] == pd.Timestamp(when)) & (frame["series_id"] == series_id)]
    assert len(row) == 1, (when, series_id)
    return row["mmcf"].item()


VESSEL = "NGM_EPG0_EVE_NUS-%s_MMCF"


# --------------------------------------------------------------------------
# Test 15, the anchors: exports as released on 31 August 2026
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "series_id, jan, may, jun",
    [
        ("N9133US2", 539203, 502812, 521059),
        (VESSEL % "NJA", 3269, 42531, 28827),
        (VESSEL % "NKS", 6868, 49533, 46922),
        (VESSEL % "NTW", 14240, 34770, 28305),
        (VESSEL % "NCH", 0, 0, 4576),
    ],
)
def test_the_august_release_reproduces_every_anchor(series_id, jan, may, jun):
    frame, released, following = eia.parse_exports_workbook(AUGUST)
    assert released.isoformat() == "2026-08-31"
    assert following.isoformat() == "2026-09-30"
    assert value(frame, "2026-01-15", series_id) == jan
    assert value(frame, "2026-05-15", series_id) == may
    assert value(frame, "2026-06-15", series_id) == jun


def test_the_asian_share_of_the_anchor_months():
    frame, _, _ = eia.parse_exports_workbook(AUGUST)
    for when, share in (("2026-01-15", 4.5), ("2026-05-15", 25.2), ("2026-06-15", 20.8)):
        month = frame[frame["date"] == pd.Timestamp(when)]
        jkm = month[(month["block"] == "exports by vessel") & (month["region"] == "jkm_markets")]
        total = value(frame, when, "N9133US2")
        assert round(100 * jkm["mmcf"].sum() / total, 1) == share


# --------------------------------------------------------------------------
# Test 16, regions: every destination in the table maps to one
# --------------------------------------------------------------------------

def test_every_destination_in_the_table_maps_to_a_region():
    frame, _, _ = eia.parse_exports_workbook(AUGUST)
    countries = frame[frame["code"] != "Z00"]
    assert (countries["region"] != "").all()
    assert set(countries["region"]) <= set(config.REGIONS)
    vessel = countries[countries["block"] == "exports by vessel"]
    assert vessel["series_id"].nunique() == 51


def test_an_unmapped_destination_stops_the_parse(monkeypatch):
    trimmed = {k: v for k, v in config.EIA_DESTINATIONS.items() if k != "NSG"}
    monkeypatch.setattr(eia, "EIA_DESTINATIONS", trimmed)
    with pytest.raises(eia.ParseError) as caught:
        eia.parse_exports_workbook(AUGUST)
    assert "NSG" in str(caught.value)
    assert "does not map to a region" in str(caught.value)


def test_a_code_mapped_to_the_wrong_country_stops_the_parse(monkeypatch):
    wrong = dict(config.EIA_DESTINATIONS)
    wrong["NJA"] = config.Destination("Japon", "jkm_markets")
    monkeypatch.setattr(eia, "EIA_DESTINATIONS", wrong)
    with pytest.raises(eia.ParseError) as caught:
        eia.parse_exports_workbook(AUGUST)
    assert "Japon" in str(caught.value)


def test_the_regions_are_the_five_the_flow_analysis_names():
    assert list(config.REGIONS) == [
        "jkm_markets", "other_asia", "europe", "middle_east_africa", "americas",
    ]
    jkm = sorted(d.country for d in config.EIA_DESTINATIONS.values() if d.region == "jkm_markets")
    assert jkm == ["China", "Japan", "South Korea", "Taiwan"]


# --------------------------------------------------------------------------
# The workbook's structure, and what is and is not read
# --------------------------------------------------------------------------

def test_the_frame_starts_in_january_2016_and_dates_months_on_the_15th():
    frame, _, _ = eia.parse_exports_workbook(AUGUST)
    assert frame["date"].min() == pd.Timestamp("2016-01-15")
    assert frame["date"].max() == pd.Timestamp("2026-06-15")
    assert set(frame["date"].dt.day) == {15}
    assert frame["date"].is_monotonic_increasing


def test_the_first_shale_era_cargo_is_split_across_two_blocks():
    frame, _, _ = eia.parse_exports_workbook(AUGUST)
    assert value(frame, "2016-02-15", VESSEL % "NBR") == 1993
    assert value(frame, "2016-02-15", "NGM_EPG0_ERE_NUS-NBR_MMCF") == 1290
    assert value(frame, "2016-02-15", "N9133US2") == 3309


def test_empty_cells_are_missing_and_zeros_stay_zeros():
    frame, _, _ = eia.parse_exports_workbook(AUGUST)
    # The re-exports total stops in February 2026 while its country rows go on.
    assert math.isnan(value(frame, "2026-06-15", "NGM_EPG0_ERE_NUS-Z00_MMCF"))
    assert value(frame, "2026-05-15", VESSEL % "NCH") == 0


def test_pipeline_and_compressed_gas_are_not_read():
    frame, _, _ = eia.parse_exports_workbook(AUGUST)
    assert not frame["series_id"].isin(["N9130US2", "N9132CN2", "N9132MX2"]).any()
    assert not frame["series_id"].str.contains("_ENC_").any()


# --------------------------------------------------------------------------
# Vintages: the April and August releases disagree, and that is recorded
# --------------------------------------------------------------------------

def test_the_april_release_is_the_vintage_it_says_it_is():
    frame, released, following = eia.parse_exports_workbook(APRIL)
    assert released.isoformat() == "2026-04-30"
    assert following.isoformat() == "2026-05-29"
    assert frame["date"].max() == pd.Timestamp("2026-02-15")


def test_the_china_february_2026_revision_is_found_and_new_months_are_not_revisions():
    april, _, _ = eia.parse_exports_workbook(APRIL)
    august, _, _ = eia.parse_exports_workbook(AUGUST)
    revisions = eia.compare_vintages(april, august)
    china = revisions[
        (revisions["series_id"] == VESSEL % "NCH")
        & (revisions["date"] == pd.Timestamp("2026-02-15"))
    ]
    assert china[["mmcf_before", "mmcf_after"]].values.tolist() == [[509.0, 0.0]]
    assert china["vintage_before"].item() == "2026-04-30"
    assert china["vintage_after"].item() == "2026-08-31"
    # March to June 2026 are not in the April release: new data, not revisions.
    assert revisions["date"].max() <= pd.Timestamp("2026-02-15")
    korea = revisions[
        (revisions["series_id"] == VESSEL % "NKS")
        & (revisions["date"] == pd.Timestamp("2025-05-15"))
    ]
    assert korea[["mmcf_before", "mmcf_after"]].values.tolist() == [[22865.0, 21207.0]]


def test_the_china_february_2026_price_went_with_its_volume():
    april, _, _ = eia.parse_exports_workbook(APRIL)
    august, _, _ = eia.parse_exports_workbook(AUGUST)
    revisions = eia.compare_vintages(april, august)
    china = revisions[
        (revisions["series_id"] == VESSEL % "NCH")
        & (revisions["date"] == pd.Timestamp("2026-02-15"))
    ]
    assert china["usd_per_mcf_before"].item() == 13.28
    assert math.isnan(china["usd_per_mcf_after"].item())


def test_every_row_carries_the_price_of_its_own_series():
    frame, _, _ = eia.parse_exports_workbook(AUGUST)
    assert eia.price_key("N9133US2") == "N9133US3"
    assert eia.price_key(VESSEL % "NJA") == "NGM_EPG0_EVE_NUS-NJA_DMCF"
    priced = frame["usd_per_mcf"].dropna()
    assert len(priced) > 1000
    assert priced.min() > 0
    # Prices and volumes do not always come together. One price stands on a
    # volume printed as 0 (Canada by truck, January 2018), and eight months of
    # 2019 carry a volume with no price. Both are kept as EIA prints them.
    no_volume = frame[frame["usd_per_mcf"].notna() & ~(frame["mmcf"] > 0)]
    assert no_volume["series_id"].tolist() == ["NGM_EPG0_ETR_NUS-NCA_MMCF"]
    assert no_volume["date"].tolist() == [pd.Timestamp("2018-01-15")]
    assert no_volume["usd_per_mcf"].item() == 19.21
    no_price = frame[frame["usd_per_mcf"].isna() & (frame["mmcf"] > 0)]
    assert len(no_price) == 8
    assert set(no_price["date"].dt.year) == {2019}


def test_a_price_series_missing_from_data_2_stops_the_parse(monkeypatch):
    real = eia.price_key
    monkeypatch.setattr(eia, "price_key", lambda key: real(key) + "_GONE" if key.endswith("NJA_MMCF") else real(key))
    with pytest.raises(eia.ParseError) as caught:
        eia.parse_exports_workbook(AUGUST)
    assert "NJA" in str(caught.value)


def test_the_adapter_writes_the_latest_vintage_and_logs_what_it_revised(sandbox, tmp_path):
    april_file = tmp_path / "april.xls"
    april_file.write_bytes(APRIL)
    august_file = tmp_path / "august.xls"
    august_file.write_bytes(AUGUST)

    first = eia.LngExportsMonthly(from_file=april_file, fetched_at="2026-09-30T12:02:26Z").run()
    assert first["status"] == "ok"
    assert first["vintage"].startswith("release of 2026-04-30")
    assert base.read_cache("eia_lng_exports_revisions") is None

    second = eia.LngExportsMonthly(from_file=august_file, fetched_at="2026-09-30T11:53:09Z").run()
    assert second["vintage"].startswith("release of 2026-08-31")
    # A copy read later records when it was fetched, not when it was read.
    assert second["fetched_at"] == "2026-09-30T11:53:09Z"
    logged = [e for e in base.manifest_read()["series"] if e["series"] == "eia_lng_exports_revisions"]
    assert logged[0]["fetched_at"] == "2026-09-30T11:53:09Z"
    assert second["last_date"] == "2026-06-15"
    revisions = base.read_cache("eia_lng_exports_revisions")
    assert len(revisions) > 0
    assert set(revisions["vintage_after"]) == {"2026-08-31"}
    assert (sandbox / "private" / "eia_exports" / "NG_MOVE_EXPC_S1_M_release_2026-08-31.xls").exists()


def test_an_older_release_never_replaces_a_newer_one(sandbox, tmp_path):
    newer = tmp_path / "august.xls"
    newer.write_bytes(AUGUST)
    older = tmp_path / "april.xls"
    older.write_bytes(APRIL)
    eia.LngExportsMonthly(from_file=newer, fetched_at="x").run()
    with pytest.raises(base.SourceError) as caught:
        eia.LngExportsMonthly(from_file=older, fetched_at="x").run()
    assert "older than the committed" in str(caught.value)


# --------------------------------------------------------------------------
# Henry Hub
# --------------------------------------------------------------------------

def test_henry_hub_reproduces_its_two_anchors():
    frame, released, following = eia.parse_henry_hub_workbook(HENRY_HUB)
    assert released.isoformat() == "2026-09-23"
    series = frame.set_index("date")["henry_hub_usd_mmbtu"]
    assert series[pd.Timestamp("2026-09-15")] == 2.97
    assert series[pd.Timestamp("2026-09-22")] == 2.90


def test_henry_hub_range_and_the_one_empty_row():
    frame, _, _ = eia.parse_henry_hub_workbook(HENRY_HUB)
    assert frame["date"].iloc[0] == pd.Timestamp("1997-01-07")
    assert frame["date"].iloc[-1] == pd.Timestamp("2026-09-22")
    assert len(frame) == 5693
    empty = frame[frame["henry_hub_usd_mmbtu"].isna()]
    assert empty["date"].tolist() == [pd.Timestamp("2018-01-05")]


def test_henry_hub_prints_above_25_twice_in_january_2026_and_the_bound_holds_them():
    """Two real prints above 25 USD/MMBtu. The bound is a guard against a unit
    error, set at 50 so that EIA's own prints pass and a price read in cents
    does not."""
    frame, _, _ = eia.parse_henry_hub_workbook(HENRY_HUB)
    above = frame[frame["henry_hub_usd_mmbtu"] > 25]
    assert above["date"].dt.strftime("%Y-%m-%d").tolist() == ["2026-01-23", "2026-01-26"]
    assert above["henry_hub_usd_mmbtu"].tolist() == [30.72, 25.01]
    low, high = config.BOUNDS_HENRY_HUB_USD_MMBTU
    assert frame["henry_hub_usd_mmbtu"].dropna().between(low, high).all()


def test_the_henry_hub_adapter_writes_the_workbook_and_refuses_a_price_in_cents(sandbox, tmp_path, monkeypatch):
    workbook = tmp_path / "hh.xls"
    workbook.write_bytes(HENRY_HUB)
    entry = eia.HenryHubDaily(from_file=workbook, fetched_at="2026-09-30T11:59:08Z").run()
    assert entry["status"] == "ok"
    assert entry["fetched_at"] == "2026-09-30T11:59:08Z"
    real = eia.parse_henry_hub_workbook

    def in_cents(payload):
        frame, released, following = real(payload)
        frame["henry_hub_usd_mmbtu"] = frame["henry_hub_usd_mmbtu"] * 100
        return frame, released, following

    monkeypatch.setattr(eia, "parse_henry_hub_workbook", in_cents)
    with pytest.raises(base.SourceError) as caught:
        eia.HenryHubDaily(from_file=workbook, fetched_at="x").run()
    assert "outside [0.5, 50]" in str(caught.value)

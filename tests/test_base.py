"""The shared plumbing: validation on write, caches, gaps, the manifest, the adapter, http.

No test here touches the network or the committed data directory. The sandbox
fixture in conftest.py redirects every path, and http is monkeypatched.
"""

from __future__ import annotations

import json
import re

import numpy as np
import pandas as pd
import pytest

from lngarb import config, manual_steps
from lngarb.config import Source
from lngarb.sources import base
from lngarb.sources.base import (
    Adapter,
    SourceError,
    find_gaps,
    manifest_read,
    manifest_upsert,
    read_cache,
    validate_frame,
    write_cache,
)


def frame(dates, values, col="value"):
    return pd.DataFrame({"date": pd.to_datetime(dates), col: values})


def _fake_source(series, *, frequency="weekly", method="parsed", committable=True):
    return Source(
        series=series,
        label="a test series",
        publisher="the test suite",
        page_url="https://example.invalid/",
        machine_url="https://example.invalid/data",
        url_note="none",
        frequency=frequency,
        unit="USD per MMBtu",
        method=method,
        licence="none",
        licence_note=(
            "the publisher does not permit reproduction" if not committable else "public domain"
        ),
        committable=committable,
    )


@pytest.fixture()
def registry(monkeypatch):
    """A registry holding the fake series these tests run, and nothing else."""
    entries = {
        "fake_weekly": _fake_source("fake_weekly"),
        "fetched_thing": _fake_source("fetched_thing"),
        "seeded_thing": _fake_source("seeded_thing", method="seed"),
        "restricted_thing": _fake_source("restricted_thing", committable=False),
        "long_thing": _fake_source("long_thing", frequency="monthly", method="published"),
    }
    monkeypatch.setattr(base, "SOURCES", entries)
    return entries


# --------------------------------------------------------------------------
# Paths and small helpers
# --------------------------------------------------------------------------

def test_repo_root_points_at_the_repository():
    assert (base.REPO_ROOT / "pyproject.toml").exists()
    assert (base.REPO_ROOT / "src" / "lngarb" / "sources" / "base.py").exists()
    assert base.CACHE == base.REPO_ROOT / "data" / "cache"
    assert base.PRIVATE == base.REPO_ROOT / "data" / "private"


def test_utc_now_iso_shape():
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", base.utc_now_iso())


# --------------------------------------------------------------------------
# validate_frame
# --------------------------------------------------------------------------

def test_valid_frame_has_no_problems():
    good = frame(["2026-01-07", "2026-01-14"], [10.7, 11.2])
    assert validate_frame(good, required_cols=("date", "value"), bounds={"value": (1, 120)}) == []


def test_duplicate_dates_are_caught():
    problems = validate_frame(frame(["2026-01-07", "2026-01-07"], [10.0, 11.0]))
    assert any("duplicate" in p for p in problems)


def test_a_long_frame_may_repeat_dates_but_must_stay_sorted():
    long = frame(["2026-01-01", "2026-01-01", "2026-02-01"], [1.0, 2.0, 3.0])
    assert validate_frame(long, unique_dates=False) == []
    unsorted = frame(["2026-02-01", "2026-01-01"], [1.0, 2.0])
    assert any("not increasing" in p for p in validate_frame(unsorted, unique_dates=False))


def test_non_monotonic_dates_are_caught():
    problems = validate_frame(frame(["2026-01-14", "2026-01-07"], [10.0, 11.0]))
    assert any("not increasing" in p for p in problems)


def test_out_of_bounds_value_is_caught_and_nan_is_not():
    bounds = {"value": config.BOUNDS_LNG_USD_MMBTU}
    bad = frame(["2026-01-07", "2026-01-14"], [10.0, 150.0])
    assert any("outside" in p for p in validate_frame(bad, bounds=bounds))
    missing = frame(["2026-01-07", "2026-01-14"], [10.0, np.nan])
    assert validate_frame(missing, bounds=bounds) == []


def test_the_bounds_are_the_ones_the_methodology_names():
    """docs/methodology.md states these ranges; a change must fail here by name."""
    assert config.BOUNDS_LNG_USD_MMBTU == (1.0, 120.0)
    assert config.BOUNDS_HENRY_HUB_USD_MMBTU == (0.5, 25.0)
    assert config.BOUNDS_USD_PER_EUR == (0.8, 1.7)
    assert config.BOUNDS_HIRE_USD_DAY == (-10000.0, 500000.0)
    assert config.BOUNDS_DES_SPREAD_EUR_MWH == (-20.0, 5.0)


def test_shrinking_row_count_is_caught():
    old = frame(["2026-01-07", "2026-01-14", "2026-01-21"], [1.0, 2.0, 3.0])
    new = frame(["2026-01-07", "2026-01-14"], [1.0, 2.0])
    assert any("shrank" in p for p in validate_frame(new, previous=old))
    assert any("shrank" in p for p in validate_frame(new, previous=3))


def test_missing_columns_and_min_rows_are_caught():
    problems = validate_frame(frame([], []), required_cols=("date", "jkm"), min_rows=1)
    assert any("jkm" in p for p in problems)
    assert any("below the minimum" in p for p in problems)


def test_unparseable_date_is_caught():
    bad = pd.DataFrame({"date": ["2026-01-07", "not a date"], "value": [1.0, 2.0]})
    assert any("do not parse" in p for p in validate_frame(bad))


def test_validate_frame_rejects_non_frames():
    assert validate_frame([1, 2, 3]) == ["expected a DataFrame, got list"]


def test_an_all_nan_column_is_refused_and_an_eroding_one_too():
    blank = frame(["2026-01-07", "2026-01-14"], [np.nan, np.nan])
    problems = validate_frame(blank, min_observations={"value": 1})
    assert any("0 observation(s)" in p for p in problems)

    before = frame(["2026-01-07", "2026-01-14", "2026-01-21"], [1.0, 2.0, 3.0])
    after = frame(["2026-01-07", "2026-01-14", "2026-01-21"], [1.0, np.nan, 3.0])
    problems = validate_frame(after, min_observations={"value": 1}, previous=before)
    assert any("shrank from 3 to 2" in p for p in problems)


def test_a_blank_text_cell_is_not_an_observation():
    assert base.observation_count(pd.Series(["a", "", "  ", None, "b"])) == 2


# --------------------------------------------------------------------------
# Gaps
# --------------------------------------------------------------------------

def test_daily_gaps_find_the_hole_and_ignore_the_weekend():
    dates = ["2026-09-14", "2026-09-15", "2026-09-17", "2026-09-18", "2026-09-21"]
    assert find_gaps(dates, "daily") == ["2026-09-16"]


def test_weekly_gaps_are_reported_as_the_monday_of_the_missing_week():
    dates = ["2026-01-07", "2026-01-21"]
    assert find_gaps(dates, "weekly") == ["2026-01-12"]


def test_a_release_that_slips_a_day_for_a_holiday_is_not_a_weekly_gap():
    dates = ["2025-12-17", "2025-12-23", "2025-12-31"]
    assert find_gaps(dates, "weekly") == []


def test_monthly_and_annual_gaps():
    assert find_gaps(["2020-01-01", "2020-04-01"], "monthly") == ["2020-02-01", "2020-03-01"]
    assert find_gaps(["2018-06-30", "2021-01-31"], "annual") == ["2019-01-01", "2020-01-01"]


def test_gaps_of_a_short_or_empty_series_are_empty():
    assert find_gaps([], "weekly") == []
    assert find_gaps(["2026-01-07"], "monthly") == []


def test_an_unknown_frequency_raises_rather_than_guessing():
    with pytest.raises(ValueError):
        find_gaps(["2026-01-07", "2026-01-21"], "fortnightly")


# --------------------------------------------------------------------------
# Caches
# --------------------------------------------------------------------------

def test_write_then_read_cache_round_trips_including_nan(sandbox):
    original = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-01-07", "2026-01-14", "2026-01-21"]),
            "value": [10.73, np.nan, 1201.7159025169021],
            "text": ["as printed", "", "$34.420MBtu"],
        }
    )
    write_cache("round_trip", original)
    back = read_cache("round_trip")
    assert back["date"].tolist() == original["date"].tolist()
    assert back["value"].iloc[0] == 10.73
    assert np.isnan(back["value"].iloc[1])
    assert back["value"].iloc[2] == 1201.7159025169021
    assert back["text"].iloc[2] == "$34.420MBtu"


def test_read_cache_returns_none_when_absent(sandbox):
    assert read_cache("nothing_here") is None


def test_write_cache_avoids_scientific_notation(sandbox):
    write_cache("tiny", frame(["2026-01-07"], [0.00000012]))
    text = (base.CACHE / "tiny.csv").read_text(encoding="utf-8")
    assert "e-" not in text and "0.00000012" in text


def test_write_cache_writes_lf_and_leaves_no_temporary_file(sandbox):
    write_cache("lf", frame(["2026-01-07", "2026-01-14"], [1.0, 2.0]))
    raw = (base.CACHE / "lf.csv").read_bytes()
    assert b"\r" not in raw
    assert [p.name for p in base.CACHE.iterdir()] == ["lf.csv"]


def test_write_cache_is_byte_stable(sandbox):
    data = frame(["2026-01-07", "2026-01-14"], [16.1, 12.91])
    write_cache("stable", data)
    first = (base.CACHE / "stable.csv").read_bytes()
    write_cache("stable", read_cache("stable"))
    assert (base.CACHE / "stable.csv").read_bytes() == first


def test_cache_names_must_be_plain():
    with pytest.raises(ValueError):
        base._cache_path("../escape")
    with pytest.raises(ValueError):
        base._cache_path("fine", directory="elsewhere")


# --------------------------------------------------------------------------
# Manifest
# --------------------------------------------------------------------------

def _entry(**overrides):
    entry = {
        "series": "fake_weekly",
        "status": "ok",
        "method": "parsed",
        "committable": True,
        "machine_fetched": True,
        "fetched_at": "2026-09-30T10:00:00Z",
        "licence_note": "public domain",
    }
    entry.update(overrides)
    return entry


def test_manifest_read_on_a_missing_file_is_empty(sandbox):
    payload = manifest_read()
    assert payload["series"] == []
    assert payload["schema_version"] == base.MANIFEST_SCHEMA_VERSION


def test_manifest_upsert_round_trips_and_preserves_other_entries(sandbox):
    manifest_upsert(_entry(series="b_series"))
    manifest_upsert(_entry(series="a_series"))
    manifest_upsert(_entry(series="b_series", note="second run"))
    series = manifest_read()["series"]
    assert [e["series"] for e in series] == ["a_series", "b_series"]
    assert series[1]["note"] == "second run"
    for key in base.ENTRY_KEYS:
        assert key in series[0]


def test_every_manifest_write_reattaches_the_manual_steps(sandbox, monkeypatch):
    step = {
        "id": "a_step",
        "series": ["fake_weekly"],
        "what": "collect a file by hand",
        "why": "the site forbids automated access",
        "cost_if_skipped": "a gap",
        "how": "download it",
        "cadence": "weekly",
        "status": "standing",
    }
    monkeypatch.setattr(manual_steps, "MANUAL_STEPS", (step,))
    manifest_upsert(_entry())
    payload = manifest_read()
    assert payload["series"][0]["manual_step"][0]["id"] == "a_step"
    assert "series" not in payload["series"][0]["manual_step"][0]
    assert payload["manual_steps"][0]["id"] == "a_step"


def test_attaching_the_manual_steps_twice_changes_nothing():
    payload = {"series": [{"series": "x"}]}
    once = json.dumps(manual_steps.apply(json.loads(json.dumps(payload))), sort_keys=True)
    twice = json.dumps(
        manual_steps.apply(manual_steps.apply(json.loads(json.dumps(payload)))), sort_keys=True
    )
    assert once == twice


@pytest.mark.parametrize(
    "overrides, message",
    [
        ({"status": "fine"}, "status"),
        ({"method": None}, "method"),
        ({"committable": "yes"}, "committable"),
        ({"committable": False, "licence_note": ""}, "licence_note"),
        ({"machine_fetched": False}, "fetched_at"),
    ],
)
def test_manifest_upsert_refuses_entries_that_would_lie(sandbox, overrides, message):
    with pytest.raises(ValueError) as caught:
        manifest_upsert(_entry(**overrides))
    assert message in str(caught.value)


def test_manifest_is_written_lf(sandbox):
    manifest_upsert(_entry())
    assert b"\r" not in base.MANIFEST.read_bytes()


# --------------------------------------------------------------------------
# Adapter
# --------------------------------------------------------------------------

class FakeAdapter(Adapter):
    name = "fake_weekly"
    source = "test fixture"
    url = "https://example.invalid/fixture"
    page_url = "https://example.invalid/"
    unit = "USD per MMBtu"
    frequency = "weekly"
    method = "parsed"
    required_cols = ("date", "value")
    bounds = {"value": config.BOUNDS_LNG_USD_MMBTU}
    min_observations = {"value": 1}
    observation_column = "value"

    def __init__(self, payload):
        self.payload = payload

    def fetch(self):
        if isinstance(self.payload, Exception):
            raise self.payload
        return self.payload


def test_adapter_run_writes_cache_and_an_ok_entry(sandbox, registry):
    good = frame(["2026-01-07", "2026-01-14", "2026-01-28"], [10.7, 11.2, 11.9])
    result = FakeAdapter(good).run()
    assert result["status"] == "ok"
    assert result["rows"] == result["observations"] == result["file_rows"] == 3
    assert (result["first_date"], result["last_date"]) == ("2026-01-07", "2026-01-28")
    assert result["gaps"] == ["2026-01-19"]
    assert result["file"] == "data/cache/fake_weekly.csv"
    assert (base.CACHE / "fake_weekly.csv").exists()


def test_a_failed_fetch_leaves_the_previous_cache_untouched(sandbox, registry):
    FakeAdapter(frame(["2026-01-07", "2026-01-14"], [10.7, 11.2])).run()
    before = (base.CACHE / "fake_weekly.csv").read_bytes()

    with pytest.raises(SourceError):
        FakeAdapter(SourceError("eia.gov returned HTTP 503")).run()

    assert (base.CACHE / "fake_weekly.csv").read_bytes() == before
    recorded = manifest_read()["series"][0]
    assert recorded["status"] == "failed"
    assert "503" in recorded["note"]
    assert "previous cache kept unchanged" in recorded["note"]
    assert recorded["rows"] == 2
    assert recorded["last_date"] == "2026-01-14"


def test_adapter_run_refuses_a_shrunk_an_out_of_bounds_and_an_all_nan_frame(sandbox, registry):
    FakeAdapter(frame(["2026-01-07", "2026-01-14"], [10.7, 11.2])).run()
    before = (base.CACHE / "fake_weekly.csv").read_bytes()
    for bad, words in (
        (frame(["2026-01-07"], [10.7]), "shrank"),
        (frame(["2026-01-07", "2026-01-14"], [10.7, 400.0]), "outside"),
        (frame(["2026-01-07", "2026-01-14", "2026-01-21"], [np.nan] * 3), "0 observation(s)"),
    ):
        with pytest.raises(SourceError) as caught:
            FakeAdapter(bad).run()
        assert words in str(caught.value)
        assert (base.CACHE / "fake_weekly.csv").read_bytes() == before


def test_an_adapter_that_bounds_a_column_without_flooring_it_is_refused(sandbox, registry):
    class Unfloored(Adapter):
        name = "fetched_thing"
        frequency = "weekly"
        method = "parsed"
        bounds = {"value": (0.0, 10.0)}

        def fetch(self):  # pragma: no cover, run() raises before this
            raise AssertionError("fetch() must not be reached")

    with pytest.raises(SourceError) as caught:
        Unfloored().run()
    assert "min_observations" in str(caught.value)


def test_an_unregistered_adapter_is_refused(sandbox, registry):
    class Stray(Adapter):
        name = "not_in_the_registry"
        frequency = "weekly"
        method = "parsed"

        def fetch(self):  # pragma: no cover
            raise AssertionError("fetch() must not be reached")

    with pytest.raises(SourceError) as caught:
        Stray().run()
    assert "not registered" in str(caught.value)


def test_an_adapter_may_not_disagree_with_the_source_registry(sandbox, registry):
    class Wrong(Adapter):
        name = "restricted_thing"
        frequency = "weekly"
        method = "parsed"
        committable = True

        def fetch(self):  # pragma: no cover
            raise AssertionError("fetch() must not be reached")

    with pytest.raises(SourceError) as caught:
        Wrong().run()
    assert "committable" in str(caught.value)


def test_where_the_bytes_land_follows_the_declarations(sandbox, registry):
    payload = frame(["2026-01-07", "2026-01-14"], [1.0, 2.0])

    class Common(Adapter):
        frequency = "weekly"
        method = "parsed"
        observation_column = "value"
        min_observations = {"value": 1}
        bounds = {"value": (0.0, 10.0)}

        def fetch(self):
            return payload.copy()

    class Fetched(Common):
        name = "fetched_thing"

    class Seeded(Common):
        name = "seeded_thing"
        method = "seed"
        machine_fetched = False

    class Restricted(Common):
        name = "restricted_thing"
        committable = False
        licence_note = "the publisher does not permit reproduction"

    assert Fetched().run()["file"] == "data/cache/fetched_thing.csv"
    assert Seeded().run()["file"] == "data/seed/seeded_thing.csv"
    assert Restricted().run()["file"] == "data/private/restricted_thing.csv"
    assert not (sandbox / "cache" / "restricted_thing.csv").exists()

    entries = {e["series"]: e for e in manifest_read()["series"]}
    assert entries["seeded_thing"]["fetched_at"] is None
    assert entries["seeded_thing"]["checked_at"]
    assert entries["fetched_thing"]["checked_at"] is None


def test_a_long_frame_counts_its_dates_not_its_rows(sandbox, registry):
    class Long(Adapter):
        name = "long_thing"
        frequency = "monthly"
        method = "published"
        unique_dates = False
        observation_column = "value"
        min_observations = {"value": 1}
        bounds = {"value": (0.0, 10.0)}

        def fetch(self):
            return frame(["2026-01-01", "2026-01-01", "2026-03-01"], [1.0, 2.0, 3.0])

    entry = Long().run()
    assert entry["file_rows"] == 3
    assert entry["observations"] == 2
    assert entry["gaps"] == ["2026-02-01"]


# --------------------------------------------------------------------------
# robots.txt, RFC 9309 matching, against EIA's file as served on 2026-09-30
# --------------------------------------------------------------------------

FIXTURES_DIR = base.REPO_ROOT / "tests" / "fixtures"
EIA_ROBOTS = (FIXTURES_DIR / "eia_robots_2026-09-30.txt").read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "url, allowed",
    [
        # the weekly update archive, closed to code
        ("https://www.eia.gov/naturalgas/weekly/archivenew_ngwu/2023/12_07/", False),
        ("https://www.eia.gov/naturalgas/weekly/archivenew_ngwu/2021/12_16", False),
        # its successor's archive, caught by the wildcard rule
        ("https://www.eia.gov/naturalgas/weekly/supplement/archive/2026/09/17", False),
        ("https://www.eia.gov/beta/naturalgas/weekly/supplement/", False),
        # what the study does read
        ("https://www.eia.gov/naturalgas/weekly/", True),
        ("https://www.eia.gov/naturalgas/weekly/includes/archive.php", True),
        ("https://www.eia.gov/naturalgas/weekly/supplement/content/bullets_lng_2.html", True),
        ("https://www.eia.gov/dnav/ng/xls/NG_MOVE_EXPC_S1_M.xls", True),
        ("https://www.eia.gov/dnav/ng/hist_xls/RNGWHHDd.xls", True),
        ("https://www.eia.gov/about/copyrights_reuse.php", True),
        ("https://www.eia.gov/todayinenergy/detail.php?id=61363", True),
        # an Allow longer than the Disallow it sits under
        ("https://www.eia.gov/reports/upcoming.php", True),
        ("https://www.eia.gov/reports/other.php", False),
        ("https://www.eia.gov/beta/international/data/", True),
    ],
)
def test_eia_robots_is_read_with_longest_match(url, allowed):
    rules = base.parse_robots(EIA_ROBOTS, "Mozilla")
    assert base.robots_allows(rules, url) is allowed


def test_the_standard_library_parser_would_have_crawled_the_archive():
    """The reason this module parses robots.txt itself."""
    from urllib.robotparser import RobotFileParser

    parser = RobotFileParser()
    parser.parse(EIA_ROBOTS.splitlines())
    archive = "https://www.eia.gov/naturalgas/weekly/archivenew_ngwu/2023/12_07/"
    assert parser.can_fetch("*", archive) is True
    assert base.robots_allows(base.parse_robots(EIA_ROBOTS, "Mozilla"), archive) is False


def test_robots_groups_wildcards_and_anchors():
    text = "\n".join(
        [
            "User-agent: jkm-ttf-arbitrage",
            "Disallow: /private",
            "",
            "User-agent: *",
            "Disallow: /",
            "Allow: /data/*.csv$",
            "Allow: /page",
        ]
    )
    ours = base.parse_robots(text, "jkm-ttf-arbitrage")
    assert base.robots_allows(ours, "https://h.example/private/x") is False
    assert base.robots_allows(ours, "https://h.example/anything") is True

    anyone = base.parse_robots(text, "Mozilla")
    assert base.robots_allows(anyone, "https://h.example/data/a/b.csv") is True
    assert base.robots_allows(anyone, "https://h.example/data/a/b.csv?x=1") is False
    assert base.robots_allows(anyone, "https://h.example/data/b.json") is False
    assert base.robots_allows(anyone, "https://h.example/page/2") is True
    assert base.robots_allows(anyone, "https://h.example/") is False


def test_an_empty_or_missing_robots_file_allows_everything():
    assert base.robots_allows(base.parse_robots("", "Mozilla"), "https://h.example/x") is True


def test_http_get_refuses_a_disallowed_url_without_requesting_it(monkeypatch):
    requested = []

    def fake_get(url, headers=None, timeout=None):
        requested.append(url)
        response = FakeResponse(200)
        response.text = EIA_ROBOTS
        return response

    monkeypatch.setattr(base.requests, "get", fake_get)
    monkeypatch.setattr(base.time, "sleep", lambda _s: None)
    monkeypatch.setattr(base, "_ROBOTS_CACHE", {})
    with pytest.raises(base.RobotsDisallowed):
        base.http_get("https://www.eia.gov/naturalgas/weekly/archivenew_ngwu/2023/12_07/")
    assert requested == ["https://www.eia.gov/robots.txt"]


def test_an_unreadable_robots_file_is_a_complete_disallow(monkeypatch):
    monkeypatch.setattr(
        base.requests, "get", lambda url, headers=None, timeout=None: FakeResponse(503)
    )
    monkeypatch.setattr(base, "_ROBOTS_CACHE", {})
    with pytest.raises(base.RobotsDisallowed):
        base.check_robots("https://h.example/data.csv", base.USER_AGENT)


# --------------------------------------------------------------------------
# http, no network
# --------------------------------------------------------------------------

class FakeResponse:
    def __init__(self, status_code):
        self.status_code = status_code
        self.headers = {}
        self.text = "body"


@pytest.fixture()
def robots_allow_all(monkeypatch):
    """The retry tests are about retries, so robots.txt is taken as allowing."""
    monkeypatch.setattr(base, "check_robots", lambda url, user_agent: None)


def test_http_get_retries_a_503_then_succeeds(monkeypatch, robots_allow_all):
    seen = []

    def fake_get(url, headers=None, timeout=None):
        seen.append(headers["User-Agent"])
        return FakeResponse(503 if len(seen) < 3 else 200)

    monkeypatch.setattr(base.requests, "get", fake_get)
    monkeypatch.setattr(base.time, "sleep", lambda _s: None)
    assert base.http_get("https://example.invalid/x").status_code == 200
    assert len(seen) == 3


def test_http_get_gives_up_and_names_the_url_and_status(monkeypatch, robots_allow_all):
    monkeypatch.setattr(base.requests, "get", lambda url, headers=None, timeout=None: FakeResponse(503))
    monkeypatch.setattr(base.time, "sleep", lambda _s: None)
    with pytest.raises(SourceError) as caught:
        base.http_get("https://example.invalid/y", retries=2)
    assert "https://example.invalid/y" in str(caught.value)
    assert "503" in str(caught.value)


def test_http_get_does_not_retry_a_403(monkeypatch, robots_allow_all):
    calls = []

    def fake_get(url, headers=None, timeout=None):
        calls.append(url)
        return FakeResponse(403)

    monkeypatch.setattr(base.requests, "get", fake_get)
    monkeypatch.setattr(base.time, "sleep", lambda _s: None)
    with pytest.raises(SourceError):
        base.http_get("https://example.invalid/z")
    assert len(calls) == 1


def test_head_is_refused_for_eia_because_it_answers_503_to_head(monkeypatch):
    def boom(*_a, **_k):  # pragma: no cover
        raise AssertionError("no request may be made")

    monkeypatch.setattr(base.requests, "head", boom)
    with pytest.raises(SourceError) as caught:
        base.http_head("https://www.eia.gov/dnav/ng/xls/NG_MOVE_EXPC_S1_M.xls")
    assert "503" in str(caught.value)


def test_manifest_remove_drops_one_entry_and_keeps_the_rest(sandbox):
    manifest_upsert(_entry(series="a_series"))
    manifest_upsert(_entry(series="b_series"))
    assert base.manifest_remove("a_series") is True
    assert [e["series"] for e in manifest_read()["series"]] == ["b_series"]
    assert base.manifest_remove("a_series") is False
    assert b"\r" not in base.MANIFEST.read_bytes()

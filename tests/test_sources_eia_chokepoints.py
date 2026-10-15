"""EIA's chokepoint tables, from the two pages as fetched on 15 October 2026."""

from __future__ import annotations

import math

import pandas as pd
import pytest

from lngarb.sources import base, eia_chokepoints
from lngarb.sources.base import SourceError

FIXTURES = base.REPO_ROOT / "tests" / "fixtures"
CHOKEPOINTS = FIXTURES / "eia_chokepoints_2026-03-03_fetched_2026-10-15.html"
STEO = FIXTURES / "eia_steo_energysecurity_2026-08-12_fetched_2026-10-15.html"


def test_the_annual_page_gives_seven_chokepoints_for_five_years_and_a_first_half():
    frame, updated = eia_chokepoints.parse_annual(CHOKEPOINTS.read_bytes())
    assert updated == "March 3, 2026"
    assert len(frame) == 42 and sorted(set(frame["chokepoint"])) == [
        "Bab el-Mandeb Strait", "Cape of Good Hope", "Danish Straits", "Strait of Hormuz", "Strait of Malacca",
        "Suez Canal", "Turkish Straits"]
    suez = frame[frame["chokepoint"] == "Suez Canal"].set_index("date")["bcf_per_day"]
    assert suez[pd.Timestamp("2023-01-01")] == 4.1 and suez[pd.Timestamp("2024-01-01")] == 0.5
    half = frame[(frame["period"] == "first_half")]
    assert set(half["date"]) == {pd.Timestamp("2025-01-01")} and len(half) == 7
    cape = frame[(frame["chokepoint"] == "Cape of Good Hope") & (frame["period"] == "year")].set_index("date")["bcf_per_day"]
    assert cape[pd.Timestamp("2024-01-01")] == 7.8


def test_the_outlook_article_gives_eight_chokepoints_by_quarter_with_dashes_missing():
    frame, released = eia_chokepoints.parse_quarterly(STEO.read_bytes())
    assert released == {"article": "August 12, 2026", "outlook": "October 6, 2026"}
    assert len(frame) == 48 and "Panama Canal" in set(frame["chokepoint"])
    assert frame["date"].min() == pd.Timestamp("2025-01-01") and frame["date"].max() == pd.Timestamp("2026-04-01")
    hormuz = frame[frame["chokepoint"] == "Strait of Hormuz"].set_index("date")["bcf_per_day"]
    assert hormuz[pd.Timestamp("2025-10-01")] == 10.5 and hormuz[pd.Timestamp("2026-04-01")] == 0.8
    mandeb = frame[frame["chokepoint"] == "Bab el-Mandeb Strait"].set_index("date")["bcf_per_day"]
    assert math.isnan(mandeb[pd.Timestamp("2025-04-01")]) and mandeb[pd.Timestamp("2026-01-01")] == 3.0


def test_an_unknown_chokepoint_or_a_page_without_rows_is_refused():
    with pytest.raises(SourceError, match="no 'LNG flows' row"):
        eia_chokepoints.parse_annual("<html>Last Updated: March 3, 2026<table><tr><td>Oil</td><td>1</td></tr></table></html>")
    with pytest.raises(SourceError, match="does not know"):
        eia_chokepoints.parse_annual("<html>Last Updated: March 3, 2026<table><tr><th>x</th><th>2020</th></tr>"
                                     "<tr><td>LNG flows through the Bosporus</td><td>1</td></tr></table></html>")


def test_the_two_adapters_run_from_the_fixtures_and_declare_long_frames():
    annual = eia_chokepoints.EiaChokepointLngAnnual(from_file=str(CHOKEPOINTS), fetched_at="2026-10-15T13:20:00Z")
    quarterly = eia_chokepoints.EiaSteoChokepointLngQuarterly(from_file=str(STEO), fetched_at="2026-10-15T13:20:00Z")
    assert not annual.unique_dates and not quarterly.unique_dates
    assert annual.frequency == "annual" and quarterly.frequency == "quarterly"
    a = annual.fetch()
    q = quarterly.fetch()
    assert len(a) == 42 and len(q) == 48
    assert "page last updated March 3, 2026" in annual.note and "dash is missing" in quarterly.note

"""Test 14 in part: the committed routes seed, checked from its own geometry.

The seed was computed once with searoute 1.6.0 by scripts/routes.py. These tests
need neither searoute nor the network: they read the committed files and check
them with lngarb.sea_routes, which measures the lines itself.
"""

from __future__ import annotations

import json
import math

import pytest

from lngarb import sea_routes
from lngarb.sources import base


@pytest.fixture(scope="module")
def committed():
    document = json.loads(sea_routes.routes_json().read_text(encoding="utf-8"))
    geojson = json.loads(sea_routes.routes_geojson().read_text(encoding="utf-8"))
    return document, geojson


def test_the_committed_seed_passes_every_check_it_is_held_to(committed):
    assert sea_routes.route_problems(*committed) == []


def test_the_seed_records_the_library_the_points_and_the_restrictions(committed):
    document, _ = committed
    assert document["library"]["name"] == "searoute"
    assert document["library"]["version"] == "1.6.0"
    assert document["points"]["sabine_pass"] == {"lon": -93.87, "lat": 29.74, "name": "Sabine Pass LNG, Louisiana"}
    assert document["points"]["gate"]["lon"] == 4.03 and document["points"]["gate"]["lat"] == 51.96
    assert document["points"]["futtsu"]["lon"] == 139.82 and document["points"]["futtsu"]["lat"] == 35.30
    restrictions = {r["id"]: r["restrictions"] for r in document["routes"]}
    assert restrictions == {
        "nwe_direct": ["northwest"],
        "nea_panama": ["northwest", "suez", "south_africa", "chili"],
        "nea_suez": ["northwest", "panama", "south_africa", "chili"],
        "nea_cape": ["northwest", "panama", "suez", "babalmandab", "chili"],
    }


def test_the_distances_and_the_passages_each_route_takes(committed):
    document, _ = committed
    routes = {r["id"]: r for r in document["routes"]}
    assert routes["nwe_direct"]["distance_nm"] == 4979.2
    assert routes["nea_panama"]["distance_nm"] == 9305.9
    assert routes["nea_suez"]["distance_nm"] == 14624.2
    assert routes["nea_cape"]["distance_nm"] == 15824.8
    assert routes["nea_panama"]["passages_reported_by_searoute"] == ["panama"]
    assert set(routes["nea_suez"]["passes"]) >= {"Suez Canal", "Strait of Malacca"}
    assert set(routes["nea_cape"]["passes"]) >= {"Cape of Good Hope", "Sunda Strait"}
    assert routes["nea_panama"]["crosses_antimeridian"] is True


def test_the_extra_distances_east_keep_the_ratio_a_speed_does_not_change(committed):
    document, _ = committed
    d = {r["id"]: r["distance_nm"] for r in document["routes"]}
    ratio = (d["nea_suez"] - d["nea_panama"]) / (d["nea_cape"] - d["nea_panama"])
    assert round(ratio, 2) == 0.82


def test_a_line_drawn_past_the_antimeridian_is_measured_correctly():
    """Regression: wrapping each vertex separately once put a Pacific crossing
    79 nm from the Dover Strait. A segment is wrapped once, as a whole."""
    pacific = [[-177.342032, 49.360999], [-180.0, 50.0], [-185.0, 50.5]]
    dover = sea_routes.REFERENCE_POINTS["Dover Strait"]
    assert sea_routes.nearest_distance_nm(pacific, dover) > 3000
    # and the same line is still close to a point it does pass
    near = {"lon": -180.0, "lat": 50.1}
    assert sea_routes.nearest_distance_nm(pacific, near) < 10


def test_great_circle_length_of_one_degree_of_latitude():
    assert math.isclose(sea_routes.polyline_length_nm([[0.0, 0.0], [0.0, 1.0]]), 60.04, abs_tol=0.01)


def test_a_route_that_misses_its_strait_or_takes_an_avoided_one_is_reported(committed):
    document, geojson = committed
    broken = json.loads(json.dumps(geojson))
    for feature in broken["features"]:
        if feature["id"] == "nwe_direct":
            # push the whole line 5 degrees south, away from Dover
            feature["geometry"]["coordinates"] = [[x, y - 5.0] for x, y in feature["geometry"]["coordinates"]]
    problems = sea_routes.route_problems(document, broken)
    assert any("nwe_direct should pass Dover Strait" in p for p in problems)


def test_the_seed_is_recorded_in_the_manifest_with_a_check_time_and_no_fetch_time(sandbox, monkeypatch, committed):
    document, geojson = committed
    seed = base.SEED
    seed.mkdir(parents=True, exist_ok=True)
    sea_routes.write_json(seed / "routes.json", document)
    sea_routes.write_json(seed / "routes.geojson", geojson)
    entry = sea_routes.record_routes()
    assert entry["status"] == "ok"
    assert entry["fetched_at"] is None and entry["checked_at"]
    assert entry["files"] == ["data/seed/routes.geojson"]
    assert entry["rows"] == 4

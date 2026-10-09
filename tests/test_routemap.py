"""The Routes view's map, table and timeline: drawn from the lines the distances are measured on."""

from __future__ import annotations

import json
import re
from datetime import date, timedelta

import pytest

from lngarb import routemap
from lngarb.sources import base

DATA = base.REPO_ROOT / "data"


@pytest.fixture(scope="module")
def routes():
    return json.loads((DATA / "routes.json").read_text(encoding="utf-8"))


def test_the_land_decodes_to_closed_rings_inside_the_globe():
    topology = json.loads(routemap.LAND.read_text(encoding="utf-8"))
    polygons = routemap.decode_topojson(topology)
    assert len(polygons) > 100
    for polygon in polygons:
        for ring in polygon:
            assert ring[0] == pytest.approx(ring[-1], abs=1e-9)
            assert all(-180.0 - 1e-6 <= lon <= 180.0 + 1e-6 and -90.0 - 1e-6 <= lat <= 90.0 + 1e-6 for lon, lat in ring)


def _land_rings(d):
    """The closed rings of an SVG path made of M, L and Z only."""
    rings, ring = [], []
    for token in re.findall(r"[MLZ]|-?\d+(?:\.\d+)?", d):
        if token in ("M", "Z"):
            if ring:
                rings.append(ring)
            ring = []
        elif token != "L":
            ring.append(float(token))
    if ring:
        rings.append(ring)
    return [list(zip(r[0::2], r[1::2])) for r in rings]


def _winding(rings, x, y):
    """The nonzero winding number of the land path at a map point."""
    total = 0
    for ring in rings:
        for (x0, y0), (x1, y1) in zip(ring, ring[1:] + ring[:1]):
            cross = (x1 - x0) * (y - y0) - (x - x0) * (y1 - y0)
            if y0 <= y < y1 and cross > 0:
                total += 1
            elif y1 <= y < y0 and cross < 0:
                total -= 1
    return total


@pytest.fixture(scope="module")
def land_rings():
    topology = json.loads(routemap.LAND.read_text(encoding="utf-8"))
    return _land_rings(routemap.land_path(topology))


def test_no_land_edge_jumps_across_the_map(land_rings):
    """A ring that crosses the antimeridian is unwrapped, not drawn across the plane."""
    width, _ = routemap.project(routemap.LON_MAX, routemap.LAT_MAX)
    for ring in land_rings:
        for (x0, _), (x1, _) in zip(ring, ring[1:] + ring[:1]):
            assert abs(x1 - x0) < width / 4


@pytest.mark.parametrize("lon, lat", [
    (2.0, 67.0),        # the Norwegian Sea
    (-58.0, 67.0),      # the Davis Strait
    (-20.0, -16.3),     # the South Atlantic
    (-140.0, -16.3),    # the South Pacific
    (80.0, -16.3),      # the Indian Ocean
    (-175.0, 58.0),     # the Bering Sea
    (-200.0, 10.0),     # the western Pacific, drawn a turn west
])
def test_the_oceans_are_not_land(land_rings, lon, lat):
    assert _winding(land_rings, *routemap.project(lon, lat)) == 0


@pytest.mark.parametrize("lon, lat", [
    (2.35, 48.85),          # Paris
    (-98.0, 38.0),          # Kansas
    (116.0, 40.0),          # Beijing
    (139.7 - 360.0, 36.5),  # Honshu, a turn west at the Pacific edge
    (175.0 - 360.0, 66.0),  # Chukotka west of the antimeridian, a turn west
    (-174.0, 66.5),         # Chukotka east of it
])
def test_the_land_is_land(land_rings, lon, lat):
    assert _winding(land_rings, *routemap.project(lon, lat)) != 0


def test_a_ring_round_a_pole_is_closed_along_it():
    ring = [(-180.0, -70.0), (-90.0, -75.0), (0.0, -70.0), (90.0, -75.0), (180.0, -70.0)]
    out = routemap.unwrap(ring)
    assert out[-2:] == [(180.0, -90.0), (-180.0, -90.0)]
    assert routemap.unwrap([(179.0, 1.0), (-179.0, 1.0), (-179.0, 2.0), (179.0, 1.0)]) == [
        (179.0, 1.0), (181.0, 1.0), (181.0, 2.0), (179.0, 1.0)]


def test_the_projection_puts_the_corners_where_the_map_says():
    assert routemap.project(routemap.LON_MIN, routemap.LAT_MAX) == (0.0, 0.0)
    width, height = routemap.project(routemap.LON_MAX, routemap.LAT_MIN)
    assert width == pytest.approx((routemap.LON_MAX - routemap.LON_MIN) * routemap.PX_PER_DEGREE)
    assert height == pytest.approx((routemap.LAT_MAX - routemap.LAT_MIN) * routemap.PX_PER_DEGREE)


def test_futtsu_is_at_both_edges_and_every_route_is_drawn(routes):
    futtsu = [p for p in routes["map"]["ports"] if p["id"] == "futtsu"]
    assert len(futtsu) == 2
    xs = sorted(p["x"] for p in futtsu)
    assert xs[0] < routes["map"]["width"] * 0.1 and xs[1] > routes["map"]["width"] * 0.9
    assert {r["id"] for r in routes["map"]["routes"]} == {"nwe_direct", "nea_panama", "nea_suez", "nea_cape"}
    for route in routes["map"]["routes"]:
        assert route["d"].startswith("M")
        assert 0 <= route["label_x"] <= routes["map"]["width"] and 0 <= route["label_y"] <= routes["map"]["height"]


def test_the_table_is_the_engine_s_for_the_latest_week(routes):
    now = json.loads((DATA / "now.json").read_text(encoding="utf-8"))
    lines = {"nwe_direct": now["result"]["west"], **now["result"]["east"]}
    for row in routes["rows"]:
        assert row["distance_nm"] == lines[row["route"]]["distance_nm"]
        assert row["days_total"] == lines[row["route"]]["days_total"]
        assert row["open"] == lines[row["route"]]["open"]


def test_the_timeline_bands_tile_each_row_and_carry_a_source(routes):
    first = date.fromisoformat(routes["timeline"]["first"])
    last = date.fromisoformat(routes["timeline"]["last"])
    for row in routes["timeline"]["rows"]:
        bands = row["bands"]
        assert date.fromisoformat(bands[0]["start"]) == first
        assert date.fromisoformat(bands[-1]["end"]) == last
        for before, after in zip(bands, bands[1:]):
            assert (date.fromisoformat(after["start"]) - date.fromisoformat(before["end"])).days == 1, row["route"]
        for band in bands:
            assert band["source"] and band["words"] and band["state_words"]
            assert band["state"] in ("open", "closed", "restricted", "unknown")
    (suez,) = [r for r in routes["timeline"]["rows"] if r["route"] == "nea_suez"]
    states = [(b["start"], b["state"]) for b in suez["bands"]]
    assert states[0] == ("2016-01-01", "unknown") and ("2021-01-01", "open") in states
    assert ("2024-01-13", "closed") in states
    assert all(b["status"] == "assumption" for b in suez["bands"] if b["state"] == "closed")
    (panama,) = [r for r in routes["timeline"]["rows"] if r["route"] == "nea_panama"]
    assert panama["bands"][0]["state"] == "closed" and panama["bands"][1]["start"] == "2016-06-26"
    assert {b["state"] for b in panama["bands"][1:]} == {"open", "restricted"}


def _in_record(start, text):
    """A band's first day as docs/methodology.md writes it: '26 Jun 2016',
    'June 2024', or a bare year for the first of January."""
    day = date.fromisoformat(start)
    forms = ["%d %s %d" % (day.day, day.strftime("%b"), day.year)]
    if day.day == 1:
        forms.append("%s %d" % (day.strftime("%B"), day.year))
        if day.month == 1:
            forms.append("| %d |" % day.year)
    return any(form in text for form in forms)


@pytest.mark.parametrize("route, heading", [("nea_panama", "### 8.3"), ("nea_suez", "### 6.3")])
def test_every_band_begins_on_a_day_the_methodology_records(route, heading):
    text = (base.REPO_ROOT / "docs" / "methodology.md").read_text(encoding="utf-8")
    section = text[text.index(heading):]
    section = section[:section.index("\n---")]
    for start, state, *_ in routemap.AVAILABILITY[route]:
        if start == routemap.TIMELINE_FROM.isoformat():
            continue
        assert _in_record(start, section), (route, start)


def test_the_timeline_heading_counts_panama_s_restricted_days(routes):
    """The count, worked again from the bands' own dates."""
    from lngarb import config

    values = {s["field"]: s["value"] for s in routes["timeline_heading_segments"] if "field" in s}
    since = date.fromisoformat(config.PARAMETERS["suez_closed_to_us_cargo_from"].value)
    last = date.fromisoformat(routes["timeline"]["last"])
    table = routemap.AVAILABILITY["nea_panama"]
    restricted = 0
    for index, (start, state, *_) in enumerate(table):
        first = date.fromisoformat(start)
        end = date.fromisoformat(table[index + 1][0]) if index + 1 < len(table) else last + timedelta(days=1)
        lo, hi = max(first, since), min(end, last + timedelta(days=1))
        if state == "restricted" and lo < hi:
            restricted += (hi - lo).days
    assert values["panama_restricted_days"] == restricted
    assert values["days_since_suez"] == (last - since).days + 1


def test_a_link_names_only_the_document_it_opens(routes):
    for row in routes["timeline"]["rows"]:
        for band in row["bands"]:
            if band["url"]:
                assert band["source"].startswith(band["link_label"]) and ";" not in band["link_label"]
            else:
                assert band["link_label"] is None


def _segments(d):
    points = [float(t) for t in re.findall(r"-?\d+(?:\.\d+)?", d)]
    line = list(zip(points[0::2], points[1::2]))
    return list(zip(line, line[1:]))


def test_no_route_line_runs_through_a_label(routes):
    segments = [seg for route in routes["map"]["routes"] for seg in _segments(route["d"])]
    for route in routes["map"]["routes"]:
        box = routemap.text_box(route["label"], route["label_x"], route["label_y"], "middle", routemap.LABEL_FONT)
        assert not any(routemap._crosses(box, p, q) for p, q in segments), route["id"]
    for port in routes["map"]["ports"]:
        box = routemap.text_box(port["name"], port["label_x"], port["label_y"], port["anchor"], routemap.PORT_FONT)
        assert not any(routemap._crosses(box, p, q) for p, q in segments), port["name"]


def test_the_label_sizes_are_the_stylesheet_s():
    css = (base.REPO_ROOT / "styles" / "components.css").read_text(encoding="utf-8")
    for selector, size in ((".map-label {", routemap.LABEL_FONT), (".map-port {", routemap.PORT_FONT)):
        block = css[css.index(selector):]
        block = block[:block.index("}")]
        assert "font-size: %gpx;" % size in block, selector

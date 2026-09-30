"""The four sea routes: their definition, and the checks their committed geometry must pass.

The routes are computed once with searoute by scripts/routes.py and committed to
data/seed/routes.json and data/seed/routes.geojson. They have no fetch time. What
the pipeline can do is check them every time it runs and record, in the
manifest, when it last did.

The checks work from the committed geometry alone, independently of the library
that drew it: each line's length is recomputed along great circles, each route
must pass within a stated distance of the straits it is meant to take and stay
clear of those it is meant to avoid, and each ballast leg must have the same
length as the laden one.
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

from .sources import base

__all__ = [
    "routes_json",
    "routes_geojson",
    "POINTS",
    "REFERENCE_POINTS",
    "ROUTE_SPECS",
    "EARTH_RADIUS_NM",
    "polyline_length_nm",
    "nearest_distance_nm",
    "check_geometry",
    "route_problems",
    "write_json",
    "record_routes",
]


def routes_json() -> Path:
    return base.SEED / "routes.json"


def routes_geojson() -> Path:
    return base.SEED / "routes.geojson"


#: Mean Earth radius, 6,371.0088 km (IUGG), in nautical miles of 1,852 m.
EARTH_RADIUS_NM = 6371.0088 / 1.852

#: The load port and the two delivery areas, longitude then latitude, each a
#: point at the terminal rounded to two decimals. Gate stands for Northwest
#: Europe and Futtsu, in Tokyo Bay, for the JKM delivery area. Other US Gulf
#: terminals lie within a few hundred miles of Sabine Pass and are not modelled.
POINTS: Mapping[str, Mapping[str, Any]] = {
    "sabine_pass": {"lon": -93.87, "lat": 29.74, "name": "Sabine Pass LNG, Louisiana"},
    "gate": {"lon": 4.03, "lat": 51.96, "name": "Gate terminal, Rotterdam"},
    "futtsu": {"lon": 139.82, "lat": 35.30, "name": "Futtsu, Tokyo Bay"},
}

#: A point in each passage the routes are tested against, longitude then
#: latitude, with the distance within which a route counts as passing it. The
#: Cape is rounded offshore, so its radius is wider.
REFERENCE_POINTS: Mapping[str, Mapping[str, Any]] = {
    "Florida Strait": {"lon": -81.0, "lat": 24.1, "within_nm": 60},
    "Yucatan Channel": {"lon": -85.9, "lat": 21.9, "within_nm": 60},
    "Dover Strait": {"lon": 1.45, "lat": 51.0, "within_nm": 30},
    "Strait of Gibraltar": {"lon": -5.6, "lat": 35.95, "within_nm": 30},
    "Panama Canal": {"lon": -79.7, "lat": 9.1, "within_nm": 30},
    "Suez Canal": {"lon": 32.55, "lat": 30.6, "within_nm": 30},
    "Bab el Mandeb": {"lon": 43.4, "lat": 12.6, "within_nm": 30},
    "Strait of Malacca": {"lon": 101.0, "lat": 2.6, "within_nm": 60},
    "Sunda Strait": {"lon": 105.8, "lat": -6.0, "within_nm": 30},
    "Lombok Strait": {"lon": 115.7, "lat": -8.6, "within_nm": 30},
    "Cape of Good Hope": {"lon": 18.47, "lat": -34.36, "within_nm": 200},
    "Strait of Magellan": {"lon": -70.5, "lat": -53.5, "within_nm": 150},
}

#: The four routes. restrictions are the searoute passage names each route is
#: told to avoid; passes and avoids are what its geometry must show.
ROUTE_SPECS: Sequence[Mapping[str, Any]] = (
    {
        "id": "nwe_direct",
        "label": "Sabine Pass to Gate, direct",
        "from": "sabine_pass",
        "to": "gate",
        "restrictions": ("northwest",),
        "passes": ("Florida Strait", "Dover Strait"),
        "avoids": ("Panama Canal", "Suez Canal", "Cape of Good Hope"),
    },
    {
        "id": "nea_panama",
        "label": "Sabine Pass to Futtsu, via Panama",
        "from": "sabine_pass",
        "to": "futtsu",
        "restrictions": ("northwest", "suez", "south_africa", "chili"),
        "passes": ("Panama Canal",),
        "avoids": ("Suez Canal", "Cape of Good Hope", "Strait of Magellan", "Florida Strait"),
    },
    {
        "id": "nea_suez",
        "label": "Sabine Pass to Futtsu, via Suez",
        "from": "sabine_pass",
        "to": "futtsu",
        "restrictions": ("northwest", "panama", "south_africa", "chili"),
        "passes": ("Florida Strait", "Strait of Gibraltar", "Suez Canal", "Bab el Mandeb", "Strait of Malacca"),
        "avoids": ("Panama Canal", "Cape of Good Hope"),
    },
    {
        "id": "nea_cape",
        "label": "Sabine Pass to Futtsu, via the Cape of Good Hope",
        "from": "sabine_pass",
        "to": "futtsu",
        "restrictions": ("northwest", "panama", "suez", "babalmandab", "chili"),
        "passes": ("Florida Strait", "Cape of Good Hope", "Sunda Strait"),
        "avoids": ("Panama Canal", "Suez Canal", "Bab el Mandeb", "Strait of Malacca"),
    },
)


# --------------------------------------------------------------------------
# Geometry
# --------------------------------------------------------------------------

def _haversine_nm(a: Sequence[float], b: Sequence[float]) -> float:
    lon1, lat1, lon2, lat2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    )
    return 2 * EARTH_RADIUS_NM * math.asin(math.sqrt(min(1.0, h)))


def polyline_length_nm(coordinates: Sequence[Sequence[float]]) -> float:
    """Length of a line of longitude, latitude pairs along great circles, in nautical miles."""
    return sum(_haversine_nm(a, b) for a, b in zip(coordinates, coordinates[1:]))


def nearest_distance_nm(coordinates: Sequence[Sequence[float]], reference: Mapping[str, float]) -> float:
    """Shortest distance from a reference point to a line, on a local plane.

    A plane tangent at the reference point is accurate to well under a mile at
    the tens of miles that matter here; far from the point the figure only has
    to be large. Each segment is placed on the plane by wrapping its first
    vertex's longitude once and adding the segment's own change in longitude,
    never by wrapping both ends separately: a line drawn past 180 degrees, as
    searoute draws the Pacific, would otherwise gain a false segment spanning
    the whole plane.
    """
    lon0, lat0 = reference["lon"], reference["lat"]
    scale = 60.0 * math.cos(math.radians(lat0))
    best = math.inf
    for a, b in zip(coordinates, coordinates[1:]):
        da = (a[0] - lon0 + 540.0) % 360.0 - 180.0
        db = da + (b[0] - a[0])
        ax, ay = da * scale, (a[1] - lat0) * 60.0
        bx, by = db * scale, (b[1] - lat0) * 60.0
        dx, dy = bx - ax, by - ay
        span = dx * dx + dy * dy
        t = 0.0 if span == 0 else max(0.0, min(1.0, -(ax * dx + ay * dy) / span))
        best = min(best, math.hypot(ax + t * dx, ay + t * dy))
    return best


def check_geometry(spec: Mapping[str, Any], coordinates: Sequence[Sequence[float]]) -> dict[str, Any]:
    """What a route's line shows: the passages it takes, and how close it comes to each."""
    nearest = {
        name: round(nearest_distance_nm(coordinates, point), 1)
        for name, point in REFERENCE_POINTS.items()
    }
    passes = [name for name, point in REFERENCE_POINTS.items() if nearest[name] <= point["within_nm"]]
    # searoute draws a Pacific crossing as one continuous line whose longitudes
    # run past -180 rather than jumping to +180. Either form crosses.
    crosses = any(abs(p[0]) > 180.0 for p in coordinates) or any(
        abs(b[0] - a[0]) > 180.0 for a, b in zip(coordinates, coordinates[1:])
    )
    return {
        "passes": passes,
        "nearest_nm": nearest,
        "geodesic_length_nm": round(polyline_length_nm(coordinates), 1),
        "crosses_antimeridian": crosses,
    }


def route_problems(document: Mapping[str, Any], geojson: Mapping[str, Any]) -> list[str]:
    """Everything wrong with a routes document and its GeoJSON, as sentences."""
    problems: list[str] = []
    specs = {spec["id"]: spec for spec in ROUTE_SPECS}
    routes = {route["id"]: route for route in document.get("routes", [])}
    if sorted(routes) != sorted(specs):
        problems.append("the routes are %s, expected %s" % (sorted(routes), sorted(specs)))
    features = {f.get("id"): f for f in geojson.get("features", [])}
    for route_id, spec in specs.items():
        route = routes.get(route_id)
        feature = features.get(route_id)
        if route is None or feature is None:
            problems.append("%s is missing from the document or the GeoJSON" % route_id)
            continue
        coordinates = feature["geometry"]["coordinates"]
        shown = check_geometry(spec, coordinates)
        for name in spec["passes"]:
            if name not in shown["passes"]:
                problems.append(
                    "%s should pass %s but comes no closer than %.1f nm"
                    % (route_id, name, shown["nearest_nm"][name])
                )
        for name in spec["avoids"]:
            if name in shown["passes"]:
                problems.append(
                    "%s should avoid %s but passes %.1f nm from it"
                    % (route_id, name, shown["nearest_nm"][name])
                )
        if route["reverse_distance_nm"] != route["distance_nm"]:
            problems.append(
                "%s is %.1f nm laden and %.1f nm in ballast"
                % (route_id, route["distance_nm"], route["reverse_distance_nm"])
            )
        drift = abs(shown["geodesic_length_nm"] / route["distance_nm"] - 1.0)
        if drift > 0.005:
            problems.append(
                "%s: the line measures %.1f nm along great circles, the recorded "
                "distance is %.1f nm" % (route_id, shown["geodesic_length_nm"], route["distance_nm"])
            )
        if route.get("vertices") != len(coordinates):
            problems.append(
                "%s records %s vertices, the GeoJSON has %d" % (route_id, route.get("vertices"), len(coordinates))
            )
    return problems


# --------------------------------------------------------------------------
# Writing and recording
# --------------------------------------------------------------------------

def write_json(path: Path, payload: Any) -> None:
    """utf-8, LF, two space indent, ASCII only, written atomically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp.%d" % os.getpid())
    try:
        with open(tmp, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=True)
            handle.write("\n")
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass


def record_routes() -> dict:
    """Check the committed routes seed and write its manifest entry. Returns the entry."""
    from .config import SOURCES

    registered = SOURCES["routes"]
    status = "ok"
    rows = 0
    vintage = None
    try:
        document = json.loads(routes_json().read_text(encoding="utf-8"))
        geojson = json.loads(routes_geojson().read_text(encoding="utf-8"))
        problems = route_problems(document, geojson)
        rows = len(document.get("routes", []))
        library = document.get("library", {})
        vintage = "%s %s" % (library.get("name"), library.get("version"))
        if problems:
            status = "failed"
            note = "the committed seed fails its own checks: " + "; ".join(problems)
        else:
            note = (
                "%d routes computed once with %s over the Eurostat SeaRoute network and "
                "committed. Checked on every run from the committed geometry: each line's "
                "great circle length is within 0.5 percent of its recorded distance, each "
                "passes the straits it should and avoids those it should not, and each "
                "ballast leg equals its laden leg. A seed, not a time series: the schema's "
                "frequency field reads annual and no dates apply."
                % (rows, vintage)
            )
    except (OSError, ValueError, KeyError) as exc:
        status = "failed"
        note = "the routes seed could not be read: %s: %s" % (type(exc).__name__, exc)

    entry = {
        "series": "routes",
        "source": registered.publisher,
        "url": None,
        "page_url": registered.page_url,
        "machine_fetched": False,
        "fetched_at": None,
        "checked_at": base.utc_now_iso(),
        "rows": rows,
        "observations": rows,
        "file_rows": rows,
        "first_date": None,
        "last_date": None,
        "frequency": registered.frequency,
        "gaps": [],
        "provisional_from": None,
        "vintage": vintage,
        "method": registered.method,
        "committable": registered.committable,
        "licence_note": registered.licence_note,
        "licence": registered.licence,
        "status": status,
        "note": note,
        "file": "data/seed/routes.json",
        "files": ["data/seed/routes.geojson"],
        "unit": "nautical miles",
        "observation_column": None,
        "unique_dates": True,
    }
    base.manifest_upsert(entry)
    return entry

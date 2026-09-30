#!/usr/bin/env python
"""Compute the four sea routes once and commit them as a seed. Nothing else runs searoute.

    python scripts/routes.py              compute, check and write data/seed/routes.*
    python scripts/routes.py --check      compute and compare with the committed seed, write nothing

The routes are computed with searoute (Apache 2.0), which finds the shortest
path over Eurostat's SeaRoute maritime network (MARNET), with the passages the
study wants each route to avoid passed as restrictions. The result is committed
to data/seed/routes.json, with the library version, the coordinates and the
restrictions, and each route's line to data/seed/routes.geojson for the map. The
engine reads the seed; nothing computes a route at build time, and searoute is
not a dependency of the site or of the pipeline.

searoute is installed only where this script runs, for example:

    python -m venv data/private/venv-routes
    data/private/venv-routes/Scripts/python -m pip install searoute==1.6.0
    data/private/venv-routes/Scripts/python scripts/routes.py

Each route is then checked from its own geometry: it must pass within a stated
distance of every strait it is meant to pass and not near those it is meant to
avoid, and its reverse, the ballast leg, must have the same length.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from lngarb import sea_routes  # noqa: E402

SEAROUTE_VERSION = "1.6.0"


def compute() -> tuple[dict, dict]:
    """The routes document and the GeoJSON collection, computed now."""
    import searoute  # imported here: only this script needs it

    version = getattr(searoute, "__version__", None)
    if version != SEAROUTE_VERSION:
        raise SystemExit(
            "searoute %s is installed; the seed is defined for %s. Install that "
            "version rather than change the seed silently." % (version, SEAROUTE_VERSION)
        )

    features = []
    routes = []
    for spec in sea_routes.ROUTE_SPECS:
        origin = sea_routes.POINTS[spec["from"]]
        destination = sea_routes.POINTS[spec["to"]]
        laden = searoute.searoute(
            [origin["lon"], origin["lat"]],
            [destination["lon"], destination["lat"]],
            units="naut",
            restrictions=list(spec["restrictions"]),
            return_passages=True,
        )
        ballast = searoute.searoute(
            [destination["lon"], destination["lat"]],
            [origin["lon"], origin["lat"]],
            units="naut",
            restrictions=list(spec["restrictions"]),
        )
        coordinates = laden["geometry"]["coordinates"]
        route = {
            "id": spec["id"],
            "label": spec["label"],
            "from": spec["from"],
            "to": spec["to"],
            "restrictions": list(spec["restrictions"]),
            "distance_nm": round(float(laden["properties"]["length"]), 1),
            "reverse_distance_nm": round(float(ballast["properties"]["length"]), 1),
            "passages_reported_by_searoute": sorted(laden["properties"].get("traversed_passages") or []),
            "vertices": len(coordinates),
        }
        route.update(sea_routes.check_geometry(spec, coordinates))
        routes.append(route)
        features.append(
            {
                "type": "Feature",
                "id": spec["id"],
                "properties": {"id": spec["id"], "label": spec["label"], "distance_nm": route["distance_nm"]},
                "geometry": {"type": "LineString", "coordinates": coordinates},
            }
        )

    document = {
        "schema_version": 1,
        "library": {
            "name": "searoute",
            "version": SEAROUTE_VERSION,
            "licence": "Apache License 2.0",
            "url": "https://github.com/genthalili/searoute-py",
            "network": "Eurostat SeaRoute maritime network (MARNET), as bundled with the library",
        },
        "units": {"distance": "nautical miles", "speed_for_days": "knots"},
        "points": sea_routes.POINTS,
        "reference_points": sea_routes.REFERENCE_POINTS,
        "routes": routes,
    }
    geojson = {"type": "FeatureCollection", "features": features}
    return document, geojson


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="compare with the committed seed, write nothing")
    args = parser.parse_args(argv)

    document, geojson = compute()
    problems = sea_routes.route_problems(document, geojson)
    for route in document["routes"]:
        print(
            "%-22s %8.1f nm  reverse %8.1f nm  %5.2f days at 17 knots  passes %s"
            % (route["id"], route["distance_nm"], route["reverse_distance_nm"],
               route["distance_nm"] / (17 * 24), ", ".join(route["passes"]))
        )
    if problems:
        print("\nthe computed routes fail their own checks:")
        for problem in problems:
            print("  " + problem)
        return 1

    if args.check:
        committed = json.loads(sea_routes.routes_json().read_text(encoding="utf-8"))
        same = [r["distance_nm"] for r in committed["routes"]] == [r["distance_nm"] for r in document["routes"]]
        print("\ncommitted seed %s the computation" % ("matches" if same else "DIFFERS FROM"))
        return 0 if same else 1

    sea_routes.write_json(sea_routes.routes_json(), document)
    sea_routes.write_json(sea_routes.routes_geojson(), geojson)
    entry = sea_routes.record_routes()
    print("\nwrote %s and %s, manifest entry %s" % (
        sea_routes.routes_json().relative_to(REPO_ROOT), sea_routes.routes_geojson().relative_to(REPO_ROOT), entry["status"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

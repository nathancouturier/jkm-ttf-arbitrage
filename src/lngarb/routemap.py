"""The Routes view's data: the map, the table of the four routes, and when each was open.

The map is drawn here, once, as SVG path strings: the page needs no map
library and makes no request for map data. Land is Natural Earth's 1:110m
land, as world-atlas 2.0.2 packs it (vendor/world-atlas/land-110m.json); the
routes are the very lines the distances are measured on (the routes seed,
through lngarb.sea_routes), so the map and the table cannot disagree.

THE PROJECTION. Equirectangular, from 235 degrees west to 150 degrees east:
more than the whole circle, because the way to Futtsu by Panama runs west
across the Pacific while the ways by Suez and the Cape run east, and any
single centring would cut one of them. Futtsu therefore appears twice, at the
left edge (reached by Panama) and at the right (reached by Suez and the
Cape), and the land of East Asia is drawn at both edges. The latitudes run
from 48 south, below the Cape, to 72 north.

THE LABELS. Each port's name and each route's label is placed here, where
no route line runs through it and no other word lies under it, from the sizes
the stylesheet gives the words; the page draws them where they are put.

THE TIMELINE. When each route was open to a US cargo, band by band, each with
its source, as docs/methodology.md records it: Panama in section 8.3, from the
expanded locks of 26 June 2016 through the drought restrictions of 2023 and
2024 and the water conservation from December 2025; Suez in section 6.3,
unknown before 2021 for want of a source, open to the end of 2023, and treated
as closed to a US cargo from 13 January 2024, which is an absence of reports.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Mapping, Sequence

from . import config, reader, sea_routes
from .sources import base

__all__ = ["LAND", "AVAILABILITY", "decode_topojson", "unwrap", "project", "land_path", "place_labels",
           "map_document", "timeline", "timeline_heading", "routes_document"]

LAND: Path = base.REPO_ROOT / "vendor" / "world-atlas" / "land-110m.json"

LON_MIN, LON_MAX = -235.0, 150.0
LAT_MIN, LAT_MAX = -48.0, 72.0
#: Map units per degree: the map is drawn at this size and scaled by the page.
PX_PER_DEGREE = 2.4
#: Places kept in a map coordinate.
PLACES = 1

#: Where each route's label sits: the route's vertex nearest this point,
#: chosen in open water away from the other labels.
LABEL_AT: Mapping[str, tuple[float, float]] = {
    "nwe_direct": (-45.0, 44.0),
    "nea_panama": (-150.0, 22.0),
    "nea_suez": (62.0, 13.0),
    "nea_cape": (2.0, -36.0),
}

#: The first day the timeline shows: the first month the study's data cover.
TIMELINE_FROM = date(2016, 1, 1)


def decode_topojson(topology: Mapping[str, Any]) -> list[list[list[tuple[float, float]]]]:
    """The polygons of a TopoJSON land object as rings of (lon, lat).

    Arcs are delta encoded and quantized: each position is the running sum of
    the deltas, scaled and translated by the transform. A negative arc index
    ~i is arc i reversed. Consecutive arcs of a ring share their joining
    point, which is dropped once."""
    scale = topology["transform"]["scale"]
    translate = topology["transform"]["translate"]
    arcs = []
    for arc in topology["arcs"]:
        x = y = 0
        points = []
        for dx, dy in arc:
            x += dx
            y += dy
            points.append((x * scale[0] + translate[0], y * scale[1] + translate[1]))
        arcs.append(points)

    def ring(indices: Sequence[int]) -> list[tuple[float, float]]:
        out: list[tuple[float, float]] = []
        for index in indices:
            points = arcs[index] if index >= 0 else list(reversed(arcs[~index]))
            out.extend(points if not out else points[1:])
        return out

    polygons = []
    for geometry in topology["objects"]["land"]["geometries"]:
        if geometry["type"] == "Polygon":
            polygons.append([ring(r) for r in geometry["arcs"]])
        elif geometry["type"] == "MultiPolygon":
            polygons.extend([ring(r) for r in polygon] for polygon in geometry["arcs"])
    return polygons


def project(lon: float, lat: float) -> tuple[float, float]:
    """Map coordinates of a point: x east from the left edge, y down from the top."""
    return (lon - LON_MIN) * PX_PER_DEGREE, (LAT_MAX - lat) * PX_PER_DEGREE


def _path(points: Sequence[tuple[float, float]], close: bool) -> str:
    parts = []
    last = None
    for index, (lon, lat) in enumerate(points):
        x, y = project(lon, lat)
        text = "%s %s" % (round(x, PLACES), round(y, PLACES))
        if text == last:
            continue
        parts.append(("M" if index == 0 else "L") + text)
        last = text
    return "".join(parts) + ("Z" if close else "")


def unwrap(ring: Sequence[tuple[float, float]]) -> list[tuple[float, float]]:
    """A ring with its longitudes made continuous.

    The rings are drawn on the sphere: an edge from 179.99 to -180 east of
    Chukotka is a hundredth of a degree long, not a whole turn. Each step is
    therefore taken the short way round, so a ring that crosses the
    antimeridian runs on past 180 (or below -180) instead of jumping across
    the plane. A ring round a pole comes back a whole turn from where it began;
    it is closed along that pole."""
    out = [(float(ring[0][0]), float(ring[0][1]))]
    for lon, lat in ring[1:]:
        lon += 360.0 * round((out[-1][0] - lon) / 360.0)
        out.append((lon, float(lat)))
    if abs(out[-1][0] - out[0][0]) > 180.0:
        pole = 90.0 if sum(lat for _, lat in ring) > 0 else -90.0
        out += [(out[-1][0], pole), (out[0][0], pole)]
    return out


def land_path(topology: Mapping[str, Any]) -> str:
    """Every land ring that falls in the window, unwrapped at the antimeridian,
    then drawn at each whole turn east or west where it falls in the window:
    once for most land, twice for East Asia, which shows at both edges."""
    out = []
    for polygon in decode_topojson(topology):
        for ring in polygon:
            ring = unwrap(ring)
            lats = [lat for _, lat in ring]
            if max(lats) < LAT_MIN or min(lats) > LAT_MAX:
                continue
            for turns in (-2, -1, 0, 1):
                lons = [lon + 360.0 * turns for lon, _ in ring]
                if max(lons) < LON_MIN or min(lons) > LON_MAX:
                    continue
                out.append(_path([(lon + 360.0 * turns, lat) for lon, lat in ring], close=True))
    return "".join(out)


#: The sizes styles/components.css sets for a route's label (.map-label) and a
#: port's name (.map-port), in map units, and a width per character that
#: overstates Figtree's, so a label's box holds its words.
LABEL_FONT = 11.0
PORT_FONT = 10.0
CHAR_EM = 0.6
#: Clear space kept round a label, and a port's dot with its ring.
LABEL_PAD = 2.0
PORT_DOT = 5.0
#: Where a port's name may go: beside the dot, right or left, centred on it
#: and then moved up or down a step at a time; or centred above or below the
#: dot. How far a route's label may move from its anchor. In map units.
PORT_GAP = 6.0
PORT_STEPS = tuple(float(step) for step in range(0, 32, 2))
NUDGES_Y = (-6.0, 15.0, -14.0, 23.0, -22.0, 31.0)
NUDGES_X = (0.0, 24.0, -24.0, 48.0, -48.0)

Box = tuple[float, float, float, float]


def _nearest(coordinates: Sequence[Sequence[float]], target: tuple[float, float]) -> tuple[float, float]:
    best = min(coordinates, key=lambda p: (p[0] - target[0]) ** 2 + (p[1] - target[1]) ** 2)
    return project(best[0], best[1])


def text_box(text: str, x: float, y: float, anchor: str, size: float) -> Box:
    """The box a line of text takes, from its anchor point and baseline."""
    width = len(text) * size * CHAR_EM
    left = {"start": x, "middle": x - width / 2.0, "end": x - width}[anchor]
    return (left - LABEL_PAD, y - size * 0.8 - LABEL_PAD, left + width + LABEL_PAD, y + size * 0.25 + LABEL_PAD)


def _overlaps(a: Box, b: Box) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def _crosses(box: Box, p: tuple[float, float], q: tuple[float, float]) -> bool:
    """Whether the segment from p to q enters the box (Liang and Barsky's clip)."""
    t0, t1 = 0.0, 1.0
    dx, dy = q[0] - p[0], q[1] - p[1]
    for edge_p, edge_q in ((-dx, p[0] - box[0]), (dx, box[2] - p[0]), (-dy, p[1] - box[1]), (dy, box[3] - p[1])):
        if edge_p == 0.0:
            if edge_q < 0.0:
                return False
            continue
        t = edge_q / edge_p
        if edge_p < 0.0:
            t0 = max(t0, t)
        else:
            t1 = min(t1, t)
        if t0 > t1:
            return False
    return True


def _clear(box: Box, lines: Sequence[Sequence[tuple[float, float]]], taken: Sequence[Box], width: float,
           height: float) -> bool:
    if box[0] < 0.0 or box[1] < 0.0 or box[2] > width or box[3] > height:
        return False
    if any(_overlaps(box, other) for other in taken):
        return False
    return not any(_crosses(box, p, q) for line in lines for p, q in zip(line, line[1:]))


def place_labels(routes: Sequence[Mapping[str, Any]], ports: Sequence[Mapping[str, Any]], width: float,
                 height: float) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Each port's name and each route's label put where no route line runs
    through it and no other word or dot lies under it.

    A port's name goes beside its dot, on the side away from the map's nearer
    edge first, or centred above or below it, whichever needs the shortest
    move. A route's label starts above the vertex nearest its anchor in
    LABEL_AT and moves up, down and sideways until it is clear. Where nothing
    is clear, the first place is kept, so every word is drawn."""
    lines = [route["points"] for route in routes]
    taken: list[Box] = [(p["x"] - PORT_DOT, p["y"] - PORT_DOT, p["x"] + PORT_DOT, p["y"] + PORT_DOT) for p in ports]
    placed_ports = []
    for port in ports:
        sides = ("end", "start") if port["x"] > width / 2.0 else ("start", "end")
        beside = port["y"] + PORT_FONT * 0.35
        above = port["y"] - PORT_DOT - LABEL_PAD - PORT_FONT * 0.25
        below = port["y"] + PORT_DOT + LABEL_PAD + PORT_FONT * 0.8
        options = []
        for step in PORT_STEPS:
            for dy in ((0.0,) if step == 0.0 else (-step, step)):
                for anchor in sides:
                    options.append((anchor, port["x"] + (PORT_GAP if anchor == "start" else -PORT_GAP), beside + dy))
            options += [("middle", port["x"], above - step), ("middle", port["x"], below + step)]
        chosen = next((o for o in options if _clear(text_box(port["name"], o[1], o[2], o[0], PORT_FONT), lines,
                                                    taken, width, height)), options[0])
        taken.append(text_box(port["name"], chosen[1], chosen[2], chosen[0], PORT_FONT))
        placed_ports.append({**port, "anchor": chosen[0], "label_x": round(chosen[1], PLACES),
                             "label_y": round(chosen[2], PLACES)})
    placed_routes = []
    for route in routes:
        x, y = route["anchor"]
        options = sorted(((x + dx, y + dy) for dy in NUDGES_Y for dx in NUDGES_X),
                         key=lambda o: (abs(o[1] - y) + abs(o[0] - x)))
        chosen = next((o for o in options if _clear(text_box(route["label"], o[0], o[1], "middle", LABEL_FONT),
                                                    lines, taken, width, height)), options[0])
        taken.append(text_box(route["label"], chosen[0], chosen[1], "middle", LABEL_FONT))
        placed_routes.append({**route, "label_x": round(chosen[0], PLACES), "label_y": round(chosen[1], PLACES)})
    return placed_routes, placed_ports


def map_document(*, best_route: str | None, routes_open: Mapping[str, bool]) -> dict[str, Any]:
    """The map: its size, the land, each route's line and label, the ports."""
    topology = json.loads(LAND.read_text(encoding="utf-8"))
    geojson = json.loads(sea_routes.routes_geojson().read_text(encoding="utf-8"))
    seed = json.loads(sea_routes.routes_json().read_text(encoding="utf-8"))
    width, _ = project(LON_MAX, LAT_MAX)
    _, height = project(LON_MIN, LAT_MIN)
    routes = []
    for feature in geojson["features"]:
        route_id = feature["id"]
        coordinates = feature["geometry"]["coordinates"]
        name = reader.ROUTE_SHORT.get(route_id, "Gate")
        label = ("to Gate" if route_id == "nwe_direct" else "via " + name)
        if not routes_open.get(route_id, True):
            label += ", closed"
        routes.append({
            "id": route_id,
            "d": _path(coordinates, close=False),
            "pattern": reader.ROUTE_PATTERNS.get(route_id, "context"),
            "accent": route_id == best_route,
            "open": routes_open.get(route_id, True),
            "label": label,
            "anchor": _nearest(coordinates, LABEL_AT[route_id]),
            "points": [project(lon, lat) for lon, lat in coordinates],
        })
    ports = []
    for key, point in seed["points"].items():
        shifts = (0.0, -360.0) if key == "futtsu" else (0.0,)
        for shift in shifts:
            x, y = project(point["lon"] + shift, point["lat"])
            ports.append({"id": key, "name": point["name"].split(",")[0], "x": round(x, PLACES), "y": round(y, PLACES)})
    routes, ports = place_labels(routes, ports, width, height)
    sabine = next(port for port in ports if port["id"] == "sabine_pass")
    start_x = text_box(sabine["name"], sabine["label_x"], sabine["label_y"], sabine["anchor"], PORT_FONT)[0] - LABEL_PAD
    for route in routes:
        del route["anchor"], route["points"]
    return {
        "width": round(width, PLACES), "height": round(height, PLACES),
        "land": land_path(topology),
        # Where a narrow screen first opens the map: its left edge just before
        # Sabine Pass's name, so the load port and the Atlantic show first.
        "start_x": round(max(start_x, 0.0), PLACES),
        "routes": routes,
        "ports": ports,
        "desc": ("A world map from 235 degrees west to 150 degrees east, so that Futtsu appears at both edges: "
                 "reached by Panama across the Pacific on the left, by Suez and round the Cape on the right. "
                 "Gate is reached directly across the Atlantic."),
    }


#: What each state of the timeline means, in the band table's words.
STATE_WORDS: Mapping[str, str] = {
    "open": "open",
    "restricted": "open, under restrictions",
    "closed": "closed",
    "unknown": "no source read",
}

_OIES = "https://www.oxfordenergy.org/wpcms/wp-content/uploads/2024/02/NG-188-LNG-Shipping-Chokepoints.pdf"
_PANAMA_2016 = "https://pancanal.com/en/inaugural-transit-of-the-expanded-panama-canal-begins/"

#: When Panama and Suez were open to a US cargo, as docs/methodology.md records
#: it, Panama in section 8.3 and Suez in section 6.3: each band's first day,
#: state, what the record shows, sources, link, and status. Where a band has a
#: link, the first source named is the document it opens. A band runs to the
#: day before the next begins, the last to the latest date of the data. Where
#: the record gives a month, the band begins on its first day. "assumption"
#: marks a state that is this study's reading rather than a source's words:
#: Suez closed to a US cargo, which is an absence of reports, not a count.
AVAILABILITY: Mapping[str, Sequence[tuple[str, str, str, str, str | None, str]]] = {
    "nea_panama": (
        ("2016-01-01", "closed", "closed to LNG carriers until the expanded locks opened",
         "Panama Canal Authority, press release of 26 June 2016", _PANAMA_2016, "published"),
        ("2016-06-26", "restricted", "the expanded locks open, the first LNG carrier passing on 25 July 2016, "
         "from Sabine Pass; daylight and encounter restrictions on LNG carriers",
         "Panama Canal Authority, press release of 26 June 2016; its press releases of 2016 and 2018",
         _PANAMA_2016, "published"),
        ("2018-10-01", "open", "restrictions lifted; up to two booked LNG slots a day; slot auctions from "
         "January 2021",
         "Panama Canal Authority, advisory A-29-2018 and press release of 3 February 2021", None, "published"),
        ("2023-01-03", "restricted", "water saving measures; neopanamax draught cut in steps to 44 feet by "
         "19 June 2023; 12 days of delay for unbooked vessels in late July",
         "Panama Canal Authority, advisories of 2023; LNG Prime, 28 July 2023", None, "published"),
        ("2023-07-30", "restricted", "daily transits cut to an average of 32, 10 of them neopanamax; queues of "
         "up to 21 days in August, all ship types",
         "Panama Canal Authority, advisory A-35-2023; IEA, Global Gas Security Review 2024", None, "published"),
        ("2023-11-01", "restricted", "31 transits a day, 9 of them neopanamax, then 8, 7 and 6 neopanamax "
         "booking slots in December; waits of 15 days for unreserved LNG carriers in mid December",
         "Panama Canal Authority, advisories A-48-2023 and A-53-2023; IEA, Gas Market Report Q1 2024", None,
         "published"),
        ("2024-01-16", "restricted", "24 booking slots, 7 of them neopanamax, full container ships ahead of LNG "
         "in the first booking period; LNG transits all but stopped by early 2024",
         "Panama Canal Authority, advisories A-54-2023 and A-08-2024; IEA", None, "published"),
        ("2024-06-01", "restricted", "neopanamax booking slots back to 8, 9, then 10",
         "Panama Canal Authority, advisories of 2024", None, "published"),
        ("2024-08-15", "restricted", "the Authority states its commitment to return to normal operating "
         "conditions, 50 feet and 36 booking slots, 10 of them neopanamax, from 1 September 2024",
         "Panama Canal Authority, advisory A-28-2024", None, "published"),
        ("2024-09-01", "open", "normal operating conditions, 36 booking slots, 10 of them neopanamax; LNG use "
         "stays low", "Panama Canal Authority, advisory A-28-2024; IEA, Gas Market Reports of 2025 and Q1 2026",
         None, "published"),
        ("2025-12-01", "restricted", "water conservation; neopanamax draught cut to 48 feet by 2 September "
         "2026; an LNG first rule for one booking slot from 4 January 2026",
         "Panama Canal Authority, press release of 5 August 2026 and advisories of 2025 and 2026", None,
         "published"),
        ("2026-09-04", "restricted", "El Nino measures: 9 neopanamax slots a day; 10 slots and at least four "
         "LNG slots a week announced from 15 October 2026",
         "Panama Canal Authority, advisories A-29-2026 and A-36-2026", None, "published"),
    ),
    "nea_suez": (
        ("2016-01-01", "unknown", "no source this study read covers these years; the model treats the route "
         "as open", "none: a gap in the record", None, "assumption"),
        ("2021-01-01", "open", "routine use: 434 laden LNG transits of Suez in 2023, 130 of them US cargoes "
         "southbound", "Oxford Institute for Energy Studies, NG 188", _OIES, "published"),
        ("2024-01-01", "restricted", "most carriers already diverting; eight laden transits, Qatari and "
         "Russian, none from the US",
         "Oxford Institute for Energy Studies, NG 188; The National, 15 January 2024", _OIES, "published"),
        ("2024-01-13", "closed", "Qatari laden carriers turn south; the last ballast LNG carrier passes Suez on "
         "16 January", "Oxford Institute for Energy Studies, NG 188; The National, 15 and 16 January 2024",
         _OIES, "assumption"),
        ("2024-01-17", "closed", "no LNG carrier crosses the Red Sea; canal transits only for Aqaba and Ain "
         "Sukhna", "Oxford Institute for Energy Studies, NG 188; IEA, Gas Market Report Q3 2025", _OIES,
         "assumption"),
        ("2024-06-01", "closed", "crossings by two Russia linked ships and a few ballast ships bound for "
         "Russia", "gCaptain, 8 February 2025; IEA, Global Gas Security Review 2024", None, "assumption"),
        ("2024-10-01", "closed", "no LNG carrier crosses", "gCaptain, 8 February 2025", None, "assumption"),
        ("2025-02-08", "closed", "three crossings in the half year; the two named are Salalah LNG, from Oman, "
         "and Trader III",
         "IEA, Gas Market Reports Q2 and Q3 2025; Kpler, 8 May 2025", None, "assumption"),
        ("2025-07-01", "closed", "only a handful of crossings in 2025, and limited in the winter",
         "IEA, Gas Market Reports Q1 and Q2 2026", None, "assumption"),
        ("2026-03-01", "closed", "no LNG vessel at Bab el Mandeb, then one in ballast",
         "Discovery Alert, 22 July 2026, citing S&P Global data (secondary)", None, "assumption"),
        ("2026-08-01", "unknown", "no source this study uses reports on LNG carriers in the Red Sea; the model "
         "keeps the route closed", "none: a gap in the record", None, "assumption"),
    ),
}

#: The two routes no closure is recorded on.
_ALWAYS_OPEN = ("nwe_direct", "nea_cape")


def timeline(as_of: date) -> list[dict[str, Any]]:
    """When each route was open to a US cargo, band by band, with its source.

    Panama and Suez follow AVAILABILITY; Gate and the Cape are open
    throughout. Bands that begin after the latest date are dropped and the last
    band ends on it."""
    shorts = {"nwe_direct": "Gate", "nea_panama": "Panama", "nea_suez": "Suez", "nea_cape": "The Cape"}
    rows = []
    for route in ("nwe_direct", "nea_panama", "nea_suez", "nea_cape"):
        if route in _ALWAYS_OPEN:
            table = (("2016-01-01", "open", "open throughout; no closure of this route is recorded in the "
                      "sources read", "no closure recorded", None, "published"),)
        else:
            table = AVAILABILITY[route]
        starts = [date.fromisoformat(entry[0]) for entry in table]
        bands = []
        for index, (first, state, words, source, url, status) in enumerate(table):
            start = max(starts[index], TIMELINE_FROM)
            if start > as_of:
                break
            end = starts[index + 1] - timedelta(days=1) if index + 1 < len(table) else as_of
            link_label = source.split("; ")[0] if url else None
            bands.append({"start": start, "end": min(end, as_of), "state": state, "link_label": link_label,
                          "state_words": STATE_WORDS[state] + (", this study's reading"
                                                               if status == "assumption" and state != "unknown"
                                                               else ""),
                          "words": words, "source": source, "url": url, "status": status})
        rows.append({"route": route, "name": reader.ROUTE_NAMES[route], "short": shorts[route], "bands": bands})
    return rows


def _days_in(bands: Sequence[Mapping[str, Any]], state: str, start: date, end: date) -> int:
    """How many days from start to end, both included, the bands give a state."""
    total = 0
    for band in bands:
        first, last = max(band["start"], start), min(band["end"], end)
        if band["state"] == state and first <= last:
            total += (last - first).days + 1
    return total


def timeline_heading(rows: Sequence[Mapping[str, Any]], as_of: date) -> list[dict[str, Any]]:
    """The timeline's finding: since Suez closed to a US cargo, the two ways
    left, and on how many of those days Panama was restricted."""
    by = {row["route"]: row for row in rows}
    suez_from = date.fromisoformat(config.PARAMETERS["suez_closed_to_us_cargo_from"].value)
    if as_of < suez_from:
        return [reader.T("When each route was open to a US cargo, from "),
                reader.D("timeline_first", TIMELINE_FROM, "month"), reader.T(".")]
    days = (as_of - suez_from).days + 1
    restricted = _days_in(by["nea_panama"]["bands"], "restricted", suez_from, as_of)
    return [
        reader.T("Since "), reader.D("suez_closed_from", suez_from),
        reader.T(", with Suez treated as closed, a US cargo to Futtsu has had two ways: round the Cape, or "
                 "through Panama, which ran under restrictions (draught or booking slots cut, or waits reported) "
                 "on "),
        reader.N("panama_restricted_days", restricted, "count"), reader.T(" of those "),
        reader.N("days_since_suez", days, "count"), reader.T(" days."),
    ]


def routes_document(now_document: Mapping[str, Any]) -> dict[str, Any]:
    """routes.json's body: the map, the table and the timeline for the latest week."""
    result = now_document["result"]
    inputs = now_document["engine_inputs"]
    as_of = date.fromisoformat(now_document["as_of"])
    speed = inputs["vessel"]["speed_kn"]
    lines = {"nwe_direct": result["west"], **result["east"]}
    routes_open = {route: l["open"] for route, l in lines.items()}
    closed = {route: reader.closed_words(l["why_closed"]) for route, l in lines.items() if not l["open"]}
    rows = []
    for route, l in lines.items():
        engine_route = inputs["routes"][route]
        rows.append({
            "route": route,
            "name": reader.ROUTE_NAMES[route],
            "distance_nm": l["distance_nm"],
            "sea_days": l["distance_nm"] / (speed * 24.0),
            "days_total": l["days_total"],
            "canal_laden_usd": engine_route["canal_laden_usd"],
            "canal_ballast_usd": engine_route["canal_ballast_usd"],
            "open": l["open"],
            "status_words": "open" if l["open"] else "closed: " + closed[route],
        })
    by = {row["route"]: row for row in rows}
    heading = [
        reader.T("From Sabine Pass, Futtsu is "), reader.N("panama_nm", by["nea_panama"]["distance_nm"], "nm"),
        reader.T(" nautical miles away via Panama, "), reader.N("suez_nm", by["nea_suez"]["distance_nm"], "nm"),
        reader.T(" via Suez and "), reader.N("cape_nm", by["nea_cape"]["distance_nm"], "nm"),
        reader.T(" round the Cape; Gate is "), reader.N("gate_nm", by["nwe_direct"]["distance_nm"], "nm"),
        reader.T("."),
    ]
    closed_now = [route for route in by if not by[route]["open"]]
    if closed_now:
        heading += [reader.T(" In the week to "), reader.D("as_of", as_of), reader.T(", "),
                    reader.W("closed_routes", reader.listed(reader.ROUTE_SHORT[r] for r in closed_now)),
                    reader.T(" is closed to a US cargo." if len(closed_now) == 1 else " are closed to a US cargo.")]
    best = result["best_route"]
    if best == "nwe_direct":
        best_words = [reader.T(" Gate nets the latest cargo most, so no route east is in the accent.")]
    else:
        best_words = [reader.T(" The accent is the route the latest cargo nets most by, "),
                      reader.W("best_route", reader.ROUTE_SHORT[best]), reader.T(".")]
    rows_timeline = timeline(as_of)
    waits = config.PARAMETERS["panama_waits_reported"].value
    return {
        "as_of": as_of,
        "heading_segments": heading,
        "map": map_document(best_route=best if best != "nwe_direct" else None, routes_open=routes_open),
        "map_caption_segments": [
            reader.T("The four routes as the distances are measured, each drawn from the same line: Gate in a thin "
                     "line, Panama solid, Suez dashed and the Cape dotted. Futtsu is at both edges of the map."),
            *best_words,
        ],
        "map_scroll_words": ("The map is wider than the screen and scrolls sideways: Futtsu by Panama is to the "
                             "left, Suez and the Cape to the right."),
        "speed_kn": speed,
        "rows": rows,
        "table_caption_segments": [
            reader.T("The four routes from Sabine Pass: distance, days at sea one way at "),
            reader.N("speed_kn", speed, "knots"),
            reader.T(" knots, the round trip in days with a day each to load and discharge, and the canal tolls "
                     "for a cargo loading in the week to "), reader.D("as_of", as_of), reader.T("."),
        ],
        "timeline": {"first": TIMELINE_FROM, "last": as_of, "rows": rows_timeline},
        "timeline_heading_segments": timeline_heading(rows_timeline, as_of),
        "timeline_caption_segments": [
            reader.T("A full bar is open, a thin bar open under restrictions (draught or booking slots cut, "
                     "daylight and encounter rules, waits reported, or most carriers diverting), an empty outline "
                     "closed, a pale bar a stretch no source read covers; from "),
            reader.D("timeline_first", TIMELINE_FROM, "month"), reader.T(" to "), reader.D("as_of", as_of),
            reader.T(". The engine adds waiting days at Panama only in the months a wait was reported for LNG, "),
            reader.W("wait_months", reader.listed([reader.month_label(date.fromisoformat(month + "-01"))
                                                   for month in sorted(waits)])),
            reader.T("; the table under the chart gives every band's source."),
        ],
        "source_segments": [
            reader.T("Routes and distances: this study's computation with the searoute library over Eurostat's "
                     "SeaRoute network. Land: Natural Earth, public domain, through world-atlas. Tolls: the Panama "
                     "Canal Authority's tariffs and the Suez Canal Authority's circulars, as the study's "
                     "methodology sets out in its sections on Suez and Panama (docs/methodology.md). Data to "),
            reader.D("as_of", as_of), reader.T("."),
        ],
    }

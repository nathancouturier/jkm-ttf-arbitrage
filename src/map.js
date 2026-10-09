/* map.js
 *
 * The Routes view's two drawings: the map and the timeline of when each route
 * was open. Like src/charts.js, SVG drawn by hand, marks coloured by the role
 * classes in styles/components.css.
 *
 * THE MAP is drawn by Python (src/lngarb/routemap.py) as path strings in its
 * own coordinates, the land and the very route lines the distances are
 * measured on, with every word already placed; here it is only put on the
 * page. Its viewBox scales it to the column, and below its own width it
 * scrolls sideways in its own box rather than shrink its words.
 *
 * THE TIMELINE has one row per route: an open stretch is a full bar, a
 * stretch under restrictions a thin bar, a closed stretch an empty outline,
 * and a stretch no source covers a pale bar. Year ticks under the rows. The
 * bands' words and sources are the table under it.
 *
 * Numeric literals: GEOMETRY below, declared in tools/check-literals.mjs.
 */

import { svgEl, imageSvg, px, linear, present, GEOMETRY } from "./charts.js";

export const MAP_GEOMETRY = Object.freeze({
  /* A port's dot. */
  PORT_RADIUS: 3.5,
  /* The timeline: a row, the column of route names and the gap after it. */
  ROW: 30,
  NAME_COLUMN: 150,
  NAME_COLUMN_NARROW: 104,
  NAME_GAP: 6,
  /* A band's thickness, open or closed, and under restrictions; the
   * narrowest band drawn, so a stretch of days still shows on a phone. */
  BAND: 10,
  BAND_THIN: 4,
  MIN_BAND: 2,
  PAD_TOP: 8,
  AXIS: 26,
  PAD_RIGHT: 12,
  NARROW: 560,
  /* The least room a year's label needs; fewer years are labelled where a
   * year is narrower than this. */
  YEAR_ROOM: 40,
});

/** The map as an image: land, routes with their labels, ports. Every word is
 *  drawn where routemap.py placed it, clear of the lines. */
export function routeMap(map, words) {
  const g = MAP_GEOMETRY;
  const svg = imageSvg({ width: map.width, height: map.height, title: words.title, desc: map.desc, className: "map" });
  svg.removeAttribute("width");
  svg.removeAttribute("height");
  // The map never draws narrower than its own units, so its words keep the
  // sizes the stylesheet gives them; the frame scrolls instead.
  svg.style.setProperty("--map-width", px(map.width) + "px");
  svg.appendChild(svgEl("path", { class: "map-land", d: map.land }));
  for (const route of map.routes) {
    const kind = route.id === "nwe_direct" ? "map-route map-route--west" : "line line--" + route.pattern + " map-route";
    const group = svgEl("g", { class: kind + (route.accent ? " map-route--accent" : "") + (route.open ? "" : " map-route--closed") });
    group.appendChild(svgEl("path", { class: route.accent ? "mark-accent" : (route.open && route.id !== "nwe_direct" ? "mark-series" : "mark-context"), d: route.d }));
    svg.appendChild(group);
  }
  for (const port of map.ports) {
    svg.appendChild(svgEl("circle", { class: "mark-printed", cx: px(port.x), cy: px(port.y), r: g.PORT_RADIUS }));
  }
  for (const route of map.routes) {
    const attrs = { class: route.accent ? "map-label text-accent" : "map-label", x: px(route.label_x), y: px(route.label_y), "text-anchor": "middle" };
    svg.appendChild(svgEl("text", { ...attrs, class: attrs.class + " halo" }, route.label));
    svg.appendChild(svgEl("text", attrs, route.label));
  }
  for (const port of map.ports) {
    const attrs = { class: "map-port", x: px(port.label_x), y: px(port.label_y), "text-anchor": port.anchor };
    svg.appendChild(svgEl("text", { ...attrs, class: "map-port halo" }, port.name));
    svg.appendChild(svgEl("text", attrs, port.name));
  }
  return svg;
}

function dayMs(iso) {
  const [y, m, d] = iso.split("-").map(Number);
  return Date.UTC(y, m - 1, d);
}

/** Consecutive bands in the same state, drawn as one run; each run ends where
 *  the next begins, the last on its own last day. */
function runs(bands) {
  const out = [];
  for (const band of bands) {
    const previous = out[out.length - 1];
    if (previous && previous.state === band.state) previous.last = band.end;
    else out.push({ state: band.state, first: band.start, last: band.end });
  }
  return out.map((run, index) => ({ ...run, to: index + 1 < out.length ? out[index + 1].first : run.last }));
}

/** The timeline: a row per route, its bands across the years. A full bar is
 *  open, a thin bar open under restrictions, an empty outline closed, a pale
 *  bar a stretch no source covers. None of these reuses a route's pattern on
 *  the map. */
export function routeTimeline({ width, timeline, words }) {
  const g = MAP_GEOMETRY;
  const narrow = width < g.NARROW;
  const left = narrow ? g.NAME_COLUMN_NARROW : g.NAME_COLUMN;
  const right = Math.max(width - g.PAD_RIGHT, left + g.NAME_COLUMN);
  const rows = timeline.rows;
  const height = g.PAD_TOP + rows.length * g.ROW + g.AXIS;
  const svg = imageSvg({ width, height, title: words.title, desc: words.desc, className: "chart--timeline" });
  const first = dayMs(timeline.first);
  const last = dayMs(timeline.last);
  const xOf = linear(first, last, left, right);

  // Year ticks: a rule every year, a label every year that has room.
  const firstYear = new Date(first).getUTCFullYear();
  const lastYear = new Date(last).getUTCFullYear();
  const perYear = (right - left) / Math.max(lastYear - firstYear, 1);
  const step = Math.max(Math.ceil(g.YEAR_ROOM / perYear), 1);
  const bottom = g.PAD_TOP + rows.length * g.ROW;
  for (let year = firstYear; year <= lastYear; year += 1) {
    const at = Date.UTC(year, 0, 1);
    if (at < first) continue;
    const x = xOf(at);
    svg.appendChild(svgEl("line", { class: "mark-grid", x1: px(x), x2: px(x), y1: px(g.PAD_TOP), y2: px(bottom) }));
    if ((year - firstYear) % step !== 0) continue;
    svg.appendChild(svgEl("text", { class: "tick", x: px(x), y: px(bottom + g.AXIS * GEOMETRY.HALF), "text-anchor": "middle", "dominant-baseline": "middle" }, String(year)));
  }

  const kinds = {
    open: { className: "band-open", thickness: g.BAND },
    restricted: { className: "band-open", thickness: g.BAND_THIN },
    closed: { className: "band-closed", thickness: g.BAND },
    unknown: { className: "band-unknown", thickness: g.BAND },
  };
  rows.forEach((row, index) => {
    const middle = g.PAD_TOP + index * g.ROW + g.ROW * GEOMETRY.HALF;
    svg.appendChild(svgEl("text", { class: "chart-label", x: px(left - g.NAME_GAP), y: px(middle), "text-anchor": "end", "dominant-baseline": "middle" }, narrow ? row.short : row.name));
    const wide = [];
    const narrowRuns = [];
    for (const run of runs(row.bands)) {
      const kind = kinds[run.state];
      const x0 = xOf(dayMs(run.first));
      const x1 = xOf(dayMs(run.to));
      if (!kind || !present(x0) || !present(x1)) continue;
      const rect = svgEl("rect", {
        class: kind.className,
        x: px(x0), y: px(middle - kind.thickness * GEOMETRY.HALF),
        width: px(Math.max(x1 - x0, g.MIN_BAND)), height: px(kind.thickness),
      });
      (x1 - x0 < g.MIN_BAND ? narrowRuns : wide).push(rect);
    }
    for (const rect of [...wide, ...narrowRuns]) svg.appendChild(rect);
  });
  return svg;
}

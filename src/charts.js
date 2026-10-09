/* charts.js
 *
 * SVG drawn by hand. No chart library is vendored: every mark this study needs
 * is specific to it, and a library's defaults (a legend, a tooltip card, colour
 * cycling) are each something the page does without. The helpers follow the
 * sibling crack-spread-study's src/charts.js: a namespace helper, a path that
 * breaks at a gap, a 1, 2, 5, 10 tick ladder and a redraw on width change, so
 * type inside a plot stays the size the stylesheet says. Marks take colour from
 * the role classes in styles/components.css, never from a fill or stroke
 * attribute holding a value, so a theme change needs no redraw.
 *
 * The four charts of the Now view:
 *   netbackBar      one route's netback at Sabine Pass, a bar in a table row
 *   waterfallBar    one row's bar in the table of the arb's steps
 *   breakevenChart  S* against hire per route east, today's spread, the
 *                   reported hire, and where they cross (H*)
 *   flowsChart      the monthly share of exports to Asia over the arb's sign
 *
 * Missing is never zero. A null ends the current line and the next value
 * starts a new one; a finite value with a gap on both sides is a small dot.
 *
 * NUMERIC LITERALS. GEOMETRY is the drawing surface: heights, paddings, a dot
 * radius. Coordinate system decisions that carry no observation, each declared
 * with its value in tools/check-literals.mjs. Every quantity about the market
 * arrives from a JSON artifact through the caller, and every word drawn is
 * handed in by the caller from the artifact's sentences.
 */

import { formatNumber, segmentsText } from "./format.js";

export const GEOMETRY = Object.freeze({
  /* Room above a plot for the unit title. */
  PAD_TOP: 28,
  /* Room left of a plot for the tick values. */
  PAD_LEFT: 48,
  /* Room right of a plot for the direct end labels. */
  PAD_RIGHT: 88,
  /* From the plot's bottom edge to the middle of the x tick values. */
  AXIS_GAP: 16,
  /* Room under the x tick values for the axis title. */
  AXIS_BELOW: 22,
  TICK_LENGTH: 4,
  /* Space between a mark and its label. */
  LABEL_GAP: 8,
  /* Two end labels closer than this are pushed apart. */
  LABEL_SPACING: 14,
  /* The accent dot and its ring, and a printed point. */
  DOT_RADIUS: 4,
  RING_WIDTH: 2,
  ISOLATED_RADIUS: 1.5,
  /* About this many tick intervals on each axis. */
  Y_TICKS: 5,
  X_TICKS: 4,
  HALF: 0.5,
  /* Pixel coordinates are written to two places. */
  COORD_DECIMALS: 2,
  /* A bar inside a table row or a bar chart. A step narrower than SMALL_STEP
   * px is drawn as a circle. */
  BAR_THICKNESS: 14,
  SMALL_STEP: 4,
  SMALL_RADIUS: 2.5,
  OUTLINE_INSET: 0.75,
  /* The breakeven plot. */
  BREAKEVEN_HEIGHT: 300,
  BREAKEVEN_HEIGHT_NARROW: 230,
  NARROW_WIDTH: 600,
  /* The flows panels. */
  SHARE_HEIGHT: 180,
  ARB_HEIGHT: 110,
  PANEL_GAP: 30,
  /* A month bar takes this share of its slot. */
  BAR_SHARE: 0.6,
  /* The History view's panels, and the room above a plot for the numbers of
   * its rules. */
  HISTORY_HEIGHT: 260,
  HISTORY_HEIGHT_NARROW: 200,
  HSTAR_HEIGHT: 200,
  HSTAR_HEIGHT_NARROW: 160,
  RULE_ROOM: 14,
  HISTORY_PAD_RIGHT: 128,
  /* On a narrow screen the end labels give way to the legend under the
   * chart; a tick value is labelled only where it has this much room per
   * character. */
  HISTORY_PAD_RIGHT_NARROW: 12,
  TICK_CHAR: 7,
  /* Room per character of a rule's label, a little over the glyph's width,
   * so a label moved back inside the chart ends inside it. */
  RULE_CHAR: 7.5,
  /* The events: a short mark up from the foot of the plot, or a bar along it
   * for a period, its letter above. */
  EVENT_TICK: 10,
  EVENT_BAR: 3,
});

/* The mantissas of decimal notation, a fact about how numbers are written. */
const TICK_LADDER = Object.freeze([1, 2, 5, 10]);

/* The SVG namespace, read from an element the parser made, so this file holds
 * no URL. */
let svgNamespace = null;
function svgNs() {
  if (svgNamespace === null) {
    const holder = document.createElement("div");
    holder.innerHTML = "<svg></svg>";
    svgNamespace = holder.firstChild.namespaceURI;
  }
  return svgNamespace;
}

let idCounter = 0;
/** A document unique id for a title or desc. */
export function uid(prefix) {
  idCounter += 1;
  return prefix + "-" + String(idCounter);
}

/** An SVG element with attributes. null and undefined attributes are skipped. */
export function svgEl(tag, attrs, text) {
  const node = document.createElementNS(svgNs(), tag);
  for (const [name, value] of Object.entries(attrs || {})) {
    if (value === null || value === undefined) continue;
    node.setAttribute(name, String(value));
  }
  if (text !== undefined) node.textContent = text;
  return node;
}

/** A coordinate as an attribute string. */
export function px(value) {
  return value.toFixed(GEOMETRY.COORD_DECIMALS);
}

/** Missing is null, undefined, NaN or an infinity, and never zero. */
export function present(value) {
  return typeof value === "number" && Number.isFinite(value);
}

/** A root svg that is an image with a title and a description: role img,
 *  aria-labelledby naming both. */
export function imageSvg({ width, height, title, desc, className }) {
  const titleId = uid("chart-title");
  const descId = uid("chart-desc");
  const svg = svgEl("svg", {
    class: className ? "chart " + className : "chart",
    width,
    height,
    viewBox: [0, 0, width, height].join(" "),
    role: "img",
    "aria-labelledby": titleId + " " + descId,
    focusable: "false",
  });
  svg.appendChild(svgEl("title", { id: titleId }, title));
  svg.appendChild(svgEl("desc", { id: descId }, desc));
  return svg;
}

/** A decorative svg whose values are all printed beside it. */
export function hiddenSvg({ width, height, className }) {
  return svgEl("svg", {
    class: className ? "chart " + className : "chart",
    width,
    height,
    viewBox: [0, 0, width, height].join(" "),
    "aria-hidden": "true",
    focusable: "false",
  });
}

/** A linear map from a domain that came from an artifact to pixels. */
export function linear(domainLow, domainHigh, rangeLow, rangeHigh) {
  const span = domainHigh - domainLow;
  const map = (value) => (span === 0 ? rangeLow : rangeLow + ((value - domainLow) / span) * (rangeHigh - rangeLow));
  map.domain = [domainLow, domainHigh];
  map.range = [rangeLow, rangeHigh];
  return map;
}

function powerOfTenBelow(value) {
  return Math.pow(TICK_LADDER[TICK_LADDER.length - 1], Math.floor(Math.log10(value)));
}

/** The round step for about `count` intervals across a span. */
export function tickStep(low, high, count) {
  if (!(high > low) || !(count > 0)) return 0;
  const rough = (high - low) / count;
  const magnitude = powerOfTenBelow(rough);
  for (const rung of TICK_LADDER) {
    if (magnitude * rung >= rough) return magnitude * rung;
  }
  return magnitude * TICK_LADDER[TICK_LADDER.length - 1];
}

/** Tick values across a domain, on the step the artifact gives (so both ends
 *  of an axis fall on a tick), or on one found for about `count` intervals. */
export function tickValues(low, high, count, given) {
  const step = given > 0 ? given : tickStep(low, high, count);
  if (step === 0) return [low];
  const places = stepPlaces(step);
  const out = [];
  for (let k = Math.ceil(low / step); k * step <= high + step * Number.EPSILON; k += 1) {
    out.push(Number((k * step).toFixed(places)));
  }
  return out;
}

/** A tick label with as many places as the step needs and no more. */
export function tickLabel(value, step) {
  return formatNumber(value, "tick", { tick: stepPlaces(step) }, { context: "table" });
}

function stepPlaces(step) {
  return step > 0 && step < 1 ? Math.ceil(-Math.log10(step)) : 0;
}

/** Redraw on a width change, never scale a viewBox. A zero width means the
 *  node is not laid out yet, for example inside a section that is still
 *  closed; the observer fires again when it is. Returns a function that stops
 *  watching. */
export function onWidthChange(node, draw) {
  let last = 0;
  const run = () => {
    const width = node.clientWidth;
    if (width === 0 || width === last) return;
    last = width;
    draw(width);
  };
  if (typeof ResizeObserver === "function") {
    // The redraw changes the node's height, so it waits for the next frame
    // rather than running inside the observer's own notification.
    let frame = 0;
    const observer = new ResizeObserver(() => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(run);
    });
    observer.observe(node);
    run();
    return () => observer.disconnect();
  }
  window.addEventListener("resize", run, { passive: true });
  run();
  return () => window.removeEventListener("resize", run);
}

/** Runs of consecutive present values. `points` is [[x, y], ...] in order. */
export function splitRuns(points) {
  const runs = [];
  let current = [];
  for (const [x, y] of points) {
    if (present(y)) {
      current.push([x, y]);
    } else {
      if (current.length) runs.push(current);
      current = [];
    }
  }
  if (current.length) runs.push(current);
  return runs;
}

/** One path per run, never joined across a gap; a run of one point is a dot. */
function drawRuns(group, runs, xOf, yOf) {
  for (const run of runs) {
    if (run.length === 1) {
      group.appendChild(svgEl("circle", { class: "mark-series-fill", cx: px(xOf(run[0][0])), cy: px(yOf(run[0][1])), r: GEOMETRY.ISOLATED_RADIUS }));
      continue;
    }
    const d = run.map(([x, y], index) => (index === 0 ? "M" : "L") + px(xOf(x)) + " " + px(yOf(y))).join(" ");
    group.appendChild(svgEl("path", { class: "mark-series", d }));
  }
}

/** Spread labels that want the same column apart, keeping their order. Each
 *  item has `want` (a y) and gets `y`. */
function spreadLabels(items, low, high) {
  const sorted = [...items].sort((a, b) => a.want - b.want);
  for (const item of sorted) item.y = item.want;
  for (let pass = 0; pass < sorted.length; pass += 1) {
    let moved = false;
    for (let index = 1; index < sorted.length; index += 1) {
      const above = sorted[index - 1];
      const below = sorted[index];
      const gap = below.y - above.y;
      if (gap < GEOMETRY.LABEL_SPACING) {
        const push = (GEOMETRY.LABEL_SPACING - gap) * GEOMETRY.HALF;
        above.y -= push;
        below.y += push;
        moved = true;
      }
    }
    if (!moved) break;
  }
  if (sorted.length) {
    const overflowTop = low - sorted[0].y;
    if (overflowTop > 0) for (const item of sorted) item.y += overflowTop;
    const overflowBottom = sorted[sorted.length - 1].y - high;
    if (overflowBottom > 0) for (const item of sorted) item.y -= overflowBottom;
  }
  return sorted;
}

/** A text label with a --bg halo, so it reads where it crosses a line. */
function haloText(group, attrs, text) {
  group.appendChild(svgEl("text", { ...attrs, class: (attrs.class || "") + " halo" }, text));
  return group.appendChild(svgEl("text", attrs, text));
}

/** Horizontal gridlines and tick values on the left of a plot. */
function yAxis(svg, yOf, domain, left, right, given) {
  const step = given > 0 ? given : tickStep(domain[0], domain[1], GEOMETRY.Y_TICKS);
  for (const value of tickValues(domain[0], domain[1], GEOMETRY.Y_TICKS, step)) {
    const y = yOf(value);
    svg.appendChild(svgEl("line", { class: "mark-grid", x1: px(left), x2: px(right), y1: px(y), y2: px(y) }));
    svg.appendChild(svgEl("text", {
      class: "tick", x: px(left - GEOMETRY.LABEL_GAP), y: px(y), "text-anchor": "end", "dominant-baseline": "middle",
    }, tickLabel(value, step)));
  }
}

/** Ticks and tick values under a plot. */
function xAxis(svg, xOf, values, labels, bottom) {
  values.forEach((value, index) => {
    const x = xOf(value);
    svg.appendChild(svgEl("line", { class: "mark-context", x1: px(x), x2: px(x), y1: px(bottom), y2: px(bottom + GEOMETRY.TICK_LENGTH) }));
    svg.appendChild(svgEl("text", { class: "tick", x: px(x), y: px(bottom + GEOMETRY.AXIS_GAP), "text-anchor": "middle", "dominant-baseline": "middle" }, labels[index]));
  });
}

/* ======================================================== netback bar === */

/** One route's netback at Sabine Pass, a bar from zero in a table row, at the
 *  size of its cell.
 *
 *    row        { value, open, accent }
 *    scale      [low, high] from the artifact, zero inside
 *    threshold  a value or null: the dashed rule at 115 percent of Henry Hub,
 *               drawn the height of the cell, so it runs down the column
 *
 *  A closed route is an outline, never a filled bar; the best route is the
 *  one accent bar. */
export function netbackBar({ width, height, row, scale, threshold }) {
  const g = GEOMETRY;
  const svg = hiddenSvg({ width, height, className: "chart--bar" });
  const inset = g.RING_WIDTH;
  const xOf = linear(scale[0], scale[1], inset, Math.max(width - inset, inset));
  const barTop = (height - g.BAR_THICKNESS) * g.HALF;
  const zero = xOf(0);
  svg.appendChild(svgEl("line", { class: "mark-context", x1: px(zero), x2: px(zero), y1: 0, y2: height }));
  if (present(row.value)) {
    const from = xOf(Math.min(0, row.value));
    const to = xOf(Math.max(0, row.value));
    const attrs = { x: px(from), y: px(barTop), width: px(Math.max(to - from, 0)), height: g.BAR_THICKNESS };
    let className = "mark-series-fill";
    if (!row.open) className = "mark-closed";
    else if (row.accent) className = "mark-accent-bar";
    if (to - from < g.SMALL_STEP) {
      // Too small for a bar: a dot, so a value is never drawn as nothing.
      svg.appendChild(svgEl("circle", { class: row.accent ? "mark-accent-dot" : (row.open ? "mark-series-fill" : "mark-printed"), cx: px(to), cy: px(barTop + g.BAR_THICKNESS * g.HALF), r: g.SMALL_RADIUS }));
    } else {
      svg.appendChild(svgEl("rect", { ...attrs, class: className }));
    }
  }
  if (present(threshold)) {
    const x = xOf(threshold);
    svg.appendChild(svgEl("line", { class: "mark-reference", x1: px(x), x2: px(x), y1: 0, y2: height }));
  }
  return svg;
}

/* ====================================================== waterfall bar === */

/** One row's bar in the waterfall table, at the size of its cell.
 *
 *    row      { kind: "step" | "total", start, end, accent }
 *    previous the row before it, or null, for the connector
 *    isLast   no connector below the last row
 *    scale    [low, high] from the artifact, zero inside
 *
 *  Positive steps filled, negative outlined, a step under SMALL_STEP px a dot,
 *  the total in the accent when the artifact marks it. */
export function waterfallBar({ width, height, row, previous, isLast, scale }) {
  const g = GEOMETRY;
  const svg = hiddenSvg({ width, height, className: "chart--bar" });
  const inset = g.SMALL_RADIUS + g.RING_WIDTH;
  const xOf = linear(scale[0], scale[1], inset, Math.max(width - inset, inset));
  const barTop = (height - g.BAR_THICKNESS) * g.HALF;
  const barBottom = barTop + g.BAR_THICKNESS;

  const zero = xOf(0);
  svg.appendChild(svgEl("line", { class: "mark-context", x1: px(zero), x2: px(zero), y1: 0, y2: height }));

  if (previous && present(previous.end)) {
    const x = xOf(previous.end);
    svg.appendChild(svgEl("line", { class: "mark-connector", x1: px(x), x2: px(x), y1: 0, y2: px(barTop) }));
  }
  if (!isLast && present(row.end)) {
    const x = xOf(row.end);
    svg.appendChild(svgEl("line", { class: "mark-connector", x1: px(x), x2: px(x), y1: px(barBottom), y2: height }));
  }
  if (!present(row.start) || !present(row.end)) return svg;

  const from = xOf(Math.min(row.start, row.end));
  const to = xOf(Math.max(row.start, row.end));
  const negative = row.end < row.start;
  const middle = (barTop + barBottom) * g.HALF;

  if (row.kind === "total") {
    if (to - from < g.SMALL_STEP) {
      svg.appendChild(svgEl("circle", { class: row.accent ? "mark-accent-dot" : "mark-series-fill", cx: px(xOf(row.end)), cy: px(middle), r: g.SMALL_RADIUS }));
      return svg;
    }
    svg.appendChild(svgEl("rect", {
      class: row.accent ? (negative ? "mark-accent-outline" : "mark-accent-bar") : (negative ? "mark-negative" : "mark-series-fill"),
      x: px(from), y: px(barTop), width: px(Math.max(to - from, 0)), height: g.BAR_THICKNESS,
    }));
    return svg;
  }
  if (to - from < g.SMALL_STEP) {
    svg.appendChild(svgEl("circle", { class: negative ? "mark-negative" : "mark-series-fill", cx: px(xOf(row.end)), cy: px(middle), r: g.SMALL_RADIUS }));
    return svg;
  }
  if (negative) {
    svg.appendChild(svgEl("rect", {
      class: "mark-negative",
      x: px(from + g.OUTLINE_INSET), y: px(barTop + g.OUTLINE_INSET),
      width: px(to - from - g.OUTLINE_INSET - g.OUTLINE_INSET), height: px(g.BAR_THICKNESS - g.OUTLINE_INSET - g.OUTLINE_INSET),
    }));
  } else {
    svg.appendChild(svgEl("rect", { class: "mark-series-fill", x: px(from), y: px(barTop), width: px(to - from), height: g.BAR_THICKNESS }));
  }
  return svg;
}

/* ===================================================== breakeven lines === */

/** S* against hire for each open route east.
 *
 *    xDomain, yDomain   from the artifact; x in $/day
 *    xDivisor           x tick values are printed divided by this (thousands)
 *    lines              [{ route, pattern, points: [[hire, s], [hire, s]],
 *                          hStar, label }] for the open routes
 *    spread             { value, label }: today's JKM over TTF, the accent rule
 *    reported           { hire, label } or null: the reported charter rate
 *    words              { title, desc, xAxis, yAxis }
 */
export function breakevenChart({ width, xDomain, yDomain, xStep, yStep, xDivisor, lines, spread, reported, words }) {
  const g = GEOMETRY;
  const narrow = width < g.NARROW_WIDTH;
  const plotHeight = narrow ? g.BREAKEVEN_HEIGHT_NARROW : g.BREAKEVEN_HEIGHT;
  const top = g.PAD_TOP;
  const bottom = top + plotHeight;
  const height = bottom + g.AXIS_GAP + g.AXIS_BELOW;
  const left = g.PAD_LEFT;
  const right = Math.max(width - g.PAD_RIGHT, left + g.PAD_LEFT);
  const svg = imageSvg({ width, height, title: words.title, desc: words.desc, className: "chart--breakeven" });
  const xOf = linear(xDomain[0], xDomain[1], left, right);
  const yOf = linear(yDomain[0], yDomain[1], bottom, top);

  yAxis(svg, yOf, yDomain, left, right, yStep);
  svg.appendChild(svgEl("text", { class: "chart-axis-title", x: px(left - g.PAD_LEFT), y: px(g.AXIS_GAP) }, words.yAxis));
  const xTicks = tickValues(xDomain[0], xDomain[1], g.X_TICKS, xStep);
  const shownStep = (xStep > 0 ? xStep : tickStep(xDomain[0], xDomain[1], g.X_TICKS)) / xDivisor;
  xAxis(svg, xOf, xTicks, xTicks.map((value) => tickLabel(value / xDivisor, shownStep)), bottom);
  svg.appendChild(svgEl("text", { class: "chart-axis-title", x: px(right), y: px(height - g.RING_WIDTH), "text-anchor": "end" }, words.xAxis));

  if (yDomain[0] < 0 && yDomain[1] > 0) {
    const y = yOf(0);
    svg.appendChild(svgEl("line", { class: "mark-context", x1: px(left), x2: px(right), y1: px(y), y2: px(y) }));
  }

  if (reported && present(reported.hire)) {
    const x = xOf(reported.hire);
    svg.appendChild(svgEl("line", { class: "mark-reference", x1: px(x), x2: px(x), y1: px(top), y2: px(bottom) }));
    // Labelled at the foot of the rule, clear of the end labels at the top
    // right, where the steepest route's line ends.
    haloText(svg, { class: "chart-label--context", x: px(x + g.RING_WIDTH + g.RING_WIDTH), y: px(bottom - g.LABEL_GAP) }, reported.label);
  }

  const group = svgEl("g", {});
  const labels = [];
  for (const line of lines) {
    const node = svgEl("g", { class: "line line--" + line.pattern });
    drawRuns(node, splitRuns(line.points), xOf, yOf);
    group.appendChild(node);
    const last = line.points[line.points.length - 1];
    if (present(last[1])) labels.push({ want: yOf(last[1]), text: line.label });
  }
  svg.appendChild(group);

  if (present(spread.value)) {
    const y = yOf(spread.value);
    svg.appendChild(svgEl("line", { class: "mark-accent-rule", x1: px(left), x2: px(right), y1: px(y), y2: px(y) }));
    haloText(svg, { class: "chart-label text-accent", x: px(left + g.LABEL_GAP), y: px(y - g.LABEL_GAP) }, spread.label);
    for (const line of lines) {
      if (!present(line.hStar) || line.hStar < xDomain[0] || line.hStar > xDomain[1]) continue;
      svg.appendChild(svgEl("circle", { class: "mark-printed", cx: px(xOf(line.hStar)), cy: px(y), r: g.DOT_RADIUS }));
    }
  }

  for (const item of spreadLabels(labels, top, bottom)) {
    haloText(svg, { class: "chart-label", x: px(right + g.LABEL_GAP), y: px(item.y), "dominant-baseline": "middle" }, item.text);
  }
  return svg;
}

/* ============================================================== flows === */

/** The monthly share of US exports to Asia, over the arb at loading.
 *
 *    months   [{ label, values: { name: number | null }, arb }] in order
 *    shares   [{ key, pattern, label }]: the share lines, percent 0 to 100
 *    arbDomain  [low, high] from the artifact, zero inside
 *    ticks    indexes of the months that carry an x label
 *    words    { title, desc, shareAxis, arbAxis }
 *
 *  Two panels on one month axis: the share lines, then the arb as bars from a
 *  drawn zero line, filled when positive and outlined when negative. */
export function flowsChart({ width, months, shares, shareDomain, arbDomain, shareStep, arbStep, ticks, words }) {
  const g = GEOMETRY;
  const left = g.PAD_LEFT;
  const right = Math.max(width - g.PAD_RIGHT, left + g.PAD_LEFT);
  const shareTop = g.PAD_TOP;
  const shareBottom = shareTop + g.SHARE_HEIGHT;
  const arbTop = shareBottom + g.PANEL_GAP + g.PAD_TOP;
  const arbBottom = arbTop + g.ARB_HEIGHT;
  const height = arbBottom + g.AXIS_GAP + g.AXIS_BELOW;
  const svg = imageSvg({ width, height, title: words.title, desc: words.desc, className: "chart--flows" });
  const slot = (right - left) / Math.max(months.length, 1);
  const xOf = (index) => left + slot * (index + g.HALF);

  const yShare = linear(shareDomain[0], shareDomain[1], shareBottom, shareTop);
  yAxis(svg, yShare, shareDomain, left, right, shareStep);
  svg.appendChild(svgEl("text", { class: "chart-axis-title", x: px(left - g.PAD_LEFT), y: px(g.AXIS_GAP) }, words.shareAxis));

  const labels = [];
  for (const share of shares) {
    const node = svgEl("g", { class: "line line--" + share.pattern });
    drawRuns(node, splitRuns(months.map((month, index) => [index, month.values[share.key]])), xOf, yShare);
    svg.appendChild(node);
    for (let index = months.length - 1; index >= 0; index -= 1) {
      const value = months[index].values[share.key];
      if (present(value)) {
        labels.push({ want: yShare(value), text: share.label });
        break;
      }
    }
  }
  for (const item of spreadLabels(labels, shareTop, shareBottom)) {
    haloText(svg, { class: "chart-label", x: px(right + g.LABEL_GAP), y: px(item.y), "dominant-baseline": "middle" }, item.text);
  }

  const yArb = linear(arbDomain[0], arbDomain[1], arbBottom, arbTop);
  yAxis(svg, yArb, arbDomain, left, right, arbStep);
  svg.appendChild(svgEl("text", { class: "chart-axis-title", x: px(left - g.PAD_LEFT), y: px(arbTop - g.LABEL_GAP - g.LABEL_GAP) }, words.arbAxis));
  // Bars from zero: filled when positive, outlined when negative; the latest
  // month, the one the reader is likely to ask about, in the accent. A present
  // value too small for a bar is a dot on the zero line, so it never looks like
  // a missing month.
  const zero = yArb(0);
  const barWidth = slot * g.BAR_SHARE;
  const dots = [];
  months.forEach((month, index) => {
    if (!present(month.arb)) return;
    const latest = index === months.length - 1;
    const y = yArb(month.arb);
    const x = xOf(index) - barWidth * g.HALF;
    const top = Math.min(y, zero);
    const tall = Math.abs(y - zero);
    if (tall < g.SMALL_STEP) {
      dots.push({ cx: xOf(index), negative: month.arb < 0, latest });
    } else if (month.arb < 0 && barWidth - g.OUTLINE_INSET - g.OUTLINE_INSET <= 0) {
      // Too narrow for an outline: the month is a line, so it still shows.
      svg.appendChild(svgEl("line", { class: latest ? "mark-accent-outline" : "mark-negative", x1: px(xOf(index)), x2: px(xOf(index)), y1: px(top), y2: px(top + tall) }));
    } else if (month.arb < 0) {
      svg.appendChild(svgEl("rect", { class: latest ? "mark-accent-outline" : "mark-negative", x: px(x + g.OUTLINE_INSET), y: px(top + g.OUTLINE_INSET), width: px(Math.max(barWidth - g.OUTLINE_INSET - g.OUTLINE_INSET, 0)), height: px(Math.max(tall - g.OUTLINE_INSET - g.OUTLINE_INSET, 0)) }));
    } else {
      svg.appendChild(svgEl("rect", { class: latest ? "mark-accent-bar" : "mark-series-fill", x: px(x), y: px(top), width: px(barWidth), height: px(tall) }));
    }
  });
  svg.appendChild(svgEl("line", { class: "mark-context", x1: px(left), x2: px(right), y1: px(zero), y2: px(zero) }));
  for (const dot of dots) {
    const className = dot.latest ? "mark-accent-dot" : (dot.negative ? "mark-printed" : "mark-series-fill");
    svg.appendChild(svgEl("circle", { class: className, cx: px(dot.cx), cy: px(zero), r: g.SMALL_RADIUS }));
  }

  // Month labels thinned to every few where they would touch at this width.
  const tickSpacing = ticks.length > 1 ? (xOf(ticks[ticks.length - 1]) - xOf(ticks[0])) / (ticks.length - 1) : right - left;
  const longest = Math.max(0, ...ticks.map((index) => months[index].label.length));
  const every = Math.max(1, Math.ceil((longest * g.TICK_CHAR + g.LABEL_GAP) / Math.max(tickSpacing, 1)));
  xAxis(svg, xOf, ticks, ticks.map((index, at) => (at % every === 0 ? months[index].label : "")), arbBottom);
  return svg;
}

/* ============================================================ history === */

/** Days as UTC milliseconds, from the artifact's ISO days. */
function dayValue(iso) {
  const [y, m, d] = iso.split("-").map(Number);
  return Date.UTC(y, m - 1, d);
}

/** A band between two series over time: one closed shape per run where both
 *  ends are present. */
function drawBand(group, xs, lows, highs, yOf) {
  let run = [];
  const flush = () => {
    if (run.length > 1) {
      const top = run.map(([x, , high], index) => (index === 0 ? "M" : "L") + px(x) + " " + px(yOf(high)));
      const bottom = [...run].reverse().map(([x, low]) => "L" + px(x) + " " + px(yOf(low)));
      group.appendChild(svgEl("path", { class: "band-span", d: top.join(" ") + " " + bottom.join(" ") + " Z" }));
    }
    run = [];
  };
  xs.forEach((x, index) => {
    if (present(x) && present(lows[index]) && present(highs[index])) run.push([x, lows[index], highs[index]]);
    else flush();
  });
  flush();
}

/** One series over time, clipped to the plot, never joined across a gap. */
function drawSeries(group, xs, values, yOf, className) {
  const node = svgEl("g", { class: className });
  drawRuns(node, splitRuns(xs.map((x, index) => [x, present(x) ? values[index] : null])), (x) => x, yOf);
  group.appendChild(node);
}

/** A time series chart: the History view's panels.
 *
 *    days       ISO days, a gap as null
 *    first, last  the days the x axis spans
 *    y          { low, high, step, divisor }: from the artifact; divisor prints
 *               the tick values divided (thousands)
 *    band       { low: [], high: [], label } or null: a shaded span
 *    reference  { values: [], label } or null: a dashed line
 *    references [{ values, label, pattern }]: further lines, each drawn as
 *               .line--<pattern> (thin, dot or reference)
 *    series     { values: [], label }: the ink line
 *    marks      [{ index, kind }]: a hollow ring on the series at these points,
 *               a solid dot where kind is "mixed"
 *    rules      [{ day, numbers }]: numbered rules across the plot
 *    events     [{ day, end, letter }]: lettered marks at the foot of the plot,
 *               a bar for a period that has an end
 *    points     [{ day, value, accent }]: printed points, one in the accent
 *    ticks      [{ day, label }]
 *    words      { title, desc, yAxis }
 *
 *  Values beyond the y domain are clipped at its edge, where a short tick
 *  marks each one; the artifact counts them in words. */
export function timeChart({ width, days, first, last, y, band, reference, references, series, marks, rules, events, points, ticks, words, height }) {
  const g = GEOMETRY;
  const narrow = width < g.NARROW_WIDTH;
  const top = g.PAD_TOP + g.RULE_ROOM;
  const plotHeight = height || (narrow ? g.HISTORY_HEIGHT_NARROW : g.HISTORY_HEIGHT);
  const bottom = top + plotHeight;
  const total = bottom + g.AXIS_GAP + g.AXIS_BELOW;
  const left = g.PAD_LEFT;
  const right = Math.max(width - (narrow ? g.HISTORY_PAD_RIGHT_NARROW : g.HISTORY_PAD_RIGHT), left + g.PAD_LEFT);
  const svg = imageSvg({ width, height: total, title: words.title, desc: words.desc, className: "chart--history" });
  const xOf = linear(dayValue(first), dayValue(last), left, right);
  const yOf = linear(y.low, y.high, bottom, top);
  const divisor = y.divisor || 1;

  // The y axis, its values divided where the artifact says so.
  const step = y.step > 0 ? y.step : tickStep(y.low, y.high, g.Y_TICKS);
  for (const value of tickValues(y.low, y.high, g.Y_TICKS, step)) {
    const at = yOf(value);
    svg.appendChild(svgEl("line", { class: "mark-grid", x1: px(left), x2: px(right), y1: px(at), y2: px(at) }));
    svg.appendChild(svgEl("text", { class: "tick", x: px(left - g.LABEL_GAP), y: px(at), "text-anchor": "end", "dominant-baseline": "middle" }, tickLabel(value / divisor, step / divisor)));
  }
  svg.appendChild(svgEl("text", { class: "chart-axis-title", x: px(left - g.PAD_LEFT), y: px(g.AXIS_GAP) }, words.yAxis));
  if (y.low < 0 && y.high > 0) {
    svg.appendChild(svgEl("line", { class: "mark-context", x1: px(left), x2: px(right), y1: px(yOf(0)), y2: px(yOf(0)) }));
  }
  // Tick values thinned to every few where they would touch at this width.
  const spacing = ticks.length > 1 ? (xOf(dayValue(ticks[ticks.length - 1].day)) - xOf(dayValue(ticks[0].day))) / (ticks.length - 1) : right - left;
  const longest = Math.max(0, ...ticks.map((tick) => tick.label.length));
  const every = Math.max(1, Math.ceil((longest * g.TICK_CHAR + g.LABEL_GAP) / Math.max(spacing, 1)));
  xAxis(svg, (day) => xOf(dayValue(day)), ticks.map((tick) => tick.day),
    ticks.map((tick, index) => (index % every === 0 ? tick.label : "")), bottom);

  // The breaks: a rule each, numbered above the plot. A label starts at its
  // first rule, or is moved back inside the chart's right edge; one that would
  // touch the label before it, where both are drawn, joins that label.
  // One number, a pair, or the first and last of three or more.
  const ruleLabel = (numbers) => (numbers.slice(1).length > 1
    ? String(numbers[0]) + " to " + String(numbers[numbers.length - 1]) : numbers.join(", "));
  const labelAt = (group) => Math.min(group.at, width - ruleLabel(group.numbers).length * g.RULE_CHAR);
  const groups = [];
  for (const rule of rules || []) {
    const at = xOf(dayValue(rule.day));
    if (!present(at) || at < left || at > right) continue;
    svg.appendChild(svgEl("line", { class: "mark-decor", x1: px(at), x2: px(at), y1: px(top), y2: px(bottom) }));
    groups.push({ at, numbers: [...rule.numbers] });
    // A joined label is longer and may move, so it is checked in turn.
    while (groups.slice(1).length > 0) {
      const last = groups.pop();
      const before = groups[groups.length - 1];
      if (labelAt(last) >= labelAt(before) + ruleLabel(before.numbers).length * g.RULE_CHAR + g.LABEL_GAP) {
        groups.push(last);
        break;
      }
      before.numbers.push(...last.numbers);
    }
  }
  for (const group of groups) {
    svg.appendChild(svgEl("text", { class: "tick", x: px(labelAt(group)), y: px(top - g.LABEL_GAP), "text-anchor": "start" }, ruleLabel(group.numbers)));
  }

  // Everything inside the plot is clipped to it; what lies beyond is marked.
  const clipId = uid("history-clip");
  const defs = svgEl("defs", {});
  const clip = svgEl("clipPath", { id: clipId });
  clip.appendChild(svgEl("rect", { x: px(left), y: px(top), width: px(right - left), height: px(bottom - top) }));
  defs.appendChild(clip);
  svg.appendChild(defs);
  const plot = svgEl("g", { "clip-path": "url(#" + clipId + ")" });
  svg.appendChild(plot);

  const xs = days.map((day) => (day === null ? null : xOf(dayValue(day))));
  if (band) drawBand(plot, xs, band.low, band.high, yOf);
  if (reference) drawSeries(plot, xs, reference.values, yOf, "line line--reference");
  for (const other of references || []) drawSeries(plot, xs, other.values, yOf, "line line--" + other.pattern);
  drawSeries(plot, xs, series.values, yOf, "line");
  for (const mark of marks || []) {
    const value = series.values[mark.index];
    if (!present(value) || !present(xs[mark.index])) continue;
    // A mixed week is a solid dot, a misaligned one a ring.
    plot.appendChild(mark.kind === "mixed"
      ? svgEl("circle", { class: "mark-series-fill", cx: px(xs[mark.index]), cy: px(yOf(value)), r: g.SMALL_RADIUS })
      : svgEl("circle", { class: "mark-printed", cx: px(xs[mark.index]), cy: px(yOf(value)), r: g.SMALL_RADIUS }));
  }
  series.values.forEach((value, index) => {
    if (!present(value) || !present(xs[index]) || (value >= y.low && value <= y.high)) return;
    const edge = value < y.low ? bottom : top;
    const inward = value < y.low ? -g.TICK_LENGTH : g.TICK_LENGTH;
    svg.appendChild(svgEl("line", { class: "mark-context", x1: px(xs[index]), x2: px(xs[index]), y1: px(edge), y2: px(edge + inward) }));
  });
  for (const point of points || []) {
    const at = xOf(dayValue(point.day));
    if (!present(at) || !present(point.value) || at < left || at > right) continue;
    const cy = yOf(Math.min(Math.max(point.value, y.low), y.high));
    svg.appendChild(svgEl("circle", { class: point.accent ? "mark-accent-dot" : "mark-printed", cx: px(at), cy: px(cy), r: g.DOT_RADIUS }));
  }

  // The events: a mark, or a bar for a period, at the foot of the plot, its
  // letter above; letters that would touch join the one before.
  const eventLabels = [];
  for (const item of events || []) {
    const from = Math.max(xOf(dayValue(item.day)), left);
    const to = Math.min(item.end ? xOf(dayValue(item.end)) : xOf(dayValue(item.day)), right);
    if (!present(from) || !present(to) || to < left || from > right || to < from) continue;
    if (item.end) {
      svg.appendChild(svgEl("rect", { class: "mark-event-fill", x: px(from), y: px(bottom - g.EVENT_BAR), width: px(Math.max(to - from, g.EVENT_BAR)), height: px(g.EVENT_BAR) }));
    } else {
      svg.appendChild(svgEl("line", { class: "mark-event", x1: px(from), x2: px(from), y1: px(bottom), y2: px(bottom - g.EVENT_TICK) }));
    }
    const before = eventLabels[eventLabels.length - 1];
    const placed = (label) => Math.min(label.at, right - label.text.length * g.RULE_CHAR);
    if (before && Math.min(from, right - item.letter.length * g.RULE_CHAR) < placed(before) + before.text.length * g.RULE_CHAR + g.LABEL_GAP) {
      before.text += ", " + item.letter;
    } else {
      eventLabels.push({ at: from, text: item.letter });
    }
  }
  for (const label of eventLabels) {
    haloText(svg, { class: "tick event-label", x: px(Math.min(label.at, right - label.text.length * g.RULE_CHAR)), y: px(bottom - g.EVENT_TICK - g.LABEL_GAP), "text-anchor": "start" }, label.text);
  }

  // Labels at the right end of each line, apart.
  const labels = [];
  const lastPresent = (values) => {
    for (let index = values.length - 1; index >= 0; index -= 1) if (present(values[index])) return values[index];
    return null;
  };
  const clamp = (value) => Math.min(Math.max(value, y.low), y.high);
  const end = lastPresent(series.values);
  if (present(end)) labels.push({ want: yOf(clamp(end)), text: series.label });
  for (const other of [...(reference ? [reference] : []), ...(references || [])]) {
    const at = lastPresent(other.values);
    if (present(at)) labels.push({ want: yOf(clamp(at)), text: other.label });
  }
  if (band) {
    const high = lastPresent(band.high);
    if (present(high)) labels.push({ want: yOf(clamp(high)), text: band.label });
  }
  if (!narrow) {
    for (const item of spreadLabels(labels, top, bottom)) {
      haloText(svg, { class: "chart-label", x: px(right + g.LABEL_GAP), y: px(item.y), "dominant-baseline": "middle" }, item.text);
    }
  }
  return svg;
}

/** The plain text of a sentence of segments, for a title or desc. */
export function words(segments, decimals) {
  return segmentsText(segments || [], decimals);
}

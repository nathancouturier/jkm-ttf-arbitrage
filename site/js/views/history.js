// History: JKM minus TTF against the reroute level, week by week and month by month.

import { usdMmbtuToEurMwh } from "../engine.js";
import { h, b, put, num, int, day, month, toDate, ROUTES, EAST, tag, panel, table, segmented } from "../util.js";
import { frame, axisX, axisY, path, s, showTip, hover, dot, d3 } from "../chart.js";

const HIRE = [["rep", "Reported"], ["0", "Sunk"], ["low", "Low"], ["central", "Central"], ["high", "High"]];
const ROUTE = [["best", "Cheapest open"], ["panama", "Panama"], ["cape", "Cape"], ["suez", "Suez"]];
const RANGE = [["all", "All"], ["2024", "Since 2024"], ["52", "Last year"]];

export function mount(root, ctx) {
  const D = ctx.D;
  const scenarios = Object.fromEntries(Object.entries(D.presets[0].ships).map(([id, sh]) => [id, sh.scenarios]));

  const kicker = h("p", { class: "kicker" });
  const head = h("h1");
  const dek = h("p", { class: "dek" });
  const controls = h("div", { class: "controls" });
  const figTitle = h("p", { class: "fig-title" });
  const legend = h("p", { class: "fig-sub" });
  const plot = h("div");
  const source = h("p", { class: "source" });
  const tableBody = h("div");
  const eventsBody = h("div");
  root.append(kicker, head, dek, controls, h("figure", null, figTitle, legend, plot, source),
    h("div", { class: "more" }, panel("The table", tableBody), panel("Events and their sources", eventsBody)));

  let tuneOpen = false;    // on a phone the three lesser controls sit behind one button that states them

  const state = () => ({
    freq: ctx.params.freq === "m" ? "m" : "w",
    hire: HIRE.some(([k]) => k === ctx.params.hire) ? ctx.params.hire : "rep",
    route: ROUTE.some(([k]) => k === ctx.params.route) ? ctx.params.route : "best",
    range: RANGE.some(([k]) => k === ctx.params.range) ? ctx.params.range : "all",
  });

  // One row with the hire case and the route choice applied.
  function evaluate(row, st) {
    const hire = st.hire === "rep" ? row.hire : st.hire === "0" ? 0 : scenarios[row.ship][st.hire];
    const levels = Object.fromEntries(EAST.map((id) => [id, row.routes[id][0] + (row.routes[id][1] * hire) / 1e5]));
    let route = st.route;
    let available = true;
    if (st.route === "best") {
      const open = EAST.filter((id) => row.routes[id][2] === "open");
      route = open.reduce((a, c) => (levels[c] < levels[a] ? c : a), open[0]);
    } else available = row.routes[route][2] === "open";
    const level = levels[route];
    return { ...row, t: toDate(row.date), hireUsed: hire, levels, route, level, available, open: available && row.spread > level };
  }

  function draw(rows, st, weekly) {
    const narrow = (plot.clientWidth || 900) < 640;
    const events = D.events.filter((e) => (e.on || []).includes(weekly ? "weekly" : "monthly") && e.date >= rows[0].date.slice(0, 7) && e.date <= rows[rows.length - 1].date);
    const c = frame(plot, {
      height: narrow ? 400 : 500, margin: { top: narrow ? 64 : 52, right: narrow ? 12 : 26, bottom: 34, left: 40 },
      label: "JKM minus TTF and the reroute level over time, with the periods when the arb was open shaded",
    });
    const x = d3.scaleUtc([rows[0].t, rows[rows.length - 1].t], [0, c.w]);
    const values = rows.flatMap((r) => [r.spread, r.level]);
    const lo = Math.max(-6, Math.floor(d3.min(values) - 0.5));
    const hi = Math.min(8, Math.ceil(d3.max(values) + 0.5));
    const y = d3.scaleLinear([lo, hi], [c.h, 0]);
    const clipId = "clip-history";
    s("rect", { x: 0, y: 0, width: c.w, height: c.h }, s("clipPath", { id: clipId }, s("defs", null, c.svg)));

    // Runs of rows with no hole in the prices longer than three periods: nothing is drawn or shaded across missing prices.
    const step = weekly ? 7 : 31;
    const runs = [];
    rows.forEach((r, i) => {
      if (!i || (r.t - rows[i - 1].t) / 864e5 > step * 3) runs.push([]);
      runs[runs.length - 1].push(r);
    });

    // shaded: the arb open
    const half = ((c.w / Math.max(1, (rows[rows.length - 1].t - rows[0].t) / 864e5)) * step) / 2 || 3;
    for (const part of runs) {
      let run = null;
      const flush = (end) => { if (run) s("rect", { x: Math.max(0, x(run.t) - half), y: 0, width: Math.min(c.w, x(end.t) + half) - Math.max(0, x(run.t) - half), height: c.h, fill: "var(--wash)" }, c.g); run = null; };
      part.forEach((r, i) => {
        if (r.open && !run) run = r;
        if (!r.open && run) flush(part[i - 1]);
      });
      flush(part[part.length - 1]);
    }

    axisY(c, y, { values: d3.ticks(lo, hi, 7), format: (v) => num(v, 0), label: "USD/MMBtu" });
    const years = d3.utcYear.range(d3.utcYear.ceil(rows[0].t), rows[rows.length - 1].t);
    const tickDates = years.length >= 2 ? (narrow && years.length > 6 ? years.filter((_, i) => i % 2 === 0) : years) : x.ticks(6);
    axisX(c, x, { values: tickDates, format: years.length >= 2 ? d3.utcFormat("%Y") : d3.utcFormat("%b %Y") });

    const plotG = s("g", { "clip-path": `url(#${clipId})` }, c.g);
    const inner = { ...c, g: plotG };
    // the reroute level, coloured by the route that sets it; dashed where the route was not open
    for (const part of runs) {
      let seg = [];
      const emit = () => {
        if (seg.length > 1) path(inner, seg.map((r) => [x(r.t), y(r.level)]),
          { stroke: ROUTES[seg[0].route].color, "stroke-width": 1.8, "stroke-dasharray": seg[0].available ? null : "2 4" });
      };
      part.forEach((r, i) => {
        const prev = part[i - 1];
        if (prev && (prev.route !== r.route || prev.available !== r.available)) { seg.push(r); emit(); seg = []; }
        seg.push(r);
      });
      emit();
      path(inner, part.map((r) => [x(r.t), y(r.spread)]), { stroke: "var(--ink)", "stroke-width": 1.6 });
    }
    const holes = runs.length - 1;
    const last = rows[rows.length - 1];
    dot(c, x(last.t), y(Math.max(lo, Math.min(hi, last.spread))), "var(--accent)", 4.5);     // drawn outside the clip, so the edge does not cut it

    // off the scale
    const lowest = rows.reduce((a, r) => (r.spread < a.spread ? r : a));
    if (lowest.spread < lo) s("text", { class: "label-sub halo", x: Math.min(c.w - 150, Math.max(4, x(lowest.t) - 60)), y: c.h - 8 }, c.g, `off the scale: ${num(lowest.spread, 1)} in ${month(lowest.date, true)}`);
    const highest = rows.reduce((a, r) => (r.spread > a.spread ? r : a));
    if (highest.spread > hi) s("text", { class: "label-sub halo", x: Math.max(4, x(highest.t) + 8), y: 12 }, c.g, `off the scale: ${num(highest.spread, 1)}`);

    // events: at most eight labels, in two rows above the plot
    const rowsUsed = [[], []];
    const ordered = [...events].sort((a, e) => (a.date < e.date ? 1 : -1));
    for (const e of ordered) {
      const ex = x(toDate(e.date));
      const width = e.label.length * 6.3 + 10;
      const anchor = ex + width > c.w ? "end" : "start";
      const from = anchor === "end" ? ex - width : ex;
      const level = rowsUsed.findIndex((used) => used.every(([a, z]) => from > z || from + width < a));
      const g = s("g", { class: "event" }, c.g);
      if (level < 0 || (narrow && rowsUsed[0].length + rowsUsed[1].length >= 4)) { s("line", { x1: ex, x2: ex, y1: -5, y2: 0 }, g); continue; }
      rowsUsed[level].push([from, from + width]);
      const ty = -c.margin.top + 14 + level * 15 + (narrow ? 12 : 0);
      s("line", { x1: ex, x2: ex, y1: ty + 4, y2: c.h, "stroke-dasharray": "1 3" }, g);
      s("text", { x: anchor === "end" ? ex - 4 : ex + 4, y: ty, "text-anchor": anchor }, g, e.label);
    }

    const cursor = s("line", { class: "cursor", y1: 0, y2: c.h, visibility: "hidden" }, c.g);
    const bisect = d3.bisector((r) => r.t).center;
    hover(c, {
      count: rows.length,
      toIndex: (px) => bisect(rows, x.invert(px)),
      leave: () => cursor.setAttribute("visibility", "hidden"),
      move: (i) => {
        const r = rows[i];
        cursor.setAttribute("x1", x(r.t)); cursor.setAttribute("x2", x(r.t)); cursor.setAttribute("visibility", "visible");
        const near = D.events.filter((e) => (weekly ? Math.abs(toDate(e.date) - r.t) < 4.5 * 864e5 : e.date.slice(0, 7) === r.date.slice(0, 7)));
        showTip(c, x(r.t), y(Math.max(lo, Math.min(hi, r.spread))), weekly ? `Week to ${day(r.date)}` : month(r.date), [
          { key: "c-ink", label: "JKM minus TTF", value: num(r.spread) },
          { key: ROUTES[r.route].cls + (r.available ? "" : " dash"), label: `Level ${ROUTES[r.route].via}`, value: num(r.level) },
          { label: "JKM", value: num(r.jkm) },
          { label: "TTF", value: `${num(r.ttf)} (${num(usdMmbtuToEurMwh(r.ttf, r.fx), 1)} EUR/MWh)` },
          { label: "Charter rate" + (st.hire === "rep" && r.hire_status !== "reported" ? `, ${r.hire_status}` : ""), value: int(r.hireUsed) },
          { label: "DES discount" + (r.des_status !== "observed" ? `, ${r.des_status}` : ""), value: num(r.des) },
        ], [r.open ? "Arb open. " : r.available ? "Arb closed. " : "Route not open. ", near.map((e) => e.text).join(" ")].join(""));
      },
    });
    return holes;
  }

  function update() {
    const st = state();
    const weekly = st.freq === "w";
    let rows = (weekly ? D.history.weekly : D.history.monthly).map((r) => evaluate(r, st));
    if (st.range === "2024") rows = rows.filter((r) => r.date >= "2024-01-01");
    if (st.range === "52") rows = rows.slice(weekly ? -52 : -12);
    const unit = weekly ? "weeks" : "months";
    const counted = rows.filter((r) => r.available);
    const open = counted.filter((r) => r.open).length;
    const sunkOpen = st.hire === "rep" ? rows.map((r) => evaluate(r, { ...st, hire: "0" })).filter((r) => r.open).length : null;
    const where = st.route === "best" ? "the reroute level of the cheapest open route" : `the level ${ROUTES[st.route].via}`;
    const hireWords = { rep: "at the reported charter rate", 0: "with the ship already paid for", low: "at the low charter rate", central: "at the central charter rate", high: "at the high charter rate" }[st.hire];

    const lastRow = rows[rows.length - 1];
    const toDateOnly = !weekly && lastRow.date.slice(0, 7) === D.data_date.slice(0, 7);     // the current month, on the weeks published so far
    put(kicker, `${weekly ? "Weekly" : "Monthly"}, ${month(rows[0].date)} to ${weekly ? day(lastRow.date) : month(lastRow.date)}${toDateOnly ? ", the last month to date" : ""}`);
    put(head, "JKM minus TTF cleared ", where, " in ", b(`${open} of ${counted.length} ${unit}`), " ", hireWords,
      sunkOpen != null ? [", and in ", b(String(sunkOpen)), " with the ship already paid for."] : ".");

    const byYear = d3.rollups(counted, (v) => [v.filter((r) => r.open).length, v.length], (r) => r.date.slice(0, 4)).filter(([, [, n]]) => n >= (weekly ? 20 : 6));
    const share = ([, [o, n]]) => o / n;
    const best = byYear.reduce((a, c) => (share(c) > share(a) ? c : a), byYear[0]);
    const worst = byYear.reduce((a, c) => (share(c) < share(a) ? c : a), byYear[0]);
    const count = (key, value) => rows.filter((r) => r[key] === value).length;
    const desAssumed = count("des_status", "assumed");
    const rateWords = st.hire !== "rep" ? "" : [count("hire_status", "held") ? ` The charter rate is held from an earlier report in ${count("hire_status", "held")} of these ${unit}` : "",
      count("hire_status", "assumed") ? `${count("hire_status", "held") ? " and" : " The charter rate is"} assumed in ${count("hire_status", "assumed")}` : ""].join("") ;
    const lastAssumed = rows.filter((r) => r.des_status === "assumed").pop();
    put(dek, "Shaded: the arb east is open.", rateWords ? rateWords + "." : "", desAssumed ? ` Europe's DES discount is an assumption in ${desAssumed}, none after ${month(lastAssumed.date)}.` : "");
    put(figTitle, byYear.length > 1
      ? `Open most often in ${best[0]} (${best[1][0]} of ${best[1][1]} ${unit}) and least in ${worst[0]} (${worst[1][0]} of ${worst[1][1]})`
      : `Open in ${open} of ${counted.length} ${unit}`);
    put(legend, h("span", { class: "key c-ink" }), "JKM minus TTF   ",
      (st.route === "best" ? EAST : [st.route]).map((id) => [h("span", { class: "key " + ROUTES[id].cls, style: "margin-left:14px" }), `level ${ROUTES[id].via}`]),
      h("span", { class: "swatch c-accent", style: "margin-left:14px;border-radius:50%" }), "latest");

    const named = (options, key) => options.find(([k]) => k === key)[1].toLowerCase();
    put(controls,
      segmented("Frequency", [["w", "Weekly"], ["m", "Monthly from 2016"]], st.freq, (v) => ctx.set({ freq: v === "w" ? null : v, range: null })),
      h("button", { type: "button", class: "btn tune-toggle", "aria-expanded": String(tuneOpen), "data-focus": "tune", onclick: () => { tuneOpen = !tuneOpen; update(); } },
        `Charter rate ${named(HIRE, st.hire)}, route ${named(ROUTE, st.route)}, period ${named(RANGE, st.range)}`),
      h("div", { class: "tune" + (tuneOpen ? " open" : "") },
        segmented("Charter rate", HIRE, st.hire, (v) => ctx.set({ hire: v === "rep" ? null : v })),
        segmented("Route", ROUTE, st.route, (v) => ctx.set({ route: v === "best" ? null : v })),
        segmented("Period", RANGE, st.range, (v) => ctx.set({ range: v === "all" ? null : v }))));

    const holes = draw(rows, st, weekly);
    put(source, weekly
      ? "Prices: EIA weekly averages of front-month futures; before January 2022 swaps for JKM and day-ahead prices for TTF, as EIA then printed them. "
      : "Prices: METI's spot price for Japan as a proxy for JKM and the World Bank's TTF to September 2020, then means of EIA's weekly averages. ",
      "Charter rates: Spark30S Atlantic as reported. DES discount: ACER from 2023. Dotted level: the route was not open. ",
      holes ? "Breaks in the lines: no price was published. " : "",
      `Data to ${day(rows[rows.length - 1].date)}.`);

    put(tableBody, table([
      { label: weekly ? "Week to" : "Month", value: (r) => (weekly ? day(r.date, true) : month(r.date, true)), head: true },
      { label: "JKM", n: true, value: (r) => num(r.jkm) },
      { label: "TTF", n: true, value: (r) => num(r.ttf) },
      { label: "JKM minus TTF", n: true, value: (r) => num(r.spread) },
      { label: "Charter rate", n: true, value: (r) => [int(r.hireUsed), st.hire === "rep" ? tag(r.hire_status) : null] },
      { label: "DES discount", n: true, value: (r) => [num(r.des), tag(r.des_status)] },
      ...EAST.map((id) => ({ label: `Level ${ROUTES[id].via}`, n: true, value: (r) => num(r.levels[id]), cls: (r) => (r.routes[id][2] === "open" ? "" : "no") })),
      { label: "Arb", value: (r) => (r.open ? "open " + ROUTES[r.route].via : "closed"), cls: (r) => (r.open ? "yes" : "no") },
    ], [...rows].reverse(), { tall: true, min: 860, caption: "USD/MMBtu; charter rate in USD a day. Grey levels: the route was not open on that date." }));
    put(eventsBody, table([
      { label: "Date", value: (e) => (e.end ? `${day(e.date, true)} to ${day(e.end, true)}` : day(e.date, true)), head: true },
      { label: "Event", value: (e) => e.text },
      { label: "Source", value: (e) => h("a", { href: e.url, rel: "noopener" }, e.source) },
    ], D.events, { tall: true, min: 640 }));
  }

  return { update };
}

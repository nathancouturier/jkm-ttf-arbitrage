// Routes: the four ways out of Sabine Pass on one map, and what a Panama slot is worth against the Cape.

import { priceCargo, canalQuestion, withChanges } from "../engine.js";
import { h, b, put, num, int, musd, day, month, ROUTES, EAST, panel, table, segmented } from "../util.js";
import { frame, axisX, axisY, path, dot, s, showTip, hover, endLabels, d3 } from "../chart.js";

const LON = [-232, 152];
const LAT = [-50, 64];
const merc = (lat) => Math.log(Math.tan(Math.PI / 4 + (lat * Math.PI) / 360));
// where each route's label sits: a share of the way along its line, and a nudge in pixels
const LABEL_AT = { europe: [0.6, -16], panama: [0.6, -16], suez: [0.72, 18], cape: [0.72, 20] };
const PLACES = [["Panama Canal", -79.7, 9.1, 8, 15, "start"], ["Suez Canal", 32.55, 30.6, 8, -8, "start"], ["Cape of Good Hope", 18.47, -34.36, -8, 16, "end"]];

export function mount(root, ctx) {
  const D = ctx.D;
  const P = D.now.preset;
  const base = P.inputs;
  const res = priceCargo(base);

  const kicker = h("p", { class: "kicker" }, `Four routes from Sabine Pass, week to ${day(P.date)}`);
  const head = h("h1");
  const dek = h("p", { class: "dek" });
  const mapTitle = h("p", { class: "fig-title" });
  const mapBox = h("div", { class: "scroll" });
  const mapPlot = h("div");
  mapBox.append(mapPlot);
  const mapSource = h("p", { class: "source" });
  const controls = h("div", { class: "controls" });
  const figTitle = h("p", { class: "fig-title" });
  const plot = h("div");
  const source = h("p", { class: "source" });
  const factsBody = h("div");
  root.append(kicker, head, dek, h("figure", null, mapTitle, h("p", { class: "fig-sub hint-scroll" }, "Slide the map sideways to follow each route."), mapBox, mapSource),
    h("h2", null, "What a Panama slot is worth"),
    controls, h("figure", null, figTitle, plot, source),
    h("div", { class: "more" }, panel("Routes in figures", factsBody), panel("Route status since 2016", statusTable()), panel("LNG carriers through the canals", traffic()),
      panel("Panama, month by month", panamaMonths())));

  function statusTable() {
    return table([
      { label: "Route", value: (r) => ROUTES[r.route].name.replace("the ", ""), head: true },
      { label: "From", value: (r) => day(r.from, true) },
      { label: "Status", value: (r) => r.status },
      { label: "What the record shows", value: (r) => r.note },
      { label: "Source", value: (r) => (r.url ? h("a", { href: r.url, rel: "noopener" }, r.source) : r.source) },
    ], D.routes.status_history, { min: 720 });
  }

  function traffic() {
    const t = D.routes.traffic;
    const pan = t.panama_lng_transits_by_fiscal_year;
    const suez = Object.fromEntries(t.suez_lng_ships_by_year.rows.map((r) => [r.year, r.ships]));
    const top = Math.max(...pan.rows.map((r) => r.transits), ...Object.values(suez));
    const bar = (v, cls) => (v == null ? "" : h("span", { style: "display:flex;align-items:center;gap:8px;justify-content:flex-start" },
      h("span", { class: cls, style: `display:inline-block;height:10px;border-radius:2px;background:currentColor;width:${(v / top) * 120}px` }), int(v)));
    return [table([
      { label: "Year", value: (r) => r.fiscal_year, head: true },
      { label: "Panama, LNG transits (fiscal year to September)", value: (r) => bar(r.transits, "c-panama") },
      { label: "Suez, LNG carriers (calendar year)", value: (r) => bar(suez[r.fiscal_year], "c-suez") },
    ], pan.rows, { min: 480 }), h("p", { class: "source" }, "Both directions, all origins. Sources: ", pan.source, "; ", t.suez_lng_ships_by_year.source,
      ". Unbooked ships at Panama were reported waiting ", D.routes.waits_reported.map((w) => `${w.days} days in ${w.month}`).join(", "), ".")];
  }

  // The canal's own monthly record: how long a ship spent in canal waters, queue included.
  function panamaMonths() {
    const rows = [...D.routes.panama_monthly].reverse();
    return [table([
      { label: "Month", value: (r) => month(r.month, true), head: true },
      { label: "Hours in canal waters, average", n: true, value: (r) => num(r.cwt_hours_avg, 1) },
      { label: "Highest daily average", n: true, value: (r) => num(r.cwt_hours_high, 1) },
      { label: "Transits, all ships", n: true, value: (r) => (r.transits_total == null ? "" : int(r.transits_total)) },
      { label: "Of which through the Neopanamax locks", n: true, value: (r) => (r.neopanamax_transits == null ? "" : int(r.neopanamax_transits)) },
    ], rows, { tall: true, min: 560 }),
    h("p", { class: "source" }, "Canal waters time runs from arrival to exit, waiting included, for every kind of ship. Source: Panama Canal Authority, monthly canal operations summaries in its advisories to shipping.")];
  }

  function drawMap(map) {
    const W = Math.max(mapBox.clientWidth || 900, 700);
    const H = Math.round((W * (merc(LAT[1]) - merc(LAT[0]))) / (((LON[1] - LON[0]) * Math.PI) / 180));
    mapPlot.style.width = W + "px";
    const c = frame(mapPlot, { height: H, margin: { top: 0, right: 0, bottom: 0, left: 0 }, focusable: false,
      label: "Map of the four routes from Sabine Pass: to Gate, and to Futtsu via Panama, via Suez and via the Cape of Good Hope" });
    const x = (lon) => ((lon - LON[0]) / (LON[1] - LON[0])) * W;
    const y = (lat) => ((merc(LAT[1]) - merc(Math.max(-70, Math.min(80, lat)))) / (merc(LAT[1]) - merc(LAT[0]))) * H;
    s("rect", { x: 0, y: 0, width: W, height: H }, s("clipPath", { id: "clip-map" }, s("defs", null, c.svg)));
    const g = s("g", { "clip-path": "url(#clip-map)" }, c.g);
    // Each ring is drawn wherever a whole turn of the globe brings it into the window; inner rings (the Caspian) are cut out.
    let d = "";
    for (const shift of [-360, 0, 360]) {
      for (const ring of map.land) {
        if (ring.every(([lon]) => lon + shift < LON[0] - 5 || lon + shift > LON[1] + 5)) continue;
        d += "M" + ring.map(([lon, lat]) => `${x(lon + shift).toFixed(1)},${y(lat).toFixed(1)}`).join("L") + "Z";
      }
    }
    s("path", { d, fill: "var(--rule)", "fill-rule": "evenodd", stroke: "none" }, g);
    for (const id of ["cape", "suez", "panama", "europe"]) {
      const pts = map.routes[id].map(([lon, lat]) => [x(lon), y(lat)]);
      const open = res.routes[id].open;
      path({ g }, pts, { stroke: ROUTES[id].color, "stroke-width": 2.4, "stroke-dasharray": open ? null : "2 5" });
      // the label, part of the way along the line
      const lengths = pts.map((p, i) => (i ? Math.hypot(p[0] - pts[i - 1][0], p[1] - pts[i - 1][1]) : 0));
      const total = lengths.reduce((a, v) => a + v, 0);
      let walked = 0;
      let at = pts[0];
      for (let i = 1; i < pts.length; i += 1) { walked += lengths[i]; if (walked >= total * LABEL_AT[id][0]) { at = pts[i]; break; } }
      const r = res.routes[id];
      const t = s("text", { class: "label halo", x: at[0], y: at[1] + LABEL_AT[id][1], "text-anchor": "middle" }, c.g);
      s("tspan", { fill: ROUTES[id].color }, t, "● ");
      s("tspan", null, t, id === "europe" ? "to Gate" : ROUTES[id].via);
      const tolls = base.routes[id].toll_laden + base.routes[id].toll_ballast;
      s("tspan", { class: "label-sub", dx: 6 }, t, `${int(map_distance(id))} nm, ${num(r.round_trip_days, 0)} days${tolls ? `, tolls ${musd(tolls)} M USD` : ""}${open ? "" : ", closed"}`);
    }
    for (const [name, lon, lat, dx, dy, anchor] of PLACES) {
      s("circle", { cx: x(lon), cy: y(lat), r: 3, fill: "var(--paper)", stroke: "var(--ink)", "stroke-width": 1.2 }, c.g);
      s("text", { class: "label-sub halo", x: x(lon) + dx, y: y(lat) + dy, "text-anchor": anchor }, c.g, name);
    }
    const ports = [["Sabine Pass", map.ports.sabine_pass, 0, -12, "middle"], ["Gate", map.ports.gate, 10, -8, "start"],
      ["Futtsu", map.ports.futtsu, -10, -10, "end"], ["Futtsu", { ...map.ports.futtsu, lon: map.ports.futtsu.lon - 360 }, 10, -10, "start"]];
    for (const [name, p, dx, dy, anchor] of ports) {
      s("circle", { cx: x(p.lon), cy: y(p.lat), r: 5, fill: "var(--ink)", stroke: "var(--paper)", "stroke-width": 2 }, c.g);
      s("text", { class: "label halo", x: x(p.lon) + dx, y: y(p.lat) + dy, "text-anchor": anchor }, c.g, name);
    }
    // on a narrow screen the map scrolls sideways and opens on the Atlantic
    mapBox.scrollLeft = Math.max(0, x(-55) - mapBox.clientWidth / 2);
  }
  const map_distance = (id) => D.routes.distances[id];

  function drawCanal(mode) {
    const narrow = (plot.clientWidth || 900) < 600;
    const c = frame(plot, { height: narrow ? 320 : 400, margin: { top: 26, right: narrow ? 12 : 150, bottom: 46, left: 44 },
      label: "What a Panama slot is worth against the Cape, by charter rate and gas price" });
    const top = Math.max(200000, Math.ceil((base.hire * 1.15) / 50000) * 50000);      // the axis always reaches today's charter rate
    const hires = d3.range(0, top + 1, 5000);
    const levels = [[base.jkm, `JKM ${num(base.jkm)}, this week`, ROUTES.panama.color, 2.4], [20, "JKM 20", "var(--faint)", 1.5], [10, "JKM 10", "var(--faint)", 1.5]];
    const value = (q) => (mode === "wait" ? q.wait_days : q.premium_usd / 1e6);
    const series = levels.map(([jkm, label, color, width]) => ({ label, color, width,
      points: hires.map((hire) => [hire, value(canalQuestion(withChanges(base, { hire, jkm })))]) }));
    const all = series.flatMap((se) => se.points.map((p) => p[1]));
    const x = d3.scaleLinear([0, top], [0, c.w]);
    const y = d3.scaleLinear([Math.min(0, d3.min(all)), d3.max(all) * 1.05], [c.h, 0]).nice();
    axisY(c, y, { values: y.ticks(6), format: (v) => num(v, mode === "wait" ? 0 : 1), label: mode === "wait" ? "Days of waiting at each transit that cancel Panama's lead" : "Million USD for the two transits, above the tariff" });
    axisX(c, x, { values: (narrow ? [0, 0.5, 1] : [0, 0.25, 0.5, 0.75, 1]).map((k) => k * top), format: int, label: "Charter rate, USD a day" });
    for (const se of [...series].reverse()) path(c, se.points.map(([hire, v]) => [x(hire), y(v)]), { stroke: se.color, "stroke-width": se.width });
    const today = value(canalQuestion(base));
    s("line", { x1: x(base.hire), x2: x(base.hire), y1: 0, y2: c.h, stroke: "var(--accent)", "stroke-width": 1, "stroke-dasharray": "3 3" }, c.g);
    dot(c, x(base.hire), y(today), "var(--accent)", 5.5);
    s("text", { class: "today-text halo", x: x(base.hire) + 10, y: y(today) + 16 }, c.g,
      mode === "wait" ? `${num(today, 1)} days at ${int(base.hire)} a day` : `${num(today)} million at ${int(base.hire)} a day`);
    const labels = series.map((se) => ({ y: y(se.points[se.points.length - 1][1]), color: se.color, text: se.label }));
    if (narrow) { for (const l of labels) l.y -= 9; endLabels(c, labels, { x: c.w - 2, anchor: "end" }); } else endLabels(c, labels, { x: c.w + 10 });
    const cursor = s("line", { class: "cursor", y1: 0, y2: c.h, visibility: "hidden" }, c.g);
    hover(c, {
      count: hires.length, start: Math.round(base.hire / 5000),
      toIndex: (px) => Math.round(x.invert(px) / 5000),
      leave: () => cursor.setAttribute("visibility", "hidden"),
      move: (i) => {
        cursor.setAttribute("x1", x(hires[i])); cursor.setAttribute("x2", x(hires[i])); cursor.setAttribute("visibility", "visible");
        showTip(c, x(hires[i]), y(series[0].points[i][1]), `${int(hires[i])} USD a day`,
          series.map((se) => ({ label: se.label, value: num(se.points[i][1], mode === "wait" ? 1 : 2) + (mode === "wait" ? " days" : " M USD") })));
      },
    });
  }

  function update() {
    const mode = ctx.params.y === "wait" ? "wait" : "premium";
    const q = canalQuestion(base);
    const pan = res.routes.panama;
    const cape = res.routes.cape;
    const saved = cape.round_trip_days - pan.round_trip_days;
    put(head, "Through Panama the round trip is ", b(`${num(saved, 0)} days`), " shorter than round the Cape. At ", b(int(base.hire)), " USD a day a ship can pay ", b(`${musd(q.premium_usd)} million USD`),
      " above the tariff for its two transits, or wait ", b(`${num(q.wait_days, 1)} days`), " at each, before the Cape is the cheaper way east.");
    const pm = D.routes.panama_monthly[D.routes.panama_monthly.length - 1];
    const status = (id) => P.route_status[id].status;
    put(dek, status("panama") === status("suez") ? `This week Panama and Suez are both ${status("panama")}. ` : `This week Panama is ${status("panama")} and Suez is ${status("suez")}. `,
      `A day of waiting costs ${int(q.cost_of_a_waiting_day_usd / 2)} USD in hire, boil-off and financing; in ${month(pm.month)} ships spent ${num(pm.cwt_hours_avg, 0)} hours in canal waters on average.`);
    put(mapTitle, `Round the Cape a cargo sails ${int(map_distance("cape") - map_distance("panama"))} nautical miles further each way than through Panama`);
    put(mapSource, `Distances: this study, over Eurostat's SeaRoute network. Days: round trips at 17 knots with a day in each port and at each canal. Tolls and fees for the round trip: tariffs in force on ${day(P.date)}. Japan is drawn at both edges so that every route runs unbroken.`);
    put(controls, segmented("Show", [["premium", "Slot premium"], ["wait", "Waiting days"]], mode, (v) => ctx.set({ y: v === "premium" ? null : v })));
    put(figTitle, mode === "wait"
      ? "The dearer the ship and the gas, the longer a cargo can wait for the canal before the Cape is cheaper"
      : "A pair of Panama slots is worth more the dearer the ship and the gas");
    put(source, "Each line: the premium, or the wait, at which a cargo nets the same through Panama as round the Cape; below zero the Cape is already cheaper. The tariff already counts tolls, the fresh water surcharge and booking fees of ",
      int(P.panama.laden + P.panama.ballast), ` USD for the round trip. Model: this study, prices to ${day(P.date)}.`);
    drawCanal(mode);
    ctx.map().then(drawMap);

    const ids = ["europe", ...EAST];
    const row = (label, f) => ({ label, ...Object.fromEntries(ids.map((id) => [id, f(id, res.routes[id])])) });
    put(factsBody, table([{ label: "", value: (r) => r.label, head: true },
      ...ids.map((id) => ({ label: id === "europe" ? "To Gate" : ROUTES[id].via, n: true, value: (r) => r[id] }))], [
      row("Distance one way, nautical miles", (id) => int(map_distance(id))),
      row("Days at sea one way", (id, r) => num(r.sea_days, 1)),
      row("Round trip, days", (id, r) => num(r.round_trip_days, 1)),
      row("Tolls and fees laden, USD", (id) => int(base.routes[id].toll_laden)),
      row("Tolls and fees in ballast, USD", (id) => int(base.routes[id].toll_ballast)),
      row("Port costs, USD", (id) => int(base.routes[id].port_cost)),
      row("Cargo delivered, percent of loaded", (id, r) => num((r.delivered / r.loaded) * 100, 1)),
      row("Status this week", (id) => (id === "europe" ? "open" : P.route_status[id].status)),
    ], { min: 640 }), h("p", { class: "source" }, `Panama for the ${P.ships[P.ship_id].name}: toll ${int(P.panama.toll_laden)} USD laden and ${int(P.panama.toll_ballast)} in ballast, fresh water surcharge ${int(P.panama.fresh_water_laden)} and ${int(P.panama.fresh_water_ballast)}, booking fee ${int(P.panama.booking_fee)} each way. Suez: ${int(P.suez.scnt)} tons of Suez Canal net tonnage, ${num(P.suez.surcharge * 100, 0)} percent surcharge, ${num(P.suez.rebate * 100, 0)} percent rebate.`));
  }

  return { update };
}

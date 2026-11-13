// One cargo: netbacks at Sabine Pass by destination and route, and the bridge from Europe's to Asia's.

import { priceCargo, usdMmbtuToEurMwh } from "../engine.js";
import { h, b, put, num, int, signed, day, month, ROUTES, EAST, panel, table, segmented } from "../util.js";
import { frame, axisX, s, showTip, d3 } from "../chart.js";
import { inputsTable, methodLink } from "./shared.js";

// [group, path, label, scale shown, step]
const FIELDS = [
  ["Prices", "jkm", "JKM, USD/MMBtu", 1, 0.01],
  ["Prices", "ttf", "TTF, USD/MMBtu", 1, 0.01],
  ["Prices", "des_discount", "Europe's DES discount, USD/MMBtu", 1, 0.01],
  ["Prices", "henry_hub", "Henry Hub, USD/MMBtu", 1, 0.01],
  ["Prices", "hire", "Charter rate, USD a day", 1, 250],
  ["Ship", "ship.capacity_m3", "Capacity, m3", 1, 1000],
  ["Ship", "ship.fill", "Fill, percent of capacity", 100, 0.1],
  ["Ship", "ship.boil_off", "Boil-off, percent a day", 100, 0.001],
  ["Ship", "ship.speed_kn", "Speed, knots", 1, 0.1],
  ["Ship", "ship.mmbtu_per_m3", "MMBtu per m3 of LNG", 1, 0.1],
  ["Ship", "port_days.load", "Days to load", 1, 0.5],
  ["Ship", "port_days.discharge", "Days to discharge", 1, 0.5],
  ["Carbon, financing and contract", "eua_eur", "EU allowance, EUR a tonne", 1, 0.5],
  ["Carbon, financing and contract", "fx", "Dollars per euro", 1, 0.0001],
  ["Carbon, financing and contract", "carbon.phase_in", "Emissions surrendered, percent", 100, 1],
  ["Carbon, financing and contract", "carbon.tco2e_per_t_lng", "Tonnes CO2e per tonne of LNG burnt", 1, 0.01],
  ["Carbon, financing and contract", "finance.rate", "SOFR, percent", 100, 0.01],
  ["Carbon, financing and contract", "finance.spread", "Margin over SOFR, basis points", 10000, 5],
  ["Carbon, financing and contract", "contract.hh_multiple", "Gas lifted, percent of Henry Hub", 100, 1],
  ["Carbon, financing and contract", "contract.fee", "Fixed liquefaction fee, USD/MMBtu", 1, 0.05],
];
const ROUTE_FIELDS = [
  ["distance_nm", "Distance, nm", 10], ["canal_days", "Canal days, each way", 0.5], ["wait_days", "Waiting days, each way", 0.5],
  ["toll_laden", "Tolls and fees laden, USD", 1000], ["toll_ballast", "Tolls and fees in ballast, USD", 1000], ["port_cost", "Port costs, USD", 1000],
];

const getPath = (obj, path) => path.split(".").reduce((o, k) => o[k], obj);
function setPath(obj, path, value) {
  const keys = path.split(".");
  const last = keys.pop();
  keys.reduce((o, k) => o[k], obj)[last] = value;
}
const parseEdits = (text) => Object.fromEntries((text || "").split(";").filter(Boolean).map((kv) => kv.split(":")));
const writeEdits = (edits) => Object.entries(edits).map(([k, v]) => `${k}:${v}`).join(";") || null;

export function mount(root, ctx) {
  const D = ctx.D;
  const presets = Object.fromEntries(D.presets.map((p) => [p.id, p]));

  const kicker = h("p", { class: "kicker" });
  const head = h("h1");
  const controls = h("div", { class: "controls" });
  const note = h("p", { class: "dek" });
  const tiles = h("div", { class: "tiles" });
  const figTitle = h("p", { class: "fig-title" });
  const plot = h("div");
  const source = h("p", { class: "source" });
  const strip = h("p", { class: "strip" });
  const costBody = h("div");
  const formBody = h("div");
  const inputsBody = h("div");
  const formPanel = panel("Edit the inputs", formBody);
  root.append(kicker, head, controls, note, tiles, h("figure", null, figTitle, plot, source), strip,
    h("div", { class: "more" }, formPanel, panel("Cost lines by route", costBody), panel("Inputs and their dates", inputsBody)));

  function current() {
    const P = presets[ctx.params.preset] || D.presets[0];
    const edits = parseEdits(ctx.params.set);
    const inputs = JSON.parse(JSON.stringify(P.inputs));
    const extra = { fx: P.usd_per_eur, eua_eur: P.eua_eur_t, ship: P.ship_id };
    if (edits.ship && P.ships[edits.ship]) {
      const alt = P.ships[edits.ship];
      extra.ship = edits.ship;
      inputs.ship = { ...alt.ship };
      for (const canal of ["panama", "suez"]) [inputs.routes[canal].toll_laden, inputs.routes[canal].toll_ballast] = alt.tolls[canal];
      inputs.carbon.tco2e_per_t_lng = alt.tco2e_per_t_lng;
    }
    for (const [path, raw] of Object.entries(edits)) {
      const value = Number(raw);
      if (path === "ship" || Number.isNaN(value)) continue;
      if (path === "fx" || path === "eua_eur") extra[path] = value;
      else if (path.endsWith(".open")) setPath(inputs, path, value === 1);
      else setPath(inputs, path, value);
    }
    if ("fx" in edits || "eua_eur" in edits) inputs.carbon.eua_usd_t = extra.eua_eur * extra.fx;
    return { P, edits, inputs, extra };
  }

  // An edit recomputes the page after the browser has moved the focus, then puts the focus back.
  function edit(path, value, P) {
    setTimeout(() => {
      const edits = parseEdits(ctx.params.set);
      if (value == null) delete edits[path];
      else edits[path] = value;
      const focused = document.activeElement && document.activeElement.dataset ? document.activeElement.dataset.path : null;
      ctx.set({ set: writeEdits(edits), preset: P.id === D.presets[0].id ? null : P.id });
      const again = focused ? formBody.querySelector(`[data-path="${focused}"]`) : null;
      if (again) again.focus();
    }, 0);
  }

  // -- the bridge from Europe's netback to Asia's -------------------------------------
  function bridge(res, id) {
    const r = res.routes[id];
    const k = r.delivered / r.loaded;
    return [
      ["JKM over TTF", res.spread * k],
      ["Europe's DES discount, not paid", -r.drivers.des_discount * k],
      ["Extra boil-off", -r.drivers.boil_off * k],
      ["Extra hire", -r.drivers.hire * k],
      ["Canal tolls and fees", -r.drivers.tolls * k],
      ["Ports, carbon and financing", -r.drivers.other * k],
    ];
  }

  function draw(res, id) {
    const steps = bridge(res, id);
    const start = res.routes.europe.netback;
    const end = res.routes[id].netback;
    const narrow = (plot.clientWidth || 800) < 620;
    const rows = [["Netback at Gate", null], ...steps, [`Netback ${ROUTES[id].via}`, null]];
    const rowH = narrow ? 46 : 40;
    const c = frame(plot, {
      height: rows.length * rowH + 58, margin: { top: 8, right: 64, bottom: 50, left: narrow ? 8 : 236 },
      label: `Bridge from the netback at Gate, ${num(start)}, to the netback ${ROUTES[id].via}, ${num(end)} USD per MMBtu`,
    });
    let running = start;
    const marks = [start];
    for (const [, v] of steps) { running += v; marks.push(running); }
    const lo = Math.min(...marks, end);
    const hi = Math.max(...marks, end);
    const pad = Math.max(0.15, (hi - lo) * 0.12);
    const x = d3.scaleLinear([lo - pad, hi + pad], [0, c.w]).nice();
    axisX(c, x, { values: x.ticks(narrow ? 4 : 8), format: (v) => num(v, 2), label: narrow ? "USD/MMBtu loaded; the axis does not start at zero" : "USD per MMBtu loaded at Sabine Pass (the axis does not start at zero)" });
    for (const v of x.ticks(narrow ? 4 : 8)) s("line", { class: "grid", x1: x(v), x2: x(v), y1: 0, y2: c.h }, c.g);

    running = start;
    rows.forEach(([label, delta], i) => {
      const y = i * rowH + rowH / 2 + (narrow ? 8 : 0);
      if (narrow) s("text", { class: "label", x: 0, y: y - 15 }, c.g, label);
      else s("text", { class: i === 0 || delta === null ? "label" : "", x: -14, y: y + 4, "text-anchor": "end" }, c.g, label);
      const hit = s("rect", { x: -c.margin.left, y: y - rowH / 2, width: c.W, height: rowH, fill: "transparent" }, c.g);
      if (delta === null) {
        const value = i === 0 ? start : end;
        const color = i === 0 ? ROUTES.europe.color : ROUTES[id].color;
        s("line", { x1: x(value), x2: x(value), y1: y - 12, y2: y + 12, stroke: color, "stroke-width": 3 }, c.g);
        s("circle", { cx: x(value), cy: y, r: 6, fill: color, stroke: "var(--paper)", "stroke-width": 2 }, c.g);
        s("text", { class: "label mono", x: x(value) + 12, y: y + 4 }, c.g, num(value));
        hit.addEventListener("pointermove", () => showTip(c, x(value), y, label, [{ label: "USD/MMBtu loaded", value: num(value, 3) }]));
      } else {
        const from = running;
        running += delta;
        const to = running;
        const x0 = x(Math.min(from, to));
        const width = Math.max(1.5, Math.abs(x(to) - x(from)));
        s("rect", { x: x0, y: y - 7, width, height: 14, rx: 3, fill: delta >= 0 ? ROUTES[id].color : "var(--loss)" }, c.g);
        s("line", { class: "zero", x1: x(to), x2: x(to), y1: y + 7, y2: y + rowH - 7, "stroke-dasharray": "2 2" }, c.g);
        s("text", { class: "mono", x: x(Math.max(from, to)) + 8, y: y + 4, fill: "var(--ink)" }, c.g, signed(delta));
        hit.addEventListener("pointermove", () => showTip(c, x(Math.max(from, to)), y, label,
          [{ label: "Change", value: signed(delta, 3) }, { label: "Running netback", value: num(to, 3) }]));
      }
      hit.addEventListener("pointerleave", () => { c.tip.hidden = true; });
    });
    if (Math.abs(running - end) > 1e-9) console.error("the bridge does not close", running, end);
    return steps;
  }

  // -- the inputs form --------------------------------------------------------------------
  function form(P, edits, inputs, extra) {
    const field = (path, label, scale, step, value) => {
      const input = h("input", { type: "number", step, "data-path": path, value: Number((value * scale).toPrecision(10)), class: path in edits ? "edited" : null,
        onchange: () => { if (input.value !== "" && !Number.isNaN(Number(input.value))) edit(path, Number(input.value) / scale, P); } });
      const hint = path === "ttf" ? h("span", { class: "hint" }, `${num(usdMmbtuToEurMwh(inputs.ttf, extra.fx))} EUR/MWh`) : null;
      return h("label", null, label, input, hint);
    };
    const groups = [];
    let last = null;
    for (const [group, path, label, scale, step] of FIELDS) {
      if (group !== last) {
        groups.push(h("h3", null, group));
        if (group === "Ship") {
          const select = h("select", { "aria-label": "Ship", "data-path": "ship", onchange: () => edit("ship", select.value === P.ship_id ? null : select.value, P) },
            Object.entries(P.ships).map(([id, sh]) => h("option", { value: id, selected: id === extra.ship }, sh.name)));
          groups.push(h("label", null, "Ship", select, h("span", { class: "hint" }, "Changes capacity, boil-off, tolls and carbon")));
        }
        last = group;
      }
      const value = path === "fx" ? extra.fx : path === "eua_eur" ? extra.eua_eur : getPath(inputs, path);
      groups.push(field(path, label, scale, step, value));
    }
    const routeRows = ["europe", ...EAST].map((id) => h("tr", null,
      h("th", { scope: "row" }, h("span", { class: "swatch " + ROUTES[id].cls }), id === "europe" ? "Gate" : ROUTES[id].via,
        id === "europe" ? null : h("label", { style: "display:block;font-weight:400" },
          h("input", { type: "checkbox", "data-path": `routes.${id}.open`, checked: inputs.routes[id].open,
            onchange: (e) => edit(`routes.${id}.open`, e.target.checked === P.inputs.routes[id].open ? null : (e.target.checked ? 1 : 0), P) }), "open")),
      ROUTE_FIELDS.map(([key, label, step]) => {
        const path = `routes.${id}.${key}`;
        const input = h("input", { type: "number", step, "data-path": path, value: Number(inputs.routes[id][key].toPrecision(10)), "aria-label": `${label}, ${ROUTES[id].via}`,
          class: path in edits ? "edited" : null, style: "min-width:92px",
          onchange: () => { if (input.value !== "") edit(path, Number(input.value), P); } });
        return h("td", null, input);
      })));
    const routesTable = h("div", { class: "scroll" }, h("table", null,
      h("thead", null, h("tr", null, h("th", { scope: "col" }, "Route"), ROUTE_FIELDS.map(([, label]) => h("th", { scope: "col" }, label)))),
      h("tbody", null, routeRows)));
    put(formBody,
      h("p", { class: "source" }, "Type over any figure. An edited field is outlined, the page recomputes at once and the address keeps your inputs. ",
        Object.keys(edits).length ? h("button", { type: "button", class: "btn quiet", onclick: () => ctx.set({ set: null }) }, "Put the preset's figures back") : null),
      h("div", { class: "form" }, groups), h("h3", { style: "margin-top:16px" }, "Routes"), routesTable);
  }

  function costs(res) {
    const ids = ["europe", ...EAST];
    const line = (label, f, digits = 0) => ({ label, ...Object.fromEntries(ids.map((id) => [id, num(f(res.routes[id]), digits)])) });
    const rows = [
      line("Round trip, days", (r) => r.round_trip_days, 1),
      line("Loaded, MMBtu", (r) => r.loaded),
      line("Boil-off, MMBtu", (r) => r.boil_off),
      line("Delivered, MMBtu", (r) => r.delivered),
      line("DES price, USD/MMBtu", (r) => r.price, 2),
      line("Revenue, USD", (r) => r.price * r.delivered),
      line("Hire, USD", (r) => r.cost.hire),
      line("Ports, USD", (r) => r.cost.ports),
      line("Canal tolls and fees, USD", (r) => r.cost.tolls),
      line("EU ETS, USD", (r) => r.cost.carbon),
      line("Financing, USD", (r) => r.cost.financing),
      line("Voyage cost, USD", (r) => r.cost.total),
      line("Voyage cost, USD per MMBtu delivered", (r) => r.cost.total / r.delivered, 3),
      line("Netback, USD per MMBtu loaded", (r) => r.netback, 3),
    ];
    return table([{ label: "", value: (r) => r.label, head: true },
      ...ids.map((id) => ({ label: id === "europe" ? "Gate" : ROUTES[id].via + (res.routes[id].open ? "" : " (closed)"), n: true, value: (r) => r[id] }))], rows);
  }

  function update() {
    const { P, edits, inputs, extra } = current();
    const res = priceCargo(inputs);
    const edited = Object.keys(edits).length > 0;
    const chosen = EAST.includes(ctx.params.route) ? ctx.params.route : (res.best_east || "cape");
    const when = P.period === "month" ? month(P.date) : `the week to ${day(P.date)}`;
    put(kicker, `One cargo from Sabine Pass, ${when}`, edited ? h("span", { class: "flag" }, " · your inputs") : null);

    const east = EAST.filter((id) => res.routes[id].open);
    const bestEast = res.best_east;
    const sentence = ["A cargo nets ", b(num(res.routes.europe.netback)), " USD/MMBtu at Gate"];
    east.forEach((id, i) => sentence.push(i === east.length - 1 ? " and " : ", ", b(num(res.routes[id].netback)), " ", ROUTES[id].via));
    sentence.push(". ");
    if (bestEast) {
      const arb = res.routes[bestEast].arb;
      const name = ROUTES[bestEast].name.replace(/^t/, "T");
      sentence.push(arb >= 0 ? [name, " beats Gate by ", b(num(arb)), "."] : ["Gate beats ", ROUTES[bestEast].name, " by ", b(num(-arb)), "."]);
    }
    put(head, sentence);

    put(controls, segmented("Loading date", D.presets.map((p) => [p.id, p.label]), P.id,
      (id) => ctx.set({ preset: id === D.presets[0].id ? null : id, set: null, route: null })),
      h("button", { type: "button", class: "btn", onclick: () => { formPanel.open = true; formPanel.scrollIntoView({ behavior: "smooth", block: "start" }); } }, "Edit the inputs"));
    put(note, P.note, " JKM ", num(inputs.jkm), ", TTF ", num(inputs.ttf), " (", num(usdMmbtuToEurMwh(inputs.ttf, extra.fx)), " EUR/MWh), Henry Hub ",
      num(inputs.henry_hub), ", ", int(inputs.hire), " USD a day.");

    put(tiles, ["europe", ...EAST].map((id) => {
      const r = res.routes[id];
      const flags = [id === res.best ? "best" : null, r.open ? null : "closed"].filter(Boolean).join(", ");
      return h("button", { type: "button", class: `tile ${ROUTES[id].cls}${r.open ? "" : " shut"}`, disabled: id === "europe", "data-focus": `tile-${id}`,
        "aria-pressed": id === "europe" ? null : String(id === chosen), onclick: () => ctx.set({ route: id }) },
        h("span", { class: "name" }, id === "europe" ? "Gate, Europe" : `Futtsu ${ROUTES[id].via}`, flags ? ` (${flags})` : ""),
        h("span", { class: "value" }, num(r.netback)),
        h("span", { class: "meta" }, `${num(r.round_trip_days, 1)} days, ${num((r.delivered / r.loaded) * 100, 1)} percent delivered`));
    }));

    const steps = draw(res, chosen);
    const gain = steps.reduce((a, c) => (c[1] > a[1] ? c : a));
    const loss = steps.reduce((a, c) => (c[1] < a[1] ? c : a));
    const arb = res.routes[chosen].arb;
    const lower = (text) => text.replace("JKM over TTF", "the spread").replace("Europe's DES discount, not paid", "Europe's discount").toLowerCase().replace("europe", "Europe");
    put(figTitle, `${ROUTES[chosen].via.replace(/^v/, "V")} the cargo keeps ${num(Math.abs(arb))} ${arb >= 0 ? "more" : "less"} than at Gate: `,
      `${lower(gain[0])} adds ${num(gain[1])}, ${lower(loss[0])} takes ${num(-loss[1])}`);
    put(source, "Coloured bars add to the netback, grey bars take from it, in USD per MMBtu loaded. Choose a tile to bridge to another route. ",
      `Prices: EIA${P.period === "month" ? ", " + P.basis : ""}. Charter rate: ${P.sources.hire.status === "assumed" ? "assumed, " + P.sources.hire.note : "Spark30S Atlantic of " + day(String(P.sources.hire.date))}. `,
      `DES discount: ${P.sources.des_discount.status === "assumed" ? "assumed, " + P.sources.des_discount.note : "ACER"}.`);

    const lift = res.lift;
    put(strip, b("Lift test. "), `The best netback, ${num(lift.best_netback)} ${res.best === "europe" ? "at Gate" : ROUTES[res.best].via}, is ${num(Math.abs(lift.margin))} `,
      lift.lifts ? "above" : "below", ` 115 percent of Henry Hub (${num(lift.threshold)}): the cargo is ${lift.lifts ? "lifted" : "cancelled"}. `,
      `After the fixed fee of ${num(inputs.contract.fee)}, owed either way, ${num(lift.margin_after_fee)}.`);

    put(costBody, costs(res));
    form(P, edits, inputs, extra);
    put(inputsBody, inputsTable(P, inputs), methodLink());
    if (edited && !formPanel.dataset.seen) { formPanel.open = true; formPanel.dataset.seen = "1"; }
  }

  return { update };
}

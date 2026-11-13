// Reroute levels: the JKM minus TTF spread a cargo needs to go east, against the charter rate.

import { priceCargo, breakevenLine, usdMmbtuToEurMwh } from "../engine.js";
import { h, b, put, num, int, day, ROUTES, EAST, panel, table } from "../util.js";
import { frame, axisX, axisY, path, dot, endLabels, showTip, hover, s, d3 } from "../chart.js";
import { inputsTable, driversTable, methodLink } from "./shared.js";

const X_MAX = 200000;

export function mount(root, ctx) {
  const P = ctx.D.now.preset;
  const base = P.inputs;
  const spread = base.jkm - base.ttf;
  const fx = P.usd_per_eur;
  const defaults = { ttf: base.ttf, des: base.des_discount, wait: 0 };
  const defaultOpen = EAST.filter((id) => base.routes[id].open).join(",");

  const state = () => {
    const p = ctx.params;
    const open = (p.routes ?? defaultOpen).split(",").filter(Boolean);
    const f = (key) => (p[key] != null && !Number.isNaN(Number(p[key])) ? Number(p[key]) : defaults[key]);
    return { ttf: f("ttf"), des: f("des"), wait: f("wait"), open };
  };
  const modified = (st) => st.ttf !== defaults.ttf || st.des !== defaults.des || st.wait !== 0 || st.open.join(",") !== defaultOpen;

  function inputsFor(st) {
    const routes = {};
    for (const [id, r] of Object.entries(base.routes)) {
      routes[id] = { ...r, open: id === "europe" || st.open.includes(id), wait_days: id === "panama" ? st.wait : 0 };
    }
    return { ...base, ttf: st.ttf, jkm: st.ttf + spread, des_discount: st.des, routes };
  }

  // -- skeleton ---------------------------------------------------------------
  const kicker = h("p", { class: "kicker" });
  const head = h("h1");
  const dek = h("p", { class: "dek" });
  const plot = h("div");
  const figTitle = h("p", { class: "fig-title" }, "The longer the route, the faster its reroute level rises with the charter rate");
  const source = h("p", { class: "source" });
  const tableBox = h("div", { class: "box" });
  const details = h("div", { class: "more" });

  const slider = (key, label, min, max, step, show) => {
    const out = h("output");
    const also = h("div", { class: "also" });
    const input = h("input", { type: "range", min, max, step, "aria-label": label,
      oninput: () => ctx.set({ [key]: Number(input.value) === defaults[key] ? null : input.value }) });
    const el = h("div", { class: "slider" }, h("label", null, h("span", null, label), out), also, input);
    el.sync = (v) => { input.value = v; const [a, c] = show(v); out.textContent = a; also.textContent = c; };
    return el;
  };
  const sTtf = slider("ttf", "Gas price, TTF", 2, 60, 0.01, (v) => [`${num(v)} USD/MMBtu`, `${num(usdMmbtuToEurMwh(v, fx))} EUR/MWh`]);
  const sDes = slider("des", "Europe's DES discount to TTF", -6, 1, 0.01, (v) => [`${num(v)} USD/MMBtu`, `${num(usdMmbtuToEurMwh(v, fx))} EUR/MWh`]);
  const sWait = slider("wait", "Wait at Panama, each transit", 0, 20, 0.5, (v) => [`${num(v, 1)} days`, "0 with a booked slot"]);
  const reset = h("button", { type: "button", class: "btn quiet", onclick: () => ctx.set({ ttf: null, des: null, wait: null, routes: null }) }, "Reset to this week");

  const whyBody = h("div");
  const inputsBody = h("div");
  details.append(
    panel("What the levels are made of", whyBody),
    panel("Inputs and their dates", inputsBody),
    panel("Route status", table([
      { label: "Route", value: (r) => ROUTES[r].name.replace("the ", ""), head: true },
      { label: "Status", value: (r) => P.route_status[r].status },
      { label: "Why", value: (r) => P.route_status[r].note },
      { label: "Source", value: (r) => (P.route_status[r].url ? h("a", { href: P.route_status[r].url, rel: "noopener" }, P.route_status[r].source) : P.route_status[r].source) },
    ], EAST)));

  root.append(kicker, head, dek,
    h("div", { class: "split" },
      h("figure", null, figTitle, plot, source),
      h("aside", { class: "side", "aria-label": "Controls and table" }, h("div", { class: "box" }, sTtf, sDes, sWait, reset), tableBox)),
    details);

  // -- words ---------------------------------------------------------------------
  function words(st, res) {
    const open = EAST.filter((id) => res.routes[id].open);
    const clears = open.filter((id) => res.spread > res.routes[id].breakeven_spread);
    const list = (items) => items.flatMap((x, i) => (i === 0 ? [x] : [i === items.length - 1 ? " and " : ", ", x]));
    const out = ["JKM is ", b(num(Math.abs(res.spread))), res.spread >= 0 ? " above TTF. " : " below TTF. "];
    if (!open.length) return [...out, "No route east is switched on."];
    out.push("At ", b(int(base.hire)), " USD a day a cargo pays to go east above ",
      list(open.map((id) => [b(num(res.routes[id].breakeven_spread)), " ", ROUTES[id].via])), ", so the arb is ");
    if (clears.length === open.length) out.push(open.length === 1 ? "open." : open.length === 2 ? "open on both routes." : "open on all three routes.");
    else if (!clears.length) out.push(open.length === 1 ? "closed." : "closed on " + (open.length === 2 ? "both" : "all three") + " routes.");
    else out.push("open ", list(clears.map((id) => ROUTES[id].via)), " only.");
    return out;
  }

  // -- chart ------------------------------------------------------------------------
  function draw(st, res, lines) {
    const narrow = (plot.clientWidth || 800) < 560;
    const c = frame(plot, {
      height: narrow ? 340 : Math.max(380, Math.min(480, window.innerHeight - 380)),
      margin: { top: 28, right: narrow ? 10 : 132, bottom: 46, left: 44 },
      label: "Reroute level by route against the charter rate, with this week's spread and charter rate marked",
    });
    const values = [res.spread, 0];
    for (const id of EAST) if (st.open.includes(id) || id !== "suez") values.push(lines[id][0], lines[id][0] + lines[id][1] * X_MAX);
    const lo = Math.floor((Math.min(...values) - 0.25) * 2) / 2;
    const hi = Math.ceil((Math.max(...values) + 0.25) * 2) / 2;
    const x = d3.scaleLinear([0, X_MAX], [0, c.w]);
    const y = d3.scaleLinear([lo, hi], [c.h, 0]);
    axisY(c, y, { values: d3.ticks(lo, hi, 7), format: (v) => num(v, 1), label: "Reroute level, JKM minus TTF, USD/MMBtu" });
    axisX(c, x, { values: narrow ? [0, 100000, 200000] : [0, 50000, 100000, 150000, 200000], format: int, label: "Charter rate, USD a day" });

    const labels = [];
    for (const id of EAST) {
      const [a, slope] = lines[id];
      const isOpen = res.routes[id].open;
      path(c, [[x(0), y(a)], [x(X_MAX), y(a + slope * X_MAX)]],
        { stroke: ROUTES[id].color, "stroke-dasharray": isOpen ? null : "2 5", opacity: isOpen ? 1 : 0.8 });
      labels.push({ y: y(a + slope * X_MAX), color: ROUTES[id].color, text: ROUTES[id].via, sub: isOpen ? null : "closed" });
      const hStar = res.routes[id].breakeven_hire;
      if (isOpen && hStar > 0 && hStar < X_MAX) {
        s("circle", { cx: x(hStar), cy: y(res.spread), r: 4.5, fill: "var(--paper)", stroke: ROUTES[id].color, "stroke-width": 2 }, c.g);
      }
    }
    // today: the spread, the charter rate and the point where they meet
    const ty = y(res.spread);
    const tx = x(base.hire);
    s("line", { x1: 0, x2: c.w, y1: ty, y2: ty, stroke: "var(--accent)", "stroke-width": 1.5 }, c.g);
    s("line", { x1: tx, x2: tx, y1: 0, y2: c.h, stroke: "var(--accent)", "stroke-width": 1, "stroke-dasharray": "3 3" }, c.g);
    dot(c, tx, ty, "var(--accent)", 5.5);
    s("text", { class: "today-text halo", x: narrow ? tx + 8 : c.w - 4, y: ty - 7, "text-anchor": narrow ? "start" : "end" }, c.g, `JKM minus TTF this week, ${num(res.spread)}`);
    s("text", { class: "today-text halo", x: tx + 6, y: 10 }, c.g, `${int(base.hire)} a day`);
    if (narrow) {
      for (const l of labels) l.y += l.y > ty ? 13 : -9;
      endLabels(c, labels, { x: c.w - 2, anchor: "end" });
    } else endLabels(c, labels, { x: c.w + 10 });

    const cursor = s("line", { class: "cursor", y1: 0, y2: c.h, visibility: "hidden" }, c.g);
    const STEP = 500;
    hover(c, {
      count: X_MAX / STEP + 1,
      start: Math.round(base.hire / STEP),
      toIndex: (px) => Math.round(x.invert(px) / STEP),
      leave: () => cursor.setAttribute("visibility", "hidden"),
      move: (i) => {
        const hire = i * STEP;
        cursor.setAttribute("x1", x(hire)); cursor.setAttribute("x2", x(hire)); cursor.setAttribute("visibility", "visible");
        showTip(c, x(hire), ty, `${int(hire)} USD a day`,
          EAST.map((id) => ({ key: ROUTES[id].cls + (res.routes[id].open ? "" : " dash"), label: `Level ${ROUTES[id].via}`, value: num(lines[id][0] + lines[id][1] * hire) })),
          `This week JKM minus TTF is ${num(res.spread)}.`);
      },
    });
  }

  // -- table --------------------------------------------------------------------------
  function fill(st, res, lines) {
    const sc = P.scenarios;
    const cols = [["Sunk", 0], ["Low", sc.low], ["Central", sc.central], ["High", sc.high]];
    const cell = (id, hire) => {
      const level = lines[id][0] + lines[id][1] * hire;
      return h("td", { class: "n " + (res.routes[id].open && res.spread > level ? "yes" : "no") }, num(level));
    };
    const toggle = (id) => h("input", { type: "checkbox", checked: st.open.includes(id), "aria-label": `Route ${ROUTES[id].via} open`, "data-focus": `open-${id}`,
      onchange: (e) => {
        const next = EAST.filter((r) => (r === id ? e.target.checked : st.open.includes(r))).join(",");
        ctx.set({ routes: next === defaultOpen ? null : next });
      } });
    const t = h("table", null,
      h("caption", null, "Reroute level by charter rate in USD a day. Sunk: the ship is already paid for. Untick a route to close it."),
      h("thead", null, h("tr", null, h("th", { scope: "col" }, "Route east"),
        cols.map(([name, v]) => h("th", { class: "n", scope: "col" }, name, h("br"), int(v))),
        h("th", { class: "n", scope: "col" }, "Closes", h("br"), "above"))),
      h("tbody", null, EAST.map((id) => h("tr", null,
        h("th", { scope: "row" }, h("label", null, toggle(id), h("span", { class: "swatch " + ROUTES[id].cls }), ROUTES[id].name.replace("the ", ""))),
        cols.map(([, v]) => cell(id, v)),
        h("td", { class: "n" }, int(res.routes[id].breakeven_hire))))));
    tableBox.replaceChildren(h("div", { class: "scroll" }, t),
      h("p", { class: "note" }, `Bold: this week's spread of ${num(res.spread)} clears the level. Low, central and high are the quartiles of the rates reported for the ship since 2024. Closes above: the charter rate at which the route stops paying.`));
  }

  // -- update --------------------------------------------------------------------------
  function update() {
    const st = state();
    const inputs = inputsFor(st);
    const res = priceCargo(inputs);
    const lines = Object.fromEntries(EAST.map((id) => [id, breakevenLine(inputs, id)]));
    const hire = P.sources.hire;
    put(kicker, `US Gulf LNG, week to ${day(P.date)}`, modified(st) ? h("span", { class: "flag" }, " · your settings") : null);
    put(head, words(st, res));
    const eur = usdMmbtuToEurMwh(Math.abs(st.des), fx);
    put(dek,
      "Levels are JKM minus TTF in USD/MMBtu for a cargo loaded at Sabine Pass. ",
      st.des < 0
        ? `A cargo delivered to Northwest Europe sells ${num(Math.abs(st.des))} under TTF (${num(eur, 1)} EUR/MWh), which lowers every level by as much.`
        : `A cargo delivered to Northwest Europe sells ${num(st.des)} over TTF.`);
    sTtf.sync(st.ttf); sDes.sync(st.des); sWait.sync(st.wait);
    reset.hidden = !modified(st);
    draw(st, res, lines);
    fill(st, res, lines);
    const held = (src) => (src.status === "held" ? ", held since" : "");
    put(source,
      `Prices: EIA, week to ${day(P.date)}. Charter rate: Spark30S Atlantic as reported on ${day(String(hire.date))}${held(hire)} (`,
      hire.url ? h("a", { href: hire.url, rel: "noopener" }, "LNG Prime") : "LNG Prime",
      `). DES discount: ACER, 20 days to ${day(String(P.sources.des_discount.date))}${held(P.sources.des_discount)}. `,
      "Hollow circle: the charter rate at which a route stops paying.");
    whyBody.replaceChildren(driversTable(res), h("p", { class: "source" },
      "Each line is USD per MMBtu delivered east. Extra boil-off is the gas the longer voyage burns, valued at what Europe pays; it grows with the gas price."));
    inputsBody.replaceChildren(inputsTable(P, inputs), methodLink());
  }

  return { update };
}

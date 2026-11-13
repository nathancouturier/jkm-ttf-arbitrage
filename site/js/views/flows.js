// Flows: did US cargoes follow the arb, and what happened when no market covered the gas.

import { h, b, put, num, int, month, toDate, ROUTES, panel, table } from "../util.js";
import { frame, axisX, axisY, path, s, showTip, hover, dot, d3 } from "../chart.js";

export function mount(root, ctx) {
  const D = ctx.D;
  const F = D.flows;
  const months = F.months.filter((m) => m.month >= "2016-02");
  const lag = F.test.lag;

  const kicker = h("p", { class: "kicker" }, `US LNG by destination, ${month(months[0].month)} to ${month(months[months.length - 1].month)}`);
  const head = h("h1");
  const dek = h("p", { class: "dek" });
  const figTitle = h("p", { class: "fig-title" });
  const plot = h("div");
  const source = h("p", { class: "source" });
  const compare = h("div");
  const limits = h("p", { class: "dek", style: "margin-top:14px" },
    "The comparison cannot separate the arb from term contracts, from China's tariff on US LNG since February 2025, or from ships already on charter, for which the long way costs only fuel. Europe's pull since 2022 moves the spread and the cargoes together.");
  const liftTitle = h("p", { class: "fig-title" });
  const liftPlot = h("div");
  const liftSource = h("p", { class: "source" });
  const liftLead = h("p", { class: "dek" });
  const tableBody = h("div");
  root.append(kicker, head, dek,
    h("div", { class: "cols" }, h("figure", null, figTitle, plot, source), h("div", null, compare, limits)),
    h("h2", null, "When no market covers the gas: 2020"), liftLead, h("figure", null, liftTitle, liftPlot, liftSource),
    h("div", { class: "more" }, panel("The table", tableBody)));

  // the arb of the month before decides the shading of a month's cargoes
  const byMonth = Object.fromEntries(months.map((m) => [m.month, m]));
  const before = (m) => {
    const d = toDate(m.month);
    d.setUTCMonth(d.getUTCMonth() - lag);
    return byMonth[d.toISOString().slice(0, 7)] || null;
  };

  function drawShare() {
    const narrow = (plot.clientWidth || 800) < 600;
    const topH = narrow ? 210 : 270;
    const gap = 54;
    const botH = narrow ? 110 : 130;
    const c = frame(plot, { height: topH + gap + botH + 60, margin: { top: 26, right: narrow ? 14 : 30, bottom: 34, left: 40 },
      label: "Monthly share of US LNG cargoes sent to Japan, South Korea, China and Taiwan, above the arb margin of each month" });
    const rows = months.map((m) => ({ ...m, t: toDate(m.month), prior: before(m) }));
    const x = d3.scaleUtc([rows[0].t, rows[rows.length - 1].t], [0, c.w]);
    const half = c.w / rows.length / 2;
    const y = d3.scaleLinear([0, 0.7], [topH, 0]);
    for (const r of rows) if (r.prior && r.prior.open) s("rect", { x: x(r.t) - half, y: 0, width: half * 2 + 0.6, height: topH, fill: "var(--wash)" }, c.g);
    const top = { ...c, h: topH };
    axisY(top, y, { values: [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7], format: (v) => num(v * 100, 0), label: "Share of US LNG to JKM markets, percent. Shaded: the arb was open the month before" });
    path(c, rows.map((r) => [x(r.t), y(r.share_jkm)]), { stroke: "var(--ink)", "stroke-width": 1.8 });
    const last = rows[rows.length - 1];
    dot(c, x(last.t), y(last.share_jkm), "var(--accent)", 4.5);
    s("text", { class: "today-text halo", x: x(last.t) - 8, y: y(last.share_jkm) - 10, "text-anchor": "end" }, c.g, `${num(last.share_jkm * 100, 0)} percent in ${month(last.month, true)}`);

    const g2 = s("g", { transform: `translate(0,${topH + gap})` }, c.g);
    const bottom = { ...c, g: g2, h: botH };
    const y2 = d3.scaleLinear([-4, 4], [botH, 0]);
    axisY(bottom, y2, { values: [-4, -2, 0, 2, 4], format: (v) => num(v, 0), label: "Arb margin: JKM minus TTF less the reroute level, USD/MMBtu" });
    for (const r of rows) {
      if (r.margin == null) continue;
      const v = Math.max(-4, Math.min(4, r.margin));
      s("rect", { x: x(r.t) - Math.max(1, half - 0.8), width: Math.max(2, half * 2 - 1.6), y: Math.min(y2(0), y2(v)), height: Math.abs(y2(v) - y2(0)), fill: r.margin > 0 ? "var(--gain)" : "var(--loss)" }, g2);
    }
    const years = d3.utcYear.range(d3.utcYear.ceil(rows[0].t), last.t);
    axisX(bottom, x, { values: narrow ? years.filter((_, i) => i % 2 === 0) : years, format: d3.utcFormat("%Y") });
    s("text", { class: "label-sub halo", x: x(toDate("2022-09")), y: botH - 4, "text-anchor": "middle" }, g2, "2022: off the scale");

    const cursor = s("line", { class: "cursor", y1: 0, y2: topH + gap + botH, visibility: "hidden" }, c.g);
    const bisect = d3.bisector((r) => r.t).center;
    hover({ ...c, h: topH + gap + botH }, {
      count: rows.length, toIndex: (px) => bisect(rows, x.invert(px)),
      leave: () => cursor.setAttribute("visibility", "hidden"),
      move: (i) => {
        const r = rows[i];
        cursor.setAttribute("x1", x(r.t)); cursor.setAttribute("x2", x(r.t)); cursor.setAttribute("visibility", "visible");
        showTip(c, x(r.t), y(r.share_jkm), month(r.month), [
          { key: "c-ink", label: "To JKM markets", value: num(r.share_jkm * 100, 1) + " percent" },
          { label: "To Europe", value: num(r.share_europe * 100, 1) + " percent" },
          { label: "Cargoes that left", value: int(r.cargoes) },
          r.margin == null ? null : { label: "Arb margin this month", value: num(r.margin) },
          r.prior && r.prior.margin != null ? { label: "Arb margin the month before", value: num(r.prior.margin) } : null,
        ], r.prior && r.prior.open != null ? `The month before, the arb was ${r.prior.open ? "open" : "closed"}.` : "No price for the month before.");
      },
    });
  }

  function bars() {
    const row = (label, side) => h("div", { style: "display:grid;grid-template-columns:140px 1fr;gap:10px;align-items:center;margin:5px 0" },
      h("span", { style: "font-size:13.5px;color:var(--muted)" }, label),
      h("span", { style: "display:flex;align-items:center;gap:8px" },
        h("span", { style: `display:inline-block;height:14px;border-radius:0 3px 3px 0;background:var(--ink);opacity:${label.includes("open") ? 1 : 0.42};width:${side.mean_share * 320}px;max-width:60%` }),
        h("span", { class: "mono", style: "font-size:13.5px;font-weight:600" }, num(side.mean_share * 100, 0) + " percent"),
        h("span", { style: "font-size:12.5px;color:var(--faint)" }, `${side.months} months`)));
    const block = (title, t) => h("div", { class: "compare" }, h("h3", null, title), row("After an open month", t.open), row("After a closed month", t.closed));
    put(compare, h("p", { class: "fig-title" }, "Share of US LNG sent to JKM markets"),
      block(`All months, ${month(months[0].month, true)} to ${month(months[months.length - 1].month, true)}`, F.test),
      block("Since January 2022", F.since_2022),
      h("p", { class: "source" }, `Mean share of the volume that left the month after. Correlation of the share with the arb margin: ${num(F.test.correlation)}. `,
        "The split since 2022 was cut after the result was known."));
  }

  function drawLift() {
    const narrow = (liftPlot.clientWidth || 800) < 600;
    const rows = F.lift.map((r) => ({ ...r, t: toDate(r.month) }));
    const topH = narrow ? 170 : 200;
    const gap = 58;
    const botH = narrow ? 160 : 190;
    const c = frame(liftPlot, { height: topH + gap + botH + 60, margin: { top: 26, right: narrow ? 14 : 30, bottom: 34, left: 40 },
      label: "US cargoes loaded and cancelled each month from 2019 to early 2021, above the margin of a cargo over 115 percent of Henry Hub" });
    const x = d3.scaleUtc([rows[0].t, rows[rows.length - 1].t], [14, c.w - 14]);
    const bw = Math.max(3, (c.w - 28) / rows.length - 3);
    const y = d3.scaleLinear([0, 100], [topH, 0]);
    axisY({ ...c, h: topH }, y, { values: [0, 20, 40, 60, 80, 100], format: int, label: "Cargoes a month: loaded (solid) and cancelled (outlined)" });
    for (const r of rows) {
      s("rect", { x: x(r.t) - bw / 2, width: bw, y: y(r.cargoes), height: topH - y(r.cargoes), fill: "var(--europe)", rx: 1.5 }, c.g);
      if (r.cancelled) s("rect", { x: x(r.t) - bw / 2 + 0.75, width: bw - 1.5, y: y(r.cargoes + r.cancelled), height: y(r.cargoes) - y(r.cargoes + r.cancelled) - 2, fill: "none", stroke: "var(--ink)", "stroke-width": 1.5, rx: 1.5 }, c.g);
    }
    const g2 = s("g", { transform: `translate(0,${topH + gap})` }, c.g);
    const bottom = { ...c, g: g2, h: botH };
    const y2 = d3.scaleLinear([-2, 6], [botH, 0]);
    axisY(bottom, y2, { values: [-2, -1, 0, 1, 2, 3, 4, 5, 6], format: (v) => num(v, 0), label: "Netback less 115 percent of Henry Hub, USD/MMBtu. Solid: sold in Europe. Dashed: sold in Asia" });
    s("rect", { x: 0, width: c.w, y: y2(0), height: botH - y2(0), fill: "var(--wash)" }, g2);
    path(bottom, rows.map((r) => [x(r.t), r.margin_asia == null ? null : y2(r.margin_asia)]), { stroke: ROUTES.panama.color, "stroke-width": 1.6, "stroke-dasharray": "4 3" });
    path(bottom, rows.map((r) => [x(r.t), r.margin_europe == null ? null : y2(r.margin_europe)]), { stroke: "var(--ink)", "stroke-width": 2 });
    s("text", { class: "label-sub", x: 6, y: botH - 6 }, g2, "below zero: the cargo does not cover its gas");
    axisX(bottom, x, { values: d3.utcMonth.every(narrow ? 6 : 3).range(rows[0].t, d3.utcMonth.offset(rows[rows.length - 1].t, 1)), format: (d) => (d.getUTCMonth() === 0 ? d3.utcFormat("%Y")(d) : d3.utcFormat("%b")(d)) });

    const cursor = s("line", { class: "cursor", y1: 0, y2: topH + gap + botH, visibility: "hidden" }, c.g);
    const bisect = d3.bisector((r) => r.t).center;
    hover({ ...c, h: topH + gap + botH }, {
      count: rows.length, toIndex: (px) => bisect(rows, x.invert(px)),
      leave: () => cursor.setAttribute("visibility", "hidden"),
      move: (i) => {
        const r = rows[i];
        cursor.setAttribute("x1", x(r.t)); cursor.setAttribute("x2", x(r.t)); cursor.setAttribute("visibility", "visible");
        showTip(c, x(r.t), y(r.cargoes), month(r.month), [
          { label: "Cargoes loaded", value: int(r.cargoes) },
          { label: "Cargoes cancelled", value: int(r.cancelled) },
          r.margin_europe == null ? null : { key: "c-ink", label: "Margin sold in Europe", value: num(r.margin_europe) },
          r.margin_asia == null ? null : { key: "c-panama dash", label: "Margin sold in Asia", value: num(r.margin_asia) },
          r.threshold == null ? null : { label: "115 percent of Henry Hub", value: num(r.threshold) },
        ], r.margin_europe == null ? "No Japanese spot price was published for this month." : null);
      },
    });
  }

  function update() {
    const t = F.test;
    const s22 = F.since_2022;
    put(head, "After a month with the arb open, ", b(num(t.open.mean_share * 100, 0) + " percent"), " of US LNG left for JKM markets; after a closed month, ",
      b(num(t.closed.mean_share * 100, 0) + " percent"), ". Since 2022 the gap is ", b(num((s22.open.mean_share - s22.closed.mean_share) * 100, 0) + " point" + (Math.round((s22.open.mean_share - s22.closed.mean_share) * 100) === 1 ? "" : "s")), ".");
    put(dek, `Departures in DOE's cargo record against the arb of the month before, over ${t.months} months. The rule was fixed before the result was computed.`);
    put(figTitle, "Cargoes went to Asia when the arb paid, until 2022; since then Asia's share has stayed low whatever the arb");
    put(source, `JKM markets: Japan, South Korea, China and Taiwan. Share of the volume exported by vessel each departure month: US Department of Energy, to ${month(months[months.length - 1].month)}. `,
      "Arb margin: this study, cheapest open route at the reported charter rate.");
    drawShare();
    bars();

    // the longest run of months in which a cargo sold in Europe did not cover its gas
    let run = [];
    let longest = [];
    for (const r of F.lift) {
      if (r.margin_europe != null && r.margin_europe < 0) run.push(r);
      else { if (run.length > longest.length) longest = run; run = []; }
    }
    if (run.length > longest.length) longest = run;
    const cancelled = F.lift.reduce((a, r) => a + r.cancelled, 0);
    const y2020 = F.lift.filter((r) => r.month.startsWith("2020"));
    const low = y2020.reduce((a, r) => (r.cargoes < a.cargoes ? r : a));
    const high = y2020.slice(0, y2020.indexOf(low) + 1).reduce((a, r) => (r.cargoes > a.cargoes ? r : a));
    put(liftLead, "A buyer lifts a cargo when its best netback covers 115 percent of Henry Hub, and must cancel about two months ahead.");
    put(liftTitle, `From ${month(longest[0].month).split(" ")[0]} to ${month(longest[longest.length - 1].month)} a cargo sold in Europe did not cover its gas: about ${cancelled} cargoes were cancelled and loadings fell from ${high.cargoes} to ${low.cargoes} a month`);
    put(liftSource, "Cargoes loaded: US Department of Energy. Cancelled: ", h("a", { href: F.cancellations_source.url, rel: "noopener" }, "EIA, 11 August 2020"),
      ". Margins: this study, on the World Bank's TTF and, for Asia to September 2020, METI's price of spot cargoes contracted in the month. In mid 2020 that price includes cargoes sold for the winter and overstates what a prompt cargo fetched, so the dashed line flatters Asia.");
    drawLift();

    put(tableBody, table([
      { label: "Month", value: (m) => month(m.month, true), head: true },
      { label: "Cargoes", n: true, value: (m) => int(m.cargoes) },
      { label: "To JKM markets, percent", n: true, value: (m) => num(m.share_jkm * 100, 1) },
      { label: "To all Asia, percent", n: true, value: (m) => num(m.share_asia * 100, 1) },
      { label: "To Europe, percent", n: true, value: (m) => num(m.share_europe * 100, 1) },
      { label: "Arb margin, USD/MMBtu", n: true, value: (m) => (m.margin == null ? "no price" : num(m.margin)) },
      { label: "Arb", value: (m) => (m.open == null ? "" : m.open ? "open" : "closed"), cls: (m) => (m.open ? "yes" : "no") },
    ], [...months].reverse(), { tall: true }),
    h("h3", { style: "margin-top:16px" }, "The same comparison at other lags"),
    table([
      { label: "Cargoes that left", value: (r) => r[0], head: true },
      { label: "After open months, percent", n: true, value: (r) => `${num(r[1].open.mean_share * 100, 1)} (${r[1].open.months})` },
      { label: "After closed months, percent", n: true, value: (r) => `${num(r[1].closed.mean_share * 100, 1)} (${r[1].closed.months})` },
      { label: "Correlation with the margin", n: true, value: (r) => num(r[1].correlation) },
    ], [["the same month", F.robustness[0]], ["one month later (the rule)", F.test], ["two months later", F.robustness[1]], ["one month later, since 2022", F.since_2022]]),
    h("p", { class: "source" }, F.rule));
  }

  return { update };
}

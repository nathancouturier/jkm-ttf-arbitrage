// Method: the formulas, one cargo worked line by line, the parameters with their sources, credits and limits.

import { priceCargo, usdMmbtuToEurMwh } from "../engine.js";
import { h, b, num, int, day, month, panel, table, tag } from "../util.js";

// [name, what it equals, a note]
const FORMULAS = [
  ["loaded", "capacity x fill x MMBtu per m3"],
  ["round trip", "2 x distance / (speed x 24) + days in port + canal and waiting days, both ways"],
  ["delivered", "loaded - loaded x boil-off a day x round trip days", "the boil-off is the ship's fuel"],
  ["cost", "hire x round trip days + port costs + canal tolls and fees, laden and ballast + EU ETS (the European voyage only) + financing of the cargo"],
  ["netback", "(DES price x delivered - cost) / loaded", "DES price: TTF + discount in Europe (the discount is negative), JKM in Asia"],
  ["S*(route)", "the JKM minus TTF spread at which netback(Asia, route) = netback(Europe)", "= extra hire + canal tolls + extra boil-off + Europe's DES discount + other, per MMBtu delivered east"],
  ["H*(route)", "the charter rate at which the two netbacks are equal at today's prices"],
  ["lift margin", "best netback - 1.15 x Henry Hub", "the fixed liquefaction fee is owed either way"],
];

const LIMITS = [
  ["The charter rate is one published assessment,", " held between reports; a real fixture differs, and the zero case stands for tonnage already on term charter."],
  ["Europe's DES discount is this study's measure,", " not ACER's own spread: ACER's assessment against TTF over the days it covers. Other weightings move the levels by about 0.15; until January 2023 the discount is an assumption."],
  ["Panama is priced at the tariff", " with a booked slot; an auctioned slot costs more and its price is not published."],
  ["Front-month prices are not the cargo's price:", " a cargo is sold four to eight weeks out, and before October 2020 the JKM series is METI's price of spot cargoes for Japan."],
  ["Voyage details are a benchmark's:", " 17 knots, the same boil-off laden and in ballast, a day in each port and canal, port costs from one 2022 note. Financing is on the purchase cost, not on the later sale."],
  ["Flows show association, not cause:", " term contracts, tariffs and ships already paid for move cargoes as well, and nothing here is a forecast."],
];

export function mount(root, ctx) {
  const D = ctx.D;
  const P = D.now.preset;
  const x = P.inputs;
  const res = priceCargo(x);
  const E = res.routes.europe;
  const A = res.routes.panama;
  const fx = P.usd_per_eur;
  const ship = x.ship;
  const perDay = ship.speed_kn * 24;
  const burnt = E.boil_off_per_day / x.carbon.mmbtu_per_t_lng;
  const rate = (x.finance.rate + x.finance.spread) * 100;
  const financing = (r) => `${num(x.contract.hh_multiple * x.henry_hub, 3)} x ${int(r.loaded)} x ${num(rate, 2)} percent x ${num(r.laden_days, 2)} / 360 = ${int(r.cost.financing)}`;

  const two = (label, formula, e, a) => ({ label, formula, e, a });
  const lines = [
    two("Days at sea, one way", `nautical miles / (${num(ship.speed_kn, 0)} knots x 24)`, `${num(x.routes.europe.distance_nm, 1)} / ${num(perDay, 0)} = ${num(E.sea_days, 2)}`, `${num(x.routes.panama.distance_nm, 1)} / ${num(perDay, 0)} = ${num(A.sea_days, 2)}`),
    two("Round trip, days", "2 x sea days + a day to load and a day to discharge + a day in the canal each way; no waiting", `2 x ${num(E.sea_days, 2)} + 2 = ${num(E.round_trip_days, 2)}`, `2 x ${num(A.sea_days, 2)} + 2 + 2 = ${num(A.round_trip_days, 2)}`),
    two("Loaded, MMBtu", `${int(ship.capacity_m3)} m3 x ${num(ship.fill, 3)} x ${num(ship.mmbtu_per_m3, 0)}`, int(E.loaded), int(A.loaded)),
    two("Boil-off, MMBtu", `loaded x ${num(ship.boil_off * 100, 3)} percent = ${num(E.boil_off_per_day, 2)} a day, x round trip days`, `${num(E.boil_off_per_day, 2)} x ${num(E.round_trip_days, 2)} = ${int(E.boil_off)}`, `${num(A.boil_off_per_day, 2)} x ${num(A.round_trip_days, 2)} = ${int(A.boil_off)}`),
    two("Delivered, MMBtu", "loaded - boil-off", int(E.delivered), int(A.delivered)),
    two("DES price, USD/MMBtu", "TTF + Europe's DES discount; JKM", `${num(x.ttf)} + (${num(x.des_discount, 4)}) = ${num(E.price, 4)}`, num(A.price)),
    two("Revenue, USD", "DES price x delivered", int(E.price * E.delivered), int(A.price * A.delivered)),
    two("Hire, USD", `${int(x.hire)} USD a day x round trip days`, int(E.cost.hire), int(A.cost.hire)),
    two("Port costs, USD", "both ports", int(E.cost.ports), int(A.cost.ports)),
    two("Canal tolls and fees, USD", "laden + ballast", int(E.cost.tolls), `${int(x.routes.panama.toll_laden)} + ${int(x.routes.panama.toll_ballast)} = ${int(A.cost.tolls)}`),
    two("EU ETS, USD", `allowance in USD (${num(P.eua_eur_t)} EUR x ${num(fx, 4)}) x share surrendered x tCO2e per tonne of LNG x tonnes burnt a day (${num(E.boil_off_per_day, 2)} / ${num(x.carbon.mmbtu_per_t_lng)} MMBtu a tonne) x days counted (half the sea days + the berth day)`,
      `${num(x.carbon.eua_usd_t, 2)} x ${num(x.carbon.phase_in, 2)} x ${num(x.carbon.tco2e_per_t_lng, 3)} x ${num(burnt, 2)} x ${num(0.5 * (E.round_trip_days - 2) + 1, 2)} = ${int(E.cost.carbon)}`, "0"),
    two("Laden days", "sea days + the two port days + the canal day", `${num(E.sea_days, 2)} + 2 = ${num(E.laden_days, 2)}`, `${num(A.sea_days, 2)} + 2 + 1 = ${num(A.laden_days, 2)}`),
    two("Financing, USD", `${num(x.contract.hh_multiple, 2)} x Henry Hub x loaded x (SOFR ${num(x.finance.rate * 100, 2)} + ${num(x.finance.spread * 100, 2)} percent) x laden days / 360`, financing(E), financing(A)),
    two("Voyage cost, USD", "hire + ports + canal + EU ETS + financing", int(E.cost.total), int(A.cost.total)),
    two("Netback, USD/MMBtu loaded", "(revenue - voyage cost) / loaded", h("b", null, num(E.netback, 3)), h("b", null, num(A.netback, 3))),
  ];
  const dr = A.drivers;
  const extraDays = A.round_trip_days - E.round_trip_days;
  const sStar = A.breakeven_spread;
  const atLevel = priceCargo({ ...x, jkm: x.ttf + sStar }).routes.panama.netback;
  const sLines = [
    ["Extra hire", `${int(x.hire)} x ${num(extraDays, 3)} extra days / ${int(A.delivered)} delivered east`, num(dr.hire, 4)],
    ["Canal tolls and fees", `${int(A.cost.tolls)} / ${int(A.delivered)}`, num(dr.tolls, 4)],
    ["Extra boil-off", `${num(E.price, 4)} x (${int(E.delivered)} - ${int(A.delivered)}) / ${int(A.delivered)}`, num(dr.boil_off, 4)],
    ["Europe's DES discount", "as measured", num(dr.des_discount, 4)],
    ["Ports, carbon and financing", `(${int(A.cost.ports)} - ${int(E.cost.ports)} - ${int(E.cost.carbon)} + ${int(A.cost.financing)} - ${int(E.cost.financing)}) / ${int(A.delivered)}`, num(dr.other, 4)],
    ["Reroute level S*", `the sum; JKM minus TTF this week is ${num(res.spread)}`, h("b", null, num(sStar, 4))],
    ["Check", `at JKM = ${num(x.ttf)} + (${num(sStar, 4)}) = ${num(x.ttf + sStar, 4)} the netback via Panama is Gate's`, num(atLevel, 3)],
    ["Charter rate that closes the arb, H*", `${int(x.hire)} + (${num(res.spread)} - (${num(sStar, 4)})) x ${int(A.delivered)} / ${num(extraDays, 3)} extra days, in USD a day`, int(A.breakeven_hire)],
    ["Lift margin", `best netback - ${num(x.contract.hh_multiple, 2)} x Henry Hub = ${num(res.lift.best_netback, 3)} - ${num(x.contract.hh_multiple, 2)} x ${num(x.henry_hub)}; after the fixed fee of ${num(x.contract.fee)}, ${num(res.lift.margin_after_fee)}`, num(res.lift.margin, 3)],
  ];
  const T = D.timing;
  const C = D.checks;
  const share = (g) => num((g.open / g.weeks) * 100, 0);

  const sources = panel("Data, dates and credits", [table([
    { label: "Series", value: (r) => h("a", { href: r.url, rel: "noopener" }, r.series), head: true },
    { label: "Covers", value: (r) => `${r.from.length === 7 ? month(r.from, true) : day(r.from, true)} to ${r.to.length === 7 ? month(r.to, true) : day(r.to, true)}` },
    { label: "Kept up to date", value: (r) => [r.kept, r.ok === false ? h("span", { class: "tag held" }, " last refresh failed, data held") : null] },
    { label: "Credit", value: (r) => r.credit },
  ], D.credits, { min: 760 }), h("p", { class: "source" }, "Routes: this study with searoute (Apache License 2.0) over Eurostat's SeaRoute network (EUPL 1.2). Land: Natural Earth, public domain, through world-atlas (ISC). Charts: D3 (ISC). Typefaces: Fraunces, Figtree and JetBrains Mono, SIL Open Font License. Platts' counts are quoted from the publications that republished them.")]);

  const gap = C.platts.model_via_panama - C.platts.model_via_cape;
  const theirs = C.platts.via_panama_usd_mmbtu - C.platts.via_cape_usd_mmbtu;
  const sameSigns = C.platts.model_via_panama > 0 === C.platts.via_panama_usd_mmbtu > 0 && C.platts.model_via_cape > 0 === C.platts.via_cape_usd_mmbtu > 0;
  const checks = panel("Checked against published figures", [table([
    { label: "Published", value: (r) => r[0], head: true },
    { label: "Their figure", n: true, value: (r) => r[1] },
    { label: "This model", n: true, value: (r) => r[2] },
  ], [
    ["Spark's worked freight example, 8 February 2022: charterer's payment at half ballast bonus, USD", int(C.spark.half_ballast_bonus.charterer_payment_usd), "reproduced within 1 USD"],
    ["The same example: total voyage cost, USD", int(C.spark.half_ballast_bonus.total_cost_usd), "reproduced within 1 USD"],
    ["Platts, 28 April 2026: arb to North Asia via Panama, USD/MMBtu", num(C.platts.via_panama_usd_mmbtu, 3), num(C.platts.model_via_panama, 3)],
    ["Platts, the same day: via the Cape", num(C.platts.via_cape_usd_mmbtu, 3), num(C.platts.model_via_cape, 3)],
    ["Platts: gap between the two routes", num(theirs, 3), num(gap, 3)],
  ], { min: 520 }),
  h("p", { class: "source" }, sameSigns ? "The model has the arb open and shut on the same routes as Platts" : "The two routes come out in the same order as Platts'",
    `, ${num(gap)} apart against Platts' ${num(theirs)}, about ${num((gap / theirs) * 100, 0)} percent of its gap. Platts prices one day with its own freight, European netback and delivery months; the model's line is the week to ${day(C.platts.week)} at the last reported charter rate, ${int(C.platts.hire)} USD a day. Platts counted ${C.platts.of_which_via_cape} of ${C.platts.cargoes_to_asia} US cargoes to Asia going round the Cape. `,
    h("a", { href: C.platts.url, rel: "noopener" }, "Source"), ".")]);

  const rates = panel("Charter rates and their articles", [table([
    { label: "Reported", value: (r) => day(r.date, true), head: true },
    { label: "USD a day", n: true, value: (r) => int(r.usd_per_day) },
    { label: "Assessment and ship", value: (r) => `${r.assessment}, ${r.ship}` },
    { label: "Read in", value: (r) => (r.url ? h("a", { href: r.url, rel: "noopener" }, r.publisher) : r.publisher) },
  ], [...D.charter_rates].reverse(), { tall: true, min: 620 }),
  h("p", { class: "source" }, `${D.charter_rates.length} figures. Between two reports the last one is held, for 26 weeks at most; the History view's table marks a rate as held once it is more than 14 days old, and as assumed where there is none.`)]);

  root.append(
    h("p", { class: "kicker" }, "Method"),
    h("h1", null, "One cargo, two markets, four routes. Every number on this site is the arithmetic below."),
    h("p", { class: "dek" }, "The model is ", h("a", { href: "https://github.com/nathancouturier/jkm-ttf-arbitrage/blob/main/src/arb/engine.py" }, "one Python file"),
      ", copied line for line into the browser and held to it by a test. Both prices are delivered ex-ship: Europe's is TTF plus the DES discount, a negative number, which is what the market charges for regasification and entry to the grid."),
    h("dl", { class: "formula" }, FORMULAS.map(([name, equals, note]) => h("div", null, h("dt", null, name), h("dd", null, "= " + equals, note ? h("span", { class: "why" }, note) : null)))),

    h("h2", null, `One cargo, line by line: the week to ${day(P.date)}`),
    h("p", { class: "dek" }, `JKM ${num(x.jkm)}, TTF ${num(x.ttf)} (${num(usdMmbtuToEurMwh(x.ttf, fx))} EUR/MWh at ${num(fx, 4)} USD per EUR), Henry Hub ${num(x.henry_hub)}, charter rate ${int(x.hire)} USD a day, on the ${P.ships[P.ship_id].name}.`),
    table([
      { label: "Line", value: (r) => r.label, head: true },
      { label: "How", value: (r) => r.formula, cls: () => "how" },
      { label: "To Gate", n: true, value: (r) => r.e },
      { label: "To Futtsu via Panama", n: true, value: (r) => r.a },
    ], lines, { stack: true, widths: ["17%", "33%", "25%", "25%"] }),
    h("h3", { style: "margin-top:20px" }, "The reroute level via Panama, the charter rate that closes the arb and the lift test, from the same cargo"),
    table([
      { label: "Line", value: (r) => r[0], head: true },
      { label: "How", value: (r) => r[1], cls: () => "how" },
      { label: "USD/MMBtu", n: true, value: (r) => r[2] },
    ], sLines, { stack: true, widths: ["24%", "58%", "18%"] }),
    h("p", { class: "source" }, "Every line is computed on unrounded figures, so a last digit can differ from what the printed figures give."),

    h("p", { class: "prose", style: "margin-top:18px" }, b("Which prices are compared. "), "EIA's weekly averages of the two front months. From the 16th JKM's names a month later than TTF's, and a cargo reaches Asia two to four weeks after it would reach Europe: ",
      `since January 2022, when EIA's series became front-month futures, the arb was open in ${share(T.same_month)} percent of the ${T.same_month.weeks} weeks that compare the same month and in ${share(T.different_months)} percent of the other ${T.different_months.weeks}.`),

    h("h2", null, "Limits"),
    h("ol", { class: "prose" }, LIMITS.map(([lead, rest]) => h("li", null, b(lead), rest))),

    h("div", { class: "more" }, checks,
      panel("Parameters and their sources", table([
        { label: "", value: (r) => r.group },
        { label: "Parameter", value: (r) => r.name, head: true },
        { label: "Value", value: (r) => [r.value, r.status === "assumption" ? tag("assumed") : null] },
        { label: "Source", value: (r) => (r.url ? h("a", { href: r.url, rel: "noopener" }, r.source) : r.source) },
      ], D.parameters, { min: 760 })),
      rates, sources));

  // The footer's link to the sources opens their panel and brings it into view, from any view and from this one.
  let shown = false;
  const showSources = () => {
    sources.open = true;
    sources.scrollIntoView({ block: "start" });
  };
  const link = document.querySelector('footer a[href="#/method?open=sources"]');
  if (link) link.onclick = () => { if (root.isConnected && sources.isConnected) setTimeout(showSources, 0); };

  return {
    update() {
      const wanted = ctx.params.open === "sources";
      if (wanted && !shown) showSources();
      shown = wanted;
    },
  };
}

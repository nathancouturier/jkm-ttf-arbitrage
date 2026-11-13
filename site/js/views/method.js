// Method: the formulas, one cargo worked line by line, the parameters with their sources, credits and limits.

import { priceCargo, usdMmbtuToEurMwh } from "../engine.js";
import { h, b, put, num, int, day, month, ROUTES, panel, table, tag } from "../util.js";

const FORMULAS = `loaded      = capacity x fill x MMBtu per m3
round trip  = 2 x distance / (speed x 24) + days in port + canal and waiting days, both ways
delivered   = loaded - loaded x boil-off a day x round trip days
cost        = hire x round trip days + port costs + canal tolls and fees, laden and ballast
              + EU ETS (the European voyage only) + financing of the cargo
netback     = (DES price x delivered - cost) / loaded        DES price: TTF + discount in Europe, JKM in Asia

S*(route)   = the JKM minus TTF spread at which netback(Asia, route) = netback(Europe)
            = extra hire + canal tolls + extra boil-off + Europe's DES discount + other, per MMBtu delivered east
H*(route)   = the charter rate at which the two netbacks are equal at today's prices
lift margin = best netback - 1.15 x Henry Hub                the fixed liquefaction fee is owed either way`;

const LIMITS = [
  ["The charter rate is one published assessment.", " Spark30S Atlantic is a round-trip rate for one ship, reported here from press articles and held between reports. A real fixture differs with the ballast bonus, the positioning and the ship; the zero case stands for tonnage already on term charter."],
  ["What Europe pays is an assessment too.", " The DES discount is ACER's Northwest Europe assessment against TTF's front month, averaged over 20 days. Before 2023 it is an assumption, except in the squeeze of 2022 where ACER gives a floor."],
  ["Panama is priced at the tariff.", " Slots are booked, auctioned or allocated a year ahead, and the price of an auctioned slot is not published. The Routes view gives what a slot is worth instead; the wait is a control."],
  ["Front-month prices are not the cargo's price.", " A cargo loaded this week is sold for delivery four to eight weeks out, and the two front months can name different months. Before October 2020 the JKM series is METI's price of spot cargoes for Japan, a proxy."],
  ["Voyage details are a benchmark's.", " Seventeen knots, the same boil-off laden and in ballast, a day in each port, port costs from one 2022 note held for every year, and tariffs taken as in force on the loading day."],
  ["Flows show association.", " DOE records the destination declared at departure. Term contracts, tariffs and ships already paid for move cargoes as well, and the study forecasts nothing."],
];

export function mount(root, ctx) {
  const D = ctx.D;
  const P = D.now.preset;
  const x = P.inputs;
  const res = priceCargo(x);
  const E = res.routes.europe;
  const A = res.routes.panama;
  const fx = P.usd_per_eur;

  const two = (label, formula, e, a) => ({ label, formula, e, a });
  const ship = x.ship;
  const lines = [
    two("Days at sea, one way", "distance / (speed x 24)", `${int(x.routes.europe.distance_nm)} / ${num(ship.speed_kn * 24, 0)} = ${num(E.sea_days, 2)}`, `${int(x.routes.panama.distance_nm)} / ${num(ship.speed_kn * 24, 0)} = ${num(A.sea_days, 2)}`),
    two("Round trip, days", "2 x sea days + 2 port days + 2 x canal days", `2 x ${num(E.sea_days, 2)} + 2 = ${num(E.round_trip_days, 2)}`, `2 x ${num(A.sea_days, 2)} + 2 + 2 = ${num(A.round_trip_days, 2)}`),
    two("Loaded, MMBtu", `${int(ship.capacity_m3)} x ${num(ship.fill, 3)} x ${num(ship.mmbtu_per_m3, 0)}`, int(E.loaded), int(A.loaded)),
    two("Boil-off, MMBtu", `loaded x ${num(ship.boil_off * 100, 3)} percent x days`, `${num(E.boil_off_per_day, 2)} x ${num(E.round_trip_days, 2)} = ${int(E.boil_off)}`, `${num(A.boil_off_per_day, 2)} x ${num(A.round_trip_days, 2)} = ${int(A.boil_off)}`),
    two("Delivered, MMBtu", "loaded - boil-off", int(E.delivered), int(A.delivered)),
    two("DES price, USD/MMBtu", "TTF + discount; JKM", `${num(x.ttf)} + (${num(x.des_discount, 3)}) = ${num(E.price, 3)}`, num(A.price)),
    two("Revenue, USD", "price x delivered", int(E.price * E.delivered), int(A.price * A.delivered)),
    two("Hire, USD", `${int(x.hire)} x days`, int(E.cost.hire), int(A.cost.hire)),
    two("Port costs, USD", "both ports", int(E.cost.ports), int(A.cost.ports)),
    two("Canal tolls and fees, USD", "laden + ballast", int(E.cost.tolls), `${int(x.routes.panama.toll_laden)} + ${int(x.routes.panama.toll_ballast)} = ${int(A.cost.tolls)}`),
    two("EU ETS, USD", "allowance x share x tCO2e per t x tonnes burnt a day x (half the sea days + the berth day)",
      `${num(x.carbon.eua_usd_t, 2)} x ${num(x.carbon.phase_in, 2)} x ${num(x.carbon.tco2e_per_t_lng, 3)} x ${num(E.boil_off_per_day / x.carbon.mmbtu_per_t_lng, 2)} x ${num(0.5 * (E.round_trip_days - 2) + 1, 2)} = ${int(E.cost.carbon)}`, "0"),
    two("Financing, USD", `1.15 x Henry Hub x loaded x (SOFR + 1.5 percent) x laden days / 360`,
      `${num(x.contract.hh_multiple * x.henry_hub, 3)} x ${int(E.loaded)} x ${num((x.finance.rate + x.finance.spread) * 100, 2)} percent x ${num(E.laden_days, 2)} / 360 = ${int(E.cost.financing)}`, int(A.cost.financing)),
    two("Voyage cost, USD", "sum of the five lines", int(E.cost.total), int(A.cost.total)),
    two("Netback, USD/MMBtu loaded", "(revenue - cost) / loaded", h("b", null, num(E.netback, 3)), h("b", null, num(A.netback, 3))),
  ];
  const dr = A.drivers;
  const extraDays = A.round_trip_days - E.round_trip_days;
  const sLines = [
    ["Extra hire", `${int(x.hire)} x ${num(extraDays, 2)} extra days / ${int(A.delivered)}`, dr.hire],
    ["Canal tolls and fees", `${int(A.cost.tolls)} / ${int(A.delivered)}`, dr.tolls],
    ["Extra boil-off", `${num(E.price, 3)} x (${int(E.delivered)} - ${int(A.delivered)}) / ${int(A.delivered)}`, dr.boil_off],
    ["Europe's DES discount", "as observed", dr.des_discount],
    ["Ports, carbon and financing", `(${int(A.cost.ports)} - ${int(E.cost.ports)} - ${int(E.cost.carbon)} + ${int(A.cost.financing)} - ${int(E.cost.financing)}) / ${int(A.delivered)}`, dr.other],
  ];
  const T = D.timing;
  const C = D.checks;

  const openParams = ctx.params.open === "sources";
  root.append(
    h("p", { class: "kicker" }, "Method"),
    h("h1", null, "One cargo, two markets, four routes. Every number on this site is the arithmetic below."),
    h("p", { class: "dek" }, "The model is ", h("a", { href: "https://github.com/nathancouturier/jkm-ttf-arbitrage/blob/main/src/arb/engine.py" }, "one Python file"),
      ", copied line for line into the browser and held to it by a test. Hire runs for the round trip and the gas that boils off is the ship's fuel, as in the freight benchmark."),
    h("pre", { class: "formula" }, FORMULAS),

    h("h2", null, `One cargo, line by line: the week to ${day(P.date)}`),
    h("p", { class: "dek" }, `JKM ${num(x.jkm)}, TTF ${num(x.ttf)} (${num(usdMmbtuToEurMwh(x.ttf, fx))} EUR/MWh at ${num(fx, 4)}), Henry Hub ${num(x.henry_hub)}, charter rate ${int(x.hire)} USD a day, on the ${P.ships[P.ship_id].name}.`),
    table([
      { label: "Line", value: (r) => r.label, head: true },
      { label: "How", value: (r) => r.formula },
      { label: "To Gate", n: true, value: (r) => r.e },
      { label: "To Futtsu via Panama", n: true, value: (r) => r.a },
    ], lines),
    h("h3", { style: "margin-top:20px" }, "The reroute level via Panama, from the same cargo"),
    table([
      { label: "Driver", value: (r) => r[0], head: true },
      { label: "How", value: (r) => r[1] },
      { label: "USD/MMBtu", n: true, value: (r) => num(r[2], 3) },
    ], [...sLines, ["Reroute level S*", "the sum; JKM minus TTF this week is " + num(res.spread), A.breakeven_spread],
      ["Check", `at JKM = ${num(x.ttf)} + (${num(A.breakeven_spread, 3)}) the Asian netback is ${num(E.netback, 3)}, the European one`, A.breakeven_spread]]),

    h("h2", null, "Which prices are compared"),
    h("p", { class: "prose" }, "EIA's weekly averages of the JKM and TTF front months, Thursday to Wednesday. From the 16th of a month JKM's front month is one delivery month later than TTF's, and a cargo reaches Asia about four weeks after it would reach Europe. ",
      `In the ${T.same_month.weeks} weeks that compare the same month the spread averaged ${num(T.same_month.mean_spread)} and the arb was open in ${num((T.same_month.open / T.same_month.weeks) * 100, 0)} percent of them; in the other ${T.different_months.weeks} it averaged ${num(T.different_months.mean_spread)} and was open in ${num((T.different_months.open / T.different_months.weeks) * 100, 0)} percent. The difference is about ${num(Math.abs(T.same_month.mean_spread - T.different_months.mean_spread), 1)} USD/MMBtu on average.`),

    h("h2", null, "Checked against published figures"),
    table([
      { label: "Published", value: (r) => r[0], head: true },
      { label: "Their figure", n: true, value: (r) => r[1] },
      { label: "This model", n: true, value: (r) => r[2] },
    ], [
      ["Spark's worked freight example, 8 February 2022: charterer's payment at half ballast bonus, USD", int(C.spark.half_ballast_bonus.charterer_payment_usd), "reproduced within 1 USD"],
      ["The same example: total voyage cost, USD", int(C.spark.half_ballast_bonus.total_cost_usd), "reproduced within 1 USD"],
      [`Platts, 28 April 2026: arb to North Asia via Panama, USD/MMBtu`, num(C.platts.via_panama_usd_mmbtu, 3), num(C.platts.model_via_panama, 3)],
      ["Platts, the same day: via the Cape", num(C.platts.via_cape_usd_mmbtu, 3), num(C.platts.model_via_cape, 3)],
      ["Platts: gap between the two routes", num(C.platts.via_panama_usd_mmbtu - C.platts.via_cape_usd_mmbtu, 3), num(C.platts.model_via_panama - C.platts.model_via_cape, 3)],
    ]),
    h("p", { class: "source" }, `The two routes come out in the same order and ${num(C.platts.model_via_panama - C.platts.model_via_cape)} apart against Platts' ${num(C.platts.via_panama_usd_mmbtu - C.platts.via_cape_usd_mmbtu)}. Platts prices one day with its own freight and European netback; the model's line is the week to ${day(C.platts.week)} at the last reported charter rate, ${int(C.platts.hire)} USD a day. Platts counted ${C.platts.of_which_via_cape} of ${C.platts.cargoes_to_asia} US cargoes to Asia going round the Cape. `,
      h("a", { href: C.platts.url, rel: "noopener" }, "Source"), "."),

    h("h2", null, "Limits"),
    h("ol", { class: "prose" }, LIMITS.map(([lead, rest]) => h("li", null, b(lead), rest))),

    h("div", { class: "more" },
      panel("Parameters and their sources", table([
        { label: "", value: (r) => r.group },
        { label: "Parameter", value: (r) => r.name, head: true },
        { label: "Value", value: (r) => [r.value, r.status === "assumption" ? tag("assumed") : null] },
        { label: "Source", value: (r) => (r.url ? h("a", { href: r.url, rel: "noopener" }, r.source) : r.source) },
      ], D.parameters)),
      panel("Data, dates and credits", [table([
        { label: "Series", value: (r) => h("a", { href: r.url, rel: "noopener" }, r.series), head: true },
        { label: "Covers", value: (r) => `${r.from.length === 7 ? month(r.from, true) : day(r.from, true)} to ${r.to.length === 7 ? month(r.to, true) : day(r.to, true)}` },
        { label: "Kept up to date", value: (r) => [r.kept, r.ok === false ? h("span", { class: "tag held" }, " last refresh failed, data held") : null] },
        { label: "Credit", value: (r) => r.credit },
      ], D.credits), h("p", { class: "source" }, "Routes: this study with searoute (Apache License 2.0) over Eurostat's SeaRoute network (EUPL 1.2). Land: Natural Earth, public domain, through world-atlas (ISC). Charts: D3 (ISC). Typefaces: Fraunces, Figtree and JetBrains Mono, SIL Open Font License. Platts' counts are quoted from the publications that republished them.")], openParams)));

  return { update() {} };
}

// Tables several views open behind a button: where each input comes from, and what a reroute level is made of.

import { usdMmbtuToEurMwh } from "../engine.js";
import { h, num, int, day, tag, table, ROUTES, EAST } from "../util.js";

const asOf = (src) => (src && src.date ? day(String(src.date)) : "");

export function inputsTable(P, inputs = P.inputs) {
  const s = P.sources;
  const fx = P.usd_per_eur;
  const link = (src) => (src && src.url ? h("a", { href: src.url, rel: "noopener" }, src.note) : (src && src.note) || "");
  const rows = [
    ["JKM, front month", `${num(inputs.jkm)} USD/MMBtu`, s.prices, "EIA, " + s.prices.note],
    ["TTF, front month", `${num(inputs.ttf)} USD/MMBtu, ${num(usdMmbtuToEurMwh(inputs.ttf, fx))} EUR/MWh`, s.prices, "EIA, " + s.prices.note],
    ["Charter rate, round trip", `${int(inputs.hire)} USD a day`, s.hire, link(s.hire)],
    ["Europe's DES discount to TTF", `${num(inputs.des_discount)} USD/MMBtu, ${num(s.des_discount.value)} EUR/MWh`, s.des_discount, s.des_discount.note],
    ["Henry Hub", `${num(inputs.henry_hub)} USD/MMBtu`, s.henry_hub, "EIA, " + s.henry_hub.note],
    ["Dollars per euro", num(fx, 4), s.usd_per_eur, s.usd_per_eur.note],
    ["SOFR", `${num(inputs.finance.rate * 100)} percent`, s.sofr, s.sofr.note],
    ["EU allowance", `${num(P.eua_eur_t)} EUR a tonne`, s.eua, s.eua.note],
    ["Ship", P.ships[P.ship_id].name, null, "The freight benchmark's ship on the loading day"],
  ];
  return table([
    { label: "Input", value: (r) => r[0], head: true },
    { label: "Value", value: (r) => h("span", { class: "mono" }, r[1]) },
    { label: "As of", value: (r) => (r[2] ? [asOf(r[2]), tag(r[2].status)] : "") },
    { label: "Source", value: (r) => r[3] },
  ], rows, { min: 640 });
}

const DRIVERS = [
  ["hire", "Extra hire"],
  ["tolls", "Canal tolls and fees"],
  ["boil_off", "Extra boil-off"],
  ["des_discount", "Europe's DES discount"],
  ["other", "Ports, carbon and financing"],
];

export function driversTable(result, routes = EAST) {
  const col = (id) => ({ label: ROUTES[id].via + (result.routes[id].open ? "" : " (closed)"), n: true, value: (r) => r[id] });
  const rows = DRIVERS.map(([key, label]) => {
    const row = { label };
    for (const id of routes) row[id] = num(result.routes[id].drivers[key]);
    return row;
  });
  const total = { label: "Reroute level, JKM minus TTF" };
  const days = { label: "Extra days against Gate" };
  const hstar = { label: "Charter rate that closes the arb, USD a day" };
  for (const id of routes) {
    total[id] = h("b", null, num(result.routes[id].breakeven_spread));
    days[id] = num(result.routes[id].round_trip_days - result.routes.europe.round_trip_days, 1);
    hstar[id] = int(result.routes[id].breakeven_hire);
  }
  return table([{ label: "USD/MMBtu delivered east", value: (r) => r.label, head: true }, ...routes.map(col)], [...rows, total, days, hstar], { min: 520 });
}

export const methodLink = () => h("p", { class: "source" }, "Every parameter and its source is on the ", h("a", { href: "#/method" }, "Method"), " view.");

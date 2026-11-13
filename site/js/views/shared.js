// Tables several views open behind a button: where each input comes from, and what a reroute level is made of.

import { usdMmbtuToEurMwh } from "../engine.js";
import { h, num, int, day, month, tag, table, ROUTES, EAST } from "../util.js";

const asOf = (src) => (src && src.date ? day(String(src.date)) : "");

// Where the charter rate comes from, in a few words, whatever its standing.
export function hireSource(hire) {
  if (hire.status === "assumed") {
    return [`Charter rate: the ship's low scenario, no rate having been reported since ${hire.last_reported ? day(String(hire.last_reported)) : "the series began"}. `];
  }
  return [`Charter rate: Spark30S Atlantic as reported on ${day(String(hire.date))}${hire.status === "held" ? " and held since" : ""} (`,
    hire.url ? h("a", { href: hire.url, rel: "noopener" }, "LNG Prime") : "LNG Prime", "). "];
}

// The inputs behind a result. Rows the reader has changed say so in place of a date and a source.
export function inputsTable(P, inputs = P.inputs, changed = {}) {
  const s = P.sources;
  const fx = changed.fx ?? P.usd_per_eur;
  const link = (src) => (src && src.url ? h("a", { href: src.url, rel: "noopener" }, src.note) : (src && src.note) || "");
  const prices = `${s.prices.publisher}, ${s.prices.note}`;
  const rows = [
    ["jkm", "JKM, front month", `${num(inputs.jkm)} USD/MMBtu`, s.prices, prices],
    ["ttf", "TTF, front month", `${num(inputs.ttf)} USD/MMBtu, ${num(usdMmbtuToEurMwh(inputs.ttf, fx))} EUR/MWh`, s.prices, prices],
    ["hire", "Charter rate, round trip", `${int(inputs.hire)} USD a day`, s.hire, link(s.hire)],
    ["des_discount", "Europe's DES discount to TTF", `${num(inputs.des_discount)} USD/MMBtu, ${num(usdMmbtuToEurMwh(inputs.des_discount, fx))} EUR/MWh`, s.des_discount, s.des_discount.note],
    ["henry_hub", "Henry Hub", `${num(inputs.henry_hub)} USD/MMBtu`, s.henry_hub, "EIA, " + s.henry_hub.note],
    ["fx", "Dollars per euro", num(fx, 4), s.usd_per_eur, s.usd_per_eur.note],
    ["sofr", "SOFR", `${num(inputs.finance.rate * 100)} percent`, s.sofr, s.sofr.note],
    ["eua", "EU allowance", `${num(changed.eua ?? P.eua_eur_t)} EUR a tonne`, s.eua, s.eua.note],
    ["ship", "Ship", changed.shipText ?? P.ships[changed.ship ?? P.ship_id].name, null, "The freight benchmark's ship on the loading day"],
  ];
  const yours = (r) => r[0] in changed || (r[0] === "ship" && changed.shipText != null);
  const dated = (r) => (r[3] === s.prices && P.period === "month" ? [month(String(s.prices.date)), tag(s.prices.status)] : [asOf(r[3]), tag(r[3].status)]);
  return table([
    { label: "Input", value: (r) => r[1], head: true },
    { label: "Value", value: (r) => h("span", { class: "mono" }, r[2]) },
    { label: "As of", value: (r) => (yours(r) ? h("span", { class: "tag assumed" }, " your figure") : r[3] ? dated(r) : "") },
    { label: "Source", value: (r) => (yours(r) ? "" : r[4]) },
  ], rows, { min: 640 });
}

const DRIVERS = [
  ["hire", "Extra hire"],
  ["tolls", "Canal tolls and fees"],
  ["boil_off", "Extra boil-off"],
  ["des_discount", "Europe's DES discount"],
  ["other", "Ports, carbon and financing"],
];

// The charter rate at which a route stops paying; a route that does not pay even with the ship paid for has none.
export const closesAbove = (hStar) => (hStar > 0 ? int(hStar) : "shut");

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
    hstar[id] = closesAbove(result.routes[id].breakeven_hire);
  }
  return table([{ label: "USD/MMBtu delivered east", value: (r) => r.label, head: true }, ...routes.map(col)], [...rows, total, days, hstar], { min: 520 });
}

export const methodLink = () => h("p", { class: "source" }, "Every parameter and its source is on the ", h("a", { href: "#/method" }, "Method"), " view.");

// The cargo model, as in src/arb/engine.py. tests/test_js_port.py holds the two together.
//
// One LNG cargo is loaded at Sabine Pass and sold in Northwest Europe (at TTF less the DES
// discount) or in Northeast Asia (at JKM) by one of three routes. Netbacks are in USD per
// MMBtu loaded. Hire runs for the round trip, and the ship boils off the same share of the
// loaded cargo on every day of it: that gas is its fuel, and it is simply not sold.

export const MMBTU_PER_MWH = 3.412142;
export const EUROPE = "europe";

export const eurMwhToUsdMmbtu = (eurMwh, usdPerEur) => (eurMwh * usdPerEur) / MMBTU_PER_MWH;
export const usdMmbtuToEurMwh = (usdMmbtu, usdPerEur) => (usdMmbtu * MMBTU_PER_MWH) / usdPerEur;

export function voyage(ship, route, portDays) {
  const sea = route.distance_nm / (ship.speed_kn * 24);
  const canal = (route.canal_days || 0) + (route.wait_days || 0);
  const laden = portDays.load + sea + canal + portDays.discharge;
  const ballast = sea + canal;
  const loaded = ship.capacity_m3 * ship.fill * ship.mmbtu_per_m3;
  const perDay = loaded * ship.boil_off;
  const roundTrip = laden + ballast;
  return {
    sea_days: sea,
    laden_days: laden,
    ballast_days: ballast,
    round_trip_days: roundTrip,
    loaded,
    boil_off_per_day: perDay,
    boil_off: perDay * roundTrip,
    delivered: loaded - perDay * roundTrip,
  };
}

export function carbonCost(v, carbon, portDays) {
  const tonnesPerDay = v.boil_off_per_day / carbon.mmbtu_per_t_lng;
  const atSea = v.round_trip_days - portDays.load - portDays.discharge;
  const days = carbon.voyage_share * atSea + carbon.berth_share * portDays.discharge;
  return carbon.eua_usd_t * carbon.phase_in * carbon.tco2e_per_t_lng * tonnesPerDay * days;
}

export function financingCost(v, finance, contract, henryHub) {
  const paid = contract.hh_multiple * henryHub * v.loaded;
  return (paid * (finance.rate + finance.spread) * v.laden_days) / finance.day_count;
}

export function priceRoute(inputs, routeId) {
  const route = inputs.routes[routeId];
  const v = voyage(inputs.ship, route, inputs.port_days);
  const toEurope = route.market === "nwe";
  const price = toEurope ? inputs.ttf + inputs.des_discount : inputs.jkm;
  const cost = {
    hire: inputs.hire * v.round_trip_days,
    ports: route.port_cost,
    tolls: (route.toll_laden || 0) + (route.toll_ballast || 0),
    carbon: toEurope ? carbonCost(v, inputs.carbon, inputs.port_days) : 0,
    financing: financingCost(v, inputs.finance, inputs.contract, inputs.henry_hub),
  };
  cost.total = cost.hire + cost.ports + cost.tolls + cost.carbon + cost.financing;
  return {
    ...v,
    market: route.market,
    open: route.open !== false,
    price,
    cost,
    netback: (price * v.delivered - cost.total) / v.loaded,
  };
}

// S*, its five drivers, H* and the arb of one route east against Europe.
export function breakeven(inputs, west, east) {
  const de = east.delivered;
  const dw = west.delivered;
  const extraDays = east.round_trip_days - west.round_trip_days;
  const cw = west.cost;
  const ce = east.cost;
  const drivers = {
    hire: (inputs.hire * extraDays) / de,
    tolls: (ce.tolls - cw.tolls) / de,
    boil_off: (west.price * (dw - de)) / de,
    des_discount: inputs.des_discount,
    other: (ce.ports - cw.ports + ce.carbon - cw.carbon + ce.financing - cw.financing) / de,
  };
  const sStar = drivers.hire + drivers.tolls + drivers.boil_off + drivers.des_discount + drivers.other;
  const noHire = ce.total - ce.hire - (cw.total - cw.hire);
  const margin = inputs.jkm * de - west.price * dw - noHire;
  return {
    breakeven_spread: sStar,
    drivers,
    spread_slope_per_usd_day: extraDays / de,
    breakeven_hire: extraDays ? margin / extraDays : NaN,
    arb: east.netback - west.netback,
  };
}

export function priceCargo(inputs) {
  const routes = {};
  for (const id of Object.keys(inputs.routes)) routes[id] = priceRoute(inputs, id);
  const west = routes[EUROPE];
  for (const r of Object.values(routes)) if (r.market === "nea") Object.assign(r, breakeven(inputs, west, r));
  const openIds = Object.keys(routes).filter((id) => routes[id].open);
  const eastOpen = openIds.filter((id) => routes[id].market === "nea");
  const best = openIds.reduce((a, b) => (routes[b].netback > routes[a].netback ? b : a));
  const bestEast = eastOpen.length
    ? eastOpen.reduce((a, b) => (routes[b].breakeven_spread < routes[a].breakeven_spread ? b : a))
    : null;
  const threshold = inputs.contract.hh_multiple * inputs.henry_hub;
  const margin = routes[best].netback - threshold;
  return {
    spread: inputs.jkm - inputs.ttf,
    routes,
    best,
    best_east: bestEast,
    lift: {
      best_netback: routes[best].netback,
      threshold,
      margin,
      margin_after_fee: margin - inputs.contract.fee,
      lifts: margin >= 0,
    },
  };
}

export const withChanges = (inputs, changes) => ({ ...inputs, ...changes });

export function withRoute(inputs, routeId, changes) {
  return { ...inputs, routes: { ...inputs.routes, [routeId]: { ...inputs.routes[routeId], ...changes } } };
}

// S* is linear in hire: [S* at zero hire, USD/MMBtu per USD a day].
export function breakevenLine(inputs, routeId) {
  const r = priceCargo(withChanges(inputs, { hire: 0 })).routes[routeId];
  return [r.breakeven_spread, r.spread_slope_per_usd_day];
}

// What a canal slot is worth against the long way round: the premium a ship can pay for its
// two transits, or the days it can wait at each, before the long way nets the same.
export function canalQuestion(inputs, canal = "panama", longWay = "cape") {
  const base = priceCargo(inputs).routes;
  const lead = base[canal].netback - base[longWay].netback;
  const wait0 = inputs.routes[canal].wait_days || 0;
  const oneMore = priceCargo(withRoute(inputs, canal, { wait_days: wait0 + 1 })).routes[canal].netback;
  const perWaitDay = base[canal].netback - oneMore;
  return {
    premium_usd: lead * base[canal].loaded,
    wait_days: lead / perWaitDay,
    cost_of_a_waiting_day_usd: perWaitDay * base[canal].loaded,
  };
}

// The cargo economics in the browser: the same arithmetic as
// src/lngarb/engine.py and src/lngarb/cases.py, line for line, so that
// tools/validate-engine.mjs can hold the two to 1e-9 on every output.
//
// Units: prices in USD per MMBtu, costs in USD, hire in USD per day, days in
// days, distances in nautical miles, speeds in knots, volumes in MMBtu.
// Objects crossing the data contract keep the Python names (snake_case).

export const HOURS_PER_DAY = 24.0;
export const DAYS_PER_YEAR_FOR_INTEREST = 365.0;
const MS_PER_DAY = 86400000;
// Percent per unit, and basis points per percent.
const PERCENT_PER_ONE = 100.0;
const BP_PER_PERCENT = 100.0;
// Rounding half up: the half a unit added before Math.floor.
const HALF_UP = 0.5;

// The route to Northwest Europe and the three to Northeast Asia.
export const WEST = "nwe_direct";
export const EAST = ["nea_panama", "nea_suez", "nea_cape"];

// --------------------------------------------------------------------------
// Volumes and days
// --------------------------------------------------------------------------

export function leg(distance_nm, canal_days = 0, wait_days = 0, sea_days = null) {
  return { distance_nm, canal_days, wait_days, sea_days };
}

export function voyage(vessel, laden, ballast, mmbtu_per_m3, flex_days = 0) {
  const q_load = vessel.capacity_m3 * vessel.fill * mmbtu_per_m3;
  const boil_off_per_day = q_load * vessel.boil_off_per_day;
  // Days at sea typed directly win over the distance over the speed.
  const seaDays = (l) => (l.sea_days != null ? l.sea_days : l.distance_nm / (vessel.speed_kn * HOURS_PER_DAY));
  const t_laden = seaDays(laden) + laden.canal_days + laden.wait_days
    + vessel.load_days + vessel.discharge_days + flex_days;
  const t_ballast = seaDays(ballast) + ballast.canal_days + ballast.wait_days;
  const t_total = t_laden + t_ballast;
  const gas_used = boil_off_per_day * t_total;
  return {
    vessel, laden, ballast, mmbtu_per_m3, flex_days,
    q_load, boil_off_per_day, seaDays, t_laden, t_ballast, t_total, gas_used,
    q_delivered: q_load - gas_used,
  };
}

// --------------------------------------------------------------------------
// The cost stack and the results
// --------------------------------------------------------------------------

export function costStack({ port = 0, canal_laden = 0, canal_ballast = 0, slot_premium = 0, ets = 0, financing = 0 } = {}) {
  const without_hire = port + canal_laden + canal_ballast + slot_premium + ets + financing;
  return { port, canal_laden, canal_ballast, slot_premium, ets, financing, without_hire };
}

export function voyageCost(hire_usd_day, v, costs) {
  return hire_usd_day * v.t_total + costs.without_hire;
}

export function netback(p_des, v, cost_usd) {
  return (p_des * v.q_delivered - cost_usd) / v.q_load;
}

export function conventionalNetback(p_des, p_ref, v, cost_usd) {
  const f_conv = (cost_usd + p_ref * v.gas_used) / v.q_delivered;
  return [f_conv, p_des - f_conv];
}

export function breakevenSpread(ttf, delta_nwe, west, cost_west, east, cost_east) {
  const qw = west.q_delivered;
  const qe = east.q_delivered;
  const boil_off = ttf * (qw / qe - 1);
  const regas = delta_nwe * qw / qe;
  const voyage_part = (cost_east - cost_west) / qe;
  const total = (ttf + delta_nwe) * qw / qe + (cost_east - cost_west) / qe - ttf;
  return { s_star: total, boil_off, regas, voyage: voyage_part };
}

export function breakevenHire(jkm, ttf, delta_nwe, west, costs_west, east, costs_east) {
  const days = east.t_total - west.t_total;
  if (days === 0) return NaN;
  return (jkm * east.q_delivered - (ttf + delta_nwe) * west.q_delivered
    - (costs_east.without_hire - costs_west.without_hire)) / days;
}

export function liftTest(best_netback, henry_hub, liquefaction_fee, hh_multiple) {
  const lift = best_netback - hh_multiple * henry_hub;
  return { lift_margin: lift, full_margin: lift - liquefaction_fee, cancel: lift < 0 };
}

export function etsCost({ eua_usd_per_t, phase_in, tco2_per_t_lng, mmbtu_per_t_lng, boil_off_mmbtu_per_day,
  laden_days, ballast_days, berth_days, voyage_share, berth_share }) {
  const weighted_days = voyage_share * (laden_days + ballast_days) + berth_share * berth_days;
  const tonnes_lng = boil_off_mmbtu_per_day * weighted_days / mmbtu_per_t_lng;
  return eua_usd_per_t * phase_in * tco2_per_t_lng * tonnes_lng;
}

export function financingCost({ fob_usd_per_mmbtu, q_load, rate_percent, spread_bp, days }) {
  const rate = (rate_percent + spread_bp / BP_PER_PERCENT) / PERCENT_PER_ONE;
  return fob_usd_per_mmbtu * q_load * rate * days / DAYS_PER_YEAR_FOR_INTEREST;
}

// Spark's freight assessment, as its note on negative rates works it through.
export function sparkChartererPayment({ hire_usd_day, laden_days, ballast_days, ballast_share_of_hire,
  ballast_share_of_fuel, ballast_fuel_usd, positioning_usd = 0 }) {
  const hire = laden_days * hire_usd_day;
  const bonus = ballast_days * hire_usd_day * ballast_share_of_hire + ballast_fuel_usd * ballast_share_of_fuel;
  return { hire, ballast_bonus: bonus, positioning: positioning_usd, charterer_payment: hire + bonus + positioning_usd };
}

export function sparkRate(charterer_payment, ballast_fuel_usd, duration_days) {
  return (charterer_payment - ballast_fuel_usd) / duration_days;
}

export function sparkRound(rate_usd_day, step) {
  const size = Math.floor(Math.abs(rate_usd_day) / step + HALF_UP) * step;
  return rate_usd_day < 0 ? -size : size;
}

// --------------------------------------------------------------------------
// One loading date, every line (lngarb.cases)
// --------------------------------------------------------------------------

// The steps from the Northwest Europe netback to a Northeast Asia one, in order.
export const WATERFALL_STEPS = ["spread", "boil_off", "regas", "hire", "canals", "slot_premium", "ports", "carbon", "financing"];

// The arb of one route east as steps from the Northwest Europe netback, USD/MMBtu
// loaded; the steps add up to the arb exactly (lngarb.cases.waterfall).
export function waterfall(inputs, west, east) {
  const q_load = west.q_load_mmbtu;
  const qw = west.q_delivered_mmbtu;
  const qe = east.q_delivered_mmbtu;
  const steps = {
    spread: (inputs.jkm - inputs.ttf) * qe / q_load,
    boil_off: -inputs.ttf * (qw - qe) / q_load,
    regas: -inputs.delta_nwe * qw / q_load,
    hire: -(east.hire_usd - west.hire_usd) / q_load,
    canals: -((east.canal_laden_usd + east.canal_ballast_usd) - (west.canal_laden_usd + west.canal_ballast_usd)) / q_load,
    slot_premium: -(east.slot_premium_usd - west.slot_premium_usd) / q_load,
    ports: -(east.port_usd - west.port_usd) / q_load,
    carbon: -(east.ets_usd - west.ets_usd) / q_load,
    financing: -(east.financing_usd - west.financing_usd) / q_load,
  };
  const out = { start: west.netback };
  for (const k of WATERFALL_STEPS) out[k] = steps[k];
  out.end = east.netback;
  return out;
}

function parseDay(iso) {
  const [y, m, d] = iso.split("-").map(Number);
  return Date.UTC(y, m - 1, d);
}

// The days between start and end, counted from the loading day, split by calendar year.
function yearDays(start, end, dayIso) {
  const day = parseDay(dayIso);
  const out = new Map();
  let t = start;
  while (t < end) {
    // A date plus a fractional number of days moves by whole days only.
    const when = new Date(day + Math.floor(t) * MS_PER_DAY);
    const year = when.getUTCFullYear();
    const nextYear = Math.round((Date.UTC(year + 1, 0, 1) - day) / MS_PER_DAY);
    const stop = Math.min(end, nextYear);
    out.set(year, (out.get(year) || 0) + (stop - t));
    t = stop;
  }
  return out;
}

function routeVoyage(inputs, route) {
  const laden = leg(route.distance_nm, route.canal_days, route.wait_days, route.laden_sea_days);
  const ballast = leg(
    route.ballast_distance_nm ?? route.distance_nm,
    route.ballast_canal_days ?? route.canal_days,
    route.ballast_wait_days ?? route.wait_days,
    route.ballast_sea_days,
  );
  return voyage(inputs.vessel, laden, ballast, inputs.mmbtu_per_m3, route.flex_days);
}

// Nothing surrendered costs nothing, whatever the price; a surrender at a
// price not read (null) is unknown. Flex days count as days of the laden voyage.
function ets(inputs, v, toEurope) {
  if (!toEurope) return 0;
  const price = inputs.eua_usd_t == null ? Number.NaN : inputs.eua_usd_t;
  const laden_sea = v.seaDays(v.laden) + v.laden.canal_days + v.laden.wait_days + v.flex_days;
  if (inputs.ets_by_year == null) {
    if (inputs.ets_phase === 0) return 0;
    return etsCost({
      eua_usd_per_t: price, phase_in: inputs.ets_phase, tco2_per_t_lng: inputs.tco2_per_t_lng,
      mmbtu_per_t_lng: inputs.mmbtu_per_t_lng, boil_off_mmbtu_per_day: v.boil_off_per_day,
      laden_days: laden_sea, ballast_days: v.t_ballast, berth_days: inputs.vessel.discharge_days,
      voyage_share: inputs.ets_voyage_share, berth_share: inputs.ets_berth_share,
    });
  }
  const load = inputs.vessel.load_days;
  const arrive = load + laden_sea;
  const leave = arrive + inputs.vessel.discharge_days;
  const back = leave + v.t_ballast;
  const stretches = [[load, arrive, inputs.ets_voyage_share], [arrive, leave, inputs.ets_berth_share],
    [leave, back, inputs.ets_voyage_share]];
  let weighted = 0;
  for (const [start, end, share] of stretches) {
    for (const [year, days] of yearDays(start, end, inputs.day)) {
      const [phase, factor] = inputs.ets_by_year[String(year)] || [0, 0];
      weighted += share * days * phase * factor;
    }
  }
  if (weighted === 0) return 0;
  const tonnes_per_day = v.boil_off_per_day / inputs.mmbtu_per_t_lng;
  return price * tonnes_per_day * weighted;
}

function costs(inputs, route, v, toEurope) {
  // Only the part of the price paid when the cargo is lifted is financed.
  const fob = inputs.hh_multiple * inputs.henry_hub;
  return costStack({
    port: toEurope ? inputs.port_west_usd : inputs.port_east_usd,
    canal_laden: route.canal_laden_usd,
    canal_ballast: route.canal_ballast_usd,
    slot_premium: route.slot_premium_usd,
    ets: ets(inputs, v, toEurope),
    financing: financingCost({
      fob_usd_per_mmbtu: fob, q_load: v.q_load, rate_percent: inputs.rate_percent,
      spread_bp: inputs.spread_bp, days: v.t_laden,
    }),
  });
}

function routeLines(inputs, routeId, toEurope) {
  const route = inputs.routes[routeId];
  const v = routeVoyage(inputs, route);
  const c = costs(inputs, route, v, toEurope);
  const hire = inputs.hire_usd_day * v.t_total;
  const total = voyageCost(inputs.hire_usd_day, v, c);
  const p_des = toEurope ? inputs.ttf + inputs.delta_nwe : inputs.jkm;
  const [f_conv, nb_conv] = conventionalNetback(p_des, p_des, v, total);
  return {
    route: routeId,
    open: route.open,
    why_closed: route.why_closed,
    distance_nm: route.distance_nm,
    days_laden: v.t_laden,
    days_ballast: v.t_ballast,
    days_total: v.t_total,
    q_load_mmbtu: v.q_load,
    gas_used_mmbtu: v.gas_used,
    q_delivered_mmbtu: v.q_delivered,
    hire_usd: hire,
    port_usd: c.port,
    canal_laden_usd: c.canal_laden,
    canal_ballast_usd: c.canal_ballast,
    slot_premium_usd: c.slot_premium,
    ets_usd: c.ets,
    financing_usd: c.financing,
    canal_note: route.canal_note,
    cost_without_hire_usd: c.without_hire,
    cost_usd: total,
    p_des,
    netback: netback(p_des, v, total),
    freight_conventional: f_conv,
    netback_conventional: nb_conv,
    _voyage: v,
    _costs: c,
  };
}

// The defaults of lngarb.cases.RouteInput and Inputs, so that an input object
// leaving out an optional field is priced as Python prices it.
const ROUTE_DEFAULTS = Object.freeze({
  open: true,
  why_closed: "",
  canal_laden_usd: 0,
  canal_ballast_usd: 0,
  canal_days: 0,
  wait_days: 0,
  slot_premium_usd: 0,
  canal_note: "",
  ballast_distance_nm: null,
  ballast_canal_days: null,
  ballast_wait_days: null,
  laden_sea_days: null,
  flex_days: 0,
  ballast_sea_days: null,
});
const INPUT_DEFAULTS = Object.freeze({
  eua_usd_t: 0,
  ets_phase: 0,
  tco2_per_t_lng: 0,
  ets_by_year: null,
  mmbtu_per_t_lng: 1,
  ets_voyage_share: 0.5,
  ets_berth_share: 1,
});

function withDefaults(given, defaults) {
  const out = { ...given };
  for (const [name, value] of Object.entries(defaults)) {
    if (out[name] === undefined) out[name] = value;
  }
  return out;
}

// The figures a JSON file writes as null where Python held NaN: missing, so
// NaN here, never the zero JavaScript's arithmetic would make of null. Null
// keeps its own meaning elsewhere: an allowance price not read, a ballast leg
// the laden leg's way, days at sea from the distance, no split by year.
const NUMBERS = Object.freeze(["mmbtu_per_m3", "jkm", "ttf", "delta_nwe", "hire_usd_day", "henry_hub",
  "hh_multiple", "liquefaction_fee", "port_west_usd", "port_east_usd", "rate_percent", "spread_bp",
  "ets_phase", "tco2_per_t_lng", "mmbtu_per_t_lng", "ets_voyage_share", "ets_berth_share"]);
const ROUTE_NUMBERS = Object.freeze(["distance_nm", "canal_laden_usd", "canal_ballast_usd", "canal_days",
  "wait_days", "slot_premium_usd", "flex_days"]);
const VESSEL_NUMBERS = Object.freeze(["capacity_m3", "fill", "boil_off_per_day", "speed_kn", "load_days",
  "discharge_days"]);

function nullsMissing(object, names) {
  for (const name of names) if (object[name] === null) object[name] = Number.NaN;
  return object;
}

/** The inputs with every optional field present, as the Python dataclasses
 *  would hold them. The caller's object is not changed. */
export function complete(inputs) {
  const out = nullsMissing(withDefaults(inputs, INPUT_DEFAULTS), NUMBERS);
  out.vessel = nullsMissing({ ...inputs.vessel }, VESSEL_NUMBERS);
  out.routes = {};
  for (const [name, route] of Object.entries(inputs.routes)) {
    out.routes[name] = nullsMissing(withDefaults(route, ROUTE_DEFAULTS), ROUTE_NUMBERS);
  }
  return out;
}

// Every line of one date. Closed routes are computed too, and flagged, never chosen.
export function evaluate(given) {
  const inputs = complete(given);
  const west = routeLines(inputs, WEST, true);
  const east = {};
  for (const r of EAST) if (r in inputs.routes) east[r] = routeLines(inputs, r, false);
  for (const lines of Object.values(east)) {
    lines.arb = lines.netback - west.netback;
    Object.assign(lines, breakevenSpread(inputs.ttf, inputs.delta_nwe, west._voyage, west.cost_usd,
      lines._voyage, lines.cost_usd));
    lines.h_star_usd_day = breakevenHire(inputs.jkm, inputs.ttf, inputs.delta_nwe, west._voyage, west._costs,
      lines._voyage, lines._costs);
    lines.waterfall = waterfall(inputs, west, lines);
  }
  const open = Object.entries(east).filter(([, l]) => l.open);
  let bestEast = null;
  for (const [r, l] of open) if (bestEast === null || l.netback > east[bestEast].netback) bestEast = r;
  let best = { destination: "NWE", route: WEST, netback: west.netback };
  for (const [r, l] of open) if (l.netback > best.netback) best = { destination: "NEA", route: r, netback: l.netback };
  const lift = liftTest(best.netback, inputs.henry_hub, inputs.liquefaction_fee, inputs.hh_multiple);
  for (const lines of [west, ...Object.values(east)]) {
    delete lines._voyage;
    delete lines._costs;
  }
  return {
    day: inputs.day,
    spread: inputs.jkm - inputs.ttf,
    west,
    east,
    best_route_east: bestEast,
    best_destination: best.destination,
    best_route: best.route,
    best_netback: best.netback,
    ...lift,
  };
}

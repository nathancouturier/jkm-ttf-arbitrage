/* model-calc.js
 *
 * The Model view's arithmetic, with no DOM, so it runs under plain node:
 * tools/validate-engine.mjs holds it to the Python on every preset.
 *
 *   applyEdits(preset, edits, model)   the engine's inputs: a preset's, with the
 *                                      figures the visitor typed laid over them
 *   emptyCargo(result)                 the routes on which no cargo is delivered
 *   compute(inputs)                    src/engine.js evaluate, the mirror proven
 *                                      to 1e-9 against lngarb.cases.evaluate
 *   verdictSegments(result, inputs, model)
 *                                      the landing sentence for those inputs,
 *                                      clause for clause lngarb.reader.verdict
 *
 * A missing or unusable figure is NaN in the inputs, never zero: the engine
 * carries it through and every output that depends on it comes out missing;
 * src/model.js names the input. Nothing here clamps quietly: a figure outside
 * the calculator's limits (model.json's limits), or one too large to be
 * finite, is refused with words. A set of inputs under which the ship burns
 * all its cargo is found by emptyCargo, and the page shows no netback for it.
 *
 * Numeric literals: none.
 */

import { evaluate, complete } from "./engine.js";

/** A deep copy of plain JSON. */
function copy(value) {
  return JSON.parse(JSON.stringify(value));
}

export function present(value) {
  return typeof value === "number" && Number.isFinite(value);
}

/* ---------------------------------------------------------- the edits --- */

/* Each edit is { key, value } where value is a number, or NaN or null for an
 * input left empty or not a number. Route edits name their route: { key,
 * route }. The keys:
 *   jkm, ttf (USD/MMBtu), ttf_eur_mwh, usd_per_eur, delta_nwe, henry_hub,
 *   liquefaction_fee, hire_usd_day, vessel (a key of model.vessels), speed_kn,
 *   boil_off_percent, fill_percent, load_days, discharge_days, port_west_usd,
 *   port_east_usd, eua_eur_t, ets_phase, ets_voyage_share, ets_berth_share,
 *   rate_percent, spread_bp, mmbtu_per_m3, mmbtu_per_t_lng,
 *   hh_multiple_percent
 *   per route: open (true or false), laden_sea_days, ballast_sea_days (null:
 *   an empty field, the days from the distance; NaN: missing), flex_days,
 *   ballast_route (a route id, or the route's own), canal_laden_usd,
 *   canal_ballast_usd, canal_days, wait_days, slot_premium_usd
 * lngarb.presets.apply_edits reads them the same way, step for step, and
 * tools/validate-engine.mjs holds the two together on model.json's checks.
 */

const SCALARS = Object.freeze(["jkm", "ttf", "delta_nwe", "henry_hub", "liquefaction_fee", "hire_usd_day",
  "port_west_usd", "port_east_usd", "rate_percent", "spread_bp", "mmbtu_per_m3", "mmbtu_per_t_lng",
  "ets_voyage_share", "ets_berth_share"]);
const ROUTE_NUMBERS = Object.freeze(["flex_days", "canal_days", "wait_days", "canal_laden_usd", "canal_ballast_usd",
  "slot_premium_usd"]);

/** Why a figure cannot be used, in words, or null. A missing figure (NaN) is
 *  not refused here: it is said elsewhere. A figure that is not finite is. */
export function refusal(key, value, limits) {
  if (typeof value !== "number" || Number.isNaN(value)) return null;
  if (!Number.isFinite(value)) return "is too large to use";
  const range = limits[key];
  if (range && (value < range[0] || value > range[1])) {
    return "must lie between " + range[0] + " and " + range[1];
  }
  return null;
}

function number(value) {
  return value === null || value === undefined ? Number.NaN : value;
}

/** The inputs for a preset with the visitor's edits laid over them. Returns
 *  { inputs, refused: [{ key, route, why }] }. A refused figure leaves the
 *  input missing (NaN), never the preset's figure in its place. */
export function applyEdits(preset, edits, model) {
  const inputs = complete(copy(preset.inputs));
  const units = model.units;
  const limits = model.limits || {};
  const refused = [];
  const usable = (edit, limitKey) => {
    const value = number(edit.value);
    const why = refusal(limitKey || edit.key, value, limits);
    if (why) {
      refused.push({ key: edit.key, route: edit.route || null, why });
      return Number.NaN;
    }
    return value;
  };

  // The ship first: a change of ship brings its own speed and boil-off, and
  // the canal tolls priced on its capacity, which typed figures then override.
  const vesselEdit = edits.find((edit) => edit.key === "vessel" && model.vessels[edit.value]);
  const ship = vesselEdit ? vesselEdit.value : preset.vessel_key;
  const tolls = (preset.route_tolls || {})[ship] || {};
  if (vesselEdit) {
    inputs.vessel = copy(model.vessels[ship]);
    for (const [routeId, route] of Object.entries(inputs.routes)) {
      if (!tolls[routeId]) continue;
      route.canal_laden_usd = number(tolls[routeId].canal_laden_usd);
      route.canal_ballast_usd = number(tolls[routeId].canal_ballast_usd);
    }
  }

  for (const edit of edits) {
    if (edit.route) continue;
    if (SCALARS.includes(edit.key)) inputs[edit.key] = usable(edit);
    else if (edit.key === "hh_multiple_percent") inputs.hh_multiple = usable(edit) / units.percent_per_one;
    else if (edit.key === "speed_kn") inputs.vessel.speed_kn = usable(edit);
    else if (edit.key === "boil_off_percent") inputs.vessel.boil_off_per_day = usable(edit) / units.percent_per_one;
    else if (edit.key === "fill_percent") inputs.vessel.fill = usable(edit) / units.percent_per_one;
    else if (edit.key === "load_days" || edit.key === "discharge_days") inputs.vessel[edit.key] = usable(edit);
    else if (edit.key === "ets_phase") {
      // A typed share applies to the whole voyage: it replaces the preset's
      // split by calendar year.
      inputs.ets_by_year = null;
      inputs.ets_phase = usable(edit);
    }
  }

  // Figures quoted in euros, converted at the exchange rate in force: the
  // preset's, or the one typed. An allowance price the preset does not hold
  // stays unread (null): it costs nothing while nothing is surrendered.
  const fxEdit = edits.find((edit) => edit.key === "usd_per_eur");
  const usdPerEur = fxEdit ? usable(fxEdit) : preset.usd_per_eur;
  let euaTyped = false;
  for (const edit of edits) {
    if (edit.key === "ttf_eur_mwh") inputs.ttf = usable(edit) * usdPerEur / units.mmbtu_per_mwh;
    if (edit.key === "eua_eur_t") {
      inputs.eua_usd_t = usable(edit) * usdPerEur;
      euaTyped = true;
    }
  }
  if (fxEdit && !euaTyped) inputs.eua_usd_t = present(preset.eua_eur_t) ? preset.eua_eur_t * usdPerEur : null;

  // Routes: what is typed for a route.
  for (const edit of edits) {
    if (!edit.route || !inputs.routes[edit.route] || edit.key === "ballast_route") continue;
    const route = inputs.routes[edit.route];
    if (edit.key === "open") {
      route.open = edit.value === true;
      if (!route.open && !route.why_closed) route.why_closed = "closed by hand in the calculator";
    } else if (edit.key === "laden_sea_days" || edit.key === "ballast_sea_days") {
      route[edit.key] = edit.value === null ? null : usable(edit, "sea_days");
    } else if (ROUTE_NUMBERS.includes(edit.key)) {
      route[edit.key] = usable(edit);
    }
  }

  // Then a ballast leg back by another route: that route's distance, canal
  // days and wait as they now stand, and the toll of a ballast transit alone
  // unless this route's ballast toll is typed; the ballast days at sea stay
  // this route's own, typed or from the distance. Back by a closed route, the
  // route closes.
  for (const edit of edits) {
    if (edit.key !== "ballast_route" || !edit.route || !inputs.routes[edit.route]) continue;
    const route = inputs.routes[edit.route];
    if (edit.value === edit.route || !inputs.routes[edit.value]) {
      route.ballast_distance_nm = null;
      route.ballast_canal_days = null;
      route.ballast_wait_days = null;
      continue;
    }
    const other = inputs.routes[edit.value];
    const typed = (key) => edits.some((e) => e.key === key && e.route === edit.route);
    route.ballast_distance_nm = other.distance_nm;
    route.ballast_canal_days = other.canal_days;
    route.ballast_wait_days = other.wait_days;
    if (!typed("canal_ballast_usd")) route.canal_ballast_usd = number((tolls[edit.value] || {}).canal_ballast_alone_usd);
    if (!other.open) {
      route.open = false;
      route.why_closed = "back by " + model.route_short[edit.value] + ", which is closed";
    }
  }
  return { inputs, refused };
}

/** The routes, west included, on which the ship would burn as much gas as it
 *  loads or more: no cargo is delivered, so no netback has a meaning there. */
export function emptyCargo(result) {
  const out = [];
  const lines = { nwe_direct: result.west, ...result.east };
  for (const [routeId, line] of Object.entries(lines)) {
    if (present(line.q_delivered_mmbtu) && line.q_delivered_mmbtu <= 0) out.push(routeId);
  }
  return out;
}

/** The engine's every line for these inputs. */
export function compute(inputs) {
  return evaluate(inputs);
}

/* ------------------------------------------------------- the sentence --- */

const T = (text) => ({ text });
function N(field, value, format, signed) {
  let number = present(value) ? value : null;
  if (number !== null && (format === "count" || format === "year")) number = Math.round(number);
  const out = { field, value: number, format };
  if (signed) out.signed = true;
  return out;
}
const W = (field, word) => ({ field, value: word, label: word });

const MONTHS = Object.freeze(["January", "February", "March", "April", "May", "June", "July", "August",
  "September", "October", "November", "December"]);

function D(field, iso) {
  const [y, m, d] = iso.split("-").map(Number);
  return { field, value: iso, label: String(d) + " " + MONTHS[m - 1] + " " + String(y) };
}

/** The contract's share of Henry Hub as a percent: a whole number as the
 *  landing sentence writes it, or with its decimals when one is typed. */
export function percentSegment(multiple, model, decimals) {
  const percent = multiple * model.units.percent_per_one;
  const whole = Math.round(percent) === Number(percent.toFixed(decimals.fill_percent));
  return N("hh_multiple_percent", percent, whole ? "count" : "fill_percent");
}

function regasPart(delta, model) {
  return delta > 0 ? model.part_words_premium : model.part_words.regas;
}

function cheapestOpen(result) {
  let best = null;
  for (const [route, lines] of Object.entries(result.east)) {
    if (lines.open && present(lines.s_star)) {
      if (best === null || lines.s_star < result.east[best].s_star) best = route;
    }
  }
  return best;
}

function dominantPart(lines) {
  let best = null;
  for (const name of ["boil_off", "regas", "voyage"]) {
    if (best === null || Math.abs(lines[name]) > Math.abs(lines[best])) best = name;
  }
  return best;
}

/** The landing sentence for these inputs, as lngarb.reader.verdict writes
 *  it with weekly=False. */
export function verdictSegments(result, inputs, model) {
  const names = model.route_names;
  const short = model.route_short;
  const west = result.west;
  const east = result.east;
  const segments = [
    T("A cargo loading at Sabine Pass on "), D("as_of", inputs.day),
    T(" nets "), N("best_netback", result.best_netback, "usd_mmbtu"),
    T(" $/MMBtu delivered to "), W("best_route_name", names[result.best_route]),
  ];
  if (result.best_destination === "NEA") {
    segments.push(T(", "), N("gap_to_gate", result.best_netback - west.netback, "usd_mmbtu"), T(" more than at Gate. "));
  } else if (result.best_route_east) {
    const other = result.best_route_east;
    segments.push(T(", "), N("gap_to_east", west.netback - east[other].netback, "usd_mmbtu"), T(" more than at "),
      W("best_east_name", names[other]), T(", the best open route east. "));
  } else {
    segments.push(T("; no route east is open to a US cargo. "));
  }
  const cheapest = cheapestOpen(result);
  const spread = result.spread;
  segments.push(T("JKM is "), N("spread", Math.abs(spread), "usd_mmbtu"), T(spread >= 0 ? " above TTF" : " below TTF"));
  if (cheapest) {
    const lines = east[cheapest];
    const part = dominantPart(lines);
    const words = part === "regas" ? regasPart(inputs.delta_nwe, model) : model.part_words[part];
    segments.push(
      T(", and the cheapest open route east, via "), W("cheapest_route", short[cheapest]),
      T(", breaks even at a spread of "), N("s_star", lines.s_star, "usd_mmbtu", true),
      T("; the largest part of that is "), W("dominant_part", words), T(", "),
      N("dominant_value", lines[part], "usd_mmbtu", true), T(". "),
    );
  } else {
    segments.push(T(". "));
  }
  const margin = result.lift_margin;
  const percent = percentSegment(inputs.hh_multiple, model, model.conventions.decimals);
  if (margin >= 0) {
    segments.push(T("The best destination clears "), percent, T(" percent of Henry Hub by "),
      N("lift_margin", margin, "usd_mmbtu"), T("; net of the liquefaction fee of "),
      N("liquefaction_fee", inputs.liquefaction_fee, "usd_mmbtu"), T(" as well, its margin is "),
      N("full_margin", result.full_margin, "usd_mmbtu", true), T("."));
  } else {
    segments.push(T("The best destination falls short of "), percent, T(" percent of Henry Hub by "),
      N("lift_margin", -margin, "usd_mmbtu"), T(", so a cargo would not be lifted."));
  }
  return segments;
}

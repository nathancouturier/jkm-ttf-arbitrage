/* model.js
 *
 * The Model view: the calculator. Presets built from the data of their dates,
 * every input editable, and every output recomputed in place by
 * src/engine.js, the mirror proven against the Python engine to 1e-9:
 * netbacks by route, the arb, S* and its parts, H*, the lift test, and the
 * conventional freight beside the exact netback. The landing sentence is
 * recomposed from the outputs clause for clause as the Now view's.
 *
 * WHAT IT COMPUTES WITH. Nothing of its own: src/model-calc.js lays the edits
 * over the preset's inputs and calls the engine. A field that still shows the
 * preset's figure, as text or as the same number written another way,
 * computes with the preset's stored figure, not the rounded text, so an
 * untouched preset is exactly the artifact's case. The figure on the screen is
 * what is priced, in the unit shown: TTF in EUR/MWh moves in dollars with the
 * exchange rate. The tolls on the screen follow the ship and the way back.
 *
 * MISSING AND REFUSED. A field left empty or holding something that is not a
 * number is a missing input, and so is a figure the data do not hold for the
 * preset's date: the engine carries it as NaN, every output that depends on
 * it says "no figure", and a sentence under the outputs table names it, route
 * cells included. A missing hire offers the three levels the analysis runs. A figure outside the calculator's limits, or too large
 * to be finite, is refused, with the limits, rather than clamped. Inputs
 * under which the ship burns all it loads give no netback, and say so.
 *
 * STATE. The preset is in the address, #/model?preset=october_2022. Edits are
 * not: they belong to this reading of the page, and "Put back the preset's
 * figures" returns to the address's state. An address naming no preset says
 * so and is rewritten to the preset shown.
 *
 * Numeric literals: none.
 */

import { el, clear, sentence, appendSegments, scrollTable } from "./dom.js";
import { formatNumber, formatCell, UNITS, MINUS_PROSE } from "./format.js";
import * as router from "./router.js";
import { applyEdits, compute, verdictSegments, emptyCargo, present, percentSegment } from "./model-calc.js";

export const artifacts = Object.freeze(["model"]);

const VIEW = "model";

/* What a field accepts as a number: an optional sign, digits with a point for
 * decimals, an optional exponent. A comma followed by groups of three digits
 * after a first group that is not zero groups thousands, as the site writes
 * them (300,000); any other single comma is a decimal mark (12,5 or 0,085).
 * The status under the field says how it was read. */
const NUMBER_TEXT = /^[+\-]?(\d+\.?\d*|\.\d+)([eE][+\-]?\d+)?$/;
const GROUPED_TEXT = /^[+\-]?[1-9]\d{0,2}(,\d{3})+(\.\d+)?$/;
const DECIMAL_COMMA_TEXT = /^[+\-]?\d*,\d+$/;

/* The scalar inputs, by group, in the order the form shows them. `read` takes
 * the preset's stored figure; `format` names the decimals of the text the
 * preset puts in the field; `source` the key of its source words; `signed` a
 * figure that can be negative, typed on a full keyboard since a phone's
 * decimal pad has no minus key. */
const GROUPS = Object.freeze([
  {
    name: "Prices",
    fields: [
      { key: "jkm", label: "JKM", unit: "usd_mmbtu", format: "usd_mmbtu", source: "jkm", read: (p) => p.inputs.jkm },
      { key: "ttf", label: "TTF", unit: "usd_mmbtu", format: "usd_mmbtu", source: "ttf", read: (p) => p.inputs.ttf, euro: true },
      { key: "usd_per_eur", label: "Dollars per euro", unit: "usd_per_eur", format: "usd_per_eur", source: "fx", read: (p) => p.usd_per_eur },
      { key: "delta_nwe", label: "Europe's DES spread to TTF", unit: "usd_mmbtu", format: "usd_mmbtu", source: "delta_nwe", read: (p) => p.inputs.delta_nwe, signed: true },
      { key: "henry_hub", label: "Henry Hub, the month's average", unit: "usd_mmbtu", format: "usd_mmbtu", source: "henry_hub", read: (p) => p.inputs.henry_hub },
      { key: "liquefaction_fee", label: "Liquefaction fee", unit: "usd_mmbtu", format: "usd_mmbtu", source: "liquefaction_fee", read: (p) => p.inputs.liquefaction_fee },
    ],
  },
  {
    name: "Charter",
    fields: [
      { key: "hire_usd_day", label: "Hire, round trip", unit: "usd_day", format: "usd_day", source: "hire", read: (p) => p.inputs.hire_usd_day, signed: true },
    ],
  },
  {
    name: "Ports, carbon and financing",
    fields: [
      { key: "port_west_usd", label: "Port costs, Sabine Pass and Gate", unit: "usd", format: "usd", source: "port_west_usd", read: (p) => p.inputs.port_west_usd },
      { key: "port_east_usd", label: "Port costs, Sabine Pass and Futtsu", unit: "usd", format: "usd", source: "port_east_usd", read: (p) => p.inputs.port_east_usd },
      { key: "eua_eur_t", label: "EU allowance", unit: "eur_t", format: "eur_t", source: "eua", read: (p) => p.eua_eur_t, onlyIfUsed: true },
      { key: "ets_phase", label: "Share of shipping emissions surrendered", unit: "share", format: "share", source: "ets_phase", read: (p) => p.inputs.ets_phase },
      { key: "ets_voyage_share", label: "Share of a voyage's emissions counted", unit: "share", format: "share", source: "ets_voyage_share", read: (p) => p.inputs.ets_voyage_share },
      { key: "ets_berth_share", label: "Share of emissions at berth counted", unit: "share", format: "share", source: "ets_berth_share", read: (p) => p.inputs.ets_berth_share },
      { key: "rate_percent", label: "Overnight rate", unit: "rate_percent", format: "rate_percent", source: "rate", read: (p) => p.inputs.rate_percent },
      { key: "spread_bp", label: "Funding spread over it", unit: "bp", format: "bp", source: "spread_bp", read: (p) => p.inputs.spread_bp },
    ],
  },
  {
    name: "Contract and conversions",
    fields: [
      { key: "hh_multiple_percent", label: "Contract price, share of Henry Hub", unit: "share_percent", format: "share_percent", source: "hh_multiple_percent", read: (p, model) => p.inputs.hh_multiple * model.units.percent_per_one },
      { key: "mmbtu_per_m3", label: "Energy of a cubic metre of LNG", unit: "mmbtu_per_m3", format: "mmbtu_per_m3", source: "mmbtu_per_m3", read: (p) => p.inputs.mmbtu_per_m3 },
      { key: "mmbtu_per_t_lng", label: "Energy of a tonne of LNG", unit: "mmbtu_per_t", format: "mmbtu_per_t", source: "mmbtu_per_t_lng", read: (p) => p.inputs.mmbtu_per_t_lng },
    ],
  },
]);

/* The ship's own inputs, which follow the carrier chosen, with their sources. */
const SHIP_FIELDS = Object.freeze([
  { key: "speed_kn", label: "Speed", unit: "knots", format: "knots", read: (vessel) => vessel.speed_kn },
  { key: "boil_off_percent", label: "Boil-off", unit: "percent_day", format: "boil_off_percent", read: (vessel, model) => vessel.boil_off_per_day * model.units.percent_per_one },
  { key: "fill_percent", label: "Cargo loaded, share of capacity", unit: "fill_percent", format: "fill_percent", read: (vessel, model) => vessel.fill * model.units.percent_per_one },
  { key: "load_days", label: "Days to load", unit: "days", format: "days", read: (vessel) => vessel.load_days },
  { key: "discharge_days", label: "Days to discharge", unit: "days", format: "days", read: (vessel) => vessel.discharge_days },
]);

/* The route table's inputs, per route. */
const ROUTE_FIELDS = Object.freeze([
  { key: "laden_sea_days", label: "Laden days at sea", format: "days" },
  { key: "ballast_sea_days", label: "Ballast days at sea", format: "days" },
  { key: "flex_days", label: "Flex days, laden", format: "days" },
  { key: "canal_laden_usd", label: "Canal toll laden, $", format: "usd" },
  { key: "canal_ballast_usd", label: "Canal toll ballast, $", format: "usd" },
  { key: "canal_days", label: "Canal days", format: "days" },
  { key: "wait_days", label: "Waiting days", format: "days" },
  { key: "slot_premium_usd", label: "Slot premium, $", format: "usd" },
]);

/* Outputs per route, in the order the table shows them. */
const OUTPUTS = Object.freeze([
  { key: "days_total", head: "Round trip, days", format: "days", from: (l) => l.days_total },
  { key: "netback", head: "Netback, $/MMBtu", format: "usd_mmbtu", from: (l) => l.netback },
  { key: "arb", head: "Over Gate", format: "usd_mmbtu", signed: true, from: (l) => l.arb },
  { key: "s_star", head: "S*", format: "usd_mmbtu", signed: true, from: (l) => l.s_star },
  { key: "boil_off", head: "S*, boil-off", format: "usd_mmbtu", signed: true, from: (l) => l.boil_off },
  { key: "regas", head: "S*, Europe's spread", format: "usd_mmbtu", signed: true, from: (l) => l.regas },
  { key: "voyage", head: "S*, voyage", format: "usd_mmbtu", signed: true, from: (l) => l.voyage },
  { key: "h_star", head: "H*, $/day", format: "usd_day", from: (l) => l.h_star_usd_day },
  { key: "freight_conventional", head: "Freight, conventional", format: "usd_mmbtu", from: (l) => l.freight_conventional },
  { key: "netback_conventional", head: "Netback, conventional", format: "usd_mmbtu", from: (l) => l.netback_conventional },
]);

/* The outputs that have no meaning for Gate, the reference itself. */
const EAST_ONLY = Object.freeze(["arb", "s_star", "boil_off", "regas", "voyage", "h_star"]);

const ROUTES = Object.freeze(["nwe_direct", "nea_panama", "nea_suez", "nea_cape"]);

/* The words for an input, by its key, for the sentences under the form. */
const KEY_WORDS = new Map([
  ...GROUPS.flatMap((group) => group.fields.map((field) => [field.key, field.label])),
  ...SHIP_FIELDS.map((field) => [field.key, field.label]),
  ...ROUTE_FIELDS.map((field) => [field.key, field.label.replace(/, \$$/, "")]),
  ["ttf_eur_mwh", "TTF"],
]);

let held = null;

/* -------------------------------------------------------------- reading --- */

/* The text a preset puts in a field: its stored figure at the artifact's
 * decimals, without grouping so it reads back as a number. Empty when missing. */
function fieldText(value, format, decimals) {
  if (!present(value)) return "";
  return formatNumber(value, format, decimals, { context: "table" }).replace(/,/g, "");
}

/* A field's text as a number: { state: "number" | "empty" | "text", value,
 * readAs }. readAs is the plain number a grouped or decimal comma text was
 * read as. */
function parseNumber(raw) {
  const text = raw.trim().replace(MINUS_PROSE, "-");
  if (text === "") return { state: "empty", value: Number.NaN };
  if (NUMBER_TEXT.test(text)) return { state: "number", value: Number(text) };
  let plain = null;
  if (GROUPED_TEXT.test(text)) plain = text.replace(/,/g, "");
  else if (DECIMAL_COMMA_TEXT.test(text)) plain = text.replace(",", ".");
  if (plain !== null && NUMBER_TEXT.test(plain)) return { state: "number", value: Number(plain), readAs: plain };
  return { state: "text", value: Number.NaN };
}

/* What a field holds: { state: "preset" | "number" | "empty" | "text", value }.
 * The preset's figure written another way (75.1 for 75.10) is the preset's. */
function readField(field) {
  const typed = field.input.value;
  const reading = parseNumber(typed);
  const shown = field.presetText === "" ? null : parseNumber(field.presetText);
  if (typed === field.presetText || (shown && reading.state === "number" && reading.value === shown.value)) {
    return { state: "preset", value: present(field.stored) ? field.stored : Number.NaN };
  }
  return reading;
}

function capitalised(words) {
  return words ? words.charAt(0).toUpperCase() + words.slice(1) : words;
}

function presetFrom(route, model) {
  const asked = route && route.params ? route.params.preset || "" : "";
  const found = model.presets.find((p) => p.id === asked);
  return { preset: found || model.presets[0], unknown: asked !== "" && !found ? asked : null };
}

/* ---------------------------------------------------------------- view --- */

export function render(root, data, route) {
  const model = data.model;
  const decimals = model.conventions.decimals;
  const { preset, unknown } = presetFrom(route, model);
  held = { model, decimals, root, preset, fields: [], routeFields: [], outputs: new Map() };

  const title = sentence("h1", model.title_segments, decimals, "view-title");
  title.id = "view-title";
  title.setAttribute("tabindex", "-1");
  root.appendChild(title);

  const presets = el("div", { class: "choice-row", attrs: { role: "group", "aria-label": "Presets" } });
  for (const option of model.presets) {
    const button = el("button", {
      class: "choice",
      text: option.label,
      attrs: { type: "button", "aria-pressed": option.id === preset.id ? "true" : "false", "data-preset": option.id },
    });
    button.addEventListener("click", () => {
      if (option.id !== held.preset.id) router.go(VIEW, { preset: option.id });
    });
    presets.appendChild(button);
  }
  root.appendChild(presets);
  if (unknown !== null) {
    root.appendChild(el("p", { class: "state-message", text: "The address names no preset called " + JSON.stringify(unknown) + ", so the " + preset.label.toLowerCase() + " is shown." }));
    router.replaceState(VIEW, { preset: preset.id });
  }
  for (const item of model.unavailable || []) {
    root.appendChild(el("p", { class: "state-message", text: "Not offered: " + item.label + ", since " + item.why + "." }));
  }
  root.appendChild(sentence("p", preset.lead_segments, decimals, "lead model-lead"));

  // The outputs first, so the answer sits above the inputs that move it. The
  // sentence is not a live region: it changes on every keystroke. A short
  // summary is announced when a field is left or a choice made.
  const verdict = el("p", { class: "model-verdict" });
  held.verdict = verdict;
  root.appendChild(verdict);
  held.announcer = document.getElementById("view-status");
  root.appendChild(outputsTable());
  held.notes = el("div", { class: "model-notes" });
  root.appendChild(held.notes);

  const form = el("form", { class: "model-form", attrs: { "aria-label": "Inputs", novalidate: "" } });
  form.addEventListener("submit", (event) => event.preventDefault());
  form.appendChild(groupFieldset(GROUPS[0]));
  form.appendChild(shipFieldset());
  for (const group of GROUPS.slice(1)) form.appendChild(groupFieldset(group));
  form.appendChild(routesFieldset());
  const reset = el("button", { class: "disclosure__button", text: "Put back the preset's figures", attrs: { type: "button" } });
  reset.addEventListener("click", () => {
    held.vessel.restore();
    for (const field of [...held.fields, ...held.routeFields]) field.restore();
    recompute();
    announce();
  });
  form.appendChild(el("div", { class: "block" }, [reset]));
  root.appendChild(form);

  recompute();
  return title;
}

/** The preset changed in the address: draw the view again for it, and keep
 *  the keyboard on the preset just chosen. */
export function update(root, route) {
  if (!held) return;
  clear(root);
  render(root, { model: held.model }, route);
  const pressed = root.querySelector('.choice[aria-pressed="true"]');
  if (pressed) pressed.focus();
  announce();
}

/* -------------------------------------------------------------- fields --- */

/* A labelled text field, with its status and the source of the preset's
 * figure under it, both read out with the field. */
function textField({ id, label, unitWords, stored, format, source, signed }) {
  const { decimals } = held;
  const attrs = { type: "text", autocomplete: "off", spellcheck: "false" };
  if (!signed) attrs.inputmode = "decimal";
  const input = el("input", { class: "model-input", id, attrs });
  const presetText = fieldText(stored, format, decimals);
  input.value = presetText;
  const labelText = el("span", { text: label + (unitWords ? ", " + unitWords : "") });
  const labelNode = el("label", { class: "model-label", attrs: { for: id } }, [labelText]);
  const status = el("span", { class: "model-field__status", id: id + "-status" });
  const described = [status.id];
  const children = [labelNode, input, status];
  let sourceNode = null;
  if (source) {
    sourceNode = el("span", { class: "model-field__source", id: id + "-source", text: capitalised(source) });
  } else if (!present(stored)) {
    sourceNode = el("span", { class: "model-field__source", id: id + "-source", text: "Missing for this date: the data hold no figure." });
  }
  if (sourceNode) {
    children.push(sourceNode);
    described.push(sourceNode.id);
  }
  input.setAttribute("aria-describedby", described.join(" "));
  const wrapper = el("div", { class: "model-field" }, children);
  const field = { input, presetText, stored, original: { presetText, stored }, status, wrapper, label, labelText, sourceNode };
  field.restore = () => {
    field.presetText = field.original.presetText;
    field.stored = field.original.stored;
    input.value = field.presetText;
  };
  input.addEventListener("input", recompute);
  input.addEventListener("change", announce);
  return field;
}

function groupFieldset(group) {
  const { preset, model } = held;
  const set = el("fieldset", { class: "model-group" }, [el("legend", { class: "block__heading", text: group.name })]);
  const grid = el("div", { class: "model-grid" });
  for (const spec of group.fields) {
    const stored = spec.read(preset, model);
    const source = spec.source ? preset.source_words[spec.source] || null : null;
    const field = textField({ id: "field-" + spec.key, label: spec.label, unitWords: UNITS[spec.unit] || "", stored, format: spec.format, source, signed: spec.signed === true });
    field.key = spec.key;
    field.onlyIfUsed = spec.onlyIfUsed === true;
    if (spec.euro) addEuroSwitch(field);
    if (spec.key === "hire_usd_day" && !present(stored) && model.hire_levels) addHireLevels(field);
    held.fields.push(field);
    grid.appendChild(field.wrapper);
  }
  set.appendChild(grid);
  return set;
}

/* Buttons that type one of the three hire levels the analysis runs into a
 * hire field the data leave empty. Nothing is typed until one is pressed. */
function addHireLevels(field) {
  const { model, decimals } = held;
  const levels = model.hire_levels;
  const row = el("div", { class: "choice-row model-levels", attrs: { role: "group", "aria-label": "Hire levels the analysis runs" } });
  for (const [name, words] of [["low", "Low"], ["central", "Central"], ["high", "High"]]) {
    const button = el("button", { class: "choice", text: words + ", " + formatNumber(levels[name], "usd_day", decimals) + " " + UNITS.usd_day, attrs: { type: "button" } });
    button.addEventListener("click", () => {
      field.input.value = fieldText(levels[name], "usd_day", decimals);
      recompute();
      announce();
    });
    row.appendChild(button);
  }
  field.wrapper.appendChild(row);
  field.wrapper.appendChild(el("span", { class: "model-field__source", text: capitalised(levels.words) + "." }));
}

/* TTF in $/MMBtu or EUR/MWh. The figure on the screen is what is priced, in
 * the unit shown: in EUR/MWh it is converted at the exchange rate in force,
 * so a new rate moves its dollars. A switch converts what is priced at the
 * rate in force and keeps the unrounded figure behind the text, so switching
 * back and forth changes nothing. */
function addEuroSwitch(field) {
  const { model, decimals } = held;
  const choice = el("select", { class: "model-select", attrs: { "aria-label": "TTF unit" } }, [
    el("option", { text: UNITS.usd_mmbtu, attrs: { value: "usd_mmbtu" } }),
    el("option", { text: UNITS.eur_mwh, attrs: { value: "eur_mwh" } }),
  ]);
  const presetShown = () => ({ unit: "usd_mmbtu", text: field.original.presetText, value: field.original.stored, fromPreset: true });
  field.shown = presetShown();
  field.euro = choice;
  choice.addEventListener("change", () => {
    if (!usableFx()) {
      choice.value = field.shown.unit;
      field.status.textContent = "The unit cannot change while the dollars per euro is missing or refused.";
      return;
    }
    const reading = ttfReading(field);
    const fx = currentFx();
    const fxIsPreset = fxUntouched();
    const fromEuro = field.shown.unit === "eur_mwh";
    let usd = Number.NaN;
    if (reading.state === "preset" && (!fromEuro || fxIsPreset)) usd = field.original.stored;
    else if (present(reading.value)) usd = fromEuro ? reading.value * fx / model.units.mmbtu_per_mwh : reading.value;
    const fromPreset = reading.state === "preset" && (!fromEuro || fxIsPreset);
    const toEuro = choice.value === "eur_mwh";
    if (!present(usd)) {
      field.shown = { unit: choice.value, text: field.input.value, value: Number.NaN, fromPreset: false };
    } else if (toEuro) {
      const value = usd * model.units.mmbtu_per_mwh / fx;
      field.shown = { unit: "eur_mwh", text: fieldText(value, "eur_mwh", decimals), value, fromPreset: fromPreset && fxIsPreset };
    } else {
      field.shown = { unit: "usd_mmbtu", text: fromPreset ? field.original.presetText : fieldText(usd, "usd_mmbtu", decimals), value: usd, fromPreset };
    }
    field.input.value = field.shown.text;
    field.labelText.textContent = field.label + ", " + UNITS[choice.value];
    recompute();
    announce();
  });
  field.restore = () => {
    choice.value = "usd_mmbtu";
    field.shown = presetShown();
    field.input.value = field.shown.text;
    field.labelText.textContent = field.label + ", " + UNITS.usd_mmbtu;
  };
  field.wrapper.insertBefore(choice, field.status);
}

/* What the TTF field holds, in the unit shown: the unrounded figure behind
 * the text while the text is unchanged. */
function ttfReading(field) {
  const shown = field.shown;
  const typed = parseNumber(field.input.value);
  const same = field.input.value === shown.text ||
    (shown.text !== "" && typed.state === "number" && typed.value === parseNumber(shown.text).value);
  if (same && present(shown.value)) return { state: shown.fromPreset ? "preset" : "number", value: shown.value };
  return typed;
}

function fxField() {
  return held.fields.find((f) => f.key === "usd_per_eur");
}

function currentFx() {
  const fx = fxField();
  return fx ? readField(fx).value : held.preset.usd_per_eur;
}

/* An exchange rate the page can convert at: present and within its limits. */
function usableFx() {
  const fx = currentFx();
  const range = (held.model.limits || {}).usd_per_eur;
  return present(fx) && fx > 0 && (!range || (fx >= range[0] && fx <= range[1]));
}

function fxUntouched() {
  const fx = fxField();
  return !fx || readField(fx).state === "preset";
}

/* The ship: either benchmark carrier; its speed, boil-off and tolls follow it. */
function shipFieldset() {
  const { model, preset } = held;
  const set = el("fieldset", { class: "model-group" }, [el("legend", { class: "block__heading", text: "The ship" })]);
  const choice = el("select", { class: "model-select", id: "field-vessel" });
  for (const [key, vessel] of Object.entries(model.vessels)) {
    choice.appendChild(el("option", { text: vessel.name, attrs: { value: key, selected: key === preset.vessel_key ? "" : null } }));
  }
  const presetKey = choice.value;
  held.vessel = { choice, presetKey };
  const carrierNote = el("span", { class: "model-field__source", id: "field-vessel-source", text: "The canal tolls in the route table follow the ship, priced on its capacity, unless typed." });
  choice.setAttribute("aria-describedby", carrierNote.id);
  const grid = el("div", { class: "model-grid" }, [
    el("div", { class: "model-field" }, [el("label", { class: "model-label", text: "Carrier", attrs: { for: "field-vessel" } }), choice, carrierNote]),
  ]);
  const sourcesOf = (key) => (model.vessel_sources || {})[key] || {};
  const shipFields = SHIP_FIELDS.map((spec) => {
    const field = textField({ id: "field-" + spec.key, label: spec.label, unitWords: UNITS[spec.unit] || "", stored: spec.read(preset.inputs.vessel, model), format: spec.format, source: sourcesOf(presetKey)[spec.key] || null });
    field.key = spec.key;
    field.spec = spec;
    held.fields.push(field);
    grid.appendChild(field.wrapper);
    return field;
  });
  // A change of carrier brings its own speed and boil-off: a field still
  // showing the last carrier's figure takes the new one.
  const follow = (key) => {
    const vessel = model.vessels[key];
    for (const field of shipFields) {
      const untouched = readField(field).state === "preset";
      field.stored = field.spec.read(vessel, model);
      field.presetText = fieldText(field.stored, field.spec.format, held.decimals);
      if (untouched) field.input.value = field.presetText;
      const source = sourcesOf(key)[field.spec.key];
      if (field.sourceNode && source) field.sourceNode.textContent = capitalised(source);
    }
  };
  choice.addEventListener("change", () => {
    follow(choice.value);
    refreshRouteDefaults();
    recompute();
    announce();
  });
  held.vessel.restore = () => {
    choice.value = presetKey;
    for (const field of shipFields) {
      const source = sourcesOf(presetKey)[field.spec.key];
      if (field.sourceNode && source) field.sourceNode.textContent = capitalised(source);
    }
  };
  set.appendChild(grid);
  return set;
}

/* The figure a route cell shows while untouched: the preset's, with the
 * tolls of the ship chosen, and back by another route the toll of a ballast
 * transit alone. model-calc.js applyEdits prices an untouched cell the same
 * way, so the screen and the outputs agree. */
function routeDefault(routeId, key, back) {
  const { preset } = held;
  const ship = held.vessel.choice.value;
  const tolls = (preset.route_tolls || {})[ship] || {};
  const own = preset.inputs.routes[routeId][key];
  if (key === "canal_ballast_usd" && back !== routeId) {
    const alone = (tolls[back] || {}).canal_ballast_alone_usd;
    return present(alone) ? alone : null;
  }
  if ((key === "canal_laden_usd" || key === "canal_ballast_usd") && ship !== preset.vessel_key && tolls[routeId]) {
    return present(tolls[routeId][key]) ? tolls[routeId][key] : null;
  }
  return own;
}

function backOf(routeId) {
  const field = held.routeFields.find((f) => f.kind === "back" && f.route === routeId);
  return field ? field.back.value : routeId;
}

function refreshRouteDefaults() {
  for (const field of held.routeFields) {
    if (field.kind !== "value" || (field.key !== "canal_laden_usd" && field.key !== "canal_ballast_usd")) continue;
    const untouched = readField(field).state === "preset";
    const value = routeDefault(field.route, field.key, backOf(field.route));
    field.stored = present(value) ? value : null;
    field.presetText = fieldText(field.stored, field.format, held.decimals);
    if (untouched) field.input.value = field.presetText;
  }
}

/* Every route: open, the way back, its days typed or computed, its canal. */
function routesFieldset() {
  const { model, preset, decimals } = held;
  const set = el("fieldset", { class: "model-group" }, [el("legend", { class: "block__heading", text: "Routes" })]);
  const head = el("tr", {}, [el("th", { text: "Route", attrs: { scope: "col" } }), el("th", { text: "Open", attrs: { scope: "col" } }),
    el("th", { text: "Back by", attrs: { scope: "col" } })]);
  for (const spec of ROUTE_FIELDS) head.appendChild(el("th", { text: spec.label, attrs: { scope: "col", "data-short": spec.label } }));
  const body = el("tbody");
  const changed = () => {
    refreshRouteDefaults();
    recompute();
    announce();
  };
  for (const routeId of ROUTES) {
    const stored = preset.inputs.routes[routeId];
    if (!stored) continue;
    const name = model.route_names[routeId];
    const row = el("tr", { attrs: { "data-route": routeId } }, [el("th", { text: name, attrs: { scope: "row" } })]);
    // Open: a checkbox for the routes east; Gate is always open.
    const openCell = el("td");
    if (routeId !== "nwe_direct") {
      const box = el("input", { class: "model-check__box", attrs: { type: "checkbox" } });
      box.checked = stored.open;
      box.addEventListener("change", changed);
      held.routeFields.push({ kind: "open", route: routeId, box, restore: () => { box.checked = stored.open; } });
      openCell.appendChild(el("label", { class: "model-check" }, [box, el("span", { class: "visually-hidden", text: name + " open" })]));
    } else {
      openCell.appendChild(document.createTextNode("always"));
    }
    row.appendChild(openCell);
    // Back by: the same route, or another route east.
    const backCell = el("td");
    if (routeId !== "nwe_direct") {
      const back = el("select", { class: "model-select", attrs: { "aria-label": name + ", back by" } });
      for (const other of ROUTES.filter((r) => r !== "nwe_direct" && preset.inputs.routes[r])) {
        back.appendChild(el("option", { text: other === routeId ? "the same way" : model.route_short[other], attrs: { value: other } }));
      }
      back.value = routeId;
      back.addEventListener("change", changed);
      held.routeFields.push({ kind: "back", route: routeId, back, restore: () => { back.value = routeId; } });
      backCell.appendChild(back);
    } else {
      backCell.appendChild(document.createTextNode("the same way"));
    }
    row.appendChild(backCell);
    for (const spec of ROUTE_FIELDS) {
      const value = stored[spec.key];
      const input = el("input", { class: "model-input model-input--cell", attrs: { type: "text", inputmode: "decimal", autocomplete: "off", "aria-label": name + ", " + spec.label } });
      const presetText = fieldText(present(value) ? value : null, spec.format, decimals);
      input.value = presetText;
      if (spec.key.endsWith("sea_days")) input.setAttribute("placeholder", "from distance");
      input.addEventListener("input", recompute);
      input.addEventListener("change", announce);
      const field = { kind: "value", route: routeId, key: spec.key, format: spec.format, input, presetText,
        stored: present(value) ? value : null, original: { presetText, stored: present(value) ? value : null } };
      field.restore = () => {
        field.presetText = field.original.presetText;
        field.stored = field.original.stored;
        input.value = field.presetText;
      };
      held.routeFields.push(field);
      row.appendChild(el("td", {}, [input]));
    }
    body.appendChild(row);
  }
  const table = el("table", { class: "table model-routes" }, [el("thead", {}, [head]), body]);
  set.appendChild(scrollTable(["Each route's legs. An empty days-at-sea field takes the days from the distance at the ship's speed. Back by another route, the ballast leg takes that route's distance, canal days and waiting days, and the toll of a ballast transit alone."], table));
  held.routeNotes = el("div", { class: "model-route-notes" });
  set.appendChild(held.routeNotes);
  if (preset.source_words.days) {
    const line = el("p", { class: "model-field__source", id: "model-days-source", text: "Days typed for this preset: " + preset.source_words.days + "." });
    set.appendChild(line);
    for (const field of held.routeFields) {
      if (field.kind === "value" && field.route === "nwe_direct" && (field.key.endsWith("sea_days") || field.key === "flex_days")) {
        field.input.setAttribute("aria-describedby", line.id);
      }
    }
  }
  return set;
}

/* The outputs table, built once and filled in place. */
function outputsTable() {
  const { model } = held;
  const head = el("tr", {}, [el("th", { text: "Destination and route", attrs: { scope: "col" } })]);
  for (const spec of OUTPUTS) head.appendChild(el("th", { class: "col-num", text: spec.head, attrs: { scope: "col", "data-short": spec.head } }));
  const body = el("tbody");
  for (const routeId of ROUTES) {
    const name = el("th", { attrs: { scope: "row" } }, [el("span", { text: model.route_names[routeId] })]);
    const row = el("tr", { attrs: { "data-route": routeId } }, [name]);
    const cells = new Map();
    for (const spec of OUTPUTS) {
      const cell = el("td", { class: "num", attrs: { "data-field": spec.key } });
      cells.set(spec.key, cell);
      row.appendChild(cell);
    }
    held.outputs.set(routeId, { row, name, cells });
    body.appendChild(row);
  }
  const lift = el("p", { class: "lead model-lift" });
  held.lift = lift;
  const table = el("table", { class: "table model-outputs" }, [el("thead", {}, [head]), body]);
  return el("div", { class: "block" }, [scrollTable(["What the inputs below give, route by route, per MMBtu loaded; S* and its parts are the spread of JKM over TTF at which the route pays as much as Gate."], table), lift]);
}

/* ------------------------------------------------------------ compute --- */

function collectEdits() {
  const edits = [];
  for (const field of held.fields) {
    if (field.key === "ttf") {
      const reading = ttfReading(field);
      const euro = field.shown.unit === "eur_mwh";
      if (reading.state === "preset" && (!euro || fxUntouched())) continue;
      edits.push({ key: euro ? "ttf_eur_mwh" : "ttf", value: reading.value });
      continue;
    }
    const reading = readField(field);
    if (reading.state === "preset") continue;
    edits.push({ key: field.key, value: reading.value });
  }
  if (held.vessel.choice.value !== held.vessel.presetKey) {
    edits.unshift({ key: "vessel", value: held.vessel.choice.value });
  }
  for (const field of held.routeFields) {
    if (field.kind === "open") {
      const stored = held.preset.inputs.routes[field.route].open;
      if (field.box.checked !== stored) edits.push({ key: "open", route: field.route, value: field.box.checked });
    } else if (field.kind === "back") {
      if (field.back.value !== field.route) edits.push({ key: "ballast_route", route: field.route, value: field.back.value });
    } else {
      const reading = readField(field);
      if (reading.state === "preset") continue;
      // An empty days-at-sea field means the days from the distance (null);
      // text there is a missing input (NaN), like anywhere else.
      if (field.key.endsWith("sea_days") && reading.state === "empty") {
        edits.push({ key: field.key, route: field.route, value: null });
        continue;
      }
      edits.push({ key: field.key, route: field.route, value: reading.value });
    }
  }
  return edits;
}

function compose() {
  const { model, preset } = held;
  const edits = collectEdits();
  const { inputs, refused } = applyEdits(preset, edits, model);
  const result = compute(inputs);
  const empty = emptyCargo(result);
  const complete = present(result.best_netback) && present(result.lift_margin) && present(result.full_margin) &&
    present(result.spread) && Object.values(result.east).every((lines) => !lines.open || present(lines.netback)) &&
    !empty.some((routeId) => routeId === "nwe_direct" || result.east[routeId].open);
  return { inputs, refused, result, empty, complete };
}

/** A short summary for a screen reader, once a field is left or a choice made. */
function announce() {
  if (!held) return;
  const { model, decimals } = held;
  const state = compose();
  const words = state.complete
    ? model.route_names[state.result.best_route] + " nets most, " + formatNumber(state.result.best_netback, "usd_mmbtu", decimals) + " " + UNITS.usd_mmbtu + "."
    : withheld(state);
  if (held.announcer) held.announcer.textContent = words;
}

/* Whether any emissions are surrendered under these inputs: a share above
 * zero, typed or in a year of the preset's split. */
function surrenders(inputs) {
  if (inputs.ets_by_year) return Object.values(inputs.ets_by_year).some(([phase]) => phase > 0);
  return !(inputs.ets_phase <= 0);
}

/* Why there is no sentence, in words: an input missing or refused, or, when
 * every input is there, no cargo delivered. */
function withheld(state) {
  const cause = withheldCause(state);
  return "No sentence while " + cause.words + (cause.lacking ? "; the inputs are named under the table." : ".");
}

/* The cause, in words: an input missing or refused, or, when every input is
 * there, no cargo delivered to Gate or by an open route east. */
function withheldCause(state) {
  const { model } = held;
  const empty = state.empty.filter((routeId) => routeId === "nwe_direct" || state.result.east[routeId].open);
  const lacking = state.refused.length > 0 || !present(state.result.best_netback) || !present(state.result.lift_margin) ||
    !present(state.result.full_margin) || !present(state.result.spread) ||
    Object.values(state.result.east).some((lines) => lines.open && !present(lines.netback) && !empty.includes(lines.route));
  if (lacking || !empty.length) return { lacking: true, words: "an input it needs is missing or refused" };
  return { lacking: false, words: "no cargo is delivered " + empty.map((routeId) => (routeId === "nwe_direct" ? "to Gate" : "via " + model.route_short[routeId])).join(" or ") };
}

function setInvalid(input, invalid) {
  if (invalid) input.setAttribute("aria-invalid", "true");
  else input.removeAttribute("aria-invalid");
}

function recompute() {
  const { model, decimals, preset } = held;
  const state = compose();
  const { inputs, refused, result, empty, complete } = state;

  // The sentence needs every figure it compares: while one is missing or
  // refused, or no cargo is delivered, it says so rather than comparing a
  // figure with nothing.
  clear(held.verdict);
  if (complete) appendSegments(held.verdict, verdictSegments(result, inputs, model), decimals);
  else held.verdict.textContent = withheld(state);

  for (const routeId of ROUTES) {
    const target = held.outputs.get(routeId);
    const lines = routeId === "nwe_direct" ? result.west : result.east[routeId];
    if (!lines) {
      target.row.hidden = true;
      continue;
    }
    target.row.hidden = false;
    const closed = routeId !== "nwe_direct" && !lines.open;
    const noCargo = empty.includes(routeId);
    const noGate = routeId !== "nwe_direct" && empty.includes("nwe_direct");
    target.name.textContent = model.route_names[routeId] + (closed ? ", closed" : "") + (complete && routeId === result.best_route ? ", best" : "");
    for (const spec of OUTPUTS) {
      const reference = routeId === "nwe_direct" && EAST_ONLY.includes(spec.key);
      const value = reference || (noCargo && spec.key !== "days_total") || (noGate && EAST_ONLY.includes(spec.key)) ? null : spec.from(lines);
      let text = present(value) ? formatCell(value, spec.format, decimals, spec.signed === true) : "no figure";
      if (reference) text = spec.key === "arb" ? "the reference" : "";
      const cell = target.cells.get(spec.key);
      if (cell.textContent !== text) cell.textContent = text;
      cell.classList.toggle("is-missing", !present(value) && text !== "");
      cell.classList.toggle("text-accent", complete && routeId === result.best_route && spec.key === "netback");
    }
  }

  // The lift test, in words, or why there is none.
  clear(held.lift);
  if (complete) {
    appendSegments(held.lift, [
      { text: "Lift test: the best netback less " },
      percentSegment(inputs.hh_multiple, model, decimals),
      { text: " percent of Henry Hub is " },
      { field: "lift_margin", value: result.lift_margin, format: "usd_mmbtu", signed: true },
      { text: " $/MMBtu, and " },
      { field: "full_margin", value: result.full_margin, format: "usd_mmbtu", signed: true },
      { text: " after the liquefaction fee; a cargo is lifted while the first is not below zero." },
    ], decimals);
  } else {
    held.lift.textContent = "Lift test: no figure while " + withheldCause(state).words + ".";
  }

  // What is missing, refused or read another way, in words, field by field
  // and under the outputs.
  const refusedHere = (key, route) => refused.find((item) => item.key === key && (item.route || null) === (route || null));
  const missing = [];
  for (const field of held.fields) {
    const reading = field.key === "ttf" ? ttfReading(field) : readField(field);
    const key = field.key === "ttf" && field.shown.unit === "eur_mwh" ? "ttf_eur_mwh" : field.key;
    const refusal = refusedHere(key, null);
    const absent = reading.state === "text" || reading.state === "empty" || (reading.state === "preset" && !present(field.stored));
    // An allowance price counts only where something is surrendered.
    const counts = absent && !(field.onlyIfUsed && !surrenders(inputs));
    let words = "";
    if (reading.state === "text") words = "Not a number: the input is missing until it is one.";
    else if (reading.state === "empty" && counts) words = "Empty: the input is missing.";
    else if (refusal) words = (reading.readAs ? "Read as " + reading.readAs + "; refused" : "Refused") + ": it " + refusal.why + ".";
    else if (reading.readAs) words = "Read as " + reading.readAs + ".";
    if (field.status.textContent !== words) field.status.textContent = words;
    setInvalid(field.input, counts || Boolean(refusal));
    if (counts) missing.push(field.label);
  }
  for (const field of held.routeFields) {
    if (field.kind !== "value") continue;
    const reading = readField(field);
    const name = model.route_names[field.route] + ", " + KEY_WORDS.get(field.key).toLowerCase();
    const absent = reading.state === "text" || (reading.state === "empty" && !field.key.endsWith("sea_days")) ||
      (reading.state === "preset" && !present(field.stored) && !field.key.endsWith("sea_days"));
    setInvalid(field.input, absent || Boolean(refusedHere(field.key, field.route)));
    if (absent) missing.push(name);
  }
  clear(held.notes);
  if (missing.length) {
    held.notes.appendChild(el("p", { class: "state-message", text: "Missing: " + missing.join("; ") + ". Every output that depends on them says no figure until they are given." }));
  }
  for (const item of refused) {
    const words = KEY_WORDS.get(item.key) || "this input";
    held.notes.appendChild(el("p", { class: "state-message", text: (item.route ? model.route_names[item.route] + ", " + words.toLowerCase() : words) + " " + item.why + "; it is treated as missing." }));
  }
  if (empty.length) {
    held.notes.appendChild(el("p", { class: "state-message", text: "At these inputs the ship burns as much gas as it loads, or more, " + empty.map((routeId) => (routeId === "nwe_direct" ? "to Gate" : "via " + model.route_short[routeId])).join(", ") + ": no cargo is delivered, so no netback is shown there." }));
  }

  // Which routes are closed, and why, beside the route table.
  clear(held.routeNotes);
  for (const routeId of ROUTES) {
    const lines = result.east[routeId];
    if (!lines) continue;
    const presetClosed = !preset.inputs.routes[routeId].open;
    const inData = presetClosed ? "closed in the data: " + (preset.closed_words[routeId] || preset.inputs.routes[routeId].why_closed) : "";
    let words = "";
    if (!lines.open && presetClosed && lines.why_closed === preset.inputs.routes[routeId].why_closed) words = capitalised(inData) + ".";
    else if (!lines.open) words = "Closed here: " + lines.why_closed + (presetClosed ? "; " + inData : "") + ".";
    else if (presetClosed) words = capitalised(inData) + "; opened here.";
    if (words) held.routeNotes.appendChild(el("p", { class: "model-field__source", text: model.route_names[routeId] + ". " + words }));
  }
}

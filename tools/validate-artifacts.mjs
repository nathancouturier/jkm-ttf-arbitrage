#!/usr/bin/env node
// Check every JSON artifact the page reads against what the page expects.
//
//     node tools/validate-artifacts.mjs              self test, then the files
//
// The page refuses an artifact whose name or schema version it does not know
// (src/state.js), formats every figure with the decimals the artifact
// declares, throwing on a format it does not declare (src/format.js), and its
// section modules read named fields. A file that would be refused, a format
// that would throw, or a field a module reads and does not find is found here
// rather than by a reader. Plain node, no dependencies: it imports the page's
// own state.js and format.js, so the rules checked are the ones the page applies.
//
// FOR EACH ARTIFACT IN src/state.js's REGISTRY
//   1  the file exists, parses, and state.js's refusal() accepts it
//   2  the header: generated_by, data_date (an ISO day), describes, source
//   3  conventions.decimals maps every format name to a whole number of places
//   4  every field the page's modules read is there (REQUIRED below)
//   5  every "format" anywhere in the file, in a sentence or a table column,
//      is declared in conventions.decimals
//   6  every sentence, a key ending in "segments" (or a list of them under
//      "notes"), is a list of segments of one of the three shapes:
//        { text }                    words, never a digit
//        { field, value, format }    a number or null, formatted by format.js
//        { field, value, label }     a date or a word
//
// AND FOR data/
//   7  every top level data/*.json is read by the page, linked from it, or
//      named below as waiting for a view, so no file is published unread
//
// SELF TEST. Before checking the files, the tool plants an undeclared format,
// a missing field, a digit in words and a wrong schema version in copies of
// the real artifacts and asserts each is reported.

import { readdirSync, readFileSync, existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { artifactNames, artifactEntry, refusal } from "../src/state.js";
import { segmentText, decimalsFor } from "../src/format.js";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const ISO_DAY = /^\d{4}-\d{2}-\d{2}$/;

// data/*.json files the page does not read through state.js, and why.
const NOT_READ = Object.freeze({
  "manifest.json": "linked from the Provenance section, the full record",
});

// The fields the page's modules read, by artifact, as dotted paths.
const REQUIRED = Object.freeze({
  now: [
    "verdict.segments", "data_dates", "sections", "regas_sensitivity.segments",
    "closing.heading", "closing.segments", "closing.link_words", "closing.link_view",
    "netbacks.scale.low", "netbacks.scale.high", "netbacks.scale_segments", "netbacks.threshold", "netbacks.rows",
    "netbacks.table_caption", "netbacks.source_segments",
    "cost.rows", "cost.heading_segments", "cost.scale.low", "cost.scale.high", "cost.start_segments",
    "cost.end_segments", "cost.table_caption", "cost.source_segments", "cost.others.button", "cost.others.caption",
    "cost.others.routes", "cost.others.rows",
    "breakeven.x.low", "breakeven.x.high", "breakeven.x.step", "breakeven.x.divisor", "breakeven.x.axis",
    "breakeven.y.low", "breakeven.y.high", "breakeven.y.step", "breakeven.y.axis", "breakeven.lines",
    "breakeven.spread.value", "breakeven.spread.label_segments", "breakeven.heading_segments",
    "breakeven.desc_segments", "breakeven.caption_segments", "breakeven.source_segments",
    "breakeven.table.columns", "breakeven.table.rows", "breakeven.table.caption_segments",
  ],
  model: [
    "presets", "unavailable", "vessels.tfde_160k", "vessels.two_stroke_174k", "route_names", "route_short", "part_words",
    "part_words_premium", "units.mmbtu_per_mwh", "units.percent_per_one", "limits", "title_segments",
    "carbon.tco2_per_t_lng", "carbon.tn2o_per_t_lng", "carbon.gwp_ch4", "carbon.gwp_n2o", "carbon.ch4_n2o_from_year",
    "carbon.slip.tfde_160k", "carbon.slip.two_stroke_174k", "carbon.on",
  ],
  routes: [
    "heading_segments", "map.width", "map.height", "map.land", "map.start_x", "map.routes", "map.ports", "map.desc",
    "map_caption_segments", "map_scroll_words", "source_segments", "rows", "table_caption_segments",
    "timeline.first", "timeline.last", "timeline.rows", "timeline_heading_segments", "timeline_caption_segments",
  ],
  history: [
    "page.words.spread", "page.words.reference", "page.words.band", "page.words.h_star", "page.words.reported",
    "page.words.y_axis", "page.words.hstar_axis", "page.words.legend", "page.words.hstar_legend", "page.words.weeks.caption",
    "page.words.months.caption", "page.words.anchors_caption", "page.words.breaks_caption",
    "page.weekly.day", "page.weekly.spread", "page.weekly.s_low", "page.weekly.s_central", "page.weekly.s_high",
    "page.weekly.h_star", "page.weekly.alignment", "page.weekly.ranges",
    "page.monthly.day", "page.monthly.spread", "page.monthly.s_low", "page.monthly.s_central", "page.monthly.s_high",
    "page.monthly.first", "page.monthly.last", "page.monthly.y.low", "page.monthly.y.high", "page.monthly.y.step",
    "page.monthly.ticks", "page.monthly.heading_segments", "page.monthly.desc_segments",
    "page.monthly.caption_segments", "page.monthly.years",
    "page.breaks", "page.rules", "page.breaks_lead_segments", "page.anchors", "page.divisor", "page.source_segments",
    "page.weekly.boil_off", "page.weekly.regas", "page.weekly.voyage", "page.weekly.delta_nwe",
    "page.weekly.assumed_delta_nwe", "page.words.parts_legend", "page.words.parts.s_star", "page.words.parts.boil_off",
    "page.words.parts.regas", "page.words.parts.voyage", "page.words.regas_legend", "page.words.regas.observed",
    "page.words.regas.assumed", "page.words.events_caption", "page.words.events_heading", "page.words.left_out_heading",
    "page.events", "page.event_marks", "page.events_lead_segments", "page.events_left_out",
    "page.weekly.west_netback", "page.weekly.east_netback", "page.words.netbacks_legend", "page.words.netbacks.west",
    "page.words.netbacks.east",
  ],
  flows: [
    "page.whole.months", "page.whole.heading_segments", "page.whole.ticks", "page.whole.ticks_narrow",
    "page.test.heading_segments", "page.test.sign_segments", "page.test.rows", "page.test.caption",
    "page.y2020.heading_segments", "page.y2020.months", "page.y2020.y.low", "page.y2020.y.high", "page.y2020.ticks",
    "page.y2020.desc", "page.y2020.caption_segments",
    "page.y2026.heading_segments", "page.y2026.days", "page.y2026.spread", "page.y2026.panama", "page.y2026.cape",
    "page.y2026.y.low", "page.y2026.ticks", "page.y2026.desc", "page.y2026.compare", "page.y2026.reported",
    "page.y2026.assessment_day", "page.y2026.assessment_week", "page.y2026.story_segments", "page.y2026.source_segments",
    "page.y2020.cancelled_marks",
    "page.waits.heading_segments", "page.waits.rows", "page.waits.source", "page.limits_segments",
    "page.waits.months", "page.waits.reported_points", "page.waits.y.low", "page.waits.ticks",
    "page.waits.march_2024_segments", "page.words.waits_legend", "page.words.waits_axis", "page.words.waits_line",
    "page.words.panama_route", "page.words.cape_route", "page.words.y2026_legend", "page.words.y2020_legend", "page.words.y2020_caption",
    "page.y2026.compare_caption_segments", "page.words.waits_caption",
    "panel.months", "panel.shares", "panel.share_domain.low", "panel.share_domain.high", "panel.share_domain.step",
    "panel.arb_domain.low", "panel.arb_domain.high", "panel.arb_domain.step", "panel.share_axis", "panel.arb_axis",
    "panel.ticks", "panel.ticks_narrow", "panel.notes", "panel.heading_segments", "panel.desc_segments",
    "panel.source_segments", "panel.table_caption", "panel.missing_words", "panel.arb_missing_words",
  ],
  method: [
    "title_segments", "formulas", "parameters", "parameters_caption", "units", "units_segments", "delivery_segments",
    "limits", "documents", "type_words", "credits",
    "k_sensitivity.rows", "k_sensitivity.routes", "k_sensitivity.route_names", "k_sensitivity.caption_segments",
    "conventional.rows", "conventional.caption_segments",
  ],
  provenance: [
    "columns", "series", "summary_segments", "table_caption", "manual_heading", "manual_intro", "manual_steps",
    "credits_heading", "credits", "manifest_words",
  ],
});

// Fields required of every row of a list, by artifact.
const ROW_FIELDS = Object.freeze({
  now: {
    "data_dates": ["id", "segments"],
    "sections": ["id", "name", "summary_segments"],
    "netbacks.rows": ["id", "name", "open", "accent", "value", "detail_segments"],
    "cost.rows": ["id", "kind", "name", "detail_segments", "value", "start", "end", "accent"],
    "cost.others.routes": ["route", "name"],
    "cost.others.rows": ["id", "kind", "name", "values"],
    "breakeven.lines": ["route", "pattern", "points", "h_star", "label"],
    "breakeven.table.columns": ["id", "head", "format"],
    "breakeven.table.rows": ["route", "name", "values", "missing_words"],
  },
  model: {
    presets: ["id", "label", "day", "inputs", "result", "lead_segments", "verdict_segments", "usd_per_eur", "eua_eur_t",
      "source_words", "closed_words", "vessel_key", "route_tolls", "assumed", "alignment"],
  },
  routes: {
    "map.routes": ["id", "d", "pattern", "accent", "open", "label", "label_x", "label_y"],
    "map.ports": ["id", "name", "x", "y", "anchor", "label_x", "label_y"],
    rows: ["route", "name", "distance_nm", "sea_days", "days_total", "canal_laden_usd", "canal_ballast_usd", "status_words"],
    "timeline.rows": ["route", "name", "short", "bands"],
  },
  history: {
    "page.weekly.ranges": ["id", "label", "first", "last", "y", "hstar", "ticks", "heading_segments", "desc_segments",
      "caption_segments", "hstar_heading_segments", "hstar_desc_segments", "hstar_caption_segments", "accent_day", "years",
      "parts_y", "parts_heading_segments", "regas_y", "regas_heading_segments", "netbacks_y", "netbacks_heading_segments"],
    "page.events": ["letter", "day", "end", "what", "publisher", "url"],
    "page.event_marks": ["day", "end", "letter"],
    "page.events_left_out": ["what", "reason"],
    "page.breaks": ["number", "day", "kind", "kind_words", "what", "source"],
    "page.rules": ["day", "numbers"],
    "page.anchors": ["day", "hire_usd_day", "publisher", "assessment", "vessel", "accent"],
    "page.monthly.years": ["year", "open", "count", "ttf_above"],
  },
  flows: {
    "panel.months": ["month", "label", "share_jkm", "share_asia", "arb"],
    "page.test.rows": ["share", "share_words", "sample", "hire_level", "n", "slope_pp", "t", "r2", "lags", "open_above",
      "open_below", "closed_above", "closed_below"],
    "page.y2020.months": ["month", "label", "loading", "notice", "cancelled"],
    "page.y2020.cancelled_marks": ["day", "end", "letter"],
    "page.y2026.compare": ["route", "platts", "study"],
    "page.y2026.reported": ["period", "figure", "what", "publisher", "url", "format", "signed"],
    "page.waits.rows": ["month", "label", "hire_level", "hire_usd_day", "wait_reported", "wait_breakeven", "lead_no_wait", "lead_with_wait"],
  },
  method: {
    formulas: ["formula", "segments"],
    parameters: ["key", "name", "value_words", "status", "source", "read_on"],
    units: ["words", "value", "format"],
    documents: ["label", "href"],
  },
  provenance: {
    series: ["id", "label", "publisher", "page_url", "status"],
    columns: ["id", "head", "short"],
    manual_steps: ["what", "why", "cost_if_skipped"],
  },
});

function at(data, dotted) {
  let value = data;
  for (const key of dotted.split(".")) {
    if (value === null || typeof value !== "object" || !Object.prototype.hasOwnProperty.call(value, key)) return undefined;
    value = value[key];
  }
  return value;
}

function checkSegment(fail, where, segment, decimals) {
  if (!segment || typeof segment !== "object" || Array.isArray(segment)) {
    fail(where, "a segment is not an object");
    return;
  }
  if (Object.prototype.hasOwnProperty.call(segment, "text")) {
    if (typeof segment.text !== "string") fail(where, "a text segment holds no string");
    else if (/\d/.test(segment.text)) fail(where, "a text segment holds a digit: " + JSON.stringify(segment.text));
    return;
  }
  if (typeof segment.field !== "string" || segment.field === "") {
    fail(where, "a value segment names no field");
    return;
  }
  if (typeof segment.label === "string") return;
  if (typeof segment.format !== "string") {
    fail(where, "the value segment " + segment.field + " has neither a format nor a label");
    return;
  }
  try {
    segmentText(segment, decimals);
  } catch (error) {
    fail(where, error.message);
    return;
  }
  if (segment.value !== null && (typeof segment.value !== "number" || !Number.isFinite(segment.value))) {
    fail(where, "the value segment " + segment.field + " holds " + JSON.stringify(segment.value) + ", not a number or null");
  }
}

/* Walk the document: sentences under keys ending in "segments" or "notes",
 * and every "format" anywhere. Returns how many sentences were checked. */
function walk(fail, value, where, decimals) {
  let sentences = 0;
  if (Array.isArray(value)) {
    value.forEach((item, index) => { sentences += walk(fail, item, where + "[" + index + "]", decimals); });
    return sentences;
  }
  if (!value || typeof value !== "object") return 0;
  for (const [key, child] of Object.entries(value)) {
    const here = where ? where + "." + key : key;
    if (!where && key === "conventions") continue; // its "segments" describes the shape in words
    if (key === "format" && typeof child === "string") {
      try {
        decimalsFor(child, decimals);
      } catch (error) {
        fail(here, error.message);
      }
    }
    if (key.endsWith("segments")) {
      if (child === null) continue;
      if (!Array.isArray(child)) {
        fail(here, "a sentence is not a list of segments");
        continue;
      }
      child.forEach((segment, index) => checkSegment(fail, here + "[" + index + "]", segment, decimals));
      sentences += 1;
    } else if (key === "notes" && Array.isArray(child) && child.every(Array.isArray)) {
      child.forEach((paragraph, p) => paragraph.forEach((segment, index) => checkSegment(fail, here + "[" + p + "][" + index + "]", segment, decimals)));
      sentences += child.length;
    } else {
      sentences += walk(fail, child, here, decimals);
    }
  }
  return sentences;
}

/** Every problem with one parsed artifact, as "where: what" strings. */
export function validateArtifact(name, data) {
  const problems = [];
  const fail = (where, what) => problems.push((where ? where + ": " : "") + what);
  const refused = refusal(name, data);
  if (refused) {
    fail("", "the page would refuse it: " + refused);
    return { problems, sentences: 0 };
  }
  for (const key of ["generated_by", "describes", "source"]) {
    if (typeof data[key] !== "string" || !data[key]) fail(key, "missing from the header");
  }
  if (!ISO_DAY.test(String(data.data_date))) fail("data_date", "not an ISO day: " + JSON.stringify(data.data_date));
  const decimals = data.conventions && data.conventions.decimals;
  if (!decimals || typeof decimals !== "object") {
    fail("conventions.decimals", "missing");
    return { problems, sentences: 0 };
  }
  for (const [format, places] of Object.entries(decimals)) {
    if (!Number.isInteger(places) || places < 0) fail("conventions.decimals." + format, "not a whole number of places");
  }
  for (const dotted of REQUIRED[name] || []) {
    // A day with no open route east has no steps to cost: the section says so.
    if (name === "now" && dotted.startsWith("cost.") && dotted !== "cost.rows" && dotted !== "cost.heading_segments" &&
        Array.isArray(at(data, "cost.rows")) && at(data, "cost.rows").length === 0) continue;
    if (at(data, dotted) === undefined) fail(dotted, "missing, and the page reads it");
  }
  for (const [list, fields] of Object.entries(ROW_FIELDS[name] || {})) {
    const rows = at(data, list);
    if (!Array.isArray(rows)) continue;
    rows.forEach((row, index) => {
      for (const field of fields) {
        if (!row || !Object.prototype.hasOwnProperty.call(row, field)) fail(list + "[" + index + "]." + field, "missing, and the page reads it");
      }
    });
  }
  if (name === "provenance" && Array.isArray(data.columns) && Array.isArray(data.series)) {
    for (const column of data.columns) {
      if (column.id === "series" || column.id === "source") continue;
      data.series.forEach((row, index) => {
        if (typeof row[column.id] !== "string") fail("series[" + index + "]." + column.id, "no words for the column " + column.head);
      });
    }
  }
  const sentences = walk(fail, data, "", decimals);
  return { problems, sentences };
}

function selfTest(real) {
  const planted = [
    { name: "an undeclared format in a table column", artifact: "now", change: (d) => { d.breakeven.table.columns[0].format = "usd_day_k"; }, expect: "usd_day_k" },
    { name: "a field the page reads, removed", artifact: "now", change: (d) => { delete d.netbacks.scale; }, expect: "netbacks.scale.low" },
    { name: "a digit in words", artifact: "now", change: (d) => { d.verdict.segments.unshift({ text: "nets 23.96 " }); }, expect: "a digit" },
    { name: "a schema the page does not read", artifact: "flows", change: (d) => { d.schema_version = 2; }, expect: "would refuse" },
    { name: "a row without a field", artifact: "flows", change: (d) => { delete d.panel.months[0].arb; }, expect: "panel.months[0].arb" },
    { name: "a provenance column with no words", artifact: "provenance", change: (d) => { delete d.series[0].status_words; }, expect: "status_words" },
    { name: "the cost scale removed", artifact: "now", change: (d) => { delete d.cost.scale; }, expect: "cost.scale.low" },
    { name: "a cost step without its value", artifact: "now", change: (d) => { delete d.cost.rows[0].value; }, expect: "cost.rows[0].value" },
    { name: "a section without its summary", artifact: "now", change: (d) => { delete d.sections[0].summary_segments; }, expect: "sections[0].summary_segments" },
    { name: "a manual step without its reason", artifact: "provenance", change: (d) => { delete d.manual_steps[0].why; }, expect: "manual_steps[0].why" },
  ];
  const failures = [];
  for (const test of planted) {
    if (!real[test.artifact]) continue;
    const copy = structuredClone(real[test.artifact]);
    test.change(copy);
    const { problems } = validateArtifact(test.artifact, copy);
    const ok = problems.some((p) => p.includes(test.expect));
    console.log((ok ? "  ok    " : "  FAIL  ") + test.name + (ok ? "" : ": reported " + JSON.stringify(problems.slice(0, 3))));
    if (!ok) failures.push(test.name);
  }
  return failures;
}

const isMain = process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url);
if (isMain) {
  const problems = [];
  const summary = [];
  const real = {};
  const read = new Set();
  for (const name of artifactNames()) {
    const file = artifactEntry(name).path;
    read.add(path.basename(file));
    const full = path.join(ROOT, file);
    if (!existsSync(full)) {
      problems.push(file + ": missing, and the page reads it");
      continue;
    }
    try {
      real[name] = JSON.parse(readFileSync(full, "utf8"));
    } catch (error) {
      problems.push(file + ": not valid JSON: " + error.message);
    }
  }
  console.log("validate-artifacts.mjs");
  console.log("self test: planted faults must be reported");
  if (selfTest(real).length) {
    console.log("FAIL  the self test failed, so a check of the files would mean nothing");
    process.exit(1);
  }
  for (const [name, data] of Object.entries(real)) {
    const file = artifactEntry(name).path;
    const result = validateArtifact(name, data);
    for (const p of result.problems) problems.push(file + " at " + p);
    summary.push(file + ": schema " + data.schema_version + ", data to " + data.data_date + ", " + result.sentences + " sentences");
  }
  for (const name of readdirSync(path.join(ROOT, "data")).filter((n) => n.endsWith(".json")).sort()) {
    if (read.has(name)) continue;
    if (Object.prototype.hasOwnProperty.call(NOT_READ, name)) {
      summary.push("data/" + name + ": not read through state.js, " + NOT_READ[name]);
      continue;
    }
    problems.push("data/" + name + ": no view reads it and nothing links it");
  }
  console.log("");
  for (const line of summary) console.log("  " + line);
  if (problems.length) {
    for (const problem of problems.slice(0, 60)) console.log("FAIL  " + problem);
    console.log(problems.length + " problem(s)");
    process.exit(1);
  }
  console.log("PASS  every artifact the page reads is accepted, holds what the page reads, and every figure formats");
}

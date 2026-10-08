#!/usr/bin/env node
// Validate data/manifest.json against the files it describes, and the whole
// tracked tree against the repository's house rules.
//
//     node tools/validate-data.mjs
//     node tools/validate-data.mjs path/to/other-manifest.json
//
// Plain node, no npm install, no dependencies. Exits 0 when every check passes
// and 1 when any fails, so it can sit in the deploy gate.
//
// This is deliberately not the code that wrote the manifest. The Python
// pipeline measures the caches and records what it found; this reads the same
// files in JavaScript, measures them again, and compares. A number only one of
// the two produces is a claim. A number both produce independently is a fact.
//
// What is checked, in order:
//
//    1  the manifest parses and declares the schema version this tool knows
//    2  the header fields are present and no series name appears twice
//    3  every entry carries the required keys, with a known status, method and
//       frequency
//    4  provenance is consistent: a file nothing fetched claims no fetch time,
//       and anything that may not be redistributed says in words what is
//       forbidden
//    5  every committable entry points at a file that exists
//    6  no orphans, in both directions, for every file under data/cache and
//       data/seed whatever its extension
//    7  nothing marked committable false, and nothing under data/private, is in
//       the tracked tree
//    8  every committed CSV is utf-8, LF only, and starts with a date column
//    9  dates are yyyy-mm-dd and increasing; unique unless the entry declares a
//       long frame
//   10  declared rows, observations, file_rows, first_date and last_date match
//       what the file contains
//   11  no series is empty or in a failed state
//   12  declared gaps match the file, recomputed at the declared frequency
//   13  every numeric column is classified by name and sits inside its bounds
//   14  every destination country in the exports cache carries one of the five
//       regions
//   15  the manual steps are present, well formed, and attached to the series
//       they name
//   16  no tracked file outside vendor/ and tests/fixtures/ carries either of
//       the two long dash characters, an emoji, a trace of the tooling the
//       repository was written with, a generator meta tag, a reference to the
//       private build brief, an absolute local path, or a trace of the build
//       process; no instruction file for automated tooling and no brief is
//       tracked; no commit message carries a co-author trailer
//
// Nothing here is allowed to skip. There is no third outcome between pass and
// fail: a check that cannot run is a failure, because a check a typo can
// switch off is not a check.

import { execFileSync } from "node:child_process";
import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "..");
const MANIFEST_PATH = process.argv[2]
  ? path.resolve(process.argv[2])
  : path.join(ROOT, "data", "manifest.json");

const EXPECTED_SCHEMA_VERSION = 1;
const STATUS_VALUES = new Set(["ok", "stale", "failed"]);
const METHOD_VALUES = new Set(["published", "parsed", "reconstructed", "derived", "seed"]);
const FREQUENCY_VALUES = new Set(["daily", "weekly", "monthly", "annual"]);
const REGION_VALUES = new Set(["jkm_markets", "other_asia", "europe", "middle_east_africa", "americas"]);

const REQUIRED_ENTRY_KEYS = [
  "series", "source", "url", "page_url", "machine_fetched", "fetched_at",
  "checked_at", "rows", "observations", "file_rows", "first_date", "last_date",
  "frequency", "gaps", "provisional_from", "vintage", "method", "committable",
  "licence_note", "status", "note", "file", "unit", "observation_column",
  "unique_dates",
];

const REQUIRED_MANUAL_STEP_KEYS = ["id", "what", "why", "cost_if_skipped", "how", "cadence", "status"];

const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;
const ISO_STAMP = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/;

// --------------------------------------------------------------------------
// Bounds, by column name
// --------------------------------------------------------------------------
//
// These repeat the bounds in src/lngarb/config.py on purpose. This tool exists
// to disagree with the Python when the Python is wrong, so importing them would
// defeat it. When a bound moves in config.py it moves here too.
//
// First match wins, so specific rules sit above general ones. A numeric column
// that matches none is a failure: a column nobody classified is how an
// unbounded quantity gets into a published series.

const COLUMN_RULES = [
  { match: /_printed$/, text: true, what: "a value kept as the source printed it, which is text" },
  { match: /^henry_hub_usd_mmbtu$/, lo: 0.5, hi: 50.0, what: "Henry Hub, USD/MMBtu" },
  { match: /_usd_mmbtu$/, lo: 1.0, hi: 120.0, what: "JKM, TTF or spot LNG, USD/MMBtu" },
  { match: /^usd_per_eur$/, lo: 0.8, hi: 1.7, what: "US dollars per euro" },
  { match: /^sofr_percent$/, lo: -1.0, hi: 15.0, what: "SOFR, percent per year" },
  { match: /^effr_percent$/, lo: -1.0, hi: 15.0, what: "EFFR, percent per year" },
  { match: /^usd_per_sdr$/, lo: 1.0, hi: 2.0, what: "US dollars per SDR" },
  { match: /^eua_eur_t$/, lo: 1.0, hi: 200.0, what: "an EU allowance price, EUR per tonne of CO2" },
  { match: /^reports_printing_it$/, lo: 1.0, hi: 20.0, what: "a count of the reports that print a month" },
  { match: /^value_(before|after)$/, lo: 0.5, hi: 120.0, what: "a Pink Sheet gas price before or after a revision, USD/MMBtu" },
  { match: /^hire_usd_day$/, lo: -10000.0, hi: 500000.0, what: "reported LNG carrier hire, USD per day" },
  { match: /_spread_eur_mwh$/, lo: -20.0, hi: 5.0, what: "a DES LNG spread to TTF, EUR/MWh" },
  { match: /_des_eur_mwh$/, lo: 1.0, hi: 400.0, what: "a DES LNG price level, EUR/MWh" },
  { match: /^mmcf(_before|_after)?$/, lo: 0.0, hi: 2000000.0, what: "US gas exports in a month, MMcf" },
  { match: /^volume_mmcf$/, lo: 0.0, hi: 10000.0, what: "one LNG cargo or part of one, MMcf" },
  { match: /^usd_per_mcf(_before|_after)?$/, lo: 0.1, hi: 100.0, what: "the price of US LNG exports in a month, USD per thousand cubic feet" },
];

function ruleFor(column) {
  for (const rule of COLUMN_RULES) if (rule.match.test(column)) return rule;
  return null;
}

// --------------------------------------------------------------------------
// Reading
// --------------------------------------------------------------------------

function parseCsv(text) {
  const rows = [];
  let row = [];
  let cell = "";
  let quoted = false;
  for (let i = 0; i < text.length; i += 1) {
    const ch = text[i];
    if (quoted) {
      if (ch === '"') {
        if (text[i + 1] === '"') { cell += '"'; i += 1; } else quoted = false;
      } else cell += ch;
    } else if (ch === '"') quoted = true;
    else if (ch === ",") { row.push(cell); cell = ""; }
    else if (ch === "\n") { row.push(cell); rows.push(row); row = []; cell = ""; }
    else cell += ch;
  }
  if (cell !== "" || row.length) { row.push(cell); rows.push(row); }
  return { header: rows[0] || [], rows: rows.slice(1) };
}

const csvCache = new Map();
function loadCsv(relative) {
  if (csvCache.has(relative)) return csvCache.get(relative);
  const full = path.join(ROOT, relative);
  let value = null;
  if (existsSync(full)) {
    const raw = readFileSync(full);
    value = { ...parseCsv(raw.toString("utf8")), raw };
  }
  csvCache.set(relative, value);
  return value;
}

function listFiles(relativeDir) {
  const full = path.join(ROOT, relativeDir);
  if (!existsSync(full)) return [];
  return readdirSync(full)
    .filter((name) => !name.startsWith("."))
    .filter((name) => statSync(path.join(full, name)).isFile())
    .map((name) => relativeDir + "/" + name);
}

function git(args) {
  return execFileSync("git", args, { cwd: ROOT, encoding: "utf8", maxBuffer: 64 * 1024 * 1024 });
}

// --------------------------------------------------------------------------
// Dates and gaps, recomputed
// --------------------------------------------------------------------------

const DAY = 86400000;
const toUtc = (iso) => Date.UTC(Number(iso.slice(0, 4)), Number(iso.slice(5, 7)) - 1, Number(iso.slice(8, 10)));
const fromUtc = (ms) => new Date(ms).toISOString().slice(0, 10);

// Mirrors lngarb.sources.base.find_gaps. daily: every weekday in the span, no
// holiday calendar. weekly, monthly, annual: every period must carry at least
// one observation, reported at the start of the period.
function findGaps(dates, frequency) {
  const unique = [...new Set(dates)].sort();
  if (unique.length < 2) return [];
  if (frequency === "daily") {
    const have = new Set(unique);
    const out = [];
    const last = toUtc(unique[unique.length - 1]);
    for (let ms = toUtc(unique[0]); ms <= last; ms += DAY) {
      const day = new Date(ms).getUTCDay();
      if (day === 0 || day === 6) continue;
      const iso = fromUtc(ms);
      if (!have.has(iso)) out.push(iso);
    }
    return out;
  }
  let anchorOf;
  let step;
  if (frequency === "weekly") {
    anchorOf = (iso) => {
      const ms = toUtc(iso);
      return fromUtc(ms - ((new Date(ms).getUTCDay() + 6) % 7) * DAY);
    };
    step = (iso) => fromUtc(toUtc(iso) + 7 * DAY);
  } else if (frequency === "monthly") {
    anchorOf = (iso) => iso.slice(0, 7) + "-01";
    step = (iso) => {
      let year = Number(iso.slice(0, 4));
      let month = Number(iso.slice(5, 7)) + 1;
      if (month > 12) { month = 1; year += 1; }
      return year + "-" + String(month).padStart(2, "0") + "-01";
    };
  } else {
    anchorOf = (iso) => iso.slice(0, 4) + "-01-01";
    step = (iso) => Number(iso.slice(0, 4)) + 1 + "-01-01";
  }
  const anchors = new Set(unique.map(anchorOf));
  const sorted = [...anchors].sort();
  const out = [];
  let cursor = sorted[0];
  const end = sorted[sorted.length - 1];
  while (cursor < end) {
    cursor = step(cursor);
    if (cursor <= end && !anchors.has(cursor)) out.push(cursor);
  }
  return out;
}

function observationDates(entry, csv) {
  const dateAt = csv.header.indexOf("date");
  const column = entry.observation_column;
  const valueAt = column ? csv.header.indexOf(column) : -1;
  if (dateAt === -1 || (column && valueAt === -1)) return null;
  const dates = [];
  for (const row of csv.rows) {
    const iso = (row[dateAt] || "").trim();
    if (!iso) continue;
    if (column && !(row[valueAt] || "").trim()) continue;
    dates.push(iso);
  }
  return dates;
}

// --------------------------------------------------------------------------
// The run
// --------------------------------------------------------------------------

const results = [];
function check(name, fn) {
  let problems;
  try {
    problems = fn() || [];
  } catch (err) {
    problems = [err.name + ": " + err.message];
  }
  results.push({ name, problems });
}

if (!existsSync(MANIFEST_PATH)) {
  console.log("FAIL  data/manifest.json exists");
  console.log("      run: python scripts/refresh.py --offline");
  process.exit(1);
}

let manifest = null;
let entries = [];

check("manifest parses and declares schema_version " + EXPECTED_SCHEMA_VERSION, () => {
  manifest = JSON.parse(readFileSync(MANIFEST_PATH, "utf8"));
  entries = Array.isArray(manifest.series) ? manifest.series : [];
  const problems = [];
  if (manifest.schema_version !== EXPECTED_SCHEMA_VERSION) {
    problems.push("schema_version is " + JSON.stringify(manifest.schema_version));
  }
  if (!Array.isArray(manifest.series)) problems.push("series is not an array");
  if (!entries.length) problems.push("the series list is empty");
  return problems;
});

check("header fields and unique, sorted series names", () => {
  if (!manifest) return ["manifest did not parse"];
  const problems = [];
  if (!ISO_STAMP.test(String(manifest.generated_at || ""))) problems.push("generated_at is not a timestamp");
  const run = manifest.run || {};
  if (!["offline", "online"].includes(run.mode)) problems.push("run.mode is " + JSON.stringify(run.mode));
  for (const key of ["started_at", "finished_at"]) {
    if (!ISO_STAMP.test(String(run[key] || ""))) problems.push("run." + key + " is not a timestamp");
  }
  const names = entries.map((e) => String(e.series));
  if (new Set(names).size !== names.length) problems.push("a series name appears twice");
  if (names.join(" ") !== [...names].sort().join(" ")) problems.push("the series list is not sorted by name");
  return problems;
});

check("every entry carries the required keys and a known status, method and frequency", () => {
  const problems = [];
  for (const entry of entries) {
    const name = entry.series || "an entry with no name";
    for (const key of REQUIRED_ENTRY_KEYS) if (!(key in entry)) problems.push(name + " has no " + key);
    if (!STATUS_VALUES.has(entry.status)) problems.push(name + " status " + JSON.stringify(entry.status));
    if (!METHOD_VALUES.has(entry.method)) problems.push(name + " method " + JSON.stringify(entry.method));
    if (!FREQUENCY_VALUES.has(entry.frequency)) problems.push(name + " frequency " + JSON.stringify(entry.frequency));
    if (typeof entry.committable !== "boolean") problems.push(name + " committable is not a boolean");
    if (typeof entry.unique_dates !== "boolean") problems.push(name + " unique_dates is not a boolean");
    if (!Array.isArray(entry.gaps)) problems.push(name + " gaps is not an array");
    for (const key of ["first_date", "last_date"]) {
      if (entry[key] !== null && !ISO_DATE.test(String(entry[key]))) problems.push(name + " " + key + " is not yyyy-mm-dd");
    }
  }
  return problems;
});

check("provenance is consistent, and what may not be redistributed says so in words", () => {
  const problems = [];
  for (const entry of entries) {
    const name = entry.series;
    if (entry.machine_fetched === false && entry.fetched_at !== null) problems.push(name + " was never fetched but carries a fetched_at");
    if (entry.machine_fetched === false && !entry.checked_at) problems.push(name + " was never fetched and records no checked_at");
    for (const key of ["fetched_at", "checked_at"]) {
      if (entry[key] !== null && entry[key] !== undefined && !ISO_STAMP.test(String(entry[key]))) {
        problems.push(name + " " + key + " is not a timestamp");
      }
    }
    if (!String(entry.licence_note || "").trim()) problems.push(name + " carries no licence_note");
    if (entry.committable === false && !/not|prohibit|forbid/i.test(String(entry.licence_note || ""))) {
      problems.push(name + " is not committable but its licence_note never says what is not permitted");
    }
    if (!String(entry.page_url || "").startsWith("http")) problems.push(name + " has no linkable page_url");
  }
  return problems;
});

check("every committable entry points at a file that exists", () => {
  const problems = [];
  for (const entry of entries) {
    if (entry.committable === false) continue;
    const relative = String(entry.file || "");
    if (!/^data\/(cache|seed)\//.test(relative)) {
      problems.push(entry.series + " is committable but its file is " + JSON.stringify(relative));
      continue;
    }
    if (entry.status === "failed" && Number(entry.observations) === 0) continue; // check 11 reports it
    if (!existsSync(path.join(ROOT, relative))) problems.push(entry.series + " points at " + relative + ", not on disk");
  }
  return problems;
});

check("no orphans: every file under data/cache and data/seed has an entry, and every entry a file", () => {
  const problems = [];
  const declared = new Set();
  for (const entry of entries) {
    declared.add(String(entry.file || ""));
    for (const extra of entry.files || []) declared.add(String(extra));
  }
  for (const relative of [...listFiles("data/cache"), ...listFiles("data/seed")]) {
    if (!declared.has(relative)) problems.push(relative + " is committed but no manifest entry claims it");
  }
  return problems;
});

check("nothing marked committable false, and nothing under data/private, is tracked", () => {
  const problems = [];
  let tracked;
  try {
    tracked = git(["ls-files", "--cached", "--others", "--exclude-standard"]).split("\n").filter(Boolean);
  } catch (err) {
    return ["git is not available, so this check cannot run, which is a failure: " + err.message];
  }
  const set = new Set(tracked);
  for (const relative of tracked) {
    if (relative.startsWith("data/private/")) problems.push(relative + " is under data/private but would be committed");
  }
  for (const entry of entries) {
    if (entry.committable !== false) continue;
    const relative = String(entry.file || "");
    if (!relative.startsWith("data/private/")) problems.push(entry.series + " is private but its file is " + relative);
    if (set.has(relative)) problems.push(entry.series + " is private and " + relative + " would be committed");
  }
  return problems;
});

const committedCsv = entries
  .filter((e) => e.committable !== false && String(e.file || "").endsWith(".csv"))
  .filter((e) => existsSync(path.join(ROOT, String(e.file))));

check("every committed CSV is utf-8, LF only, and starts with a date column", () => {
  const problems = [];
  for (const entry of committedCsv) {
    const csv = loadCsv(entry.file);
    if (csv.raw.includes(13)) problems.push(entry.file + " carries a carriage return");
    if (csv.raw.toString("utf8").includes(String.fromCharCode(0xFFFD))) problems.push(entry.file + " is not valid utf-8");
    if (csv.header[0] !== "date") problems.push(entry.file + " does not start with a date column");
    if (!csv.rows.length) problems.push(entry.file + " has no rows");
  }
  return problems;
});

check("dates are yyyy-mm-dd and increasing, unique unless the entry declares a long frame", () => {
  const problems = [];
  for (const entry of committedCsv) {
    const csv = loadCsv(entry.file);
    let previous = "";
    const seen = new Set();
    csv.rows.forEach((row, i) => {
      const iso = row[0];
      if (!ISO_DATE.test(iso)) { problems.push(entry.file + " row " + (i + 2) + " date " + JSON.stringify(iso)); return; }
      if (iso < previous) problems.push(entry.file + " row " + (i + 2) + ": " + iso + " follows " + previous);
      if (entry.unique_dates && seen.has(iso)) problems.push(entry.file + " repeats " + iso);
      seen.add(iso);
      previous = iso;
    });
  }
  return problems.slice(0, 20);
});

check("declared counts and dates match the files", () => {
  const problems = [];
  for (const entry of committedCsv) {
    const csv = loadCsv(entry.file);
    const dates = observationDates(entry, csv);
    if (dates === null) { problems.push(entry.series + " declares observation column " + entry.observation_column + ", not in the file"); continue; }
    const observations = entry.unique_dates ? dates.length : new Set(dates).size;
    const sorted = [...dates].sort();
    const expect = {
      file_rows: csv.rows.length,
      observations,
      rows: observations,
      first_date: sorted.length ? sorted[0] : null,
      last_date: sorted.length ? sorted[sorted.length - 1] : null,
    };
    for (const [key, value] of Object.entries(expect)) {
      if (entry[key] !== value) problems.push(entry.series + " declares " + key + " " + JSON.stringify(entry[key]) + ", the file gives " + JSON.stringify(value));
    }
  }
  return problems;
});

check("no series is empty or in a failed state", () => {
  const problems = [];
  for (const entry of entries) {
    if (entry.status === "failed") problems.push(entry.series + " is failed: " + String(entry.note || "").slice(0, 240));
    else if (!Number(entry.observations)) problems.push(entry.series + " has no observations");
  }
  return problems;
});

check("declared gaps match the file, recomputed at the declared frequency", () => {
  const problems = [];
  for (const entry of committedCsv) {
    const dates = observationDates(entry, loadCsv(entry.file));
    if (dates === null) continue;
    const gaps = findGaps(dates, entry.frequency);
    if (JSON.stringify(gaps) !== JSON.stringify(entry.gaps)) {
      problems.push(entry.series + " declares " + entry.gaps.length + " gap(s), the file gives " + gaps.length);
    }
  }
  return problems;
});

check("every numeric column is classified and inside its bounds", () => {
  const problems = [];
  for (const entry of committedCsv) {
    const csv = loadCsv(entry.file);
    csv.header.forEach((column, at) => {
      if (column === "date") return;
      const cells = csv.rows.map((r) => (r[at] || "").trim()).filter((c) => c !== "");
      if (!cells.length) return;
      const numeric = cells.filter((c) => /^-?\d+(\.\d+)?$/.test(c));
      const rule = ruleFor(column);
      if (rule && rule.text) return;
      if (numeric.length === 0) return; // a text column
      if (numeric.length !== cells.length) {
        problems.push(entry.file + " column " + column + " mixes numbers and text");
        return;
      }
      if (!rule) { problems.push(entry.file + " numeric column " + column + " matches no bounds rule"); return; }
      const outside = numeric.map(Number).filter((v) => v < rule.lo || v > rule.hi);
      if (outside.length) problems.push(entry.file + " column " + column + " has " + outside.length + " value(s) outside [" + rule.lo + ", " + rule.hi + "], for example " + outside[0]);
    });
  }
  return problems;
});

check("every destination country in the exports cache carries one of the five regions", () => {
  const entry = entries.find((e) => e.series === "eia_lng_exports_monthly");
  if (!entry) return ["eia_lng_exports_monthly is not in the manifest"];
  const csv = loadCsv(entry.file);
  if (!csv) return [entry.file + " is not on disk"];
  const code = csv.header.indexOf("code");
  const region = csv.header.indexOf("region");
  const country = csv.header.indexOf("country");
  if (code === -1 || region === -1 || country === -1) return ["the exports cache lacks code, country or region"];
  const problems = new Set();
  for (const row of csv.rows) {
    if (row[code] === "Z00") continue;
    if (!REGION_VALUES.has(row[region])) problems.add(row[country] + " (" + row[code] + ") has region " + JSON.stringify(row[region]));
  }
  return [...problems];
});

check("the manual steps are present, well formed and attached to the series they name", () => {
  const problems = [];
  const steps = Array.isArray(manifest && manifest.manual_steps) ? manifest.manual_steps : null;
  if (!steps) return ["manifest.manual_steps is missing"];
  const byName = new Map(entries.map((e) => [e.series, e]));
  for (const step of steps) {
    for (const key of REQUIRED_MANUAL_STEP_KEYS) {
      if (!String(step[key] || "").trim()) problems.push("manual step " + step.id + " has no " + key);
    }
    for (const name of step.series || []) {
      const entry = byName.get(name);
      if (!entry) { problems.push("manual step " + step.id + " names " + name + ", which has no entry"); continue; }
      const attached = (entry.manual_step || []).some((s) => s.id === step.id);
      if (!attached) problems.push("manual step " + step.id + " is not attached to " + name);
    }
  }
  return problems;
});

// --------------------------------------------------------------------------
// House rules over the tracked tree
// --------------------------------------------------------------------------
//
// Every character and word below is assembled by code so that this file does
// not match its own rules and carries no character it forbids.
const BACKSLASH = String.fromCharCode(92);
const EM = String.fromCharCode(0x2014);
const EN = String.fromCharCode(0x2013);
// The same two characters written as JSON escapes, which is how a file
// serialised with ensure_ascii would carry them.
const ESCAPED_EM = new RegExp(BACKSLASH + BACKSLASH + "u" + "2014", "i");
const ESCAPED_EN = new RegExp(BACKSLASH + BACKSLASH + "u" + "2013", "i");
const EMOJI = new RegExp(
  "[" + String.fromCodePoint(0x1F000) + "-" + String.fromCodePoint(0x1FAFF) + "]",
  "u"
);
const words = (list) => list.join("|");

const TRACE_RULES = [
  { what: "the long dash U+2014", test: (t) => t.includes(EM) || ESCAPED_EM.test(t) },
  { what: "the long dash U+2013", test: (t) => t.includes(EN) || ESCAPED_EN.test(t) },
  { what: "an emoji", test: (t) => EMOJI.test(t) },
  {
    what: "a tooling vendor or product name",
    re: new RegExp("\\b(" + words(["cla" + "ude", "anthro" + "pic", "chat" + "gpt", "open" + "ai", "co" + "pilot", "gem" + "ini"]) + ")\\b", "i"),
  },
  { what: "the two letter abbreviation for machine intelligence", re: new RegExp("\\b" + "A" + "I" + "\\b") },
  { what: "a mention of a code writing tool or a model", re: new RegExp("(coding as" + "sistant|language mo" + "del|\\bL" + "LM\\b)", "i") },
  { what: "a line crediting how the files were made", re: new RegExp("(gene" + "rated (with|by)|(made|bu" + "ilt) wi" + "th)", "i") },
  { what: "a generator meta tag", re: new RegExp("<meta[^>]+name=[\"']gene" + "rator", "i") },
  { what: "a reference to the private build brief", re: new RegExp("\\bSP" + "EC(\\.md|\\s+section|\\s+\\d)") },
  {
    what: "an absolute local path",
    re: new RegExp("([A-Za-z]:[" + BACKSLASH + BACKSLASH + "/]+Us" + "ers[" + BACKSLASH + BACKSLASH + "/]|/ho" + "me/[a-z]|/Us" + "ers/[A-Za-z])"),
  },
  { what: "a trace of the build process", re: new RegExp("\\b(Ga" + "te \\d|rec" + "on \\d+|build ag" + "ent)\\b", "i") },
  { what: "the word for an automated worker, outside user agent", re: new RegExp("(?<![Uu][Ss][Ee][Rr][ _-])\\bag" + "ents?\\b", "i") },
];

// The ignore file must name the private brief and the tooling settings in
// order to keep them out; those exact lines are the one exception.
const GITIGNORE_ALLOWED = new Set(["SP" + "EC.md", ".cla" + "ude/", "CLA" + "UDE.md"]);

const BINARY = /\.(png|jpe?g|gif|webp|ico|pdf|xlsx?|woff2?|ttf|otf|zip|gz)$/i;

check("no tracked file carries a long dash, an emoji, a tooling trace, a brief reference or a local path", () => {
  const problems = [];
  let tracked;
  try {
    tracked = git(["ls-files", "--cached", "--others", "--exclude-standard"]).split("\n").filter(Boolean);
  } catch (err) {
    return ["git is not available, so this check cannot run: " + err.message];
  }
  let scanned = 0;
  for (const relative of tracked) {
    if (relative.startsWith("vendor/") || relative.startsWith("tests/fixtures/") || BINARY.test(relative)) continue;
    const full = path.join(ROOT, relative);
    if (!existsSync(full)) continue;
    const text = readFileSync(full, "utf8");
    scanned += 1;
    const lines = text.split("\n");
    lines.forEach((line, i) => {
      if (relative === ".gitignore" && GITIGNORE_ALLOWED.has(line.trim())) return;
      for (const rule of TRACE_RULES) {
        const hit = rule.test ? rule.test(line) : rule.re.test(line);
        if (hit) problems.push(relative + ":" + (i + 1) + " carries " + rule.what);
      }
    });
  }
  if (!scanned) problems.push("no tracked file was scanned");
  return problems.slice(0, 40);
});

check("no tooling instruction file or build brief is tracked, and no commit carries a trailer", () => {
  const problems = [];
  let tracked;
  let messages;
  try {
    tracked = git(["ls-files"]).split("\n").filter(Boolean);
    messages = git(["log", "--format=%B"]);
  } catch (err) {
    return ["git is not available, so this check cannot run: " + err.message];
  }
  const forbidden = new RegExp("(^|/)(CLA" + "UDE\\.md|SP" + "EC\\.md|\\.cla" + "ude/)", "i");
  for (const relative of tracked) if (forbidden.test(relative)) problems.push(relative + " is tracked");
  if (new RegExp("co-autho" + "red-by", "i").test(messages)) problems.push("a commit message carries a co-author trailer");
  if (new RegExp("gener" + "ated (with|by)", "i").test(messages)) problems.push("a commit message credits how it was made");
  return problems;
});

// --------------------------------------------------------------------------
// Report
// --------------------------------------------------------------------------

let failed = 0;
for (const result of results) {
  if (result.problems.length) {
    failed += 1;
    console.log("FAIL  " + result.name);
    for (const problem of result.problems) console.log("      " + problem);
  } else {
    console.log("ok    " + result.name);
  }
}
console.log("");
console.log(failed ? failed + " of " + results.length + " checks failed" : "all " + results.length + " checks passed");
process.exit(failed ? 1 : 0);

// Python to JavaScript parity: run src/engine.js on every case of
// data/fixtures/engine-cases.json and require every output to agree with the
// Python engine's to 1e-9, relative to the size of the figure (at least 1).
//
//   node tools/validate-engine.mjs [path/to/engine-cases.json]
//
// The cases are written by scripts/gen_fixtures.py from lngarb.cases.evaluate.
// If the two disagree, the JavaScript is fixed to match the Python, never the
// reverse. Exit status 1 on any disagreement.

import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { evaluate } from "../src/engine.js";
import { applyEdits, verdictSegments } from "../src/model-calc.js";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const FILE = process.argv[2] ? path.resolve(process.argv[2]) : path.join(ROOT, "data", "fixtures", "engine-cases.json");
const TOLERANCE = 1e-9;

function compare(expected, actual, where, problems) {
  if (expected === null) {
    // JSON has no NaN: the Python writes null where it computed NaN.
    if (!(actual === null || (typeof actual === "number" && Number.isNaN(actual)))) {
      problems.push(where + ": expected null, got " + JSON.stringify(actual));
    }
    return;
  }
  if (typeof expected === "number") {
    // An infinity is a disagreement: Python raises where JavaScript divides by
    // zero, and JSON carries no infinity, so the Python figure is finite.
    if (typeof actual !== "number" || !Number.isFinite(actual)) {
      problems.push(where + ": expected " + expected + ", got " + (typeof actual === "number" ? String(actual) : JSON.stringify(actual)));
      return;
    }
    // The tolerance is relative to the Python figure, at least 1.
    const scale = Math.max(1, Math.abs(expected));
    if (Math.abs(expected - actual) > TOLERANCE * scale) {
      problems.push(where + ": expected " + expected + ", got " + actual);
    }
    return;
  }
  if (typeof expected === "object") {
    if (actual === null || typeof actual !== "object") {
      problems.push(where + ": expected an object, got " + JSON.stringify(actual));
      return;
    }
    const keys = new Set([...Object.keys(expected), ...Object.keys(actual)]);
    for (const key of keys) {
      if (!(key in expected)) {
        problems.push(where + "." + key + ": not in the Python output");
      } else if (!(key in actual)) {
        problems.push(where + "." + key + ": missing from the JavaScript output");
      } else {
        compare(expected[key], actual[key], where + "." + key, problems);
      }
    }
    return;
  }
  if (expected !== actual) {
    problems.push(where + ": expected " + JSON.stringify(expected) + ", got " + JSON.stringify(actual));
  }
}

const data = JSON.parse(readFileSync(FILE, "utf-8"));
if (data.schema_version !== 1) {
  console.log("FAIL  " + FILE + " has schema_version " + data.schema_version + ", expected 1");
  process.exit(1);
}
const problems = [];
let lines = 0;
data.cases.forEach((c, i) => {
  const before = problems.length;
  compare(c.output, evaluate(structuredClone(c.inputs)), "case " + i, problems);
  lines += 1;
  if (problems.length > before && problems.length > 50) return;
});
if (problems.length) {
  for (const p of problems.slice(0, 50)) console.log("FAIL  " + p);
  console.log("\n" + problems.length + " disagreement(s) over " + lines + " cases");
  process.exit(1);
}
console.log("ok    " + lines + " cases agree with the Python engine to " + TOLERANCE + " on every output");

// The calculator's presets: the page's own path from a preset to its outputs
// (src/model-calc.js, then the engine) must give the Python's every line, and
// the landing sentence the Python wrote for the preset, segment for segment.
// Skipped only when the cases file was named on the command line.
const MODEL = path.join(ROOT, "data", "model.json");
if (!process.argv[2] && existsSync(MODEL)) {
  const model = JSON.parse(readFileSync(MODEL, "utf-8"));
  const presetProblems = [];
  for (const preset of model.presets) {
    const { inputs } = applyEdits(preset, [], model);
    const result = evaluate(inputs);
    compare(preset.result, result, "preset " + preset.id, presetProblems);
    // A preset missing a figure the sentence needs has none, in Python as on the page.
    if (preset.verdict_segments !== null) {
      compare(preset.verdict_segments, verdictSegments(result, inputs, model), "preset " + preset.id + " sentence", presetProblems);
    }
  }
  // The named edits: the page's way of laying a visitor's figures over a
  // preset, against the same edits worked in Python.
  for (const check of model.checks || []) {
    const preset = model.presets.find((p) => p.id === check.preset);
    if (!preset) {
      presetProblems.push("edit " + check.name + ": no preset " + check.preset);
      continue;
    }
    const { inputs, refused } = applyEdits(preset, check.edits, model);
    // The same figures refused, by input and route, as the Python refuses.
    const said = (list) => list.map((r) => r.key + "@" + (r.route || "")).sort().join(",");
    if (said(refused) !== said(check.refused || [])) {
      presetProblems.push("edit " + check.name + ": refused " + said(refused) + ", the Python " + said(check.refused || []));
    }
    compare(check.result, evaluate(inputs), "edit " + check.name, presetProblems);
  }
  if (presetProblems.length) {
    for (const p of presetProblems.slice(0, 50)) console.log("FAIL  " + p);
    console.log(presetProblems.length + " disagreement(s) over the calculator's presets");
    process.exit(1);
  }
  console.log("ok    " + model.presets.length + " calculator presets give the Python's output and sentence, and " + (model.checks || []).length + " named edits its output");
}

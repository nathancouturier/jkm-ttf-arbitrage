// Runs site/js/engine.js on every fixture case and compares each number with the Python engine's.
import { readFileSync } from "node:fs";
import { priceCargo, canalQuestion } from "../site/js/engine.js";

const cases = JSON.parse(readFileSync(new URL("./fixtures/engine_cases.json", import.meta.url)));
let compared = 0;
const failures = [];

function compare(path, want, got) {
  if (want !== null && typeof want === "object") {
    for (const key of Object.keys(want)) compare(`${path}.${key}`, want[key], got == null ? undefined : got[key]);
  } else if (typeof want === "number") {
    compared += 1;
    const tolerance = 1e-9 * Math.max(1, Math.abs(want));
    if (typeof got !== "number" || Math.abs(got - want) > tolerance) failures.push(`${path}: python ${want}, javascript ${got}`);
  } else {
    compared += 1;
    if (got !== want) failures.push(`${path}: python ${want}, javascript ${got}`);
  }
}

for (const c of cases) {
  compare(c.name, c.expected, priceCargo(c.inputs));
  compare(`${c.name} canal`, c.canal_question, canalQuestion(c.inputs));
}
if (failures.length) {
  console.error(failures.slice(0, 20).join("\n"));
  console.error(`${failures.length} of ${compared} values differ`);
  process.exit(1);
}
console.log(`${cases.length} cases, ${compared} values agree to 1e-9`);

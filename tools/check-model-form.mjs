#!/usr/bin/env node
// The calculator's form, driven in headless Chromium: what a visitor types,
// and what the page must then show. tools/validate-engine.mjs holds the
// arithmetic of src/model-calc.js to the Python; this holds the form layer of
// src/model.js, which no other check reaches.
//
//     python scripts/serve.py --port 8131                 in another shell
//     node tools/check-model-form.mjs [--base URL] [--browser PATH]
//
// Each check opens the Model view afresh, types into fields the way a visitor
// does (the value set, then the input and change events), and reads the page.
// Exit status 1 on any failure or any console error.

import { argValue, launch, openView } from "./browser.mjs";

const BASE = argValue(process.argv, "--base") || "http://localhost:8131/jkm-ttf-arbitrage/";

/* A snippet run in the page: type into the element the selector names. */
function typeInto(selector, text) {
  return "(() => { const input = document.querySelector(" + JSON.stringify(selector) + ");" +
    " input.value = " + JSON.stringify(text) + ";" +
    " input.dispatchEvent(new Event('input', { bubbles: true }));" +
    " input.dispatchEvent(new Event('change', { bubbles: true })); return true; })()";
}

function choose(selector, value) {
  return "(() => { const select = document.querySelector(" + JSON.stringify(selector) + ");" +
    " select.value = " + JSON.stringify(value) + ";" +
    " select.dispatchEvent(new Event('change', { bubbles: true })); return true; })()";
}

const cell = (route, field) => "document.querySelector('.model-outputs tr[data-route=\"" + route + "\"] td[data-field=\"" + field + "\"]').textContent";
const routeInput = (route, label) => ".model-routes tr[data-route=\"" + route + "\"] input[aria-label$=\", " + label + "\"]";
const notes = "document.querySelector('.model-notes').textContent";
const verdict = "document.querySelector('.model-verdict').textContent";

const CHECKS = [
  {
    name: "TTF in EUR/MWh follows a new exchange rate, and its label says the unit",
    hash: "#/model?preset=latest",
    async run(page) {
      const before = await page.evaluate(cell("nwe_direct", "netback"));
      await page.evaluate(choose("select[aria-label=\"TTF unit\"]", "eur_mwh"));
      const label = await page.evaluate("document.querySelector('label[for=\"field-ttf\"]').textContent");
      const same = await page.evaluate(cell("nwe_direct", "netback"));
      const shown = await page.evaluate("document.querySelector('#field-ttf').value");
      await page.evaluate(typeInto("#field-usd_per_eur", "1.3"));
      const after = await page.evaluate(cell("nwe_direct", "netback"));
      const still = await page.evaluate("document.querySelector('#field-ttf').value");
      return [
        [label.includes("EUR/MWh"), "the label reads " + label],
        [same === before, "switching the unit moved Gate from " + before + " to " + same],
        [still === shown, "the EUR figure changed with the rate: " + shown + " then " + still],
        [after !== before, "a new rate left Gate at " + after],
      ];
    },
  },
  {
    name: "a figure typed in EUR/MWh survives switching the unit both ways",
    hash: "#/model?preset=latest",
    async run(page) {
      await page.evaluate(choose("select[aria-label=\"TTF unit\"]", "eur_mwh"));
      await page.evaluate(typeInto("#field-ttf", "30.01"));
      await page.evaluate(choose("select[aria-label=\"TTF unit\"]", "usd_mmbtu"));
      await page.evaluate(choose("select[aria-label=\"TTF unit\"]", "eur_mwh"));
      const back = await page.evaluate("document.querySelector('#field-ttf').value");
      return [[back === "30.01", "back in EUR/MWh the field reads " + back]];
    },
  },
  {
    name: "the preset's figure written another way is the preset's",
    hash: "#/model?preset=latest",
    async run(page) {
      const before = await page.evaluate(cell("nwe_direct", "netback"));
      const text = await page.evaluate("document.querySelector('#field-ttf').value");
      await page.evaluate(typeInto("#field-ttf", text.replace(/0+$/, "").replace(/\.$/, "")));
      const after = await page.evaluate(cell("nwe_direct", "netback"));
      return [[after === before, "Gate moved from " + before + " to " + after]];
    },
  },
  {
    name: "a figure too large to be finite is refused with words",
    hash: "#/model?preset=latest",
    async run(page) {
      await page.evaluate(typeInto("#field-speed_kn", "1e999"));
      const said = await page.evaluate(notes);
      const sentence = await page.evaluate(verdict);
      const invalid = await page.evaluate("document.querySelector('#field-speed_kn').getAttribute('aria-invalid')");
      return [
        [said.includes("Speed is too large to use"), "the notes read " + said],
        [sentence.startsWith("No sentence"), "the sentence reads " + sentence],
        [invalid === "true", "the field is not marked invalid"],
      ];
    },
  },
  {
    name: "text in a route cell is a missing input, named with its route",
    hash: "#/model?preset=latest",
    async run(page) {
      await page.evaluate(typeInto(routeInput("nea_panama", "Canal toll laden, $"), "abc"));
      await page.evaluate(typeInto(routeInput("nea_cape", "Laden days at sea"), "abc"));
      const said = await page.evaluate(notes);
      const invalid = await page.evaluate("document.querySelector(" + JSON.stringify(routeInput("nea_panama", "Canal toll laden, $")) + ").getAttribute('aria-invalid')");
      const cape = await page.evaluate(cell("nea_cape", "netback"));
      await page.evaluate(typeInto(routeInput("nea_cape", "Laden days at sea"), ""));
      const after = await page.evaluate(notes);
      return [
        [said.includes("Futtsu via Panama, canal toll laden"), "the notes read " + said],
        [said.includes("Futtsu via the Cape, laden days at sea"), "the notes do not name the Cape's days"],
        [invalid === "true", "the cell is not marked invalid"],
        [cape === "no figure", "the Cape's netback reads " + cape],
        [!after.includes("laden days at sea"), "an emptied days cell is still named missing: " + after],
      ];
    },
  },
  {
    name: "the tolls follow the ship",
    hash: "#/model?preset=latest",
    async run(page) {
      const selector = routeInput("nea_panama", "Canal toll laden, $");
      const before = await page.evaluate("document.querySelector(" + JSON.stringify(selector) + ").value");
      await page.evaluate(choose("#field-vessel", "tfde_160k"));
      const after = await page.evaluate("document.querySelector(" + JSON.stringify(selector) + ").value");
      return [[after !== before && after !== "", "the Panama toll stayed " + before + " for the smaller ship (" + after + ")"]];
    },
  },
  {
    name: "a ballast leg back by a closed route closes the route, and says so",
    hash: "#/model?preset=march_2024",
    async run(page) {
      await page.evaluate(choose("select[aria-label=\"Futtsu via the Cape, back by\"]", "nea_suez"));
      const name = await page.evaluate("document.querySelector('.model-outputs tr[data-route=\"nea_cape\"] th').textContent");
      const said = await page.evaluate("document.querySelector('.model-route-notes').textContent");
      return [
        [name.includes("closed"), "the Cape's row reads " + name],
        [said.includes("back by Suez, which is closed"), "the route notes read " + said],
      ];
    },
  },
  {
    name: "a closed route opened by its box says it is opened here",
    hash: "#/model?preset=march_2024",
    async run(page) {
      await page.evaluate("(() => { const box = document.querySelector('.model-routes tr[data-route=\"nea_suez\"] input[type=checkbox]'); box.checked = true; box.dispatchEvent(new Event('change', { bubbles: true })); return true; })()");
      const said = await page.evaluate("document.querySelector('.model-route-notes').textContent");
      return [[said.includes("opened here"), "the route notes read " + said]];
    },
  },
  {
    name: "a ship that burns all it loads gives no netback, and says so",
    hash: "#/model?preset=latest",
    async run(page) {
      await page.evaluate(typeInto("#field-boil_off_percent", "1"));
      await page.evaluate(typeInto("#field-speed_kn", "5"));
      const said = await page.evaluate(notes);
      const panama = await page.evaluate(cell("nea_panama", "netback"));
      const sentence = await page.evaluate(verdict);
      return [
        [said.includes("burns as much gas as it loads"), "the notes read " + said],
        [panama === "no figure", "Panama's netback reads " + panama],
        [sentence.startsWith("No sentence"), "the sentence reads " + sentence],
      ];
    },
  },
  {
    name: "a comma is read as the site writes figures, and says how",
    hash: "#/model?preset=latest",
    async run(page) {
      await page.evaluate(typeInto("#field-hire_usd_day", "300,000"));
      const hire = await page.evaluate("document.querySelector('#field-hire_usd_day-status').textContent");
      await page.evaluate(typeInto("#field-jkm", "12,5"));
      const jkm = await page.evaluate("document.querySelector('#field-jkm-status').textContent");
      return [
        [hire === "Read as 300000.", "the hire's status reads " + hire],
        [jkm === "Read as 12.5.", "JKM's status reads " + jkm],
      ];
    },
  },
  {
    name: "the unit of TTF cannot change while the exchange rate is missing",
    hash: "#/model?preset=april_2020",
    async run(page) {
      await page.evaluate(choose("select[aria-label=\"TTF unit\"]", "eur_mwh"));
      const euro = await page.evaluate("document.querySelector('#field-ttf').value");
      await page.evaluate(typeInto("#field-usd_per_eur", ""));
      await page.evaluate(choose("select[aria-label=\"TTF unit\"]", "usd_mmbtu"));
      const unit = await page.evaluate("document.querySelector('select[aria-label=\"TTF unit\"]').value");
      const still = await page.evaluate("document.querySelector('#field-ttf').value");
      const status = await page.evaluate("document.querySelector('#field-ttf-status').textContent");
      return [
        [unit === "eur_mwh", "the unit changed to " + unit],
        [still === euro, "the figure changed from " + euro + " to " + still],
        [status.includes("cannot change"), "the status reads " + status],
      ];
    },
  },
  {
    name: "a hire the data do not hold is missing, and the three levels are offered",
    hash: "#/model?preset=april_2020",
    async run(page) {
      const hire = await page.evaluate("document.querySelector('#field-hire_usd_day').value");
      const said = await page.evaluate(notes);
      const sentence = await page.evaluate(verdict);
      await page.evaluate("(() => { const b = [...document.querySelectorAll('.model-levels .choice')].find((x) => x.textContent.startsWith('Central')); b.click(); return true; })()");
      const typed = await page.evaluate("document.querySelector('#field-hire_usd_day').value");
      const gate = await page.evaluate(cell("nwe_direct", "netback"));
      return [
        [hire === "", "the hire reads " + hire],
        [said.includes("Hire, round trip"), "the notes read " + said],
        [sentence.startsWith("No sentence"), "the sentence reads " + sentence],
        [typed !== "", "the central level was not typed"],
        [gate !== "no figure", "Gate's netback still reads " + gate],
      ];
    },
  },
  {
    name: "choosing the preset already shown keeps what was typed",
    hash: "#/model?preset=latest",
    async run(page) {
      await page.evaluate(typeInto("#field-hire_usd_day", "100000"));
      await page.evaluate("document.querySelector('.choice[data-preset=\"latest\"]').click(), true");
      await page.evaluate("new Promise((r) => setTimeout(r, 300))");
      const hire = await page.evaluate("document.querySelector('#field-hire_usd_day').value");
      return [[hire === "100000", "the hire reads " + hire]];
    },
  },
  {
    name: "a decimal comma after a zero is read as a decimal",
    hash: "#/model?preset=latest",
    async run(page) {
      await page.evaluate(typeInto("#field-boil_off_percent", "0,075"));
      const status = await page.evaluate("document.querySelector('#field-boil_off_percent-status').textContent");
      await page.evaluate(typeInto("#field-boil_off_percent", "0,085"));
      const same = await page.evaluate(notes);
      return [
        [status === "Read as 0.075.", "the status reads " + status],
        [!same.includes("Boil-off"), "the preset's own figure with a comma is named: " + same],
      ];
    },
  },
  {
    name: "no cargo delivered to Gate leaves no comparison with Gate, and the sentence says why",
    hash: "#/model?preset=latest",
    async run(page) {
      await page.evaluate(typeInto("#field-boil_off_percent", "1"));
      await page.evaluate(typeInto(routeInput("nwe_direct", "Laden days at sea"), "120"));
      await page.evaluate(typeInto(routeInput("nwe_direct", "Ballast days at sea"), "120"));
      const over = await page.evaluate(cell("nea_panama", "arb"));
      const sentence = await page.evaluate(verdict);
      return [
        [over === "no figure", "Panama over Gate reads " + over],
        [sentence.includes("no cargo is delivered to Gate"), "the sentence reads " + sentence],
      ];
    },
  },
  {
    name: "the ship's parameters name their sources, which follow the carrier",
    hash: "#/model?preset=latest",
    async run(page) {
      const before = await page.evaluate("document.querySelector('#field-boil_off_percent-source').textContent");
      await page.evaluate(choose("#field-vessel", "tfde_160k"));
      const after = await page.evaluate("document.querySelector('#field-boil_off_percent-source').textContent");
      return [
        [before.includes("Spark"), "the boil-off's source reads " + before],
        [after !== before, "the source did not follow the carrier"],
      ];
    },
  },
  {
    name: "an address naming no preset says so and is rewritten",
    // Opened on a known preset, then sent to an unknown one: opening the
    // unknown one directly would be rewritten before the reload that opens
    // every check.
    hash: "#/model?preset=latest",
    async run(page) {
      await page.evaluate("location.hash = '#/model?preset=octobre_2022', true");
      await page.waitFor("document.querySelector('#view').textContent.includes('names no preset')", 5000).catch(() => null);
      const said = await page.evaluate("document.querySelector('#view').textContent");
      const hash = await page.evaluate("location.hash");
      return [
        [said.includes("names no preset called \"octobre_2022\""), "nothing says the preset is unknown"],
        [hash === "#/model?preset=latest", "the address reads " + hash],
      ];
    },
  },
  {
    name: "choosing a preset keeps the keyboard on it",
    hash: "#/model?preset=latest",
    async run(page) {
      await page.evaluate("document.querySelector('.choice[data-preset=\"april_2020\"]').focus(), document.querySelector('.choice[data-preset=\"april_2020\"]').click(), true");
      await page.waitFor("location.hash === '#/model?preset=april_2020' && document.querySelector('.choice[aria-pressed=\"true\"]').dataset.preset === 'april_2020'");
      const focused = await page.evaluate("document.activeElement && document.activeElement.dataset ? document.activeElement.dataset.preset || document.activeElement.tagName : 'none'");
      return [[focused === "april_2020", "focus is on " + focused]];
    },
  },
  {
    name: "before 2024 the allowance price is not shown as zero, and is missing only once a share is surrendered",
    hash: "#/model?preset=april_2020",
    async run(page) {
      const price = await page.evaluate("document.querySelector('#field-eua_eur_t').value");
      const quiet = await page.evaluate(notes);
      await page.evaluate(typeInto("#field-ets_phase", "1"));
      const said = await page.evaluate(notes);
      const gate = await page.evaluate(cell("nwe_direct", "netback"));
      return [
        [price === "", "the allowance field reads " + price],
        [!quiet.includes("EU allowance"), "the untouched preset names the allowance missing"],
        [said.includes("EU allowance"), "with a share surrendered the notes read " + said],
        [gate === "no figure", "Gate's netback reads " + gate],
      ];
    },
  },
];

const browser = await launch(process.argv);
let failed = 0;
try {
  const page = await browser.page();
  for (const check of CHECKS) {
    let results;
    try {
      // Inside the try, so a page that will not open fails this check alone.
      await openView(page, BASE, { hash: check.hash });
      page.errors.length = 0;
      results = await check.run(page);
    } catch (error) {
      results = [[false, "threw " + (error && error.message ? error.message : String(error))]];
    }
    const wrong = results.filter(([ok]) => !ok).map(([, why]) => why);
    if (page.errors.length) wrong.push(...page.errors);
    if (wrong.length) {
      failed += 1;
      console.log("FAIL  " + check.name);
      for (const why of wrong) console.log("      " + why);
    } else {
      console.log("ok    " + check.name);
    }
  }
} finally {
  await browser.close();
}
if (failed) {
  console.log("\n" + failed + " of " + CHECKS.length + " form checks failed");
  process.exit(1);
}
console.log("PASS  " + CHECKS.length + " form checks");

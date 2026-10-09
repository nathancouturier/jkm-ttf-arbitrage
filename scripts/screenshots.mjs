#!/usr/bin/env node
// Full page screenshots of the site, from its subpath, in headless Chromium.
//
//     python scripts/serve.py --port 8131                          in another shell
//     node scripts/screenshots.mjs
//     node scripts/screenshots.mjs --base https://nathancouturier.github.io/jkm-ttf-arbitrage/
//     node scripts/screenshots.mjs --out assets --browser "C:/Program Files/Google/Chrome/Application/chrome.exe"
//     node scripts/screenshots.mjs --only now-mobile          shots whose names start so
//
// One PNG per entry in SHOTS into --out (default assets/), each the whole page,
// every pixel of its height, at desktop and mobile widths in both themes, with
// every console error or uncaught exception the page raised printed beside it.
// The theme is set the way a visitor's choice is, through the nc-theme key in
// localStorage, before the page loads. The browser is any Chromium, found by
// tools/browser.mjs; every run uses a fresh profile.
//
// Exit status 1 if any shot fails or the page logged an error, so a run that
// photographed a broken page does not look like a good one.

import { mkdirSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { argValue, launch, openNow, openView } from "../tools/browser.mjs";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const argv = process.argv;
const BASE = argValue(argv, "--base") || "http://localhost:8131/jkm-ttf-arbitrage/";
const OUT = path.resolve(ROOT, argValue(argv, "--out") || "assets");

const DESKTOP = { width: 1440, height: 900 };
const MOBILE = { width: 375, height: 812 };
const TABLET = { width: 768, height: 1024 };
const NARROW = { width: 320, height: 640 };
const ALL = "netbacks,cost,breakeven,flows,provenance";

const SHOTS = [
  { name: "now-desktop-light", ...DESKTOP, theme: "light", open: "" },
  { name: "now-desktop-dark", ...DESKTOP, theme: "dark", open: "" },
  { name: "now-desktop-light-open", ...DESKTOP, theme: "light", open: ALL },
  { name: "now-desktop-dark-open", ...DESKTOP, theme: "dark", open: ALL },
  { name: "now-mobile-light", ...MOBILE, theme: "light", open: "" },
  { name: "now-mobile-dark", ...MOBILE, theme: "dark", open: "" },
  { name: "now-mobile-light-open", ...MOBILE, theme: "light", open: ALL },
  { name: "now-mobile-dark-open", ...MOBILE, theme: "dark", open: ALL },
  { name: "model-desktop-light", ...DESKTOP, theme: "light", hash: "#/model" },
  { name: "model-desktop-dark-october-2022", ...DESKTOP, theme: "dark", hash: "#/model?preset=october_2022" },
  { name: "model-mobile-light-spark", ...MOBILE, theme: "light", hash: "#/model?preset=spark_example" },
  { name: "routes-desktop-light", ...DESKTOP, theme: "light", hash: "#/routes" },
  { name: "routes-desktop-dark", ...DESKTOP, theme: "dark", hash: "#/routes" },
  { name: "routes-mobile-light", ...MOBILE, theme: "light", hash: "#/routes" },
  { name: "routes-mobile-dark", ...MOBILE, theme: "dark", hash: "#/routes" },
  { name: "routes-tablet-dark", ...TABLET, theme: "dark", hash: "#/routes" },
  { name: "routes-narrow-light", ...NARROW, theme: "light", hash: "#/routes" },
  { name: "model-mobile-dark", ...MOBILE, theme: "dark", hash: "#/model?preset=march_2024" },
  { name: "model-tablet-light", ...TABLET, theme: "light", hash: "#/model?preset=april_2020" },
  { name: "model-narrow-dark", ...NARROW, theme: "dark", hash: "#/model" },
  { name: "history-desktop-light", ...DESKTOP, theme: "light", hash: "#/history" },
  { name: "history-desktop-dark-last-52", ...DESKTOP, theme: "dark", hash: "#/history?range=last_52" },
  { name: "history-tablet-dark", ...TABLET, theme: "dark", hash: "#/history?range=from_2024" },
  { name: "history-mobile-light", ...MOBILE, theme: "light", hash: "#/history" },
  { name: "history-narrow-dark", ...NARROW, theme: "dark", hash: "#/history?range=to_2023" },
  { name: "flows-desktop-light", ...DESKTOP, theme: "light", hash: "#/flows" },
  { name: "flows-desktop-dark", ...DESKTOP, theme: "dark", hash: "#/flows" },
  { name: "flows-tablet-light", ...TABLET, theme: "light", hash: "#/flows" },
  { name: "flows-mobile-dark", ...MOBILE, theme: "dark", hash: "#/flows" },
  { name: "flows-narrow-light", ...NARROW, theme: "light", hash: "#/flows" },
  { name: "method-desktop-light", ...DESKTOP, theme: "light", hash: "#/method" },
  { name: "method-desktop-dark", ...DESKTOP, theme: "dark", hash: "#/method" },
  { name: "method-tablet-dark", ...TABLET, theme: "dark", hash: "#/method" },
  { name: "method-mobile-light", ...MOBILE, theme: "light", hash: "#/method" },
  { name: "method-narrow-dark", ...NARROW, theme: "dark", hash: "#/method" },
];
const ONLY = (argValue(argv, "--only") || "").split(",").filter(Boolean);

/** Width and height from a PNG's IHDR chunk, to report what was written. */
function pngSize(buffer) {
  return { width: buffer.readUInt32BE(16), height: buffer.readUInt32BE(20) };
}

mkdirSync(OUT, { recursive: true });
const browser = await launch(argv);
console.log("screenshots.mjs, " + BASE + " into " + path.relative(ROOT, OUT));
let failed = false;
try {
  const page = await browser.page();
  for (const shot of SHOTS.filter((s) => !ONLY.length || ONLY.some((prefix) => s.name.startsWith(prefix)))) {
    page.errors.length = 0;
    try {
      if (shot.hash) await openView(page, BASE, shot);
      else await openNow(page, BASE, shot);
      const theme = await page.evaluate("document.documentElement.dataset.theme");
      if (theme !== shot.theme) throw new Error("the page is in " + theme + ", not " + shot.theme);
      const overflow = await page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth");
      const { png, height } = await page.screenshotFullPage(shot.width);
      const file = path.join(OUT, shot.name + ".png");
      writeFileSync(file, png);
      const size = pngSize(png);
      const errors = page.errors.filter((m) => !/chrome-extension:\/\//.test(m) && /^(exception|console error|log error)/.test(m));
      console.log("  " + path.relative(ROOT, file) + "  " + size.width + " x " + size.height + " px" +
        (size.height !== height ? ", PAGE IS " + height + " px TALL" : "") +
        (overflow > 0 ? ", THE PAGE SCROLLS SIDEWAYS BY " + overflow + " px" : "") +
        ", console errors: " + (errors.length ? errors.length : "none"));
      for (const error of errors) console.log("      " + error);
      if (errors.length || size.height !== height || overflow > 0) failed = true;
    } catch (error) {
      failed = true;
      console.log("  FAIL  " + shot.name + ": " + error.message);
    }
  }
} finally {
  await browser.close();
}
process.exit(failed ? 1 : 0);

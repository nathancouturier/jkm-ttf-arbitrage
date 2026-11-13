// Loads the study, shows one view at a time and keeps the page state in the address.

import { h, day, readHash, writeHash } from "./util.js";
import * as reroute from "./views/reroute.js";
import * as cargo from "./views/cargo.js";
import * as history_ from "./views/history.js";
import * as routes from "./views/routes.js";
import * as flows from "./views/flows.js";
import * as method from "./views/method.js";

const VIEWS = { reroute, cargo, history: history_, routes, flows, method };
const TITLES = { reroute: "Reroute levels", cargo: "One cargo", history: "History", routes: "Routes", flows: "Flows", method: "Method" };
const main = document.getElementById("main");
let D = null;
let current = null;
let mapData = null;

function show() {
  const { view, params } = readHash();
  const name = VIEWS[view] ? view : "reroute";
  for (const a of document.querySelectorAll(".top nav a")) {
    if (a.dataset.view === name) a.setAttribute("aria-current", "page");
    else a.removeAttribute("aria-current");
  }
  document.title = `${TITLES[name]} · JKM-TTF arbitrage`;
  if (!current || current.name !== name) {
    main.replaceChildren();
    const ctx = {
      D,
      params,
      map: () => (mapData ||= fetch("data/map.json").then((r) => r.json())),
      // A control changed: keep the state in the address, redraw, and give the focus back to the control.
      set(patch) {
        for (const [k, v] of Object.entries(patch)) {
          if (v == null) delete ctx.params[k];
          else ctx.params[k] = String(v);
        }
        writeHash(name, ctx.params);
        const focus = document.activeElement && document.activeElement.dataset ? document.activeElement.dataset.focus : null;
        current.view.update();
        const again = focus ? main.querySelector(`[data-focus="${focus}"]`) : null;
        if (again) again.focus();
      },
    };
    current = { name, ctx, view: VIEWS[name].mount(main, ctx) };
    window.scrollTo(0, 0);
  } else {
    current.ctx.params = params;
  }
  current.view.update();
}

// "Skip to the content" moves the focus; it must not change the address, which names the view.
document.querySelector(".skip").addEventListener("click", (event) => {
  event.preventDefault();
  main.focus();
});

document.getElementById("theme").addEventListener("click", () => {
  const dark = document.documentElement.dataset.theme !== "dark";
  document.documentElement.dataset.theme = dark ? "dark" : "light";
  try { localStorage.setItem("theme", dark ? "dark" : "light"); } catch (e) { /* private mode */ }
});

let resizing = null;
let lastWidth = window.innerWidth;
window.addEventListener("resize", () => {
  if (window.innerWidth === lastWidth) return;
  lastWidth = window.innerWidth;
  clearTimeout(resizing);
  resizing = setTimeout(() => current && current.view.update(), 120);
});
window.addEventListener("hashchange", show);

fetch("data/study.json")
  .then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); })
  .then((study) => {
    D = study;
    document.getElementById("data-date").textContent = `Prices to ${day(D.data_date)}`;
    show();
  })
  .catch(() => {
    main.replaceChildren(h("p", { class: "dek" }, "The study's data could not be loaded. Serve the site folder over HTTP and reload."));
  });

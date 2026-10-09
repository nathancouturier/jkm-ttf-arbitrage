/* now.js
 *
 * The Now view: the verdict, the date of every input, then five sections,
 * closed on first load, each opened by a button the visitor operates. Their
 * names and the sentences stating what each shows come from data/now.json.
 *
 * OPENING. Each section is an h2 holding a full width native button, so Tab
 * reaches it and Enter and Space operate it with no key handler of ours. The
 * button carries aria-expanded and aria-controls; the body it controls is a
 * region labelled by the button, and while closed it is inert, so nothing
 * inside a closed section takes focus or is read. The open set lives in the
 * address, #/now?open=netbacks,breakeven, written with router.replaceState so
 * opening a section adds no history entry and does not rebuild the page.
 *
 * LOADING. A section that needs another artifact loads it the first time it
 * opens, so the landing view needs only now.json, and a failed artifact takes
 * down its own section with a sentence saying what happened and what to do,
 * never the verdict. The one motion is the body's height, which
 * prefers-reduced-motion cuts to nothing.
 *
 * Numeric literals: none. Every figure is a segment of an artifact.
 */

import { el, clear, appendSegments, loadingMessage, failureMessages, renderFailureMessages } from "./dom.js";
import * as router from "./router.js";
import * as state from "./state.js";
import * as netbacksSection from "./section-netbacks.js";
import * as costSection from "./section-cost.js";
import * as breakevenSection from "./section-breakeven.js";
import * as flowsSection from "./section-flows.js";
import * as provenanceSection from "./section-provenance.js";

export const artifacts = Object.freeze(["now"]);

const VIEW = "now";

/* Section id in now.json, to the module that fills it. Each module exports
 * `artifact`, the state.js name it reads, `loading`, the words for its loading
 * sentence, and render(inner, data, now). */
const SECTION_MODULES = Object.freeze({
  netbacks: netbacksSection,
  cost: costSection,
  breakeven: breakevenSection,
  flows: flowsSection,
  provenance: provenanceSection,
});

const WORD_SHOW = "Show";
const WORD_HIDE = "Hide";

let rendered = new Map();
let nowData = null;

function sectionIds() {
  return [...rendered.keys()];
}

/** Render into `root`. Returns the element that takes focus on a route change:
 *  the verdict h1. */
export function render(root, data, route) {
  const now = data.now;
  nowData = now;
  const decimals = now.conventions.decimals;
  rendered = new Map();

  const verdict = el("h1", { class: "verdict", id: "view-title", attrs: { tabindex: "-1" } });
  appendSegments(verdict, now.verdict.segments, decimals);

  // How much the verdict rests on Europe's regasification discount, which
  // ACER publishes sparsely: one sentence, the counts over every week.
  const regas = now.regas_sensitivity
    ? appendSegments(el("p", { class: "lead block" }), now.regas_sensitivity.segments, decimals)
    : null;

  const dates = el("ul", { class: "data-dates", attrs: { "aria-label": "The date of every input" } });
  for (const row of now.data_dates) {
    dates.appendChild(appendSegments(el("li", { attrs: { "data-date": row.id } }), row.segments, decimals));
  }

  const sections = el("div", { class: "sections", id: "now-sections" });
  for (const section of now.sections) {
    const module = SECTION_MODULES[section.id];
    if (!module) continue; // a section this build has no module for is not drawn
    sections.appendChild(buildSection(section, module, decimals));
  }

  root.appendChild(verdict);
  if (regas) root.appendChild(regas);
  root.appendChild(dates);
  root.appendChild(sections);
  applyRoute(route);
  return verdict;
}

/** Only the address changed, for example a pasted link with open sections. */
export function update(root, route) {
  applyRoute(route);
}

function applyRoute(route) {
  const open = new Set(state.openSections(route && route.params, sectionIds()));
  for (const [id, entry] of rendered) setOpen(entry, open.has(id));
}

function buildSection(section, module, decimals) {
  const buttonId = "section-button-" + section.id;
  const bodyId = "section-body-" + section.id;

  const word = el("span", { class: "section__toggle-word", text: WORD_SHOW, attrs: { "aria-hidden": "true" } });
  const button = el("button", {
    class: "section__button",
    id: buttonId,
    attrs: { type: "button", "aria-expanded": "false", "aria-controls": bodyId, "data-section": section.id },
  }, [
    el("span", { class: "section__name", text: section.name }),
    appendSegments(el("span", { class: "section__summary" }), section.summary_segments, decimals),
    word,
  ]);

  const inner = el("div", { class: "section__inner" });
  const body = el("div", {
    class: "section__body",
    id: bodyId,
    attrs: { role: "region", "aria-labelledby": buttonId, "data-open": "false", inert: "" },
  }, [inner]);

  const node = el("section", { class: "section", id: "section-" + section.id }, [
    el("h2", { class: "section__heading" }, [button]),
    body,
  ]);

  const entry = { id: section.id, module, button, word, body, inner, filled: false };
  rendered.set(section.id, entry);

  button.addEventListener("click", () => {
    const opening = button.getAttribute("aria-expanded") !== "true";
    setOpen(entry, opening);
    const open = sectionIds().filter((id) => rendered.get(id).button.getAttribute("aria-expanded") === "true");
    router.replaceState(VIEW, state.openParams(open));
  });
  return node;
}

function setOpen(entry, open) {
  entry.button.setAttribute("aria-expanded", open ? "true" : "false");
  entry.word.textContent = open ? WORD_HIDE : WORD_SHOW;
  entry.body.setAttribute("data-open", open ? "true" : "false");
  if (open) entry.body.removeAttribute("inert");
  else entry.body.setAttribute("inert", "");
  if (open && !entry.filled) fill(entry);
}

async function fill(entry) {
  entry.filled = true;
  const { module, inner } = entry;
  clear(inner);
  inner.appendChild(loadingMessage(module.loading));
  const result = await state.loadAll([module.artifact]);
  clear(inner);
  if (!result.ok) {
    for (const node of failureMessages(result.failures)) inner.appendChild(node);
    // Let a later open try again rather than keeping the failure forever.
    state.forget(module.artifact);
    entry.filled = false;
    return;
  }
  try {
    module.render(inner, result.data[module.artifact], nowData);
  } catch (error) {
    // The file arrived and was accepted, but this section cannot draw it: say
    // so in the section, and let a later open try again.
    clear(inner);
    for (const node of renderFailureMessages([module.artifact], error)) inner.appendChild(node);
    entry.filled = false;
  }
}

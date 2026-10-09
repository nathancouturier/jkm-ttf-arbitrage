/* section-provenance.js
 *
 * "Provenance", inside the Now view: the manifest as a table, failed and stale
 * series first (series, status, range, missing dates, last fetch, vintage,
 * source, terms), then the work done by hand, then the credits.
 *
 * WHOSE WORDS. data/provenance.json carries a reader's layer over
 * data/manifest.json: a label, the publisher and its page, and every cell in
 * words. Nothing here prints a series identifier. A status is a word in a cell
 * at full ink; a gap is a count of missing dates with the first and last
 * named; a series no machine fetches says so instead of an empty fetch time.
 *
 * Numeric literals: none.
 */

import { el, scrollTable } from "./dom.js";
import { artifactUrl } from "./state.js";

export const artifact = "provenance";
export const loading = "the manifest of every series, its source, its last fetch and its terms";

/* Rows that did not come back cleanly lead the table. */
const TROUBLE = new Set(["failed", "stale"]);

export function render(inner, data) {
  const columns = data.columns;
  const head = el("tr", {}, columns.map((column) => el("th", { text: column.head, attrs: { scope: "col", "data-short": column.short } })));
  const rows = [...data.series].sort((a, b) => Number(TROUBLE.has(b.status)) - Number(TROUBLE.has(a.status)));
  const body = el("tbody");
  for (const row of rows) {
    const cells = columns.map((column) => {
      if (column.id === "series") {
        return el("th", { class: "manifest__series", attrs: { scope: "row" } }, [
          el("span", { text: row.label }),
        ]);
      }
      if (column.id === "source") {
        return el("td", { class: "manifest__words" }, [
          el("a", { class: "text-link", text: row.publisher, attrs: { href: row.page_url, rel: "noopener" } }),
        ]);
      }
      return el("td", { class: "manifest__words", text: row[column.id] });
    });
    body.appendChild(el("tr", { attrs: { "data-status": row.status } }, cells));
  }
  const table = el("table", { class: "table manifest-table" }, [el("thead", {}, [head]), body]);
  inner.appendChild(el("div", { class: "block" }, [scrollTable([data.table_caption], table)]));

  const steps = el("div", { class: "block" }, [el("h3", { class: "block__heading", text: data.manual_heading })]);
  steps.appendChild(el("p", { class: "prose", text: data.manual_intro }));
  for (const step of data.manual_steps) {
    steps.appendChild(el("div", { class: "manual-step" }, [
      el("p", { class: "prose manual-step__what", text: step.what }),
      el("p", { class: "prose", text: step.why }),
      el("p", { class: "prose", text: step.cost_if_skipped }),
    ]));
  }
  inner.appendChild(steps);

  const credits = el("ul", { class: "credit-list" });
  for (const credit of data.credits) credits.appendChild(el("li", { class: "prose note", text: credit }));
  inner.appendChild(el("div", { class: "block" }, [el("h3", { class: "block__heading", text: data.credits_heading }), credits]));

  inner.appendChild(el("p", { class: "block note" }, [
    data.manifest_words + " ",
    el("a", { class: "text-link", text: "data/manifest.json", attrs: { href: artifactUrl("data/manifest.json") } }),
    ".",
  ]));
}

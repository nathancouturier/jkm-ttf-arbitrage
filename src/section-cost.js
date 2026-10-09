/* section-cost.js
 *
 * "Why the long way costs more", inside the Now view: the arb of the best open
 * route east as steps from the netback at Gate. A table, one row per step, a
 * bar in a cell, the figure at the right; the last row is the arb itself, the
 * one accent bar. The bar scale is anchored on zero at the Gate netback, so the
 * steps are drawn at the size of the argument rather than as slivers on a
 * scale built for a netback of twenty dollars.
 *
 * The table is the text alternative of its own bars: every bar's value is the
 * figure in its row, so the bars are aria-hidden. At 600px and below each row
 * becomes two lines by CSS grid on the tr, which is why the roles are written
 * into the markup. A positive and a negative step are told apart without
 * colour: a filled bar against an outlined one, and the printed sign.
 *
 * Numeric literals: none.
 */

import { el, sentence, disclosure, figureCell } from "./dom.js";
import { formatCell, UNITS } from "./format.js";
import * as charts from "./charts.js";

export const artifact = "now";
export const loading = "the steps from the Gate netback to the Futtsu netback";

export function render(inner, data) {
  const decimals = data.conventions.decimals;
  const cost = data.cost;
  if (!cost.rows.length) {
    inner.appendChild(sentence("p", cost.heading_segments, decimals, "lead"));
    return;
  }
  const scale = [cost.scale.low, cost.scale.high];
  inner.appendChild(sentence("p", cost.start_segments, decimals, "lead"));

  const body = el("tbody", { attrs: { role: "rowgroup" } });
  const barCells = [];
  cost.rows.forEach((row, index) => {
    const isTotal = row.kind === "total";
    const nameCell = el("th", { class: "waterfall__name", attrs: { scope: "row", role: "rowheader" } }, [
      el("span", { class: "waterfall__line", text: row.name }),
    ]);
    if (row.detail_segments) nameCell.appendChild(sentence("span", row.detail_segments, decimals, "waterfall__detail"));
    const barCell = el("td", { class: "waterfall__bar", attrs: { role: "cell" } });
    barCells.push({ cell: barCell, row, previous: index > 0 ? cost.rows[index - 1] : null, isLast: index === cost.rows.length - 1 });
    const figure = figureCell(formatCell(row.value, "usd_mmbtu", decimals, true), "value",
      [isTotal ? "num--total" : "", row.accent ? "text-accent" : ""].filter(Boolean).join(" "));
    figure.setAttribute("role", "cell");
    body.appendChild(el("tr", {
      class: isTotal ? "waterfall__row is-total" : "waterfall__row",
      attrs: { role: "row", "data-row": row.id },
    }, [nameCell, barCell, figure]));
  });

  const table = el("table", { class: "table waterfall", attrs: { role: "table" } }, [
    el("caption", { class: "visually-hidden", text: cost.table_caption }),
    el("thead", { attrs: { role: "rowgroup" } }, [
      el("tr", { attrs: { role: "row" } }, [
        el("th", { text: "Step", attrs: { scope: "col", role: "columnheader" } }),
        el("th", { class: "waterfall__bar-head", attrs: { scope: "col", role: "columnheader" } }, [el("span", { class: "visually-hidden", text: "Bar from the running total" })]),
        el("th", { class: "col-num", text: UNITS.usd_mmbtu, attrs: { scope: "col", role: "columnheader" } }),
      ]),
    ]),
    body,
  ]);
  inner.appendChild(el("div", { class: "block" }, [table]));

  // Every bar at the size of its cell, drawn again whenever the table resizes.
  const draw = () => {
    for (const item of barCells) {
      const width = item.cell.clientWidth;
      const height = item.cell.clientHeight;
      if (width === 0 || height === 0) continue;
      item.cell.replaceChildren(charts.waterfallBar({ width, height, row: item.row, previous: item.previous, isLast: item.isLast, scale }));
    }
  };
  if (typeof ResizeObserver === "function") new ResizeObserver(draw).observe(table);
  else window.addEventListener("resize", draw, { passive: true });
  draw();

  inner.appendChild(sentence("p", cost.end_segments, decimals, "block lead"));
  inner.appendChild(sentence("p", cost.source_segments, decimals, "source-line"));
  if (cost.others && cost.others.rows.length) {
    inner.appendChild(disclosure(cost.others.button, () => othersTable(cost.others, decimals)));
  }
}

/* The same steps for every route east, one column each. */
function othersTable(others, decimals) {
  const head = el("tr", {}, [el("th", { text: "Step", attrs: { scope: "col" } })]);
  for (const route of others.routes) head.appendChild(el("th", { class: "col-num", text: route.name, attrs: { scope: "col" } }));
  const body = el("tbody");
  for (const row of others.rows) {
    const tr = el("tr", { class: row.kind === "total" ? "is-total" : "", attrs: { "data-row": row.id } }, [el("th", { text: row.name, attrs: { scope: "row" } })]);
    for (const route of others.routes) {
      tr.appendChild(figureCell(formatCell(row.values[route.route], "usd_mmbtu", decimals, row.kind !== "level"), row.id, row.kind === "total" ? "num--total" : ""));
    }
    body.appendChild(tr);
  }
  return el("table", { class: "table" }, [el("caption", { text: others.caption }), el("thead", {}, [head]), body]);
}

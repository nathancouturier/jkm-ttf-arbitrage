/* section-netbacks.js
 *
 * "Netbacks", inside the Now view: the value at Sabine Pass of a cargo
 * delivered to Gate and to Futtsu by each route east. A table, one row per
 * destination and route: the route and what sets it apart (its gap to Gate, or
 * why it is closed), a bar from zero in a cell, the figure at the right. The
 * best route is the one accent bar; a route closed to a US cargo is an
 * outline, priced as if it were open. A dashed rule down the bar column marks
 * 115 percent of Henry Hub, the price below which a cargo is not worth
 * lifting, so the last clause of the verdict is read off the chart itself.
 *
 * The table is the text alternative of its own bars: every bar's value is the
 * figure in its row, so the bars are aria-hidden. At 600px and below each row
 * becomes two lines, as the waterfall's rows do, so the words wrap rather than
 * run off a narrow screen.
 *
 * Numeric literals: none.
 */

import { el, sentence, figureCell } from "./dom.js";
import { formatCell, UNITS } from "./format.js";
import * as charts from "./charts.js";

export const artifact = "now";
export const loading = "the netbacks of every route";

export function render(inner, data) {
  const decimals = data.conventions.decimals;
  const section = data.netbacks;
  const scale = [section.scale.low, section.scale.high];
  inner.appendChild(sentence("p", section.scale_segments, decimals, "lead"));

  const body = el("tbody", { attrs: { role: "rowgroup" } });
  const barCells = [];
  for (const row of section.rows) {
    const nameCell = el("th", { class: "waterfall__name", attrs: { scope: "row", role: "rowheader" } }, [
      el("span", { class: row.accent ? "waterfall__line text-accent" : "waterfall__line", text: row.name }),
      sentence("span", row.detail_segments, decimals, "waterfall__detail"),
    ]);
    const barCell = el("td", { class: "waterfall__bar", attrs: { role: "cell" } });
    barCells.push({ cell: barCell, row });
    const figure = figureCell(formatCell(row.value, "usd_mmbtu", decimals), "value", row.accent ? "text-accent" : "");
    figure.setAttribute("role", "cell");
    body.appendChild(el("tr", { class: "waterfall__row", attrs: { role: "row", "data-row": row.id } }, [nameCell, barCell, figure]));
  }
  const table = el("table", { class: "table waterfall netbacks", attrs: { role: "table" } }, [
    el("caption", { class: "visually-hidden", text: section.table_caption }),
    el("thead", { attrs: { role: "rowgroup" } }, [
      el("tr", { attrs: { role: "row" } }, [
        el("th", { text: "Destination and route", attrs: { scope: "col", role: "columnheader" } }),
        el("th", { class: "waterfall__bar-head", attrs: { scope: "col", role: "columnheader" } }, [el("span", { class: "visually-hidden", text: "Bar from zero" })]),
        el("th", { class: "col-num", text: UNITS.usd_mmbtu, attrs: { scope: "col", role: "columnheader" } }),
      ]),
    ]),
    body,
  ]);
  inner.appendChild(el("div", { class: "block" }, [table]));

  const draw = () => {
    for (const item of barCells) {
      const width = item.cell.clientWidth;
      const height = item.cell.clientHeight;
      if (width === 0 || height === 0) continue;
      item.cell.replaceChildren(charts.netbackBar({ width, height, row: item.row, scale, threshold: section.threshold }));
    }
  };
  if (typeof ResizeObserver === "function") new ResizeObserver(draw).observe(table);
  else window.addEventListener("resize", draw, { passive: true });
  draw();

  inner.appendChild(sentence("p", section.source_segments, decimals, "source-line"));
}

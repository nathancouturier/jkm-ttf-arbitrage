/* section-breakeven.js
 *
 * "Breakeven", inside the Now view: S*, the premium of JKM over TTF that makes
 * a route east pay as much as Gate, against the charter rate, one line per
 * open route east, at today's prices. Today's premium is the accent rule, the
 * reported charter rate a dashed rule; where a route's line crosses today's
 * premium is H*, the hire at which that route stops paying, marked with a
 * ringed dot. The chart the study exists for.
 *
 * S* is linear in hire, so each line is the two points data/now.json gives;
 * nothing is computed here. The routes are told apart by pattern and an end
 * label: Panama solid, Suez dashed, the Cape dotted.
 *
 * Numeric literals: none.
 */

import { el, sentence, disclosure, figureCell } from "./dom.js";
import { formatCell, segmentsText, UNITS } from "./format.js";
import * as charts from "./charts.js";

export const artifact = "now";
export const loading = "the breakeven premium of every route against the charter rate";

export function render(inner, data) {
  const decimals = data.conventions.decimals;
  const section = data.breakeven;
  const chart = el("div", { class: "chart-frame" });
  const block = el("figure", { class: "block" }, [chart]);

  const lines = section.lines.map((line) => ({
    route: line.route,
    pattern: line.pattern,
    points: line.points,
    hStar: line.h_star,
    label: line.label,
  }));
  charts.onWidthChange(chart, (width) => {
    chart.replaceChildren(charts.breakevenChart({
      width,
      xDomain: [section.x.low, section.x.high],
      yDomain: [section.y.low, section.y.high],
      xStep: section.x.step,
      yStep: section.y.step,
      xDivisor: section.x.divisor,
      lines,
      spread: { value: section.spread.value, label: segmentsText(section.spread.label_segments, decimals) },
      reported: section.reported ? { hire: section.reported.hire, label: segmentsText(section.reported.label_segments, decimals) } : null,
      words: {
        title: segmentsText(section.heading_segments, decimals),
        desc: segmentsText(section.desc_segments, decimals),
        xAxis: section.x.axis,
        yAxis: section.y.axis,
      },
    }));
  });

  block.appendChild(sentence("p", section.caption_segments, decimals, "source-line"));
  block.appendChild(sentence("p", section.source_segments, decimals, "source-line"));
  block.appendChild(disclosure("S* at each charter rate and H*, route by route", () => table(section, decimals)));
  inner.appendChild(block);
}

function table(section, decimals) {
  const body = el("tbody");
  for (const row of section.table.rows) {
    const tr = el("tr", { attrs: { "data-route": row.route } }, [el("th", { text: row.name, attrs: { scope: "row" } })]);
    for (const column of section.table.columns) {
      const value = row.values[column.id];
      tr.appendChild(figureCell(formatCell(value, column.format, decimals, column.signed === true), column.id, { missing: row.missing_words }));
    }
    body.appendChild(tr);
  }
  const head = el("tr", {}, [el("th", { text: "Route east", attrs: { scope: "col" } })]);
  for (const column of section.table.columns) {
    head.appendChild(el("th", { class: "col-num", text: column.head + ", " + UNITS[column.format], attrs: { scope: "col" } }));
  }
  return el("table", { class: "table" }, [sentence("caption", section.table.caption_segments, decimals), el("thead", {}, [head]), body]);
}

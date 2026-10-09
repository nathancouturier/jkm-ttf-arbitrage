/* section-flows.js
 *
 * "Where the cargoes went", inside the Now view: the latest months of US LNG
 * exports, the share that went to the JKM markets and to all of Asia, over the
 * model's arb at loading. Two panels on one month axis: the two share lines,
 * solid and dashed with a label at each end, then the arb as bars from a drawn
 * zero line, filled when positive and outlined when negative. Under it, the
 * regression on every month since 2016 and what it cannot separate.
 *
 * Every figure is from data/flows.json.
 *
 * Numeric literals: none.
 */

import { el, sentence, disclosure, figureCell, scrollTable } from "./dom.js";
import { formatCell, segmentsText, UNITS } from "./format.js";
import * as charts from "./charts.js";

export const artifact = "flows";
export const loading = "the monthly share of US exports to Asia against the arb";

export function render(inner, data) {
  const decimals = data.conventions.decimals;
  const panel = data.panel;
  const chart = el("div", { class: "chart-frame" });
  const block = el("figure", { class: "block" }, [chart]);

  const months = panel.months.map((month) => ({
    label: month.label,
    values: { share_jkm: month.share_jkm, share_asia: month.share_asia },
    arb: month.arb,
  }));
  charts.onWidthChange(chart, (width) => {
    chart.replaceChildren(charts.flowsChart({
      width,
      months,
      shares: panel.shares,
      shareDomain: [panel.share_domain.low, panel.share_domain.high],
      arbDomain: [panel.arb_domain.low, panel.arb_domain.high],
      shareStep: panel.share_domain.step,
      arbStep: panel.arb_domain.step,
      ticks: width < charts.GEOMETRY.NARROW_WIDTH ? panel.ticks_narrow : panel.ticks,
      words: {
        title: segmentsText(panel.heading_segments, decimals),
        desc: segmentsText(panel.desc_segments, decimals),
        shareAxis: panel.share_axis,
        arbAxis: panel.arb_axis,
      },
    }));
  });
  block.appendChild(sentence("p", panel.source_segments, decimals, "source-line"));
  block.appendChild(disclosure("The months in a table", () => table(panel, decimals)));
  inner.appendChild(block);
  for (const paragraph of panel.notes) inner.appendChild(sentence("p", paragraph, decimals, "block lead"));
}

function table(panel, decimals) {
  const body = el("tbody");
  for (const month of panel.months) {
    body.appendChild(el("tr", { attrs: { "data-month": month.month } }, [
      el("th", { text: month.label, attrs: { scope: "row" } }),
      figureCell(formatCell(month.share_jkm, "share_percent", decimals), "share_jkm", { missing: panel.missing_words }),
      figureCell(formatCell(month.share_asia, "share_percent", decimals), "share_asia", { missing: panel.missing_words }),
      figureCell(formatCell(month.arb, "usd_mmbtu", decimals, true), "arb", { missing: panel.arb_missing_words }),
    ]));
  }
  const table = el("table", { class: "table" }, [
    el("thead", {}, [el("tr", {}, [
      el("th", { text: "Month", attrs: { scope: "col" } }),
      el("th", { class: "col-num", text: "To the JKM markets, " + UNITS.share_percent, attrs: { scope: "col", "data-short": "JKM markets" } }),
      el("th", { class: "col-num", text: "To Asia, " + UNITS.share_percent, attrs: { scope: "col", "data-short": "Asia" } }),
      el("th", { class: "col-num", text: "Arb at loading, " + UNITS.usd_mmbtu, attrs: { scope: "col", "data-short": "arb" } }),
    ])]),
    body,
  ]);
  return scrollTable([panel.table_caption], table);
}

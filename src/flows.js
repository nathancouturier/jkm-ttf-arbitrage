/* flows.js
 *
 * The Flows view: did US cargoes follow the arb? Every month of US LNG
 * exports by vessel since 2016, the share to the JKM markets and to Asia over
 * the arb at loading; the regression of each share on the arb and the months
 * by sign; 2020, the lift margin when the notice to cancel was due, against
 * the cargoes EIA reported cancelled; 2026, the breakeven of Panama and of
 * the Cape against the route Platts reported US cargoes took; the waits at
 * Panama; and what the test cannot separate.
 *
 * Every figure and sentence is from data/flows.json. Numeric literals: none.
 */

import { el, sentence, disclosure, figureCell, scrollTable } from "./dom.js";
import { formatCell, formatDay, segmentsText, UNITS } from "./format.js";
import * as charts from "./charts.js";

export const artifacts = Object.freeze(["flows"]);

export function render(root, data) {
  const flows = data.flows;
  const page = flows.page;
  const decimals = flows.conventions.decimals;

  const title = sentence("h1", page.test.heading_segments, decimals, "view-title");
  title.id = "view-title";
  title.setAttribute("tabindex", "-1");
  root.appendChild(title);

  root.appendChild(wholeFigure(page.whole, decimals));
  root.appendChild(testBlock(page, decimals));
  root.appendChild(y2020Figure(page, decimals));
  root.appendChild(y2026Figure(page, decimals));
  root.appendChild(waitsBlock(page, decimals));
  root.appendChild(el("div", { class: "block" }, [sentence("p", page.limits_segments, decimals, "lead")]));
  return title;
}

function wholeFigure(panel, decimals) {
  const frame = el("div", { class: "chart-frame" });
  const months = panel.months.map((month) => ({
    label: month.label,
    values: { share_jkm: month.share_jkm, share_asia: month.share_asia },
    arb: month.arb,
  }));
  charts.onWidthChange(frame, (width) => {
    frame.replaceChildren(charts.flowsChart({
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
  return el("figure", { class: "block" }, [
    sentence("h2", panel.heading_segments, decimals, "block__heading"),
    frame,
    sentence("p", panel.source_segments, decimals, "source-line"),
    disclosure("Every month in a table", () => monthsTable(panel, decimals)),
  ]);
}

function monthsTable(panel, decimals) {
  const body = el("tbody");
  for (const month of panel.months) {
    body.appendChild(el("tr", {}, [
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

function testBlock(page, decimals) {
  const test = page.test;
  const body = el("tbody");
  for (const row of test.rows) {
    body.appendChild(el("tr", {}, [
      el("th", { text: row.share_words + ", " + row.sample + ", " + row.hire_level + " hire", attrs: { scope: "row" } }),
      figureCell(formatCell(row.n, "count", decimals), "n"),
      figureCell(formatCell(row.slope_pp, "pp", decimals, true), "slope_pp"),
      figureCell(formatCell(row.t, "t_stat", decimals), "t"),
      figureCell(formatCell(row.lags, "count", decimals), "lags"),
      figureCell(formatCell(row.r2, "r2", decimals), "r2"),
      figureCell(formatCell(row.open_above, "count", decimals), "open_above"),
      figureCell(formatCell(row.open_below, "count", decimals), "open_below"),
      figureCell(formatCell(row.closed_above, "count", decimals), "closed_above"),
      figureCell(formatCell(row.closed_below, "count", decimals), "closed_below"),
    ]));
  }
  const head = [
    ["Share, sample and hire", null], ["Months", "months"], ["Slope, points per $", "slope"], ["t", "t"],
    ["Lags", "lags"], ["R squared", "R2"], ["Open, share above median", "open, above"],
    ["Open, at or below", "open, below"], ["Closed, above", "closed, above"], ["Closed, at or below", "closed, below"],
  ];
  const table = el("table", { class: "table" }, [
    el("thead", {}, [el("tr", {}, head.map(([text, short], index) => el("th", {
      class: index === 0 ? null : "col-num", text, attrs: { scope: "col", "data-short": short },
    })))]),
    body,
  ]);
  return el("div", { class: "block" }, [
    el("h2", { class: "block__heading", text: page.words.test_heading }),
    sentence("p", test.sign_segments, decimals, "lead"),
    scrollTable([test.caption], table),
  ]);
}

function y2020Figure(page, decimals) {
  const y2020 = page.y2020;
  const frame = el("div", { class: "chart-frame" });
  const days = y2020.months.map((m) => m.month);
  charts.onWidthChange(frame, (width) => {
    frame.replaceChildren(charts.timeChart({
      width,
      days,
      first: days[0],
      last: days[days.length - 1],
      y: y2020.y,
      band: { low: y2020.months.map((m) => m.notice.low), high: y2020.months.map((m) => m.notice.high), label: page.words.band },
      reference: { values: y2020.months.map((m) => m.loading.central), label: page.words.loading },
      series: { values: y2020.months.map((m) => m.notice.central), label: page.words.notice },
      marks: [],
      rules: [],
      ticks: y2020.ticks,
      words: { title: segmentsText(y2020.heading_segments, decimals), desc: y2020.desc, yAxis: page.words.y_axis },
    }));
  });
  const body = el("tbody");
  for (const month of y2020.months) {
    const source = month.cancelled_url
      ? el("a", { class: "text-link", text: month.cancelled_source, attrs: { href: month.cancelled_url, rel: "noopener" } })
      : document.createTextNode("");
    body.appendChild(el("tr", {}, [
      el("th", { text: month.label, attrs: { scope: "row" } }),
      figureCell(formatCell(month.notice.low, "usd_mmbtu", decimals, true), "notice_low"),
      figureCell(formatCell(month.notice.central, "usd_mmbtu", decimals, true), "notice_central"),
      figureCell(formatCell(month.notice.high, "usd_mmbtu", decimals, true), "notice_high"),
      figureCell(formatCell(month.loading.central, "usd_mmbtu", decimals, true), "loading_central"),
      figureCell(formatCell(month.cancelled, "count", decimals), "cancelled", { missing: "none reported" }),
      el("td", { class: "words" }, [source]),
    ]));
  }
  const table = el("table", { class: "table" }, [
    el("thead", {}, [el("tr", {}, [
      el("th", { text: "Loading month", attrs: { scope: "col" } }),
      el("th", { class: "col-num", text: "At notice, low hire", attrs: { scope: "col", "data-short": "notice, low" } }),
      el("th", { class: "col-num", text: "At notice, central", attrs: { scope: "col", "data-short": "notice, central" } }),
      el("th", { class: "col-num", text: "At notice, high hire", attrs: { scope: "col", "data-short": "notice, high" } }),
      el("th", { class: "col-num", text: "At loading, central", attrs: { scope: "col", "data-short": "loading" } }),
      el("th", { class: "col-num", text: "Cargoes cancelled", attrs: { scope: "col", "data-short": "cancelled" } }),
      el("th", { text: "Reported by", attrs: { scope: "col" } }),
    ])]),
    body,
  ]);
  return el("figure", { class: "block" }, [
    el("h2", { class: "block__heading", text: page.words.y2020_heading }),
    sentence("p", y2020.heading_segments, decimals, "lead"),
    frame,
    el("p", { class: "source-line", text: page.words.y2020_legend }),
    sentence("p", y2020.caption_segments, decimals, "source-line"),
    disclosure("Each month's lift margin in a table, in " + UNITS.usd_mmbtu, () => scrollTable([page.words.y2020_caption], table)),
  ]);
}

function y2026Figure(page, decimals) {
  const y2026 = page.y2026;
  const frame = el("div", { class: "chart-frame" });
  charts.onWidthChange(frame, (width) => {
    frame.replaceChildren(charts.timeChart({
      width,
      days: y2026.days,
      first: y2026.days[0],
      last: y2026.days[y2026.days.length - 1],
      y: y2026.y,
      band: null,
      reference: null,
      references: [
        { values: y2026.panama, label: page.words.panama, pattern: "thin" },
        { values: y2026.cape, label: page.words.cape, pattern: "dot" },
      ],
      series: { values: y2026.spread, label: page.words.spread },
      marks: [],
      rules: [],
      ticks: y2026.ticks,
      words: { title: segmentsText(y2026.heading_segments, decimals), desc: y2026.desc, yAxis: page.words.y_axis },
    }));
  });
  const body = el("tbody");
  for (const row of y2026.compare) {
    body.appendChild(el("tr", {}, [
      el("th", { text: row.route === "panama" ? page.words.panama_route : page.words.cape_route, attrs: { scope: "row" } }),
      figureCell(formatCell(row.platts, "usd_mmbtu", decimals, true), "platts"),
      figureCell(formatCell(row.study.low, "usd_mmbtu", decimals, true), "study_low"),
      figureCell(formatCell(row.study.central, "usd_mmbtu", decimals, true), "study_central"),
      figureCell(formatCell(row.study.high, "usd_mmbtu", decimals, true), "study_high"),
    ]));
  }
  const compare = el("table", { class: "table" }, [
    el("thead", {}, [el("tr", {}, [
      el("th", { text: "Route", attrs: { scope: "col" } }),
      el("th", { class: "col-num", text: "Platts, " + formatDay(y2026.assessment_day), attrs: { scope: "col", "data-short": "Platts" } }),
      el("th", { class: "col-num", text: "This study, low hire", attrs: { scope: "col", "data-short": "low" } }),
      el("th", { class: "col-num", text: "Central hire", attrs: { scope: "col", "data-short": "central" } }),
      el("th", { class: "col-num", text: "High hire", attrs: { scope: "col", "data-short": "high" } }),
    ])]),
    body,
  ]);
  const reported = el("ul", { class: "credit-list" }, y2026.reported.map((item) => el("li", {}, [
    document.createTextNode(formatCell(item.figure, item.format, decimals, item.signed) + ": " + item.what + ". "),
    el("a", { class: "text-link", text: item.publisher, attrs: { href: item.url, rel: "noopener" } }),
  ])));
  return el("figure", { class: "block" }, [
    el("h2", { class: "block__heading", text: page.words.y2026_heading }),
    sentence("p", y2026.heading_segments, decimals, "lead"),
    frame,
    el("p", { class: "source-line", text: page.words.y2026_legend }),
    scrollTable([sentence("span", y2026.compare_caption_segments, decimals)], compare),
    disclosure("What Platts reported", () => reported),
  ]);
}

function waitsBlock(page, decimals) {
  const body = el("tbody");
  for (const row of page.waits.rows) {
    body.appendChild(el("tr", {}, [
      el("th", { text: row.label + ", " + row.hire_level + " hire", attrs: { scope: "row" } }),
      figureCell(formatCell(row.wait_reported, "days", decimals), "wait_reported"),
      figureCell(formatCell(row.wait_breakeven, "days", decimals), "wait_breakeven", { missing: "none" }),
      figureCell(formatCell(row.lead_no_wait, "usd_mmbtu", decimals, true), "lead_no_wait"),
      figureCell(formatCell(row.lead_with_wait, "usd_mmbtu", decimals, true), "lead_with_wait"),
    ]));
  }
  const table = el("table", { class: "table" }, [
    el("thead", {}, [el("tr", {}, [
      el("th", { text: "Month and hire", attrs: { scope: "col" } }),
      el("th", { class: "col-num", text: "Wait reported, days", attrs: { scope: "col", "data-short": "reported" } }),
      el("th", { class: "col-num", text: "Wait at which the two net the same, days", attrs: { scope: "col", "data-short": "breakeven" } }),
      el("th", { class: "col-num", text: "Panama over the Cape, no wait", attrs: { scope: "col", "data-short": "no wait" } }),
      el("th", { class: "col-num", text: "With the wait reported", attrs: { scope: "col", "data-short": "with wait" } }),
    ])]),
    body,
  ]);
  return el("div", { class: "block" }, [
    el("h2", { class: "block__heading", text: page.words.waits_heading }),
    sentence("p", page.waits.heading_segments, decimals, "lead"),
    scrollTable([page.words.waits_caption], table),
  ]);
}

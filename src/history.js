/* history.js
 *
 * The History view: JKM's premium over TTF against what the cheapest route
 * east needs, week by week from September 2021 and month by month from 2016,
 * and the hire at which that route nets what Gate does, against the charter
 * rates reported.
 *
 * THREE PANELS. The weekly spread over the band of S*, the breakeven spread
 * of the cheapest open route east, between the low and the high hire, its
 * middle line the central hire: where the spread line runs above that line
 * the arb east was open. The breakeven hire H* of the same route, with each
 * reported charter rate as a point, the latest in the accent: a rate below
 * the line is a week the arb was open at the market's own freight. The
 * monthly spread over the same band from 2016, with the change of price
 * definition in 2021 marked.
 *
 * RANGES. Named ranges cut the two weekly panels; each comes with its own
 * domains, ticks and sentences in data/history.json, and the address keeps
 * it: #/history?range=last_52. The breaks of the data are numbered rules,
 * listed in a table under the charts.
 *
 * Every figure and every sentence is from data/history.json. Numeric
 * literals: none.
 */

import { el, sentence, disclosure, figureCell, scrollTable, clear } from "./dom.js";
import { formatCell, formatDay, segmentsText, UNITS } from "./format.js";
import * as charts from "./charts.js";
import * as router from "./router.js";

export const artifacts = Object.freeze(["history"]);

const VIEW = "history";

let held = null;

function rangeFrom(route, page) {
  const asked = route && route.params ? route.params.range || "" : "";
  const ranges = page.weekly.ranges;
  const found = ranges.find((r) => r.id === asked);
  return { range: found || ranges[0], unknown: asked !== "" && !found ? asked : null };
}

export function render(root, data, route) {
  const history = data.history;
  const page = history.page;
  const decimals = history.conventions.decimals;
  const { range, unknown } = rangeFrom(route, page);
  held = { history, root };

  const title = sentence("h1", range.heading_segments, decimals, "view-title");
  title.id = "view-title";
  title.setAttribute("tabindex", "-1");
  root.appendChild(title);

  const choices = el("div", { class: "choice-row", attrs: { role: "group", "aria-label": "Weeks shown" } });
  for (const option of page.weekly.ranges) {
    const button = el("button", {
      class: "choice",
      text: option.label,
      attrs: { type: "button", "aria-pressed": option.id === range.id ? "true" : "false", "data-range": option.id },
    });
    button.addEventListener("click", () => {
      if (option.id !== range.id) router.go(VIEW, { range: option.id });
    });
    choices.appendChild(button);
  }
  root.appendChild(choices);
  if (unknown !== null) {
    root.appendChild(el("p", { class: "state-message", text: "The address names no range called " + JSON.stringify(unknown) + ", so every week is shown." }));
    router.replaceState(VIEW, { range: range.id });
  }

  root.appendChild(weeklyFigure(page, range, decimals));
  root.appendChild(hstarFigure(page, range, decimals));
  root.appendChild(monthlyFigure(page, decimals));
  root.appendChild(el("div", { class: "block" }, [
    el("h2", { class: "block__heading", text: "The breaks in the data" }),
    sentence("p", page.breaks_lead_segments, decimals, "lead"),
    breaksTable(page),
  ]));
  root.appendChild(sentence("p", page.source_segments, decimals, "source-line block"));
  return title;
}

export function update(root, route) {
  if (!held) return;
  clear(root);
  render(root, { history: held.history }, route);
  const pressed = root.querySelector('.choice[aria-pressed="true"]');
  if (pressed) pressed.focus();
}

/* The indexes of the weekly columns inside a range. */
function slice(weekly, range) {
  const out = [];
  weekly.day.forEach((day, index) => {
    if (day === null) {
      if (out.length && out[out.length - 1] !== null) out.push(null);
      return;
    }
    if (day >= range.first && day <= range.last) out.push(index);
  });
  return out;
}

function pick(column, indexes) {
  return indexes.map((index) => (index === null ? null : column[index]));
}

function weeklyFigure(page, range, decimals) {
  const weekly = page.weekly;
  const indexes = slice(weekly, range);
  const days = pick(weekly.day, indexes);
  const marks = [];
  indexes.forEach((index, at) => {
    if (index !== null && weekly.alignment[index] === "misaligned") marks.push({ index: at });
  });
  const frame = el("div", { class: "chart-frame" });
  charts.onWidthChange(frame, (width) => {
    frame.replaceChildren(charts.timeChart({
      width,
      days,
      first: range.first,
      last: range.last,
      y: range.y,
      band: { low: pick(weekly.s_low, indexes), high: pick(weekly.s_high, indexes), label: page.words.band },
      reference: { values: pick(weekly.s_central, indexes), label: page.words.reference },
      series: { values: pick(weekly.spread, indexes), label: page.words.spread },
      marks,
      rules: page.rules,
      ticks: range.ticks,
      words: { title: segmentsText(range.heading_segments, decimals), desc: segmentsText(range.desc_segments, decimals), yAxis: page.words.y_axis },
    }));
  });
  return el("figure", { class: "block", attrs: { "aria-labelledby": "view-title" } }, [
    frame,
    el("p", { class: "source-line", text: page.words.legend }),
    sentence("p", range.caption_segments, decimals, "source-line"),
    disclosure("The weeks by year, in a table", () => yearsTable(range.years, page.words.weeks, decimals)),
  ]);
}

function hstarFigure(page, range, decimals) {
  const weekly = page.weekly;
  const indexes = slice(weekly, range);
  const days = pick(weekly.day, indexes);
  const points = page.anchors
    .filter((a) => a.day >= range.first && a.day <= range.last)
    .map((a) => ({ day: a.day, value: a.hire_usd_day, accent: a.day === range.accent_day }));
  const frame = el("div", { class: "chart-frame" });
  charts.onWidthChange(frame, (width) => {
    frame.replaceChildren(charts.timeChart({
      width,
      days,
      first: range.first,
      last: range.last,
      y: { ...range.hstar, divisor: page.divisor },
      band: null,
      reference: null,
      series: { values: pick(weekly.h_star, indexes), label: page.words.h_star },
      marks: [],
      rules: page.rules,
      points,
      ticks: range.ticks,
      height: width < charts.GEOMETRY.NARROW_WIDTH ? charts.GEOMETRY.HSTAR_HEIGHT_NARROW : charts.GEOMETRY.HSTAR_HEIGHT,
      words: { title: segmentsText(range.hstar_heading_segments, decimals), desc: segmentsText(range.hstar_desc_segments, decimals), yAxis: page.words.hstar_axis },
    }));
  });
  return el("figure", { class: "block" }, [
    sentence("h2", range.hstar_heading_segments, decimals, "block__heading"),
    frame,
    el("p", { class: "source-line", text: page.words.hstar_legend }),
    sentence("p", range.hstar_caption_segments, decimals, "source-line"),
    disclosure("The charter rates reported, in a table", () => anchorsTable(page, decimals)),
  ]);
}

function monthlyFigure(page, decimals) {
  const monthly = page.monthly;
  const frame = el("div", { class: "chart-frame" });
  charts.onWidthChange(frame, (width) => {
    frame.replaceChildren(charts.timeChart({
      width,
      days: monthly.day,
      first: monthly.first,
      last: monthly.last,
      y: monthly.y,
      band: { low: monthly.s_low, high: monthly.s_high, label: page.words.band },
      reference: { values: monthly.s_central, label: page.words.reference },
      series: { values: monthly.spread, label: page.words.spread },
      marks: [],
      rules: page.rules,
      ticks: monthly.ticks,
      words: { title: segmentsText(monthly.heading_segments, decimals), desc: segmentsText(monthly.desc_segments, decimals), yAxis: page.words.y_axis },
    }));
  });
  return el("figure", { class: "block" }, [
    sentence("h2", monthly.heading_segments, decimals, "block__heading"),
    frame,
    el("p", { class: "source-line", text: page.words.legend }),
    sentence("p", monthly.caption_segments, decimals, "source-line"),
    disclosure("The months by year, in a table", () => yearsTable(monthly.years, page.words.months, decimals)),
  ]);
}

function yearsTable(years, unitWords, decimals) {
  const body = el("tbody");
  for (const year of years) {
    body.appendChild(el("tr", {}, [
      el("th", { text: String(year.year), attrs: { scope: "row" } }),
      figureCell(formatCell(year.count, "count", decimals), "count"),
      figureCell(formatCell(year.open, "count", decimals), "open"),
      figureCell(formatCell(year.ttf_above, "count", decimals), "ttf_above"),
    ]));
  }
  const table = el("table", { class: "table" }, [
    el("thead", {}, [el("tr", {}, [
      el("th", { text: "Year", attrs: { scope: "col" } }),
      el("th", { class: "col-num", text: unitWords.count, attrs: { scope: "col" } }),
      el("th", { class: "col-num", text: unitWords.open, attrs: { scope: "col" } }),
      el("th", { class: "col-num", text: unitWords.ttf_above, attrs: { scope: "col" } }),
    ])]),
    body,
  ]);
  return scrollTable([unitWords.caption], table);
}

function anchorsTable(page, decimals) {
  const body = el("tbody");
  for (const anchor of page.anchors) {
    body.appendChild(el("tr", {}, [
      el("th", { text: formatDay(anchor.day), attrs: { scope: "row" } }),
      figureCell(formatCell(anchor.hire_usd_day, "usd_day", decimals), "hire_usd_day"),
      el("td", { class: "words", text: anchor.assessment }),
      el("td", { class: "words", text: anchor.publisher }),
    ]));
  }
  const table = el("table", { class: "table" }, [
    el("thead", {}, [el("tr", {}, [
      el("th", { text: "Day", attrs: { scope: "col" } }),
      el("th", { class: "col-num", text: "Hire, " + UNITS.usd_day, attrs: { scope: "col" } }),
      el("th", { text: "Assessment", attrs: { scope: "col" } }),
      el("th", { text: "Reported by", attrs: { scope: "col" } }),
    ])]),
    body,
  ]);
  return scrollTable([page.words.anchors_caption], table);
}

function breaksTable(page) {
  const body = el("tbody");
  for (const item of page.breaks) {
    body.appendChild(el("tr", {}, [
      el("th", { text: String(item.number), attrs: { scope: "row" } }),
      el("td", { class: "nowrap", text: formatDay(item.day) }),
      el("td", { class: "words", text: item.kind_words }),
      el("td", { class: "words", text: item.what }),
      el("td", { class: "words", text: item.source }),
    ]));
  }
  const table = el("table", { class: "table table--bands" }, [
    el("thead", {}, [el("tr", {}, [
      el("th", { text: "Rule", attrs: { scope: "col" } }),
      el("th", { text: "From", attrs: { scope: "col" } }),
      el("th", { text: "Kind", attrs: { scope: "col" } }),
      el("th", { text: "What changes", attrs: { scope: "col" } }),
      el("th", { text: "Source", attrs: { scope: "col" } }),
    ])]),
    body,
  ]);
  return scrollTable([page.words.breaks_caption], table);
}

/* method.js
 *
 * The Method view: how a cargo is priced. The engine as formulas, each with
 * what it means; every parameter of the parameter table with its value, its
 * status, the document it is read in and the day; the units; the delivery
 * months; the limits of the study; the documents in full; and the credits.
 *
 * Every figure and sentence is from data/method.json. Numeric literals: none.
 */

import { el, sentence, figureCell, scrollTable } from "./dom.js";
import { formatCell, formatDay } from "./format.js";

export const artifacts = Object.freeze(["method"]);

const STATUS_WORDS = Object.freeze({ published: "published", derived: "derived", assumption: "this study's assumption" });

export function render(root, data) {
  const method = data.method;
  const decimals = method.conventions.decimals;

  const title = sentence("h1", method.title_segments, decimals, "view-title");
  title.id = "view-title";
  title.setAttribute("tabindex", "-1");
  root.appendChild(title);

  const engine = el("section", { class: "block", attrs: { "aria-labelledby": "method-engine" } }, [
    el("h2", { class: "block__heading", id: "method-engine", text: "The engine" }),
  ]);
  for (const item of method.formulas) {
    engine.appendChild(el("p", { class: "formula", text: item.formula }));
    engine.appendChild(sentence("p", item.segments, decimals, "prose"));
  }
  if (method.conventional) engine.appendChild(conventionalTable(method.conventional, decimals));
  root.appendChild(engine);

  root.appendChild(el("section", { class: "block", attrs: { "aria-labelledby": "method-parameters" } }, [
    el("h2", { class: "block__heading", id: "method-parameters", text: "The parameters" }),
    parametersTable(method),
  ]));

  const unitsBody = el("tbody");
  for (const unit of method.units) {
    unitsBody.appendChild(el("tr", {}, [
      el("th", { text: unit.words, attrs: { scope: "row" } }),
      figureCell(formatCell(unit.value, unit.format, decimals), "value"),
    ]));
  }
  root.appendChild(el("section", { class: "block", attrs: { "aria-labelledby": "method-units" } }, [
    el("h2", { class: "block__heading", id: "method-units", text: "Units and conversions" }),
    sentence("p", method.units_segments, decimals, "prose"),
    scrollTable(["The conversions the engine uses."], el("table", { class: "table" }, [
      el("thead", {}, [el("tr", {}, [
        el("th", { text: "Conversion", attrs: { scope: "col" } }),
        el("th", { class: "col-num", text: "Value", attrs: { scope: "col" } }),
      ])]),
      unitsBody,
    ])),
    ...(method.k_sensitivity ? [sensitivityTable(method.k_sensitivity, decimals)] : []),
  ]));

  root.appendChild(el("section", { class: "block", attrs: { "aria-labelledby": "method-delivery" } }, [
    el("h2", { class: "block__heading", id: "method-delivery", text: "Delivery months" }),
    sentence("p", method.delivery_segments, decimals, "prose"),
  ]));

  root.appendChild(el("section", { class: "block", attrs: { "aria-labelledby": "method-limits" } }, [
    el("h2", { class: "block__heading", id: "method-limits", text: "What the study cannot see" }),
    el("ul", { class: "credit-list" }, method.limits.map((segments) => sentence("li", segments, decimals, "prose"))),
  ]));

  root.appendChild(el("section", { class: "block", attrs: { "aria-labelledby": "method-documents" } }, [
    el("h2", { class: "block__heading", id: "method-documents", text: "The documents in full" }),
    el("ul", { class: "credit-list" }, method.documents.map((doc) => el("li", {}, [
      el("a", { class: "text-link", text: doc.label, attrs: { href: doc.href } }),
    ]))),
  ]));

  root.appendChild(el("section", { class: "block", attrs: { "aria-labelledby": "method-credits" } }, [
    el("h2", { class: "block__heading", id: "method-credits", text: "Credits" }),
    el("ul", { class: "credit-list" }, method.credits.map((words) => el("li", { class: "prose", text: words }))),
    el("p", { class: "source-line", text: method.type_words }),
  ]));
  return title;
}

/* The latest week at each energy content of a cubic metre: the convention's
 * range, so the reader sees how far it moves the answer. */
function sensitivityTable(sensitivity, decimals) {
  const head = el("tr", {}, [
    el("th", { text: "MMBtu a cubic metre", attrs: { scope: "col" } }),
    el("th", { class: "col-num", text: "Best netback", attrs: { scope: "col" } }),
  ]);
  for (const route of sensitivity.routes) {
    head.appendChild(el("th", { class: "col-num", text: "Arb via " + sensitivity.route_names[route], attrs: { scope: "col" } }));
    head.appendChild(el("th", { class: "col-num", text: "S* via " + sensitivity.route_names[route], attrs: { scope: "col" } }));
  }
  const body = el("tbody");
  for (const row of sensitivity.rows) {
    const cells = [
      el("th", { text: formatCell(row.k, "mmbtu_per_m3", decimals), attrs: { scope: "row" } }),
      figureCell(formatCell(row.best_netback, "usd_mmbtu", decimals), "best_netback"),
    ];
    for (const route of sensitivity.routes) {
      const lines = row.routes[route] || {};
      cells.push(figureCell(formatCell(lines.arb, "usd_mmbtu", decimals, true), "arb"));
      cells.push(figureCell(formatCell(lines.s_star, "usd_mmbtu", decimals, true), "s_star"));
    }
    body.appendChild(el("tr", {}, cells));
  }
  return scrollTable([sentence("span", sensitivity.caption_segments, decimals)],
    el("table", { class: "table" }, [el("thead", {}, [head]), body]));
}

/* The exact netback against the conventional one, for the latest week. */
function conventionalTable(conventional, decimals) {
  const body = el("tbody");
  for (const row of conventional.rows) {
    body.appendChild(el("tr", {}, [
      el("th", { text: row.name, attrs: { scope: "row" } }),
      figureCell(formatCell(row.exact, "usd_mmbtu", decimals), "exact"),
      figureCell(formatCell(row.conventional, "usd_mmbtu", decimals), "conventional"),
      figureCell(formatCell(row.difference, "usd_mmbtu", decimals, true), "difference"),
    ]));
  }
  return scrollTable([sentence("span", conventional.caption_segments, decimals)], el("table", { class: "table" }, [
    el("thead", {}, [el("tr", {}, [
      el("th", { text: "Destination and route", attrs: { scope: "col" } }),
      el("th", { class: "col-num", text: "Exact", attrs: { scope: "col" } }),
      el("th", { class: "col-num", text: "Conventional", attrs: { scope: "col" } }),
      el("th", { class: "col-num", text: "Difference", attrs: { scope: "col" } }),
    ])]),
    body,
  ]));
}

function parametersTable(method) {
  const body = el("tbody");
  for (const parameter of method.parameters) {
    const source = parameter.url
      ? el("a", { class: "text-link", text: parameter.source, attrs: { href: parameter.url, rel: "noopener" } })
      : document.createTextNode(parameter.source);
    body.appendChild(el("tr", { attrs: { "data-parameter": parameter.key } }, [
      el("th", { text: parameter.name, attrs: { scope: "row" } }),
      el("td", { class: "words", text: parameter.value_words }),
      el("td", { class: "words", text: STATUS_WORDS[parameter.status] || parameter.status }),
      el("td", { class: "words" }, [source]),
      el("td", { class: "nowrap", text: formatDay(parameter.read_on) }),
      el("td", { class: "words", text: parameter.note || "" }),
    ]));
  }
  const table = el("table", { class: "table table--bands" }, [
    el("thead", {}, [el("tr", {}, [
      el("th", { text: "Parameter", attrs: { scope: "col" } }),
      el("th", { text: "Value", attrs: { scope: "col" } }),
      el("th", { text: "Status", attrs: { scope: "col" } }),
      el("th", { text: "Source", attrs: { scope: "col" } }),
      el("th", { text: "Read on", attrs: { scope: "col" } }),
      el("th", { text: "Note", attrs: { scope: "col" } }),
    ])]),
    body,
  ]);
  return scrollTable([method.parameters_caption], table);
}

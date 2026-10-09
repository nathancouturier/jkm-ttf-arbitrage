/* routes.js
 *
 * The Routes view: the three ways from Sabine Pass to Futtsu and the one to
 * Gate, on a map drawn from the same lines the distances are measured on; a
 * table of each route's distance, days, round trip and tolls for a cargo
 * loading in the latest week; and when each route was open to a US cargo,
 * every band with its source.
 *
 * Every figure is from data/routes.json. The title states what the map shows,
 * and the timeline's heading what its bands show.
 *
 * Numeric literals: none.
 */

import { el, sentence, figureCell, scrollTable, disclosure } from "./dom.js";
import { formatCell, formatDay, segmentsText, UNITS } from "./format.js";
import { onWidthChange } from "./charts.js";
import { routeMap, routeTimeline } from "./map.js";

export const artifacts = Object.freeze(["routes"]);

export function render(root, data) {
  const routes = data.routes;
  const decimals = routes.conventions.decimals;
  const title = sentence("h1", routes.heading_segments, decimals, "view-title");
  title.id = "view-title";
  title.setAttribute("tabindex", "-1");
  root.appendChild(title);

  // The map, scaled to the column, scrolling sideways in its own box when the
  // column is narrower than the map's own width. Only then is the box a tab
  // stop, and only then is the sentence that says so shown; it first opens
  // with Sabine Pass at its left edge.
  const map = routeMap(routes.map, { title: segmentsText(routes.heading_segments, decimals) });
  const frame = el("div", { class: "map-frame", attrs: { role: "region", "aria-label": "Map of the routes" } }, [map]);
  const scrollNote = el("p", { class: "source-line", text: routes.map_scroll_words });
  scrollNote.hidden = true;
  let placed = false;
  onWidthChange(frame, () => {
    const overflows = frame.scrollWidth > frame.clientWidth;
    if (overflows) frame.tabIndex = 0;
    else frame.removeAttribute("tabindex");
    scrollNote.hidden = !overflows;
    if (overflows && !placed) {
      placed = true;
      frame.scrollLeft = routes.map.start_x / routes.map.width * map.getBoundingClientRect().width;
    }
  });
  root.appendChild(el("figure", { class: "block" }, [
    frame,
    scrollNote,
    sentence("p", routes.map_caption_segments, decimals, "source-line"),
    sentence("p", routes.source_segments, decimals, "source-line"),
  ]));

  root.appendChild(el("div", { class: "block" }, [routeTable(routes, decimals)]));

  const timelineTitle = segmentsText(routes.timeline_heading_segments, decimals);
  const timelineFrame = el("div", { class: "chart-frame" });
  onWidthChange(timelineFrame, (width) => {
    timelineFrame.replaceChildren(routeTimeline({
      width,
      timeline: routes.timeline,
      words: {
        title: timelineTitle,
        desc: segmentsText(routes.timeline_caption_segments, decimals) + " " +
          routes.timeline.rows.map((row) => row.name + ": " + row.bands.map((band) => band.state_words + " from " + formatDay(band.start) + " to " + formatDay(band.end)).join(", then ")).join(". ") + ".",
      },
    }));
  });
  root.appendChild(el("figure", { class: "block" }, [
    sentence("h2", routes.timeline_heading_segments, decimals, "block__heading"),
    timelineFrame,
    sentence("p", routes.timeline_caption_segments, decimals, "source-line"),
    disclosure("Every band with its dates, what the record shows and its source", () => bandTable(routes)),
  ]));
  return title;
}

function routeTable(routes, decimals) {
  const head = el("tr", {}, [
    el("th", { text: "Route", attrs: { scope: "col" } }),
    el("th", { class: "col-num", text: "Distance, " + UNITS.nm, attrs: { scope: "col", "data-short": "distance" } }),
    el("th", { class: "col-num", text: "Days at sea one way", attrs: { scope: "col", "data-short": "days at sea" } }),
    el("th", { class: "col-num", text: "Round trip, days", attrs: { scope: "col", "data-short": "round trip" } }),
    el("th", { class: "col-num", text: "Toll laden, $", attrs: { scope: "col", "data-short": "toll laden" } }),
    el("th", { class: "col-num", text: "Toll ballast, $", attrs: { scope: "col", "data-short": "toll ballast" } }),
    el("th", { text: "In the latest week", attrs: { scope: "col", "data-short": "latest week" } }),
  ]);
  const body = el("tbody");
  for (const row of routes.rows) {
    body.appendChild(el("tr", { attrs: { "data-route": row.route } }, [
      el("th", { text: row.name, attrs: { scope: "row" } }),
      figureCell(formatCell(row.distance_nm, "nm", decimals), "distance_nm"),
      figureCell(formatCell(row.sea_days, "days", decimals), "sea_days"),
      figureCell(formatCell(row.days_total, "days", decimals), "days_total"),
      figureCell(formatCell(row.canal_laden_usd, "usd", decimals), "canal_laden_usd"),
      figureCell(formatCell(row.canal_ballast_usd, "usd", decimals), "canal_ballast_usd"),
      el("td", { class: "words", text: row.status_words }),
    ]));
  }
  const table = el("table", { class: "table table--routes" }, [el("thead", {}, [head]), body]);
  return scrollTable([sentence("span", routes.table_caption_segments, decimals)], table);
}

function bandTable(routes) {
  const head = el("tr", {}, [
    el("th", { text: "Route", attrs: { scope: "col" } }),
    el("th", { text: "From", attrs: { scope: "col" } }),
    el("th", { text: "To", attrs: { scope: "col" } }),
    el("th", { text: "State", attrs: { scope: "col" } }),
    el("th", { text: "What the record shows", attrs: { scope: "col" } }),
    el("th", { text: "Source", attrs: { scope: "col" } }),
  ]);
  const body = el("tbody");
  for (const row of routes.timeline.rows) {
    for (const band of row.bands) {
      // The link carries the name of the document it opens, and only that;
      // the other sources of the band follow as plain text.
      const label = band.url && band.link_label && band.source.startsWith(band.link_label) ? band.link_label : null;
      const source = label
        ? [el("a", { class: "text-link", text: label, attrs: { href: band.url, rel: "noopener" } }),
          document.createTextNode(band.source.slice(label.length))]
        : [document.createTextNode(band.source)];
      body.appendChild(el("tr", {}, [
        el("th", { text: row.name, attrs: { scope: "row" } }),
        el("td", { class: "nowrap", text: formatDay(band.start) }),
        el("td", { class: "nowrap", text: formatDay(band.end) }),
        el("td", { class: "words", text: band.state_words }),
        el("td", { class: "words", text: band.words }),
        el("td", { class: "words" }, source),
      ]));
    }
  }
  const table = el("table", { class: "table table--bands" }, [el("thead", {}, [head]), body]);
  return scrollTable(["Every band of the timeline: its dates, its state, what the record shows and the source of it."], table);
}

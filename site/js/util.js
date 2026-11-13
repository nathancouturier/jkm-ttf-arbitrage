// Formatting, a small DOM builder and the page state kept in the address.

const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

export const ROUTES = {
  europe: { name: "Gate", via: "to Europe", long: "Sabine Pass to Gate", cls: "c-europe", color: "var(--europe)" },
  panama: { name: "Panama", via: "via Panama", long: "Sabine Pass to Futtsu via Panama", cls: "c-panama", color: "var(--panama)" },
  suez: { name: "Suez", via: "via Suez", long: "Sabine Pass to Futtsu via Suez", cls: "c-suez", color: "var(--suez)" },
  cape: { name: "the Cape", via: "via the Cape", long: "Sabine Pass to Futtsu via the Cape of Good Hope", cls: "c-cape", color: "var(--cape)" },
};
export const EAST = ["panama", "suez", "cape"];

export function num(x, digits = 2) {
  if (x == null || Number.isNaN(x)) return "";
  const s = Math.abs(x).toLocaleString("en-GB", { minimumFractionDigits: digits, maximumFractionDigits: digits });
  return (x < 0 && Number(s.replace(/,/g, "")) !== 0 ? "-" : "") + s;
}
export const signed = (x, digits = 2) => (x > 0 ? "+" : "") + num(x, digits);
export const clamp = (x, lo, hi) => Math.min(hi, Math.max(lo, x));
export const int = (x) => num(Math.round(x), 0);
export const pct = (x, digits = 0) => num(x * 100, digits) + " percent";
export const musd = (x, digits = 2) => num(x / 1e6, digits);

export function day(iso, short = false) {
  const [y, m, d] = iso.split("-").map(Number);
  const month = short ? MONTHS[m - 1].slice(0, 3) : MONTHS[m - 1];
  return d ? `${d} ${month} ${y}` : `${month} ${y}`;
}
export const month = (iso, short = false) => day(iso.slice(0, 7), short);
export const toDate = (iso) => new Date(iso.length === 7 ? iso + "-15T00:00:00Z" : iso + "T00:00:00Z");

// h("p", {class: "x"}, "text", node) builds an element; text is always set as text.
export function h(tag, attrs, ...children) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v == null || v === false) continue;
    if (k === "class") el.className = v;
    else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else if (k === "html") el.innerHTML = v;
    else el.setAttribute(k, v === true ? "" : v);
  }
  for (const c of children.flat(Infinity)) {
    if (c == null || c === false) continue;
    el.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
  return el;
}

export const b = (text) => h("b", null, text);

// Replaces an element's content; nested lists are flattened and empty items dropped.
export function put(el, ...children) {
  el.replaceChildren(...children.flat(Infinity).filter((c) => c != null && c !== false));
  return el;
}

// A status word after a value: nothing for an observed input, a quiet mark for a held or assumed one.
export function tag(status) {
  if (!status || status === "observed" || status === "reported") return null;
  const word = { held: "held", assumed: "assumed", derived: "derived", "month to date": "month to date" }[status] || status;
  return h("span", { class: "tag " + (status === "assumed" ? "assumed" : "held"), title: word }, " " + word);
}

export function segmented(label, options, value, onChange) {
  const group = h("div", { class: "seg", role: "group", "aria-label": label });
  for (const [key, text] of options) {
    group.append(h("button", { type: "button", "aria-pressed": String(key === value), "data-focus": `${label}-${key}`, onclick: () => onChange(key) }, text));
  }
  return h("div", null, h("span", { class: "seg-label" }, label), group);
}

export function panel(title, body, open = false) {
  return h("details", { class: "panel", open }, h("summary", null, title), h("div", { class: "body" }, body));
}

export function table(columns, rows, opts = {}) {
  const head = h("tr", null, columns.map((c) => h("th", { class: c.n ? "n" : null, scope: "col" }, c.label)));
  const body = rows.map((r) => h("tr", null, columns.map((c) => {
    const v = c.value(r);
    const cls = [c.n ? "n" : "", c.cls ? c.cls(r) : ""].join(" ").trim();
    return h(c.head ? "th" : "td", { class: cls || null, scope: c.head ? "row" : null, "data-label": opts.stack && !c.head ? c.label : null }, v);
  })));
  // A table with many columns keeps a readable width and scrolls sideways on a narrow screen.
  // A stacked table instead sets each row as a block there, every cell under its column's name.
  const t = h("table", { class: opts.stack ? "stack" : null, style: opts.min && !opts.stack ? `min-width:${opts.min}px` : null },
    opts.caption ? h("caption", null, opts.caption) : null,
    opts.widths ? h("colgroup", null, opts.widths.map((w) => h("col", { style: `width:${w}` }))) : null, h("thead", null, head), h("tbody", null, body));
  return h("div", { class: "scroll" + (opts.tall ? " tall" : "") }, t);
}

// -- the address: #/view?key=value ------------------------------------------------------------
export function readHash() {
  const raw = location.hash.replace(/^#\/?/, "");
  const [view, query] = raw.split("?");
  return { view: view || "reroute", params: Object.fromEntries(new URLSearchParams(query || "")) };
}
export function writeHash(view, params, replace = true) {
  const q = new URLSearchParams(Object.entries(params).filter(([, v]) => v != null && v !== "")).toString();
  const hash = "#/" + (view === "reroute" ? "" : view) + (q ? "?" + q : "");
  if (replace) history.replaceState(null, "", hash || "#/");
  else location.hash = hash;
}

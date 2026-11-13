// SVG chart parts on top of d3: a frame, axes, direct labels and a hover layer with a tooltip.
// Every chart is redrawn at its container's width, so the same code serves 1440 and 390 pixels.

import { h } from "./util.js";

const d3 = window.d3;
const NS = "http://www.w3.org/2000/svg";

export function s(name, attrs, parent, text) {
  const el = document.createElementNS(NS, name);
  for (const [k, v] of Object.entries(attrs || {})) if (v != null) el.setAttribute(k, v);
  if (text != null) el.textContent = text;
  if (parent) parent.append(el);
  return el;
}

// A plot inside a container: returns the svg, the inner group and the inner size.
export function frame(container, { height, margin, label, focusable = true }) {
  container.replaceChildren();
  container.classList.add("plot");
  const W = Math.max(280, Math.round(container.clientWidth || 600));
  const svg = s("svg", { viewBox: `0 0 ${W} ${height}`, role: "img", "aria-label": label, tabindex: focusable ? "0" : null }, container);
  const g = s("g", { transform: `translate(${margin.left},${margin.top})` }, svg);
  const tip = h("div", { class: "tip", hidden: true, role: "status" });
  container.append(tip);
  return { svg, g, tip, W, H: height, w: W - margin.left - margin.right, h: height - margin.top - margin.bottom, margin, container };
}

export function axisX(c, scale, { values, format, label, y }) {
  const g = s("g", { class: "tick", transform: `translate(0,${y ?? c.h})` }, c.g);
  s("line", { class: "zero", x1: 0, x2: c.w, y1: 0, y2: 0 }, g);
  for (const v of values) {
    const x = scale(v);
    if (x < -1 || x > c.w + 1) continue;
    s("line", { class: "zero", x1: x, x2: x, y1: 0, y2: 5 }, g);
    s("text", { x, y: 19, "text-anchor": x > c.w - 18 && c.margin.right < 30 ? "end" : "middle" }, g, format(v));
  }
  if (label) s("text", { class: "axis-label", x: c.w, y: 38, "text-anchor": "end" }, c.g.appendChild(s("g", { transform: `translate(0,${y ?? c.h})` })), label);
  return g;
}

export function axisY(c, scale, { values, format, label, zero = true }) {
  const g = s("g", { class: "tick" }, c.g);
  for (const v of values) {
    const y = scale(v);
    if (y < -1 || y > c.h + 1) continue;
    s("line", { class: v === 0 && zero ? "zero" : "grid", x1: 0, x2: c.w, y1: y, y2: y }, g);
    s("text", { x: -8, y: y + 4, "text-anchor": "end" }, g, format(v));
  }
  if (label) s("text", { class: "axis-label", x: -c.margin.left + 2, y: -12 }, c.g, label);
  return g;
}

export function path(c, points, attrs) {
  const d = d3.line().defined((p) => p[1] != null && !Number.isNaN(p[1]))(points);
  return s("path", { d, fill: "none", "stroke-width": 2, "stroke-linejoin": "round", "stroke-linecap": "round", ...attrs }, c.g);
}

export function dot(c, x, y, color, r = 4.5) {
  return s("circle", { cx: x, cy: y, r, fill: color, stroke: "var(--paper)", "stroke-width": 2 }, c.g);
}

// Direct labels at given heights, pushed apart when they would overlap.
export function endLabels(c, labels, { x, anchor = "start", gap = 15 }) {
  const sorted = labels.filter((l) => l.y != null).sort((a, b) => a.y - b.y);
  for (let i = 1; i < sorted.length; i += 1) if (sorted[i].y - sorted[i - 1].y < gap) sorted[i].y = sorted[i - 1].y + gap;
  for (let i = sorted.length - 2; i >= 0; i -= 1) if (sorted[i + 1].y > c.h + 4 && sorted[i + 1].y - sorted[i].y < gap) sorted[i].y = sorted[i + 1].y - gap;
  for (const l of sorted) {
    const t = s("text", { class: "label halo", x, y: l.y + 4, "text-anchor": anchor }, c.g);
    s("tspan", { fill: l.color }, t, "● ");
    s("tspan", null, t, l.text);
    if (l.sub) s("tspan", { class: "label-sub", dx: 6 }, t, l.sub);
  }
}

// The tooltip: a head line, then rows with the value leading in weight.
export function showTip(c, x, y, head, rows, note) {
  const tip = c.tip;
  tip.replaceChildren(h("div", { class: "t-head" }, head));
  for (const r of rows) {
    if (!r) continue;
    tip.append(h("div", { class: "t-row" },
      r.key ? h("span", { class: "key " + r.key }) : null,
      h("span", { class: "k" }, r.label), h("span", { class: "v" }, r.value)));
  }
  if (note) tip.append(h("div", { class: "t-note" }, note));
  tip.hidden = false;
  const box = c.container.getBoundingClientRect();
  const scale = box.width / c.W;
  const px = (x + c.margin.left) * scale;
  const py = (y + c.margin.top) * scale;
  const tw = tip.offsetWidth;
  const left = px + 14 + tw > box.width ? Math.max(0, px - tw - 14) : px + 14;
  tip.style.left = left + "px";
  tip.style.top = Math.max(0, py - tip.offsetHeight / 2) + "px";
}

// Pointer and keyboard on the plot area: calls move(index) with the nearest position, and leave().
export function hover(c, { count, toIndex, move, leave, start }) {
  const hit = s("rect", { x: 0, y: 0, width: c.w, height: c.h, fill: "transparent" }, c.g);
  let current = null;
  const go = (i) => {
    current = Math.max(0, Math.min(count - 1, i));
    move(current);
  };
  const out = () => {
    current = null;
    c.tip.hidden = true;
    leave();
  };
  const at = (event) => {
    const box = c.svg.getBoundingClientRect();
    go(toIndex(((event.clientX - box.left) / box.width) * c.W - c.margin.left));
  };
  hit.addEventListener("pointermove", at);
  hit.addEventListener("pointerdown", at);
  hit.addEventListener("pointerleave", out);
  c.svg.addEventListener("keydown", (event) => {
    const step = { ArrowLeft: -1, ArrowRight: 1, PageUp: -10, PageDown: 10 }[event.key];
    if (event.key === "Escape") return out();
    if (event.key === "Home") { event.preventDefault(); return go(0); }
    if (event.key === "End") { event.preventDefault(); return go(count - 1); }
    if (!step) return undefined;
    event.preventDefault();
    return go((current ?? (start ?? count - 1)) + step);
  });
  c.svg.addEventListener("blur", out);
}

export function niceTicks(lo, hi, count = 6) {
  return d3.ticks(lo, hi, count);
}

export { d3 };

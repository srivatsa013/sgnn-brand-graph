"""Brand graph. Reads only files in this folder. Writes nothing."""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
FOOTER = "Demo build. Illustrative estimates from a model on an augmented dataset; see the accompanying presentation for details."

PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<style>
  html, body { margin: 0; height: 100%; background: #fafafa; color: #111827;
    font-family: "Helvetica Neue", Helvetica, Arial, sans-serif; }
  .wrap { height: 100%; display: flex; flex-direction: column; }
  .topbar { display: flex; flex-wrap: wrap; align-items: flex-end; gap: 12px 16px;
    padding: 12px 18px 6px; background: #fafafa; }
  .field { display: flex; flex-direction: column; gap: 3px; }
  .field > span { font-size: 12px; color: #6b7280; font-weight: 400; letter-spacing: 0.01em; }
  input[type="search"], button { background: #fafafa; color: #111827; border: 1px solid #d1d5db;
    border-radius: 2px; font-family: inherit; font-size: 13px; }
  input[type="search"] { padding: 0 10px; height: 32px; width: min(220px, 70vw); outline: none; }
  input[type="search"]:focus, button:focus { border-color: #111827; outline: none; }
  .choices { display: flex; gap: 6px; }
  .choices button { height: 32px; padding: 0 10px; cursor: pointer; }
  .choices button.on { border-color: #111827; }
  input[type="range"] { -webkit-appearance: none; appearance: none; width: 112px; height: 32px; background: transparent; margin: 0; }
  input[type="range"]::-webkit-slider-runnable-track { height: 1px; background: #d1d5db; }
  input[type="range"]::-webkit-slider-thumb { -webkit-appearance: none; width: 12px; height: 12px; margin-top: -6px;
    border-radius: 50%; background: #111827; cursor: pointer; border: 0; }
  input[type="range"]::-moz-range-track { height: 1px; background: #d1d5db; border: 0; }
  input[type="range"]::-moz-range-thumb { width: 12px; height: 12px; border: 0; border-radius: 50%; background: #111827; cursor: pointer; }
  #play { height: 32px; padding: 0 12px; cursor: pointer; background: transparent; }
  #summary { margin: 0; min-height: 0; padding: 0 18px 4px; font-size: 12px; line-height: 1.35; color: #6b7280; font-weight: 400; }
  #summary:empty { display: none; }
  #stage { position: relative; flex: 1; min-height: 0; }
  #net { position: absolute; inset: 0; }
  .legend { display: flex; align-items: center; gap: 6px; flex: 0 0 auto;
    padding: 4px 14px 6px; color: #6b7280; font-size: 11px; font-weight: 400; background: #fafafa; }
  .swatch { width: 14px; height: 8px; display: inline-block; }
  .swatch.down { background: #b23a48; }
  .swatch.mid { width: 22px; background: linear-gradient(90deg, #b23a48, #e5e7eb 50%, #2f855a); }
  .swatch.up { background: #2f855a; }
</style>
</head>
<body>
<div class="wrap">
  <div class="topbar" id="controls">
    <label class="field"><span>Brand</span><input id="search" type="search" placeholder="Search" list="names" autocomplete="off" /></label>
    <datalist id="names"></datalist>
    <div class="field"><span>News</span>
      <div class="choices">
        <button type="button" id="pos" class="on">Positive</button>
        <button type="button" id="neg">Negative</button>
      </div>
    </div>
    <label class="field"><span>Size</span><input id="size" type="range" min="0.5" max="2" step="0.01" value="1" /></label>
    <label class="field"><span>Strength</span><input id="strength" type="range" min="0.5" max="5" step="0.01" value="1" /></label>
    <label class="field"><span>Day</span><input id="day" type="range" min="0" max="7" step="0.01" value="0" /></label>
    <button type="button" id="play">Play</button>
  </div>
  <p id="summary"></p>
  <div id="stage">
    <div id="net"></div>
  </div>
  <div class="legend"><span>Down</span><i class="swatch down"></i><i class="swatch mid"></i><i class="swatch up"></i><span>Up</span></div>
</div>
<script type="application/json" id="graph">__GRAPH__</script>
<script>__VIS__</script>
<script>
const graph = JSON.parse(document.getElementById("graph").textContent);
const UP = "#2f855a";
const DOWN = "#b23a48";
const DIM = "#e5e7eb";
const INK = "#111827";
const EDGE = "#9ca3af";
const MAX_HOPS = 2;
const byId = {};
graph.nodes.forEach(node => { byId[node.id] = node; });
function sameCluster(left, right) {
  const a = byId[left] && byId[left].ecosystem;
  const b = byId[right] && byId[right].ecosystem;
  return !!(a && a === b);
}
let newsSign = 1;
let selected = null;
let day = 0;
let playing = false;
let hovered = null;
let paths = null;

function ramp(dayValue, hop) {
  const start = hop - 1;
  if (dayValue <= start) return 0;
  const span = 7 - start;
  if (span <= 0) return 1;
  return Math.max(0, Math.min(1, (dayValue - start) / span));
}
function response(edgeSign, magnitude, hop, dayValue) {
  if (hop > MAX_HOPS || edgeSign === 0 || magnitude === 0) return 0;
  const size = Number(document.getElementById("size").value);
  const scenario = Number(document.getElementById("strength").value);
  return newsSign * edgeSign * magnitude * scenario * size * ramp(dayValue, hop);
}
function walk(origin) {
  const outgoing = {};
  graph.links.forEach(link => {
    if (link.sign === 0) return;
    (outgoing[link.src] = outgoing[link.src] || []).push(link);
  });
  const dist = {};
  const arrivedSign = {};
  const arrivedKind = {};
  const parent = {};
  dist[origin] = 0;
  const queue = [origin];
  while (queue.length) {
    const node = queue.shift();
    if (dist[node] >= MAX_HOPS) continue;
    const parentSign = node === origin ? 1 : arrivedSign[node];
    (outgoing[node] || []).forEach(link => {
      const nxt = link.dst;
      const hop = dist[node] + 1;
      if (hop > MAX_HOPS) return;
      const sign = parentSign === 0 ? 0 : parentSign * link.sign;
      if (!(nxt in dist)) {
        dist[nxt] = hop;
        arrivedSign[nxt] = sign;
        arrivedKind[nxt] = link.kind;
        parent[nxt] = { prev: node, link };
        queue.push(nxt);
      } else if (dist[nxt] === hop && arrivedSign[nxt] !== sign) {
        arrivedSign[nxt] = 0;
      }
    });
  }
  const edgesOf = {};
  Object.keys(parent).forEach(node => {
    const edges = [];
    let cur = node;
    while (cur !== origin) {
      const step = parent[cur];
      edges.push(step.link);
      cur = step.prev;
    }
    edges.reverse();
    edgesOf[node] = edges;
  });
  return { dist, arrivedSign, arrivedKind, edgesOf };
}
function shiftsAt(dayValue) {
  const values = {};
  if (!selected || !paths) return values;
  Object.keys(paths.dist).forEach(id => {
    if (id === selected) return;
    const hop = paths.dist[id];
    if (hop === 1) values[id] = response(paths.arrivedSign[id], graph.magnitudes[paths.arrivedKind[id]] || 0, 1, dayValue);
    else if (hop === 2) {
      const first = (paths.edgesOf[id] || [])[0];
      const second = (paths.edgesOf[id] || [])[1];
      if (!first || !second) return;
      const firstEffect = response(first.sign, graph.magnitudes[first.kind] || 0, 1, dayValue);
      values[id] = 0.5 * firstEffect * second.sign;
    }
  });
  return values;
}
const FIRST = ["iPhone", "MacBook", "Apple CEO", "Dell", "HPQ", "LOGI", "Samsung"];
function ordered(names) {
  return names.slice().sort((a, b) => {
    const ia = FIRST.indexOf(a);
    const ib = FIRST.indexOf(b);
    if (ia < 0 && ib < 0) return a < b ? -1 : a > b ? 1 : 0;
    if (ia < 0) return 1;
    if (ib < 0) return -1;
    return ia - ib;
  });
}
function clause(names, verb) {
  if (!names.length) return "";
  const shown = ordered(names).slice(0, 8);
  const extra = names.length - shown.length;
  let body;
  if (extra) body = shown.join(", ") + " and " + extra + " more";
  else if (shown.length === 1) body = shown[0];
  else if (shown.length === 2) body = shown[0] + " and " + shown[1];
  else body = shown.slice(0, -1).join(", ") + " and " + shown[shown.length - 1];
  return body + " " + (names.length === 1 ? verb + "s" : verb);
}
function summaryLine() {
  if (!selected) return "";
  const values = shiftsAt(7);
  const fall = Object.keys(values).filter(id => values[id] < 0);
  const rise = Object.keys(values).filter(id => values[id] > 0);
  const parts = [];
  if (rise.length) parts.push(clause(rise, "rise"));
  if (fall.length) parts.push(clause(fall, "fall"));
  const polarity = newsSign > 0 ? "Positive" : "Negative";
  const detail = parts.length ? parts.join("; ") : "no neighbor moves";
  return polarity + " news at " + selected + ": " + detail;
}
function mix(value, scale) {
  if (!scale || Math.abs(value) < 1e-8) return DIM;
  const t = Math.max(-1, Math.min(1, value / scale));
  const dest = t >= 0 ? [47, 133, 90] : [178, 58, 72];
  const base = [229, 231, 235];
  const amount = Math.abs(t);
  const rgb = base.map((channel, index) => Math.round(channel + (dest[index] - channel) * amount));
  return "rgb(" + rgb.join(",") + ")";
}
const home = {};
const pos = {};
graph.nodes.forEach(node => {
  home[node.id] = { x: node.x, y: node.y };
  pos[node.id] = { x: node.x, y: node.y };
});
const springs = graph.draw.map(edge => [edge.src, edge.dst, sameCluster(edge.src, edge.dst)]);
const INTRA = 1;
const CROSS = 0.02;
for (let step = 0; step < 40; step++) {
  const force = {};
  graph.nodes.forEach(node => { force[node.id] = { x: 0, y: 0 }; });
  for (let i = 0; i < graph.nodes.length; i++) {
    const a = graph.nodes[i];
    for (let j = i + 1; j < graph.nodes.length; j++) {
      const b = graph.nodes[j];
      if (a.ecosystem !== b.ecosystem) continue;
      let dx = pos[b.id].x - pos[a.id].x;
      let dy = pos[b.id].y - pos[a.id].y;
      const dist2 = dx * dx + dy * dy;
      if (dist2 > 160 * 160 || dist2 === 0) continue;
      const dist = Math.sqrt(dist2);
      const push = 260 / dist2;
      dx /= dist;
      dy /= dist;
      force[a.id].x -= dx * push;
      force[a.id].y -= dy * push;
      force[b.id].x += dx * push;
      force[b.id].y += dy * push;
    }
  }
  springs.forEach(pair => {
    const a = pair[0];
    const b = pair[1];
    let dx = pos[b].x - pos[a].x;
    let dy = pos[b].y - pos[a].y;
    const dist = Math.sqrt(dx * dx + dy * dy) || 1;
    const pull = (dist - 42) * (pair[2] ? INTRA : CROSS) * 0.04;
    dx /= dist;
    dy /= dist;
    force[a].x += dx * pull;
    force[a].y += dy * pull;
    force[b].x -= dx * pull;
    force[b].y -= dy * pull;
  });
  graph.nodes.forEach(node => {
    if (node.kind === "brand") return;
    force[node.id].x += (home[node.id].x - pos[node.id].x) * 0.12;
    force[node.id].y += (home[node.id].y - pos[node.id].y) * 0.12;
    let mx = force[node.id].x * 0.2;
    let my = force[node.id].y * 0.2;
    const mag = Math.sqrt(mx * mx + my * my);
    if (mag > 4) { mx *= 4 / mag; my *= 4 / mag; }
    pos[node.id].x += mx;
    pos[node.id].y += my;
  });
}
const basePos = {};
graph.nodes.forEach(node => { basePos[node.id] = { x: pos[node.id].x, y: pos[node.id].y }; });
function dotSize(node) {
  return node.kind === "brand" ? 8 : 5;
}
function showLabel(id) {
  if (id === hovered) return true;
  const scale = network ? network.getScale() : 1;
  if (scale >= 1.2) return true;
  if (selected && id === selected) return true;
  return !!(byId[id] && byId[id].kind === "brand");
}
function sameEcosystem(left, right) {
  return sameCluster(left, right);
}
function edgeWidth(edge, active) {
  const lit = selected && active && active[edge.from + ">" + edge.to];
  if (lit) return 1.2;
  if (selected) return 0.3;
  if (edge.kind !== "competitor" && !sameEcosystem(edge.from, edge.to)) return 0.25;
  return 0.4;
}
function sentence(node) {
  if (!selected || !paths || node.id === selected) {
    if (node.id === selected) return "This is where the news is applied.";
    return node.kind === "brand" ? "Brand." : "Linked by a Wikidata statement.";
  }
  const sign = paths.arrivedSign[node.id];
  if (!(node.id in paths.dist) || paths.dist[node.id] > MAX_HOPS) return "No signed link within two hops.";
  if (sign < 0) return "Competitor: moves the other way.";
  if (sign > 0) return "Ownership or product: moves the same way.";
  return "No signed link within two hops.";
}
const nodeItems = graph.nodes.map(node => ({
  id: node.id,
  label: node.kind === "brand" ? node.id : "",
  title: sentence(node),
  x: pos[node.id].x,
  y: pos[node.id].y,
  size: dotSize(node),
  color: { background: DIM, border: DIM },
  borderWidth: 0,
  font: { size: 11, color: INK, face: "Helvetica Neue, Helvetica, Arial, sans-serif", strokeWidth: 2, strokeColor: "#fafafa" }
}));
const drawItems = graph.draw.map((edge, index) => ({
  id: index,
  from: edge.src,
  to: edge.dst,
  kind: edge.kind,
  color: { color: EDGE },
  width: edge.kind === "competitor" || sameEcosystem(edge.src, edge.dst) ? 0.4 : 0.25,
  hidden: false,
  smooth: false
}));
const nodes = new vis.DataSet(nodeItems);
const edges = new vis.DataSet(drawItems);
const network = new vis.Network(document.getElementById("net"), { nodes, edges }, {
  physics: false,
  autoResize: true,
  interaction: { hover: true, tooltipDelay: 80, dragNodes: false, zoomView: true, dragView: true, selectConnectedEdges: false },
  nodes: { shape: "dot", borderWidth: 0, chosen: false, shadow: false },
  edges: { selectionWidth: 0, hoverWidth: 0, chosen: false, shadow: false }
});
function fitView() {
  network.fit({ animation: false, padding: 28 });
  paint();
}
let fitted = false;
network.on("afterDrawing", () => {
  if (fitted) return;
  fitted = true;
  fitView();
});
window.addEventListener("resize", fitView);
setTimeout(fitView, 60);
function paint() {
  const now = shiftsAt(day);
  const full = shiftsAt(7);
  let scale = 0;
  Object.keys(full).forEach(id => { scale = Math.max(scale, Math.abs(full[id])); });
  const active = {};
  Object.keys(full).forEach(id => {
    if (!full[id]) return;
    (paths.edgesOf[id] || []).forEach(link => { active[link.src + ">" + link.dst] = true; active[link.dst + ">" + link.src] = true; });
  });
  nodes.update(graph.nodes.map(node => {
    let background = DIM;
    if (selected && node.id === selected) background = newsSign > 0 ? UP : DOWN;
    else if (selected && now[node.id]) background = mix(now[node.id], scale || 1);
    return {
      id: node.id,
      label: showLabel(node.id) ? node.id : "",
      title: sentence(node),
      size: Math.max(dotSize(node), 3 / (network.getScale() || 1)),
      borderWidth: 0,
      color: { background, border: background },
      font: { size: 11, color: INK, strokeWidth: 2, strokeColor: "#fafafa" }
    };
  }));
  edges.update(drawItems.map(edge => {
    const lit = selected && active[edge.from + ">" + edge.to];
    return { id: edge.id, hidden: false, width: edgeWidth(edge, active), color: { color: lit ? INK : EDGE } };
  }));
  document.getElementById("summary").textContent = summaryLine();
}
function choose(id) {
  const found = graph.nodes.find(node => node.id.toLowerCase() === String(id).toLowerCase());
  if (!found) return;
  selected = found.id;
  paths = walk(selected);
  day = 0;
  document.getElementById("day").value = "0";
  playing = true;
  document.getElementById("play").textContent = "Pause";
  network.focus(selected, { scale: 1.15, animation: { duration: 280, easingFunction: "easeInOutQuad" } });
  paint();
}
document.getElementById("pos").onclick = () => { newsSign = 1; document.getElementById("pos").classList.add("on"); document.getElementById("neg").classList.remove("on"); paint(); };
document.getElementById("neg").onclick = () => { newsSign = -1; document.getElementById("neg").classList.add("on"); document.getElementById("pos").classList.remove("on"); paint(); };
["size", "strength", "day"].forEach(id => {
  document.getElementById(id).addEventListener("input", event => {
    if (id === "day") { day = Number(event.target.value); playing = false; document.getElementById("play").textContent = "Play"; }
    paint();
  });
});
document.getElementById("play").onclick = () => {
  playing = !playing;
  if (day >= 7) day = 0;
  document.getElementById("play").textContent = playing ? "Pause" : "Play";
};
document.getElementById("search").addEventListener("change", event => choose(event.target.value));
document.getElementById("search").addEventListener("keydown", event => { if (event.key === "Enter") choose(event.target.value); });
graph.nodes.forEach(node => {
  const option = document.createElement("option");
  option.value = node.id;
  document.getElementById("names").appendChild(option);
});
network.on("click", params => { if (params.nodes.length) choose(params.nodes[0]); });
network.on("hoverNode", params => { hovered = params.node; paint(); });
network.on("blurNode", () => { hovered = null; paint(); });
network.on("zoom", () => paint());
function frame() {
  if (playing) {
    day = Math.min(7, day + 0.018);
    document.getElementById("day").value = String(day);
    if (day >= 7) { playing = false; document.getElementById("play").textContent = "Play"; }
    paint();
  }
  requestAnimationFrame(frame);
}
paint();
requestAnimationFrame(frame);
</script>
</body>
</html>
"""


def render() -> str:
    graph = json.dumps(json.loads((ROOT / "assets" / "graph.json").read_text())).replace("<", "\\u003c")
    vis = (ROOT / "assets" / "vis-network.min.js").read_text()
    return PAGE.replace("__GRAPH__", graph).replace("__VIS__", vis)


st.set_page_config(page_title="Brand graph", layout="wide", initial_sidebar_state="collapsed")
st.markdown(
    """
    <style>
      #MainMenu, header, footer, [data-testid="stToolbar"], [data-testid="stStatusWidget"] { display: none !important; }
      .stApp { background: #fafafa; }
      .block-container { padding: 0 0 40px; max-width: 100%; }
      p.demo-foot { position: fixed; left: 0; right: 0; bottom: 0; margin: 0; padding: 8px 12px;
        text-align: center; color: #6b7280 !important; font-size: 11px !important; line-height: 11px !important;
        font-weight: 400; background: #fafafa; z-index: 4; }
      .stApp iframe { border: 0; display: block; height: calc(100vh - 36px) !important; }
      [data-testid="stElementContainer"]:has(iframe) ~ [data-testid="stElementContainer"]:has(iframe) iframe { height: 3480px !important; }
    </style>
    """,
    unsafe_allow_html=True,
)


def render_evidence() -> str:
    data = json.dumps(json.loads((ROOT / "assets" / "evidence.json").read_text())).replace("<", "\\u003c")
    return (ROOT / "evidence_page.html").read_text().replace("__DATA__", data)


st.iframe(render(), height=760)
st.iframe(render_evidence(), height=3480)
st.markdown(
    f'<p class="demo-foot" style="color:#6b7280;font-size:11px;line-height:11px;font-weight:400;text-align:center;">{FOOTER}</p>',
    unsafe_allow_html=True,
)

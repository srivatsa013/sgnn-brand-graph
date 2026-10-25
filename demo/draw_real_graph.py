"""Draw the real 14-ecosystem graph. Writes only under demo/real/."""

from __future__ import annotations

import json
import struct
import zlib
from pathlib import Path

from guard import demo_file
from real_graph import layout, load_graph

FONT = {
    " ": ["00000"] * 7,
    "-": ["00000", "00000", "00000", "11111", "00000", "00000", "00000"],
    "'": ["11000", "11000", "10000", "00000", "00000", "00000", "00000"],
    "+": ["00000", "00100", "00100", "11111", "00100", "00100", "00000"],
    ".": ["00000", "00000", "00000", "00000", "00000", "01100", "01100"],
    "0": ["01110", "10001", "10011", "10101", "11001", "10001", "01110"],
    "1": ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
    "2": ["01110", "10001", "00001", "00010", "00100", "01000", "11111"],
    "3": ["11110", "00001", "00001", "01110", "00001", "00001", "11110"],
    "4": ["00010", "00110", "01010", "10010", "11111", "00010", "00010"],
    "5": ["11111", "10000", "11110", "00001", "00001", "10001", "01110"],
    "6": ["00110", "01000", "10000", "11110", "10001", "10001", "01110"],
    "7": ["11111", "00001", "00010", "00100", "01000", "01000", "01000"],
    "8": ["01110", "10001", "10001", "01110", "10001", "10001", "01110"],
    "9": ["01110", "10001", "10001", "01111", "00001", "00010", "01100"],
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "B": ["11110", "10001", "10001", "11110", "10001", "10001", "11110"],
    "C": ["01110", "10001", "10000", "10000", "10000", "10001", "01110"],
    "D": ["11110", "10001", "10001", "10001", "10001", "10001", "11110"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "F": ["11111", "10000", "10000", "11110", "10000", "10000", "10000"],
    "G": ["01110", "10001", "10000", "10111", "10001", "10001", "01110"],
    "H": ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
    "I": ["01110", "00100", "00100", "00100", "00100", "00100", "01110"],
    "J": ["00111", "00010", "00010", "00010", "00010", "10010", "01100"],
    "K": ["10001", "10010", "10100", "11000", "10100", "10010", "10001"],
    "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
    "M": ["10001", "11011", "10101", "10101", "10001", "10001", "10001"],
    "N": ["10001", "11001", "10101", "10011", "10001", "10001", "10001"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "P": ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
    "Q": ["01110", "10001", "10001", "10001", "10101", "10010", "01101"],
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    "U": ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
    "V": ["10001", "10001", "10001", "10001", "10001", "01010", "00100"],
    "W": ["10001", "10001", "10001", "10101", "10101", "10101", "01010"],
    "X": ["10001", "10001", "01010", "00100", "01010", "10001", "10001"],
    "Y": ["10001", "10001", "01010", "00100", "00100", "00100", "00100"],
    "Z": ["11111", "00001", "00010", "00100", "01000", "10000", "11111"],
}
for _ch in list(FONT):
    if _ch.isalpha():
        FONT.setdefault(_ch.lower(), FONT[_ch])

TYPE_COLOR = {
    "brand": (23, 92, 211),
    "product": (181, 71, 8),
    "ceo": (105, 65, 198),
    "competitor": (180, 35, 24),
}
EDGE_COLOR = {"positive": (27, 127, 78), "competitor": (180, 35, 24), "comention": (102, 112, 133)}


class Canvas:
    def __init__(self, width: int, height: int):
        self.w = width
        self.h = height
        self.buf = bytearray([248, 250, 252]) * (width * height)

    def pixel(self, x: int, y: int, color: tuple[int, int, int]) -> None:
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.buf[i : i + 3] = bytes(color)

    def line(self, x0: float, y0: float, x1: float, y1: float, color: tuple[int, int, int], dashed: bool = False) -> None:
        x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
        err = dx - dy
        step = 0
        while True:
            if not dashed or (step // 6) % 2 == 0:
                self.pixel(x0, y0, color)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy
            step += 1

    def disc(self, cx: float, cy: float, radius: int, color: tuple[int, int, int]) -> None:
        r2 = radius * radius
        for y in range(int(cy) - radius, int(cy) + radius + 1):
            for x in range(int(cx) - radius, int(cx) + radius + 1):
                if (x - cx) ** 2 + (y - cy) ** 2 <= r2:
                    self.pixel(x, y, color)

    def box(self, cx: float, cy: float, radius: int, color: tuple[int, int, int]) -> None:
        for y in range(int(cy) - radius, int(cy) + radius + 1):
            for x in range(int(cx) - radius, int(cx) + radius + 1):
                self.pixel(x, y, color)

    def diamond(self, cx: float, cy: float, radius: int, color: tuple[int, int, int]) -> None:
        for y in range(int(cy) - radius, int(cy) + radius + 1):
            span = radius - abs(y - int(cy))
            for x in range(int(cx) - span, int(cx) + span + 1):
                self.pixel(x, y, color)

    def triangle(self, cx: float, cy: float, radius: int, color: tuple[int, int, int]) -> None:
        top = int(cy) - radius
        for y in range(top, int(cy) + radius + 1):
            span = int((y - top) * radius / max(2 * radius, 1))
            for x in range(int(cx) - span, int(cx) + span + 1):
                self.pixel(x, y, color)

    def text(self, x: int, y: int, message: str, color: tuple[int, int, int] = (15, 23, 42), scale: int = 1) -> None:
        cursor = x
        for ch in message:
            rows = FONT.get(ch, FONT.get(ch.upper(), FONT[" "]))
            for row_i, row in enumerate(rows):
                for col_i, bit in enumerate(row):
                    if bit == "1":
                        for sy in range(scale):
                            for sx in range(scale):
                                self.pixel(cursor + col_i * scale + sx, y + row_i * scale + sy, color)
            cursor += 6 * scale

    def save(self, path: Path) -> None:
        raw = b"".join(b"\x00" + self.buf[y * self.w * 3 : (y + 1) * self.w * 3] for y in range(self.h))

        def chunk(tag: bytes, data: bytes) -> bytes:
            return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

        ihdr = struct.pack(">IIBBBBB", self.w, self.h, 8, 2, 0, 0, 0)
        png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b"")
        path.write_bytes(png)


def _shape(canvas: Canvas, kind: str, x: float, y: float, radius: int, color: tuple[int, int, int]) -> None:
    if kind == "product":
        canvas.box(x, y, radius, color)
    elif kind == "competitor":
        canvas.diamond(x, y, radius, color)
    elif kind == "ceo":
        canvas.triangle(x, y, radius, color)
    else:
        canvas.disc(x, y, radius, color)


def paint(graph: dict, pos: dict[str, tuple[float, float]], path: Path, title: str, width: int, height: int) -> None:
    canvas = Canvas(width, height)
    canvas.text(24, 18, "REAL GRAPH", scale=2)
    canvas.text(24, 40, title, scale=1)
    drawn = set(pos)
    for edge in graph["comention_edges"]:
        if edge["src"] in drawn and edge["dst"] in drawn:
            canvas.line(*pos[edge["src"]], *pos[edge["dst"]], EDGE_COLOR["comention"], dashed=True)
    for edge in graph["positive_edges"]:
        if edge["src"] in drawn and edge["dst"] in drawn:
            canvas.line(*pos[edge["src"]], *pos[edge["dst"]], EDGE_COLOR["positive"])
    for edge in graph["competitor_edges"]:
        if edge["src"] in drawn and edge["dst"] in drawn:
            canvas.line(*pos[edge["src"]], *pos[edge["dst"]], EDGE_COLOR["competitor"])
    for name, (x, y) in pos.items():
        kind = graph["nodes"][name]["type"]
        _shape(canvas, kind, x, y, 7 if len(pos) > 20 else 11, TYPE_COLOR[kind])
        canvas.text(int(x) + 8, int(y) - 4, name[:18], scale=1)
    canvas.text(24, height - 36, "Green positive  Red competitor  Dashed gray co-mention", scale=1)
    canvas.text(24, height - 22, "Circle brand  Square product  Triangle CEO  Diamond competitor", scale=1)
    canvas.save(path)


def html_page(graph: dict, overview: dict, zoom: dict) -> str:
    payload = {
        "title": "REAL GRAPH",
        "nodes": [{"id": name, "type": meta["type"], "ecosystems": meta["ecosystems"]} for name, meta in graph["nodes"].items()],
        "edges": graph["positive_edges"] + graph["competitor_edges"] + graph["comention_edges"],
        "views": {"overview": {name: [x, y] for name, (x, y) in overview.items()}, "apple_microsoft": {name: [x, y] for name, (x, y) in zoom.items()}},
    }
    data = json.dumps(payload)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>REAL GRAPH</title>
<style>
body {{ font-family: Georgia, serif; margin: 0; background: #f8fafc; color: #0f172a; }}
header {{ padding: 16px 24px 0; }}
h1 {{ margin: 0; font-size: 28px; }}
button {{ margin-right: 8px; }}
#stage {{ width: 100%; height: calc(100vh - 120px); display: block; background: white; border-top: 1px solid #e2e8f0; }}
#tip {{ position: fixed; background: white; border: 1px solid #cbd5e1; padding: 6px 8px; display: none; pointer-events: none; }}
</style>
</head>
<body>
<header>
<h1>REAL GRAPH</h1>
<p>14 ecosystems from the study files. Positive edges are green, competitor edges are red, co-mention edges are dashed. This page does not contain synthetic rows.</p>
<button id="overview" type="button">Overview</button>
<button id="zoom" type="button">Apple and Microsoft</button>
</header>
<canvas id="stage"></canvas>
<div id="tip"></div>
<script>
const DATA = {data};
const canvas = document.getElementById('stage');
const tip = document.getElementById('tip');
const ctx = canvas.getContext('2d');
let view = 'overview';
let cam = {{x: 0, y: 0, z: 1}};
let drag = null;
function resize() {{ canvas.width = canvas.clientWidth; canvas.height = canvas.clientHeight; draw(); }}
function pos(id) {{ const p = DATA.views[view][id]; return p ? [p[0], p[1]] : null; }}
function toScreen(x, y) {{ return [(x + cam.x) * cam.z + 40, (y + cam.y) * cam.z + 20]; }}
function draw() {{
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = '#0f172a'; ctx.font = '20px Georgia'; ctx.fillText('REAL GRAPH', 16, 28);
  const ids = new Set(Object.keys(DATA.views[view]));
  for (const edge of DATA.edges) {{
    if (!ids.has(edge.src) || !ids.has(edge.dst)) continue;
    const a = pos(edge.src), b = pos(edge.dst);
    const [x1, y1] = toScreen(a[0], a[1]);
    const [x2, y2] = toScreen(b[0], b[1]);
    ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2);
    ctx.strokeStyle = edge.kind === 'positive' ? '#1b7f4e' : edge.kind === 'competitor' ? '#b42318' : '#667085';
    ctx.setLineDash(edge.kind === 'comention' ? [5, 5] : []);
    ctx.lineWidth = edge.kind === 'comention' ? 1 : 2;
    ctx.stroke();
  }}
  ctx.setLineDash([]);
  for (const node of DATA.nodes) {{
    if (!ids.has(node.id)) continue;
    const p = pos(node.id);
    const [x, y] = toScreen(p[0], p[1]);
    ctx.fillStyle = {{brand:'#175cd3', product:'#b54708', ceo:'#6941c6', competitor:'#b42318'}}[node.type];
    ctx.beginPath();
    if (node.type === 'product') ctx.rect(x-6, y-6, 12, 12);
    else if (node.type === 'competitor') {{ ctx.moveTo(x, y-8); ctx.lineTo(x+8, y); ctx.lineTo(x, y+8); ctx.lineTo(x-8, y); }}
    else if (node.type === 'ceo') {{ ctx.moveTo(x, y-8); ctx.lineTo(x+8, y+6); ctx.lineTo(x-8, y+6); }}
    else ctx.arc(x, y, 7, 0, Math.PI*2);
    ctx.fill();
    ctx.fillStyle = '#0f172a'; ctx.font = '12px Georgia'; ctx.fillText(node.id, x+10, y+4);
  }}
}}
document.getElementById('overview').onclick = () => {{ view = 'overview'; cam = {{x:0,y:0,z:0.72}}; draw(); }};
document.getElementById('zoom').onclick = () => {{ view = 'apple_microsoft'; cam = {{x:0,y:0,z:0.95}}; draw(); }};
canvas.onwheel = (event) => {{ event.preventDefault(); cam.z = Math.min(2.5, Math.max(0.4, cam.z * (event.deltaY < 0 ? 1.1 : 0.9))); draw(); }};
canvas.onmousedown = (event) => {{ drag = [event.clientX, event.clientY, cam.x, cam.y]; }};
window.onmouseup = () => {{ drag = null; }};
window.onmousemove = (event) => {{
  if (drag) {{ cam.x = drag[2] + (event.clientX - drag[0]) / cam.z; cam.y = drag[3] + (event.clientY - drag[1]) / cam.z; draw(); }}
  const ids = Object.keys(DATA.views[view]);
  let hit = null;
  for (const id of ids) {{
    const p = pos(id); const [x, y] = toScreen(p[0], p[1]);
    const rect = canvas.getBoundingClientRect();
    if (Math.hypot(event.clientX - rect.left - x, event.clientY - rect.top - y) < 12) hit = id;
  }}
  if (hit) {{ const node = DATA.nodes.find(item => item.id === hit); tip.style.display = 'block'; tip.style.left = event.clientX + 12 + 'px'; tip.style.top = event.clientY + 12 + 'px'; tip.textContent = hit + ' · ' + node.type; }}
  else tip.style.display = 'none';
}};
window.onresize = resize;
cam = {{x:0,y:0,z:0.72}};
resize();
</script>
</body>
</html>
"""


def main() -> None:
    graph = load_graph()
    overview = layout(graph, width=1600, height=1100)
    zoom = layout(graph, ["Apple", "Microsoft"], width=1400, height=900)
    paint(graph, overview, demo_file("real/REAL_GRAPH_overview.png"), "Overview of 14 ecosystems", 1600, 1100)
    paint(graph, zoom, demo_file("real/REAL_GRAPH_apple_microsoft.png"), "Apple and Microsoft", 1400, 900)
    demo_file("real/REAL_GRAPH.html").write_text(html_page(graph, overview, zoom))
    demo_file("real/REAL_GRAPH_layout.json").write_text(json.dumps({"label": "REAL GRAPH", "sources": graph["sources"], "n_nodes": len(graph["nodes"]), "n_positive": len(graph["positive_edges"]), "n_competitor": len(graph["competitor_edges"]), "n_comention": len(graph["comention_edges"])}, indent=2) + "\n")
    print("REAL GRAPH", len(graph["nodes"]), "nodes", len(graph["positive_edges"]), "positive", len(graph["competitor_edges"]), "competitor", len(graph["comention_edges"]), "comention")


if __name__ == "__main__":
    main()

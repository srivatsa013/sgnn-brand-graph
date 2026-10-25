"""Read-only view of the 14-ecosystem graph. This module does not write."""

from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NODES_PATH = ROOT / "configs" / "phase2_nodes.json"
EDGES_PATH = ROOT / "kg" / "phase2_structural_edges.json"
SERIES_DB = ROOT / "data" / "interim" / "phase2" / "series.sqlite"


def node_type(name: str, competitor: set[str]) -> str:
    if name.endswith(" CEO"):
        return "ceo"
    if name in competitor:
        return "competitor"
    return "product"


def load_graph() -> dict:
    nodes_doc = json.loads(NODES_PATH.read_text())
    edges_doc = json.loads(EDGES_PATH.read_text())
    ecosystems = nodes_doc["ecosystems"]
    if len(ecosystems) != 14:
        raise SystemExit(f"expected 14 ecosystems, found {len(ecosystems)}")
    competitor = {name for spec in ecosystems.values() for name in spec["competitor_nodes"]}
    info = {}
    membership = defaultdict(list)
    for eco, spec in ecosystems.items():
        info[eco] = {"type": "brand", "ecosystems": [eco]}
        membership[eco].append(eco)
        for name in spec["positive_nodes"]:
            info.setdefault(name, {"type": node_type(name, competitor), "ecosystems": []})
            if eco not in info[name]["ecosystems"]:
                info[name]["ecosystems"].append(eco)
            membership[eco].append(name)
        for name in spec["competitor_nodes"]:
            info.setdefault(name, {"type": "competitor", "ecosystems": []})
            if eco not in info[name]["ecosystems"]:
                info[name]["ecosystems"].append(eco)
            membership[eco].append(name)
    positive = []
    for edge in edges_doc["positive_edges"] + edges_doc["ceo_edges"]:
        left, right = edge["nodes"]
        positive.append({"src": left, "dst": right, "sign": 1, "kind": "positive"})
    competitor_edges = []
    for edge in edges_doc["competitor_edges_confirmed"]:
        competitor_edges.append(
            {
                "src": edge["from"],
                "dst": edge["to"],
                "sign": -1,
                "kind": "competitor",
                "reverse_asserted": bool(edge.get("reverse_asserted")),
            }
        )
    allowed = set(info)
    co_edges = []
    if SERIES_DB.exists():
        con = sqlite3.connect(f"file:{SERIES_DB}?mode=ro", uri=True)
        grouped: dict[tuple[str, str], int] = {}
        for left, right, count in con.execute("SELECT node_a, node_b, n FROM comention"):
            if left not in allowed or right not in allowed or left == right:
                continue
            key = tuple(sorted((left, right)))
            grouped[key] = grouped.get(key, 0) + int(count)
        con.close()
        for (left, right), count in sorted(grouped.items()):
            if count < 3:
                continue
            co_edges.append({"src": left, "dst": right, "sign": 0, "kind": "comention", "documents": count})
    return {
        "ecosystems": {name: {"members": members, "sector": ecosystems[name]["sector_bucket"]} for name, members in membership.items()},
        "nodes": info,
        "positive_edges": positive,
        "competitor_edges": competitor_edges,
        "comention_edges": co_edges,
        "sources": {
            "nodes": str(NODES_PATH.relative_to(ROOT)),
            "edges": str(EDGES_PATH.relative_to(ROOT)),
            "comention": "data/interim/phase2/series.sqlite table comention, pooled count at least 3, read only",
        },
    }


def layout(graph: dict, names: list[str] | None = None, width: int = 1600, height: int = 1100) -> dict[str, tuple[float, float]]:
    import math

    ecosystems = [name for name in graph["ecosystems"] if names is None or name in names]
    selected = set()
    for eco in ecosystems:
        for member in graph["ecosystems"][eco]["members"]:
            if names is None or eco in names:
                selected.add(member)
    pos = {}
    if len(ecosystems) == 1:
        centers = {ecosystems[0]: (width / 2, height / 2)}
    elif len(ecosystems) == 2:
        centers = {ecosystems[0]: (width * 0.28, height * 0.52), ecosystems[1]: (width * 0.72, height * 0.52)}
    else:
        centers = {}
        for index, eco in enumerate(ecosystems):
            angle = 2 * math.pi * index / len(ecosystems) - math.pi / 2
            centers[eco] = (width * 0.50 + width * 0.36 * math.cos(angle), height * 0.52 + height * 0.34 * math.sin(angle))
    for eco in ecosystems:
        members = [member for member in graph["ecosystems"][eco]["members"] if member in selected]
        cx, cy = centers[eco]
        others = [member for member in members if member != eco]
        pos[eco] = (cx, cy)
        radius = 78 if len(ecosystems) > 2 else 150
        for index, member in enumerate(others):
            angle = 2 * math.pi * index / max(len(others), 1) - math.pi / 2
            pos[member] = (cx + radius * math.cos(angle), cy + radius * math.sin(angle))
    return pos

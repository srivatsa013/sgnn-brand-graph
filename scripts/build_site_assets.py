"""Copy the graph and the augmented estimates into site/assets. Build time only."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "demo"))

from real_graph import load_graph  # noqa: E402

OUT = ROOT / "site" / "assets" / "graph.json"


def main() -> None:
    graph = load_graph()
    edges = json.loads((ROOT / "kg" / "phase2_structural_edges.json").read_text())
    popularity = edges["popularity_sitelinks"]
    augmented = json.loads((ROOT / "eval" / "results" / "phase5_augmented.json").read_text())
    estimates = augmented["edge_class_estimates"]
    payload = {
        "magnitudes": {
            "positive": estimates["positive"],
            "competitor": estimates["negative"],
            "comention": estimates["comention"],
        },
        "nodes": [],
        "links": [],
        "draw": [],
    }
    for name, info in graph["nodes"].items():
        payload["nodes"].append(
            {
                "id": name,
                "kind": info["type"],
                "popularity": int(popularity.get(name) or 1),
                "shift": augmented["node_shift"].get(name),
            }
        )
    seen = set()
    for edge in graph["positive_edges"]:
        left, right = edge["src"], edge["dst"]
        payload["links"].append({"src": left, "dst": right, "sign": 1, "kind": "positive"})
        payload["links"].append({"src": right, "dst": left, "sign": 1, "kind": "positive"})
        key = tuple(sorted((left, right))) + ("positive",)
        if key not in seen:
            seen.add(key)
            payload["draw"].append({"src": left, "dst": right, "kind": "positive"})
    for edge in graph["competitor_edges"]:
        left, right = edge["src"], edge["dst"]
        payload["links"].append({"src": left, "dst": right, "sign": -1, "kind": "competitor"})
        if edge.get("reverse_asserted"):
            payload["links"].append({"src": right, "dst": left, "sign": -1, "kind": "competitor"})
        key = tuple(sorted((left, right))) + ("competitor",)
        if key not in seen:
            seen.add(key)
            payload["draw"].append({"src": left, "dst": right, "kind": "competitor"})
    for edge in graph["comention_edges"]:
        left, right = edge["src"], edge["dst"]
        key = tuple(sorted((left, right))) + ("comention",)
        if key in seen:
            continue
        seen.add(key)
        payload["draw"].append({"src": left, "dst": right, "kind": "comention"})
    OUT.write_text(json.dumps(payload) + "\n")
    print(f"nodes {len(payload['nodes'])} links {len(payload['links'])} draw {len(payload['draw'])}")


if __name__ == "__main__":
    main()

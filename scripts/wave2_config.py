"""Wave 2 ecosystem config (amendments A2026-10-24-wave2 and A2026-10-25).

Builds, in memory or on disk, the 30-ecosystem NODES and GRAPH that the Wave 1 helpers read:
  - the 14 Wave 1 ecosystems exactly as stored in configs/phase2_nodes.json and kg/phase2_structural_edges.json
  - the 16 Wave 2 ecosystems, with neighbours from configs/wave2_gdelt_aliases.json
    (neighbour rule of amendment A2026-10-25) and the 34 competitor edges of
    reports/wave2_competitor_edges.json.

No network. No Wave 1 file is written. Run `python3 scripts/wave2_config.py` to write
configs/wave2_nodes.json and kg/wave2_structural_edges.json.
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NODES_W1 = ROOT / "configs" / "phase2_nodes.json"
GRAPH_W1 = ROOT / "kg" / "phase2_structural_edges.json"
ALIASES = ROOT / "configs" / "wave2_gdelt_aliases.json"
COMPETITORS = ROOT / "reports" / "wave2_competitor_edges.json"
CANDIDATES = ROOT / "reports" / "wave2_candidates.json"
OUT_NODES = ROOT / "configs" / "wave2_nodes.json"
OUT_GRAPH = ROOT / "kg" / "wave2_structural_edges.json"
PRIMARY = {"P749", "P355", "P1716", "P1056", "P176", "P169", "P127"}
SNAP = ROOT / "kg" / "snapshots" / "wikidata_2026-10-12"
OWNER_P31 = ROOT / "reports" / "wave2_owner_p31.json"
# neighbour counts frozen in reports/wave2_amendment_a2026-10-25.md, section 5 ("Proposed neighbors")
AMENDMENT_COUNTS = {"DD": 19, "BLK": 68, "JNJ": 35, "COP": 10, "BA": 46, "DOW": 7, "ACN": 7, "DIS": 210,
                    "KO": 34, "BAC": 14, "GILD": 10, "PSX": 8, "GD": 19, "EA": 37, "WMT": 34}
INVESTOR_CLASSES = {"bank", "investment bank", "commercial bank", "retail bank", "global systemically important bank", "credit institution"}
INVESTOR_WORDS = ("asset manager", "asset management", "investment company", "investment firm", "investment fund", "mutual fund",
                  "hedge fund", "private equity", "pension fund", "sovereign wealth", "investment management")
SNAPSHOT_PROPERTIES = {"P749", "P355", "P1716", "P1056", "P176", "P127"}  # P169 comes from the brand item's claims; never P1830
EXPECTED_ECOSYSTEMS = 30
EXPECTED_COMPETITOR_EDGES = 34


def _load(path: Path):
    return json.loads(path.read_text())


def build() -> tuple[dict, dict]:
    nodes, graph = _load(NODES_W1), _load(GRAPH_W1)
    aliases, comp, cand = _load(ALIASES), _load(COMPETITORS), _load(CANDIDATES)
    sector = {row["ticker"]: row["sector"] for row in cand["selected"]}
    by_ticker = {item["ticker"]: item for item in aliases["items"] if item["wave"] == 2}
    new_nodes, new_graph = copy.deepcopy(nodes), copy.deepcopy(graph)
    eco_spec = new_nodes["ecosystems"]
    wave2 = {item["name"]: item for item in by_ticker.values()}
    for name, item in wave2.items():
        if name in eco_spec:
            raise SystemExit(f"Wave 2 ecosystem {name} already in Wave 1 config")
        eco_spec[name] = {"sector_bucket": sector[item["ticker"]], "brand_tickers": [item["ticker"]],
                          "brand_aliases": [name], "positive_nodes": [], "competitor_nodes": [], "wave": 2}
    # positive neighbours: amendment A2026-10-25 section 4, recounted from the 2026-10-12 snapshot.
    # Never P1830. A P127 edge is dropped when its owner (the edge target) is investor-type.
    entities, neighbors = _load(SNAP / "entities.json"), _load(SNAP / "neighbor_entities.json")
    owner_p31 = _load(OWNER_P31)
    sitelinks, labels = {}, {}
    for table in (neighbors, entities):
        for qid, row in table.items():
            sitelinks[qid] = row.get("sitelink_count", 0)
            labels[qid] = row.get("label") or row.get("enwiki") or qid

    def investor(qid: str) -> bool:
        classes = [c["label"].lower() for c in owner_p31.get(qid, {}).get("p31", [])]
        return any(c in INVESTOR_CLASSES or any(w in c for w in INVESTOR_WORDS) for c in classes)

    statements = {}
    for edge in _load(SNAP / "path_edges.json")["edges"]:
        if edge["rank"] in ("normal", "preferred") and edge["property_id"] in SNAPSHOT_PROPERTIES \
                and sitelinks.get(edge["source"], 0) >= 1 and sitelinks.get(edge["target"], 0) >= 1:
            if edge["property_id"] == "P127" and investor(edge["target"]):
                continue
            statements[edge["statement_id"]] = edge
    for ticker, item in by_ticker.items():
        eco, qid = item["name"], item["qid"]
        if ticker == "SPG":      # not in the snapshot; amendment keeps it on its own CEO edge
            continue
        found: dict[str, str] = {}
        for edge in statements.values():
            if qid in (edge["source"], edge["target"]):
                other = edge["target"] if edge["source"] == qid else edge["source"]
                found.setdefault(other, edge["property_id"])
        ceo = []
        brand = entities.get(qid) or neighbors.get(qid) or {}
        for claim in brand.get("claims", {}).get("P169", []):
            if claim.get("rank") in ("normal", "preferred") and sitelinks.get(claim.get("target"), 0) >= 1:
                ceo.append(claim["target"])
        if len(found.keys() | set(ceo)) != AMENDMENT_COUNTS[ticker]:
            raise SystemExit(f"{ticker}: recount {len(found.keys() | set(ceo))} != amendment {AMENDMENT_COUNTS[ticker]}")
        spec = eco_spec[eco]
        every = set(found) | set(ceo)
        counts: dict[str, int] = {}
        for other in every:
            counts[labels[other]] = counts.get(labels[other], 0) + 1

        def node_name(other: str) -> str:   # two items can share a label; keep them as two nodes
            return labels[other] if counts[labels[other]] == 1 else f"{labels[other]} ({other})"

        for other, prop in sorted(found.items()):
            label = node_name(other)
            if label not in spec["positive_nodes"]:
                spec["positive_nodes"].append(label)
            new_graph["positive_edges"].append({
                "edge_class": "positive", "sign": 1, "stored_as": "two_arcs_sharing_W_pos", "nodes": [eco, label],
                "property_id": prop, "source_qid": other, "wave": 2, "snapshot": "wikidata_2026-10-12"})
        for other in ceo:
            label = node_name(other)
            if label not in spec["positive_nodes"]:
                spec["positive_nodes"].append(label)
            new_graph["ceo_edges"].append({
                "edge_class": "positive", "sign": 1, "stored_as": "two_arcs_sharing_W_pos", "nodes": [eco, label],
                "property_id": "P169", "company_qid": qid, "person_qid": other, "wave": 2, "snapshot": "wikidata_2026-10-12"})
    # Simon Property Group is not in the snapshot: its neighbour is its CEO, taken from the alias table
    for row in aliases["neighbors"]:
        if row.get("role") == "neighbor" and "Simon Property Group" in row["ecosystems"] and set(row["properties"]) & PRIMARY:
            spec = eco_spec["Simon Property Group"]
            if row["name"] not in spec["positive_nodes"]:
                spec["positive_nodes"].append(row["name"])
                new_graph["positive_edges"].append({
                    "edge_class": "positive", "sign": 1, "stored_as": "two_arcs_sharing_W_pos", "nodes": ["Simon Property Group", row["name"]],
                    "property_id": sorted(set(row["properties"]) & PRIMARY)[0], "source_qid": row["qid"], "wave": 2, "snapshot": "live_2026-10-25"})
    # competitor edges: the 34 named on English Wikipedia
    added = 0
    for edge in comp["edges"]:
        item = by_ticker[edge["ticker"]]
        eco = item["name"]
        rival = edge["retained_ticker"] or edge["rival"]
        spec = eco_spec[eco]
        if rival not in spec["competitor_nodes"]:
            spec["competitor_nodes"].append(rival)
        new_graph["competitor_edges_confirmed"].append({
            "edge_class": "competitor", "sign": -1, "direction": "brand_to_named_competitor", "from": eco, "to": rival,
            "reverse_asserted": False, "property_id": None, "pending_user_confirmation": False, "wave": 2,
            "provenance": "English Wikipedia names the rival (reports/wave2_competitor_edges.json, A2026-10-25)",
            "rival_name": edge["rival"]})
        added += 1
    if len(eco_spec) != EXPECTED_ECOSYSTEMS:
        raise SystemExit(f"expected {EXPECTED_ECOSYSTEMS} ecosystems, built {len(eco_spec)}")
    if added != EXPECTED_COMPETITOR_EDGES:
        raise SystemExit(f"expected {EXPECTED_COMPETITOR_EDGES} competitor edges, built {added}")
    return new_nodes, new_graph


def activate() -> None:
    """Swap the 30-ecosystem data into the Wave 1 helpers' module dicts, in place, for this process only."""
    import phase2_feasibility as F
    # These Wave 1 modules check or derive things from NODES when first imported (for example the
    # 13 non-Tesla Arm B list). Import them while NODES is still the Wave 1 data, then swap.
    import phase2_gdelt_reserve_after  # noqa: F401
    import phase4_outcome_run  # noqa: F401

    nodes, graph = build()
    F.NODES.clear(); F.NODES.update(nodes)
    F.GRAPH.clear(); F.GRAPH.update(graph)


def main() -> int:
    nodes, graph = build()
    OUT_NODES.write_text(json.dumps(nodes, indent=1) + "\n")
    OUT_GRAPH.write_text(json.dumps(graph, indent=1) + "\n")
    per = {eco: (len(s["positive_nodes"]), len(s["competitor_nodes"])) for eco, s in nodes["ecosystems"].items() if s.get("wave") == 2}
    print(f"wrote {OUT_NODES.relative_to(ROOT)} and {OUT_GRAPH.relative_to(ROOT)}")
    for eco, (p, c) in per.items():
        print(f"  {eco}: positive {p}, competitor {c}")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT / "scripts"))
    sys.exit(main())

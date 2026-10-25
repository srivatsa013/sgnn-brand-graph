"""Seeded synthetic events on the real graph.

Demonstration only. A row from this module is not evidence about real
propagation. Every written filename contains SYNTHETIC. Nothing here is
written outside demo/synthetic/.
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import phase5_model as M  # noqa: E402

from guard import ROOT, demo_file  # noqa: E402
from real_graph import load_graph  # noqa: E402

GENERATOR_VERSION = "demo-synthetic-2026-10-24"
LAMBDAS = (0.0, 0.25, 0.5, 1.0, 2.0)
SEEDS = tuple(range(20))
OUTCOMES = ROOT / "eval" / "results" / "phase4_outcomes.json"
PHASE0 = ROOT / "configs" / "phase0.json"

COLUMNS = (
    "is_synthetic",
    "lambda",
    "seed",
    "generator_version",
    "arm",
    "source",
    "ecosystem",
    "event_id",
    "t0",
    "source_node",
    "target_node",
    "edge_class",
    "edge_sign",
    "shock_sign",
    "noise_sd",
    "planted_shift",
    "label",
    "is_label",
)


def frozen_noise() -> dict[str, float]:
    cfg = json.loads(PHASE0.read_text())
    found = {}
    for row in cfg["amendments"]:
        social = row.get("social")
        gdelt = row.get("arm_b_gdelt")
        if isinstance(social, dict) and social.get("status") == "FROZEN":
            found["social"] = float(social["sd"])
        if isinstance(gdelt, dict) and gdelt.get("status") == "FROZEN":
            found["gdelt"] = float(gdelt["sd"])
    if "social" not in found or "gdelt" not in found:
        raise SystemExit("frozen Arm A social and Arm B GDELT SDs were not both found")
    return found


def event_counts() -> dict[str, dict[str, int]]:
    """Frozen counts of events with a matched pair, by ecosystem. Read only."""
    payload = json.loads(OUTCOMES.read_text())
    out = {}
    for source, arm in (("social", "A"), ("gdelt", "B")):
        lags = payload["arms"][arm]["sources"][source]["lags"]
        counts: dict[str, int] = {}
        for eco, _t0, _lag in lags:
            counts[eco] = counts.get(eco, 0) + 1
        out[source] = counts
    return out


def structural_neighbors(graph: dict, eco: str) -> list[tuple[str, str, int]]:
    """One row per neighbor: name, edge class, sign. A node on both classes is not a label."""
    members = set(graph["ecosystems"][eco]["members"])
    signs: dict[str, set[int]] = {}
    classes: dict[str, set[str]] = {}
    for edge in graph["positive_edges"]:
        pair = {edge["src"], edge["dst"]}
        if eco not in pair or not pair <= members:
            continue
        other = edge["dst"] if edge["src"] == eco else edge["src"]
        if other == eco:
            continue
        signs.setdefault(other, set()).add(1)
        classes.setdefault(other, set()).add("positive")
    for edge in graph["competitor_edges"]:
        if edge["src"] != eco or edge["dst"] not in members:
            continue
        signs.setdefault(edge["dst"], set()).add(-1)
        classes.setdefault(edge["dst"], set()).add("competitor")
        if edge["reverse_asserted"]:
            signs.setdefault(eco, set()).add(-1)
    rows = []
    for name in sorted(signs):
        if name == eco:
            continue
        if signs[name] == {1}:
            rows.append((name, "positive", 1))
        elif signs[name] == {-1}:
            rows.append((name, "competitor", -1))
    return rows


def model_edges(graph: dict, eco: str) -> list[tuple[str, str, str, float, float]]:
    members = set(graph["ecosystems"][eco]["members"])
    edges = []
    for edge in graph["positive_edges"]:
        if edge["src"] in members and edge["dst"] in members:
            edges.append((edge["src"], edge["dst"], "struct", 1.0, 1.0))
            edges.append((edge["dst"], edge["src"], "struct", 1.0, 1.0))
    for edge in graph["competitor_edges"]:
        if edge["src"] in members and edge["dst"] in members:
            edges.append((edge["src"], edge["dst"], "struct", -1.0, 1.0))
            if edge["reverse_asserted"]:
                edges.append((edge["dst"], edge["src"], "struct", -1.0, 1.0))
    for edge in graph["comention_edges"]:
        if edge["src"] in members and edge["dst"] in members:
            edges.append((edge["src"], edge["dst"], "co", 0.0, 1.0))
            edges.append((edge["dst"], edge["src"], "co", 0.0, 1.0))
    return edges


def generate_rows(graph: dict | None = None) -> tuple[list[dict], dict]:
    graph = graph or load_graph()
    noise = frozen_noise()
    counts = event_counts()
    specs = (
        ("A", "social", noise["social"], counts["social"]),
        ("B", "gdelt", noise["gdelt"], counts["gdelt"]),
    )
    rows = []
    for arm, source, sd, by_eco in specs:
        ecos = [eco for eco in graph["ecosystems"] if by_eco.get(eco, 0) > 0]
        for seed in SEEDS:
            rng = random.Random(seed)
            drawn = []
            for eco_index, eco in enumerate(ecos):
                neighbors = structural_neighbors(graph, eco)
                for event_index in range(by_eco[eco]):
                    shock = rng.choice((-1, 1))
                    noises = {name: rng.gauss(0.0, sd) for name, _cls, _sign in neighbors}
                    drawn.append((eco, eco_index, event_index, shock, neighbors, noises))
            for lam in LAMBDAS:
                for eco, eco_index, event_index, shock, neighbors, noises in drawn:
                    event_id = f"{source}-{eco}-{event_index}"
                    t0 = 100000 + eco_index * 1000 + event_index
                    for name, edge_class, sign in neighbors:
                        planted = lam * sd * sign * shock
                        rows.append(
                            {
                                "is_synthetic": 1,
                                "lambda": lam,
                                "seed": seed,
                                "generator_version": GENERATOR_VERSION,
                                "arm": arm,
                                "source": source,
                                "ecosystem": eco,
                                "event_id": event_id,
                                "t0": t0,
                                "source_node": eco,
                                "target_node": name,
                                "edge_class": edge_class,
                                "edge_sign": sign,
                                "shock_sign": shock,
                                "noise_sd": sd,
                                "planted_shift": planted,
                                "label": planted + noises[name],
                                "is_label": 1,
                            }
                        )
    meta = {
        "generator_version": GENERATOR_VERSION,
        "lambdas": list(LAMBDAS),
        "seeds": list(SEEDS),
        "noise_sd": noise,
        "events_per_ecosystem": counts,
        "rows": len(rows),
        "note": "SYNTHETIC demonstration rows. Not evidence about real propagation.",
    }
    return rows, meta


def write_rows(rows: list[dict], meta: dict) -> Path:
    path = demo_file("synthetic/SYNTHETIC_events.parquet")
    table = pa.Table.from_pylist(rows)
    pq.write_table(table, path)
    demo_file("synthetic/SYNTHETIC_generator_meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    return path


def events_from_rows(rows: list[dict], graph: dict) -> list[M.Event]:
    import torch

    grouped: dict[str, list[dict]] = {}
    for row in rows:
        if row["is_label"] != 1:
            continue
        grouped.setdefault(row["event_id"], []).append(row)
    events = []
    cache: dict[str, tuple] = {}
    for event_id, group in grouped.items():
        eco = group[0]["ecosystem"]
        if eco not in cache:
            members = list(dict.fromkeys(graph["ecosystems"][eco]["members"]))
            index = {name: i for i, name in enumerate(members)}
            edges = []
            for src, dst, kind, sign, weight in model_edges(graph, eco):
                if src in index and dst in index:
                    edges.append(M.Edge(index[src], index[dst], kind, sign, weight))
            cache[eco] = (members, index, edges)
        members, index, edges = cache[eco]
        features = torch.zeros(len(members), 4)
        src = index[group[0]["source_node"]]
        features[src, 0] = float(group[0]["shock_sign"])
        features[src, 1] = 1.0
        for i, name in enumerate(members):
            kind = graph["nodes"][name]["type"]
            features[i, 2] = {"brand": 1, "product": 2, "ceo": 3, "competitor": 4}[kind]
        labels = {index[row["target_node"]]: float(row["label"]) for row in group}
        t0 = int(group[0]["t0"])
        events.append(
            M.Event(
                event_id=event_id,
                t0=t0,
                features=features,
                edges=edges,
                labels=labels,
                comention_times=[t0 - 8],
                history_times=[t0 - 1],
                feature_doc_ids={f"f-{event_id}"},
                label_doc_ids={f"y-{event_id}"},
            )
        )
    return events


def main() -> None:
    rows, meta = generate_rows()
    path = write_rows(rows, meta)
    print(path, "rows", meta["rows"])


if __name__ == "__main__":
    main()

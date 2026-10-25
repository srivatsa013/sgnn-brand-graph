"""One real Phase 5 fit. Choices below were fixed before any test metric.

- Ecosystems are the frozen Arm A 14 and Arm B 13. The plan's earlier three-brand
  sentence was replaced by the 2026-10-23 log. The four sources are not pooled.
- Neighbor labels use the series with the brand excluded, key (neighbor, brand).
  Brand features use (brand, ""). Mentions in a bin are cell[2]. Sentiment is
  cell[0]/cell[1]. The baseline triple comes from phase1_gates.baseline.
- Node order is sorted names. One-hot is brand, parent, product, competitor,
  CEO, other. product and manufacturer map to product. owned_by maps to other.
  A CEO node is CEO only on a day inside configs/ceo_tenures.json. Parent is
  in the vector and is unused by these edges.
- Co-mention rows exist for Arm A news and social only. Joined and headline
  both use the news rows. Arm B has no co-mention table, so those edges are absent.
- Same-day events stay in one fold. Cuts move to a day boundary near 60/20/20.
- The grid is selected by mean validation MAE across seeds 0-4. Ties take the
  smaller hidden size, then depth, then dropout. Rejected configs are not tested.
- Learned baselines are signed, unsigned, and no-graph, each with the grid.
  Sign-shuffled, degree-matched, and linear diffusion use the selected signed
  hyperparameters. Linear diffusion is one training-fold coefficient on edge
  sign times shock z, feature index 31, and has no seed.
- Degree-matched rewiring is inside each ecosystem, target 1. Sign shuffle
  permutes structural signs once per ecosystem per seed. Co-mention stays.
- Event MAE is averaged across seeds, then one paired permutation (seed 1,
  1000) and one clustered bootstrap (seed 0, 1000).
- The Holm family of 8 is per arm. Arm A inserts the joined-news H3 p-values.
  Arm B inserts the GDELT H3 p-values. Social and TweetsKB are reported and
  are not a second family. Phase 4 files are not rewritten.
- Leave-one-ecosystem-out uses seed 0 and the selected signed hyperparameters.
  It is robustness and is not a Holm test.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import random
import sqlite3
import subprocess
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import phase4_analysis as A  # noqa: E402
import phase4_outcome_run as R  # noqa: E402
from phase1_gates import baseline, detect_daily, window_mean  # noqa: E402
from phase2_gdelt_reserve_after import ARM_B, series_from_db  # noqa: E402
from phase2_tweetskb_arm_b_counts import build_series  # noqa: E402
from phase5_model import (  # noqa: E402
    Edge,
    Event,
    SignedMP,
    _event_errors,
    _scale_stats,
    apply_scaler,
    evaluate,
    leakage_failures,
    train_loop,
)
from phase5_model import mean_of_neighbors  # noqa: E402

torch.set_num_threads(4)

IN_DIM = 33
SHOCK_Z = 31
SEEDS = (0, 1, 2, 3, 4)
GRID = tuple((h, d, p) for h in (32, 64) for d in (1, 2) for p in (0.0, 0.2))
LEARNED = ("signed", "unsigned", "no_graph")
TYPE_AT = {"brand": 0, "parent": 1, "product": 2, "competitor": 3, "ceo": 4, "other": 5}
SOURCES = (
    ("news_joined", "A", "news"),
    ("social", "A", "social"),
    ("gdelt", "B", None),
    ("tweetskb", "B", None),
)
PRIMARY = {"A": "news_joined", "B": "gdelt"}
BUILD = ROOT / "eval" / "results" / "phase5_build.json"
EVENTS = ROOT / "eval" / "results" / "phase5_events.pt"
LABELS = ROOT / "eval" / "results" / "phase5_label_table.parquet"
MODELS = ROOT / "eval" / "results" / "phase5_models"
OUT_JSON = ROOT / "eval" / "results" / "phase5_outcomes.json"
OUT_MD = ROOT / "reports" / "phase5_outcomes.md"


def script_sha() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def preconditions() -> None:
    free = os.statvfs(ROOT).f_bavail * os.statvfs(ROOT).f_frsize
    print(f"free_bytes {free}", flush=True)
    if free < 6_000_000_000:
        raise SystemExit("free disk is below 6 GB")
    listing = subprocess.check_output(["ps", "ax", "-o", "pid=,command="], text=True)
    hits = []
    for line in listing.splitlines():
        low = line.lower()
        if "phase4_watchdog" in low or "caffeinate" in low or "phase5_train" in low:
            continue
        if any(token in low for token in (" bq ", "gcloud", "phase2_gdelt", "phase3_score", "score_fnspid")):
            hits.append(line.strip())
    if hits:
        raise SystemExit("collection job still running: " + " | ".join(hits))
    tests = subprocess.run([sys.executable, str(ROOT / "scripts" / "test_phase5_model.py")], cwd=ROOT)
    if tests.returncode != 0:
        raise SystemExit("synthetic tests failed")
    hashed = subprocess.run([sys.executable, str(ROOT / "scripts" / "check_frozen_sha256.py")], cwd=ROOT)
    if hashed.returncode != 0:
        raise SystemExit("hash check failed")


def ceo_windows() -> dict[str, list[tuple[date, date]]]:
    payload = json.loads((ROOT / "configs" / "ceo_tenures.json").read_text())
    found = {}
    for node, people in payload["nodes"].items():
        spans = []
        for person in people:
            windows = person["windows"] if "windows" in person else [person]
            for window in windows:
                start = date.fromisoformat(window["start"])
                end = date.fromisoformat(window["end"]) if window.get("end") else date(9999, 12, 31)
                spans.append((start, end))
        found[node] = spans
    return found


def in_office(node: str, t0: date, windows: dict) -> bool:
    return any(start <= t0 <= end for start, end in windows.get(node, []))


def node_kind(name: str, eco: str, spec: dict, properties: dict[str, str], t0: date, windows: dict) -> str:
    if name == eco:
        return "brand"
    if name.endswith(" CEO"):
        return "ceo" if in_office(name, t0, windows) else "other"
    if name in spec["competitor_nodes"]:
        return "competitor"
    key = properties.get(name, "")
    if key in {"product", "manufacturer"}:
        return "product"
    return "other"


def property_map() -> dict[str, dict[str, str]]:
    graph = json.loads((ROOT / "kg" / "phase2_structural_edges.json").read_text())
    found: dict[str, dict[str, str]] = defaultdict(dict)
    for edge in graph["positive_edges"]:
        left, right = edge["nodes"]
        key = edge.get("property_key", "")
        found[left][right] = key
        found[right][left] = key
    return found


def load_comention() -> dict[tuple[str, str, str], list[tuple[str, int]]]:
    path = ROOT / "data" / "interim" / "phase2" / "series.sqlite"
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    grouped: dict[tuple[str, str, str], list[tuple[str, int]]] = defaultdict(list)
    for source, left, right, day, count in con.execute("SELECT source, node_a, node_b, day, n FROM comention"):
        a, b = sorted((left, right))
        grouped[(source, a, b)].append((day, int(count)))
    con.close()
    for rows in grouped.values():
        rows.sort()
    return grouped


def comention_edges(index, source: str | None, names: list[str], t0: date) -> tuple[list[Edge], list[int]]:
    if source is None:
        return [], []
    start = (t0 - timedelta(days=187)).isoformat()
    end = (t0 - timedelta(days=8)).isoformat()
    lookup = {name: i for i, name in enumerate(names)}
    edges = []
    days = set()
    for i, left in enumerate(names):
        for right in names[i + 1 :]:
            rows = index.get((source, *sorted((left, right))))
            if not rows:
                continue
            total = 0
            for day, count in rows:
                if day < start:
                    continue
                if day > end:
                    break
                total += count
                days.add(day)
            if total < 3:
                continue
            weight = math.log1p(total)
            edges.append(Edge(lookup[left], lookup[right], "co", 0.0, weight))
            edges.append(Edge(lookup[right], lookup[left], "co", 0.0, weight))
    ordinals = [date.fromisoformat(day).toordinal() for day in sorted(days)]
    return edges, ordinals


def fill_features(series: dict, t0: date, row: torch.Tensor) -> None:
    for slot, lag in enumerate(range(7, 0, -1)):
        cell = series.get((t0 - timedelta(days=lag)).isoformat())
        if cell and cell[1] >= 1:
            base = slot * 3
            row[base] = cell[0] / cell[1]
            row[base + 1] = 1.0
            row[base + 2] = math.log1p(cell[2])
    stats = baseline(series, t0, 28, 14)
    if stats:
        row[21], row[22], row[23] = stats


class Simple:
    def __init__(self, t0: int, event_id: str):
        self.t0 = t0
        self.event_id = event_id


def day_folds(events: list) -> tuple[list, list, list, dict]:
    ordered = sorted(events, key=lambda event: (event.t0, event.event_id))
    n = len(ordered)
    if n < 15:
        split = __import__("phase5_model", fromlist=["chronological_split"]).chronological_split(events)
        if split["mode"] == "leave_one_event_out":
            return [], [], [], {"mode": split["mode"], "splits": split["splits"]}
        return split["train"], split["val"], split["test"], {"mode": split["mode"]}
    groups: list[list] = []
    for event in ordered:
        if not groups or groups[-1][0].t0 != event.t0:
            groups.append([])
        groups[-1].append(event)
    target_train = n * 60 // 100
    target_val = n * 80 // 100
    train, val, test = [], [], []
    seen = 0
    for group in groups:
        if seen < target_train:
            train.extend(group)
        elif seen < target_val:
            val.extend(group)
        else:
            test.extend(group)
        seen += len(group)
    if test == [] and val:
        moved = [event for event in val if event.t0 == val[-1].t0]
        val = [event for event in val if event.t0 != val[-1].t0]
        test = moved
    if val == [] and len(train) > 1:
        moved = [event for event in train if event.t0 == train[-1].t0]
        remain = [event for event in train if event.t0 != train[-1].t0]
        if remain:
            train, val = remain, moved
    info = {"mode": "day_boundary_60_20_20", "n_train": len(train), "n_val": len(val), "n_test": len(test)}
    return train, val, test, info


def self_check_folds() -> None:
    unique = [Simple(i, f"e{i}") for i in range(20)]
    train, val, test, _info = day_folds(unique)
    assert train and val and test
    assert max(event.t0 for event in train) < min(event.t0 for event in test)
    paired = [Simple(i // 2, f"e{i}") for i in range(20)]
    train, val, test, _info = day_folds(paired)
    assert train and val and test
    assert max(event.t0 for event in train) < min(event.t0 for event in val)
    assert max(event.t0 for event in val) < min(event.t0 for event in test)
    train_days = {event.t0 for event in train}
    assert train_days.isdisjoint({event.t0 for event in test})


def build_all() -> dict:
    windows = ceo_windows()
    properties = property_map()
    comention = load_comention()
    print("loading series", flush=True)
    arm_a = R.load_arm_a()
    arm_b = {"gdelt": series_from_db(R.GDELT_DB), "tweetskb": build_series()}
    series_of = {**arm_a, **arm_b}
    ecosystems = {"A": list(R.ARM_A), "B": list(ARM_B)}
    label_rows = []
    saved = {}
    counts = {}
    for source, arm, co_source in SOURCES:
        series = series_of[source]
        cache = R.Cache(series)
        built = []
        unlabeled_events = 0
        for eco in ecosystems[arm]:
            spec = R.NODES["ecosystems"][eco]
            members = sorted(set([eco, *spec["positive_nodes"], *spec["competitor_nodes"]]))
            names = set(members)
            arcs = [edge for edge in R.structural_edges(names) if edge[0] in names and edge[1] in names]
            targets = R.registered_targets(eco)
            for t0 in detect_daily(cache.block(eco, "")):
                features = torch.zeros(len(members), IN_DIM)
                for index, name in enumerate(members):
                    exclude = "" if name == eco else eco
                    fill_features(cache.block(name, exclude), t0, features[index])
                    kind = node_kind(name, eco, spec, properties.get(eco, {}), t0, windows)
                    features[index, 24 + TYPE_AT[kind]] = 1.0
                brand = cache.block(eco, "")
                cell = brand[t0.isoformat()]
                stats = baseline(brand, t0, 28, 14)
                brand_index = members.index(eco)
                features[brand_index, 30] = cell[0] / cell[1]
                features[brand_index, SHOCK_Z] = (cell[0] / cell[1] - stats[0]) / stats[1]
                features[brand_index, 32] = 1.0
                lookup = {name: index for index, name in enumerate(members)}
                struct = [Edge(lookup[left], lookup[right], "struct", float(sign), 1.0) for left, right, sign in arcs if left in lookup and right in lookup]
                co_edges, co_days = comention_edges(comention, co_source, members, t0)
                labels = {}
                for name, edge_class in targets:
                    block = cache.block(name, eco)
                    pre = window_mean(block, t0 - timedelta(days=7), t0 - timedelta(days=1), 3)
                    post = window_mean(block, t0, t0 + timedelta(days=7), 3)
                    if pre is None or post is None:
                        continue
                    labels[lookup[name]] = post - pre
                    sign = 0 if edge_class is None else (1 if edge_class == "positive" else -1)
                    label_rows.append({
                        "source": source,
                        "arm": arm,
                        "ecosystem": eco,
                        "event_id": f"{source}:{eco}:{t0.isoformat()}",
                        "t0": t0.isoformat(),
                        "neighbor": name,
                        "edge_class": edge_class or "both",
                        "edge_sign": sign,
                        "shift": post - pre,
                        "is_synthetic": 0,
                    })
                if not labels:
                    unlabeled_events += 1
                history = [(t0 - timedelta(days=lag)).toordinal() for lag in range(1, 29)]
                event = Event(
                    event_id=f"{source}:{eco}:{t0.isoformat()}",
                    t0=t0.toordinal(),
                    features=features,
                    edges=struct + co_edges,
                    labels=labels,
                    comention_times=co_days,
                    history_times=history,
                    feature_doc_ids={f"feature:{source}:{eco}:{t0.isoformat()}"},
                    label_doc_ids={f"label:{source}:{eco}:{t0.isoformat()}"},
                )
                built.append({"event": event, "ecosystem": eco, "t0_iso": t0.isoformat(), "names": members})
        saved[source] = built
        counts[source] = {"events": len(built), "labels": sum(row["source"] == source for row in label_rows), "events_without_labels": unlabeled_events}
        print(source, counts[source], flush=True)
    pq.write_table(pa.Table.from_pylist(label_rows), LABELS)
    torch.save(saved, EVENTS)
    return counts


def restore_events() -> dict:
    return torch.load(EVENTS, weights_only=False)


def leakage_or_stop(saved: dict) -> dict:
    report = {}
    for source, _arm, _co in SOURCES:
        events = [row["event"] for row in saved[source]]
        train, val, test, info = day_folds(events)
        if info.get("mode") == "leave_one_event_out":
            report[source] = info
            continue
        if not train or not val or not test:
            raise SystemExit(f"empty fold for {source}: {info}")
        failures = leakage_failures(train, val, test, {event.event_id for event in train}, {event.event_id for event in train})
        info["leakage_failures"] = failures
        report[source] = info
        if failures:
            raise SystemExit(f"leakage failed for {source}: {failures}")
        print(f"leakage {source} pass {info}", flush=True)
    return report


def fit_state(train, val, variant, hidden, depth, dropout, seed):
    model = SignedMP(IN_DIM, hidden, depth, dropout, variant)
    info = train_loop(model, train, val, seed=seed)
    mean, std = _scale_stats(train)
    val_mae = evaluate(model, val, mean, std)["mae"]
    state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
    return state, mean.detach().cpu(), std.detach().cpu(), val_mae, info["epochs_ran"]


def load_model(state, hidden, depth, dropout, variant) -> SignedMP:
    model = SignedMP(IN_DIM, hidden, depth, dropout, variant)
    model.load_state_dict(state)
    model.eval()
    return model


def event_maes(model, events, mean, std) -> dict[str, float]:
    found = {}
    with torch.no_grad():
        for event in events:
            pred, _ = model.predict(apply_scaler(event, mean, std), event.edges)
            mae, _rmse, _sign, _skip = _event_errors(pred, event.labels)
            if event.labels:
                found[event.event_id] = mae
    return found


def choose(table: dict) -> tuple:
    best = None
    for config, by_seed in table.items():
        values = list(by_seed.values())
        if len(values) != len(SEEDS) or any(value is None for value in values):
            continue
        score = sum(values) / len(values)
        key = (score, config[0], config[1], config[2])
        if best is None or key < best[0]:
            best = (key, config, score)
    if best is None:
        raise RuntimeError("no validation MAE")
    return best[1], best[2]


def mean_map(maps: list[dict]) -> dict[str, float]:
    keys = set.intersection(*(set(item) for item in maps)) if maps else set()
    return {key: sum(item[key] for item in maps) / len(maps) for key in keys}


def sample_sd(values: list[float]) -> float | None:
    if len(values) < 2:
        return None
    center = sum(values) / len(values)
    return math.sqrt(sum((value - center) ** 2 for value in values) / (len(values) - 1))


def compare(signed_map: dict, other_map: dict, clusters_of: dict) -> dict:
    diffs = []
    clusters = defaultdict(list)
    for event_id, signed in signed_map.items():
        diff = signed - other_map[event_id]
        diffs.append(diff)
        clusters[clusters_of[event_id]].append(diff)
    boot = A.clustered_bootstrap(clusters, 1000, 0)
    draws = A.pair_permutation(diffs, 1000, 1)
    mae_signed = sum(signed_map.values()) / len(signed_map)
    mae_other = sum(other_map[key] for key in signed_map) / len(signed_map)
    relative = None if mae_other == 0 else (mae_other - mae_signed) / mae_other
    return {
        "mae_signed": mae_signed,
        "mae_other": mae_other,
        "gap": boot["estimate"],
        "low": boot["low"],
        "high": boot["high"],
        "permutation_p": A.permutation_p(boot["estimate"], draws),
        "relative_mae_gain": relative,
        "n_events": len(diffs),
    }


def clone(event: Event, edges: list[Edge]) -> Event:
    return Event(event.event_id, event.t0, event.features, edges, event.labels, event.comention_times, event.history_times, event.feature_doc_ids, event.label_doc_ids)


def sign_shuffled(rows: list[dict], seed: int) -> list[Event]:
    """Permute structural signs once per ecosystem. Co-mention edges stay."""
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["ecosystem"]].append(row)
    replaced = {}
    for eco, group in grouped.items():
        rng = random.Random(f"{seed}:{eco}")
        struct = [edge for edge in group[0]["event"].edges if edge.kind == "struct"]
        signs = [edge.sign for edge in struct]
        rng.shuffle(signs)
        sign_of = {(edge.src, edge.dst): sign for edge, sign in zip(struct, signs)}
        for row in group:
            changed = []
            for edge in row["event"].edges:
                if edge.kind == "struct":
                    changed.append(Edge(edge.src, edge.dst, edge.kind, sign_of[(edge.src, edge.dst)], edge.weight))
                else:
                    changed.append(edge)
            replaced[row["event"].event_id] = clone(row["event"], changed)
    return [replaced[row["event"].event_id] for row in rows]


def degree_matched(rows: list[dict], seed: int) -> list[Event]:
    by_eco = defaultdict(list)
    for row in rows:
        by_eco[row["ecosystem"]].append(row)
    replaced = {}
    for eco, group in by_eco.items():
        names = group[0]["names"]
        lookup = {name: index for index, name in enumerate(names)}
        arcs = []
        seen = set()
        for edge in group[0]["event"].edges:
            if edge.kind != "struct":
                continue
            key = (names[edge.src], names[edge.dst], int(edge.sign))
            if key not in seen:
                seen.add(key)
                arcs.append(key)
        graphs = A.rewire(arcs, target=1, seed=seed) if len(arcs) >= 2 else {"graphs": []}
        chosen = graphs["graphs"][0] if graphs["graphs"] else None
        for row in group:
            co = [edge for edge in row["event"].edges if edge.kind != "struct"]
            if chosen is None:
                struct = [edge for edge in row["event"].edges if edge.kind == "struct"]
            else:
                struct = [Edge(lookup[a], lookup[b], "struct", float(sign), 1.0) for a, b, sign in chosen if a in lookup and b in lookup]
            replaced[row["event"].event_id] = clone(row["event"], struct + co)
    return [replaced[row["event"].event_id] for row in rows]


def linear_maes(train, test) -> dict[str, float]:
    num = den = 0.0
    for event in train:
        guess = mean_of_neighbors(event.features, event.edges, SHOCK_Z)
        for node, label in event.labels.items():
            value = float(guess[node])
            num += value * label
            den += value * value
    beta = 0.0 if den == 0 else num / den
    found = {}
    for event in test:
        guess = mean_of_neighbors(event.features, event.edges, SHOCK_Z)
        errors = []
        for node, label in event.labels.items():
            errors.append(abs(beta * float(guess[node]) - label))
        if errors:
            found[event.event_id] = sum(errors) / len(errors)
    return found, beta


def train_source(source: str, rows: list[dict], sha: str) -> dict:
    events = [row["event"] for row in rows]
    train, val, test, info = day_folds(events)
    meta = {row["event"].event_id: (row["ecosystem"], date.fromordinal(row["event"].t0).isocalendar()[:2]) for row in rows}
    zeros = sum(1 for event in test for label in event.labels.values() if label == 0)
    learned_states = {}
    val_table = {variant: {} for variant in LEARNED}
    for seed in SEEDS:
        for variant in LEARNED:
            for hidden, depth, dropout in GRID:
                print(f"{source} seed {seed} {variant} h{hidden} d{depth} p{dropout}", flush=True)
                state, mean, std, val_mae, epochs = fit_state(train, val, variant, hidden, depth, dropout, seed)
                config = (hidden, depth, dropout)
                val_table[variant].setdefault(config, {})[seed] = val_mae
                learned_states.setdefault((variant, config, seed), (state, mean, std, epochs))
                print(f"  val {val_mae} epochs {epochs}", flush=True)
    chosen = {}
    maps = {variant: [] for variant in LEARNED}
    seed_mae = {variant: [] for variant in LEARNED}
    epochs = {variant: [] for variant in LEARNED}
    MODELS.mkdir(parents=True, exist_ok=True)
    for variant in LEARNED:
        config, score = choose(val_table[variant])
        chosen[variant] = {"hidden": config[0], "depth": config[1], "dropout": config[2], "mean_validation_mae": score}
        for seed in SEEDS:
            state, mean, std, ran = learned_states[(variant, config, seed)]
            model = load_model(state, *config, variant)
            by_event = event_maes(model, test, mean, std)
            maps[variant].append(by_event)
            seed_mae[variant].append(sum(by_event.values()) / len(by_event))
            epochs[variant].append(ran)
            if variant == "signed":
                torch.save({"state": state, "mean": mean, "std": std, "config": chosen[variant], "seed": seed}, MODELS / f"{source}_seed{seed}.pt")
    signed = mean_map(maps["signed"])
    no_graph = mean_map(maps["no_graph"])
    unsigned = mean_map(maps["unsigned"])
    secondary = {"sign_shuffled": [], "degree_matched": []}
    signed_config = chosen["signed"]
    for seed in SEEDS:
        print(f"{source} secondary seed {seed}", flush=True)
        for name, edited in (
            ("sign_shuffled", sign_shuffled(rows, seed)),
            ("degree_matched", degree_matched(rows, seed)),
        ):
            edited_train, edited_val, edited_test, _info = day_folds(edited)
            state, mean, std, _val, _ran = fit_state(edited_train, edited_val, "signed", signed_config["hidden"], signed_config["depth"], signed_config["dropout"], seed)
            model = load_model(state, signed_config["hidden"], signed_config["depth"], signed_config["dropout"], "signed")
            secondary[name].append(event_maes(model, edited_test, mean, std))
    linear, beta = linear_maes(train, test)
    models = {}
    averaged = {
        "signed": signed,
        "unsigned": unsigned,
        "no_graph": no_graph,
        "sign_shuffled": mean_map(secondary["sign_shuffled"]),
        "degree_matched": mean_map(secondary["degree_matched"]),
        "linear_diffusion": linear,
    }
    seed_lists = {
        "signed": seed_mae["signed"],
        "unsigned": seed_mae["unsigned"],
        "no_graph": seed_mae["no_graph"],
        "sign_shuffled": [sum(item.values()) / len(item) for item in secondary["sign_shuffled"]],
        "degree_matched": [sum(item.values()) / len(item) for item in secondary["degree_matched"]],
        "linear_diffusion": [sum(linear.values()) / len(linear)],
    }
    for name, by_event in averaged.items():
        gap = compare(by_event, no_graph, meta) if name != "no_graph" else None
        models[name] = {
            "test_mae": sum(seed_lists[name]) / len(seed_lists[name]),
            "test_mae_sd": sample_sd(seed_lists[name]),
            "gap_to_no_graph": None if gap is None else gap["gap"],
            "interval": None if gap is None else [gap["low"], gap["high"]],
            "permutation_p": None if gap is None else gap["permutation_p"],
            "relative_mae_gain": None if gap is None else gap["relative_mae_gain"],
        }
    h3 = {
        "signed_vs_unsigned": compare(signed, unsigned, meta),
        "signed_vs_nograph": compare(signed, no_graph, meta),
    }
    result = {
        "sha": sha,
        "source": source,
        "split": info,
        "exact_zero_test_labels": zeros,
        "chosen": chosen,
        "epochs_ran": epochs,
        "validation_grid": {variant: {str(config): by_seed for config, by_seed in table.items()} for variant, table in val_table.items()},
        "models": models,
        "h3": h3,
        "linear_beta": beta,
    }
    path = ROOT / "eval" / "results" / f"phase5_source_{source}.json"
    path.write_text(json.dumps(result) + "\n")
    result["loeo"] = leave_one_ecosystem(rows, signed_config)
    path.write_text(json.dumps(result) + "\n")
    return result


def leave_one_ecosystem(rows: list[dict], config: dict) -> list[dict]:
    ecos = sorted({row["ecosystem"] for row in rows})
    report = []
    for eco in ecos:
        held = [row["event"] for row in rows if row["ecosystem"] == eco]
        rest = [row["event"] for row in rows if row["ecosystem"] != eco]
        if not any(event.labels for event in held) or len(rest) < 5:
            report.append({"ecosystem": eco, "test_mae": None, "n_test": len(held)})
            continue
        ordered = sorted(rest, key=lambda event: (event.t0, event.event_id))
        cut = max(1, len(ordered) * 80 // 100)
        state, mean, std, _val, _ran = fit_state(ordered[:cut], ordered[cut:], "signed", config["hidden"], config["depth"], config["dropout"], 0)
        model = load_model(state, config["hidden"], config["depth"], config["dropout"], "signed")
        by_event = event_maes(model, held, mean, std)
        report.append({"ecosystem": eco, "test_mae": None if not by_event else sum(by_event.values()) / len(by_event), "n_test": len(by_event)})
        print(f"loeo {eco} {report[-1]['test_mae']}", flush=True)
    return report


def holm_block(results: dict) -> dict:
    stored = json.loads((ROOT / "eval" / "results" / "phase4_outcomes.json").read_text())
    out = {}
    for arm, source in PRIMARY.items():
        news = stored["arms"][arm]["sources"][source]
        h4 = stored["arms"][arm]["h4"]
        pvalues = {
            "H1_pair_permutation": news["H1"].get("permutation_p"),
            "H1_rewiring": news["H1"].get("rewiring_p"),
            "H2_positive_edges": news["H2_positive"].get("permutation_p"),
            "H2_competitor_edges": news["H2_competitor"].get("permutation_p"),
            "H3_signed_vs_unsigned": results[source]["h3"]["signed_vs_unsigned"]["permutation_p"],
            "H3_signed_vs_nograph": results[source]["h3"]["signed_vs_nograph"]["permutation_p"],
            "H4_magnitude": h4["magnitude"].get("permutation_p"),
            "H4_lag": h4["lag"].get("permutation_p"),
        }
        adjusted = A.holm(pvalues)
        decisions = {}
        for key, family in (("signed_vs_unsigned", "H3_signed_vs_unsigned"), ("signed_vs_nograph", "H3_signed_vs_nograph")):
            row = results[source]["h3"][key]
            relative = row["relative_mae_gain"]
            decisions[key] = A.h3_decision(row["gap"], adjusted["rejected"][family], row["low"], row["high"], -1 if relative is None else relative)
        out[arm] = {"pvalues": pvalues, "holm": adjusted, "h3_decision": decisions, "final": True, "primary_source": source}
    return out


def support_text(decision: str | None) -> str:
    return decision or "not in the registered family of 8"


def render(payload: dict) -> str:
    lines = [
        "# Phase 5 outcomes",
        "",
        "One fit. Hyperparameters were chosen on validation MAE. The Holm family of 8 is recomputed here and marked final. `eval/results/phase4_outcomes.json` still holds the family-of-6 adjustment from when H3 was not run.",
        "",
        "H3 is supported only when the MAE gap is negative, the Holm p-value is below 0.05, the interval excludes 0, and the relative MAE gain is at least 5 percent. Social and TweetsKB are outside that family.",
        "",
    ]
    for source, block in payload["sources"].items():
        lines.append(f"## {source}")
        lines.append("")
        chosen = block["chosen"]["signed"]
        lines.append(f"Selected signed model: hidden {chosen['hidden']}, depth {chosen['depth']}, dropout {chosen['dropout']}, mean validation MAE {chosen['mean_validation_mae']:.6g}. Exact-zero test labels ignored: {block['exact_zero_test_labels']}.")
        lines.append("")
        lines.append("| Model | Test MAE | SD | Gap to no-graph | 95% interval | p | Relative MAE gain |")
        lines.append("|---|---:|---:|---:|---|---:|---:|")
        for name, row in block["models"].items():
            interval = "" if row["interval"] is None else f"[{row['interval'][0]:.6g}, {row['interval'][1]:.6g}]"
            lines.append(f"| {name} | {row['test_mae']:.6g} | {'' if row['test_mae_sd'] is None else f'{row['test_mae_sd']:.6g}'} | {'' if row['gap_to_no_graph'] is None else f'{row['gap_to_no_graph']:.6g}'} | {interval} | {'' if row['permutation_p'] is None else f'{row['permutation_p']:.6g}'} | {'' if row['relative_mae_gain'] is None else f'{row['relative_mae_gain']:.6g}'} |")
        lines.append("")
        for key, row in block["h3"].items():
            decision = payload["support"].get(source, {}).get(key)
            lines.append(f"{key}: gap {row['gap']:.6g}, interval [{row['low']:.6g}, {row['high']:.6g}], p {row['permutation_p']:.6g}, relative gain {row['relative_mae_gain']:.6g}, H3 {support_text(decision)}.")
        lines.append("")
        lines.append("| Held-out ecosystem | Test MAE | Events |")
        lines.append("|---|---:|---:|")
        for row in block.get("loeo", []):
            value = "" if row["test_mae"] is None else f"{row['test_mae']:.6g}"
            lines.append(f"| {row['ecosystem']} | {value} | {row['n_test']} |")
        lines.append("")
    lines.append("## Final Holm family of 8")
    lines.append("")
    for arm, block in payload["holm"].items():
        lines.append(f"### Arm {arm} ({block['primary_source']}), family size {block['holm']['family_size']}")
        lines.append("")
        lines.append("| Test | Unadjusted p | Holm p | Rejects |")
        lines.append("|---|---:|---:|---|")
        for name in A.FAMILY:
            raw = block["pvalues"].get(name)
            adj = block["holm"]["adjusted"].get(name)
            lines.append(f"| {name} | {'' if raw is None else f'{raw:.6g}'} | {'' if adj is None else f'{adj:.6g}'} | {block['holm']['rejected'].get(name)} |")
        lines.append("")
    return "\n".join(lines) + "\n"


def main() -> None:
    self_check_folds()
    sha = script_sha()
    preconditions()
    if BUILD.exists():
        built = json.loads(BUILD.read_text())
        if built.get("sha") != sha or not EVENTS.exists():
            counts = build_all()
            saved = restore_events()
            leakage = leakage_or_stop(saved)
            BUILD.write_text(json.dumps({"sha": sha, "counts": counts, "leakage": leakage}) + "\n")
        else:
            saved = restore_events()
    else:
        counts = build_all()
        saved = restore_events()
        leakage = leakage_or_stop(saved)
        BUILD.write_text(json.dumps({"sha": sha, "counts": counts, "leakage": leakage}) + "\n")
    results = {}
    for source, _arm, _co in SOURCES:
        path = ROOT / "eval" / "results" / f"phase5_source_{source}.json"
        if path.exists():
            prior = json.loads(path.read_text())
            if prior.get("sha") == sha and "models" in prior:
                if "loeo" not in prior:
                    prior["loeo"] = leave_one_ecosystem(saved[source], prior["chosen"]["signed"])
                    path.write_text(json.dumps(prior) + "\n")
                results[source] = prior
                continue
        results[source] = train_source(source, saved[source], sha)
    holm = holm_block(results)
    support = {}
    for source, _arm, _co in SOURCES:
        arm = _arm
        if source == PRIMARY[arm]:
            support[source] = holm[arm]["h3_decision"]
        else:
            support[source] = {"signed_vs_unsigned": None, "signed_vs_nograph": None}
    payload = {"sha": sha, "sources": results, "holm": holm, "support": support, "final_holm": True}
    OUT_JSON.write_text(json.dumps(payload) + "\n")
    OUT_MD.write_text(render(payload))
    print(f"wrote {OUT_MD}", flush=True)


if __name__ == "__main__":
    main()

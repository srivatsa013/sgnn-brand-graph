"""One augmented Phase 5 fit. These choices were fixed before any test metric.

The demonstration model is the signed model. The source is the stored
restricted joined-news events. Synthetic share is 0.5 of the combined event
count: one synthetic event for each real event. Lambda is 1.0. Noise is
normal with the frozen joined-news SD. A positive structural arc plants +1,
a competitor arc plants -1, and co-mention is not a label. The split is the
same day-boundary 60/20/20 rule. The grid is selected on validation MAE only.
The chosen models are then scored once on the augmented test fold and once
on the real events inside that fold.

This script does not write the real-only Phase 5 files.
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from phase5_model import Edge, Event, apply_scaler, channel_contribution, evaluate, leakage_failures  # noqa: E402
from phase5_train import (  # noqa: E402
    EVENTS,
    GRID,
    IN_DIM,
    SEEDS,
    SHOCK_Z,
    choose,
    day_folds,
    fit_state,
    load_model,
    sample_sd,
)

torch.set_num_threads(4)

SOURCE = "news_joined"
LAMBDA = 1.0
NOISE_SD = 0.2694611493987299
SHARE = 0.5
OUT_JSON = ROOT / "eval" / "results" / "phase5_augmented.json"
OUT_MD = ROOT / "reports" / "phase5_augmented.md"
MODEL_DIR = ROOT / "eval" / "results" / "phase5_augmented_models"
FORBIDDEN = {
    ROOT / "eval" / "results" / "phase5_outcomes.json",
    ROOT / "reports" / "phase5_outcomes.md",
    ROOT / "eval" / "results" / "phase5_events.pt",
    ROOT / "eval" / "results" / "phase5_label_table.parquet",
    ROOT / "eval" / "results" / "phase5_models",
}


def fmt(value) -> str:
    if value is None:
        return ""
    return f"{value:.6g}"


def structural_signs(event: Event, brand_index: int) -> dict[int, float]:
    found: dict[int, list[float]] = {}
    for edge in event.edges:
        if edge.kind != "struct" or edge.src != brand_index:
            continue
        found.setdefault(edge.dst, []).append(float(edge.sign))
    signs = {}
    for node, values in found.items():
        if all(value > 0 for value in values):
            signs[node] = 1.0
        elif all(value < 0 for value in values):
            signs[node] = -1.0
    return signs


def synthetic_event(row: dict) -> Event:
    event = row["event"]
    names = row["names"]
    brand_index = names.index(row["ecosystem"])
    shock = 1.0 if float(event.features[brand_index, SHOCK_Z]) >= 0 else -1.0
    labels = {}
    for node, edge_sign in structural_signs(event, brand_index).items():
        noise = random.Random(f"augmented-phase5-2026-10-24:{event.event_id}:{node}").gauss(0.0, NOISE_SD)
        labels[node] = LAMBDA * NOISE_SD * edge_sign * shock + noise
    stamp = f"{event.event_id}:synthetic"
    return Event(
        event_id=stamp,
        t0=event.t0,
        features=event.features.clone(),
        edges=[Edge(edge.src, edge.dst, edge.kind, edge.sign, edge.weight) for edge in event.edges],
        labels=labels,
        comention_times=list(event.comention_times),
        history_times=list(event.history_times),
        feature_doc_ids={f"synthetic-feature:{stamp}"},
        label_doc_ids={f"synthetic-label:{stamp}"},
    )


def mean(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def pack(metrics: list[dict]) -> dict:
    def column(key: str) -> list[float]:
        return [item[key] for item in metrics if item[key] is not None]

    mae = column("mae")
    rmse = column("rmse")
    sign = column("sign_accuracy")
    return {
        "mae": mean(mae),
        "mae_sd": sample_sd(mae),
        "rmse": mean(rmse),
        "rmse_sd": sample_sd(rmse),
        "sign_accuracy": mean(sign),
        "sign_accuracy_sd": sample_sd(sign),
        "events": metrics[-1]["events"] if metrics else 0,
    }


def render(payload: dict) -> str:
    chosen = payload["chosen"]
    lines = [
        "# Augmented run (contains synthetic events)",
        "",
        "One signed fit on the augmented joined-news events. Hyperparameters were chosen on validation MAE. This file does not replace the real-only Phase 5 results.",
        "",
        f"Synthetic share {fmt(payload['synthetic_share'])}. Lambda {fmt(payload['lambda'])}. Frozen noise SD {payload['noise_sd']}. Real events {payload['n_real']}. Synthetic events {payload['n_synthetic']}.",
        "",
        f"Selected signed model: hidden {chosen['hidden']}, depth {chosen['depth']}, dropout {chosen['dropout']}, mean validation MAE {fmt(chosen['mean_validation_mae'])}.",
        "",
        "| Split | Events | Test MAE | SD | Test RMSE | SD | Sign accuracy | SD |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name in ("augmented_test", "real_only_test"):
        block = payload["evaluation"][name]
        lines.append(
            f"| {name} | {block['events']} | {fmt(block['mae'])} | {fmt(block['mae_sd'])} | {fmt(block['rmse'])} | {fmt(block['rmse_sd'])} | {fmt(block['sign_accuracy'])} | {fmt(block['sign_accuracy_sd'])} |"
        )
    lines.extend(["", "Per-edge-class estimates on the augmented test fold. These are mean absolute channel contributions.", ""])
    lines.append("| Edge class | Estimate |")
    lines.append("|---|---:|")
    for name, value in payload["edge_class_estimates"].items():
        lines.append(f"| {name} | {fmt(value)} |")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    for path in (OUT_JSON, OUT_MD, MODEL_DIR):
        if path in FORBIDDEN or path.name in {"phase5_outcomes.json", "phase5_outcomes.md"}:
            raise SystemExit("refusing to write a real-only file")
    saved = torch.load(EVENTS, weights_only=False)
    rows = saved[SOURCE]
    synthetic = [synthetic_event(row) for row in rows]
    combined = [row["event"] for row in rows] + synthetic
    real_ids = {row["event"].event_id for row in rows}
    names_of = {row["event"].event_id: row["names"] for row in rows}
    for row, event in zip(rows, synthetic):
        names_of[event.event_id] = row["names"]
    train, val, test, info = day_folds(combined)
    print("folds", info, "share", len(synthetic) / len(combined), flush=True)
    if not train or not val or not test:
        raise SystemExit(f"empty fold: {info}")
    failures = leakage_failures(train, val, test, {event.event_id for event in train}, {event.event_id for event in train})
    if failures:
        raise SystemExit(f"leakage failed: {failures[:8]}")
    print("leakage pass", flush=True)
    val_table: dict = {}
    states = {}
    for seed in SEEDS:
        for hidden, depth, dropout in GRID:
            print(f"seed {seed} h{hidden} d{depth} p{dropout}", flush=True)
            state, mean_s, std_s, val_mae, epochs = fit_state(train, val, "signed", hidden, depth, dropout, seed)
            config = (hidden, depth, dropout)
            val_table.setdefault(config, {})[seed] = val_mae
            states[(config, seed)] = (state, mean_s, std_s, epochs)
            print(f"  val {val_mae} epochs {epochs}", flush=True)
    config, score = choose(val_table)
    print("chosen", config, score, flush=True)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    real_test = [event for event in test if event.event_id in real_ids]
    augmented_metrics = []
    real_metrics = []
    class_rows = []
    node_sums: dict[str, float] = {}
    node_counts: dict[str, int] = {}
    for seed in SEEDS:
        state, mean_s, std_s, epochs = states[(config, seed)]
        torch.save({"state": state, "mean": mean_s, "std": std_s, "config": {"hidden": config[0], "depth": config[1], "dropout": config[2]}, "seed": seed}, MODEL_DIR / f"seed{seed}.pt")
        model = load_model(state, *config, "signed")
        augmented_metrics.append(evaluate(model, test, mean_s, std_s))
        real_metrics.append(evaluate(model, real_test, mean_s, std_s))
        class_rows.append(channel_contribution(model, test, mean_s, std_s))
        with torch.no_grad():
            for event in real_test:
                pred, _ = model.predict(apply_scaler(event, mean_s, std_s), event.edges)
                for index, name in enumerate(names_of[event.event_id]):
                    node_sums[name] = node_sums.get(name, 0.0) + float(pred[index])
                    node_counts[name] = node_counts.get(name, 0) + 1
    estimates = {}
    for key in ("positive", "negative", "comention"):
        estimates[key] = sum(row[key] for row in class_rows) / len(class_rows)
    node_shift = {name: node_sums[name] / node_counts[name] for name in sorted(node_sums)}
    payload = {
        "contains_synthetic_events": True,
        "source": SOURCE,
        "synthetic_share": len(synthetic) / len(combined),
        "lambda": LAMBDA,
        "noise_sd": NOISE_SD,
        "n_real": len(rows),
        "n_synthetic": len(synthetic),
        "split": info,
        "leakage_failures": failures,
        "chosen": {"hidden": config[0], "depth": config[1], "dropout": config[2], "mean_validation_mae": score},
        "evaluation": {"augmented_test": pack(augmented_metrics), "real_only_test": pack(real_metrics)},
        "edge_class_estimates": estimates,
        "node_shift": node_shift,
    }
    if payload["synthetic_share"] != SHARE:
        raise SystemExit(f"share {payload['synthetic_share']} is not {SHARE}")
    OUT_JSON.write_text(json.dumps(payload) + "\n")
    OUT_MD.write_text(render(payload))
    print(f"wrote {OUT_JSON}", flush=True)


if __name__ == "__main__":
    main()

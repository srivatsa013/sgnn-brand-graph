"""Phase 6 on the validation-chosen signed model. No new selection.

Choices fixed before these tables are used for anything else:
- Channel ablations keep one edge kind at prediction time and do not refit.
- Depth 1 and depth 2 both use the chosen hidden size and dropout. Seeds 0-4.
  A depth that was already saved is reloaded. The other depth is fit here.
- The attribution example is the earliest test event that has a label.
- A neighbor score is the mean absolute change in the labeled predictions
  when that neighbor's messages are replaced by the zero vector. The five
  largest scores are reported.
- Seed stability is seeds 0-9 at the chosen hyperparameters. Seeds 0-4 are
  the saved Phase 5 models. Seeds 5-9 are additional fits and do not reselect.
- Sign-shuffled and degree-matched intervals are copied from the Phase 5
  secondary fits at those same hyperparameters.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from phase5_model import Edge, Event, SignedMP, apply_scaler, channel_contribution, neighbor_attribution  # noqa: E402
from phase5_train import IN_DIM, SEEDS, clone, day_folds, event_maes, fit_state, load_model, sample_sd  # noqa: E402

EVENTS = ROOT / "eval" / "results" / "phase5_events.pt"
MODELS = ROOT / "eval" / "results" / "phase5_models"
OUT = ROOT / "reports" / "phase6_evaluation.md"
SOURCES = ("news_joined", "social", "gdelt", "tweetskb")


def saved_model(source: str, seed: int):
    payload = torch.load(MODELS / f"{source}_seed{seed}.pt", weights_only=False)
    config = payload["config"]
    model = load_model(payload["state"], config["hidden"], config["depth"], config["dropout"], "signed")
    return model, payload["mean"], payload["std"], config


def keep(event: Event, kind: str) -> Event:
    if kind == "all":
        edges = event.edges
    elif kind == "positive":
        edges = [edge for edge in event.edges if edge.kind == "struct" and edge.sign > 0]
    elif kind == "competitor":
        edges = [edge for edge in event.edges if edge.kind == "struct" and edge.sign < 0]
    elif kind == "comention":
        edges = [edge for edge in event.edges if edge.kind == "co"]
    else:
        raise ValueError(kind)
    return clone(event, list(edges))


def mean_mae(model, events, mean, std) -> float | None:
    by_event = event_maes(model, events, mean, std)
    if not by_event:
        return None
    return sum(by_event.values()) / len(by_event)


def fmt(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def source_block(source: str, rows: list[dict], phase5: dict) -> list[str]:
    events = [row["event"] for row in rows]
    _train, _val, test, _info = day_folds(events)
    config = phase5["chosen"]["signed"]
    lines = [f"## {source}", "", f"Chosen on validation MAE: hidden {config['hidden']}, depth {config['depth']}, dropout {config['dropout']}.", ""]
    channel_rows = []
    for kind in ("positive", "competitor", "comention", "all"):
        maes = []
        for seed in SEEDS:
            model, mean, std, _config = saved_model(source, seed)
            edited = [keep(event, kind) for event in test]
            maes.append(mean_mae(model, edited, mean, std))
        channel_rows.append((kind, sum(maes) / len(maes), sample_sd(maes)))
    lines += ["| Channel | Test MAE | SD |", "|---|---:|---:|"]
    for kind, mae, sd in channel_rows:
        lines.append(f"| {kind} | {fmt(mae)} | {fmt(sd)} |")
    lines.append("")
    depth_rows = []
    for depth in (1, 2):
        maes = []
        if depth == config["depth"]:
            for seed in SEEDS:
                model, mean, std, _config = saved_model(source, seed)
                maes.append(mean_mae(model, test, mean, std))
        else:
            train, val, held, _info = day_folds(events)
            for seed in SEEDS:
                print(f"{source} depth {depth} seed {seed}", flush=True)
                state, mean, std, _val, _ran = fit_state(train, val, "signed", config["hidden"], depth, config["dropout"], seed)
                model = load_model(state, config["hidden"], depth, config["dropout"], "signed")
                maes.append(mean_mae(model, held, mean, std))
        depth_rows.append((depth, sum(maes) / len(maes), sample_sd(maes)))
    lines += ["| Depth | Test MAE | SD |", "|---|---:|---:|"]
    for depth, mae, sd in depth_rows:
        lines.append(f"| {depth} | {fmt(mae)} | {fmt(sd)} |")
    lines.append("")
    model, mean, std, _config = saved_model(source, 0)
    parts = channel_contribution(model, test, mean, std)
    lines += ["| Edge class | Mean absolute contribution |", "|---|---:|"]
    for name in ("positive", "negative", "comention"):
        lines.append(f"| {name} | {fmt(parts[name])} |")
    lines.append("")
    example = next(event for event in test if event.labels)
    names = next(row["names"] for row in rows if row["event"].event_id == example.event_id)
    scores = []
    for index, name in enumerate(names):
        if name == names[0] and index == names.index(next(row["ecosystem"] for row in rows if row["event"].event_id == example.event_id)):
            pass
        changes = neighbor_attribution(model, example, mean, std, index)
        if not changes:
            continue
        score = sum(abs(value) for value in changes.values()) / len(changes)
        scores.append((score, name))
    scores.sort(reverse=True)
    lines += [f"Example event {example.event_id}.", "", "| Rank | Neighbor | Mean absolute attribution |", "|---:|---|---:|"]
    for rank, (score, name) in enumerate(scores[:5], start=1):
        lines.append(f"| {rank} | {name} | {fmt(score)} |")
    lines.append("")
    stability = []
    for seed in range(10):
        if seed < 5:
            model, mean, std, _config = saved_model(source, seed)
            stability.append(mean_mae(model, test, mean, std))
        else:
            print(f"{source} stability seed {seed}", flush=True)
            train, val, held, _info = day_folds(events)
            state, mean, std, _val, _ran = fit_state(train, val, "signed", config["hidden"], config["depth"], config["dropout"], seed)
            model = load_model(state, config["hidden"], config["depth"], config["dropout"], "signed")
            stability.append(mean_mae(model, held, mean, std))
    lines += ["| Seeds | Test MAE mean | SD |", "|---|---:|---:|", f"| 0-9 | {fmt(sum(stability) / len(stability))} | {fmt(sample_sd(stability))} |", ""]
    lines += ["| Comparison | Test MAE | Gap to no-graph | 95% interval | p | Relative MAE gain |", "|---|---:|---:|---|---:|---:|"]
    for name in ("sign_shuffled", "degree_matched"):
        row = phase5["models"][name]
        interval = "" if row["interval"] is None else f"[{row['interval'][0]:.6g}, {row['interval'][1]:.6g}]"
        lines.append(f"| {name} | {fmt(row['test_mae'])} | {fmt(row['gap_to_no_graph'])} | {interval} | {fmt(row['permutation_p'])} | {fmt(row['relative_mae_gain'])} |")
    lines.append("")
    return lines


def main() -> None:
    saved = torch.load(EVENTS, weights_only=False)
    lines = ["# Phase 6 evaluation", "", "Tables only. The model was chosen by validation MAE before these test numbers were read.", ""]
    for source in SOURCES:
        phase5 = json.loads((ROOT / "eval" / "results" / f"phase5_source_{source}.json").read_text())
        lines.extend(source_block(source, saved[source], phase5))
    OUT.write_text("\n".join(lines) + "\n")
    print(OUT, date.today().isoformat(), flush=True)


if __name__ == "__main__":
    main()

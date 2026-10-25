"""Planted sign-specificity check. Demonstration only. Not a Phase 5 fit.

Choices fixed before the run: hidden 32, depth 1, dropout 0, at most 6 epochs,
patience 3, seeds 0-9, 40 events, 2 positive neighbors and 6 competitor
neighbors. Condition opposite plants a negative competitor shift. Condition
same plants a positive competitor shift on those same negative edges. The
Phase 5 grid is not used.
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from phase5_model import Edge, Event, SignedMP, train_loop, evaluate  # noqa: E402

from guard import demo_file  # noqa: E402

SD = 0.28373788888841645
SEEDS = tuple(range(10))


def events(seed: int, opposite: bool) -> list[Event]:
    rng = random.Random(f"sign:{seed}:{opposite}")
    torch.manual_seed(seed)
    rows = []
    for index in range(40):
        shock = 1.0 if rng.random() < 0.5 else -1.0
        features = torch.zeros(9, 33)
        features[0, 31] = shock
        features[0, 32] = 1.0
        edges = []
        labels = {}
        for node, sign in ((1, 1.0), (2, 1.0), (3, -1.0), (4, -1.0), (5, -1.0), (6, -1.0), (7, -1.0), (8, -1.0)):
            edges.append(Edge(0, node, "struct", sign, 1.0))
            plant_sign = sign if opposite or sign > 0 else 1.0
            labels[node] = plant_sign * shock * SD + rng.gauss(0.0, SD)
        rows.append(Event(f"e{index}", index, features, edges, labels, [], list(range(max(0, index - 28), index)), {f"f{index}"}, {f"l{index}"}))
    return rows


def mae_for(seed: int, opposite: bool, variant: str) -> float:
    rows = events(seed, opposite)
    train, val, test = rows[:24], rows[24:32], rows[32:]
    model = SignedMP(33, 32, 1, 0.0, variant)
    train_loop(model, train, val, epochs=6, patience=3, seed=seed)
    from phase5_model import _scale_stats

    mean, std = _scale_stats(train)
    return evaluate(model, test, mean, std)["mae"]


def main() -> None:
    report = {"label": "AUGMENTED CONTAINS SYNTHETIC DATA", "conditions": {}}
    for name, opposite in (("opposite_sign_competitor", True), ("same_sign_competitor", False)):
        signed, unsigned = [], []
        for seed in SEEDS:
            signed.append(mae_for(seed, opposite, "signed"))
            unsigned.append(mae_for(seed, opposite, "unsigned"))
            print(name, seed, signed[-1], unsigned[-1], flush=True)
        report["conditions"][name] = {
            "signed_mae_mean": sum(signed) / len(signed),
            "unsigned_mae_mean": sum(unsigned) / len(unsigned),
            "competitor_neighbors": 6,
            "positive_neighbors": 2,
        }
    path = demo_file("synthetic/SIGN_SPECIFICITY.json")
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(path, flush=True)


if __name__ == "__main__":
    main()

"""Wave 1 predict-zero (persistence) baseline on the stored Phase 5 test folds.

Reads eval/results/phase5_events.pt and the stored signed weights. Writes only
eval/results/wave1_persistence.json. Changes no Wave 1 number. The row it adds
to Table IV is a new baseline, computed on the exact same test events, so it is
reported as an added descriptive row, not as a test in the Holm family.

    PYTHONPATH=scripts python3 scripts/wave1_persistence_baseline.py
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import phase4_analysis as A  # noqa: E402
import phase5_train as P  # noqa: E402
from phase5_model import _event_errors, apply_scaler  # noqa: E402

OUT = ROOT / "eval" / "results" / "wave1_persistence.json"


def main() -> None:
    saved = P.restore_events()
    out = {}
    for source, _arm, _co in P.SOURCES:
        rows = saved[source]
        events = [r["event"] for r in rows]
        _train, _val, test, info = P.day_folds(events)
        zero = {}
        for event in test:
            if event.labels:
                zero[event.event_id] = _event_errors(torch.zeros(event.features.shape[0]), event.labels)[0]
        signed_maps = []
        for seed in P.SEEDS:
            path = P.MODELS / f"{source}_seed{seed}.pt"
            if not path.exists():
                continue
            stored = torch.load(path, weights_only=False)
            cfg = stored["config"]
            model = P.load_model(stored["state"], cfg["hidden"], cfg["depth"], cfg["dropout"], "signed")
            signed_maps.append(P.event_maes(model, test, stored["mean"], stored["std"]))
        signed = P.mean_map(signed_maps) if signed_maps else {}
        meta = {r["event"].event_id: (r["ecosystem"], date.fromordinal(r["event"].t0).isocalendar()[:2]) for r in rows}
        block = {"split": info, "test_events": len(zero), "persistence_mae": sum(zero.values()) / len(zero)}
        if signed:
            block["signed_mae"] = sum(signed.values()) / len(signed)
            block["signed_vs_persistence"] = P.compare(signed, zero, meta)
        out[source] = block
        print(source, json.dumps({k: v for k, v in block.items() if k != "split"}, default=str), flush=True)
    OUT.write_text(json.dumps(out, default=str, indent=1) + "\n")


if __name__ == "__main__":
    main()

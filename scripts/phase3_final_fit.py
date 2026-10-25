"""Final fit of the RoBERTa scorer on all gold items.

Training loss only. This is not an accuracy estimate. Event detection
does not run.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from phase3_adapt import gold_items  # noqa: E402
from phase3_enlarged import read_csv  # noqa: E402
from phase3_gate import CKPT, SEED, examples, training_docs  # noqa: E402
from phase3_roberta import fit_fold, load_fresh  # noqa: E402

SAMPLE = ROOT / "data" / "handlabel" / "sample.csv"
SAMPLE2 = ROOT / "data" / "handlabel" / "sample2.csv"
DEST = ROOT / "data" / "interim" / "phase3" / "final_scorer"
SERIES = ROOT / "configs" / "phase4_series.json"
FORWARD = 2


def main() -> None:
    device = torch.device("cpu")
    torch.set_num_threads(4)
    torch.manual_seed(SEED)
    items = gold_items(read_csv(SAMPLE)) + gold_items(read_csv(SAMPLE2))
    if len(items) != 713:
        raise SystemExit(f"gold set has {len(items)} items, expected 713")
    if any(item["label"] == "not_about_brand" for item in items):
        raise SystemExit("not_about_brand is still in the gold set")
    print(f"gold {len(items)}", flush=True)
    splits, _skipped = training_docs()
    replay = examples(splits["train"])
    state = torch.load(CKPT / "roberta_pretrain.pt", map_location="cpu", weights_only=True)
    model, _tokenizer = load_fresh(device, state)
    fit_fold(model, _tokenizer, device, items, replay, 5, FORWARD)
    DEST.mkdir(parents=True, exist_ok=True)
    weight_path = DEST / "model.pt"
    torch.save(model.state_dict(), weight_path)
    digest = hashlib.sha256(weight_path.read_bytes()).hexdigest()
    (DEST / "checkpoint.json").write_text(
        json.dumps(
            {
                "base": "roberta-base",
                "weights": "model.pt",
                "sha256": digest,
                "gold_n": 713,
                "not_about_brand": "dropped",
                "epochs": 4,
                "use_last_epoch": True,
                "learning_rate": 2e-5,
                "replay_examples_per_epoch": 2000,
                "optimizer_step_examples": 16,
                "forward_batch": 2,
                "replay_seed": "20261021 + 60 + epoch",
                "started_from": "data/interim/phase3/entity_classifier/roberta_pretrain.pt",
                "training_metric": "mean training loss per epoch, not an accuracy claim",
            },
            indent=2,
        )
    )
    series = json.loads(SERIES.read_text())
    series["main_series"]["full_data_fit_saved"] = True
    series["main_series"]["final_weights"] = "data/interim/phase3/final_scorer/model.pt"
    series["main_series"]["sha256"] = digest
    series["main_series"]["fit_note"] = "Training loss only. The 0.70 gate remains unmet. This fit is not an accuracy claim."
    SERIES.write_text(json.dumps(series, indent=2) + "\n")
    print(f"sha256 {digest}", flush=True)


if __name__ == "__main__":
    main()

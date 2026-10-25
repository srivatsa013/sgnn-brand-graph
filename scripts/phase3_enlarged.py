"""Enlarged five-fold adaptation from the RoBERTa pretrain checkpoint.

The recipe is the one fixed on 2026-10-21. Forward batch is 2.
Event detection does not run.
"""

from __future__ import annotations

import csv
import gc
import json
import sys
import time
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from phase3_adapt import (  # noqa: E402
    fold_table,
    gold_items,
    near_duplicate_folds,
    two_class_stocktwits,
)
from phase3_gate import (  # noqa: E402
    CKPT,
    SEED,
    bootstrap,
    confusion,
    examples,
    macro_f1,
    training_docs,
)
from phase3_roberta import fit_fold, load_fresh, predict  # noqa: E402

OUT = ROOT / "eval" / "results" / "phase3_enlarged.json"
SAMPLE = ROOT / "data" / "handlabel" / "sample.csv"
SAMPLE2 = ROOT / "data" / "handlabel" / "sample2.csv"
GATE = 0.70
FORWARD = 2


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def log(text: str) -> None:
    print(text, flush=True)


def main() -> None:
    device = torch.device("cpu")
    torch.set_num_threads(4)
    torch.manual_seed(SEED)
    first = gold_items(read_csv(SAMPLE))
    second = gold_items(read_csv(SAMPLE2))
    if len(first) != 432:
        raise SystemExit(f"existing gold has {len(first)} items, expected 432")
    items = first + second
    log(f"gold {len(items)} existing 432 new {len(second)}")
    fold_of = near_duplicate_folds(items)
    for fold in range(5):
        test_ids = {items[i]["item_id"] for i, assigned in enumerate(fold_of) if assigned == fold}
        train_ids = {items[i]["item_id"] for i, assigned in enumerate(fold_of) if assigned != fold}
        if test_ids & train_ids:
            raise SystemExit(f"fold {fold} overlaps")
    splits, _skipped = training_docs()
    replay = examples(splits["train"])
    state = torch.load(CKPT / "roberta_pretrain.pt", map_location="cpu", weights_only=True)
    preds = [""] * len(items)
    per_fold = []
    started = time.time()
    forward = FORWARD
    for fold in range(5):
        torch.manual_seed(SEED + fold)
        model, tokenizer = load_fresh(device, state)
        hand = [items[i] for i, assigned in enumerate(fold_of) if assigned != fold]
        forward = fit_fold(model, tokenizer, device, hand, replay, fold, forward)
        held_index = [i for i, assigned in enumerate(fold_of) if assigned == fold]
        held_pred = predict(
            model,
            tokenizer,
            device,
            [(items[i]["node"], items[i]["text"]) for i in held_index],
            forward,
        )
        for i, pred in zip(held_index, held_pred):
            preds[i] = pred
        score = macro_f1([items[i]["label"] for i in held_index], held_pred)
        per_fold.append({"fold": fold, "n": len(held_index), "macro_f1": score})
        log(f"fold {fold} macro_f1 {score:.4f} n {len(held_index)}")
        del model
        gc.collect()
    labels = [item["label"] for item in items]
    pooled = bootstrap(labels, preds, "enlarged_oof")
    by_source = {}
    for source in ("huffpost", "fnspid", "stocktwits"):
        idx = [i for i, item in enumerate(items) if item["source"] == source]
        by_source[source] = bootstrap(
            [labels[i] for i in idx],
            [preds[i] for i in idx],
            f"enlarged_oof:{source}",
        )
    passed = pooled["macro_f1"] >= GATE
    raw_rows = read_csv(SAMPLE) + read_csv(SAMPLE2)
    log("stocktwits user labels")
    user = two_class_stocktwits(raw_rows, items)
    payload = {
        "plan": "DECISIONS_LOG 2026-10-21 enlarged attempt",
        "checkpoint": str(CKPT / "roberta_pretrain.pt"),
        "gold_n": len(items),
        "existing_gold_n": 432,
        "new_gold_n": len(second),
        "folds": fold_table(items, fold_of),
        "oof": {
            "overall": pooled,
            "by_source": by_source,
            "per_fold": per_fold,
            "confusion": confusion(labels, preds),
            "seconds": time.time() - started,
            "forward_batch": forward,
            "gate": GATE,
            "pass": passed,
        },
        "fnspid_only_macro_f1": by_source["fnspid"]["macro_f1"],
        "stocktwits_text_macro_f1": by_source["stocktwits"]["macro_f1"],
        "huffpost_macro_f1": by_source["huffpost"]["macro_f1"],
        "stocktwits_user_label_two_class": user,
    }
    if passed:
        model, tokenizer = load_fresh(device, state)
        fit_fold(model, tokenizer, device, items, replay, 5, forward)
        torch.save(model.state_dict(), CKPT / "roberta_enlarged_all.pt")
        payload["final_fit"] = "saved roberta_enlarged_all.pt; the gate number remains the out-of-fold estimate"
        log("final fit saved")
    OUT.write_text(json.dumps(payload, indent=2))
    log(f"oof {pooled['macro_f1']:.4f} pass {passed}")


if __name__ == "__main__":
    main()

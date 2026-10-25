"""Stage 2. RoBERTa-base pretraining, then the fixed five-fold recipe.

Fold weights are not saved. The pretrain checkpoint is kept. Event
detection does not run.
"""

from __future__ import annotations

import gc
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from phase3_adapt import (  # noqa: E402
    FORWARD,
    GROUP,
    RSS_LIMIT,
    epoch_rows,
    fold_table,
    gold_items,
    near_duplicate_folds,
    predict,
    rss_bytes,
)
from phase3_gate import (  # noqa: E402
    CKPT,
    LABELS,
    MAX_LEN,
    SEED,
    bootstrap,
    confusion,
    examples,
    load_rows,
    macro_f1,
    training_docs,
)

BASE = "roberta-base"
PRETRAIN_EPOCHS = 3
PRETRAIN_BATCH = 4
LR = 2e-5
OUT = ROOT / "eval" / "results" / "phase3_roberta.json"
ADAPT = ROOT / "eval" / "results" / "phase3_adapt.json"
GATE = 0.70


def log(text: str) -> None:
    print(text, flush=True)


def load_fresh(device, state: dict | None = None):
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    label2id = {label: i for i, label in enumerate(LABELS)}
    id2label = {i: label for label, i in label2id.items()}
    tokenizer = AutoTokenizer.from_pretrained(BASE)
    model = AutoModelForSequenceClassification.from_pretrained(
        BASE,
        num_labels=3,
        id2label=id2label,
        label2id=label2id,
        ignore_mismatched_sizes=True,
    )
    if state is not None:
        model.load_state_dict(state)
    model.to(device)
    return model, tokenizer


def run_pretrain(device, splits: dict) -> tuple[dict, dict, float]:
    import torch
    from torch.optim import AdamW

    batch = PRETRAIN_BATCH
    model, tokenizer = load_fresh(device)
    optimizer = AdamW(model.parameters(), lr=LR)
    train_rows = examples(splits["train"])
    val_rows = examples(splits["validation"])
    test_rows = examples(splits["test"])
    label2id = {label: i for i, label in enumerate(LABELS)}
    best_state = None
    best_val = -1.0
    history = []
    for epoch in range(1, PRETRAIN_EPOCHS + 1):
        if rss_bytes() > RSS_LIMIT:
            batch = 2
        order = list(range(len(train_rows)))
        torch.manual_seed(SEED + epoch)
        import random

        random.Random(SEED + epoch).shuffle(order)
        model.train()
        total = 0.0
        seen = 0
        step = 0
        for start in range(0, len(order), batch):
            pick = [train_rows[i] for i in order[start : start + batch]]
            encoded = tokenizer(
                [row[0] for row in pick],
                [row[1] for row in pick],
                padding=True,
                truncation=True,
                max_length=MAX_LEN,
                return_tensors="pt",
            )
            encoded = {key: value.to(device) for key, value in encoded.items()}
            labels = torch.tensor([label2id[row[2]] for row in pick], device=device)
            optimizer.zero_grad()
            loss = model(**encoded, labels=labels).loss
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            total += float(loss.item()) * len(pick)
            seen += len(pick)
            step += 1
            if step % 100 == 0:
                log(f"pretrain epoch {epoch} step {step} loss {total / seen:.4f} rss {rss_bytes()} batch {batch}")
        val_pred = predict(model, tokenizer, device, [(row[0], row[1]) for row in val_rows], batch)
        val_f1 = macro_f1([row[2] for row in val_rows], val_pred)
        history.append({"epoch": epoch, "train_loss": total / max(seen, 1), "validation_macro_f1": val_f1})
        log(f"pretrain epoch {epoch} val_macro_f1 {val_f1:.4f} rss {rss_bytes()} batch {batch}")
        if val_f1 > best_val:
            best_val = val_f1
            best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
    CKPT.mkdir(parents=True, exist_ok=True)
    torch.save(best_state, CKPT / "roberta_pretrain.pt")
    model.load_state_dict(best_state)
    model.to(device)
    test_pred = predict(model, tokenizer, device, [(row[0], row[1]) for row in test_rows], batch)
    test_f1 = macro_f1([row[2] for row in test_rows], test_pred)
    log(f"test_split_macro_f1 {test_f1:.4f}")
    report = {
        "base": BASE,
        "epochs": history,
        "selected_validation_macro_f1": best_val,
        "pretrain_batch": batch,
        "test_split": {
            "documents": {name: len(docs) for name, docs in splits.items()},
            "examples": {"train": len(train_rows), "validation": len(val_rows), "test": len(test_rows)},
            "macro_f1": test_f1,
            "confusion": confusion([row[2] for row in test_rows], test_pred),
        },
    }
    del model
    del optimizer
    gc.collect()
    return best_state, report, test_f1


def fit_fold(model, tokenizer, device, hand, replay, fold: int, forward: int) -> int:
    import torch
    from torch.optim import AdamW

    label2id = {label: i for i, label in enumerate(LABELS)}
    optimizer = AdamW(model.parameters(), lr=LR)
    for epoch in range(1, 5):
        if rss_bytes() > RSS_LIMIT:
            forward = 2
        rows = epoch_rows(hand, replay, fold, epoch)
        model.train()
        total = 0.0
        seen = 0
        step = 0
        for start in range(0, len(rows), GROUP):
            group = rows[start : start + GROUP]
            optimizer.zero_grad()
            for micro_at in range(0, len(group), forward):
                pick = group[micro_at : micro_at + forward]
                encoded = tokenizer(
                    [row[0] for row in pick],
                    [row[1] for row in pick],
                    padding=True,
                    truncation=True,
                    max_length=MAX_LEN,
                    return_tensors="pt",
                )
                encoded = {key: value.to(device) for key, value in encoded.items()}
                labels = torch.tensor([label2id[row[2]] for row in pick], device=device)
                raw = model(**encoded, labels=labels).loss
                (raw * (len(pick) / len(group))).backward()
                total += float(raw.item()) * len(pick)
                seen += len(pick)
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            step += 1
            if step % 50 == 0:
                log(f"fold {fold} epoch {epoch} step {step} loss {total / max(seen, 1):.4f} rss {rss_bytes()}")
        log(f"fold {fold} epoch {epoch} done loss {total / max(seen, 1):.4f} rss {rss_bytes()} forward {forward}")
    del optimizer
    gc.collect()
    return forward


def main() -> None:
    import torch

    device = torch.device("cpu")
    torch.set_num_threads(4)
    torch.manual_seed(SEED)
    splits, skipped = training_docs()
    started = time.time()
    state, pretrain, test_f1 = run_pretrain(device, splits)
    payload = {
        "plan": "DECISIONS_LOG 2026-10-21 Stage 2",
        "training_documents_skipped_annotations": skipped,
        "pretrain": pretrain,
        "test_split_macro_f1": test_f1,
    }
    OUT.write_text(json.dumps(payload, indent=2))
    items = gold_items(load_rows())
    if len(items) != 432:
        raise SystemExit(f"gold set has {len(items)} items, expected 432")
    fold_of = near_duplicate_folds(items)
    replay = examples(splits["train"])
    preds = [""] * len(items)
    per_fold = []
    forward = 2 if rss_bytes() > RSS_LIMIT else FORWARD
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
        held_gold = [items[i]["label"] for i in held_index]
        for i, pred in zip(held_index, held_pred):
            preds[i] = pred
        score = macro_f1(held_gold, held_pred)
        per_fold.append({"fold": fold, "n": len(held_gold), "macro_f1": score})
        log(f"fold {fold} macro_f1 {score:.4f} n {len(held_gold)}")
        del model
        gc.collect()
    gold_labels = [item["label"] for item in items]
    pooled = bootstrap(gold_labels, preds, "roberta_oof")
    by_source = {}
    for source in ("huffpost", "fnspid", "stocktwits"):
        idx = [i for i, item in enumerate(items) if item["source"] == source]
        by_source[source] = bootstrap(
            [gold_labels[i] for i in idx],
            [preds[i] for i in idx],
            f"roberta_oof:{source}",
        )
    prior = json.loads(ADAPT.read_text())
    payload["folds"] = fold_table(items, fold_of)
    payload["oof"] = {
        "overall": pooled,
        "by_source": by_source,
        "per_fold": per_fold,
        "confusion": confusion(gold_labels, preds),
        "seconds": time.time() - started,
        "forward_batch": forward,
        "gate": GATE,
        "pass": pooled["macro_f1"] >= GATE,
    }
    payload["fnspid_only_macro_f1"] = by_source["fnspid"]["macro_f1"]
    payload["huffpost_macro_f1"] = by_source["huffpost"]["macro_f1"]
    payload["stocktwits_user_label_two_class"] = prior["stocktwits_two_class"]
    payload["note"] = "Fold weights were not saved. The gate number is the pooled out-of-fold macro-F1."
    OUT.write_text(json.dumps(payload, indent=2))
    log(f"oof {pooled['macro_f1']:.4f} pass {payload['oof']['pass']}")


if __name__ == "__main__":
    main()

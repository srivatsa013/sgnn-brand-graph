"""Five-fold adaptation of the epoch-3 entity classifier.

The recipe is fixed in DECISIONS_LOG.md on 2026-10-21. The held-out fold
is not used to choose an epoch. Event detection does not run.
"""

from __future__ import annotations

import gc
import json
import random
import re
import resource
import sqlite3
import sys
import time
from collections import Counter
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from phase3_gate import (  # noqa: E402
    BASE,
    BOOT,
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

OUT = ROOT / "eval" / "results" / "phase3_adapt.json"
STATUS = ROOT / "eval" / "results" / "phase3_adapt.status"
SERIES = ROOT / "data" / "interim" / "phase2" / "series.sqlite"
BRANDS = ("Apple", "Microsoft", "Alphabet", "Tesla")
FOLDS = 5
EPOCHS = 4
LR = 2e-5
GROUP = 16
FORWARD = 4
RSS_LIMIT = int(2.5 * 1024**3)
REPLAY_N = 2000
GATE = 0.70
WORD = re.compile(r"[a-z0-9]+")


def log(text: str) -> None:
    print(text, flush=True)
    with STATUS.open("a") as handle:
        handle.write(text + "\n")


def gold_items(rows: list[dict]) -> list[dict]:
    gold = []
    for row in rows:
        a = row["label_A"].strip()
        b = row["label_B"].strip()
        if a and b:
            if a != b:
                continue
            label = a
        elif a:
            label = a
        else:
            continue
        if label == "not_about_brand":
            continue
        gold.append(
            {
                "item_id": row["item_id"],
                "source": row["source"],
                "node": row["node"],
                "text": row["text"],
                "label": label,
            }
        )
    return gold


def normalize(text: str) -> str:
    return " ".join(WORD.findall(text.casefold()))


class UnionFind:
    def __init__(self, n: int) -> None:
        self.parent = list(range(n))

    def find(self, i: int) -> int:
        while self.parent[i] != i:
            self.parent[i] = self.parent[self.parent[i]]
            i = self.parent[i]
        return i

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra


def near_duplicate_folds(items: list[dict]) -> list[int]:
    norms = [normalize(item["text"]) for item in items]
    tokens = [set(text.split()) for text in norms]
    groups = UnionFind(len(items))
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            left, right = norms[i], norms[j]
            if left == right:
                groups.union(i, j)
                continue
            shorter, longer = (left, right) if len(left) <= len(right) else (right, left)
            if len(shorter) >= 40 and shorter in longer:
                groups.union(i, j)
                continue
            a, b = tokens[i], tokens[j]
            if len(a) >= 8 and len(b) >= 8:
                overlap = len(a & b)
                union = len(a | b)
                if union and overlap / union >= 0.8:
                    groups.union(i, j)
    clusters: dict[int, list[int]] = {}
    for i in range(len(items)):
        clusters.setdefault(groups.find(i), []).append(i)
    by_stratum: dict[str, list[list[int]]] = {}
    for members in clusters.values():
        sources = {items[i]["source"] for i in members}
        labels = {items[i]["label"] for i in members}
        if len(sources) == 1 and len(labels) == 1:
            key = f"{next(iter(sources))}|{next(iter(labels))}"
        else:
            key = "mixed"
        members.sort(key=lambda i: items[i]["item_id"])
        by_stratum.setdefault(key, []).append(members)
    fold_of = [-1] * len(items)
    counts = [0] * FOLDS
    for key in sorted(by_stratum):
        groups_here = by_stratum[key]
        groups_here.sort(key=lambda members: items[members[0]]["item_id"])
        random.Random(SEED).shuffle(groups_here)
        for members in groups_here:
            fold = min(range(FOLDS), key=lambda k: (counts[k], k))
            for i in members:
                fold_of[i] = fold
            counts[fold] += len(members)
    if any(fold < 0 for fold in fold_of):
        raise SystemExit("an item was left without a fold")
    return fold_of


def rss_bytes() -> int:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss


def load_start(device):
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
    state = torch.load(CKPT / "best.pt", map_location="cpu", weights_only=True)
    model.load_state_dict(state)
    model.to(device)
    return model, tokenizer


def predict(model, tokenizer, device, pairs: list[tuple[str, str]], batch: int) -> list[str]:
    import torch

    model.eval()
    preds = []
    id2label = {int(k): v.lower() for k, v in model.config.id2label.items()}
    with torch.no_grad():
        for start in range(0, len(pairs), batch):
            chunk = pairs[start : start + batch]
            encoded = tokenizer(
                [entity for entity, _ in chunk],
                [text for _, text in chunk],
                padding=True,
                truncation=True,
                max_length=MAX_LEN,
                return_tensors="pt",
            )
            encoded = {key: value.to(device) for key, value in encoded.items()}
            choice = model(**encoded).logits.argmax(dim=1).tolist()
            preds.extend(id2label[i] for i in choice)
    return preds


def epoch_rows(
    hand: list[dict], replay: list[tuple[str, str, str]], fold: int, epoch: int
) -> list[tuple[str, str, str]]:
    rng = random.Random(SEED + 10 * (fold + 1) + epoch)
    drawn = replay if len(replay) <= REPLAY_N else rng.sample(replay, REPLAY_N)
    rows = [(item["node"], item["text"], item["label"]) for item in hand]
    rows.extend(drawn)
    rng.shuffle(rows)
    return rows


def two_class_stocktwits(rows: list[dict], gold: list[dict]) -> dict:
    wanted = {" ".join(row["text"].split()): row for row in rows if row["source"] == "stocktwits"}
    ids_for_text: dict[str, list[int]] = {text: [] for text in wanted}
    for path in sorted((ROOT / "data" / "raw" / "stocktwits" / "bodies").glob("*.parquet")):
        table = pq.read_table(path, columns=["message_id", "message_body"])
        for message_id, body in zip(table.column("message_id").to_pylist(), table.column("message_body").to_pylist()):
            key = " ".join((body or "").split())
            if key in ids_for_text:
                ids_for_text[key].append(message_id)
    needed = {message_id for ids in ids_for_text.values() for message_id in ids}
    sentiment: dict[int, str] = {}
    for path in sorted((ROOT / "data" / "raw" / "stocktwits" / "features").glob("*.parquet")):
        table = pq.read_table(path, columns=["message_id", "sentiment"])
        for message_id, raw in zip(table.column("message_id").to_pylist(), table.column("sentiment").to_pylist()):
            if message_id in needed:
                sentiment[message_id] = (raw or "").strip()
    gold_by_id = {item["item_id"]: item for item in gold}
    user_map = {"bullish": "positive", "bearish": "negative"}
    hand_labels = []
    user_labels = []
    eligible = 0
    no_user_label = 0
    conflicting = 0
    for text, row in wanted.items():
        item = gold_by_id.get(row["item_id"])
        if item is None or item["label"] not in {"positive", "negative"}:
            continue
        eligible += 1
        labels = []
        for message_id in ids_for_text.get(text) or []:
            raw = sentiment.get(message_id, "").lower()
            if raw in user_map:
                labels.append(user_map[raw])
        labels = sorted(set(labels))
        if not labels:
            no_user_label += 1
            continue
        if len(labels) != 1:
            conflicting += 1
            continue
        hand_labels.append(item["label"])
        user_labels.append(labels[0])
    n = len(hand_labels)
    agree = sum(a == b for a, b in zip(hand_labels, user_labels))
    pair_labels = ("positive", "negative")
    table = {label: {other: 0 for other in pair_labels} for label in pair_labels}
    for hand, user in zip(hand_labels, user_labels):
        table[hand][user] += 1
    return {
        "subset": "hand label positive or negative, and one user label",
        "hand_positive_or_negative": eligible,
        "no_user_label": no_user_label,
        "conflicting_user_label": conflicting,
        "n": n,
        "agreement": (agree / n) if n else None,
        "macro_f1": macro_f1(hand_labels, user_labels, pair_labels) if n else None,
        "confusion_gold_rows_user_columns": table,
    }


def series_user_labels() -> dict:
    con = sqlite3.connect(f"file:{SERIES}?mode=ro", uri=True)
    marks = ",".join("?" for _ in BRANDS)
    rows = con.execute(
        f"""
        SELECT node,
               SUM(mentions > 0),
               SUM(scored > 0),
               SUM(mentions),
               SUM(scored),
               SUM(scored >= 5)
        FROM cell
        WHERE source = 'social' AND exclude_brand = '' AND node IN ({marks})
        GROUP BY node
        ORDER BY node
        """,
        BRANDS,
    ).fetchall()
    con.close()
    by_node = {}
    mention_days = labeled_days = messages = labeled_messages = event_days = 0
    for node, days, user_days, n_msg, n_lab, n_event in rows:
        by_node[node] = {
            "mention_days": days,
            "days_with_a_user_label": user_days,
            "share_of_mention_days": (user_days / days) if days else None,
            "messages": n_msg,
            "user_labeled_messages": n_lab,
            "share_of_messages": (n_lab / n_msg) if n_msg else None,
            "days_with_at_least_5_user_labels": n_event,
        }
        mention_days += days
        labeled_days += user_days
        messages += n_msg
        labeled_messages += n_lab
        event_days += n_event
    return {
        "score": "user label: bullish is +1 and bearish is -1. A message with no user label adds a mention and does not enter the daily mean. No text scorer is applied.",
        "brands": by_node,
        "mention_days": mention_days,
        "days_with_a_user_label": labeled_days,
        "share_of_mention_days": (labeled_days / mention_days) if mention_days else None,
        "messages": messages,
        "user_labeled_messages": labeled_messages,
        "share_of_messages": (labeled_messages / messages) if messages else None,
        "days_with_at_least_5_user_labels": event_days,
    }


def fold_table(items: list[dict], fold_of: list[int]) -> list[dict]:
    out = []
    for fold in range(FOLDS):
        chosen = [items[i] for i, assigned in enumerate(fold_of) if assigned == fold]
        out.append(
            {
                "fold": fold,
                "n": len(chosen),
                "by_source_and_class": {
                    f"{source}|{label}": count
                    for (source, label), count in sorted(
                        Counter((item["source"], item["label"]) for item in chosen).items()
                    )
                },
            }
        )
    return out


def main() -> None:
    import torch

    STATUS.write_text("")
    items = gold_items(load_rows())
    if len(items) != 432:
        raise SystemExit(f"gold set has {len(items)} items, expected 432")
    fold_of = near_duplicate_folds(items)
    train_mask = []
    for fold in range(FOLDS):
        test_ids = {items[i]["item_id"] for i, assigned in enumerate(fold_of) if assigned == fold}
        train_ids = {items[i]["item_id"] for i, assigned in enumerate(fold_of) if assigned != fold}
        if test_ids & train_ids:
            raise SystemExit(f"fold {fold} overlaps")
        train_mask.append(len(test_ids))
    clusters = len({normalize(item["text"]) for item in items})
    log(f"gold {len(items)} folds {train_mask}")
    payload = {
        "plan": "DECISIONS_LOG 2026-10-21 Phase 3 adaptation plan",
        "checkpoint": str(CKPT / "best.pt"),
        "gold_n": len(items),
        "folds": fold_table(items, fold_of),
        "normalized_text_groups": clusters,
    }
    log("stocktwits two-class")
    payload["stocktwits_two_class"] = two_class_stocktwits(load_rows(), items)
    log("stocktwits series")
    payload["arm_a_stocktwits_series"] = series_user_labels()
    OUT.write_text(json.dumps(payload, indent=2))
    log(json.dumps(payload["stocktwits_two_class"]))
    splits, _skipped = training_docs()
    replay = examples(splits["train"])
    log(f"replay pool {len(replay)}")
    device = torch.device("cpu")
    torch.set_num_threads(4)
    preds = [""] * len(items)
    per_fold = []
    forward = FORWARD
    started = time.time()
    for fold in range(FOLDS):
        torch.manual_seed(SEED + fold)
        model, tokenizer = load_start(device)
        hand = [items[i] for i, assigned in enumerate(fold_of) if assigned != fold]
        forward = fit_fold(model, tokenizer, device, hand, replay, fold, forward)
        held = [(items[i]["node"], items[i]["text"]) for i, assigned in enumerate(fold_of) if assigned == fold]
        held_gold = [items[i]["label"] for i, assigned in enumerate(fold_of) if assigned == fold]
        held_pred = predict(model, tokenizer, device, held, forward)
        cursor = 0
        for i, assigned in enumerate(fold_of):
            if assigned == fold:
                preds[i] = held_pred[cursor]
                cursor += 1
        score = macro_f1(held_gold, held_pred)
        per_fold.append({"fold": fold, "n": len(held_gold), "macro_f1": score})
        log(f"fold {fold} macro_f1 {score:.4f} n {len(held_gold)}")
        del model
        gc.collect()
    gold_labels = [item["label"] for item in items]
    pooled = bootstrap(gold_labels, preds, "adapt_oof")
    by_source = {}
    for source in ("huffpost", "fnspid", "stocktwits"):
        idx = [i for i, item in enumerate(items) if item["source"] == source]
        by_source[source] = bootstrap(
            [gold_labels[i] for i in idx],
            [preds[i] for i in idx],
            f"adapt_oof:{source}",
        )
    passed = pooled["macro_f1"] >= GATE
    payload["oof"] = {
        "overall": pooled,
        "by_source": by_source,
        "per_fold": per_fold,
        "confusion": confusion(gold_labels, preds),
        "seconds": time.time() - started,
        "forward_batch": forward,
        "gate": GATE,
        "pass": passed,
    }
    OUT.write_text(json.dumps(payload, indent=2))
    log(f"oof {pooled['macro_f1']:.4f} pass {passed}")
    if passed:
        model, tokenizer = load_start(device)
        fit_fold(model, tokenizer, device, items, replay, 5, forward)
        torch.save(model.state_dict(), CKPT / "adapted_all.pt")
        payload["final_fit"] = "saved adapted_all.pt; the gate number remains the out-of-fold estimate"
        OUT.write_text(json.dumps(payload, indent=2))
        log("final fit saved")


def fit_fold(model, tokenizer, device, hand, replay, fold: int, forward: int) -> int:
    import torch
    from torch.optim import AdamW

    label2id = {label: i for i, label in enumerate(LABELS)}
    optimizer = AdamW(model.parameters(), lr=LR)
    for epoch in range(1, EPOCHS + 1):
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
                log(
                    f"fold {fold} epoch {epoch} step {step} loss {total / max(seen, 1):.4f} rss {rss_bytes()}"
                )
        log(
            f"fold {fold} epoch {epoch} done loss {total / max(seen, 1):.4f} rss {rss_bytes()} forward {forward}"
        )
    del optimizer
    gc.collect()
    return forward


if __name__ == "__main__":
    main()

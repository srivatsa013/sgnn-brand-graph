"""Phase 3 scorer gate. No event detection.

Gold labels are the agreed double-coded rows plus the single-coded rows,
after not_about_brand is dropped. The entity classifier trains only on
SEntFiN and FinEntity. The hand-labeled sheet is an evaluation set.
"""

from __future__ import annotations

import ast
import csv
import json
import os
import random
from collections import Counter
from pathlib import Path

import pyarrow.parquet as pq
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("HF_HOME", str(ROOT / "data" / "interim" / "phase3" / "hf"))
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

SAMPLE = ROOT / "data" / "handlabel" / "sample.csv"
DISAGREE = ROOT / "data" / "handlabel" / "disagreements.csv"
OUT = ROOT / "eval" / "results" / "phase3_gate.json"
CKPT = ROOT / "data" / "interim" / "phase3" / "entity_classifier"
SEED = 20261021
LABELS = ("positive", "negative", "neutral")
VADER_CUT = 0.05
BOOT = 1000
BASE = "distilbert-base-uncased"
FINBERT = "ProsusAI/finbert"
EPOCHS = 3
BATCH = 4
LR = 2e-5
MAX_LEN = 128


def parse_decisions(raw: str) -> dict[str, str]:
    text = raw.strip()
    if text.startswith("{") and text.endswith("}"):
        text = text[1:-1].strip()
    out: dict[str, str] = {}
    i = 0
    while i < len(text):
        while i < len(text) and text[i] in " ,":
            i += 1
        if i >= len(text):
            break
        quote = text[i]
        if quote not in "'\"":
            raise ValueError(raw)
        i += 1
        ent: list[str] = []
        while i < len(text):
            if text[i] == "\\" and i + 1 < len(text):
                ent.append(text[i + 1])
                i += 2
                continue
            if text[i] == quote:
                nxt = text[i + 1] if i + 1 < len(text) else ""
                if quote == "'" and nxt.isalpha():
                    ent.append(text[i])
                    i += 1
                    continue
                i += 1
                break
            ent.append(text[i])
            i += 1
        while i < len(text) and text[i] in " :":
            i += 1
        q2 = text[i]
        i += 1
        lab: list[str] = []
        while i < len(text) and text[i] != q2:
            lab.append(text[i])
            i += 1
        i += 1
        name = "".join(ent).strip()
        label = "".join(lab).strip().lower()
        if name and label in LABELS:
            out[name] = label
    if not out:
        raise ValueError(raw)
    return out


def macro_f1(gold: list[str], pred: list[str], labels: tuple[str, ...] = LABELS) -> float:
    scores = []
    for label in labels:
        tp = sum(g == label and p == label for g, p in zip(gold, pred))
        fp = sum(g != label and p == label for g, p in zip(gold, pred))
        fn = sum(g == label and p != label for g, p in zip(gold, pred))
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        scores.append(0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall))
    return sum(scores) / len(labels)


def confusion(gold: list[str], pred: list[str]) -> dict[str, dict[str, int]]:
    table = {label: {other: 0 for other in LABELS} for label in LABELS}
    for g, p in zip(gold, pred):
        if g in table and p in table[g]:
            table[g][p] += 1
    return table


def bootstrap(gold: list[str], pred: list[str], key: str) -> dict:
    rng = random.Random(f"{SEED}:{key}")
    n = len(gold)
    if n == 0:
        return {"n": 0, "macro_f1": None, "ci95": None}
    point = macro_f1(gold, pred)
    draws = []
    for _ in range(BOOT):
        pick = [rng.randrange(n) for _ in range(n)]
        draws.append(macro_f1([gold[i] for i in pick], [pred[i] for i in pick]))
    draws.sort()
    lo = draws[int(0.025 * (BOOT - 1))]
    hi = draws[int(0.975 * (BOOT - 1))]
    return {
        "n": n,
        "macro_f1": point,
        "ci95": [lo, hi],
        "confusion": confusion(gold, pred),
    }


def kappa(pairs: list[tuple[str, str]]) -> dict:
    n = len(pairs)
    labels = sorted({a for a, _ in pairs} | {b for _, b in pairs})
    po = sum(a == b for a, b in pairs) / n
    count_a = Counter(a for a, _ in pairs)
    count_b = Counter(b for _, b in pairs)
    pe = sum((count_a[label] / n) * (count_b[label] / n) for label in labels)
    value = 1.0 if pe == 1 else (po - pe) / (1 - pe)
    return {
        "n": n,
        "observed_agreement": po,
        "expected_agreement": pe,
        "cohen_kappa": value,
        "labels": labels,
    }


def vader_label(analyzer: SentimentIntensityAnalyzer, text: str) -> str:
    compound = analyzer.polarity_scores(text)["compound"]
    if compound > VADER_CUT:
        return "positive"
    if compound < -VADER_CUT:
        return "negative"
    return "neutral"


def load_rows() -> list[dict]:
    with SAMPLE.open(newline="") as handle:
        return list(csv.DictReader(handle))


def assemble(rows: list[dict]) -> dict:
    pairs = []
    disagreements = []
    gold = []
    dropped = []
    for row in rows:
        a = row["label_A"].strip()
        b = row["label_B"].strip()
        if a and b:
            pairs.append((a, b))
            if a != b:
                disagreements.append(row)
                continue
            label = a
        elif a:
            label = a
        else:
            continue
        item = {
            "item_id": row["item_id"],
            "source": row["source"],
            "node": row["node"],
            "text": row["text"],
            "label": label,
        }
        if label == "not_about_brand":
            dropped.append(item["item_id"])
        else:
            gold.append(item)
    with DISAGREE.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["item_id", "source", "node", "text", "label_A", "label_B", "adjudication"],
        )
        writer.writeheader()
        for row in disagreements:
            writer.writerow(
                {
                    "item_id": row["item_id"],
                    "source": row["source"],
                    "node": row["node"],
                    "text": row["text"],
                    "label_A": row["label_A"].strip(),
                    "label_B": row["label_B"].strip(),
                    "adjudication": "",
                }
            )
    by_source_a = {}
    for source in ("huffpost", "fnspid", "stocktwits"):
        by_source_a[source] = dict(Counter(row["label_A"].strip() for row in rows if row["source"] == source))
    gold_by = {}
    for source in ("huffpost", "fnspid", "stocktwits"):
        gold_by[source] = dict(Counter(item["label"] for item in gold if item["source"] == source))
    nab_a = sum(row["label_A"].strip() == "not_about_brand" for row in rows)
    nab_b = sum(row["label_B"].strip() == "not_about_brand" for row in rows)
    return {
        "kappa": kappa(pairs),
        "disagreement_n": len(disagreements),
        "disagreement_pairs": {
            f"{a}|{b}": n for (a, b), n in Counter((a, b) for a, b in pairs if a != b).items()
        },
        "label_A_by_source": by_source_a,
        "not_about_brand": {
            "label_A": nab_a,
            "label_B": nab_b,
            "dropped_from_gold": len(dropped),
            "dropped_ids": dropped,
        },
        "gold_n": len(gold),
        "gold_by_source_and_class": gold_by,
        "gold": gold,
    }


def training_docs() -> tuple[dict, int]:
    docs = []
    with (ROOT / "data" / "raw" / "sentfin" / "SEntFiN.csv").open(newline="") as handle:
        for row in csv.DictReader(handle):
            decisions = parse_decisions(row["Decisions"])
            docs.append({"text": row["Title"], "ents": list(decisions.items())})
    fin = json.loads((ROOT / "data" / "raw" / "finentity" / "FinEntity.json").read_text())
    skipped = 0
    for doc in fin:
        ents = []
        for ann in doc.get("annotations") or []:
            label = str(ann.get("label") or "").strip().lower()
            name = str(ann.get("value") or "").strip()
            if name and label in LABELS:
                ents.append((name, label))
            else:
                skipped += 1
        if ents:
            docs.append({"text": doc.get("content") or "", "ents": ents})
    rng = random.Random(SEED)
    rng.shuffle(docs)
    n = len(docs)
    n_train = int(0.8 * n)
    n_val = int(0.1 * n)
    splits = {
        "train": docs[:n_train],
        "validation": docs[n_train : n_train + n_val],
        "test": docs[n_train + n_val :],
    }
    return splits, skipped


def examples(docs: list[dict]) -> list[tuple[str, str, str]]:
    rows = []
    for doc in docs:
        for entity, label in doc["ents"]:
            rows.append((entity, doc["text"], label))
    return rows


def score_vader(gold: list[dict]) -> list[str]:
    analyzer = SentimentIntensityAnalyzer()
    return [vader_label(analyzer, item["text"]) for item in gold]


def stocktwits_check(rows: list[dict], gold: list[dict]) -> dict:
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
    gold_ids = {item["item_id"] for item in gold}
    user_map = {"bullish": "positive", "bearish": "negative"}
    compared_gold = []
    compared_user = []
    unlabeled = 0
    conflict = 0
    unmatched = 0
    not_in_gold = 0
    for text, row in wanted.items():
        ids = ids_for_text.get(text) or []
        if not ids:
            unmatched += 1
            continue
        labels = []
        for message_id in ids:
            raw = sentiment.get(message_id, "").lower()
            if raw in user_map:
                labels.append(user_map[raw])
        labels = sorted(set(labels))
        if not labels:
            unlabeled += 1
            continue
        if len(labels) > 1:
            conflict += 1
            continue
        if row["item_id"] not in gold_ids:
            not_in_gold += 1
            continue
        hand = next(item["label"] for item in gold if item["item_id"] == row["item_id"])
        compared_gold.append(hand)
        compared_user.append(labels[0])
    n = len(compared_gold)
    agree = sum(a == b for a, b in zip(compared_gold, compared_user))
    return {
        "sample_stocktwits": len(wanted),
        "unmatched_body": unmatched,
        "no_user_label": unlabeled,
        "conflicting_user_label": conflict,
        "user_label_but_not_in_gold": not_in_gold,
        "compared_n": n,
        "agreement": (agree / n) if n else None,
        "macro_f1": macro_f1(compared_gold, compared_user) if n else None,
        "confusion_gold_rows_user_columns": confusion(compared_gold, compared_user) if n else None,
    }


def predict_pairs(model, tokenizer, device, pairs: list[tuple[str, str]], batch: int = 32) -> list[str]:
    import torch

    model.eval()
    preds = []
    id2label = {int(k): v.lower() for k, v in model.config.id2label.items()}
    with torch.no_grad():
        for start in range(0, len(pairs), batch):
            chunk = pairs[start : start + batch]
            entities = [entity for entity, _ in chunk]
            texts = [text for _, text in chunk]
            encoded = tokenizer(
                entities,
                texts,
                padding=True,
                truncation=True,
                max_length=MAX_LEN,
                return_tensors="pt",
            )
            encoded = {key: value.to(device) for key, value in encoded.items()}
            logits = model(**encoded).logits
            choice = logits.argmax(dim=1).tolist()
            preds.extend(id2label[i] for i in choice)
    return preds


def run_neural(gold: list[dict], splits: dict) -> dict:
    import torch
    from torch.optim import AdamW
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    # This MacBook Air has 8 GB. A batch of 16 on MPS held 5.2 GB and the
    # machine swapped instead of training. CPU and batch 4 fit beside the
    # GDELT rerun.
    device = torch.device("cpu")
    torch.set_num_threads(4)
    torch.manual_seed(SEED)
    label2id = {label: i for i, label in enumerate(LABELS)}
    id2label = {i: label for label, i in label2id.items()}
    tokenizer = AutoTokenizer.from_pretrained(BASE)
    model = AutoModelForSequenceClassification.from_pretrained(
        BASE,
        num_labels=3,
        id2label=id2label,
        label2id=label2id,
        ignore_mismatched_sizes=True,
    ).to(device)
    optimizer = AdamW(model.parameters(), lr=LR)
    train_rows = examples(splits["train"])
    val_rows = examples(splits["validation"])
    test_rows = examples(splits["test"])

    def batches(rows: list[tuple[str, str, str]]):
        order = list(range(len(rows)))
        random.Random(SEED).shuffle(order)
        for start in range(0, len(order), BATCH):
            pick = [rows[i] for i in order[start : start + BATCH]]
            yield pick

    best_state = None
    best_val = -1.0
    history = []
    for epoch in range(EPOCHS):
        model.train()
        total = 0.0
        seen = 0
        step = 0
        for pick in batches(train_rows):
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
            loss = model(**encoded, labels=labels).loss
            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            total += float(loss.item()) * len(pick)
            seen += len(pick)
            step += 1
            if step % 100 == 0:
                print(f"epoch {epoch + 1} step {step} loss {total / seen:.4f}", flush=True)
        val_pred = predict_pairs(model, tokenizer, device, [(e, t) for e, t, _ in val_rows])
        val_f1 = macro_f1([row[2] for row in val_rows], val_pred)
        history.append({"epoch": epoch + 1, "train_loss": total / max(seen, 1), "validation_macro_f1": val_f1})
        print(f"epoch {epoch + 1} val_macro_f1 {val_f1:.4f}", flush=True)
        if val_f1 > best_val:
            best_val = val_f1
            best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
    CKPT.mkdir(parents=True, exist_ok=True)
    torch.save(best_state, CKPT / "best.pt")
    model.load_state_dict(best_state)
    model.to(device)
    test_pred = predict_pairs(model, tokenizer, device, [(e, t) for e, t, _ in test_rows])
    test_gold = [row[2] for row in test_rows]
    test_f1 = macro_f1(test_gold, test_pred)
    print(f"test_split_macro_f1 {test_f1:.4f}", flush=True)
    gold_pred = predict_pairs(model, tokenizer, device, [(item["node"], item["text"]) for item in gold])
    fin_tok = AutoTokenizer.from_pretrained(FINBERT)
    fin_model = AutoModelForSequenceClassification.from_pretrained(FINBERT).to(device)
    # FinBERT scores the text. An empty entity string still builds a pair, so
    # score with the text as the only sequence.
    fin_model.eval()
    fin_pred = []
    fin_map = {int(k): v.lower() for k, v in fin_model.config.id2label.items()}
    if any(label not in LABELS for label in fin_map.values()):
        raise SystemExit(f"FinBERT labels are not the three-class set: {fin_map}")
    with torch.no_grad():
        texts = [item["text"] for item in gold]
        for start in range(0, len(texts), 32):
            encoded = fin_tok(
                texts[start : start + 32],
                padding=True,
                truncation=True,
                max_length=MAX_LEN,
                return_tensors="pt",
            )
            encoded = {key: value.to(device) for key, value in encoded.items()}
            choice = fin_model(**encoded).logits.argmax(dim=1).tolist()
            fin_pred.extend(fin_map[i] for i in choice)
    return {
        "base": BASE,
        "device": str(device),
        "epochs": history,
        "selected_validation_macro_f1": best_val,
        "test_split": {
            "documents": {name: len(docs) for name, docs in splits.items()},
            "examples": {
                "train": len(train_rows),
                "validation": len(val_rows),
                "test": len(test_rows),
            },
            "macro_f1": test_f1,
            "confusion": confusion(test_gold, test_pred),
        },
        "gold_entity": gold_pred,
        "gold_finbert": fin_pred,
    }


def pack_scores(gold: list[dict], pred: list[str], key: str) -> dict:
    overall = bootstrap([item["label"] for item in gold], pred, key)
    by_source = {}
    for source in ("huffpost", "fnspid", "stocktwits"):
        idx = [i for i, item in enumerate(gold) if item["source"] == source]
        by_source[source] = bootstrap(
            [gold[i]["label"] for i in idx],
            [pred[i] for i in idx],
            f"{key}:{source}",
        )
    return {"overall": overall, "by_source": by_source}


def public_copy(payload: dict) -> dict:
    hidden = {"gold", "vader_pred", "entity_pred", "finbert_pred"}
    out = {key: value for key, value in payload.items() if key not in hidden}
    return out


def main() -> None:
    rows = load_rows()
    assembled = assemble(rows)
    gold = assembled.pop("gold")
    vader = score_vader(gold)
    assembled["vader"] = pack_scores(gold, vader, "vader")
    assembled["stocktwits_user_label"] = stocktwits_check(rows, gold)
    splits, skipped = training_docs()
    assembled["training_documents_skipped_annotations"] = skipped
    OUT.write_text(json.dumps(public_copy(assembled), indent=2))
    print("kappa", round(assembled["kappa"]["cohen_kappa"], 4), flush=True)
    print("gold", assembled["gold_n"], "dropped", assembled["not_about_brand"]["dropped_from_gold"], flush=True)
    print("vader", round(assembled["vader"]["overall"]["macro_f1"], 4), flush=True)
    neural = run_neural(gold, splits)
    entity_pred = neural.pop("gold_entity")
    fin_pred = neural.pop("gold_finbert")
    assembled["entity_classifier"] = neural
    assembled["entity_classifier"]["gold"] = pack_scores(gold, entity_pred, "entity")
    assembled["finbert"] = pack_scores(gold, fin_pred, "finbert")
    primary = assembled["entity_classifier"]["gold"]["overall"]["macro_f1"]
    assembled["gate"] = {
        "primary": "entity_classifier",
        "threshold": 0.70,
        "macro_f1": primary,
        "pass": primary >= 0.70,
    }
    OUT.write_text(json.dumps(public_copy(assembled), indent=2))
    print("gate", assembled["gate"], flush=True)


if __name__ == "__main__":
    main()

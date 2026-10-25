"""Compare the Wave 1 scorer with one finance-pretrained scorer.

Reads data/handlabel/wave2_sample.csv. Exits while label_A is empty.
Does not download weights. The finance-pretrained candidate is
ProsusAI/finbert, loaded only from the local cache.
"""

from __future__ import annotations

import csv
import json
import os
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("HF_HOME", str(ROOT / "data" / "interim" / "phase3" / "hf"))
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
sys.path.insert(0, str(ROOT / "scripts"))

from phase3_gate import LABELS, bootstrap  # noqa: E402

SHEET = ROOT / "data" / "handlabel" / "wave2_sample.csv"
OUT = ROOT / "eval" / "results" / "wave2_scorer_v2.json"
WEIGHTS = ROOT / "data" / "interim" / "phase3" / "final_scorer" / "model.pt"
FINBERT = "ProsusAI/finbert"
FOUR = ("positive", "negative", "neutral", "not_about_brand")


def load_sheet() -> list[dict]:
    rows = list(csv.DictReader(SHEET.open()))
    if not rows:
        raise SystemExit("the label sheet is empty")
    blank = [row["id"] for row in rows if not (row.get("label_A") or "").strip()]
    if blank:
        raise SystemExit(f"labels are not saved yet: {len(blank)} blank label_A cells")
    bad = [row["id"] for row in rows if row["label_A"].strip() not in FOUR]
    if bad:
        raise SystemExit(f"label_A is outside the four words: {bad[:5]}")
    unmarked = [row["id"] for row in rows if "[[" not in row["text"] or "]]" not in row["text"]]
    if unmarked:
        raise SystemExit(f"a row has no marked mention: {unmarked[:5]}")
    return rows


def predict_wave1(rows: list[dict]) -> list[str]:
    import torch

    from phase3_roberta import load_fresh

    device = torch.device("cpu")
    torch.set_num_threads(4)
    state = torch.load(WEIGHTS, map_location="cpu", weights_only=True)
    model, tokenizer = load_fresh(device, state)
    model.eval()
    labels = []
    with torch.no_grad():
        for start in range(0, len(rows), 8):
            batch = rows[start : start + 8]
            encoded = tokenizer(
                [row["node"] for row in batch],
                [row["text"] for row in batch],
                padding=True,
                truncation=True,
                max_length=128,
                return_tensors="pt",
            )
            encoded = {key: value.to(device) for key, value in encoded.items()}
            choice = torch.softmax(model(**encoded).logits, dim=1).argmax(dim=1).tolist()
            labels.extend(LABELS[index] for index in choice)
    return labels


def predict_finbert(rows: list[dict]) -> list[str]:
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    device = torch.device("cpu")
    torch.set_num_threads(4)
    try:
        tokenizer = AutoTokenizer.from_pretrained(FINBERT, local_files_only=True)
        model = AutoModelForSequenceClassification.from_pretrained(FINBERT, local_files_only=True)
    except OSError as exc:
        raise SystemExit(f"finance-pretrained weights are not local. Not downloading. {exc}") from exc
    model.to(device)
    model.eval()
    mapping = {int(key): value.lower() for key, value in model.config.id2label.items()}
    if any(label not in LABELS for label in mapping.values()):
        raise SystemExit(f"FinBERT labels are not the three-class set: {mapping}")
    labels = []
    with torch.no_grad():
        for start in range(0, len(rows), 8):
            batch = rows[start : start + 8]
            encoded = tokenizer(
                [row["text"] for row in batch],
                padding=True,
                truncation=True,
                max_length=128,
                return_tensors="pt",
            )
            encoded = {key: value.to(device) for key, value in encoded.items()}
            choice = model(**encoded).logits.argmax(dim=1).tolist()
            labels.extend(mapping[index] for index in choice)
    return labels


def by_ecosystem(rows: list[dict], gold: list[str], pred: list[str], tag: str) -> dict:
    out = {}
    for eco in sorted({row["ecosystem"] for row in rows}):
        idx = [i for i, row in enumerate(rows) if row["ecosystem"] == eco]
        out[eco] = bootstrap([gold[i] for i in idx], [pred[i] for i in idx], f"{tag}-{eco}")
    return out


def main() -> None:
    rows = load_sheet()
    scored = [row for row in rows if row["label_A"].strip() != "not_about_brand"]
    if not scored:
        raise SystemExit("every row is not_about_brand")
    gold = [row["label_A"].strip() for row in scored]
    wave1 = predict_wave1(scored)
    finance = predict_finbert(scored)
    totals = Counter(row["ecosystem"] for row in rows)
    nab = Counter(row["ecosystem"] for row in rows if row["label_A"].strip() == "not_about_brand")
    payload = {
        "sheet": "data/handlabel/wave2_sample.csv",
        "rows": len(rows),
        "scored_rows": len(scored),
        "excluded_not_about_brand": len(rows) - len(scored),
        "not_about_brand_by_ecosystem": {
            eco: {"rows": totals[eco], "not_about_brand": nab[eco]} for eco in sorted(totals)
        },
        "input": "marked mention. The Wave 1 scorer receives the node and the marked sentence. FinBERT receives the marked sentence.",
        "gate": 0.70,
        "wave1_scorer": bootstrap(gold, wave1, "wave2-wave1-scorer"),
        "finance_pretrained": bootstrap(gold, finance, "wave2-finbert"),
        "wave1_scorer_by_ecosystem": by_ecosystem(scored, gold, wave1, "wave2-wave1"),
        "finance_pretrained_by_ecosystem": by_ecosystem(scored, gold, finance, "wave2-finbert"),
    }
    winner = "wave1_scorer"
    if payload["finance_pretrained"]["macro_f1"] > payload["wave1_scorer"]["macro_f1"]:
        winner = "finance_pretrained"
    payload["higher_macro_f1"] = winner
    payload["gate_met"] = payload[winner]["macro_f1"] >= 0.70
    OUT.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps({"higher_macro_f1": winner, "gate_met": payload["gate_met"]}), flush=True)


if __name__ == "__main__":
    main()

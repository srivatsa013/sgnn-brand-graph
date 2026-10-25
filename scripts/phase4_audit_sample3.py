"""Third-sheet audit. Scores the saved sheet. Does not train.

The draw is rebuilt only to check that the ids, headlines, and text
were not edited. The sheet file is not rewritten.
"""

from __future__ import annotations

import csv
import io
import json
import os
import random
import sys
from collections import Counter
from pathlib import Path

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from phase3_gate import LABELS, VADER_CUT, confusion, kappa, macro_f1, vader_label  # noqa: E402
from phase3_roberta import load_fresh  # noqa: E402
from phase4_sample3 import SHEET, already_used, collapse, draw, fill_text  # noqa: E402
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer  # noqa: E402

WEIGHTS = ROOT / "data" / "interim" / "phase3" / "final_scorer" / "model.pt"
DISAGREE = ROOT / "data" / "handlabel" / "disagreements3.csv"
OUT = ROOT / "eval" / "results" / "phase4_audit_sample3.json"
WORDS = {"positive", "negative", "neutral", "not_about_brand"}
DOUBLE = {
    "HL2002", "HL2006", "HL2008", "HL2011", "HL2013", "HL2016", "HL2024",
    "HL2029", "HL2038", "HL2039", "HL2043", "HL2048", "HL2054", "HL2056",
    "HL2065", "HL2067", "HL2072", "HL2076", "HL2089", "HL2093", "HL2097",
    "HL2098", "HL2112", "HL2115", "HL2128", "HL2129", "HL2140", "HL2154",
    "HL2165", "HL2168", "HL2180", "HL2182", "HL2186", "HL2187", "HL2188",
    "HL2189", "HL2192", "HL2198", "HL2199", "HL2200",
}
EXPECTED_IDS = [f"HL{2001 + i}" for i in range(200)]
FIELDS = ["item_id", "source", "node", "headline", "text", "label_A", "label_B"]
BOOT = 1000
Z = 1.959964
FORWARD = 2


def load_sheet(path: Path) -> tuple[list[dict], list[str]]:
    raw_lines = path.read_text().splitlines()
    problems = []
    start = 0
    if raw_lines and not raw_lines[0].startswith("item_id,"):
        problems.append(f"leading line is not the header: {raw_lines[0]!r}")
        start = 1
    reader = csv.DictReader(io.StringIO("\n".join(raw_lines[start:])))
    if reader.fieldnames != FIELDS:
        problems.append(f"columns are {reader.fieldnames}")
    return list(reader), problems


def validate(rows: list[dict], expected: list[dict], problems: list[str]) -> list[str]:
    got_ids = [row["item_id"] for row in rows]
    if got_ids != EXPECTED_IDS:
        problems.append("item ids are not HL2001 through HL2200 in order")
    if len(rows) != len(expected):
        problems.append(f"row count {len(rows)} expected {len(expected)}")
    by_id = {row["item_id"]: row for row in expected}
    changed = []
    for row in rows:
        item = row["item_id"]
        label_a = (row.get("label_A") or "").strip()
        label_b = (row.get("label_B") or "").strip()
        if label_a not in WORDS:
            problems.append(f"{item} label_A {label_a!r}")
        if item in DOUBLE:
            if label_b not in WORDS:
                problems.append(f"{item} label_B {label_b!r}")
        elif label_b:
            problems.append(f"{item} label_B is filled")
        original = by_id.get(item)
        if original is None:
            changed.append(item)
            continue
        if row["source"] != original["source"] or row["node"] != original["node"]:
            changed.append(item)
        elif row["headline"] != original["headline"] or row["text"] != original["text"]:
            changed.append(item)
    if changed:
        problems.append(f"headline or text differs on {len(changed)} rows, first {changed[:8]}")
    return problems


def resolve(rows: list[dict]) -> tuple[list[tuple[str, str]], list[dict], list[dict], list[dict]]:
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
            "node": row["node"],
            "headline": row["headline"],
            "text": row["text"],
            "stratum": row["stratum"],
            "label": label,
        }
        if label == "not_about_brand":
            dropped.append(item)
        else:
            gold.append(item)
    return pairs, disagreements, gold, dropped


def write_disagreements(rows: list[dict]) -> None:
    with DISAGREE.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["item_id", "source", "node", "headline", "text", "label_A", "label_B", "adjudication"],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "item_id": row["item_id"],
                    "source": row["source"],
                    "node": row["node"],
                    "headline": row["headline"],
                    "text": row["text"],
                    "label_A": row["label_A"].strip(),
                    "label_B": row["label_B"].strip(),
                    "adjudication": "",
                }
            )


def percentile(seed: str, gold: list[str], pred: list[str]) -> dict:
    n = len(gold)
    if n == 0:
        return {"macro_f1": None, "lo": None, "hi": None, "seed": seed, "draws": BOOT, "n": 0, "confusion": {}}
    rng = random.Random(seed)
    draws = []
    for _ in range(BOOT):
        pick = [rng.randrange(n) for _ in range(n)]
        draws.append(macro_f1([gold[i] for i in pick], [pred[i] for i in pick]))
    draws.sort()
    point = macro_f1(gold, pred)
    return {
        "macro_f1": point,
        "lo": draws[int(0.025 * (BOOT - 1))],
        "hi": draws[int(0.975 * (BOOT - 1))],
        "seed": seed,
        "draws": BOOT,
        "n": n,
        "confusion": confusion(gold, pred),
    }


def wilson(successes: int, n: int) -> dict:
    if n == 0:
        return {"n": 0, "successes": 0, "precision": None, "lo": None, "hi": None}
    p = successes / n
    z2 = Z * Z
    denom = 1 + z2 / n
    center = (p + z2 / (2 * n)) / denom
    half = Z * ((p * (1 - p) / n + z2 / (4 * n * n)) ** 0.5) / denom
    return {"n": n, "successes": successes, "precision": p, "lo": center - half, "hi": center + half}


def score_both(gold: list[dict]) -> tuple[list[str], list[str]]:
    device = torch.device("cpu")
    torch.set_num_threads(4)
    state = torch.load(WEIGHTS, map_location="cpu", weights_only=True)
    model, tokenizer = load_fresh(device, state)
    model.eval()

    def run(texts: list[str]) -> list[str]:
        labels = []
        with torch.no_grad():
            for start in range(0, len(gold), FORWARD):
                chunk_nodes = [row["node"] for row in gold[start : start + FORWARD]]
                chunk_text = texts[start : start + FORWARD]
                encoded = tokenizer(
                    chunk_nodes,
                    chunk_text,
                    padding=True,
                    truncation=True,
                    max_length=128,
                    return_tensors="pt",
                )
                encoded = {key: value.to(device) for key, value in encoded.items()}
                probs = torch.softmax(model(**encoded).logits, dim=1).tolist()
                for prob in probs:
                    labels.append(LABELS[max(range(3), key=lambda i: prob[i])])
        return labels

    joined = run([row["text"] for row in gold])
    headline = run([collapse(row["headline"]) for row in gold])
    return headline, joined


def block(gold: list[dict], pred: list[str], seed: str) -> dict:
    by_group = {}
    for stratum in ("named", "other"):
        chosen = [i for i, row in enumerate(gold) if row["stratum"] == stratum]
        by_group[stratum] = percentile(
            f"{seed}:{stratum}",
            [gold[i]["label"] for i in chosen],
            [pred[i] for i in chosen],
        )
    return {
        "overall": percentile(seed, [row["label"] for row in gold], pred),
        "by_draw_group": by_group,
    }


def linking(resolved: list[dict]) -> dict:
    out = {}
    for stratum in ("named", "other"):
        rows = [row for row in resolved if row["stratum"] == stratum]
        about = sum(row["label"] != "not_about_brand" for row in rows)
        out[stratum] = wilson(about, len(rows))
    named = out["named"]["precision"]
    other = out["other"]["precision"]
    out["weighted"] = None if named is None or other is None else 0.2037 * named + 0.7963 * other
    out["weights"] = {"named": 0.2037, "other": 0.7963}
    return out


def main() -> None:
    rows, problems = load_sheet(SHEET)
    print(f"sheet rows {len(rows)} preamble_problems {len(problems)}", flush=True)
    expected, double = draw(already_used())
    if set(double) != DOUBLE:
        problems.append("the 40 double-coded ids do not match the draw")
    fill_text(expected)
    for row in expected:
        row["source"] = "fnspid"
    strata = {row["item_id"]: row["stratum"] for row in expected}
    for row in rows:
        row["stratum"] = strata.get(row["item_id"], "")
    problems = validate(rows, expected, problems)
    hard = [item for item in problems if not item.startswith("leading line")]
    print("validation problems:", flush=True)
    if problems:
        for item in problems:
            print(f"  {item}", flush=True)
    else:
        print("  none", flush=True)
    if hard:
        raise SystemExit(2)
    pairs, disagreements, gold, dropped = resolve(rows)
    write_disagreements(disagreements)
    resolved = gold + dropped
    counts = {}
    for stratum in ("named", "other"):
        counts[stratum] = dict(Counter(row["label"] for row in resolved if row["stratum"] == stratum))
    vader = SentimentIntensityAnalyzer()
    headline_gold = gold
    print("scoring the saved sheet", flush=True)
    headline_pred, joined_pred = score_both(headline_gold)
    vader_pred = [
        vader_label(vader, collapse(row["headline"]))
        for row in headline_gold
    ]
    headline = block(headline_gold, headline_pred, "20261022:headline")
    joined = block(headline_gold, joined_pred, "20261022:joined")
    vader_block = block(headline_gold, vader_pred, "20261022:vader")
    link = linking(resolved)
    h = headline["overall"]
    j = joined["overall"]
    overlap = h["lo"] <= j["hi"] and j["lo"] <= h["hi"]
    if overlap or j["macro_f1"] > h["macro_f1"]:
        chosen = "joined"
        chosen_f1 = j["macro_f1"]
    else:
        chosen = "headline"
        chosen_f1 = h["macro_f1"]
    payload = {
        "rows": len(rows),
        "validation_problems": problems,
        "kappa_40": kappa(pairs),
        "double_coded": len(pairs),
        "disagreements": [
            {"item_id": row["item_id"], "label_A": row["label_A"].strip(), "label_B": row["label_B"].strip()}
            for row in disagreements
        ],
        "resolved_label_counts": counts,
        "not_about_brand_dropped": len(dropped),
        "scored": len(gold),
        "headline": headline,
        "joined": joined,
        "vader_headline": vader_block,
        "linking_precision": link,
        "intervals_overlap": overlap,
        "main_news_input": chosen,
        "main_macro_f1": chosen_f1,
        "retest_070": chosen_f1 >= 0.70,
        "restrict_news": link["weighted"] is not None and link["weighted"] < 0.90,
        "vader_cut": VADER_CUT,
    }
    OUT.write_text(json.dumps(payload, indent=2) + "\n")
    print(
        json.dumps(
            {
                "kappa_40": payload["kappa_40"],
                "disagreements": len(disagreements),
                "dropped": len(dropped),
                "scored": len(gold),
                "headline_f1": h["macro_f1"],
                "headline_interval": [h["lo"], h["hi"]],
                "joined_f1": j["macro_f1"],
                "joined_interval": [j["lo"], j["hi"]],
                "overlap": overlap,
                "chosen": chosen,
                "retest_070": payload["retest_070"],
                "linking_weighted": link["weighted"],
                "restrict_news": payload["restrict_news"],
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()

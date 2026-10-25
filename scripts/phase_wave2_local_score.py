"""Plumbing test for Wave 2 FNSPID and StockTwits scoring.

Uses the Wave 1 scorer on a fixed sample. Does not write a series and
does not score the full extracts. The full pass waits until scorer v2
is chosen.
"""

from __future__ import annotations

import argparse
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

import pyarrow.parquet as pq
import torch

from phase3_roberta import load_fresh  # noqa: E402

WEIGHTS = ROOT / "data" / "interim" / "phase3" / "final_scorer" / "model.pt"
AVAIL = ROOT / "reports" / "wave2_availability.json"
ALIASES = ROOT / "configs" / "wave2_gdelt_aliases.json"
OUT = ROOT / "eval" / "results" / "wave2_score_probe.json"
LABELS = ("positive", "negative", "neutral")


def wave2_nodes() -> dict[str, str]:
    items = json.loads(ALIASES.read_text())["items"]
    return {row["ticker"]: row["name"] for row in items if row["wave"] == 2}


def social_tickers(nodes: dict[str, str]) -> set[str]:
    payload = json.loads(AVAIL.read_text())["tickers"]
    kept = set()
    for ticker in nodes:
        row = payload[ticker]
        if row["series"] == "social" and row["distinct_days"] >= 14:
            kept.add(ticker)
    return kept


def take_fnspid(nodes: dict[str, str], limit: int) -> list[dict]:
    rows = []
    for path in sorted((ROOT / "data" / "raw" / "fnspid" / "parts").glob("*.parquet")):
        table = pq.ParquetFile(path)
        for batch in table.iter_batches(batch_size=2000, columns=["row_id", "day_utc", "ticker", "headline", "summary", "text"]):
            data = batch.to_pydict()
            for i, ticker in enumerate(data["ticker"]):
                ticker = (ticker or "").strip().upper()
                if ticker not in nodes or not data["day_utc"][i]:
                    continue
                text = " ".join(
                    part
                    for part in (data["headline"][i] or "", data["summary"][i] or "", data["text"][i] or "")
                    if part
                )
                if not text:
                    continue
                rows.append(
                    {
                        "source": "fnspid",
                        "ticker": ticker,
                        "node": nodes[ticker],
                        "day": data["day_utc"][i],
                        "text": text,
                    }
                )
                if len(rows) == limit:
                    return rows
    return rows


def take_stocktwits(nodes: dict[str, str], social: set[str], limit: int) -> list[dict]:
    wanted: dict[int, dict] = {}
    for path in sorted((ROOT / "data" / "raw" / "stocktwits" / "features").glob("*.parquet")):
        table = pq.read_table(path, columns=["message_id", "day_utc", "cashtags"])
        data = table.to_pydict()
        for mid, day, tags in zip(data["message_id"], data["day_utc"], data["cashtags"]):
            if not day or not tags:
                continue
            hit = next((tok for tok in tags.split("|") if tok in social), None)
            if hit is None or mid in wanted:
                continue
            wanted[mid] = {
                "source": "stocktwits",
                "ticker": hit,
                "node": nodes[hit],
                "day": day,
                "message_id": mid,
            }
            if len(wanted) == limit * 20:
                break
        if len(wanted) == limit * 20:
            break
    found = 0
    for path in sorted((ROOT / "data" / "raw" / "stocktwits" / "bodies").glob("*.parquet")):
        table = pq.read_table(path, columns=["message_id", "message_body"])
        data = table.to_pydict()
        for mid, body in zip(data["message_id"], data["message_body"]):
            row = wanted.get(mid)
            if row is None or "text" in row or not body:
                continue
            row["text"] = body
            found += 1
            if found == limit:
                return [row for row in wanted.values() if "text" in row][:limit]
    return [row for row in wanted.values() if "text" in row][:limit]


def load_model():
    device = torch.device("cpu")
    torch.set_num_threads(4)
    state = torch.load(WEIGHTS, map_location="cpu", weights_only=True)
    model, tokenizer = load_fresh(device, state)
    model.eval()
    return device, model, tokenizer


def score(rows: list[dict], device, model, tokenizer) -> Counter:
    counts: Counter = Counter()
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
            for label_index in choice:
                counts[LABELS[label_index]] += 1
    return counts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--full", action="store_true")
    args = parser.parse_args()
    if args.full:
        raise SystemExit("full scoring waits until scorer v2 is chosen")
    if not WEIGHTS.exists():
        raise SystemExit("Wave 1 scorer weights are missing")
    nodes = wave2_nodes()
    social = social_tickers(nodes)
    fnspid = take_fnspid(nodes, args.limit)
    stock = take_stocktwits(nodes, social, args.limit)
    if len(fnspid) != args.limit or len(stock) != args.limit:
        raise SystemExit(f"plumbing sample short: fnspid {len(fnspid)} stocktwits {len(stock)}")
    device, model, tokenizer = load_model()
    payload = {
        "scorer": "data/interim/phase3/final_scorer/model.pt",
        "full_extract_scored": False,
        "social_tickers": sorted(social),
        "news_only_tickers": sorted(set(nodes) - social),
        "fnspid": {"rows": len(fnspid), "labels": dict(score(fnspid, device, model, tokenizer))},
        "stocktwits": {"rows": len(stock), "labels": dict(score(stock, device, model, tokenizer))},
    }
    OUT.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps(payload), flush=True)


if __name__ == "__main__":
    main()

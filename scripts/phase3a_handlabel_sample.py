"""Draw the Phase 3A hand-label sample. No scores. Labels stay blank."""

from __future__ import annotations

import csv
import json
import random
import re
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "handlabel"
SEED = 20261021
BRANDS = ("Apple", "Microsoft", "Alphabet", "Tesla")
SOURCES = ("huffpost", "fnspid", "stocktwits")
PER_CELL = 38  # 4 brands x 3 sources x 38 = 456, trimmed to 450
TARGET = 450
DOUBLE = 100
STUDY = {"AAPL": "Apple", "MSFT": "Microsoft", "GOOG": "Alphabet", "GOOGL": "Alphabet", "TSLA": "Tesla"}


def wb(phrase: str, flags: int = re.IGNORECASE) -> re.Pattern:
    return re.compile(r"(?<![A-Za-z0-9])" + re.escape(phrase) + r"(?![A-Za-z0-9])", flags)


RULES = {
    "Apple": [wb("Apple", 0)],
    "Microsoft": [wb("Microsoft")],
    "Alphabet": [wb("Google"), wb("Alphabet")],
    "Tesla": [wb("Tesla")],
}


def mentioned(text: str) -> list[str]:
    return [brand for brand, patterns in RULES.items() if any(pattern.search(text) for pattern in patterns)]


def reservoir(found: dict, source: str, brand: str, text: str, rng: random.Random, cap: int = 400) -> None:
    text = " ".join(text.split())
    if len(text) < 20:
        return
    bucket = found.setdefault((source, brand), [])
    row = {"source": source, "node": brand, "text": text}
    if len(bucket) < cap:
        bucket.append(row)
        return
    slot = rng.randrange(len(bucket) + 1)
    if slot < cap:
        bucket[slot] = row


def huffpost(found: dict, rng: random.Random) -> None:
    path = ROOT / "data" / "interim" / "news_category" / "data.json"
    with path.open() as handle:
        for line in handle:
            row = json.loads(line)
            if row.get("category") not in {"TECH", "BUSINESS"}:
                continue
            text = f"{row.get('headline') or ''}. {row.get('short_description') or ''}"
            brands = mentioned(text)
            if len(brands) != 1:
                continue
            reservoir(found, "huffpost", brands[0], text, rng)


def fnspid(found: dict, rng: random.Random) -> None:
    for path in sorted((ROOT / "data" / "raw" / "fnspid" / "parts").glob("*.parquet")):
        table = pq.read_table(path, columns=["headline"])
        for headline in table.column("headline").to_pylist():
            brands = mentioned(headline or "")
            if len(brands) != 1:
                continue
            reservoir(found, "fnspid", brands[0], headline, rng)


def stocktwits(found: dict, rng: random.Random) -> None:
    wanted: dict[int, str] = {}
    pools = {brand: [] for brand in BRANDS}
    for path in sorted((ROOT / "data" / "raw" / "stocktwits" / "features").glob("*.parquet")):
        table = pq.read_table(path, columns=["message_id", "cashtags"])
        for message_id, cashtags in zip(table.column("message_id").to_pylist(), table.column("cashtags").to_pylist()):
            brands = sorted({STUDY[tag] for tag in (cashtags or "").split("|") if tag in STUDY})
            if len(brands) != 1:
                continue
            pools[brands[0]].append(message_id)
    chosen = {}
    for brand, ids in pools.items():
        pick = ids if len(ids) <= 80 else rng.sample(ids, 80)
        for message_id in pick:
            chosen[message_id] = brand
    bodies = {}
    for path in sorted((ROOT / "data" / "raw" / "stocktwits" / "bodies").glob("*.parquet")):
        table = pq.read_table(path, columns=["message_id", "message_body"])
        for message_id, body in zip(table.column("message_id").to_pylist(), table.column("message_body").to_pylist()):
            if message_id in chosen and message_id not in bodies:
                bodies[message_id] = body or ""
    for message_id, brand in chosen.items():
        if message_id in bodies:
            reservoir(found, "stocktwits", brand, bodies[message_id], rng, cap=80)


def main() -> None:
    rng = random.Random(SEED)
    found: dict = {}
    huffpost(found, rng)
    fnspid(found, rng)
    stocktwits(found, rng)
    print({key: len(value) for key, value in sorted(found.items())}, flush=True)
    draw = []
    for source in SOURCES:
        for brand in BRANDS:
            pool = found.get((source, brand), [])
            take = min(PER_CELL, len(pool))
            draw.extend(rng.sample(pool, take) if take else [])
    rng.shuffle(draw)
    if len(draw) > TARGET:
        draw = draw[:TARGET]
    rng.shuffle(draw)
    double_ids = []
    rows = []
    for index, row in enumerate(draw, start=1):
        double = len(double_ids) < DOUBLE and index <= DOUBLE
        # Spread the double-coded rows by taking every k-th item after a shuffle.
        item_id = f"HL{index:04d}"
        rows.append(row | {"item_id": item_id, "label_A": "", "label_B": ""})
    # Re-pick 100 double-coded ids spread across source and brand.
    by_cell: dict[tuple, list] = {}
    for row in rows:
        by_cell.setdefault((row["source"], row["node"]), []).append(row)
    double_rows = []
    while len(double_rows) < min(DOUBLE, len(rows)):
        progress = False
        for source in SOURCES:
            for brand in BRANDS:
                cell = [row for row in by_cell.get((source, brand), []) if row not in double_rows]
                if cell and len(double_rows) < DOUBLE:
                    double_rows.append(cell[0])
                    progress = True
        if not progress:
            break
    double_ids = {row["item_id"] for row in double_rows}
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "sample.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["item_id", "source", "node", "text", "label_A", "label_B"])
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row[key] for key in writer.fieldnames})
    counts = {}
    for row in rows:
        counts[(row["source"], row["node"])] = counts.get((row["source"], row["node"]), 0) + 1
    (OUT / "sample_design.json").write_text(
        json.dumps(
            {
                "seed": SEED,
                "n": len(rows),
                "double_item_ids": sorted(double_ids),
                "counts": {f"{source}|{brand}": counts.get((source, brand), 0) for source in SOURCES for brand in BRANDS},
                "blind_to_model_score": True,
            },
            indent=2,
        )
    )
    print("wrote", len(rows), "double", len(double_ids), flush=True)


if __name__ == "__main__":
    main()

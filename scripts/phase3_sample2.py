"""Draw the second hand-label sheet. No scores and no user labels are written."""

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
FNSPID_N = 200
PER_CLASS = 50
DOUBLE_PER_SOURCE = 25
RESERVOIR = 2000


def collapse(text: str) -> str:
    return " ".join((text or "").split())


def load_patterns() -> tuple[list[tuple[str, re.Pattern]], dict[str, str]]:
    phase2 = json.loads((ROOT / "configs" / "phase2_nodes.json").read_text())
    phase1 = json.loads((ROOT / "configs" / "phase1_universe.json").read_text())
    aliases: dict[str, str] = {}
    tickers: dict[str, str] = {}
    for name, spec in phase2["ecosystems"].items():
        for alias in spec.get("brand_aliases") or []:
            aliases.setdefault(alias, name)
        for ticker in spec.get("brand_tickers") or []:
            tickers[ticker] = name
        for node in (spec.get("positive_nodes") or []) + (spec.get("competitor_nodes") or []):
            if any(ch.islower() for ch in node) and len(node) >= 4:
                aliases.setdefault(node, node)
            elif node.isupper() and node.isalpha():
                tickers.setdefault(node, node)
    for name, spec in phase1["alias_nodes"].items():
        for alias in spec.get("aliases") or []:
            aliases.setdefault(alias, name)
        for ticker in spec.get("aliases_are_tickers") or []:
            tickers[ticker] = name
    patterns = []
    for alias, node in sorted(aliases.items(), key=lambda item: (-len(item[0]), item[0])):
        if len(alias) < 4:
            continue
        patterns.append(
            (
                node,
                re.compile(r"(?<![A-Za-z0-9])" + re.escape(alias) + r"(?![A-Za-z0-9])"),
            )
        )
    return patterns, tickers


def matched_nodes(text: str, patterns: list[tuple[str, re.Pattern]]) -> list[str]:
    found = []
    for node, pattern in patterns:
        if pattern.search(text) and node not in found:
            found.append(node)
    return found


def reservoir_add(bucket: list, row: dict, seen: int, rng: random.Random, cap: int) -> None:
    if len(bucket) < cap:
        bucket.append(row)
        return
    slot = rng.randrange(seen)
    if slot < cap:
        bucket[slot] = row


def build_rows() -> list[dict]:
    rng = random.Random(SEED)
    patterns, tickers = load_patterns()
    used = set()
    with (OUT / "sample.csv").open(newline="") as handle:
        for row in csv.DictReader(handle):
            used.add(collapse(row["text"]))
    news = []
    news_texts = set()
    news_seen = 0
    for path in sorted((ROOT / "data" / "raw" / "fnspid" / "parts").glob("*.parquet")):
        table = pq.read_table(path, columns=["headline"])
        for headline in table.column("headline").to_pylist():
            text = collapse(headline)
            if len(text) < 20 or text in used or text in news_texts:
                continue
            nodes = matched_nodes(text, patterns)
            if len(nodes) != 1:
                continue
            news_seen += 1
            if len(news) < FNSPID_N:
                news.append({"source": "fnspid", "node": nodes[0], "text": text, "hidden_class": ""})
                news_texts.add(text)
                continue
            slot = rng.randrange(news_seen)
            if slot < FNSPID_N:
                news_texts.discard(news[slot]["text"])
                news[slot] = {"source": "fnspid", "node": nodes[0], "text": text, "hidden_class": ""}
                news_texts.add(text)
        print(f"fnspid {path.name} eligible {news_seen}", flush=True)
    if len(news) < FNSPID_N:
        raise SystemExit(f"only {len(news)} FNSPID headlines were eligible")
    for row in news:
        used.add(row["text"])
    pools = {"bullish": [], "bearish": []}
    seen = {"bullish": 0, "bearish": 0}
    label_of = {"bullish": "bullish", "bearish": "bearish", "1": "bullish", "1.0": "bullish", "-1": "bearish", "-1.0": "bearish"}
    for path in sorted((ROOT / "data" / "raw" / "stocktwits" / "features").glob("*.parquet")):
        table = pq.read_table(path, columns=["message_id", "sentiment", "cashtags"])
        for message_id, sentiment, cashtags in zip(
            table.column("message_id").to_pylist(),
            table.column("sentiment").to_pylist(),
            table.column("cashtags").to_pylist(),
        ):
            klass = label_of.get((sentiment or "").strip().lower())
            if klass is None:
                continue
            nodes = []
            for tag in (cashtags or "").split("|"):
                node = tickers.get(tag)
                if node and node not in nodes:
                    nodes.append(node)
            if len(nodes) != 1:
                continue
            seen[klass] += 1
            reservoir_add(pools[klass], {"message_id": message_id, "node": nodes[0]}, seen[klass], rng, RESERVOIR)
        print(f"features {path.name} bullish {seen['bullish']} bearish {seen['bearish']}", flush=True)
    wanted = {row["message_id"]: row for klass in pools for row in pools[klass]}
    bodies = {}
    for path in sorted((ROOT / "data" / "raw" / "stocktwits" / "bodies").glob("*.parquet")):
        table = pq.read_table(path, columns=["message_id", "message_body"])
        for message_id, body in zip(table.column("message_id").to_pylist(), table.column("message_body").to_pylist()):
            if message_id in wanted and message_id not in bodies:
                bodies[message_id] = collapse(body)
        print(f"bodies {path.name}", flush=True)
    social = []
    for klass in ("bullish", "bearish"):
        ready = []
        for row in pools[klass]:
            text = bodies.get(row["message_id"]) or ""
            if len(text) < 20 or text in used:
                continue
            ready.append({"source": "stocktwits", "node": row["node"], "text": text, "hidden_class": klass})
        if len(ready) < PER_CLASS:
            raise SystemExit(f"{klass} has {len(ready)} messages after exclusions")
        social.extend(rng.sample(ready, PER_CLASS))
    draw = news + social
    rng.shuffle(draw)
    rows = []
    for index, row in enumerate(draw, start=1001):
        rows.append(row | {"item_id": f"HL{index:04d}", "label_A": "", "label_B": ""})
    buckets = {"fnspid": [], "bullish": [], "bearish": []}
    for row in rows:
        if row["source"] == "fnspid":
            buckets["fnspid"].append(row)
        else:
            buckets[row["hidden_class"]].append(row)
    double = []
    while len(double) < DOUBLE_PER_SOURCE:
        if not buckets["fnspid"]:
            raise SystemExit("ran out of FNSPID rows while choosing double codes")
        double.append(buckets["fnspid"].pop(0))
    flips = ("bullish", "bearish")
    while len([row for row in double if row["source"] == "stocktwits"]) < DOUBLE_PER_SOURCE:
        placed = False
        for klass in flips:
            if len([row for row in double if row["source"] == "stocktwits"]) >= DOUBLE_PER_SOURCE:
                break
            if buckets[klass]:
                double.append(buckets[klass].pop(0))
                placed = True
        if not placed:
            raise SystemExit("ran out of StockTwits rows while choosing double codes")
    double_ids = {row["item_id"] for row in double}
    for row in rows:
        row["double"] = row["item_id"] in double_ids
    return rows


def main() -> None:
    if (OUT / "sample2.csv").exists():
        with (OUT / "sample2.csv").open(newline="") as handle:
            filled = any(row["label_A"].strip() for row in csv.DictReader(handle))
        if filled:
            raise SystemExit("sample2.csv already has labels and was not overwritten")
    rows = build_rows()
    double_ids = {row["item_id"] for row in rows if row["double"]}
    with (OUT / "sample2.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["item_id", "source", "node", "text", "label_A", "label_B"])
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row[key] for key in writer.fieldnames})
    design = {
        "seed": SEED,
        "n": len(rows),
        "fnspid": sum(row["source"] == "fnspid" for row in rows),
        "stocktwits": sum(row["source"] == "stocktwits" for row in rows),
        "double_ids": [row["item_id"] for row in rows if row["item_id"] in double_ids],
        "by_source_and_node": {},
    }
    for row in rows:
        key = f"{row['source']}|{row['node']}"
        design["by_source_and_node"][key] = design["by_source_and_node"].get(key, 0) + 1
    (OUT / "sample2_design.json").write_text(json.dumps(design, indent=2))
    print(json.dumps({"n": design["n"], "double": len(design["double_ids"])}, indent=2))


if __name__ == "__main__":
    main()

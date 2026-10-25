"""Count FNSPID (document, node) pairs for the Phase 4 scorer.

A pair is one kept news row and one node. The node is in the 14
ecosystems (brand, product, person, competitor) or in the control pool.
Ticker links and alias links use the Phase 2 linker. Control-pool
tickers that the linker does not already map are added from the row
ticker. This script does not score and does not write series.sqlite.
"""

from __future__ import annotations

import json
import random
import sys
from collections import Counter
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from phase2_build_series import node_hits, patterns_from_universe, ticker_nodes  # noqa: E402

UNI = json.loads((ROOT / "configs" / "phase1_universe.json").read_text())
NODES = json.loads((ROOT / "configs" / "phase2_nodes.json").read_text())
OUT = ROOT / "eval" / "results" / "phase4_fnspid_pair_count.json"
SAMPLE = ROOT / "data" / "interim" / "phase3" / "fnspid_timing_pairs.jsonl"
SAMPLE_N = 1000


def document_hits(ticker: str, blob: str, nodes: set[str], pool: set[str], ticker_map: dict[str, str], alias_patterns) -> set[str]:
    present = {ticker} if ticker else set()
    hits = node_hits(ticker_map, present, blob, alias_patterns)
    if ticker in pool and ticker not in ticker_map:
        hits.add(ticker)
    return hits & nodes


def wanted_nodes() -> tuple[set[str], set[str]]:
    pool = {ticker for names in UNI["control_pool_by_bucket"].values() for ticker in names}
    nodes = set(NODES["ecosystems"]) | pool
    for spec in NODES["ecosystems"].values():
        nodes.update(spec["positive_nodes"])
        nodes.update(spec["competitor_nodes"])
    return nodes, pool


def main() -> None:
    nodes, pool = wanted_nodes()
    alias_patterns, _brand_patterns = patterns_from_universe()
    ticker_map = ticker_nodes()
    parts = sorted((ROOT / "data" / "raw" / "fnspid" / "parts").glob("*.parquet"))
    pairs = 0
    sample_n = 0
    documents_with_pair = 0
    by_node: Counter[str] = Counter()
    kept = 0
    drawn: list[dict] = []
    rng = random.Random(20261021)
    for path in parts:
        table = pq.ParquetFile(path)
        for batch in table.iter_batches(batch_size=2000, columns=["row_id", "day_utc", "ticker", "headline", "summary", "text"]):
            data = batch.to_pydict()
            for i, day in enumerate(data["day_utc"]):
                if not day:
                    continue
                kept += 1
                ticker = (data["ticker"][i] or "").strip().upper()
                headline = data["headline"][i] or ""
                blob = " ".join(
                    part for part in (headline, data["summary"][i] or "", data["text"][i] or "") if part
                )
                hits = document_hits(ticker, blob, nodes, pool, ticker_map, alias_patterns)
                if not hits:
                    continue
                documents_with_pair += 1
                for node in hits:
                    pairs += 1
                    by_node[node] += 1
                    record = {
                        "row_id": data["row_id"][i],
                        "day": day,
                        "node": node,
                        "text": blob[:4000],
                    }
                    if sample_n < SAMPLE_N:
                        drawn.append(record)
                    else:
                        slot = rng.randrange(pairs)
                        if slot < SAMPLE_N:
                            drawn[slot] = record
                    sample_n = min(sample_n + 1, SAMPLE_N)
        print(f"{path.name} documents {kept} pairs {pairs}", flush=True)
    SAMPLE.parent.mkdir(parents=True, exist_ok=True)
    with SAMPLE.open("w") as sample:
        for record in drawn:
            sample.write(json.dumps(record) + "\n")
    report = {
        "documents_with_day": kept,
        "documents_with_at_least_one_pair": documents_with_pair,
        "pairs": pairs,
        "nodes_with_pairs": len(by_node),
        "pairs_by_node": dict(sorted(by_node.items())),
        "timing_sample": str(SAMPLE.relative_to(ROOT)),
        "timing_sample_pairs": len(drawn),
        "link_rule": "Phase 2 ticker map and alias patterns, plus a control-pool ticker when the row ticker is in the pool and is not already mapped",
        "text_scored": "headline, summary, and text joined, the same blob the linker searches",
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n")
    print(f"pairs {pairs} documents {documents_with_pair}", flush=True)


if __name__ == "__main__":
    main()

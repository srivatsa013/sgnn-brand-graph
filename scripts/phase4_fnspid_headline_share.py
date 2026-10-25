"""Share of scored pairs whose headline names the node.

Counts only. No headline text is written. A registered alias list is
the name. A node with no alias list matches its own string.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

UNI = json.loads((ROOT / "configs" / "phase1_universe.json").read_text())
NODES = json.loads((ROOT / "configs" / "phase2_nodes.json").read_text())
PARTS = ROOT / "data" / "interim" / "phase3" / "fnspid_scores" / "parts"
RAW = ROOT / "data" / "raw" / "fnspid" / "parts"
OUT = ROOT / "eval" / "results" / "phase4_fnspid_headline_share.json"


def compile_aliases(aliases: list[str]) -> re.Pattern:
    parts = [r"\b" + re.escape(alias) + r"\b" for alias in aliases]
    return re.compile("|".join(parts), re.IGNORECASE)


def patterns() -> dict[str, re.Pattern]:
    found = {}
    for name, spec in UNI["alias_nodes"].items():
        aliases = spec.get("aliases") or []
        if aliases:
            found[name] = compile_aliases(aliases)
    for eco, spec in NODES["ecosystems"].items():
        found[eco] = compile_aliases(spec["brand_aliases"])
    return found


def names_node(headline: str, node: str, named: dict[str, re.Pattern], fallback: dict[str, re.Pattern]) -> bool:
    pattern = named.get(node)
    if pattern is None:
        pattern = fallback.get(node)
        if pattern is None:
            pattern = re.compile(r"\b" + re.escape(node) + r"\b", re.IGNORECASE)
            fallback[node] = pattern
    return pattern.search(headline or "") is not None


def main() -> None:
    named = patterns()
    fallback: dict[str, re.Pattern] = {}
    pairs: dict[tuple[str, str], list[str]] = {}
    for path in sorted(PARTS.glob("*.jsonl")):
        with path.open() as handle:
            for line in handle:
                row = json.loads(line)
                pairs.setdefault((path.stem, str(row["row_id"])), []).append(row["node"])
    total = 0
    hit = 0
    for path in sorted(RAW.glob("*.parquet")):
        table = pq.ParquetFile(path)
        for batch in table.iter_batches(batch_size=4000, columns=["row_id", "headline"]):
            data = batch.to_pydict()
            for row_id, headline in zip(data["row_id"], data["headline"]):
                nodes = pairs.get((path.stem, str(row_id)))
                if not nodes:
                    continue
                text = headline or ""
                for node in nodes:
                    total += 1
                    if names_node(text, node, named, fallback):
                        hit += 1
    payload = {
        "pairs": total,
        "headline_names_node": hit,
        "share": None if total == 0 else hit / total,
        "match": "registered alias list, or the node string when the node has no alias list",
        "joined_scores_kept": "data/interim/phase3/fnspid_scores",
    }
    OUT.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"pairs {total} named {hit} share {payload['share']}", flush=True)


if __name__ == "__main__":
    main()

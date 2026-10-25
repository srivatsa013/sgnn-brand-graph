"""Draw the third hand-label sheet from scored FNSPID pairs.

No score, ticker, or stratum is written. The text column is the document
span the joined scorer kept inside max_length 128.
"""

from __future__ import annotations

import csv
import json
import os
import random
import sys
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("HF_HOME", str(ROOT / "data" / "interim" / "phase3" / "hf"))
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
sys.path.insert(0, str(ROOT / "scripts"))

from phase4_fnspid_headline_share import names_node, patterns  # noqa: E402

OUT = ROOT / "data" / "handlabel"
SHEET = OUT / "sample3.csv"
INSTRUCTIONS = OUT / "INSTRUCTIONS.md"
SCORED = ROOT / "data" / "interim" / "phase3" / "fnspid_scores" / "parts"
RAW = ROOT / "data" / "raw" / "fnspid" / "parts"
SEED = 20261022
N = 100
MAX_LEN = 128


def collapse(text: str) -> str:
    return " ".join((text or "").split())


def already_used() -> set[tuple[str, str]]:
    used = set()
    for name in ("sample.csv", "sample2.csv"):
        with (OUT / name).open(newline="") as handle:
            for row in csv.DictReader(handle):
                if row["source"] != "fnspid":
                    continue
                used.add((row["node"], collapse(row["text"])))
    return used


def draw(used: set[tuple[str, str]]) -> tuple[list[dict], list[str]]:
    named_patterns = patterns()
    fallback = {}
    wanted: dict[tuple[str, str], list[str]] = {}
    for path in sorted(SCORED.glob("*.jsonl")):
        with path.open() as handle:
            for line in handle:
                row = json.loads(line)
                wanted.setdefault((path.stem, str(row["row_id"])), []).append(row["node"])
    named_rows = []
    other_rows = []
    for path in sorted(RAW.glob("*.parquet")):
        table = pq.ParquetFile(path)
        for batch in table.iter_batches(batch_size=4000, columns=["row_id", "headline"]):
            data = batch.to_pydict()
            for row_id, headline in zip(data["row_id"], data["headline"]):
                nodes = wanted.get((path.stem, str(row_id)))
                if not nodes:
                    continue
                headline = headline or ""
                for node in nodes:
                    if (node, collapse(headline)) in used:
                        continue
                    slot = {
                        "part": path.name,
                        "row_id": row_id,
                        "node": node,
                    }
                    if names_node(headline, node, named_patterns, fallback):
                        named_rows.append(slot)
                    else:
                        other_rows.append(slot)
    if len(named_rows) < N or len(other_rows) < N:
        raise SystemExit(f"pool too small: named {len(named_rows)} other {len(other_rows)}")
    rng = random.Random(SEED)
    picked = rng.sample(named_rows, N) + rng.sample(other_rows, N)
    strata = ["named"] * N + ["other"] * N
    order = list(range(2 * N))
    rng.shuffle(order)
    picked = [picked[i] for i in order]
    strata = [strata[i] for i in order]
    named_ids = []
    other_ids = []
    for index, stratum in enumerate(strata):
        item_id = f"HL{2001 + index}"
        picked[index]["item_id"] = item_id
        picked[index]["stratum"] = stratum
        if stratum == "named":
            named_ids.append(item_id)
        else:
            other_ids.append(item_id)
    double = sorted(rng.sample(named_ids, 20) + rng.sample(other_ids, 20))
    return picked, double


def joined_blob(headline: str, summary: str, body: str) -> str:
    return " ".join(part for part in (headline or "", summary or "", body or "") if part)


def model_text(tokenizer, node: str, blob: str) -> str:
    encoded = tokenizer(node, blob, truncation=True, max_length=MAX_LEN)
    ids = encoded["input_ids"]
    if len(ids) > MAX_LEN:
        raise SystemExit(f"tokenizer returned {len(ids)} ids")
    text_ids = [token for token, seq in zip(ids, encoded.sequence_ids()) if seq == 1]
    return tokenizer.decode(text_ids, skip_special_tokens=True)


def fill_text(rows: list[dict]) -> None:
    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained("roberta-base")
    by_part: dict[str, list[dict]] = {}
    for row in rows:
        by_part.setdefault(row["part"], []).append(row)
    for name, group in by_part.items():
        wanted = {str(row["row_id"]): [] for row in group}
        for row in group:
            wanted[str(row["row_id"])].append(row)
        table = pq.ParquetFile(RAW / name)
        for batch in table.iter_batches(batch_size=2000, columns=["row_id", "headline", "summary", "text"]):
            data = batch.to_pydict()
            for row_id, headline, summary, body in zip(
                data["row_id"], data["headline"], data["summary"], data["text"]
            ):
                targets = wanted.get(str(row_id))
                if not targets:
                    continue
                for row in targets:
                    row["headline"] = collapse(headline or "")
                    row["text"] = model_text(tokenizer, row["node"], joined_blob(headline or "", summary or "", body or ""))


def write_sheet(rows: list[dict]) -> None:
    fields = ["item_id", "source", "node", "headline", "text", "label_A", "label_B"]
    with SHEET.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "item_id": row["item_id"],
                    "source": "fnspid",
                    "node": row["node"],
                    "headline": row["headline"],
                    "text": row["text"],
                    "label_A": "",
                    "label_B": "",
                }
            )


def write_instructions(double: list[str]) -> None:
    marker = "## Third sheet"
    text = INSTRUCTIONS.read_text()
    if marker in text:
        text = text.split(marker)[0].rstrip() + "\n"
    ids = ", ".join(double)
    text += f"""
{marker}

`sample3.csv` is a third labeling task. The four label words are the same as above. Judge the sentiment toward the node expressed in `text`. If the text is not about that node, `not_about_brand`. If it is about the node but takes no side, `neutral`.

There are 200 rows, ids HL2001–HL2200, drawn with seed 20261022 from scored FNSPID pairs. `node` is the tracked node named in that column. `headline` is the headline. `text` is the headline, summary, and body as cut by the 128-token window the joined scorer used. Do not score the sheet. The sheet has no score, no ticker column, and no stratum column. Do not add them. Do not add rows. Do not change `headline` or `text`.

Annotator A fills `label_A` on every row.

Annotator B fills `label_B` on the 40 double-coded rows only and leaves it blank on the rest. Twenty of those rows are from each of the two draw groups. Those ids are:

{ids}.

Do not discuss a row until both labels are written.
"""
    INSTRUCTIONS.write_text(text)


def main() -> None:
    if SHEET.exists():
        raise SystemExit(f"{SHEET} already exists")
    used = already_used()
    print(f"excluded keys {len(used)}", flush=True)
    rows, double = draw(used)
    fill_text(rows)
    write_sheet(rows)
    write_instructions(double)
    print(f"wrote {SHEET} rows {len(rows)} double {len(double)}", flush=True)


if __name__ == "__main__":
    main()

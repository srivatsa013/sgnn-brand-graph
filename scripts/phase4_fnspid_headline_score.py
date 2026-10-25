"""Score the same FNSPID pairs again, using the headline only.

The joined headline, summary, and body scores stay in
data/interim/phase3/fnspid_scores. This writes a new parts folder and
its own daily table. The pair is still the Phase 2 link on the joined
text. The model sees the collapsed headline, the same entity string,
and max_length 128. Resumes from parts marked done. Pauses while free
disk is under 6 GB.
"""

from __future__ import annotations

import json
import shutil
import sqlite3
import sys
import time
from pathlib import Path

import pyarrow.parquet as pq
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from phase2_build_series import patterns_from_universe, ticker_nodes  # noqa: E402
from phase3_roberta import load_fresh  # noqa: E402
from phase4_fnspid_pair_count import document_hits, wanted_nodes  # noqa: E402

WEIGHTS = ROOT / "data" / "interim" / "phase3" / "final_scorer" / "model.pt"
DEST = ROOT / "data" / "interim" / "phase3" / "fnspid_scores_headline"
DISK_PAUSE = 6_000_000_000
FORWARD = 2
MAX_LEN = 128
LABELS = ("positive", "negative", "neutral")


def free_bytes() -> int:
    return shutil.disk_usage(ROOT).free


def wait_for_disk(part: str) -> None:
    while free_bytes() < DISK_PAUSE:
        print(f"pause {part}: free disk {free_bytes()} under 6 GB", flush=True)
        time.sleep(30)


def headline_text(headline: str) -> str:
    return " ".join((headline or "").split())


def open_daily() -> sqlite3.Connection:
    DEST.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DEST / "daily.sqlite")
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS daily (
          node TEXT, day TEXT,
          signed_sum REAL, n INT,
          n_positive INT, n_negative INT, n_neutral INT,
          PRIMARY KEY (node, day)
        )
        """
    )
    con.execute("CREATE TABLE IF NOT EXISTS part_done (name TEXT PRIMARY KEY)")
    return con


def main() -> None:
    if not WEIGHTS.exists():
        raise SystemExit("final weights are not saved yet")
    DEST.mkdir(parents=True, exist_ok=True)
    (DEST / "parts").mkdir(exist_ok=True)
    progress_path = DEST / "progress.json"
    nodes, pool = wanted_nodes()
    alias_patterns, _brand_patterns = patterns_from_universe()
    ticker_map = ticker_nodes()
    parts = sorted((ROOT / "data" / "raw" / "fnspid" / "parts").glob("*.parquet"))
    con = open_daily()
    done = {row[0] for row in con.execute("SELECT name FROM part_done")}
    pending = [path for path in parts if path.name not in done]
    print(f"input collapsed headline only max_length {MAX_LEN} entity node string", flush=True)
    print(f"parts {len(parts)} done {len(done)} pending {len(pending)}", flush=True)
    if not pending:
        print("already complete", flush=True)
        return
    wait_for_disk("startup")
    device = torch.device("cpu")
    torch.set_num_threads(4)
    state = torch.load(WEIGHTS, map_location="cpu", weights_only=True)
    model, tokenizer = load_fresh(device, state)
    model.eval()
    scored_total = 0
    started = time.perf_counter()
    for path in pending:
        wait_for_disk(path.name)
        part_path = DEST / "parts" / f"{path.stem}.jsonl"
        if part_path.exists():
            part_path.unlink()
        scored = 0
        with part_path.open("w") as handle, torch.no_grad():
            table = pq.ParquetFile(path)
            batch_rows: list[dict] = []

            def flush_rows() -> None:
                nonlocal scored
                if not batch_rows:
                    return
                encoded = tokenizer(
                    [row["node"] for row in batch_rows],
                    [row["text"] for row in batch_rows],
                    padding=True,
                    truncation=True,
                    max_length=MAX_LEN,
                    return_tensors="pt",
                )
                encoded = {key: value.to(device) for key, value in encoded.items()}
                probs = torch.softmax(model(**encoded).logits, dim=1).tolist()
                for row, prob in zip(batch_rows, probs):
                    scores = {LABELS[i]: prob[i] for i in range(3)}
                    label = LABELS[max(range(3), key=lambda i: prob[i])]
                    handle.write(
                        json.dumps(
                            {
                                "row_id": row["row_id"],
                                "day": row["day"],
                                "node": row["node"],
                                "label": label,
                                "signed": scores["positive"] - scores["negative"],
                                "p_positive": scores["positive"],
                                "p_negative": scores["negative"],
                                "p_neutral": scores["neutral"],
                            }
                        )
                        + "\n"
                    )
                scored += len(batch_rows)
                batch_rows.clear()

            for batch in table.iter_batches(
                batch_size=2000, columns=["row_id", "day_utc", "ticker", "headline", "summary", "text"]
            ):
                data = batch.to_pydict()
                for i, day in enumerate(data["day_utc"]):
                    if not day:
                        continue
                    if free_bytes() < DISK_PAUSE:
                        flush_rows()
                        handle.flush()
                        wait_for_disk(path.name)
                    ticker = (data["ticker"][i] or "").strip().upper()
                    headline = data["headline"][i] or ""
                    summary = data["summary"][i] or ""
                    body = data["text"][i] or ""
                    blob = " ".join(part for part in (headline, summary, body) if part)
                    for node in document_hits(ticker, blob, nodes, pool, ticker_map, alias_patterns):
                        batch_rows.append(
                            {
                                "row_id": data["row_id"][i],
                                "day": day,
                                "node": node,
                                "text": headline_text(headline),
                            }
                        )
                        if len(batch_rows) == FORWARD:
                            flush_rows()
            flush_rows()
        adds: dict[tuple[str, str], list[float]] = {}
        with part_path.open() as handle:
            for line in handle:
                row = json.loads(line)
                cell = adds.get((row["node"], row["day"]))
                if cell is None:
                    cell = [0.0, 0, 0, 0, 0]
                    adds[(row["node"], row["day"])] = cell
                cell[0] += row["signed"]
                cell[1] += 1
                cell[2 + LABELS.index(row["label"])] += 1
        with con:
            for (node, day), cell in adds.items():
                con.execute(
                    """
                    INSERT INTO daily(node, day, signed_sum, n, n_positive, n_negative, n_neutral)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(node, day) DO UPDATE SET
                      signed_sum = signed_sum + excluded.signed_sum,
                      n = n + excluded.n,
                      n_positive = n_positive + excluded.n_positive,
                      n_negative = n_negative + excluded.n_negative,
                      n_neutral = n_neutral + excluded.n_neutral
                    """,
                    (node, day, cell[0], cell[1], cell[2], cell[3], cell[4]),
                )
            con.execute("INSERT INTO part_done(name) VALUES (?)", (path.name,))
        done.add(path.name)
        progress_path.write_text(json.dumps({"done_parts": sorted(done)}, indent=2) + "\n")
        scored_total += scored
        elapsed = time.perf_counter() - started
        print(
            f"{path.name} pairs {scored} total {scored_total} "
            f"{scored_total / max(elapsed, 0.001):.2f} pairs/s free {free_bytes()}",
            flush=True,
        )
    print(f"complete pairs {scored_total}", flush=True)


if __name__ == "__main__":
    main()

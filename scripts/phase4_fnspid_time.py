"""Time the final scorer on 1,000 FNSPID pairs.

Uses the saved final weights. Prints a wall-time estimate for the
counted pair total. Does not start the full run.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from phase3_gate import LABELS  # noqa: E402
from phase3_roberta import load_fresh  # noqa: E402

WEIGHTS = ROOT / "data" / "interim" / "phase3" / "final_scorer" / "model.pt"
SAMPLE = ROOT / "data" / "interim" / "phase3" / "fnspid_timing_pairs.jsonl"
COUNT = ROOT / "eval" / "results" / "phase4_fnspid_pair_count.json"
FORWARD = 2


def main() -> None:
    if not WEIGHTS.exists():
        raise SystemExit("final weights are not saved yet")
    if not SAMPLE.exists() or not COUNT.exists():
        raise SystemExit("pair count is not finished yet")
    rows = [json.loads(line) for line in SAMPLE.read_text().splitlines() if line.strip()]
    if len(rows) != 1000:
        raise SystemExit(f"timing sample has {len(rows)} pairs, expected 1000")
    device = torch.device("cpu")
    torch.set_num_threads(4)
    state = torch.load(WEIGHTS, map_location="cpu", weights_only=True)
    model, tokenizer = load_fresh(device, state)
    model.eval()
    started = time.perf_counter()
    scored = 0
    with torch.no_grad():
        for start in range(0, len(rows), FORWARD):
            chunk = rows[start : start + FORWARD]
            encoded = tokenizer(
                [row["node"] for row in chunk],
                [row["text"] for row in chunk],
                padding=True,
                truncation=True,
                max_length=128,
                return_tensors="pt",
            )
            encoded = {key: value.to(device) for key, value in encoded.items()}
            model(**encoded)
            scored += len(chunk)
    elapsed = time.perf_counter() - started
    total = json.loads(COUNT.read_text())["pairs"]
    hours = (total / scored) * elapsed / 3600
    print(
        json.dumps(
            {
                "timed_pairs": scored,
                "seconds": round(elapsed, 3),
                "pairs_per_second": round(scored / elapsed, 4),
                "counted_pairs": total,
                "estimated_hours": round(hours, 3),
                "forward_batch": FORWARD,
                "labels": list(LABELS),
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()

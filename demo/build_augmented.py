"""Option B. Not run unless --confirm-augmented is passed.

Every output is labeled AUGMENTED and CONTAINS SYNTHETIC DATA.
Real study files are opened read-only and are never replaced.
"""

from __future__ import annotations

import argparse
import json
import random

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from draw_real_graph import Canvas
from guard import ROOT, demo_file

MARK = "AUGMENTED CONTAINS SYNTHETIC DATA"
LABELS = ROOT / "eval" / "results" / "phase5_label_table.parquet"


def real_shift_rows() -> list[dict]:
    """Real rows are the Phase 5 label table. They are read and not rewritten."""
    if not LABELS.exists():
        raise SystemExit("the Phase 5 label table is not written yet")
    rows = []
    for item in pq.read_table(LABELS).to_pylist():
        rows.append(
            {
                "is_synthetic": 0,
                "lambda": None,
                "seed": None,
                "generator_version": None,
                "arm": item["arm"],
                "source": item["source"],
                "ecosystem": item["ecosystem"],
                "event_id": item["event_id"],
                "t0": item["t0"],
                "source_node": item["ecosystem"],
                "target_node": item["neighbor"],
                "edge_class": item["edge_class"],
                "edge_sign": item["edge_sign"],
                "shock_sign": None,
                "noise_sd": None,
                "planted_shift": None,
                "label": item["shift"],
                "is_label": 1,
            }
        )
    return rows


def subset_report(rows: list[dict]) -> dict:
    def block(part: list[dict]) -> dict:
        labels = [float(row["label"]) for row in part if row.get("label") is not None]
        return {
            "n": len(part),
            "n_with_label": len(labels),
            "mean_label": None if not labels else sum(labels) / len(labels),
        }

    real = [row for row in rows if row["is_synthetic"] == 0]
    synthetic = [row for row in rows if row["is_synthetic"] == 1]
    total = len(rows)
    return {
        "real_only": block(real),
        "synthetic_only": block(synthetic),
        "combined": block(rows),
        "synthetic_share": None if total == 0 else len(synthetic) / total,
        "note": "The real-only numbers stay beside the combined numbers. AUGMENTED CONTAINS SYNTHETIC DATA.",
    }


def _watermark(path, share: float) -> None:
    canvas = Canvas(900, 220)
    canvas.text(20, 20, "AUGMENTED", scale=3)
    canvas.text(20, 60, "CONTAINS SYNTHETIC DATA", scale=2)
    canvas.text(20, 100, f"synthetic share {share:.4f}", scale=2)
    canvas.save(path)


def build(lam: float, share: float) -> dict:
    if not 0 < share < 1:
        raise SystemExit("synthetic share must be between 0 and 1")
    real = real_shift_rows()
    table = pq.read_table(demo_file("synthetic/SYNTHETIC_events.parquet"))
    synthetic = table.filter(pc.equal(table["lambda"], lam)).to_pylist()
    if not synthetic:
        raise SystemExit(f"no SYNTHETIC rows at lambda {lam}")
    n_syn = int(round(len(real) * share / (1 - share)))
    n_syn = max(1, min(n_syn, len(synthetic)))
    picked = random.Random(0).sample(synthetic, n_syn)
    for row in picked:
        row["t0"] = str(row["t0"])
    combined = real + picked
    report = subset_report(combined)
    tag = f"lambda{lam}_share{share:.2f}".replace(".", "p")
    stem = f"AUGMENTED_CONTAINS_SYNTHETIC_DATA_{tag}"
    parquet_path = demo_file(f"augmented/{stem}.parquet")
    json_path = demo_file(f"augmented/{stem}_subsets.json")
    figure_path = demo_file(f"augmented/{stem}.png")
    pq.write_table(pa.Table.from_pylist(combined), parquet_path)
    json_path.write_text(json.dumps({"title": MARK, "lambda": lam, **report}, indent=2) + "\n")
    _watermark(figure_path, report["synthetic_share"])
    print(f"synthetic share {report['synthetic_share']:.6f}", flush=True)
    print(MARK, flush=True)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Build an augmented demo table. Refuses to run without --confirm-augmented.")
    parser.add_argument("--confirm-augmented", action="store_true")
    parser.add_argument("--lambda", dest="lam", type=float, default=1.0)
    parser.add_argument("--synthetic-share", type=float, default=0.25)
    args = parser.parse_args()
    if not args.confirm_augmented:
        raise SystemExit("Option B was not run. Pass --confirm-augmented to write AUGMENTED output.")
    build(args.lam, args.synthetic_share)


if __name__ == "__main__":
    main()

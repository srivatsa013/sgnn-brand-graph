"""Run the 14-ecosystem counts after the headline scorer finishes."""

from __future__ import annotations

import sqlite3
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARTS = ROOT / "data" / "raw" / "fnspid" / "parts"
DB = ROOT / "data" / "interim" / "phase3" / "fnspid_scores_headline" / "daily.sqlite"
OUT = ROOT / "eval" / "results" / "phase4_arm_a_headline_counts.json"
PYTHON = ROOT / ".venv" / "bin" / "python"
COUNTS = ROOT / "scripts" / "phase4_arm_a_headline_counts.py"


def ready() -> bool:
    expected = len(list(PARTS.glob("*.parquet")))
    if expected == 0 or not DB.exists():
        return False
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    done = con.execute("SELECT COUNT(*) FROM part_done").fetchone()[0]
    con.close()
    return done == expected


def main() -> None:
    while not ready():
        print("waiting for headline parts", flush=True)
        time.sleep(60)
    if OUT.exists():
        print(f"already wrote {OUT}", flush=True)
        return
    print("headline parts complete; starting counts", flush=True)
    code = subprocess.call([str(PYTHON), str(COUNTS)], cwd=ROOT)
    raise SystemExit(code)


if __name__ == "__main__":
    main()

"""Backoff wrapper for the Wave 2 GDELT loop.

Uses the same waits and the same hard stops as
scripts/phase2_gdelt_supervisor.py. The running watchdog does not call
this file. Nothing starts unless --confirm-wave2 --execute-full is passed.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from phase2_gdelt_supervisor import MAX_TRANSIENT, WAITS, kind  # noqa: E402

LOOP = ROOT / "scripts" / "phase2_gdelt_wave2.py"
STATUS = ROOT / "eval" / "results" / "phase2_gdelt_wave2_supervisor.status"
PYTHON = ROOT / ".venv" / "bin" / "python"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm-wave2", action="store_true")
    parser.add_argument("--execute-full", action="store_true")
    args = parser.parse_args()
    if not args.confirm_wave2 or not args.execute_full:
        print("Wave 2 GDELT supervisor is prepared and not started.", flush=True)
        return
    consecutive = 0
    while True:
        before = STATUS.stat().st_size if STATUS.exists() else 0
        STATUS.parent.mkdir(parents=True, exist_ok=True)
        with STATUS.open("a", encoding="utf-8") as handle:
            handle.write(f"supervisor attempt {consecutive + 1} {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}\n")
            handle.flush()
            proc = subprocess.Popen(
                [str(PYTHON), str(LOOP), "--confirm-wave2", "--execute-full"],
                cwd=ROOT,
                stdout=handle,
                stderr=subprocess.STDOUT,
            )
            print(f"loop pid {proc.pid}", flush=True)
            code = proc.wait()
        added = STATUS.read_text(errors="replace")[before:]
        reason = kind(added)
        print(f"loop exit {code} {reason}", flush=True)
        if code == 0:
            print("supervisor exit 0", flush=True)
            return
        if reason != "transient":
            print(f"stop {reason}", flush=True)
            raise SystemExit(1)
        consecutive += 1
        if consecutive >= MAX_TRANSIENT:
            print(f"stop {MAX_TRANSIENT} consecutive transient failures", flush=True)
            raise SystemExit(1)
        wait = WAITS[min(consecutive - 1, len(WAITS) - 1)]
        print(f"wait {wait} restart {consecutive}", flush=True)
        time.sleep(wait)


if __name__ == "__main__":
    os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    main()

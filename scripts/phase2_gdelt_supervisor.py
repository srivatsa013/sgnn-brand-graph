"""Keep the frozen GDELT loop running across a transient failure.

The loop stays under this process. A DNS failure, timeout, connection
reset, or HTTP 5xx waits and starts the loop again. The waits are 5,
10, 20, then 30 minutes, and the process stops after 12 consecutive
failures. Auth, quota, the 960 GB guard, a dry run above 10 GB, or an
unexpected result shape stops this process immediately.
"""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOOP = ROOT / "scripts" / "phase2_gdelt_frozen_rerun.py"
STATUS = ROOT / "eval" / "results" / "phase2_gdelt_reserve_full.status"
PID = ROOT / "eval" / "results" / "phase2_gdelt_supervisor.pid"
PYTHON = ROOT / ".venv" / "bin" / "python"
WAITS = (300, 600, 1200, 1800)
MAX_TRANSIENT = 12


def kind(text: str) -> str:
    lines = [
        line for line in text.splitlines()
        if "failed twice" in line or "would pass 960" in line or "exceeds 10 GB" in line or line.startswith("refusing")
    ]
    low = (lines[-1] if lines else text).lower()
    if any(marker in low for marker in ("reauthentication", "gcloud auth login", "cannot prompt", "unauthorized", "http error 401", "invalid_grant")):
        return "auth"
    if "quota" in low:
        return "quota"
    if "would pass 960" in low:
        return "960 GB guard"
    if "exceeds 10 gb" in low:
        return "dry run above 10 GB"
    transient = (
        "timeout",
        "timed out",
        "errno 60",
        "connection reset",
        "econnreset",
        "connection aborted",
        "http error 500",
        "http error 502",
        "http error 503",
        "http error 504",
        "name or service not known",
        "nodename nor servname",
        "temporary failure in name resolution",
        "certificate_verify_failed",
        "could not connect",
        "servernotfounderror",
        "unable to find the server",
        "remote end closed",
        "connection refused",
        "errno 8",
        "http error 5",
        "ssl:",
    )
    if any(marker in low for marker in transient):
        return "transient"
    return "unexpected result shape"


def main() -> None:
    PID.write_text(str(os.getpid()) + "\n")
    consecutive = 0
    while True:
        before = STATUS.stat().st_size if STATUS.exists() else 0
        with STATUS.open("a", encoding="utf-8") as handle:
            handle.write(f"supervisor attempt {consecutive + 1} {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}\n")
            handle.flush()
            proc = subprocess.Popen([str(PYTHON), str(LOOP), "--execute-full"], cwd=ROOT, stdout=handle, stderr=subprocess.STDOUT)
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
    main()

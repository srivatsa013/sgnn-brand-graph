"""Wait for the GDELT supervisor, not for an individual loop process.

A restart inside the supervisor leaves this process waiting. It runs the
Arm B rebuild only after the supervisor exits 0 and 128 slice files are
present. It does not treat a restart as a failed rerun.
"""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PID = ROOT / "eval" / "results" / "phase2_gdelt_supervisor.pid"
SUPER = ROOT / "eval" / "results" / "phase2_gdelt_supervisor.status"
SLICES = ROOT / "data" / "interim" / "phase2" / "gdelt_frozen_full"
AFTER = ROOT / "scripts" / "phase2_gdelt_reserve_after.py"
AFTER_LOG = ROOT / "eval" / "results" / "phase2_gdelt_reserve_after.status"
PYTHON = ROOT / ".venv" / "bin" / "python"


def alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def main() -> None:
    while not PID.exists():
        time.sleep(1)
    pid = int(PID.read_text().strip())
    print(f"waiting on supervisor {pid}", flush=True)
    while alive(pid):
        time.sleep(30)
    time.sleep(1)
    text = SUPER.read_text(errors="replace") if SUPER.exists() else ""
    if "supervisor exit 0" not in text.splitlines()[-5:]:
        last = next((line for line in reversed(text.splitlines()) if line.startswith("stop ") or line.startswith("loop exit ")), "supervisor ended")
        print(f"supervisor stopped: {last}", flush=True)
        return
    files = list(SLICES.glob("*.jsonl.gz"))
    if len(files) != 128:
        print(f"supervisor exit 0 with {len(files)} slice files, rebuild not started", flush=True)
        return
    print("supervisor exit 0, 128 slice files, starting the rebuild", flush=True)
    with AFTER_LOG.open("a", encoding="utf-8") as handle:
        proc = subprocess.run([str(PYTHON), str(AFTER)], cwd=ROOT, stdout=handle, stderr=subprocess.STDOUT)
    print(f"rebuild exit {proc.returncode}", flush=True)


if __name__ == "__main__":
    main()

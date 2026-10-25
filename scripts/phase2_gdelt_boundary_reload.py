"""Restart the GDELT supervisor at the next stored-slice boundary.

The current fetch is left alone. After that slice is stored, the loop is
stopped before the next query is submitted, any submitted job id is
pinned, and a new supervisor loads the 12-failure backoff.
"""

from __future__ import annotations

import os
import re
import signal
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATUS = ROOT / "eval" / "results" / "phase2_gdelt_reserve_full.status"
SUPER = ROOT / "eval" / "results" / "phase2_gdelt_supervisor.status"
RERUN = ROOT / "scripts" / "phase2_gdelt_frozen_rerun.py"
SLICES = ROOT / "data" / "interim" / "phase2" / "gdelt_frozen_full"
FLAG = ROOT / "eval" / "results" / "gdelt_boundary.busy"
RESUME = ROOT / "scripts" / "resume_all.sh"
JOB = re.compile(r"sgnn2_frozen_(\d{8})_(\d+)")


def pids(fragment: str) -> list[int]:
    out = subprocess.check_output(["ps", "-ax", "-o", "pid=,command="], text=True)
    found = []
    for line in out.splitlines():
        pid_text, _, command = line.strip().partition(" ")
        if fragment in command and "boundary_reload" not in command and "watchdog" not in command:
            found.append(int(pid_text))
    return found


def alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def pin(day: str, job_id: str) -> None:
    text = RERUN.read_text()
    if job_id in text:
        print(f"already pinned {day} {job_id}", flush=True)
        return
    needle = '    "2021-03-29": "sgnn2_frozen_20210329_1792600858",\n}'
    if needle not in text:
        raise SystemExit("RESUME_JOB block was not found")
    insert = needle[:-2] + f'\n    "{day}": "{job_id}",\n' + "}"
    RERUN.write_text(text.replace(needle, insert, 1))
    print(f"pinned {day} {job_id}", flush=True)


def orphan_jobs(added: str) -> list[tuple[str, str]]:
    found = []
    for match in JOB.finditer(added):
        stamp, job_id = match.group(1), match.group(0)
        day = f"{stamp[:4]}-{stamp[4:6]}-{stamp[6:8]}"
        path = SLICES / f"{day}.jsonl.gz"
        if path.exists() and path.stat().st_size > 0:
            continue
        found.append((day, job_id))
    return found


def main() -> None:
    FLAG.write_text("waiting\n")
    try:
        offset = STATUS.stat().st_size if STATUS.exists() else 0
        print(f"waiting for the next stored line after byte {offset}", flush=True)
        stored_line = ""
        while True:
            time.sleep(0.5)
            if not STATUS.exists():
                continue
            added = STATUS.read_text(errors="replace")[offset:]
            for line in added.splitlines():
                if line.startswith("stored "):
                    stored_line = line
            if stored_line:
                break
        print(f"boundary {stored_line}", flush=True)
        loops = [pid for pid in pids("phase2_gdelt_frozen_rerun.py") if alive(pid)]
        for pid in loops:
            os.kill(pid, signal.SIGTERM)
            print(f"term loop {pid}", flush=True)
        deadline = time.time() + 60
        while loops and time.time() < deadline:
            loops = [pid for pid in loops if alive(pid)]
            time.sleep(0.2)
        if loops:
            raise SystemExit(f"loop still alive {loops}")
        supers = pids("phase2_gdelt_supervisor.py")
        wait_until = time.time() + 30
        while supers and time.time() < wait_until:
            supers = [pid for pid in supers if alive(pid)]
            time.sleep(0.2)
        for pid in supers:
            os.kill(pid, signal.SIGTERM)
            print(f"term supervisor {pid}", flush=True)
        deadline = time.time() + 30
        while supers and time.time() < deadline:
            supers = [pid for pid in supers if alive(pid)]
            time.sleep(0.2)
        added = STATUS.read_text(errors="replace")[offset:]
        for day, job_id in orphan_jobs(added):
            pin(day, job_id)
        waiters = [pid for pid in pids("phase2_gdelt_waiter.py") if alive(pid)]
        for pid in waiters:
            os.kill(pid, signal.SIGTERM)
            print(f"term waiter {pid}", flush=True)
        deadline = time.time() + 30
        while waiters and time.time() < deadline:
            waiters = [pid for pid in waiters if alive(pid)]
            time.sleep(0.2)
        with SUPER.open("a", encoding="utf-8") as handle:
            handle.write(f"boundary reload after {stored_line}\n")
        subprocess.run([str(RESUME), "--only", "gdelt"], cwd=ROOT, check=False)
        subprocess.run([str(RESUME), "--only", "waiter"], cwd=ROOT, check=False)
        print("supervisor reloaded", flush=True)
    finally:
        if FLAG.exists():
            FLAG.unlink()


if __name__ == "__main__":
    main()

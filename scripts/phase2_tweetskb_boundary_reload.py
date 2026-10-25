"""Reload TweetsKB at the next month boundary.

The current month is left running. After its reduce is committed, the
continue process is stopped and started again so the next month uses
the leading-range queue.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATUS = ROOT / "eval" / "results" / "tweetskb_download.status.json"
DONE = ROOT / "eval" / "results" / "tweetskb_stream_done.json"
LOG = ROOT / "eval" / "results" / "tweetskb_continue.status"
FLAG = ROOT / "eval" / "results" / "tweetskb_boundary.busy"
RESUME = ROOT / "scripts" / "resume_all.sh"


def pids() -> list[int]:
    out = subprocess.check_output(["ps", "-ax", "-o", "pid=,command="], text=True)
    found = []
    for line in out.splitlines():
        pid_text, _, command = line.strip().partition(" ")
        if "phase2_tweetskb_continue.py" in command and "boundary_reload" not in command:
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


def reduced(name: str) -> bool:
    if not DONE.exists():
        return False
    files = json.loads(DONE.read_text()).get("files") or []
    return name in files


def main() -> None:
    FLAG.write_text("waiting\n")
    try:
        current = json.loads(STATUS.read_text())["current"]
        print(f"waiting until {current} is reduced", flush=True)
        while not reduced(current):
            time.sleep(2)
        print(f"state saved {current}", flush=True)
        offset = LOG.stat().st_size if LOG.exists() else 0
        while True:
            time.sleep(0.25)
            added = LOG.read_text(errors="replace")[offset:] if LOG.exists() else ""
            if any(line.startswith("download ") and current not in line for line in added.splitlines()):
                break
        targets = [pid for pid in pids() if alive(pid)]
        for pid in targets:
            os.kill(pid, signal.SIGTERM)
            print(f"term continue {pid}", flush=True)
        deadline = time.time() + 60
        while targets and time.time() < deadline:
            targets = [pid for pid in targets if alive(pid)]
            time.sleep(0.2)
        if targets:
            raise SystemExit(f"continue still alive {targets}")
        subprocess.run([str(RESUME), "--only", "tweetskb"], cwd=ROOT, check=False)
        print("tweetskb reloaded", flush=True)
    finally:
        if FLAG.exists():
            FLAG.unlink()


if __name__ == "__main__":
    main()

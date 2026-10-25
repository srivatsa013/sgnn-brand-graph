"""Watch the Wave 2 GDELT supervisor.

A hard stop is written to NEEDS_ME.txt and shown as a macOS
notification. The same notice is repeated every 30 minutes until that
supervisor is running again. This process does not start the supervisor
and does not call BigQuery.
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NEEDS = ROOT / "eval" / "results" / "NEEDS_ME.txt"
STATUS = ROOT / "eval" / "results" / "phase2_gdelt_wave2_supervisor.status"
FRAGMENT = "phase2_gdelt_wave2_supervisor.py"
HARD = ("auth", "quota", "960 gb", "dry run above 10 gb", "unexpected result shape", "unexpected result")
REPEAT = 30 * 60
CHECK = 60


def running() -> bool:
    out = subprocess.check_output(["ps", "-ax", "-o", "command="], text=True)
    return any(
        FRAGMENT in line and "watchdog" not in line
        for line in out.splitlines()
    )


def last_stop() -> str:
    if not STATUS.exists():
        return ""
    lines = [line.strip() for line in STATUS.read_text(errors="replace").splitlines() if line.strip()]
    for line in reversed(lines):
        low = line.lower()
        if low.startswith("stop ") or low.startswith("loop exit ") or low.startswith("supervisor exit"):
            return line
    return ""


def hard(reason: str) -> bool:
    low = reason.lower()
    return any(marker in low for marker in HARD)


def notify(text: str) -> None:
    NEEDS.parent.mkdir(parents=True, exist_ok=True)
    with NEEDS.open("a", encoding="utf-8") as handle:
        handle.write(f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} {text}\n")
    safe = text.replace('"', "'")
    subprocess.run(
        ["osascript", "-e", f'display notification "{safe}" with title "sgnn-csp"'],
        check=False,
    )
    print(f"needs me {text}", flush=True)


def main() -> None:
    last_notified = 0.0
    while True:
        up = running()
        reason = last_stop()
        if up:
            last_notified = 0.0
        elif hard(reason) and (last_notified == 0.0 or time.time() - last_notified >= REPEAT):
            notify(f"Wave 2 GDELT supervisor stopped: {reason}")
            last_notified = time.time()
        time.sleep(CHECK)


if __name__ == "__main__":
    main()

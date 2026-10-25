"""Restart a stopped job when the stop was transient.

Checks every 10 minutes. A hard stop is written to NEEDS_ME.txt and
shown as a macOS notification. A finished job is left stopped.
"""

from __future__ import annotations

import json
import sqlite3
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NEEDS = ROOT / "eval" / "results" / "NEEDS_ME.txt"
RESUME = ROOT / "scripts" / "resume_all.sh"
GDELT_FLAG = ROOT / "eval" / "results" / "gdelt_boundary.busy"
TWEET_FLAG = ROOT / "eval" / "results" / "tweetskb_boundary.busy"
HEADLINE_DB = ROOT / "data" / "interim" / "phase3" / "fnspid_scores_headline" / "daily.sqlite"
HEADLINE_PARTS = ROOT / "data" / "raw" / "fnspid" / "parts"
COUNTS_OUT = ROOT / "eval" / "results" / "phase4_arm_a_counts_both.json"
HARD = ("auth", "quota", "960 gb", "dry run above 10 gb", "unexpected result shape", "unexpected result")


def running(fragment: str) -> bool:
    out = subprocess.check_output(["ps", "-ax", "-o", "command="], text=True)
    return any(fragment in line and "watchdog" not in line and "boundary_reload" not in line for line in out.splitlines())


def last_stop(path: Path) -> str:
    if not path.exists():
        return ""
    lines = [line.strip() for line in path.read_text(errors="replace").splitlines() if line.strip()]
    for line in reversed(lines):
        low = line.lower()
        if low.startswith("stop ") or low.startswith("loop exit ") or low.startswith("supervisor exit"):
            return line
    return ""


def hard(reason: str) -> bool:
    low = reason.lower()
    return any(marker in low for marker in HARD)


def finished_ok(reason: str) -> bool:
    return reason.lower().startswith("supervisor exit 0")


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


def resume(name: str) -> None:
    print(f"restart {name}", flush=True)
    subprocess.run([str(RESUME), "--only", name], cwd=ROOT, check=False)


def headline_done() -> bool:
    expected = len(list(HEADLINE_PARTS.glob("*.parquet")))
    if expected == 0 or not HEADLINE_DB.exists():
        return False
    con = sqlite3.connect(f"file:{HEADLINE_DB}?mode=ro", uri=True)
    try:
        done = con.execute("SELECT COUNT(*) FROM part_done").fetchone()[0]
    except sqlite3.OperationalError:
        return False
    finally:
        con.close()
    return done == expected


def tweets_done() -> bool:
    path = ROOT / "eval" / "results" / "tweetskb_continue.status"
    if not path.exists():
        return False
    lines = path.read_text(errors="replace").splitlines()
    return bool(lines) and lines[-1].strip() == "months finished"


def check() -> None:
    if not GDELT_FLAG.exists():
        reason = last_stop(ROOT / "eval" / "results" / "phase2_gdelt_supervisor.status")
        up = running("phase2_gdelt_supervisor.py")
        if not up and hard(reason):
            notify(f"GDELT supervisor stopped: {reason}")
        elif not up and not finished_ok(reason):
            resume("gdelt")
            resume("waiter")
        elif up and not running("phase2_gdelt_waiter.py"):
            resume("waiter")
    if not TWEET_FLAG.exists() and not running("phase2_tweetskb_continue.py") and not tweets_done():
        reason = last_stop(ROOT / "eval" / "results" / "tweetskb_continue.status")
        if hard(reason):
            notify(f"TweetsKB stopped: {reason}")
        else:
            resume("tweetskb")
    if not headline_done() and not running("phase4_fnspid_headline_score.py"):
        reason = last_stop(ROOT / "eval" / "results" / "phase4_fnspid_headline_score.status")
        if hard(reason):
            notify(f"FNSPID headline scorer stopped: {reason}")
        else:
            resume("headline")
    if not COUNTS_OUT.exists() and not headline_done() and not running("phase4_headline_counts_waiter.py"):
        resume("counts")
    elif headline_done() and not COUNTS_OUT.exists() and not running("phase4_headline_counts_waiter.py"):
        resume("counts")


def main() -> None:
    while True:
        check()
        time.sleep(600)


if __name__ == "__main__":
    main()

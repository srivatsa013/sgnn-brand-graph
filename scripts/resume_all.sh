#!/bin/bash
# Relaunch the stopped jobs in their own session.
# A new session is not in this shell's process group, so closing the
# terminal or Cursor does not signal them. Starts nothing when passed --check.
# Does not log in to gcloud. Refuses to start a job that is already running.

set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PY="$ROOT/.venv/bin/python"
PIDFILE="$ROOT/eval/results/phase2_gdelt_supervisor.pid"
CHECK=0
ONLY=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --check) CHECK=1 ;;
    --only)
      ONLY="${2:-}"
      if [[ -z "$ONLY" ]]; then
        echo "usage: scripts/resume_all.sh [--check] [--only name]" >&2
        exit 2
      fi
      shift
      ;;
    *)
      echo "usage: scripts/resume_all.sh [--check] [--only name]" >&2
      exit 2
      ;;
  esac
  shift
done

want() {
  [[ -z "$ONLY" || "$ONLY" == "$1" ]]
}

refuse=0

busy() {
  pgrep -f "$1" >/dev/null 2>&1
}

launch() {
  local name="$1"
  local pattern="$2"
  local log="$3"
  shift 3
  if busy "$pattern"; then
    echo "REFUSE $name: a copy is already running"
    refuse=1
    return
  fi
  if [[ "$CHECK" -eq 1 ]]; then
    echo "WOULD START $name"
    echo "  setsid caffeinate -i $PY $*"
    echo "  log: $log"
    return
  fi
  mkdir -p "$(dirname "$log")"
  local pid
  pid="$("$PY" -c '
import os, sys
log = sys.argv[1]
cmd = sys.argv[2:]
pid = os.fork()
if pid > 0:
    print(pid)
    raise SystemExit(0)
os.setsid()
out = os.open(log, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
os.dup2(out, 1)
os.dup2(out, 2)
inn = os.open("/dev/null", os.O_RDONLY)
os.dup2(inn, 0)
os.execvp("caffeinate", ["caffeinate", "-i", *cmd])
' "$log" "$PY" "$@")"
  echo "STARTED $name pid $pid log $log"
}

if want fnspid; then
  launch "FNSPID scorer" "scripts/phase4_fnspid_score.py" \
    "eval/results/phase4_fnspid_score.status" \
    scripts/phase4_fnspid_score.py
fi

if want headline; then
  launch "FNSPID headline scorer" "scripts/phase4_fnspid_headline_score.py" \
    "eval/results/phase4_fnspid_headline_score.status" \
    scripts/phase4_fnspid_headline_score.py
fi

if want tweetskb; then
  launch "TweetsKB continue" "scripts/phase2_tweetskb_continue.py" \
    "eval/results/tweetskb_continue.status" \
    scripts/phase2_tweetskb_continue.py
fi

before_pid=""
if [[ -f "$PIDFILE" ]]; then
  before_pid="$(cat "$PIDFILE")"
fi
gdelt_launched=0
if want gdelt; then
  if ! busy "scripts/phase2_gdelt_supervisor.py"; then
    gdelt_launched=1
  fi
  launch "GDELT supervisor" "scripts/phase2_gdelt_supervisor.py" \
    "eval/results/phase2_gdelt_supervisor.status" \
    scripts/phase2_gdelt_supervisor.py
  echo "  2021-01-04 pinned to sgnn2_frozen_20210104_1792577922"
  echo "  2021-03-01 pinned to sgnn2_frozen_20210301_1792600287"
  echo "  2021-03-29 pinned to sgnn2_frozen_20210329_1792600858"
fi

block_waiter=0
if [[ "$CHECK" -eq 0 && "$gdelt_launched" -eq 1 ]]; then
  now_pid="$before_pid"
  for _ in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do
    if [[ -f "$PIDFILE" ]]; then
      now_pid="$(cat "$PIDFILE")"
    fi
    if [[ -n "$now_pid" && "$now_pid" != "$before_pid" ]]; then
      break
    fi
    sleep 0.25
  done
  if [[ -z "$now_pid" || "$now_pid" == "$before_pid" ]]; then
    echo "REFUSE GDELT waiter: the supervisor did not write a new pid"
    refuse=1
    block_waiter=1
  fi
fi

if [[ "$block_waiter" -eq 0 && ( -z "$ONLY" || "$ONLY" == "waiter" ) ]]; then
  launch "GDELT waiter" "scripts/phase2_gdelt_waiter.py" \
    "eval/results/phase2_gdelt_waiter.status" \
    scripts/phase2_gdelt_waiter.py
  echo "  waiter follows eval/results/phase2_gdelt_supervisor.pid"
fi

if want counts; then
  launch "headline counts waiter" "scripts/phase4_headline_counts_waiter.py" \
    "eval/results/phase4_headline_counts_waiter.status" \
    scripts/phase4_headline_counts_waiter.py
fi

if [[ "$CHECK" -eq 1 ]]; then
  echo "started nothing"
fi
exit "$refuse"

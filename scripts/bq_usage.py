"""BigQuery jobs with a recorded byte count and a hard monthly stop.

The October 2026 baseline is the sum of totalBytesBilled from `bq ls -j`
on 2026-10-14. A later job is refused when the baseline plus the ledger
plus that job's dry run would pass 1,000,000,000,000 bytes, or when the
dry run itself is above 10 GB.
"""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "eval" / "results" / "bq_ledger.jsonl"
PROJECT = "sgnn-csp"
# Conservative reading of the sandbox allowance: 1 TB, not 1 TiB.
MONTH_CAP = 1_000_000_000_000
QUERY_CAP = 10 * 10**9
# Filled in by the history script if the billed total differs. Processed
# bytes on 2026-10-14 were 929,202,553,187 across 130 jobs.
OCTOBER_BILLED_BASELINE = 929_292_091_392


def _append(row: dict) -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row) + "\n")


def ledger_bytes() -> int:
    if not LEDGER.exists():
        return 0
    total = 0
    for line in LEDGER.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("executed"):
            total += int(row.get("bytes_processed") or 0)
    return total


def month_used() -> int:
    return OCTOBER_BILLED_BASELINE + ledger_bytes()


def _bq(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["bq", *args], text=True, capture_output=True)


def dry_run_bytes(query: str) -> int:
    proc = _bq(
        [
            "query",
            f"--project_id={PROJECT}",
            "--use_legacy_sql=false",
            "--format=json",
            "--dry_run",
            query,
        ]
    )
    if proc.returncode != 0:
        raise SystemExit((proc.stderr or proc.stdout)[-2000:])
    data = json.loads(proc.stdout)
    return int(data["statistics"]["query"]["totalBytesProcessed"])


def run_query(query: str, purpose: str, execute: bool) -> tuple[list | dict, int]:
    """Dry-run first. Execute only when the stop allows it."""
    estimated = dry_run_bytes(query)
    used = month_used()
    _append(
        {
            "purpose": purpose,
            "executed": False,
            "dry_run_bytes": estimated,
            "project_id": PROJECT,
            "month_used_before": used,
            "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
    )
    if estimated > QUERY_CAP:
        raise SystemExit(f"{purpose} dry run {estimated} bytes exceeds 10 GB")
    if used + estimated > MONTH_CAP:
        raise SystemExit(
            f"{purpose} dry run {estimated} would pass the 1 TB stop "
            f"(month used {used})"
        )
    if not execute:
        return {}, estimated
    job_id = f"sgnn_{purpose}_{int(time.time())}"
    proc = _bq(
        [
            "query",
            f"--project_id={PROJECT}",
            "--use_legacy_sql=false",
            "--format=json",
            "--max_rows=100000",
            f"--job_id={job_id}",
            query,
        ]
    )
    if proc.returncode != 0:
        raise SystemExit(proc.stderr[-2000:])
    shown = _bq(["show", "-j", "--format=json", f"--project_id={PROJECT}", job_id])
    if shown.returncode != 0:
        raise SystemExit(shown.stderr[-2000:])
    stats = json.loads(shown.stdout)["statistics"]["query"]
    processed = int(stats.get("totalBytesProcessed") or 0)
    billed = int(stats.get("totalBytesBilled") or 0)
    _append(
        {
            "purpose": purpose,
            "executed": True,
            "job_id": job_id,
            "project_id": PROJECT,
            "bytes_processed": processed,
            "bytes_billed": billed,
            "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
    )
    payload = json.loads(proc.stdout) if proc.stdout.strip() else []
    return payload, processed

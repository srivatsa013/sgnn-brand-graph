"""Run the allow-list GDELT scan on sgnn-csp-2 only.

Each 28-day slice is dry-run first. A slice above 10 GB is refused.
This project's billed bytes stop at 1 TB. The October sgnn-csp baseline
is not applied here. Results are one gzip jsonl file per slice.
"""

from __future__ import annotations

import gzip
import json
import shutil
import subprocess
import time
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOW = ROOT / "configs" / "scan_allowlist.json"
LEDGER = ROOT / "eval" / "results" / "bq_ledger.jsonl"
OUT_DIR = ROOT / "data" / "interim" / "phase2" / "gdelt_allowlist"
PROGRESS = ROOT / "eval" / "results" / "phase2_gdelt_allowlist_progress.json"
PROJECT = "sgnn-csp-2"
MONTH_CAP = 1_000_000_000_000
QUERY_CAP = 10 * 10**9
RESULT_CAP = 10 * 1024**3
START = date(2016, 11, 14)
END = date(2026, 8, 15)
SLICE_DAYS = 28


def account() -> str:
    proc = subprocess.run(
        ["gcloud", "config", "get-value", "account"],
        text=True,
        capture_output=True,
    )
    return (proc.stdout or "").strip()


def project_billed() -> int:
    if not LEDGER.exists():
        return 0
    total = 0
    for line in LEDGER.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("executed") and row.get("project_id") == PROJECT:
            total += int(row.get("bytes_billed") or row.get("bytes_processed") or 0)
    return total


def append(row: dict) -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row) + "\n")


def bq(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["bq", *args], text=True, capture_output=True)


def sql(titles: list[str], mids: list[str], start: date, end: date) -> str:
    def quote(value: str) -> str:
        return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"

    title_list = ", ".join(quote(title) for title in titles)
    mid_list = ", ".join(quote(mid) for mid in mids)
    mid_clause = f"OR ent.mid IN ({mid_list})" if mids else ""
    return f"""
SELECT
  DATE(date) AS day,
  ANY_VALUE(lang) AS lang,
  CAST(FARM_FINGERPRINT(url) AS STRING) AS url_hash,
  ANY_VALUE(score) AS score,
  ARRAY_AGG(STRUCT(
    REPLACE(REGEXP_REPLACE(ent.wikipediaUrl, r'^https?://[^/]+/wiki/', ''), ' ', '_') AS wiki,
    ent.mid AS mid
  )) AS entities
FROM `gdelt-bq.gdeltv2.geg_gcnlapi`,
UNNEST(entities) AS ent
WHERE date >= TIMESTAMP('{start.isoformat()}')
  AND date < TIMESTAMP('{end.isoformat()}')
  AND lang = 'en'
  AND (
    REPLACE(REGEXP_REPLACE(ent.wikipediaUrl, r'^https?://[^/]+/wiki/', ''), ' ', '_') IN ({title_list})
    {mid_clause}
  )
GROUP BY day, url_hash
""".strip()


def allow_lists() -> tuple[list[str], list[str]]:
    allow = json.loads(ALLOW.read_text())
    titles = sorted(
        {
            row["enwiki"].replace(" ", "_")
            for row in allow["nodes"]
            if row.get("enwiki") and row.get("role") != "control"
        }
    )
    mids = sorted({mid for row in allow["nodes"] for mid in (row.get("mids") or []) if mid})
    return titles, mids


def dry_run_bytes(query: str) -> int:
    proc = bq(
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


def slices():
    cursor = START
    index = 1
    while cursor < END:
        end = min(cursor + timedelta(days=SLICE_DAYS), END)
        yield index, cursor, end
        cursor = end
        index += 1


def main() -> None:
    who = account()
    active = subprocess.run(
        ["gcloud", "config", "get-value", "project"],
        text=True,
        capture_output=True,
    ).stdout.strip()
    if active != PROJECT:
        raise SystemExit(f"active project is {active}, refusing to run outside {PROJECT}")
    titles, mids = allow_lists()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    done = []
    result_bytes = 0
    for index, start, end in slices():
        path = OUT_DIR / f"{start.isoformat()}.jsonl.gz"
        if path.exists() and path.stat().st_size > 0:
            result_bytes += path.stat().st_size
            done.append(start.isoformat())
            print(f"skip {start.isoformat()} bytes {path.stat().st_size}", flush=True)
            continue
        free = shutil.disk_usage(OUT_DIR).free
        if free < 4 * 1024**3:
            raise SystemExit(f"stopping at {start.isoformat()}: {free} bytes free")
        query = sql(titles, mids, start, end)
        estimated = dry_run_bytes(query)
        used = project_billed()
        append(
            {
                "purpose": f"gdelt_allowlist_{start.isoformat()}",
                "executed": False,
                "project_id": PROJECT,
                "account": who,
                "dry_run_bytes": estimated,
                "month_used_before": used,
                "slice_index": index,
                "slice_start": start.isoformat(),
                "slice_end_exclusive": end.isoformat(),
                "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
        )
        print(
            f"slice {index} {start.isoformat()} dry_run {estimated} used {used}",
            flush=True,
        )
        if estimated > QUERY_CAP:
            raise SystemExit(f"{start.isoformat()} dry run {estimated} exceeds 10 GB")
        if used + estimated > MONTH_CAP:
            raise SystemExit(f"{start.isoformat()} would pass 1 TB on {PROJECT}")
        job_id = f"sgnn2_gdelt_{start.strftime('%Y%m%d')}_{int(time.time())}"
        proc = bq(
            [
                "query",
                f"--project_id={PROJECT}",
                "--use_legacy_sql=false",
                "--format=json",
                "--max_rows=5000000",
                f"--job_id={job_id}",
                query,
            ]
        )
        if proc.returncode != 0:
            raise SystemExit((proc.stderr or proc.stdout)[-2000:])
        if "truncated" in (proc.stderr or "").lower():
            raise SystemExit(f"{start.isoformat()} result truncated at 5000000 rows")
        shown = bq(["show", "-j", "--format=json", f"--project_id={PROJECT}", job_id])
        if shown.returncode != 0:
            raise SystemExit(shown.stderr[-2000:])
        stats = json.loads(shown.stdout)["statistics"]["query"]
        processed = int(stats.get("totalBytesProcessed") or 0)
        billed = int(stats.get("totalBytesBilled") or 0)
        rows = json.loads(proc.stdout) if proc.stdout.strip() else []
        with gzip.open(path, "wt", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, separators=(",", ":")) + "\n")
        size = path.stat().st_size
        result_bytes += size
        append(
            {
                "purpose": f"gdelt_allowlist_{start.isoformat()}",
                "executed": True,
                "project_id": PROJECT,
                "account": who,
                "job_id": job_id,
                "bytes_processed": processed,
                "bytes_billed": billed,
                "result_rows": len(rows),
                "result_gzip_bytes": size,
                "slice_index": index,
                "slice_start": start.isoformat(),
                "slice_end_exclusive": end.isoformat(),
                "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
        )
        done.append(start.isoformat())
        print(
            f"stored {start.isoformat()} rows {len(rows)} gzip {size} billed {billed}",
            flush=True,
        )
        if result_bytes > RESULT_CAP:
            raise SystemExit(f"result files passed 10 GB at {start.isoformat()}")
    PROGRESS.write_text(
        json.dumps(
            {
                "project_id": PROJECT,
                "account": who,
                "slices_stored": done,
                "result_gzip_bytes": result_bytes,
                "finished": len(done) == 128,
            },
            indent=2,
        )
    )
    print("finished", len(done), "gzip_bytes", result_bytes, flush=True)


if __name__ == "__main__":
    main()

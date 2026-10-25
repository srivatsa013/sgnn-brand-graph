"""Frozen-allow-list GDELT rerun on sgnn-csp-2.

Dry-run first. A slice above 10 GB is refused. This file's full loop does
not run unless --execute-full is passed. The default action is the
three-day pilot: 2016-11-14, 2020-03-16, and 2025-06-16.
"""

from __future__ import annotations

import argparse
import gzip
import json
import shutil
import subprocess
import time
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOW = ROOT / "configs" / "gdelt_frozen_allowlist.json"
LEDGER = ROOT / "eval" / "results" / "bq_ledger.jsonl"
PILOT_DIR = ROOT / "data" / "interim" / "phase2" / "gdelt_reserve_pilot"
FULL_DIR = ROOT / "data" / "interim" / "phase2" / "gdelt_frozen_full"
PROJECT = "sgnn-csp-2"
MONTH_CAP = 960_000_000_000
QUERY_CAP = 10 * 10**9
SLICE_TIMEOUT = 20 * 60
# Attach these finished or in-flight jobs by id. Do not submit a second
# query for either slice. Only 2020-04-27 may fall through to one
# replacement, and only after its attach fails twice.
RESUME_JOB = {
    "2020-04-27": "sgnn2_frozen_20200427_1792535531",
    "2021-01-04": "sgnn2_frozen_20210104_1792577922",
    # DONE and being fetched when the loop was detached. Attach this id.
    "2021-03-01": "sgnn2_frozen_20210301_1792600287",
    # Submitted, then the status read failed on TLS. Attach this id.
    "2021-03-29": "sgnn2_frozen_20210329_1792600858",
    # Submitted, then the token refresh returned 401. Attach this id.
    "2024-12-02": "sgnn2_frozen_20241202_1792655471",
}
FIRST_RUN_BILLED = 2_661_285_888
START = date(2016, 11, 14)
END = date(2026, 8, 15)
SLICE_DAYS = 28
PILOT_DAYS = (date(2016, 11, 14), date(2020, 3, 16), date(2022, 6, 15), date(2025, 9, 16))


def account() -> str:
    proc = subprocess.run(["gcloud", "config", "get-value", "account"], text=True, capture_output=True)
    return (proc.stdout or "").strip()


def active_project() -> str:
    proc = subprocess.run(["gcloud", "config", "get-value", "project"], text=True, capture_output=True)
    return (proc.stdout or "").strip()


def project_billed() -> int:
    if not LEDGER.exists():
        return 0
    total = 0
    for line in LEDGER.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("project_id") != PROJECT:
            continue
        if row.get("executed"):
            total += int(row.get("bytes_billed") or row.get("bytes_processed") or 0)
        total += int(row.get("bytes_billed_not_stored") or 0)
    return total


def append(row: dict) -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row) + "\n")


def bq(args: list[str], label: str, deadline: float) -> subprocess.CompletedProcess[str]:
    proc = subprocess.Popen(["bq", *args], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    last = 0.0
    started = deadline - SLICE_TIMEOUT
    while True:
        try:
            out, err = proc.communicate(timeout=20)
            return subprocess.CompletedProcess(["bq", *args], proc.returncode or 0, out, err)
        except subprocess.TimeoutExpired:
            now = time.time()
            if now - last >= 60:
                print(f"heartbeat {label} elapsed {int(now - started)}", flush=True)
                last = now
            if now >= deadline:
                proc.kill()
                proc.communicate()
                raise TimeoutError(label)


def sql(titles: list[str], mids: list[str], start: date, end: date) -> str:
    def quote(value: str) -> str:
        return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"

    title_list = ", ".join(quote(title) for title in titles)
    mid_list = ", ".join(quote(mid) for mid in mids)
    mid_clause = f"OR ent.mid IN ({mid_list})" if mids else ""
    return f"""
SELECT
  DATE(date) AS day,
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
    titles = sorted({title for row in allow["entities"] for title in row.get("titles") or [] if title})
    mids = sorted({mid for row in allow["entities"] for mid in row.get("mids") or [] if mid})
    return titles, mids


def dry_run_bytes(query: str, label: str, deadline: float) -> int:
    proc = bq(
        ["query", f"--project_id={PROJECT}", "--use_legacy_sql=false", "--format=json", "--dry_run", query],
        label,
        deadline,
    )
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout)[-2000:])
    data = json.loads(proc.stdout)
    return int(data["statistics"]["query"]["totalBytesProcessed"])


def job_info(job_id: str, label: str, deadline: float) -> dict | None:
    proc = bq(["show", "-j", "--format=json", f"--project_id={PROJECT}", job_id], label, deadline)
    if proc.returncode != 0:
        text = (proc.stderr or "") + (proc.stdout or "")
        if "Not found" in text or "not found" in text:
            return None
        raise RuntimeError(text[-2000:])
    return json.loads(proc.stdout)


def decode_row(raw: dict) -> dict:
    cells = raw["f"]
    packed = cells[3]["v"] or []
    entities = []
    for item in packed:
        fields = item["v"]["f"]
        entities.append({"mid": fields[1]["v"], "wiki": fields[0]["v"]})
    return {"day": cells[0]["v"], "entities": entities, "score": cells[2]["v"], "url_hash": cells[1]["v"]}


def fetch_results(job_id: str, dest: Path, label: str, deadline: float) -> int:
    token = subprocess.check_output(["gcloud", "auth", "print-access-token"], text=True).strip()
    partial = dest.with_name(dest.name + ".partial")
    if partial.exists():
        partial.unlink()
    url = f"https://bigquery.googleapis.com/bigquery/v2/projects/{PROJECT}/queries/{job_id}"
    page = None
    count = 0
    last = 0.0
    started = deadline - SLICE_TIMEOUT
    try:
        with gzip.open(partial, "wt", encoding="utf-8") as handle:
            while True:
                now = time.time()
                if now >= deadline:
                    raise TimeoutError(label)
                if now - last >= 60:
                    print(f"heartbeat {label} rows {count} elapsed {int(now - started)}", flush=True)
                    last = now
                params = {"maxResults": "2000", "location": "US"}
                if page:
                    params["pageToken"] = page
                request = urllib.request.Request(
                    url + "?" + urllib.parse.urlencode(params),
                    headers={"Authorization": f"Bearer {token}"},
                )
                with urllib.request.urlopen(request, timeout=120) as response:
                    payload = json.loads(response.read().decode())
                if not payload.get("jobComplete", True):
                    time.sleep(15)
                    continue
                for raw in payload.get("rows") or []:
                    handle.write(json.dumps(decode_row(raw), separators=(",", ":")) + "\n")
                    count += 1
                page = payload.get("pageToken")
                if not page:
                    break
    except Exception:
        if partial.exists():
            partial.unlink()
        raise
    partial.replace(dest)
    return count


def submit_job(job_id: str, query: str, label: str, deadline: float) -> None:
    proc = bq(
        [
            "--nosynchronous_mode",
            "query",
            f"--project_id={PROJECT}",
            "--use_legacy_sql=false",
            "--format=json",
            f"--job_id={job_id}",
            query,
        ],
        label,
        deadline,
    )
    if proc.returncode == 0:
        return
    text = (proc.stderr or "") + (proc.stdout or "")
    if "Already Exists" in text or "already exists" in text:
        return
    raise RuntimeError(text[-2000:])


def wait_done(job_id: str, label: str, deadline: float) -> dict:
    while True:
        info = job_info(job_id, label, deadline)
        if info is None:
            raise RuntimeError(f"{job_id} is not in BigQuery")
        state = info["status"]["state"]
        if state == "DONE":
            error = info["status"].get("errorResult")
            if error:
                raise RuntimeError(json.dumps(error))
            return info
        if time.time() >= deadline:
            raise TimeoutError(label)
        time.sleep(20)


def store_job(job_id: str, dest: Path, label: str, deadline: float, submit: bool, query: str) -> dict:
    if submit:
        submit_job(job_id, query, label + " submit", deadline)
    info = wait_done(job_id, label + " wait", deadline)
    rows = fetch_results(job_id, dest, label + " fetch", deadline)
    stats = info["statistics"]["query"]
    return {
        "job_id": job_id,
        "rows": rows,
        "bytes_processed": int(stats.get("totalBytesProcessed") or 0),
        "bytes_billed": int(stats.get("totalBytesBilled") or 0),
    }


def full_slices():
    cursor = START
    index = 1
    while cursor < END:
        end = min(cursor + timedelta(days=SLICE_DAYS), END)
        yield index, cursor, end
        cursor = end
        index += 1


def run_one(
    index: int,
    start: date,
    end: date,
    titles: list[str],
    mids: list[str],
    who: str,
    execute: bool,
    out_dir: Path,
) -> dict:
    path = out_dir / f"{start.isoformat()}.jsonl.gz"
    if execute and path.exists() and path.stat().st_size > 0:
        print(f"skip {start.isoformat()} bytes {path.stat().st_size}", flush=True)
        return {"slice_start": start.isoformat(), "skipped": True, "result_gzip_bytes": path.stat().st_size}
    query = sql(titles, mids, start, end)
    label = start.isoformat()
    try:
        estimated = dry_run_bytes(query, label + " dry_run", time.time() + SLICE_TIMEOUT)
    except (TimeoutError, RuntimeError) as first:
        print(f"retry {label} dry_run after {first}", flush=True)
        try:
            estimated = dry_run_bytes(query, label + " dry_run", time.time() + SLICE_TIMEOUT)
        except (TimeoutError, RuntimeError) as second:
            raise SystemExit(f"{label} dry run failed twice: {second}") from second
    used = project_billed()
    row = {
        "purpose": f"gdelt_frozen_{start.isoformat()}",
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
    append(row)
    print(f"dry_run {start.isoformat()} {estimated} used {used}", flush=True)
    if estimated > QUERY_CAP:
        raise SystemExit(f"{start.isoformat()} dry run {estimated} exceeds 10 GB")
    if not execute:
        return row
    out_dir.mkdir(parents=True, exist_ok=True)
    known = RESUME_JOB.get(start.isoformat())
    if known is None and used + estimated > MONTH_CAP:
        raise SystemExit(f"{start.isoformat()} would pass 960 GB on {PROJECT}")
    if known is None:
        job_id = f"sgnn2_frozen_{start.strftime('%Y%m%d')}_{int(time.time())}"
        submit = True
    else:
        job_id = known
        submit = False

    def once(active_id: str, do_submit: bool) -> dict:
        attempt_deadline = time.time() + SLICE_TIMEOUT
        return store_job(active_id, path, label, attempt_deadline, do_submit, query)

    try:
        stored = once(job_id, submit)
    except (TimeoutError, RuntimeError, OSError) as first:
        print(f"retry {label} attach {job_id} after {first}", flush=True)
        try:
            stored = once(job_id, False)
        except (TimeoutError, RuntimeError, OSError) as second:
            if start.isoformat() != "2020-04-27":
                raise SystemExit(f"{label} failed twice: {second}") from second
            append(
                {
                    "purpose": f"gdelt_frozen_{label}",
                    "executed": False,
                    "project_id": PROJECT,
                    "account": who,
                    "job_id": known,
                    "bytes_billed_not_stored": FIRST_RUN_BILLED,
                    "note": "The finished job could not be read. The first run billed 2661285888 bytes. One replacement query follows.",
                    "slice_index": index,
                    "slice_start": label,
                    "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                }
            )
            if project_billed() + estimated > MONTH_CAP:
                raise SystemExit(f"{label} replacement would pass 960 GB") from second
            job_id = f"sgnn2_frozen_{start.strftime('%Y%m%d')}_{int(time.time())}"
            print(f"rerun {label} job {job_id}", flush=True)
            try:
                stored = once(job_id, True)
            except (TimeoutError, RuntimeError, OSError) as third:
                print(f"retry {label} attach {job_id} after {third}", flush=True)
                try:
                    stored = once(job_id, False)
                except (TimeoutError, RuntimeError, OSError) as fourth:
                    raise SystemExit(f"{label} failed twice: {fourth}") from fourth
    done = {
        "purpose": f"gdelt_frozen_{label}",
        "executed": True,
        "project_id": PROJECT,
        "account": who,
        "job_id": stored["job_id"],
        "bytes_processed": stored["bytes_processed"],
        "bytes_billed": stored["bytes_billed"],
        "result_rows": stored["rows"],
        "result_gzip_bytes": path.stat().st_size,
        "slice_index": index,
        "slice_start": label,
        "slice_end_exclusive": end.isoformat(),
        "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    append(done)
    print(f"stored {label} rows {stored['rows']} billed {done['bytes_billed']}", flush=True)
    return done


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pilot", action="store_true")
    parser.add_argument("--execute-pilot", action="store_true")
    parser.add_argument("--execute-full", action="store_true")
    parser.add_argument("--dry-run-first-slice", action="store_true")
    args = parser.parse_args()
    who = account()
    if active_project() != PROJECT:
        raise SystemExit(f"active project is {active_project()}, refusing to run outside {PROJECT}")
    titles, mids = allow_lists()
    print(f"titles {len(titles)} mids {len(mids)} account {who}", flush=True)
    if args.dry_run_first_slice:
        run_one(1, START, START + timedelta(days=SLICE_DAYS), titles, mids, who, False, FULL_DIR)
    if args.pilot:
        for index, day in enumerate(PILOT_DAYS, start=1):
            run_one(index, day, day + timedelta(days=1), titles, mids, who, args.execute_pilot, PILOT_DIR)
        return
    slices = list(full_slices())
    print(f"full loop would run {len(slices)} slices from {FULL_DIR}")
    print("stop: dry run above 10 GB, or projected bytes on sgnn-csp-2 above 960 GB")
    print("timeout: 20 minutes per slice, one attach retry, then stop")
    print("resume: a non-empty slice file is skipped")
    if not args.execute_full:
        raise SystemExit("full loop not started")
    free = shutil.disk_usage(ROOT).free
    if free < 4 * 1024**3:
        raise SystemExit(f"refusing full loop, {free} bytes free")
    for index, start, end in slices:
        run_one(index, start, end, titles, mids, who, True, FULL_DIR)


if __name__ == "__main__":
    main()

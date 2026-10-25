"""Stream StockTwits message metadata and bodies for the retained tickers.

The full feature and message directories are not stored. Resume is per
completed source file. Message clocks come from feature_wo_messages,
which carries a UTC timestamp. Message text comes from messages/.
"""

from __future__ import annotations

import csv
import io
import json
from concurrent.futures import ThreadPoolExecutor
import re
import shutil
import sqlite3
import threading
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
UNI = json.loads((ROOT / "configs" / "phase1_universe.json").read_text())
KEEP: set[str] = set()
for eco in UNI["ecosystems"].values():
    KEEP.update(eco["brand_tickers"])
    KEEP.update(eco["competitor_tickers"])
for ticks in UNI["control_pool_by_bucket"].values():
    KEEP.update(ticks)

BUCKET = "https://stocktwits-nyu.s3.amazonaws.com/"
NS = {"s": "http://s3.amazonaws.com/doc/2006-03-01/"}
INTERIM = ROOT / "data" / "interim" / "phase1"
DB_PATH = INTERIM / "stocktwits_stream.sqlite"
FEAT_DIR = ROOT / "data" / "raw" / "stocktwits" / "features"
BODY_DIR = ROOT / "data" / "raw" / "stocktwits" / "bodies"
PROGRESS = ROOT / "eval" / "results" / "phase1_stocktwits_progress.json"
CASHTAG = re.compile(r"[A-Za-z][A-Za-z0-9.\-]*")
LOCK = threading.Lock()
WORKERS = 3

FEAT_SCHEMA = pa.schema(
    [
        ("message_id", pa.int64()),
        ("created_at", pa.string()),
        ("day_utc", pa.string()),
        ("sentiment", pa.string()),
        ("cashtags", pa.string()),
    ]
)
BODY_SCHEMA = pa.schema(
    [
        ("message_id", pa.int64()),
        ("message_body", pa.string()),
    ]
)


def list_keys(prefix: str) -> list[str]:
    keys: list[str] = []
    token = None
    while True:
        url = f"{BUCKET}?list-type=2&prefix={prefix}&max-keys=1000"
        if token:
            url += "&continuation-token=" + urllib.parse.quote(token, safe="")
        req = urllib.request.Request(url, headers={"User-Agent": "sgnn-csp-phase1"})
        with urllib.request.urlopen(req, timeout=90) as response:
            root = ET.fromstring(response.read())
        for node in root.findall("s:Contents", NS):
            keys.append(node.find("s:Key", NS).text)
        trunc = root.find("s:IsTruncated", NS)
        if trunc is None or trunc.text != "true":
            return keys
        token = root.find("s:NextContinuationToken", NS).text


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=120)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=120000")
    return conn


def open_db() -> sqlite3.Connection:
    INTERIM.mkdir(parents=True, exist_ok=True)
    FEAT_DIR.mkdir(parents=True, exist_ok=True)
    BODY_DIR.mkdir(parents=True, exist_ok=True)
    conn = connect()
    conn.execute("CREATE TABLE IF NOT EXISTS done (k TEXT PRIMARY KEY)")
    conn.execute("CREATE TABLE IF NOT EXISTS ids (message_id INTEGER PRIMARY KEY)")
    conn.execute("CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT)")
    conn.commit()
    return conn


def disk_ok() -> None:
    free = shutil.disk_usage(ROOT).free
    if free < 4 * 1024**3:
        raise SystemExit(f"free disk {free / 1024**3:.1f} GiB is below 4 GiB. Stopped.")


def parse_cashtags(raw: str) -> list[str]:
    if not raw or raw == "[]":
        return []
    return [token.upper() for token in CASHTAG.findall(raw)]


def stream_features(conn: sqlite3.Connection, key: str) -> tuple[int, int]:
    url = BUCKET + key
    req = urllib.request.Request(url, headers={"User-Agent": "sgnn-csp-phase1"})
    rows: list[dict] = []
    ids: list[tuple[int]] = []
    scanned = 0
    with urllib.request.urlopen(req, timeout=180) as response:
        text = io.TextIOWrapper(response, encoding="utf-8", newline="")
        reader = csv.DictReader(text)
        for row in reader:
            scanned += 1
            tags = parse_cashtags(row.get("symbol_list") or "")
            if not tags or KEEP.isdisjoint(tags):
                continue
            raw_id = (row.get("message_id") or "").strip()
            if not raw_id.isdigit():
                continue
            created = (row.get("created_at") or "").strip()
            day = created[:10] if len(created) >= 10 and created[4] == "-" else ""
            rows.append(
                {
                    "message_id": int(raw_id),
                    "created_at": created,
                    "day_utc": day,
                    "sentiment": (row.get("sentiment") or "").strip(),
                    "cashtags": "|".join(tags),
                }
            )
            ids.append((int(raw_id),))
    stem = Path(key).stem
    if rows:
        pq.write_table(pa.Table.from_pylist(rows, schema=FEAT_SCHEMA), FEAT_DIR / f"{stem}.parquet", compression="zstd")
    if ids:
        conn.executemany("INSERT OR IGNORE INTO ids(message_id) VALUES(?)", ids)
    conn.execute("INSERT OR IGNORE INTO done(k) VALUES(?)", (key,))
    conn.commit()
    return scanned, len(rows)


def feature_stage(conn: sqlite3.Connection) -> None:
    keys = list_keys("dataset/v1/data/csv/feature_wo_messages/")
    done = {row[0] for row in conn.execute("SELECT k FROM done")}
    pending = [key for key in keys if key not in done]
    print(f"feature files {len(keys)} pending {len(pending)}", flush=True)
    scanned = 0
    kept = 0
    t0 = time.time()

    def work(key: str) -> tuple[str, int, int]:
        disk_ok()
        last_error = None
        for attempt in range(8):
            local = connect()
            try:
                return (key, *stream_features(local, key))
            except Exception as exc:
                last_error = exc
                print(f"retry feature {Path(key).name} attempt {attempt + 1}: {exc}", flush=True)
                time.sleep(min(60, 2 ** attempt))
            finally:
                local.close()
        raise RuntimeError(last_error)

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        for key, n_scan, n_keep in pool.map(work, pending):
            scanned += n_scan
            kept += n_keep
            print(
                f"feature {Path(key).name} scan {n_scan} keep {n_keep} "
                f"totals {scanned} {kept} elapsed {time.time() - t0:.0f}s",
                flush=True,
            )
            PROGRESS.write_text(
                json.dumps({"stage": "features", "scanned": scanned, "kept": kept, "file": key}, indent=2)
            )


def id_bounds(key: str) -> tuple[int, int] | None:
    url = BUCKET + key
    head = urllib.request.Request(url, headers={"User-Agent": "sgnn-csp-phase1", "Range": "bytes=0-400"})
    with urllib.request.urlopen(head, timeout=60) as response:
        first = response.read().decode("utf-8", "replace")
        size = int((response.headers.get("content-range") or "/0").split("/")[-1] or 0)
    lines = [line for line in first.splitlines() if line and not line.startswith("message_id")]
    if not lines:
        return None
    first_id = int(lines[0].split(",", 1)[0])
    if size <= 0:
        return None
    start = max(0, size - 900)
    tail_req = urllib.request.Request(
        url, headers={"User-Agent": "sgnn-csp-phase1", "Range": f"bytes={start}-{size - 1}"}
    )
    with urllib.request.urlopen(tail_req, timeout=60) as response:
        tail = response.read().decode("utf-8", "replace")
    last_id = None
    for line in reversed(tail.splitlines()):
        token = line.split(",", 1)[0]
        if token.isdigit():
            last_id = int(token)
            break
    if last_id is None:
        return None
    return first_id, last_id


def stream_bodies(conn: sqlite3.Connection, key: str) -> tuple[int, int]:
    bounds = id_bounds(key)
    if bounds is None:
        conn.execute("INSERT OR IGNORE INTO done(k) VALUES(?)", (key,))
        conn.commit()
        return 0, 0
    first_id, last_id = bounds
    wanted = {
        row[0]
        for row in conn.execute(
            "SELECT message_id FROM ids WHERE message_id BETWEEN ? AND ?",
            (first_id, last_id),
        )
    }
    if not wanted:
        conn.execute("INSERT OR IGNORE INTO done(k) VALUES(?)", (key,))
        conn.commit()
        return 0, 0
    url = BUCKET + key
    req = urllib.request.Request(url, headers={"User-Agent": "sgnn-csp-phase1"})
    rows: list[dict] = []
    scanned = 0
    with urllib.request.urlopen(req, timeout=180) as response:
        text = io.TextIOWrapper(response, encoding="utf-8", newline="")
        reader = csv.DictReader(text)
        for row in reader:
            scanned += 1
            raw_id = (row.get("message_id") or "").strip()
            if not raw_id.isdigit():
                continue
            message_id = int(raw_id)
            if message_id not in wanted:
                continue
            rows.append({"message_id": message_id, "message_body": row.get("message_body") or ""})
    stem = Path(key).stem
    if rows:
        pq.write_table(pa.Table.from_pylist(rows, schema=BODY_SCHEMA), BODY_DIR / f"{stem}.parquet", compression="zstd")
    conn.execute("INSERT OR IGNORE INTO done(k) VALUES(?)", (key,))
    conn.commit()
    return scanned, len(rows)


def body_stage(conn: sqlite3.Connection) -> None:
    keys = list_keys("dataset/v1/data/csv/messages/")
    done = {row[0] for row in conn.execute("SELECT k FROM done")}
    pending = [key for key in keys if key not in done]
    print(f"message files {len(keys)} pending {len(pending)}", flush=True)
    t0 = time.time()
    scanned = 0
    kept = 0

    def work(key: str) -> tuple[str, int, int]:
        disk_ok()
        last_error = None
        for attempt in range(8):
            local = connect()
            try:
                return (key, *stream_bodies(local, key))
            except Exception as exc:
                last_error = exc
                print(f"retry body {Path(key).name} attempt {attempt + 1}: {exc}", flush=True)
                time.sleep(min(60, 2 ** attempt))
            finally:
                local.close()
        raise RuntimeError(last_error)

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        for key, n_scan, n_keep in pool.map(work, pending):
            scanned += n_scan
            kept += n_keep
            print(
                f"body {Path(key).name} scan {n_scan} keep {n_keep} "
                f"totals {scanned} {kept} elapsed {time.time() - t0:.0f}s",
                flush=True,
            )
            PROGRESS.write_text(
                json.dumps({"stage": "bodies", "scanned": scanned, "kept": kept, "file": key}, indent=2)
            )


def main() -> None:
    conn = open_db()
    if conn.execute("SELECT 1 FROM meta WHERE k='features_complete'").fetchone() is None:
        feature_stage(conn)
        conn.execute("INSERT INTO meta(k,v) VALUES('features_complete','1')")
        conn.commit()
    body_stage(conn)
    n_ids = conn.execute("SELECT COUNT(*) FROM ids").fetchone()[0]
    print(f"stocktwits ids retained {n_ids}", flush=True)


if __name__ == "__main__":
    main()

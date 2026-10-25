"""Stream FNSPID news and keep one ticker universe.

Does not write the source CSV to disk. Counts every ticker by UTC day.
Writes compressed parquet for the retained tickers only.
Resume is the byte offset of the last committed record, stored in SQLite.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pyarrow as pa
import pyarrow.parquet as pq

from phase1_csvstream import feed_csv


def prefer_ipv4() -> None:
    """The IPv6 path to this host had multi-second latency. Use IPv4."""
    import socket

    original = socket.getaddrinfo

    def ipv4(host, port, family=0, socktype=0, proto=0, flags=0):
        try:
            found = original(host, port, socket.AF_INET, socktype, proto, flags)
        except socket.gaierror:
            found = []
        return found or original(host, port, family, socktype, proto, flags)

    socket.getaddrinfo = ipv4


prefer_ipv4()

ROOT = Path(__file__).resolve().parents[1]
UNI = json.loads((ROOT / "configs" / "phase1_universe.json").read_text())
OUT_DIR = ROOT / "data" / "raw" / "fnspid"
PART_DIR = OUT_DIR / "parts"
INTERIM = ROOT / "data" / "interim" / "phase1"
DB_PATH = INTERIM / "fnspid_stream.sqlite"
PROGRESS = ROOT / "eval" / "results" / "phase1_fnspid_progress.json"

FILES = [
    {
        "name": "nasdaq_exteral_data.csv",
        "url": "https://huggingface.co/datasets/Zihan1004/FNSPID/resolve/main/Stock_news/nasdaq_exteral_data.csv",
        "size": 23232979597,
        "etag": "cccdf2f3312e575d78ae94f799379cb85c03557374c6778cd7b7fd3d55102a2b",
    },
    {
        "name": "All_external.csv",
        "url": "https://huggingface.co/datasets/Zihan1004/FNSPID/resolve/main/Stock_news/All_external.csv",
        "size": 5731397037,
        "etag": "dde529189c87048a8be1f73d17ecd5e211fc7809032e60c72cd22645f111c470",
    },
]

KEEP = set()
for eco in UNI["ecosystems"].values():
    KEEP.update(eco["brand_tickers"])
    KEEP.update(eco["competitor_tickers"])
for ticks in UNI["control_pool_by_bucket"].values():
    KEEP.update(ticks)

BATCH_ROWS = 20000
READ = 1 << 20
SCHEMA = pa.schema(
    [
        ("source_file", pa.string()),
        ("row_id", pa.string()),
        ("date_utc", pa.string()),
        ("day_utc", pa.string()),
        ("ticker", pa.string()),
        ("headline", pa.string()),
        ("summary", pa.string()),
        ("text", pa.string()),
        ("publisher", pa.string()),
    ]
)


def retain_set() -> set[str]:
    return KEEP


def open_db() -> sqlite3.Connection:
    INTERIM.mkdir(parents=True, exist_ok=True)
    PART_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT)")
    conn.execute(
        "CREATE TABLE IF NOT EXISTS counts (ticker TEXT, day TEXT, n INTEGER, PRIMARY KEY (ticker, day))"
    )
    conn.execute("CREATE TABLE IF NOT EXISTS seen (k BLOB PRIMARY KEY)")
    return conn


def meta_get(conn: sqlite3.Connection, key: str, default: str | None = None) -> str | None:
    row = conn.execute("SELECT v FROM meta WHERE k=?", (key,)).fetchone()
    return default if row is None else row[0]


def meta_set(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute("INSERT INTO meta(k,v) VALUES(?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v", (key, value))


def rehash_prefix(url: str, nbytes: int):
    """Rebuild the SHA-256 of a resumed prefix. hashlib has no portable state."""
    hasher = hashlib.sha256()
    got = 0
    failures = 0
    last_report = 0
    while got < nbytes:
        try:
            response = http_open(url, got)
            while got < nbytes:
                chunk = response.read(min(READ, nbytes - got))
                if not chunk:
                    break
                hasher.update(chunk)
                got += len(chunk)
                failures = 0
                if got - last_report >= 64 * 1024 * 1024:
                    print(f"rehash {got}/{nbytes}", flush=True)
                    last_report = got
            if got >= nbytes:
                break
            failures += 1
            print(f"rehash short read at {got}/{nbytes}, retry {failures}", flush=True)
        except Exception as exc:
            failures += 1
            print(f"rehash error at {got}/{nbytes}: {exc}; retry {failures}", flush=True)
        if failures > 40:
            raise RuntimeError(f"rehash failed at {got}/{nbytes}")
        time.sleep(min(120, 2 ** min(failures, 7)))
    return hasher


def http_open(url: str, start: int):
    headers = {"User-Agent": "sgnn-csp-phase1", "Range": f"bytes={start}-"}
    last_error = None
    for attempt in range(8):
        try:
            req = urllib.request.Request(url, headers=headers)
            return urllib.request.urlopen(req, timeout=180)
        except Exception as exc:  # network blips on a multi-hour stream
            last_error = exc
            time.sleep(min(60, 2 ** attempt))
    raise RuntimeError(f"FNSPID open failed at byte {start}: {last_error}")


def column_map(header: list[str]) -> dict[str, int]:
    index = {name.strip(): i for i, name in enumerate(header)}
    needed = ["Date", "Article_title", "Stock_symbol", "Publisher", "Article", "Lsa_summary"]
    missing = [name for name in needed if name not in index]
    if missing:
        raise SystemExit(f"FNSPID header missing {missing}. Saw {header}")
    return index


def day_of(value: str) -> str:
    value = value.strip()
    if len(value) >= 10 and value[4] == "-" and value[7] == "-":
        return value[:10]
    return ""


def flush_counts(conn: sqlite3.Connection, counts: dict[tuple[str, str], int]) -> None:
    if not counts:
        return
    conn.executemany(
        "INSERT INTO counts(ticker, day, n) VALUES(?,?,?) "
        "ON CONFLICT(ticker, day) DO UPDATE SET n = n + excluded.n",
        [(t, d, n) for (t, d), n in counts.items()],
    )
    counts.clear()


def write_part(rows: list[dict], start_byte: int) -> None:
    if not rows:
        return
    path = PART_DIR / f"part_{start_byte}.parquet"
    table = pa.Table.from_pylist(rows, schema=SCHEMA)
    pq.write_table(table, path, compression="zstd")


def stream_file(conn: sqlite3.Connection, spec: dict) -> None:
    name = spec["name"]
    done = meta_get(conn, f"done:{name}")
    if done == "1":
        print(f"skip complete {name}", flush=True)
        return
    offset = int(meta_get(conn, f"offset:{name}", "0") or "0")
    if offset:
        print(f"rehash {name} prefix {offset}", flush=True)
        hasher = rehash_prefix(spec["url"], offset)
    else:
        hasher = hashlib.sha256()
    header_done = meta_get(conn, f"header:{name}") == "1"
    cols = None
    if header_done:
        cols = json.loads(meta_get(conn, f"cols:{name}") or "{}")
    buf = b""
    file_pos = offset
    counts: dict[tuple[str, str], int] = {}
    kept: list[dict] = []
    kept_start = offset
    rows_seen = int(meta_get(conn, f"rows:{name}", "0") or "0")
    rows_kept = int(meta_get(conn, "rows_kept", "0") or "0")
    bad_rows = int(meta_get(conn, f"bad:{name}", "0") or "0")
    seq = rows_seen
    since_flush = 0
    print(f"start {name} at {offset}", flush=True)
    failures = 0
    t0 = time.time()
    last_report = offset
    while file_pos < spec["size"]:
        try:
            response = http_open(spec["url"], file_pos)
            buf = b""
            while True:
                chunk = response.read(READ)
                if not chunk:
                    break
                buf += chunk
                records, consumed = feed_csv(buf)
                if consumed:
                    hasher.update(buf[:consumed])
                    file_pos += consumed
                    buf = buf[consumed:]
                for rec in records:
                    if not header_done:
                        cols = column_map(rec)
                        header_done = True
                        meta_set(conn, f"header:{name}", "1")
                        meta_set(conn, f"cols:{name}", json.dumps(cols))
                        continue
                    if cols is None:
                        raise RuntimeError("header missing after resume")
                    if len(rec) <= max(cols.values()):
                        bad_rows += 1
                        continue
                    ticker = rec[cols["Stock_symbol"]].strip().upper()
                    if not ticker:
                        continue
                    date_utc = rec[cols["Date"]].strip()
                    day = day_of(date_utc)
                    if not day:
                        bad_rows += 1
                        continue
                    headline = rec[cols["Article_title"]]
                    seq += 1
                    rows_seen += 1
                    key = hashlib.sha1(f"{day}|{ticker}|{headline}".encode("utf-8", "replace")).digest()
                    inserted = conn.execute("INSERT OR IGNORE INTO seen(k) VALUES(?)", (key,)).rowcount
                    if inserted == 0:
                        continue
                    counts[(ticker, day)] = counts.get((ticker, day), 0) + 1
                    since_flush += 1
                    if ticker not in KEEP:
                        continue
                    row_id = ""
                    if "Unnamed: 0" in cols and cols["Unnamed: 0"] < len(rec):
                        row_id = rec[cols["Unnamed: 0"]].strip()
                    if not row_id:
                        row_id = f"{name}:{seq}"
                    kept.append(
                        {
                            "source_file": name,
                            "row_id": row_id,
                            "date_utc": date_utc,
                            "day_utc": day,
                            "ticker": ticker,
                            "headline": headline,
                            "summary": rec[cols["Lsa_summary"]],
                            "text": rec[cols["Article"]],
                            "publisher": rec[cols["Publisher"]],
                        }
                    )
                if len(kept) >= BATCH_ROWS or len(counts) >= 50000 or since_flush >= 20000:
                    write_part(kept, kept_start)
                    rows_kept += len(kept)
                    kept = []
                    flush_counts(conn, counts)
                    meta_set(conn, f"offset:{name}", str(file_pos))
                    meta_set(conn, f"rows:{name}", str(rows_seen))
                    meta_set(conn, "rows_kept", str(rows_kept))
                    meta_set(conn, f"bad:{name}", str(bad_rows))
                    conn.commit()
                    kept_start = file_pos
                    since_flush = 0
                if file_pos - last_report >= 64 * 1024 * 1024:
                    elapsed = max(time.time() - t0, 1)
                    print(
                        f"{name} byte {file_pos}/{spec['size']} rows {rows_seen} kept {rows_kept + len(kept)} "
                        f"bad {bad_rows} MB/s {(file_pos - offset) / elapsed / 1e6:.2f}",
                        flush=True,
                    )
                    last_report = file_pos
                    write_progress(conn, name, file_pos, spec["size"], rows_seen, rows_kept + len(kept))
                    failures = 0
            if file_pos >= spec["size"] or file_pos + len(buf) >= spec["size"]:
                break
            failures += 1
            print(f"short read {name} at {file_pos}/{spec['size']}, retry {failures}", flush=True)
            if failures > 40:
                break
            time.sleep(min(120, 2 ** min(failures, 7)))
        except Exception as exc:
            failures += 1
            print(f"read error {name} at {file_pos}: {exc}; retry {failures}", flush=True)
            if failures > 40:
                break
            time.sleep(min(120, 2 ** min(failures, 7)))
    if buf.strip(b"\r\n"):
        # A file that does not end in a newline still has one last record.
        tail_rows, consumed = feed_csv(buf + b"\n")
        if consumed:
            hasher.update(buf[: max(0, consumed - 1)])
            file_pos += len(buf)
            buf = b""
            for rec in tail_rows:
                if not header_done:
                    continue
                if len(rec) <= max(cols.values()):
                    bad_rows += 1
                    continue
                ticker = rec[cols["Stock_symbol"]].strip().upper()
                date_utc = rec[cols["Date"]].strip()
                day = day_of(date_utc)
                if not ticker or not day:
                    continue
                headline = rec[cols["Article_title"]]
                seq += 1
                rows_seen += 1
                key = hashlib.sha1(f"{day}|{ticker}|{headline}".encode("utf-8", "replace")).digest()
                if conn.execute("INSERT OR IGNORE INTO seen(k) VALUES(?)", (key,)).rowcount == 0:
                    continue
                counts[(ticker, day)] = counts.get((ticker, day), 0) + 1
                if ticker not in KEEP:
                    continue
                row_id = ""
                if "Unnamed: 0" in cols and cols["Unnamed: 0"] < len(rec):
                    row_id = rec[cols["Unnamed: 0"]].strip()
                kept.append(
                    {
                        "source_file": name,
                        "row_id": row_id or f"{name}:{seq}",
                        "date_utc": date_utc,
                        "day_utc": day,
                        "ticker": ticker,
                        "headline": headline,
                        "summary": rec[cols["Lsa_summary"]],
                        "text": rec[cols["Article"]],
                        "publisher": rec[cols["Publisher"]],
                    }
                )
    write_part(kept, kept_start)
    rows_kept += len(kept)
    flush_counts(conn, counts)
    digest = hasher.hexdigest()
    meta_set(conn, f"offset:{name}", str(file_pos))
    meta_set(conn, f"rows:{name}", str(rows_seen))
    meta_set(conn, "rows_kept", str(rows_kept))
    meta_set(conn, f"bad:{name}", str(bad_rows))
    complete = file_pos >= spec["size"]
    if complete:
        meta_set(conn, f"shahex:{name}", digest)
        meta_set(conn, f"done:{name}", "1")
    conn.commit()
    match = digest == spec["etag"]
    print(
        f"end {name} complete {complete} sha256 {digest} etag_match {match} "
        f"bytes {file_pos}/{spec['size']} rows {rows_seen} kept_total {rows_kept}",
        flush=True,
    )
    if not complete:
        raise SystemExit(f"{name} stopped at byte {file_pos} of {spec['size']}. Resume will continue.")
    write_progress(conn, name, file_pos, spec["size"], rows_seen, rows_kept)


def write_progress(conn, name, pos, size, rows, kept) -> None:
    PROGRESS.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "file": name,
        "byte": pos,
        "size": size,
        "rows_seen_this_file": rows,
        "rows_kept": kept,
        "sha_nasdaq": meta_get(conn, "shahex:nasdaq_exteral_data.csv"),
        "sha_all_external": meta_get(conn, "shahex:All_external.csv"),
    }
    PROGRESS.write_text(json.dumps(payload, indent=2))


def export_counts(conn: sqlite3.Connection) -> None:
    path = ROOT / "eval" / "results" / "phase1_fnspid_ticker_daily.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    cur = conn.execute("SELECT ticker, day, n FROM counts ORDER BY ticker, day")
    with path.open("w", encoding="utf-8") as handle:
        handle.write("ticker,day,rows\n")
        for ticker, day, n in cur:
            handle.write(f"{ticker},{day},{n}\n")
    print(f"wrote {path}", flush=True)


def main() -> None:
    conn = open_db()
    meta_set(conn, "universe_sha256", hashlib.sha256((ROOT / "configs" / "phase1_universe.json").read_bytes()).hexdigest())
    meta_set(conn, "retain_n", str(len(KEEP)))
    conn.commit()
    for spec in FILES:
        stream_file(conn, spec)
    export_counts(conn)


if __name__ == "__main__":
    main()

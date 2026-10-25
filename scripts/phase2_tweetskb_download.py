"""Download one TweetsKB month at a time. Resumable. Deletes nothing.

Six workers each request a 1 MB range. That is the method that transferred
843,055,104 bytes in 603.8 seconds (1.396 MB/s) on 2026-10-19. TLS
verification stays on. A free-disk reading under 6 GB pauses the workers.
The reducer deletes the raw file after a successful reduce.
"""

from __future__ import annotations

import json
import os
import shutil
import threading
import time
import urllib.request
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "interim" / "tweetskb_raw"
STATUS = ROOT / "eval" / "results" / "tweetskb_download.status.json"
UA = "sgnn-csp-phase2/0.1 (srivatsa.singaraju2023@vitstudent.ac.in)"
CHUNK = 1024 * 1024
WORKERS = 6
DISK_PAUSE = 6 * 10**9


def load_status() -> dict:
    if STATUS.exists():
        return json.loads(STATUS.read_text())
    return {"files_done": [], "files": {}}


def save_status(status: dict) -> None:
    STATUS.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATUS.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(status, indent=2))
    tmp.replace(STATUS)


def free_bytes() -> int:
    return shutil.disk_usage(ROOT).free


def download_one(name: str, url: str, size: int) -> Path:
    if size > 10 * 10**9:
        raise SystemExit(f"{name} is {size} bytes, above the 10 GB raw-file stop")
    RAW.mkdir(parents=True, exist_ok=True)
    dest = RAW / name
    status = load_status()
    file_status = status["files"].setdefault(name, {"url": url, "size": size, "bytes": 0})
    start_at = int(file_status.get("bytes") or 0)
    if file_status.get("complete") and start_at >= size and dest.exists():
        return dest
    if not dest.exists() or dest.stat().st_size != size:
        with dest.open("wb") as handle:
            handle.truncate(size)
    if start_at >= size:
        file_status["complete"] = True
        save_status(status)
        return dest

    pending: deque[tuple[int, int]] = deque()
    cursor = start_at
    while cursor < size:
        end = min(cursor + CHUNK, size) - 1
        pending.append((cursor, end))
        cursor = end + 1

    lock = threading.Lock()
    state = {
        "contiguous": start_at,
        "received": 0,
        "t0": time.time(),
        "done_at": {},
    }
    file_status["method"] = "six parallel 1 MB ranges"
    file_status["parallel_start_bytes"] = start_at
    file_status["parallel_started_unix"] = state["t0"]
    status["current"] = name
    save_status(status)
    fd = os.open(dest, os.O_RDWR)
    stop = threading.Event()

    def note(begin: int, end: int) -> None:
        with lock:
            state["received"] += end - begin + 1
            state["done_at"][begin] = end
            contiguous = state["contiguous"]
            while contiguous in state["done_at"]:
                contiguous = state["done_at"].pop(contiguous) + 1
            state["contiguous"] = contiguous
            elapsed = max(time.time() - state["t0"], 0.001)
            file_status["bytes"] = contiguous
            file_status["session_received"] = state["received"]
            file_status["speed_mb_s"] = round(state["received"] / elapsed / 1e6, 4)
            file_status["free_bytes"] = free_bytes()
            if state["received"] % (32 * 1024 * 1024) < (end - begin + 1):
                save_status(status)
                print(
                    f"{name} {contiguous}/{size} {file_status['speed_mb_s']} MB/s",
                    flush=True,
                )

    def take_range() -> tuple[int, int] | None:
        with lock:
            if not pending:
                return None
            return pending.popleft()

    def return_range(begin: int, end: int) -> None:
        with lock:
            if begin == state["contiguous"]:
                pending.appendleft((begin, end))
            else:
                pending.append((begin, end))

    def worker() -> None:
        while not stop.is_set():
            item = take_range()
            if item is None:
                time.sleep(0.2)
                continue
            begin, end = item
            try:
                while free_bytes() < DISK_PAUSE and not stop.is_set():
                    print(f"pause {name}: free disk under 6 GB", flush=True)
                    time.sleep(30)
                request = urllib.request.Request(
                    url,
                    headers={"User-Agent": UA, "Range": f"bytes={begin}-{end}"},
                )
                with urllib.request.urlopen(request, timeout=120) as response:
                    data = response.read()
                    code = getattr(response, "status", None)
                expected = end - begin + 1
                if code != 206 or len(data) != expected:
                    raise OSError(f"status {code} got {len(data)} expected {expected}")
                os.pwrite(fd, data, begin)
                note(begin, end)
            except Exception as exc:
                print(f"retry {name} at {begin} after {exc}", flush=True)
                return_range(begin, end)
                time.sleep(5)

    threads = [threading.Thread(target=worker, daemon=True) for _ in range(WORKERS)]
    for thread in threads:
        thread.start()
    while state["contiguous"] < size:
        time.sleep(2)
        if not any(thread.is_alive() for thread in threads):
            break
    stop.set()
    for thread in threads:
        thread.join(timeout=5)
    os.close(fd)
    if state["contiguous"] < size:
        save_status(status)
        raise SystemExit(f"{name} stopped at {state['contiguous']} of {size}")
    file_status["bytes"] = size
    file_status["complete"] = True
    elapsed = max(time.time() - state["t0"], 0.001)
    file_status["speed_mb_s"] = round(state["received"] / elapsed / 1e6, 4)
    save_status(status)
    print(f"complete {name} {size} {file_status['speed_mb_s']} MB/s", flush=True)
    return dest


def main() -> None:
    import sys

    name, url, size = sys.argv[1], sys.argv[2], int(sys.argv[3])
    download_one(name, url, size)


if __name__ == "__main__":
    main()

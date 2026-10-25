"""Fetch the missing leading 1 MB of the current TweetsKB file.

Does not start a second download and does not move the live offset.
The running downloader still records that range when its own request
finishes.
"""

from __future__ import annotations

import json
import os
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "interim" / "tweetskb_raw"
STATUS = ROOT / "eval" / "results" / "tweetskb_download.status.json"
UA = "sgnn-csp-phase2/0.1 (srivatsa.singaraju2023@vitstudent.ac.in)"
CHUNK = 1024 * 1024
TRIES = 8


def main() -> None:
    status = json.loads(STATUS.read_text())
    name = status["current"]
    row = status["files"][name]
    url = row["url"]
    size = int(row["size"])
    end = min(CHUNK, size) - 1
    dest = RAW / name
    if not dest.exists():
        raise SystemExit(f"{dest} is missing")
    last = ""
    for attempt in range(1, TRIES + 1):
        started = time.perf_counter()
        try:
            request = urllib.request.Request(
                url,
                headers={"User-Agent": UA, "Range": f"bytes=0-{end}"},
            )
            with urllib.request.urlopen(request, timeout=120) as response:
                data = response.read()
                code = getattr(response, "status", None)
            expected = end + 1
            if code != 206 or len(data) != expected:
                raise OSError(f"status {code} got {len(data)} expected {expected}")
            fd = os.open(dest, os.O_RDWR)
            try:
                os.pwrite(fd, data, 0)
            finally:
                os.close(fd)
            elapsed = max(time.perf_counter() - started, 0.001)
            speed = len(data) / elapsed / 1e6
            print(
                f"filled {name} bytes 0-{end} {len(data)} {speed:.4f} MB/s attempt {attempt}",
                flush=True,
            )
            return
        except Exception as exc:
            last = str(exc)
            print(f"retry leading {name} attempt {attempt} after {exc}", flush=True)
            time.sleep(min(2 ** attempt, 30))
    raise SystemExit(f"leading range failed after {TRIES} tries: {last}")


if __name__ == "__main__":
    main()

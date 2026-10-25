"""Check frozen files and model weights against the recorded sha256 values.

Reads configs/frozen_sha256.json and the GDELT allow-list manifest.
Does not rewrite a file. A missing file and a hash that differs are both mismatches.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "configs" / "frozen_sha256.json"
CHUNK = 1024 * 1024


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(CHUNK)
            if not block:
                break
            hasher.update(block)
    return hasher.hexdigest()


def report(status: str, path: Path, detail: str) -> None:
    print(f"{status}\t{path.relative_to(ROOT)}\t{detail}")


def main() -> None:
    spec = json.loads(MANIFEST.read_text())
    mismatches = 0
    for row in spec["files"]:
        path = ROOT / row["path"]
        if not path.is_file():
            mismatches += 1
            report("MISSING", path, f"recorded {row['sha256']}")
            continue
        amendments = row.get("amendments") or []
        expected = amendments[-1]["sha256"] if amendments else row["sha256"]
        got = digest(path)
        if got == expected:
            if amendments:
                report("MATCH", path, f"{got} amendment {amendments[-1]['recorded_on']} kept {row['sha256']}")
            else:
                report("MATCH", path, got)
        else:
            mismatches += 1
            report("MISMATCH", path, f"expected {expected} actual {got}")
    for row in spec["manifests"]:
        manifest = ROOT / row["path"]
        directory = ROOT / row["directory"]
        if not manifest.is_file():
            mismatches += 1
            print(f"MISSING\t{row['path']}\tmanifest")
            continue
        listed = 0
        size_sum = 0
        for line in manifest.read_text().splitlines():
            if not line.strip():
                continue
            listed += 1
            digest_hex, name, size_text = line.split()
            size_sum += int(size_text)
            path = directory / name
            if not path.is_file():
                mismatches += 1
                report("MISSING", path, f"recorded {digest_hex}")
                continue
            got = digest(path)
            if path.stat().st_size != int(size_text) or got != digest_hex:
                mismatches += 1
                report("MISMATCH", path, f"recorded {digest_hex} actual {got}")
            else:
                report("MATCH", path, got)
        if size_sum != row["size_sum"]:
            mismatches += 1
            print(f"MISMATCH\t{row['path']}\tsize sum recorded {row['size_sum']} actual {size_sum} files {listed}")
        else:
            print(f"MATCH\t{row['path']}\tsize sum {size_sum} files {listed}")
    if mismatches:
        print(f"mismatches {mismatches}")
        sys.exit(1)
    print("mismatches 0")


if __name__ == "__main__":
    main()

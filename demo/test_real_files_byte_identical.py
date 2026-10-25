"""Confirm Option B does not change real study files."""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REAL_FILES = (
    "configs/phase0.json",
    "configs/phase4_series.json",
    "configs/frozen_sha256.json",
    "eval/results/phase4_outcomes.json",
    "reports/phase4_outcomes.md",
    "kg/phase2_structural_edges.json",
    "scripts/phase4_analysis.py",
    "scripts/phase5_model.py",
    "DECISIONS_LOG.md",
)


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    hasher.update(path.read_bytes())
    return hasher.hexdigest()


def main() -> None:
    before = {name: digest(ROOT / name) for name in REAL_FILES}
    before_sizes = {name: (ROOT / name).stat().st_size for name in REAL_FILES}
    command = [
        sys.executable,
        str(ROOT / "demo" / "build_augmented.py"),
        "--confirm-augmented",
        "--lambda",
        "1.0",
        "--synthetic-share",
        "0.25",
    ]
    completed = subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)
    after = {name: digest(ROOT / name) for name in REAL_FILES}
    after_sizes = {name: (ROOT / name).stat().st_size for name in REAL_FILES}
    changed = [name for name in REAL_FILES if before[name] != after[name] or before_sizes[name] != after_sizes[name]]
    if changed:
        raise SystemExit(f"real files changed: {changed}")
    if "synthetic share" not in completed.stdout:
        raise SystemExit("builder did not print the synthetic share")
    outputs = list((ROOT / "demo" / "augmented").glob("AUGMENTED_CONTAINS_SYNTHETIC_DATA_*"))
    if not outputs:
        raise SystemExit("no AUGMENTED output")
    text = (ROOT / "demo" / "augmented").joinpath(next(path.name for path in outputs if path.suffix == ".json")).read_text()
    if "CONTAINS SYNTHETIC DATA" not in text or "real_only" not in text or "combined" not in text:
        raise SystemExit("subset report is missing the required labels")
    print("PASS real files byte-identical", len(REAL_FILES), "files")
    print(completed.stdout.strip())


if __name__ == "__main__":
    main()

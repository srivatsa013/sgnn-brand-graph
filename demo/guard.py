"""Write guard for the faculty demo. Demo code may read the study files. It may not write them."""

from __future__ import annotations

from pathlib import Path

DEMO = Path(__file__).resolve().parent
ROOT = DEMO.parent
FORBIDDEN = (
    (ROOT / "data").resolve(),
    (ROOT / "eval" / "results").resolve(),
)


def demo_file(relative: str) -> Path:
    path = (DEMO / relative).resolve()
    if path != DEMO and DEMO not in path.parents:
        raise SystemExit(f"refusing to write outside demo/: {path}")
    for banned in FORBIDDEN:
        if path == banned or banned in path.parents:
            raise SystemExit(f"refusing to write into a study folder: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path

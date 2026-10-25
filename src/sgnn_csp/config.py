"""Load the frozen Phase 0 configuration.

configs/phase0.json is the numeric source of truth. Later phases read it
instead of introducing new thresholds.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def config_path() -> Path:
    return repo_root() / "configs" / "phase0.json"


def load_config(path: Path | None = None) -> dict[str, Any]:
    target = path or config_path()
    with target.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if data.get("schema_version") != "0.1.0":
        raise ValueError(f"Unexpected schema_version in {target}")
    return data

"""One-day GDELT entity sample for the wikipediaUrl / mid match rule.

Dry-runs first. Does not scan the historical span. Article URLs are not selected.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bq_usage import run_query  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "eval" / "results" / "phase1c_gdelt_match_audit.json"

NAMES = (
    "Apple",
    "Windows",
    "Azure",
    "Android",
    "Model S",
    "Dell",
    "Amazon",
    "Meta",
    "Oracle",
    "Google",
    "Samsung",
    "HP",
    "Snap",
    "iPhone",
    "YouTube",
    "Logitech",
)

AUDIT = f"""
SELECT entity.name AS name, entity.type AS type,
       entity.wikipediaUrl AS wiki, entity.mid AS mid,
       COUNT(*) AS n
FROM `gdelt-bq.gdeltv2.geg_gcnlapi`, UNNEST(entities) AS entity
WHERE date >= TIMESTAMP('2016-11-14')
  AND date < TIMESTAMP('2016-11-15')
  AND lang = 'en'
  AND entity.name IN ({", ".join(repr(name) for name in NAMES)})
GROUP BY name, type, wiki, mid
ORDER BY n DESC
"""

FULL = """
SELECT COUNT(*) AS n
FROM `gdelt-bq.gdeltv2.geg_gcnlapi`, UNNEST(entities) AS entity
WHERE date >= TIMESTAMP('2016-11-14')
  AND date < TIMESTAMP('2026-08-15')
  AND lang = 'en'
"""


def main() -> None:
    full, full_bytes = run_query(FULL, "gdelt_full_span_dry", execute=False)
    print("full_span_dry_bytes", full_bytes, flush=True)
    rows, used = run_query(AUDIT, "gdelt_match_audit_2016_11_14", execute=True)
    payload = {
        "day": "2016-11-14",
        "bytes_processed": used,
        "full_span_dry_run_bytes": full_bytes,
        "full_span_executed": False,
        "rows": rows,
    }
    OUT.write_text(json.dumps(payload))
    print("audit_rows", len(rows) if isinstance(rows, list) else type(rows), "bytes", used, flush=True)


if __name__ == "__main__":
    main()

"""Dry-run the first 28-day slice of the allow-list GDELT scan. Does not execute it.

The filter is in SQL so the result is small. Bytes billed do not shrink,
because the entities column is still read.
"""

from __future__ import annotations

import json
import time
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOW = ROOT / "configs" / "scan_allowlist.json"
SQL_PATH = ROOT / "eval" / "results" / "phase2_gdelt_allowlist_scan.sql"
OUT = ROOT / "eval" / "results" / "phase2_gdelt_allowlist_dry_run.json"
START = date(2016, 11, 14)
SLICE_DAYS = 28


def sql(titles: list[str], mids: list[str], start: date, end: date) -> str:
    def quote(value: str) -> str:
        return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"

    title_list = ", ".join(quote(title) for title in titles)
    mid_list = ", ".join(quote(mid) for mid in mids)
    mid_clause = f"OR ent.mid IN ({mid_list})" if mids else ""
    return f"""
SELECT
  DATE(date) AS day,
  ANY_VALUE(lang) AS lang,
  FARM_FINGERPRINT(url) AS url_hash,
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


def main() -> None:
    import sys

    sys.path.insert(0, str(ROOT / "scripts"))
    from bq_usage import PROJECT, dry_run_bytes, month_used
    from bq_usage import _append

    allow = json.loads(ALLOW.read_text())
    titles = sorted(
        {
            row["enwiki"].replace(" ", "_")
            for row in allow["nodes"]
            if row.get("enwiki") and row.get("role") != "control"
        }
    )
    mids = sorted({mid for row in allow["nodes"] for mid in (row.get("mids") or []) if mid})
    end = START + timedelta(days=SLICE_DAYS)
    query = sql(titles, mids, START, end)
    SQL_PATH.write_text(query + "\n")
    estimated = dry_run_bytes(query)
    _append(
        {
            "purpose": "gdelt_allowlist_slice_2016-11-14",
            "executed": False,
            "project_id": PROJECT,
            "dry_run_bytes": estimated,
            "month_used_before": month_used(),
            "slice_start": START.isoformat(),
            "slice_end_exclusive": end.isoformat(),
            "titles": len(titles),
            "mids": len(mids),
            "real_scan": False,
            "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
    )
    payload = {
        "project_id": PROJECT,
        "executed": False,
        "slice_start": START.isoformat(),
        "slice_end_exclusive": end.isoformat(),
        "slice_days": SLICE_DAYS,
        "titles": len(titles),
        "mids": len(mids),
        "dry_run_bytes": estimated,
        "result_size_bytes": None,
        "result_size_note": "A BigQuery dry run returns bytes processed, not the size of the result.",
        "sql": str(SQL_PATH),
    }
    OUT.write_text(json.dumps(payload, indent=2))
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()

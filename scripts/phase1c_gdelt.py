"""Arm B news aggregates from GDELT GEG. One article counts once per node.

Document score is the article score, on [-1, 1]. No article URL is stored.
Each query is a 28-day slice. A slice whose dry run exceeds 10 GB is not run.
"""

from __future__ import annotations

import json
import subprocess
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "eval" / "results" / "phase1c_gdelt_days.json"
PROJECT = "sgnn-csp"
CAP = 10 * 10**9
START = date(2016, 11, 14)
END = date(2026, 8, 15)  # table max observed day is 2026-08-14

# Exact names and types. A second name on the same article does not add a row.
FLAGS = {
    "Apple": "entity.type = 'ORGANIZATION' AND entity.name IN ('Apple','Apple Inc','Apple Inc.')",
    "iPhone": "entity.type = 'CONSUMER_GOOD' AND entity.name = 'iPhone'",
    "MacBook": "entity.type = 'CONSUMER_GOOD' AND entity.name = 'MacBook'",
    "Apple CEO": "entity.type = 'PERSON' AND entity.name IN ('Tim Cook','Timothy Cook') AND date >= TIMESTAMP('2011-08-24') AND date < TIMESTAMP('2026-09-01')",
    "DELL": "entity.type = 'ORGANIZATION' AND entity.name = 'Dell'",
    "HPQ": "entity.type = 'ORGANIZATION' AND entity.name IN ('Hewlett-Packard','Hewlett Packard')",
    "LOGI": "entity.type = 'ORGANIZATION' AND entity.name = 'Logitech'",
    "Microsoft": "entity.type = 'ORGANIZATION' AND entity.name IN ('Microsoft','Microsoft Corporation','Microsoft Corp','Microsoft Corp.')",
    "Windows": "(entity.type = 'CONSUMER_GOOD' AND entity.name IN ('Windows','Microsoft Windows'))",
    "Azure": "entity.name IN ('Azure','Microsoft Azure') AND entity.type IN ('CONSUMER_GOOD','ORGANIZATION','OTHER')",
    "Microsoft CEO": "entity.type = 'PERSON' AND entity.name = 'Satya Nadella' AND date >= TIMESTAMP('2014-02-04')",
    "ORCL": "entity.type = 'ORGANIZATION' AND entity.name IN ('Oracle','Oracle Corporation')",
    "CRM": "entity.type = 'ORGANIZATION' AND entity.name IN ('Salesforce','Salesforce.com')",
    "IBM": "entity.type = 'ORGANIZATION' AND entity.name = 'IBM'",
    "ADBE": "entity.type = 'ORGANIZATION' AND entity.name IN ('Adobe','Adobe Inc.','Adobe Inc')",
    "Alphabet": "entity.type = 'ORGANIZATION' AND entity.name = 'Google'",
    "YouTube": "entity.name IN ('YouTube','Youtube') AND entity.type IN ('OTHER','ORGANIZATION','CONSUMER_GOOD')",
    "Android": "entity.type = 'CONSUMER_GOOD' AND entity.name = 'Android'",
    "Alphabet CEO": """(
        (entity.type = 'PERSON' AND entity.name = 'Sundar Pichai' AND date >= TIMESTAMP('2015-08-10'))
        OR (entity.type = 'PERSON' AND entity.name = 'Larry Page'
            AND date >= TIMESTAMP('2011-04-04') AND date < TIMESTAMP('2019-12-04'))
    )""",
    "Meta": "entity.name IN ('Facebook','Meta','Meta Platforms') AND entity.type IN ('ORGANIZATION','OTHER')",
    "AMZN": "entity.type = 'ORGANIZATION' AND entity.name = 'Amazon'",
    "SNAP": "entity.name = 'Snapchat' AND entity.type IN ('OTHER','CONSUMER_GOOD','ORGANIZATION')",
    "PINS": "entity.name = 'Pinterest' AND entity.type IN ('OTHER','ORGANIZATION')",
    "Samsung": "entity.type = 'ORGANIZATION' AND entity.name IN ('Samsung','Samsung Electronics','Samsung Electronics Co.')",
}


def sql(start: date, end: date) -> str:
    cols = []
    preds = []
    for name, pred in FLAGS.items():
        key = name.replace(" ", "_")
        cols.append(
            f"COUNTIF({key} = 1) AS {key}_n, "
            f"SUM(IF({key} = 1, score, NULL)) AS {key}_sum, "
            f"COUNTIF({key} = 1 AND score IS NOT NULL) AS {key}_scored"
        )
        preds.append(f"MAX(IF({pred}, 1, 0)) AS {key}")
    where_names = " OR ".join(f"({pred})" for pred in FLAGS.values())
    return f"""
SELECT day, {", ".join(cols)}
FROM (
  SELECT DATE(date) AS day, url, ANY_VALUE(score) AS score, {", ".join(preds)}
  FROM `gdelt-bq.gdeltv2.geg_gcnlapi`, UNNEST(entities) AS entity
  WHERE date >= TIMESTAMP('{start.isoformat()}')
    AND date < TIMESTAMP('{end.isoformat()}')
    AND lang = 'en'
    AND ({where_names})
  GROUP BY day, url
)
GROUP BY day
ORDER BY day
"""


def main() -> None:
    if OUT.exists():
        raise SystemExit(
            f"{OUT} already holds the only historical extract. "
            "Refusing to scan those dates again."
        )
    from bq_usage import dry_run_bytes, month_used, run_query

    cursor = START
    end = cursor + timedelta(days=28)
    nbytes = dry_run_bytes(sql(cursor, end))
    print("dry_run_bytes", nbytes, "month_used", month_used(), flush=True)
    if nbytes > CAP:
        raise SystemExit(f"dry run {nbytes} exceeds 10 GB")
    spent = 0
    rows: dict[str, dict] = {}
    while cursor < END:
        end = min(cursor + timedelta(days=28), END)
        query = sql(cursor, end)
        data, processed = run_query(query, f"gdelt_{cursor.isoformat()}", execute=True)
        spent += processed
        if not isinstance(data, list):
            data = []
        for row in data:
            day = row["day"][:10]
            slot = rows.setdefault(day, {})
            for name in FLAGS:
                key = name.replace(" ", "_")
                raw_sum = row.get(f"{key}_sum")
                slot[name] = {
                    "n": int(row[f"{key}_n"]),
                    "sum": float(raw_sum) if raw_sum not in (None, "null") else 0.0,
                    "scored": int(row[f"{key}_scored"]),
                }
        print(cursor.isoformat(), "days", len(data), "spent", spent, flush=True)
        OUT.write_text(json.dumps({"bytes": spent, "rows": rows, "window_days": 28}))
        if spent > 900 * 10**9:
            raise SystemExit(f"stopping at {spent} bytes to stay inside the sandbox")
        cursor = end
    print("done", len(rows), "bytes", spent, flush=True)


if __name__ == "__main__":
    main()

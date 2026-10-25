"""Coverage bar for the three dated Nike subsidiaries. Does not add an edge.

A day counts when it has at least 14 scored documents on or after the
year-precision start (1 January of that year). The generic Colgate target
Toothpaste is not scanned.
"""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
TARGETS = [
    ("Hurley International", "Q3266971", "Nike", "2002-01-01", re.compile(r"\bHurley International\b")),
    ("Converse", "Q319515", "Nike", "2003-01-01", re.compile(r"\bConverse\b")),
    ("Umbro", "Q652047", "Nike", "2007-01-01", re.compile(r"\bUmbro\b")),
]
OUT = ROOT / "eval" / "results" / "phase2_subsidiary_coverage.json"


def main() -> None:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

    analyzer = SentimentIntensityAnalyzer()
    news = {name: {} for name, *_ in TARGETS}
    for path in sorted((ROOT / "data" / "raw" / "fnspid" / "parts").glob("*.parquet")):
        pf = pq.ParquetFile(path)
        for batch in pf.iter_batches(batch_size=4000, columns=["day_utc", "headline", "summary", "text"]):
            data = batch.to_pydict()
            for i, day in enumerate(data["day_utc"]):
                if not day:
                    continue
                headline = data["headline"][i] or ""
                blob = " ".join(part for part in (headline, data["summary"][i] or "", data["text"][i] or "") if part)
                if not blob:
                    continue
                score = float(analyzer.polarity_scores(headline)["compound"]) if headline else None
                for name, _qid, _parent, start, pattern in TARGETS:
                    if day < start or not pattern.search(blob):
                        continue
                    cell = news[name].setdefault(day, [0, 0])
                    if score is not None:
                        cell[0] += score
                        cell[1] += 1
        print("news", path.name, flush=True)

    social = {name: {} for name, *_ in TARGETS}
    con = sqlite3.connect(ROOT / "data" / "interim" / "phase2" / "series.sqlite")
    for path in sorted((ROOT / "data" / "raw" / "stocktwits" / "bodies").glob("*.parquet")):
        table = pq.read_table(path, columns=["message_id", "message_body"])
        ids = table.column("message_id").to_pylist()
        bodies = table.column("message_body").to_pylist()
        if not ids:
            continue
        meta = {
            row[0]: (row[1], row[2])
            for row in con.execute(
                "SELECT message_id, day, score FROM feat WHERE message_id BETWEEN ? AND ?",
                (min(ids), max(ids)),
            )
        }
        for message_id, body in zip(ids, bodies):
            info = meta.get(message_id)
            if not info or not info[0] or not body:
                continue
            day, score = info
            for name, _qid, _parent, start, pattern in TARGETS:
                if day < start or not pattern.search(body):
                    continue
                cell = social[name].setdefault(day, [0, 0])
                if score is not None:
                    cell[0] += score
                    cell[1] += 1
        print("social", path.name, flush=True)
    con.close()

    rows = []
    for name, qid, parent, start, _pattern in TARGETS:
        news_dense = sum(1 for cell in news[name].values() if cell[1] >= 14)
        social_dense = sum(1 for cell in social[name].values() if cell[1] >= 14)
        rows.append(
            {
                "name": name,
                "qid": qid,
                "parent": parent,
                "counts_from": start,
                "precision": "year",
                "news_days": len(news[name]),
                "news_dense_days": news_dense,
                "social_days": len(social[name]),
                "social_dense_days": social_dense,
                "clears_bar": news_dense >= 14 or social_dense >= 14,
                "added_to_graph": False,
            }
        )
    OUT.write_text(json.dumps({"checked_on": "2026-10-14", "rows": rows}, indent=2))
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()

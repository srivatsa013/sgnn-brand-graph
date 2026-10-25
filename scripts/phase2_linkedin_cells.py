"""Insert LinkedIn Arm A cells from 2016-06-13. Does not rebuild series.sqlite.

News is the headline alias, scored with VADER on the headline only.
Social is the LNKD cashtag or the LinkedIn alias, one message once.
A cell with exclude_brand Microsoft drops documents that mention Microsoft.
"""

from __future__ import annotations

import re
import sqlite3
from datetime import date
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "interim" / "phase2" / "series.sqlite"
START = "2016-06-13"
ALIAS = re.compile(r"\bLinkedIn\b", re.I)
MICROSOFT = re.compile(r"\bMicrosoft\b", re.I)
BRANDS = {
    "Apple": (re.compile(r"\bApple\b"), {"AAPL"}),
    "Microsoft": (MICROSOFT, {"MSFT"}),
    "Alphabet": (re.compile(r"\b(?:Alphabet|Google)\b"), {"GOOG", "GOOGL"}),
    "Tesla": (re.compile(r"\bTesla\b"), {"TSLA"}),
}


def accumulate(bucket: dict, key: tuple, day: str, score: float | None) -> None:
    rec = bucket.get(key)
    if rec is None:
        rec = {}
        bucket[key] = rec
    cell = rec.get(day)
    if cell is None:
        cell = [0.0, 0, 0]
        rec[day] = cell
    cell[2] += 1
    if score is not None:
        cell[0] += score
        cell[1] += 1


def keep(day: str | None) -> bool:
    return bool(day) and day >= START


def brands_in(text: str, tickers: set[str]) -> set[str]:
    found = set()
    for name, (pattern, symbols) in BRANDS.items():
        if tickers & symbols or (text and pattern.search(text)):
            found.add(name)
    return found


def flush(con: sqlite3.Connection, bucket: dict, source: str) -> int:
    rows = []
    n = 0
    for (node, exclude), days in bucket.items():
        for day, rec in days.items():
            rows.append((source, node, exclude, day, rec[0], rec[1], rec[2]))
            n += 1
    con.executemany(
        """
        INSERT INTO cell(source, node, exclude_brand, day, score_sum, scored, mentions)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(source, node, exclude_brand, day) DO UPDATE SET
          score_sum = excluded.score_sum,
          scored = excluded.scored,
          mentions = excluded.mentions
        """,
        rows,
    )
    return n


def news(bucket: dict) -> int:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

    analyzer = SentimentIntensityAnalyzer()
    docs = 0
    parts = sorted((ROOT / "data" / "raw" / "fnspid" / "parts").glob("*.parquet"))
    for path in parts:
        pf = pq.ParquetFile(path)
        for batch in pf.iter_batches(batch_size=4000, columns=["day_utc", "ticker", "headline", "summary", "text"]):
            data = batch.to_pydict()
            for i, day in enumerate(data["day_utc"]):
                if not keep(day):
                    continue
                ticker = (data["ticker"][i] or "").strip().upper()
                headline = data["headline"][i] or ""
                blob = " ".join(part for part in (headline, data["summary"][i] or "", data["text"][i] or "") if part)
                if ticker != "LNKD" and not ALIAS.search(blob):
                    continue
                docs += 1
                score = float(analyzer.polarity_scores(headline)["compound"]) if headline else None
                present = {ticker} if ticker else set()
                mentioned = brands_in(blob, present)
                accumulate(bucket, ("LinkedIn", ""), day, score)
                for brand in BRANDS:
                    if brand not in mentioned:
                        accumulate(bucket, ("LinkedIn", brand), day, score)
        print("news", path.name, "linkedin_docs", docs, flush=True)
    return docs


def social(con: sqlite3.Connection, bucket: dict) -> tuple[int, int]:
    seen = set()
    docs = 0
    for path in sorted((ROOT / "data" / "raw" / "stocktwits" / "bodies").glob("*.parquet")):
        table = pq.read_table(path, columns=["message_id", "message_body"])
        ids = table.column("message_id").to_pylist()
        bodies = table.column("message_body").to_pylist()
        if not ids:
            continue
        meta = {
            row[0]: (row[1], row[2], row[3])
            for row in con.execute(
                "SELECT message_id, day, score, tags FROM feat WHERE message_id BETWEEN ? AND ?",
                (min(ids), max(ids)),
            )
        }
        for message_id, body in zip(ids, bodies):
            info = meta.get(message_id)
            if not info or not keep(info[0]):
                continue
            day, score, tags = info
            present = {t for t in (tags or "").split("|") if t}
            text = body or ""
            if "LNKD" not in present and not ALIAS.search(text):
                continue
            seen.add(message_id)
            docs += 1
            mentioned = brands_in(text, present)
            accumulate(bucket, ("LinkedIn", ""), day, score)
            for brand in BRANDS:
                if brand not in mentioned:
                    accumulate(bucket, ("LinkedIn", brand), day, score)
        print("social bodies", path.name, "linkedin", docs, flush=True)
    extra = 0
    for message_id, day, score, tags in con.execute("SELECT message_id, day, score, tags FROM feat"):
        if message_id in seen or not keep(day):
            continue
        present = {t for t in (tags or "").split("|") if t}
        if "LNKD" not in present:
            continue
        extra += 1
        mentioned = brands_in("", present)
        accumulate(bucket, ("LinkedIn", ""), day, score)
        for brand in BRANDS:
            if brand not in mentioned:
                accumulate(bucket, ("LinkedIn", brand), day, score)
    return docs, extra


def main() -> None:
    con = sqlite3.connect(DB)
    con.execute("DELETE FROM cell WHERE node = 'LinkedIn'")
    bucket: dict = {}
    docs = news(bucket)
    n = flush(con, bucket, "news")
    con.commit()
    print("news cells", n, "docs", docs, flush=True)
    bucket = {}
    body_docs, cashtag_only = social(con, bucket)
    n = flush(con, bucket, "social")
    con.commit()
    rows = con.execute(
        """
        SELECT source, exclude_brand, COUNT(*), SUM(scored), SUM(mentions), MIN(day), MAX(day)
        FROM cell WHERE node='LinkedIn' GROUP BY 1, 2 ORDER BY 1, 2
        """
    ).fetchall()
    dense = con.execute(
        """
        SELECT source, exclude_brand, SUM(scored >= 14)
        FROM cell WHERE node='LinkedIn' GROUP BY 1, 2
        """
    ).fetchall()
    con.close()
    print("social cells", n, "body_docs", body_docs, "cashtag_only", cashtag_only, flush=True)
    print("rows", rows, flush=True)
    print("dense", dense, flush=True)


if __name__ == "__main__":
    main()

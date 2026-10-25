"""Daily series for Phase 2 pair counts and co-mention edges.

Brand events use the Phase 1 rule. Target windows later drop documents
that mention the event entity. This script only stores counts. It does
not compute a shift.
"""

from __future__ import annotations

import json
import re
import sqlite3
import sys
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from phase1_gates import detect_daily, label_score  # noqa: E402

UNI = json.loads((ROOT / "configs" / "phase1_universe.json").read_text())
NODES = json.loads((ROOT / "configs" / "phase2_nodes.json").read_text())
OUT = ROOT / "data" / "interim" / "phase2"
DB = OUT / "series.sqlite"


def patterns_from_universe() -> list[tuple[str, re.Pattern]]:
    out = []
    nodes = dict(UNI["alias_nodes"])
    for name, spec in nodes.items():
        aliases = spec.get("aliases") or []
        if not aliases:
            continue
        parts = [r"\b" + re.escape(alias) + r"\b" for alias in aliases]
        out.append((name, re.compile("|".join(parts), re.IGNORECASE)))
    brand = []
    for eco, spec in NODES["ecosystems"].items():
        parts = [r"\b" + re.escape(alias) + r"\b" for alias in spec["brand_aliases"]]
        brand.append((eco, re.compile("|".join(parts), re.IGNORECASE)))
    return out, brand


def ticker_nodes() -> dict[str, str]:
    mapping = {}
    for eco, spec in NODES["ecosystems"].items():
        for ticker in spec["brand_tickers"]:
            mapping[ticker] = eco if eco != "Alphabet" else "Alphabet"
        for ticker in spec["competitor_nodes"]:
            if ticker == "Meta":
                continue
            mapping[ticker] = ticker
    mapping["FB"] = "Meta"
    mapping["META"] = "Meta"
    mapping["GOOG"] = "Alphabet"
    mapping["GOOGL"] = "Alphabet"
    return mapping


def ecosystem_of(node: str) -> str | None:
    for eco, spec in NODES["ecosystems"].items():
        if node == eco:
            return eco
        if node in spec["positive_nodes"] or node in spec["competitor_nodes"]:
            return eco
    return None


def add(con: sqlite3.Connection, source: str, node: str, exclude: str, day: str, score: float | None) -> None:
    scored = 0 if score is None else 1
    value = 0.0 if score is None else float(score)
    con.execute(
        """
        INSERT INTO cell(source, node, exclude_brand, day, score_sum, scored, mentions)
        VALUES (?, ?, ?, ?, ?, ?, 1)
        ON CONFLICT(source, node, exclude_brand, day) DO UPDATE SET
          score_sum = score_sum + excluded.score_sum,
          scored = scored + excluded.scored,
          mentions = mentions + 1
        """,
        (source, node, exclude, day, value, scored),
    )


def add_pair(con: sqlite3.Connection, source: str, a: str, b: str, day: str) -> None:
    if a == b:
        return
    left, right = (a, b) if a < b else (b, a)
    con.execute(
        """
        INSERT INTO comention(source, node_a, node_b, day, n)
        VALUES (?, ?, ?, ?, 1)
        ON CONFLICT(source, node_a, node_b, day) DO UPDATE SET n = n + 1
        """,
        (source, left, right, day),
    )


def brands_mentioned(tickers_present: set[str], text: str, brand_patterns) -> set[str]:
    found = set()
    for eco, spec in NODES["ecosystems"].items():
        if tickers_present & set(spec["brand_tickers"]):
            found.add(eco)
    if text:
        for eco, pattern in brand_patterns:
            if pattern.search(text):
                found.add(eco)
    return found


def node_hits(ticker_map: dict[str, str], tickers_present: set[str], text: str, alias_patterns) -> set[str]:
    hits = set()
    for ticker in tickers_present:
        node = ticker_map.get(ticker)
        if node:
            hits.add(node)
    if text:
        for name, pattern in alias_patterns:
            if pattern.search(text):
                hits.add(name)
    return hits


def flush(con: sqlite3.Connection, rows: list[tuple], pairs: list[tuple]) -> None:
    if rows:
        con.executemany(
            """
            INSERT INTO cell(source, node, exclude_brand, day, score_sum, scored, mentions)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source, node, exclude_brand, day) DO UPDATE SET
              score_sum = score_sum + excluded.score_sum,
              scored = scored + excluded.scored,
              mentions = mentions + excluded.mentions
            """,
            rows,
        )
    if pairs:
        con.executemany(
            """
            INSERT INTO comention(source, node_a, node_b, day, n)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(source, node_a, node_b, day) DO UPDATE SET n = n + excluded.n
            """,
            pairs,
        )


def accumulate(bucket: dict, key: tuple, day: str, score: float | None, mentions: int = 1) -> None:
    cell = bucket.get(key)
    if cell is None:
        cell = {}
        bucket[key] = cell
    rec = cell.get(day)
    if rec is None:
        rec = [0.0, 0, 0]
        cell[day] = rec
    rec[2] += mentions
    if score is not None:
        rec[0] += score
        rec[1] += 1


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    if DB.exists():
        DB.unlink()
    con = sqlite3.connect(DB)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    con.execute(
        """
        CREATE TABLE cell (
          source TEXT, node TEXT, exclude_brand TEXT, day TEXT,
          score_sum REAL, scored INT, mentions INT,
          PRIMARY KEY (source, node, exclude_brand, day)
        )
        """
    )
    con.execute(
        """
        CREATE TABLE comention (
          source TEXT, node_a TEXT, node_b TEXT, day TEXT, n INT,
          PRIMARY KEY (source, node_a, node_b, day)
        )
        """
    )
    alias_patterns, brand_patterns = patterns_from_universe()
    ticker_map = ticker_nodes()
    brand_names = list(NODES["ecosystems"])
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

    analyzer = SentimentIntensityAnalyzer()
    news_bucket: dict = {}
    pair_bucket: dict = {}
    parts = sorted((ROOT / "data" / "raw" / "fnspid" / "parts").glob("*.parquet"))
    news_rows = 0
    for path in parts:
        pf = pq.ParquetFile(path)
        for batch in pf.iter_batches(batch_size=2000):
            data = batch.to_pydict()
            for i, day in enumerate(data["day_utc"]):
                if not day:
                    continue
                news_rows += 1
                ticker = (data["ticker"][i] or "").strip().upper()
                present = {ticker} if ticker else set()
                headline = data["headline"][i] or ""
                blob = " ".join(
                    part for part in (headline, data["summary"][i] or "", data["text"][i] or "") if part
                )
                score = float(analyzer.polarity_scores(headline)["compound"])
                hits = node_hits(ticker_map, present, blob, alias_patterns)
                brands = brands_mentioned(present, blob, brand_patterns)
                for node in hits:
                    accumulate(news_bucket, (node, ""), day, score)
                    for brand in brand_names:
                        if brand not in brands:
                            accumulate(news_bucket, (node, brand), day, score)
                eco_hits: dict[str, list[str]] = {}
                for node in hits:
                    eco = ecosystem_of(node)
                    if eco:
                        eco_hits.setdefault(eco, []).append(node)
                for group in eco_hits.values():
                    group = sorted(set(group))
                    for a_i, left in enumerate(group):
                        for right in group[a_i + 1 :]:
                            key = ("news", left, right, day)
                            pair_bucket[key] = pair_bucket.get(key, 0) + 1
        print(f"news {path.name} rows {news_rows}", flush=True)
    cell_rows = []
    for (node, exclude), days in news_bucket.items():
        for day, rec in days.items():
            cell_rows.append(("news", node, exclude, day, rec[0], rec[1], rec[2]))
            if len(cell_rows) >= 50000:
                flush(con, cell_rows, [])
                cell_rows.clear()
    pair_rows = [(src, a, b, day, n) for (src, a, b, day), n in pair_bucket.items()]
    flush(con, cell_rows, pair_rows)
    con.commit()
    print("news stored", news_rows, "pair days", len(pair_rows), flush=True)

    # Social: cashtags from features, aliases from bodies, one count per message.
    con.execute("CREATE TABLE feat (message_id INTEGER PRIMARY KEY, day TEXT, score REAL, tags TEXT)")
    batch = []
    for path in sorted((ROOT / "data" / "raw" / "stocktwits" / "features").glob("*.parquet")):
        table = pq.read_table(path, columns=["message_id", "day_utc", "sentiment", "cashtags"])
        for message_id, day, sentiment, tags in zip(
            table.column("message_id").to_pylist(),
            table.column("day_utc").to_pylist(),
            table.column("sentiment").to_pylist(),
            table.column("cashtags").to_pylist(),
        ):
            batch.append((message_id, day, label_score(sentiment), tags or ""))
            if len(batch) >= 50000:
                con.executemany("INSERT OR REPLACE INTO feat VALUES (?,?,?,?)", batch)
                batch.clear()
    if batch:
        con.executemany("INSERT OR REPLACE INTO feat VALUES (?,?,?,?)", batch)
    con.commit()
    print("features indexed", flush=True)

    seen = set()
    social_messages = 0
    body_bucket: dict = {}
    social_pairs: dict = {}
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
            if not info or not info[0]:
                continue
            day, score, tags = info
            present = {t for t in (tags or "").split("|") if t}
            hits = node_hits(ticker_map, present, body or "", alias_patterns)
            brands = brands_mentioned(present, body or "", brand_patterns)
            seen.add(message_id)
            social_messages += 1
            for node in hits:
                accumulate(body_bucket, (node, ""), day, score)
                for brand in brand_names:
                    if brand not in brands:
                        accumulate(body_bucket, (node, brand), day, score)
            grouped: dict[str, list[str]] = {}
            for node in hits:
                eco = ecosystem_of(node)
                if eco:
                    grouped.setdefault(eco, []).append(node)
            for group in grouped.values():
                group = sorted(set(group))
                for a_i, left in enumerate(group):
                    for right in group[a_i + 1 :]:
                        key = ("social", left, right, day)
                        social_pairs[key] = social_pairs.get(key, 0) + 1
        print(f"bodies {path.name} messages {social_messages}", flush=True)
    # Cashtag-only messages whose body file was not retained.
    extra = 0
    for message_id, day, score, tags in con.execute("SELECT message_id, day, score, tags FROM feat"):
        if message_id in seen or not day:
            continue
        present = {t for t in (tags or "").split("|") if t}
        hits = node_hits(ticker_map, present, "", alias_patterns)
        brands = brands_mentioned(present, "", brand_patterns)
        extra += 1
        for node in hits:
            accumulate(body_bucket, (node, ""), day, score)
            for brand in brand_names:
                if brand not in brands:
                    accumulate(body_bucket, (node, brand), day, score)
        grouped = {}
        for node in hits:
            eco = ecosystem_of(node)
            if eco:
                grouped.setdefault(eco, []).append(node)
        for group in grouped.values():
            group = sorted(set(group))
            for a_i, left in enumerate(group):
                for right in group[a_i + 1 :]:
                    key = ("social", left, right, day)
                    social_pairs[key] = social_pairs.get(key, 0) + 1
    print("cashtag-only messages", extra, flush=True)
    cell_rows = []
    for (node, exclude), days in body_bucket.items():
        for day, rec in days.items():
            cell_rows.append(("social", node, exclude, day, rec[0], rec[1], rec[2]))
            if len(cell_rows) >= 50000:
                flush(con, cell_rows, [])
                cell_rows.clear()
    pair_rows = [(src, a, b, day, n) for (src, a, b, day), n in social_pairs.items()]
    flush(con, cell_rows, pair_rows)
    con.commit()

    events = {}
    for eco, spec in NODES["ecosystems"].items():
        events[eco] = {}
        for source in ("news", "social"):
            series = series_of(con, source, eco, "")
            found = [day.isoformat() for day in detect_daily(series)]
            events[eco][source] = found
            print(eco, source, "events", len(found), flush=True)
    (OUT / "brand_events.json").write_text(json.dumps(events, indent=2))
    con.close()


def series_of(con: sqlite3.Connection, source: str, node: str, exclude: str) -> dict:
    out = {}
    for day, score_sum, scored, mentions in con.execute(
        "SELECT day, score_sum, scored, mentions FROM cell WHERE source=? AND node=? AND exclude_brand=?",
        (source, node, exclude),
    ):
        out[day] = [score_sum, scored, mentions]
    return out


if __name__ == "__main__":
    main()

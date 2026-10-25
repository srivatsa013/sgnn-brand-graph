"""Fill Arm A social and VADER cells the control pass stored under a ticker.

The brand event series is the ticker rows and the cashtag rows. Those cells
were written under NKE, CMG, and the other control tickers. Counts ask for
the ecosystem name. This script copies that series onto the ecosystem name
and writes the exclude-brand cells the pair counter reads. Samsung and
Adidas have no such ticker cells, so they are built from the extracts.
Existing cells are not rewritten. No shift is computed.
"""

from __future__ import annotations

import json
import re
import shutil
import sqlite3
import sys
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from phase2_build_series import accumulate, brands_mentioned, patterns_from_universe  # noqa: E402
from phase2_feasibility import NODES  # noqa: E402
from phase2_gdelt_reserve_after import controls_for  # noqa: E402
from phase2_revised_recount import build_adj  # noqa: E402

DB = ROOT / "data" / "interim" / "phase2" / "series.sqlite"
STATUS = ROOT / "eval" / "results" / "phase4_missing_series.status.json"
DISK_PAUSE = 6_000_000_000
NEW_BRANDS = (
    "Chipotle",
    "T-Mobile US",
    "Lowe's",
    "Mastercard",
    "Chevron",
    "Hershey",
    "Colgate-Palmolive",
    "Eli Lilly",
    "Nike",
    "John Deere",
)
NAME_NODES = {"Samsung": re.compile(r"\bSamsung\b", re.IGNORECASE), "Adidas": re.compile(r"\bAdidas\b", re.IGNORECASE)}


def ticker_of(eco: str) -> str:
    tickers = NODES["ecosystems"][eco]["brand_tickers"]
    if len(tickers) != 1:
        raise SystemExit(f"{eco} does not have one brand ticker")
    return tickers[0]


def copy_cells(con: sqlite3.Connection, source: str, src_node: str, src_exclude: str, dst_node: str, dst_exclude: str) -> int:
    before = con.execute(
        "SELECT COUNT(*) FROM cell WHERE source=? AND node=? AND exclude_brand=?",
        (source, dst_node, dst_exclude),
    ).fetchone()[0]
    if before:
        return 0
    con.execute(
        """
        INSERT INTO cell(source, node, exclude_brand, day, score_sum, scored, mentions)
        SELECT source, ?, ?, day, score_sum, scored, mentions
        FROM cell
        WHERE source=? AND node=? AND exclude_brand=?
        """,
        (dst_node, dst_exclude, source, src_node, src_exclude),
    )
    return con.execute("SELECT changes()").fetchone()[0]


def nodes_for(eco: str, adj: dict, pool: dict) -> list[str]:
    spec = NODES["ecosystems"][eco]
    names = list(spec["positive_nodes"]) + list(spec["competitor_nodes"]) + controls_for(eco, adj, pool)
    seen = set()
    out = []
    for name in names:
        if name not in seen:
            seen.add(name)
            out.append(name)
    return out


def apply_delta(con: sqlite3.Connection, source: str, node: str, exclude: str, day: str, score: float, scored: int, mentions: int) -> None:
    row = con.execute(
        "SELECT score_sum, scored, mentions FROM cell WHERE source=? AND node=? AND exclude_brand=? AND day=?",
        (source, node, exclude, day),
    ).fetchone()
    if row is None:
        return
    score_sum, scored_now, mentions_now = row
    if scored_now < scored or mentions_now < mentions:
        raise SystemExit(f"subtract past zero for {source} {node} {exclude} {day}")
    con.execute(
        """
        UPDATE cell
        SET score_sum = ?, scored = ?, mentions = ?
        WHERE source=? AND node=? AND exclude_brand=? AND day=?
        """,
        (score_sum - score, scored_now - scored, mentions_now - mentions, source, node, exclude, day),
    )


def main() -> None:
    if shutil.disk_usage(ROOT).free < DISK_PAUSE:
        raise SystemExit("free disk under 6 GB")
    status = json.loads(STATUS.read_text()) if STATUS.exists() else {}
    alias_patterns, brand_patterns = patterns_from_universe()
    del alias_patterns
    brand_alias = {eco: pattern for eco, pattern in brand_patterns}
    prefilter = re.compile("|".join(pattern.pattern for pattern in list(brand_alias.values()) + list(NAME_NODES.values())))
    pool = json.loads((ROOT / "configs" / "phase1_universe.json").read_text())["control_pool_by_bucket"]
    adj = build_adj(True, True)
    con = sqlite3.connect(DB)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    con.execute("PRAGMA busy_timeout=60000")
    if not status.get("copied"):
        copied = 0
        for eco in NEW_BRANDS:
            ticker = ticker_of(eco)
            for source in ("news", "social"):
                copied += copy_cells(con, source, ticker, "", eco, "")
            for node in nodes_for(eco, adj, pool):
                for source in ("news", "social"):
                    copied += copy_cells(con, source, node, "", node, eco)
            con.commit()
            print(f"copied through {eco}", flush=True)
        status["copied"] = True
        status["copied_rows"] = copied
        STATUS.write_text(json.dumps(status) + "\n")
        print(f"copy rows {copied}", flush=True)
    if status.get("subtracted"):
        con.close()
        print("already subtracted", flush=True)
        return
    subtract_nodes = {eco: set(nodes_for(eco, adj, pool)) for eco in NEW_BRANDS}
    news_delta: dict[tuple, list] = {}
    name_bucket: dict = {}
    rows = 0
    hits = 0
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

    analyzer = SentimentIntensityAnalyzer()
    for path in sorted((ROOT / "data" / "raw" / "fnspid" / "parts").glob("*.parquet")):
        pf = pq.ParquetFile(path)
        for batch in pf.iter_batches(batch_size=4000, columns=["day_utc", "ticker", "headline", "summary", "text"]):
            data = batch.to_pydict()
            for i, day in enumerate(data["day_utc"]):
                if not day:
                    continue
                rows += 1
                headline = data["headline"][i] or ""
                summary = data["summary"][i] or ""
                body = data["text"][i] or ""
                blob = " ".join(part for part in (headline, summary, body) if part)
                if not blob or prefilter.search(blob) is None:
                    continue
                hits += 1
                ticker = (data["ticker"][i] or "").strip().upper()
                present = {ticker} if ticker else set()
                brands = brands_mentioned(present, blob, brand_patterns)
                score = None
                for eco in NEW_BRANDS:
                    if eco not in brands or ticker not in subtract_nodes[eco]:
                        continue
                    if score is None:
                        score = float(analyzer.polarity_scores(headline)["compound"])
                    rec = news_delta.get((ticker, eco, day))
                    if rec is None:
                        rec = [0.0, 0, 0]
                        news_delta[(ticker, eco, day)] = rec
                    rec[0] += score
                    rec[1] += 1
                    rec[2] += 1
                for name, pattern in NAME_NODES.items():
                    if pattern.search(headline) is None:
                        continue
                    if score is None:
                        score = float(analyzer.polarity_scores(headline)["compound"])
                    accumulate(name_bucket, ("news", name, ""), day, score)
                    for eco in NODES["ecosystems"]:
                        if eco not in brands:
                            accumulate(name_bucket, ("news", name, eco), day, score)
        print(f"news {path.name} rows {rows} hits {hits} deltas {len(news_delta)}", flush=True)
    print(f"news scan rows {rows} hits {hits}", flush=True)
    social_delta: dict[tuple, list] = {}
    for message_id, day, score, tags in con.execute("SELECT message_id, day, score, tags FROM feat"):
        if not day:
            continue
        present = {part for part in (tags or "").split("|") if part}
        if not present:
            continue
        brands = brands_mentioned(present, "", brand_patterns)
        if "SSNLF" in present:
            accumulate(name_bucket, ("social", "Samsung", ""), day, score)
            for eco in NODES["ecosystems"]:
                if eco not in brands:
                    accumulate(name_bucket, ("social", "Samsung", eco), day, score)
        for eco, nodes in subtract_nodes.items():
            if eco not in brands:
                continue
            for ticker in present & nodes:
                rec = social_delta.get((ticker, eco, day))
                if rec is None:
                    rec = [0.0, 0, 0]
                    social_delta[(ticker, eco, day)] = rec
                if score is not None:
                    rec[0] += float(score)
                    rec[1] += 1
                rec[2] += 1
        if message_id % 5000000 == 0:
            print(f"feat {message_id}", flush=True)
    print(f"cashtag deltas {len(social_delta)}", flush=True)
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
            if not info or not info[0] or not body:
                continue
            if prefilter.search(body) is None:
                continue
            day, score, tags = info
            present = {part for part in (tags or "").split("|") if part}
            brands = brands_mentioned(present, body, brand_patterns)
            for eco, nodes in subtract_nodes.items():
                if eco not in brands or brand_alias[eco].search(body) is None:
                    continue
                # A cashtag mention was already subtracted from the feature pass.
                if set(NODES["ecosystems"][eco]["brand_tickers"]) & present:
                    continue
                for ticker in present & nodes:
                    rec = social_delta.get((ticker, eco, day))
                    if rec is None:
                        rec = [0.0, 0, 0]
                        social_delta[(ticker, eco, day)] = rec
                    if score is not None:
                        rec[0] += float(score)
                        rec[1] += 1
                    rec[2] += 1
            if NAME_NODES["Adidas"].search(body):
                accumulate(name_bucket, ("social", "Adidas", ""), day, score)
                for eco in NODES["ecosystems"]:
                    if eco not in brands:
                        accumulate(name_bucket, ("social", "Adidas", eco), day, score)
        print(f"bodies {path.name}", flush=True)
    print(f"applying news deltas {len(news_delta)} social deltas {len(social_delta)}", flush=True)
    for (node, eco, day), rec in news_delta.items():
        apply_delta(con, "news", node, eco, day, rec[0], rec[1], rec[2])
    for (node, eco, day), rec in social_delta.items():
        apply_delta(con, "social", node, eco, day, rec[0], rec[1], rec[2])
    fresh = []
    for (source, node, exclude), days in name_bucket.items():
        for day, rec in days.items():
            fresh.append((source, node, exclude, day, rec[0], rec[1], rec[2]))
    if fresh:
        con.executemany(
            """
            INSERT INTO cell(source, node, exclude_brand, day, score_sum, scored, mentions)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source, node, exclude_brand, day) DO NOTHING
            """,
            fresh,
        )
    con.commit()
    con.close()
    status["subtracted"] = True
    status["news_deltas"] = len(news_delta)
    status["social_deltas"] = len(social_delta)
    status["name_node_rows"] = len(fresh)
    STATUS.write_text(json.dumps(status) + "\n")
    print(f"stored name-node rows {len(fresh)}", flush=True)


if __name__ == "__main__":
    main()

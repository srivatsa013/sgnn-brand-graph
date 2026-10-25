"""Control-ticker daily cells for the Phase 2 caliper check.

Brand series are already in series.sqlite. This pass adds control tickers
only. A cell with exclude_brand set drops documents that mention that
brand. No shift is computed.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from phase2_build_series import accumulate, brands_mentioned, flush, patterns_from_universe  # noqa: E402

UNI = json.loads((ROOT / "configs" / "phase1_universe.json").read_text())
DB = ROOT / "data" / "interim" / "phase2" / "series.sqlite"


def main() -> None:
    social_only = "--social-only" in sys.argv
    controls = []
    for names in UNI["control_pool_by_bucket"].values():
        controls.extend(names)
    controls = set(controls)
    _, brand_patterns = patterns_from_universe()
    brand_names = list(json.loads((ROOT / "configs" / "phase2_nodes.json").read_text())["ecosystems"])
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

    analyzer = SentimentIntensityAnalyzer()
    con = sqlite3.connect(DB)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    bucket: dict = {}
    rows = 0
    if social_only:
        print("skipping control news; those cells are already stored", flush=True)
    if not social_only:
        for path in sorted((ROOT / "data" / "raw" / "fnspid" / "parts").glob("*.parquet")):
            pf = pq.ParquetFile(path)
            for batch in pf.iter_batches(batch_size=2000, columns=["day_utc", "ticker", "headline", "summary", "text"]):
                data = batch.to_pydict()
                for i, day in enumerate(data["day_utc"]):
                    ticker = (data["ticker"][i] or "").strip().upper()
                    if not day or ticker not in controls:
                        continue
                    rows += 1
                    headline = data["headline"][i] or ""
                    blob = " ".join(part for part in (headline, data["summary"][i] or "", data["text"][i] or "") if part)
                    score = float(analyzer.polarity_scores(headline)["compound"])
                    brands = brands_mentioned({ticker}, blob, brand_patterns)
                    accumulate(bucket, (ticker, ""), day, score)
                    for brand in brand_names:
                        if brand not in brands:
                            accumulate(bucket, (ticker, brand), day, score)
            print(f"control news {path.name} rows {rows}", flush=True)
    cell_rows = []
    for (node, exclude), days in bucket.items():
        for day, rec in days.items():
            cell_rows.append(("news", node, exclude, day, rec[0], rec[1], rec[2]))
            if len(cell_rows) >= 50000:
                flush(con, cell_rows, [])
                cell_rows.clear()
    flush(con, cell_rows, [])
    con.commit()
    print("control news stored", rows, flush=True)

    bucket = {}
    messages = 0
    features = {path.name: path for path in (ROOT / "data" / "raw" / "stocktwits" / "features").glob("*.parquet")}
    # Bodies carry the ids that need an alias check. Cashtag-only messages are read from features.
    from phase1_gates import label_score

    seen = set()
    for path in sorted((ROOT / "data" / "raw" / "stocktwits" / "bodies").glob("*.parquet")):
        table = pq.read_table(path, columns=["message_id", "message_body"])
        ids = table.column("message_id").to_pylist()
        bodies = table.column("message_body").to_pylist()
        if not ids:
            continue
        # Feature files are not id-aligned with body files, so use the feat table written by the series script.
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
            hit = present & controls
            if not hit:
                continue
            seen.add(message_id)
            messages += 1
            brands = brands_mentioned(present, body or "", brand_patterns)
            for ticker in hit:
                accumulate(bucket, (ticker, ""), day, score)
                for brand in brand_names:
                    if brand not in brands:
                        accumulate(bucket, (ticker, brand), day, score)
        print(f"control bodies {path.name} messages {messages}", flush=True)
    extra = 0
    for message_id, day, score, tags in con.execute("SELECT message_id, day, score, tags FROM feat"):
        if message_id in seen or not day:
            continue
        present = {t for t in (tags or "").split("|") if t}
        hit = present & controls
        if not hit:
            continue
        extra += 1
        brands = brands_mentioned(present, "", brand_patterns)
        for ticker in hit:
            accumulate(bucket, (ticker, ""), day, score)
            for brand in brand_names:
                if brand not in brands:
                    accumulate(bucket, (ticker, brand), day, score)
    print("control cashtag-only", extra, flush=True)
    cell_rows = []
    for (node, exclude), days in bucket.items():
        for day, rec in days.items():
            cell_rows.append(("social", node, exclude, day, rec[0], rec[1], rec[2]))
            if len(cell_rows) >= 50000:
                flush(con, cell_rows, [])
                cell_rows.clear()
    flush(con, cell_rows, [])
    con.commit()
    con.close()
    print("control social messages", messages, "cashtag-only", extra, flush=True)
    del features


if __name__ == "__main__":
    main()

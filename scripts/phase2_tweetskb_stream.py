"""Stream one TweetsKB monthly file into daily aggregates. Resumable.

Keeps per-entity per-day count, scored count, and score sum, plus the
study-node list of each matching tweet. Deletes the compressed file after
a successful reduce. Does not download the next file.
"""

from __future__ import annotations

import gzip
import json
import re
import sqlite3
import time
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOW = ROOT / "configs" / "scan_allowlist.json"
RAW = ROOT / "data" / "interim" / "tweetskb_raw"
DB = ROOT / "data" / "interim" / "phase2" / "tweetskb_full.sqlite"
DONE = ROOT / "eval" / "results" / "tweetskb_stream_done.json"
STATUS = ROOT / "eval" / "results" / "tweetskb_download.status.json"
MONTHS = ROOT / "eval" / "results" / "tweetskb_month_stats.jsonl"

HEX = r"[0-9a-fA-F]+"
POST = re.compile(rf"_:t({HEX}) rdf:type sioc:Post ; dc:created \"(\d{{4}}-\d{{2}}-\d{{2}})")
POS = re.compile(
    rf"_:em({HEX})Pos onyx:hasEmotionCategory wna:positive-emotion ; onyx:hasEmotionIntensity \"([0-9.eE+-]+)\""
)
NEG = re.compile(
    rf"_:em({HEX})Neg onyx:hasEmotionCategory wna:negative-emotion ; onyx:hasEmotionIntensity \"([0-9.eE+-]+)\""
)
MENTION = re.compile(rf"_:t({HEX}) schema:mentions _:e({HEX})_(\d+)")
URI = re.compile(rf"_:e({HEX})_(\d+) rdf:type nee:Entity ;.*?nee:hasMatchedURI <([^>]+)>")


def load_uris() -> dict[str, str]:
    allow = json.loads(ALLOW.read_text())
    found = {}
    for row in allow["nodes"]:
        uri = row.get("dbpedia")
        if not uri:
            continue
        found[uri] = row["name"]
        found[urllib.parse.unquote(uri)] = row["name"]
    return found


def flush_tweet(state: dict, out: dict) -> None:
    tweet = state.get("id")
    if not tweet or not state.get("uris"):
        return
    names = sorted({out["uris"][uri] for uri in state["uris"] if uri in out["uris"]})
    if not names:
        return
    day = state.get("day")
    if not day:
        return
    pos = state.get("pos")
    neg = state.get("neg")
    score = None if pos is None and neg is None else (pos or 0.0) - (neg or 0.0)
    for name in names:
        cell = out["days"].setdefault((name, day), [0, 0, 0.0])
        cell[0] += 1
        if score is not None:
            cell[1] += 1
            cell[2] += score
    out["tweets"].append((tweet, day, "|".join(names), score))


def reduce_file(path: Path, uris: dict[str, str], allow_truncated: bool = False) -> dict:
    out = {"uris": uris, "days": {}, "tweets": []}
    state: dict = {}
    t0 = time.time()
    lines = 0
    posts = 0
    entity_rows = 0
    try:
        with gzip.open(path, "rt", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                lines += 1
                if line.startswith("@prefix") or not line.strip():
                    continue
                post = POST.search(line)
                if post:
                    flush_tweet(state, out)
                    posts += 1
                    state = {"id": post.group(1), "day": post.group(2), "uris": set()}
                    continue
                pos = POS.search(line)
                if pos and state.get("id") == pos.group(1):
                    state["pos"] = float(pos.group(2))
                    continue
                neg = NEG.search(line)
                if neg and state.get("id") == neg.group(1):
                    state["neg"] = float(neg.group(2))
                    continue
                mention = MENTION.search(line)
                if mention and state.get("id") == mention.group(1):
                    continue
                matched = URI.search(line)
                if matched and state.get("id") == matched.group(1):
                    entity_rows += 1
                    state["uris"].add(urllib.parse.unquote(matched.group(3)))
                    state["uris"].add(matched.group(3))
    except EOFError:
        if not allow_truncated:
            raise
    flush_tweet(state, out)
    matched = len(out["tweets"])
    if lines > 1000 and posts == 0:
        raise SystemExit(f"{path.name}: read {lines} lines and parsed 0 posts; raw file kept")
    if posts > 1000 and matched == 0:
        raise SystemExit(f"{path.name}: parsed {posts} posts and matched 0; raw file kept")
    scored = sum(1 for row in out["tweets"] if row[3] is not None)
    entities = sorted({name for row in out["tweets"] for name in row[2].split("|") if name})
    return {
        "lines": lines,
        "posts": posts,
        "entity_rows": entity_rows,
        "matched": matched,
        "scored": scored,
        "entities": entities,
        "seconds": time.time() - t0,
        "days": out["days"],
        "tweets": out["tweets"],
    }


def store(path: Path, reduced: dict) -> None:
    con = sqlite3.connect(DB)
    con.execute("CREATE TABLE IF NOT EXISTS daily (entity TEXT, day TEXT, n INT, scored INT, score_sum REAL, PRIMARY KEY(entity, day))")
    con.execute("CREATE TABLE IF NOT EXISTS tweet (tweet_id TEXT PRIMARY KEY, day TEXT, entities TEXT, score REAL)")
    con.execute("CREATE TABLE IF NOT EXISTS file (name TEXT PRIMARY KEY, lines INT, seconds REAL, tweets INT)")
    rows = [(entity, day, rec[0], rec[1], rec[2]) for (entity, day), rec in reduced["days"].items()]
    con.executemany(
        """
        INSERT INTO daily(entity, day, n, scored, score_sum) VALUES (?,?,?,?,?)
        ON CONFLICT(entity, day) DO UPDATE SET
          n = n + excluded.n,
          scored = scored + excluded.scored,
          score_sum = score_sum + excluded.score_sum
        """,
        rows,
    )
    con.executemany("INSERT OR REPLACE INTO tweet(tweet_id, day, entities, score) VALUES (?,?,?,?)", reduced["tweets"])
    con.execute(
        "INSERT OR REPLACE INTO file(name, lines, seconds, tweets) VALUES (?,?,?,?)",
        (path.name, reduced["lines"], reduced["seconds"], len(reduced["tweets"])),
    )
    con.commit()
    con.close()


def main() -> None:
    done = json.loads(DONE.read_text()) if DONE.exists() else {"files": []}
    uris = load_uris()
    for path in sorted(RAW.glob("month_*.n3.gz")):
        if path.name in done["files"]:
            continue
        if path.stat().st_size < 1000:
            continue
        complete = set()
        if STATUS.exists():
            downloaded = json.loads(STATUS.read_text()).get("files") or {}
            complete = {name for name, row in downloaded.items() if row.get("complete")}
        if path.name not in complete:
            continue
        reduced = reduce_file(path, uris)
        if reduced["matched"] == 0:
            raise SystemExit(f"{path.name} matched 0 tweets; raw file kept")
        store(path, reduced)
        summary = {
            "file": path.name,
            "lines": reduced["lines"],
            "posts": reduced["posts"],
            "entity_rows": reduced["entity_rows"],
            "matched": reduced["matched"],
            "scored": reduced["scored"],
            "distinct_entities": len(reduced["entities"]),
            "entities": reduced["entities"],
            "seconds": round(reduced["seconds"], 3),
        }
        with MONTHS.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(summary) + "\n")
        print(json.dumps(summary), flush=True)
        path.unlink()
        done["files"].append(path.name)
        done["last"] = summary
        DONE.write_text(json.dumps(done, indent=2))


if __name__ == "__main__":
    main()

"""Rebuild CEO daily series with the logged tenure windows.

One document counts once for a CEO node. A person outside their window
does not count. News score is VADER on the headline. Social score is the
stored user label.
"""

from __future__ import annotations

import json
import re
import sqlite3
import sys
from datetime import date
from pathlib import Path

import pyarrow.parquet as pq
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

ROOT = Path(__file__).resolve().parents[1]
TENURES = json.loads((ROOT / "configs" / "ceo_tenures.json").read_text())
OUT = ROOT / "eval" / "results" / "ceo_windowed_arm_a.json"


def windows_for(person: dict) -> list[tuple[str, str | None, str]]:
    node_windows = []
    if "windows" in person:
        for window in person["windows"]:
            node_windows.append((window["start"], window["end"], person["person"]))
    else:
        node_windows.append((person["start"], person["end"], person["person"]))
    return node_windows


def load_rules() -> list[tuple[re.Pattern[str], str, str, str | None]]:
    rules = []
    for node, people in TENURES["nodes"].items():
        for person in people:
            for alias in person["aliases"]:
                pattern = re.compile(r"\b" + re.escape(alias) + r"\b")
                for start, end, _name in windows_for(person):
                    rules.append((pattern, node, start, end))
    return rules


def in_window(day: str, start: str, end: str | None) -> bool:
    if day < start:
        return False
    if end is not None and day > end:
        return False
    return True


def add(bucket: dict, node: str, day: str, score: float | None) -> None:
    cell = bucket.setdefault(node, {}).setdefault(day, [0.0, 0, 0])
    cell[2] += 1
    if score is not None:
        cell[0] += score
        cell[1] += 1


def pack(bucket: dict) -> dict:
    out = {}
    for node, days in bucket.items():
        out[node] = {
            "days": len(days),
            "mentions": sum(cell[2] for cell in days.values()),
            "scored": sum(cell[1] for cell in days.values()),
            "series": {day: cell for day, cell in sorted(days.items())},
        }
    return out


def main() -> None:
    rules = load_rules()
    news: dict = {}
    analyzer = SentimentIntensityAnalyzer()
    for path in sorted((ROOT / "data" / "raw" / "fnspid" / "parts").glob("*.parquet")):
        table = pq.read_table(path, columns=["headline", "summary", "text", "day_utc"])
        headlines = table.column("headline").to_pylist()
        summaries = table.column("summary").to_pylist()
        texts = table.column("text").to_pylist()
        days = table.column("day_utc").to_pylist()
        for headline, summary, body, day in zip(headlines, summaries, texts, days):
            if not day:
                continue
            blob = " ".join(part for part in (headline or "", summary or "", body or "") if part)
            if not blob:
                continue
            hit_nodes = set()
            for pattern, node, start, end in rules:
                if node in hit_nodes:
                    continue
                if in_window(day, start, end) and pattern.search(blob):
                    hit_nodes.add(node)
            if not hit_nodes:
                continue
            score = float(analyzer.polarity_scores(headline or "")["compound"])
            for node in hit_nodes:
                add(news, node, day, score)
        print("news", path.name, flush=True)
    if "--news-only" in sys.argv:
        packed = pack(news)
        previous = json.loads(OUT.read_text()) if OUT.exists() else {}
        previous["news"] = packed
        OUT.write_text(json.dumps(previous))
        for node, info in packed.items():
            print("news", node, "days", info["days"], "mentions", info["mentions"], flush=True)
        return

    social: dict = {}
    con = sqlite3.connect(ROOT / "data" / "interim" / "phase2" / "series.sqlite")
    for path in sorted((ROOT / "data" / "raw" / "stocktwits" / "bodies").glob("*.parquet")):
        table = pq.read_table(path, columns=["message_id", "message_body"])
        ids = table.column("message_id").to_pylist()
        bodies = table.column("message_body").to_pylist()
        pending = []
        for message_id, body in zip(ids, bodies):
            if not body:
                continue
            pending.append((message_id, body))
        if not pending:
            continue
        # Resolve days only for bodies that contain a CEO alias.
        matched = []
        for message_id, body in pending:
            if any(pattern.search(body) for pattern, *_rest in rules):
                matched.append((message_id, body))
        if not matched:
            continue
        id_list = [message_id for message_id, _body in matched]
        meta = {}
        for start in range(0, len(id_list), 500):
            chunk = id_list[start : start + 500]
            marks = ",".join("?" for _ in chunk)
            for message_id, day, score in con.execute(
                f"SELECT message_id, day, score FROM feat WHERE message_id IN ({marks})",
                chunk,
            ):
                meta[message_id] = (day, score)
        for message_id, body in matched:
            day, score = meta.get(message_id, (None, None))
            if not day:
                continue
            hit_nodes = set()
            for pattern, node, start, end in rules:
                if node in hit_nodes:
                    continue
                if in_window(day, start, end) and pattern.search(body):
                    hit_nodes.add(node)
            for node in hit_nodes:
                add(social, node, day, score)
        print("social", path.name, flush=True)

    OUT.write_text(json.dumps({"news": pack(news), "social": pack(social)}))
    for source, packed in ("news", pack(news)), ("social", pack(social)):
        for node, info in packed.items():
            print(source, node, "days", info["days"], "mentions", info["mentions"], flush=True)


if __name__ == "__main__":
    main()

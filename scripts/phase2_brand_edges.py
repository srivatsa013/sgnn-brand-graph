"""Wikidata check for the twelve candidate brands. Does not add a competitor edge.

The 2026-10-12 snapshot has no property labeled competitor. A proposed
competitor edge is reported and left out of the graph when no kept claim
links the two items. Dated subsidiaries and products are collected from
the live API. Only a dated edge that clears the coverage bar is added.
"""

from __future__ import annotations

import json
import sys
import re
import sqlite3
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
API = "https://www.wikidata.org/w/api.php"
UA = "sgnn-csp-phase2/0.1 (academic research; undergraduate project)"
SNAP = ROOT / "kg" / "snapshots" / "wikidata_2026-10-12" / "entities.json"
OUT = ROOT / "eval" / "results" / "phase2_brand_edges.json"
POSITIVE = {"P355", "P1830", "P1056", "P176", "P1716", "P127", "P749"}
LABELS = {
    "P355": "child organization or unit",
    "P1830": "owner of",
    "P1056": "product or material produced",
    "P176": "manufacturer",
    "P1716": "brand",
    "P127": "owned by",
    "P749": "parent organization or unit",
}

BRANDS = [
    {"ticker": "NKE", "qid": "Q483915", "name": "Nike", "group": "open"},
    {"ticker": "CMG", "qid": "Q465751", "name": "Chipotle", "group": "clean"},
    {"ticker": "LOW", "qid": "Q1373493", "name": "Lowe's", "group": "open"},
    {"ticker": "TMUS", "qid": "Q3511885", "name": "T-Mobile US", "group": "clean"},
    {"ticker": "NYT", "qid": "Q2529982", "name": "New York Times Co", "group": "open"},
    {"ticker": "HSY", "qid": "Q1056637", "name": "Hershey", "group": "clean"},
    {"ticker": "CL", "qid": "Q609466", "name": "Colgate-Palmolive", "group": "clean"},
    {"ticker": "MA", "qid": "Q489921", "name": "Mastercard", "group": "open"},
    {"ticker": "CVX", "qid": "Q319642", "name": "Chevron", "group": "clean"},
    {"ticker": "NEE", "qid": "Q967868", "name": "NextEra Energy", "group": "clean"},
    {"ticker": "DE", "qid": "Q496302", "name": "John Deere", "group": "open"},
    {"ticker": "LLY", "qid": "Q632240", "name": "Eli Lilly", "group": "clean"},
]
PEERS = {
    "CMG": [("DRI", "Q742196", "Darden")],
    "TMUS": [("DISH", "Q1199757", "Dish Network")],
    "HSY": [("GIS", "Q629998", "General Mills"), ("K", "Q856897", "Kellanova")],
    "CL": [("CLX", "Q910368", "Clorox"), ("KMB", "Q1741634", "Kimberly-Clark")],
    "CVX": [("MPC", "Q458363", "Marathon Petroleum"), ("VLO", "Q1283291", "Valero")],
    "NEE": [("DUK", "Q1264404", "Duke Energy"), ("SO", "Q2304693", "Southern Company")],
    "LLY": [("AMGN", "Q470517", "Amgen"), ("VRTX", "Q2744099", "Vertex")],
}
INSIDE = {
    "LOW": [("HD", "Home Depot")],
    "MA": [("V", "Visa")],
    "DE": [("CAT", "Caterpillar")],
    "NKE": [],
    "NYT": [],
}


def api(params: dict) -> dict:
    query = urllib.parse.urlencode(params)
    request = urllib.request.Request(f"{API}?{query}", headers={"User-Agent": UA})
    last = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            last = exc
            time.sleep(2 ** attempt)
    raise RuntimeError(last)


def chunks(items: list[str], size: int):
    for i in range(0, len(items), size):
        yield items[i : i + size]


def start_date(statement: dict) -> str | None:
    qualifiers = statement.get("qualifiers") or {}
    snaks = qualifiers.get("P580") or []
    if not snaks:
        return None
    value = (snaks[0].get("datavalue") or {}).get("value") or {}
    if not isinstance(value, dict) or "time" not in value:
        return None
    precision = int(value.get("precision") or 0)
    year, month, day = value["time"][1:11].split("-")
    if precision >= 11:
        return f"{year}-{month}-{day}"
    if precision == 10:
        return f"{year}-{month}-01"
    if precision == 9:
        return f"{year}-01-01"
    return None


def fetch_entities(qids: list[str]) -> dict:
    found = {}
    for batch in chunks(qids, 20):
        payload = api(
            {
                "action": "wbgetentities",
                "ids": "|".join(batch),
                "props": "claims|sitelinks|labels",
                "languages": "en",
                "format": "json",
            }
        )
        found.update(payload.get("entities") or {})
        time.sleep(0.3)
    return found


def enwiki(entity: dict) -> str | None:
    title = ((entity.get("sitelinks") or {}).get("enwiki") or {}).get("title")
    return title


def item_links(entity: dict) -> list[dict]:
    rows = []
    for prop, statements in (entity.get("claims") or {}).items():
        for statement in statements:
            if statement.get("rank") == "deprecated":
                continue
            snak = statement.get("mainsnak") or {}
            value = (snak.get("datavalue") or {}).get("value")
            if not isinstance(value, dict) or not value.get("id"):
                continue
            rows.append(
                {
                    "property": prop,
                    "target": value["id"],
                    "statement_id": statement.get("id"),
                    "counts_from": start_date(statement) if prop in POSITIVE else None,
                }
            )
    return rows


def main() -> None:
    snapshot = json.loads(SNAP.read_text())
    tickers = json.loads((ROOT / "kg" / "snapshots" / "wikidata_2026-10-12" / "tickers.json").read_text())
    qid_ticker = {}
    for ticker, row in tickers.items():
        chosen = row.get("chosen") or {}
        if chosen.get("qid"):
            qid_ticker[chosen["qid"]] = ticker
    peer_qids = {qid for peers in PEERS.values() for _, qid, _ in peers}
    brand_qids = [row["qid"] for row in BRANDS]
    entities = fetch_entities(sorted(set(brand_qids) | peer_qids))

    edges = []
    for brand in BRANDS:
        entity = entities.get(brand["qid"]) or {}
        links = item_links(entity)
        for ticker, qid, name in PEERS.get(brand["ticker"], []):
            hits = [link for link in links if link["target"] == qid]
            snap = snapshot.get(brand["qid"], {}).get("claims") or {}
            snap_hits = []
            for prop, statements in snap.items():
                for statement in statements:
                    if statement.get("target") == qid:
                        snap_hits.append(prop)
            if hits or snap_hits:
                reason = (
                    "A claim links these items, but the property is not a competitor property. "
                    f"Snapshot properties {snap_hits or 'none'}; live properties {[hit['property'] for hit in hits] or 'none'}."
                )
            else:
                reason = "The snapshot has no competitor property, and no claim on the brand points at this peer."
            edges.append(
                {
                    "brand": brand["name"],
                    "brand_ticker": brand["ticker"],
                    "brand_qid": brand["qid"],
                    "peer": name,
                    "peer_ticker": ticker,
                    "peer_qid": qid,
                    "group": "clean",
                    "snapshot_properties": snap_hits,
                    "live_properties": [hit["property"] for hit in hits],
                    "wikidata_states_competitor_edge": False,
                    "added": False,
                    "reason": reason,
                }
            )
        if brand["group"] == "open":
            company_hits = []
            for link in links:
                ticker = qid_ticker.get(link["target"])
                if ticker:
                    company_hits.append({**link, "ticker": ticker})
            edges.append(
                {
                    "brand": brand["name"],
                    "brand_ticker": brand["ticker"],
                    "brand_qid": brand["qid"],
                    "group": "open",
                    "company_item_links": company_hits,
                    "inside_two_hop_names_not_added": INSIDE.get(brand["ticker"], []),
                    "added": False,
                }
            )

    dated = []
    child_qids = []
    for brand in BRANDS:
        entity = entities.get(brand["qid"]) or {}
        for link in item_links(entity):
            if link["property"] not in POSITIVE or not link["counts_from"]:
                continue
            dated.append({**link, "brand": brand["name"], "brand_ticker": brand["ticker"], "brand_qid": brand["qid"]})
            child_qids.append(link["target"])
    children = fetch_entities(sorted(set(child_qids))) if child_qids else {}
    for row in dated:
        child = children.get(row["target"]) or {}
        row["child_label"] = ((child.get("labels") or {}).get("en") or {}).get("value")
        row["enwiki"] = enwiki(child)
        row["sitelinks"] = len(child.get("sitelinks") or {})

    if "--api-only" in sys.argv:
        payload = {
            "checked_on": "2026-10-14",
            "snapshot": "wikidata_2026-10-12",
            "competitor_property": None,
            "edges": edges,
            "dated_ownership": dated,
            "brands": [
                {
                    "ticker": brand["ticker"],
                    "qid": brand["qid"],
                    "name": brand["name"],
                    "enwiki": enwiki(entities.get(brand["qid"]) or {}),
                    "sitelinks": len((entities.get(brand["qid"]) or {}).get("sitelinks") or {}),
                }
                for brand in BRANDS
            ],
            "peers": [
                {
                    "ticker": ticker,
                    "qid": qid,
                    "name": name,
                    "enwiki": enwiki(entities.get(qid) or {}),
                    "sitelinks": len((entities.get(qid) or {}).get("sitelinks") or {}),
                }
                for peers in PEERS.values()
                for ticker, qid, name in peers
            ],
        }
        OUT.write_text(json.dumps(payload, indent=2))
        print("api-only", "dated", len(dated), flush=True)
        return

    # Coverage bar: at least 14 days with at least 14 scored documents, on or after P580.
    patterns = []
    for row in dated:
        title = row.get("enwiki")
        if not title or len(title) < 6:
            row["coverage"] = {"skipped": "title missing or shorter than 6 characters"}
            continue
        patterns.append((row, re.compile(r"\b" + re.escape(title.replace("_", " ")) + r"\b", re.I)))
    news_days: dict[int, dict[str, list]] = defaultdict(dict)
    social_days: dict[int, dict[str, list]] = defaultdict(dict)
    if patterns:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

        analyzer = SentimentIntensityAnalyzer()
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
                    for idx, (row, pattern) in enumerate(patterns):
                        if day < row["counts_from"] or not pattern.search(blob):
                            continue
                        cell = news_days[idx].setdefault(day, [0.0, 0])
                        if score is not None:
                            cell[0] += score
                            cell[1] += 1
            print("coverage news", path.name, flush=True)
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
                for idx, (row, pattern) in enumerate(patterns):
                    if day < row["counts_from"] or not pattern.search(body):
                        continue
                    cell = social_days[idx].setdefault(day, [0.0, 0])
                    if score is not None:
                        cell[0] += score
                        cell[1] += 1
            print("coverage social", path.name, flush=True)
        con.close()
    for idx, (row, _pattern) in enumerate(patterns):
        def dense(days: dict) -> int:
            return sum(1 for cell in days.values() if cell[1] >= 14)

        news_n = dense(news_days[idx])
        social_n = dense(social_days[idx])
        row["coverage"] = {
            "news_days": len(news_days[idx]),
            "news_dense_days": news_n,
            "social_days": len(social_days[idx]),
            "social_dense_days": social_n,
            "clears_bar": news_n >= 14 or social_n >= 14,
        }

    payload = {
        "checked_on": "2026-10-14",
        "snapshot": "wikidata_2026-10-12",
        "competitor_property": None,
        "edges": edges,
        "dated_ownership": dated,
        "brands": [
            {
                "ticker": brand["ticker"],
                "qid": brand["qid"],
                "name": brand["name"],
                "enwiki": enwiki(entities.get(brand["qid"]) or {}),
                "sitelinks": len((entities.get(brand["qid"]) or {}).get("sitelinks") or {}),
            }
            for brand in BRANDS
        ],
        "peers": [
            {
                "ticker": ticker,
                "qid": qid,
                "name": name,
                "enwiki": enwiki(entities.get(qid) or {}),
                "sitelinks": len((entities.get(qid) or {}).get("sitelinks") or {}),
            }
            for peers in PEERS.values()
            for ticker, qid, name in peers
        ],
    }
    OUT.write_text(json.dumps(payload, indent=2))
    print("wrote", OUT, "dated", len(dated), "clear", sum(1 for row in dated if (row.get("coverage") or {}).get("clears_bar")))


if __name__ == "__main__":
    main()

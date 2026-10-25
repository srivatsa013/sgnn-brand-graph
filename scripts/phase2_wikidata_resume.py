"""Finish the 2026-10-12 Wikidata snapshot without the query-service outage path.

Parent and subsidiary ids are accepted only when the saved search hit is
the property returned for that query and the official label is the one
recorded below. Competitor search did not return a competitor property.
P710 (participant) is rejected.
"""

from __future__ import annotations

import json
import socket
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "kg" / "snapshots" / "wikidata_2026-10-12"
API = "https://www.wikidata.org/w/api.php"
SPARQL = "https://query.wikidata.org/sparql"
UA = "sgnn-csp-phase2/0.1 (academic research; undergraduate project)"

OFFICIAL_LABELS = {
    "parent_organization": ("P749", "parent organization or unit"),
    "subsidiary": ("P355", "child organization or unit"),
}

FOCAL = [
    "Apple Inc.",
    "Microsoft",
    "Alphabet Inc.",
    "Google",
    "Tesla, Inc.",
    "iPhone",
    "MacBook",
    "Microsoft Windows",
    "Microsoft Azure",
    "YouTube",
    "Android",
    "Tesla Model 3",
    "Tesla Model S",
    "Tim Cook",
    "Steve Jobs",
    "Satya Nadella",
    "Steve Ballmer",
    "Sundar Pichai",
    "Larry Page",
    "Eric Schmidt",
    "Elon Musk",
    "Dell",
    "HP Inc.",
    "Logitech",
    "Oracle Corporation",
    "Salesforce, Inc.",
    "IBM",
    "Adobe Inc.",
    "Meta Platforms",
    "Amazon",
    "Snap Inc.",
    "Pinterest",
    "Ford Motor Company",
    "General Motors",
    "Toyota",
    "NIO Inc.",
]


def prefer_ipv4() -> None:
    original = socket.getaddrinfo

    def ipv4(host, port, family=0, socktype=0, proto=0, flags=0):
        try:
            found = original(host, port, socket.AF_INET, socktype, proto, flags)
        except socket.gaierror:
            found = []
        return found or original(host, port, family, socktype, proto, flags)

    socket.getaddrinfo = ipv4


def call(url: str, data: bytes | None = None, accept: str | None = None) -> dict:
    headers = {"User-Agent": UA}
    if accept:
        headers["Accept"] = accept
    last = None
    for attempt in range(8):
        try:
            request = urllib.request.Request(url, data=data, headers=headers)
            with urllib.request.urlopen(request, timeout=120) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            last = exc
            wait = 70 if "429" in str(exc) else min(60, 2 ** attempt)
            print(f"retry {attempt} after {wait}s: {exc}", flush=True)
            time.sleep(wait)
    raise RuntimeError(last)


def api(params: dict) -> dict:
    params = dict(params)
    params["format"] = "json"
    params["maxlag"] = "5"
    url = API + "?" + urllib.parse.urlencode(params)
    payload = call(url)
    time.sleep(1.0)
    return payload


def sparql(query: str) -> dict:
    data = urllib.parse.urlencode({"query": query}).encode()
    payload = call(SPARQL, data=data, accept="application/sparql-results+json")
    time.sleep(65)
    return payload


def main() -> None:
    prefer_ipv4()
    properties = json.loads((OUT / "properties.json").read_text())
    verified = {}
    for key, row in properties.items():
        chosen = row.get("chosen") or {}
        if row.get("label_matched") and chosen.get("id"):
            verified[key] = {"id": chosen["id"], "label": chosen["label"], "exact_label": True}
    for key, (pid, label) in OFFICIAL_LABELS.items():
        chosen = (properties.get(key) or {}).get("chosen") or {}
        if chosen.get("id") == pid and chosen.get("label") == label:
            verified[key] = {"id": pid, "label": label, "exact_label": False, "accepted_because": "unique or top search hit; official label recorded"}
    competitor = properties.get("competitor") or {}
    verified_ids = {row["id"] for row in verified.values()}
    if "P710" in verified_ids:
        raise SystemExit("participant property was accepted as a relation; refusing")
    (OUT / "verified_properties.json").write_text(
        json.dumps(
            {
                "retrieved_on": "2026-10-12",
                "properties": verified,
                "competitor_property": None,
                "competitor_search_rejected": competitor.get("hits"),
                "reason": "No returned property has the label competitor. P710 participant is not a competitor relation.",
            },
            indent=2,
        )
    )
    print("properties", {k: v["id"] for k, v in verified.items()}, flush=True)

    universe = json.loads((ROOT / "configs" / "phase1_universe.json").read_text())
    tickers = []
    for eco in universe["ecosystems"].values():
        tickers.extend(eco["brand_tickers"])
        tickers.extend(eco["competitor_tickers"])
    for names in universe["control_pool_by_bucket"].values():
        tickers.extend(names)
    tickers = sorted(set(tickers))
    # P249 is verified as "ticker symbol", but on the companies checked it is a
    # qualifier of P414 (stock exchange), not a main statement. wdt:P249 alone
    # matched unrelated items. Both paths are queried. The earlier tickers.json
    # from the main-value query is discarded.
    resolution = {}
    print("pending tickers", len(tickers), flush=True)
    for start in range(0, len(tickers), 25):
        batch = tickers[start : start + 25]
        values = " ".join(f'"{ticker}"' for ticker in batch)
        query = f"""
        SELECT ?ticker ?item ?sitelinks WHERE {{
          VALUES ?ticker {{ {values} }}
          {{
            ?item p:P414 ?stmt .
            ?stmt pq:P249 ?ticker .
          }} UNION {{
            ?item p:P249 ?stmt2 .
            ?stmt2 ps:P249 ?ticker .
          }}
          ?item wikibase:sitelinks ?sitelinks .
        }}
        """
        try:
            rows = sparql(query)["results"]["bindings"]
        except Exception as exc:
            print("sparql batch failed", batch[0], exc, flush=True)
            rows = []
        grouped: dict[str, list] = {}
        for row in rows:
            ticker = row["ticker"]["value"]
            qid = row["item"]["value"].rsplit("/", 1)[-1]
            grouped.setdefault(ticker, []).append({"qid": qid, "sitelinks": int(float(row["sitelinks"]["value"]))})
        for ticker in batch:
            best = {}
            for hit in grouped.get(ticker, []):
                prev = best.get(hit["qid"])
                if prev is None or hit["sitelinks"] > prev["sitelinks"]:
                    best[hit["qid"]] = hit
            hits = sorted(best.values(), key=lambda item: -item["sitelinks"])
            ambiguous = bool(
                len(hits) >= 2
                and hits[1]["sitelinks"] >= 10
                and hits[1]["sitelinks"] >= 0.5 * hits[0]["sitelinks"]
            )
            resolution[ticker] = {
                "chosen": hits[0] if hits else None,
                "alternatives": hits[1:],
                "unresolved": not hits,
                "ambiguous": ambiguous,
                "match": "P249 as a qualifier of P414, or as a main value; highest sitelink count",
            }
        (OUT / "tickers.json").write_text(json.dumps(resolution, indent=2))
        print("resolved", sum(1 for row in resolution.values() if row.get("chosen")), "of", len(tickers), flush=True)

    focal = {}
    for text in FOCAL:
        payload = api(
            {
                "action": "wbsearchentities",
                "search": text,
                "language": "en",
                "type": "item",
                "limit": 3,
            }
        )
        focal[text] = [
            {"id": row.get("id"), "label": row.get("label"), "description": row.get("description")}
            for row in payload.get("search", [])
        ]
        print("search", text, focal[text][:1], flush=True)
    (OUT / "focal_search.json").write_text(json.dumps(focal, indent=2))

    qids = []
    for row in resolution.values():
        if row.get("chosen"):
            qids.append(row["chosen"]["qid"])
    for hits in focal.values():
        if hits and hits[0].get("id"):
            qids.append(hits[0]["id"])
    qids = sorted(set(qids))
    compact = {}
    keep = {row["id"] for row in verified.values()}
    for start in range(0, len(qids), 25):
        batch = qids[start : start + 25]
        payload = api({"action": "wbgetentities", "ids": "|".join(batch), "props": "info|claims|sitelinks"})
        for qid, entity in (payload.get("entities") or {}).items():
            claims = {}
            for prop, statements in (entity.get("claims") or {}).items():
                if prop not in keep:
                    continue
                kept_statements = []
                for statement in statements:
                    snak = statement.get("mainsnak") or {}
                    value = (snak.get("datavalue") or {}).get("value")
                    target = value.get("id") if isinstance(value, dict) else value if isinstance(value, str) else None
                    kept_statements.append(
                        {
                            "statement_id": statement.get("id"),
                            "rank": statement.get("rank"),
                            "snaktype": snak.get("snaktype"),
                            "target": target,
                        }
                    )
                claims[prop] = kept_statements
            compact[qid] = {
                "lastrevid": entity.get("lastrevid"),
                "modified": entity.get("modified"),
                "sitelink_count": len(entity.get("sitelinks") or {}),
                "enwiki": ((entity.get("sitelinks") or {}).get("enwiki") or {}).get("title"),
                "claims": claims,
            }
        print("entities", len(compact), flush=True)
        (OUT / "entities.json").write_text(json.dumps(compact))
    summary = {
        "retrieved_on": "2026-10-12",
        "resolved_tickers": sum(1 for row in resolution.values() if row.get("chosen")),
        "tickers": len(tickers),
        "entities": len(compact),
        "verified_properties": {k: v["id"] for k, v in verified.items()},
        "competitor_property": None,
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()

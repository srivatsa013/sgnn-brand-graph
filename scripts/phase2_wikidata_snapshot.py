"""Dated Wikidata snapshot for the Phase 2 structural graph.

Property ids are taken from the live property search, then checked against
the returned English label. Nothing is stored as an edge until that check
passes. Raw responses are kept under kg/snapshots.
"""

from __future__ import annotations

import json
import socket
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "kg" / "snapshots" / "wikidata_2026-10-12"
API = "https://www.wikidata.org/w/api.php"
SPARQL = "https://query.wikidata.org/sparql"
UA = "sgnn-csp-phase2/0.1 (academic research; undergraduate project)"

PROPERTY_QUERIES = {
    "parent_organization": "parent organization",
    "subsidiary": "subsidiary",
    "owned_by": "owned by",
    "owner_of": "owner of",
    "brand": "brand",
    "product": "product or material produced",
    "manufacturer": "manufacturer",
    "industry": "industry",
    "chief_executive_officer": "chief executive officer",
    "ticker_symbol": "ticker symbol",
    "competitor": "competitor",
}

FOCAL_SEARCH = [
    ("Apple", "Apple Inc."),
    ("Microsoft", "Microsoft"),
    ("Alphabet", "Alphabet Inc."),
    ("Google", "Google"),
    ("Tesla", "Tesla, Inc."),
    ("iPhone", "iPhone"),
    ("MacBook", "MacBook"),
    ("Windows", "Microsoft Windows"),
    ("Azure", "Microsoft Azure"),
    ("YouTube", "YouTube"),
    ("Android", "Android"),
    ("Model 3", "Tesla Model 3"),
    ("Model S", "Tesla Model S"),
    ("Tim Cook", "Timothy Donald Cook"),
    ("Steve Jobs", "Steve Jobs"),
    ("Satya Nadella", "Satya Nadella"),
    ("Steve Ballmer", "Steve Ballmer"),
    ("Sundar Pichai", "Pichai Sundararajan"),
    ("Larry Page", "Lawrence Edward Page"),
    ("Eric Schmidt", "Eric Schmidt"),
    ("Elon Musk", "Elon Reeve Musk"),
    ("Dell", "Dell"),
    ("HP", "HP Inc."),
    ("Logitech", "Logitech"),
    ("Oracle", "Oracle Corporation"),
    ("Salesforce", "Salesforce"),
    ("IBM", "IBM"),
    ("Adobe", "Adobe Inc."),
    ("Meta", "Meta Platforms"),
    ("Amazon", "Amazon"),
    ("Snap", "Snap Inc."),
    ("Pinterest", "Pinterest"),
    ("Ford", "Ford Motor Company"),
    ("General Motors", "General Motors"),
    ("Toyota", "Toyota Motor Corporation"),
    ("NIO", "NIO"),
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


def get_json(url: str, data: bytes | None = None, accept: str | None = None) -> dict:
    headers = {"User-Agent": UA}
    if accept:
        headers["Accept"] = accept
    last = None
    for attempt in range(5):
        try:
            request = urllib.request.Request(url, data=data, headers=headers)
            with urllib.request.urlopen(request, timeout=90) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            last = exc
            time.sleep(min(30, 2 ** attempt))
    raise RuntimeError(f"GET failed {url[:120]}: {last}")


def api(params: dict) -> dict:
    params = dict(params)
    params["format"] = "json"
    url = API + "?" + urllib.parse.urlencode(params)
    payload = get_json(url)
    time.sleep(0.2)
    return payload


def sparql(query: str) -> dict:
    url = SPARQL + "?" + urllib.parse.urlencode({"query": query})
    payload = get_json(url, accept="application/sparql-results+json")
    time.sleep(0.5)
    return payload


def search_property(label: str) -> dict:
    payload = api(
        {
            "action": "wbsearchentities",
            "search": label,
            "language": "en",
            "type": "property",
            "limit": 5,
        }
    )
    hits = []
    for row in payload.get("search", []):
        hits.append({"id": row.get("id"), "label": row.get("label"), "description": row.get("description")})
    exact = [hit for hit in hits if (hit.get("label") or "").lower() == label.lower()]
    chosen = exact[0] if exact else (hits[0] if hits else None)
    return {"query": label, "chosen": chosen, "hits": hits, "label_matched": bool(exact)}


def search_entity(text: str) -> list[dict]:
    payload = api(
        {
            "action": "wbsearchentities",
            "search": text,
            "language": "en",
            "type": "item",
            "limit": 5,
        }
    )
    return [
        {"id": row.get("id"), "label": row.get("label"), "description": row.get("description")}
        for row in payload.get("search", [])
    ]


def chunks(items: list[str], size: int) -> list[list[str]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def main() -> None:
    prefer_ipv4()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    universe = json.loads((ROOT / "configs" / "phase1_universe.json").read_text())
    tickers = []
    for eco in universe["ecosystems"].values():
        tickers.extend(eco["brand_tickers"])
        tickers.extend(eco["competitor_tickers"])
    for names in universe["control_pool_by_bucket"].values():
        tickers.extend(names)
    tickers = sorted(set(tickers))

    properties = {key: search_property(label) for key, label in PROPERTY_QUERIES.items()}
    verified = {}
    for key, row in properties.items():
        chosen = row["chosen"]
        if row["label_matched"] and chosen and chosen.get("id"):
            verified[key] = chosen["id"]
    (OUT_DIR / "properties.json").write_text(json.dumps(properties, indent=2))
    print("verified properties", verified, flush=True)

    ticker_pid = verified.get("ticker_symbol")
    if not ticker_pid:
        raise SystemExit("ticker symbol property was not verified")
    values = " ".join(f'"{ticker}"' for ticker in tickers)
    query = f"""
    SELECT ?ticker ?item ?sitelinks WHERE {{
      VALUES ?ticker {{ {values} }}
      ?item wdt:{ticker_pid} ?ticker .
      ?item wikibase:sitelinks ?sitelinks .
    }}
    """
    ticker_rows = sparql(query)["results"]["bindings"]
    by_ticker: dict[str, list[dict]] = {}
    for row in ticker_rows:
        ticker = row["ticker"]["value"]
        qid = row["item"]["value"].rsplit("/", 1)[-1]
        sitelinks = int(float(row["sitelinks"]["value"]))
        by_ticker.setdefault(ticker, []).append({"qid": qid, "sitelinks": sitelinks})
    resolution = {}
    for ticker in tickers:
        hits = sorted(by_ticker.get(ticker, []), key=lambda item: -item["sitelinks"])
        resolution[ticker] = {
            "chosen": hits[0] if hits else None,
            "alternatives": hits[1:],
            "unresolved": not hits,
        }
    (OUT_DIR / "tickers.json").write_text(json.dumps(resolution, indent=2))
    print("unresolved tickers", [t for t, row in resolution.items() if row["unresolved"]], flush=True)

    focal = {name: search_entity(text) for name, text in FOCAL_SEARCH}
    (OUT_DIR / "focal_search.json").write_text(json.dumps(focal, indent=2))

    qids = []
    for row in resolution.values():
        if row["chosen"]:
            qids.append(row["chosen"]["qid"])
    focal_qids = []
    for hits in focal.values():
        if hits:
            focal_qids.append(hits[0]["id"])
    qids = sorted(set(qids + focal_qids))
    relation_ids = [
        verified[key]
        for key in (
            "parent_organization",
            "subsidiary",
            "owned_by",
            "owner_of",
            "brand",
            "product",
            "manufacturer",
            "chief_executive_officer",
            "competitor",
            "industry",
        )
        if key in verified
    ]
    id_values = " ".join(f"wd:{qid}" for qid in qids)
    prop_values = " ".join(f"wdt:{pid}" for pid in relation_ids)
    edge_query = f"""
    SELECT ?s ?p ?o WHERE {{
      VALUES ?s {{ {id_values} }}
      VALUES ?p {{ {prop_values} }}
      ?s ?p ?o .
    }}
    """
    edge_rows = sparql(edge_query)["results"]["bindings"]
    edges = []
    allowed = set(qids)
    for row in edge_rows:
        source = row["s"]["value"].rsplit("/", 1)[-1]
        prop = row["p"]["value"].rsplit("/", 1)[-1]
        target = row["o"]["value"].rsplit("/", 1)[-1]
        edges.append({"source": source, "property": prop, "target": target, "target_in_universe": target in allowed})
    (OUT_DIR / "sparql_edges.json").write_text(json.dumps(edges, indent=2))
    print("sparql edges", len(edges), flush=True)

    entities = {}
    for batch in chunks(sorted(set(focal_qids)), 20):
        payload = api(
            {
                "action": "wbgetentities",
                "ids": "|".join(batch),
                "props": "info|claims|sitelinks",
                "languages": "en",
            }
        )
        entities.update(payload.get("entities", {}))
        print("entities", len(entities), flush=True)
    # Keep claims only for verified properties, plus the revision id and sitelink count.
    compact = {}
    keep_props = set(verified.values())
    for qid, entity in entities.items():
        claims = {}
        for prop, statements in (entity.get("claims") or {}).items():
            if prop not in keep_props:
                continue
            kept = []
            for statement in statements:
                snak = statement.get("mainsnak") or {}
                value = (snak.get("datavalue") or {}).get("value")
                target = None
                if isinstance(value, dict) and value.get("id"):
                    target = value["id"]
                elif isinstance(value, str):
                    target = value
                kept.append(
                    {
                        "statement_id": statement.get("id"),
                        "rank": statement.get("rank"),
                        "snaktype": snak.get("snaktype"),
                        "target": target,
                    }
                )
            claims[prop] = kept
        compact[qid] = {
            "id": qid,
            "lastrevid": (entity.get("lastrevid")),
            "modified": (entity.get("modified")),
            "sitelink_count": len(entity.get("sitelinks") or {}),
            "enwiki": ((entity.get("sitelinks") or {}).get("enwiki") or {}).get("title"),
            "claims": claims,
        }
    (OUT_DIR / "entities.json").write_text(json.dumps(compact, indent=2))
    summary = {
        "retrieved_on": "2026-10-12",
        "api": API,
        "sparql": SPARQL,
        "verified_properties": verified,
        "ticker_count": len(tickers),
        "resolved_tickers": sum(1 for row in resolution.values() if row["chosen"]),
        "entity_records": len(compact),
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()

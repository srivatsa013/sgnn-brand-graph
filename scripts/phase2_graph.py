"""Structural edges from the dated Wikidata snapshot.

Positive edges are added only when a verified statement links two study
nodes. Competitor edges are the study list: no Wikidata property with the
label competitor was verified. P710 is not used. This script does not
compute a shift.
"""

from __future__ import annotations

import json
import socket
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAP = ROOT / "kg" / "snapshots" / "wikidata_2026-10-12"
OUT = ROOT / "kg" / "phase2_structural_edges.json"
API = "https://www.wikidata.org/w/api.php"
UA = "sgnn-csp-phase2/0.1 (academic research; undergraduate project)"

POSITIVE = {
    "P127": "owned_by",
    "P1830": "owner_of",
    "P1716": "brand",
    "P1056": "product",
    "P176": "manufacturer",
    "P749": "parent_organization",
    "P355": "subsidiary",
}
CEO = "P169"
ACTIVE = {"preferred", "normal"}

SEARCH_FOR_NODE = {
    "iPhone": "iPhone",
    "MacBook": "MacBook",
    "Windows": "Microsoft Windows",
    "Azure": "Microsoft Azure",
    "YouTube": "YouTube",
    "Android": "Android",
    "Model 3": "Tesla Model 3",
    "Model S": "Tesla Model S",
}


def prefer_ipv4() -> None:
    original = socket.getaddrinfo

    def ipv4(host, port, family=0, socktype=0, proto=0, flags=0):
        try:
            found = original(host, port, socket.AF_INET, socktype, proto, flags)
        except socket.gaierror:
            found = []
        return found or original(host, port, family, socktype, proto, flags)

    socket.getaddrinfo = ipv4


def api(params: dict) -> dict:
    params = dict(params)
    params["format"] = "json"
    params["maxlag"] = "5"
    url = API + "?" + urllib.parse.urlencode(params)
    last = None
    for attempt in range(6):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(request, timeout=120) as response:
                payload = json.loads(response.read().decode("utf-8"))
            time.sleep(1.0)
            return payload
        except Exception as exc:
            last = exc
            time.sleep(70 if "429" in str(exc) else min(30, 2 ** attempt))
    raise RuntimeError(last)


def norm(text: str | None) -> str:
    return " ".join((text or "").replace("_", " ").lower().split())


def main() -> None:
    prefer_ipv4()
    nodes = json.loads((ROOT / "configs" / "phase2_nodes.json").read_text())
    universe = json.loads((ROOT / "configs" / "phase1_universe.json").read_text())
    verified = json.loads((SNAP / "verified_properties.json").read_text())
    tickers = json.loads((SNAP / "tickers.json").read_text())
    focal = json.loads((SNAP / "focal_search.json").read_text())
    entities = json.loads((SNAP / "entities.json").read_text())
    if verified.get("competitor_property") is not None:
        raise SystemExit("competitor property was set; refusing to build edges")

    def ticker_row(ticker: str) -> dict | None:
        row = tickers.get(ticker) or {}
        chosen = row.get("chosen")
        if not chosen or row.get("ambiguous"):
            return None
        return chosen

    node_qids: dict[str, list[str]] = {}
    ticker_alts: dict[str, list[str]] = {}
    ticker_notes = []
    for eco, spec in nodes["ecosystems"].items():
        qids = []
        for ticker in spec["brand_tickers"]:
            chosen = ticker_row(ticker)
            if chosen:
                qids.append(chosen["qid"])
            else:
                ticker_notes.append({"node": eco, "ticker": ticker, "status": "unresolved_or_ambiguous"})
        node_qids[eco] = list(dict.fromkeys(qids))
        for ticker in spec["brand_tickers"]:
            for alt in (tickers.get(ticker) or {}).get("alternatives") or []:
                if alt.get("sitelinks", 0) >= 10:
                    ticker_alts.setdefault(eco, []).append(alt["qid"])
        for ticker in spec["competitor_nodes"]:
            if ticker == "Meta":
                meta = []
                for symbol in ("FB", "META"):
                    chosen = ticker_row(symbol)
                    if chosen:
                        meta.append(chosen["qid"])
                    else:
                        ticker_notes.append({"node": "Meta", "ticker": symbol, "status": "unresolved_or_ambiguous"})
                node_qids["Meta"] = list(dict.fromkeys(meta))
                for symbol in ("FB", "META"):
                    for alt in (tickers.get(symbol) or {}).get("alternatives") or []:
                        if alt.get("sitelinks", 0) >= 10:
                            ticker_alts.setdefault("Meta", []).append(alt["qid"])
                continue
            chosen = ticker_row(ticker)
            if chosen:
                node_qids[ticker] = [chosen["qid"]]
            else:
                ticker_notes.append({"node": ticker, "ticker": ticker, "status": "unresolved_or_ambiguous"})
            for alt in (tickers.get(ticker) or {}).get("alternatives") or []:
                if alt.get("sitelinks", 0) >= 10:
                    ticker_alts.setdefault(ticker, []).append(alt["qid"])

    # Labels for claim targets that are people or products.
    need = set()
    for alts in ticker_alts.values():
        need.update(alts)
    for qid, entity in entities.items():
        for prop, statements in (entity.get("claims") or {}).items():
            if prop not in POSITIVE and prop != CEO:
                continue
            for statement in statements:
                target = statement.get("target")
                if target and target not in entities:
                    need.add(target)
    labels = {}
    extra_entities = {}
    missing = sorted(need)
    print("neighbor entities to fetch", len(missing), flush=True)
    for start in range(0, len(missing), 25):
        batch = missing[start : start + 25]
        payload = api(
            {
                "action": "wbgetentities",
                "ids": "|".join(batch),
                "props": "labels|sitelinks|info|claims",
                "languages": "en",
            }
        )
        for qid, entity in (payload.get("entities") or {}).items():
            if entity.get("missing"):
                continue
            label = ((entity.get("labels") or {}).get("en") or {}).get("value")
            labels[qid] = label
            claims = {}
            for prop, statements in (entity.get("claims") or {}).items():
                if prop not in POSITIVE and prop != CEO:
                    continue
                kept = []
                for statement in statements:
                    snak = statement.get("mainsnak") or {}
                    value = (snak.get("datavalue") or {}).get("value")
                    target = value.get("id") if isinstance(value, dict) else None
                    kept.append(
                        {
                            "statement_id": statement.get("id"),
                            "rank": statement.get("rank"),
                            "target": target,
                        }
                    )
                claims[prop] = kept
            extra_entities[qid] = {
                "lastrevid": entity.get("lastrevid"),
                "sitelink_count": len(entity.get("sitelinks") or {}),
                "enwiki": ((entity.get("sitelinks") or {}).get("enwiki") or {}).get("title"),
                "label": label,
                "claims": claims,
            }
        print("neighbors", len(extra_entities), flush=True)
    (SNAP / "neighbor_entities.json").write_text(json.dumps(extra_entities))

    # Labels of entities we already stored, from the focal search and a small fetch.
    known_qids = sorted({qid for qids in node_qids.values() for qid in qids})
    for start in range(0, len(known_qids), 40):
        batch = known_qids[start : start + 40]
        payload = api({"action": "wbgetentities", "ids": "|".join(batch), "props": "labels", "languages": "en"})
        for qid, entity in (payload.get("entities") or {}).items():
            labels[qid] = ((entity.get("labels") or {}).get("en") or {}).get("value")

    qid_node = {}
    for name, qids in node_qids.items():
        for qid in qids:
            qid_node.setdefault(qid, name)

    def entity_of(qid: str) -> dict | None:
        return entities.get(qid) or extra_entities.get(qid)

    def sitelinks(qid: str) -> int | None:
        entity = entity_of(qid)
        if not entity:
            return None
        return entity.get("sitelink_count")

    positive_edges = []
    seen_pair = set()
    external_parents = []
    misses = []

    def add_positive(left: str, right: str, prop: str, statement: dict, source_qid: str, target_qid: str) -> None:
        if left == right:
            return
        key = tuple(sorted((left, right))) + (prop, statement.get("statement_id"))
        if key in seen_pair:
            return
        seen_pair.add(key)
        source_entity = entity_of(source_qid) or {}
        target_entity = entity_of(target_qid) or {}
        record = {
            "edge_class": "positive",
            "sign": 1,
            "stored_as": "two_arcs_sharing_W_pos",
            "nodes": [left, right],
            "stated_direction": {"from": qid_node.get(source_qid, left), "to": qid_node.get(target_qid, right)},
            "property_id": prop,
            "property_key": POSITIVE[prop],
            "property_label": (verified["properties"].get(POSITIVE[prop]) or {}).get("label"),
            "statement_id": statement.get("statement_id"),
            "rank": statement.get("rank"),
            "source_qid": source_qid,
            "target_qid": target_qid,
            "source_lastrevid": source_entity.get("lastrevid"),
            "target_lastrevid": target_entity.get("lastrevid"),
            "snapshot": "wikidata_2026-10-12",
        }
        positive_edges.append(record)

    all_claims = {}
    for qid, entity in list(entities.items()) + list(extra_entities.items()):
        all_claims[qid] = entity.get("claims") or {}

    # A high-sitelink ticker alternative is the same study node only when a
    # verified ownership or parent statement already links the two items.
    for name, alts in ticker_alts.items():
        primary = set(node_qids.get(name) or [])
        for alt in alts:
            if alt in primary:
                continue
            linked = False
            for prop in POSITIVE:
                for statement in (all_claims.get(alt) or {}).get(prop) or []:
                    if statement.get("target") in primary and statement.get("rank") in ACTIVE:
                        linked = True
                for qid in primary:
                    for statement in (all_claims.get(qid) or {}).get(prop) or []:
                        if statement.get("target") == alt and statement.get("rank") in ACTIVE:
                            linked = True
            if linked:
                node_qids.setdefault(name, []).append(alt)
                qid_node.setdefault(alt, name)
                ticker_notes.append({"node": name, "qid": alt, "status": "alternative_ticker_item_linked_by_an_ownership_or_parent_statement"})

    for source_qid, claims in all_claims.items():
        source_node = qid_node.get(source_qid)
        for prop, statements in claims.items():
            if prop not in POSITIVE:
                continue
            for statement in statements:
                target = statement.get("target")
                if not target or statement.get("rank") not in ACTIVE:
                    continue
                target_node = qid_node.get(target)
                if source_node and target_node:
                    add_positive(source_node, target_node, prop, statement, source_qid, target)
                elif source_node and prop == "P749":
                    external_parents.append(
                        {
                            "node": source_node,
                            "property_id": "P749",
                            "target_qid": target,
                            "target_label": labels.get(target),
                            "statement_id": statement.get("statement_id"),
                            "action": "not_added",
                            "reason": "Each listed company is its own parent. An outside parent is not a study node.",
                        }
                    )

    # Product and CEO links that the search suggested, confirmed only by a statement.
    confirmed_products = {}
    for node, search_text in SEARCH_FOR_NODE.items():
        hits = focal.get(search_text) or []
        eco = None
        for name, spec in nodes["ecosystems"].items():
            if node in spec["positive_nodes"]:
                eco = name
                break
        company_qids = set(node_qids.get(eco) or [])
        matched = False
        chosen_hits = [
            hit
            for hit in hits
            if norm(hit.get("label")) in {norm(search_text), norm(node)}
        ]
        if not chosen_hits and hits:
            chosen_hits = hits[:1]
        else:
            chosen_hits = chosen_hits[:1]
        for hit in chosen_hits:
            qid = hit.get("id")
            if not qid:
                continue
            entity = entity_of(qid)
            # The product entity may not have been in the first fetch. Fetch it.
            if entity is None:
                payload = api(
                    {
                        "action": "wbgetentities",
                        "ids": qid,
                        "props": "labels|sitelinks|info|claims",
                        "languages": "en",
                    }
                )
                raw = (payload.get("entities") or {}).get(qid) or {}
                claims = {}
                for prop, statements in (raw.get("claims") or {}).items():
                    if prop not in POSITIVE and prop != CEO:
                        continue
                    kept = []
                    for statement in statements:
                        snak = statement.get("mainsnak") or {}
                        value = (snak.get("datavalue") or {}).get("value")
                        target = value.get("id") if isinstance(value, dict) else None
                        kept.append(
                            {
                                "statement_id": statement.get("id"),
                                "rank": statement.get("rank"),
                                "target": target,
                            }
                        )
                    claims[prop] = kept
                entity = {
                    "lastrevid": raw.get("lastrevid"),
                    "sitelink_count": len(raw.get("sitelinks") or {}),
                    "enwiki": ((raw.get("sitelinks") or {}).get("enwiki") or {}).get("title"),
                    "label": ((raw.get("labels") or {}).get("en") or {}).get("value"),
                    "claims": claims,
                }
                extra_entities[qid] = entity
                labels[qid] = entity["label"]
                all_claims[qid] = claims
            linked = False
            for prop, statements in (entity.get("claims") or {}).items():
                if prop not in POSITIVE:
                    continue
                for statement in statements:
                    if statement.get("rank") in ACTIVE and statement.get("target") in company_qids:
                        add_positive(node, eco, prop, statement, qid, statement["target"])
                        qid_node.setdefault(qid, node)
                        node_qids.setdefault(node, [])
                        if qid not in node_qids[node]:
                            node_qids[node].append(qid)
                        linked = True
                        matched = True
            if not linked and company_qids:
                for company_qid in company_qids:
                    for prop, statements in (all_claims.get(company_qid) or {}).items():
                        if prop not in POSITIVE:
                            continue
                        for statement in statements:
                            if statement.get("rank") in ACTIVE and statement.get("target") == qid:
                                add_positive(eco, node, prop, statement, company_qid, qid)
                                qid_node.setdefault(qid, node)
                                node_qids.setdefault(node, [])
                                if qid not in node_qids[node]:
                                    node_qids[node].append(qid)
                                linked = True
                                matched = True
            if matched:
                confirmed_products[node] = {"qid": qid, "label": labels.get(qid) or hit.get("label"), "sitelinks": entity.get("sitelink_count")}
                break
        if not matched:
            misses.append(
                {
                    "node": node,
                    "search": search_text,
                    "top_hit": hits[0] if hits else None,
                    "reason": "No verified product, brand, manufacturer, owner, or parent statement links this search hit to the company.",
                }
            )

    ceo_edges = []
    for eco, spec in nodes["ecosystems"].items():
        role = f"{eco} CEO" if eco != "Alphabet" else "Alphabet CEO"
        # role names in the node file
        role = [name for name in spec["positive_nodes"] if name.endswith("CEO")][0]
        aliases = {norm(a) for a in (universe["alias_nodes"].get(role) or {}).get("aliases") or []}
        found = False
        for company_qid in node_qids.get(eco) or []:
            for statement in (all_claims.get(company_qid) or {}).get(CEO) or []:
                if statement.get("rank") not in ACTIVE:
                    continue
                person = statement.get("target")
                if not person:
                    continue
                if person not in labels or person not in extra_entities and person not in entities:
                    payload = api(
                        {
                            "action": "wbgetentities",
                            "ids": person,
                            "props": "labels|sitelinks|info",
                            "languages": "en",
                        }
                    )
                    raw = (payload.get("entities") or {}).get(person) or {}
                    labels[person] = ((raw.get("labels") or {}).get("en") or {}).get("value")
                    extra_entities[person] = {
                        "lastrevid": raw.get("lastrevid"),
                        "sitelink_count": len(raw.get("sitelinks") or {}),
                        "enwiki": ((raw.get("sitelinks") or {}).get("enwiki") or {}).get("title"),
                        "label": labels[person],
                        "claims": {},
                    }
                person_entity = extra_entities.get(person) or entities.get(person) or {}
                names = {norm(labels.get(person)), norm(person_entity.get("enwiki"))}
                if not (names & aliases):
                    misses.append(
                        {
                            "node": role,
                            "property_id": CEO,
                            "person_qid": person,
                            "person_label": labels.get(person),
                            "reason": "P169 target does not match an alias. No CEO edge was added for this statement.",
                        }
                    )
                    continue
                company_entity = entity_of(company_qid) or {}
                ceo_edges.append(
                    {
                        "edge_class": "positive",
                        "sign": 1,
                        "stored_as": "two_arcs_sharing_W_pos",
                        "nodes": [eco, role],
                        "property_id": CEO,
                        "property_label": (verified["properties"].get("chief_executive_officer") or {}).get("label"),
                        "statement_id": statement.get("statement_id"),
                        "rank": statement.get("rank"),
                        "company_qid": company_qid,
                        "person_qid": person,
                        "person_label": labels.get(person),
                        "person_sitelinks": person_entity.get("sitelink_count"),
                        "company_lastrevid": company_entity.get("lastrevid"),
                        "person_lastrevid": person_entity.get("lastrevid"),
                        "snapshot": "wikidata_2026-10-12",
                    }
                )
                node_qids.setdefault(role, [])
                if person not in node_qids[role]:
                    node_qids[role].append(person)
                found = True
        if not found:
            misses.append({"node": role, "reason": "No active P169 statement matched an alias."})

    competitor_edges = []
    for eco, spec in nodes["ecosystems"].items():
        for competitor in spec["competitor_nodes"]:
            competitor_edges.append(
                {
                    "edge_class": "competitor",
                    "sign": -1,
                    "direction": "brand_to_named_competitor",
                    "from": eco,
                    "to": competitor,
                    "reverse_asserted": False,
                    "property_id": None,
                    "pending_user_confirmation": True,
                    "provenance": "Study list in configs/phase2_nodes.json. No Wikidata property labeled competitor was verified. P710 participant was rejected.",
                }
            )

    # Path graph. Deprecated statements count for ineligibility only.
    path_edges = []
    deprecated_edges = []
    for source_qid, claims in all_claims.items():
        for prop, statements in claims.items():
            if prop not in POSITIVE:
                continue
            for statement in statements:
                target = statement.get("target")
                if not target:
                    continue
                record = (source_qid, target, prop, statement.get("rank"), statement.get("statement_id"))
                path_edges.append(record)
                if statement.get("rank") == "deprecated":
                    deprecated_edges.append(record)

    popularity = {}
    for name, qids in node_qids.items():
        counts = [sitelinks(qid) for qid in qids]
        counts = [c for c in counts if c is not None]
        popularity[name] = max(counts) if counts else None

    # CEO popularity is the matched person's sitelinks, already on the edge.
    for edge in ceo_edges:
        role = edge["nodes"][1]
        popularity[role] = edge.get("person_sitelinks")

    payload = {
        "snapshot": "wikidata_2026-10-12",
        "retrieved_on": "2026-10-12",
        "sony": nodes["sony_decision"],
        "verified_properties": verified.get("properties"),
        "competitor_property": None,
        "ticker_resolution": "P249 as a qualifier of stock-exchange statement P414, or as a main value. Highest sitelink count. Ambiguous tickers are not used.",
        "node_qids": node_qids,
        "node_labels": {name: [labels.get(qid) for qid in qids] for name, qids in node_qids.items()},
        "popularity_sitelinks": popularity,
        "positive_edges": positive_edges,
        "ceo_edges": ceo_edges,
        "competitor_edges_pending_confirmation": competitor_edges,
        "external_parents_not_added": external_parents,
        "not_linked": misses,
        "ticker_notes": ticker_notes,
        "path_edge_count": len(path_edges),
        "deprecated_path_edge_count": len(deprecated_edges),
        "neighbor_entities_fetched": len(extra_entities),
        "neighbor_entities_not_fetched": 0,
    }
    # Persist the path graph for the feasibility check.
    (SNAP / "path_edges.json").write_text(
        json.dumps(
            {
                "edges": [
                    {"source": a, "target": b, "property_id": prop, "rank": rank, "statement_id": sid}
                    for a, b, prop, rank, sid in path_edges
                ]
            }
        )
    )
    (SNAP / "node_qids.json").write_text(json.dumps({"node_qids": node_qids, "popularity_sitelinks": popularity, "labels": labels}, indent=2))
    OUT.write_text(json.dumps(payload, indent=2))
    print("positive", len(positive_edges), "ceo", len(ceo_edges), "competitor", len(competitor_edges), "misses", len(misses), flush=True)


if __name__ == "__main__":
    main()

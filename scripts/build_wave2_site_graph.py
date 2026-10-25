"""Site graph for 30 ecosystems. Wikidata statements only.

Does not read news, does not call BigQuery, and does not change a study file.
"""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALIASES = ROOT / "configs" / "wave2_gdelt_aliases.json"
AUGMENTED = ROOT / "eval" / "results" / "phase5_augmented.json"
OUT = ROOT / "site" / "assets" / "graph.json"
API = "https://www.wikidata.org/w/api.php"
SPARQL = "https://query.wikidata.org/sparql"
UA = "sgnn-csp-site-graph/0.1 (academic research; undergraduate project)"
POSITIVE = ("P127", "P1830", "P1716", "P1056", "P176", "P749", "P355", "P169")
CAP = 300


def api(params: dict) -> dict:
    url = API + "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={"User-Agent": UA})
    last = None
    for attempt in range(5):
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                return json.loads(response.read().decode())
        except Exception as exc:
            last = exc
            time.sleep(30 if "429" in str(exc) else min(20, 2 ** attempt))
    raise RuntimeError(last)


def sparql(query: str) -> list[dict]:
    url = SPARQL + "?" + urllib.parse.urlencode({"query": query, "format": "json"})
    request = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/sparql-results+json"})
    last = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                payload = json.loads(response.read().decode())
            return payload["results"]["bindings"]
        except Exception as exc:
            last = exc
            time.sleep(70 if "429" in str(exc) else min(20, 2 ** attempt))
    raise RuntimeError(last)


def qid_of(uri: str) -> str:
    return uri.rsplit("/", 1)[-1]


def competitor_property() -> str | None:
    payload = api(
        {
            "action": "wbsearchentities",
            "search": "competitor",
            "type": "property",
            "language": "en",
            "limit": "20",
            "format": "json",
        }
    )
    for row in payload.get("search") or []:
        if (row.get("label") or "").strip().lower() == "competitor":
            return row["id"]
    return None


def entity_batch(qids: list[str], props: str) -> dict:
    found = {}
    pending = list(dict.fromkeys(qids))
    for start in range(0, len(pending), 40):
        chunk = pending[start : start + 40]
        payload = api(
            {
                "action": "wbgetentities",
                "ids": "|".join(chunk),
                "props": props,
                "languages": "en",
                "format": "json",
            }
        )
        found.update(payload.get("entities") or {})
        time.sleep(0.8)
    return found


def outgoing(entity: dict) -> list[tuple[str, str]]:
    pairs = []
    for prop in POSITIVE:
        for claim in (entity.get("claims") or {}).get(prop) or []:
            if claim.get("rank") == "deprecated":
                continue
            snak = claim.get("mainsnak") or {}
            value = (snak.get("datavalue") or {}).get("value")
            if not isinstance(value, dict) or value.get("entity-type") != "item":
                continue
            target = value.get("id")
            if target:
                pairs.append((prop, target))
    return pairs


def incoming(brand_qids: list[str]) -> list[tuple[str, str, str, int]]:
    values = " ".join(f"wd:{qid}" for qid in brand_qids)
    props = " ".join(f"wdt:{prop}" for prop in POSITIVE)
    rows = sparql(
        f"""
        SELECT ?item ?brand ?prop ?sitelinks WHERE {{
          VALUES ?brand {{ {values} }}
          VALUES ?prop {{ {props} }}
          ?item ?prop ?brand .
          FILTER(isIRI(?item) && STRSTARTS(STR(?item), "http://www.wikidata.org/entity/Q"))
          ?item wikibase:sitelinks ?sitelinks .
          FILTER(?sitelinks >= 1)
        }}
        """
    )
    return [
        (qid_of(row["item"]["value"]), qid_of(row["brand"]["value"]), qid_of(row["prop"]["value"]), int(float(row["sitelinks"]["value"])))
        for row in rows
    ]


def main() -> None:
    items = json.loads(ALIASES.read_text())["items"]
    if len(items) != 30:
        raise SystemExit(f"expected 30 ecosystems, found {len(items)}")
    brands = {row["qid"]: row["name"] for row in items}
    competitor = competitor_property()
    print("competitor_property", competitor, flush=True)
    brand_entities = entity_batch(list(brands), "claims|labels|sitelinks")
    star = []
    for brand_qid in brands:
        for prop, target in outgoing(brand_entities.get(brand_qid) or {}):
            star.append((target, brand_qid, prop))
    print("outgoing", len(star), flush=True)
    incoming_rows = []
    try:
        incoming_rows = incoming(list(brands))
        print("incoming", len(incoming_rows), flush=True)
    except Exception as exc:
        print("incoming unavailable", type(exc).__name__, exc, flush=True)
    per_brand_top: dict[str, list[tuple[str, str, int]]] = defaultdict(list)
    for item, brand_qid, prop, sitelinks in incoming_rows:
        per_brand_top[brand_qid].append((item, prop, sitelinks))
    chosen_incoming = []
    for brand_qid, rows in per_brand_top.items():
        best: dict[str, tuple[str, int]] = {}
        for item, prop, sitelinks in rows:
            current = best.get(item)
            if current is None or sitelinks > current[1]:
                best[item] = (prop, sitelinks)
        ranked = sorted(best.items(), key=lambda pair: -pair[1][1])[:40]
        for item, (prop, sitelinks) in ranked:
            chosen_incoming.append((item, brand_qid, prop, sitelinks))
    print("incoming kept", len(chosen_incoming), flush=True)
    raw_targets = sorted({item for item, _brand, _prop in star if item not in brands} | {item for item, _b, _p, _s in chosen_incoming})
    described = entity_batch(raw_targets, "labels|sitelinks")
    known_sitelinks = {item: sitelinks for item, _brand, _prop, sitelinks in chosen_incoming}
    for item, brand_qid, prop, _sitelinks in chosen_incoming:
        star.append((item, brand_qid, prop))
    by_brand: dict[str, list[dict]] = {qid: [] for qid in brands}
    touched: dict[str, set[str]] = defaultdict(set)
    info: dict[str, dict] = {}
    star_edges = []
    for item, brand_qid, prop in star:
        if item == brand_qid or brand_qid not in brands:
            continue
        if item in brands:
            label = brands[item]
            sitelinks = len((brand_entities.get(item) or {}).get("sitelinks") or {}) or 1
        else:
            entity = described.get(item) or {}
            label = ((entity.get("labels") or {}).get("en") or {}).get("value") or ""
            sitelinks = len(entity.get("sitelinks") or {}) or known_sitelinks.get(item, 0)
            if not label or sitelinks < 1:
                continue
        touched[item].add(brand_qid)
        current = info.get(item)
        if current is None or sitelinks > current["sitelinks"]:
            info[item] = {"qid": item, "label": label, "sitelinks": sitelinks, "property": prop}
        star_edges.append((brand_qid, item, info[item]["property"] if item not in brands else prop))
        if item not in brands and all(row["qid"] != item for row in by_brand[brand_qid]):
            by_brand[brand_qid].append(info[item])
    for brand_qid, neighbors in by_brand.items():
        print(brands[brand_qid], len(neighbors), flush=True)
    cross = {qid for qid, owners in touched.items() if len(owners) >= 2 and qid not in brands}
    sample = set(brands) | set(cross)
    for brand_qid, neighbors in by_brand.items():
        ranked = sorted(neighbors, key=lambda row: (-row["sitelinks"], row["label"]))
        sample.update(row["qid"] for row in ranked[:25])
    sample_entities = entity_batch([qid for qid in sample if qid not in brands], "claims")
    inter = []
    for qid, entity in sample_entities.items():
        for prop, target in outgoing(entity):
            if target in sample and target != qid:
                inter.append((qid, target, prop))
    print("sample", len(sample), "cross", len(cross), "inter", len(inter), flush=True)
    undirected = {}
    for left, right, prop in star_edges + inter:
        if left == right:
            continue
        key = tuple(sorted((left, right)))
        undirected.setdefault(key, prop)
    degree = defaultdict(int)
    neighbors_of = defaultdict(set)
    for (left, right), _prop in undirected.items():
        neighbors_of[left].add(right)
        neighbors_of[right].add(left)
        degree[left] += 1
        degree[right] += 1
    hubs = {qid for qid, count in degree.items() if count >= 6}
    keep = set(brands) | cross | hubs
    for hub in list(hubs):
        keep.update(neighbors_of[hub])
    for brand_qid, neighbors in by_brand.items():
        if len(neighbors) < 6:
            continue
        ranked = sorted(neighbors, key=lambda row: (-row["sitelinks"], row["label"]))
        for row in ranked:
            if len(keep) >= CAP:
                break
            keep.add(row["qid"])
    keep = {qid for qid in keep if qid in brands or qid in info}
    if len(keep) > CAP:
        protected = set(brands) | cross
        extra = [qid for qid in keep if qid not in protected]
        extra.sort(key=lambda qid: (qid not in hubs, -(info.get(qid) or {}).get("sitelinks", 0)))
        keep = set(protected)
        for qid in extra:
            if len(keep) >= CAP:
                break
            keep.add(qid)
    names = dict(brands)
    used = set(names.values())
    for qid in sorted(keep):
        if qid in names:
            continue
        label = info[qid]["label"]
        if label in used:
            label = f"{label} ({qid})"
        names[qid] = label
        used.add(label)
    estimates = json.loads(AUGMENTED.read_text())["edge_class_estimates"]
    nodes = []
    for qid in sorted(keep, key=lambda item: names[item]):
        owners = [brands[owner] for owner in sorted(touched.get(qid) or []) if owner in brands]
        nodes.append(
            {
                "id": names[qid],
                "qid": qid,
                "kind": "brand" if qid in brands else "related",
                "ecosystem": brands.get(qid) or (owners[0] if owners else ""),
                "ecosystems": [brands[qid]] if qid in brands else owners,
                "popularity": int((info.get(qid) or {}).get("sitelinks") or len((brand_entities.get(qid) or {}).get("sitelinks") or {}) or 1),
                "hub": qid in brands or degree[qid] >= 6,
            }
        )
    links = []
    draw = []
    seen = set()
    for (left, right), prop in sorted(undirected.items()):
        if left not in keep or right not in keep:
            continue
        src, dst = names[left], names[right]
        for source, target in ((src, dst), (dst, src)):
            links.append({"src": source, "dst": target, "sign": 1, "kind": "positive", "property": prop})
        key = tuple(sorted((src, dst)))
        if key not in seen:
            seen.add(key)
            draw.append({"src": src, "dst": dst, "kind": "positive", "property": prop})
    payload = {
        "magnitudes": {
            "positive": estimates["positive"],
            "competitor": estimates["negative"],
            "comention": estimates["comention"],
        },
        "competitor_property": competitor,
        "nodes": nodes,
        "links": links,
        "draw": draw,
    }
    OUT.write_text(json.dumps(payload) + "\n")
    print(
        f"nodes {len(nodes)} edges {len(draw)} directed {len(links)} ecosystems {len({node['ecosystem'] for node in nodes})} hubs {sum(1 for node in nodes if node['hub'])}",
        flush=True,
    )


if __name__ == "__main__":
    main()

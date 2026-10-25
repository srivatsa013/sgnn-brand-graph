"""Expand the frozen GDELT allow-list before the one rerun.

Additions are reserve names for Arm B controls. They are not graph edges
and they are not Arm A controls. Titles and mids come from Wikidata.
"""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOW = ROOT / "configs" / "gdelt_frozen_allowlist.json"
NODES = ROOT / "configs" / "phase2_nodes.json"
EDGES = ROOT / "kg" / "phase2_structural_edges.json"
UA = "sgnn-csp-phase2/0.1 (srivatsa.singaraju2023@vitstudent.ac.in)"
NOTE = "reserve, Arm B controls only"
NAMED = [
    "Cisco",
    "Texas Instruments",
    "PayPal",
    "ServiceNow",
    "Uber",
    "Airbnb",
    "Spotify",
    "Twitter",
    "Zoom Video Communications",
    "LinkedIn",
    "Pinterest",
]


def get(url: str) -> dict:
    last = None
    for attempt in range(6):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(request, timeout=120) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            last = exc
            time.sleep(min(30, 2 ** attempt))
    raise RuntimeError(last)


def underscore(title: str) -> str:
    return title.replace(" ", "_")


def wiki_qids(titles: list[str]) -> dict[str, str]:
    query = urllib.parse.urlencode(
        {
            "action": "query",
            "prop": "pageprops",
            "ppprop": "wikibase_item",
            "redirects": "1",
            "format": "json",
            "titles": "|".join(titles),
        }
    )
    data = get("https://en.wikipedia.org/w/api.php?" + query)
    pages = data.get("query", {}).get("pages", {})
    found = {}
    for page in pages.values():
        qid = (page.get("pageprops") or {}).get("wikibase_item")
        if qid and page.get("title"):
            found[page["title"]] = qid
    return found


def entities(qids: list[str]) -> dict:
    out = {}
    for start in range(0, len(qids), 40):
        chunk = "|".join(qids[start : start + 40])
        query = urllib.parse.urlencode(
            {
                "action": "wbgetentities",
                "ids": chunk,
                "props": "claims|sitelinks|labels",
                "languages": "en",
                "format": "json",
            }
        )
        data = get("https://www.wikidata.org/w/api.php?" + query)
        out.update(data.get("entities") or {})
        time.sleep(0.3)
    return out


def claim_values(entity: dict, prop: str) -> list:
    values = []
    for claim in (entity.get("claims") or {}).get(prop) or []:
        if claim.get("rank") == "deprecated":
            continue
        snak = claim.get("mainsnak") or {}
        if snak.get("snaktype") != "value":
            continue
        values.append(snak.get("datavalue", {}).get("value"))
    return values


def mid_of(entity: dict) -> list[str]:
    mids = []
    for value in claim_values(entity, "P646"):
        if not isinstance(value, str) or not value.strip():
            continue
        mid = value.strip()
        if not mid.startswith("/"):
            mid = "/" + mid
        mids.append(mid)
    return sorted(set(mids))


def en_title(entity: dict) -> str | None:
    site = (entity.get("sitelinks") or {}).get("enwiki") or {}
    return site.get("title")


def sitelinks(entity: dict) -> int:
    return len(entity.get("sitelinks") or {})


def parents_of(entity: dict) -> list[str]:
    found = []
    for value in claim_values(entity, "P749"):
        if isinstance(value, dict) and value.get("id"):
            found.append(value["id"])
    return found


def sp500() -> list[str]:
    query = """
    SELECT ?item ?sitelinks WHERE {
      ?item wdt:P361 wd:Q242345 .
      ?item wikibase:sitelinks ?sitelinks .
      FILTER(?sitelinks >= 60)
    }
    """
    url = "https://query.wikidata.org/sparql?" + urllib.parse.urlencode({"query": query, "format": "json"})
    data = get(url)
    qids = []
    for row in data["results"]["bindings"]:
        qids.append(row["item"]["value"].rsplit("/", 1)[-1])
    return sorted(set(qids))


def main() -> None:
    allow = json.loads(ALLOW.read_text())
    nodes = json.loads(NODES.read_text())
    edges = json.loads(EDGES.read_text())
    by_qid = {}
    for row in allow["entities"]:
        if row.get("qid"):
            by_qid.setdefault(row["qid"], row)
    pages = wiki_qids(NAMED)
    print("pages", pages, flush=True)
    brand_qids = []
    for name in nodes["ecosystems"]:
        brand_qids.extend(edges["node_qids"].get(name) or [])
    named_qids = list(pages.values())
    sp = sp500()
    print("sp500_at_least_60", len(sp), flush=True)
    first = entities(sorted(set(named_qids + brand_qids)))
    parent_qids = []
    for qid, entity in first.items():
        if "missing" in entity:
            continue
        parent_qids.extend(parents_of(entity))
    parent_qids = sorted(set(parent_qids))
    print("parents", len(parent_qids), flush=True)
    second = entities(sorted(set(parent_qids + sp)))
    catalog = {**first, **second}

    def add(qid: str, why: str) -> None:
        entity = catalog.get(qid) or {}
        if not entity or "missing" in entity:
            print("missing", qid, why, flush=True)
            return
        title = en_title(entity)
        mids = mid_of(entity)
        links = sitelinks(entity)
        label = ((entity.get("labels") or {}).get("en") or {}).get("value") or title or qid
        if qid in by_qid:
            row = by_qid[qid]
            if title:
                row["titles"] = sorted(set(row.get("titles") or []) | {underscore(title)})
            if mids:
                row["mids"] = sorted(set(row.get("mids") or []) | set(mids))
            return
        if links < 60 and why != "named":
            return
        if not title and not mids:
            print("no title and no mid", qid, label, why, flush=True)
            return
        row = {
            "name": label,
            "role": "reserve",
            "qid": qid,
            "titles": [underscore(title)] if title else [],
            "mids": mids,
            "sitelinks": links,
            "note": NOTE,
            "added_on": "2026-10-21",
            "why": why,
        }
        allow["entities"].append(row)
        by_qid[qid] = row
        print("add", why, qid, label, links, row["titles"], row["mids"], flush=True)

    for qid in named_qids:
        add(qid, "named")
    for qid in sp:
        add(qid, "sp500")
    for qid in parent_qids:
        add(qid, "parent")

    # Ticker PINS maps through the Pinterest page.
    pinterest_qid = pages.get("Pinterest")
    pinterest = catalog.get(pinterest_qid) or {}
    p_title = en_title(pinterest) if pinterest else None
    p_mids = mid_of(pinterest) if pinterest else []
    for row in allow["entities"]:
        if row["name"] in {"PINS", "Pinterest"} or row.get("qid") == "Q96095585":
            if p_title:
                row["titles"] = sorted(set(row.get("titles") or []) | {underscore(p_title)})
            if p_mids:
                row["mids"] = sorted(set(row.get("mids") or []) | set(p_mids))
            row["note"] = (
                "Ticker item Q96095585 had no English title and no P646. "
                f"Mapped through the Pinterest page {pinterest_qid}. {NOTE if row['name'] == 'Pinterest' else ''}"
            ).strip()

    linkedin_qid = pages.get("LinkedIn")
    linkedin = catalog.get(linkedin_qid) or {}
    if linkedin and "missing" not in linkedin:
        title = en_title(linkedin) or "LinkedIn"
        mids = mid_of(linkedin)
        row = by_qid.get(linkedin_qid)
        if row is None:
            row = {
                "name": "LinkedIn",
                "role": "product",
                "qid": linkedin_qid,
                "titles": [],
                "mids": [],
                "added_on": "2026-10-21",
            }
            allow["entities"].append(row)
            by_qid[linkedin_qid] = row
        row["titles"] = sorted(set(row.get("titles") or []) | {underscore(title), "LinkedIn"})
        row["mids"] = sorted(set(row.get("mids") or []) | set(mids))
        row["note"] = "English Wikipedia title LinkedIn. Not only LinkedIn_Corporation."

    allow["expanded_on"] = "2026-10-21"
    allow["reserve_note"] = NOTE
    ALLOW.write_text(json.dumps(allow, indent=2) + "\n")
    titles = {title for row in allow["entities"] for title in row.get("titles") or []}
    mids = {mid for row in allow["entities"] for mid in row.get("mids") or []}
    print("entities", len(allow["entities"]), "titles", len(titles), "mids", len(mids), flush=True)
    required = {
        "Pinterest": ("Pinterest",),
        "LinkedIn": ("LinkedIn",),
        "Meta": ("Facebook", "Meta_Platforms"),
        "Larry Page": ("Larry_Page",),
        "Sundar Pichai": ("Sundar_Pichai",),
    }
    by_name = {row["name"]: row for row in allow["entities"]}
    for name, need in required.items():
        row = by_name.get(name)
        have = set(row.get("titles") or []) if row else set()
        mids_have = row.get("mids") if row else []
        print("confirm", name, "titles", sorted(have & set(need)), "mids", mids_have, flush=True)


if __name__ == "__main__":
    main()

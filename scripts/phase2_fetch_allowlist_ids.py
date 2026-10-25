"""Resolve left-out companies, rival mentions, and P646 mids.

No graph edge is written. Titles for the seven ambiguous tickers are not requested.
"""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UA = "sgnn-csp-phase2/0.1"
SEARCHES = {
    "AZO": "AutoZone",
    "AAP": "Advance Auto Parts",
    "GPC": "Genuine Parts Company",
    "ALB": "Albemarle Corporation",
    "RIVN": "Rivian",
    "LCID": "Lucid Motors",
    "STLA": "Stellantis",
    "HMC": "Honda",
    "VWAGY": "Volkswagen Group",
    "Larry_Page": "Larry Page",
    "Sundar_Pichai": "Sundar Pichai",
    "Under_Armour": "Under Armour",
    "Adidas": "Adidas",
    "Gannett": "Gannett",
    "News_Corp": "News Corp",
}
PAGES = {
    "Chipotle": ("Chipotle_Mexican_Grill", ["McDonald's", "Yum! Brands", "Yum Brands"]),
    "T-Mobile US": ("T-Mobile_US", ["AT&T", "Verizon"]),
    "Lowe's": ("Lowe's", ["Home Depot"]),
    "Mastercard": ("Mastercard", ["Visa"]),
    "Chevron": ("Chevron_Corporation", ["ExxonMobil", "Exxon"]),
    "Hershey": ("The_Hershey_Company", ["Mondelēz", "Mondelez"]),
    "Colgate-Palmolive": ("Colgate-Palmolive", ["Procter & Gamble", "Kimberly-Clark"]),
    "Eli Lilly": ("Eli_Lilly_and_Company", ["Pfizer", "Merck", "AbbVie"]),
    "John Deere": ("John_Deere", ["Caterpillar"]),
    "NextEra Energy": ("NextEra_Energy", ["Duke Energy", "Southern Company"]),
    "Nike": ("Nike,_Inc.", ["Under Armour", "Adidas"]),
    "New York Times Co": ("The_New_York_Times_Company", ["News Corp", "Gannett"]),
}


def get(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.load(resp)
        except Exception as exc:
            if attempt == 3:
                raise
            time.sleep(8 * (attempt + 1))
            last = exc
    raise last


def search(text: str) -> list[dict]:
    url = "https://www.wikidata.org/w/api.php?" + urllib.parse.urlencode(
        {
            "action": "wbsearchentities",
            "search": text,
            "language": "en",
            "type": "item",
            "limit": 3,
            "format": "json",
        }
    )
    payload = get(url)
    return [
        {"id": row.get("id"), "label": row.get("label"), "description": row.get("description")}
        for row in payload.get("search") or []
    ]


def wiki_sections(title: str) -> list[dict]:
    url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode(
        {
            "action": "parse",
            "page": title,
            "prop": "sections",
            "format": "json",
        }
    )
    payload = get(url)
    return payload.get("parse", {}).get("sections") or []


def wiki_text(title: str, section: str) -> str:
    url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode(
        {
            "action": "parse",
            "page": title,
            "prop": "wikitext",
            "section": section,
            "format": "json",
        }
    )
    payload = get(url)
    return payload.get("parse", {}).get("wikitext", {}).get("*") or ""


def main() -> None:
    found = {}
    for key, text in SEARCHES.items():
        found[key] = search(text)
        print(key, found[key][:1], flush=True)
        time.sleep(1.2)
    (ROOT / "eval" / "results" / "phase2_leftout_search.json").write_text(json.dumps(found, indent=2))

    sources = {}
    for name, (title, names) in PAGES.items():
        sections = wiki_sections(title)
        time.sleep(0.8)
        competition = next((row for row in sections if row.get("line", "").lower() == "competition"), None)
        section_index = competition["index"] if competition else "0"
        section_line = competition["line"] if competition else "lead"
        text = wiki_text(title, section_index)
        time.sleep(0.8)
        hits = []
        for wanted in names:
            at = text.lower().find(wanted.lower())
            if at >= 0:
                start = max(0, at - 40)
                snippet = " ".join(text[start : at + len(wanted) + 40].split())
                hits.append({"name": wanted, "snippet": snippet[:140]})
        sources[name] = {
            "page": title,
            "section": section_line,
            "section_index": section_index,
            "names_found": hits,
            "retrieved": "2026-10-19",
        }
        print(name, section_line, [row["name"] for row in hits], flush=True)
    (ROOT / "eval" / "results" / "phase2_rival_sources.json").write_text(json.dumps(sources, indent=2))

    allow = json.loads((ROOT / "configs" / "scan_allowlist.json").read_text())
    qids = sorted({row["qid"] for row in allow["nodes"] if row.get("qid")})
    extra = []
    for key, hits in found.items():
        if hits:
            extra.append(hits[0]["id"])
    qids = sorted(set(qids) | set(extra))
    values = " ".join(f"wd:{qid}" for qid in qids)
    query = f"""
    SELECT ?item ?mid ?title WHERE {{
      VALUES ?item {{ {values} }}
      OPTIONAL {{ ?item wdt:P646 ?mid }}
      OPTIONAL {{
        ?article schema:about ?item ;
                 schema:isPartOf <https://en.wikipedia.org/> ;
                 schema:name ?title .
      }}
    }}
    """
    url = "https://query.wikidata.org/sparql"
    data = urllib.parse.urlencode({"query": query}).encode()
    req = urllib.request.Request(url, data=data, headers={"User-Agent": UA, "Accept": "application/sparql-results+json"})
    time.sleep(5)
    with urllib.request.urlopen(req, timeout=180) as resp:
        payload = json.load(resp)
    (ROOT / "eval" / "results" / "phase2_p646.json").write_text(json.dumps(payload))
    print("p646 bindings", len(payload["results"]["bindings"]), flush=True)


if __name__ == "__main__":
    main()

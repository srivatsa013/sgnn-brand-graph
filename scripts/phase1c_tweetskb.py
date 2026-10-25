"""Phase 1C TweetsKB aggregates from the public SPARQL endpoint.

Counts and mean sentiment only. No tweet text, no tweet-id hydration,
no H1-H4 outcome. The endpoint is the published 5 percent sample.
"""

from __future__ import annotations

import json
import socket
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "eval" / "results" / "phase1c_tweetskb.json"
ENDPOINT = "https://data.gesis.org/tweetskb/sparql"
UA = "sgnn-csp-phase1c/0.1 (academic research; undergraduate project)"

# Linked ids only. Alternate URIs are tried when the first count is zero.
NODES = {
    "Apple": ["http://dbpedia.org/resource/Apple_Inc."],
    "iPhone": ["http://dbpedia.org/resource/IPhone"],
    "MacBook": ["http://dbpedia.org/resource/MacBook"],
    "Tim Cook": ["http://dbpedia.org/resource/Tim_Cook"],
    "DELL": ["http://dbpedia.org/resource/Dell"],
    "HPQ": ["http://dbpedia.org/resource/HP_Inc.", "http://dbpedia.org/resource/Hewlett-Packard"],
    "LOGI": ["http://dbpedia.org/resource/Logitech"],
    "Microsoft": ["http://dbpedia.org/resource/Microsoft"],
    "Windows": ["http://dbpedia.org/resource/Microsoft_Windows"],
    "Azure": ["http://dbpedia.org/resource/Microsoft_Azure"],
    "Satya Nadella": ["http://dbpedia.org/resource/Satya_Nadella"],
    "ORCL": ["http://dbpedia.org/resource/Oracle_Corporation"],
    "CRM": ["http://dbpedia.org/resource/Salesforce", "http://dbpedia.org/resource/Salesforce.com"],
    "IBM": ["http://dbpedia.org/resource/IBM"],
    "ADBE": ["http://dbpedia.org/resource/Adobe_Inc.", "http://dbpedia.org/resource/Adobe_Systems"],
    "Google": ["http://dbpedia.org/resource/Google"],
    "Alphabet": ["http://dbpedia.org/resource/Alphabet_Inc."],
    "YouTube": ["http://dbpedia.org/resource/YouTube"],
    "Android": ["http://dbpedia.org/resource/Android_(operating_system)"],
    "Sundar Pichai": ["http://dbpedia.org/resource/Sundar_Pichai"],
    "Meta": ["http://dbpedia.org/resource/Meta_Platforms", "http://dbpedia.org/resource/Facebook"],
    "AMZN": ["http://dbpedia.org/resource/Amazon_(company)"],
    "SNAP": ["http://dbpedia.org/resource/Snap_Inc.", "http://dbpedia.org/resource/Snapchat"],
    "PINS": ["http://dbpedia.org/resource/Pinterest"],
    "Tesla": ["http://dbpedia.org/resource/Tesla,_Inc.", "http://dbpedia.org/resource/Tesla_Motors"],
    "Model 3": ["http://dbpedia.org/resource/Tesla_Model_3"],
    "Model S": ["http://dbpedia.org/resource/Tesla_Model_S"],
    "Elon Musk": ["http://dbpedia.org/resource/Elon_Musk"],
    "F": ["http://dbpedia.org/resource/Ford_Motor_Company"],
    "GM": ["http://dbpedia.org/resource/General_Motors"],
    "TM": ["http://dbpedia.org/resource/Toyota"],
    "NIO": ["http://dbpedia.org/resource/NIO_(car_company)", "http://dbpedia.org/resource/Nio_Inc."],
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


PREFIX = """
PREFIX schema: <http://schema.org/>
PREFIX nee: <http://www.ics.forth.gr/isl/oae/core#>
PREFIX onyx: <http://www.gsi.dit.upm.es/ontologies/onyx/ns#>
PREFIX wna: <http://www.gsi.dit.upm.es/ontologies/wnaffect/ns#>
PREFIX dc: <http://purl.org/dc/terms/>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
PREFIX sioc: <http://rdfs.org/sioc/ns#>
"""


def sparql(query: str) -> dict:
    data = urllib.parse.urlencode({"query": PREFIX + query}).encode()
    last = None
    for attempt in range(3):
        try:
            request = urllib.request.Request(
                ENDPOINT,
                data=data,
                headers={"User-Agent": UA, "Accept": "application/sparql-results+json"},
            )
            with urllib.request.urlopen(request, timeout=180) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            body = ""
            if hasattr(exc, "read"):
                try:
                    body = exc.read().decode("utf-8", "replace")[:500]
                except Exception:
                    body = ""
            last = exc
            print(f"retry {attempt}: {exc} {body}", flush=True)
            time.sleep(min(20, 2 ** attempt))
    raise RuntimeError(last)


def count_uri(uri: str) -> int | None:
    query = f"""
    SELECT (COUNT(?tweet) AS ?n) WHERE {{
      ?tweet schema:mentions ?entity .
      ?entity nee:hasMatchedURI <{uri}> .
    }}
    """
    try:
        rows = sparql(query)["results"]["bindings"]
    except Exception as exc:
        print("count failed", uri, exc, flush=True)
        return None
    if not rows:
        return 0
    return int(rows[0]["n"]["value"])


def daily(uri: str) -> list[dict]:
    """One row per tweet. Two annotations of the same entity do not add."""
    query = f"""
    SELECT ?day (COUNT(?tweet) AS ?n) (SUM(?signed) AS ?sum) (SUM(?scored) AS ?scored)
    WHERE {{
      {{
        SELECT ?tweet ?day
               ((MAX(?pos0) - MAX(?neg0)) AS ?signed)
               (MAX(?flag) AS ?scored)
        WHERE {{
          ?tweet schema:mentions ?entity .
          ?entity nee:hasMatchedURI <{uri}> .
          ?tweet dc:created ?date .
          BIND(SUBSTR(STR(?date), 1, 10) AS ?day)
          OPTIONAL {{
            ?tweet onyx:hasEmotionSet/onyx:hasEmotion ?epos .
            ?epos onyx:hasEmotionCategory wna:positive-emotion ;
                  onyx:hasEmotionIntensity ?pos .
          }}
          OPTIONAL {{
            ?tweet onyx:hasEmotionSet/onyx:hasEmotion ?eneg .
            ?eneg onyx:hasEmotionCategory wna:negative-emotion ;
                  onyx:hasEmotionIntensity ?neg .
          }}
          BIND(IF(BOUND(?pos), ?pos, 0) AS ?pos0)
          BIND(IF(BOUND(?neg), ?neg, 0) AS ?neg0)
          BIND(IF(BOUND(?pos) || BOUND(?neg), 1, 0) AS ?flag)
        }}
        GROUP BY ?tweet ?day
      }}
    }}
    GROUP BY ?day
    """
    rows = sparql(query)["results"]["bindings"]
    out = []
    for row in rows:
        out.append(
            {
                "day": row["day"]["value"],
                "n": int(float(row["n"]["value"])),
                "sum": float(row["sum"]["value"]) if row.get("sum") else 0.0,
                "scored": int(float(row["scored"]["value"])) if row.get("scored") else 0,
            }
        )
    return out


def comention_probe() -> dict:
    query = """
    SELECT (COUNT(DISTINCT ?tweet) AS ?n) WHERE {
      ?tweet schema:mentions ?iphone .
      ?iphone nee:hasMatchedURI <http://dbpedia.org/resource/IPhone> .
      ?tweet dc:created ?date .
      FILTER(?date >= "2019-06-01"^^xsd:date && ?date < "2019-07-01"^^xsd:date)
      FILTER NOT EXISTS {
        ?tweet schema:mentions ?apple .
        ?apple nee:hasMatchedURI <http://dbpedia.org/resource/Apple_Inc.> .
      }
    }
    """
    try:
        rows = sparql(query)["results"]["bindings"]
        value = int(rows[0]["n"]["value"]) if rows else None
        return {"expressible": True, "june_2019_iphone_not_apple": value, "error": None}
    except Exception as exc:
        return {"expressible": True, "june_2019_iphone_not_apple": None, "error": str(exc)}


def main() -> None:
    prefer_ipv4()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "endpoint": ENDPOINT,
        "sample": "public SPARQL endpoint, documented as a 5 percent sample",
        "signed_score": "positive_intensity_minus_negative_intensity on [0,1] intensities",
        "nodes": {},
    }
    for name, uris in NODES.items():
        chosen = None
        counts = {}
        for uri in uris:
            n = count_uri(uri)
            counts[uri] = n
            print(name, uri, n, flush=True)
            if n:
                chosen = uri
                break
        entry = {"uri_counts": counts, "chosen": chosen, "days": None, "error": None}
        if chosen:
            try:
                entry["days"] = daily(chosen)
                print(name, "days", len(entry["days"]), flush=True)
            except Exception as exc:
                entry["error"] = str(exc)
                print(name, "daily failed", exc, flush=True)
        payload["nodes"][name] = entry
        OUT.write_text(json.dumps(payload))
    payload["comention"] = comention_probe()
    OUT.write_text(json.dumps(payload))
    print("comention", payload["comention"], flush=True)


if __name__ == "__main__":
    main()

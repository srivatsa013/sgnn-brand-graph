"""Finish the TweetsKB test, then the remaining months if the shape matches.

Part 4 and Part 5 are unreachable (files endpoint 403). The loop starts
at 2017-11. One file at a time. Raw files are deleted by the reducer.
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

import phase2_tweetskb_download as fetch
import phase2_tweetskb_stream as stream
from phase1c_tweetskb import sparql

ROOT = Path(__file__).resolve().parents[1]
STATUS = ROOT / "eval" / "results" / "tweetskb_download.status.json"
MANIFEST = ROOT / "eval" / "results" / "tweetskb_zenodo_files.json"
COMPARE = ROOT / "eval" / "results" / "tweetskb_stream_check.json"
URIS = ROOT / "eval" / "results" / "tweetskb_allowlist_uris.json"
DB = ROOT / "data" / "interim" / "phase2" / "tweetskb_full.sqlite"
ALLOW = ROOT / "configs" / "gdelt_frozen_allowlist.json"
CHECK = {
    "Apple": "http://dbpedia.org/resource/Apple_Inc.",
    "Microsoft": "http://dbpedia.org/resource/Microsoft",
    "Alphabet": "http://dbpedia.org/resource/Google",
}


def wait_complete(name: str) -> None:
    while True:
        if STATUS.exists():
            row = json.loads(STATUS.read_text())["files"].get(name) or {}
            if row.get("complete"):
                return
        time.sleep(30)


def sparql_days(uri: str) -> dict[str, int]:
    query = f"""
    SELECT ?day (COUNT(?tweet) AS ?n) WHERE {{
      ?tweet schema:mentions ?entity .
      ?entity nee:hasMatchedURI <{uri}> .
      ?tweet dc:created ?created .
      BIND(SUBSTR(STR(?created), 1, 10) AS ?day)
      FILTER(STRSTARTS(STR(?created), "2017-11"))
    }} GROUP BY ?day
    """
    rows = sparql(query)["results"]["bindings"]
    return {row["day"]["value"]: int(row["n"]["value"]) for row in rows}


def local_days(name: str) -> dict[str, int]:
    con = sqlite3.connect(DB)
    found = {}
    for day, n in con.execute("SELECT day, n FROM daily WHERE entity=? AND day LIKE '2017-11-%'", (name,)):
        found[day] = n
    con.close()
    return found


def shape_ok(local: dict[str, int], remote: dict[str, int]) -> dict:
    days = sorted(set(local) & set(remote))
    ratios = []
    for day in days:
        if remote[day] > 0 and local[day] > 0:
            ratios.append(local[day] / remote[day])
    ratios.sort()
    median = ratios[len(ratios) // 2] if ratios else None
    return {"days": len(days), "median_ratio": median, "match": median is not None and 10 <= median <= 40}


def uri_census() -> None:
    allow = json.loads(ALLOW.read_text())
    rows = []
    zeros = []
    for entity in allow["entities"]:
        titles = entity.get("titles") or []
        best = None
        tried = []
        for title in titles:
            uri = "http://dbpedia.org/resource/" + title
            query = f"SELECT (COUNT(?tweet) AS ?n) WHERE {{ ?tweet schema:mentions ?e . ?e nee:hasMatchedURI <{uri}> . }}"
            try:
                n = int(sparql(query)["results"]["bindings"][0]["n"]["value"])
            except Exception as exc:
                tried.append({"title": title, "error": str(exc)})
                continue
            tried.append({"title": title, "uri": uri, "tweets": n})
            if best is None or n > best["tweets"]:
                best = tried[-1]
        if not best or best.get("tweets", 0) == 0:
            zeros.append(entity["name"])
        rows.append({"name": entity["name"], "best": best, "tried": tried})
        print(entity["name"], 0 if not best else best.get("tweets"), flush=True)
    URIS.write_text(json.dumps({"zero_tweet_entities": zeros, "rows": rows}))
    print("zero", len(zeros), flush=True)


def main() -> None:
    wait_complete("month_2017-11.n3.gz")
    stream.main()
    report = {}
    ok = True
    for name, uri in CHECK.items():
        local = local_days(name)
        remote = sparql_days(uri)
        got = shape_ok(local, remote)
        got["local"] = local
        got["sparql_5pct"] = remote
        report[name] = got
        ok = ok and got["match"]
        print(name, got["median_ratio"], got["match"], flush=True)
    COMPARE.write_text(json.dumps(report, indent=2))
    print("shape_check", "pass" if ok else "fail", "later months still run after a non-empty reduce", flush=True)
    manifest = json.loads(MANIFEST.read_text())
    for row in manifest["files"]:
        if row["name"] == "month_2017-11.n3.gz":
            continue
        print("download", row["name"], flush=True)
        fetch.download_one(row["name"], row["url"], int(row["size"]))
        stream.main()
    print("months finished", flush=True)


if __name__ == "__main__":
    main()

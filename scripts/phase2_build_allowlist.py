"""Build the GDELT and TweetsKB allow-list. Does not add graph edges."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "configs" / "scan_allowlist.json"


def uri(title: str) -> str:
    return "http://dbpedia.org/resource/" + title.replace(" ", "_")


def add(rows: dict, name: str, **fields) -> None:
    key = fields.get("enwiki") or name
    current = rows.get(key)
    if current is None:
        rows[key] = {"name": name, **fields}
        return
    for field, value in fields.items():
        if value and not current.get(field):
            current[field] = value


def main() -> None:
    arm_b = json.loads((ROOT / "configs" / "arm_b_dbpedia_uris.json").read_text())
    gdelt = json.loads((ROOT / "configs" / "gdelt_match_rule.json").read_text())
    entities = json.loads((ROOT / "kg" / "snapshots" / "wikidata_2026-10-12" / "entities.json").read_text())
    tickers = json.loads((ROOT / "kg" / "snapshots" / "wikidata_2026-10-12" / "tickers.json").read_text())
    universe = json.loads((ROOT / "configs" / "phase1_universe.json").read_text())
    brands = json.loads((ROOT / "eval" / "results" / "phase2_brand_edges.json").read_text())
    rows: dict[str, dict] = {}

    for name, node in arm_b["nodes"].items():
        title = node.get("enwiki")
        add(
            rows,
            name,
            role=node.get("role") or "study",
            qid=node.get("wikidata_qid"),
            enwiki=title,
            dbpedia=node.get("series_uri") or (uri(title) if title else None),
            mids=[],
            graph_edge=True,
        )
    for name, node in gdelt["nodes"].items():
        add(rows, name, role="study", enwiki=node.get("enwiki"), dbpedia=uri(node["enwiki"]) if node.get("enwiki") else None, mids=node.get("mids") or [])

    for brand in brands["brands"]:
        add(
            rows,
            brand["name"],
            role="candidate_brand",
            qid=brand["qid"],
            ticker=brand["ticker"],
            enwiki=brand["enwiki"],
            dbpedia=uri(brand["enwiki"]),
            mids=[],
            graph_edge=False,
        )
    for peer in brands["peers"]:
        add(
            rows,
            peer["name"],
            role="candidate_competitor",
            qid=peer["qid"],
            ticker=peer["ticker"],
            enwiki=peer["enwiki"],
            dbpedia=uri(peer["enwiki"]),
            mids=[],
            graph_edge=False,
            note="On the allow-list for the scan. Not a graph edge. Wikidata does not state a competitor relation.",
        )
    for edge in brands["dated_ownership"]:
        if edge.get("target") == "Q35855":
            continue
        title = edge.get("enwiki")
        if not title:
            continue
        add(
            rows,
            edge.get("child_label") or title,
            role="dated_subsidiary",
            qid=edge["target"],
            enwiki=title,
            dbpedia=uri(title),
            mids=[],
            graph_edge=False,
            counts_from=edge["counts_from"],
            parent=edge["brand"],
            property=edge["property"],
        )

    for _bucket, names in universe["control_pool_by_bucket"].items():
        for ticker in names:
            chosen = (tickers.get(ticker) or {}).get("chosen") or {}
            qid = chosen.get("qid")
            title = (entities.get(qid) or {}).get("enwiki") if qid else None
            if ticker == "EPAM" and not title:
                add(
                    rows,
                    "EPAM",
                    role="control",
                    qid=qid,
                    ticker=ticker,
                    enwiki=None,
                    dbpedia="http://dbpedia.org/resource/EPAM_Systems",
                    mids=[],
                    graph_edge=False,
                    note="Wikidata Q1275613 has no English Wikipedia sitelink. The DBpedia title is the English label. GDELT has no title to match.",
                )
                continue
            if not title:
                continue
            add(rows, ticker, role="control", qid=qid, ticker=ticker, enwiki=title, dbpedia=uri(title), mids=[], graph_edge=False)

    payload = {
        "logged_on": "2026-10-14",
        "purpose": "Match list for the GDELT scan and the TweetsKB stream. A name here is not a graph edge.",
        "competitor_edges_added": False,
        "nyt_and_hershey": "Kept on this list. Coverage is decided after the GDELT scan, which has not been run.",
        "nodes": list(rows.values()),
    }
    OUT.write_text(json.dumps(payload, indent=2))

    for row in payload["nodes"]:
        if row["name"] in arm_b["nodes"]:
            continue
        if row["role"] not in {"candidate_brand", "candidate_competitor", "dated_subsidiary", "control"}:
            continue
        arm_b["nodes"][row["name"]] = {
            "arm": "B",
            "role": row["role"],
            "wikidata_qid": row.get("qid"),
            "enwiki": row.get("enwiki"),
            "series_uri": row.get("dbpedia"),
            "ticker": row.get("ticker"),
            "graph_edge": False,
            "probe_days": None,
            "note": row.get("note") or "Added to the allow-list on 2026-10-14. No probe count is invented.",
        }
    arm_b["allowlist_extended_on"] = "2026-10-14"
    (ROOT / "configs" / "arm_b_dbpedia_uris.json").write_text(json.dumps(arm_b, indent=2) + "\n")

    for row in payload["nodes"]:
        if row["name"] in gdelt["nodes"] or not row.get("enwiki"):
            continue
        if row["role"] not in {"candidate_brand", "candidate_competitor", "dated_subsidiary"}:
            continue
        gdelt["nodes"][row["name"]] = {
            "enwiki": row["enwiki"].replace(" ", "_"),
            "mids": [],
            "role": row["role"],
            "graph_edge": False,
        }
    gdelt["allowlist_extended_on"] = "2026-10-14"
    (ROOT / "configs" / "gdelt_match_rule.json").write_text(json.dumps(gdelt, indent=2) + "\n")
    print("nodes", len(payload["nodes"]), "arm_b", len(arm_b["nodes"]), "gdelt", len(gdelt["nodes"]))


if __name__ == "__main__":
    main()

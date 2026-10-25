"""Arm B news series from the stored GDELT allow-list extract.

Match rule: Wikipedia title, or mid only when the title is empty.
No bare names. One article once per node. No BigQuery.
"""

from __future__ import annotations

import gzip
import json
import sqlite3
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "interim" / "phase2" / "gdelt_allowlist"
DB = ROOT / "data" / "interim" / "phase2" / "gdelt_series.sqlite"
DOCS = ROOT / "data" / "interim" / "phase2" / "gdelt_documents.jsonl.gz"
INVENTORY = ROOT / "eval" / "results" / "phase2_gdelt_filter_inventory.json"
PRECISION = ROOT / "eval" / "results" / "phase2_gdelt_precision.json"

BRANDS = ("Apple", "Microsoft", "Alphabet")
# Tenure windows that apply inside the GDELT span. One document once.
CEO_WINDOWS = {
    "Apple CEO": [("Tim_Cook", "2011-08-24", "2026-08-31")],
    "Microsoft CEO": [("Satya_Nadella", "2014-02-04", "9999-12-31")],
    "Alphabet CEO": [
        ("Larry_Page", "2011-04-04", "2019-12-03"),
        ("Sundar_Pichai", "2015-08-10", "9999-12-31"),
    ],
}


def wiki_key(title: str) -> str:
    return title.replace(" ", "_")


def load_maps() -> tuple[dict[str, str], dict[str, str], dict[str, dict]]:
    rule = json.loads((ROOT / "configs" / "gdelt_match_rule.json").read_text())
    arm = json.loads((ROOT / "configs" / "arm_b_dbpedia_uris.json").read_text())
    wiki: dict[str, str] = {}
    mids: dict[str, str] = {}
    nodes: dict[str, dict] = {}
    for name, spec in rule["nodes"].items():
        if spec.get("role") in {"candidate_brand", "candidate_competitor", "dated_subsidiary"}:
            title = spec.get("enwiki")
            if title:
                wiki[wiki_key(title)] = name
                nodes[name] = {"enwiki": wiki_key(title), "mids": [], "group": spec["role"]}
            continue
        title = spec.get("enwiki")
        if title:
            wiki[wiki_key(title)] = name
        nodes[name] = {"enwiki": wiki_key(title) if title else None, "mids": list(spec.get("mids") or []), "group": "study"}
        for mid in spec.get("mids") or []:
            mids[mid] = name
    # Study nodes whose title is in the Arm B map but not in the original rule list.
    for name, spec in arm["nodes"].items():
        if name in nodes or name in CEO_WINDOWS:
            continue
        if spec.get("excluded_from_arm_b"):
            title = spec.get("enwiki")
            if title:
                wiki[wiki_key(title)] = name
                nodes[name] = {"enwiki": wiki_key(title), "mids": [], "group": "arm_a_only"}
            continue
        title = spec.get("enwiki")
        if name == "PINS":
            wiki["Pinterest"] = "PINS"
            nodes["PINS"] = {"enwiki": "Pinterest", "mids": [], "group": "study"}
            continue
        if name == "Meta":
            wiki["Facebook"] = "Meta"
            nodes["Meta"] = {"enwiki": "Facebook", "mids": [], "group": "study", "also_seen_title": "Meta_Platforms"}
            continue
        if not title or name == "Alphabet CEO":
            continue
        key = wiki_key(title)
        if key not in wiki:
            wiki[key] = name
            nodes[name] = {"enwiki": key, "mids": [], "group": spec.get("role") or "study"}
    # Logged iPhone title is IPhone. The public title is also iPhone.
    wiki["iPhone"] = "iPhone"
    wiki["IPhone"] = "iPhone"
    if "iPhone" in nodes:
        nodes["iPhone"]["enwiki"] = ["IPhone", "iPhone"]
    for ceo, windows in CEO_WINDOWS.items():
        nodes[ceo] = {"enwiki": [title for title, _, _ in windows], "mids": [], "group": "ceo"}
        for title, _, _ in windows:
            wiki[title] = ceo
    aliases = json.loads((ROOT / "configs" / "gdelt_alias_table.json").read_text())
    for row in aliases["accepted"]:
        wiki[row["title"]] = row["node"]
        spec = nodes.setdefault(row["node"], {"enwiki": [], "mids": [], "group": "study"})
        titles = spec.get("enwiki")
        if isinstance(titles, list):
            if row["title"] not in titles:
                titles.append(row["title"])
        elif titles:
            spec["enwiki"] = [titles, row["title"]]
        else:
            spec["enwiki"] = [row["title"]]
        if row["mid"] not in spec["mids"]:
            spec["mids"].append(row["mid"])
        mids.setdefault(row["mid"], row["node"])
    return wiki, mids, nodes


def ceo_ok(node: str, title: str, day: str) -> bool:
    windows = CEO_WINDOWS.get(node)
    if not windows:
        return True
    for allowed, start, end in windows:
        if title == allowed and start <= day <= end:
            return True
    return False


def main() -> None:
    wiki_to_node, mid_to_node, nodes = load_maps()
    wiki_counts: Counter[str] = Counter()
    mid_counts: Counter[str] = Counter()
    # node -> year -> [right_wiki, empty_mid, wrong_wiki]
    precision: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(lambda: [0, 0, 0]))
    alternate = Counter()
    daily: dict[tuple[str, str, str], list] = {}
    doc_count = 0
    if DB.exists():
        DB.unlink()
    con = sqlite3.connect(DB)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    con.execute(
        """
        CREATE TABLE daily (
          node TEXT, exclude_brand TEXT, day TEXT,
          document_count INT, scored_count INT, score_sum REAL,
          PRIMARY KEY (node, exclude_brand, day)
        )
        """
    )
    doc_batch = []
    out = gzip.open(DOCS, "wt", encoding="utf-8")

    def add_daily(node: str, exclude: str, day: str, score: float | None) -> None:
        rec = daily.get((node, exclude, day))
        if rec is None:
            rec = [0, 0, 0.0]
            daily[(node, exclude, day)] = rec
        rec[0] += 1
        if score is not None:
            rec[1] += 1
            rec[2] += score

    for path in sorted(SRC.glob("*.jsonl.gz")):
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            for line in handle:
                row = json.loads(line)
                day = row["day"]
                year = day[:4]
                score_text = row.get("score")
                score = float(score_text) if score_text not in (None, "") else None
                matched: dict[str, str] = {}
                for ent in row.get("entities") or []:
                    title = ent.get("wiki") or ""
                    mid = ent.get("mid") or ""
                    if title:
                        wiki_counts[title] += 1
                    if mid:
                        mid_counts[mid] += 1
                    node = None
                    how = None
                    if title and title in wiki_to_node:
                        node = wiki_to_node[title]
                        if ceo_ok(node, title, day):
                            how = "wiki"
                        else:
                            node = None
                    elif not title and mid in mid_to_node:
                        node = mid_to_node[mid]
                        how = "mid"
                    if node and how == "wiki":
                        matched[node] = title
                    elif node and how == "mid":
                        matched.setdefault(node, "")
                    # Precision for nodes that own this mid or this title.
                    owner = mid_to_node.get(mid)
                    titled = wiki_to_node.get(title) if title else None
                    subject = owner or titled
                    if subject and subject in {
                        "Apple", "Windows", "Azure", "Android", "Model S", "HPQ", "SNAP", "AMZN", "Meta", "iPhone", "Alphabet", "YouTube", "Samsung",
                    }:
                        bucket = precision[subject][year]
                        right = nodes[subject].get("enwiki")
                        if isinstance(right, list):
                            right_set = set(right)
                        else:
                            right_set = {right} if right else set()
                        if title and title in right_set:
                            bucket[0] += 1
                        elif not title and mid and mid in (nodes[subject].get("mids") or []):
                            bucket[1] += 1
                        elif title and mid and mid in (nodes[subject].get("mids") or []) and title not in right_set:
                            bucket[2] += 1
                            alternate[(subject, title, year)] += 1
                if not matched:
                    continue
                doc_count += 1
                names = sorted(matched)
                out.write(f"{row['url_hash']}\t{day}\t{'' if score is None else score}\t{'|'.join(names)}\n")
                brands_here = {brand for brand in BRANDS if brand in matched}
                for node in names:
                    add_daily(node, "", day, score)
                    for brand in BRANDS:
                        if brand not in brands_here:
                            add_daily(node, brand, day, score)
        print(path.name, "docs", doc_count, flush=True)
    out.close()
    rows = [
        (node, exclude, day, rec[0], rec[1], rec[2])
        for (node, exclude, day), rec in daily.items()
    ]
    con.executemany("INSERT INTO daily VALUES (?,?,?,?,?,?)", rows)
    con.commit()
    con.close()
    inventory = {
        "files": len(list(SRC.glob('*.jsonl.gz'))),
        "documents_with_a_matched_node": doc_count,
        "wiki_counts": wiki_counts.most_common(),
        "mid_counts": mid_counts.most_common(),
        "match_map_wiki": wiki_to_node,
    }
    INVENTORY.write_text(json.dumps(inventory))
    prec_out = {}
    for node, years in precision.items():
        prec_out[node] = {
            year: {"right_page": vals[0], "empty_url_mid": vals[1], "wrong_page_via_mid": vals[2]}
            for year, vals in sorted(years.items())
        }
    PRECISION.write_text(
        json.dumps(
            {
                "by_node_year": prec_out,
                "wrong_titles": [
                    {"node": node, "wiki": title, "year": year, "rows": n}
                    for (node, title, year), n in alternate.most_common()
                ],
            },
            indent=2,
        )
    )
    print("daily cells", len(rows), "docs", doc_count, flush=True)


if __name__ == "__main__":
    main()

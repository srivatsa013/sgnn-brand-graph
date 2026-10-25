"""Build the frozen GDELT allow-list. Does not query BigQuery."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AMBIGUOUS = {"ADP", "BMY", "C", "FOXA", "HAL", "MRK", "NWSA"}
DROPPED_TITLES = {"Larry Page and Sundar Pichai"}


def underscore(title: str) -> str:
    return title.replace(" ", "_")


def main() -> None:
    allow = json.loads((ROOT / "configs" / "scan_allowlist.json").read_text())
    alias = json.loads((ROOT / "configs" / "gdelt_alias_table.json").read_text())
    p646 = json.loads((ROOT / "eval" / "results" / "phase2_p646.json").read_text())
    by_qid: dict[str, dict] = {}
    for row in p646["results"]["bindings"]:
        qid = row["item"]["value"].rsplit("/", 1)[-1]
        slot = by_qid.setdefault(qid, {"mids": set(), "titles": set()})
        if row.get("mid"):
            slot["mids"].add(row["mid"]["value"])
        if row.get("title"):
            slot["titles"].add(underscore(row["title"]["value"]))

    entities = []
    seen_names = set()
    for row in allow["nodes"]:
        name = row["name"]
        ticker = row.get("ticker")
        titles = set()
        mids = set()
        qid = row.get("qid")
        if name in DROPPED_TITLES or (row.get("enwiki") in DROPPED_TITLES):
            continue
        if ticker in AMBIGUOUS:
            entities.append(
                {
                    "name": name,
                    "role": row.get("role"),
                    "ticker": ticker,
                    "qid": None,
                    "titles": [],
                    "mids": [],
                    "note": "Ambiguous ticker. No title and no mid, so the wrong page is not scanned.",
                }
            )
            seen_names.add(name)
            continue
        if row.get("enwiki") and row["enwiki"] not in DROPPED_TITLES:
            titles.add(underscore(row["enwiki"]))
        if qid and qid in by_qid:
            titles |= by_qid[qid]["titles"]
            mids |= by_qid[qid]["mids"]
        entities.append(
            {
                "name": name,
                "role": row.get("role"),
                "ticker": ticker,
                "qid": qid,
                "titles": sorted(titles),
                "mids": sorted(mids),
            }
        )
        seen_names.add(name)

    def add(name: str, role: str, qid: str | None, extra_titles: list[str], note: str | None = None) -> None:
        if name in seen_names:
            for row in entities:
                if row["name"] == name:
                    row["titles"] = sorted(set(row["titles"]) | {underscore(t) for t in extra_titles})
                    if qid and qid in by_qid:
                        row["mids"] = sorted(set(row["mids"]) | by_qid[qid]["mids"])
                        row["titles"] = sorted(set(row["titles"]) | by_qid[qid]["titles"])
            return
        titles = {underscore(t) for t in extra_titles}
        mids: set[str] = set()
        if qid and qid in by_qid:
            titles |= by_qid[qid]["titles"]
            mids |= by_qid[qid]["mids"]
        item = {"name": name, "role": role, "qid": qid, "titles": sorted(titles), "mids": sorted(mids)}
        if note:
            item["note"] = note
        entities.append(item)
        seen_names.add(name)

    add("Larry Page", "ceo", "Q4934", ["Larry Page"])
    add("Sundar Pichai", "ceo", "Q3503829", ["Sundar Pichai"])
    add("Meta", "competitor", "Q380", ["Meta Platforms", "Facebook", "Facebook,_Inc."])
    add("Pinterest", "competitor", "Q96095585", ["Pinterest"], "Ticker item has no English title and no P646. The title Pinterest is included because it was requested.")
    add("Sony", "retained_ticker", "Q41187", [], "In the 206 retained tickers. Title and mid are filled when P646 returned them.")
    for row in alias["accepted"]:
        add(row["node"], "alias", None, [row["title"]])
        for item in entities:
            if item["name"] == row["node"] and row.get("mid"):
                item["mids"] = sorted(set(item["mids"]) | {row["mid"]})

    # Left-out names and the rival pages that are not already retained tickers.
    extras = [
        ("AutoZone", "left_out", "Q4826087"),
        ("Advance Auto Parts", "left_out", "Q4686051"),
        ("Genuine Parts Company", "left_out", "Q5533818"),
        ("Albemarle Corporation", "left_out", "Q127074"),
        ("Rivian", "left_out", "Q7338847"),
        ("Lucid Motors", "left_out", "Q28027517"),
        ("Stellantis", "left_out", "Q97439162"),
        ("Honda", "left_out", "Q9584"),
        ("Volkswagen Group", "left_out", "Q156578"),
        ("Nvidia", "left_out", "Q182477"),
        ("TSMC", "left_out", "Q713418"),
        ("Broadcom", "left_out", "Q790060"),
        ("Qualcomm", "left_out", "Q544847"),
        ("AMD", "left_out", "Q128896"),
        ("Micron Technology", "left_out", "Q1197548"),
        ("Intel", "left_out", "Q248"),
        ("Applied Materials", "left_out", "Q621610"),
        ("ASML Holding", "left_out", "Q297879"),
        ("Lam Research", "left_out", "Q1342041"),
        ("KLA Corporation", "left_out", "Q624649"),
        ("Netflix", "left_out", "Q907311"),
        ("Best Buy", "left_out", "Q533415"),
        ("Garmin Ltd.", "left_out", "Q30338591"),
        ("O'Reilly Auto Parts", "left_out", "Q7071951"),
        ("Under Armour", "possible_rival", "Q2031485"),
        ("Adidas", "possible_rival", "Q3895"),
        ("News Corp", "possible_rival", "Q14289857"),
        ("USA Today Co.", "possible_rival", "Q1345971"),
    ]
    for name, role, qid in extras:
        add(name, role, qid, [])

    # Sony may be absent from the P646 file. Keep the qid so a later mid can be joined.
    payload = {
        "logged_on": "2026-10-19",
        "purpose": "Frozen allow-list for one GDELT rerun. A name here is not a graph edge.",
        "graph_edges_added": False,
        "ambiguous_tickers_without_a_title": sorted(AMBIGUOUS),
        "rejected_alias_titles_not_included": [row["title"] for row in alias["rejected"] if row["title"] != "Snap_Inc."],
        "concatenated_ceo_title_not_included": "Larry Page and Sundar Pichai",
        "entities": entities,
    }
    # Snap Inc. is SNAP's own English title, so it stays. Hewlett Packard Enterprise does not.
    out = ROOT / "configs" / "gdelt_frozen_allowlist.json"
    out.write_text(json.dumps(payload, indent=2))
    titles = {title for row in entities for title in row["titles"]}
    mids = {mid for row in entities for mid in row["mids"]}
    no_key = [row["name"] for row in entities if not row["titles"] and not row["mids"]]
    print("entities", len(entities), "titles", len(titles), "mids", len(mids))
    print("no title and no mid", no_key)


if __name__ == "__main__":
    main()

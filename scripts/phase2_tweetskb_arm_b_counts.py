"""Arm B pair counts from the reduced TweetsKB months.

Counts only. Does not compute a shift or a planning SD. Exits without
counting until every manifest month from 2017-11 through 2020-12 is
reduced into the sqlite file table.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from phase2_feasibility import NODES  # noqa: E402
from phase2_gdelt_reserve_after import ARM_B, exclusion_pairs, pair_count  # noqa: E402
from phase2_revised_recount import build_adj  # noqa: E402

DB = ROOT / "data" / "interim" / "phase2" / "tweetskb_full.sqlite"
DONE = ROOT / "eval" / "results" / "tweetskb_stream_done.json"
MANIFEST = ROOT / "eval" / "results" / "tweetskb_zenodo_files.json"
OUT = ROOT / "eval" / "results" / "phase2_tweetskb_arm_b_counts.json"


def manifest_names() -> list[str]:
    rows = json.loads(MANIFEST.read_text())["files"]
    return [row["name"] for row in rows]


def ready() -> tuple[bool, str]:
    names = manifest_names()
    if len(names) != 38 or names[0] != "month_2017-11.n3.gz" or names[-1] != "month_2020-12.n3.gz":
        return False, f"manifest is {len(names)} files, expected month_2017-11 through month_2020-12"
    done = set(json.loads(DONE.read_text()).get("files") or [])
    missing = [name for name in names if name not in done]
    if missing:
        return False, f"not reduced yet: {missing[0]}"
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    stored = {name: tweets for name, tweets in con.execute("SELECT name, tweets FROM file")}
    con.close()
    absent = [name for name in names if stored.get(name, 0) <= 0]
    if absent:
        return False, f"sqlite has no tweets for {absent[0]}"
    return True, f"months {len(names)}"


def build_series() -> dict[tuple[str, str], dict]:
    pool = json.loads((ROOT / "configs" / "phase1_universe.json").read_text())["control_pool_by_bucket"]
    keep = exclusion_pairs(build_adj(True, True), pool)
    brands = set(ARM_B)
    wanted = brands | {node for node, _eco in keep}
    series: dict[tuple[str, str], dict] = {}

    def add(node: str, exclude: str, day: str, score: float | None) -> None:
        cell = series.get((node, exclude))
        if cell is None:
            cell = {}
            series[(node, exclude)] = cell
        rec = cell.get(day)
        if rec is None:
            rec = [0.0, 0, 0]
            cell[day] = rec
        rec[2] += 1
        if score is not None:
            rec[0] += score
            rec[1] += 1

    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    cursor = con.execute("SELECT day, entities, score FROM tweet")
    seen = 0
    while True:
        rows = cursor.fetchmany(50_000)
        if not rows:
            break
        for day, entities, score in rows:
            seen += 1
            names = [name for name in entities.split("|") if name in wanted]
            if not names:
                continue
            present = set(names)
            for name in names:
                if name in brands:
                    add(name, "", day, score)
                for eco in ARM_B:
                    if (name, eco) in keep and eco not in present:
                        add(name, eco, day, score)
        if seen % 1_000_000 == 0:
            print(f"tweets {seen} cells {sum(len(days) for days in series.values())}", flush=True)
    con.close()
    print(f"tweets {seen} cells {sum(len(days) for days in series.values())}", flush=True)
    return series


def main() -> None:
    ok, message = ready()
    print(message, flush=True)
    if not ok:
        print("counts not started", flush=True)
        return
    series = build_series()
    pool = json.loads((ROOT / "configs" / "phase1_universe.json").read_text())["control_pool_by_bucket"]
    adj = build_adj(True, True)
    full = pair_count(series, adj, pool, None)
    payload = {
        "counts_only": True,
        "event_shifts_computed": False,
        "planning_sd": "not_computed",
        "ecosystems": list(ARM_B),
        "months": manifest_names(),
        "pairs_full_span": full,
    }
    OUT.write_text(json.dumps(payload) + "\n")
    for row in full["rows"]:
        print(
            f"{row['ecosystem']} events {row['events']} "
            f"H1 pairs {row['h1_pairs']} events_with_pair {row['h1_events_with_a_pair']} "
            f"H2_positive pairs {row['positive_pairs']} events {row['positive_events_with_a_pair']} "
            f"H2_competitor pairs {row['competitor_pairs']} events {row['competitor_events_with_a_pair']}",
            flush=True,
        )
    print(f"wrote {OUT}", flush=True)


if __name__ == "__main__":
    main()

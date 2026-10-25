"""After the frozen rerun: series, precision, coverage, proposed SD, pairs.

Does not replace the pre-rerun gdelt_series.sqlite. Does not freeze the SD.
"""

from __future__ import annotations

import argparse
import gzip
import json
import random
import resource
import shutil
import sqlite3
import sys
import time
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from phase1_gates import abs_shift_daily, baseline, detect_daily, eligible_placebo_days, sample_sd  # noqa: E402
from phase2_revised_recount import (  # noqa: E402
    POP_CALIPER,
    build_adj,
    both_windows,
    exclusion_starts,
    flag_map,
    ticker_row,
    within_hops,
)
from phase2_feasibility import GRAPH, NODES, pool_tickers  # noqa: E402

SRC = ROOT / "data" / "interim" / "phase2" / "gdelt_frozen_full"
DB = ROOT / "data" / "interim" / "phase2" / "gdelt_reserve_series.sqlite"
OUT = ROOT / "eval" / "results" / "phase2_gdelt_reserve_after.json"
ARM_B = tuple(eco for eco in NODES["ecosystems"] if eco != "Tesla")
if len(ARM_B) != 13 or "Tesla" in ARM_B:
    raise SystemExit(f"Arm B must be the 13 non-Tesla ecosystems, got {ARM_B}")
OVERLAP = (date(2017, 11, 1), date(2020, 12, 31))
TEST_DB = ROOT / "data" / "interim" / "phase2" / "gdelt_reserve_series_test.sqlite"
TEST_OUT = ROOT / "eval" / "results" / "phase2_gdelt_reserve_after_test.json"
TEST = False


def say(message: str) -> None:
    print(("TEST " if TEST else "") + message, flush=True)


def load_maps() -> tuple[dict[str, str], dict[str, str], dict[str, list[dict]], dict[str, set[str]]]:
    allow = json.loads((ROOT / "configs" / "gdelt_frozen_allowlist.json").read_text())
    alias = json.loads((ROOT / "configs" / "gdelt_alias_table.json").read_text())
    allow_titles: dict[str, str] = {}
    mids: dict[str, str] = {}
    aliases: dict[str, list[dict]] = defaultdict(list)
    owned: dict[str, set[str]] = defaultdict(set)
    for row in allow["entities"]:
        for title in row.get("titles") or []:
            allow_titles.setdefault(title, row["name"])
            owned[row["name"]].add(title)
        for mid in row.get("mids") or []:
            mids.setdefault(mid, row["name"])
    for row in alias["accepted"]:
        aliases[row["title"]].append(row)
        owned[row["node"]].add(row["title"])
    return allow_titles, mids, aliases, owned


def resolve_node(title: str, mid: str, allow_titles: dict[str, str], mids: dict[str, str], aliases: dict[str, list[dict]]) -> str | None:
    if title and title in allow_titles:
        return allow_titles[title]
    if title:
        for row in aliases.get(title, []):
            if mid and mid == row.get("mid"):
                return row["node"]
        return None
    return mids.get(mid) if mid else None


def exclusion_pairs(adj: dict, pool: dict) -> set[tuple[str, str]]:
    """Node and ecosystem pairs the matcher can read. Nothing else is stored."""
    pairs: set[tuple[str, str]] = set()
    for eco in ARM_B:
        spec = NODES["ecosystems"][eco]
        names = list(spec["positive_nodes"]) + list(spec["competitor_nodes"]) + controls_for(eco, adj, pool)
        for name in names:
            pairs.add((name, eco))
    return pairs


def build(db_path: Path) -> dict:
    allow_titles, mids, aliases, owned = load_maps()
    pool = json.loads((ROOT / "configs" / "phase1_universe.json").read_text())["control_pool_by_bucket"]
    keep_exclude = exclusion_pairs(build_adj(True, True), pool)
    brands = set(ARM_B)
    if db_path.exists():
        db_path.unlink()
    con = sqlite3.connect(db_path)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    con.execute("CREATE TABLE daily (node TEXT, exclude_brand TEXT, day TEXT, document_count INT, scored_count INT, score_sum REAL, PRIMARY KEY (node, exclude_brand, day))")
    daily: dict[tuple[str, str, str], list] = {}
    precision = defaultdict(lambda: [0, 0, 0])
    mismatch: Counter[tuple[str, str, str]] = Counter()
    docs = 0

    def add(node: str, exclude: str, day: str, score: float | None) -> None:
        rec = daily.get((node, exclude, day))
        if rec is None:
            rec = [0, 0, 0.0]
            daily[(node, exclude, day)] = rec
        rec[0] += 1
        if score is not None:
            rec[1] += 1
            rec[2] += score

    def flush() -> None:
        if not daily:
            return
        con.executemany(
            """
            INSERT INTO daily(node, exclude_brand, day, document_count, scored_count, score_sum)
            VALUES (?,?,?,?,?,?)
            ON CONFLICT(node, exclude_brand, day) DO UPDATE SET
              document_count = document_count + excluded.document_count,
              scored_count = scored_count + excluded.scored_count,
              score_sum = score_sum + excluded.score_sum
            """,
            [(node, exclude, day, rec[0], rec[1], rec[2]) for (node, exclude, day), rec in daily.items()],
        )
        daily.clear()

    for path in sorted(SRC.glob("*.jsonl.gz")):
        with gzip.open(path, "rt") as handle:
            for line in handle:
                row = json.loads(line)
                day = row["day"]
                score = float(row["score"]) if row.get("score") not in (None, "") else None
                matched: dict[str, str] = {}
                for ent in row.get("entities") or []:
                    title = ent.get("wiki") or ""
                    mid = ent.get("mid") or ""
                    for alias in aliases.get(title, []):
                        if mid != (alias.get("mid") or ""):
                            mismatch[(alias["node"], alias["title"], alias.get("mid") or "")] += 1
                    node = resolve_node(title, mid, allow_titles, mids, aliases)
                    if node:
                        matched.setdefault(node, title)
                    owner = mids.get(mid) if mid else None
                    allow_node = allow_titles.get(title) if title else None
                    alias_node = node if title and title not in allow_titles else None
                    if allow_node:
                        precision[allow_node][0] += 1
                    elif alias_node:
                        precision[alias_node][0] += 1
                    elif not title and owner:
                        precision[owner][1] += 1
                    elif title and owner and title not in owned.get(owner, set()):
                        precision[owner][2] += 1
                if not matched:
                    continue
                docs += 1
                brands_here = brands & matched.keys()
                for node in matched:
                    if node in brands:
                        add(node, "", day, score)
                    for eco in ARM_B:
                        if (node, eco) in keep_exclude and eco not in brands_here:
                            add(node, eco, day, score)
        flush()
        say(f"{path.name} docs {docs} cells_flushed")
    flush()
    cells = con.execute("SELECT COUNT(*) FROM daily").fetchone()[0]
    con.commit()
    con.close()
    alias_mid = [
        {"node": node, "title": title, "expected_mid": expected, "different_mid_rows": count}
        for (node, title, expected), count in sorted(mismatch.items())
    ]
    return {
        "docs": docs,
        "cells": cells,
        "precision": {node: {"right_page": v[0], "empty_url_mid": v[1], "wrong_page_via_mid": v[2]} for node, v in precision.items()},
        "alias_title_different_mid": alias_mid,
    }


def series_from_db(db_path: Path) -> dict[tuple[str, str], dict]:
    con = sqlite3.connect(db_path)
    series: dict[tuple[str, str], dict] = {}
    for node, exclude, day, documents, scored, score_sum in con.execute("SELECT node, exclude_brand, day, document_count, scored_count, score_sum FROM daily"):
        series.setdefault((node, exclude), {})[day] = [score_sum, scored, documents]
    con.close()
    return series


def coverage(series: dict) -> dict:
    out = {}
    nodes = sorted({node for node, exclude in series if exclude == ""})
    for node in nodes:
        cells = series.get((node, ""), {})
        scored = sum(1 for cell in cells.values() if cell[1] >= 1)
        dense = sum(1 for cell in cells.values() if cell[1] >= 14)
        out[node] = {"scored_days": scored, "dense_days": dense}
    return out


def passes(treated, other, treated_pop: int, other_pop: int) -> bool:
    got = flag_map(treated, other, treated_pop, other_pop)
    return all(got.values())


def controls_for(eco: str, adj: dict, pool: dict) -> list[str]:
    near = within_hops(adj, exclusion_starts(eco), 2)
    spec = NODES["ecosystems"][eco]
    return [
        ticker
        for ticker in pool_tickers(pool, spec["sector_bucket"])
        if ticker_row(ticker).get("chosen")
        and ticker_row(ticker)["chosen"]["qid"] not in near
        and ticker not in spec["brand_tickers"]
        and ticker not in spec["competitor_nodes"]
        and not ticker_row(ticker).get("ambiguous")
    ]


def pair_count(series: dict, adj: dict, pool: dict, span: tuple[date, date] | None) -> dict:
    popularity = GRAPH["popularity_sitelinks"]
    rows = []
    for eco in ARM_B:
        controls = controls_for(eco, adj, pool)
        events = detect_daily(series.get((eco, ""), {}))
        if span:
            events = [day for day in events if span[0] <= day <= span[1]]
        classes = {"positive": 0, "competitor": 0}
        hit = {"positive": set(), "competitor": set()}
        for t0 in events:
            for edge_class, names in (("positive", NODES["ecosystems"][eco]["positive_nodes"]), ("competitor", NODES["ecosystems"][eco]["competitor_nodes"])):
                for target in names:
                    pop = popularity.get(target)
                    treated_series = series.get((target, eco), {})
                    treated = baseline(treated_series, t0, 28, 14)
                    if pop is None or treated is None or not both_windows(treated_series, t0):
                        continue
                    for ticker in controls:
                        other_series = series.get((ticker, eco), {})
                        other = baseline(other_series, t0, 28, 14)
                        other_pop = (ticker_row(ticker).get("chosen") or {}).get("sitelinks")
                        if other is None or other_pop is None or not both_windows(other_series, t0):
                            continue
                        if passes(treated, other, pop, other_pop):
                            classes[edge_class] += 1
                            hit[edge_class].add(t0)
                            break
        h1_events = len(hit["positive"] | hit["competitor"])
        rows.append({
            "ecosystem": eco,
            "events": len(events),
            "h1_pairs": classes["positive"] + classes["competitor"],
            "h1_events_with_a_pair": h1_events,
            "events_with_a_matched_pair": h1_events,
            "positive_pairs": classes["positive"],
            "positive_events_with_a_pair": len(hit["positive"]),
            "competitor_pairs": classes["competitor"],
            "competitor_events_with_a_pair": len(hit["competitor"]),
            "eligible_controls": len(controls),
        })
    positive = sum(row["positive_pairs"] for row in rows)
    competitor = sum(row["competitor_pairs"] for row in rows)
    return {
        "rows": rows,
        "h1_matched_pairs": positive + competitor,
        "h1_events_with_a_pair": sum(row["h1_events_with_a_pair"] for row in rows),
        "positive_pairs": positive,
        "positive_events_with_a_pair": sum(row["positive_events_with_a_pair"] for row in rows),
        "competitor_pairs": competitor,
        "competitor_events_with_a_pair": sum(row["competitor_events_with_a_pair"] for row in rows),
        "events_with_a_matched_pair": sum(row["events_with_a_matched_pair"] for row in rows),
    }


def proposed_sd(series: dict, adj: dict, pool: dict) -> dict:
    """Placebo SD on neighbor targets, not on the brand series.

    Dates are non-event days of the brand. The treated series is each
    positive or competitor node with the brand excluded. The control is
    the closest baseline among sector names that pass the same calipers
    and the same two-hop path rule as the pair count. Status stays proposed.
    """
    popularity = GRAPH["popularity_sitelinks"]
    rng = random.Random(3)
    diffs = []
    detail = []
    for eco in ARM_B:
        controls = controls_for(eco, adj, pool)
        spec = NODES["ecosystems"][eco]
        brand = series.get((eco, ""), {})
        events = detect_daily(brand)
        eligible = eligible_placebo_days(brand, events)
        chosen = rng.sample(eligible, 20) if len(eligible) > 20 else list(eligible)
        matched = 0
        for t0 in chosen:
            for names in (spec["positive_nodes"], spec["competitor_nodes"]):
                for target in names:
                    pop = popularity.get(target)
                    treated_series = series.get((target, eco), {})
                    treated = baseline(treated_series, t0, 28, 14)
                    shift = abs_shift_daily(treated_series, t0)
                    if pop is None or treated is None or shift is None or not both_windows(treated_series, t0):
                        continue
                    best = None
                    for ticker in controls:
                        other_series = series.get((ticker, eco), {})
                        other = baseline(other_series, t0, 28, 14)
                        other_shift = abs_shift_daily(other_series, t0)
                        other_pop = (ticker_row(ticker).get("chosen") or {}).get("sitelinks")
                        if other is None or other_shift is None or other_pop is None or not both_windows(other_series, t0):
                            continue
                        if not passes(treated, other, pop, other_pop):
                            continue
                        dist = abs(treated[0] - other[0])
                        if best is None or dist < best[0]:
                            best = (dist, other_shift)
                    if best is None:
                        continue
                    diffs.append(shift - best[1])
                    matched += 1
        detail.append({"ecosystem": eco, "eligible_dates": len(eligible), "dates_drawn": len(chosen), "placebo_pairs": matched})
    sd = sample_sd(diffs)
    return {
        "status": "PROPOSED",
        "frozen": False,
        "placebo_pairs": len(diffs),
        "sd": sd,
        "sesoi_0.05_in_sd_units": None if not sd else 0.05 / sd,
        "mean_caliper_0.20_in_sd_units": None if not sd else 0.20 / sd,
        "by_brand": detail,
    }


def gate(name: str, count: int, minimum: int, unit: str) -> dict:
    return {"name": name, "count": count, "minimum": minimum, "unit": unit, "result": "GO" if count >= minimum else "NO-GO"}


def main() -> None:
    global TEST
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true")
    args = parser.parse_args()
    TEST = args.test
    files = sorted(SRC.glob("*.jsonl.gz"))
    db_path = TEST_DB if TEST else DB
    out_path = TEST_OUT if TEST else OUT
    if not TEST and len(files) < 128:
        raise SystemExit(f"refusing the rebuild, {len(files)} slice files are present")
    free = shutil.disk_usage(ROOT).free
    say(f"slices {len(files)} free_bytes {free}")
    if free < 7_000_000_000:
        raise SystemExit(f"refusing the run, {free} bytes free")
    started = time.perf_counter()
    built = build(db_path)
    series = series_from_db(db_path)
    pool = json.loads((ROOT / "configs" / "phase1_universe.json").read_text())["control_pool_by_bucket"]
    adj = build_adj(True, True)
    cov = coverage(series)
    full = pair_count(series, adj, pool, None)
    overlap = pair_count(series, adj, pool, OVERLAP)
    if TEST:
        sd = {"status": "not_computed", "frozen": False, "reason": "The scratch test does not compute a planning SD."}
    else:
        sd = proposed_sd(series, adj, pool)
    results = [
        gate("H1", full["h1_matched_pairs"], 10, "matched pairs, full span"),
        gate("H2_positive", full["positive_pairs"], 10, "positive pairs, full span"),
        gate("H2_competitor", full["competitor_pairs"], 10, "competitor pairs, full span"),
        gate("H4", overlap["events_with_a_matched_pair"], 5, "events with a matched pair, 2017-11-01 through 2020-12-31"),
    ]
    payload = {
        "test": TEST,
        "series_db": str(db_path),
        "pre_rerun_series_left_in_place": True,
        "slices": len(files),
        "documents": built["docs"],
        "precision": built["precision"],
        "alias_title_different_mid": built["alias_title_different_mid"],
        "coverage": cov,
        "pairs_full_span": full,
        "pairs_overlap_2017-11-01_2020-12-31": overlap,
        "planning_sd": sd,
        "results": results,
        "rule": "H1 needs 10 matched pairs in total. H2 positive and H2 competitor each need 10. H4 needs 5 events with a matched pair on 2017-11-01 through 2020-12-31. The planning SD is proposed and is not frozen.",
        "seconds": round(time.perf_counter() - started, 1),
    }
    out_path.write_text(json.dumps(payload))
    for row in results:
        say(f"{row['name']} {row['result']} {row['count']} {row['unit']}")
    for row in full["rows"]:
        say(
            f"{row['ecosystem']} events {row['events']} "
            f"H1 pairs {row['h1_pairs']} events_with_pair {row['h1_events_with_a_pair']} "
            f"H2_positive pairs {row['positive_pairs']} events {row['positive_events_with_a_pair']} "
            f"H2_competitor pairs {row['competitor_pairs']} events {row['competitor_events_with_a_pair']}"
        )
    say(f"documents {built['docs']} cells {built['cells']} alias_mid_rows {sum(row['different_mid_rows'] for row in built['alias_title_different_mid'])} seconds {payload['seconds']}")
    if sd.get("by_brand"):
        for row in sd["by_brand"]:
            say(f"placebo {row['ecosystem']} pairs {row['placebo_pairs']} dates {row['dates_drawn']}")
        say(f"sd {sd['sd']} status {sd['status']} frozen {sd['frozen']} pairs {sd['placebo_pairs']}")
    else:
        say(f"planning_sd {sd['status']}")
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    say(f"max_rss_bytes {rss}")
    if rss > 3_000_000_000:
        raise SystemExit(f"memory {rss} bytes exceeded 3 GB")


if __name__ == "__main__":
    main()

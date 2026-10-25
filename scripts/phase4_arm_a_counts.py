"""Arm A coverage, event counts, matched-pair counts, and a proposed news SD.

Counts only. No event shift is computed or written. The planning SD uses
placebo dates. It is proposed and is not frozen.
"""

from __future__ import annotations

import json
import random
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from phase1_gates import abs_shift_daily, baseline, detect_daily, eligible_placebo_days, sample_sd  # noqa: E402
from phase2_feasibility import GRAPH, NODES, both_windows, pool_tickers  # noqa: E402
from phase2_gdelt_reserve_after import controls_for  # noqa: E402
from phase2_revised_recount import ARM_A, build_adj, passes, targets_for, ticker_row  # noqa: E402

PARTS = ROOT / "data" / "interim" / "phase3" / "fnspid_scores" / "parts"
SERIES = ROOT / "data" / "interim" / "phase2" / "series.sqlite"
OUT = ROOT / "eval" / "results" / "phase4_arm_a_counts.json"
SOURCES = ("news_main", "news_vader", "social")


def add(cell: dict, day: str, signed: float) -> None:
    got = cell.get(day)
    if got is None:
        got = [0.0, 0, 0]
        cell[day] = got
    got[0] += signed
    got[1] += 1
    got[2] += 1


def needed_names(pool: dict) -> set[str]:
    names = set(ARM_A)
    for eco in ARM_A:
        names.update(targets_for(eco)["positive"])
        names.update(targets_for(eco)["competitor"])
        names.update(pool_tickers(pool, NODES["ecosystems"][eco]["sector_bucket"]))
    return names


def load_main(needed: set[str]) -> dict:
    brands = set(ARM_A)
    brand_rows = {name: set() for name in brands}
    for path in sorted(PARTS.glob("*.jsonl")):
        with path.open() as handle:
            for line in handle:
                row = json.loads(line)
                if row["node"] in brands:
                    brand_rows[row["node"]].add(row["row_id"])
    series: dict[tuple[str, str], dict] = defaultdict(dict)
    for path in sorted(PARTS.glob("*.jsonl")):
        with path.open() as handle:
            for line in handle:
                row = json.loads(line)
                node = row["node"]
                if node not in needed:
                    continue
                day = str(row["day"])[:10]
                signed = float(row["signed"])
                add(series[(node, "")], day, signed)
                for eco in ARM_A:
                    if node == eco or row["row_id"] in brand_rows[eco]:
                        continue
                    add(series[(node, eco)], day, signed)
    return series


def load_saved(needed: set[str]) -> dict[str, dict]:
    con = sqlite3.connect(f"file:{SERIES}?mode=ro", uri=True)
    out = {"news_vader": defaultdict(dict), "social": defaultdict(dict)}
    names = {"news": "news_vader", "social": "social"}
    query = "SELECT source, node, exclude_brand, day, score_sum, scored, mentions FROM cell"
    for source, node, exclude, day, score_sum, scored, mentions in con.execute(query):
        if source not in names or node not in needed:
            continue
        out[names[source]][(node, exclude or "")][day] = [score_sum, scored, mentions]
    con.close()
    return out


def coverage(series: dict) -> dict:
    nodes = sorted({node for node, _exclude in series})
    out = {}
    for node in nodes:
        cells = series.get((node, ""), {})
        out[node] = {
            "scored_days": sum(1 for cell in cells.values() if cell[1] >= 1),
            "dense_days": sum(1 for cell in cells.values() if cell[1] >= 14),
        }
    return out


def events_for(series: dict) -> dict:
    out = {}
    for eco in ARM_A:
        found = detect_daily(series.get((eco, ""), {}))
        out[eco] = len(found)
    return out


def pair_counts(series: dict, adj: dict, pool: dict) -> dict:
    popularity = GRAPH["popularity_sitelinks"]
    rows = []
    for eco in ARM_A:
        controls = controls_for(eco, adj, pool)
        classes = {"positive": 0, "competitor": 0}
        events = detect_daily(series.get((eco, ""), {}))
        for t0 in events:
            for edge_class, names in targets_for(eco).items():
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
                            break
        rows.append(
            {
                "ecosystem": eco,
                "positive_pairs": classes["positive"],
                "competitor_pairs": classes["competitor"],
                "eligible_controls": len(controls),
            }
        )
    return {
        "by_ecosystem": rows,
        "positive_pairs": sum(row["positive_pairs"] for row in rows),
        "competitor_pairs": sum(row["competitor_pairs"] for row in rows),
    }


def proposed_news_sd(series: dict, adj: dict, pool: dict) -> dict:
    popularity = GRAPH["popularity_sitelinks"]
    rng = random.Random(3)
    diffs = []
    detail = []
    for eco in ARM_A:
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
        "source": "news_main",
        "placebo_pairs": len(diffs),
        "sd": sd,
        "sesoi_0.05_in_sd_units": None if not sd else 0.05 / sd,
        "mean_caliper_0.20_in_sd_units": None if not sd else 0.20 / sd,
        "by_brand": detail,
        "frozen_arm_a_sd_unchanged": 0.10636804456181562,
    }


def main() -> None:
    pool = json.loads((ROOT / "configs" / "phase1_universe.json").read_text())["control_pool_by_bucket"]
    needed = needed_names(pool)
    print(f"needed {len(needed)}", flush=True)
    main_series = load_main(needed)
    print(f"main cells {len(main_series)}", flush=True)
    saved = load_saved(needed)
    adj = build_adj(True, True)
    bundle = {"news_main": main_series, "news_vader": saved["news_vader"], "social": saved["social"]}
    payload = {
        "counts_only": True,
        "event_shifts_computed": False,
        "sector_match": "information_technology_and_communication_services",
        "coverage": {source: coverage(series) for source, series in bundle.items()},
        "events": {source: events_for(series) for source, series in bundle.items()},
        "matched_pairs": {source: pair_counts(series, adj, pool) for source, series in bundle.items()},
        "planning_sd_news_main": proposed_news_sd(main_series, adj, pool),
    }
    OUT.write_text(json.dumps(payload) + "\n")
    print(f"wrote {OUT}", flush=True)


if __name__ == "__main__":
    main()

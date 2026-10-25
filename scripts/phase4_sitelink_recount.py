"""Recount Apple-Samsung and Nike-Adidas after sitelinks are filled.

Counts only. Does not compute a shift, a placebo pair, or a planning SD.
Calipers are unchanged.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from phase1_gates import baseline, detect_daily  # noqa: E402
from phase2_feasibility import GRAPH, NODES, both_windows  # noqa: E402
from phase2_gdelt_reserve_after import controls_for  # noqa: E402
from phase2_revised_recount import build_adj, passes, ticker_row  # noqa: E402
from phase4_arm_a_headline_counts import (  # noqa: E402
    HEADLINE,
    JOINED,
    OUT as COUNTS,
    load_main,
    load_saved,
)

AFFECTED = (("Apple", "Samsung"), ("Nike", "Adidas"))
OUT = ROOT / "eval" / "results" / "phase4_sitelink_recount.json"


def _matched(series: dict, eco: str, target: str, t0, controls: list[str]) -> bool:
    pop = GRAPH["popularity_sitelinks"].get(target)
    treated_series = series.get((target, eco), {})
    treated = baseline(treated_series, t0, 28, 14)
    if pop is None or treated is None or not both_windows(treated_series, t0):
        return False
    for ticker in controls:
        other_series = series.get((ticker, eco), {})
        other = baseline(other_series, t0, 28, 14)
        other_pop = (ticker_row(ticker).get("chosen") or {}).get("sitelinks")
        if other is None or other_pop is None or not both_windows(other_series, t0):
            continue
        if passes(treated, other, pop, other_pop):
            return True
    return False


def class_counts(series: dict, eco: str, target: str, adj: dict, pool: dict) -> dict:
    controls = controls_for(eco, adj, pool)
    events = detect_daily(series.get((eco, ""), {}))
    target_days = set()
    class_days = set()
    target_pairs = 0
    class_pairs = 0
    for t0 in events:
        if _matched(series, eco, target, t0, controls):
            target_pairs += 1
            target_days.add(t0)
        for name in NODES["ecosystems"][eco]["competitor_nodes"]:
            if _matched(series, eco, name, t0, controls):
                class_pairs += 1
                class_days.add(t0)
    return {
        "events": len(events),
        "target_pairs": target_pairs,
        "target_events_with_a_pair": len(target_days),
        "competitor_pairs": class_pairs,
        "competitor_events_with_a_pair": len(class_days),
        "eligible_controls": len(controls),
        "target_sitelinks": GRAPH["popularity_sitelinks"].get(target),
    }


def needed_for(pool: dict) -> set[str]:
    names = set()
    for eco, target in AFFECTED:
        spec = NODES["ecosystems"][eco]
        names.add(eco)
        names.add(target)
        names.update(spec["competitor_nodes"])
        names.update(controls_for(eco, build_adj(True, True), pool))
    return names


def main() -> None:
    pool = json.loads((ROOT / "configs" / "phase1_universe.json").read_text())["control_pool_by_bucket"]
    adj = build_adj(True, True)
    needed = needed_for(pool)
    saved = load_saved(needed)
    bundle = {
        "news_headline": load_main(HEADLINE, needed),
        "news_joined": load_main(JOINED, needed),
        "news_vader": saved["news_vader"],
        "social": saved["social"],
    }
    rows = []
    for source, series in bundle.items():
        for eco, target in AFFECTED:
            rows.append({"source": source, "ecosystem": eco, "target": target, **class_counts(series, eco, target, adj, pool)})
    payload = {"counts_only": True, "event_shifts_computed": False, "calipers_unchanged": True, "rows": rows}
    OUT.write_text(json.dumps(payload) + "\n")
    counts = json.loads(COUNTS.read_text())
    by_source = {(row["source"], row["ecosystem"], row["target"]): row for row in rows}
    for source, block in counts["matched_pairs"].items():
        for eco_row in block["by_ecosystem"]:
            target = {"Apple": "Samsung", "Nike": "Adidas"}.get(eco_row["ecosystem"])
            if target is None:
                continue
            got = by_source[(source, eco_row["ecosystem"], target)]
            block["competitor_pairs"] += got["competitor_pairs"] - eco_row["competitor_pairs"]
            block["competitor_events_with_a_pair"] += got["competitor_events_with_a_pair"] - eco_row["competitor_events_with_a_pair"]
            eco_row["competitor_pairs"] = got["competitor_pairs"]
            eco_row["competitor_events_with_a_pair"] = got["competitor_events_with_a_pair"]
            eco_row["sitelink_target"] = target
            eco_row["sitelink_target_pairs"] = got["target_pairs"]
            eco_row["sitelink_target_events_with_a_pair"] = got["target_events_with_a_pair"]
    counts["sitelink_recount"] = {
        "date": "2026-10-23",
        "counts_only": True,
        "rows": rows,
    }
    COUNTS.write_text(json.dumps(counts) + "\n")
    for row in rows:
        print(
            f"{row['source']} {row['ecosystem']}-{row['target']} "
            f"events {row['events']} target_pairs {row['target_pairs']} "
            f"target_events {row['target_events_with_a_pair']} "
            f"class_pairs {row['competitor_pairs']} class_events {row['competitor_events_with_a_pair']} "
            f"sitelinks {row['target_sitelinks']}",
            flush=True,
        )


if __name__ == "__main__":
    main()

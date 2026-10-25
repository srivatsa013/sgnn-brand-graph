"""Positive-edge funnel for Apple, Microsoft, and Alphabet.

Counts only. No shift, no widened caliper, no new control. A CEO node is
in this class when it is both a positive node and a CEO edge. Android is
a positive node and has no ownership edge, so it is not in the class.
"""

from __future__ import annotations

import json
import math
import sqlite3
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from phase1_gates import baseline  # noqa: E402
from phase2_feasibility import (  # noqa: E402
    CFG,
    DB,
    EVENTS,
    GRAPH,
    MEAN_CALIPER,
    MENTION_CALIPER,
    NODES,
    PATHS,
    POP_CALIPER,
    SD_CALIPER,
    TICKERS,
    UNI,
    both_windows,
    within_hops,
)

OUT = ROOT / "eval" / "results" / "phase2_positive_funnel.json"
ECOS = ("Apple", "Microsoft", "Alphabet")


def control_ok(ticker: str, eco: str, near: set[str], pool: dict, study: set[str]) -> bool:
    row = TICKERS.get(ticker) or {}
    chosen = row.get("chosen")
    if not chosen or row.get("ambiguous") or row.get("unresolved"):
        return False
    if ticker in study:
        return False
    if chosen.get("sitelinks") is None:
        return False
    if chosen["qid"] in near:
        return False
    return ticker in pool.get(NODES["ecosystems"][eco]["sector_bucket"], [])


def load_series(con: sqlite3.Connection, keys: set[tuple[str, str]]) -> dict:
    series: dict[tuple, dict] = {}
    for source, node in sorted(keys):
        for exclude, day, score_sum, scored, mentions in con.execute(
            "SELECT exclude_brand, day, score_sum, scored, mentions FROM cell WHERE source=? AND node=?",
            (source, node),
        ):
            series.setdefault((source, node, exclude), {})[day] = [score_sum, scored, mentions]
    return series


def main() -> None:
    targets = {}
    for eco in ECOS:
        spec = NODES["ecosystems"][eco]
        positive = []
        for edge in GRAPH["positive_edges"] + GRAPH["ceo_edges"]:
            pair = edge["nodes"]
            if eco not in pair:
                continue
            other = pair[0] if pair[1] == eco else pair[1]
            if other in spec["positive_nodes"] and other not in positive:
                positive.append(other)
        targets[eco] = positive

    node_qids = GRAPH["node_qids"]
    popularity = GRAPH["popularity_sitelinks"]
    adj = defaultdict(set)
    for edge in PATHS["edges"]:
        if edge.get("rank") == "deprecated":
            continue
        adj[edge["source"]].add(edge["target"])
        adj[edge["target"]].add(edge["source"])
    pool = UNI["control_pool_by_bucket"]
    study = set()
    for spec in NODES["ecosystems"].values():
        study.update(spec["brand_tickers"])
        study.update(t for t in spec["competitor_nodes"] if t != "Meta")
    study.update(["FB", "META"])

    blocked = {}
    candidates = {}
    keys = set()
    for eco in ECOS:
        start = []
        for name in [eco] + targets[eco] + NODES["ecosystems"][eco]["competitor_nodes"]:
            start.extend(node_qids.get(name) or [])
        blocked[eco] = within_hops(adj, start, 2)
        candidates[eco] = [t for t in pool.get(NODES["ecosystems"][eco]["sector_bucket"], []) if control_ok(t, eco, blocked[eco], pool, study)]
        for source in ("news", "social"):
            keys.add((source, eco))
            for name in targets[eco]:
                keys.add((source, name))
            for ticker in candidates[eco]:
                keys.add((source, ticker))

    con = sqlite3.connect(DB)
    series = load_series(con, keys)
    con.close()

    def caliper_flags(treated, other, treated_pop: int, other_pop: int) -> dict[str, bool]:
        ratio = treated[1] / other[1] if other[1] else 99
        return {
            "mean": abs(treated[0] - other[0]) <= MEAN_CALIPER,
            "sd": SD_CALIPER[0] <= ratio <= SD_CALIPER[1],
            "mention": abs(treated[2] - other[2]) <= MENTION_CALIPER,
            "popularity": abs(math.log1p(treated_pop) - math.log1p(other_pop)) <= POP_CALIPER,
        }

    rows = []
    alphabet_social = []
    for eco in ECOS:
        for source in ("news", "social"):
            events = EVENTS[eco][source]
            step_events = len(events)
            step_windows = 0
            step_after_exclusion = 0
            step_control = 0
            by_target = {name: {"events": 0, "windows_full": 0, "windows_excluded": 0, "control": 0} for name in targets[eco]}
            lost_at = {"windows_full": 0, "exclusion": 0, "control": 0}
            for t0_text in events:
                t0 = date.fromisoformat(t0_text)
                full = []
                excluded = []
                for name in targets[eco]:
                    by_target[name]["events"] += 1
                    if both_windows(series.get((source, name, ""), {}), t0):
                        full.append(name)
                        by_target[name]["windows_full"] += 1
                    if both_windows(series.get((source, name, eco), {}), t0):
                        excluded.append(name)
                        by_target[name]["windows_excluded"] += 1
                if full:
                    step_windows += 1
                else:
                    lost_at["windows_full"] += 1
                    continue
                if not excluded:
                    lost_at["exclusion"] += 1
                    continue
                step_after_exclusion += 1
                event_control = False
                for name in excluded:
                    pop = popularity.get(name)
                    treated = baseline(series.get((source, name, eco), {}), t0, 28, 14)
                    detail = {
                        "t0": t0_text,
                        "target": name,
                        "controls_with_baseline": 0,
                        "pass": {"mean": 0, "sd": 0, "mention": 0, "popularity": 0},
                        "sole_blocker": defaultdict(int),
                        "passes_mean_and_sd": 0,
                        "matched": False,
                    }
                    if pop is None or treated is None:
                        detail["reason"] = "target_missing_popularity_or_baseline"
                    else:
                        for ticker in candidates[eco]:
                            other_series = series.get((source, ticker, eco), {})
                            other = baseline(other_series, t0, 28, 14)
                            other_pop = (TICKERS[ticker]["chosen"] or {}).get("sitelinks")
                            if other is None or other_pop is None:
                                continue
                            flags = caliper_flags(treated, other, pop, other_pop)
                            detail["controls_with_baseline"] += 1
                            for key, ok in flags.items():
                                if ok:
                                    detail["pass"][key] += 1
                            failed = [key for key, ok in flags.items() if not ok]
                            windows_ok = both_windows(other_series, t0)
                            if windows_ok and flags["mean"] and flags["sd"]:
                                detail["passes_mean_and_sd"] += 1
                            if not failed and windows_ok:
                                detail["matched"] = True
                                event_control = True
                                by_target[name]["control"] += 1
                            elif len(failed) == 1 and windows_ok:
                                detail["sole_blocker"][failed[0]] += 1
                    if eco == "Alphabet" and source == "social":
                        detail["sole_blocker"] = dict(detail["sole_blocker"])
                        alphabet_social.append(detail)
                if event_control:
                    step_control += 1
                else:
                    lost_at["control"] += 1
            drops = {
                "window_requirement": step_events - step_windows,
                "co_mention_exclusion": step_windows - step_after_exclusion,
                "caliper_control": step_after_exclusion - step_control,
            }
            rows.append(
                {
                    "ecosystem": eco,
                    "source": source,
                    "positive_targets": targets[eco],
                    "ceo_edges_are_in_this_class": any(name.endswith("CEO") for name in targets[eco]),
                    "events": step_events,
                    "both_windows_before_exclusion": step_windows,
                    "both_windows_after_exclusion": step_after_exclusion,
                    "control_within_calipers": step_control,
                    "removed": drops,
                    "step_that_removes_the_most": max(drops, key=drops.get),
                    "by_target": by_target,
                    "eligible_controls": candidates[eco],
                }
            )

    def summarise(details: list[dict]) -> dict:
        summary = {
            "events_reaching_calipers": len(details),
            "matched": sum(1 for row in details if row["matched"]),
            "target_missing_popularity_or_baseline": sum(1 for row in details if row.get("reason")),
            "no_control_with_baseline": sum(1 for row in details if not row.get("reason") and row["controls_with_baseline"] == 0),
            "comparisons_passing": {"mean": 0, "sd": 0, "mention": 0, "popularity": 0},
            "comparisons": 0,
            "events_with_a_sole_blocker": {"mean": 0, "sd": 0, "mention": 0, "popularity": 0},
            "events_blocked_only_by_popularity": 0,
            "events_passing_mean_and_sd": 0,
        }
        for row in details:
            if row.get("reason"):
                continue
            summary["comparisons"] += row["controls_with_baseline"]
            for key, n in row["pass"].items():
                summary["comparisons_passing"][key] += n
            for key, n in row["sole_blocker"].items():
                if n:
                    summary["events_with_a_sole_blocker"][key] += 1
            if row["sole_blocker"].get("popularity"):
                summary["events_blocked_only_by_popularity"] += 1
            if row.get("passes_mean_and_sd"):
                summary["events_passing_mean_and_sd"] += 1
        return summary

    summary = summarise(alphabet_social)
    control_popularity = {
        eco: {
            ticker: (TICKERS[ticker]["chosen"] or {}).get("sitelinks")
            for ticker in candidates[eco]
        }
        for eco in ECOS
    }
    payload = {
        "calipers": {
            "baseline_mean_abs": MEAN_CALIPER,
            "baseline_sd_ratio": SD_CALIPER,
            "log_mention_abs": MENTION_CALIPER,
            "log_popularity_abs": POP_CALIPER,
        },
        "class_rule": "Positive edges plus CEO edges whose person node is listed as a positive node. Android has no such edge.",
        "rows": rows,
        "alphabet_social_calipers": summary,
        "target_sitelinks": {name: popularity.get(name) for eco in ECOS for name in targets[eco]},
        "control_sitelinks": control_popularity,
        "h2_minimum_matched_pairs": 10,
        "phase0_min_pairs_field_unchanged": CFG["statistics"]["min_matched_pairs_to_estimate_h1"],
    }
    OUT.write_text(json.dumps(payload, indent=2))
    print(json.dumps({"rows": rows, "alphabet_social_calipers": summary}, indent=2))


if __name__ == "__main__":
    main()

"""Usable-pair counts. No outcome, no shift, no widened caliper.

(a) brand events with at least one structural target that has 3 or more
observed bins in both the pre window and the post window, after documents
that mention the event entity are dropped.
(b) how many of those events also have a control inside the pre-registered
calipers.
A second count requires the control to have both windows as well. That is
the count compared with the minimum of 10 matched pairs. Windows and
calipers are the Phase 0 values.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from phase1_gates import baseline  # noqa: E402

CFG = json.loads((ROOT / "configs" / "phase0.json").read_text())
TAXONOMY = json.loads((ROOT / "configs" / "sector_taxonomy.json").read_text())
NODES = json.loads((ROOT / "configs" / "phase2_nodes.json").read_text())
UNI = json.loads((ROOT / "configs" / "phase1_universe.json").read_text())
GRAPH = json.loads((ROOT / "kg" / "phase2_structural_edges.json").read_text())
TICKERS = json.loads((ROOT / "kg" / "snapshots" / "wikidata_2026-10-12" / "tickers.json").read_text())
PATHS = json.loads((ROOT / "kg" / "snapshots" / "wikidata_2026-10-12" / "path_edges.json").read_text())
EVENTS = json.loads((ROOT / "data" / "interim" / "phase2" / "brand_events.json").read_text())
DB = ROOT / "data" / "interim" / "phase2" / "series.sqlite"
OUT = ROOT / "eval" / "results" / "phase2_feasibility.json"

def pool_tickers(pool: dict, bucket: str) -> list[str]:
    """Control tickers for a match. Merged buckets share one list."""
    keys = [bucket]
    for group in TAXONOMY.get("match_bucket_merge", {}).get("groups", []):
        if bucket in group["members"]:
            keys = list(group["members"])
            break
    out = []
    seen: set[str] = set()
    for key in keys:
        for ticker in pool.get(key, []):
            if ticker not in seen:
                seen.add(ticker)
                out.append(ticker)
    return out


EXPECTED = {
    "Apple": {"news": 14, "social": 171},
    "Microsoft": {"news": 5, "social": 110},
    "Alphabet": {"news": 15, "social": 142},
    "Tesla": {"news": 11, "social": 145},
}
MEAN_CALIPER = CFG["controls"]["caliper_baseline_mean_abs"]
SD_CALIPER = CFG["controls"]["caliper_baseline_sd_ratio"]
MENTION_CALIPER = CFG["controls"]["caliper_log_mention_abs"]
POP_CALIPER = CFG["controls"]["caliper_log_popularity_abs"]
H1_MIN = CFG["statistics"]["min_matched_pairs_to_estimate_h1"]
H4_MIN = CFG["hypotheses"]["H4_magnitude"]["min_events_per_source"]
# Shown to the user. Not written back into phase0.json.
H2_PROPOSED = 10


def observed_bins(series: dict, start: date, end: date) -> int:
    count = 0
    day = start
    while day <= end:
        cell = series.get(day.isoformat())
        if cell and cell[1] >= 1:
            count += 1
        day += timedelta(days=1)
    return count


def both_windows(series: dict, t0: date) -> bool:
    pre = observed_bins(series, t0 - timedelta(days=7), t0 - timedelta(days=1))
    post = observed_bins(series, t0, t0 + timedelta(days=7))
    return pre >= 3 and post >= 3


def log1p(value: int) -> float:
    import math

    return math.log1p(value)


def within_hops(adj: dict[str, set[str]], starts: list[str], limit: int) -> set[str]:
    seen = set()
    layer = [qid for qid in starts if qid]
    for qid in layer:
        seen.add(qid)
    for _ in range(limit):
        nxt = []
        for qid in layer:
            for other in adj.get(qid, ()):
                if other not in seen:
                    seen.add(other)
                    nxt.append(other)
        layer = nxt
    return seen


def main() -> None:
    mismatch = []
    for eco, sources in EXPECTED.items():
        for source, expected in sources.items():
            got = len((EVENTS.get(eco) or {}).get(source) or [])
            if got != expected:
                mismatch.append({"ecosystem": eco, "source": source, "phase2": got, "phase1": expected})
    if mismatch:
        print(json.dumps({"event_count_mismatch": mismatch}, indent=2))
        raise SystemExit("brand event counts do not match Phase 1; feasibility was not written")

    con = sqlite3.connect(DB)
    series: dict[tuple, dict] = {}
    for source, node, exclude, day, score_sum, scored, mentions in con.execute(
        "SELECT source, node, exclude_brand, day, score_sum, scored, mentions FROM cell"
    ):
        series.setdefault((source, node, exclude), {})[day] = [score_sum, scored, mentions]
    con.close()

    targets = {}
    for eco, spec in NODES["ecosystems"].items():
        positive = []
        for edge in GRAPH["positive_edges"] + GRAPH["ceo_edges"]:
            pair = edge["nodes"]
            if eco in pair:
                other = pair[0] if pair[1] == eco else pair[1]
                if other in spec["positive_nodes"] and other not in positive:
                    positive.append(other)
        targets[eco] = {"positive": positive, "competitor": list(spec["competitor_nodes"])}

    node_qids = GRAPH["node_qids"]
    popularity = GRAPH["popularity_sitelinks"]
    adj_all = defaultdict(set)
    adj_active = defaultdict(set)
    for edge in PATHS["edges"]:
        adj_all[edge["source"]].add(edge["target"])
        adj_all[edge["target"]].add(edge["source"])
        if edge.get("rank") != "deprecated":
            adj_active[edge["source"]].add(edge["target"])
            adj_active[edge["target"]].add(edge["source"])

    blocked = {}
    blocked_deprecated_only = {}
    for eco in NODES["ecosystems"]:
        start = []
        for name in [eco] + targets[eco]["positive"] + targets[eco]["competitor"]:
            start.extend(node_qids.get(name) or [])
        near_all = within_hops(adj_all, start, 2)
        near_active = within_hops(adj_active, start, 2)
        blocked[eco] = near_all
        blocked_deprecated_only[eco] = near_all - near_active

    pool = UNI["control_pool_by_bucket"]
    study_tickers = set()
    for spec in NODES["ecosystems"].values():
        study_tickers.update(spec["brand_tickers"])
        study_tickers.update(t for t in spec["competitor_nodes"] if t != "Meta")
    study_tickers.update(["FB", "META"])

    def control_ok(ticker: str, eco: str, near: set[str]) -> tuple[bool, str]:
        row = TICKERS.get(ticker) or {}
        chosen = row.get("chosen")
        if not chosen or row.get("ambiguous") or row.get("unresolved"):
            return False, "ticker_unresolved_or_ambiguous"
        if ticker in study_tickers:
            return False, "study_node"
        qid = chosen["qid"]
        if chosen.get("sitelinks") is None:
            return False, "missing_popularity"
        if qid in near:
            return False, "wikidata_path_leq_2"
        bucket = NODES["ecosystems"][eco]["sector_bucket"]
        if ticker not in pool.get(bucket, []):
            return False, "different_sector"
        return True, "eligible"

    def passes_calipers(treated, other, treated_pop: int, other_pop: int) -> bool:
        if abs(treated[0] - other[0]) > MEAN_CALIPER:
            return False
        ratio = treated[1] / other[1] if other[1] else 99
        if ratio < SD_CALIPER[0] or ratio > SD_CALIPER[1]:
            return False
        if abs(treated[2] - other[2]) > MENTION_CALIPER:
            return False
        if abs(log1p(treated_pop) - log1p(other_pop)) > POP_CALIPER:
            return False
        return True

    rows = []
    pair_rows = []
    for eco, spec in NODES["ecosystems"].items():
        bucket = spec["sector_bucket"]
        candidates = [t for t in pool.get(bucket, []) if control_ok(t, eco, blocked[eco])[0]]
        for source in ("news", "social"):
            for edge_class, names in targets[eco].items():
                events_a = 0
                events_b = 0
                events_b_with_control_windows = 0
                pairs_a = 0
                pairs_b = 0
                pairs_usable = 0
                for t0_text in EVENTS[eco][source]:
                    t0 = date.fromisoformat(t0_text)
                    usable = []
                    for target in names:
                        target_series = series.get((source, target, eco), {})
                        if both_windows(target_series, t0):
                            usable.append(target)
                    if not usable:
                        continue
                    events_a += 1
                    pairs_a += len(usable)
                    event_has_caliper = False
                    event_has_usable = False
                    for target in usable:
                        pop = popularity.get(target)
                        treated = baseline(series.get((source, target, eco), {}), t0, 28, 14)
                        if pop is None or treated is None:
                            pair_rows.append(
                                {
                                    "ecosystem": eco,
                                    "source": source,
                                    "edge_class": edge_class,
                                    "t0": t0_text,
                                    "target": target,
                                    "caliper_control": False,
                                    "reason": "target_missing_popularity_or_baseline",
                                }
                            )
                            continue
                        found = None
                        found_windows = False
                        for ticker in candidates:
                            other_series = series.get((source, ticker, eco), {})
                            other = baseline(other_series, t0, 28, 14)
                            other_pop = (TICKERS[ticker]["chosen"] or {}).get("sitelinks")
                            if other is None or other_pop is None:
                                continue
                            if not passes_calipers(treated, other, pop, other_pop):
                                continue
                            found = ticker
                            if both_windows(other_series, t0):
                                found_windows = True
                                break
                        pair_rows.append(
                            {
                                "ecosystem": eco,
                                "source": source,
                                "edge_class": edge_class,
                                "t0": t0_text,
                                "target": target,
                                "caliper_control": found is not None,
                                "control_also_has_both_windows": found_windows,
                            }
                        )
                        if found is not None:
                            pairs_b += 1
                            event_has_caliper = True
                        if found_windows:
                            pairs_usable += 1
                            event_has_usable = True
                    if event_has_caliper:
                        events_b += 1
                    if event_has_usable:
                        events_b_with_control_windows += 1
                rows.append(
                    {
                        "ecosystem": eco,
                        "source": source,
                        "edge_class": edge_class,
                        "structural_targets": names,
                        "brand_events": len(EVENTS[eco][source]),
                        "events_with_a_target_both_windows": events_a,
                        "events_with_a_caliper_control": events_b,
                        "events_with_a_control_that_also_has_both_windows": events_b_with_control_windows,
                        "pairs_both_windows": pairs_a,
                        "pairs_with_caliper_control": pairs_b,
                        "pairs_with_control_both_windows": pairs_usable,
                        "eligible_controls_in_bucket": len(candidates),
                    }
                )

    def pooled(source: str, edge_class: str | None, key: str) -> int:
        total = 0
        for row in rows:
            if row["source"] != source:
                continue
            if edge_class is not None and row["edge_class"] != edge_class:
                continue
            total += row[key]
        return total

    comparison = []
    for source in ("news", "social"):
        h1_pairs = pooled(source, None, "pairs_with_control_both_windows")
        h1_events = 0
        # An H4 event is a brand event with at least one usable matched pair on either edge class.
        seen_events = set()
        for eco in EVENTS:
            for t0_text in EVENTS[eco][source]:
                if any(
                    row["t0"] == t0_text and row["ecosystem"] == eco and row["source"] == source and row.get("control_also_has_both_windows")
                    for row in pair_rows
                ):
                    seen_events.add((eco, t0_text))
        h1_events = len(seen_events)
        comparison.append(
            {
                "source": source,
                "h1_matched_pairs": h1_pairs,
                "h1_minimum": H1_MIN,
                "h1_meets_minimum": h1_pairs >= H1_MIN,
                "h4_events": h1_events,
                "h4_minimum": H4_MIN,
                "h4_meets_minimum": h1_events >= H4_MIN,
            }
        )
        for edge_class in ("positive", "competitor"):
            got = pooled(source, edge_class, "pairs_with_control_both_windows")
            comparison.append(
                {
                    "source": source,
                    "edge_class": edge_class,
                    "h2_matched_pairs": got,
                    "h2_proposed_minimum": H2_PROPOSED,
                    "h2_proposal_is_preregistered": False,
                    "meets_proposed_minimum": got >= H2_PROPOSED,
                }
            )

    blocked_counts = {}
    for eco, spec in NODES["ecosystems"].items():
        bucket = spec["sector_bucket"]
        reasons = defaultdict(int)
        dep_only = 0
        for ticker in pool.get(bucket, []):
            ok, reason = control_ok(ticker, eco, blocked[eco])
            reasons[reason if not ok else "eligible"] += 1
            chosen = (TICKERS.get(ticker) or {}).get("chosen") or {}
            qid = chosen.get("qid")
            if qid and qid in blocked_deprecated_only[eco] and qid not in blocked[eco] - blocked_deprecated_only[eco]:
                dep_only += 1
        blocked_counts[eco] = {"reasons": dict(reasons), "blocked_only_because_a_deprecated_statement_is_within_two_hops": dep_only}

    payload = {
        "outcomes_computed": False,
        "calipers_widened": False,
        "windows_changed": False,
        "observed_bin": "at least one scored document that day, after dropping documents that mention the event entity",
        "windows": {"pre": [-7, -1], "post": [0, 7], "min_bins_each": 3},
        "h2_proposed_minimum_matched_pairs_per_edge_class_per_source": H2_PROPOSED,
        "h2_proposal_note": "Not pre-registered. Same pair minimum as H1, per edge class, sources separate. Waiting for approval before it is locked.",
        "event_counts_match_phase1": True,
        "structural_targets": targets,
        "by_ecosystem_source_edge_class": rows,
        "comparison": comparison,
        "control_eligibility": blocked_counts,
        "pair_detail_count": len(pair_rows),
    }
    OUT.write_text(json.dumps(payload, indent=2))
    detail = ROOT / "eval" / "results" / "phase2_feasibility_pairs.json"
    detail.write_text(json.dumps(pair_rows))
    print(json.dumps({"comparison": comparison, "rows": rows}, indent=2))


if __name__ == "__main__":
    main()

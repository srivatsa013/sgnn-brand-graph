"""Recount usable pairs under the strict graph and Amendment 8.

Counts only. No shift, no widened caliper. Amendment 8 was logged in
DECISIONS_LOG.md on 2026-10-19 before this script runs. The strict graph
keeps every owner link. Amendment 8 drops an owner link whose owner is
one of the six passive holders logged that day.
"""

from __future__ import annotations

import json
import math
import random
import sqlite3
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from phase1_gates import abs_shift_daily, baseline, detect_daily, eligible_placebo_days  # noqa: E402
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
    log1p,
    within_hops,
)

OUT = ROOT / "eval" / "results" / "phase2_amendment8_recount.json"
ECOS = ("Apple", "Microsoft", "Alphabet")
PASSIVE = {
    "Q539627",
    "Q762479",
    "Q1196231",
    "Q1571175",
    "Q1794766",
    "Q89593177",
}
# wbsearchentities, 2026-10-19. The company hit, not a product or a race.
# Remaining tickers are filled from configs/phase2_leftout_qids.json when present.
LEFT_OUT = {
    "NVDA": "Q182477",
    "TSM": "Q713418",
    "AVGO": "Q790060",
    "QCOM": "Q544847",
    "AMD": "Q128896",
    "MU": "Q1197548",
    "INTC": "Q248",
    "AMAT": "Q621610",
    "ASML": "Q297879",
    "LRCX": "Q1342041",
    "KLAC": "Q624649",
    "NFLX": "Q907311",
    "BBY": "Q533415",
    "GRMN": "Q30338591",
    "ORLY": "Q7071951",
}


def passive_owner_edge(edge: dict) -> bool:
    if edge.get("property_id") == "P127" and edge.get("target") in PASSIVE:
        return True
    if edge.get("property_id") == "P1830" and edge.get("source") in PASSIVE:
        return True
    return False


def build_adj(drop_passive: bool, drop_deprecated: bool) -> dict[str, set[str]]:
    adj: dict[str, set[str]] = defaultdict(set)
    for edge in PATHS["edges"]:
        if drop_deprecated and edge.get("rank") == "deprecated":
            continue
        if drop_passive and passive_owner_edge(edge):
            continue
        adj[edge["source"]].add(edge["target"])
        adj[edge["target"]].add(edge["source"])
    return adj


def study_tickers() -> set[str]:
    names = set()
    for spec in NODES["ecosystems"].values():
        names.update(spec["brand_tickers"])
        names.update(t for t in spec["competitor_nodes"] if t != "Meta")
    names.update(["FB", "META"])
    return names


def direct_competitors() -> set[str]:
    names = set()
    for edge in GRAPH["competitor_edges_confirmed"]:
        names.add(edge["to"])
    names.update(["SSNLF", "SMSN", "SSNGY"])
    return names


def targets_for(eco: str) -> dict[str, list[str]]:
    spec = NODES["ecosystems"][eco]
    positive = []
    for edge in GRAPH["positive_edges"] + GRAPH["ceo_edges"]:
        pair = edge["nodes"]
        if eco in pair:
            other = pair[0] if pair[1] == eco else pair[1]
            if other in spec["positive_nodes"] and other not in positive:
                positive.append(other)
    return {"positive": positive, "competitor": list(spec["competitor_nodes"])}


def starts(eco: str, targets: dict[str, list[str]]) -> list[str]:
    node_qids = GRAPH["node_qids"]
    out = []
    for name in [eco] + targets["positive"] + targets["competitor"]:
        out.extend(node_qids.get(name) or [])
    return out


def control_ok(ticker: str, eco: str, near: set[str], pool: dict, study: set[str]) -> tuple[bool, str]:
    row = TICKERS.get(ticker) or {}
    chosen = row.get("chosen")
    if not chosen or row.get("ambiguous") or row.get("unresolved"):
        return False, "ticker_unresolved_or_ambiguous"
    if ticker in study:
        return False, "study_node"
    if chosen.get("sitelinks") is None:
        return False, "missing_popularity"
    if chosen["qid"] in near:
        return False, "wikidata_path_leq_2"
    if ticker not in pool.get(NODES["ecosystems"][eco]["sector_bucket"], []):
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


def flags(treated, other, treated_pop: int, other_pop: int) -> dict[str, bool]:
    ratio = treated[1] / other[1] if other[1] else 99
    return {
        "mean": abs(treated[0] - other[0]) <= MEAN_CALIPER,
        "sd": SD_CALIPER[0] <= ratio <= SD_CALIPER[1],
        "mention": abs(treated[2] - other[2]) <= MENTION_CALIPER,
        "popularity": abs(math.log1p(treated_pop) - math.log1p(other_pop)) <= POP_CALIPER,
    }


def load_series(needed: set[str]) -> dict:
    con = sqlite3.connect(DB)
    series: dict[tuple, dict] = {}
    for source, name, exclude, day, score_sum, scored, mentions in con.execute(
        "SELECT source, node, exclude_brand, day, score_sum, scored, mentions FROM cell"
    ):
        if name not in needed:
            continue
        series.setdefault((source, name, exclude), {})[day] = [score_sum, scored, mentions]
    con.close()
    return series


def recount(series: dict, graphs: dict[str, dict], pool: dict, study: set[str]) -> dict:
    popularity = GRAPH["popularity_sitelinks"]
    target_map = {eco: targets_for(eco) for eco in NODES["ecosystems"]}
    rows = {}
    for rule, adj in graphs.items():
        blocked = {}
        candidates = {}
        for eco in NODES["ecosystems"]:
            blocked[eco] = within_hops(adj, starts(eco, target_map[eco]), 2)
            bucket = NODES["ecosystems"][eco]["sector_bucket"]
            candidates[eco] = [
                ticker
                for ticker in pool.get(bucket, [])
                if control_ok(ticker, eco, blocked[eco], pool, study)[0]
            ]
        class_rows = []
        h1 = {source: {"pairs": 0, "events": set()} for source in ("news", "social")}
        for eco in NODES["ecosystems"]:
            for source in ("news", "social"):
                for edge_class, names in target_map[eco].items():
                    pairs = 0
                    for t0_text in EVENTS[eco][source]:
                        t0 = date.fromisoformat(t0_text)
                        usable = [
                            target
                            for target in names
                            if both_windows(series.get((source, target, eco), {}), t0)
                        ]
                        event_hit = False
                        for target in usable:
                            pop = popularity.get(target)
                            treated = baseline(series.get((source, target, eco), {}), t0, 28, 14)
                            if pop is None or treated is None:
                                continue
                            for ticker in candidates[eco]:
                                other_series = series.get((source, ticker, eco), {})
                                other = baseline(other_series, t0, 28, 14)
                                other_pop = (TICKERS[ticker]["chosen"] or {}).get("sitelinks")
                                if other is None or other_pop is None:
                                    continue
                                if not passes_calipers(treated, other, pop, other_pop):
                                    continue
                                if both_windows(other_series, t0):
                                    pairs += 1
                                    event_hit = True
                                    break
                        if event_hit:
                            h1[source]["events"].add((eco, t0_text))
                    h1[source]["pairs"] += pairs
                    class_rows.append(
                        {
                            "ecosystem": eco,
                            "source": source,
                            "edge_class": edge_class,
                            "pairs_with_control_both_windows": pairs,
                            "eligible_controls": candidates[eco],
                        }
                    )
        pooled = []
        for source in ("news", "social"):
            pooled.append(
                {
                    "source": source,
                    "h1_matched_pairs": h1[source]["pairs"],
                    "h4_events": len(h1[source]["events"]),
                }
            )
            for edge_class in ("positive", "competitor"):
                got = sum(
                    row["pairs_with_control_both_windows"]
                    for row in class_rows
                    if row["source"] == source and row["edge_class"] == edge_class
                )
                pooled.append({"source": source, "edge_class": edge_class, "h2_matched_pairs": got})
        rows[rule] = {
            "comparison": pooled,
            "by_ecosystem": class_rows,
            "eligible_control_counts": {eco: len(candidates[eco]) for eco in candidates},
        }
    return rows


def funnel(series: dict, graphs: dict[str, dict], pool: dict, study: set[str]) -> dict:
    popularity = GRAPH["popularity_sitelinks"]
    target_map = {eco: targets_for(eco)["positive"] for eco in ECOS}
    out = {}
    for rule, adj in graphs.items():
        candidates = {}
        for eco in ECOS:
            near = within_hops(adj, starts(eco, targets_for(eco)), 2)
            bucket = NODES["ecosystems"][eco]["sector_bucket"]
            candidates[eco] = [
                ticker
                for ticker in pool.get(bucket, [])
                if control_ok(ticker, eco, near, pool, study)[0]
            ]
        eco_rows = []
        alphabet = []
        for eco in ECOS:
            for source in ("news", "social"):
                step_events = len(EVENTS[eco][source])
                step_windows = 0
                step_after = 0
                step_control = 0
                for t0_text in EVENTS[eco][source]:
                    t0 = date.fromisoformat(t0_text)
                    full = [
                        name
                        for name in target_map[eco]
                        if both_windows(series.get((source, name, ""), {}), t0)
                    ]
                    excluded = [
                        name
                        for name in target_map[eco]
                        if both_windows(series.get((source, name, eco), {}), t0)
                    ]
                    if not full:
                        continue
                    step_windows += 1
                    if not excluded:
                        continue
                    step_after += 1
                    event_control = False
                    for name in excluded:
                        pop = popularity.get(name)
                        treated = baseline(series.get((source, name, eco), {}), t0, 28, 14)
                        detail = {
                            "controls_with_baseline": 0,
                            "pass": {"mean": 0, "sd": 0, "mention": 0, "popularity": 0},
                            "matched": False,
                            "passes_mean_and_sd": 0,
                            "sole_popularity": 0,
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
                                got = flags(treated, other, pop, other_pop)
                                detail["controls_with_baseline"] += 1
                                for key, ok in got.items():
                                    if ok:
                                        detail["pass"][key] += 1
                                windows_ok = both_windows(other_series, t0)
                                failed = [key for key, ok in got.items() if not ok]
                                if windows_ok and got["mean"] and got["sd"]:
                                    detail["passes_mean_and_sd"] += 1
                                if windows_ok and not failed:
                                    detail["matched"] = True
                                    event_control = True
                                elif windows_ok and failed == ["popularity"]:
                                    detail["sole_popularity"] += 1
                        if eco == "Alphabet" and source == "social":
                            alphabet.append(detail)
                    if event_control:
                        step_control += 1
                eco_rows.append(
                    {
                        "ecosystem": eco,
                        "source": source,
                        "events": step_events,
                        "both_windows_before_exclusion": step_windows,
                        "both_windows_after_exclusion": step_after,
                        "control_within_calipers": step_control,
                        "eligible_controls": len(candidates[eco]),
                    }
                )
        summary = {
            "events_reaching_calipers": len(alphabet),
            "matched": sum(1 for row in alphabet if row["matched"]),
            "target_missing_popularity_or_baseline": sum(1 for row in alphabet if row.get("reason")),
            "no_control_with_baseline": sum(
                1 for row in alphabet if not row.get("reason") and row["controls_with_baseline"] == 0
            ),
            "comparisons": 0,
            "comparisons_passing": {"mean": 0, "sd": 0, "mention": 0, "popularity": 0},
            "events_passing_mean_and_sd": 0,
            "events_with_a_sole_popularity_blocker": 0,
        }
        for row in alphabet:
            if row.get("reason"):
                continue
            summary["comparisons"] += row["controls_with_baseline"]
            for key, n in row["pass"].items():
                summary["comparisons_passing"][key] += n
            if row["passes_mean_and_sd"]:
                summary["events_passing_mean_and_sd"] += 1
            if row["sole_popularity"]:
                summary["events_with_a_sole_popularity_blocker"] += 1
        out[rule] = {"rows": eco_rows, "alphabet_social": summary, "eligible": {eco: candidates[eco] for eco in ECOS}}
    return out


def day_map(rows: list[dict]) -> dict:
    return {row["day"]: [row["sum"], row["scored"], row["n"]] for row in rows}


def tweetskb(graphs: dict[str, dict], pool: dict, study: set[str]) -> dict:
    brand_file = json.loads((ROOT / "eval" / "results" / "phase1c_tweetskb.json").read_text())
    control_file = json.loads((ROOT / "eval" / "results" / "phase1c_tweetskb_controls_daily.json").read_text())
    brands = {}
    for name in ("Apple", "Microsoft", "Alphabet", "Google"):
        node = brand_file["nodes"][name]
        days = node["days"] if isinstance(node, dict) else node
        brands[name] = day_map(days)
    controls = {ticker: day_map(row["days"]) for ticker, row in control_file.items()}
    eligible_counts = {}
    for name, series in brands.items():
        eligible_counts[name] = len(eligible_placebo_days(series, detect_daily(series)))
    # One Random(3) stream, in the order the log names: Apple, Microsoft, Alphabet.
    rng = random.Random(3)
    focal = {}
    for name in ("Apple", "Microsoft", "Alphabet"):
        events = detect_daily(brands[name])
        eligible = eligible_placebo_days(brands[name], events)
        picked = rng.sample(eligible, 20) if len(eligible) > 20 else list(eligible)
        focal[name] = picked
    target_map = {eco: targets_for(eco) for eco in ECOS}
    out = {"eligible_date_counts": eligible_counts, "rules": {}}
    for rule, adj in graphs.items():
        near = {eco: within_hops(adj, starts(eco, target_map[eco]), 2) for eco in ECOS}
        per_brand = []
        for eco, dates in focal.items():
            bucket = NODES["ecosystems"][eco]["sector_bucket"]
            eligible_controls = []
            absent = []
            for ticker in pool.get(bucket, []):
                ok, reason = control_ok(ticker, eco, near[eco], pool, study)
                if not ok:
                    continue
                if ticker in controls:
                    eligible_controls.append(ticker)
                else:
                    absent.append(ticker)
            tallies = {
                "placebo_dates": len(dates),
                "eligible_controls_in_5pct_file": eligible_controls,
                "eligible_controls_with_no_5pct_series": absent,
                "attempted_comparisons": 0,
                "control_has_14_day_baseline": 0,
                "among_those_pass": {"mean": 0, "sd": 0, "mention": 0, "popularity": 0},
                "matched_all_four_calipers": 0,
            }
            pop = GRAPH["popularity_sitelinks"].get(eco if eco != "Alphabet" else "Google")
            if eco == "Alphabet":
                pop = GRAPH["popularity_sitelinks"].get("Alphabet") or GRAPH["popularity_sitelinks"].get("Google")
            for t0 in dates:
                treated = baseline(brands[eco], t0, 28, 14)
                if treated is None or pop is None:
                    continue
                for ticker in eligible_controls:
                    tallies["attempted_comparisons"] += 1
                    other = baseline(controls[ticker], t0, 28, 14)
                    other_pop = (TICKERS[ticker]["chosen"] or {}).get("sitelinks")
                    if other is None or other_pop is None:
                        continue
                    tallies["control_has_14_day_baseline"] += 1
                    got = flags(treated, other, pop, other_pop)
                    for key, ok in got.items():
                        if ok:
                            tallies["among_those_pass"][key] += 1
                    if all(got.values()):
                        tallies["matched_all_four_calipers"] += 1
            per_brand.append({"ecosystem": eco, **tallies})
        out["rules"][rule] = per_brand
    return out


def left_out(graphs: dict[str, dict]) -> dict:
    extra_path = ROOT / "configs" / "phase2_leftout_qids.json"
    qids = dict(LEFT_OUT)
    if extra_path.exists():
        qids.update(json.loads(extra_path.read_text()))
    entities = json.loads((ROOT / "kg" / "snapshots" / "wikidata_2026-10-12" / "neighbor_entities.json").read_text())
    entities.update(json.loads((ROOT / "kg" / "snapshots" / "wikidata_2026-10-12" / "entities.json").read_text()))
    taxonomy = json.loads((ROOT / "configs" / "sector_taxonomy.json").read_text())["wikidata_industry_label_to_bucket"]
    label_bucket = {}
    for bucket, labels in taxonomy.items():
        for label in labels:
            label_bucket[label] = bucket
    direct = direct_competitors()
    reasons = UNI["excluded_from_control_pool"]
    target_map = {eco: targets_for(eco) for eco in NODES["ecosystems"]}
    neighborhoods = {}
    for rule, adj in graphs.items():
        neighborhoods[rule] = {eco: within_hops(adj, starts(eco, target_map[eco]), 2) for eco in NODES["ecosystems"]}
    rows = []
    for ticker, reason in reasons.items():
        qid = qids.get(ticker)
        entity = entities.get(qid) if qid else None
        industries = []
        if entity:
            for claim in (entity.get("claims") or {}).get("P452") or []:
                target = claim.get("target")
                industries.append(entities.get(target, {}).get("label") or target)
        buckets = sorted({label_bucket[label] for label in industries if label in label_bucket})
        sitelinks = None
        if entity and entity.get("sitelink_count") is not None:
            sitelinks = entity["sitelink_count"]
        path = {}
        for rule, near in neighborhoods.items():
            path[rule] = sorted(eco for eco, ids in near.items() if qid and qid in ids)
        returns = (ticker not in direct) and qid is not None and not path["amendment8_active"]
        rows.append(
            {
                "ticker": ticker,
                "qid": qid,
                "phase1_reason": reason,
                "direct_competitor": ticker in direct,
                "sitelinks_in_snapshot": sitelinks,
                "p452_labels_in_snapshot": industries,
                "mapped_buckets": buckets,
                "within_two_hops": path,
                "returns_under_amendment_8": returns,
                "in_snapshot": entity is not None,
            }
        )
    return {"rows": rows}


def main() -> None:
    dropped = sum(1 for edge in PATHS["edges"] if passive_owner_edge(edge))
    graphs_all = {
        "strict_all_ranks": build_adj(False, False),
        "amendment8_all_ranks": build_adj(True, False),
    }
    graphs_active = {
        "strict_active": build_adj(False, True),
        "amendment8_active": build_adj(True, True),
    }
    pool = UNI["control_pool_by_bucket"]
    study = study_tickers()
    needed = set(study)
    for eco, spec in NODES["ecosystems"].items():
        needed.add(eco)
        needed.update(targets_for(eco)["positive"])
        needed.update(targets_for(eco)["competitor"])
        needed.update(pool.get(spec["sector_bucket"], []))
    print("loading series", len(needed), flush=True)
    series = load_series(needed)
    print("recount", flush=True)
    pairs = recount(series, graphs_all, pool, study)
    print("funnel", flush=True)
    funnels = funnel(series, graphs_active, pool, study)
    print("tweetskb", flush=True)
    social = tweetskb(graphs_active, pool, study)
    print("left out", flush=True)
    review = left_out(graphs_active)
    payload = {
        "outcomes_computed": False,
        "calipers_widened": False,
        "amendment_8_logged_before_this_recount": "2026-10-19",
        "passive_owner_edges_dropped": dropped,
        "usable_pairs_graph": "all statement ranks, matching scripts/phase2_feasibility.py",
        "funnel_and_tweetskb_graph": "non-deprecated statements, matching scripts/phase2_positive_funnel.py and the 2026-10-17 log",
        "usable_pairs": pairs,
        "positive_funnel": funnels,
        "tweetskb_5pct_placebo": social,
        "left_out_review": review,
        "phase0_min_pairs_field_unchanged": CFG["statistics"]["min_matched_pairs_to_estimate_h1"],
    }
    OUT.write_text(json.dumps(payload, indent=2))
    print("wrote", OUT, flush=True)


if __name__ == "__main__":
    main()

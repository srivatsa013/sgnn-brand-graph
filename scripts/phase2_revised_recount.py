"""Recount under the 2026-10-20 universal-owner rule.

The owner list was logged before this script. Counts only. No shift.
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
from phase1_gates import baseline, detect_daily, eligible_placebo_days  # noqa: E402
from phase2_feasibility import (  # noqa: E402
    DB,
    EVENTS,
    GRAPH,
    MEAN_CALIPER,
    MENTION_CALIPER,
    NODES,
    PATHS,
    pool_tickers,
    POP_CALIPER,
    SD_CALIPER,
    TICKERS,
    both_windows,
    log1p,
    within_hops,
)

OUT = ROOT / "eval" / "results" / "phase2_pool_restore_recount.json"
OWNERS = json.loads((ROOT / "configs" / "amendment8_revised_owners.json").read_text())
ARM_A = ("Apple", "Microsoft", "Alphabet", "Tesla")
FUNNEL = ("Apple", "Microsoft", "Alphabet")
RETURNED = {
    "NVDA": ("Q182477", 81),
    "TSM": ("Q713418", 54),
    "AVGO": ("Q790060", 26),
    "QCOM": ("Q544847", 56),
    "AMD": ("Q128896", 78),
    "MU": ("Q1197548", 31),
    "AMAT": ("Q621610", 21),
    "ASML": ("Q297879", 44),
    "LRCX": ("Q1342041", 17),
    "KLAC": ("Q624649", 17),
    "BBY": ("Q533415", 32),
    "ORLY": ("Q7071951", 10),
    "AZO": ("Q4826087", 11),
    "AAP": ("Q4686051", 8),
    "GPC": ("Q5533818", 6),
    "RIVN": ("Q7338847", 25),
    "LCID": ("Q28027517", 23),
    "HMC": ("Q9584", 105),
    "VWAGY": ("Q156578", 69),
    "ALB": ("Q127074", 11),
    "NFLX": ("Q907311", 144),
}
UNIVERSAL = {row["qid"] for row in OWNERS["owners"]}


def is_universal_owner_edge(edge: dict) -> bool:
    if edge.get("property_id") == "P127" and edge.get("target") in UNIVERSAL:
        return True
    if edge.get("property_id") == "P1830" and edge.get("source") in UNIVERSAL:
        return True
    return False


def build_adj(drop_universal: bool, drop_deprecated: bool) -> dict[str, set[str]]:
    adj: dict[str, set[str]] = defaultdict(set)
    for edge in PATHS["edges"]:
        if drop_deprecated and edge.get("rank") == "deprecated":
            continue
        if drop_universal and is_universal_owner_edge(edge):
            continue
        adj[edge["source"]].add(edge["target"])
        adj[edge["target"]].add(edge["source"])
    return adj


def ticker_row(ticker: str) -> dict:
    if ticker in RETURNED:
        qid, links = RETURNED[ticker]
        return {"chosen": {"qid": qid, "sitelinks": links}, "ambiguous": False, "unresolved": False}
    return TICKERS.get(ticker) or {}


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


def starts(eco: str, target_map: dict[str, list[str]]) -> list[str]:
    out = []
    for name in [eco] + target_map["positive"] + target_map["competitor"]:
        out.extend(GRAPH["node_qids"].get(name) or [])
    return out


def exclusion_starts(eco: str) -> list[str]:
    """Path exclusion starts at the event brand and its targets, not at rivals."""
    spec = NODES["ecosystems"][eco]
    out = []
    for name in [eco, *spec["positive_nodes"]]:
        out.extend(GRAPH["node_qids"].get(name) or [])
    return out


def brand_tickers() -> set[str]:
    names = set()
    for spec in NODES["ecosystems"].values():
        names.update(spec["brand_tickers"])
    names.update(["FB", "META"])
    return names


def control_ok(ticker: str, eco: str, near: set[str], pool: dict, brands: set[str] | None = None) -> bool:
    row = ticker_row(ticker)
    chosen = row.get("chosen")
    if not chosen or row.get("ambiguous") or row.get("unresolved"):
        return False
    if ticker in NODES["ecosystems"][eco]["brand_tickers"]:
        return False
    if ticker in NODES["ecosystems"][eco]["competitor_nodes"]:
        return False
    if chosen.get("sitelinks") is None:
        return False
    if chosen["qid"] in near:
        return False
    return ticker in pool_tickers(pool, NODES["ecosystems"][eco]["sector_bucket"])


def passes(treated, other, treated_pop: int, other_pop: int) -> bool:
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


def flag_map(treated, other, treated_pop: int, other_pop: int) -> dict[str, bool]:
    ratio = treated[1] / other[1] if other[1] else 99
    return {
        "mean": abs(treated[0] - other[0]) <= MEAN_CALIPER,
        "sd": SD_CALIPER[0] <= ratio <= SD_CALIPER[1],
        "mention": abs(treated[2] - other[2]) <= MENTION_CALIPER,
        "popularity": abs(math.log1p(treated_pop) - math.log1p(other_pop)) <= POP_CALIPER,
    }


def load_series(needed: set[str]) -> tuple[dict, set[str]]:
    con = sqlite3.connect(DB)
    series: dict[tuple, dict] = {}
    seen: set[str] = set()
    for source, name, exclude, day, score_sum, scored, mentions in con.execute(
        "SELECT source, node, exclude_brand, day, score_sum, scored, mentions FROM cell"
    ):
        seen.add(name)
        if name not in needed:
            continue
        series.setdefault((source, name, exclude), {})[day] = [score_sum, scored, mentions]
    con.close()
    return series, seen


AMBIGUOUS = {"ADP", "BMY", "C", "FOXA", "HAL", "MRK", "NWSA"}


def reason_codes(ticker: str, eco: str, near: set[str], pool: dict, seen: set[str]) -> list[str]:
    bucket = NODES["ecosystems"][eco]["sector_bucket"]
    reasons = []
    if ticker not in pool_tickers(pool, bucket):
        reasons.append("no_bucket")
    if ticker in AMBIGUOUS or (ticker_row(ticker).get("ambiguous")):
        reasons.append("ambiguous_ticker")
    if ticker in NODES["ecosystems"][eco]["competitor_nodes"] or ticker in {"FB", "META"} and eco == "Alphabet":
        reasons.append("direct_competitor")
    row = ticker_row(ticker)
    chosen = row.get("chosen") or {}
    qid = chosen.get("qid")
    if qid and qid in near:
        reasons.append("path_to_event_brand")
    if ticker not in seen:
        reasons.append("no_arm_a_series")
    brand_pop = GRAPH["popularity_sitelinks"].get(eco)
    other_pop = chosen.get("sitelinks")
    if other_pop is None or brand_pop is None:
        reasons.append("popularity_out_of_range")
    elif abs(math.log1p(brand_pop) - math.log1p(other_pop)) > POP_CALIPER:
        reasons.append("popularity_out_of_range")
    return reasons or ["eligible"]


def alphabet_candidates(graphs: dict, pool: dict, seen: set[str]) -> dict:
    eco = "Alphabet"
    bucket = pool_tickers(pool, NODES["ecosystems"][eco]["sector_bucket"])
    extra = ["AMZN", "FB", "META", "PINS", "SNAP"]
    tickers = sorted(set(bucket) | set(extra))
    out = {}
    for rule, adj in graphs.items():
        near = within_hops(adj, exclusion_starts(eco), 2)
        out[rule] = [
            {"ticker": ticker, "reasons": reason_codes(ticker, eco, near, pool, seen)}
            for ticker in tickers
        ]
    return out


def recount(series: dict, graphs: dict, pool: dict, brands: set[str]) -> dict:
    popularity = GRAPH["popularity_sitelinks"]
    target_map = {eco: targets_for(eco) for eco in ARM_A}
    out = {}
    for rule, adj in graphs.items():
        candidates = {}
        for eco in ARM_A:
            near = within_hops(adj, exclusion_starts(eco), 2)
            bucket = NODES["ecosystems"][eco]["sector_bucket"]
            candidates[eco] = [
                ticker for ticker in pool_tickers(pool, bucket) if control_ok(ticker, eco, near, pool, brands)
            ]
        class_rows = []
        h1 = {source: {"pairs": 0, "events": set()} for source in ("news", "social")}
        for eco in ARM_A:
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
                                other_pop = (ticker_row(ticker).get("chosen") or {}).get("sitelinks")
                                if other is None or other_pop is None:
                                    continue
                                if not passes(treated, other, pop, other_pop):
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
                            "eligible_controls": len(candidates[eco]),
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
        out[rule] = {
            "comparison": pooled,
            "by_ecosystem": class_rows,
            "eligible": {eco: candidates[eco] for eco in ARM_A},
        }
    return out


def funnel(series: dict, graphs: dict, pool: dict, brands: set[str]) -> dict:
    popularity = GRAPH["popularity_sitelinks"]
    target_map = {eco: targets_for(eco) for eco in FUNNEL}
    out = {}
    for rule, adj in graphs.items():
        candidates = {}
        for eco in FUNNEL:
            near = within_hops(adj, exclusion_starts(eco), 2)
            candidates[eco] = [
                ticker
                for ticker in pool_tickers(pool, NODES["ecosystems"][eco]["sector_bucket"])
                if control_ok(ticker, eco, near, pool, brands)
            ]
        rows = []
        alphabet = []
        for eco in FUNNEL:
            for source in ("news", "social"):
                step_events = len(EVENTS[eco][source])
                step_windows = 0
                step_after = 0
                step_control = 0
                for t0_text in EVENTS[eco][source]:
                    t0 = date.fromisoformat(t0_text)
                    names = target_map[eco]["positive"]
                    full = [name for name in names if both_windows(series.get((source, name, ""), {}), t0)]
                    excluded = [name for name in names if both_windows(series.get((source, name, eco), {}), t0)]
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
                            detail["reason"] = "target_missing"
                        else:
                            for ticker in candidates[eco]:
                                other_series = series.get((source, ticker, eco), {})
                                other = baseline(other_series, t0, 28, 14)
                                other_pop = (ticker_row(ticker).get("chosen") or {}).get("sitelinks")
                                if other is None or other_pop is None:
                                    continue
                                got = flag_map(treated, other, pop, other_pop)
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
                rows.append(
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
        out[rule] = {"rows": rows, "alphabet_social": summary}
    return out


def day_map(rows: list[dict]) -> dict:
    return {row["day"]: [row["sum"], row["scored"], row["n"]] for row in rows}


def tweetskb(graphs: dict, pool: dict, brands: set[str]) -> dict:
    brand_file = json.loads((ROOT / "eval" / "results" / "phase1c_tweetskb.json").read_text())
    control_file = json.loads((ROOT / "eval" / "results" / "phase1c_tweetskb_controls_daily.json").read_text())
    series = {
        name: day_map(brand_file["nodes"][name]["days"]) for name in ("Apple", "Microsoft", "Google", "Alphabet")
    }
    controls = {ticker: day_map(row["days"]) for ticker, row in control_file.items()}
    eligible_counts = {
        name: len(eligible_placebo_days(series[name], detect_daily(series[name])))
        for name in series
    }
    rng = random.Random(3)
    focal = {}
    for name in ("Apple", "Microsoft", "Google"):
        eligible = eligible_placebo_days(series[name], detect_daily(series[name]))
        focal[name] = rng.sample(eligible, 20) if len(eligible) > 20 else list(eligible)
    target_map = {eco: targets_for(eco) for eco in FUNNEL}
    pops = {
        "Apple": GRAPH["popularity_sitelinks"]["Apple"],
        "Microsoft": GRAPH["popularity_sitelinks"]["Microsoft"],
        "Google": GRAPH["popularity_sitelinks"]["Alphabet"],
    }
    out = {"eligible_date_counts": eligible_counts, "third_series": "Google", "rules": {}}
    for rule, adj in graphs.items():
        per_brand = []
        for name, eco in (("Apple", "Apple"), ("Microsoft", "Microsoft"), ("Google", "Alphabet")):
            near = within_hops(adj, starts(eco, target_map[eco]), 2)
            present = []
            absent = []
            for ticker in pool_tickers(pool, NODES["ecosystems"][eco]["sector_bucket"]):
                if not control_ok(ticker, eco, near, pool, brands):
                    continue
                if ticker in controls:
                    present.append(ticker)
                else:
                    absent.append(ticker)
            tallies = {"mean": 0, "sd": 0, "mention": 0, "popularity": 0}
            attempted = 0
            baseline_ok = 0
            dates_zero = 0
            for t0 in focal[name]:
                treated = baseline(series[name], t0, 28, 14)
                if treated is None:
                    continue
                got_base = 0
                for ticker in present:
                    attempted += 1
                    other = baseline(controls[ticker], t0, 28, 14)
                    other_pop = (ticker_row(ticker).get("chosen") or {}).get("sitelinks")
                    if other is None or other_pop is None:
                        continue
                    got_base += 1
                    baseline_ok += 1
                    got = flag_map(treated, other, pops[name], other_pop)
                    for key, ok in got.items():
                        if ok:
                            tallies[key] += 1
                if got_base == 0:
                    dates_zero += 1
            per_brand.append(
                {
                    "series": name,
                    "placebo_dates": len(focal[name]),
                    "eligible_in_5pct": present,
                    "eligible_absent_from_5pct": absent,
                    "attempted_comparisons": attempted,
                    "control_has_14_day_baseline": baseline_ok,
                    "dates_with_zero_baselines": dates_zero,
                    "among_baseline_pass": tallies,
                }
            )
        out["rules"][rule] = per_brand
    return out


def main() -> None:
    pool = json.loads((ROOT / "configs" / "phase1_universe.json").read_text())["control_pool_by_bucket"]
    brands = brand_tickers()
    graphs_all = {
        "strict_all_ranks": build_adj(False, False),
        "revised_all_ranks": build_adj(True, False),
    }
    graphs_active = {
        "strict_active": build_adj(False, True),
        "revised_active": build_adj(True, True),
    }
    needed = set(brands)
    for eco in ARM_A:
        needed.add(eco)
        needed.update(targets_for(eco)["positive"])
        needed.update(targets_for(eco)["competitor"])
        needed.update(pool_tickers(pool, NODES["ecosystems"][eco]["sector_bucket"]))
    print("loading", len(needed), flush=True)
    series, seen = load_series(needed)
    print("pairs", flush=True)
    pairs = recount(series, graphs_all, pool, brands)
    print("funnel", flush=True)
    funnels = funnel(series, graphs_active, pool, brands)
    print("alphabet candidates", flush=True)
    candidates = alphabet_candidates(graphs_all, pool, seen)
    payload = {
        "outcomes_computed": False,
        "calipers_widened": False,
        "pool_restored_on": "2026-10-21",
        "owner_rule_logged_on": OWNERS["logged_on"],
        "universal_owners": [row["qid"] for row in OWNERS["owners"]],
        "exclusion": "path of length at most 2 from the event brand or its target, or a direct competitor of that event brand",
        "usable_pairs": pairs,
        "positive_funnel": funnels,
        "alphabet_communication_candidates": candidates,
    }
    OUT.write_text(json.dumps(payload, indent=2))
    print("wrote", OUT, flush=True)


if __name__ == "__main__":
    main()

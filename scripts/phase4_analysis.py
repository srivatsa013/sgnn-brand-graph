"""Phase 4 confirmatory analysis on records passed in by the caller.

This module does not read a series, a score file, or an event list from
disk. It does not compute an outcome on the study data. Callers pass
synthetic records in tests, or later pass a finished arm.

The eight-test Holm family, the (b+1)/(B+1) p-value, the rewiring rules,
the clustered bootstrap, the H1 decision table, and the 10-pair rule are
the pre-registered ones.
"""

from __future__ import annotations

import math
import random
from collections import defaultdict
from datetime import date, timedelta

FAMILY = (
    "H1_pair_permutation",
    "H1_rewiring",
    "H2_positive_edges",
    "H2_competitor_edges",
    "H3_signed_vs_unsigned",
    "H3_signed_vs_nograph",
    "H4_magnitude",
    "H4_lag",
)
MIN_PAIRS = 10
MIN_EVENTS_PER_SOURCE = 5
SESOI = 0.05
ALPHA = 0.05


def permutation_p(observed: float, draws: list[float]) -> float:
    """Two-sided permutation p-value. Never exactly zero."""
    if not draws:
        raise ValueError("a permutation p-value needs at least one draw")
    b = sum(1 for value in draws if abs(value) >= abs(observed))
    return (b + 1) / (len(draws) + 1)


def holm(pvalues: dict[str, float | None], alpha: float = ALPHA) -> dict:
    """Holm adjustment over the p-values that exist. Family order is FAMILY."""
    ranked = [(name, pvalues[name]) for name in FAMILY if pvalues.get(name) is not None]
    ranked.sort(key=lambda item: (item[1], item[0]))
    m = len(ranked)
    adjusted: dict[str, float | None] = {}
    running = 0.0
    for index, (name, pvalue) in enumerate(ranked):
        running = max(running, (m - index) * pvalue)
        adjusted[name] = min(1.0, running)
    rejected = {}
    for name in FAMILY:
        if name not in adjusted:
            adjusted[name] = None
            rejected[name] = False
        else:
            rejected[name] = adjusted[name] < alpha
    return {"adjusted": adjusted, "rejected": rejected, "family_size": m}


def ten_pair_rule(n_pairs: int, minimum: int = MIN_PAIRS) -> str:
    if n_pairs < minimum:
        return "not estimable"
    return "estimable"


def h1_decision(
    n_pairs: int,
    distinct_rewirings: int,
    placebo_valid: bool,
    balance_valid: bool,
    pair_rejects: bool,
    rewiring_rejects: bool,
    estimate: float,
    ci_low: float,
    ci_high: float,
    sesoi: float = SESOI,
) -> str:
    """First matching row of the pre-registered H1 table wins."""
    if n_pairs < MIN_PAIRS or distinct_rewirings == 0:
        return "not estimable"
    if not placebo_valid or not balance_valid:
        return "method failed"
    if ci_low >= -sesoi and ci_high <= sesoi:
        return "no meaningful effect"
    excludes_zero = ci_low > 0 or ci_high < 0
    if pair_rejects and rewiring_rejects and estimate > 0 and excludes_zero:
        return "supported"
    if pair_rejects and not rewiring_rejects and estimate > 0 and excludes_zero:
        return "differs from controls but not graph-specific"
    return "inconclusive"


def h2_decision(n_pairs: int, estimate: float, holm_rejects: bool, ci_low: float, ci_high: float) -> str:
    if ten_pair_rule(n_pairs) == "not estimable":
        return "not estimable"
    if estimate > 0 and holm_rejects and ci_low > 0:
        return "supported"
    return "not supported"


def h3_decision(
    estimate: float,
    holm_rejects: bool,
    ci_low: float,
    ci_high: float,
    relative_improvement: float,
) -> str:
    significant = estimate < 0 and holm_rejects and ci_high < 0
    if significant and relative_improvement >= SESOI:
        return "supported"
    if significant and relative_improvement < SESOI:
        return "detectable and below the pre-registered margin"
    return "not supported"


def h4_decision(
    n_news_events: int,
    n_social_events: int,
    estimate: float,
    holm_rejects: bool,
    ci_low: float,
    ci_high: float,
) -> str:
    if n_news_events < MIN_EVENTS_PER_SOURCE or n_social_events < MIN_EVENTS_PER_SOURCE:
        return "not estimable"
    excludes_zero = ci_low > 0 or ci_high < 0
    if estimate != 0 and holm_rejects and excludes_zero:
        return "supported"
    return "not supported"


def mean(values: list[float]) -> float:
    if not values:
        raise ValueError("empty mean")
    return sum(values) / len(values)


def pair_table(rows: list[dict]) -> list[dict]:
    """One row per matched pair. Differences are computed here, not supplied."""
    out = []
    for row in rows:
        h1 = row["treated_abs_shift"] - row["control_abs_shift"]
        edge_sign = 1 if row["edge_class"] == "positive" else -1
        aligned = row["treated_signed_shift"] * row["shock_sign"] * edge_sign
        out.append(
            {
                "event_id": row["event_id"],
                "ecosystem": row["ecosystem"],
                "source": row["source"],
                "t0": row["t0"],
                "iso_week": row["t0"].isocalendar()[:2],
                "target": row["target"],
                "control": row["control"],
                "edge_class": row["edge_class"],
                "h1_diff": h1,
                "aligned_shift": aligned,
                "cluster": (row["ecosystem"], row["t0"].isocalendar()[:2]),
            }
        )
    return out


def pair_permutation(diffs: list[float], draws: int, seed: int) -> list[float]:
    """Swap treated and control inside each pair, independently, with equal probability."""
    rng = random.Random(seed)
    stats = []
    for _ in range(draws):
        total = 0.0
        for diff in diffs:
            total += -diff if rng.random() < 0.5 else diff
        stats.append(total / len(diffs))
    return stats


def clustered_bootstrap(clusters: dict[tuple, list[float]], draws: int, seed: int) -> dict:
    """Percentile interval. A draw takes whole clusters, with replacement."""
    rng = random.Random(seed)
    keys = list(clusters)
    if not keys:
        raise ValueError("bootstrap needs a cluster")
    stats = []
    for _ in range(draws):
        chosen = [keys[rng.randrange(len(keys))] for _ in keys]
        values = [value for key in chosen for value in clusters[key]]
        stats.append(mean(values))
    stats.sort()
    return {
        "draws": stats,
        "low": _percentile(stats, 0.025),
        "high": _percentile(stats, 0.975),
        "estimate": mean([value for values in clusters.values() for value in values]),
    }


def _percentile(sorted_values: list[float], p: float) -> float:
    if len(sorted_values) == 1:
        return sorted_values[0]
    position = p * (len(sorted_values) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    weight = position - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


Edge = tuple[str, str, int]


def _swap_ok(edges: set[Edge], first: Edge, second: Edge) -> Edge | None:
    a, b, s1 = first
    c, d, s2 = second
    left = (a, d, s1)
    right = (c, b, s2)
    if a == d or c == b:
        return None
    if left in edges or right in edges:
        return None
    return (left, right)


def rewire(
    edges: list[Edge],
    target: int = 500,
    seed: int = 2,
    max_attempts: int = 20000,
    consecutive_stop: int = 500,
) -> dict:
    """Degree-preserving double-edge swaps. Only new edge sets are counted."""
    rng = random.Random(seed)
    current = set(edges)
    seen = {frozenset(current)}
    found: list[frozenset[Edge]] = []
    attempts = 0
    stale = 0
    swaps = 20 * max(len(edges), 1)
    while len(found) < target and attempts < max_attempts and stale < consecutive_stop:
        attempts += 1
        proposal = set(current)
        changed = False
        arc_list = list(proposal)
        for _ in range(swaps):
            if len(arc_list) < 2:
                break
            i, j = rng.sample(range(len(arc_list)), 2)
            first, second = arc_list[i], arc_list[j]
            swapped = _swap_ok(proposal, first, second)
            if swapped is None:
                continue
            left, right = swapped
            proposal.remove(first)
            proposal.remove(second)
            proposal.add(left)
            proposal.add(right)
            arc_list = list(proposal)
            changed = True
        key = frozenset(proposal)
        if not changed or key in seen:
            stale += 1
            continue
        seen.add(key)
        found.append(key)
        current = proposal
        stale = 0
    return {"graphs": found, "distinct": len(found), "attempts": attempts}


def rewiring_p(observed: float, graph_stats: list[float]) -> float | None:
    if not graph_stats:
        return None
    return permutation_p(observed, graph_stats)


def placebo_rate(pvalues: list[float], alpha: float = ALPHA) -> dict:
    if not pvalues:
        return {"rate": None, "valid": False, "n": 0}
    rate = sum(1 for value in pvalues if value < alpha) / len(pvalues)
    return {"rate": rate, "valid": rate <= 0.10, "n": len(pvalues)}


def detect_events(series: dict) -> list[dict]:
    """Registered daily rule: |z| >= 2, baseline 28/14, at least 5 mentions, 8-day gap.

    series maps an ISO date to [score_sum, scored_count, mentions].
    """
    days = []
    for text, cell in series.items():
        parsed = date.fromisoformat(text)
        if cell[1] >= 5:
            days.append(parsed)
    days.sort()
    events = []
    last = None
    for t0 in days:
        if last is not None and (t0 - last).days < 8:
            continue
        base = _baseline(series, t0)
        if base is None:
            continue
        mean_value, sd = base
        cell = series[t0.isoformat()]
        level = cell[0] / cell[1]
        z = (level - mean_value) / sd
        if abs(z) >= 2:
            events.append({"t0": t0, "z": z, "shock_sign": 1 if z > 0 else -1})
            last = t0
    return events


def _baseline(series: dict, t0: date) -> tuple[float, float] | None:
    vals = []
    for k in range(1, 29):
        cell = series.get((t0 - timedelta(days=k)).isoformat())
        if cell and cell[1] >= 1:
            vals.append(cell[0] / cell[1])
    if len(vals) < 14:
        return None
    center = sum(vals) / len(vals)
    var = sum((v - center) ** 2 for v in vals) / (len(vals) - 1)
    if var <= 0:
        return None
    return center, math.sqrt(var)


def degrees(edges: set[Edge]) -> dict[str, tuple[int, int]]:
    out: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for src, dst, _sign in edges:
        out[src][0] += 1
        out[dst][1] += 1
    return {node: (counts[0], counts[1]) for node, counts in out.items()}


def main() -> None:
    from phase4_outcome_run import main as run_outcomes

    run_outcomes()


if __name__ == "__main__":
    main()

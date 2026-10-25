"""Wave 2 within-entity (self-controlled) spillover test (amendment B).

Why: in Wave 1 every source failed balance on popularity (SMD 0.25 to 0.95).
Neighbours of the 30 brands are better known than unconnected firms, and a
better-known entity has more mentions, a less noisy daily mean and so a
smaller |shift|. That is the one covariate H1 cannot tolerate.

Design: the control for neighbour j after event (s, t0) is j itself on
placebo days. Popularity is then identical by construction (SMD exactly 0).
The time-varying covariates (baseline mean, baseline SD, log mentions) are
still matched with the Wave 1 calipers and their SMDs are still reported.

Placebo day rules, all fixed before outcomes:
- d is at least 8 days from t0 and at least 8 days from every event day of s
  (so j is not reacting to any s shock on d).
- |d - t0| <= 365 days, so the placebo days come from the same regime.
- j has both windows (>= 3 observed bins each) on d.
- j's baseline on d passes the Wave 1 calipers against j's baseline on t0:
  |mean diff| <= 0.20, SD ratio in [0.5, 2.0], |log mention diff| <= ln 2.
- Up to K = 5 passers, nearest by standardized Euclidean distance on the three
  covariates. Fewer than 1 passer drops the pair. The control outcome is the
  mean over the chosen days.

Estimands (outcome y is the abnormal shift from wave2_labels, or raw shift):
- H1:  |y(j, t0)| - mean_d |y(j, d)|                      > 0 means spillover
- H2:  sign(s) * edge_sign * (y(j, t0) - mean_d y(j, d))   two-sided
       positive edges: > 0 means "moved with the shock" (balance theory)
       competitor edges: > 0 means "moved against" (substitution),
                         < 0 means "moved with" (contagion)

Inference reuses phase4_analysis: clustered bootstrap on ecosystem x ISO week,
pair permutation, Holm. Also here: a regression-adjusted version of the Wave 1
cross-entity H1 (secondary), for comparison with the Wave 1 table.
"""

from __future__ import annotations

import math
from collections import defaultdict
from datetime import date, timedelta
from typing import Callable

import phase4_analysis as A
from wave2_labels import baseline

K_PLACEBO = 5
MIN_GAP_DAYS = 8
MAX_DISTANCE_DAYS = 365
MEAN_CALIPER = 0.20
SD_RATIO = (0.5, 2.0)
MENTION_CALIPER = math.log(2)

Outcome = Callable[[dict, date], "float | None"]


def _passes(t_base: tuple, d_base: tuple) -> bool:
    if abs(t_base[0] - d_base[0]) > MEAN_CALIPER:
        return False
    ratio = t_base[1] / d_base[1] if d_base[1] else 99.0
    if ratio < SD_RATIO[0] or ratio > SD_RATIO[1]:
        return False
    return abs(t_base[2] - d_base[2]) <= MENTION_CALIPER


def placebo_days(block: dict, t0: date, s_event_days: list[date], outcome: Outcome) -> list[tuple[date, tuple, float]]:
    """Chosen placebo days for one treated (j, t0), nearest first."""
    t_base = baseline(block, t0)
    if t_base is None:
        return []
    blocked = list(s_event_days) + [t0]
    options = []
    for text in block:
        d = date.fromisoformat(text)
        if abs((d - t0).days) > MAX_DISTANCE_DAYS:
            continue
        if any(abs((d - e).days) < MIN_GAP_DAYS for e in blocked):
            continue
        d_base = baseline(block, d)
        if d_base is None or not _passes(t_base, d_base):
            continue
        y = outcome(block, d)
        if y is None:
            continue
        options.append((d, d_base, y))
    if not options:
        return []
    scales = []
    for i in range(3):
        vals = [o[1][i] for o in options] + [t_base[i]]
        center = sum(vals) / len(vals)
        sd = math.sqrt(sum((v - center) ** 2 for v in vals) / max(1, len(vals) - 1))
        scales.append(sd or 1.0)
    options.sort(key=lambda o: (sum(((o[1][i] - t_base[i]) / scales[i]) ** 2 for i in range(3)), o[0]))
    return options[:K_PLACEBO]


def build_pairs(treated: list[dict], outcome: Outcome) -> list[dict]:
    """treated rows need: ecosystem, t0, target, edge_class, shock_sign, block, s_event_days."""
    rows = []
    for item in treated:
        block, t0 = item["block"], item["t0"]
        fn = item.get("outcome", outcome)
        y_t = fn(block, t0)
        t_base = baseline(block, t0)
        if y_t is None or t_base is None:
            continue
        chosen = placebo_days(block, t0, item["s_event_days"], fn)
        if not chosen:
            continue
        y_c = [c[2] for c in chosen]
        edge_sign = 0 if item["edge_class"] not in ("positive", "competitor") else (1 if item["edge_class"] == "positive" else -1)
        control_mean = sum(y_c) / len(y_c)
        rows.append({
            "event_id": f"{item['ecosystem']}:{t0.isoformat()}",
            "ecosystem": item["ecosystem"],
            "t0": t0,
            "target": item["target"],
            "edge_class": item["edge_class"],
            "shock_sign": item["shock_sign"],
            "n_placebo": len(chosen),
            "treated_y": y_t,
            "control_y": control_mean,
            "h1_diff": abs(y_t) - sum(abs(v) for v in y_c) / len(y_c),
            "aligned_diff": None if edge_sign == 0 else item["shock_sign"] * edge_sign * (y_t - control_mean),
            "treated_cov": t_base,
            "control_cov": tuple(sum(c[1][i] for c in chosen) / len(chosen) for i in range(3)),
            "cluster": (item["ecosystem"], t0.isocalendar()[:2]),
        })
    return rows


def balance(rows: list[dict]) -> dict:
    """SMD on the three time-varying covariates. Popularity is 0 by construction."""
    names = ("baseline_mean", "baseline_sd", "log_mention")
    smd = {"log_popularity": 0.0}
    for i, name in enumerate(names):
        t = [r["treated_cov"][i] for r in rows]
        c = [r["control_cov"][i] for r in rows]
        if len(t) < 2:
            smd[name] = None
            continue
        pooled = math.sqrt((_var(t) + _var(c)) / 2)
        smd[name] = 0.0 if pooled == 0 else abs(sum(t) / len(t) - sum(c) / len(c)) / pooled
    valid = all(v is not None and v <= 0.20 for v in smd.values())
    return {"valid": valid, "smd": smd}


def _var(values: list[float]) -> float:
    center = sum(values) / len(values)
    return sum((v - center) ** 2 for v in values) / (len(values) - 1)


def test(rows: list[dict], key: str, sesoi: float = A.SESOI) -> dict:
    """Two-sided clustered-bootstrap interval and pair-permutation p for one estimand."""
    usable = [r for r in rows if r[key] is not None]
    n_pairs = len(usable)
    out = {"n_pairs": n_pairs, "n_events": len({r["event_id"] for r in usable})}
    if n_pairs < A.MIN_PAIRS:
        out.update({"tested": False})
        return out
    clusters = defaultdict(list)
    for r in usable:
        clusters[r["cluster"]].append(r[key])
    boot = A.clustered_bootstrap(clusters, 1000, 0)
    draws = A.pair_permutation([r[key] for r in usable], 1000, 1)
    out.update({
        "tested": True,
        "effect": boot["estimate"],
        "low": boot["low"],
        "high": boot["high"],
        "permutation_p": A.permutation_p(boot["estimate"], draws),
        "inside_sesoi": boot["low"] >= -sesoi and boot["high"] <= sesoi,
    })
    return out


def decide_h2(result: dict, edge_class: str, holm_rejects: bool) -> str:
    """Two-sided H2. Direction is reported, not assumed."""
    if not result.get("tested"):
        return "not estimable"
    if not (holm_rejects and (result["low"] > 0 or result["high"] < 0)):
        return "inside SESOI (equivalence)" if result["inside_sesoi"] else "not supported"
    if edge_class == "positive":
        return "same direction (balance theory)" if result["effect"] > 0 else "opposite direction"
    return "substitution (moved against shock)" if result["effect"] > 0 else "contagion (moved with shock)"


def run(treated: list[dict], outcome: Outcome) -> dict:
    rows = build_pairs(treated, outcome)
    report = {"pairs": len(rows), "balance": balance(rows) if rows else {"valid": False, "smd": {}}}
    report["H1"] = test(rows, "h1_diff")
    report["H2_positive"] = test([r for r in rows if r["edge_class"] == "positive"], "aligned_diff")
    report["H2_competitor"] = test([r for r in rows if r["edge_class"] == "competitor"], "aligned_diff")
    return report


# Secondary: regression-adjusted Wave 1 cross-entity H1 ------------------------------------

def _solve(matrix: list[list[float]], vector: list[float]) -> list[float] | None:
    n = len(vector)
    aug = [row[:] + [vector[i]] for i, row in enumerate(matrix)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(aug[r][col]))
        if abs(aug[pivot][col]) < 1e-12:
            return None
        aug[col], aug[pivot] = aug[pivot], aug[col]
        for r in range(n):
            if r != col:
                f = aug[r][col] / aug[col][col]
                aug[r] = [a - f * b for a, b in zip(aug[r], aug[col])]
    return [aug[i][n] / aug[i][i] for i in range(n)]


def adjusted_effect(rows: list[dict]) -> float | None:
    """Intercept of OLS: (treated|shift| - control|shift|) ~ 1 + covariate differences.

    The intercept is the treated-minus-control difference at zero covariate
    gap, which removes the linear part of the popularity imbalance.
    Wave 1 rows from phase4_outcome_run.Bank.match have the needed fields.
    """
    xs, ys = [], []
    for r in rows:
        t, c = r["treated_base"], r["control_base"]
        xs.append([1.0, t[0] - c[0], t[1] - c[1], t[2] - c[2], math.log1p(r["treated_pop"]) - math.log1p(r["control_pop"])])
        ys.append(r["treated_abs_shift"] - r["control_abs_shift"])
    if len(rows) < 10:
        return None
    keep = [0] + [j for j in range(1, len(xs[0])) if len({round(x[j], 12) for x in xs}) > 1]
    xs = [[x[j] for j in keep] for x in xs]
    p = len(xs[0])
    xtx = [[sum(x[i] * x[j] for x in xs) for j in range(p)] for i in range(p)]
    xty = [sum(x[i] * y for x, y in zip(xs, ys)) for i in range(p)]
    beta = _solve(xtx, xty)
    return None if beta is None else beta[0]


def adjusted_test(rows: list[dict], draws: int = 1000, seed: int = 0) -> dict:
    """Cluster bootstrap of the adjusted intercept (ecosystem x ISO week)."""
    import random

    estimate = adjusted_effect(rows)
    if estimate is None:
        return {"tested": False, "n_pairs": len(rows)}
    clusters = defaultdict(list)
    for r in rows:
        clusters[(r["ecosystem"], r["t0"].isocalendar()[:2])].append(r)
    keys = list(clusters)
    rng = random.Random(seed)
    stats = []
    for _ in range(draws):
        sample = [row for k in (keys[rng.randrange(len(keys))] for _ in keys) for row in clusters[k]]
        value = adjusted_effect(sample)
        if value is not None:
            stats.append(value)
    stats.sort()
    low = stats[int(0.025 * (len(stats) - 1))]
    high = stats[int(0.975 * (len(stats) - 1))]
    return {"tested": True, "n_pairs": len(rows), "effect": estimate, "low": low, "high": high,
            "inside_sesoi": low >= -A.SESOI and high <= A.SESOI}

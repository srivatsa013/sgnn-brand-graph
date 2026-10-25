"""One confirmatory Phase 4 run. Does not call BigQuery and does not train.

The statistics are the functions in phase4_analysis.py. Series, windows,
calipers, and seeds are the logged ones. Nothing here is refit after
the numbers are known.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import phase4_analysis as A  # noqa: E402
from phase1_gates import (  # noqa: E402
    abs_shift_daily,
    baseline,
    detect_daily,
    eligible_placebo_days,
    window_mean,
)
from phase2_feasibility import GRAPH, NODES, both_windows, pool_tickers  # noqa: E402
from phase2_gdelt_reserve_after import (  # noqa: E402
    ARM_B,
    DB as GDELT_DB,
    controls_for,
    series_from_db,
)
from phase2_revised_recount import build_adj, passes, targets_for, ticker_row  # noqa: E402
from phase4_arm_a_headline_counts import HEADLINE, JOINED, load_main, load_saved, named_pairs, needed_names  # noqa: E402
from phase2_tweetskb_arm_b_counts import build_series  # noqa: E402

Z975 = 1.959964
Z80 = 0.841621
OUT_JSON = ROOT / "eval" / "results" / "phase4_outcomes.json"
OUT_MD = ROOT / "reports" / "phase4_outcomes.md"
ARM_A = tuple(NODES["ecosystems"])


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(1024 * 1024)
            if not block:
                break
            hasher.update(block)
    return hasher.hexdigest()


def frozen_sds() -> dict:
    cfg = json.loads((ROOT / "configs" / "phase0.json").read_text())
    found = {}
    for row in cfg["amendments"]:
        for key in ("news_joined_restricted", "social", "news_headline_restricted", "arm_b_gdelt", "arm_b_tweetskb"):
            if key in row and isinstance(row[key], dict) and row[key].get("status") == "FROZEN":
                found[key] = row[key]
    found["arm_a_pooled"] = cfg["power_gate"]["planning_sd_paired_abs_shift"]
    return found


def checklist(sds: dict) -> list[dict]:
    cfg = json.loads((ROOT / "configs" / "phase0.json").read_text())
    tax = json.loads((ROOT / "configs" / "sector_taxonomy.json").read_text())
    items = []

    def add(name: str, ok: bool, detail: str) -> None:
        items.append({"item": name, "true": ok, "detail": detail})

    used = ("news_joined_restricted", "news_headline_restricted", "social", "arm_b_gdelt", "arm_b_tweetskb")
    add(
        "every SD used is frozen",
        all(key in sds and sds[key].get("status") == "FROZEN" for key in used)
        and sds["arm_a_pooled"] == 0.10636804456181562,
        "joined, headline, social, GDELT, and TweetsKB are frozen; the pooled Arm A SD stays 0.10636804456181562 and is not used as a source SD",
    )
    event = cfg["event_detection"]
    add(
        "event rule",
        event["k_sd"] == 2.0
        and event["baseline_window_days_inclusive"] == [-28, -1]
        and event["min_baseline_observed_bins"] == 14
        and event["min_mentions_event_bin"] == 5
        and event["refractory_days_after_t0"] == 8
        and event["sd_ddof"] == 1,
        "k=2, baseline [-28,-1] with 14 days, 5 mentions, 8-day gap, divisor n-1",
    )
    windows = cfg["windows_daily"]
    shift = cfg["shift"]
    add(
        "windows and co-mention exclusion",
        windows["pre_inclusive"] == [-7, -1]
        and windows["post_inclusive"] == [0, 7]
        and shift["min_observed_bins_per_window"] == 3
        and shift["exclude_documents_mentioning_event_entity"] is True,
        "pre [-7,-1], post [0,7], at least 3 observed days, event-entity documents excluded",
    )
    controls = cfg["controls"]
    add(
        "matching calipers",
        controls["caliper_baseline_mean_abs"] == 0.20
        and controls["caliper_baseline_sd_ratio"] == [0.5, 2.0]
        and abs(controls["caliper_log_mention_abs"] - math.log(2)) < 1e-6
        and abs(controls["caliper_log_popularity_abs"] - math.log(3)) < 1e-6
        and controls["balance_smd_max_abs"] == 0.20,
        "mean 0.20, SD ratio [0.5, 2], mention ln2, popularity ln3, balance SMD 0.20",
    )
    add(
        "11 coarse sector buckets",
        tax["buckets"] == [
            "information_technology",
            "communication_services",
            "consumer_discretionary",
            "consumer_staples",
            "financials",
            "healthcare",
            "energy",
            "utilities",
            "industrials",
            "materials",
            "real_estate",
        ]
        and tax["match_bucket_merge"]["groups"][0]["name"] == "information_technology_and_communication_services",
        "11 bucket names stay on the map; the logged 2026-10-21 union is the match list for those two",
    )
    add(
        "10-pair rule and SESOI 0.05",
        A.MIN_PAIRS == 10 and A.MIN_EVENTS_PER_SOURCE == 5 and A.SESOI == 0.05 and cfg["hypotheses"]["H1"]["sesoi_abs"] == 0.05,
        "H1 and each H2 class need 10 pairs; H4 needs 5 events on each source; SESOI is 0.05",
    )
    add(
        "Holm family and seeds",
        A.FAMILY == (
            "H1_pair_permutation",
            "H1_rewiring",
            "H2_positive_edges",
            "H2_competitor_edges",
            "H3_signed_vs_unsigned",
            "H3_signed_vs_nograph",
            "H4_magnitude",
            "H4_lag",
        )
        and cfg["gnn"]["seeds"] == [0, 1, 2, 3, 4]
        and cfg["statistics"]["bootstrap_resamples"] == 1000
        and cfg["statistics"]["rewirings"] == 500,
        "eight tests, bootstrap seed 0, pair permutation seed 1, rewiring seed 2, placebo seed 3; GNN seeds 0-4 are not used",
    )
    add("arms are not pooled", True, "Arm A and Arm B are estimated in separate calls and never concatenated")
    add("Tesla is excluded from Arm B", "Tesla" not in ARM_B and len(ARM_B) == 13, "Arm B ecosystems are the 13 non-Tesla names")
    return items


def popularity(name: str) -> int | None:
    if name in GRAPH["popularity_sitelinks"]:
        return int(GRAPH["popularity_sitelinks"][name])
    chosen = (ticker_row(name).get("chosen") or {}).get("sitelinks")
    return None if chosen is None else int(chosen)


def structural_edges(names: set[str]) -> list[tuple[str, str, int]]:
    found = set()
    for edge in GRAPH["positive_edges"] + GRAPH["ceo_edges"]:
        left, right = edge["nodes"]
        if left in names and right in names:
            found.add((left, right, 1))
            found.add((right, left, 1))
    for edge in GRAPH["competitor_edges_confirmed"]:
        if edge["from"] in names and edge["to"] in names:
            found.add((edge["from"], edge["to"], -1))
            if edge.get("reverse_asserted"):
                found.add((edge["to"], edge["from"], -1))
    return sorted(found)


def within_two(edges: list[tuple[str, str, int]], start: str) -> set[str]:
    adj: dict[str, set[str]] = defaultdict(set)
    for left, right, _sign in edges:
        adj[left].add(right)
        adj[right].add(left)
    seen = {start}
    frontier = {start}
    for _ in range(2):
        nxt = set()
        for node in frontier:
            nxt |= adj[node]
        nxt -= seen
        seen |= nxt
        frontier = nxt
    seen.discard(start)
    return seen


def outgoing(edges: list[tuple[str, str, int]]) -> dict[str, list[tuple[str, int]]]:
    out: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for left, right, sign in edges:
        out[left].append((right, sign))
    return out


def neighbor_classes(neigh: list[tuple[str, int]]) -> list[tuple[str, str | None]]:
    signs: dict[str, set[int]] = defaultdict(set)
    for other, sign in neigh:
        signs[other].add(sign)
    rows = []
    for other, got in signs.items():
        if got == {1}:
            rows.append((other, "positive"))
        elif got == {-1}:
            rows.append((other, "competitor"))
        else:
            rows.append((other, None))
    return rows


class Cache:
    def __init__(self, series: dict):
        self.series = series
        self.base: dict[tuple[str, str, str], tuple | None] = {}
        self.signed: dict[tuple[str, str, str], float | None] = {}

    def cell(self, node: str, exclude: str, t0: date):
        key = (node, exclude, t0.isoformat())
        if key not in self.base:
            block = self.series.get((node, exclude), {})
            self.base[key] = baseline(block, t0, 28, 14)
            pre = window_mean(block, t0 - timedelta(days=7), t0 - timedelta(days=1), 3)
            post = window_mean(block, t0, t0 + timedelta(days=7), 3)
            self.signed[key] = None if pre is None or post is None else post - pre
        return self.base[key], self.signed[key]

    def block(self, node: str, exclude: str) -> dict:
        return self.series.get((node, exclude), {})


def invert(matrix: list[list[float]]) -> list[list[float]] | None:
    n = len(matrix)
    work = [row[:] + [1.0 if i == j else 0.0 for j in range(n)] for i, row in enumerate(matrix)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda row: abs(work[row][col]))
        if abs(work[pivot][col]) < 1e-12:
            return None
        work[col], work[pivot] = work[pivot], work[col]
        scale = work[col][col]
        for j in range(2 * n):
            work[col][j] /= scale
        for row in range(n):
            if row == col:
                continue
            factor = work[row][col]
            for j in range(2 * n):
                work[row][j] -= factor * work[col][j]
    return [row[n:] for row in work]


def norm1(matrix: list[list[float]]) -> float:
    size = len(matrix)
    return max(sum(abs(matrix[row][col]) for row in range(size)) for col in range(size))


def _sd(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    center = sum(values) / len(values)
    return math.sqrt(sum((v - center) ** 2 for v in values) / (len(values) - 1))


def shock_sign(cache: Cache, node: str, t0: date) -> int:
    base, _signed = cache.cell(node, "", t0)
    cell = cache.block(node, "")[t0.isoformat()]
    z = (cell[0] / cell[1] - base[0]) / base[1]
    return 1 if z > 0 else -1


def ranked_controls(treated_base: tuple, treated_pop: int, options: list[tuple]) -> list[tuple]:
    """Sort caliper passers by Mahalanobis distance to the treated unit.

    The covariance is the covariance of those passers. A covariate with zero
    dispersion is dropped. A singular matrix, or a condition number above
    1,000,000, uses standardized Euclidean distance on the remaining covariates.
    """
    if len(options) <= 1:
        return list(options)
    points = [[row[1][0], row[1][1], row[1][2], math.log1p(row[4])] for row in options]
    keep = [i for i in range(4) if _sd([point[i] for point in points]) > 0]
    if not keep:
        return list(options)
    cols = [[point[i] for i in keep] for point in points]
    means = [sum(point[i] for point in cols) / len(cols) for i in range(len(keep))]
    inverse = None
    if len(cols) >= len(keep) + 1:
        cov = [[0.0 for _ in keep] for _ in keep]
        for point in cols:
            delta = [point[i] - means[i] for i in range(len(keep))]
            for r in range(len(keep)):
                for c in range(len(keep)):
                    cov[r][c] += delta[r] * delta[c]
        scale = len(cols) - 1
        cov = [[value / scale for value in row] for row in cov]
        inverse = invert(cov)
        if inverse is not None and norm1(cov) * norm1(inverse) > 1_000_000:
            inverse = None
    sds = [_sd([point[i] for point in cols]) or 1.0 for i in range(len(keep))]
    treated_vec = [treated_base[i] for i in (0, 1, 2)] + [math.log1p(treated_pop)]
    treated_kept = [treated_vec[i] for i in keep]
    scored = []
    for row, point in zip(options, cols):
        delta = [point[i] - treated_kept[i] for i in range(len(keep))]
        if inverse is not None:
            dist = 0.0
            for r in range(len(keep)):
                acc = sum(inverse[r][c] * delta[c] for c in range(len(keep)))
                dist += delta[r] * acc
        else:
            dist = sum((delta[i] / sds[i]) ** 2 for i in range(len(keep)))
        scored.append((dist, row[0], row))
    scored.sort()
    return [row for _dist, _name, row in scored]


def registered_targets(eco: str) -> list[tuple[str, str | None]]:
    """One-hop structural neighbors. A neighbor on both edge types stays in H1 and leaves H2."""
    spec = targets_for(eco)
    linked = set()
    for edge in GRAPH["competitor_edges_confirmed"]:
        if edge["from"] == eco:
            linked.add(edge["to"])
        if edge.get("reverse_asserted") and edge["to"] == eco:
            linked.add(edge["from"])
    positive = set(spec["positive"])
    competitor = {name for name in spec["competitor"] if name in linked}
    rows = []
    for name in spec["positive"]:
        rows.append((name, None if name in competitor else "positive"))
    for name in competitor:
        if name not in positive:
            rows.append((name, "competitor"))
    return rows


class Bank:
    """Cached caliper passers. Ranking uses the full passer pool and is reused across graphs."""

    def __init__(self, cache: Cache, ecosystems: list[str], controls: dict[str, list[str]]):
        self.cache = cache
        self.controls = controls
        self.events: list[tuple[str, date]] = []
        self.ready: dict[tuple[str, str, str], tuple | None] = {}
        self.ranked: dict[tuple[str, str, str], list[tuple]] = {}
        for eco in ecosystems:
            brand = cache.block(eco, "")
            if not brand:
                continue
            for t0 in detect_daily(brand):
                self.events.append((eco, t0))

    def prepare(self, eco: str, t0: date, target: str) -> None:
        key = (eco, t0.isoformat(), target)
        if key in self.ready:
            return
        treated_base, treated_signed = self.cache.cell(target, eco, t0)
        treated_pop = popularity(target)
        if treated_base is None or treated_signed is None or treated_pop is None or not both_windows(self.cache.block(target, eco), t0):
            self.ready[key] = None
            self.ranked[key] = []
            return
        options = []
        for ticker in self.controls[eco]:
            if ticker == target:
                continue
            other_base, other_signed = self.cache.cell(ticker, eco, t0)
            other_pop = popularity(ticker)
            if other_base is None or other_signed is None or other_pop is None:
                continue
            if not both_windows(self.cache.block(ticker, eco), t0):
                continue
            if not passes(treated_base, other_base, treated_pop, other_pop):
                continue
            options.append((ticker, other_base, other_signed, abs(other_signed), other_pop))
        self.ready[key] = (treated_base, treated_signed, treated_pop, shock_sign(self.cache, eco, t0))
        self.ranked[key] = ranked_controls(treated_base, treated_pop, options)

    def match(self, eco: str, t0: date, targets: list[tuple[str, str | None]], blocked: set[str], source: str) -> list[dict]:
        used = set()
        rows = []
        brand_base, _signed = self.cache.cell(eco, "", t0)
        if brand_base is None:
            return rows
        for target, edge_class in sorted(targets, key=lambda item: (item[0], item[1] or "")):
            if target == eco:
                continue
            self.prepare(eco, t0, target)
            key = (eco, t0.isoformat(), target)
            treated = self.ready[key]
            if treated is None:
                continue
            treated_base, treated_signed, treated_pop, sign = treated
            pool = self.ranked[key]
            if any(row[0] in blocked for row in pool):
                pool = ranked_controls(treated_base, treated_pop, [row for row in pool if row[0] not in blocked and row[0] not in used])
            picked = None
            for ticker, other_base, other_signed, other_abs, other_pop in pool:
                if ticker in used or ticker in blocked:
                    continue
                picked = (ticker, other_base, other_signed, other_abs, other_pop)
                break
            if picked is None:
                continue
            ticker, other_base, _other_signed, other_abs, other_pop = picked
            used.add(ticker)
            rows.append(
                {
                    "event_id": f"{eco}:{t0.isoformat()}",
                    "ecosystem": eco,
                    "source": source,
                    "t0": t0,
                    "target": target,
                    "control": ticker,
                    "edge_class": edge_class or "both",
                    "shock_sign": sign,
                    "treated_abs_shift": abs(treated_signed),
                    "control_abs_shift": other_abs,
                    "treated_signed_shift": treated_signed,
                    "treated_base": treated_base,
                    "control_base": other_base,
                    "treated_pop": treated_pop,
                    "control_pop": other_pop,
                }
            )
        return rows


def rows_for(bank: Bank, ecosystems: list[str], edges: list[tuple[str, str, int]], source: str, mode: str) -> list[dict]:
    far = outgoing(edges)
    blocked = {eco: within_two(edges, eco) for eco in ecosystems}
    rows = []
    events = bank.events if mode == "confirmatory" else bank.events
    for eco, t0 in events:
        if mode == "confirmatory":
            targets = registered_targets(eco)
        else:
            targets = [(name, edge) for name, edge in neighbor_classes(far.get(eco, [])) if name != eco]
        rows.extend(bank.match(eco, t0, targets, blocked[eco], source))
    return rows


def balance(rows: list[dict]) -> dict:
    if not rows:
        return {"valid": False, "smd": {}}
    names = ("baseline_mean", "baseline_sd", "log_mention", "log_popularity")

    def vec(row: dict, side: str) -> list[float]:
        base = row["treated_base"] if side == "treated" else row["control_base"]
        pop = row["treated_pop"] if side == "treated" else row["control_pop"]
        return [base[0], base[1], base[2], math.log1p(pop)]

    smd = {}
    for index, name in enumerate(names):
        treated = [vec(row, "treated")[index] for row in rows]
        control = [vec(row, "control")[index] for row in rows]
        pooled = math.sqrt((_sd(treated) ** 2 + _sd(control) ** 2) / 2)
        smd[name] = 0.0 if pooled == 0 else abs(sum(treated) / len(treated) - sum(control) / len(control)) / pooled
    return {"valid": all(value <= 0.20 for value in smd.values()), "smd": smd}


def power(sd: float, n_events: int) -> dict:
    if n_events <= 0 or not sd:
        return {"n_events": n_events, "mde": None, "half_width": None}
    return {
        "n_events": n_events,
        "mde": (Z975 + Z80) * sd / math.sqrt(n_events),
        "half_width": Z975 * sd / math.sqrt(n_events),
    }


def clusters_of(rows: list[dict], key: str) -> dict:
    grouped: dict[tuple, list[float]] = defaultdict(list)
    for row in rows:
        grouped[row["cluster"]].append(row[key])
    return grouped


def summarize(rows: list[dict], key: str, sd: float, min_pairs: int = 10) -> dict:
    n_pairs = len(rows)
    n_events = len({row["event_id"] for row in rows})
    base = {"n_pairs": n_pairs, "n_events": n_events, "tested": n_pairs >= min_pairs, **power(sd, n_events)}
    if n_pairs < min_pairs:
        base.update({"effect": None, "low": None, "high": None, "permutation_p": None, "sesoi_interval": None})
        return base
    grouped = clusters_of(rows, key)
    boot = A.clustered_bootstrap(grouped, 1000, 0)
    effect = boot["estimate"]
    values = [row[key] for row in rows]
    draws = A.pair_permutation(values, 1000, 1)
    inside = boot["low"] >= -A.SESOI and boot["high"] <= A.SESOI
    base.update(
        {
            "effect": effect,
            "low": boot["low"],
            "high": boot["high"],
            "permutation_p": A.permutation_p(effect, draws),
            "sesoi_interval": "inside" if inside else "outside",
            "cohen_d": cohen_d(values),
        }
    )
    return base


def cohen_d(values: list[float]) -> float | None:
    if len(values) < 2:
        return None
    center = sum(values) / len(values)
    scale = _sd(values)
    if scale == 0:
        return None
    return center / scale


def placebo(bank: Bank, ecosystems: list[str], edges: list[tuple[str, str, int]], source: str) -> dict:
    rng = random.Random(3)
    pvalues = []
    excluded = []
    blocked = {eco: within_two(edges, eco) for eco in ecosystems}
    for eco in ecosystems:
        brand = bank.cache.block(eco, "")
        events = detect_daily(brand) if brand else []
        eligible = eligible_placebo_days(brand, events) if brand else []
        if len(eligible) < 5:
            excluded.append(eco)
            continue
        chosen = rng.sample(eligible, 20) if len(eligible) > 20 else list(eligible)
        targets = registered_targets(eco)
        for t0 in chosen:
            matched = bank.match(eco, t0, targets, blocked[eco], source)
            if not matched:
                continue
            diffs = [row["h1_diff"] for row in A.pair_table(matched)]
            observed = sum(diffs) / len(diffs)
            draws = A.pair_permutation(diffs, 200, 1)
            pvalues.append({"ecosystem": eco, "p": A.permutation_p(observed, draws)})
    rate = A.placebo_rate([row["p"] for row in pvalues])
    rate["excluded_fewer_than_5_dates"] = excluded
    rate["by_ecosystem"] = pvalues
    return rate


def rewiring_stats(bank: Bank, ecosystems: list[str], edges: list[tuple[str, str, int]], source: str) -> dict:
    graphs = A.rewire(edges, target=500, seed=2)
    print(f"rewiring {source} distinct {graphs['distinct']} attempts {graphs['attempts']}", flush=True)
    all_means = []
    no_tesla = []
    for index, graph in enumerate(graphs["graphs"], start=1):
        rows = rows_for(bank, ecosystems, sorted(graph), source, "rewired")
        if rows:
            table = A.pair_table(rows)
            all_means.append(sum(row["h1_diff"] for row in table) / len(table))
            kept = [row for row in table if row["ecosystem"] != "Tesla"]
            if kept:
                no_tesla.append(sum(row["h1_diff"] for row in kept) / len(kept))
        if index % 50 == 0:
            print(f"rewiring {source} graph {index}", flush=True)
    return {
        "distinct": graphs["distinct"],
        "attempts": graphs["attempts"],
        "means": all_means,
        "means_without_tesla": no_tesla,
        "original_edge_count": len(edges),
    }


def h4_block(news_rows: list[dict], social_rows: list[dict], news_lags: list[tuple], social_lags: list[tuple], news_sd: float) -> dict:
    n_news = len({row["event_id"] for row in news_rows})
    n_social = len({row["event_id"] for row in social_rows})
    out = {
        "n_news_events": n_news,
        "n_social_events": n_social,
        "magnitude": {"tested": False},
        "lag": {"tested": False},
    }
    if n_news < 5 or n_social < 5 or not news_rows or not social_rows:
        out["magnitude"]["reason"] = "not estimable"
        out["lag"]["reason"] = "not estimable"
        return out
    news_c = clusters_of(A.pair_table(news_rows) if "h1_diff" not in news_rows[0] else news_rows, "h1_diff")
    social_c = clusters_of(social_rows, "h1_diff")
    # news_rows may already be pair_table rows
    mag = _diff_boot(news_c, social_c)
    mag["permutation_p"] = _two_sample_p(
        [v for vals in news_c.values() for v in vals],
        [v for vals in social_c.values() for v in vals],
    )
    mag["sesoi_interval"] = "inside" if mag["low"] >= -A.SESOI and mag["high"] <= A.SESOI else "outside"
    mag["tested"] = True
    mag.update(power(news_sd, min(n_news, n_social)))
    out["magnitude"] = mag
    if len(news_lags) < 5 or len(social_lags) < 5:
        out["lag"] = {"tested": False, "reason": "not estimable", "n_news": len(news_lags), "n_social": len(social_lags)}
        return out
    lag = _diff_boot(clusters_of_lags(news_lags), clusters_of_lags(social_lags))
    lag["permutation_p"] = _two_sample_p([row[2] for row in news_lags], [row[2] for row in social_lags])
    lag["sesoi_interval"] = "inside" if lag["low"] >= -A.SESOI and lag["high"] <= A.SESOI else "outside"
    lag["tested"] = True
    lag["n_news"] = len(news_lags)
    lag["n_social"] = len(social_lags)
    lag.update(power(news_sd, min(len(news_lags), len(social_lags))))
    out["lag"] = lag
    return out


def clusters_of_lags(rows: list[tuple]) -> dict:
    grouped: dict[tuple, list[float]] = defaultdict(list)
    for eco, t0, lag in rows:
        iso = t0.isocalendar()
        grouped[(eco, (iso[0], iso[1]))].append(float(lag))
    return grouped


def _diff_boot(left: dict, right: dict) -> dict:
    rng = random.Random(0)
    keys_l = list(left)
    keys_r = list(right)
    stats = []
    for _ in range(1000):
        pick_l = [keys_l[rng.randrange(len(keys_l))] for _ in keys_l]
        pick_r = [keys_r[rng.randrange(len(keys_r))] for _ in keys_r]
        vals_l = [v for key in pick_l for v in left[key]]
        vals_r = [v for key in pick_r for v in right[key]]
        stats.append(sum(vals_l) / len(vals_l) - sum(vals_r) / len(vals_r))
    stats.sort()
    effect = sum(v for vals in left.values() for v in vals) / sum(len(vals) for vals in left.values())
    effect -= sum(v for vals in right.values() for v in vals) / sum(len(vals) for vals in right.values())
    return {"effect": effect, "low": A._percentile(stats, 0.025), "high": A._percentile(stats, 0.975)}


def _two_sample_p(left: list[float], right: list[float]) -> float:
    observed = sum(left) / len(left) - sum(right) / len(right)
    pool = left + right
    n_left = len(left)
    rng = random.Random(1)
    draws = []
    for _ in range(1000):
        rng.shuffle(pool)
        draws.append(sum(pool[:n_left]) / n_left - sum(pool[n_left:]) / len(right))
    return A.permutation_p(observed, draws)


def lags_for(cache: Cache, rows: list[dict]) -> list[tuple]:
    by_event: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_event[row["event_id"]].append(row)
    found = []
    for event_id, group in by_event.items():
        eco = group[0]["ecosystem"]
        t0 = group[0]["t0"]
        day_vals = {offset: [] for offset in range(8)}
        for row in group:
            block = cache.block(row["target"], eco)
            pre = window_mean(block, t0 - timedelta(days=7), t0 - timedelta(days=1), 3)
            if pre is None:
                continue
            for offset in range(8):
                cell = block.get((t0 + timedelta(days=offset)).isoformat())
                if cell and cell[1] >= 1:
                    day_vals[offset].append(cell[0] / cell[1] - pre)
        best = None
        for offset, vals in day_vals.items():
            if not vals:
                continue
            level = sum(vals) / len(vals)
            if best is None or abs(level) > abs(best[1]):
                best = (offset, level)
        if best is not None:
            found.append((eco, t0, best[0]))
    return found


def source_report(raw_rows: list[dict], sd: float, placebo_result: dict, rewire: dict, label: str) -> dict:
    table = A.pair_table(raw_rows)
    for raw, row in zip(raw_rows, table):
        row["treated_base"] = raw["treated_base"]
        row["control_base"] = raw["control_base"]
        row["treated_pop"] = raw["treated_pop"]
        row["control_pop"] = raw["control_pop"]
    bal = balance(raw_rows)
    h1 = summarize(table, "h1_diff", sd)
    h2_pos = summarize([row for row in table if row["edge_class"] == "positive"], "aligned_shift", sd)
    h2_comp = summarize([row for row in table if row["edge_class"] == "competitor"], "aligned_shift", sd)
    rewiring_p = None
    if h1["tested"] and rewire["distinct"] and rewire["means"]:
        rewiring_p = A.rewiring_p(h1["effect"], rewire["means"])
    h1["rewiring_p"] = rewiring_p
    h1["distinct_rewirings"] = rewire["distinct"]
    h1["placebo"] = {k: placebo_result[k] for k in ("rate", "valid", "n")}
    h1["placebo_excluded"] = placebo_result["excluded_fewer_than_5_dates"]
    h1["balance"] = bal
    if h1["tested"] and h1["effect"] is not None and rewiring_p is not None:
        h1["decision"] = A.h1_decision(
            h1["n_pairs"],
            rewire["distinct"],
            bool(placebo_result["valid"]),
            bool(bal["valid"]),
            h1["permutation_p"] < 0.05,
            rewiring_p < 0.05,
            h1["effect"],
            h1["low"],
            h1["high"],
        )
    else:
        h1["decision"] = "not estimable"
    return {"label": label, "H1": h1, "H2_positive": h2_pos, "H2_competitor": h2_comp, "balance": bal}


def family_for(report: dict, h4: dict) -> dict:
    pvalues = {
        "H1_pair_permutation": report["H1"].get("permutation_p"),
        "H1_rewiring": report["H1"].get("rewiring_p"),
        "H2_positive_edges": report["H2_positive"].get("permutation_p"),
        "H2_competitor_edges": report["H2_competitor"].get("permutation_p"),
        "H3_signed_vs_unsigned": None,
        "H3_signed_vs_nograph": None,
        "H4_magnitude": h4["magnitude"].get("permutation_p"),
        "H4_lag": h4["lag"].get("permutation_p"),
    }
    return A.holm(pvalues)


def _drop_ecosystem(result: dict, name: str) -> dict:
    kept = [row for row in result["by_ecosystem"] if row["ecosystem"] != name]
    rate = A.placebo_rate([row["p"] for row in kept])
    rate["excluded_fewer_than_5_dates"] = [eco for eco in result["excluded_fewer_than_5_dates"] if eco != name]
    rate["by_ecosystem"] = kept
    return rate


def _label_family(report: dict, family: dict, h4: dict) -> None:
    for key, fam in (("H2_positive", "H2_positive_edges"), ("H2_competitor", "H2_competitor_edges")):
        row = report[key]
        holm_p = family["adjusted"].get(fam)
        row["holm_p"] = holm_p
        if not row["tested"] or row.get("effect") is None:
            row["decision"] = "not estimable"
        else:
            row["decision"] = A.h2_decision(row["n_pairs"], row["effect"], bool(holm_p is not None and holm_p < A.ALPHA), row["low"], row["high"])
    for key, fam in (("magnitude", "H4_magnitude"), ("lag", "H4_lag")):
        row = h4[key]
        holm_p = family["adjusted"].get(fam)
        row["holm_p"] = holm_p
        if not row.get("tested") or row.get("effect") is None:
            row["decision"] = "not estimable"
            continue
        if key == "magnitude":
            n_news, n_social = h4["n_news_events"], h4["n_social_events"]
        else:
            n_news, n_social = row["n_news"], row["n_social"]
        row["decision"] = A.h4_decision(n_news, n_social, row["effect"], bool(holm_p is not None and holm_p < A.ALPHA), row["low"], row["high"])


def subset_report(raw_rows: list[dict], sd: float, rewire_means: list[float], placebo_result: dict) -> dict:
    kept = [row for row in raw_rows if row["ecosystem"] != "Tesla"]
    report = source_report(kept, sd, placebo_result, {"distinct": len(rewire_means), "means": rewire_means, "attempts": None}, "Tesla excluded")
    return report


def load_arm_a() -> dict[str, dict]:
    pool = json.loads((ROOT / "configs" / "phase1_universe.json").read_text())["control_pool_by_bucket"]
    keep = named_pairs()
    needed = needed_names(pool)
    print("loading restricted news series", flush=True)
    joined = load_main(JOINED, needed, keep)
    headline = load_main(HEADLINE, needed, keep)
    social = load_saved(needed)["social"]
    return {"news_joined": joined, "news_headline": headline, "social": social}


def prepare_controls(ecosystems: list[str]) -> dict[str, list[str]]:
    pool = json.loads((ROOT / "configs" / "phase1_universe.json").read_text())["control_pool_by_bucket"]
    adj = build_adj(True, True)
    return {eco: controls_for(eco, adj, pool) for eco in ecosystems}


def run_arm(name: str, series_map: dict[str, dict], ecosystems: list[str], main_news: str, main_social: str, sds: dict) -> dict:
    controls = prepare_controls(ecosystems)
    names = set(ecosystems)
    for eco in ecosystems:
        spec = NODES["ecosystems"][eco]
        names.update(spec["positive_nodes"])
        names.update(spec["competitor_nodes"])
    edges = structural_edges(names)
    reports = {}
    tables = {}
    placebos = {}
    rewires = {}
    caches = {}
    for source, series in series_map.items():
        print(f"arm {name} source {source}", flush=True)
        cache = Cache(series)
        caches[source] = cache
        bank = Bank(cache, list(ecosystems), controls)
        print(f"arm {name} source {source} events {len(bank.events)}", flush=True)
        raw = rows_for(bank, list(ecosystems), edges, source, "confirmatory")
        print(f"arm {name} source {source} matched pairs {len(raw)}", flush=True)
        tables[source] = raw
        placebos[source] = placebo(bank, list(ecosystems), edges, source)
        rewires[source] = rewiring_stats(bank, list(ecosystems), edges, source)
        sd_key = {
            "news_joined": "news_joined_restricted",
            "news_headline": "news_headline_restricted",
            "social": "social",
            "gdelt": "arm_b_gdelt",
            "tweetskb": "arm_b_tweetskb",
        }[source]
        reports[source] = source_report(raw, sds[sd_key]["sd"], placebos[source], rewires[source], source)
        reports[source]["lags"] = [(eco, t0.isoformat(), lag) for eco, t0, lag in lags_for(cache, raw)]
    news_table = A.pair_table(tables[main_news])
    social_table = A.pair_table(tables[main_social])
    h4 = h4_block(
        news_table,
        social_table,
        lags_for(caches[main_news], tables[main_news]),
        lags_for(caches[main_social], tables[main_social]),
        sds[{"news_joined": "news_joined_restricted", "gdelt": "arm_b_gdelt"}[main_news]]["sd"],
    )
    family = family_for(reports[main_news], h4)
    _label_family(reports[main_news], family, h4)
    sensitivity = None
    if "Tesla" in ecosystems:
        sensitivity = {
            "news": subset_report(tables[main_news], sds["news_joined_restricted"]["sd"], rewires[main_news]["means_without_tesla"], _drop_ecosystem(placebos[main_news], "Tesla")),
            "social": subset_report(tables["social"], sds["social"]["sd"], rewires["social"]["means_without_tesla"], _drop_ecosystem(placebos["social"], "Tesla")),
        }
    return {"sources": reports, "h4": h4, "holm": family, "sensitivity_tesla_excluded": sensitivity}


def plain(value):
    if isinstance(value, dict):
        return {key: plain(item) for key, item in value.items() if key != "by_ecosystem"}
    if isinstance(value, list):
        return [plain(item) for item in value]
    if isinstance(value, date):
        return value.isoformat()
    return value


def markdown(payload: dict) -> str:
    lines = [
        "# Phase 4 outcomes",
        "",
        "Seeds: bootstrap 0, pair permutation 1, rewiring 2, placebo 3. H3 was not estimated. Holm uses the tests that have a p-value. The pooled Arm A SD is not a source SD.",
        "",
        "No git repository. File hashes:",
        "",
    ]
    for path, value in payload["hashes"].items():
        lines.append(f"- `{path}` `{value}`")
    lines.append("")
    for arm, block in payload["arms"].items():
        lines.append(f"## Arm {arm}")
        lines.append("")
        lines.append(
            f"Holm family size {block['holm']['family_size']}. H3 was not run, so this size is the number of tests that have a p-value. The family uses `{block['main_news']}` for H1 and H2. H4 compares that news series with the arm's social series. Headline, social H1 and H2, and the Tesla-excluded rows are not a second family."
        )
        lines.append("")
        lines.append("| Source | Test | Pairs | Events | Effect | 95% interval | Permutation p | Rewiring p | Placebo rate | Holm p | SESOI interval | MDE | Half-width |")
        lines.append("|---|---|---:|---:|---:|---|---:|---:|---:|---:|---|---:|---:|")
        for source, report in block["sources"].items():
            _row(lines, source, "H1", report["H1"], report["H1"].get("permutation_p"), report["H1"].get("rewiring_p"), report["H1"]["placebo"].get("rate"), _holm(block, "H1_pair_permutation", source, block["main_news"]))
            _row(lines, source, "H1 rewiring", report["H1"], None, report["H1"].get("rewiring_p"), report["H1"]["placebo"].get("rate"), _holm(block, "H1_rewiring", source, block["main_news"]))
            _row(lines, source, "H2 positive", report["H2_positive"], report["H2_positive"].get("permutation_p"), None, None, _holm(block, "H2_positive_edges", source, block["main_news"]))
            _row(lines, source, "H2 competitor", report["H2_competitor"], report["H2_competitor"].get("permutation_p"), None, None, _holm(block, "H2_competitor_edges", source, block["main_news"]))
        h4 = block["h4"]
        _h4_row(lines, "H4 magnitude", h4["magnitude"], _holm(block, "H4_magnitude", block["main_news"], block["main_news"]))
        _h4_row(lines, "H4 lag", h4["lag"], _holm(block, "H4_lag", block["main_news"], block["main_news"]))
        lines.append("")
        lines.append(f"H1 decision on `{block['main_news']}`: {block['sources'][block['main_news']]['H1'].get('decision')}.")
        lines.append(f"H2 positive decision: {block['sources'][block['main_news']]['H2_positive'].get('decision')}. H2 competitor decision: {block['sources'][block['main_news']]['H2_competitor'].get('decision')}.")
        lines.append(f"H4 magnitude decision: {h4['magnitude'].get('decision')}. H4 lag decision: {h4['lag'].get('decision')}.")
        for source, report in block["sources"].items():
            smd = report["balance"]["smd"]
            lines.append(
                f"Balance {source}: valid={report['balance']['valid']}, SMD baseline mean {smd.get('baseline_mean')}, SD {smd.get('baseline_sd')}, log mention {smd.get('log_mention')}, log popularity {smd.get('log_popularity')}."
            )
        lines.append("")
        if block.get("sensitivity_tesla_excluded"):
            lines.append("Tesla-excluded sensitivity, not a second Holm family.")
            lines.append("")
            lines.append("| Source | Test | Pairs | Events | Effect | 95% interval | Permutation p | Rewiring p |")
            lines.append("|---|---|---:|---:|---:|---|---:|---:|")
            for source, report in (("news", block["sensitivity_tesla_excluded"]["news"]), ("social", block["sensitivity_tesla_excluded"]["social"])):
                for test, key, pkey in (
                    ("H1", "H1", "permutation_p"),
                    ("H2 positive", "H2_positive", "permutation_p"),
                    ("H2 competitor", "H2_competitor", "permutation_p"),
                ):
                    row = report[key]
                    lines.append(
                        f"| {source} | {test} | {row['n_pairs']} | {row['n_events']} | {_num(row.get('effect'))} | {_interval(row)} | {_num(row.get(pkey))} | {_num(row.get('rewiring_p'))} |"
                    )
            lines.append("")
    return "\n".join(lines) + "\n"


def _holm(block: dict, name: str, source: str, main_news: str):
    if source != main_news and name not in {"H4_magnitude", "H4_lag"}:
        return None
    return block["holm"]["adjusted"].get(name)


def _row(lines, source, test, row, perm, rewire, placebo, holm):
    lines.append(
        f"| {source} | {test} | {row['n_pairs']} | {row['n_events']} | {_num(row.get('effect'))} | {_interval(row)} | {_num(perm)} | {_num(rewire)} | {_num(placebo)} | {_num(holm)} | {row.get('sesoi_interval') or ''} | {_num(row.get('mde'))} | {_num(row.get('half_width'))} |"
    )


def _h4_row(lines, test, row, holm):
    lines.append(
        f"| news minus social | {test} |  | {row.get('n_events') or row.get('n_news_events') or ''} | {_num(row.get('effect'))} | {_interval(row)} | {_num(row.get('permutation_p'))} |  |  | {_num(holm)} | {row.get('sesoi_interval') or ''} | {_num(row.get('mde'))} | {_num(row.get('half_width'))} |"
    )


def _num(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return f"{value:.6g}"


def _interval(row: dict) -> str:
    if row.get("low") is None or row.get("high") is None:
        return ""
    return f"[{row['low']:.6g}, {row['high']:.6g}]"


def main() -> None:
    sds = frozen_sds()
    items = checklist(sds)
    print("CHECKLIST", flush=True)
    for item in items:
        print(f"{'TRUE' if item['true'] else 'FALSE'}\t{item['item']}\t{item['detail']}", flush=True)
    if not all(item["true"] for item in items):
        raise SystemExit(2)
    print("loading series", flush=True)
    arm_a = load_arm_a()
    arm_b = {"gdelt": series_from_db(GDELT_DB), "tweetskb": build_series()}
    print("estimating", flush=True)
    arms = {
        "A": run_arm("A", arm_a, list(ARM_A), "news_joined", "social", sds),
        "B": run_arm("B", arm_b, list(ARM_B), "gdelt", "tweetskb", sds),
    }
    arms["A"]["main_news"] = "news_joined"
    arms["B"]["main_news"] = "gdelt"
    hashes = {}
    for relative in (
        "configs/phase0.json",
        "configs/phase4_series.json",
        "configs/frozen_sha256.json",
        "scripts/phase4_analysis.py",
        "scripts/phase4_outcome_run.py",
        "data/interim/phase3/final_scorer/model.pt",
    ):
        hashes[relative] = digest(ROOT / relative)
    payload = {
        "git": None,
        "seeds": {"bootstrap": 0, "pair_permutation": 1, "rewiring": 2, "placebo_dates": 3, "placebo_inner_permutations": 1, "gnn_not_used": [0, 1, 2, 3, 4]},
        "hashes": hashes,
        "checklist": items,
        "frozen_sds": plain(sds),
        "h3": "not estimated; Phase 5 training was not started",
        "choices": {
            "pair_permutation": "phase4_analysis.pair_permutation, each pair independently, seed 1, 1000 draws",
            "h2_permutation": "the same sign flip applied to aligned shifts",
            "h4_permutation": "two-sample reassignment of the pair differences or lag values, seed 1, 1000 draws",
            "h1_decision_rejects": "unadjusted pair and rewiring p-values below 0.05",
            "h2_h4_decision_rejects": "Holm-adjusted p-values below 0.05",
            "mde_n": "events with a matched pair",
            "rewired_targets": "one-hop neighbors on the rewired graph",
            "confirmatory_targets": "registered one-hop positive and competitor targets",
            "distance": "Mahalanobis on the four covariates among caliper passers; singular or ill-conditioned covariance uses standardized Euclidean",
        },
        "arms": plain(arms),
    }
    OUT_JSON.write_text(json.dumps(payload) + "\n")
    OUT_MD.write_text(markdown(payload))
    print(f"wrote {OUT_JSON}", flush=True)


if __name__ == "__main__":
    main()

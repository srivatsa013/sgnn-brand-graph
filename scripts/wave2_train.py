"""Wave 2 driver (amendment B). New outputs only; no Wave 1 file is rewritten.

Steps per source:
1. Build events exactly as phase5_train.build_all does (same features, graph,
   co-mention edges, CEO windows), but keep the label as a pending
   (neighbour, t0) instead of the raw shift.
2. Cut day-boundary 60/20/20 folds (phase5_train.day_folds).
3. Fit own reversion (wave2_labels.fit_reversion) on entity-days whose post
   window ends before the first validation day.
4. Label = abnormal shift = raw - expected own - sector factor (pool = the
   Wave 1 eligible control list of that ecosystem).
5. Train own_only, shock_broadcast, relational, relational_tied on the
   hidden {32, 64} x dropout {0.0, 0.2} grid, depth 1, seeds 0-4, select on
   mean validation MAE. Relational is also refit on sign-shuffled and
   degree-matched graphs (phase5_train helpers). Persistence predicts 0.
6. Self-controlled H1 / H2 (wave2_self_controlled) on the same abnormal
   outcome, plus the raw-outcome version and the regression-adjusted Wave 1
   cross-entity H1 as secondary rows.
7. Write eval/results/wave2_outcomes.json and reports/wave2_outcomes.md.

Run
    python3 scripts/wave2_train.py --self-check
    python3 scripts/wave2_train.py --sources gdelt news_joined
    python3 scripts/wave2_train.py --sources gdelt --exploratory-wave1

--exploratory-wave1 labels every number EXPLORATORY in the output, because
Wave 1 outcomes have already been seen. Confirmatory numbers come only from
Wave 2 events, after amendment B is frozen in configs/frozen_sha256.json.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import phase4_analysis as A  # noqa: E402
import wave2_labels as L  # noqa: E402
import wave2_model as W  # noqa: E402
import wave2_self_controlled as S  # noqa: E402
from phase5_model import Edge, Event  # noqa: E402

GRID = tuple((h, 1, p) for h in (32, 64) for p in (0.0, 0.2))
SEEDS = (0, 1, 2, 3, 4)
LEARNED = W.VARIANTS
OUT_JSON = ROOT / "eval" / "results" / "wave2_outcomes.json"
OUT_MD = ROOT / "reports" / "wave2_outcomes.md"
FAMILY = (
    "H1_self_controlled",
    "H2_positive_two_sided",
    "H2_competitor_two_sided",
    "H3_graph_relational_vs_broadcast",
    "H3_sign_relational_vs_tied",
    "H3_persistence_relational_vs_zero",
)


# 1. events with pending labels ---------------------------------------------------------

def build_events(source: str, arm: str, co_source: str | None, series: dict, ecosystems: list[str]) -> tuple[list[dict], dict]:
    """Mirror of phase5_train.build_all for one source. Labels are filled later."""
    import phase4_outcome_run as R
    import phase5_train as P
    from phase1_gates import baseline, detect_daily

    windows, properties, comention = P.ceo_windows(), P.property_map(), P.load_comention()
    cache = R.Cache(series)
    controls = R.prepare_controls(ecosystems)
    rows = []
    for eco in ecosystems:
        spec = R.NODES["ecosystems"][eco]
        members = sorted(set([eco, *spec["positive_nodes"], *spec["competitor_nodes"]]))
        names = set(members)
        arcs = [e for e in R.structural_edges(names) if e[0] in names and e[1] in names]
        targets = R.registered_targets(eco)
        brand = cache.block(eco, "")
        s_days = detect_daily(brand)
        for t0 in s_days:
            features = torch.zeros(len(members), P.IN_DIM)
            for i, name in enumerate(members):
                P.fill_features(cache.block(name, "" if name == eco else eco), t0, features[i])
                features[i, 24 + P.TYPE_AT[P.node_kind(name, eco, spec, properties.get(eco, {}), t0, windows)]] = 1.0
            cell = brand[t0.isoformat()]
            stats = baseline(brand, t0, 28, 14)
            b = members.index(eco)
            features[b, 30] = cell[0] / cell[1]
            features[b, P.SHOCK_Z] = (cell[0] / cell[1] - stats[0]) / stats[1]
            features[b, 32] = 1.0
            lookup = {n: i for i, n in enumerate(members)}
            struct = [Edge(lookup[l], lookup[r], "struct", float(sg), 1.0) for l, r, sg in arcs]
            co_edges, co_days = P.comention_edges(comention, co_source, members, t0)
            event = Event(
                event_id=f"{source}:{eco}:{t0.isoformat()}", t0=t0.toordinal(), features=features,
                edges=struct + co_edges, labels={}, comention_times=co_days,
                history_times=[(t0 - timedelta(days=k)).toordinal() for k in range(1, 29)],
                feature_doc_ids={f"feature:{source}:{eco}:{t0.isoformat()}"},
                label_doc_ids={f"label:{source}:{eco}:{t0.isoformat()}"},
            )
            pending = [(lookup[n], n, ec) for n, ec in targets if n in lookup]
            rows.append({"event": event, "ecosystem": eco, "t0": t0, "names": members, "pending": pending,
                         "shock_sign": R.shock_sign(cache, eco, t0), "s_days": s_days})
    blocks = {"cache": cache, "controls": controls}
    return rows, blocks


# 2-4. abnormal labels -------------------------------------------------------------------

def fill_labels(rows: list[dict], blocks: dict, cutoff: date) -> dict:
    cache, controls = blocks["cache"], blocks["controls"]
    entity_blocks = {}
    for row in rows:
        eco = row["ecosystem"]
        for _i, name, _ec in row["pending"]:
            entity_blocks[(name, eco)] = cache.block(name, eco)
        for ticker in controls[eco]:
            entity_blocks[(ticker, eco)] = cache.block(ticker, eco)
    rev = L.fit_reversion(L.reversion_samples(entity_blocks, cutoff))
    raw, own, factor, abnormal, thin_factor = [], [], [], [], 0
    for row in rows:
        eco, t0 = row["ecosystem"], row["t0"]
        pool = [cache.block(t, eco) for t in controls[eco]]
        row["pool"] = pool
        labels = {}
        for index, name, _ec in row["pending"]:
            got = L.abnormal_shift(cache.block(name, eco), t0, rev, pool)
            if got is None:
                continue
            labels[index] = got["abnormal"]
            raw.append(got["raw_shift"])
            own.append(got["expected_own"])
            factor.append(got["sector_factor"])
            abnormal.append(got["abnormal"])
            thin_factor += got["sector_entities"] < L.MIN_SECTOR_ENTITIES
        row["event"].labels = labels
    return {"reversion": {"a": rev.a, "b": rev.b, "n": rev.n}, "decomposition": decomposition(raw, own, factor, abnormal),
            "labels": len(abnormal), "labels_with_thin_sector_factor": thin_factor, "rev": rev}


def decomposition(raw, own, factor, abnormal) -> dict:
    """Share of raw-shift variance removed by each component (reported in the paper)."""
    def var(v):
        if len(v) < 2:
            return None
        c = sum(v) / len(v)
        return sum((x - c) ** 2 for x in v) / (len(v) - 1)
    vr = var(raw)
    if not vr:
        return {}
    after_own = [r - o for r, o in zip(raw, own)]
    return {
        "raw_variance": vr,
        "variance_after_own_reversion": var(after_own),
        "abnormal_variance": var(abnormal),
        "share_removed_by_own_reversion": 1 - var(after_own) / vr,
        "share_removed_in_total": 1 - var(abnormal) / vr,
        "n": len(raw),
    }


# 5. models -------------------------------------------------------------------------------

def fit(train, val, variant, hidden, dropout, seed):
    model = W.Wave2Net(train[0].features.shape[1], hidden, 1, dropout, variant)
    info = W.train_loop(model, train, val, seed=seed)
    return model, info


def train_models(rows: list[dict]) -> dict:
    import phase5_train as P

    events = [r["event"] for r in rows]
    train, val, test, split = P.day_folds(events)
    if not (train and val and test):
        return {"split": split, "skipped": "empty fold"}
    meta = {r["event"].event_id: (r["ecosystem"], date.fromordinal(r["event"].t0).isocalendar()[:2]) for r in rows}
    val_table = {v: defaultdict(dict) for v in LEARNED}
    fitted = {}
    for seed in SEEDS:
        for variant in LEARNED:
            for hidden, _depth, dropout in GRID:
                model, info = fit(train, val, variant, hidden, dropout, seed)
                val_table[variant][(hidden, 1, dropout)][seed] = info["best_validation_mae"]
                fitted[(variant, hidden, dropout, seed)] = (model, info)
    chosen, maps, betas = {}, {}, defaultdict(list)
    for variant in LEARNED:
        config, score = choose(val_table[variant])
        chosen[variant] = {"hidden": config[0], "depth": 1, "dropout": config[2], "mean_validation_mae": score}
        per_seed = []
        for seed in SEEDS:
            model, info = fitted[(variant, config[0], config[2], seed)]
            per_seed.append(W.event_maes(model, test, info["mean"], info["std"]))
            for k, v in model.betas().items():
                betas[f"{variant}.{k}"].append(v)
        maps[variant] = P.mean_map(per_seed)
    maps["persistence"] = W.event_maes(None, test, None, None)
    rel = chosen["relational"]
    for name, editor in (("relational_sign_shuffled", P.sign_shuffled), ("relational_degree_matched", P.degree_matched)):
        per_seed = []
        for seed in SEEDS:
            edited = editor([{"event": r["event"], "ecosystem": r["ecosystem"], "names": r["names"]} for r in rows], seed)
            tr, va, te, _ = P.day_folds(edited)
            model, info = fit(tr, va, "relational", rel["hidden"], rel["dropout"], seed)
            per_seed.append(W.event_maes(model, te, info["mean"], info["std"]))
        maps[name] = P.mean_map(per_seed)
    table = {name: sum(m.values()) / len(m) for name, m in maps.items() if m}
    comparisons = {
        "H3_graph_relational_vs_broadcast": P.compare(maps["relational"], maps["shock_broadcast"], meta),
        "H3_sign_relational_vs_tied": P.compare(maps["relational"], maps["relational_tied"], meta),
        "H3_persistence_relational_vs_zero": P.compare(maps["relational"], maps["persistence"], meta),
        "secondary_relational_vs_own_only": P.compare(maps["relational"], maps["own_only"], meta),
        "secondary_relational_vs_sign_shuffled": P.compare(maps["relational"], maps["relational_sign_shuffled"], meta),
        "secondary_relational_vs_degree_matched": P.compare(maps["relational"], maps["relational_degree_matched"], meta),
    }
    beta_summary = {k: {"mean": sum(v) / len(v), "sd": _sd(v), "seeds": v} for k, v in betas.items()}
    return {"split": split, "chosen": chosen, "test_mae": table, "comparisons": comparisons, "betas": beta_summary}


def choose(table: dict) -> tuple:
    """Lowest mean validation MAE over all seeds; ties take smaller hidden, then dropout."""
    best = None
    for config, by_seed in table.items():
        values = [by_seed.get(seed) for seed in SEEDS]
        if any(v is None for v in values):
            continue
        key = (sum(values) / len(values), config[0], config[2])
        if best is None or key < best[0]:
            best = (key, config)
    if best is None:
        raise RuntimeError("no validation MAE")
    return best[1], best[0][0]


def _sd(v):
    if len(v) < 2:
        return None
    c = sum(v) / len(v)
    return math.sqrt(sum((x - c) ** 2 for x in v) / (len(v) - 1))


# 6. self-controlled tests ---------------------------------------------------------------

def self_controlled(rows: list[dict], blocks: dict, rev: L.Reversion) -> dict:
    cache = blocks["cache"]
    treated_abn, treated_raw = [], []
    for row in rows:
        eco, t0, pool = row["ecosystem"], row["t0"], row["pool"]
        for _i, name, edge_class in row["pending"]:
            base = {"ecosystem": eco, "t0": t0, "target": name, "edge_class": edge_class or "both",
                    "shock_sign": row["shock_sign"], "block": cache.block(name, eco), "s_event_days": row["s_days"]}

            def outcome(block, d, pool=pool):
                got = L.abnormal_shift(block, d, rev, pool)
                return None if got is None else got["abnormal"]

            treated_abn.append({**base, "outcome": outcome})
            treated_raw.append(dict(base))
    return {"abnormal": S.run(treated_abn, None), "raw": S.run(treated_raw, L.raw_shift)}


# 7. family, report -----------------------------------------------------------------------

def family(sc: dict, models: dict) -> dict:
    ab = sc["abnormal"]
    p = {
        "H1_self_controlled": ab["H1"].get("permutation_p"),
        "H2_positive_two_sided": ab["H2_positive"].get("permutation_p"),
        "H2_competitor_two_sided": ab["H2_competitor"].get("permutation_p"),
    }
    for key in FAMILY[3:]:
        p[key] = models.get("comparisons", {}).get(key, {}).get("permutation_p")
    adjusted = A.holm(p)
    decisions = {
        "H2_positive": S.decide_h2(ab["H2_positive"], "positive", bool(adjusted["rejected"].get("H2_positive_two_sided"))),
        "H2_competitor": S.decide_h2(ab["H2_competitor"], "competitor", bool(adjusted["rejected"].get("H2_competitor_two_sided"))),
    }
    return {"pvalues": p, "holm": adjusted, "decisions": decisions}


def render(payload: dict) -> str:
    tag = "EXPLORATORY (Wave 1 events, outcomes already seen)" if payload["exploratory"] else "CONFIRMATORY (Wave 2, amendment B)"
    out = [f"# Wave 2 outcomes — {tag}", ""]
    for source, block in payload["sources"].items():
        out += [f"## {source}", ""]
        lab = block["labels"]
        dec = lab.get("decomposition", {})
        out.append(f"Reversion fit: a = {lab['reversion']['a']:.4g}, b = {lab['reversion']['b']:.4g}, n = {lab['reversion']['n']}. "
                   f"Labels {lab['labels']}, with thin sector factor {lab['labels_with_thin_sector_factor']}.")
        if dec:
            out.append(f"Raw-shift variance {dec['raw_variance']:.4g}; removed by own reversion {dec['share_removed_by_own_reversion']:.1%}; "
                       f"removed in total {dec['share_removed_in_total']:.1%}.")
        out.append("")
        m = block["models"]
        if "test_mae" in m:
            out += ["| Model | Test MAE (abnormal) |", "|---|---:|"]
            out += [f"| {k} | {v:.6g} |" for k, v in sorted(m["test_mae"].items(), key=lambda kv: kv[1])]
            out += ["", "| Comparison | Gap | 95% interval | p | Relative gain |", "|---|---:|---|---:|---:|"]
            for k, c in m["comparisons"].items():
                out.append(f"| {k} | {c['gap']:.4g} | [{c['low']:.4g}, {c['high']:.4g}] | {c['permutation_p']:.4g} | {c['relative_mae_gain']:.2%} |")
            out += ["", "| Learned beta | Mean | SD |", "|---|---:|---:|"]
            out += [f"| {k} | {v['mean']:.4g} | {'' if v['sd'] is None else f'{v['sd']:.4g}'} |" for k, v in sorted(m["betas"].items())]
            out.append("")
        for label, sc in block["self_controlled"].items():
            out += [f"### Self-controlled tests, {label} outcome", "",
                    f"Pairs {sc['pairs']}. Balance valid {sc['balance']['valid']}, SMD {json.dumps({k: (None if v is None else round(v, 3)) for k, v in sc['balance']['smd'].items()})}.", "",
                    "| Test | Pairs | Effect | 95% interval | p | Inside ±0.05 |", "|---|---:|---:|---|---:|---|"]
            for t in ("H1", "H2_positive", "H2_competitor"):
                r = sc[t]
                if r.get("tested"):
                    out.append(f"| {t} | {r['n_pairs']} | {r['effect']:.4g} | [{r['low']:.4g}, {r['high']:.4g}] | {r['permutation_p']:.4g} | {r['inside_sesoi']} |")
                else:
                    out.append(f"| {t} | {r['n_pairs']} | not estimable (<10 pairs) | | | |")
            out.append("")
        fam = block["family"]
        out += ["### Holm family of 6", "", "| Test | p | Holm p | Rejects |", "|---|---:|---:|---|"]
        for k in FAMILY:
            raw, adj = fam["pvalues"].get(k), fam["holm"]["adjusted"].get(k)
            out.append(f"| {k} | {'' if raw is None else f'{raw:.4g}'} | {'' if adj is None else f'{adj:.4g}'} | {fam['holm']['rejected'].get(k)} |")
        out += ["", f"H2 positive: {fam['decisions']['H2_positive']}. H2 competitor: {fam['decisions']['H2_competitor']}.", ""]
    return "\n".join(out) + "\n"


WAVE2_GDELT_DB = ROOT / "data" / "interim" / "wave2" / "gdelt_wave2_series.sqlite"


def load_sources(names: list[str], wave2: bool = False) -> dict:
    """Wave 1 loaders by default. With wave2=True the 30-ecosystem config (scripts/wave2_config.py,
    amendments A2026-10-24-wave2 and A2026-10-25) replaces the Wave 1 NODES and GRAPH in place, and the
    Wave 2 GDELT series is read. A Wave 2 source whose series is not built stops with a message."""
    if wave2:
        import wave2_config as C
        C.activate()
    import phase4_outcome_run as R
    from phase2_gdelt_reserve_after import ARM_B, series_from_db
    from phase2_tweetskb_arm_b_counts import build_series

    spec = {"news_joined": ("A", "news"), "social": ("A", "social"), "gdelt": ("B", None), "tweetskb": ("B", None)}
    if wave2:
        everyone = list(R.NODES["ecosystems"])
        if len(everyone) != 30:
            raise SystemExit(f"Wave 2 needs 30 ecosystems, found {len(everyone)}")
        if "tweetskb" in names:
            raise SystemExit("Wave 2 Arm B is GDELT only; tweetskb was not extended")
        if {"news_joined", "social"} & set(names):
            raise SystemExit("Wave 2 Arm A series for the 16 new tickers are not built yet; run only --sources gdelt")
    arm_a = R.load_arm_a() if (not wave2 and {"news_joined", "social"} & set(names)) else {}
    loaded = {}
    for name in names:
        arm, co = spec[name]
        if name == "gdelt":
            if wave2 and not WAVE2_GDELT_DB.exists():
                raise SystemExit(f"{WAVE2_GDELT_DB} is not built yet; it needs all 128 GDELT slices first")
            series = series_from_db(WAVE2_GDELT_DB if wave2 else R.GDELT_DB)
        elif name == "tweetskb":
            series = build_series()
        else:
            series = arm_a[name]
        ecosystems = everyone if wave2 else (list(R.ARM_A) if arm == "A" else list(ARM_B))
        loaded[name] = (arm, co, series, ecosystems)
    return loaded


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sources", nargs="+", default=["gdelt", "news_joined", "social", "tweetskb"])
    parser.add_argument("--exploratory-wave1", action="store_true")
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()
    if args.self_check:
        import subprocess
        sys.exit(subprocess.run([sys.executable, str(ROOT / "scripts" / "test_wave2.py")]).returncode)
    import phase5_train as P

    if not args.exploratory_wave1:
        frozen = json.loads((ROOT / "configs" / "phase0.json").read_text()).get("amendments", [])
        if not any(str(a.get("id", "")).startswith("B") for a in frozen):
            raise SystemExit("amendment B is not frozen; run scripts/freeze_amendment_b.py --write first, "
                             "or pass --exploratory-wave1")
        import subprocess
        if subprocess.run([sys.executable, str(ROOT / "scripts" / "check_frozen_sha256.py")], cwd=ROOT).returncode != 0:
            raise SystemExit("frozen hashes do not match; a frozen file changed after the freeze")
    global OUT_JSON, OUT_MD
    if args.exploratory_wave1:
        OUT_JSON = OUT_JSON.with_name("wave2_outcomes_EXPLORATORY_wave1.json")
        OUT_MD = OUT_MD.with_name("wave2_outcomes_EXPLORATORY_wave1.md")
    payload = {"exploratory": args.exploratory_wave1, "sources": {}}
    for name, (arm, co, series, ecosystems) in load_sources(args.sources, wave2=not args.exploratory_wave1).items():
        print(f"building {name}", flush=True)
        rows, blocks = build_events(name, arm, co, series, ecosystems)
        train, val, _test, _split = P.day_folds([r["event"] for r in rows])
        cutoff = date.fromordinal(min(e.t0 for e in val)) if val else date.max
        labels = fill_labels(rows, blocks, cutoff)
        rev = labels.pop("rev")
        models = train_models(rows)
        sc = self_controlled(rows, blocks, rev)
        payload["sources"][name] = {"arm": arm, "labels": labels, "models": models, "self_controlled": sc, "family": family(sc, models)}
        OUT_JSON.write_text(json.dumps(payload, default=str) + "\n")
    OUT_MD.write_text(render(payload))
    print(f"wrote {OUT_MD}", flush=True)


if __name__ == "__main__":
    main()

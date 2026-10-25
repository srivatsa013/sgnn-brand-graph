"""Option A, the default demo. Synthetic fits stay in demo/. No real Phase 5 training."""

from __future__ import annotations

import html
import json
import random
import sys
from pathlib import Path

import pyarrow.compute as pc
import pyarrow.parquet as pq
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import phase4_analysis as stats  # noqa: E402
import phase5_model as M  # noqa: E402

from draw_real_graph import main as draw_real  # noqa: E402
from draw_real_graph import layout  # noqa: E402
from guard import ROOT, demo_file  # noqa: E402
from real_graph import load_graph  # noqa: E402
from synthetic_generator import (  # noqa: E402
    GENERATOR_VERSION,
    LAMBDAS,
    SEEDS,
    events_from_rows,
    frozen_noise,
    generate_rows,
    write_rows,
)

torch.set_num_threads(4)
EPOCHS = 6
PATIENCE = 3
HIDDEN = 32
DEPTH = 1
DROPOUT = 0.0


def _fit(variant: str, train: list, val: list, seed: int) -> tuple[M.SignedMP, dict]:
    model = M.SignedMP(4, HIDDEN, DEPTH, DROPOUT, variant)
    info = M.train_loop(model, train, val, epochs=EPOCHS, patience=PATIENCE, seed=seed)
    return model, info


def _event_mae(model: M.SignedMP, events: list, mean: torch.Tensor, std: torch.Tensor) -> list[float]:
    model.eval()
    out = []
    with torch.no_grad():
        for event in events:
            pred, _ = model.predict(M.apply_scaler(event, mean, std), event.edges)
            if not event.labels:
                continue
            out.append(sum(abs(float(pred[node]) - label) for node, label in event.labels.items()) / len(event.labels))
    return out


def _linear_mae(train: list, test: list) -> list[float]:
    xs, ys = [], []
    for event in train:
        shock = float(event.features[int(event.features[:, 1].argmax()), 0])
        for node, label in event.labels.items():
            sign = 0.0
            for edge in event.edges:
                if edge.kind == "struct" and edge.dst == node and edge.src != node and abs(float(event.features[edge.src, 1]) - 1.0) < 1e-6:
                    sign = edge.sign
            xs.append(sign * shock)
            ys.append(label)
    denom = sum(x * x for x in xs) or 1.0
    beta = sum(x * y for x, y in zip(xs, ys)) / denom
    maes = []
    for event in test:
        shock = float(event.features[int(event.features[:, 1].argmax()), 0])
        errs = []
        for node, label in event.labels.items():
            sign = 0.0
            for edge in event.edges:
                if edge.kind == "struct" and edge.dst == node and abs(float(event.features[edge.src, 1]) - 1.0) < 1e-6:
                    sign = edge.sign
            errs.append(abs(beta * sign * shock - label))
        if errs:
            maes.append(sum(errs) / len(errs))
    return maes


def _with_edges(events: list, edges_for) -> list:
    out = []
    for event in events:
        out.append(
            M.Event(
                event.event_id,
                event.t0,
                event.features,
                edges_for(event),
                dict(event.labels),
                list(event.comention_times),
                list(event.history_times),
                set(event.feature_doc_ids),
                set(event.label_doc_ids),
            )
        )
    return out


def _sign_shuffle(seed: int):
    def apply(event: M.Event) -> list:
        rng = random.Random(f"{seed}:{event.event_id}")
        struct = [edge for edge in event.edges if edge.kind == "struct"]
        signs = [edge.sign for edge in struct]
        rng.shuffle(signs)
        shuffled = [M.Edge(edge.src, edge.dst, "struct", sign, edge.weight) for edge, sign in zip(struct, signs)]
        return shuffled + [edge for edge in event.edges if edge.kind != "struct"]

    return apply


def _degree_match(seed: int):
    cache = {}

    def apply(event: M.Event) -> list:
        key = tuple((edge.src, edge.dst, edge.kind, edge.sign) for edge in event.edges)
        if key not in cache:
            struct = [(edge.src, edge.dst, int(edge.sign)) for edge in event.edges if edge.kind == "struct"]
            graphs = stats.rewire([(a, b, s) for a, b, s in struct], target=1, seed=seed)
            chosen = list(graphs["graphs"][0]) if graphs["graphs"] else struct
            cache[key] = [M.Edge(a, b, "struct", float(s), 1.0) for a, b, s in chosen]
        return cache[key] + [edge for edge in event.edges if edge.kind != "struct"]

    return apply


def _mean(values: list[float]) -> float | None:
    return None if not values else sum(values) / len(values)


def run_fits(table, graph: dict) -> list[dict]:
    records = []
    partial = demo_file("synthetic/SYNTHETIC_recovery_partial.jsonl")
    partial.write_text("")
    for arm in ("A", "B"):
        for lam in LAMBDAS:
            per_seed = []
            for seed in SEEDS:
                mask = pc.and_(
                    pc.and_(pc.equal(table["arm"], arm), pc.equal(table["lambda"], lam)),
                    pc.equal(table["seed"], seed),
                )
                rows = table.filter(mask).to_pylist()
                events = events_from_rows(rows, graph)
                split = M.chronological_split(events)
                train, val, test = split["train"], split["val"], split["test"]
                print(f"fit arm {arm} lambda {lam} seed {seed} train {len(train)} test {len(test)}", flush=True)
                fitted = {}
                maes = {}
                for variant in ("signed", "no_graph", "unsigned"):
                    model, _info = _fit(variant, train, val, seed)
                    mean, std = M._scale_stats(train)
                    maes[variant] = _event_mae(model, test, mean, std)
                    fitted[variant] = _mean(maes[variant])
                for name, edit in (("sign_shuffled", _sign_shuffle(seed)), ("degree_matched", _degree_match(seed))):
                    edited = _with_edges(events, edit)
                    edited_split = M.chronological_split(edited)
                    model, _info = _fit("signed", edited_split["train"], edited_split["val"], seed)
                    mean, std = M._scale_stats(edited_split["train"])
                    maes[name] = _event_mae(model, edited_split["test"], mean, std)
                    fitted[name] = _mean(maes[name])
                maes["linear_diffusion"] = _linear_mae(train, test)
                fitted["linear_diffusion"] = _mean(maes["linear_diffusion"])
                none_mae = fitted["no_graph"]
                row = {"arm": arm, "lambda": lam, "seed": seed, "test_mae": fitted, "gap_to_no_graph": {}}
                for name, value in fitted.items():
                    row["gap_to_no_graph"][name] = None if value is None or none_mae is None else value - none_mae
                row["event_mae_signed"] = maes["signed"]
                row["event_mae_no_graph"] = maes["no_graph"]
                per_seed.append(row)
                with partial.open("a") as handle:
                    handle.write(json.dumps({"arm": arm, "lambda": lam, "seed": seed, "test_mae": fitted, "gap_to_no_graph": row["gap_to_no_graph"]}) + "\n")
            records.extend(per_seed)
    return records


def _sign_flip_p(diffs: list[float], draws: int = 999, seed: int = 1) -> float | None:
    if not diffs:
        return None
    observed = sum(diffs) / len(diffs)
    rng = random.Random(seed)
    samples = []
    for _ in range(draws):
        total = 0.0
        for value in diffs:
            total += -value if rng.random() < 0.5 else value
        samples.append(total / len(diffs))
    return stats.permutation_p(observed, samples)


def summarize(records: list[dict]) -> dict:
    models = ("signed", "no_graph", "unsigned", "sign_shuffled", "degree_matched", "linear_diffusion")
    arms = {}
    for arm in ("A", "B"):
        by_lambda = {}
        detected = []
        fpr = None
        for lam in LAMBDAS:
            rows = [row for row in records if row["arm"] == arm and row["lambda"] == lam]
            block = {"seeds": len(rows), "models": {}}
            for name in models:
                maes = [row["test_mae"][name] for row in rows if row["test_mae"][name] is not None]
                gaps = [row["gap_to_no_graph"][name] for row in rows if row["gap_to_no_graph"][name] is not None]
                block["models"][name] = {"test_mae_mean": _mean(maes), "gap_to_no_graph_mean": _mean(gaps)}
            seed_hits = 0
            gaps = []
            for row in rows:
                signed = row["event_mae_signed"]
                base = row["event_mae_no_graph"]
                if not signed or not base or len(signed) != len(base):
                    continue
                diffs = [b - s for s, b in zip(signed, base)]
                gaps.append(sum(diffs) / len(diffs))
                p = _sign_flip_p(diffs, draws=199, seed=row["seed"] + 1)
                if p is not None and p < 0.05 and gaps[-1] > 0:
                    seed_hits += 1
            aggregate = _sign_flip_p(gaps, draws=999, seed=0)
            block["signed_better_than_no_graph_mean"] = _mean(gaps)
            block["aggregate_p"] = aggregate
            block["seeds_detected"] = seed_hits
            block["detection_rate"] = None if not rows else seed_hits / len(rows)
            by_lambda[str(lam)] = block
            if lam == 0.0:
                fpr = block["detection_rate"]
            elif aggregate is not None and aggregate < 0.05 and (block["signed_better_than_no_graph_mean"] or 0) > 0:
                detected.append(lam)
        arms[arm] = {"by_lambda": by_lambda, "smallest_lambda_detected_p_below_0.05": detected[0] if detected else None, "false_positive_rate_at_lambda_0": fpr}
    return {
        "label": "SYNTHETIC",
        "generator_version": GENERATOR_VERSION,
        "demo_fit": {"hidden": HIDDEN, "depth": DEPTH, "dropout": DROPOUT, "max_epochs": EPOCHS, "patience": PATIENCE, "seeds": list(SEEDS)},
        "gap_definition": "test MAE minus no-graph test MAE. A negative gap is a lower test error than the no-graph baseline.",
        "detection": "Across seeds, the mean of (no-graph event MAE minus signed event MAE) is tested with a sign-flip permutation. A lambda is detected when that mean is positive and the p-value is below 0.05. The false-positive rate is the fraction of seeds detected at lambda 0.",
        "arms": arms,
        "note": "SYNTHETIC demonstration. Not evidence about real propagation.",
    }


def _hex(value: float, limit: float) -> str:
    if limit <= 0:
        return "#94a3b8"
    unit = max(-1.0, min(1.0, value / limit))
    if unit >= 0:
        return f"#{int(255 - 80 * unit):02x}{int(80 + 120 * unit):02x}80"
    return f"#{int(180 + 40 * (-unit)):02x}{int(80 - 40 * (-unit)):02x}{int(60):02x}"


def summary_page(graph: dict, recovery: dict) -> None:
    outcomes = json.loads((ROOT / "eval" / "results" / "phase4_outcomes.json").read_text())
    joined = outcomes["arms"]["A"]["sources"]["news_joined"]
    pos = joined["H2_positive"]
    comp = joined["H2_competitor"]
    noise = frozen_noise()["social"]
    overview = layout(graph, width=1600, height=1100)
    real_shade = {}
    syn_shade = {}
    for edge in graph["positive_edges"]:
        real_shade[(edge["src"], edge["dst"])] = pos["effect"]
        syn_shade[(edge["src"], edge["dst"])] = noise
    for edge in graph["competitor_edges"]:
        real_shade[(edge["src"], edge["dst"])] = comp["effect"]
        syn_shade[(edge["src"], edge["dst"])] = -noise
    real_limit = max(abs(pos["effect"] or 0), abs(comp["effect"] or 0), 1e-6)
    syn_limit = noise

    def panel(title: str, shade: dict, limit: float, caption: str) -> str:
        parts = [f'<svg viewBox="0 0 1600 1100" width="100%" role="img"><rect width="1600" height="1100" fill="#f8fafc"/>', f'<text x="24" y="36" font-size="28" font-family="Georgia">{title}</text>', f'<text x="24" y="62" font-size="14" font-family="Georgia">{caption}</text>']
        drawn = set(overview)
        for edge in graph["comention_edges"]:
            if edge["src"] in drawn and edge["dst"] in drawn:
                x1, y1 = overview[edge["src"]]
                x2, y2 = overview[edge["dst"]]
                parts.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="#667085" stroke-dasharray="5 5"/>')
        for edge in graph["positive_edges"] + graph["competitor_edges"]:
            if edge["src"] not in drawn or edge["dst"] not in drawn:
                continue
            x1, y1 = overview[edge["src"]]
            x2, y2 = overview[edge["dst"]]
            color = _hex(shade.get((edge["src"], edge["dst"]), 0.0), limit)
            parts.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{color}" stroke-width="3"/>')
        for name, (x, y) in overview.items():
            parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="#0f172a"/>')
            parts.append(f'<text x="{x+7:.1f}" y="{y+3:.1f}" font-size="11" font-family="Georgia">{name}</text>')
        parts.append("</svg>")
        return "".join(parts)

    real_caption = f'Joined-news H2 positive effect {pos["effect"]:.6g}, interval [{pos["low"]:.6g}, {pos["high"]:.6g}], pairs {pos["n_pairs"]}. Competitor effect {comp["effect"]:.6g}, interval [{comp["low"]:.6g}, {comp["high"]:.6g}], pairs {comp["n_pairs"]}.'
    syn_caption = f'Planted shift at lambda 1.0 times the Arm A social SD {noise:.6g}. Positive edges {noise:.6g}. Competitor edges {-noise:.6g}. Co-mention planted shift 0.'
    table = html.escape((ROOT / "reports" / "phase4_outcomes.md").read_text())
    recovery_html = "<pre>" + json.dumps(recovery, indent=2) + "</pre>"
    page = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>REAL and SYNTHETIC summary</title>
<style>body{{font-family:Georgia,serif;margin:24px;background:#f8fafc;color:#0f172a}} .grid{{display:grid;grid-template-columns:1fr 1fr;gap:16px}} pre{{white-space:pre-wrap;background:white;padding:12px;border:1px solid #e2e8f0}} h2{{margin-bottom:4px}}</style>
</head><body>
<h1>Option A summary</h1>
<p>The left panel and the Phase 4 table are REAL. The right panel and the recovery block are SYNTHETIC. Synthetic numbers are not written into the real table.</p>
<div class="grid">
<section><h2>REAL</h2>{panel("REAL", real_shade, real_limit, real_caption)}</section>
<section><h2>SYNTHETIC</h2>{panel("SYNTHETIC lambda = 1.0", syn_shade, syn_limit, syn_caption)}</section>
</div>
<h2>REAL Phase 4 results</h2>
<pre>{table}</pre>
<h2>SYNTHETIC simulation recovery</h2>
{recovery_html}
</body></html>
"""
    demo_file("option_a/REAL_and_SYNTHETIC_summary.html").write_text(page)


def main() -> None:
    draw_real()
    graph = load_graph()
    parquet = Path(demo_file("synthetic/SYNTHETIC_events.parquet"))
    if not parquet.exists():
        rows, meta = generate_rows(graph)
        write_rows(rows, meta)
    table = pq.read_table(parquet)
    records = run_fits(table, graph)
    recovery = summarize(records)
    demo_file("synthetic/SYNTHETIC_recovery_table.json").write_text(json.dumps(recovery, indent=2) + "\n")
    summary_page(graph, recovery)
    print("wrote SYNTHETIC recovery and REAL/SYNTHETIC summary", flush=True)


if __name__ == "__main__":
    main()

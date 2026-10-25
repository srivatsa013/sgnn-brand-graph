"""Build site/assets/evidence.json for the website's Evidence view.

Reads only stored result files. Nothing is re-estimated, refit or rescored here. Every number in the
output is copied from, or arithmetically derived from, one of these files:

  eval/results/phase5_outcomes.json        test MAE per model, gap to no-graph, held-out ecosystem MAE
  reports/phase5_outcomes.md               test RMSE and sign accuracy table (forward pass of stored weights)
  eval/results/phase4_outcomes.json        propagation effects H1, H2, H4 with intervals and balance flags
  eval/results/phase4_audit_sample3.json   scorer audit: macro-F1 with intervals, linking precision
  eval/results/wave2_scorer_v2.json        Wave 2 sheet: scorer comparison and confusion matrices

Run from the project root:  python scripts/build_site_evidence.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "eval" / "results"
OUT = ROOT / "site" / "assets" / "evidence.json"
CLASSES = ["positive", "negative", "neutral"]
SOURCE_LABELS = {
    "news_joined": ("Arm A", "News (headline, summary, body)"),
    "social": ("Arm A", "Social (StockTwits)"),
    "gdelt": ("Arm B", "News (GDELT)"),
    "tweetskb": ("Arm B", "Social (TweetsKB)"),
}
MODEL_ORDER = ["signed", "unsigned", "sign_shuffled", "degree_matched", "linear_diffusion", "no_graph"]


def load(path: Path):
    return json.loads(path.read_text())


def per_class(confusion: dict) -> dict:
    """Precision, recall and F1 per class from a gold-by-predicted confusion matrix."""
    out = {"labels": CLASSES, "precision": [], "recall": [], "f1": [], "support": []}
    for label in CLASSES:
        tp = confusion[label][label]
        predicted = sum(confusion[g][label] for g in CLASSES)
        actual = sum(confusion[label][p] for p in CLASSES)
        precision = tp / predicted if predicted else 0.0
        recall = tp / actual if actual else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        out["precision"].append(precision)
        out["recall"].append(recall)
        out["f1"].append(f1)
        out["support"].append(actual)
    out["macro_f1"] = sum(out["f1"]) / len(CLASSES)
    return out


def matrix(confusion: dict) -> list[list[int]]:
    return [[int(confusion[g][p]) for p in CLASSES] for g in CLASSES]


def rmse_table(md: str) -> dict:
    """Parse the Test RMSE and sign accuracy table of reports/phase5_outcomes.md."""
    section = md.split("## Test RMSE and sign accuracy", 1)[1]
    rows: dict = {}
    for line in section.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 6 and cells[0] in SOURCE_LABELS and cells[1] in MODEL_ORDER:

            def num(text: str):
                return float(text) if re.fullmatch(r"-?\d+(\.\d+)?([eE]-?\d+)?", text) else None

            rows[(cells[0], cells[1])] = {
                "rmse": num(cells[2]), "rmse_sd": num(cells[3]), "sign": num(cells[4]), "sign_sd": num(cells[5]),
            }
    return rows


def build() -> dict:
    p5 = load(RES / "phase5_outcomes.json")
    p4 = load(RES / "phase4_outcomes.json")
    audit = load(RES / "phase4_audit_sample3.json")
    w2 = load(RES / "wave2_scorer_v2.json")
    rmse = rmse_table((ROOT / "reports" / "phase5_outcomes.md").read_text())

    # 1. Scorer quality
    macro = []
    for key, name in (("headline", "Final scorer, headline only"), ("joined", "Final scorer, headline, summary and body")):
        o = audit[key]["overall"]
        macro.append({"name": name, "set": "Audit sheet 3", "n": o["n"], "value": o["macro_f1"], "lo": o["lo"], "hi": o["hi"]})
    v = audit["vader_headline"]["overall"]
    macro.append({"name": "VADER, headline", "set": "Audit sheet 3", "n": v["n"], "value": v["macro_f1"], "lo": v["lo"], "hi": v["hi"]})
    for key, name in (("wave1_scorer", "Final scorer, marked sentence"), ("finance_pretrained", "FinBERT, marked sentence")):
        o = w2[key]
        macro.append({"name": name, "set": "Wave 2 sheet", "n": o["n"], "value": o["macro_f1"], "lo": o["ci95"][0], "hi": o["ci95"][1]})
    shown = w2["wave1_scorer"]
    scorer = {
        "gate": w2["gate"],
        "gate_met": bool(w2["gate_met"]),
        "macro_f1": macro,
        "per_class": {**per_class(shown["confusion"]), "n": shown["n"], "scorer": "Final scorer", "set": "Wave 2 sheet"},
        "confusion": {"labels": CLASSES, "matrix": matrix(shown["confusion"]), "n": shown["n"]},
        "linking": {
            "named": audit["linking_precision"]["named"],
            "other": audit["linking_precision"]["other"],
        },
    }

    # 2-4. Propagation model against baselines
    sources = []
    for key, (arm, label) in SOURCE_LABELS.items():
        s = p5["sources"][key]
        models = []
        for name in MODEL_ORDER:
            m = s["models"][name]
            models.append({"name": name, "mae": m["test_mae"], "sd": m.get("test_mae_sd")})
        g = s["h3"]["signed_vs_nograph"]
        sources.append({
            "key": key, "arm": arm, "label": label,
            "n_test": s["split"]["n_test"],
            "models": models,
            "gap": {k: g[k] for k in ("gap", "low", "high", "permutation_p", "relative_mae_gain", "n_events")},
            "signed_rmse": rmse[(key, "signed")]["rmse"],
            "sign": {"signed": rmse[(key, "signed")]["sign"], "signed_sd": rmse[(key, "signed")]["sign_sd"],
                     "linear": rmse[(key, "linear_diffusion")]["sign"]},
            "loeo": [{"ecosystem": e["ecosystem"], "mae": e["test_mae"], "n": e["n_test"]}
                     for e in s["loeo"] if e["test_mae"] is not None],
            "h3_supported": bool((p5["support"].get(key) or {}).get("signed_vs_nograph") == "supported"),
            "in_family": key in ("news_joined", "gdelt"),
        })

    # 5. Measured propagation effects
    effects = []
    for arm_key, arm in p4["arms"].items():
        for src_key, src in arm["sources"].items():
            if src_key not in SOURCE_LABELS:
                continue
            for test_key, test_label in (("H1", "All neighbours"), ("H2_positive", "Positive edges"), ("H2_competitor", "Competitor edges")):
                t = src[test_key]
                effects.append({
                    "arm": "Arm " + arm_key, "source": SOURCE_LABELS[src_key][1], "test": test_label,
                    "pairs": t["n_pairs"], "events": t["n_events"], "tested": bool(t["tested"]),
                    "effect": t.get("effect"), "low": t.get("low"), "high": t.get("high"),
                    "balance_ok": bool(src["balance"]["valid"]),
                })
    return {
        "title": "Measured on real data (Wave 1)",
        "scorer": scorer,
        "propagation": sources,
        "effects": effects,
        "sesoi": 0.05,
        "min_pairs": 10,
    }


def main() -> int:
    data = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=1))
    print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

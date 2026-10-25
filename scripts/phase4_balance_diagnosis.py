"""Balance diagnosis and exploratory splits. Does not replace confirmatory results.

Choices logged in the output:
- Matched pairs were not stored in phase4_outcomes.json, so this script rebuilds
  them with the unchanged matcher. It does not write that file.
- Mention gap is the absolute difference of the baseline log1p mention covariate.
- Popularity gap is the absolute difference of log1p(sitelinks).
- Median and 90th percentile use position p*(n-1) on the sorted gaps.
- Event size is the brand's event-bin scored count.
- "Named in the text" is computed only for the restricted news series: the
  neighbor has a scored cell on t0, and that series keeps a document only when
  the node is named in the headline or summary. Social, GDELT, and TweetsKB
  day cells have no document text, so that split is not computed.
- The exploratory calipers are ln(1.5) for mentions and popularity. They are
  set only for this run and then restored. phase0.json is not edited.
- Exploratory rows are not in a Holm family. A class under 10 pairs is not tested.
"""

from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import phase2_revised_recount as recount  # noqa: E402
import phase4_analysis as A  # noqa: E402
import phase4_outcome_run as R  # noqa: E402
from phase2_gdelt_reserve_after import ARM_B, series_from_db  # noqa: E402
from phase2_tweetskb_arm_b_counts import build_series  # noqa: E402

OUT_JSON = ROOT / "eval" / "results" / "phase4_balance_exploratory.json"
OUT_MD = ROOT / "reports" / "phase4_balance_diagnosis.md"
SOURCES = ("news_joined", "news_headline", "social", "gdelt", "tweetskb")


def independent_smd(rows: list[dict]) -> dict[str, float]:
    """Same formula as phase4_outcome_run.balance, written separately."""
    names = ("baseline_mean", "baseline_sd", "log_mention", "log_popularity")

    def column(side: str, index: int) -> list[float]:
        values = []
        for row in rows:
            base = row["treated_base"] if side == "treated" else row["control_base"]
            pop = row["treated_pop"] if side == "treated" else row["control_pop"]
            values.append([base[0], base[1], base[2], math.log1p(pop)][index])
        return values

    out = {}
    for index, name in enumerate(names):
        treated = column("treated", index)
        control = column("control", index)
        mt = sum(treated) / len(treated)
        mc = sum(control) / len(control)
        vt = sum((v - mt) ** 2 for v in treated) / (len(treated) - 1)
        vc = sum((v - mc) ** 2 for v in control) / (len(control) - 1)
        pooled = math.sqrt((vt + vc) / 2)
        out[name] = 0.0 if pooled == 0 else abs(mt - mc) / pooled
    return out


def percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = p * (len(ordered) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def gaps(rows: list[dict]) -> dict:
    mention = [abs(row["treated_base"][2] - row["control_base"][2]) for row in rows]
    popularity = [abs(math.log1p(row["treated_pop"]) - math.log1p(row["control_pop"])) for row in rows]
    return {
        "mention_gap_median": percentile(mention, 0.5),
        "mention_gap_p90": percentile(mention, 0.9),
        "popularity_gap_median": percentile(popularity, 0.5),
        "popularity_gap_p90": percentile(popularity, 0.9),
        "n_pairs": len(rows),
    }


def failed_criteria(smd: dict) -> list[str]:
    return [name for name, value in smd.items() if value is not None and value > 0.20]


def pack_test(rows: list[dict], key: str, sd: float, rewiring_p: float | None = None) -> dict:
    summary = R.summarize(rows, key, sd)
    summary["label"] = "exploratory"
    summary["holm_family"] = None
    if rewiring_p is not None:
        summary["rewiring_p"] = rewiring_p
    return summary


def event_size(cache: R.Cache, eco: str, t0) -> int:
    cell = cache.block(eco, "").get(t0.isoformat())
    return int(cell[1]) if cell else 0


def named_on_day(cache: R.Cache, source: str, target: str, eco: str, t0) -> bool | None:
    if source not in {"news_joined", "news_headline"}:
        return None
    cell = cache.block(target, eco).get(t0.isoformat())
    return bool(cell and cell[1] >= 1)


def tercile_map(pairs: list[dict], cache: R.Cache) -> dict[str, str]:
    sizes = {}
    for row in pairs:
        sizes[row["event_id"]] = event_size(cache, row["ecosystem"], row["t0"])
    ordered = sorted(sizes, key=lambda key: (sizes[key], key))
    labels = ("tercile_1", "tercile_2", "tercile_3")
    out = {}
    n = len(ordered)
    for index, event_id in enumerate(ordered):
        out[event_id] = labels[min(2, (index * 3) // n)] if n else "tercile_1"
    return out


def split_rows(table: list[dict], cache: R.Cache, source: str) -> dict:
    terciles = tercile_map(table, cache)
    groups = {
        "edge_positive": [],
        "edge_competitor": [],
        "tercile_1": [],
        "tercile_2": [],
        "tercile_3": [],
        "named": [],
        "not_named": [],
    }
    for row in table:
        if row["edge_class"] == "positive":
            groups["edge_positive"].append(row)
        elif row["edge_class"] == "competitor":
            groups["edge_competitor"].append(row)
        groups[terciles[row["event_id"]]].append(row)
        named = named_on_day(cache, source, row["target"], row["ecosystem"], row["t0"])
        if named is True:
            groups["named"].append(row)
        elif named is False:
            groups["not_named"].append(row)
    return groups


def arm_pairs(series_map: dict, ecosystems: list[str]) -> dict[str, tuple]:
    controls = R.prepare_controls(ecosystems)
    names = set(ecosystems)
    for eco in ecosystems:
        spec = R.NODES["ecosystems"][eco]
        names.update(spec["positive_nodes"])
        names.update(spec["competitor_nodes"])
    edges = R.structural_edges(names)
    found = {}
    for source, series in series_map.items():
        print(f"match {source}", flush=True)
        cache = R.Cache(series)
        bank = R.Bank(cache, list(ecosystems), controls)
        raw = R.rows_for(bank, list(ecosystems), edges, source, "confirmatory")
        found[source] = (raw, cache, controls, edges, list(ecosystems))
    return found


def exploratory_tight(cache, ecosystems, controls, edges, source: str, sd: float) -> dict:
    old_mention, old_pop = recount.MENTION_CALIPER, recount.POP_CALIPER
    recount.MENTION_CALIPER = math.log(1.5)
    recount.POP_CALIPER = math.log(1.5)
    try:
        bank = R.Bank(cache, ecosystems, controls)
        raw = R.rows_for(bank, ecosystems, edges, source, "confirmatory")
        print(f"tight {source} pairs {len(raw)}", flush=True)
        rewire = R.rewiring_stats(bank, ecosystems, edges, source)
        table = A.pair_table(raw)
        bal = R.balance(raw)
        h1 = pack_test(table, "h1_diff", sd)
        h1["rewiring_p"] = None
        if h1["tested"] and rewire["means"] and h1["effect"] is not None:
            h1["rewiring_p"] = A.rewiring_p(h1["effect"], rewire["means"])
        h1["distinct_rewirings"] = rewire["distinct"]
        return {
            "label": "exploratory",
            "calipers": {"mention": math.log(1.5), "popularity": math.log(1.5)},
            "balance": bal,
            "failed_criteria": failed_criteria(bal["smd"]),
            "H1": h1,
            "H2_positive": pack_test([row for row in table if row["edge_class"] == "positive"], "aligned_shift", sd),
            "H2_competitor": pack_test([row for row in table if row["edge_class"] == "competitor"], "aligned_shift", sd),
        }
    finally:
        recount.MENTION_CALIPER = old_mention
        recount.POP_CALIPER = old_pop


def plain(value):
    if isinstance(value, dict):
        return {key: plain(item) for key, item in value.items()}
    if isinstance(value, list):
        return [plain(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def fmt(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def main() -> None:
    stored = json.loads((ROOT / "eval" / "results" / "phase4_outcomes.json").read_text())
    sds = R.frozen_sds()
    print("loading series", flush=True)
    arm_a = R.load_arm_a()
    arm_b = {"gdelt": series_from_db(R.GDELT_DB), "tweetskb": build_series()}
    built = {}
    built.update(arm_pairs(arm_a, list(R.ARM_A)))
    built.update(arm_pairs(arm_b, list(ARM_B)))
    sd_of = {
        "news_joined": sds["news_joined_restricted"]["sd"],
        "news_headline": sds["news_headline_restricted"]["sd"],
        "social": sds["social"]["sd"],
        "gdelt": sds["arm_b_gdelt"]["sd"],
        "tweetskb": sds["arm_b_tweetskb"]["sd"],
    }
    payload = {"label": "exploratory except the stored-balance comparison", "sources": {}}
    for source in SOURCES:
        raw, cache, controls, edges, ecosystems = built[source]
        stored_smd = stored["arms"]["A" if source in arm_a else "B"]["sources"][source]["balance"]["smd"]
        fresh = R.balance(raw)["smd"]
        again = independent_smd(raw)
        agree = all(abs(fresh[name] - stored_smd[name]) < 1e-8 and abs(again[name] - stored_smd[name]) < 1e-8 for name in fresh)
        table = A.pair_table(raw)
        for raw_row, row in zip(raw, table):
            row["treated_base"] = raw_row["treated_base"]
            row["control_base"] = raw_row["control_base"]
            row["treated_pop"] = raw_row["treated_pop"]
            row["control_pop"] = raw_row["control_pop"]
            row["t0"] = raw_row["t0"]
        groups = split_rows(table, cache, source)
        cells = {}
        for name, rows in groups.items():
            if name.startswith("edge_"):
                key = "h1_diff"
            else:
                key = "h1_diff"
            cells[name] = {
                "H1": pack_test(rows, "h1_diff", sd_of[source]),
                "H2_positive": pack_test([row for row in rows if row["edge_class"] == "positive"], "aligned_shift", sd_of[source]),
                "H2_competitor": pack_test([row for row in rows if row["edge_class"] == "competitor"], "aligned_shift", sd_of[source]),
            }
            cells[name]["H1"].pop("unused", None)
            _ = key
        payload["sources"][source] = {
            "stored_smd": stored_smd,
            "rebuilt_smd": fresh,
            "independent_smd": again,
            "smds_agree": agree,
            "failed_criteria": failed_criteria(stored_smd),
            "valid_rule": "balance() line 470: valid is False when any absolute SMD exceeds 0.20",
            "method_failed_rule": "h1_decision line 84 returns method failed when balance_valid is False",
            "smd_formula": "abs(mean_treated - mean_control) / sqrt((sample_var_treated + sample_var_control) / 2), divisor n-1",
            "gaps": gaps(raw),
            "exploratory_tight_caliper": exploratory_tight(cache, ecosystems, controls, edges, source, sd_of[source]),
            "exploratory_splits": cells,
        }
        print(source, "agree", agree, "failed", payload["sources"][source]["failed_criteria"], flush=True)
    OUT_JSON.write_text(json.dumps(plain(payload)) + "\n")
    OUT_MD.write_text(render(payload))
    print(f"wrote {OUT_MD}", flush=True)


def render(payload: dict) -> str:
    lines = [
        "# Phase 4 balance diagnosis",
        "",
        "The confirmatory tests were not rerun and `eval/results/phase4_outcomes.json` was not replaced. Every tight-caliper and split row is exploratory and is outside the Holm family.",
        "",
        "H1 is method failed when `h1_decision` reaches line 84 because `balance_valid` is false. `balance` line 470 sets `valid` false when any absolute SMD is above 0.20. The SMD is the absolute difference of means divided by the square root of the average of the two sample variances, divisor n−1.",
        "",
    ]
    for source, block in payload["sources"].items():
        lines.append(f"## {source}")
        lines.append("")
        lines.append(f"Stored and rebuilt SMDs agree: {block['smds_agree']}. Criteria above 0.20: {', '.join(block['failed_criteria']) or 'none'}.")
        lines.append("")
        lines.append("| Covariate | Stored SMD | Rebuilt SMD | Independent SMD |")
        lines.append("|---|---:|---:|---:|")
        for name in ("baseline_mean", "baseline_sd", "log_mention", "log_popularity"):
            lines.append(f"| {name} | {fmt(block['stored_smd'][name])} | {fmt(block['rebuilt_smd'][name])} | {fmt(block['independent_smd'][name])} |")
        gap = block["gaps"]
        lines.append("")
        lines.append(f"Mention-gap median {fmt(gap['mention_gap_median'])}, 90th percentile {fmt(gap['mention_gap_p90'])}. Popularity-gap median {fmt(gap['popularity_gap_median'])}, 90th percentile {fmt(gap['popularity_gap_p90'])}. Pairs {gap['n_pairs']}.")
        tight = block["exploratory_tight_caliper"]
        lines.append("")
        lines.append("Exploratory re-match, mention caliper ln 1.5 and popularity caliper ln 1.5.")
        lines.append("")
        lines.append("| Test | Pairs | Events | Effect | 95% interval | Permutation p | Rewiring p | SESOI band | SMD mean | SMD SD | SMD mention | SMD popularity |")
        lines.append("|---|---:|---:|---:|---|---:|---:|---|---:|---:|---:|---:|")
        smd = tight["balance"]["smd"]
        for test in ("H1", "H2_positive", "H2_competitor"):
            row = tight[test]
            lines.append(
                f"| exploratory {test} | {row['n_pairs']} | {row['n_events']} | {fmt(row.get('effect'))} | {interval(row)} | {fmt(row.get('permutation_p'))} | {fmt(row.get('rewiring_p'))} | {row.get('sesoi_interval') or ''} | {fmt(smd.get('baseline_mean'))} | {fmt(smd.get('baseline_sd'))} | {fmt(smd.get('log_mention'))} | {fmt(smd.get('log_popularity'))} |"
            )
        lines.append("")
        lines.append("Exploratory splits of the original matched pairs. A cell under 10 pairs is not tested.")
        lines.append("")
        lines.append("| Split | Test | Pairs | Effect | 95% interval | Permutation p | SESOI band |")
        lines.append("|---|---|---:|---:|---|---:|---|")
        for split, tests in block["exploratory_splits"].items():
            for test, row in tests.items():
                lines.append(f"| exploratory {split} | {test} | {row['n_pairs']} | {fmt(row.get('effect'))} | {interval(row)} | {fmt(row.get('permutation_p'))} | {row.get('sesoi_interval') or ''} |")
        lines.append("")
    return "\n".join(lines) + "\n"


def interval(row: dict) -> str:
    if row.get("low") is None:
        return ""
    return f"[{row['low']:.6g}, {row['high']:.6g}]"


if __name__ == "__main__":
    main()

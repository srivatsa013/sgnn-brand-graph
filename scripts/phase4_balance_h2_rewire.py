"""Fill exploratory H2 rewiring p-values. Does not change stored effects or confirmatory files."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import phase2_revised_recount as recount  # noqa: E402
import phase4_analysis as A  # noqa: E402
import phase4_outcome_run as R  # noqa: E402
from phase2_gdelt_reserve_after import ARM_B, series_from_db  # noqa: E402
from phase2_tweetskb_arm_b_counts import build_series  # noqa: E402

JSON_PATH = ROOT / "eval" / "results" / "phase4_balance_exploratory.json"
MD_PATH = ROOT / "reports" / "phase4_balance_diagnosis.md"


def h2_means(bank, ecosystems, edges, source: str) -> dict:
    graphs = A.rewire(edges, target=500, seed=2)
    positive, competitor = [], []
    for index, graph in enumerate(graphs["graphs"], start=1):
        rows = R.rows_for(bank, ecosystems, sorted(graph), source, "rewired")
        table = A.pair_table(rows)
        pos = [row["aligned_shift"] for row in table if row["edge_class"] == "positive"]
        comp = [row["aligned_shift"] for row in table if row["edge_class"] == "competitor"]
        if pos:
            positive.append(sum(pos) / len(pos))
        if comp:
            competitor.append(sum(comp) / len(comp))
        if index % 50 == 0:
            print(f"h2 rewiring {source} {index}", flush=True)
    return {"positive": positive, "competitor": competitor, "distinct": graphs["distinct"]}


def arm_inputs(series_map, ecosystems):
    controls = R.prepare_controls(ecosystems)
    names = set(ecosystems)
    for eco in ecosystems:
        spec = R.NODES["ecosystems"][eco]
        names.update(spec["positive_nodes"])
        names.update(spec["competitor_nodes"])
    edges = R.structural_edges(names)
    found = {}
    for source, series in series_map.items():
        print(f"prepare {source}", flush=True)
        cache = R.Cache(series)
        found[source] = (cache, controls, edges, list(ecosystems))
    return found


def patch_markdown(source: str, positive, competitor) -> None:
    text = MD_PATH.read_text()
    marker = f"## {source}\n"
    start = text.index(marker)
    nxt = text.find("\n## ", start + 1)
    block = text[start:nxt if nxt > 0 else len(text)]
    old = block
    for label, value in (("H2_positive", positive), ("H2_competitor", competitor)):
        needle = f"| exploratory {label} |"
        line_start = block.find(needle)
        if line_start < 0:
            continue
        line_end = block.find("\n", line_start)
        line = block[line_start:line_end]
        cells = line.split("|")
        # columns: empty, test, pairs, events, effect, interval, perm, rewiring, sesoi, smds...
        if len(cells) > 7 and cells[7].strip() == "":
            shown = "" if value is None else f"{value:.6g}"
            cells[7] = f" {shown} "
            block = block[:line_start] + "|".join(cells) + block[line_end:]
    if block != old:
        text = text[:start] + block + text[nxt if nxt > 0 else len(text):]
        MD_PATH.write_text(text)


def main() -> None:
    payload = json.loads(JSON_PATH.read_text())
    print("loading series", flush=True)
    arm_a = R.load_arm_a()
    arm_b = {"gdelt": series_from_db(R.GDELT_DB), "tweetskb": build_series()}
    built = {}
    built.update(arm_inputs(arm_a, list(R.ARM_A)))
    built.update(arm_inputs(arm_b, list(ARM_B)))
    old_m, old_p = recount.MENTION_CALIPER, recount.POP_CALIPER
    recount.MENTION_CALIPER = math.log(1.5)
    recount.POP_CALIPER = math.log(1.5)
    try:
        for source, (cache, controls, edges, ecosystems) in built.items():
            bank = R.Bank(cache, ecosystems, controls)
            means = h2_means(bank, ecosystems, edges, source)
            tight = payload["sources"][source]["exploratory_tight_caliper"]
            for key, store in (("H2_positive", "positive"), ("H2_competitor", "competitor")):
                effect = tight[key].get("effect")
                pvalue = None if effect is None else A.rewiring_p(effect, means[store])
                tight[key]["rewiring_p"] = pvalue
                tight[key]["rewiring_draws"] = len(means[store])
                print(source, key, pvalue, flush=True)
            patch_markdown(source, tight["H2_positive"].get("rewiring_p"), tight["H2_competitor"].get("rewiring_p"))
            JSON_PATH.write_text(json.dumps(payload) + "\n")
    finally:
        recount.MENTION_CALIPER = old_m
        recount.POP_CALIPER = old_p


if __name__ == "__main__":
    main()

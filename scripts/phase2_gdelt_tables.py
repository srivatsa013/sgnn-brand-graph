"""Coverage, events, and the pre-control funnel for the stored GDELT series.

No BigQuery. No shifts. Controls are absent, so pairs are not matched.
"""

from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from datetime import date
from pathlib import Path

from phase1_gates import detect_daily, eligible_placebo_days

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "interim" / "phase2" / "gdelt_series.sqlite"
OUT = ROOT / "eval" / "results" / "phase2_gdelt_tables.json"

ARM_B = ("Apple", "Microsoft", "Alphabet")
OVERLAP_START = date(2016, 11, 14)
OVERLAP_END = date(2020, 12, 31)


def both_windows(series: dict, t0: date) -> bool:
    def bins(start: date, end: date) -> int:
        n = 0
        day = start
        from datetime import timedelta

        while day <= end:
            cell = series.get(day.isoformat())
            if cell and cell[1] >= 1:
                n += 1
            day += timedelta(days=1)
        return n

    from datetime import timedelta

    return bins(t0 - timedelta(days=7), t0 - timedelta(days=1)) >= 3 and bins(t0, t0 + timedelta(days=7)) >= 3


def positive_targets(graph: dict, nodes: dict) -> dict[str, list[str]]:
    out = {}
    for eco, spec in nodes["ecosystems"].items():
        found = []
        for edge in graph["positive_edges"] + graph["ceo_edges"]:
            pair = edge.get("nodes") or []
            if eco not in pair or len(pair) != 2:
                continue
            other = pair[0] if pair[1] == eco else pair[1]
            if other in spec["positive_nodes"] and other not in found:
                found.append(other)
        out[eco] = found
    return out


def main() -> None:
    inv = json.loads((ROOT / "eval" / "results" / "phase2_gdelt_filter_inventory.json").read_text())
    present_titles = {title for title, _count in inv["wiki_counts"]}
    uni = json.loads((ROOT / "configs" / "phase1_universe.json").read_text())
    tick = json.loads((ROOT / "kg" / "snapshots" / "wikidata_2026-10-12" / "tickers.json").read_text())
    ent = json.loads((ROOT / "kg" / "snapshots" / "wikidata_2026-10-12" / "entities.json").read_text())
    nodes = json.loads((ROOT / "configs" / "phase2_nodes.json").read_text())
    graph = json.loads((ROOT / "kg" / "phase2_structural_edges.json").read_text())
    rule = json.loads((ROOT / "configs" / "gdelt_match_rule.json").read_text())

    pool = []
    for names in uni["control_pool_by_bucket"].values():
        pool.extend(names)
    control_rows = []
    for ticker in pool:
        chosen = (tick.get(ticker) or {}).get("chosen") or {}
        qid = chosen.get("qid")
        title = (ent.get(qid) or {}).get("enwiki") if qid else None
        key = title.replace(" ", "_") if title else None
        control_rows.append(
            {
                "ticker": ticker,
                "qid": qid,
                "enwiki": title,
                "in_extract": bool(key and key in present_titles),
            }
        )

    con = sqlite3.connect(DB)
    series: dict[tuple[str, str], dict] = {}
    coverage_acc: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    for node, day, documents, scored, score_sum in con.execute(
        "SELECT node, day, document_count, scored_count, score_sum FROM daily WHERE exclude_brand=''"
    ):
        series.setdefault((node, ""), {})[day] = [score_sum, scored, documents]
        year = day[:4]
        if scored >= 1:
            coverage_acc[node][year][0] += 1
        if scored >= 14:
            coverage_acc[node][year][1] += 1
    for node, exclude, day, documents, scored, score_sum in con.execute(
        "SELECT node, exclude_brand, day, document_count, scored_count, score_sum FROM daily WHERE exclude_brand!=''"
    ):
        series.setdefault((node, exclude), {})[day] = [score_sum, scored, documents]
    con.close()

    def pack(node: str) -> dict:
        years = {}
        total = [0, 0]
        for year, pair in sorted(coverage_acc.get(node, {}).items()):
            years[year] = {"scored_days": pair[0], "dense_days": pair[1]}
            total[0] += pair[0]
            total[1] += pair[1]
        return {
            "present": node in coverage_acc,
            "scored_days": total[0],
            "dense_days": total[1],
            "clears_14_scored_days": total[0] >= 14,
            "clears_14_dense_days": total[1] >= 14,
            "by_year": years,
        }

    targets = positive_targets(graph, nodes)
    events = {}
    for eco in ARM_B:
        events[eco] = [day.isoformat() for day in detect_daily(series.get((eco, ""), {}))]

    def funnel(span: str) -> dict:
        rows = {}
        for eco in ARM_B:
            chosen = []
            for text in events[eco]:
                t0 = date.fromisoformat(text)
                if span == "overlap" and not (OVERLAP_START <= t0 <= OVERLAP_END):
                    continue
                chosen.append(t0)
            step_windows = 0
            step_after = 0
            by_target = {}
            for name in targets[eco]:
                by_target[name] = {"both_windows": 0, "after_comention": 0}
            for t0 in chosen:
                full = []
                kept = []
                for name in targets[eco]:
                    if both_windows(series.get((name, ""), {}), t0):
                        full.append(name)
                        by_target[name]["both_windows"] += 1
                    if both_windows(series.get((name, eco), {}), t0):
                        kept.append(name)
                        by_target[name]["after_comention"] += 1
                if full:
                    step_windows += 1
                if kept:
                    step_after += 1
            comp_events_with_window = 0
            comp_after = 0
            for t0 in chosen:
                full = [
                    name
                    for name in nodes["ecosystems"][eco]["competitor_nodes"]
                    if both_windows(series.get((name, ""), {}), t0)
                ]
                kept = [
                    name
                    for name in nodes["ecosystems"][eco]["competitor_nodes"]
                    if both_windows(series.get((name, eco), {}), t0)
                ]
                if full:
                    comp_events_with_window += 1
                if kept:
                    comp_after += 1
            rows[eco] = {
                "brand_events": len(chosen),
                "h4_event_minimum": 5,
                "brand_events_meet_h4_count": len(chosen) >= 5,
                "positive_targets": targets[eco],
                "positive_events_with_both_windows": step_windows,
                "positive_events_after_comention": step_after,
                "positive_by_target": by_target,
                "competitor_events_with_both_windows": comp_events_with_window,
                "competitor_events_after_comention": comp_after,
                "matched_pairs": None,
                "matched_pairs_blocked": "control pool is not in the extract",
            }
        return rows

    # Eligible placebo dates exist or not, without matching.
    placebo = {}
    for eco in ARM_B:
        series_eco = series.get((eco, ""), {})
        ev = [date.fromisoformat(text) for text in events[eco]]
        eligible = eligible_placebo_days(series_eco, ev)
        placebo[eco] = {"events": len(ev), "eligible_non_event_dates": len(eligible)}

    candidates = [
        name
        for name, spec in rule["nodes"].items()
        if spec.get("role") == "candidate_brand"
    ]
    payload = {
        "controls_in_extract": [row for row in control_rows if row["in_extract"]],
        "controls_missing": [row for row in control_rows if not row["in_extract"]],
        "coverage": {node: pack(node) for node in sorted(coverage_acc)},
        "candidate_order": candidates,
        "placebo_dates_without_controls": placebo,
        "planning_sd": "blocked",
        "funnel_full_span": funnel("full"),
        "funnel_overlap_2016-11-14_2020-12-31": funnel("overlap"),
        "arm_b_news": "NO-GO",
        "reason": "160 of the 184 control-pool names are absent. The 24 names present are the candidate brands and candidate competitors, and none is an information-technology or communication-services control. Matched pairs and the placebo SD are blocked.",
    }
    OUT.write_text(json.dumps(payload))
    print(
        "controls present",
        len(payload["controls_in_extract"]),
        "missing",
        len(payload["controls_missing"]),
        "nodes",
        len(payload["coverage"]),
    )
    for span_name in ("funnel_full_span", "funnel_overlap_2016-11-14_2020-12-31"):
        print(span_name)
        for eco, row in payload[span_name].items():
            print(
                eco,
                "events",
                row["brand_events"],
                "pos windows",
                row["positive_events_with_both_windows"],
                "pos after",
                row["positive_events_after_comention"],
                "comp windows",
                row["competitor_events_with_both_windows"],
                "comp after",
                row["competitor_events_after_comention"],
            )


if __name__ == "__main__":
    main()

"""Arm A counts for every ecosystem.

Counts only. No event shift is written. Planning SDs are proposed and
are not frozen. The 2026-10-23 audit made the joined text the main news
series and restricted every Arm A news series to pairs whose headline
or summary names the node. StockTwits stays the user label, unrestricted.
"""

from __future__ import annotations

import json
import math
import random
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from phase1_gates import abs_shift_daily, baseline, detect_daily, eligible_placebo_days, sample_sd  # noqa: E402
from phase2_build_series import accumulate, brands_mentioned, node_hits, patterns_from_universe, ticker_nodes  # noqa: E402
from phase2_feasibility import GRAPH, NODES, both_windows, pool_tickers  # noqa: E402
from phase2_gdelt_reserve_after import controls_for  # noqa: E402
from phase2_revised_recount import build_adj, passes, targets_for, ticker_row  # noqa: E402
from phase4_fnspid_headline_share import names_node, patterns  # noqa: E402
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer  # noqa: E402

HEADLINE = ROOT / "data" / "interim" / "phase3" / "fnspid_scores_headline" / "parts"
JOINED = ROOT / "data" / "interim" / "phase3" / "fnspid_scores" / "parts"
RAW = ROOT / "data" / "raw" / "fnspid" / "parts"
SERIES = ROOT / "data" / "interim" / "phase2" / "series.sqlite"
OUT = ROOT / "eval" / "results" / "phase4_arm_a_counts_both.json"
ECOSYSTEMS = tuple(NODES["ecosystems"])
Z975 = 1.959964
Z80 = 0.841621


def add(cell: dict, day: str, signed: float) -> None:
    got = cell.get(day)
    if got is None:
        got = [0.0, 0, 0]
        cell[day] = got
    got[0] += signed
    got[1] += 1
    got[2] += 1


def needed_names(pool: dict) -> set[str]:
    names = set(ECOSYSTEMS)
    for eco in ECOSYSTEMS:
        spec = NODES["ecosystems"][eco]
        names.update(spec["positive_nodes"])
        names.update(spec["competitor_nodes"])
        names.update(targets_for(eco)["positive"])
        names.update(targets_for(eco)["competitor"])
        names.update(pool_tickers(pool, spec["sector_bucket"]))
    return names


def named_pairs() -> set[tuple[str, str, str]]:
    """Score-part pairs whose headline or summary names that node."""
    named = patterns()
    fallback: dict = {}
    nodes_for: dict[tuple[str, str], set[str]] = {}
    for parts in (HEADLINE, JOINED):
        for path in sorted(parts.glob("*.jsonl")):
            with path.open() as handle:
                for line in handle:
                    row = json.loads(line)
                    nodes_for.setdefault((path.stem, str(row["row_id"])), set()).add(row["node"])
    keep: set[tuple[str, str, str]] = set()
    import pyarrow.parquet as pq

    for path in sorted(RAW.glob("*.parquet")):
        table = pq.ParquetFile(path)
        for batch in table.iter_batches(batch_size=4000, columns=["row_id", "headline", "summary"]):
            data = batch.to_pydict()
            for row_id, headline, summary in zip(data["row_id"], data["headline"], data["summary"]):
                nodes = nodes_for.get((path.stem, str(row_id)))
                if not nodes:
                    continue
                headline = headline or ""
                summary = summary or ""
                for node in nodes:
                    if names_node(headline, node, named, fallback) or names_node(summary, node, named, fallback):
                        keep.add((path.stem, str(row_id), node))
        print(f"named pairs {path.name} kept {len(keep)}", flush=True)
    return keep


def load_main(parts: Path, needed: set[str], keep: set[tuple[str, str, str]]) -> dict:
    brands = set(ECOSYSTEMS)
    brand_rows = {name: set() for name in brands}
    for path in sorted(parts.glob("*.jsonl")):
        with path.open() as handle:
            for line in handle:
                row = json.loads(line)
                if row["node"] in brands:
                    brand_rows[row["node"]].add(row["row_id"])
    series: dict[tuple[str, str], dict] = defaultdict(dict)
    for path in sorted(parts.glob("*.jsonl")):
        with path.open() as handle:
            for line in handle:
                row = json.loads(line)
                node = row["node"]
                if node not in needed:
                    continue
                if (path.stem, str(row["row_id"]), node) not in keep:
                    continue
                day = str(row["day"])[:10]
                signed = float(row["signed"])
                add(series[(node, "")], day, signed)
                for eco in ECOSYSTEMS:
                    if node == eco or row["row_id"] in brand_rows[eco]:
                        continue
                    add(series[(node, eco)], day, signed)
    return series


def load_vader_restricted(needed: set[str]) -> dict:
    """Same VADER news cells, kept only when the headline or summary names the node."""
    import pyarrow.parquet as pq

    alias_patterns, brand_patterns = patterns_from_universe()
    ticker_map = ticker_nodes()
    named = patterns()
    fallback: dict = {}
    analyzer = SentimentIntensityAnalyzer()
    series: dict = {}
    for path in sorted(RAW.glob("*.parquet")):
        table = pq.ParquetFile(path)
        for batch in table.iter_batches(batch_size=2000, columns=["day_utc", "ticker", "headline", "summary", "text"]):
            data = batch.to_pydict()
            for day, ticker, headline, summary, body in zip(
                data["day_utc"], data["ticker"], data["headline"], data["summary"], data["text"]
            ):
                if not day:
                    continue
                headline = headline or ""
                summary = summary or ""
                ticker = (ticker or "").strip().upper()
                present = {ticker} if ticker else set()
                blob = " ".join(part for part in (headline, summary, body or "") if part)
                hits = node_hits(ticker_map, present, blob, alias_patterns)
                kept = [
                    node
                    for node in hits
                    if node in needed
                    and (names_node(headline, node, named, fallback) or names_node(summary, node, named, fallback))
                ]
                if not kept:
                    continue
                score = float(analyzer.polarity_scores(headline)["compound"])
                brands = brands_mentioned(present, blob, brand_patterns)
                day_key = str(day)[:10]
                for node in kept:
                    accumulate(series, (node, ""), day_key, score)
                    for eco in ECOSYSTEMS:
                        if eco not in brands:
                            accumulate(series, (node, eco), day_key, score)
        print(f"restricted vader {path.name} cells {len(series)}", flush=True)
    return series


def load_saved(needed: set[str]) -> dict[str, dict]:
    con = sqlite3.connect(f"file:{SERIES}?mode=ro", uri=True)
    out = {"news_vader": defaultdict(dict), "social": defaultdict(dict)}
    names = {"news": "news_vader", "social": "social"}
    query = "SELECT source, node, exclude_brand, day, score_sum, scored, mentions FROM cell"
    for source, node, exclude, day, score_sum, scored, mentions in con.execute(query):
        if source not in names or node not in needed:
            continue
        out[names[source]][(node, exclude or "")][day] = [score_sum, scored, mentions]
    con.close()
    return out


def coverage(series: dict) -> dict:
    out = {}
    for eco in ECOSYSTEMS:
        cells = series.get((eco, ""), {})
        out[eco] = {
            "scored_days": sum(1 for cell in cells.values() if cell[1] >= 1),
            "dense_days": sum(1 for cell in cells.values() if cell[1] >= 14),
        }
    return out


def events_for(series: dict) -> dict:
    return {eco: len(detect_daily(series.get((eco, ""), {}))) for eco in ECOSYSTEMS}


def pair_counts(series: dict, adj: dict, pool: dict) -> dict:
    popularity = GRAPH["popularity_sitelinks"]
    rows = []
    for eco in ECOSYSTEMS:
        controls = controls_for(eco, adj, pool)
        classes = {"positive": 0, "competitor": 0}
        with_pair = {"positive": set(), "competitor": set()}
        events = detect_daily(series.get((eco, ""), {}))
        for t0 in events:
            for edge_class, names in targets_for(eco).items():
                for target in names:
                    pop = popularity.get(target)
                    treated_series = series.get((target, eco), {})
                    treated = baseline(treated_series, t0, 28, 14)
                    if pop is None or treated is None or not both_windows(treated_series, t0):
                        continue
                    for ticker in controls:
                        other_series = series.get((ticker, eco), {})
                        other = baseline(other_series, t0, 28, 14)
                        other_pop = (ticker_row(ticker).get("chosen") or {}).get("sitelinks")
                        if other is None or other_pop is None or not both_windows(other_series, t0):
                            continue
                        if passes(treated, other, pop, other_pop):
                            classes[edge_class] += 1
                            with_pair[edge_class].add(t0)
                            break
        rows.append(
            {
                "ecosystem": eco,
                "positive_pairs": classes["positive"],
                "competitor_pairs": classes["competitor"],
                "positive_events_with_a_pair": len(with_pair["positive"]),
                "competitor_events_with_a_pair": len(with_pair["competitor"]),
                "eligible_controls": len(controls),
            }
        )
    return {
        "by_ecosystem": rows,
        "positive_pairs": sum(row["positive_pairs"] for row in rows),
        "competitor_pairs": sum(row["competitor_pairs"] for row in rows),
        "positive_events_with_a_pair": sum(row["positive_events_with_a_pair"] for row in rows),
        "competitor_events_with_a_pair": sum(row["competitor_events_with_a_pair"] for row in rows),
    }


def proposed_sd(series: dict, source: str, adj: dict, pool: dict) -> dict:
    popularity = GRAPH["popularity_sitelinks"]
    rng = random.Random(3)
    diffs = []
    detail = []
    for eco in ECOSYSTEMS:
        controls = controls_for(eco, adj, pool)
        spec = NODES["ecosystems"][eco]
        brand = series.get((eco, ""), {})
        events = detect_daily(brand)
        eligible = eligible_placebo_days(brand, events)
        chosen = rng.sample(eligible, 20) if len(eligible) > 20 else list(eligible)
        matched = 0
        for t0 in chosen:
            for names in (spec["positive_nodes"], spec["competitor_nodes"]):
                for target in names:
                    pop = popularity.get(target)
                    treated_series = series.get((target, eco), {})
                    treated = baseline(treated_series, t0, 28, 14)
                    shift = abs_shift_daily(treated_series, t0)
                    if pop is None or treated is None or shift is None or not both_windows(treated_series, t0):
                        continue
                    best = None
                    for ticker in controls:
                        other_series = series.get((ticker, eco), {})
                        other = baseline(other_series, t0, 28, 14)
                        other_shift = abs_shift_daily(other_series, t0)
                        other_pop = (ticker_row(ticker).get("chosen") or {}).get("sitelinks")
                        if other is None or other_shift is None or other_pop is None or not both_windows(other_series, t0):
                            continue
                        if not passes(treated, other, pop, other_pop):
                            continue
                        dist = abs(treated[0] - other[0])
                        if best is None or dist < best[0]:
                            best = (dist, other_shift)
                    if best is None:
                        continue
                    diffs.append(shift - best[1])
                    matched += 1
        detail.append(
            {"ecosystem": eco, "eligible_dates": len(eligible), "dates_drawn": len(chosen), "placebo_pairs": matched}
        )
    sd = sample_sd(diffs)
    return {
        "status": "PROPOSED",
        "frozen": False,
        "source": source,
        "placebo_pairs": len(diffs),
        "sd": sd,
        "sesoi_0.05_in_sd_units": None if not sd else 0.05 / sd,
        "mean_caliper_0.20_in_sd_units": None if not sd else 0.20 / sd,
        "by_brand": detail,
        "frozen_arm_a_sd_unchanged": 0.10636804456181562,
    }


def events_needed(sd: float | None) -> dict:
    if not sd:
        return {"events_for_mde_0.10": None, "events_for_halfwidth_0.05": None}
    mde = ((Z975 + Z80) * sd / 0.10) ** 2
    half = (Z975 * sd / 0.05) ** 2
    return {
        "events_for_mde_0.10": math.ceil(mde - 1e-9),
        "events_for_halfwidth_0.05": math.ceil(half - 1e-9),
    }


def main() -> None:
    if not any(HEADLINE.glob("*.jsonl")):
        raise SystemExit("headline score parts are not written yet")
    pool = json.loads((ROOT / "configs" / "phase1_universe.json").read_text())["control_pool_by_bucket"]
    needed = needed_names(pool)
    print(f"ecosystems {len(ECOSYSTEMS)} needed {len(needed)}", flush=True)
    keep = named_pairs()
    print(f"restricted pairs {len(keep)}", flush=True)
    headline = load_main(HEADLINE, needed, keep)
    print(f"headline cells {len(headline)}", flush=True)
    joined = load_main(JOINED, needed, keep)
    print(f"joined cells {len(joined)}", flush=True)
    vader = load_vader_restricted(needed)
    print(f"vader cells {len(vader)}", flush=True)
    saved = load_saved(needed)
    adj = build_adj(True, True)
    bundle = {
        "news_headline": headline,
        "news_joined": joined,
        "news_vader": vader,
        "social": saved["social"],
    }
    planning = {source: proposed_sd(series, source, adj, pool) for source, series in bundle.items()}
    events = {source: events_for(series) for source, series in bundle.items()}
    precision = {}
    for source, block in planning.items():
        available = sum(events[source].values())
        precision[source] = {"available_events": available, "sd": block["sd"], **events_needed(block["sd"])}
    payload = {
        "counts_only": True,
        "event_shifts_computed": False,
        "main_series": "news_joined",
        "restriction": "headline or summary names the node, by name or by alias",
        "social_restricted": False,
        "ecosystems": list(ECOSYSTEMS),
        "sector_match": "information_technology_and_communication_services",
        "coverage": {source: coverage(series) for source, series in bundle.items()},
        "events": events,
        "matched_pairs": {source: pair_counts(series, adj, pool) for source, series in bundle.items()},
        "planning_sd": planning,
        "events_at_sd": precision,
        "mde_formula": "(1.959964 + 0.841621) * sd / sqrt(n)",
        "halfwidth_formula": "1.959964 * sd / sqrt(n)",
    }
    OUT.write_text(json.dumps(payload) + "\n")
    print(f"wrote {OUT}", flush=True)


if __name__ == "__main__":
    main()

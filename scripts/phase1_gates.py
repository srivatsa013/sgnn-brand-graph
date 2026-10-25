"""Phase 1 gate counts from the retained extracts.

Sentiment numbers here are planning proxies. News uses VADER compound
because FNSPID has no sentiment column. Social uses the user Bullish or
Bearish label. This script does not compute a spillover or a shift outcome
on a real event. The only shifts it computes are on placebo dates, and only
to re-estimate the planning standard deviation.
"""

from __future__ import annotations

import json
import math
import random
import re
import sqlite3
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
UNI = json.loads((ROOT / "configs" / "phase1_universe.json").read_text())
Z975 = 1.959964
Z80 = 0.841621
LN2 = 0.693147
OLD_SD = 0.20


def n_for_mde(sd: float) -> int:
    return math.ceil(((Z975 + Z80) * sd / 0.10) ** 2)


def n_for_half(sd: float) -> int:
    return math.ceil((Z975 * sd / 0.05) ** 2)


def mde(sd: float, n: int) -> float | None:
    if n <= 0:
        return None
    return (Z975 + Z80) * sd / math.sqrt(n)


def parse_day(value: str) -> date | None:
    if not value or len(value) < 10 or value[4] != "-" or value[7] != "-":
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def label_score(raw: str) -> float | None:
    text = (raw or "").strip().lower()
    if text in {"bullish", "1", "1.0"}:
        return 1.0
    if text in {"bearish", "-1", "-1.0"}:
        return -1.0
    return None


def add_obs(bucket: dict, key: str, day: str, score: float | None, mentions: int = 1) -> None:
    rec = bucket.get(key)
    if rec is None:
        rec = {}
        bucket[key] = rec
    cell = rec.get(day)
    if cell is None:
        cell = [0.0, 0, 0]  # score sum, scored docs, all docs
        rec[day] = cell
    cell[2] += mentions
    if score is not None:
        cell[0] += score
        cell[1] += 1


def inv3(m: list[list[float]]) -> list[list[float]] | None:
    a, b, c = m[0]
    d, e, f = m[1]
    g, h, i = m[2]
    A = e * i - f * h
    B = f * g - d * i
    C = d * h - e * g
    D = c * h - b * i
    E = a * i - c * g
    F = b * g - a * h
    G = b * f - c * e
    H = c * d - a * f
    I = a * e - b * d
    det = a * A + b * B + c * C
    if abs(det) < 1e-12:
        return None
    return [[A / det, D / det, G / det], [B / det, E / det, H / det], [C / det, F / det, I / det]]


def baseline(series: dict, t0: date, back: int, min_obs: int) -> tuple[float, float, float] | None:
    vals = []
    mentions = []
    for k in range(1, back + 1):
        cell = series.get((t0 - timedelta(days=k)).isoformat())
        if cell and cell[2] >= 1 and cell[1] >= 1:
            vals.append(cell[0] / cell[1])
            mentions.append(cell[1])
    if len(vals) < min_obs:
        return None
    mean = sum(vals) / len(vals)
    var = sum((v - mean) ** 2 for v in vals) / (len(vals) - 1)
    if var <= 0:
        return None
    return mean, math.sqrt(var), math.log1p(sum(mentions) / len(mentions))


def detect_daily(series: dict) -> list[date]:
    days = []
    for text, cell in series.items():
        parsed = parse_day(text)
        if parsed and cell[1] >= 5:
            days.append(parsed)
    days.sort()
    events = []
    last = None
    for t0 in days:
        if last is not None and (t0 - last).days < 8:
            continue
        stats = baseline(series, t0, 28, 14)
        if stats is None:
            continue
        mean, sd, _ = stats
        cell = series[t0.isoformat()]
        z = (cell[0] / cell[1] - mean) / sd
        if abs(z) >= 2:
            events.append(t0)
            last = t0
    return events


def week_key(day: date) -> tuple[int, int]:
    iso = day.isocalendar()
    return iso[0], iso[1]


def to_weekly(series: dict) -> dict:
    out: dict[str, list] = {}
    for text, cell in series.items():
        parsed = parse_day(text)
        if parsed is None:
            continue
        year, week = week_key(parsed)
        monday = date.fromisocalendar(year, week, 1).isoformat()
        acc = out.get(monday)
        if acc is None:
            acc = [0.0, 0, 0]
            out[monday] = acc
        acc[0] += cell[0]
        acc[1] += cell[1]
        acc[2] += cell[2]
    return out


def detect_weekly(series: dict) -> list[date]:
    weekly = to_weekly(series)
    mondays = sorted(parse_day(text) for text in weekly if weekly[text][1] >= 15)
    mondays = [day for day in mondays if day is not None]
    events = []
    last = None
    for t0 in mondays:
        if last is not None and (t0 - last).days < 14:
            continue
        vals = []
        for k in range(1, 5):
            cell = weekly.get((t0 - timedelta(days=7 * k)).isoformat())
            if cell and cell[1] >= 1:
                vals.append(cell[0] / cell[1])
        if len(vals) < 3:
            continue
        mean = sum(vals) / len(vals)
        var = sum((v - mean) ** 2 for v in vals) / (len(vals) - 1)
        if var <= 0:
            continue
        cell = weekly[t0.isoformat()]
        z = (cell[0] / cell[1] - mean) / math.sqrt(var)
        if abs(z) >= 2:
            events.append(t0)
            last = t0
    return events


def window_mean(series: dict, start: date, end: date, min_obs: int) -> float | None:
    vals = []
    day = start
    while day <= end:
        cell = series.get(day.isoformat())
        if cell and cell[1] >= 1:
            vals.append(cell[0] / cell[1])
        day += timedelta(days=1)
    if len(vals) < min_obs:
        return None
    return sum(vals) / len(vals)


def abs_shift_daily(series: dict, t0: date) -> float | None:
    pre = window_mean(series, t0 - timedelta(days=7), t0 - timedelta(days=1), 3)
    post = window_mean(series, t0, t0 + timedelta(days=7), 3)
    if pre is None or post is None:
        return None
    return abs(post - pre)


def eligible_placebo_days(series: dict, events: list[date]) -> list[date]:
    event_set = set(events)
    out = []
    for text, cell in series.items():
        t0 = parse_day(text)
        if t0 is None or cell[1] < 5 or t0 in event_set:
            continue
        if any(abs((t0 - ev).days) < 8 for ev in events):
            continue
        if baseline(series, t0, 28, 14) is None:
            continue
        if abs_shift_daily(series, t0) is None:
            continue
        out.append(t0)
    out.sort()
    return out


def ticker_bucket() -> dict[str, str]:
    out = {}
    for bucket, ticks in UNI["control_pool_by_bucket"].items():
        for ticker in ticks:
            out[ticker] = bucket
    for eco in UNI["ecosystems"].values():
        for ticker in eco["brand_tickers"] + eco["competitor_tickers"]:
            out[ticker] = eco["sector_bucket"]
    return out


def control_pool() -> dict[str, list[str]]:
    return {bucket: list(ticks) for bucket, ticks in UNI["control_pool_by_bucket"].items()}


def pair_differences(
    treated: dict,
    all_series: dict,
    buckets: dict[str, str],
    pool: dict[str, list[str]],
) -> tuple[list[float], dict]:
    """Paired |shift| differences for focal companies only.

    Controls stay in all_series so they can be matched. They are not
    treated units. A company with fewer than 5 eligible non-event dates
    is left out, matching the pre-registered placebo minimum.
    """
    rng = random.Random(3)
    diffs = []
    info = {
        "placebos": 0,
        "matched": 0,
        "unmatched": 0,
        "excluded_fewer_than_5_eligible_dates": [],
        "included": [],
        "distance": "mahalanobis_or_standardized_euclidean",
        "treated_units": "focal companies only; one-hop neighbors do not exist until Phase 2",
    }
    for ticker in sorted(treated):
        bucket = buckets.get(ticker)
        series = treated[ticker]
        if bucket is None or not series:
            info["excluded_fewer_than_5_eligible_dates"].append(ticker)
            continue
        events = detect_daily(series)
        eligible = eligible_placebo_days(series, events)
        if len(eligible) < 5:
            info["excluded_fewer_than_5_eligible_dates"].append(ticker)
            continue
        info["included"].append(ticker)
        if len(eligible) > 20:
            chosen = rng.sample(eligible, 20)
        else:
            chosen = eligible
        candidates = [c for c in pool.get(bucket, []) if c != ticker and c in all_series]
        for t0 in chosen:
            info["placebos"] += 1
            treated_shift = abs_shift_daily(series, t0)
            treated_base = baseline(series, t0, 28, 14)
            if treated_shift is None or treated_base is None:
                info["unmatched"] += 1
                continue
            passing = []
            for cand in candidates:
                other = all_series[cand]
                base = baseline(other, t0, 28, 14)
                shift = abs_shift_daily(other, t0)
                if base is None or shift is None:
                    continue
                if abs(treated_base[0] - base[0]) > 0.20:
                    continue
                ratio = treated_base[1] / base[1] if base[1] else 99
                if ratio < 0.5 or ratio > 2:
                    continue
                if abs(treated_base[2] - base[2]) > LN2:
                    continue
                passing.append((cand, base, shift))
            if not passing:
                info["unmatched"] += 1
                continue
            points = [row[1] for row in passing]
            means = [sum(p[i] for p in points) / len(points) for i in range(3)]
            sds = []
            for i in range(3):
                var = sum((p[i] - means[i]) ** 2 for p in points) / max(len(points) - 1, 1)
                sds.append(math.sqrt(var) if var > 0 else 1.0)
            inverse = None
            if len(points) >= 4:
                cov = [[0.0, 0.0, 0.0] for _ in range(3)]
                for p in points:
                    delta = [p[i] - means[i] for i in range(3)]
                    for r in range(3):
                        for c in range(3):
                            cov[r][c] += delta[r] * delta[c]
                scale = len(points) - 1
                cov = [[cov[r][c] / scale for c in range(3)] for r in range(3)]
                inverse = inv3(cov)
            best = None
            for _cand, base, shift in passing:
                delta = [treated_base[i] - base[i] for i in range(3)]
                if inverse is not None:
                    dist = 0.0
                    for r in range(3):
                        acc = sum(inverse[r][c] * delta[c] for c in range(3))
                        dist += delta[r] * acc
                else:
                    dist = sum((delta[i] / sds[i]) ** 2 for i in range(3))
                if best is None or dist < best[0]:
                    best = (dist, shift)
            diffs.append(treated_shift - best[1])
            info["matched"] += 1
    return diffs, info


def sample_sd(values: list[float]) -> float | None:
    if len(values) < 2:
        return None
    mean = sum(values) / len(values)
    return math.sqrt(sum((v - mean) ** 2 for v in values) / (len(values) - 1))


def load_news(scorer) -> tuple[dict, dict, dict]:
    parts = sorted((ROOT / "data" / "raw" / "fnspid" / "parts").glob("*.parquet"))
    if not parts:
        raise SystemExit("No FNSPID parquet parts. The stream has not written rows yet.")
    by_ticker: dict = {}
    alias_hits: dict = {}
    stats = {"rows": 0, "utc_suffix": 0, "scored": 0}
    patterns = alias_patterns()
    for path in parts:
        pf = pq.ParquetFile(path)
        for batch in pf.iter_batches(batch_size=2000):
            data = batch.to_pydict()
            n = len(data["ticker"])
            for i in range(n):
                stats["rows"] += 1
                day = data["day_utc"][i]
                ticker = data["ticker"][i]
                stamp = data["date_utc"][i] or ""
                if stamp.endswith("UTC"):
                    stats["utc_suffix"] += 1
                headline = data["headline"][i] or ""
                score = scorer(headline)
                stats["scored"] += 1
                add_obs(by_ticker, ticker, day, score)
                blob = " ".join(
                    part for part in (headline, data["summary"][i] or "", data["text"][i] or "") if part
                )
                for name, pattern in patterns:
                    if pattern.search(blob):
                        add_obs(alias_hits, name, day, score)
    return by_ticker, alias_hits, stats


def load_social() -> tuple[dict, dict, dict]:
    files = sorted((ROOT / "data" / "raw" / "stocktwits" / "features").glob("*.parquet"))
    bodies = sorted((ROOT / "data" / "raw" / "stocktwits" / "bodies").glob("*.parquet"))
    if not files or not bodies:
        raise SystemExit("StockTwits features or message bodies are missing.")
    by_ticker: dict = {}
    stats = {"feature_rows": 0, "zulu": 0, "labeled": 0}
    groups = {"ALPHABET": {"GOOG", "GOOGL"}, "META_NODE": {"FB", "META"}}
    for path in files:
        table = pq.read_table(path)
        ids = table.column("message_id").to_pylist()
        days = table.column("day_utc").to_pylist()
        created = table.column("created_at").to_pylist()
        sentiment = table.column("sentiment").to_pylist()
        tags = table.column("cashtags").to_pylist()
        for i, day in enumerate(days):
            if not day:
                continue
            stats["feature_rows"] += 1
            if isinstance(created[i], str) and created[i].endswith("Z"):
                stats["zulu"] += 1
            score = label_score(sentiment[i])
            if score is not None:
                stats["labeled"] += 1
            tickers = [t for t in (tags[i] or "").split("|") if t]
            present = set(tickers)
            for ticker in present:
                add_obs(by_ticker, ticker, day, score)
            for name, members in groups.items():
                if present & members:
                    add_obs(by_ticker, name, day, score)
        del ids
    alias_hits: dict = {}
    patterns = alias_patterns()
    db_path = ROOT / "data" / "interim" / "phase1" / "social_for_alias.sqlite"
    db = sqlite3.connect(db_path)
    db.execute("DROP TABLE IF EXISTS feat")
    db.execute("CREATE TABLE feat (message_id INTEGER PRIMARY KEY, day TEXT, score REAL)")
    batch: list[tuple] = []
    for path in files:
        table = pq.read_table(path, columns=["message_id", "day_utc", "sentiment"])
        for message_id, day, sentiment in zip(
            table.column("message_id").to_pylist(),
            table.column("day_utc").to_pylist(),
            table.column("sentiment").to_pylist(),
        ):
            score = label_score(sentiment)
            batch.append((message_id, day, score))
            if len(batch) >= 50000:
                db.executemany("INSERT OR REPLACE INTO feat VALUES (?,?,?)", batch)
                batch.clear()
    if batch:
        db.executemany("INSERT OR REPLACE INTO feat VALUES (?,?,?)", batch)
    db.commit()
    for path in bodies:
        table = pq.read_table(path, columns=["message_id", "message_body"])
        message_ids = table.column("message_id").to_pylist()
        if not message_ids:
            continue
        lo, hi = min(message_ids), max(message_ids)
        meta = {
            message_id: (day, score)
            for message_id, day, score in db.execute(
                "SELECT message_id, day, score FROM feat WHERE message_id BETWEEN ? AND ?",
                (lo, hi),
            )
        }
        for message_id, body in zip(message_ids, table.column("message_body").to_pylist()):
            day, score = meta.get(message_id, (None, None))
            if not day or not body:
                continue
            for name, pattern in patterns:
                if pattern.search(body):
                    add_obs(alias_hits, name, day, score)
        del meta
    db.close()
    stats["bodies"] = sum(pq.ParquetFile(path).metadata.num_rows for path in bodies)
    return by_ticker, alias_hits, stats


def alias_patterns() -> list[tuple[str, re.Pattern]]:
    out = []
    nodes = dict(UNI["alias_nodes"])
    for name, spec in UNI["descriptive_aliases_not_in_the_75_percent_set"].items():
        nodes[name] = {"aliases": spec}
    for name, spec in nodes.items():
        aliases = spec.get("aliases") or []
        if not aliases:
            continue
        parts = [r"\b" + re.escape(alias) + r"\b" for alias in aliases]
        out.append((name, re.compile("|".join(parts), re.IGNORECASE)))
    return out


def days_with(series: dict | None) -> int:
    if not series:
        return 0
    return sum(1 for cell in series.values() if cell[2] >= 1)


def combine(a: dict | None, b: dict | None) -> dict:
    out: dict = {}
    for source in (a or {}), (b or {}):
        for day, cell in source.items():
            acc = out.get(day)
            if acc is None:
                out[day] = list(cell)
            else:
                acc[0] += cell[0]
                acc[1] += cell[1]
                acc[2] += cell[2]
    return out


def node_series(name: str, news: dict, social: dict, news_alias: dict, social_alias: dict) -> tuple[dict, dict]:
    spec = UNI["alias_nodes"].get(name)
    if spec and spec.get("aliases"):
        return news_alias.get(name, {}), social_alias.get(name, {})
    if name == "Meta" or (spec and spec.get("aliases_are_tickers")):
        return combine(news.get("FB"), news.get("META")), social.get("META_NODE", {})
    if name == "Alphabet":
        return combine(news.get("GOOG"), news.get("GOOGL")), social.get("ALPHABET", {})
    return news.get(name, {}), social.get(name, {})


def ecosystem_report(news, social, news_alias, social_alias, sd: float) -> list[dict]:
    rows = []
    for name, eco in UNI["ecosystems"].items():
        if name == "Alphabet":
            news_brand, social_brand = node_series("Alphabet", news, social, news_alias, social_alias)
        else:
            ticker = eco["brand_tickers"][0]
            news_brand, social_brand = news.get(ticker, {}), social.get(ticker, {})
        news_events = detect_daily(news_brand)
        social_events = detect_daily(social_brand)
        news_weeks = detect_weekly(news_brand)
        social_weeks = detect_weekly(social_brand)
        others = []
        for node in eco["planned_other_nodes"]:
            nser, sser = node_series(node, news, social, news_alias, social_alias)
            nd, sdys = days_with(nser), days_with(sser)
            others.append(
                {
                    "node": node,
                    "news_days": nd,
                    "social_days": sdys,
                    "both": nd >= 14 and sdys >= 14,
                    "news_events_daily": len(detect_daily(nser)) if nser else 0,
                    "social_events_daily": len(detect_daily(sser)) if sser else 0,
                }
            )
        both = sum(1 for row in others if row["both"])
        coverage = both / len(others)
        brand_both = days_with(news_brand) >= 14 and days_with(social_brand) >= 14
        n_events = len(news_events) + len(social_events)
        n_week = len(news_weeks) + len(social_weeks)
        rows.append(
            {
                "ecosystem": name,
                "news_days": days_with(news_brand),
                "social_days": days_with(social_brand),
                "news_mentions": sum(cell[2] for cell in news_brand.values()),
                "social_mentions": sum(cell[2] for cell in social_brand.values()),
                "social_labeled": sum(cell[1] for cell in social_brand.values()),
                "events_daily_news": len(news_events),
                "events_daily_social": len(social_events),
                "events_daily": n_events,
                "events_weekly_news": len(news_weeks),
                "events_weekly_social": len(social_weeks),
                "events_weekly": n_week,
                "coverage_fraction": coverage,
                "coverage_pass": brand_both and coverage >= 0.75,
                "brand_both_sources": brand_both,
                "mde_daily": mde(sd, n_events),
                "mde_weekly": mde(sd, n_week),
                "power_pass_daily": mde(sd, n_events) is not None and mde(sd, n_events) <= 0.10,
                "power_pass_weekly": mde(sd, n_week) is not None and mde(sd, n_week) <= 0.10,
                "other_nodes": others,
            }
        )
    return rows


def self_test() -> None:
    assert n_for_mde(0.20) == 32
    assert n_for_half(0.20) == 62
    inverse = inv3([[2, 0, 0], [0, 3, 0], [0, 0, 4]])
    assert inverse is not None
    assert abs(inverse[0][0] - 0.5) < 1e-9
    assert abs(inverse[1][1] - (1 / 3)) < 1e-9
    series = {}
    start = date(2020, 1, 1)
    for i in range(40):
        day = (start + timedelta(days=i)).isoformat()
        series[day] = [0.2 if i % 2 == 0 else 0.0, 10, 10]
    series[(start + timedelta(days=35)).isoformat()] = [10.0, 10, 10]
    found = detect_daily(series)
    assert found == [start + timedelta(days=35)], found
    print("self-test ok", "mde32", round(mde(0.20, 32), 6), "half62", round(Z975 * 0.20 / math.sqrt(62), 6))


def main() -> None:
    if "--self-test" in sys.argv:
        self_test()
        return
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

    analyzer = SentimentIntensityAnalyzer()

    def score_headline(text: str) -> float:
        return float(analyzer.polarity_scores(text or "")["compound"])

    news, news_alias, news_stats = load_news(score_headline)
    social, social_alias, social_stats = load_social()
    buckets = ticker_bucket()
    pool = control_pool()
    realized = {}
    for bucket, tickers in pool.items():
        realized[bucket] = {
            "defined": len(tickers),
            "with_news_day": sum(1 for t in tickers if days_with(news.get(t)) >= 1),
            "with_social_day": sum(1 for t in tickers if days_with(social.get(t)) >= 1),
            "with_14_news_days": sum(1 for t in tickers if days_with(news.get(t)) >= 14),
            "with_14_social_days": sum(1 for t in tickers if days_with(social.get(t)) >= 14),
        }
    buckets["ALPHABET"] = "communication_services"
    news_treated = {
        "AAPL": news.get("AAPL", {}),
        "MSFT": news.get("MSFT", {}),
        "TSLA": news.get("TSLA", {}),
        "ALPHABET": combine(news.get("GOOG"), news.get("GOOGL")),
    }
    social_treated = {
        "AAPL": social.get("AAPL", {}),
        "MSFT": social.get("MSFT", {}),
        "TSLA": social.get("TSLA", {}),
        "ALPHABET": social.get("ALPHABET", {}),
    }
    news_diffs, news_info = pair_differences(news_treated, news, buckets, pool)
    social_diffs, social_info = pair_differences(social_treated, social, buckets, pool)
    pooled = news_diffs + social_diffs
    new_sd = sample_sd(pooled)
    summary = {
        "label": "planning proxy only",
        "news_scorer": "VADER compound on the headline. FNSPID has no sentiment column.",
        "social_scorer": "StockTwits user label, Bullish=+1, Bearish=-1. Unlabeled posts are not in the mean.",
        "old_planning_sd": OLD_SD,
        "old_min_events_mde_0_10": 32,
        "old_min_events_halfwidth_0_05": 62,
        "new_planning_sd": new_sd,
        "new_min_events_mde_0_10": n_for_mde(new_sd) if new_sd else None,
        "new_min_events_halfwidth_0_05": n_for_half(new_sd) if new_sd else None,
        "placebo_pairs": len(pooled),
        "news_placebo": news_info,
        "social_placebo": social_info,
        "news_stats": news_stats,
        "social_stats": social_stats,
        "control_pool_by_bucket": {k: len(v) for k, v in pool.items()},
        "control_pool_realized": realized,
        "descriptive_alias_days": {
            name: {
                "news": days_with(news_alias.get(name)),
                "social": days_with(social_alias.get(name)),
            }
            for name in UNI["descriptive_aliases_not_in_the_75_percent_set"]
        },
        "ecosystems": ecosystem_report(news, social, news_alias, social_alias, new_sd or OLD_SD),
        "placebo_match": "Same coarse bucket and the pre-registered calipers on baseline mean, baseline SD, and log mention volume. Popularity was not applied: Wikidata sitelinks are not in these files, so this SD is a three-covariate planning proxy. Distance is Mahalanobis when the 3x3 covariance inverts, and standardized Euclidean otherwise.",
        "h1_outcomes_computed": False,
    }
    out = ROOT / "eval" / "results" / "phase1_gate_summary.json"
    out.write_text(json.dumps(summary, indent=2))
    print(json.dumps({k: summary[k] for k in ("new_planning_sd", "placebo_pairs", "news_stats", "social_stats")}, indent=2))
    for row in summary["ecosystems"]:
        print(
            row["ecosystem"],
            "days",
            row["news_days"],
            row["social_days"],
            "events",
            row["events_daily"],
            "weekly",
            row["events_weekly"],
            "coverage",
            round(row["coverage_fraction"], 3),
            "mde",
            None if row["mde_daily"] is None else round(row["mde_daily"], 3),
        )


if __name__ == "__main__":
    main()

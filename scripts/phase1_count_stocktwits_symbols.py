"""Stream StockTwits symbol files and count candidate tickers.

Does not save post text. Reads the public S3 release of Li, Al Ansari,
and Kaufman (2025) and writes counts only.
"""

from __future__ import annotations

import csv
import io
import json
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

NS = {"s": "http://s3.amazonaws.com/doc/2006-03-01/"}
PREFIX = "dataset/v1/data/csv/symbols/"
BUCKET = "https://stocktwits-nyu.s3.amazonaws.com/"
WATCH = {
    "AAPL",
    "MSFT",
    "GOOG",
    "GOOGL",
    "TSLA",
    "SSNLF",
    "SMSN",
    "SSNGY",
}
OUT = Path(__file__).resolve().parents[1] / "eval" / "results"
WORKERS = 4


def list_keys() -> list[str]:
    keys: list[str] = []
    token = None
    while True:
        url = f"{BUCKET}?list-type=2&prefix={PREFIX}&max-keys=1000"
        if token:
            url += "&continuation-token=" + urllib.parse.quote(token, safe="")
        req = urllib.request.Request(url, headers={"User-Agent": "sgnn-csp-audit"})
        with urllib.request.urlopen(req, timeout=60) as response:
            root = ET.fromstring(response.read())
        for node in root.findall("s:Contents", NS):
            keys.append(node.find("s:Key", NS).text)
        if root.find("s:IsTruncated", NS).text != "true":
            return keys
        token = root.find("s:NextContinuationToken", NS).text


def count_file(key: str) -> dict:
    url = BUCKET + key
    req = urllib.request.Request(url, headers={"User-Agent": "sgnn-csp-audit"})
    mentions: Counter[tuple[str, str]] = Counter()
    labeled: Counter[tuple[str, str]] = Counter()
    rows = 0
    min_date = None
    max_date = None
    with urllib.request.urlopen(req, timeout=120) as response:
        text = io.TextIOWrapper(response, encoding="utf-8", newline="")
        reader = csv.DictReader(text)
        for row in reader:
            rows += 1
            raw_date = (row.get("created_at") or "")[:10]
            if len(raw_date) == 10 and raw_date[4] == "-" and raw_date[7] == "-":
                if min_date is None or raw_date < min_date:
                    min_date = raw_date
                if max_date is None or raw_date > max_date:
                    max_date = raw_date
            symbol = (row.get("symbol") or "").strip().upper()
            if symbol not in WATCH:
                continue
            key_pair = (symbol, raw_date)
            mentions[key_pair] += 1
            sentiment = (row.get("sentiment") or "").strip()
            if sentiment and sentiment.lower() not in {"nan", "none", "null"}:
                labeled[key_pair] += 1
    return {
        "key": key,
        "rows": rows,
        "min_date": min_date,
        "max_date": max_date,
        "mentions": {f"{s}|{d}": n for (s, d), n in mentions.items()},
        "labeled": {f"{s}|{d}": n for (s, d), n in labeled.items()},
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    keys = sorted(list_keys())
    print(f"files={len(keys)}", flush=True)
    merged_mentions: Counter[str] = Counter()
    merged_labeled: Counter[str] = Counter()
    total_rows = 0
    min_date = None
    max_date = None
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = {pool.submit(count_file, key): key for key in keys}
        done = 0
        for future in as_completed(futures):
            result = future.result()
            done += 1
            total_rows += result["rows"]
            merged_mentions.update(result["mentions"])
            merged_labeled.update(result["labeled"])
            if result["min_date"] and (min_date is None or result["min_date"] < min_date):
                min_date = result["min_date"]
            if result["max_date"] and (max_date is None or result["max_date"] > max_date):
                max_date = result["max_date"]
            print(
                f"done {done}/{len(keys)} {result['key']} rows={result['rows']} total_rows={total_rows}",
                flush=True,
            )
    daily_path = OUT / "phase1_stocktwits_ticker_daily.csv"
    with daily_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["symbol", "date", "symbol_rows", "rows_with_user_sentiment"])
        for pair in sorted(merged_mentions):
            symbol, date = pair.split("|", 1)
            writer.writerow([symbol, date, merged_mentions[pair], merged_labeled.get(pair, 0)])
    by_symbol = Counter()
    labeled_by_symbol = Counter()
    for pair, count in merged_mentions.items():
        by_symbol[pair.split("|", 1)[0]] += count
    for pair, count in merged_labeled.items():
        labeled_by_symbol[pair.split("|", 1)[0]] += count
    summary = {
        "source": "s3://stocktwits-nyu/dataset/v1/data/csv/symbols/",
        "files": len(keys),
        "symbol_rows": total_rows,
        "min_date": min_date,
        "max_date": max_date,
        "watch": sorted(WATCH),
        "symbol_rows_by_ticker": dict(by_symbol),
        "user_labeled_rows_by_ticker": dict(labeled_by_symbol),
        "date_field": "created_at first 10 characters; symbol_000.csv stores a calendar date with no clock or timezone",
    }
    summary_path = OUT / "phase1_stocktwits_ticker_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()

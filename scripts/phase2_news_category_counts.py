"""Mention counts on heegyu/news-category-dataset. No sentiment, no shifts.

One article counts once per node. The text is headline plus short_description.
CEO names count only inside the logged tenure windows.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "interim" / "news_category" / "data.json"
OUT = ROOT / "eval" / "results" / "phase2_news_category_counts.json"

# Bare Windows, Snap, HP, and Musk are not node aliases. They are tallied aside.
SIDE = ("bare Windows", "bare Snap", "bare HP", "bare GM", "bare Musk")


def wb(phrase: str, flags: int = re.IGNORECASE) -> re.Pattern:
    return re.compile(r"(?<![A-Za-z0-9])" + re.escape(phrase) + r"(?![A-Za-z0-9])", flags)


RULES: dict[str, list[re.Pattern]] = {
    "Apple": [wb("Apple", 0)],
    "Microsoft": [wb("Microsoft")],
    "Alphabet": [wb("Google"), wb("Alphabet")],
    "Tesla": [wb("Tesla")],
    "iPhone": [wb("iPhone"), wb("iPhones")],
    "MacBook": [wb("MacBook"), wb("MacBooks")],
    "Windows": [wb("Microsoft Windows"), wb("Windows 10"), wb("Windows 11"), wb("Windows 7"), wb("Windows 8")],
    "Azure": [wb("Microsoft Azure", 0), wb("Azure", 0)],
    "LinkedIn": [wb("LinkedIn")],
    "YouTube": [wb("YouTube")],
    "Android": [wb("Android")],
    "Model 3": [wb("Model 3", 0), wb("Model3", 0)],
    "Model S": [wb("Model S", 0), wb("ModelS", 0)],
    "DELL": [wb("Dell")],
    "HPQ": [wb("Hewlett-Packard"), wb("Hewlett Packard"), wb("HP Inc.", 0), wb("HP Inc", 0)],
    "LOGI": [wb("Logitech")],
    "Samsung": [wb("Samsung")],
    "ORCL": [wb("Oracle")],
    "CRM": [wb("Salesforce"), wb("Salesforce.com")],
    "IBM": [wb("IBM", 0)],
    "ADBE": [wb("Adobe")],
    "Meta": [wb("Facebook"), wb("Meta Platforms")],
    "AMZN": [wb("Amazon")],
    "SNAP": [wb("Snapchat"), wb("Snap Inc."), wb("Snap Inc")],
    "PINS": [wb("Pinterest")],
    "F": [wb("Ford")],
    "GM": [wb("General Motors")],
    "TM": [wb("Toyota")],
    "NIO": [wb("NIO", 0)],
    "Nike": [wb("Nike")],
    "Chipotle": [wb("Chipotle", 0)],
    "Lowe's": [wb("Lowe's"), wb("Lowes")],
    "T-Mobile US": [wb("T-Mobile"), wb("TMobile")],
    "New York Times Co": [wb("New York Times")],
    "Hershey": [wb("Hershey"), wb("Hershey's")],
    "Colgate-Palmolive": [wb("Colgate-Palmolive"), wb("Colgate")],
    "Mastercard": [wb("Mastercard"), wb("MasterCard", 0)],
    "Chevron": [wb("Chevron", 0)],
    "NextEra Energy": [wb("NextEra")],
    "John Deere": [wb("John Deere")],
    "Eli Lilly": [wb("Eli Lilly")],
}

CEO_PATTERNS = {
    "Apple CEO": [
        ("Steve Jobs", [wb("Steve Jobs")], "1997-09-01", "2011-08-23"),
        ("Tim Cook", [wb("Tim Cook"), wb("Timothy Cook")], "2011-08-24", "2026-08-31"),
    ],
    "Microsoft CEO": [
        ("Steve Ballmer", [wb("Steve Ballmer")], "2000-01-01", "2014-02-04"),
        ("Satya Nadella", [wb("Satya Nadella")], "2014-02-04", "9999-12-31"),
    ],
    "Alphabet CEO": [
        ("Eric Schmidt", [wb("Eric Schmidt")], "2001-08-01", "2011-04-08"),
        ("Larry Page", [wb("Larry Page")], "2011-04-04", "2019-12-03"),
        ("Sundar Pichai", [wb("Sundar Pichai")], "2015-08-10", "9999-12-31"),
    ],
    "Tesla CEO": [
        ("Elon Musk", [wb("Elon Musk")], "2008-10-01", "9999-12-31"),
    ],
}

SIDE_PATTERNS = {
    "bare Windows": wb("Windows"),
    "bare Snap": wb("Snap", 0),
    "bare HP": wb("HP", 0),
    "bare GM": wb("GM", 0),
    "bare Musk": wb("Musk"),
}

APPLE_FOOD = re.compile(
    r"\b(?:fiona\s+apple|big\s+apple|apple\s+(?:pie|pies|cider|juice|sauce|sauces|orchard|tree|trees|fritter|fritters|crisp|tart|tarts|butter|seed|seeds|core|turnover|cobbler|strudel))\b",
    re.I,
)
APPLE_CO = re.compile(r"\b(?:iphone|ipad|macbook|ios|ipod|tim cook|app store|apple inc)\b", re.I)
AMAZON_FOREST = re.compile(r"\b(?:rainforest|rain forest|amazon river|amazon basin|amazon jungle|deforestation|tributary)\b", re.I)
AMAZON_CO = re.compile(r"\b(?:bezos|kindle|prime|aws|warehouse|alexa|amazon\.com)\b", re.I)
TESLA_SCI = re.compile(r"\b(?:nikola tesla|tesla coil)\b", re.I)
TESLA_CO = re.compile(r"\b(?:elon|motors|model [3sy])\b", re.I)
FORD_PERSON = re.compile(r"\b(?:gerald|harrison|betty|tom|john|glenn|whitey|francis|robert|christine)\s+ford\b", re.I)
FORD_OTHER = re.compile(r"\bford foundation\b", re.I)
FORD_CO = re.compile(r"\b(?:ford motor|f-150|mustang|henry ford)\b", re.I)
ORACLE_MYTH = re.compile(r"\b(?:delphi|prophecy|prophet|oracle bones)\b", re.I)
ORACLE_CO = re.compile(r"\b(?:ellison|database|oracle corp)\b", re.I)
ADOBE_CLAY = re.compile(r"\b(?:adobe\s+(?:brick|house|houses|home|homes|wall|walls)|mud-brick)\b", re.I)
NIKE_MYTH = re.compile(r"\b(?:goddess|samothrace|winged nike|victory of samothrace)\b", re.I)
ALPHABET_LETTERS = re.compile(r"\b(?:the alphabet|an alphabet|alphabet song|phonetic alphabet|alphabet soup)\b", re.I)
ALPHABET_CO = re.compile(r"\b(?:alphabet inc|google)\b", re.I)
CHEVRON_SHAPE = re.compile(r"\bchevron\s+(?:pattern|patterns|stripe|stripes|print|skirt|markings)\b", re.I)
COLGATE_SCHOOL = re.compile(r"\bcolgate university\b", re.I)
AZURE_OTHER = re.compile(r"\b(?:bentley|azure sky|azure blue|blue azure)\b", re.I)
DELL_PERSON = re.compile(r"\b(?:gerald|harrison|betty|tom|john|glenn)\s+dell\b", re.I)


def any_hit(patterns: list[re.Pattern], text: str) -> bool:
    return any(pattern.search(text) for pattern in patterns)


def keep(node: str, text: str) -> bool:
    if not any_hit(RULES[node], text):
        return False
    if node == "Apple":
        return not (APPLE_FOOD.search(text) and not APPLE_CO.search(text))
    if node == "AMZN":
        return not (AMAZON_FOREST.search(text) and not AMAZON_CO.search(text))
    if node == "Tesla":
        return not (TESLA_SCI.search(text) and not TESLA_CO.search(text))
    if node == "F":
        person = FORD_PERSON.search(text) or FORD_OTHER.search(text)
        return not (person and not FORD_CO.search(text))
    if node == "ORCL":
        return not (ORACLE_MYTH.search(text) and not ORACLE_CO.search(text))
    if node == "ADBE":
        return not ADOBE_CLAY.search(text)
    if node == "Nike":
        return not NIKE_MYTH.search(text)
    if node == "Alphabet" and ALPHABET_LETTERS.search(text) and not ALPHABET_CO.search(text):
        return False
    if node == "Chevron":
        return not CHEVRON_SHAPE.search(text)
    if node == "Colgate-Palmolive":
        return not (COLGATE_SCHOOL.search(text) and "Palmolive" not in text and "toothpaste" not in text.lower())
    if node == "Azure":
        return not (AZURE_OTHER.search(text) and "Microsoft" not in text)
    if node == "DELL":
        return not DELL_PERSON.search(text)
    return True


def ceo_keep(node: str, text: str, day: str) -> bool:
    for _person, patterns, start, end in CEO_PATTERNS[node]:
        if start <= day <= end and any_hit(patterns, text):
            return True
    return False


def main() -> None:
    daily: dict[str, Counter] = defaultdict(Counter)
    yearly: dict[str, Counter] = defaultdict(Counter)
    examples: dict[str, list[str]] = defaultdict(list)
    rejected = Counter()
    categories = Counter()
    brand_categories = Counter()
    rows = 0
    corpus_dates: set[str] = set()
    brand_items = 0
    any_items = 0
    study_brands = {"Apple", "Microsoft", "Alphabet", "Tesla"}
    nodes = list(RULES) + list(CEO_PATTERNS)
    min_day = "9999-99-99"
    max_day = "0000-00-00"

    with SRC.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            rows += 1
            day = (row.get("date") or "")[:10]
            if len(day) != 10:
                continue
            headline = row.get("headline") or ""
            desc = row.get("short_description") or ""
            text = f"{headline} {desc}"
            corpus_dates.add(day)
            if day < min_day:
                min_day = day
            if day > max_day:
                max_day = day
            matched = []
            for node in RULES:
                raw = any_hit(RULES[node], text)
                if raw and not keep(node, text):
                    rejected[node] += 1
                    continue
                if raw and keep(node, text):
                    matched.append(node)
            for node in CEO_PATTERNS:
                if ceo_keep(node, text, day):
                    matched.append(node)
            for name, pattern in SIDE_PATTERNS.items():
                if pattern.search(text):
                    # Bare Snapchat contains no bare "Snap" as a whole word.
                    # Bare Windows still fires inside "Windows 10"; those are real OS hits
                    # and are removed below so the side tally is the leftover.
                    daily[name][day] += 1
            if "Windows" in matched:
                daily["bare Windows"][day] -= 1
            if "SNAP" in matched and SIDE_PATTERNS["bare Snap"].search(text):
                daily["bare Snap"][day] -= 1
            if "Tesla CEO" in matched:
                daily["bare Musk"][day] -= 1
            for node in matched:
                daily[node][day] += 1
                yearly[node][day[:4]] += 1
                if len(examples[node]) < 2:
                    examples[node].append(headline[:180])
            if matched:
                any_items += 1
                categories[row.get("category") or ""] += 1
            if study_brands & set(matched):
                brand_items += 1
                brand_categories[row.get("category") or ""] += 1

    start = date.fromisoformat(min_day)
    end = date.fromisoformat(max_day)
    span_days = (end - start).days + 1
    period_start = date(2012, 1, 1)
    period_end = date(2017, 12, 31)
    period_n = (period_end - period_start).days + 1

    def baseline_pass(counts: Counter) -> bool:
        arr = [0] * period_n
        for text, n in counts.items():
            if n < 1:
                continue
            current = date.fromisoformat(text)
            if period_start <= current <= period_end:
                arr[(current - period_start).days] = 1
        window = sum(arr[:28])
        if window >= 14:
            return True
        for i in range(28, period_n):
            window += arr[i] - arr[i - 28]
            if window >= 14:
                return True
        return False

    def floor_days(counts: Counter, lo: str, hi: str) -> dict:
        ge5 = 0
        ge5_with_baseline = 0
        for text, n in counts.items():
            if not (lo <= text <= hi) or n < 5:
                continue
            ge5 += 1
            current = date.fromisoformat(text)
            observed = 0
            for k in range(1, 29):
                prior = (current - timedelta(days=k)).isoformat()
                if counts.get(prior, 0) >= 1:
                    observed += 1
            if observed >= 14:
                ge5_with_baseline += 1
        return {"days_with_5": ge5, "days_with_5_and_14_of_28": ge5_with_baseline}

    table = {}
    pass_count = 0
    floor_2012 = {"days_with_5": 0, "days_with_5_and_14_of_28": 0}
    floor_all = {"days_with_5": 0, "days_with_5_and_14_of_28": 0}
    for node in nodes:
        counts = daily[node]
        mention_days = sum(1 for n in counts.values() if n >= 1)
        days_3 = sum(1 for n in counts.values() if n >= 3)
        days_5 = sum(1 for n in counts.values() if n >= 5)
        busiest = max(counts.items(), key=lambda item: item[1]) if counts else ("", 0)
        passed = baseline_pass(counts)
        pass_count += int(passed)
        part_2012 = floor_days(counts, "2012-01-01", "2017-12-31")
        part_all = floor_days(counts, min_day, max_day)
        for key in floor_2012:
            floor_2012[key] += part_2012[key]
            floor_all[key] += part_all[key]
        table[node] = {
            "total_mentions": sum(counts.values()),
            "by_year": dict(sorted(yearly[node].items())),
            "mention_days": mention_days,
            "share_of_calendar_days": mention_days / span_days,
            "days_with_3": days_3,
            "days_with_5": days_5,
            "busiest_day": busiest[0],
            "busiest_count": busiest[1],
            "passes_14_of_28_in_2012_2017": passed,
            "floor_2012_2017": part_2012,
            "examples": examples[node],
        }

    side = {}
    for name in SIDE:
        counts = daily[name]
        positive = {day: n for day, n in counts.items() if n > 0}
        side[name] = {
            "articles": sum(positive.values()),
            "days": len(positive),
        }

    payload = {
        "source": "heegyu/news-category-dataset",
        "license": "CC BY 4.0",
        "file": str(SRC.relative_to(ROOT)),
        "rows": rows,
        "first_date": min_day,
        "last_date": max_day,
        "calendar_days": span_days,
        "distinct_publication_dates": len(corpus_dates),
        "nodes_passing_14_of_28_in_2012_2017": pass_count,
        "mention_floor_node_days_2012_2017": floor_2012,
        "mention_floor_node_days_full_span": floor_all,
        "hand_label_items_any_tracked_node": any_items,
        "hand_label_items_four_study_brands": brand_items,
        "hand_label_categories_any_node": categories.most_common(),
        "hand_label_categories_four_brands": brand_categories.most_common(),
        "rejected_ambiguous": dict(rejected),
        "side_tallies_not_assigned": side,
        "nodes": table,
    }
    OUT.write_text(json.dumps(payload, indent=2))
    print(
        "rows",
        rows,
        "span",
        min_day,
        max_day,
        "pass",
        pass_count,
        "floor",
        floor_2012,
        "brand_items",
        brand_items,
        "any",
        any_items,
    )


if __name__ == "__main__":
    main()

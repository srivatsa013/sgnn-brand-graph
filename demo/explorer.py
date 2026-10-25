"""superseded by site/

Streamlit explorer. Reads study files. Writes nothing.

Every displayed number is a Labeled value. Rendering a bare number raises.
"""

from __future__ import annotations

import json
import math
import random
from datetime import date
from pathlib import Path

import pyarrow.parquet as pq

from guard import ROOT
from real_graph import load_graph

MODES = ("REAL measured", "MODEL prediction", "AUGMENTED/SYNTHETIC")
SESOI = 0.05
LABELS = ROOT / "eval" / "results" / "phase5_label_table.parquet"
MODELS = ROOT / "eval" / "results" / "phase5_models"
PHASE0 = ROOT / "configs" / "phase0.json"


class Labeled:
    def __init__(self, mode: str, value):
        if mode not in MODES:
            raise ValueError("figure has no mode label")
        self.mode = mode
        self.value = value

    def text(self) -> str:
        return f"{self.mode}: {self.value}"


def figure(mode: str, title: str, rows: list[dict]) -> dict:
    if mode not in MODES:
        raise ValueError("figure has no mode label")
    for row in rows:
        for value in row.values():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                raise ValueError("figure has a number without a mode label")
    return {"mode": mode, "title": f"{mode}: {title}", "rows": rows}


def render_value(item) -> str:
    if not isinstance(item, Labeled):
        raise RuntimeError("figure rendered a number without a mode label")
    return item.text()


def _percentile(values: list[float], p: float) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = p * (len(ordered) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def bootstrap_interval(values: list[float], draws: int = 1000, seed: int = 0) -> tuple[float, float]:
    rng = random.Random(seed)
    stats = []
    n = len(values)
    for _ in range(draws):
        sample = [values[rng.randrange(n)] for _ in range(n)]
        stats.append(sum(sample) / n)
    stats.sort()
    return _percentile(stats, 0.025), _percentile(stats, 0.975)


def real_rows(brand: str) -> list[dict]:
    """Measured shifts from the Phase 5 label table. The interval is a demo bootstrap, not a Holm test."""
    grouped: dict[str, list[float]] = {}
    classes: dict[str, str] = {}
    signs: dict[str, int] = {}
    for item in pq.read_table(LABELS).to_pylist():
        if item["source"] != "news_joined" or item["ecosystem"] != brand:
            continue
        grouped.setdefault(item["neighbor"], []).append(float(item["shift"]))
        classes[item["neighbor"]] = item["edge_class"]
        signs[item["neighbor"]] = int(item["edge_sign"])
    rows = []
    mode = "REAL measured"
    for neighbor, shifts in sorted(grouped.items()):
        mean = sum(shifts) / len(shifts)
        low, high = bootstrap_interval(shifts)
        note = ""
        if low <= 0 <= high:
            note = "The interval includes zero."
        if low >= -SESOI and high <= SESOI:
            note = (note + " " if note else "") + "The interval lies inside the SESOI band."
        rows.append(
            {
                "neighbor": neighbor,
                "direction": Labeled(mode, "positive" if signs[neighbor] > 0 else "competitor" if signs[neighbor] < 0 else classes[neighbor]),
                "shift": Labeled(mode, mean),
                "interval": Labeled(mode, f"[{low:.6g}, {high:.6g}]"),
                "pair_count": Labeled(mode, len(shifts)),
                "note": Labeled(mode, note or "none"),
            }
        )
    return rows


def frozen_sd(source: str) -> float:
    cfg = json.loads(PHASE0.read_text())
    key = {"news_joined": "news_joined_restricted", "social": "social", "gdelt": "arm_b_gdelt", "tweetskb": "arm_b_tweetskb"}[source]
    for row in reversed(cfg["amendments"]):
        block = row.get(key)
        if isinstance(block, dict) and block.get("status") == "FROZEN":
            return float(block["sd"])
    raise RuntimeError(source)


def synthetic_rows(brand: str, lam: float) -> list[dict]:
    graph = load_graph()
    mode = "AUGMENTED/SYNTHETIC"
    sd = frozen_sd("news_joined")
    rows = []
    for edge in graph["positive_edges"]:
        if edge["src"] != brand and edge["dst"] != brand:
            continue
        other = edge["dst"] if edge["src"] == brand else edge["src"]
        planted = lam * sd * 1.0
        rows.append(
            {
                "neighbor": other,
                "direction": Labeled(mode, "positive"),
                "shift": Labeled(mode, planted),
                "lambda": Labeled(mode, lam),
            }
        )
    for edge in graph["competitor_edges"]:
        if edge["src"] != brand:
            continue
        planted = lam * sd * -1.0
        rows.append(
            {
                "neighbor": edge["dst"],
                "direction": Labeled(mode, "competitor"),
                "shift": Labeled(mode, planted),
                "lambda": Labeled(mode, lam),
            }
        )
    return rows


def model_rows(brand: str) -> list[dict]:
    """Mean test-fold prediction of the saved Phase 5 joined-news model, seed 0."""
    import sys

    import torch

    sys.path.insert(0, str(ROOT / "scripts"))
    from phase5_model import SignedMP, apply_scaler  # noqa: E402
    from phase5_train import day_folds  # noqa: E402

    path = MODELS / "news_joined_seed0.pt"
    if not path.exists():
        raise FileNotFoundError(path)
    saved = torch.load(path, weights_only=False)
    events = torch.load(ROOT / "eval" / "results" / "phase5_events.pt", weights_only=False)["news_joined"]
    packed = [row["event"] for row in events if row["ecosystem"] == brand]
    _train, _val, test, _info = day_folds([row["event"] for row in events])
    test_ids = {event.event_id for event in test}
    config = saved["config"]
    model = SignedMP(33, config["hidden"], config["depth"], config["dropout"], "signed")
    model.load_state_dict(saved["state"])
    model.eval()
    totals: dict[str, list[float]] = {}
    mode = "MODEL prediction"
    with torch.no_grad():
        for row in events:
            event = row["event"]
            if event.event_id not in test_ids or row["ecosystem"] != brand:
                continue
            pred, _channels = model.predict(apply_scaler(event, saved["mean"], saved["std"]), event.edges)
            names = row["names"]
            for index, name in enumerate(names):
                if name == brand or index not in event.labels:
                    continue
                totals.setdefault(name, []).append(float(pred[index]))
    rows = []
    for name, values in sorted(totals.items()):
        rows.append(
            {
                "neighbor": name,
                "direction": Labeled(mode, "predicted shift"),
                "shift": Labeled(mode, sum(values) / len(values)),
                "pair_count": Labeled(mode, len(values)),
            }
        )
    _ = packed
    return rows


def news_hits(mode: str, brand: str, lam: float = 1.0) -> dict:
    if mode == "REAL measured":
        rows = real_rows(brand)
    elif mode == "MODEL prediction":
        rows = model_rows(brand)
    elif mode == "AUGMENTED/SYNTHETIC":
        rows = synthetic_rows(brand, lam)
    else:
        raise ValueError("figure has no mode label")
    return figure(mode, f"news hits this brand: {brand}", rows)


def app() -> None:
    import streamlit as st

    st.set_page_config(page_title="AUGMENTED explorer", layout="wide")
    graph = load_graph()
    st.title("REAL MODEL AUGMENTED/SYNTHETIC")
    mode = st.radio("Mode", MODES)
    brand = st.selectbox("Brand", list(graph["ecosystems"]))
    lam = 1.0
    if mode == "AUGMENTED/SYNTHETIC":
        lam = st.slider("lambda", 0.0, 2.0, 1.0, 0.25)
    st.subheader(f"{mode}: signed edges")
    edges = []
    for edge in graph["positive_edges"]:
        if edge["src"] == brand or edge["dst"] == brand:
            edges.append({"from": edge["src"], "to": edge["dst"], "sign": Labeled(mode, edge["sign"])})
    for edge in graph["competitor_edges"]:
        if edge["src"] == brand or edge["dst"] == brand:
            edges.append({"from": edge["src"], "to": edge["dst"], "sign": Labeled(mode, edge["sign"])})
    st.table([{"from": row["from"], "to": row["to"], "sign": render_value(row["sign"])} for row in edges])
    spec = news_hits(mode, brand, lam)
    st.subheader(spec["title"])
    table = []
    for row in spec["rows"]:
        shown = {}
        for key, value in row.items():
            shown[key] = render_value(value) if isinstance(value, Labeled) else value
        table.append(shown)
    st.table(table)
    st.caption(f"{mode}: {date.today().isoformat()}. This page writes nothing.")


if __name__ == "__main__":
    app()

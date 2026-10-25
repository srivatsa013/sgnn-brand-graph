"""Phase 5 signed message passing on synthetic events.

This module does not read a study file, a score, or a hand label.
Real training stays outside this file until the collection jobs are
finished, free disk is at least 6 GB, and a go-ahead is given.
"""

from __future__ import annotations

import copy
import math
from dataclasses import dataclass, field

import torch
import torch.nn as nn

torch.set_num_threads(4)

VARIANTS = (
    "signed",
    "undirected",
    "mean_neighbors",
    "no_sign",
    "no_direction",
    "no_comention",
    "unsigned",
    "no_graph",
)


@dataclass
class Edge:
    src: int
    dst: int
    kind: str
    sign: float
    weight: float = 1.0


@dataclass
class Event:
    event_id: str
    t0: int
    features: torch.Tensor
    edges: list[Edge]
    labels: dict[int, float]
    comention_times: list[int] = field(default_factory=list)
    history_times: list[int] = field(default_factory=list)
    feature_doc_ids: set[str] = field(default_factory=set)
    label_doc_ids: set[str] = field(default_factory=set)


def chronological_split(events: list[Event]) -> dict:
    ordered = sorted(events, key=lambda event: (event.t0, event.event_id))
    n = len(ordered)
    if n >= 15:
        cut1 = n * 60 // 100
        cut2 = n * 80 // 100
        return {
            "mode": "chronological_60_20_20",
            "train": ordered[:cut1],
            "val": ordered[cut1:cut2],
            "test": ordered[cut2:],
        }
    splits = []
    for index, held in enumerate(ordered):
        rest = ordered[:index] + ordered[index + 1 :]
        n_val = max(1, math.ceil(len(rest) * 0.2)) if rest else 0
        val = rest[-n_val:] if n_val else []
        train = rest[:-n_val] if n_val else []
        splits.append({"train": train, "val": val, "test": [held]})
    return {"mode": "leave_one_event_out", "splits": splits}


def leakage_failures(train: list[Event], val: list[Event], test: list[Event], loss_ids: set[str], scaler_ids: set[str]) -> list[str]:
    """The six checks in reports/gnn_task_spec.md section 7."""
    failures = []
    for event in list(train) + list(val) + list(test):
        if any(ts > event.t0 - 8 for ts in event.comention_times):
            failures.append(f"comention {event.event_id}")
        if any(ts > event.t0 - 1 for ts in event.history_times):
            failures.append(f"history {event.event_id}")
        if event.feature_doc_ids & event.label_doc_ids:
            failures.append(f"label_document {event.event_id}")
    if train and test and max(event.t0 for event in train) >= min(event.t0 for event in test):
        failures.append("chronological")
    test_ids = {event.event_id for event in test}
    val_ids = {event.event_id for event in val}
    if loss_ids & test_ids:
        failures.append("loss")
    if scaler_ids & (test_ids | val_ids):
        failures.append("scaler")
    return failures


def _scale_stats(events: list[Event]) -> tuple[torch.Tensor, torch.Tensor]:
    stacked = torch.cat([event.features.detach() for event in events], dim=0)
    mean = stacked.mean(dim=0)
    var = stacked.var(dim=0, unbiased=False)
    return mean, torch.sqrt(var.clamp(min=1e-8))


def apply_scaler(event: Event, mean: torch.Tensor, std: torch.Tensor) -> torch.Tensor:
    return (event.features - mean) / std


class SignedMP(nn.Module):
    def __init__(self, in_dim: int, hidden: int, depth: int, dropout: float, variant: str = "signed"):
        super().__init__()
        if variant not in VARIANTS:
            raise ValueError(variant)
        if depth not in (1, 2):
            raise ValueError(depth)
        self.variant = variant
        self.depth = depth
        self.drop = nn.Dropout(dropout)
        self.w_pos = nn.Linear(in_dim, hidden, bias=False)
        self.w_in = nn.Linear(in_dim, hidden, bias=False)
        self.w_out = nn.Linear(in_dim, hidden, bias=False)
        self.w_comp = nn.Linear(in_dim, hidden, bias=False)
        self.w_co = nn.Linear(in_dim, hidden, bias=False)
        self.w_unsigned = nn.Linear(in_dim, hidden, bias=False)
        self.w_self = nn.Linear(in_dim, hidden, bias=False)
        self.w_pos_2 = nn.Linear(hidden, hidden, bias=False)
        self.w_neg_2 = nn.Linear(hidden, hidden, bias=False)
        self.w_co_2 = nn.Linear(hidden, hidden, bias=False)
        head_in = hidden * (3 if depth == 1 else 3)
        self.head = nn.Linear(head_in, 1)

    def _messages(self, edge: Edge) -> list[tuple[str, nn.Linear, int, int, float]]:
        """One stored arc. A competitor arc sends an in-message and an out-message."""
        if edge.kind == "co":
            if self.variant == "no_comention":
                return []
            return [("comention", self.w_co, edge.dst, edge.src, edge.weight)]
        if edge.kind != "struct":
            return []
        if self.variant == "unsigned":
            return [
                ("positive", self.w_unsigned, edge.dst, edge.src, 1.0),
                ("positive", self.w_unsigned, edge.src, edge.dst, 1.0),
            ]
        if self.variant == "undirected":
            return [
                ("negative", self.w_comp, edge.dst, edge.src, 1.0),
                ("negative", self.w_comp, edge.src, edge.dst, 1.0),
            ]
        if self.variant == "no_direction":
            return [("negative", self.w_comp, edge.dst, edge.src, 1.0)]
        if self.variant == "no_sign":
            return [
                ("positive", self.w_in, edge.dst, edge.src, 1.0),
                ("positive", self.w_out, edge.src, edge.dst, 1.0),
            ]
        if edge.sign < 0:
            return [
                ("negative", self.w_in, edge.dst, edge.src, 1.0),
                ("negative", self.w_out, edge.src, edge.dst, 1.0),
            ]
        return [("positive", self.w_pos, edge.dst, edge.src, 1.0)]

    def channel_tensors(self, features: torch.Tensor, edges: list[Edge], zero_sources: set[int] | None = None) -> dict[str, torch.Tensor]:
        n = features.shape[0]
        hidden = self.w_self.out_features
        zero_sources = zero_sources or set()
        grouped: dict[tuple[str, nn.Linear], list[tuple[int, int, float]]] = {}
        if self.variant != "no_graph":
            for edge in edges:
                if edge.src in zero_sources:
                    continue
                for channel, matrix, dst, src, weight in self._messages(edge):
                    grouped.setdefault((channel, matrix), []).append((dst, src, weight))
        totals = {}
        counts = {}
        for (channel, matrix), items in grouped.items():
            transformed = matrix(features)
            dst = torch.tensor([item[0] for item in items], dtype=torch.long)
            src = torch.tensor([item[1] for item in items], dtype=torch.long)
            weight = torch.tensor([item[2] for item in items], dtype=features.dtype).unsqueeze(1)
            messages = transformed[src] * weight
            total = torch.zeros(n, hidden, dtype=features.dtype).index_add(0, dst, messages)
            count = torch.zeros(n, 1, dtype=features.dtype).index_add(0, dst, weight.abs())
            totals[channel] = totals.get(channel, 0) + total
            counts[channel] = counts.get(channel, 0) + count
        self_h = self.w_self(features)
        out = {}
        for name in ("positive", "negative", "comention"):
            total = totals.get(name, torch.zeros(n, hidden, dtype=features.dtype))
            count = counts.get(name, torch.zeros(n, 1, dtype=features.dtype))
            mean = torch.where(count > 0, total / count.clamp(min=1.0), torch.zeros_like(total))
            if name == "comention":
                out[name] = self.drop(torch.relu(mean))
            else:
                out[name] = self.drop(torch.relu(self_h + mean))
        if self.depth == 2 and self.variant != "no_graph":
            out = self._second_layer(out, edges, zero_sources)
        return out

    def _second_layer(self, first: dict[str, torch.Tensor], edges: list[Edge], zero_sources: set[int]) -> dict[str, torch.Tensor]:
        state = first["positive"] + first["negative"]
        n, hidden = state.shape
        outgoing: dict[int, list[Edge]] = {}
        for edge in edges:
            if edge.kind == "struct":
                outgoing.setdefault(edge.src, []).append(edge)
        landed = {"positive": [], "negative": []}
        for first_edge in edges:
            if first_edge.kind != "struct" or first_edge.src in zero_sources:
                continue
            for second_edge in outgoing.get(first_edge.dst, []):
                if second_edge.dst == first_edge.src or second_edge.src in zero_sources:
                    continue
                name = "positive" if first_edge.sign * second_edge.sign > 0 else "negative"
                landed[name].append((first_edge.src, second_edge.dst))
        out = {}
        for name, pairs in landed.items():
            matrix = self.w_pos_2 if name == "positive" else self.w_neg_2
            if not pairs:
                out[name] = torch.relu(torch.zeros(n, hidden, dtype=state.dtype))
                continue
            transformed = matrix(state)
            dst = torch.tensor([pair[0] for pair in pairs], dtype=torch.long)
            src = torch.tensor([pair[1] for pair in pairs], dtype=torch.long)
            total = torch.zeros(n, hidden, dtype=state.dtype).index_add(0, dst, transformed[src])
            count = torch.zeros(n, 1, dtype=state.dtype).index_add(0, dst, torch.ones(len(pairs), 1, dtype=state.dtype))
            out[name] = torch.relu(torch.where(count > 0, total / count.clamp(min=1.0), torch.zeros_like(total)))
        out["comention"] = self.drop(torch.relu(self.w_co_2(first["comention"])))
        return out

    def predict(self, features: torch.Tensor, edges: list[Edge], zero_sources: set[int] | None = None) -> torch.Tensor:
        channels = self.channel_tensors(features, edges, zero_sources)
        packed = torch.cat([channels["positive"], channels["negative"], channels["comention"]], dim=-1)
        return self.head(packed).squeeze(-1), channels

    def contribution(self, features: torch.Tensor, edges: list[Edge]) -> dict[str, torch.Tensor]:
        _, channels = self.predict(features, edges)
        weight = self.head.weight.squeeze(0)
        hidden = channels["positive"].shape[-1]
        names = ("positive", "negative", "comention")
        out = {}
        for index, name in enumerate(names):
            slice_w = weight[index * hidden : (index + 1) * hidden]
            out[name] = (channels[name] * slice_w).sum(dim=-1).abs()
        return out


def mean_of_neighbors(features: torch.Tensor, edges: list[Edge], shock_index: int = 0) -> torch.Tensor:
    n = features.shape[0]
    total = torch.zeros(n, dtype=features.dtype)
    count = torch.zeros(n, dtype=features.dtype)
    for edge in edges:
        if edge.kind != "struct":
            continue
        total[edge.dst] = total[edge.dst] + edge.sign * features[edge.src, shock_index]
        count[edge.dst] = count[edge.dst] + 1
    return torch.where(count > 0, total / count, torch.zeros_like(total))


def _event_errors(pred: torch.Tensor, labels: dict[int, float]) -> tuple[float, float, float, int]:
    if not labels:
        return 0.0, 0.0, 0.0, 0
    abs_err = []
    sq = []
    signs = []
    ignored = 0
    for node, label in labels.items():
        guess = float(pred[node].detach())
        abs_err.append(abs(guess - label))
        sq.append((guess - label) ** 2)
        if label == 0:
            ignored += 1
        elif (guess > 0) == (label > 0):
            signs.append(1.0)
        else:
            signs.append(0.0)
    mae = sum(abs_err) / len(abs_err)
    rmse = math.sqrt(sum(sq) / len(sq))
    sign = sum(signs) / len(signs) if signs else 0.0
    return mae, rmse, sign, ignored


def evaluate(model: SignedMP, events: list[Event], mean: torch.Tensor, std: torch.Tensor) -> dict:
    model.eval()
    maes, rmses, signs, ignored = [], [], [], 0
    with torch.no_grad():
        for event in events:
            pred, _ = model.predict(apply_scaler(event, mean, std), event.edges)
            mae, rmse, sign, skip = _event_errors(pred, event.labels)
            if event.labels:
                maes.append(mae)
                rmses.append(rmse)
                signs.append(sign)
                ignored += skip
    empty = not maes
    return {
        "mae": None if empty else sum(maes) / len(maes),
        "rmse": None if empty else sum(rmses) / len(rmses),
        "sign_accuracy": None if empty else sum(signs) / len(signs),
        "exact_zero_labels_ignored": ignored,
        "events": len(maes),
    }


def train_loop(model: SignedMP, train: list[Event], val: list[Event], epochs: int = 200, patience: int = 20, lr: float = 0.001, weight_decay: float = 0.0001, seed: int = 0) -> dict:
    torch.manual_seed(seed)
    if len(train) < 5:
        epochs = 50
        patience = None
    mean, std = _scale_stats(train)
    opt = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=weight_decay)
    loss_fn = nn.HuberLoss(delta=0.5)
    best_state = copy.deepcopy(model.state_dict())
    best = None
    wait = 0
    ran = 0
    for epoch in range(epochs):
        model.train()
        used = 0
        for event in train:
            pred, _ = model.predict(apply_scaler(event, mean, std), event.edges)
            nodes = [node for node in event.labels]
            if not nodes:
                continue
            guess = pred[nodes]
            target = torch.tensor([event.labels[node] for node in nodes], dtype=guess.dtype)
            loss = loss_fn(guess, target)
            opt.zero_grad()
            loss.backward()
            opt.step()
            used += 1
        ran = epoch + 1
        if not val or patience is None:
            best_state = copy.deepcopy(model.state_dict())
            continue
        score = evaluate(model, val, mean, std)["mae"]
        if score is None:
            continue
        if best is None or score < best - 1e-8:
            best = score
            wait = 0
            best_state = copy.deepcopy(model.state_dict())
        else:
            wait += 1
            if wait >= patience:
                break
    model.load_state_dict(best_state)
    return {
        "epochs_ran": ran,
        "early_stopping": patience is not None,
        "scaler_event_ids": {event.event_id for event in train},
        "loss_event_ids": {event.event_id for event in train},
    }


def channel_contribution(model: SignedMP, events: list[Event], mean: torch.Tensor, std: torch.Tensor) -> dict[str, float]:
    model.eval()
    totals = {"positive": 0.0, "negative": 0.0, "comention": 0.0}
    counted = 0
    with torch.no_grad():
        for event in events:
            parts = model.contribution(apply_scaler(event, mean, std), event.edges)
            nodes = list(event.labels)
            if not nodes:
                continue
            counted += 1
            for name in totals:
                totals[name] += float(parts[name][nodes].mean())
    if not counted:
        return totals
    return {name: value / counted for name, value in totals.items()}


def neighbor_attribution(model: SignedMP, event: Event, mean: torch.Tensor, std: torch.Tensor, neighbor: int) -> dict[int, float]:
    """Change in each label prediction when that neighbor's messages become the zero vector."""
    model.eval()
    features = apply_scaler(event, mean, std)
    with torch.no_grad():
        base, _ = model.predict(features, event.edges)
        ablated, _ = model.predict(features, event.edges, zero_sources={neighbor})
    return {node: float(base[node] - ablated[node]) for node in event.labels}

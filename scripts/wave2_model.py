"""Wave 2 models (amendment B). Reads no study file.

Wave 1's signed model fixed competitor edges to sign -1 through balance-theory
channels, and its no-graph baseline never saw the shock (the shock features
are non-zero only on the event node s). That made "signed vs no-graph" mix two
things: knowing that a shock happened, and knowing who is linked to it.

Wave 2 separates them with four learned models that share one training loop,
one grid and one selection rule:

- own_only         neighbour's own features only. Same role as Wave 1 no-graph.
- shock_broadcast  own features + beta * z_s given to every node, no edges.
                   Knows a shock happened, not who is linked.
- relational       own features + typed messages (positive, competitor-in,
                   competitor-out, co-mention) + one learned scalar beta_r per
                   relation on the mean neighbouring shock z. beta_r is free,
                   so the direction of competitor spillover is learned.
- relational_tied  the same, but beta_comp_in = beta_comp_out = -beta_pos.
                   This is the balance-theory sign constraint of Wave 1,
                   expressed in the same architecture.

Plus a non-learned persistence baseline that predicts 0 abnormal shift.

Primary graph comparison: relational vs shock_broadcast.
Primary sign comparison: relational vs relational_tied, and the fitted
beta_comp with its seed spread.

Columns SHOCK_EVENT_BIN, SHOCK_Z and IS_SOURCE are left unscaled so the shock
term is exactly zero on every node that is not s.
"""

from __future__ import annotations

import copy

import torch
import torch.nn as nn

from phase5_model import Edge, Event, _event_errors

SHOCK_EVENT_BIN = 30
SHOCK_Z = 31
IS_SOURCE = 32
UNSCALED = (SHOCK_EVENT_BIN, SHOCK_Z, IS_SOURCE)
RELATIONS = ("pos", "comp_in", "comp_out", "co")
VARIANTS = ("own_only", "shock_broadcast", "relational", "relational_tied")


def scale_stats(events: list[Event]) -> tuple[torch.Tensor, torch.Tensor]:
    stacked = torch.cat([e.features.detach() for e in events], dim=0)
    mean = stacked.mean(dim=0)
    std = torch.sqrt(stacked.var(dim=0, unbiased=False).clamp(min=1e-8))
    for col in UNSCALED:
        if col < mean.shape[0]:
            mean[col] = 0.0
            std[col] = 1.0
    return mean, std


def apply_scaler(event: Event, mean: torch.Tensor, std: torch.Tensor) -> torch.Tensor:
    return (event.features - mean) / std


def _arcs(edge: Edge) -> list[tuple[str, int, int, float]]:
    """(relation, receiver, sender, weight) for one stored arc."""
    if edge.kind == "co":
        return [("co", edge.dst, edge.src, edge.weight)]
    if edge.kind != "struct":
        return []
    if edge.sign < 0:
        return [("comp_in", edge.dst, edge.src, 1.0), ("comp_out", edge.src, edge.dst, 1.0)]
    return [("pos", edge.dst, edge.src, 1.0)]


class Wave2Net(nn.Module):
    def __init__(self, in_dim: int, hidden: int, depth: int, dropout: float, variant: str = "relational"):
        super().__init__()
        if variant not in VARIANTS:
            raise ValueError(variant)
        self.variant = variant
        self.depth = depth  # kept for the grid; Wave 2 fixes depth 1, labels are one-hop
        self.drop = nn.Dropout(dropout)
        self.own = nn.Linear(in_dim, hidden)
        self.msg = nn.ModuleDict({r: nn.Linear(in_dim, hidden, bias=False) for r in RELATIONS})
        graph = variant in ("relational", "relational_tied")
        self.head = nn.Linear(hidden * (1 + len(RELATIONS) if graph else 1), 1)
        self.beta = nn.ParameterDict({r: nn.Parameter(torch.zeros(1)) for r in RELATIONS})
        self.beta_broadcast = nn.Parameter(torch.zeros(1))

    def betas(self) -> dict[str, float]:
        if self.variant == "relational_tied":
            b = float(self.beta["pos"].detach())
            return {"pos": b, "comp_in": -b, "comp_out": -b, "co": float(self.beta["co"].detach())}
        if self.variant == "relational":
            return {r: float(self.beta[r].detach()) for r in RELATIONS}
        if self.variant == "shock_broadcast":
            return {"broadcast": float(self.beta_broadcast.detach())}
        return {}

    def _beta(self, relation: str) -> torch.Tensor:
        if self.variant == "relational_tied" and relation in ("comp_in", "comp_out"):
            return -self.beta["pos"]
        return self.beta[relation]

    def predict(self, features: torch.Tensor, edges: list[Edge], zero_sources: set[int] | None = None):
        n = features.shape[0]
        zero_sources = zero_sources or set()
        own = self.drop(torch.relu(self.own(features)))
        parts = {"own": own}
        shock_term = torch.zeros(n, dtype=features.dtype)
        if self.variant == "shock_broadcast":
            z_s = (features[:, SHOCK_Z] * features[:, IS_SOURCE]).sum()
            shock_term = self.beta_broadcast * z_s * torch.ones(n, dtype=features.dtype)
        packed = [own]
        if self.variant in ("relational", "relational_tied"):
            grouped: dict[str, list[tuple[int, int, float]]] = {r: [] for r in RELATIONS}
            for edge in edges:
                if edge.src in zero_sources:
                    continue
                for rel, dst, src, w in _arcs(edge):
                    if src in zero_sources:
                        continue
                    grouped[rel].append((dst, src, w))
            for rel in RELATIONS:
                items = grouped[rel]
                if not items:
                    packed.append(torch.zeros(n, self.own.out_features, dtype=features.dtype))
                    parts[rel] = packed[-1]
                    continue
                dst = torch.tensor([i[0] for i in items], dtype=torch.long)
                src = torch.tensor([i[1] for i in items], dtype=torch.long)
                w = torch.tensor([i[2] for i in items], dtype=features.dtype)
                count = torch.zeros(n, dtype=features.dtype).index_add(0, dst, w.abs()).clamp(min=1.0)
                msgs = self.msg[rel](features)[src] * w.unsqueeze(1)
                agg = torch.zeros(n, self.own.out_features, dtype=features.dtype).index_add(0, dst, msgs) / count.unsqueeze(1)
                packed.append(self.drop(torch.relu(agg)))
                parts[rel] = packed[-1]
                z_src = features[src, SHOCK_Z] * features[src, IS_SOURCE] * w
                z_mean = torch.zeros(n, dtype=features.dtype).index_add(0, dst, z_src) / count
                shock_term = shock_term + self._beta(rel) * z_mean
        pred = self.head(torch.cat(packed, dim=-1)).squeeze(-1) + shock_term
        parts["shock_term"] = shock_term
        return pred, parts


def evaluate(model: Wave2Net | None, events: list[Event], mean: torch.Tensor, std: torch.Tensor) -> dict:
    """model None is the persistence baseline (predict 0)."""
    maes, rmses, signs, ignored = [], [], [], 0
    if model is not None:
        model.eval()
    with torch.no_grad():
        for event in events:
            if not event.labels:
                continue
            if model is None:
                pred = torch.zeros(event.features.shape[0])
            else:
                pred, _ = model.predict(apply_scaler(event, mean, std), event.edges)
            mae, rmse, sign, skip = _event_errors(pred, event.labels)
            maes.append(mae)
            rmses.append(rmse)
            signs.append(sign)
            ignored += skip
    if not maes:
        return {"mae": None, "rmse": None, "sign_accuracy": None, "events": 0, "exact_zero_labels_ignored": ignored}
    k = len(maes)
    return {"mae": sum(maes) / k, "rmse": sum(rmses) / k, "sign_accuracy": sum(signs) / k, "events": k, "exact_zero_labels_ignored": ignored}


def event_maes(model: Wave2Net | None, events: list[Event], mean: torch.Tensor, std: torch.Tensor) -> dict[str, float]:
    found = {}
    with torch.no_grad():
        for event in events:
            if not event.labels:
                continue
            if model is None:
                pred = torch.zeros(event.features.shape[0])
            else:
                model.eval()
                pred, _ = model.predict(apply_scaler(event, mean, std), event.edges)
            found[event.event_id] = _event_errors(pred, event.labels)[0]
    return found


def train_loop(model: Wave2Net, train: list[Event], val: list[Event], epochs: int = 200, patience: int = 20,
               lr: float = 0.001, weight_decay: float = 0.0001, seed: int = 0) -> dict:
    """Same rules as phase5_model.train_loop: Huber 0.5, Adam, early stop on validation MAE."""
    torch.manual_seed(seed)
    mean, std = scale_stats(train)
    opt = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=weight_decay)
    loss_fn = nn.HuberLoss(delta=0.5)
    best_state, best, wait, ran = copy.deepcopy(model.state_dict()), None, 0, 0
    for epoch in range(epochs):
        model.train()
        for event in train:
            nodes = list(event.labels)
            if not nodes:
                continue
            pred, _ = model.predict(apply_scaler(event, mean, std), event.edges)
            target = torch.tensor([event.labels[n] for n in nodes], dtype=pred.dtype)
            loss = loss_fn(pred[nodes], target)
            opt.zero_grad()
            loss.backward()
            opt.step()
        ran = epoch + 1
        score = evaluate(model, val, mean, std)["mae"] if val else None
        if score is None:
            best_state = copy.deepcopy(model.state_dict())
            continue
        if best is None or score < best - 1e-8:
            best, wait, best_state = score, 0, copy.deepcopy(model.state_dict())
        else:
            wait += 1
            if wait >= patience:
                break
    model.load_state_dict(best_state)
    return {"epochs_ran": ran, "mean": mean, "std": std, "best_validation_mae": best}

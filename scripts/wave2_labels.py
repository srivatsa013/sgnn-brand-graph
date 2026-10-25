"""Wave 2 abnormal-shift label (amendment B, drafted 2026-10-25).

Wave 1 labelled a neighbour j with its raw shift

    delta(j, t0) = mean(t0 .. t0+7) - mean(t0-7 .. t0-1)

That number is dominated by two things that have nothing to do with the
event brand s:

1. Own reversion. If j's pre window sits above its 28-day baseline, the post
   window tends to fall back toward it whatever s does.
2. Common days. A market-wide or sector-wide sentiment move lifts or sinks
   every entity on the same days.

Wave 2 removes both before any model or test sees the label:

    abnormal(j, t0) = delta(j, t0) - expected_own(j, t0) - sector_factor(t0)

    expected_own(j, t0) = a + b * (pre_mean(j, t0) - baseline_mean(j, t0))

    sector_factor(t0)   = mean over unconnected pool entities k of
                          delta(k, t0) - expected_own(k, t0)

a and b are one pooled least-squares fit per source, on entity-days dated
before the first validation day only. The sector pool for an event is the
same eligible control list Wave 1 already uses (no structural path of length
1 or 2 to s), so the factor cannot carry s's own spillover into the label.

This module reads no study file. The window rules mirror
phase1_gates.window_mean (at least 3 observed bins) and phase1_gates.baseline
(t0-28 .. t0-1, at least 14 observed bins, sample SD).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, timedelta

PRE_DAYS = 7
POST_DAYS = 7
MIN_WINDOW_OBS = 3
BASELINE_BACK = 28
BASELINE_MIN_OBS = 14
MIN_SECTOR_ENTITIES = 3
REVERSION_STEP_DAYS = 8


def _sentiment(cell) -> float | None:
    if not cell or cell[1] < 1:
        return None
    return cell[0] / cell[1]


_MEMO: dict[tuple, object] = {}


def clear_cache() -> None:
    """Blocks are keyed by id(); call between runs that rebuild series dicts."""
    _MEMO.clear()


def window_mean(block: dict, start: date, end: date, min_obs: int = MIN_WINDOW_OBS) -> float | None:
    key = ("w", id(block), start, end, min_obs)
    if key in _MEMO:
        return _MEMO[key]
    _MEMO[key] = _window_mean(block, start, end, min_obs)
    return _MEMO[key]


def _window_mean(block: dict, start: date, end: date, min_obs: int) -> float | None:
    values = []
    day = start
    while day <= end:
        value = _sentiment(block.get(day.isoformat()))
        if value is not None:
            values.append(value)
        day += timedelta(days=1)
    if len(values) < min_obs:
        return None
    return sum(values) / len(values)


def baseline(block: dict, t0: date) -> tuple[float, float, float] | None:
    key = ("b", id(block), t0)
    if key not in _MEMO:
        _MEMO[key] = _baseline(block, t0)
    return _MEMO[key]


def _baseline(block: dict, t0: date) -> tuple[float, float, float] | None:
    values, mentions = [], []
    for k in range(1, BASELINE_BACK + 1):
        cell = block.get((t0 - timedelta(days=k)).isoformat())
        if cell and cell[2] >= 1 and cell[1] >= 1:
            values.append(cell[0] / cell[1])
            mentions.append(cell[1])
    if len(values) < BASELINE_MIN_OBS:
        return None
    center = sum(values) / len(values)
    var = sum((v - center) ** 2 for v in values) / (len(values) - 1)
    if var <= 0:
        return None
    return center, math.sqrt(var), math.log1p(sum(mentions) / len(mentions))


def pre_mean(block: dict, t0: date) -> float | None:
    return window_mean(block, t0 - timedelta(days=PRE_DAYS), t0 - timedelta(days=1))


def post_mean(block: dict, t0: date) -> float | None:
    return window_mean(block, t0, t0 + timedelta(days=POST_DAYS))


def raw_shift(block: dict, t0: date) -> float | None:
    pre, post = pre_mean(block, t0), post_mean(block, t0)
    if pre is None or post is None:
        return None
    return post - pre


def reversion_gap(block: dict, t0: date) -> float | None:
    """How far the pre window sits from the 28-day baseline."""
    pre = pre_mean(block, t0)
    base = baseline(block, t0)
    if pre is None or base is None:
        return None
    return pre - base[0]


@dataclass(frozen=True)
class Reversion:
    a: float
    b: float
    n: int

    def expected(self, gap: float) -> float:
        return self.a + self.b * gap


def reversion_samples(blocks: dict, before: date, start: date | None = None) -> list[tuple[float, float]]:
    """(gap, raw shift) pairs from every entity, on days whose post window ends before `before`.

    Days are taken every REVERSION_STEP_DAYS so post windows of one entity do
    not overlap. `before` is the first validation day of the fold, so no
    validation or test outcome enters the fit.
    """
    pairs = []
    for block in blocks.values():
        days = sorted(date.fromisoformat(text) for text in block)
        if not days:
            continue
        day = max(days[0] + timedelta(days=BASELINE_BACK), start or days[0])
        last = before - timedelta(days=POST_DAYS + 1)
        while day <= last:
            gap = reversion_gap(block, day)
            shift = raw_shift(block, day)
            if gap is not None and shift is not None:
                pairs.append((gap, shift))
            day += timedelta(days=REVERSION_STEP_DAYS)
    return pairs


def fit_reversion(pairs: list[tuple[float, float]]) -> Reversion:
    """Ordinary least squares, shift = a + b * gap. Fewer than 10 pairs gives a = b = 0."""
    n = len(pairs)
    if n < 10:
        return Reversion(0.0, 0.0, n)
    mx = sum(g for g, _ in pairs) / n
    my = sum(s for _, s in pairs) / n
    sxx = sum((g - mx) ** 2 for g, _ in pairs)
    if sxx == 0:
        return Reversion(my, 0.0, n)
    b = sum((g - mx) * (s - my) for g, s in pairs) / sxx
    return Reversion(my - b * mx, b, n)


def own_residual(block: dict, t0: date, rev: Reversion) -> float | None:
    shift = raw_shift(block, t0)
    gap = reversion_gap(block, t0)
    if shift is None or gap is None:
        return None
    return shift - rev.expected(gap)


def sector_factor(pool_blocks: list[dict], t0: date, rev: Reversion) -> tuple[float, int]:
    """Mean own-residual of unconnected pool entities on the same t0.

    Returns (factor, entities used). Fewer than MIN_SECTOR_ENTITIES gives a
    factor of 0.0; the caller logs that count, it is not hidden.
    """
    key = ("f", tuple(id(b) for b in pool_blocks), t0, rev)
    if key in _MEMO:
        return _MEMO[key]
    residuals = [r for r in (own_residual(block, t0, rev) for block in pool_blocks) if r is not None]
    if len(residuals) < MIN_SECTOR_ENTITIES:
        result = (0.0, len(residuals))
    else:
        result = (sum(residuals) / len(residuals), len(residuals))
    _MEMO[key] = result
    return result


def abnormal_shift(block: dict, t0: date, rev: Reversion, pool_blocks: list[dict]) -> dict | None:
    """The Wave 2 label with every component kept, so the paper can show the decomposition."""
    shift = raw_shift(block, t0)
    gap = reversion_gap(block, t0)
    if shift is None or gap is None:
        return None
    expected = rev.expected(gap)
    factor, used = sector_factor(pool_blocks, t0, rev)
    return {
        "raw_shift": shift,
        "gap": gap,
        "expected_own": expected,
        "sector_factor": factor,
        "sector_entities": used,
        "abnormal": shift - expected - factor,
    }

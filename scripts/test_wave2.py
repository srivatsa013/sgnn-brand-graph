"""Synthetic checks for the Wave 2 modules. No study series, score or hand label is read.

    PYTHONPATH=scripts python3 scripts/test_wave2.py
"""

from __future__ import annotations

import math
import random
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))

import wave2_labels as L  # noqa: E402
import wave2_model as W  # noqa: E402
import wave2_self_controlled as S  # noqa: E402
from phase5_model import Edge, Event  # noqa: E402

DAY0 = date(2021, 1, 1)


def cell(value: float, n: int = 10) -> tuple[float, int, int]:
    return (value * n, n, n)


def flat_block(values: dict[date, float]) -> dict:
    return {d.isoformat(): cell(v) for d, v in values.items()}


class LabelTests(unittest.TestCase):
    def setUp(self):
        L.clear_cache()

    def test_worked_example(self):
        """Pre window above baseline; reversion and sector factor are removed exactly."""
        t0 = DAY0 + timedelta(days=60)
        values = {}
        for k in range(1, 29):
            values[t0 - timedelta(days=k)] = 0.30 if k <= 7 else 0.10
        for k in range(0, 8):
            values[t0 + timedelta(days=k)] = 0.18
        block = flat_block(values)
        rev = L.Reversion(a=0.0, b=-0.5, n=100)
        # three pool entities whose raw shift is -0.03 and whose pre window equals baseline
        pool = []
        for _ in range(3):
            pv = {t0 - timedelta(days=k): 0.20 + (0.01 if k % 2 else -0.01) for k in range(1, 29)}
            pv.update({t0 + timedelta(days=k): 0.17 + (0.01 if k % 2 else -0.01) for k in range(0, 8)})
            pool.append(flat_block(pv))
        got = L.abnormal_shift(block, t0, rev, pool)
        base = (21 * 0.10 + 7 * 0.30) / 28
        self.assertAlmostEqual(got["gap"], 0.30 - base, places=9)
        self.assertAlmostEqual(got["raw_shift"], 0.18 - 0.30, places=9)
        self.assertAlmostEqual(got["expected_own"], -0.5 * (0.30 - base), places=9)
        f, used = L.sector_factor(pool, t0, rev)
        self.assertEqual(used, 3)
        self.assertAlmostEqual(got["abnormal"], got["raw_shift"] - got["expected_own"] - f, places=12)
        print(f"\nworked example: raw {got['raw_shift']:+.4f}, expected own {got['expected_own']:+.4f}, "
              f"sector {f:+.4f}, abnormal {got['abnormal']:+.4f}")

    def test_reversion_fit_recovers_slope(self):
        rng = random.Random(0)
        blocks = {}
        for e in range(20):
            level, values = 0.0, {}
            for k in range(700):
                level = 0.7 * level + rng.gauss(0, 0.1)
                values[DAY0 + timedelta(days=k)] = level
            blocks[e] = flat_block(values)
        rev = L.fit_reversion(L.reversion_samples(blocks, DAY0 + timedelta(days=700)))
        self.assertGreater(rev.n, 500)
        self.assertLess(rev.b, -0.3)  # strong pull back toward baseline

    def test_cutoff_excludes_late_days(self):
        values = {DAY0 + timedelta(days=k): 0.1 * math.sin(k) for k in range(400)}
        cut = DAY0 + timedelta(days=200)
        pairs = L.reversion_samples({0: flat_block(values)}, cut)
        self.assertTrue(pairs)
        # every sampled day's post window ends before the cutoff
        n_possible = len(range(28, (cut - DAY0).days - 8 + 1, L.REVERSION_STEP_DAYS))
        self.assertLessEqual(len(pairs), n_possible)


def synthetic_ecosystem(rng, eco: str, edge_class: str, effect: float):
    """One neighbour, ~40 brand events over 2 years; effect is the planted post-window move."""
    days = 760
    noise = {DAY0 + timedelta(days=k): 0.2 + rng.gauss(0, 0.05) for k in range(days)}
    events = [DAY0 + timedelta(days=60 + 17 * i) for i in range(40)]
    signs = [1 if i % 2 else -1 for i in range(40)]
    edge_sign = 1 if edge_class == "positive" else -1
    for t0, sg in zip(events, signs):
        for k in range(0, 8):
            noise[t0 + timedelta(days=k)] += effect * sg * edge_sign
    block = flat_block(noise)
    return [{"ecosystem": eco, "t0": t0, "target": f"{eco}-n", "edge_class": edge_class, "shock_sign": sg,
             "block": block, "s_event_days": events} for t0, sg in zip(events, signs)]


class SelfControlledTests(unittest.TestCase):
    def setUp(self):
        L.clear_cache()

    def test_planted_positive_and_contagion(self):
        rng = random.Random(1)
        treated = []
        for e in range(6):
            treated += synthetic_ecosystem(rng, f"P{e}", "positive", 0.08)
        for e in range(6):
            # contagion: competitor moves WITH the shock, i.e. aligned shift is negative
            treated += synthetic_ecosystem(rng, f"C{e}", "competitor", -0.08)
        out = S.run(treated, L.raw_shift)
        self.assertEqual(out["balance"]["smd"]["log_popularity"], 0.0)
        pos, comp = out["H2_positive"], out["H2_competitor"]
        self.assertTrue(pos["tested"] and comp["tested"])
        self.assertGreater(pos["low"], 0)
        self.assertLess(comp["high"], 0)
        self.assertEqual(S.decide_h2(comp, "competitor", True), "contagion (moved with shock)")
        self.assertEqual(S.decide_h2(pos, "positive", True), "same direction (balance theory)")
        print(f"\nplanted: H2+ {pos['effect']:+.4f} [{pos['low']:+.4f}, {pos['high']:+.4f}], "
              f"H2comp {comp['effect']:+.4f} [{comp['low']:+.4f}, {comp['high']:+.4f}], pairs {out['pairs']}")

    def test_null_gives_equivalence(self):
        rng = random.Random(2)
        treated = []
        for e in range(8):
            treated += synthetic_ecosystem(rng, f"N{e}", "positive", 0.0)
        out = S.run(treated, L.raw_shift)
        r = out["H2_positive"]
        self.assertLessEqual(r["low"], 0)
        self.assertGreaterEqual(r["high"], 0)
        self.assertTrue(r["inside_sesoi"])
        self.assertEqual(S.decide_h2(r, "positive", False), "inside SESOI (equivalence)")

    def test_adjusted_effect_removes_linear_imbalance(self):
        rng = random.Random(3)
        rows = []
        for i in range(400):
            pop_gap = rng.uniform(0.5, 1.5)  # treated always more popular
            diff = -0.04 * pop_gap + rng.gauss(0, 0.01)  # pure popularity artefact, no spillover
            rows.append({"treated_base": (0.2, 0.1, 2.0), "control_base": (0.2, 0.1, 2.0),
                         "treated_pop": int(math.expm1(3 + pop_gap)), "control_pop": int(math.expm1(3)),
                         "treated_abs_shift": 0.1 + diff, "control_abs_shift": 0.1,
                         "ecosystem": f"E{i % 10}", "t0": DAY0 + timedelta(days=7 * (i // 10))})
        raw = sum(r["treated_abs_shift"] - r["control_abs_shift"] for r in rows) / len(rows)
        adj = S.adjusted_effect(rows)
        self.assertLess(raw, -0.03)
        self.assertLess(abs(adj), 0.01)


def graph_events(n: int, rng) -> list[Event]:
    """node 0 = s; node 1 positive (+0.1 z); node 2 competitor, contagion (+0.1 z); node 3 co-mention only (0)."""
    events = []
    for i in range(n):
        z = rng.choice([-2.5, -2.0, 2.0, 2.5])
        x = torch.randn(4, 33) * 0.1
        x[:, 30:] = 0
        x[0, 31], x[0, 32] = z, 1.0
        edges = [Edge(0, 1, "struct", 1.0), Edge(1, 0, "struct", 1.0), Edge(0, 2, "struct", -1.0),
                 Edge(0, 3, "co", 0.0, 1.0), Edge(3, 0, "co", 0.0, 1.0)]
        labels = {1: 0.1 * z + rng.gauss(0, 0.02), 2: 0.1 * z + rng.gauss(0, 0.02), 3: rng.gauss(0, 0.02)}
        events.append(Event(f"g{i}", 1000 + i, x, edges, labels))
    return events


class ModelTests(unittest.TestCase):
    def test_learned_sign_beats_tied_broadcast_and_zero(self):
        rng = random.Random(4)
        torch.manual_seed(0)
        ev = graph_events(120, rng)
        train, val, test = ev[:72], ev[72:96], ev[96:]
        mae = {}
        betas = {}
        for variant in W.VARIANTS:
            model = W.Wave2Net(33, 16, 1, 0.0, variant)
            info = W.train_loop(model, train, val, epochs=60, patience=15, lr=0.01, seed=0)
            mae[variant] = W.evaluate(model, test, info["mean"], info["std"])["mae"]
            betas[variant] = model.betas()
        mae["persistence"] = W.evaluate(None, test, None, None)["mae"]
        print("\nsynthetic MAE:", {k: round(v, 4) for k, v in mae.items()})
        print("relational betas:", {k: round(v, 3) for k, v in betas["relational"].items()})
        self.assertLess(mae["relational"], mae["persistence"])
        self.assertLess(mae["relational"], mae["relational_tied"])
        self.assertLess(mae["relational"], mae["shock_broadcast"])
        self.assertGreater(betas["relational"]["comp_in"], 0.03)  # contagion sign learned, not imposed

    def test_shock_term_zero_off_source(self):
        model = W.Wave2Net(33, 8, 1, 0.0, "relational")
        x = torch.zeros(3, 33)
        x[1, 31] = 5.0  # z present but IS_SOURCE is 0: must not leak
        pred, parts = model.predict(x, [Edge(1, 2, "struct", 1.0)])
        self.assertEqual(float(parts["shock_term"].abs().sum()), 0.0)

    def test_scaler_leaves_shock_columns(self):
        ev = graph_events(10, random.Random(5))
        mean, std = W.scale_stats(ev)
        for col in W.UNSCALED:
            self.assertEqual(float(mean[col]), 0.0)
            self.assertEqual(float(std[col]), 1.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)

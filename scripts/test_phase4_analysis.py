"""Synthetic checks for the Phase 4 analysis. No study series is read."""

from __future__ import annotations

import unittest
from datetime import date, timedelta

import phase4_analysis as A


def _pair(i, diff, aligned_shift, edge="positive", ecosystem="Apple", day=None):
    day = day or date(2020, 1, 6) + timedelta(days=i)
    treated_abs = 0.4 + diff
    return {
        "event_id": f"e{i}",
        "ecosystem": ecosystem,
        "source": "news",
        "t0": day,
        "target": f"t{i}",
        "control": f"c{i}",
        "edge_class": edge,
        "shock_sign": 1,
        "treated_abs_shift": treated_abs,
        "control_abs_shift": 0.4,
        "treated_signed_shift": aligned_shift if edge == "positive" else -aligned_shift,
    }


class PermutationTests(unittest.TestCase):
    def test_formula_never_zero(self):
        self.assertEqual(A.permutation_p(1.0, [0.0, 0.0, 0.0]), 1 / 4)
        self.assertEqual(A.permutation_p(0.0, [0.0, 0.0]), 1.0)
        self.assertGreater(A.permutation_p(5.0, [0.0] * 99), 0)

    def test_known_effect_and_known_null(self):
        effect = A.pair_permutation([0.3] * 40, draws=200, seed=1)
        null = A.pair_permutation([0.3, -0.3] * 20, draws=200, seed=1)
        effect_p = A.permutation_p(0.3, effect)
        null_p = A.permutation_p(0.0, null)
        self.assertLess(effect_p, 0.05)
        self.assertGreater(null_p, 0.05)


class HolmTests(unittest.TestCase):
    def test_stepdown_on_eight(self):
        pvalues = {name: 0.5 for name in A.FAMILY}
        pvalues["H1_pair_permutation"] = 0.001
        pvalues["H1_rewiring"] = 0.002
        pvalues["H2_positive_edges"] = 0.04
        result = A.holm(pvalues)
        self.assertEqual(result["family_size"], 8)
        self.assertTrue(result["rejected"]["H1_pair_permutation"])
        self.assertTrue(result["rejected"]["H1_rewiring"])
        self.assertFalse(result["rejected"]["H2_positive_edges"])
        self.assertLessEqual(
            result["adjusted"]["H1_pair_permutation"],
            result["adjusted"]["H1_rewiring"],
        )


class RewiringTests(unittest.TestCase):
    def test_preserves_degree_and_signs_and_rejects_duplicates(self):
        edges = [("a", "b", 1), ("c", "d", -1), ("e", "f", 1), ("g", "h", -1)]
        original_degree = A.degrees(set(edges))
        original_signs = sorted(sign for _s, _d, sign in edges)
        got = A.rewire(edges, target=30, seed=2, max_attempts=200, consecutive_stop=40)
        self.assertGreater(got["distinct"], 0)
        self.assertLessEqual(got["distinct"], 30)
        self.assertEqual(len(got["graphs"]), len(set(got["graphs"])))
        for graph in got["graphs"]:
            self.assertNotIn(frozenset(edges), [graph])
            self.assertEqual(A.degrees(set(graph)), original_degree)
            self.assertEqual(sorted(sign for _s, _d, sign in graph), original_signs)
            for src, dst, _sign in graph:
                self.assertNotEqual(src, dst)
        same = [1.0 for _ in got["graphs"]]
        self.assertEqual(A.rewiring_p(1.0, same), 1.0)
        self.assertEqual(A.rewiring_p(1.0, [0.0 for _ in got["graphs"]]), 1 / (got["distinct"] + 1))
        self.assertIsNone(A.rewiring_p(1.0, []))


class BootstrapTests(unittest.TestCase):
    def test_clusters_stay_whole_and_intervals_match_the_effect(self):
        clusters = {("Apple", (2020, 1)): [10.0, 10.0], ("Microsoft", (2020, 1)): [0.0, 0.0]}
        got = A.clustered_bootstrap(clusters, draws=200, seed=0)
        for value in got["draws"]:
            self.assertIn(value, (0.0, 5.0, 10.0))
        effect = {("Apple", (2020, 2)): [0.4], ("Microsoft", (2020, 2)): [0.4]}
        interval = A.clustered_bootstrap(effect, draws=100, seed=0)
        self.assertGreater(interval["low"], 0)
        null = {("Apple", (2020, 3)): [0.5], ("Microsoft", (2020, 3)): [-0.5]}
        null_interval = A.clustered_bootstrap(null, draws=200, seed=0)
        self.assertLess(null_interval["low"], 0)
        self.assertGreater(null_interval["high"], 0)


class DecisionTests(unittest.TestCase):
    def test_h1_table_and_ten_pair_rule(self):
        self.assertEqual(A.ten_pair_rule(9), "not estimable")
        self.assertEqual(A.ten_pair_rule(10), "estimable")
        self.assertEqual(A.h1_decision(9, 5, True, True, True, True, 0.2, 0.1, 0.3), "not estimable")
        self.assertEqual(A.h1_decision(12, 0, True, True, True, True, 0.2, 0.1, 0.3), "not estimable")
        self.assertEqual(A.h1_decision(12, 5, False, True, True, True, 0.2, 0.1, 0.3), "method failed")
        self.assertEqual(A.h1_decision(12, 5, True, True, True, True, 0.01, -0.02, 0.02), "no meaningful effect")
        self.assertEqual(A.h1_decision(12, 5, True, True, True, True, 0.2, 0.1, 0.3), "supported")
        self.assertEqual(A.h1_decision(12, 5, True, True, True, False, 0.2, 0.1, 0.3), "differs from controls but not graph-specific")
        self.assertEqual(A.h1_decision(12, 5, True, True, False, False, 0.2, -0.1, 0.4), "inconclusive")

    def test_h2_h3_h4_rules(self):
        self.assertEqual(A.h2_decision(9, 0.2, True, 0.1, 0.3), "not estimable")
        self.assertEqual(A.h2_decision(10, 0.2, True, 0.1, 0.3), "supported")
        self.assertEqual(A.h2_decision(10, 0.2, False, 0.1, 0.3), "not supported")
        self.assertEqual(A.h3_decision(-0.1, True, -0.2, -0.05, 0.08), "supported")
        self.assertEqual(A.h3_decision(-0.01, True, -0.02, -0.005, 0.01), "detectable and below the pre-registered margin")
        self.assertEqual(A.h4_decision(4, 8, 0.2, True, 0.1, 0.3), "not estimable")
        self.assertEqual(A.h4_decision(6, 6, 0.2, True, 0.1, 0.3), "supported")
        self.assertEqual(A.h4_decision(6, 6, 0.0, True, -0.1, 0.1), "not supported")


class PlaceboAndEventTests(unittest.TestCase):
    def test_placebo_rate(self):
        valid = A.placebo_rate([0.2, 0.4, 0.8, 0.5])
        invalid = A.placebo_rate([0.01, 0.01, 0.01, 0.4])
        self.assertTrue(valid["valid"])
        self.assertFalse(invalid["valid"])
        self.assertEqual(invalid["rate"], 0.75)

    def test_event_detection_spike_and_null(self):
        start = date(2020, 1, 1)
        flat = {}
        for i in range(40):
            level = 0.1 if i % 2 == 0 else -0.1
            flat[(start + timedelta(days=i)).isoformat()] = [level * 10, 10, 10]
        self.assertEqual(A.detect_events(flat), [])
        spiked = dict(flat)
        spiked[(start + timedelta(days=30)).isoformat()] = [50.0, 10, 10]
        found = A.detect_events(spiked)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["t0"], start + timedelta(days=30))
        self.assertEqual(found[0]["shock_sign"], 1)

    def test_pair_table_uses_registered_differences(self):
        rows = A.pair_table([_pair(i, 0.25, 0.5) for i in range(3)])
        self.assertEqual(len(rows), 3)
        self.assertAlmostEqual(rows[0]["h1_diff"], 0.25)
        self.assertAlmostEqual(rows[0]["aligned_shift"], 0.5)
        self.assertEqual(rows[0]["cluster"][0], "Apple")


if __name__ == "__main__":
    unittest.main()

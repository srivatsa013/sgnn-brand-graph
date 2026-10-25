"""Synthetic checks for Phase 5. No study series and no hand label is read."""

from __future__ import annotations

import unittest

import torch

import phase5_model as M


def _planted(n: int = 20, shuffle: bool = False) -> list[M.Event]:
    events = []
    shocks = [-2.0, -1.0, 1.0, 2.0]
    labels = []
    for index in range(n):
        shock = shocks[index % 4]
        features = torch.zeros(3, 2)
        features[0, 0] = shock
        edges = [
            M.Edge(0, 1, "struct", 1.0),
            M.Edge(1, 0, "struct", 1.0),
            M.Edge(0, 2, "struct", -1.0),
            M.Edge(1, 2, "co", 1.0, weight=1.6),
        ]
        pair = {1: shock, 2: -shock}
        labels.append(pair)
        events.append(
            M.Event(
                event_id=f"e{index}",
                t0=10_000 + index,
                features=features,
                edges=edges,
                labels=pair,
                comention_times=[10_000 + index - 8],
                history_times=[10_000 + index - 1],
                feature_doc_ids={f"f{index}"},
                label_doc_ids={f"y{index}"},
            )
        )
    if shuffle:
        rotated = labels[1:] + labels[:1]
        for event, pair in zip(events, rotated):
            event.labels = dict(pair)
    return events


class SplitAndLeakageTests(unittest.TestCase):
    def test_chronological_order_and_sizes(self):
        split = M.chronological_split(_planted(15))
        self.assertEqual(split["mode"], "chronological_60_20_20")
        self.assertEqual([len(split[name]) for name in ("train", "val", "test")], [9, 3, 3])
        self.assertLess(max(event.t0 for event in split["train"]), min(event.t0 for event in split["val"]))
        self.assertLess(max(event.t0 for event in split["val"]), min(event.t0 for event in split["test"]))

    def test_leave_one_event_out_below_fifteen(self):
        split = M.chronological_split(_planted(6))
        self.assertEqual(split["mode"], "leave_one_event_out")
        self.assertEqual(len(split["splits"]), 6)
        for row in split["splits"]:
            self.assertEqual(len(row["test"]), 1)
            self.assertGreaterEqual(len(row["val"]), 1)
            self.assertEqual(len(row["train"]) + len(row["val"]) + len(row["test"]), 6)

    def test_clean_events_pass_and_each_check_can_fail(self):
        split = M.chronological_split(_planted(15))
        train, val, test = split["train"], split["val"], split["test"]
        ids = {event.event_id for event in train}
        self.assertEqual(M.leakage_failures(train, val, test, ids, ids), [])
        dirty = _planted(15)
        dirty[0].comention_times = [dirty[0].t0 - 7]
        self.assertTrue(any(item.startswith("comention") for item in M.leakage_failures([dirty[0]], [], [], set(), set())))
        dirty[0].comention_times = [dirty[0].t0 - 8]
        dirty[0].history_times = [dirty[0].t0]
        self.assertTrue(any(item.startswith("history") for item in M.leakage_failures([dirty[0]], [], [], set(), set())))
        dirty[0].history_times = [dirty[0].t0 - 1]
        dirty[0].feature_doc_ids = {"same"}
        dirty[0].label_doc_ids = {"same"}
        self.assertTrue(any(item.startswith("label_document") for item in M.leakage_failures([dirty[0]], [], [], set(), set())))
        late = _planted(15)
        late_train = [late[-1]]
        late_test = [late[0]]
        self.assertIn("chronological", M.leakage_failures(late_train, [], late_test, set(), set()))
        self.assertIn("loss", M.leakage_failures(train, val, test, {test[0].event_id}, ids))
        self.assertIn("scaler", M.leakage_failures(train, val, test, ids, {test[0].event_id, val[0].event_id}))


class TrainAndAblationTests(unittest.TestCase):
    def test_planted_signal_beats_a_null(self):
        planted = _planted(20)
        null = _planted(20, shuffle=True)
        split_p = M.chronological_split(planted)
        split_n = M.chronological_split(null)

        def fit(split):
            model = M.SignedMP(2, 16, 1, 0.0, "signed")
            info = M.train_loop(model, split["train"], split["val"], epochs=80, patience=30, lr=0.05, seed=0)
            self.assertEqual(M.leakage_failures(split["train"], split["val"], split["test"], info["loss_event_ids"], info["scaler_event_ids"]), [])
            mean, std = M._scale_stats(split["train"])
            return M.evaluate(model, split["test"], mean, std)["mae"], info

        planted_mae, info = fit(split_p)
        null_mae, _ = fit(split_n)
        self.assertLess(planted_mae, 0.35)
        self.assertGreater(null_mae, planted_mae)
        self.assertGreater(info["epochs_ran"], 0)

    def test_mean_of_neighbors_recovers_the_sign(self):
        event = _planted(1)[0]
        pred = M.mean_of_neighbors(event.features, event.edges)
        self.assertAlmostEqual(float(pred[1]), event.labels[1], places=5)
        self.assertAlmostEqual(float(pred[2]), event.labels[2], places=5)
        null = _planted(1)[0]
        null.labels = {node: -label for node, label in null.labels.items()}
        null_pred = M.mean_of_neighbors(null.features, null.edges)
        self.assertGreater(abs(float(null_pred[1]) - null.labels[1]), 0.5)

    def test_variants_and_attribution_run_without_retuning(self):
        event = _planted(1)[0]
        model = M.SignedMP(2, 8, 1, 0.0, "signed")
        before = {name: tensor.detach().clone() for name, tensor in model.state_dict().items()}
        mean = torch.zeros(2)
        std = torch.ones(2)
        parts = M.channel_contribution(model, [event], mean, std)
        self.assertEqual(set(parts), {"positive", "negative", "comention"})
        delta = M.neighbor_attribution(model, event, mean, std, neighbor=0)
        self.assertIn(1, delta)
        self.assertIn(2, delta)
        for name, tensor in model.state_dict().items():
            self.assertTrue(torch.equal(tensor, before[name]))
        for variant in ("undirected", "no_sign", "no_direction", "no_comention", "unsigned", "no_graph"):
            other = M.SignedMP(2, 8, 2 if variant == "signed" else 1, 0.0, variant)
            pred, _ = other.predict(event.features, event.edges)
            self.assertEqual(tuple(pred.shape), (3,))
        deep = M.SignedMP(2, 8, 2, 0.0, "signed")
        pred, _ = deep.predict(event.features, event.edges)
        self.assertEqual(tuple(pred.shape), (3,))

    def test_short_train_skips_early_stopping(self):
        events = _planted(4)
        model = M.SignedMP(2, 4, 1, 0.0, "signed")
        info = M.train_loop(model, events[:3], events[3:], epochs=200, patience=1, seed=1)
        self.assertEqual(info["epochs_ran"], 50)
        self.assertFalse(info["early_stopping"])

    def test_comention_ablation_ignores_that_edge(self):
        event = _planted(1)[0]
        torch.manual_seed(2)
        model = M.SignedMP(2, 8, 1, 0.0, "no_comention")
        with torch.no_grad():
            first, _ = model.predict(event.features, event.edges)
            other_edges = [edge for edge in event.edges if edge.kind != "co"]
            other_edges.append(M.Edge(1, 2, "co", 1.0, weight=9.0))
            second, _ = model.predict(event.features, other_edges)
        self.assertTrue(torch.allclose(first, second))


if __name__ == "__main__":
    unittest.main()

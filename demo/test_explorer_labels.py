"""A figure fails this test when it renders a number without a mode label."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from explorer import Labeled, MODES, figure, news_hits, render_value  # noqa: E402


def test_unlabeled_mode_fails() -> None:
    try:
        figure("unlabeled", "news hits", [])
    except ValueError:
        return
    raise SystemExit("an unlabeled figure was accepted")


def test_bare_number_fails() -> None:
    try:
        figure("REAL measured", "news hits", [{"shift": 0.1}])
    except ValueError:
        return
    raise SystemExit("a bare number was accepted")


def test_render_rejects_a_bare_number() -> None:
    try:
        render_value(0.1)
    except RuntimeError:
        return
    raise SystemExit("render accepted a bare number")


def test_each_mode_is_on_the_figure() -> None:
    for mode in MODES:
        spec = figure(mode, "news hits this brand", [{"neighbor": "iPhone", "shift": Labeled(mode, 0.1)}])
        if mode not in spec["title"] or spec["mode"] != mode:
            raise SystemExit(f"missing label on {mode}")
        if mode not in render_value(spec["rows"][0]["shift"]):
            raise SystemExit(f"missing label on a number for {mode}")


def test_live_pages() -> None:
    real = news_hits("REAL measured", "Apple")
    synthetic = news_hits("AUGMENTED/SYNTHETIC", "Apple", 1.0)
    for spec in (real, synthetic):
        if spec["mode"] not in spec["title"]:
            raise SystemExit("live figure missing a mode label")
        for row in spec["rows"]:
            for value in row.values():
                if isinstance(value, Labeled):
                    render_value(value)
    model_path = Path(__file__).resolve().parents[1] / "eval" / "results" / "phase5_models" / "news_joined_seed0.pt"
    if model_path.exists():
        model = news_hits("MODEL prediction", "Apple")
        if "MODEL prediction" not in model["title"]:
            raise SystemExit("model figure missing a mode label")


if __name__ == "__main__":
    test_unlabeled_mode_fails()
    test_bare_number_fails()
    test_render_rejects_a_bare_number()
    test_each_mode_is_on_the_figure()
    test_live_pages()
    print("explorer labels pass")

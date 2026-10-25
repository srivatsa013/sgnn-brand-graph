"""App checks. Run from site/: python test_app.py"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from propagate import effects, response, summary_line, walk  # noqa: E402
from streamlit.testing.v1 import AppTest  # noqa: E402

FOOTER = "Demo build. Illustrative estimates from a model on an augmented dataset; see the accompanying presentation for details."


def test_sign_rules() -> None:
    links = [
        {"src": "Apple", "dst": "iPhone", "sign": 1, "kind": "positive"},
        {"src": "Apple", "dst": "DELL", "sign": -1, "kind": "competitor"},
    ]
    magnitudes = {"positive": 0.2, "competitor": 0.2, "comention": 0.0}
    positive_news = effects(links, "Apple", 1, magnitudes, 1, 1, 7)
    negative_news = effects(links, "Apple", -1, magnitudes, 1, 1, 7)
    assert positive_news["iPhone"] > 0
    assert negative_news["iPhone"] < 0
    assert negative_news["iPhone"] == -positive_news["iPhone"]
    assert positive_news["DELL"] < 0
    assert positive_news["DELL"] * positive_news["iPhone"] < 0
    assert response(1, 1, 0.2, 1, 1, 0, 1) == 0


def test_click_on_shipped_graph() -> None:
    graph = json.loads((ROOT / "assets" / "graph.json").read_text())
    ids = {node["id"] for node in graph["nodes"]}
    assert len(ids) >= 30
    assert "Simon Property Group" in ids
    assert sum(node["kind"] == "brand" for node in graph["nodes"]) == 30
    for link in graph["links"]:
        if link["sign"] == -1:
            assert link.get("source"), link
        else:
            assert link.get("property"), link
    positive = next(link for link in graph["links"] if link["src"] == "Apple" and link["sign"] == 1)
    clicked = effects(graph["links"], "Apple", -1, graph["magnitudes"], 1, 1, 7)
    assert clicked[positive["dst"]] < 0
    same_news = effects(graph["links"], "Apple", 1, graph["magnitudes"], 1, 1, 7)
    assert same_news[positive["dst"]] > 0
    competitor = next(link for link in graph["links"] if link["src"] == "Apple" and link["sign"] == -1)
    assert same_news[competitor["dst"]] < 0
    assert same_news[competitor["dst"]] * same_news[positive["dst"]] < 0


def test_color_stops_at_two_hops() -> None:
    links = [
        {"src": "A", "dst": "B", "sign": 1, "kind": "positive"},
        {"src": "B", "dst": "C", "sign": 1, "kind": "positive"},
        {"src": "C", "dst": "D", "sign": 1, "kind": "positive"},
    ]
    magnitudes = {"positive": 0.2, "competitor": 0.2, "comention": 0.0}
    values = effects(links, "A", -1, magnitudes, 1, 1, 7)
    assert values.get("B", 0) != 0
    assert values.get("C", 0) != 0
    assert abs(values["C"] - 0.5 * values["B"]) < 1e-9
    assert values.get("D", 0) == 0
    traced = walk(links, "A")
    assert "D" not in traced
    assert traced["C"]["hop"] == 2


def test_every_colored_node_is_within_two_hops() -> None:
    graph = json.loads((ROOT / "assets" / "graph.json").read_text())
    print("edge paths for nodes whose color changes")
    for source in graph["nodes"]:
        traced = walk(graph["links"], source["id"])
        values = effects(graph["links"], source["id"], -1, graph["magnitudes"], 1, 1, 7)
        for name, value in sorted(values.items()):
            if value == 0:
                continue
            info = traced[name]
            assert info["hop"] <= 2, (source["id"], name, info["hop"])
            route = " ".join(
                f"{edge['src']} -[{edge['kind']} {edge['sign']:+.0f}]-> {edge['dst']}" for edge in info["edges"]
            )
            print(f"{source['id']}: {route}")
    apple = effects(graph["links"], "Apple", -1, graph["magnitudes"], 1, 1, 7)
    outgoing: dict[str, list[str]] = {}
    for link in graph["links"]:
        if link["sign"] == 0:
            continue
        outgoing.setdefault(link["src"], []).append(link["dst"])
    dist = {"Apple": 0}
    queue = ["Apple"]
    while queue:
        node = queue.pop(0)
        for nxt in outgoing.get(node, []):
            if nxt not in dist:
                dist[nxt] = dist[node] + 1
                queue.append(nxt)
    beyond = [name for name, hop in dist.items() if hop > 2]
    assert beyond, "the larger graph should contain a node more than two hops from Apple"
    for name in beyond:
        assert apple.get(name, 0) == 0
        assert name not in walk(graph["links"], "Apple")
    line = summary_line("Apple", -1, apple)
    assert line.startswith("Negative news at Apple:")
    assert "fall" in line or "rise" in line
    print(line)


def test_no_raw_id_and_root_labels_do_not_overlap() -> None:
    import re

    graph = json.loads((ROOT / "assets" / "graph.json").read_text())
    raw = re.compile(r"^Q\d+$")
    suffix = re.compile(r"\(Q\d+\)$")
    for node in graph["nodes"]:
        assert str(node["id"]).strip(), node
        assert raw.fullmatch(str(node["id"])) is None, node["id"]
        assert suffix.search(str(node["id"])) is None, node["id"]
        assert "x" in node and "y" in node
    brands = [node for node in graph["nodes"] if node["kind"] == "brand"]
    assert len({node["id"] for node in brands}) == 30
    xs = [node["x"] for node in graph["nodes"]]
    ys = [node["y"] for node in graph["nodes"]]
    span_x = max(xs) - min(xs) or 1
    span_y = max(ys) - min(ys) or 1
    char_px = 7.2
    label_h = 19

    def boxes(width: int, height: int) -> list[tuple[str, float, float, float, float]]:
        stage_w = width
        stage_h = height - 36 - 90
        scale = min((stage_w - 56) / span_x, (stage_h - 56) / span_y)
        found = []
        for node in brands:
            width_px = len(node["id"]) * char_px * scale
            height_px = label_h * scale
            cx = (node["x"] - min(xs)) * scale
            cy = (node["y"] - min(ys)) * scale
            found.append((node["id"], cx - width_px / 2, cy - height_px / 2, width_px, height_px))
        return found

    for width, height in ((1440, 900), (1280, 720)):
        placed = boxes(width, height)
        for i, left in enumerate(placed):
            for right in placed[i + 1 :]:
                overlap_x = min(left[1] + left[3], right[1] + right[3]) - max(left[1], right[1])
                overlap_y = min(left[2] + left[4], right[2] + right[4]) - max(left[2], right[2])
                assert overlap_x <= 0 or overlap_y <= 0, (left[0], right[0], width, height)


def test_no_generic_class_node() -> None:
    graph = json.loads((ROOT / "assets" / "graph.json").read_text())
    banned = {
        "alcoholic beverage", "asset management", "broadcasting", "clothing", "combine harvester",
        "computer hardware", "consumer electronics", "credit", "credit card", "debit card",
        "diesel engine", "excavator", "financial services", "footwear", "gasoline", "grader",
        "insurance", "medication", "music", "mutual fund", "peripheral", "personal computer",
        "personal digital assistant", "plastic", "risk management", "search engine", "smartphone",
        "soft drink", "software", "supermarket", "tablet computer", "toothbrush", "toothpaste",
        "tractor", "truck", "video game",
    }
    ids = {node["id"] for node in graph["nodes"]}
    assert ids.isdisjoint(banned)
    for node in graph["nodes"]:
        if node["kind"] != "brand":
            assert len(node.get("ecosystems") or []) < 3, node["id"]


def test_app_starts() -> None:
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60)
    app.run()
    assert not app.exception
    text = " ".join(getattr(item, "value", "") for item in app.markdown)
    assert FOOTER in text


def test_app_writes_nothing_outside_site() -> None:
    source = (ROOT / "app.py").read_text()
    for banned in ("write_text", "open(", "eval/results", "data/", "demo/", 'mode="w"', "mode='w'"):
        assert banned not in source, banned


def main() -> None:
    test_sign_rules()
    test_click_on_shipped_graph()
    test_color_stops_at_two_hops()
    test_no_generic_class_node()
    test_no_raw_id_and_root_labels_do_not_overlap()
    test_every_colored_node_is_within_two_hops()
    test_app_writes_nothing_outside_site()
    test_app_starts()
    print("site tests passed")


if __name__ == "__main__":
    main()

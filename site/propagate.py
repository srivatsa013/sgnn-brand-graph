"""Shock responses for the site. Color stops at two structural hops."""

from __future__ import annotations

MAX_HOPS = 2


def ramp(day: float, hop: int) -> float:
    start = hop - 1
    if day <= start:
        return 0.0
    span = 7 - start
    if span <= 0:
        return 1.0
    return max(0.0, min(1.0, (day - start) / span))


def response(news_sign: float, edge_sign: float, magnitude: float, scenario: float, size: float, day: float, hop: int) -> float:
    if hop > MAX_HOPS or edge_sign == 0 or magnitude == 0:
        return 0.0
    return news_sign * edge_sign * magnitude * scenario * size * ramp(day, hop)


def _outgoing(links: list[dict]) -> dict[str, list[dict]]:
    outgoing: dict[str, list[dict]] = {}
    for link in links:
        if link["sign"] == 0:
            continue
        outgoing.setdefault(link["src"], []).append(link)
    return outgoing


def walk(links: list[dict], origin: str) -> dict[str, dict]:
    """Shortest structural path from the source, capped at two hops."""
    outgoing = _outgoing(links)
    dist = {origin: 0}
    arrived_sign: dict[str, float] = {}
    arrived_kind: dict[str, str] = {}
    parent: dict[str, tuple[str, dict]] = {}
    queue = [origin]
    while queue:
        node = queue.pop(0)
        if dist[node] >= MAX_HOPS:
            continue
        parent_sign = 1.0 if node == origin else arrived_sign[node]
        for link in outgoing.get(node, []):
            nxt = link["dst"]
            hop = dist[node] + 1
            if hop > MAX_HOPS:
                continue
            sign = 0.0 if parent_sign == 0 else parent_sign * float(link["sign"])
            if nxt not in dist:
                dist[nxt] = hop
                arrived_sign[nxt] = sign
                arrived_kind[nxt] = link["kind"]
                parent[nxt] = (node, link)
                queue.append(nxt)
            elif dist[nxt] == hop and arrived_sign[nxt] != sign:
                arrived_sign[nxt] = 0.0
    found = {}
    for node, hop in dist.items():
        if node == origin:
            continue
        edges = []
        cur = node
        while cur != origin:
            prev, link = parent[cur]
            edges.append({"src": link["src"], "dst": link["dst"], "kind": link["kind"], "sign": link["sign"]})
            cur = prev
        edges.reverse()
        found[node] = {
            "hop": hop,
            "sign": arrived_sign[node],
            "kind": arrived_kind[node],
            "edges": edges,
        }
    return found


def effects(links: list[dict], origin: str, news_sign: float, magnitudes: dict, scenario: float, size: float, day: float) -> dict[str, float]:
    walked = walk(links, origin)
    found = {}
    for node, info in walked.items():
        if info["hop"] > MAX_HOPS:
            continue
        if info["hop"] == 1:
            found[node] = response(news_sign, info["sign"], magnitudes.get(info["kind"], 0.0), scenario, size, day, 1)
            continue
        first = info["edges"][0]
        first_effect = response(
            news_sign, first["sign"], magnitudes.get(first["kind"], 0.0), scenario, size, day, 1
        )
        found[node] = 0.5 * first_effect * float(info["edges"][1]["sign"])
    return found


def _clause(names: list[str], verb: str) -> str:
    shown = names[:8]
    extra = len(names) - len(shown)
    if extra:
        body = ", ".join(shown) + f" and {extra} more"
    elif len(shown) == 1:
        body = shown[0]
    elif len(shown) == 2:
        body = f"{shown[0]} and {shown[1]}"
    else:
        body = ", ".join(shown[:-1]) + " and " + shown[-1]
    word = verb if len(names) > 1 else verb + "s"
    return f"{body} {word}"


def summary_line(origin: str, news_sign: float, values: dict[str, float]) -> str:
    polarity = "Positive" if news_sign > 0 else "Negative"
    fall = sorted(name for name, value in values.items() if value < 0)
    rise = sorted(name for name, value in values.items() if value > 0)
    parts = []
    if rise:
        parts.append(_clause(rise, "rise"))
    if fall:
        parts.append(_clause(fall, "fall"))
    detail = "; ".join(parts) if parts else "no neighbor moves"
    return f"{polarity} news at {origin}: {detail}"

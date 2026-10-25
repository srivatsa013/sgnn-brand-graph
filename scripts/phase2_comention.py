"""Co-mention edges from the pre-window only.

Window is t0-187 through t0-8. An undirected edge is kept when the document
count is at least 3. Weight is log(1+count). No sign is assigned. No shift
is computed.
"""

from __future__ import annotations

import json
import math
import sqlite3
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "interim" / "phase2" / "series.sqlite"
EVENTS = ROOT / "data" / "interim" / "phase2" / "brand_events.json"
NODES = json.loads((ROOT / "configs" / "phase2_nodes.json").read_text())
OUT = ROOT / "kg" / "phase2_comention_edges.json"


def main() -> None:
    events = json.loads(EVENTS.read_text())
    con = sqlite3.connect(DB)
    con.execute("CREATE INDEX IF NOT EXISTS comention_source_day ON comention(source, day)")
    edges = []
    for eco, spec in NODES["ecosystems"].items():
        members = [eco] + list(spec["positive_nodes"]) + list(spec["competitor_nodes"])
        member_set = set(members)
        for source, days in (events.get(eco) or {}).items():
            for t0_text in days:
                t0 = date.fromisoformat(t0_text)
                start = (t0 - timedelta(days=187)).isoformat()
                end = (t0 - timedelta(days=8)).isoformat()
                counts: dict[tuple[str, str], int] = {}
                for a, b, n in con.execute(
                    """
                    SELECT node_a, node_b, n FROM comention
                    WHERE source = ? AND day >= ? AND day <= ?
                    """,
                    (source, start, end),
                ):
                    if a not in member_set or b not in member_set:
                        continue
                    counts[(a, b)] = counts.get((a, b), 0) + int(n)
                for (a, b), count in sorted(counts.items()):
                    if count < 3:
                        continue
                    edges.append(
                        {
                            "ecosystem": eco,
                            "source": source,
                            "t0": t0_text,
                            "window": [start, end],
                            "nodes": [a, b],
                            "document_count": count,
                            "weight": math.log1p(count),
                            "sign": None,
                            "edge_type": "comention",
                            "structural": False,
                        }
                    )
    con.close()
    OUT.write_text(json.dumps({"rule": "prewindow_t0_minus_187_through_t0_minus_8_count_at_least_3", "edges": edges}))
    print("comention edges", len(edges), flush=True)


if __name__ == "__main__":
    main()

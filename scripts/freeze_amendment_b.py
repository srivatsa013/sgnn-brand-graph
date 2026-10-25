"""Freeze amendment B before any Wave 2 outcome exists.

What it does, in order, and it stops at the first failure:
1. Refuses if eval/results/wave2_outcomes.json or reports/wave2_outcomes.md exists
   (a freeze after outcomes would not be a pre-registration).
2. Runs scripts/test_wave2.py and scripts/check_frozen_sha256.py; both must pass.
3. Renames reports/wave2_amendment_b_draft.md to reports/wave2_amendment_b<date>.md
   and changes its status line to FROZEN.
4. Appends amendment B to configs/phase0.json "amendments".
5. In configs/frozen_sha256.json: adds the new phase0.json hash as an amendment of
   that row, and adds one row each for the amendment document and the five Wave 2
   scripts.
6. Runs scripts/check_frozen_sha256.py again; it must pass.

    python3 scripts/freeze_amendment_b.py            # dry run, changes nothing
    python3 scripts/freeze_amendment_b.py --write    # does the freeze
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PHASE0 = ROOT / "configs" / "phase0.json"
MANIFEST = ROOT / "configs" / "frozen_sha256.json"
DRAFT = ROOT / "reports" / "wave2_amendment_b_draft.md"
SCRIPTS = [
    "scripts/wave2_labels.py",
    "scripts/wave2_self_controlled.py",
    "scripts/wave2_model.py",
    "scripts/wave2_train.py",
    "scripts/test_wave2.py",
    "scripts/wave2_config.py",
    "configs/wave2_nodes.json",
    "kg/wave2_structural_edges.json",
]
OUTCOMES = [ROOT / "eval" / "results" / "wave2_outcomes.json", ROOT / "reports" / "wave2_outcomes.md"]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def append_amendment_text(text: str, entry: dict) -> str:
    """Insert one item at the end of the top-level "amendments" array without reformatting the file.

    Re-dumping phase0.json would rewrite unrelated lines (0.20 becomes 0.2) and make the
    diff look like Wave 1 values changed. This edits only the end of that array.
    """
    start = text.index('"amendments": [') + len('"amendments": [') - 1
    depth, i, in_str = 0, start, False
    while True:
        ch = text[i]
        if in_str:
            if ch == "\\":
                i += 2
                continue
            if ch == '"':
                in_str = False
        elif ch == '"':
            in_str = True
        elif ch in "[{":
            depth += 1
        elif ch in "]}":
            depth -= 1
            if depth == 0:
                break
        i += 1
    close = i
    body_end = close
    while text[body_end - 1] in " \n":
        body_end -= 1
    item = json.dumps(entry, indent=2, ensure_ascii=False)
    item = "\n".join("    " + line for line in item.splitlines())
    new = text[:body_end] + ",\n" + item + "\n  " + text[close:]
    if json.loads(new)["amendments"][-1] != json.loads(json.dumps(entry)):
        raise SystemExit("stopped: amendment insertion did not parse back")
    old, got = json.loads(text), json.loads(new)
    got["amendments"] = got["amendments"][:-1]
    if old != got:
        raise SystemExit("stopped: insertion changed something other than the amendments list")
    return new


def run(args: list[str]) -> None:
    env = {**os.environ, "PYTHONPATH": str(ROOT / "scripts")}
    result = subprocess.run([sys.executable, *args], cwd=ROOT, env=env, capture_output=True, text=True)
    tail = (result.stdout + result.stderr).strip().splitlines()[-3:]
    print(f"  {' '.join(args)} -> exit {result.returncode}")
    for line in tail:
        print(f"    {line}")
    if result.returncode != 0:
        raise SystemExit(f"stopped: {args[0]} failed")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    today = date.today().isoformat()
    amendment_id = f"B{today}"
    final_doc = ROOT / "reports" / f"wave2_amendment_b{today}.md"

    print("1. no Wave 2 outcome yet")
    for path in OUTCOMES:
        if path.exists():
            raise SystemExit(f"stopped: {path.relative_to(ROOT)} exists, so outcomes were computed before the freeze")
    if not DRAFT.exists():
        raise SystemExit("stopped: reports/wave2_amendment_b_draft.md not found (already frozen?)")
    for rel in SCRIPTS:
        if not (ROOT / rel).exists():
            raise SystemExit(f"stopped: {rel} not found; unzip wave2_changes.zip at the repo root")

    print("2. tests and current freeze")
    run(["scripts/test_wave2.py"])
    run(["scripts/check_frozen_sha256.py"])

    phase0 = json.loads(PHASE0.read_text())
    manifest = json.loads(MANIFEST.read_text())
    if any(a.get("id") == amendment_id for a in phase0.get("amendments", [])):
        raise SystemExit(f"stopped: {amendment_id} already in configs/phase0.json")

    lines = DRAFT.read_text().splitlines()
    lines[0] = lines[0].replace("Amendment B (draft)", f"Amendment {amendment_id}")
    lines[2] = f"Status: FROZEN on {today} as amendment {amendment_id}, before any Wave 2 outcome was computed."
    text = "\n".join(lines) + "\n"
    doc_rel = final_doc.relative_to(ROOT).as_posix()
    script_hashes = {rel: sha(ROOT / rel) for rel in SCRIPTS}
    entry = {
        "id": amendment_id,
        "date": today,
        "document": doc_rel,
        "changes": "Wave 2 abnormal-shift label, self-controlled H1 and two-sided H2, learned-sign relational model with shock-broadcast, tied-sign and predict-zero baselines, and a Holm family of 6 per arm. Does not change a Wave 1 result, rule, planning SD, or caliper, or amendment A2026-10-25.",
        "label": "raw shift minus own reversion (training-fold fit) minus same-day sector factor of unconnected entities",
        "controls": "same neighbour on placebo days; Wave 1 calipers on baseline mean, SD and log mention; up to 5 days",
        "h2": "two-sided; competitor direction reported as substitution or contagion",
        "family": ["H1_self_controlled", "H2_positive_two_sided", "H2_competitor_two_sided",
                   "H3_graph_relational_vs_broadcast", "H3_sign_relational_vs_tied", "H3_persistence_relational_vs_zero"],
        "gnn_grid": {"hidden": [32, 64], "depth": [1], "dropout": [0.0, 0.2], "seeds": [0, 1, 2, 3, 4]},
        "sesoi": 0.05,
        "min_pairs": 10,
        "script_sha256": script_hashes,
        "calipers_unchanged": True,
        "success_criteria_unchanged": True,
    }

    print("3-5. planned changes")
    print(f"  rename {DRAFT.relative_to(ROOT)} -> {doc_rel}")
    print(f"  configs/phase0.json: append amendment {amendment_id}")
    print(f"  configs/frozen_sha256.json: new phase0.json amendment hash, plus {1 + len(SCRIPTS)} new rows")
    for rel, value in script_hashes.items():
        print(f"    {value}  {rel}")
    if not args.write:
        print("dry run only; rerun with --write to freeze")
        return

    final_doc.write_text(text)
    DRAFT.unlink()
    PHASE0.write_text(append_amendment_text(PHASE0.read_text(), entry))

    phase0_row = next(row for row in manifest["files"] if row["path"] == "configs/phase0.json")
    phase0_row.setdefault("amendments", []).append({
        "sha256": sha(PHASE0),
        "recorded_on": today,
        "entry": f"{amendment_id} Wave 2 label, self-controlled tests and models; Wave 1 SDs and calipers unchanged",
    })
    manifest["files"].append({"path": doc_rel, "sha256": sha(final_doc), "recorded_on": today, "entry": f"{amendment_id} frozen"})
    for rel, value in script_hashes.items():
        manifest["files"].append({"path": rel, "sha256": value, "recorded_on": today, "entry": f"{amendment_id} code"})
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")

    print("6. freeze check after writing")
    run(["scripts/check_frozen_sha256.py"])
    print(f"frozen as {amendment_id}. Commit now, before running wave2_train.py.")


if __name__ == "__main__":
    main()

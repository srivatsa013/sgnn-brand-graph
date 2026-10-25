"""Phase 0 checkpoint. Standard library only.

Confirms the frozen config is complete and that the prose still contains the
same decision-critical tokens.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "configs" / "phase0.json"
REQUIRED_FILES = [
    CONFIG_PATH,
    ROOT / "reports" / "pre_registration.md",
    ROOT / "reports" / "gnn_task_spec.md",
    ROOT / "reports" / "references.md",
    ROOT / "DECISIONS_LOG.md",
    ROOT / "requirements.txt",
    ROOT / "src" / "sgnn_csp" / "config.py",
    ROOT / "src" / "sgnn_csp" / "seed.py",
]
REQUIRED_DIRS = [
    "data/raw",
    "data/interim",
    "data/processed",
    "kg/snapshots",
    "sentiment/series",
    "events/tables",
    "models/checkpoints",
    "eval/results",
    "notebooks",
    "reports",
    "configs",
]
PROSE_TOKENS = {
    "reports/pre_registration.md": [
        "k = 2",
        "SESOI = 0.05",
        "at most 0.20",
        "1,000",
        "500",
        "t0-8",
        "Holm",
        "32 events",
        "62 events",
        "(b+1)/(B+1)",
        "ecosystem crossed with the ISO week",
        "no spillover",
        "coarse sector",
        "descriptive only",
        "differs from controls but not graph-specific",
        "0.70",
        "graph-attributable association under controls",
    ],
    "reports/gnn_task_spec.md": [
        "t0-8",
        "Huber",
        "0.5",
        "W_comp_in",
        "W_comp_out",
        "no balance-theory sign",
    ],
}


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    sys.exit(1)


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def main() -> None:
    for path in REQUIRED_FILES:
        require(path.is_file(), f"missing file {path.relative_to(ROOT)}")
    for directory in REQUIRED_DIRS:
        require((ROOT / directory).is_dir(), f"missing directory {directory}")

    raw = CONFIG_PATH.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    cfg = json.loads(raw)

    require(cfg["schema_version"] == "0.1.0", "schema_version")
    require(cfg["event_detection"]["k_sd"] == 2.0, "k_sd")
    require(cfg["event_detection"]["min_mentions_event_bin"] == 5, "min mentions")
    require(cfg["event_detection"]["min_baseline_observed_bins"] == 14, "baseline bins")
    require(cfg["windows_daily"]["comention_latest_relative_day"] == -8, "comention cutoff")
    require(cfg["windows_daily"]["post_inclusive"] == [0, 7], "post window")
    require(cfg["windows_daily"]["pre_inclusive"] == [-7, -1], "pre window")
    require(cfg["shift"]["exclude_documents_mentioning_event_entity"] is True, "document filter")
    require(cfg["sentiment"]["sources_never_pooled_into_one_score"] is True, "separate sources")
    require(cfg["graph"]["competitor_sign"] == -1, "competitor sign")
    require(cfg["graph"]["positive_sign"] == 1, "positive sign")
    require(cfg["graph"]["comention_imposed_balance_sign"] is False, "comention sign")
    require(cfg["controls"]["balance_smd_max_abs"] == 0.20, "SMD")
    require(cfg["hypotheses"]["H1"]["sesoi_abs"] == 0.05, "SESOI")
    require(cfg["statistics"]["bootstrap_resamples"] == 1000, "bootstrap")
    require(cfg["statistics"]["bootstrap_cluster"] == "ecosystem_x_iso_week", "bootstrap cluster")
    require(cfg["statistics"]["permutation_p_formula"] == "(b+1)/(B+1)", "p formula")
    require(cfg["statistics"]["rewirings"] == 500, "rewirings")
    require(cfg["statistics"]["rewiring_controls_rematched"] is True, "rematch")
    require(cfg["statistics"]["rewiring_do_not_reuse_draws_to_pad"] is True, "no reuse")
    require(cfg["statistics"]["rewiring_max_attempts"] == 20000, "rewiring attempts")
    require(cfg["controls"]["raw_p452_exact_match"] is False, "raw P452")
    require(cfg["controls"]["wikidata_path_check_on_every_control_candidate"] is True, "wikidata check")
    require(cfg["controls"]["selected_control_direct_competitor_check"] is True, "competitor check")
    require(cfg["confirmatory_pooling"]["per_ecosystem_results"] == "descriptive_only", "pooling")
    labels = [row["label"] for row in cfg["h1_decision_table"]["first_matching_row_wins"]]
    require(labels == [
        "not estimable",
        "method failed",
        "no meaningful effect",
        "supported",
        "differs from controls but not graph-specific",
        "inconclusive",
    ], "decision table labels")
    require("no spillover" in cfg["h1_decision_table"]["forbidden_wording"], "forbidden wording")
    require(cfg["statistics"]["primary_family_correction"] == "holm", "holm")
    require(len(cfg["primary_holm_family"]) == 8, "holm family size")
    require(cfg["linking"]["precision_target"] == 0.90, "linking precision")
    require(cfg["classifier"]["phase3_gate_macro_f1_min"] == 0.70, "classifier gate")
    require(cfg["gnn"]["seeds"] == [0, 1, 2, 3, 4], "seeds")
    require(cfg["gnn"]["huber_delta"] == 0.5, "huber")
    require(cfg["gnn"]["loss"] == "huber", "loss name")
    require(cfg["power_gate"]["adequate_mde_max"] == 0.10, "MDE")
    require(cfg["power_gate"]["planning_sd_phase1_provisional"] == 0.20, "planning sd provisional")
    require(cfg["power_gate"]["min_passing_ecosystems"] == 2, "ecosystem count")
    require(cfg["time"]["primary_bin"] == "day", "daily bin")
    require(math.isclose(cfg["controls"]["caliper_log_mention_abs"], math.log(2), rel_tol=0, abs_tol=1e-6), "ln2 caliper")
    require(math.isclose(cfg["controls"]["caliper_log_popularity_abs"], math.log(3), rel_tol=0, abs_tol=1e-6), "ln3 caliper")

    z_sum = cfg["power_gate"]["z_975"] + cfg["power_gate"]["z_80"]
    sd_provisional = cfg["power_gate"]["planning_sd_phase1_provisional"]
    require(sd_provisional == 0.20, "provisional planning sd")
    mde_32 = z_sum * sd_provisional / math.sqrt(32)
    mde_31 = z_sum * sd_provisional / math.sqrt(31)
    require(mde_32 <= 0.10, f"MDE at 32 events should be <= 0.10, got {mde_32}")
    require(mde_31 > 0.10, f"MDE at 31 events should be > 0.10, got {mde_31}")
    require(cfg["power_gate"]["implied_min_events_if_sd_0_20"] == 32, "implied min events")
    z95 = cfg["power_gate"]["z_975"]
    half_target = cfg["power_gate"]["ci_halfwidth_target"]
    n_half = 1
    while z95 * sd_provisional / math.sqrt(n_half) > half_target:
        n_half += 1
    require(n_half == 62, f"half-width n should be 62, got {n_half}")
    require(cfg["power_gate"]["implied_min_events_for_halfwidth_0_05_at_sd_0_20"] == 62, "stored half-width n")
    half_62 = z95 * sd_provisional / math.sqrt(62)
    half_61 = z95 * sd_provisional / math.sqrt(61)
    require(half_62 <= 0.05, f"half-width at 62 should be <= 0.05, got {half_62}")
    require(half_61 > 0.05, f"half-width at 61 should be > 0.05, got {half_61}")
    sd = cfg["power_gate"]["planning_sd_paired_abs_shift"]
    amendment = cfg["amendments"][0]
    require(amendment["id"] == "A2026-10-12-planning-sd", "amendment id")
    require(amendment["date"] == "2026-10-12", "amendment date")
    require(amendment["placebo_pairs"] == 31, "placebo pairs")
    require(amendment["do_not_refreeze"] is True, "do not refreeze")
    require(amendment["gate_passes_at_0_20"] is True, "gate at 0.20")
    require(amendment["gate_passes_at_operative_sd"] is True, "gate at operative sd")
    require(sd == amendment["operative_planning_sd"], "operative sd")
    require(cfg["power_gate"]["implied_min_events_at_operative_sd"] == 9, "operative mde n")
    require(cfg["power_gate"]["implied_min_events_for_halfwidth_0_05_at_operative_sd"] == 18, "operative half n")
    mde_9 = z_sum * sd / math.sqrt(9)
    mde_8 = z_sum * sd / math.sqrt(8)
    require(mde_9 <= 0.10, f"operative MDE at 9 should be <= 0.10, got {mde_9}")
    require(mde_8 > 0.10, f"operative MDE at 8 should be > 0.10, got {mde_8}")

    for relative, tokens in PROSE_TOKENS.items():
        text = (ROOT / relative).read_text(encoding="utf-8")
        for token in tokens:
            require(token in text, f"{relative} missing token {token!r}")

    references = (ROOT / "reports" / "references.md").read_text(encoding="utf-8")
    for token in ["2306.03763", "jrfm18080417", "2548897", "1706.05812", "100417", "2201.04831", "2604.26811", "1808.06354", "2208.07323", "2305.12257"]:
        require(token in references, f"references missing {token}")
    require("not an IEEE 2025" in references or "Do not cite this as IEEE 2025" in references, "IEEE mismatch flag")
    require("Transactions on Machine Learning Research" in references, "TMLR citation")
    require("DOI status: not opened directly" in references, "Das DOI flag")

    decisions = (ROOT / "DECISIONS_LOG.md").read_text(encoding="utf-8")
    require("A15" in decisions, "decisions log missing new assumptions")

    print("PASS")
    print(f"config_sha256={digest}")
    print(f"mde_at_32_events={mde_32:.6f}")
    print(f"mde_at_31_events={mde_31:.6f}")
    print(f"halfwidth_at_62_events={half_62:.6f}")
    print(f"halfwidth_at_61_events={half_61:.6f}")
    print(f"holm_tests={len(cfg['primary_holm_family'])}")
    print("phase0_internal_check=pass")


if __name__ == "__main__":
    main()

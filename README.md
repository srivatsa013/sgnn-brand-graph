# Signed GNN sentiment propagation

Study of cross-entity sentiment spillover on brand knowledge graphs. Two arms stay separate. Numeric rules are in `configs/phase0.json`. The pre-registration is `reports/pre_registration.md`. The predictive task is `reports/gnn_task_spec.md`. Decisions are in `DECISIONS_LOG.md`. Methods and limitations drafts are `reports/methods_draft.md` and `reports/limitations_draft.md`.

Python is 3.14.6. The packages actually installed are pinned in `requirements-lock.txt` (frozen on 2026-10-23). `requirements.txt` is the Phase 0 plan from 2026-10-11. It is not the environment that ran the scripts. That plan lists pandas, scipy, scikit-learn, statsmodels, matplotlib, and torch-geometric, which are not installed. Message passing is the hand-written module in `scripts/phase5_model.py`.

## Folder map

| Path | Role |
| --- | --- |
| `configs/` | Frozen rules, nodes, CEO windows, allow-lists, sector map, recorded sha256 list |
| `src/sgnn_csp/` | Phase 0 config and seed helpers |
| `scripts/` | Collection, counts, scorers, and the synthetic Phase 5 checks |
| `kg/` | Wikidata snapshot `wikidata_2026-10-12` and the structural edges |
| `reports/` | Pre-registration, task spec, and drafts |
| `eval/results/` | Logs, checksums, and count files. Not the raw corpora |
| `data/raw/`, `data/interim/`, `data/processed/` | Extracts, slices, scores, and weights. Not shared |
| `data/handlabel/` | Hand-label sheets. Not shared |
| `models/checkpoints/` | Empty placeholder |
| `sentiment/`, `events/`, `notebooks/` | Placeholders from Phase 0 |

## Order to run

Check the freeze, then the recorded hashes, before any collection job:

```bash
python3 scripts/validate_phase0.py
python3 scripts/check_frozen_sha256.py
```

Long jobs are started only through `scripts/resume_all.sh`. It does not log in to gcloud. It refuses a second copy of a job that is already running. `--check` prints what it would start and starts nothing.

```bash
scripts/resume_all.sh --check
scripts/resume_all.sh --only gdelt
scripts/resume_all.sh --only waiter
```

`--only` names are `fnspid`, `headline`, `tweetskb`, `gdelt`, `waiter`, and `counts`. With no `--only`, the script considers every one of those jobs and still refuses any that are already running. Each start is a new session under `caffeinate`. The GDELT waiter follows `eval/results/phase2_gdelt_supervisor.pid` and runs `scripts/phase2_gdelt_reserve_after.py` only after the supervisor exits 0 with 128 slice files. `scripts/phase4_watchdog.py` is separate. It is not started by `resume_all.sh`.

Synthetic checks do not read study files:

```bash
PYTHONPATH=scripts python3 scripts/test_phase4_analysis.py
PYTHONPATH=scripts python3 scripts/test_phase5_model.py
```

Real Phase 5 training has been run once. The outcomes are `eval/results/phase5_outcomes.json` and `reports/phase5_outcomes.md`. The one-page guide is `reports/FINAL_SUMMARY.md`. The faculty demo is `demo/README.md`. It reads study files and writes only under `demo/`.

## What each script reads and writes

| Script | Reads | Writes |
| --- | --- | --- |
| `resume_all.sh` | pid file and process list | detached logs under `eval/results/` when it starts a job |
| `validate_phase0.py` | `configs/phase0.json` and the Phase 0 prose | nothing |
| `check_frozen_sha256.py` | `configs/frozen_sha256.json`, the listed files, the allow-list gzip files | nothing |
| `bq_usage.py` | BigQuery job list | `eval/results/bq_ledger.jsonl` |
| `phase1_csvstream.py` | a CSV stream | nothing by itself; helpers for the streamers |
| `phase1_stream_fnspid.py` | FNSPID CSV stream, `configs/phase1_universe.json` | retained-ticker parquet under `data/interim/`; not the source CSV |
| `phase1_stream_stocktwits.py` | StockTwits feature and message streams | retained-ticker extracts under `data/interim/` |
| `phase1_count_stocktwits_symbols.py` | StockTwits symbol files | counts only |
| `phase1_fnspid_stall_check.py` | FNSPID stream regions | a stall count |
| `phase1_gates.py` | retained extracts | Phase 1 gate files under `eval/results/` |
| `phase1c_gdelt.py` | BigQuery GDELT GEG | daily aggregates; no article URL |
| `phase1c_gdelt_match_audit.py` | one GDELT day | match audit; no article URL |
| `phase1c_tweetskb.py` | TweetsKB SPARQL | count aggregates |
| `phase2_wikidata_snapshot.py`, `phase2_wikidata_resume.py` | Wikidata | `kg/snapshots/wikidata_2026-10-12/` |
| `phase2_graph.py` | that snapshot and `configs/phase2_nodes.json` | `kg/phase2_structural_edges.json` |
| `phase2_build_series.py`, `phase2_control_series.py`, `phase2_ceo_windows.py`, `phase2_linkedin_cells.py`, `phase4_missing_series.py` | retained extracts | `data/interim/phase2/series.sqlite` |
| `phase2_comention.py` | document ids on t0−187 through t0−8 | co-mention edges |
| `phase2_build_allowlist.py`, `phase2_build_frozen_allowlist.py`, `phase2_expand_allowlist.py`, `phase2_fetch_allowlist_ids.py` | Wikidata and the node list | `configs/gdelt_frozen_allowlist.json` and related lists |
| `phase2_gdelt_allowlist_scan.py`, `phase2_gdelt_allowlist_run.py` | BigQuery | `data/interim/phase2/gdelt_allowlist/` |
| `phase2_gdelt_frozen_rerun.py` | BigQuery, pinned job ids | `data/interim/phase2/gdelt_frozen_full/` |
| `phase2_gdelt_supervisor.py` | the loop log | restarts of that loop; `eval/results/phase2_gdelt_supervisor.status` |
| `phase2_gdelt_waiter.py` | the supervisor pid | `scripts/phase2_gdelt_reserve_after.py` after a clean exit |
| `phase2_gdelt_reserve_after.py` | stored slices | the Arm B series sqlite and `eval/results/phase2_gdelt_reserve_after.json`; `--test` uses the scratch names only |
| `phase2_gdelt_series.py`, `phase2_gdelt_tables.py` | the stored allow-list | series and coverage files |
| `phase2_tweetskb_download.py`, `phase2_tweetskb_continue.py`, `phase2_tweetskb_fill_leading.py` | Zenodo monthly files | raw months, then reduced rows |
| `phase2_tweetskb_stream.py` | one monthly N3 file | `data/interim/phase2/tweetskb_full.sqlite` |
| `phase2_tweetskb_arm_b_counts.py` | that sqlite, after all 38 months | `eval/results/phase2_tweetskb_arm_b_counts.json` |
| `phase2_feasibility.py`, `phase2_positive_funnel.py`, `phase2_amendment8_recount.py`, `phase2_revised_recount.py`, `phase2_subsidiary_coverage.py`, `phase2_brand_edges.py`, `phase2_news_category_counts.py` | series and the graph | count files under `eval/results/` |
| `phase3_gate.py`, `phase3_adapt.py`, `phase3_roberta.py`, `phase3_enlarged.py`, `phase3_final_fit.py` | gold sheets under `data/handlabel/` | checkpoints under `data/interim/phase3/` and gate files under `eval/results/` |
| `phase3a_handlabel_sample.py`, `phase3_sample2.py`, `phase4_sample3.py` | extracts or scored pairs | a new sheet under `data/handlabel/` |
| `phase4_fnspid_score.py`, `phase4_fnspid_headline_score.py` | retained FNSPID rows and `model.pt` | score parts under `data/interim/phase3/` |
| `phase4_fnspid_pair_count.py`, `phase4_fnspid_time.py`, `phase4_fnspid_headline_share.py` | those rows or parts | count files |
| `phase4_headline_counts_waiter.py` | the headline scorer log | then `phase4_arm_a_headline_counts.py` |
| `phase4_arm_a_counts.py`, `phase4_arm_a_headline_counts.py`, `phase4_sitelink_recount.py` | series and score parts | count files under `eval/results/` |
| `phase4_analysis.py` | records passed in by the caller | nothing on disk |
| `phase4_watchdog.py` | status logs | `eval/results/NEEDS_ME.txt` on a hard stop |
| `phase5_model.py`, `test_phase5_model.py`, `test_phase4_analysis.py` | synthetic events for the unit tests | nothing from the unit tests |
| `phase5_train.py` | the stored series and the structural graph | `eval/results/phase5_outcomes.json`, `eval/results/phase5_label_table.parquet`, and `eval/results/phase5_models/` |
| `phase6_eval.py` | those saved models and events | `reports/phase6_evaluation.md` |
| `phase4_balance_diagnosis.py` | rebuilt pairs from the unchanged matcher | `reports/phase4_balance_diagnosis.md` and `eval/results/phase4_balance_exploratory.json` |

## Data sources and licenses

| Source | Use | License |
| --- | --- | --- |
| FNSPID | Arm A news text | CC BY-NC 4.0 |
| StockTwits | Arm A social; the daily series is the user label | no explicit license |
| TweetsKB | Arm B social, months 2017-11 through 2020-12 | CC BY 4.0 |
| HuffPost news-category set | Phase 3 hand-label pool only; not an arm | CC BY 4.0 |
| GDELT GEG | Arm B news, queried through BigQuery on project `sgnn-csp-2` | GDELT via BigQuery |
| Wikidata, snapshot `wikidata_2026-10-12` | structural graph | Wikidata's own terms; not a sentiment arm |
| FIRE English collections | checked and not used | not an arm |
| SEntFiN and FinEntity | replay rows inside the final scorer fit | training replay only |

Raw StockTwits and FNSPID text, the hand-label sheets, and the `.pt` weights stay out of a shared copy. See the share list below.

## Seeds

From `configs/phase0.json`, field `seeds`, logged with the Phase 0 freeze:

| Use | Seed |
| --- | --- |
| Global | 0 |
| Bootstrap, 1,000 resamples | 0 |
| Pair permutation, 1,000 draws | 1 |
| Rewiring | 2 |
| Placebo dates | 3 |
| Linking audit in the pre-registration | 0 |
| Model | 0, 1, 2, 3, 4 |

Later logged seeds, not replacements of that block:

| Use | Seed | Logged |
| --- | --- | --- |
| Hand-label sheet `sample2` | 20261021 | 2026-10-21 |
| Final-fit replay | `20261021 + 60 + epoch` | 2026-10-21 |
| Deployment audit sheet `sample3` | 20261022 | 2026-10-22 |
| Audit bootstrap, headline input | `20261022:headline` | 2026-10-22 |
| Audit bootstrap, joined input | `20261022:joined` | 2026-10-22 |

## What a shared copy contains

This folder is not a git repository. The share rule is `.gitignore`. A shared copy keeps files that the ignore rules do not cover and drops the rest.

Kept, 222 files when counted on 2026-10-23: the root notes, `configs/` (13), `src/` (3), `scripts/` (69), `reports/` (15), `kg/` (11), `eval/` (100), and the placeholder `.gitkeep` files under `data/`, `models/`, `events/`, `sentiment/`, and `notebooks/`. `eval/results/` holds logs, checksums, the billing ledger, and count files. It does not hold the raw corpora or the hand-label sheets. The ledger names the BigQuery account. It is not a key.

Dropped by `.gitignore`:

- `data/raw/*`, `data/interim/*`, `data/processed/*`, except each directory's `.gitkeep`. This is the raw and retained StockTwits and FNSPID text, the GDELT slices, the TweetsKB months, the score parts, and the sqlite series.
- `data/handlabel/`, including `sample.csv`, `sample2.csv`, `sample3.csv`, the disagreement sheets, and `INSTRUCTIONS.md`.
- `*.pt` and `*.pth`, including `data/interim/phase3/final_scorer/model.pt` and `roberta_pretrain.pt`.
- `.venv/`, `__pycache__/`, and `.DS_Store`.
- `.env`, `.env.*`, filenames matching `*credentials*` or `*service-account*`, and `application_default_credentials.json`. None of those files are in the tree. gcloud credentials live outside this folder.

No raw StockTwits text, raw FNSPID text, hand label, or credential file is in the 222-file share set.

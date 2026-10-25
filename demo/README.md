# Faculty demo

This folder is separate from `data/` and `eval/results/`. Code here may read those study files. It does not write into them, and it does not replace a confirmatory table.

Synthetic and augmented outputs are for demonstration only. They are not evidence about real propagation. The choice between Option A and Option B is pending with the team and the guide.

## REAL

These files are drawings or copies of the study graph and the frozen Phase 4 table. They contain no planted shifts.

- `real/REAL_GRAPH_overview.png` — 14 ecosystems
- `real/REAL_GRAPH_apple_microsoft.png` — Apple and Microsoft
- `real/REAL_GRAPH.html` — the same layouts, pan and zoom
- `real/REAL_GRAPH_layout.json` — counts for that drawing

Node shape and color: circle brand, square product, triangle CEO, diamond competitor. Positive edges are green. Competitor edges are red. Co-mention edges are dashed gray. A co-mention edge is a pair of study nodes with at least 3 documents in the stored co-mention table. That pooled drawing is not the per-event pre-window edge used in the confirmatory analysis.

The Phase 4 numbers in the summary page are copied from `reports/phase4_outcomes.md`.

## SYNTHETIC

`synthetic_generator.py` is the only generator. It places events on the real graph. The event count for each ecosystem is the frozen count of events with a matched pair: Arm A social, and Arm B GDELT. Noise standard deviations are the frozen values, Arm A social 0.28373788888841645 and Arm B GDELT 0.049974534401688475. Lambda is 0, 0.25, 0.5, 1.0, and 2.0 times that standard deviation. Positive edges propagate with sign +1, competitor edges with sign −1, and co-mention edges add nothing. Seeds are 0 through 19. Every row has `is_synthetic = 1`, plus `lambda`, `seed`, and `generator_version`.

- `synthetic/SYNTHETIC_events.parquet`
- `synthetic/SYNTHETIC_generator_meta.json`
- `synthetic/SYNTHETIC_recovery_table.json` — written by Option A
- `synthetic/SYNTHETIC_recovery_partial.jsonl` — the same run, one line per seed

## Option A, the default

`python demo/run_option_a.py`

Draws the real graph, writes the synthetic rows if they are not already there, and fits the Phase 5 signed model plus five baselines on each lambda and 20 seeds. The baselines are no-graph, unsigned, sign-shuffled, degree-matched random, and linear diffusion. The demo fit uses hidden size 32, depth 1, dropout 0, at most 6 epochs, and patience 3. It is not the confirmatory grid, and it is not real Phase 5 training.

The summary page is `option_a/REAL_and_SYNTHETIC_summary.html`. The left panel is titled REAL and is shaded by the frozen Arm A joined-news H2 class estimates, with the interval and the pair count in the caption. The right panel is titled SYNTHETIC and is shaded by the planted shift at lambda 1.0. The real Phase 4 table sits beside those panels. The recovery table is a separate SYNTHETIC block.

## Option B, not the default

`python demo/build_augmented.py --confirm-augmented --lambda 1.0 --synthetic-share 0.25`

Without `--confirm-augmented` the script exits and writes nothing. With the flag, it writes only under `demo/augmented/`. Filenames contain `AUGMENTED_CONTAINS_SYNTHETIC_DATA`. The figure title and the watermark say `AUGMENTED` and `CONTAINS SYNTHETIC DATA`. The script prints the synthetic share.

`subset_report` returns the mean label on the real-only rows, the synthetic-only rows, and the combined rows, so the real-only number stays next to any combined number. Real rows have `is_synthetic = 0`.

`python demo/test_real_files_byte_identical.py` runs that builder once and checks that the study files are byte-identical afterward.

The rebuilt table uses the Phase 5 label rows as the real rows. At lambda 1.0 and synthetic share 0.25 the file is `augmented/AUGMENTED_CONTAINS_SYNTHETIC_DATA_lambda1p0_share0p25.parquet`. Real-only mean label −0.0019613872003542603 on 7095 rows. Combined mean label −0.001531190070747276 on 9460 rows. The synthetic-only mean is −0.00024059868192632472 on 2365 rows. The share printed by the builder is 0.250000.

## Explorer

`streamlit run demo/explorer.py`

The page lists signed edges for a brand and the one-hop neighbors. The mode switch is REAL measured, MODEL prediction, or AUGMENTED/SYNTHETIC. REAL measured shows the Phase 5 label-table shift, a demo bootstrap interval, and the event count, with a note when that interval includes zero or lies inside [−0.05, 0.05]. MODEL prediction is the saved Phase 5 joined-news model, seed 0, on the real test fold. AUGMENTED/SYNTHETIC is the planted shift at the lambda on the slider, from 0 to 2. Every number carries its mode label. `python demo/test_explorer_labels.py` fails if a figure renders a number without one. The explorer writes nothing.

## Sign specificity

`python demo/sign_specificity.py` writes `synthetic/SIGN_SPECIFICITY.json`. It is planted data, labeled AUGMENTED CONTAINS SYNTHETIC DATA. Six of the eight neighbors are competitors. When the planted competitor effect has the opposite sign, the signed test MAE is 0.23273094655819312 and the unsigned test MAE is 0.29962429451503086. When the planted competitor effect has the same sign, those MAEs are 0.23225096631172124 and 0.23471831663406634. The simulation supports only this claim about those planted rows: with the larger competitor share, the signed fit has the lower test MAE under the opposite-sign plant, and the two fits are close under the same-sign plant. It supports no claim about either real arm.

# Final summary

Question. When a brand's sentiment jumps, does the sentiment of a one-hop structural neighbor move with the sign of that edge, beyond a matched control, and does a signed graph lower the error of that prediction?

Design. Two arms stay separate: Arm A is restricted FNSPID news and StockTwits for 14 ecosystems, and Arm B is GDELT and TweetsKB for the 13 ecosystems excluding Tesla. An event is a daily shock with at least 5 mentions, |z| at least 2, and an 8-day gap. The outcome is the neighbor's post-window mean minus its pre-window mean, after documents that name the brand are removed. Controls are 1:1 Mahalanobis matches inside the locked calipers. Eight tests share one Holm family per arm. H1 is method failed when the placebo check fails or any absolute standardized mean difference exceeds 0.20.

## Arm A

The family uses restricted joined news. Final Holm p-values are from `reports/phase5_outcomes.md`. Social is not a second family. H1 on joined news is method failed because log mention (0.4400205641910798) and log popularity (0.24695932282559196) exceed 0.20.

| Test | Effect | 95% interval | Final Holm p | Decision |
|---|---:|---|---:|---|
| H1 joined news | −0.0189114 | [−0.0974513, 0.0738195] | 1 | method failed |
| H2 positive | −0.161894 | [−0.360786, −0.020363] | 0.575425 | not supported |
| H2 competitor | −0.0230045 | [−0.129584, 0.0763916] | 1 | not supported |
| H4 magnitude | 0.00264656 | [−0.0848997, 0.0963307] | 1 | not supported |
| H4 lag (days) | 0.431764 | [−0.3542, 1.27656] | 1 | not supported |

Social H1 effect −0.021558, interval [−0.0457013, 0.00216357], decision method failed. Arm A VADER: no testable pair: the restricted VADER series had no matched placebo pair.

## Arm B

The family uses GDELT. H1 is method failed because log popularity is 0.9512276625627908.

| Test | Effect | 95% interval | Final Holm p | Decision |
|---|---:|---|---:|---|
| H1 GDELT | 0.00317244 | [0.00144079, 0.00495438] | 0.015984 (pair), 1 (rewiring) | method failed |
| H2 positive | 0.00787135 | [0.00106105, 0.014996] | 0.20979 | not supported |
| H2 competitor | −0.00122584 | [−0.00356668, 0.00119929] | 1 | not supported |
| H4 magnitude | 0.00288757 | [−0.00338391, 0.00884224] | 1 | not supported |
| H4 lag (days) | 0.359912 | [−0.0332138, 0.737327] | 0.394605 | not supported |

TweetsKB H1 effect 0.000284872, interval [−0.00573159, 0.00615575], decision method failed.

## Phase 5

H3 is not supported on either primary source. Joined news signed test MAE 0.276479 versus no-graph 0.294082: gap −0.0176023, interval [−0.0437192, 0.00666875], Holm p 1, relative gain 0.0598551. GDELT signed test MAE 0.0331616 versus no-graph 0.0328769: gap 0.000284724, interval [−0.000392215, 0.000931017], Holm p 1. The full model table is `reports/phase5_outcomes.md`. Test RMSE and sign accuracy for the stored signed model and for linear diffusion are in that file. Unsigned, no-graph, sign-shuffled, and degree-matched prediction outputs were not stored.

## Recovery curve

On the planted demo, not on the study, the smallest lambda detected for Arm A social is 0.25 with a false-positive rate of 0.0 at lambda 0. For Arm B GDELT it is 0.5 with a false-positive rate of 0.05. The curve is in `demo/synthetic/SYNTHETIC_recovery_table.json`.

## Limitations

The scorer gate of 0.70 was not met (joined macro-F1 0.5609), so Arm A news stays restricted to documents whose headline or summary names the node. Balance fails on every confirmatory source, so H1 is method failed before the interval is read as a substantive result. TweetsKB is concentrated on a few ecosystems and has no document text. The headline series is the robustness series. VADER was not frozen.

## The augmented set

It is a demonstration file: the real Phase 5 label rows plus synthetic rows at lambda 1.0, synthetic share 0.250000. Real-only mean label −0.0019613872003542603 (7095 rows). Combined mean label −0.001531190070747276 (9460 rows). It is not a confirmatory sample, not a Holm test, and not a substitute for either arm. Filenames say AUGMENTED and CONTAINS SYNTHETIC DATA.

The demonstration model is trained on an augmented set with synthetic events and planted propagation. The synthetic share is 0.5 and lambda is 1.0. Positive edges are planted at +1, competitor edges at −1, and co-mention at 0. The real-only results are reported separately.

## Augmented run (contains synthetic events)

One signed fit on the augmented joined-news events. The selected model is hidden 32, depth 2, dropout 0.2. These figures are not a Holm test and do not replace the real-only Phase 5 table.

| Split | Events | Test MAE | SD | Test RMSE | SD | Sign accuracy | SD |
|---|---:|---:|---:|---:|---:|---:|---:|
| augmented_test | 35 | 0.259116 | 0.00379838 | 0.301459 | 0.0050563 | 0.642986 | 0.0170838 |
| real_only_test | 16 | 0.29208 | 0.00442938 | 0.330955 | 0.00550842 | 0.57 | 0.0319148 |

Per-edge-class estimates on the augmented test fold: positive 0.03178, competitor 0.0413093, co-mention 0.0320373.

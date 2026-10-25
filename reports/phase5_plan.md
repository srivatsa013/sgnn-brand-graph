# Phase 5 plan

This is the training plan. It does not fit a model, detect an event, or change a running job. Rules stay in `configs/phase0.json` and `reports/gnn_task_spec.md`. A constant moves only by a new entry in `DECISIONS_LOG.md`.

## Target and unit

One example is an event `(s, q, t0)`: at least 5 mentions, `|z| ≥ 2` on the t0−28…t0−1 baseline (14 observed days, divisor n−1), and no earlier event for that entity and source within 8 days. The label is the same-source shift of each one-hop structural neighbor: the mean on t0…t0+7 minus the mean on t0−7…t0−1. Each window needs 3 observed days, after every document that mentions `s` is removed. `s`, a control, and a co-mention-only neighbor are not labels. An event with no unmasked neighbor leaves the loss and is counted. H1–H4 stay on the event–target pair. News and social are separate targets.

## Features

On t0−7…t0−1, each source contributes bin sentiment, a missingness mask, and `log(1 + mentions)`. A missing bin is 0 only beside that mask. Each source also adds its baseline mean, sample SD, and `log(1 + baseline mentions)` on t0−28…t0−1. Node type is one-hot: brand, parent, product, competitor, CEO, other. A CEO counts only inside `configs/ceo_tenures.json`. Two shocks are nonzero only on `s`: the event-bin sentiment of `q`, and surprise `z`, plus an indicator that is 1 only on `s`. Nothing else uses a document dated t0 or later. The training fold alone sets the scaler.

Structural edges are the Wikidata snapshot in `kg/phase2_structural_edges.json` under revised Amendment 8. The strict owner graph is robustness only. Positive relations, sign +1, share `W_pos`: parent, subsidiary, owned by, owner of, brand, product, manufacturer, and CEO. They are stored once and run as two arcs. Competitor arcs are directed, sign −1, with separate `W_comp_in` and `W_comp_out`. A missing reverse arc is left missing. Co-mention edges use only that source’s text from t0−187 through t0−8, need at least 3 documents, weigh `log(1 + count)`, and have no sign. They do not decide who is connected.

## Model

Message passing follows balance theory (Derr, Ma, and Tang, 2018). Depth 1 has three channels: own features plus the mean of `W_pos`; own features plus the means of `W_comp_in` and `W_comp_out`; and the weighted mean of `W_co`, with no sign flip. Depth 2 puts balanced structural walks in one channel and unbalanced walks in another. A walk is balanced when the product of its signs is +1. Co-mention edges stay off those walks. A linear head predicts the shift. ReLU follows each channel. An empty neighborhood is a zero vector. Validation chooses hidden size in {32, 64}, depth in {1, 2}, and dropout in {0.0, 0.2}. The loss is Huber with delta 0.5. Learning rate 0.001, weight decay 0.0001, at most 200 epochs, patience 20 on validation MAE.

## Split, events, and controls

Sort by t0. At 15 or more events, the earliest 60% train, the next 20% validate, and the last 20% test. Below 15, test by leave-one-event-out, holding out the last 20% of the rest (at least one event) for validation. Below 5 training events, skip early stopping and train for 50 epochs. Leave-one-ecosystem-out is always reported as robustness. A random time split is forbidden.

Controls never enter the loss. A control must lie beyond structural distance 2 on the study graph and on Wikidata, and must pass the direct-competitor check. Matching stays 1:1 Mahalanobis, with the locked calipers and the merged information-technology and communication-services bucket. The control stays tied to its event for H1 and H2. An H2 class is tested on an arm and a source only when it has at least 10 matched pairs. Below 10, those edges stay in the graph and in H1. The six leakage checks in `reports/gnn_task_spec.md` §7 pass before any test metric is used.

## Baselines and metrics

Learned baselines use the same grid, seeds, folds, and stopping rule. No-graph is the head on the node’s own features. Unsigned GCN treats every structural edge as positive and undirected, with one matrix, and keeps co-mention as its own type. Secondary baselines are sign-shuffled, degree-matched random, and linear diffusion, which fits one training-fold coefficient on edge sign times shock `z`.

Primary H3, read only on held-out events, is signed versus unsigned and signed versus no-graph. Support needs a negative MAE gap, a Holm-adjusted permutation p below 0.05, an interval excluding 0, and at least a 5% relative MAE gain. Test metrics are MAE, RMSE, and sign accuracy, ignoring exact-zero shifts and reporting that count. Average within the event, then across events with equal weight. Seeds 0–4 give the mean and the SD. Uncertainty is `(b+1)/(B+1)`, Holm within the arm’s eight tests, and a 95% percentile bootstrap on ecosystem × ISO-week clusters, 1,000 resamples, seed 0.

## Arms, interpretability, and compute

Arm A is FNSPID and StockTwits for Apple, Microsoft, Alphabet, and Tesla. Arm B is GDELT GEG and TweetsKB for Apple, Microsoft, and Alphabet. Tesla stays out of Arm B. News and social are fit separately. The arms share no score, baseline, event list, scaler, or test, and each keeps its own Holm family. The frozen Arm A SD 0.10636804456181562 is not refit and is not applied to Arm B.

On the test events, an edge-type effect is the mean absolute contribution of the positive, negative, or co-mention channel. A per-neighbor attribution is the change when that message is replaced by the zero vector, with no retuning.

Training is CPU only, four threads, no GPU, one source at a time, on the locked grid. It waits until the collection jobs are finished and free disk is at least 6 GB.

## Built, missing, and blocked until logged

Built: the task spec, the grid, the signed graph, Amendment 8, CEO windows, the sector bucket, `scripts/phase2_comention.py`, the Arm A scorers, the StockTwits labels, and `scripts/phase4_analysis.py`. Missing: the training loop, the chronological split, the leakage checker, and the attribution code. Arm B’s series is still being collected, and its planning SD is proposed, not frozen. The main Arm A news input waits on the 2026-10-22 audit.

Logged on 2026-10-23, before any outcome:

1. Arm A news events follow the conditional rule in the log. The 0.70 threshold is unchanged. The 2026-10-22 audit entry is not edited. Detection has not started.
2. Arm A is the 14 ecosystems and Arm B is the 13 non-Tesla ecosystems. No brand beyond these 14.
3. One shared `W_pos` stays locked. Per-property matrices are not adopted.
4. Signed undirected, mean-of-neighbors, no-sign keeping direction, no-direction keeping sign, and signed without co-mention are descriptive ablations outside the Holm family. Primary H3 is unchanged.
5. Channel contribution and per-neighbor attribution use the definitions above. They are reported after the test fold is scored.

Real training still waits until the collection jobs are finished, free disk is at least 6 GB, and a go-ahead is given. `scripts/phase5_model.py` is exercised on synthetic events only.

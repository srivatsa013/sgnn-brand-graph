# Amendment B2026-10-25 — Wave 2 label, controls, models and hypothesis direction

Status: FROZEN on 2026-10-25 as amendment B2026-10-25, before any Wave 2 outcome was computed.

## 1. Why, from Wave 1 diagnostics only

These are observations on Wave 1. None of them is a Wave 2 outcome.

1. The raw label is dominated by the target's own dynamics. On the Phase 5 test folds, a predict-zero baseline is close to or better than every learned model on news, StockTwits and TweetsKB. On GDELT, every model, including no-graph, beats zero by about the same margin, so the learnable part is the neighbour's own history (`scripts/wave1_persistence_baseline.py` gives the exact numbers).
2. Balance failed on popularity in every source (SMD 0.25, 0.65, 0.95, 0.95). Graph neighbours of the 30 brands are more widely known than unconnected firms, and popularity governs how noisy |shift| is.
3. The Wave 1 no-graph baseline does not see the shock. Shock features are non-zero only on the event node. "Signed vs no-graph" therefore mixes knowing that a shock happened with knowing who is linked.
4. Exploratory competitor rows had a negative aligned shift (news headline −0.085, p 0.012; StockTwits re-match −0.056, p 0.016). The Wave 1 H2 estimand uses the treated shift alone, with no control subtraction, so market-wide co-movement on event days also produces a negative competitor aligned shift. A one-sided H2 cannot tell substitution, contagion and common days apart.

## 2. Label

For neighbour j of event entity s at t0, on the event source:

- raw(j, t0) = mean(t0 … t0+7) − mean(t0−7 … t0−1), with Wave 1 window rules. Every document that mentions s is removed first.
- gap(j, t0) = mean(t0−7 … t0−1) − baseline mean(t0−28 … t0−1). The baseline needs at least 14 observed bins.
- expected_own(j, t0) = a + b · gap(j, t0). a and b come from one pooled least-squares fit per source, on entity-days spaced 8 days apart whose post window ends before the first validation day. Fewer than 10 fit days gives a = b = 0.
- sector_factor(t0) = mean of raw − expected_own over the ecosystem's eligible Wave 1 control list on the same t0, which has no structural path of length 1 or 2 to s. With fewer than 3 such entities the factor is 0, and the count is reported.
- abnormal(j, t0) = raw − expected_own − sector_factor.

The decomposition is reported per source: raw variance, and the share removed by own reversion and in total.

## 3. Spillover tests: self-controlled

The control for (s, t0, j) is j itself on placebo days d:

- |d − t0| ≥ 8, and |d − e| ≥ 8 for every event day e of s.
- |d − t0| ≤ 365.
- j has both windows on d.
- j's baseline on d passes the Wave 1 calipers against j's baseline on t0: mean within 0.20, SD ratio in [0.5, 2.0], log mention within ln 2.
- Up to 5 nearest passers by standardized Euclidean distance on those three covariates. With none, the pair is dropped.

Popularity SMD is 0 by construction. SMDs on the other three covariates are reported, and the 0.20 rule still applies to them.

The outcome is abnormal(j, ·). The raw-outcome version is reported beside it as secondary.

- H1: |y(j, t0)| − mean_d |y(j, d)|. Positive means spillover.
- H2, positive edges, two-sided: shock_sign · (+1) · (y(j, t0) − mean_d y(j, d)).
- H2, competitor edges, two-sided: shock_sign · (−1) · (y(j, t0) − mean_d y(j, d)). Greater than 0 is substitution, the target moved against the shock. Less than 0 is contagion, the target moved with the shock. The direction is reported, not assumed.

Inference uses the Wave 1 rules: a clustered bootstrap on ecosystem × ISO week with seed 0 and 1,000 draws, and pair permutation with seed 1 and 1,000 draws. The minimum is 10 pairs, and the SESOI is 0.05. An interval inside ±0.05 is reported as equivalence.

Secondary: the Wave 1 cross-entity H1 with regression adjustment. The OLS intercept of the treated-minus-control |shift| on the four covariate differences is reported with a cluster bootstrap. It is not in the family.

## 4. Models

These share one training loop: Huber 0.5, Adam with learning rate 0.001 and weight decay 0.0001, up to 200 epochs, patience 20 on validation MAE. They also share the day-boundary 60/20/20 folds, seeds 0–4, and the grid hidden ∈ {32, 64} × dropout ∈ {0.0, 0.2}. Depth is fixed at 1, because labels are one-hop neighbours and the shock enters through a direct term. Columns 30–32 (event-bin sentiment, shock z, source indicator) are not standardized, so the shock term is exactly 0 off the event node.

- own_only: the neighbour's own features.
- shock_broadcast: own features plus β · z_s on every node, with no edges.
- relational: own features, typed messages (positive, competitor-in, competitor-out, co-mention), and a free scalar β_r per relation on the mean neighbouring z.
- relational_tied: the same as relational, with β_comp_in = β_comp_out = −β_pos. This is the balance-theory constraint.
- persistence: predict 0. It is not learned.
- Secondary: relational refit on the sign-shuffled and degree-matched graphs, with the Wave 1 procedures.

The learned β per relation is reported as the mean and SD over seeds.

## 5. Family and decisions (per arm, Holm, two-sided α 0.05)

1. H1 self-controlled
2. H2 positive edges, two-sided
3. H2 competitor edges, two-sided
4. H3 graph: relational vs shock_broadcast
5. H3 sign: relational vs relational_tied
6. H3 persistence: relational vs predict-zero

An H3 comparison is supported when the MAE gap is negative, the Holm p is below 0.05, the interval excludes 0, and the relative MAE gain is at least 5%. This is the Wave 1 H3 rule. The H2 decision table is in `wave2_self_controlled.decide_h2`.

Arm A's primary source is news only if the scorer passes its gate after the allowed rounds. Otherwise Arm A news is dropped, as already frozen. Arm B's primary source is GDELT.

## 6. Code

`scripts/wave2_labels.py`, `scripts/wave2_self_controlled.py`, `scripts/wave2_model.py`, `scripts/wave2_train.py`, `scripts/test_wave2.py`. Their sha256 values are recorded with this freeze. `scripts/test_wave2.py` must pass before the run. No Wave 1 script is edited.

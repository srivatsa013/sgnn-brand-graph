# Pre-registration

Status: approved on 2026-10-11 with seven amendments, then re-frozen. Numeric source of truth: `configs/phase0.json`. If this prose and that file ever disagree, the JSON wins and the disagreement is a bug.

This document is written before any sentiment series, event list, or model result exists. Thresholds below are not to be revised after those outcomes are seen. The only pre-authorized revision is the Phase 1 data-audit escape hatch in Section 12.

## 1. Question

Does a sentiment shock to one entity in a brand ecosystem move the later sentiment of graph-neighbors more than it moves matched entities that are not connected to it, once articles that mention both are removed? Ownership and product links are predicted to carry the shock in the same direction. Competitor links are predicted to carry it in the opposite direction, with a separate strength in each direction. News and social media are separate shocks, not one blended score. A signed graph neural network is then asked whether those signed links predict the neighbors' shifts better than unsigned and graph-free models.

Claims, if any are supported, will be worded as a graph-attributable association under controls.

## 2. Units

- Clock: UTC. A day is a UTC calendar date. A week, used only under the fallback in Section 12, is an ISO week starting Monday.
- Language: English rows only. Non-English volume is counted and then excluded.
- Sentiment of one linked mention is a number in [-1, 1]. A discrete label maps positive to 1, neutral to 0, and negative to -1. A probabilistic classifier uses P(positive) minus P(negative).
- A bin score is the unweighted mean of linked mention scores in that entity, source, and bin. Mention count is stored beside it. A bin with zero mentions is missing. It is not a neutral zero.
- News and social media never share a score, a baseline, or an event.

## 3. Sentiment event

An event is an entity, a source, and a day t0.

Baseline days are t0-28 through t0-1. A baseline day is observed if it has at least 1 mention. Require at least 14 observed baseline days. Let the baseline mean and the sample standard deviation use those observed days, with divisor n-1. If the sample standard deviation is 0, the day is not an event.

The day t0 is an event if both of the following hold:

- mention count on t0 is at least 5
- the absolute surprise z = (s_t0 - baseline mean) / sample standard deviation is at least k = 2

The shock sign is the sign of (s_t0 - baseline mean).

After an event at t0 for that entity and source, no new event is opened until t0+8 or later. Overlapping events would share post windows. The earlier event is kept.

News events and social events on the same entity and day are two events.

## 4. Windows and the shift

For daily bins:

- Pre window: t0-7 through t0-1, inclusive.
- Post window: t0 through t0+7, inclusive. The event day is included for target entities because same-day spillover is part of the question.
- The source entity's own t0 is used only to define the shock. It is not a prediction target.

The shift of a target is the post-window mean minus the pre-window mean, on the same source as the event. Each window must contain at least 3 observed bins, and an observed bin has at least 1 mention. Otherwise the target is dropped for that event. There is no imputation.

Before those means are computed, drop every document that mentions the event entity. Shared-article reaction is not counted as a shift of the target. Document identifiers are retained so this filter can be audited.

Co-mention edges for that same event are counted only on documents dated on or before t0-8, inside a 180-day lookback. The cutoff is t0-8 so the edge list cannot use the pre window, the event day, or the post window. An edge requires at least 3 such documents. Its weight is log(1 + count). It is a separate edge type and has no balance-theory sign.

## 5. Who is connected, and who is a control

Structural edges are the ownership, product, and competitor edges. Co-mention edges do not count as connection and do not disqualify a control.

A primary target is a one-hop structural neighbor of the event entity. If that neighbor is tied to the event entity by both a positive edge and a competitor edge, it stays in H1 and is removed from H2. The conflict is logged.

A control candidate is any other entity in the sentiment tables that has no structural path of length 1 or 2 to the event entity in our graphs. Entities inside the studied ecosystems will often fail this test. The control pool is therefore the wider entity list in the datasets, not the two or three ecosystem graphs alone.

Our graphs are small, so a parent, product, or competitor that is simply missing from them could be chosen as a control. Every candidate is therefore also checked against Wikidata. The candidate is ineligible if Wikidata shows a path of length 1 or 2 to the event entity along parent, subsidiary, owner, brand, product, or manufacturer relations, and along a competitor relation when Wikidata has that relation populated. For the matched controls that are actually selected, a separate check asks whether each one is a direct competitor of the event entity. Both checks, and their outcomes, are written down for every event: how many candidates the Wikidata path removed, and whether each selected control passed the direct-competitor check. A selected control that fails the direct-competitor check is dropped and the match is redone from the remaining eligible pool. The calipers are not widened.

Matching is 1:1, without replacement inside an event, with replacement allowed across events.

Hard gates, all required:

- Same coarse sector bucket. The bucket is not the raw Wikidata industry value. Raw industry values are too fine-grained to match on. A mapping from those industry values to a small set of buckets is defined and logged in Phase 1 or Phase 2, before any matching and before any outcome is computed. If industry is missing, the entity is ineligible until a manual bucket is written into the decisions log before matching.
- Absolute difference of baseline means at most 0.20.
- Ratio of baseline standard deviations between 0.5 and 2.0.
- Absolute difference of log(1 + baseline mention count) at most 0.693147, which is ln(2).
- Absolute difference of log(1 + Wikidata sitelink count) at most 1.098612, which is ln(3). Missing popularity makes the entity ineligible. It is not imputed.

Among candidates that pass the gates, pick the minimum Mahalanobis distance on the four covariates. The covariance is the covariance of the eligible control pool for that event. If that covariance is singular or has condition number above 1,000,000, use standardized Euclidean distance with the control-pool standard deviations. If one of those standard deviations is 0, drop that covariate for that event and log it.

If nobody passes, drop the treated target. Do not widen the calipers.

Balance is the standardized mean difference on the pooled matched sample:

SMD = (mean of treated - mean of controls) / square root of ((variance of treated + variance of controls) / 2)

Confirmatory H1 and H2 are interpretable only if every covariate has absolute SMD at most 0.20. If not, report the balance table and do not claim H1 or H2. Do not rematch with looser calipers. A looser match may appear only in the Phase 6 sensitivity report, labeled exploratory.

## 6. Hypotheses and estimands

The analysis unit is the event-target pair. Confirmatory H1–H4 tests pool events across every ecosystem that passes that arm's coverage and power gates. Pooling stops at the arm boundary. Arm A and Arm B are never pooled into one score, one baseline, one event list, or one test. Each arm has its own primary Holm family of the same eight tests. A result on one arm is not evidence about the other. Per-ecosystem results are descriptive only. They are not part of the Holm family. Section 13 records the arm membership.

Events in the same ecosystem on nearby days share news days, so they are not independent. Inference treats an ecosystem crossed with the ISO week of t0 as one cluster.

- H1. Connected targets have a larger absolute shift than their matched controls. Estimand: mean of |shift| on connected targets minus the mean of |shift| on matched controls. Predicted sign: positive. The smallest effect that will be called meaningful is 0.05 sentiment points (SESOI = 0.05).
- H2, positive edges. The balance-aligned shift is shift times shock sign times edge sign (+1). Mean aligned shift is positive.
- H2, competitor edges. The same aligned shift with edge sign -1. Mean aligned shift is positive, which means the target moved against the shock.
- H3. On held-out events, the signed model has lower mean per-event MAE than the unsigned GCN, and lower mean per-event MAE than the no-graph model. Each comparison needs a relative MAE drop of at least 5 percent as well as a significant paired test. Seed-averaged MAE is computed first. The paired test uses those seed averages.
- H4 magnitude. The H1 estimand computed on news events minus the H1 estimand computed on social events is not zero.
- H4 lag. Lag is the day in {0, 1, ..., 7} where the mean connected-target shift, relative to that target's pre-window mean, has the largest absolute value. Mean news lag minus mean social lag is not zero.

H4 is not estimable if either source has fewer than 5 events. That case is reported as not estimable, not as a null result. If Arm B has no news source, H4 is not estimable on Arm B. H1 is not estimable if there are fewer than 10 matched pairs. No p-value is printed in that case.

## 7. Tests, multiplicity, and decisions

Primary family, Holm correction, eight tests, two-sided alpha 0.05 before adjustment. This family is computed once for Arm A and once for Arm B. The two families are not merged into sixteen tests, and they are not collapsed into one family of eight:

1. H1 pair-label permutation
2. H1 degree-preserving rewiring
3. H2 positive edges
4. H2 competitor edges
5. H3 signed versus unsigned
6. H3 signed versus no-graph
7. H4 magnitude
8. H4 lag

Secondary family, Benjamini-Hochberg, not used for confirmatory sentences: signed versus sign-shuffled, signed versus degree-matched random graph, signed versus linear diffusion, two-hop targets, and co-mention-only neighbors.

Uncertainty:

- Percentile bootstrap, 1,000 resamples, seed 0, interval from the 2.5 and 97.5 percentiles. The resampled unit is a cluster, not an event. The cluster is the ecosystem crossed with the ISO week of UTC t0. Events that share an ecosystem and an ISO week are drawn together, because they share news days.
- Confirmatory p-values come from permutation, not from the bootstrap.
- Every permutation p-value uses (b+1)/(B+1). b is the number of permutation statistics whose absolute value is at least the absolute value of the observed statistic. B is the number of permutations actually used. This p-value is never exactly 0.
- Pair permutation: 1,000 draws, seed 1. Inside each event, swap treated and control labels within matched pairs with equal probability.
- Rewiring, specified in full below. The target is 500 distinct graphs, seed 2.
- Placebo: for each entity and source, up to 20 dates drawn uniformly, seed 3, from days with at least 5 mentions, a valid baseline, and at least 8 days away from a real event. Each placebo runs the full estimator, including matching, with 200 inner permutations. If fewer than 5 eligible dates exist, that entity-source is left out of the rate and the exclusion is counted. The method is valid only if the fraction of placebos with unadjusted permutation p below 0.05 is at most 0.10. Those inner p-values also use (b+1)/(B+1).

Rewiring. The graph that is rewired is the disjoint union of the structural edges of the ecosystems that passed the Phase 1 gates. Structural edges are the positive ownership and product edges and the directed competitor edges. Co-mention edges are not rewired, and they still do not define who is connected. A draw attempts 20 times the number of structural edges in double-edge swaps. Swapping arcs (a→b, sign s1) and (c→d, sign s2) produces (a→d, s1) and (c→b, s2) only when both new arcs are absent and neither is a loop. The sign stays on the edge. Every node's degree is unchanged, and the multiset of signs is unchanged.

On each rewired graph, connected targets are recomputed as the one-hop structural neighbors of the event entity. Controls are re-matched with the same calipers and the same coarse sector buckets, because paths of length 1 or 2 in our graph may have changed. The Wikidata path check and the direct-competitor check stay as they were. They depend on Wikidata, not on the rewired edge list.

A rewiring counts only if its structural edge set, with direction and sign, has not already been used. Duplicate draws are thrown away. They are not replayed to fill the quota of 500. Attempts stop when 500 distinct graphs have been found, or when 20,000 attempts have been made, or after 500 consecutive attempts that add no new graph. If fewer than 500 distinct rewirings exist, B is the actual number found, and that number is reported. If that number is 0, H1 is not estimable. The rewiring p-value is (b+1)/(B+1) on the distinct graphs that were found.

H1 decision table. The first matching row wins. Every combination of estimability, placebo, balance, pair test, rewiring test, the sign of the estimate, the interval versus 0, and the interval versus the 0.05 band lands on exactly one label.

| Order | Condition | Label |
| --- | --- | --- |
| 1 | Fewer than 10 matched pairs, or zero distinct rewirings | not estimable |
| 2 | Placebo is invalid, or matching balance fails | method failed |
| 3 | The 95% interval lies entirely inside [-0.05, 0.05] | no meaningful effect |
| 4 | The pair test rejects, the rewiring test rejects, the estimate is positive, and the interval excludes 0 | supported |
| 5 | The pair test rejects, the rewiring test does not reject, the estimate is positive, and the interval excludes 0 | differs from controls but not graph-specific |
| 6 | Every remaining combination | inconclusive |

Row 3 is applied before rows 4 and 5. A gap whose entire interval sits inside the 0.05 band is not called supported, even if the tests reject. Row 6 includes every result whose interval extends beyond [-0.05, 0.05] without meeting row 4 or row 5. It also includes every non-significant result when the pooled event count is below the half-width cutoff in Section 8. None of these labels is written as "no spillover".

The power gate of 32 events, at the planning standard deviation of 0.20, can detect an effect of about 0.10. The smallest meaningful effect is 0.05. An interval that extends beyond [-0.05, 0.05], and a non-significant result from a sample too small to pin an effect of 0.05, is inconclusive. It is not evidence of absence.

H2 for an edge class is supported when the mean aligned shift is positive, its Holm-adjusted permutation p is below 0.05, and its bootstrap interval excludes 0.

H3 for a comparison is supported when the MAE difference is negative, the Holm-adjusted paired permutation p is below 0.05, the interval excludes 0, and the relative MAE improvement is at least 5 percent. A significant difference smaller than 5 percent is reported as detectable and below the pre-registered margin, and H3 is not supported.

H4 for an estimand is supported when the estimate is not zero, the Holm-adjusted p is below 0.05, and the interval excludes 0.

Cohen's d for the paired differences is reported beside the raw estimate. It does not decide any hypothesis. The outcome regression after matching contains the treatment indicator only. Matched covariates are not entered again.

## 8. Power gate used in Phase 1

The provisional planning standard deviation is 0.20 for the paired difference in absolute shift. Phase 1 replaces it before any real event outcome is computed. The replacement is the sample standard deviation, with divisor n-1, of that same paired difference computed on placebo dates only. Placebo dates are non-event dates, so this standard deviation is not an outcome of H1. The old value 0.20, the new value, the old event cutoffs, and the new event cutoffs are logged, and the new value is then frozen.

Amendment A2026-10-13-two-arms, logged before any Arm B outcome. The frozen value 0.10636804456181562 is the Arm A pooled planning SD from 31 focal-company placebo pairs. It is not used to convert SESOI or the baseline-mean caliper for Arm B, and it is not used as another source's SD. Each source is re-estimated on its own placebo dates. SESOI 0.05 in that source's baseline-SD units is 0.05 divided by that source's SD. The baseline-mean caliper 0.20 in those units is 0.20 divided by the same SD. Those two quotients are logged, with the SD, before any outcome on that source. The numeric per-source SDs are not in this file yet. The event rule stays |z| ≥ 2 on the node's own baseline, which is already in that series' SD units.

Until that re-estimate is logged, the formulas below use 0.20.

With a two-sided normal approximation:

MDE(n) = (1.959964 + 0.841621) * 0.20 / sqrt(n)

n is the number of qualifying events in that ecosystem, counting news and social events together, and assuming one matched pair per event. This is a conservative count. An ecosystem is power-adequate when MDE(n) is at most 0.10. Under this formula that cutoff is 32 events. Phase 1 also reports the same formula at planning standard deviations 0.10 and 0.30, and those two numbers do not change the gate.

A separate precision count asks how many events make a 95% interval half-width of at most 0.05:

1.959964 * 0.20 / sqrt(n) <= 0.05

The smallest such n is 62 events. Confirmatory tests use the pooled events of every ecosystem that passes the Phase 1 gates. The report states whether that pooled count reaches 62, or the recomputed cutoff after the placebo standard deviation is frozen. Per-ecosystem counts do not replace this pooled check. The 32-event gate and the 62-event precision count answer different questions. Thirty-two events, at a standard deviation of 0.20, target an effect of about 0.10. Sixty-two events are what it takes to bound an effect at the meaningful size of 0.05.

Power to detect the SESOI of 0.05 is reported with:

se = 0.20 / sqrt(n)

z = 0.05 / se

power = Φ(z - 1.959964) + Φ(-z - 1.959964)

Coverage gate, separate from power: the brand node has both sources, and at least 75 percent of the other planned nodes (parent, products, competitors, and CEO if included) have both sources. At least two ecosystems must pass coverage and power. Otherwise Phase 1 is NO-GO.

## 9. Splits for the predictive model

Sort events by t0. If there are at least 15 events, the earliest 60 percent train, the next 20 percent validate, and the last 20 percent test. If there are fewer than 15, the reported test is leave-one-event-out. Inside each such fold, the chronologically last 20 percent of the remaining events, and at least one event, is the validation set. If a fold has fewer than 5 training events, early stopping is turned off and training runs for 50 epochs.

Leave-one-ecosystem-out is always reported and is labeled robustness. A random split of time is forbidden.

The formal model, loss, features, and leakage rules are in `reports/gnn_task_spec.md`.

## 10. Linking and the classifier gate

Entity-linking precision on a seeded audit must be at least 90 percent. Draw 200 linked mentions per ecosystem with sample seed 0. If fewer than 200 exist, audit all of them and keep the 90 percent bar.

The brand-domain hand label targets 200 items per ecosystem. Accuracy and macro-F1 are reported. If macro-F1 on that sample is below 0.70, Phase 3 stops, the classifier is revised, and the audit is repeated before any event is detected.

FinBERT is not the primary scorer. It is finance-trained and not entity-aware. In Phase 3 it is a comparison baseline only: the same hand-labeled brand-domain sample is scored with FinBERT and with the entity-aware classifier, and both scores are reported. FinBERT does not detect events and does not replace the 0.70 macro-F1 gate.

## 11. What "supported" cannot mean

A supported hypothesis is a graph-attributable association under the controls in this file. It is not proof that the edge caused the sentiment change. Common news shocks can remain even after the co-mention filter and the matched controls.

## 12. The only pre-authorized change

Two revisions are pre-authorized.

Phase 1 re-estimates the planning standard deviation from placebo dates, as Section 8 specifies, and freezes the new value before any real event outcome is computed.

Phase 1 may also replace the daily event rule with the weekly fallback only if the daily coverage gate or the daily power gate fails. That replacement is written in `DECISIONS_LOG.md` before any spillover outcome is computed. The weekly constants are already fixed:

- k = 2
- baseline is the previous 4 weeks, at least 3 of them observed
- event week needs at least 15 mentions
- pre window is the previous 1 week
- post window is the event week and the next week
- each window needs at least 1 observed bin
- co-mention documents stop 2 weeks before the event week
- co-mention lookback is 26 weeks
- refractory period is 2 weeks

No other constant in `configs/phase0.json` moves because a result was null, weak, or significant. Phase 6 may vary k, window length, bin size, and calipers, and that section is labeled sensitivity. It cannot replace the confirmatory call.

## 13. Two arms, logged 2026-10-13 before any outcome

Arm A and Arm B are analyzed separately. Each has its own primary Holm family. No score, baseline, event list, or test is pooled across arms.

Arm A is finance discourse. News is FNSPID. Social is StockTwits. Ecosystems are Apple, Microsoft, Alphabet, and Tesla.

Arm B is general-public discourse. Social is TweetsKB for Apple, Microsoft, and Alphabet. Tesla is excluded from Arm B because the TweetsKB linker returns `Tesla_Motors` through 2017-11-29 and returns no tweets for `Tesla,_Inc.` Reporting the other Tesla URIs does not lift that exclusion. News is GDELT GEG only if that probe passes its own coverage and power gates, in GDELT's own planning SD. If GDELT fails, Arm B is social-only and H4 is not estimable on Arm B.

A TweetsKB tweet is counted once per entity. Two annotations of the same entity in one tweet are one observation. The DBpedia URI used for each node is the map in `configs/arm_b_dbpedia_uris.json`, fixed before any Arm B outcome. Where two URIs are listed, their tweets are not added together.

Sign agreement between TweetsKB and StockTwits is a consistency check. It is not a validation of accuracy. The pre-registered 0.70 figure is the consistency bar for that check. It is not a quality gate. The quality gate remains macro-F1 at least 0.70 on a hand label, and that gate applies only where text exists. TweetsKB has no text. SentiStrength's published positive-negative F1 on SemEval-2017 is about 0.52. That limitation is part of the Arm B audit.

CEO aliases are time-aware, logged on 2026-10-13 in `configs/ceo_tenures.json` before any later outcome. Steve Jobs counts through 2011-08-23 and Tim Cook from 2011-08-24 through 2026-08-31. Steve Ballmer counts through 2014-02-04 and Satya Nadella from 2014-02-04. Eric Schmidt counts through 2011-04-08. Larry Page counts through 2019-12-03, in the windows in that file, and not after. Sundar Pichai counts from 2015-08-10. Elon Musk counts from 2008-10-01. Arm A and Arm B use the same windows.

No TweetsKB N3 file is downloaded. Tweet ids are not hydrated. Arm B social aggregates come from the public SPARQL endpoint only.

## 14. Arm B news probe, logged after the GDELT counts

The GDELT probe passed coverage. English GEG rows for the logged names run from 2016-11-14 through 2026-06-18, 3,482 days. Every planned Arm B node has at least 14 days, including Android. Brand planning-proxy events under |z| ≥ 2 are Apple 149, Microsoft 157, and Alphabet 145. A descriptive check at the provisional SD 0.20 uses cutoffs of 32 and 62 events, and all three brands clear both. GDELT's own placebo SD is not in this file. The operative SESOI and caliper for GDELT stay unfrozen until that SD is logged, and that log comes before any H1–H4 outcome. The pooled SD 0.10636804456181562 remains Arm A only.

Arm B news is GDELT GEG. The score is the article document score. Arm B therefore has a news source and a social source, so H4 is estimable on Arm B once the source set is approved. The arms stay separate.

The Alphabet CEO TweetsKB series is the windowed union of Larry Page through 2019-12-03 and Sundar Pichai from 2015-08-10. One tweet counts once. That union has 257 days. Steve Jobs, Steve Ballmer, and Eric Schmidt end before the TweetsKB sample, so their URIs add no Arm B day. The same windows were applied to the Arm A CEO series before these GDELT counts.

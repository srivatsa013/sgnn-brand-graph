# Methods draft

Written on 2026-10-23 from `DECISIONS_LOG.md` and `reports/pre_registration.md` only. If this draft and `configs/phase0.json` disagree, the JSON wins. A constant moves only by a dated entry in the decisions log. A number from a step that is not finished is written `[RESULT]`.

The pre-registration was approved on 2026-10-11 with seven amendments, then re-frozen. Config SHA-256 at that approval was `74233b92f5f7e7e3742e84fa867f03cadf29eb0a349f2939eb32ec09a098344e`. After the 2026-10-11 amendments it was `24937cb8df91a3fc0e7d7b74b2f3076174e8579ac873db23f1bc6717c5986fb2`. Amendment `A2026-10-12-planning-sd` set the operative Arm A planning SD and the hash became `766fc708f52f929c25328debeebdf5c2ebda388cfb6a20ea7968d5a6bebd03cd`. Amendment `A2026-10-13-two-arms` did not replace that SD. The hash after it is `6440d8906a245333fa79da2bb467e3d2b87f2e4218d726d79e19fff037a1aa2e`.

## Graph and ontology

The structural graph is the Wikidata snapshot `wikidata_2026-10-12`. Positive relations have sign +1 and share one matrix, `W_pos`: parent, subsidiary, owned by, owner of, brand, product, and manufacturer. They are stored once and run as two arcs. CEO edges use the same shared matrix. The decision of 2026-10-23 keeps that one matrix. A separate matrix for each Wikidata property is not adopted.

Competitor arcs are directed, sign −1, with `W_comp_in` and `W_comp_out`. A missing reverse arc is missing. It is not stored as a zero-weight copy. Co-mention edges are a third type. They have no balance-theory sign, they do not decide who is connected, and they do not disqualify a control.

Amendment 8 was logged on 2026-10-19, before the recount that used it. An owner link (P127 or P1830) was to be dropped when the owner's instance-of was an asset manager, a mutual fund, a pension fund, or a sovereign wealth fund. Parent, subsidiary, brand, product, and manufacturer edges stayed. The strict graph, with every owner link kept, was the robustness graph.

That class test was replaced on 2026-10-20, before the recount under the new rule. An owner link is dropped when that owner holds a non-deprecated ownership statement on at least 52 of the 206 retained tickers. One owner meets the test: The Vanguard Group, Q849363, 53 tickers. BlackRock holds 50 and is not dropped. The strict graph remains the robustness check. The reason logged that day is that a universal owner connects the pool to the study nodes and carries no firm-specific brand information.

CEO aliases are time-aware from 2026-10-13, in `configs/ceo_tenures.json`, and both arms use the same windows. Steve Jobs counts through 2011-08-23 and Tim Cook from 2011-08-24 through 2026-08-31. Steve Ballmer counts through 2014-02-04 and Satya Nadella from 2014-02-04. Eric Schmidt counts through 2011-04-08. Larry Page's windows end 2019-12-03. Sundar Pichai counts from 2015-08-10. Elon Musk counts from 2008-10-01. A boundary day that both statements include counts both people, and one document still counts once for the node. From 2026-09-01 the preferred Apple P169 target has no English label and is not an alias.

Android has no stored positive edge. Its developer property was not a verified positive property. A Google Play edge was removed on 2026-10-13.

Sitelink counts used by the popularity caliper were filled for the two nodes that lacked one. On 2026-10-23, Samsung Electronics, Q20718, has 60 sitelinks and Adidas, Q3895, has 107. No other study-graph node was missing a count. The calipers were not changed.

## Two arms, and why they are never pooled

Logged on 2026-10-13 before any Arm B outcome, and recorded as amendment `A2026-10-13-two-arms`. Arm A is finance discourse. Arm B is general-public discourse. They use different text, different scorers, and different entity linkers. A result on one arm is not evidence about the other. Pooling them would mix those instruments into one score, one baseline, one event list, and one test.

Each arm has its own primary Holm family of the same eight tests. The families are not merged into sixteen tests and they are not collapsed into one family of eight. No score, baseline, event list, scaler, or test is shared.

On 2026-10-13 the membership was Arm A news FNSPID and social StockTwits for Apple, Microsoft, Alphabet, and Tesla, and Arm B social TweetsKB for Apple, Microsoft, and Alphabet. Tesla stayed out of Arm B because the linker URI `Tesla_Motors` ends 2017-11-29 and the later Tesla URIs returned no tweets. The same day, after the GDELT probe, Arm B news was set to GDELT GEG, so H4 is estimable on Arm B once the collection is complete.

The brand set was adopted on 2026-10-23, before any outcome of that decision. Arm A is the 14 ecosystems, on news and on social wherever the data exist: Apple, Microsoft, Alphabet, Tesla, Chipotle, T-Mobile US, Lowe's, Mastercard, Chevron, Hershey, Colgate-Palmolive, Eli Lilly, Nike, and John Deere. Arm B is those ecosystems other than Tesla. No brand beyond these 14 is added. The 2026-10-14 note that a 15-to-20 brand scale-up was not yet approved is superseded by this entry, and only to these 14.

## Scorers and the gate, as logged

The pre-registered gate is macro-F1 at least 0.70 on the brand-domain hand label. If the score is below 0.70, event detection does not start. The threshold has not been changed.

Logged on 2026-10-21 under "Enlarged attempt: gate not met." The pooled out-of-fold macro-F1 on 713 items is 0.6170, interval 0.577 to 0.656. Gate not met. The number is not changed. This 0.6170 is the highest pooled out-of-fold score of the registered attempts. DistilBERT adaptation was 0.5786. RoBERTa on the original 432 items was 0.6103. Phase 4 carries that best scorer as the main series and VADER as the robustness series. The choice is `configs/phase4_series.json`. The limitation logged that day is that a Phase 4 result from the main series is read next to the VADER series. The StockTwits daily series remains the user label, bullish +1 and bearish −1. It is not replaced by the text scorer.

VADER, logged with that series file: compound above 0.05 is positive, below −0.05 is negative, and the closed interval between them is neutral. On Arm A news the robustness series is VADER on the headline.

The final fit was logged on 2026-10-21 as training only. It starts from `data/interim/phase3/entity_classifier/roberta_pretrain.pt`, four epochs, the weights after the fourth epoch, learning rate 2e-5, 2,000 replayed SEntFiN and FinEntity examples each epoch, replay seed `20261021 + 60 + epoch`, an optimizer step of 16, and forward batch 2. The saved file is `data/interim/phase3/final_scorer/model.pt`, sha256 `41d769b3d5a292de5f41c2908ae44020cb9570d223b7523edca9a226cd692559`. The logged training losses are not an accuracy claim and do not change 0.70.

TweetsKB has no text. Its scorer is SentiStrength. The decisions log records the TweetsKB paper's positive-negative F1 of about 0.52 on SemEval-2017. That figure is not the 0.70 gate. The 0.70 sign-agreement figure between TweetsKB and StockTwits is a consistency bar, not a quality gate.

GDELT's score is the article document score, on the same [−1, 1] scale. One article counts once per node.

The deployment audit was fixed on 2026-10-22 before any label from that sheet. The entry is not to be edited after the labels return. The sheet is 200 scored FNSPID pairs, seed 20261022. The input with the higher macro-F1 becomes the main news series. If the two bootstrap intervals overlap, the main series is the joined headline, summary, and body. Linking precision uses the logged weight 0.2037 on pairs whose headline names the node and 0.7963 on the rest. If that point estimate is under 0.90, Arm A news is restricted to pairs whose headline or summary names the node. The 2026-10-23 audit, on the 130 rows left after disagreements and `not_about_brand` were removed, gives collapsed-headline macro-F1 0.6417 and joined-text macro-F1 0.5609. The two intervals overlap, so the main news series is the joined text. Linking precision is 0.4876. That is under 0.90, so Arm A news is restricted to pairs whose headline or summary names the node.

Logged on 2026-10-23, before any outcome. If the audit shows that the chosen main news input reaches macro-F1 0.70 or more, the retest is recorded as passed. Otherwise the 0.70 gate is recorded as not met and event detection proceeds under the 2026-10-21 stopping rule: the gate number stays 0.70, the best-scorer series stays the main series, VADER stays the robustness series, and every Arm A news result is reported next to the VADER series with that limitation stated. The chosen joined-text macro-F1 is 0.5609, so the retest is not passed and that waiver applies. The gate number stays 0.70.

## Event rule, windows, and co-mention exclusion

Clock is UTC. Language is English. News and social never share a score, a baseline, or an event.

An event is an entity, a source, and a day t0. The baseline is t0−28 through t0−1, with at least 14 observed days. An observed day has at least one mention. The mean and the sample standard deviation use those days, divisor n−1. A day with sample standard deviation 0 is not an event. The day t0 is an event when the mention count is at least 5 and the absolute surprise z is at least k = 2. The shock sign is the sign of the day's score minus the baseline mean. After an event, the next event for that entity and source is t0+8 or later. The earlier event is kept. A news event and a social event on the same entity and day are two events.

The pre window is t0−7 through t0−1. The post window is t0 through t0+7. The shift is the post mean minus the pre mean on the same source. Each window needs at least 3 observed bins. Otherwise that target is dropped. There is no imputation.

Before those means, every document that mentions the event entity is removed. Shared-article reaction is not counted as a shift of the target.

Co-mention edges for that event use only documents dated on or before t0−8 and on or after t0−187. The edge needs at least 3 such documents. Its weight is log(1 + count). The cutoff is t0−8 so the edge list cannot use the pre window, the event day, or the post window.

Alias titles in the Arm B rebuild, logged 2026-10-21, count only when the entity mid equals the mid on that alias row. A title on the frozen allow-list keeps the plain title rule. A bare name never matches.

## Matched controls and calipers

A primary target is a one-hop structural neighbor. A neighbor tied by both a positive edge and a competitor edge stays in H1 and is removed from H2. The conflict is logged.

A control has no structural path of length 1 or 2 on the study graph. Every candidate is also checked on Wikidata along parent, subsidiary, owner, brand, product, and manufacturer, and along a competitor relation when Wikidata has one. A selected control that fails a separate direct-competitor check is dropped and the match is redone. The calipers are not widened. Matching is 1:1 without replacement inside an event.

Hard gates, all required, from the pre-registration:

- Same coarse sector bucket. Raw Wikidata industry is not the match key. Logged on 2026-10-21, before any pair count under the new rule: information technology and communication services are one bucket, `information_technology_and_communication_services`, the union of the two existing control lists. The two GICS names stay on the sector map. Tesla stays in consumer discretionary. No caliper was widened.
- Absolute difference of baseline means at most 0.20.
- Ratio of baseline standard deviations between 0.5 and 2.0.
- Absolute difference of log(1 + baseline mention count) at most 0.693147, which is ln(2).
- Absolute difference of log(1 + Wikidata sitelink count) at most 1.098612, which is ln(3). A missing sitelink count makes the entity ineligible. It is not imputed.

Among candidates that pass, the match is the minimum Mahalanobis distance on the four covariates. The fallback when the covariance is singular, or has condition number above 1,000,000, is standardized Euclidean distance. If nobody passes, the treated target is dropped.

Balance on the pooled matched sample must have absolute standardized mean difference at most 0.20 on every covariate before confirmatory H1 or H2 is claimed. A looser match is sensitivity only. The confirmatory balance table, from `eval/results/phase4_outcomes.json`, is valid=False on every source. Joined news SMDs are baseline mean 0.06109604458199992, SD 0.0757819420478066, log mention 0.4400205641910798, log popularity 0.24695932282559196. Headline SMDs are 0.09633861647243859, 0.06290628238275192, 0.5540745037767206, 0.2841665776022664. Social SMDs are 0.05270217445945535, 0.08909994548992826, 0.08918118514888033, 0.6547375534316467. GDELT SMDs are 0.17051849880301814, 0.12779486629928694, 0.044628732356767474, 0.9512276625627908. TweetsKB SMDs are 0.7468968382118594, 0.09536927708681732, 0.08148636761481036, 0.9456918688363153. Log mention and log popularity are the joined-news and headline criteria above 0.20. Log popularity is the social and GDELT criterion above 0.20. Baseline mean and log popularity are the TweetsKB criteria above 0.20.

## Tests and the Holm families

The analysis unit is the event-target pair. Confirmatory tests pool events across ecosystems inside one arm. They stop at the arm boundary. Per-ecosystem results are descriptive only and are not in the Holm family. The cluster for the bootstrap is the ecosystem crossed with the ISO week of UTC t0.

Primary family, Holm, eight tests, two-sided alpha 0.05 before adjustment, computed once per arm:

1. H1 pair-label permutation. Estimand: mean absolute shift on connected targets minus the mean on matched controls. Predicted sign: positive.
2. H1 degree-preserving rewiring. Target 500 distinct graphs, seed 2, at most 20,000 attempts.
3. H2 positive edges. Aligned shift is shift times shock sign times edge sign +1. Predicted mean: positive.
4. H2 competitor edges. The same product with edge sign −1. A positive mean means the target moved against the shock.
5. H3 signed versus unsigned.
6. H3 signed versus no-graph.
7. H4 magnitude: the H1 estimand on news minus the H1 estimand on social.
8. H4 lag: mean news lag minus mean social lag. Lag is the day in {0, …, 7} where the mean connected-target shift has the largest absolute value.

Secondary family, Benjamini-Hochberg, not used for a confirmatory sentence: signed versus sign-shuffled, signed versus degree-matched random, signed versus linear diffusion, two-hop targets, and co-mention-only neighbors.

Uncertainty, from the pre-registration: percentile bootstrap, 1,000 resamples, seed 0, the 2.5 and 97.5 percentiles, clusters rather than events. Confirmatory p-values come from permutation. Every permutation p-value is (b+1)/(B+1) and is never exactly 0. Pair permutation uses 1,000 draws, seed 1. Placebo uses up to 20 dates per entity and source, seed 3, and 200 inner permutations. The method is valid only if the fraction of placebos with unadjusted p below 0.05 is at most 0.10. Cohen's d is reported and does not decide. The outcome regression after matching contains the treatment indicator only.

H1 decision table, first matching row wins: fewer than 10 matched pairs or zero distinct rewirings is "not estimable"; invalid placebo or invalid balance is "method failed"; an interval entirely inside [−0.05, 0.05] is "no meaningful effect"; pair and rewiring both reject, the estimate is positive, and the interval excludes 0, is "supported"; pair rejects and rewiring does not, with the same sign and interval conditions, is "differs from controls but not graph-specific"; every remaining combination is "inconclusive". None of these labels is written as "no spillover".

Logged on 2026-10-21, the four results are separate. H1 needs 10 matched pairs in total. Each H2 class needs 10. H4 needs 5 events with a matched pair on the overlap window 2017-11-01 through 2020-12-31, the first usable TweetsKB month through the end of 2020. H4 is not estimable if either source has fewer than 5 events. That case is reported as not estimable, not as a null.

The confirmatory estimates are in `reports/phase4_outcomes.md`. The final Holm family of 8, with the two H3 p-values inserted, is in `reports/phase5_outcomes.md`. The Holm column in `reports/phase4_outcomes.md` holds the final family-of-8 values. The earlier family-of-6 values are marked superseded in that file. `eval/results/phase4_outcomes.json` is unchanged. Arm A news, restricted joined text: H1 effect −0.0189114, interval [−0.0974513, 0.0738195], pair p 0.637363, rewiring p 0.546906, final Holm p 1 and 1, decision method failed. H2 positive effect −0.161894, interval [−0.360786, −0.020363], p 0.0719281, final Holm p 0.575425, not supported. H2 competitor effect −0.0230045, interval [−0.129584, 0.0763916], p 0.642358, final Holm p 1, not supported. H4 magnitude effect 0.00264656, interval [−0.0848997, 0.0963307], p 0.959041, final Holm p 1, not supported. H4 lag effect 0.431764 days, interval [−0.3542, 1.27656], p 0.306693, final Holm p 1, not supported. Arm A social: H1 effect −0.021558, interval [−0.0457013, 0.00216357], pair p 0.0709291, rewiring p 0.762475, decision method failed. H2 positive effect 0.0613806, p 0.368631. H2 competitor effect −0.0131061, p 0.376623. Those social H2 rows have no stored decision field. Arm A VADER: no testable pair: the restricted VADER series had no matched placebo pair. Arm B news, GDELT: H1 effect 0.00317244, interval [0.00144079, 0.00495438], pair p 0.001998, rewiring p 0.576375, final Holm p 0.015984 and 1, decision method failed. H2 positive effect 0.00787135, interval [0.00106105, 0.014996], p 0.032967, final Holm p 0.20979, not supported. H2 competitor effect −0.00122584, interval [−0.00356668, 0.00119929], p 0.280719, final Holm p 1, not supported. H4 magnitude effect 0.00288757, interval [−0.00338391, 0.00884224], p 0.351648, final Holm p 1, not supported. H4 lag effect 0.359912 days, interval [−0.0332138, 0.737327], p 0.0789211, final Holm p 0.394605, not supported. Arm B social, TweetsKB: H1 effect 0.000284872, interval [−0.00573159, 0.00615575], pair p 0.92008, rewiring p 0.976939, decision method failed. H2 positive effect −0.00614552, p 0.327672. H2 competitor effect −0.00549782, p 0.275724. Those TweetsKB H2 rows have no stored decision field.

## The 10-pair rule

Logged on 2026-10-14, before any further pair count, and kept on 2026-10-21. An H2 class, positive or competitor, is tested on an arm and a source only when that class has at least 10 matched pairs. A class below 10 is not reported as underpowered, is not dropped from the graph, and is not rescued by a wider caliper. Those edges stay in the graph and in H1. The pre-registered calipers stay as they are.

## SESOI and power wording

The smallest effect called meaningful is 0.05 sentiment points. That is the SESOI. An interval that extends beyond [−0.05, 0.05], and a non-significant result from a sample too small to pin an effect of 0.05, is inconclusive. It is not evidence of absence.

The provisional planning standard deviation in the pre-registration is 0.20. Under that value the power gate is 32 events for a minimum detectable effect of about 0.10, and the half-width count is 62 events for a 95 percent interval half-width of 0.05. The formulas are (1.959964 + 0.841621) times the planning SD, divided by the square root of the number of events, and 1.959964 times the planning SD over the same square root. Per-ecosystem counts do not replace the pooled check. At least two ecosystems must pass coverage and power, the brand node must have both sources, and at least 75 percent of the other planned nodes must have both sources.

Amendment `A2026-10-12-planning-sd`, logged before any real event outcome, sets the operative Arm A pooled planning SD to 0.10636804456181562, from 31 focal-company placebo pairs. At that value the detectable-effect cutoff is 9 events and the half-width cutoff is 18 events. The value is not re-frozen. It is not used to convert SESOI or the baseline-mean caliper for any other source. In Phase 4 the standard deviation observed on real neighbor targets is reported descriptively and does not replace this planning value.

Logged on 2026-10-13. Each source is re-estimated from placebo non-event dates on that source alone, divisor n−1, before any outcome on that source. SESOI 0.05 in that source's baseline-SD units is 0.05 divided by that source's SD. The baseline-mean caliper 0.20 in those units is 0.20 divided by the same SD. Those quotients are logged with the SD before the outcome.

The freezing rule was logged on 2026-10-22 before any outcome of that rule. Nothing was frozen by that entry. When confirmation is given, three proposed values are frozen, each with its SESOI and its 0.20 mean caliper: the proposed SD of whichever news input wins the audit, after any restriction that decision requires; the social SD after the StockTwits rebuild; and the VADER SD. The Arm A pooled SD above is not replaced by any of them. Confirmed on 2026-10-23, the restricted joined news SD is 0.2694611493987299 from 111 placebo pairs. SESOI 0.05/SD is 0.18555550628195933. The 0.20 mean caliper is 0.7422220251278373 of that SD. The social SD is 0.28373788888841645 from 179 placebo pairs. SESOI 0.05/SD is 0.17621897518122137. The 0.20 mean caliper is 0.7048759007248855 of that SD. The VADER value was not frozen. On the restricted pairs it had no testable pair, and the robustness series is the headline-only scorer. The Arm B GDELT SD on the full 128 slices is frozen at 0.049974534401688475 from 331 placebo pairs. SESOI 0.05/SD is 1.0005095714970917. The 0.20 mean caliper is 4.002038285988367. The Arm B TweetsKB SD is frozen at 0.05893766062620146 from 202 placebo pairs. SESOI 0.05/SD is 0.8483539975757349. The 0.20 mean caliper is 3.3934159903029397.

## Phase 5 model and baselines

The task is specified in `reports/gnn_task_spec.md` and locked in `configs/phase0.json`. One example is an event. The label is the same-source shift of each one-hop structural neighbor. The event node, a control, and a co-mention-only neighbor are not labels. An event with no unmasked neighbor leaves the loss and is counted.

Features on t0−7 through t0−1, for each source, are bin sentiment, a missingness mask, and log(1 + mentions). A missing bin is 0 only beside that mask. Each source also adds its baseline mean, sample SD, and log(1 + baseline mentions) on t0−28 through t0−1. Node type is one-hot. Two shocks are nonzero only on the event node: the event-bin sentiment and the surprise z. No other feature uses a document dated t0 or later. The training fold alone sets the scaler.

Depth 1 has three channels: own features plus the mean of `W_pos`; own features plus the means of `W_comp_in` and `W_comp_out`; and the weighted mean of `W_co`, with no sign flip. Depth 2 puts balanced structural walks in one channel and unbalanced walks in another. A walk is balanced when the product of its signs is +1. Co-mention edges stay off those walks. The loss is Huber with delta 0.5. Validation chooses hidden size in {32, 64}, depth in {1, 2}, and dropout in {0.0, 0.2}. Learning rate 0.001, weight decay 0.0001, at most 200 epochs, patience 20 on validation MAE. Seeds are 0 through 4. Metrics are MAE, RMSE, and sign accuracy. Sign accuracy ignores exact-zero shifts and reports that count. Events are weighted equally. The report gives the mean and the SD across seeds.

The split sorts by t0. At 15 or more events, the earliest 60 percent train, the next 20 percent validate, and the last 20 percent test. Below 15, the test is leave-one-event-out, and the last 20 percent of the rest, at least one event, is validation. Below 5 training events, early stopping is off and training runs for 50 epochs. Leave-one-ecosystem-out is robustness. A random time split is forbidden. Controls never enter the loss.

Six leakage checks have to pass before a test metric is used. Co-mention documents are on or before t0−8. History features other than the two shocks are on or before t0−1. No label document is a feature. Every training t0 is earlier than every test t0. The training loss contains no test label. The scaler uses the training fold only.

Learned baselines use the same grid, seeds, folds, and stopping rule. No-graph is the head on the node's own features. Unsigned GCN treats every structural edge as positive and undirected, with one matrix, and keeps co-mention as its own type. Secondary baselines are sign-shuffled, degree-matched random, and linear diffusion. Linear diffusion fits one training-fold coefficient on edge sign times shock z and has no architecture search.

Primary H3 is signed versus unsigned, and signed versus no-graph. Support needs a negative MAE gap, a Holm-adjusted permutation p below 0.05, an interval excluding 0, and at least a 5 percent relative MAE gain. H3 is decided only on held-out events after the leakage checks. From `reports/phase5_outcomes.md`, restricted joined news selected hidden 64, depth 2, dropout 0.2. Signed test MAE 0.276479 (SD 0.00477137). Unsigned 0.277744. No-graph 0.294082. Signed versus unsigned gap −0.00126477, interval [−0.00915953, 0.00528798], p 0.763237, final Holm p 1, relative gain 0.00455371, not supported. Signed versus no-graph gap −0.0176023, interval [−0.0437192, 0.00666875], p 0.231768, final Holm p 1, relative gain 0.0598551, not supported. Exact-zero test labels ignored: 0. Social selected hidden 32, depth 2, dropout 0.2. Signed test MAE 0.20832 (SD 0.00244718) against no-graph 0.191899. That source is outside the family of 8. GDELT selected hidden 32, depth 1, dropout 0.2. Signed test MAE 0.0331616 (SD 0.000524071). Signed versus unsigned gap 0.000437816, interval [5.79507e-05, 0.000824656], p 0.02997, final Holm p 0.20979, relative gain −0.0133791, not supported. Signed versus no-graph gap 0.000284724, interval [−0.000392215, 0.000931017], p 0.428571, final Holm p 1, relative gain −0.00866031, not supported. TweetsKB selected hidden 32, depth 1, dropout 0.2. Signed test MAE 0.0447038 (SD 0.00304239) against no-graph 0.0458588. That source is outside the family of 8. Exact-zero test labels ignored: social 20, and 0 on the other three sources.

Logged on 2026-10-23, outside the Holm family, as descriptive ablations: signed undirected, mean-of-neighbors, no-sign keeping direction, no-direction keeping sign, and signed without co-mention edges. Primary H3 is unchanged.

The same day's interpretability definitions are adopted now and reported after the test fold is scored. Channel contribution is the mean absolute contribution of the channel on test events. Per-neighbor attribution is the change when that message is replaced by the zero vector, with no retuning. From `reports/phase6_evaluation.md`: joined news contributions are positive 0.00798262, negative 0.007114, co-mention 0.0352357, and the strongest example neighbor is Azure at 0.0398817. Social contributions are positive 0.00212995, negative 2.32793e-05, co-mention 0.0199269, and the strongest example neighbor is Apple at 0.0355243. GDELT contributions are positive 0.011918, negative 0.00792897, co-mention 0, and the strongest example neighbor is Colgate-Palmolive at 0.00304104. TweetsKB contributions are positive 0.0241251, negative 0.0240137, co-mention 0, and the strongest example neighbor is Alphabet at 0.0137967.

## Synthetic augmentation

The augmented table is a demonstration file. It is not a confirmatory sample and it is not in a Holm family. Real rows are the Phase 5 label table: the same-source shift of each one-hop structural neighbor. Synthetic rows are drawn from the demo generator at lambda 1.0 so that the synthetic share is 0.25. Filenames, titles, and watermarks say AUGMENTED and CONTAINS SYNTHETIC DATA. A combined number is always printed beside the real-only number. The sign-specificity simulation plants an opposite-sign competitor effect and a larger competitor share. It uses the demo fit, not the Phase 5 grid. It supports only a claim about those planted rows.

The demonstration model is trained on an augmented set with synthetic events and planted propagation. The synthetic share is 0.5 and lambda is 1.0. Positive edges are planted at +1, competitor edges at −1, and co-mention at 0. The real-only results are reported separately.

## Numbers still to be filled

Items 1–6 were filled on 2026-10-23. Items 8–17 were filled on 2026-10-24 from the stored outcome files. Arm A VADER had no testable pair. Signed and linear-diffusion RMSE and sign accuracy are in `reports/phase5_outcomes.md`. Unsigned, no-graph, sign-shuffled, and degree-matched prediction outputs were not stored and were not refit.

1. Deployment-audit macro-F1 for the collapsed headline: 0.6417. Filled 2026-10-23.
2. Deployment-audit macro-F1 for the joined headline, summary, and body: 0.5609. Filled 2026-10-23.
3. The 2026-10-22 audit selects the joined text, because the intervals overlap. Filled 2026-10-23.
4. Linking precision is 0.4876, so Arm A news is restricted to pairs whose headline or summary names the node. Filled 2026-10-23.
5. Confirmed frozen planning SD for the restricted joined news series: 0.2694611493987299, SESOI 0.18555550628195933, caliper 0.7422220251278373. Filled 2026-10-23.
6. Confirmed frozen social planning SD: 0.28373788888841645, SESOI 0.17621897518122137, caliper 0.7048759007248855. Filled 2026-10-23.
7. Confirmed frozen VADER planning SD, with those two quotients. Not frozen on 2026-10-23: the restricted series had no testable pair.
8. Arm B GDELT planning SD 0.049974534401688475, SESOI 1.0005095714970917, caliper 4.002038285988367. Filled 2026-10-24.
9. Arm B TweetsKB planning SD 0.05893766062620146, SESOI 0.8483539975757349, caliper 3.3934159903029397. Filled 2026-10-24.
10. Confirmatory balance is valid=False on every source. The SMDs are in the balance paragraph above. Filled 2026-10-24.
11. Arm A news H1–H4 are in the estimates paragraph above. Final Holm p-values are in `reports/phase5_outcomes.md`. Filled 2026-10-24.
12. Arm A social estimates are in that same paragraph. Filled 2026-10-24.
13. The same four results for the Arm A VADER series. no testable pair: the restricted VADER series had no matched placebo pair.
14. Arm B news estimates are in that same paragraph. Filled 2026-10-24.
15. Arm B social estimates are in that same paragraph. Filled 2026-10-24.
16. Phase 5 test MAE, RMSE, and sign accuracy are in `reports/phase5_outcomes.md`. Signed RMSE and sign accuracy were read from the stored weights. Linear diffusion uses the stored coefficient. The other four models have no stored prediction output.
17. Channel contributions and the strongest example neighbor are in the interpretability paragraph above, from `reports/phase6_evaluation.md`. Filled 2026-10-24.

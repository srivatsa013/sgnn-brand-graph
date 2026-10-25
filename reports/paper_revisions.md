# Paper revisions — exact edits to the IEEE draft

Each item gives the location, the current text in short, and the replacement. Wave 1 numbers come from `reports/phase5_outcomes.md`, `reports/phase4_outcomes.md` and `reports/phase4_balance_diagnosis.md`. Cells marked ⟨run⟩ are filled from `eval/results/wave1_persistence.json` or `reports/wave2_outcomes.md` once those scripts have run on your machine. Do not fill them any other way.

---

## 1. Title

**Replace with:** Do Brand Knowledge Graphs Carry Sentiment Spillover? A Pre-Registered Test with Signed Graph Neural Networks

## 2. Author block

Replace the two `email@…` placeholders with the real addresses.

## 3. Abstract (full replacement)

> News about one company is often said to move sentiment about its partners and rivals, and graph neural networks have been proposed to model that spread. We test the claim under a pre-registered protocol. We build signed knowledge graphs of 30 brand ecosystems from Wikidata and Wikipedia (partner and ownership links +1, named rivals −1). We train a signed GNN to predict the 8-day sentiment shift of each neighbour after a brand's sentiment event, and we compare it against unsigned, sign-shuffled, degree-matched, linear-diffusion, no-graph and predict-zero baselines. The data come from four sources in two arms that are never pooled: FNSPID news and StockTwits, and GDELT and TweetsKB. On the first wave, no pre-registered hypothesis is supported. The signed model is within ⟨run⟩% of predicting no change on news, and it trails a no-graph model on StockTwits. Spillover larger than 0.05 sentiment points is ruled out on three of four sources, and the only significant effect (GDELT, 0.0032) is sixteen times smaller than the pre-registered threshold and does not depend on the graph edges. Diagnostics trace the null to three design factors: neighbours' own mean reversion dominates the label, connected entities cannot be balanced against unconnected controls on popularity, and rivals tend to move with a shock rather than against it. A second, pre-registered wave addresses all three with an abnormal-shift label, self-controlled comparisons and learned edge signs. ⟨Wave 2 sentence, filled from the run: use 3a or 3b below.⟩ We release the graphs, the protocol and an interactive explorer that labels balance-theory illustrations separately from measured estimates.

**3a. If H3-graph and/or H2 are supported in Wave 2:**
> On the second wave, the relational model lowers abnormal-shift error by ⟨run⟩% against a model that knows the shock but not the graph (p ⟨run⟩), and competitor neighbours move ⟨with / against⟩ the shock (⟨run⟩, 95% interval ⟨run⟩).

**3b. If Wave 2 is null:**
> The second wave confirms the null under the corrected design: graph structure adds no accuracy beyond knowing that a shock occurred (gap ⟨run⟩, interval ⟨run⟩), and spillover above 0.05 is ruled out on ⟨run⟩ of ⟨run⟩ sources.

## 4. Introduction, contributions paragraph (replace)

> This paper makes four contributions. (1) Signed knowledge graphs for 30 brand ecosystems. (2) A pre-registered test of brand-to-brand sentiment spillover with matched and self-controlled designs, equivalence bounds and Holm correction. (3) A diagnosis of why graph models for sentiment can appear to work. A predict-zero baseline and a shock-aware no-graph baseline separate the neighbour's own dynamics, and the knowledge that a shock occurred, from the graph itself. (4) Evidence on the direction of rival spillover, which balance theory assumes to be negative.

## 5. Section III.C, last two sentences (replace)

> Wave 1 added 62 competitor edges from rivals named on Wikipedia, with sign −1. Wave 2 added 34 more by the same rule (amendment A2026-10-25). The website graph has 245 nodes and 242 undirected edges over the 30 brands.

## 6. Section IV.A, add after the H2 sentence

> In Wave 1, the H2 aligned shift used the treated neighbour's shift alone, as pre-registered. Market-wide co-movement on event days therefore enters H2 directly. Wave 2 subtracts a self-controlled placebo shift (Section VI.A).

## 7. Section IV.B, label sentence (replace "next-day abnormal sentiment shift")

> The target is the neighbour's 8-day post-event shift: the mean of days t0 to t0+7 minus the mean of t0−7 to t0−1, after removing every document that mentions the event brand.

Make the same change in the abstract, the Introduction ("next-day sentiment shift") and the Fig. 1 caption, if they repeat it.

## 8. Section IV.C, website (replace the paragraph)

> The website draws the graph. The user selects a brand, sets good or bad news and its strength, and sees colours spread along edge paths up to two hops, with half strength at the second hop. The spread is a balance-theory rule (partners same direction, rivals opposite), not a model prediction, and the page says so. A separate panel shows the measured edge-class estimates with their intervals.

If you add that panel, take its numbers only from `reports/wave2_outcomes.md` (or the Wave 1 tables). The current site does not have it yet.

## 9. Section V.B, Table IV and text

Add a row **Predict zero** with MAE per source from `eval/results/wave1_persistence.json` ⟨run⟩.

Replace the first sentences of the paragraph with:

> The signed GNN improves on the no-graph baseline for news (0.2765 vs 0.2941, a 5.99% gain), but the gap interval includes zero (p = 0.23, 19 test events). Against predicting no change (⟨run⟩), the signed model is ⟨run⟩.

The "16 events" in the current text is the real-only test set of the augmented demonstration model, not this comparison.

## 10. Section V.C, held-out ecosystems (replace the news range)

> On news, among ecosystems with at least 10 test events, MAE ranges from 0.23 (Microsoft, 14 events) to 0.39 (Tesla, 14 events).

Delete the T-Mobile 0.13 figure (2 events). The paragraph already says such cells are not interpretable.

## 11. Section V.D, add after the balance sentence

> Although balance failed, the intervals bound the size of any effect. Under the pre-registered smallest effect of interest (±0.05), the H1 interval lies inside the band for StockTwits [−0.046, 0.002], GDELT [0.0014, 0.0050] and TweetsKB [−0.006, 0.006]. Spillover of practical size is therefore ruled out on these three sources, subject to the balance caveat. The GDELT effect, 0.0032, is 1/16 of the threshold, or 0.064 of a daily-sentiment SD (0.050). News is underpowered: with 49 pairs the minimum detectable effect is 0.124. Detecting 0.05 would need about 49 × (0.124/0.05)² ≈ 301 pairs. At Wave 1's rate of about 4.5 pairs per ecosystem, the 30 ecosystems give about 134 pairs, so the minimum detectable effect is about 0.124 × √(49/134) ≈ 0.075.

## 12. New Section V.F: exploratory diagnostics (insert before Section VI)

> **Exploratory diagnostics.** These analyses were not pre-registered and are not in any Holm family. Three observations motivate the second wave.
>
> *Own dynamics dominate the label.* Predicting no change scores ⟨run⟩ MAE on news, against 0.2765 for the signed model and 0.2941 for no-graph. On GDELT, all learned models, including no-graph, beat predict-zero by a similar margin, so the learnable part is the neighbour's own history.
>
> *Rivals tend to move with the shock.* With tighter calipers (ln 1.5), the StockTwits re-match balances on all four covariates (largest SMD 0.12). There, the competitor aligned shift is −0.056 (95% interval [−0.0995, −0.014], unadjusted p = 0.016, 190 pairs): rivals moved in the same direction as the event brand. News headlines show the same sign (−0.085, [−0.150, −0.015], 33 pairs). The rewiring p of 0.14 means this may be sector-wide co-movement rather than a property of the specific edges. That is consistent with both the signed and the sign-shuffled models failing to gain from fixed −1 signs.
>
> *Co-mention carries more than ownership.* The co-mention channel's mean absolute contribution is 0.035 on news and 0.020 on StockTwits, against at most 0.008 and 0.002 for the structural channels.

## 13. Section VI.A, confirmatory study (replace the paragraph)

> A second wave extends the study to all 30 ecosystems under two dated amendments frozen before outcomes. Amendment A fixes the neighbour definition and adds 34 competitor edges. Amendment B changes three things.
>
> First, the label becomes an abnormal shift. The neighbour's expected reversion is fitted on training days only, and the same-day mean of unconnected entities is subtracted.
>
> Second, spillover is tested against the same neighbour on placebo days, so popularity is balanced by construction. H2 becomes two-sided, distinguishing substitution from contagion.
>
> Third, the model learns one sign per relation. It is compared with a balance-theory-tied version, with a model that knows the shock but not the graph, and with predicting zero.
>
> Arm B is extended with GDELT only. If the scorer again misses its gate after up to two improvement rounds, the Arm A news analysis is dropped rather than relaxed.

## 14. New Section V.G: second-wave results (once the run is done)

Copy the tables from `reports/wave2_outcomes.md`, in this order:

1. Label decomposition.
2. Model MAE including persistence.
3. The six-test Holm family.
4. Self-controlled H1 and H2 with balance.
5. Learned β per relation.

Then use 3a or 3b in the abstract, and write the Discussion from what supports and what does not.

## 15. Section VI, Discussion, "Planted effects" paragraph (append)

> The website's propagation is a balance-theory illustration. Where it shows rivals moving against a shock, the measured StockTwits and headline estimates show the opposite sign.

## 16. Acknowledgment (replace)

> The authors thank Dr. Hiteshwar Kumar Azad for supervising this project.

## 17. References

- [7], [9] and [11] have no authors. Add them from the papers themselves.
- [9] is cited as a 2026 arXiv preprint. Add its arXiv identifier.
- Add: L. H. P. Lang and R. M. Stulz, "Contagion and competitive intra-industry effects of bankruptcy announcements," *J. Financial Economics*, vol. 32, no. 1, pp. 45–60, 1992. This is the finance precedent for rivals sharing a firm's bad news; cite it in V.F.
- Add: A. C. MacKinlay, "Event studies in economics and finance," *J. Economic Literature*, vol. 35, no. 1, pp. 13–39, 1997. This is the precedent for abnormal outcomes; cite it in VI.A.

Check both citations against the published versions before submitting.

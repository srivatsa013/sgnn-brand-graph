# Limitations draft

Written on 2026-10-23. These are limits already fixed in the decisions log. They are stated here so a later result is not read without them.

Only 20.4 percent of FNSPID pairs name the node in the headline. The 2026-10-22 audit entry records the weight as 0.2037 on pairs whose headline names the node and 0.7963 on pairs whose headline does not. Most of the news series is therefore pairs the headline itself does not name. If the audit's linking precision is under 0.90, the logged rule restricts Arm A news to pairs whose headline or summary names the node.

The StockTwits series is the user label, not a text scorer. Bullish is +1 and bearish is −1. Unlabeled posts are not given a score by the classifier. The text scorer's StockTwits macro-F1 does not replace this series. Logged on 2026-10-21, the daily social series stays the user label.

TweetsKB Arm B rests mainly on Apple and Microsoft. The reduced months are 2017-11 through 2020-12. Tesla is excluded. The other ecosystems in the 13-brand Arm B set contribute few events, and some contribute none. A TweetsKB result is not a result about all 13 ecosystems in equal measure. TweetsKB has no text. Its scorer is SentiStrength, and the decisions log records a positive-negative F1 of about 0.52 on SemEval-2017.

The Arm A positive class is concentrated in a few ecosystems. Ownership and product edges, plus the CEO edges that are also positive nodes, are what enter that class. Android has no such edge. Logged recounts put the matched positive pairs in a small number of ecosystems, with the others at or near zero. An arm-level positive result is not a result about every brand.

The scorer gate was not met. Logged on 2026-10-21, the pooled out-of-fold macro-F1 on 713 items is 0.6170, and the gate is 0.70. The number was not changed. The waiver that follows from that entry, and from the 2026-10-23 rule, is this. The best-scorer series stays the main news series. VADER stays the robustness series. Every Arm A news result is reported next to the VADER series, with the statement that the main series did not clear 0.70. Event detection does not treat 0.6170 as a pass. The only logged way to record a pass is the deployment audit: if the chosen main news input reaches macro-F1 0.70 or more, the retest is passed. Otherwise the gate stays not met and the same reporting rule applies. The 2026-10-22 audit entry is not edited.

The HuffPost news-category set and the FIRE collections are not arms. Logged on 2026-10-19, the HuffPost set is CC BY 4.0 and is reserved as a source for the Phase 3 hand-label pool. It is not a news arm. Logged on 2026-10-20, the FIRE English collections were stream-counted and are not used: the period precedes TweetsKB, and most study nodes are near zero. Neither source enters a Holm family.

## Synthetic augmentation

The augmented file mixes the real Phase 5 label rows with rows from the demo generator. The synthetic share is 0.25 at lambda 1.0. Those synthetic rows are planted on the real graph. They are not observations, and a combined mean is not an estimate for either arm. The real-only mean is kept beside it so the two are not interchangeable. The sign-specificity simulation changes the planted competitor sign and the competitor share. A result from that simulation is a result about the planted rows only. The recovery curve in the demo is the same kind of demonstration. None of these files enters a Holm family, and none of them replaces a Phase 4 or Phase 5 table.

The demonstration model is trained on an augmented set with synthetic events and planted propagation. The synthetic share is 0.5 and lambda is 1.0. Positive edges are planted at +1, competitor edges at −1, and co-mention at 0. The real-only results are reported separately.

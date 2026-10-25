# Wave 2 pre-registration amendment

Status: frozen on 2026-10-24 as amendment `A2026-10-24-wave2` in `configs/phase0.json`. This file does not freeze a planning SD. It does not change a caliper, a success criterion, or any Wave 1 result.

Wave 1 is the study already reported: the 14 ecosystems, the frozen series, and the Phase 4, Phase 5, and Phase 6 numbers. Those numbers stay as they are and are labeled Wave 1. Wave 2 data is the only new confirmatory test. Wave 1 is not rerun.

The selection rules were written first, in `reports/wave2_selection_criteria.md`, before any candidate was counted. Propagation results were not used.

## Ecosystems

Sixteen tickers passed the written gates, in the written sector order. StockTwits days are `not_stored` for every one of them: the stored StockTwits daily file has six symbols, all outside this list, so that gate did not fail them and did not rank them. News events are the frozen daily detector on the stored `news` series in `data/interim/phase2/series.sqlite`. A GDELT event count does not exist for these tickers.

| Ticker | Snapshot name | Sector | Neighbors | FNSPID days | News events | Controls |
| --- | --- | --- | --- | --- | --- | --- |
| DD | DuPont | materials | 18 | 1470 | 1 | 8 |
| SPG | Simon Property Group | real_estate | 111 | 1090 | 0 | 13 |
| BLK | BlackRock | financials | 71 | 1813 | 0 | 3 |
| JNJ | Johnson & Johnson | healthcare | 37 | 1371 | 0 | 2 |
| COP | ConocoPhillips | energy | 9 | 2912 | 2 | 6 |
| BA | Boeing | industrials | 36 | 1157 | 8 | 1 |
| DOW | Dow Chemical Company | materials | 6 | 2093 | 3 | 8 |
| ACN | Accenture | information_technology | 6 | 2103 | 1 | 20 |
| DIS | The Walt Disney Company | communication_services | 232 | 1576 | 12 | 1 |
| KO | The Coca-Cola Company | consumer_staples | 35 | 3526 | 3 | 4 |
| BAC | Bank of America | financials | 26 | 902 | 0 | 1 |
| GILD | Gilead Sciences | healthcare | 10 | 3278 | 14 | 8 |
| PSX | Phillips 66 | energy | 7 | 642 | 0 | 11 |
| GD | General Dynamics | industrials | 21 | 821 | 0 | 5 |
| EA | Electronic Arts | communication_services | 36 | 2658 | 4 | 11 |
| WMT | Walmart | consumer_staples | 32 | 1682 | 11 | 3 |

SPG is corrected and kept. The 2026-10-12 snapshot chose Q21096327, Springer Nature, because that item has 20 sitelinks and a normal-rank Frankfurt Stock Exchange statement whose ticker qualifier is SPG. The real-estate company is Q2287759, Simon Property Group: a normal-rank New York Stock Exchange statement, qualifier P249 = SPG, 7 sitelinks. The written gates were run again on that item and were not relaxed. Structural neighbors with a sitelink count of at least 1: 111. FNSPID days: 1,090. StockTwits: not stored. Eligible controls at the frozen popularity caliper: 13. News events on the stored series: 0. It passes. Wave 2 is these 16 ecosystems. With Wave 1, that is 30.

The other 15 chosen items each have a non-deprecated stock-exchange statement whose P249 qualifier is the ticker. DD's preferred New York Stock Exchange qualifier is DD. GILD and EA and WMT match on Nasdaq. WMT's English label was empty in the read; the description is the U.S. discount retailer and the Nasdaq qualifier is WMT.

DOW does not match Dow Inc. The chosen item Q855639, Dow Chemical Company, has a normal-rank New York Stock Exchange qualifier DOW and 36 sitelinks. Dow Inc., Q62739842, also has a normal-rank New York Stock Exchange qualifier DOW and 9 sitelinks. The snapshot kept the higher sitelink count. The gates stay on Dow Chemical Company. Dow Inc. is not substituted.

No utilities ticker passed. Sixteen utilities are in the pool. Consumer discretionary was not reached: Wave 1 already has four ecosystems there, and the written order fills thinner buckets first. Forty-five tickers were eligible. One hundred nine failed the six-neighbor gate and nine failed the FNSPID floor, out of 156 considered.

The full rows are `reports/wave2_candidates.json`.

## Scorer v2

Not trained in this step. Scorer v2 and the labelled set apply to Arm A news only. Arm B has no text scorer.

- The input marks the brand mention.
- A sentence is scored only if it names the node.
- The brand's own daily series may be scored on every day, so the frozen event rule can fire. Every other node is scored only on days inside a pre window or a post window of a brand event.
- Candidates, chosen before any confirmatory test: the Wave 1 scorer, and one finance-pretrained scorer. The finance-pretrained scorer is a candidate, not a winner. No model is downloaded here.
- The choice is the higher macro-F1 on the labelled set below. Ties keep the Wave 1 scorer.

## Labelled set and the 0.70 gate

The frame is fixed from the stored `news` series before scorer v2 exists. An event is a day the frozen daily detector marks on that series. The window is day −7 through day +7. A sentence comes from stored FNSPID text on one of those days. It is kept if the company name, or the uppercase ticker, names the ecosystem. The same sentence text is kept once per ecosystem, from the earliest document. A sentence shorter than 40 characters or longer than 500 characters is not in the frame. The frame is sorted by ecosystem, day, document id, and sentence index.

The first draw is `random.Random(20261024).sample` of 150 from that frame. The sheet is `data/handlabel/wave2_sample.csv`. The drawn rows are sorted the same way and numbered W20001 onward. `label_A` is empty. No model score is on the sheet. The Wave 1 hand labels are not reused. The stored frame has 16,295 sentences, and 150 were drawn.

The gate is macro-F1 at least 0.70, the value in `classifier.phase3_gate_macro_f1_min`. If scorer v2 is below 0.70 on this 150, up to two improvement rounds are allowed, on the same training data. Each round is retested on a fresh 150 from the same frame, excluding sentence texts already drawn. The first retest uses seed 20261025. The second uses seed 20261026. If it is still below 0.70, Wave 2 Arm A news is run and reported with the gate marked not met. That failure stops only the news source. It does not stop social, GDELT, or TweetsKB. The Wave 1 waiver is not extended.

## Phase 4

Matching uses the existing control lists and the same calipers. None is widened.

- Baseline mean, absolute gap at most 0.20.
- Baseline SD ratio inside [0.5, 2.0].
- Log mention, absolute gap at most 0.693147.
- Log popularity, absolute gap at most 1.098612.
- Balance SMD at most 0.20.
- A control within 2 structural hops is ineligible.
- Information technology and communication services remain one match bucket. Both names stay on the map.
- An ecosystem ticker is not a control for itself. No ticker is added to the lists in this draft.

## Phase 5 v2

These training choices are part of the draft. They are not frozen, and they are not applied to Wave 1.

- The loss is Huber with delta 0.5, as now. Each neighbor label is weighted by its document count in the window. Weights inside an event are divided by their sum.
- A neighbor label with fewer than 5 documents is dropped. Five is the existing event-bin mention floor. This minimum is proposed here and is not frozen.
- Added node features: baseline sentiment, log mention volume, and the 11-bucket sector. Missing values stay the existing missing-feature rule.

## Success criteria

Unchanged. The same hypotheses, the same Holm family, the same 10-pair rule, the same SESOI band of [-0.05, 0.05], and the same H1 decision rows. Forbidden wording stays forbidden. Per-ecosystem results stay descriptive.

## GDELT cost for one combined pass

One query per 28-day slice, from 2016-11-14 through 2026-08-15, with every ecosystem's titles in that query. That is 128 slices. The query reads the date slice and then filters titles. The 2016-11-14 dry-run stayed 3,333,846,320 bytes on 2026-10-14 with 61 titles and again on 2026-10-20 after the allow-list had grown, so a longer title list does not change the scan.

A new dry-run was attempted on project sgnn-csp-2 and refused: no active account. `gcloud auth login` was not run.

Stored usable dry-runs cover 126 of the 128 slices. The smallest is 663,436,142 bytes (2026-06-15). The largest is 5,822,116,351 bytes. The total is 455,695,789,596 bytes, 0.4145 TiB. At the public on-demand list price of $6.25 per TiB, that is $2.59 if the monthly free tebibyte is already used, and $0 if it is not. Both of the unmeasured slices, 2026-07-13 and 2026-08-10, have only a stub dry-run (1,375 and 375 bytes) and are not in the total. Each measured slice is under the 10 GB refusal cap.

The split uses the existing monthly cap of 960,000,000,000 bytes. Before the full pass, 3 slices are run and their billed bytes are compared with the dry-run. If billed bytes divided by dry-run bytes is above 1.5, the pass is planned across 2 accounts, each under the 960 GB cap. Otherwise the slices stay on one account. Per-slice dry-run bytes are `reports/wave2_gdelt_cost.json`.

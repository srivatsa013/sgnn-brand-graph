# Phase 1C: TweetsKB and GDELT probe

Date: 2026-10-13. Accepted on 2026-10-13 with a two-arm conclusion. The recommendation at the end of this file is superseded by `DECISIONS_LOG.md` for that date. Arm A keeps FNSPID and StockTwits for all four ecosystems. Arm B adds TweetsKB social for Apple, Microsoft, and Alphabet. Tesla stays out of Arm B. GDELT is Arm B news only if its probe passes.

Sign agreement with StockTwits, reported below, is a consistency check. It is not a validation of accuracy. The 0.70 figure is a consistency bar, not a quality gate. TweetsKB has no text. SentiStrength's published positive-negative F1 on SemEval-2017 is about 0.52. The mention-weighted series in this file double-counts a tweet when the linker marks the same entity twice. The Arm B series counts each tweet once. Those consistency numbers will be recomputed on that series before any outcome.

## Probe recommendation, superseded

The paragraph below is what the probe recommended before acceptance. It is not the decision. The decision is two arms, logged in `DECISIONS_LOG.md` on 2026-10-13.

GDELT was not queried, so it has no coverage gate and no power gate. TweetsKB, on the public 5 percent SPARQL sample, passes coverage for all four ecosystems and passes the 9-event power bar for Apple (49), Microsoft (77), and Google (81). Tesla has 1 planning-proxy event. That fails the power bar. `Android` and `NIO` are absent from the linker. The Tesla series the linker returns ends on 2017-11-29.

Keep FNSPID and StockTwits. The finance-orientation limitation stays. TweetsKB is not recommended as a robustness source until the text-absent check below is approved and the Tesla gap is resolved. This recommendation is waiting for approval. Phase 2 does not start.

## Scales, fixed before these counts

The planning standard deviation stays 0.10636804456181562. It was not re-estimated.

| Score | Map used | SESOI 0.05 in baseline-SD units | Caliper 0.20 in the same units |
| --- | --- | --- | --- |
| TweetsKB | positive intensity minus negative intensity, both already on [0, 1], result on [−1, 1] | 0.470069 | 1.880276 |
| GDELT `score` | already on [−1, 1], from Google's document-sentiment documentation | 0.470069 | 1.880276 |
| GDELT V2Tone, if ever used | divide by 100 | same ratios after that division | same ratios after that division |

The event rule stays |z| ≥ 2 on the node's own 28-day baseline. That z is already in baseline-SD units. The power bar stays 9 brand events for an MDE of 0.10, and 18 events for a half-width of 0.05. A day needs at least 5 scored documents, a baseline of at least 14 observed days, and 8 days since the previous event. Sample counts were not multiplied by 20.

## StockTwits vs TweetsKB

TweetsKB here is the public SPARQL endpoint at `https://data.gesis.org/tweetskb/sparql`. The 2018 paper describes it as a 5 percent sample. Returned dates run from 2015-01-01 to 2020-12-31. `dc:created` has no timezone in the triples that were inspected, so the day is the date prefix of that literal, not a confirmed UTC day. Sentiment is one score for the tweet, copied to each linked entity. The signed score is mention-weighted: a tweet with two annotations of the same URI is counted twice. On Apple that is 21,759 scored rows against 20,285 distinct tweets, about 7 percent.

| | StockTwits, Phase 1 | TweetsKB, this probe |
| --- | --- | --- |
| What it measures | Investor bullish/bearish labels | General Twitter, SentiStrength, entities linked to DBpedia |
| Text | Yes | No. Ids are present. They were not hydrated. |
| Apple events / days | 171 / 5,540 | 49 / 1,884 |
| Microsoft events / days | 110 / 5,465 | 77 / 2,038 |
| Alphabet events / days | 142 / 5,485 | 81 / 2,062, using the `Google` URI. `Alphabet_Inc.` alone is 103 days and 0 events. |
| Tesla events / days | 145 / 4,699 | 1 / 605, URI `Tesla_Motors`, last day 2017-11-29. `Tesla,_Inc.` returned 0. |
| Coverage | Pass, all four | Pass, all four. See the node notes. |
| Power, MDE ≤ 0.10 (9 events) | Pass, all four | Pass for Apple, Microsoft, and Google. Fail for Tesla (MDE 0.298). |
| Days with at least 14 tweets | Not the Phase 1 bar | Apple 681, Microsoft 408, Google 2,009, Tesla 2 |
| Scale | Bullish +1, Bearish −1 | [−1, 1], as above |
| Validation | macro-F1 ≥ 0.70 still applies, because text exists | Cannot hand-label. Proposed substitute below. Not adopted. |
| Cost | Already extracted | SPARQL aggregates. No disk. |
| Effort to use as a source | None | A new series builder. The 5 percent sample cannot be scaled up without the N3 files. |

Node notes that do not flip the coverage pass:

- Apple's other nodes all have at least 14 days on the URI with the mentions. `HP_Inc.` itself has 12 tweets and 10 days. `Hewlett-Packard` has 7,080 tweets and 1,083 days. If the node is held to `HP_Inc.`, Apple still has 5 of 6 other nodes, which is above the 0.75 bar.
- `Adobe_Inc.` has 21 days. `Adobe_Systems` has 796. Either clears 14 days.
- `Amazon_(company)` returned 0. `Amazon.com` has 1,058 days, ending 2017-11-30.
- `Snap_Inc.` has 14 tweets on 14 days. `Snapchat` has 1,004 days. Alphabet still clears 6 of 7 other nodes on `Snap_Inc.` alone.
- `Android_(operating_system)` and `Android` returned 0.
- Every NIO URI tried returned 0: `NIO_(car_company)`, `Nio_Inc.`, `NIO`, `NIO_Inc.`, `Nio_(company)`.
- Microsoft's thin nodes still clear the 14-day bar: Azure 191 days, Satya Nadella 166, Oracle 120. Azure and Oracle have no day with 5 scored tweets, so they contribute no events. Coverage does not require events on the other nodes.

Co-mention exclusion can be written as a query. In June 2019 the endpoint returned 301 distinct iPhone tweets, and 279 of those do not also mention `Apple_Inc.`. The filter is `FILTER NOT EXISTS` on the event entity's linked URI. It only drops a tweet when the linker marked the event entity. It does not read text.

A sample of control-pool companies, not the full pool: Disney 1,138 days (788 of them with at least 14 tweets), Walmart 2,053 days (465 with at least 14), Coca-Cola 1,399 days (3 with at least 14), JPMorgan Chase 675 days (0 with at least 14). Nike returned 0 for both `Nike,_Inc.` and `Nike`. Intel, Nvidia, and Netflix were counted and are not controls: they are on the product-link exclusion list. Netflix has 2,016 days with at least 14 tweets. The full control pool was not queried.

## FNSPID vs GDELT

| | FNSPID, Phase 1 | GDELT GEG |
| --- | --- | --- |
| What it measures | Stock news headlines | Worldwide online news. English from 2016-07-17. Other listed languages from 2020-01-17. |
| Entity id | Ticker on the row. Products and CEOs need aliases. | `entities.name`, `entities.type`, `entities.mid`, `entities.wikipediaUrl`. No alias search if the name matches. |
| Sentiment | None in the file. Phase 1 used VADER on the headline. | Document `score` on [−1, 1] and `magnitude`. GDELT's own Tesla post says this score is the whole article, not the entity, and that entity-level sentiment was not integrated. |
| Products and CEOs | Alias counts in Phase 1 | Not counted. The type field exists, so a product or a person can appear as a name. GKG has organization and person fields and no product field. |
| Apple events | 14 | Not computed |
| Microsoft events | 5 | Not computed |
| Alphabet events | 15 | Not computed |
| Tesla events | 11 | Not computed |
| Coverage and power | Pass, all four | Not computed |
| Co-mention exclusion | Needs the text | Expressible as a second `UNNEST` with `NOT EXISTS` on the event entity's name. Not run. |
| Validation | macro-F1 ≥ 0.70 on a hand label, because text exists | Text was not retrieved. Same proposed substitute as TweetsKB, against FNSPID VADER. Not computed. |
| Cost | Already extracted | A dry run was not possible. See the setup below. |
| Effort | None | Blocked on a Google Cloud project. |

`bq` and `gcloud` are not installed. There is no project, so no dry run and no byte count. I did not install them and I did not start a query.

What I need before any GDELT query:

1. A Google account.
2. A Cloud project with the BigQuery API enabled. The BigQuery sandbox does not need a credit card. It allows 1 TiB of query processing a month and 10 GB of storage. A query on a public dataset still counts against that 1 TiB.
3. Permission to install the Cloud SDK on this machine. It is not installed now.
4. `gcloud auth login` and `gcloud config set project YOUR_PROJECT_ID` completed so this shell can see the credentials.
5. I will then run `bq query --dry_run` and show `totalBytesProcessed` before any query that scans data. I will stop if that number is above 10 GB unless you approve the larger scan.

The table to dry-run, from GDELT's posts, is `gdelt-bq.gdeltv2.geg_gcnlapi`. The older sentiment-only table `gdelt-bq.gdeltv2.geg_gcnlapisent` has no entity list. GDELT's announcement says that sentiment-only file is 5.7 GB compressed and 21 GB uncompressed, and it stops in October 2019. It was not downloaded. It cannot answer the node probe, because it has no entity names.

## Consistency check where text is absent

Sign agreement is a consistency check, not a validation of accuracy, and not a quality gate. It does not replace macro-F1 ≥ 0.70 on FNSPID or StockTwits. Those sources have text. TweetsKB does not. The scorer is a lexicon. SentiStrength's published positive-negative F1 on SemEval-2017 is 0.52.

The numbers below were computed on the mention-weighted series. They will be recomputed after each tweet is counted once, before any outcome. The consistency bar is 0.70. It does not decide whether a source may be used.

Published SentiStrength numbers from the TweetsKB paper: SemEval-2017 Task 4, average recall 0.54, positive-negative F1 0.52, accuracy 0.57. TSentiment15, positive-negative F1 0.80, accuracy 0.91. Neither is a brand-domain macro-F1.

On days where both series have at least 5 scored documents and both daily means are nonzero:

| Brand | Overlapping days | Sign agreement with StockTwits |
| --- | --- | --- |
| Apple | 1,047 | 0.749 |
| Microsoft | 1,316 | 0.778 |
| Google, against the Alphabet StockTwits series | 1,843 | 0.762 |
| Tesla | 27 | 0.630 |

Three brands meet 0.70. Tesla does not, on a short overlap, because the linked Tesla series ends in 2017. The GDELT half of this check was not computed.

## Download, if you want the full TweetsKB files

I am not downloading anything.

Zenodo parts 1 through 9, API read on 2026-10-13, are all CC BY 4.0. Together they are 367,170,428,974 bytes, about 342 GiB. Part 1 alone is about 46 GiB. Free disk on this machine is about 18 GB, so even Part 1 does not fit. Parts 10 through 12 are not in those nine records, and I do not have their sizes. Say if you want a download, and which part, after freeing disk or pointing at another drive.

## Final source decision, 2026-10-13

Arm A stays FNSPID and StockTwits for Apple, Microsoft, Alphabet, and Tesla. Arm B social stays TweetsKB for Apple, Microsoft, and Alphabet. Tesla stays out of Arm B. Arm B news is GDELT GEG. Coverage passes. The counts are in `eval/results/phase1c_gdelt_summary.json` and `reports/phase2_arm_coverage.md`.

The 9-event bar in the scales section above uses the Arm A pooled SD. It is not the GDELT bar and it is not the TweetsKB bar. GDELT brand planning-proxy events are Apple 149, Microsoft 157, and Alphabet 145. The descriptive check at provisional SD 0.20 uses 32 and 62 events. GDELT's own placebo SD is still unestimated. The usable-pair report was not run.

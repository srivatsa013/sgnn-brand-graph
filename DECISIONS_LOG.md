# Decisions log

## 2026-10-11 — Phase 0 freeze, pending approval

No dataset was downloaded. No sentiment score, event count, or model metric exists yet.

### Locked items carried in from the project brief

L1 through L7 stand: signed GNN, brand-reputation domain, positive ownership and product edges, negative directed competitor edges, pre-built labeled data only, news and social kept separate, matched unconnected controls, two or three ecosystems, and the four deliverables (interpretable framework, reproducible prototype, case study, paper draft).

Section 9 stands: ecosystems are chosen in Phase 1 from Apple, Samsung, Tesla, Microsoft, and Google first; news data starts from SEntFiN; co-mention edges are included; the CEO is added where the data supports it; compute stays laptop-scale; there is no user interface; default k is 2, bins are days, and linking precision is 90 percent; the write-up stays in Markdown.

### Assumptions already in the brief, accepted here

A1 through A14 are accepted. One implementation choice inside A1 is recorded: package versions were read from PyPI on 2026-10-11 and written to `requirements.txt`. They were not installed in Phase 0. The checker uses the standard library. The local interpreter is Python 3.14.6, which satisfies the `>=3.12` intent. networkx 3.7 excludes Python 3.14.1 only.

### New assumptions frozen in Phase 0

These were not fixed by Section 9. They are the choices a later analyst would otherwise have to invent. Overrule any of them before Phase 1 starts and the config will be edited with a new log entry.

- A15. Event-day minimum is 5 mentions. Baseline is 28 days and needs 14 observed days. Sample standard deviation uses divisor n-1. A zero standard deviation is not an event.
- A16. Pre window is t0-7 through t0-1. Post window for targets is t0 through t0+7, so the event day is included for neighbors. Each window needs 3 observed days or the pair is dropped.
- A17. The same entity and source cannot open another event until 8 days after t0.
- A18. Co-mention edges for an event use a 180-day window ending on t0-8, and require at least 3 co-documents. Weight is log(1 + count). No sign is imposed.
- A19. Controls are 1:1 Mahalanobis matches with the calipers in `configs/phase0.json`. Balance fails if any absolute standardized mean difference exceeds 0.20. Calipers are not loosened to repair balance.
- A20. Popularity is the Wikidata sitelink count. Missing popularity makes the entity ineligible. Sector comes from industry. Missing sector makes the entity ineligible until a manual bucket is logged.
- A21. H1 must pass both the pair-label permutation and the degree-preserving rewiring test, after Holm correction across the eight primary tests. The smallest meaningful absolute-shift gap is 0.05. Placebo false-positive rate must be at most 0.10.
- A22. The Phase 1 power gate uses a planning standard deviation of 0.20, not a standard deviation estimated from outcomes. With one pair per event, an ecosystem needs 32 qualifying events to have a minimum detectable effect of 0.10 or smaller.
- A23. English text only.
- A24. Classifier macro-F1 on the brand-domain hand labels must be at least 0.70 before events are detected. This is a Phase 3 gate, not a hypothesis.
- A25. If the daily audit fails coverage or power, the weekly fallback constants already in the config are the only substitute, and they must be logged before any outcome test.
- A26. Wikidata property identifiers are not treated as verified in Phase 0. Phase 2 checks them before any edge is stored. The intended properties are parent organization, subsidiary, owned by, owner of, manufacturer, product, brand, industry, and chief executive officer.

### Citation corrections

- "NIST-GNN (IEEE 2025)" was not verified as an IEEE paper. The NIST-GNN model is Luo, He, Cucuringu, and Ma, Quantitative Finance, 2026, DOI 10.1080/14697688.2025.2548897. It will not be cited as IEEE 2025.
- "Das et al. 2024 (survey)" is identified as Das, Sadhukhan, Chatterjee, and Chakrabarti, Decision Analytics Journal, 2024, article 100417. The DOI landing page returned HTTP 406 here. The DOI string comes from a citing reference list.
- SEntFiN's journal year is 2022. The arXiv year is 2023.
- KGAN's journal year is 2023. The arXiv year is 2022.
- Wu, Liu, Chen, and Li, arXiv:2604.26811v2 (posted 2026-04-29), completes the news-versus-social citation. No journal version was found.
- Singh and Chen, arXiv:2208.07323v1, has no confirmed venue beyond the preprint.
- Forss and Sarlin, arXiv:1706.05812v2, has no confirmed journal venue in this check.

### Results

None. Phase 0 has no empirical estimates.

### Checkpoint

Internal check command: `python3 scripts/validate_phase0.py`.

Run on 2026-10-11. Result: PASS. Config SHA-256 `74233b92f5f7e7e3742e84fa867f03cadf29eb0a349f2939eb32ec09a098344e`. The power formula in the checker gave a minimum detectable effect of 0.099051 at 32 events and 0.100636 at 31 events, under the planning standard deviation of 0.20. Holm family size reported by the checker: 8.

The official Phase 0 gate is approval of this pre-registration. Status: approved on 2026-10-11 with the amendments below.

## 2026-10-11 — Phase 0 amendments applied before Phase 1

The user approved Phase 0 and required seven amendments. No other constant was changed. k remains 2, the daily windows remain t0-28 through t0-1, t0-7 through t0-1, and t0 through t0+7, the mention floors remain 5 and 14, the calipers remain 0.20, ln(2), and ln(3), the SESOI remains 0.05, the MDE bar remains 0.10, the bootstrap count remains 1,000, the rewiring target remains 500, the seeds remain unchanged, and the linking and classifier gates remain 0.90 and 0.70.

New config SHA-256 after these amendments: `24937cb8df91a3fc0e7d7b74b2f3076174e8579ac873db23f1bc6717c5986fb2`.

Previous SHA-256, before the amendments: `74233b92f5f7e7e3742e84fa867f03cadf29eb0a349f2939eb32ec09a098344e`.

Checker re-run after the amendments: PASS. Minimum detectable effect at 32 events: 0.099051. At 31 events: 0.100636. Interval half-width at 62 events: 0.049783. At 61 events: 0.050190. All four numbers were printed by `scripts/validate_phase0.py`.

### Amendment 1 — control validity

Every control candidate must pass a Wikidata path check of length at most 2 on parent, subsidiary, owner, brand, product, manufacturer, and competitor-if-populated relations, in addition to the check on our own graphs. Each selected control also gets a direct-competitor check. Both outcomes are logged per event. A failed selected control is dropped and matching is repeated without widening calipers. Sector matching uses a coarse bucket. The industry-to-bucket map is defined and logged in Phase 1 or Phase 2 before any matching or outcome. Exact match on raw P452 is rejected.

### Amendment 2 — pooling and the inconclusive rule

Confirmatory H1–H4 pool events across ecosystems that pass Phase 1. Per-ecosystem results are descriptive only. The 32-event gate targets an effect of about 0.10 at planning SD 0.20. The meaningful effect remains 0.05. A 95% interval half-width of at most 0.05 needs 62 events at that SD. The report states whether the pooled sample reaches that count. An interval that extends beyond [-0.05, 0.05] without meeting the supported or graph-nonspecific row, and a non-significant result from a sample too small to pin 0.05, is inconclusive. The phrase "no spillover" is forbidden.

### Amendment 3 — planning SD

0.20 stays in the config until Phase 1 replaces it. The replacement is the sample SD of the paired difference in absolute shift on placebo (non-event) dates. Old and new values are logged, and the new value is frozen before any real event outcome is computed.

### Amendment 4 — p-values and rewiring

All permutation p-values are (b+1)/(B+1). The rewired graph is the disjoint union of structural edges of Phase-1-passing ecosystems. Connected targets are recomputed as one-hop neighbors on that graph. Controls are re-matched. Wikidata checks stay fixed. Only distinct rewirings count. If fewer than 500 distinct graphs exist, B is the actual count and is reported. Draws are not reused. If the distinct count is 0, H1 is not estimable. New procedural caps, required so the search stops: 20,000 attempts, or 500 consecutive non-novel attempts. These caps were not previously set. Existing numeric constants were not edited to create them.

### Amendment 5 — clustered bootstrap

The bootstrap cluster changed from `event_id` to `ecosystem_x_iso_week`.

### Amendment 6 — H1 decision table

First matching row wins: not estimable; method failed; no meaningful effect; supported; differs from controls but not graph-specific; inconclusive.

### Amendment 7 — citations

Singh and Chen is Transactions on Machine Learning Research, February 2023, listed on https://jmlr.org/tmlr/papers/ and accepted on OpenReview at https://openreview.net/forum?id=RZveYHgZbu. The preprint year remains 2022. No DOI was found.

Das et al. DOI 10.1016/j.dajour.2024.100417 was fetched again and returned HTTP 406. Status: not opened directly.

### Assumptions added

- A27. Coarse sector buckets replace raw industry equality. The bucket map is a logged artifact, not a post-hoc choice.
- A28. Wikidata ineligibility is fixed under rewiring. Only our structural edge set is rewired.
- A29. The H1 decision table is authoritative when it is stricter than the shorter support checklist. A significant estimate whose interval lies entirely inside [-0.05, 0.05] is "no meaningful effect".

## 2026-10-11 — Phase 1 audit, NO-GO

No confirmatory outcome was computed. The planning standard deviation was not re-estimated. It is still 0.20. The cutoffs 32 and 62 are unchanged. The coarse sector map was not written, because there is no control pool yet. It remains required before matching.

News files opened:

- SEntFiN 1.0, https://github.com/pyRis/SEntFiN, 10,753 headlines, MIT. No date column. Entity rows for the candidate brands are in `eval/results/phase1_sentfin_entity_counts.csv`. Apple 21, Apple Inc 2, Microsoft 6, Samsung Electronics 2, Google 1, Tesla 1, plus a handful of other Samsung and India strings. News events are not computable.
- FinEntity, https://github.com/yixuantt/FinEntity, 979 paragraphs, no date field. Entity-value counts include Tesla 31, Apple 23, Alphabet 16, Microsoft 16, Google 10, Samsung 5.

Social file streamed, counts only, no post text stored:

- StockTwits symbol tables, `s3://stocktwits-nyu/dataset/v1/data/csv/symbols/`, 135 files, 241,198,362 symbol rows, dates 2008-05-27 through 2022-12-31. Summary: `eval/results/phase1_stocktwits_ticker_summary.json`. Days with at least 5 user-labeled rows: AAPL 4,040, MSFT 2,690, GOOG 2,861, GOOGL 1,981, TSLA 3,491, SSNLF 8. SMSN and SSNGY had 0 rows. These are volume days, not sentiment events. Daily mean sentiment was not computed. Products and CEOs were not counted. GitHub LICENSE returned HTTP 404. The DOI page 10.51685/jqd.2025.020 returned HTTP 406. The README citation is Li, Al Ansari, and Kaufman, 2025.

Not downloaded: FiQA Hugging Face files (HTTP 401, gated), SemEval-2017 Task 5 full text (API rebuild, not done), FNSPID `nasdaq_exteral_data.csv` (content-length 23,232,979,597 bytes).

Gate result: zero ecosystems pass. Phase 2 was not started.

## 2026-10-11 — Phase 1 extract list logged before the stream

Phase 1 stays NO-GO until the gates are recomputed from the extract. `configs/phase0.json` is not edited. No spillover, shift outcome, or H1–H4 number is computed in this pass. The list below was written before the FNSPID and StockTwits streams started.

Sector map: `configs/sector_taxonomy.json`, SHA-256 `9a191e03a468b123cee7f38870d2dc74f12a19ca24aad35573fd57749fe6a231`. Eleven buckets. Wikidata automotive labels map into `consumer_discretionary`, because an automotive-only bucket would leave Tesla with almost no non-competitor control. Raw P452 equality is not the match key.

Extract list: `configs/phase1_universe.json`, SHA-256 `90f304c40d296682c38bf219d9000394c75ed42324613bd1212022e651057d89`.

Retained tickers: 206. Control pool: 184, not competitors, parents, or product-linked names. Bucket sizes: information technology 20, communication services 16, consumer discretionary 18, financials 18, healthcare 18, energy 16, utilities 16, industrials 18, consumer staples 16, materials 14, real estate 14.

Ecosystems and competitor nodes:

- Apple, bucket information technology. Competitors DELL, HPQ, SONY, LOGI. Samsung is not an ecosystem: SSNLF had 8 labeled-volume days and SMSN and SSNGY had none. LOGI is the fourth device-adjacent listed brand because an OTC name would repeat that failure. Planned other nodes: iPhone, MacBook, Apple CEO, and those four tickers.
- Microsoft, bucket information technology. Competitors ORCL, CRM, IBM, ADBE. Planned other nodes: Windows, Azure, Microsoft CEO, and those four tickers.
- Alphabet, bucket communication services. Brand tickers GOOG and GOOGL, one entity. Competitors Meta (FB and META), AMZN, SNAP, PINS. Planned other nodes: YouTube, Android, Alphabet CEO, Meta, AMZN, SNAP, PINS.
- Tesla, bucket consumer discretionary. Competitors F, GM, TM, NIO, as specified for this pass.

No distinct parent ticker is added. Each of these four listed companies is its own parent. Bare strings Mac, Windows, and Musk are not primary aliases. iPad, Apple Watch, Model Y, and Cybertruck are counted and reported, and they are outside the 75 percent denominator.

A node has a source if that source shows at least 14 distinct UTC days with a mention. The brand must have both sources. At least 6 of the 7 other planned nodes must have both sources, because 5 of 7 is 0.714 and the gate is 0.75. This manual list is the extract only. The per-event Wikidata path check is still required before any confirmatory match.

Names left out of the control pool, and not retained, include other automakers (RIVN, LCID, STLA, HMC, VWAGY), chip suppliers and chip equipment (TSM, NVDA, AVGO, QCOM, AMD, MU, INTC, AMAT, ASML, LRCX, KLAC), NFLX, BBY, GRMN, auto-parts retailers (ORLY, AZO, AAP, GPC), and ALB. Reasons are in the universe file.

Licenses opened before building on the files:

- FNSPID dataset card README at https://huggingface.co/datasets/Zihan1004/FNSPID says Creative Commons Attribution-NonCommercial 4.0. Commercial use needs permission. Non-commercial academic research is allowed. The GitHub README at https://github.com/Zdong104/FNSPID also says, in a 2025-07-24 note, that research use and commercial use are released, while a later section of that same file still prohibits commercial use of the code. This project is academic, so the stream proceeds. The news CSV has no sentiment column.
- `Stock_news/nasdaq_exteral_data.csv` is 23,232,979,597 bytes. Hugging Face etag `cccdf2f3312e575d78ae94f799379cb85c03557374c6778cd7b7fd3d55102a2b`. A streaming SHA-256 will be checked against that etag. `Stock_news/All_external.csv` is 5,731,397,037 bytes, etag `dde529189c87048a8be1f73d17ecd5e211fc7809032e60c72cd22645f111c470`. The full files are not stored.
- StockTwits S3 README at https://stocktwits-nyu.s3.amazonaws.com/dataset/README.md says the bucket is public and holds the data for replicating the paper. No LICENSE file was in the GitHub repository. The DOI page was not opened (HTTP 406 in the prior check). No term found in the S3 README forbids academic research, so the stream proceeds. Message bodies are 51.19 GiB and message metadata are 28.71 GiB. Only rows for the retained tickers are written.
- FinEntity's GitHub license API returned HTTP 404. It is not used as an event series. SEntFiN remains MIT. Both stay on disk for the Phase 3 classifier.

Timestamps opened before the stream:

- FNSPID `Date` values seen in the first bytes include `2023-12-16 23:00:00 UTC` and `2020-06-05 06:30:54 UTC`. The zone is written on the field.
- StockTwits `symbols/` `created_at` is a calendar date with no clock. `feature_wo_messages/` `created_at` in the files themselves includes `2008-05-27T15:28:28Z` and `2017-11-17T23:47:51Z`. That is a full clock with a Zulu suffix. `messages/` has `message_id` and `message_body` only. The working day is the UTC calendar date of the message-level timestamp. Same-day alignment with FNSPID uses that UTC date. The symbol-table date has no zone; it is not the timestamp used for the social series.

## 2026-10-12 — Phase 1 gates, GO

The extract finished. Phase 2 was not started. No H1–H4 outcome was computed. `configs/phase0.json` was not edited, so its approved SHA-256 stays `24937cb8df91a3fc0e7d7b74b2f3076174e8579ac873db23f1bc6717c5986fb2`. The planning standard deviation below is the Phase 1 replacement. It is frozen here, before any real event outcome.

Hashes. The streamed SHA-256 of each FNSPID file matches the Git-LFS object id from `https://huggingface.co/api/datasets/Zihan1004/FNSPID/tree/main/Stock_news`, not the HTTP ETag recorded above. `nasdaq_exteral_data.csv` is `1a7a3eb8e6b97ec19f286f2cfca3371542bddb272ab1eb8f36e33ad98fa5c4da` (23,232,979,597 bytes). `All_external.csv` is `5d4c018036bd82ca821da71b7a9c0c7db3289642e0fc6f897ea69f4a0c5135c3` (5,731,397,037 bytes). The HTTP ETags (`cccdf2f3…` and `dde52918…`) are a different identifier. The full CSVs were not stored. Kept news rows: 731,458, all with a `UTC` suffix. StockTwits retained 29,980,570 feature rows, all with a `Z` suffix, and 20,613,589 message bodies.

Row-count stalls. The parsed row counter was flat for multi-gigabyte spans of both FNSPID files. An independent check, `scripts/phase1_fnspid_stall_check.py`, does not use this project's CSV parser. On 2 MB windows at the start, middle, and end of each stall, line-start timestamps were followed by an empty stock-symbol field. A second pattern that allows a quoted URL, ` UTC,<title>,,"http`, counted 672, 618, and 608 such rows in the three windows that the first pattern had called ambiguous, and 0 rows with a ticker in that position. Python's `csv` module, started on a record boundary inside the nasdaq stall, also returned an empty symbol. Raw `,AAPL,`, `,MSFT,`, and `,TSLA,` counts in those windows were 0. The stall is rows with no ticker. The parser was not re-run. Detail is in `reports/phase1_data_audit.md`.

Licenses. FinEntity `readme.md` line 116, opened 2026-10-12, says FinEntity is licensed under ODC-BY. Academic use with attribution is allowed. SEntFiN remains MIT. Neither file has dates. Both stay reserved for the Phase 3 classifier. They are not event series.

Planning standard deviation. Old value 0.20, old minimum-detectable-effect cutoff 32 events, old half-width cutoff 62 events. New value 0.106368, from 31 matched placebo pairs (24 news, 7 social) on the four focal companies. New cutoffs: 9 events for an MDE of 0.10, and 18 events for a half-width of 0.05. Seed 3, up to 20 non-event dates per company per source. One-hop neighbors do not exist yet, so the pair is the company's own series against a sector-matched control. Wikidata popularity was not in these files, so the match used three covariates. This number is not an H1 outcome. It is frozen.

Daily gates pass for Apple, Microsoft, Alphabet, and Tesla. The weekly fallback was computed and is reported. It is not adopted, because the daily coverage gate and the daily power gate both pass. Pooled brand events across the four ecosystems: 613. That exceeds 18 and also exceeds the old cutoff 62.

Limitation, not a pivot. FNSPID is stock news. StockTwits bullish and bearish labels are investor outlook. The idea remains brand reputation. The Phase 3 brand-domain hand label, macro-F1 at least 0.70, is the test of whether that scoring transfers. This is an item for the faculty guide.

SONY has 806 social days and 0 FNSPID rows under `SONY` or `SNE`. It is the one Apple node below the 14-day news bar. It was not replaced. Apple still has 6 of 7 other nodes on both sources.

## 2026-10-12 — Planning-SD amendment, Phase 2 paused, Phase 1B

`configs/phase0.json` SHA-256 is `766fc708f52f929c25328debeebdf5c2ebda388cfb6a20ea7968d5a6bebd03cd`. Amendment `A2026-10-12-planning-sd` sets the operative planning standard deviation to 0.10636804456181562, from 31 focal-company placebo pairs. The minimum-detectable-effect cutoff at that value is 9 events. The half-width cutoff is 18 events. The provisional value 0.20 remains in the file. The Phase 1 gate passes at both 0.20 and 0.106368, so the change did not decide the outcome. The value is not re-frozen. In Phase 4, the standard deviation observed on real neighbor targets is reported descriptively and does not replace this planning value.

StockTwits. The S3 README describes a public bucket for replicating Li, Al Ansari, and Kaufman 2025. No LICENSE file was found. No term forbidding academic use was found. The paper's data statement must say that StockTwits has no explicit license.

Phase 2 was paused before a knowledge graph was built. Phase 1B (`reports/phase1b_brand_reputation_audit.md`) did not replace FNSPID or StockTwits. No candidate was downloaded. No coverage or power gate was re-run. No H1–H4 outcome was computed.

FinBERT is a Phase 3 comparison baseline only. The same hand-labeled brand-domain sample is scored with FinBERT and with the entity-aware classifier. FinBERT is not the primary scorer and does not detect events. The macro-F1 threshold remains 0.70.

Wikidata, queried 2026-10-12: no property with the English label "competitor" is populated for the focal companies. The statement count on that label for Apple, Microsoft, Google, Alphabet, Tesla, Meta Platforms, and Amazon is 0. Competitor edges remain the hand-checked study list.

SEC Exhibit 21, latest 10-K for each of the four parents, confirms 0 of the planned product, brand, or CEO edges. Google LLC is listed under Alphabet and is already the same study node, not a product edge. Toyota and NIO file Form 20-F, not Form 10-K. Exhibit 21 does not replace Wikidata or DBpedia.

Parked, not built: a signed graph over 9 automotive firms and 7 pharma firms. It would drop products and CEOs and add a second sector. Tesla's ecosystem already covers the automotive competitors in this study.

## 2026-10-13 — Phase 1C rule clarifications, logged before any probe count

These clarifications are fixed before any TweetsKB or GDELT aggregate is computed. They do not change `configs/phase0.json`. No H1–H4 outcome is computed in the probe.

Collection. "No API collection" means no Twitter, Reddit, or other platform API, no hydration of tweet ids, and no fetching of article URLs. A query for aggregates against a public dataset endpoint is allowed. TweetsKB SPARQL and a GDELT BigQuery aggregate are in that category. A raw download above about 50 GB is not rejected by the rule. It is asked for first, with the size and the disk need. Free disk on this machine is about 18 GB. Aggregates are preferred to downloads.

Nodes. Where the dataset's own linker names an entity, that linked id is the node. Alias search is only for a source that has no linker. Text is not required for a linked entity.

Scales, fixed before any probe event count. The frozen planning standard deviation stays 0.10636804456181562. It is not re-estimated from TweetsKB or GDELT.

- TweetsKB stores SentiStrength as Onyx intensities on [0, 1]. The 2018 paper's example is a positive intensity of 0.75, and its query filters negative intensity at 0.75. That matches the documented map `(|raw| - 1) / 4` from the raw scores +1..+5 and −1..−5. The signed tweet score used here is positive intensity minus negative intensity, so a missing side is 0. The result is on [−1, 1].
- GDELT GEG `score`, from Google Cloud Natural Language document sentiment, is already on [−1, 1]. Google's documentation says the score ranges from −1.0 to 1.0. Magnitude is not used as the sentiment. GDELT V2Tone, if used, would be divided by 100. The probe uses `score` when a query is possible.
- SESOI 0.05 on that shared [−1, 1] scale is 0.470069 baseline-SD units of the frozen planning SD (0.05 / 0.10636804456181562). The baseline-mean caliper 0.20 is 1.880276 of those same units (0.20 / 0.10636804456181562). The event rule itself stays |z| ≥ 2 against the node's own 28-day baseline. That z is already in the node's baseline-SD units. The power cutoff stays 9 brand events for an MDE of 0.10 on the mapped [−1, 1] scale, and 18 events for a half-width of 0.05. These ratios are not refit after the probe.

Validation where text is absent. The macro-F1 ≥ 0.70 hand-label gate cannot be run without text. It is not dropped. The proposed substitute, which is not adopted until approved, has two parts. First, report the published SentiStrength numbers from the TweetsKB paper that was opened: on SemEval-2017 Task 4, average recall 0.54, positive-negative F1 0.52, accuracy 0.57; on TSentiment15, positive-negative F1 0.80, accuracy 0.91. Those are not a brand-domain macro-F1. Second, on UTC days where both series have at least 5 scored documents, sign agreement between TweetsKB and StockTwits, and between GDELT and FNSPID VADER, must be at least 0.70 on the four brands. That check is a proposal. It is not a passed gate. The 0.70 macro-F1 gate still applies to any source that has text.

Phase 1B rejections of Yelp, Reddit, CC-News, RepLab, the small Kaggle set, and Amazon reviews as an event source stand.

## 2026-10-13 — Phase 1C probe results, recommendation not approved

Aggregates only. No tweet was hydrated. No article URL was fetched. No N3 file and no GDELT file was downloaded. No H1–H4 outcome was computed. The planning standard deviation was not re-estimated. Detail is in `reports/phase1c_source_probe.md`.

TweetsKB public SPARQL, 5 percent sample, dates returned 2015-01-01 through 2020-12-31. Counts were not multiplied by 20. Planning-proxy brand events, |z| ≥ 2: Apple 49, Microsoft 77, Google 81, Tesla 1. Coverage passes for all four ecosystems. Power passes for Apple, Microsoft, and Google, and fails for Tesla. `Android_(operating_system)` and every NIO URI tried returned 0 tweets. `Tesla,_Inc.` returned 0. `Tesla_Motors` ends 2017-11-29. A co-mention exclusion is expressible: in June 2019 the endpoint returned 301 distinct iPhone tweets, of which 279 do not also mention `Apple_Inc.`

Zenodo records for parts 1 through 9, read 2026-10-13, are CC BY 4.0. Their files sum to 367,170,428,974 bytes, about 342 GiB. Part 1 alone is 49,857,635,935 bytes, about 46 GiB. Free disk is about 18 GB. No download was started.

GDELT was not queried. `bq` and `gcloud` are not installed, and there is no project to dry-run. The coverage and power gates for GDELT are not computed. From GDELT's own posts, `gdelt-bq.gdeltv2.geg_gcnlapi` stores document-level `score` and `magnitude`, not a per-entity sentiment. Entity fields include name, type, mid, and wikipediaUrl.

Proposed text-absent check, computed and not adopted: on days where both series have at least 5 scored documents and both means are nonzero, sign agreement of TweetsKB with StockTwits is 0.749 (Apple, 1,047 days), 0.778 (Microsoft, 1,316 days), 0.762 (Google against the Alphabet StockTwits series, 1,843 days), and 0.630 (Tesla, 27 days). The 0.70 bar is met on three brands and missed on Tesla. The macro-F1 gate is unchanged for sources that have text.

Recommendation, pending approval: do not switch the primary sources. Keep FNSPID and StockTwits, with the finance-orientation limitation. Do not start Phase 2.

## 2026-10-13 — Two arms, logged before any outcome

Phase 1C is accepted with a different conclusion from the probe's recommendation. This entry is written before any new event count, any per-source planning SD, and any H1–H4 outcome.

Arm A and Arm B are analyzed separately. Each arm has its own primary Holm family of the eight pre-registered tests. The families are not merged and the arms are not pooled. A result on one arm is not evidence about the other.

Arm A is finance discourse: FNSPID news and StockTwits social, for Apple, Microsoft, Alphabet, and Tesla. The pooled planning SD 0.10636804456181562 stays the Arm A pooled value from 31 placebo pairs. It is not used to convert SESOI or the baseline-mean caliper for any other source.

Arm B is general-public discourse. Social is TweetsKB for Apple, Microsoft, and Alphabet. Tesla is excluded from Arm B. The linker URI `Tesla_Motors` ends 2017-11-29. `Tesla,_Inc.`, `Tesla_Inc.`, and the English Wikipedia URI for Tesla, Inc. each returned 0 tweets. `Elon_Musk` has 1,530 days, `Tesla_Model_3` has 193 days, and `Tesla_Model_S` has 561 days. Those nodes are reported and do not put Tesla into Arm B. News is GDELT GEG only if its probe passes. If GDELT fails, Arm B is social-only and H4 is not estimable on Arm B.

Planning SD. Each source is re-estimated from placebo non-event dates on that source alone, divisor n-1, before any outcome on that source. SESOI 0.05 in baseline-SD units is 0.05 divided by that source's SD. The baseline-mean caliper 0.20 in those units is 0.20 divided by the same SD. Those quotients are logged with the SD before the outcome. They are not computed in this entry. The event rule stays |z| ≥ 2.

TweetsKB counting. Each tweet is counted once per entity. The Phase 1C series counted mention rows and was about 7 percent higher on Apple (21,759 rows, 20,285 distinct tweets). That series is not the Arm B series. The URI for each node is `configs/arm_b_dbpedia_uris.json`. Two URIs for one node are not added together.

Sign agreement with StockTwits is a consistency check, not a validation of accuracy. The 0.70 figure is a consistency bar, not a quality gate. TweetsKB has no text. The scorer is SentiStrength. The TweetsKB paper reports positive-negative F1 about 0.52 on SemEval-2017. The macro-F1 ≥ 0.70 hand-label gate still applies where text exists.

No download. No tweet hydration. SPARQL aggregates only. Free disk is about 18 GB. The usable-pair feasibility report waits until the GDELT probe is done and the source set is approved. The knowledge graph may be built. It does not depend on the sentiment source.

`configs/phase0.json` amendment `A2026-10-13-two-arms` records the same split. It does not replace the Arm A pooled SD. SHA-256 after that amendment is `6440d8906a245333fa79da2bb467e3d2b87f2e4218d726d79e19fff037a1aa2e`. The validator passes. The operative planning SD field is unchanged.

TweetsKB recount, after that entry. Each tweet is counted once per entity. Distinct tweets equal scored tweets on every Arm B series URI. Brand planning-proxy events under |z| ≥ 2 are Apple 44, Microsoft 70, and Alphabet 86. These are not an H1 outcome. The Arm B power cutoff is not set from 0.106368. It waits for TweetsKB's own placebo SD.

Knowledge graph, same day. `kg/phase2_structural_edges.json` has 7 positive edges and 11 CEO statements. Android Q94 is not among them. Its only link to Google Q95 is P178 developer, which is not a verified positive property, so no edge was added. A first build had attached Google Play Q79576 because that item is owned by Google. That edge was removed. Dell Technologies Q27500963 is the same DELL node because an ownership statement links it to Dell. Alphabet Inc. Q20800404 is the same Alphabet node because an ownership statement links it to Google. The usable-pair report was not run.

## 2026-10-13 — CEO tenure windows, logged before any further outcome

The 15 competitor edges are confirmed. Logitech stays. Samsung is not added in this entry. Its coverage is checked after this window list, and it is added only if that coverage clears the 14-day bar.

CEO aliases are time-aware. The windows are in `configs/ceo_tenures.json`, taken from Wikidata P580 and P582 on 2026-10-13. Arm A aliases and Arm B DBpedia URIs use the same windows. A person counts only inside an inclusive window. On a boundary day that both statements include, both people count. One document still counts once for the node.

- Steve Jobs: 1997-09-01 through 2011-08-23. Tim Cook: 2011-08-24 through 2026-08-31.
- Steve Ballmer: 2000-01-01 through 2014-02-04. Satya Nadella: 2014-02-04 onward.
- Eric Schmidt: 2001-08-01 through 2011-04-08.
- Larry Page: 1998-01-01 through 2001-12-31, 2011-04-04 through 2015-08-10, and 2015-08-10 through 2019-12-03.
- Sundar Pichai: 2015-08-10 onward as Google CEO, which is inside the Alphabet CEO node.
- Elon Musk: 2008-10-01 onward. Tesla stays out of Arm B.

From 2026-09-01 Wikidata's preferred Apple P169 target is Q106028933. That item has no English label. It is not an alias. No Apple CEO alias is active on or after that date.

GDELT name rules, fixed before the historical counts. One article counts once per node. The document `score` is the article score. Apple is an ORGANIZATION named Apple, Apple Inc, or Apple Inc. iPhone and MacBook and Android and Windows are CONSUMER_GOOD under those exact names. Tim Cook counts only inside his window. Alphabet the brand is the ORGANIZATION named Google. Alphabet CEO is Sundar Pichai from 2015-08-10 or Larry Page through 2019-12-03. Meta is Facebook, Meta, or Meta Platforms. Amazon is the ORGANIZATION named Amazon. Snap is Snapchat. Hewlett-Packard does not include Hewlett Packard Enterprise. Samsung, if counted, is an ORGANIZATION named Samsung or Samsung Electronics, and it is not an edge unless its coverage passes.

Samsung coverage, after the window entry. TweetsKB `Samsung` has 2,028 days and 14,840 tweets. `Samsung_Electronics` has 220 tweets. StockTwits `SSNLF` has 5,914 rows on 2,318 days, from 2013-01-15 to 2023-09-03. FNSPID has 0 rows for `SSNLF`, `SMSN`, and `SSNGY`. Headlines containing Samsung: 283 rows on 189 days. All three clear 14 days, so Samsung is added as an Apple competitor beside Logitech. The news series is the headline alias, because there is no ticker row. StockTwits still has only 546 labeled rows. The edge is in `kg/phase2_structural_edges.json`. The earlier 15 edges are confirmed.

## 2026-10-13 — Arm B news probe, after the logged windows

The English 2016-11-14 dry run on date, language, score, and magnitude processed 2,708,608 bytes. That is under 10 GB, so the probe continued. Each 28-day entity slice dry-ran at 7,694,617,837 bytes, also under 10 GB. The loop ran 128 slices. The upper bound is 984,911,083,136 bytes. The quiet client returned no job id, so actual bytes stayed uncounted and the 900 GB stop did not fire. No second scan was run.

GDELT name filters match on 3,482 days, 2016-11-14 through 2026-06-18. The earlier English minimum and maximum for the table were 2016-07-17 and 2026-08-14. These filters have no row after 2026-06-18. The score is the document score. One article counts once per node. Planning-proxy events under |z| ≥ 2, which are not an H1 outcome, are Apple 149, Microsoft 157, and Alphabet 145. Every planned Arm B node has at least 14 days. Android has 3,482 GDELT days and 0 TweetsKB days. Samsung has 3,482 GDELT days. A descriptive check at provisional SD 0.20 uses cutoffs of 32 and 62. All three brands clear both. GDELT's own placebo SD is not estimated. The pooled SD 0.10636804456181562 is not used.

Source decision. Arm A remains FNSPID and StockTwits for four ecosystems. Arm B social remains TweetsKB for Apple, Microsoft, and Alphabet, with Tesla excluded. Arm B news is GDELT GEG. H4 is estimable on Arm B once this source set is approved. The usable-pair report was not run.

CEO series after the windows. Arm A news, searched in headline, summary, and text, with VADER still on the headline: Apple CEO 779 days, Microsoft CEO 674 days, Alphabet CEO 467 days, Tesla CEO 1,559 days. Arm A social: Apple CEO 1,848 days, Microsoft CEO 341 days, Alphabet CEO 356 days, Tesla CEO 2,350 days. All eight clear 14 days. Arm B Alphabet CEO is the union of Larry Page through 2019-12-03 and Sundar Pichai from 2015-08-10, one tweet once: 257 days and 393 tweets. Steve Jobs, Steve Ballmer, and Eric Schmidt end before the TweetsKB sample.

## 2026-10-14 — Match rule, Samsung scored days, subsidiary bar, and planning SD, before the usable-pair counts

BigQuery history for project `sgnn-csp` has 130 jobs, all on 2026-10-13. Processed bytes sum to 929,202,553,187. Billed bytes sum to 929,292,091,392. Every job was billed. Under a 1 TB allowance, about 70.7 GB remained before the one-day audit. Under a 1 TiB allowance, about 170.3 GB remained. The audit then processed 238,212,204 bytes. The sandbox allowance is monthly. These jobs fall in October 2026, so the next calendar month begins 1 November 2026. `scripts/bq_usage.py` now records each job id and refuses a query whose dry run would pass 1,000,000,000,000 bytes or 10 GB. `scripts/phase1c_gdelt.py` refuses to scan the saved date span again.

The name-based daily file stays the only full-span local aggregate. A dry run of one unnest over 2016-11-14 through 2026-08-15, counting every entity subfield, is 2,105,210,623,656 bytes and was not executed. A 28-day extract that keeps the day, a hash of the article URL, the document score, and the Wikipedia URL or mid is 3,333,846,320 bytes. About 21 such slices fit in the remaining 1 TB budget, which is not the full span. The per-document lists were not pulled.

GDELT match rule, in `configs/gdelt_match_rule.json`, before the pair counts. A mention matches only when `wikipediaUrl` equals the node's English Wikipedia title, or when that URL is empty and `mid` is on the allow-list for that same title. A bare name never matches. On the 2016-11-14 sample, 13 of 29 Azure name rows and 32 of 1,077 Amazon name rows point at a different page. The bare name HP points at horsepower in 71 of 164 rows. The bare name Snap has no Snapchat row.

Samsung stays covered in Arm A. The symbol table's 546 labeled `SSNLF` rows fall on 385 distinct days. Unlabeled posts are not in that count. FNSPID news remains the headline alias, 189 days.

Subsidiary bar, before the coverage counts were used to add an edge. A day counts when it has at least 14 scored documents, and only on or after the Wikidata P580 date. The subsidiary is added when at least one arm has at least 14 such days. LinkedIn Corporation Q127278673 is owned by Microsoft from 2016-06-13. It has 14 such FNSPID days and 41 such TweetsKB days, so it is added. GitHub Inc. is owned by Microsoft from 2018-06-04 and has 0 such FNSPID days and 2 such TweetsKB days, so it is not added. Waymo, DeepMind, Fitbit, and SolarCity have a dated ownership statement and 0 such days in the windows. Beats has no P580. Activision Blizzard's preferred parent from 2023-10-13 is Xbox Game Studios, not a dated Microsoft statement. Those six are not added.

Planning SD. TweetsKB drew 20 placebo dates on each of Apple, Microsoft, and Alphabet, seed 3. All 60 dates failed to match a sector control that itself had a 14-day baseline. No paired SD is frozen. GDELT controls were not extracted, because that scan does not fit the remaining allowance, so no GDELT SD is frozen. The Arm A pooled SD is unchanged. The H4 overlap of GDELT and TweetsKB is 2016-11-14 through 2020-12-31.

## 2026-10-14 — Scale-up is a scope expansion, for the guide

The pre-registered design is 2–3 ecosystems. The owner asked for about 15–20 brands in total and a stronger general-domain layer. That is a scope expansion. It is not approved by this entry. Arms stay separate. Thresholds stay fixed before outcomes. No H1–H4 number is in the proposal. The proposal is `reports/phase2_scaleup.md`. The usable-pair counts, which are not shifts, are `reports/phase2_usable_pairs.md`.

## 2026-10-14 — H2 rule locked, before any further pair count

An H2 edge class, positive or competitor, is tested on an arm and a source only when that class has at least 10 matched pairs. The pre-registered calipers stay as they are. A class below 10 is not reported as underpowered, is not dropped, and is not rescued by a wider caliper. The fix has to keep the rules: more brands, dated ownership edges for subsidiaries or products, a larger or better control pool, or more data from a source already approved. Arms stay separate. This entry is the lock. The funnel, the LinkedIn cells, and the later pair recount come after it.

## 2026-10-14 — Funnel, LinkedIn cells, allow-list, TweetsKB rate, GDELT dry run

The positive class is the ownership and product edges plus the CEO edges whose person is listed as a positive node. Android has no such edge. The funnel is in `reports/phase2_positive_funnel.md`. No caliper was widened. No fix in that report was applied.

LinkedIn Arm A cells were inserted for days on or after 2016-06-13. News: 1,599 days and 4,572 scored documents. Social: 1,667 days, 5,655 mentions, 1,885 scored. LinkedIn Corporation has 3 Wikipedia sitelinks, stored so the popularity caliper can be applied. The arm-level news positive class stays at 10 matched pairs. The arm-level social positive class moves from 29 to 31. The two new pairs are LinkedIn on Microsoft social events.

The twelve brands are candidates on the GDELT and TweetsKB allow-list. They are not study ecosystems. The scale-up still waits for the guide. Wikidata states none of the seven proposed competitor edges, so none is added. Nike, Lowe's, the New York Times Company, Mastercard, and John Deere also have no competitor statement. Home Depot, Visa, and Caterpillar stay out. Nike's dated children Hurley International, Converse, and Umbro are on the allow-list. None has 14 days with at least 14 scored documents in Arm A, so none is a graph edge. Colgate's dated product statement points at the class toothpaste, and that class is not added. The New York Times Company and Hershey stay on the allow-list. Their coverage decision waits for the GDELT scan.

TweetsKB parts 1–9 are 97 files and 367,170,428,974 bytes. A curl transfer of `month_2013-10.n3.gz` averaged about 42,048 bytes per second. That file is about 20 hours. The nine parts are about 101 days at that rate. The other 96 files were not started. The placebo SD was not rerun and is not frozen. Parts 10–12 were not downloaded. GESIS states free access without registration. Parts 10 and 12 state non-commercial research. University research is within that use.

The GDELT allow-list dry run, project `sgnn-csp`, account singarajusrivatsa@gmail.com, first slice 2016-11-14 through 2016-12-11, processed 3,333,846,320 bytes. It was not executed. The real scan waits for a project choice: `sgnn-csp` after 1 November 2026, or one friend's project now. NELA-GT stays rejected. The guide's dataset uses `configs/source_adapter.json` when it arrives.

## 2026-10-15 — GDELT allow-list scan on sgnn-csp-2

The logged-in account is `srivatsa.singaraju2023@vitstudent.ac.in`. The project is `sgnn-csp-2`. Slices 1 through 128, from 2016-11-14 through 2026-08-14, run on this project. `sgnn-csp` is not queried. Each slice is dry-run first and refused above 10 GB. This project's own billed bytes stop at 1 TB. The October `sgnn-csp` baseline is not charged here. Every job is appended to `eval/results/bq_ledger.jsonl` with this project id and this account.

The scan finished the same day. All 128 slices are stored. Billed bytes on `sgnn-csp-2` are 435,140,165,632. Processed bytes are 435,056,000,909. The result is 27,346,316 articles, 447,753,963 bytes compressed, in `data/interim/phase2/gdelt_allowlist/`. The last slice with articles starts 2026-06-15. The two slices from 2026-07-13 and 2026-08-10 are empty. `sgnn-csp` was not queried.

## 2026-10-17 — GDELT series from the stored scan, before any Arm B outcome

The report is `reports/phase2_gdelt_series.md`. No BigQuery job was run. No caliper was widened. No shift was computed. Phase 3 does not start.

The 128 files contain 93 Wikipedia titles. 24,185,703 articles match a logged title. The series is `data/interim/phase2/gdelt_series.sqlite` and the per-document node lists are `data/interim/phase2/gdelt_documents.jsonl.gz`. The match rule is unchanged: a Wikipedia title matches, a mid matches only when the title is empty, and a bare name never matches. The full-span audit is `full_span_audit` in `configs/gdelt_match_rule.json`. `/m/0mgkg` does not assign `Amazon_(company)`. That title has 4,481,723 scored documents in the files and stays unassigned. `Meta_Platforms` has 738,060 scored documents and stays unassigned. Facebook, Pinterest, LinkedIn, Larry Page, and Sundar Pichai are absent. The concatenated Alphabet CEO title is absent and is not a node title.

160 of the 184 control-pool names are absent: ACN, ADP, ADSK, AKAM, ANSS, BR, CDNS, CDW, CTSH, EPAM, FFIV, FTNT, INTU, IT, JKHY, MSI, NTAP, PAYX, SNPS, VRSN, CHTR, CMCSA, DIS, EA, FOXA, IPG, LUMN, NWSA, OMC, SIRI, T, TTWO, VZ, BKNG, CCL, EBAY, EXPE, HD, HLT, LVS, MAR, MCD, ROST, SBUX, TGT, TJX, YUM, AXP, BAC, BLK, C, CB, GS, JPM, MET, MMC, MS, PGR, PNC, SCHW, SPGI, USB, V, WFC, ABBV, ABT, BMY, CVS, DHR, GILD, ISRG, JNJ, MDT, MRK, PFE, SYK, TMO, UNH, ZTS, BKR, COP, DVN, EOG, EPD, HAL, KMI, OKE, OXY, PSX, SLB, WMB, XOM, AEE, AEP, AWK, D, ED, EIX, ES, EXC, PCG, PEG, SRE, WEC, XEL, BA, CAT, CSX, EMR, ETN, FDX, GD, HON, ITW, LMT, NOC, NSC, PH, RTX, UNP, UPS, WM, CHD, COST, KO, MDLZ, MO, PEP, PG, PM, SYY, WMT, APD, BALL, DD, DOW, ECL, FCX, IP, LIN, MLM, NEM, NUE, PPG, SHW, VMC, AMT, AVB, CCI, DLR, EQIX, EQR, EXR, O, PLD, PSA, SBAC, SPG, VICI, WELL. EPAM has no English Wikipedia title. The other 24 pool names are the 12 candidate brands and 12 candidate competitors, which were scanned under those roles. No information-technology or communication-services control is present.

The 12 candidate brands, their named competitors, and Hurley, Converse, and Umbro are present. All 12 brands clear 14 scored days and 14 dense days, including the New York Times Company (3,344 and 1,004) and Hershey (3,435 and 1,717). No coverage decision is made here. Umbro has 8 dense days. The GDELT planning SD is blocked, so SESOI 0.05 and the 0.20 mean caliper are not converted and are not frozen.

Arm B news is NO-GO. Full-span brand events are Apple 151, Microsoft 151, and Alphabet 150. On 2016-11-14 through 2020-12-31 they are 67, 60, and 67. Those counts are above 5. Matched pairs are blocked, so H1, both H2 classes, and H4 are unestimated. The next scan is one frozen allow-list and then one rerun of about 435 GB. `sgnn-csp-2` has about 565 GB left in October. The allowance resets on 1 November 2026.

TweetsKB: the timed file stopped at 10,485,760 bytes and was not resumed. The 5 percent sample still has 60 placebo dates and 0 matched controls. Its planning SD is not frozen. The 16 competitor edges remain the confirmed study list of 2026-10-13, with no Wikidata competitor property and with P710 rejected. The proposed sourcing rule, not applied, is that an edge is added only when the user confirms the named pair or Wikidata states it on a logged property. Two-hop exclusion is a non-deprecated path of length at most 2: 38 study ids, neighborhood 1,445. Home Depot and Visa reach Apple through Vanguard. Caterpillar reaches GM through Electro-Motive Diesel. Adding them would newly block LOW, MA, and no further ticker, respectively. They stay out.

The allow-list directory still has 128 files. Checksums are `eval/results/gdelt_allowlist_sha256.txt`. The sizes sum to 447,753,963. The manifest SHA-256 is `b466aea1c0028006497eb9d4b2939cac128c9daa15ed2e34896a43069087e84c`.

## 2026-10-19 — Amendment 8, passive holders, logged before the recount

The Wikidata path check of length at most 2 drops an owner link when the owner is a passive financial holder. Owner links are P127 (the target is the owner) and P1830 (the source is the owner). A holder is passive when its Wikidata instance-of (P31) is one of: asset manager Q139906591, mutual fund Q791974 or Q55598711, pension fund Q182103, or sovereign wealth fund Q1061648. No English item has the exact label "investment management company"; that class is not added. Parent, subsidiary, brand, product, and manufacturer edges from Amendment 1 stay. The strict graph, with every owner link kept, is computed as well and is the robustness analysis.

Reason: a passive holder does not transmit brand sentiment, and the strict rule excludes popular consumer names and pushes competitor choice toward weak peers.

On the 2026-10-12 path graph, six owners meet the instance-of test: GIC Private Limited Q539627, Temasek Holdings Q762479, Government Pension Fund Global Q1196231, Qatar Investment Authority Q1571175, Kuwait Investment Authority Q1794766, and Castor Q89593177. The Vanguard Group Q849363 is instance of company, business, and enterprise. It is not instance of any of those five classes. Its product statements include mutual fund and asset management. Those product statements are not instance-of, so the Vanguard hop stays in both graphs. The recount below uses this wording and does not widen it.

## 2026-10-17 — HuffPost news-category mention check

`heegyu/news-category-dataset`, CC BY 4.0, is stored at `data/interim/news_category/data.json`. 209,527 articles, 2012-01-28 through 2022-09-23. The count is in `reports/phase2_news_category.md`. No sentiment score and no shift was computed. Five nodes pass a 14-of-28 window in 2012–2017: Apple, Alphabet, iPhone, Meta, and PINS. In that period, 119 node-days have at least 5 mentions, 113 of them with a prior 14-of-28 baseline. Those days are Meta, Pinterest, Apple, and iPhone. Articles naming Apple, Microsoft, Alphabet, or Tesla: 1,137. Articles naming any tracked node: 5,563.

## 2026-10-19 — Alias table, before the GDELT series rebuild

The table is `configs/gdelt_alias_table.json`. An alias title is accepted only when every stored row of that title carries the node's mid and the title is the same entity. `Amazon_(company)` maps to AMZN. `Meta_Platforms` maps to Meta. `Google_LLC` maps to Alphabet. `Apple`, `Apple_logo`, `Apple_Computer`, and `Apple_computer` map to Apple. `Youtube` maps to YouTube. `IPhones` maps to iPhone. `Android_(Betriebssystem)` and `Android_(OS)` map to Android. `Snap_Inc.` does not map to SNAP: its mid is `/g/11c1s2xz66`, and Snapchat's mid is `/m/0nbtf_n`. Hewlett Packard Enterprise does not map to HP Inc. `Planet_Google`, `Author_Rank`, and `Ludicrous_Mode` are rejected. Lowe's has no second title. Its 2023 hole is in the extract: 0 rows.

Corrected scored days and dense days, after the rebuild: AMZN 3,482 and 3,482. Meta 1,676 and 1,676, beginning in 2021. Lowe's 2,221 and 1,937, with 2023 still 0. Alphabet 3,480 and 3,480. SNAP 3,471 and 3,469. Apple 3,482 and 3,482.

## 2026-10-19 — Recount under Amendment 8, after the log above

Ten owner edges are dropped. The eligible control counts for Apple, Microsoft, Alphabet, and Tesla stay 13, 13, 9, and 11. Arm A usable pairs on the current series, which already contains the LinkedIn cells, are the same under the strict graph and under Amendment 8: news H1 37 pairs and 20 events, news positive 10, news competitor 27, social H1 209 pairs and 157 events, social positive 31, social competitor 178. The positive funnel control column is unchanged: Apple news 0, Apple social 0, Microsoft news 0, Microsoft social 2, Alphabet news 0, Alphabet social 0. Alphabet social comparisons stay 426, with mean 189, SD 273, mention 96, and popularity 0.

The Vanguard Group is still the hop that keeps Home Depot, Visa, Mastercard's rival Visa, and the other consumer names inside the two-hop set. Amendment 8 does not drop that hop.

## 2026-10-19 — Left-out names retested on the Amendment 8 graph

A name returns when it is not a confirmed competitor and the 2026-10-12 path graph has no path of length at most 2 under Amendment 8. SSNLF, SMSN, and SSNGY stay out because Samsung is a confirmed competitor. Nvidia, Intel, and Netflix stay out through Vanguard. Stellantis stays out through the product class truck, shared with Ford. The names that return, with sitelinks and the bucket given by the logged industry map, are in `reports/phase2_amendment8.md`. A missing industry label is not given a bucket. Garmin Ltd. returns by the path rule and has 0 sitelinks, so it cannot be selected.

## 2026-10-19 — Rival proposals, no edges added

A pair is proposed only where the brand's English Wikipedia article names the rival. The location is logged in the report. Yum, Kimberly-Clark, Merck, Caterpillar, Duke Energy, Southern Company, Under Armour, News Corp, and Gannett are not proposed: the fetched article text does not contain those strings. No edge is written.

Eligibility rule, before any outcome on a new brand: a new brand is eligible for an arm when it clears the coverage bar on at least one source in that arm. H4 counts only events that have both sources.

## 2026-10-19 — Frozen allow-list, pilot not queried

The list is `configs/gdelt_frozen_allowlist.json`: 260 entities, 273 titles, 232 mids. Ambiguous tickers ADP, BMY, C, FOXA, HAL, MRK, and NWSA have no title and no mid. The concatenated Alphabet CEO title is absent. Larry Page and Sundar Pichai are separate titles. The three-day pilot and the 28-day dry run were not sent. `gcloud auth print-access-token` for `srivatsa.singaraju2023@vitstudent.ac.in` failed with reauthentication required. The command is in the report. The 128-slice loop was not started.

## 2026-10-19 — TweetsKB range test

`month_2017-06` is in Zenodo record 1765240. That record's file list was empty and the files endpoint returned 403. The test used `month_2017-11.n3.gz` on record 1808741, which is inside 2016-11 through 2020-12. Six parallel 1 MB range requests for 603.8 seconds returned 206 and 843,055,104 bytes, 1.396 MB/s. DNS did not fail. Nothing was saved. The rate is above 1 MB/s, so a later download starts with 2016-11 through 2020-12. That download was not started.

## 2026-10-19 — HuffPost news-category set is not an arm

`heegyu/news-category-dataset`, CC BY 4.0, is not an arm. Apple has 493 mentions in 10 years, 2 days at the 5-mention floor, and 0 events with the 14-of-28 baseline. Microsoft has 87. Tesla has 76. Alphabet has 530. The Meta and Pinterest counts are inflated by "on Facebook" and "on Pinterest" boilerplate and are not brand events. The set is reserved as a source for the Phase 3 hand-label pool: 1,137 articles naming Apple, Microsoft, Alphabet, or Tesla, of which 503 are TECH and 148 are BUSINESS. Phase 3 does not start.

## 2026-10-20 — Amendment 8 revised, universal owners, logged before the recount

The 2026-10-19 owner test is replaced. An owner link is dropped when that owner holds a non-deprecated ownership statement on at least 25 percent of the 206 retained tickers. Ownership statements are P127, where the target is the owner, and P1830, where the source is the owner. Twenty-five percent of 206 is 51.5, so the count is at least 52 tickers. The list is computed from `kg/snapshots/wikidata_2026-10-12/path_edges.json` and stored in `configs/amendment8_revised_owners.json` before the recount. One owner meets the test: The Vanguard Group Q849363, 53 tickers, share 0.257282. BlackRock Q219635 holds 50, share 0.242718, and is not dropped. Every other Amendment 1 edge type stays. The strict graph, with every owner link kept, is the robustness check.

Reason: a universal owner connects the pool to the study nodes and carries no firm-specific brand information. The 2026-10-19 class test left this owner in, because Vanguard is typed company, business, and enterprise.

## 2026-10-20 — Manual buckets, logged before the recount

These tickers receive a bucket by this entry. AMAT, MU, LRCX, KLAC, and QCOM are information technology. NFLX is communication services. AAP and GPC are consumer discretionary. GRMN stays ineligible because it has no sitelinks. The industry map is not edited. A name is added to the pool only when the revised path check finds no path of length at most 2 and the name is not a confirmed competitor. Intel stays out through a parent/subsidiary path to Microsoft. Netflix stays out because Netflix and YouTube both have the product class streaming media. Stellantis stays out through the product class truck, shared with Ford. Nvidia returns and takes information technology from the logged semiconductor mapping. Garmin is not added.

## 2026-10-20 — Competitor edges added, before the recount

Eleven competitor edges are in `kg/phase2_structural_edges.json`, sign −1, reverse not asserted. The source is the brand's English Wikipedia article retrieved 2026-10-19. The pairs are Chipotle–McDonald's, T-Mobile–AT&T, T-Mobile–Verizon, Lowe's–Home Depot, Mastercard–Visa, Chevron–ExxonMobil, Hershey–Mondelez, Colgate–Procter & Gamble, Lilly–Pfizer, Lilly–AbbVie, and Nike–Adidas. Nike–Adidas is Arm B news only, because Adidas has no ticker. NextEra Energy is not an ecosystem. John Deere and the New York Times Company are not given edges in this entry. Rivals of the eleven new brands leave the control pool only for the ecosystem that names them. The new brand tickers leave the control pool. Ecosystems are 13. Brand nodes are 13.

## 2026-10-20 — John Deere and New York Times 10-K, no edges added

Deere & Co, CIK 0000315189, 10-K filed 2025-12-18, accession 0001104659-25-122321, period ended 2025-11-02. Item 1 Competition names Caterpillar Inc., which is retained as CAT. AGCO, CLAAS, CNH Industrial, Kubota, Toro, Doosan, Hitachi, Komatsu, Volvo, and Terex are named and are not retained tickers. The New York Times Company, CIK 0000071691, 10-K filed 2026-02-27, accession 0000071691-26-000011, period ended 2025-12-31. Item 1 Competition names Apple, Alphabet, Meta Platforms, and Microsoft, which are retained. The Wall Street Journal, ESPN, The Washington Post, CNN, BBC News, The Guardian, Financial Times, ByteDance, OpenAI, Perplexity, and X are named and are not retained tickers. No edge is written for either company.

## 2026-10-20 — Recount under the revised owner rule

The rule above was already logged. The pool is the 2026-10-20 pool: returned names are in, and the new brand tickers are out. Counts are in `eval/results/phase2_revised_recount.json`. Strict graph, every owner link kept: news H1 28 pairs and 20 events, news positive 6, news competitor 22, social H1 179 pairs and 133 events, social positive 28, social competitor 151. Eligible controls: Apple 22, Microsoft 22, Alphabet 8, Tesla 17. Revised graph, Vanguard links dropped: news is unchanged at H1 28, positive 6, competitor 22, and 20 events. Social H1 is 193 pairs and 143 events, social positive 28, social competitor 165. Eligible controls: Apple 24, Microsoft 23, Alphabet 8, Tesla 17. The names the revision adds are AKAM and NVDA for Apple, and NVDA for Microsoft. AKAM is the one of those with an Arm A series. The positive funnel is the same on both graphs: Apple news 14/14/0/0, Apple social 171/96/35/0, Microsoft news 5/5/1/0, Microsoft social 110/29/16/2, Alphabet news 15/15/5/0, Alphabet social 142/93/93/0. Alphabet social comparisons are 338, with mean 145, SD 216, mention 76, and popularity 0.

TweetsKB 5 percent placebo, seed 3, revised graph. Alphabet has 0 eligible dates, so the draw is Google. Apple: 20 dates, 14 controls in the 5 percent file, 10 eligible controls absent from that file, 280 comparisons, 8 with a 14-day baseline, 13 dates with zero baselines, and among the baselines mean 8, SD 5, mention 2, popularity 0. Microsoft: 20 dates, 13 in the file, 10 absent, 260 comparisons, 6 baselines, 15 dates with zero baselines, mean 6, SD 4, mention 0, popularity 0. Google: 20 dates, 8 in the file, 0 absent, 160 comparisons, 20 baselines, 7 dates with zero baselines, mean 20, SD 0, mention 0, popularity 0. No comparison passes popularity.

## 2026-10-20 — GDELT frozen pilot, full loop not started

Auth for `srivatsa.singaraju2023@vitstudent.ac.in` on `sgnn-csp-2` succeeded. The first 28-day dry run is 3,333,846,320 bytes. The one-day dry runs are 109,737,084, 150,532,179, and 0. October query bytes billed on that project, from `JOBS_BY_PROJECT`, are 435,353,026,560. Remaining of the 1 TB cap is 564,646,973,440. The projected 128 slices plus a 50 GB margin fit in that remainder. `geg_gcnlapi` has no rows for 2025-06-16: the dry run and the execution both process 0 bytes. The stored extract already skips 2025-06-13 through 2025-07-01. Gate (c) fails. Cisco is not on the frozen allow-list and returns rows on 0 of the 3 days. The other eighteen large names return rows on 2016-11-14 and 2020-03-16. The 128-slice loop was not started.

## 2026-10-20 — FIRE collections are not used

FIRE English collections (Telegraph 2001-2010, 303,420 entries; BDNews24, 89,610 files from 2009) were checked by stream-count only and are NOT used: era precedes TweetsKB, most nodes near zero. Line counts: Microsoft 1,607/762, Google 1,210/751, Apple 1,721/482 (fruit included), iPhone 661/280, Tesla 10/1.

## 2026-10-21 — Gate (c) waiver and allow-list expansion, before the rerun

Cisco was never on the allow-list. The 2026-10-20 gate (c) failure on Cisco is waived. The allow-list is expanded once, before the only rerun, because bytes billed do not depend on the name filter. The additions are Cisco, Texas Instruments, PayPal, ServiceNow, Uber, Airbnb, Spotify, Twitter, and Zoom; every Wikidata S&P 500 constituent that is not yet listed and has at least 60 sitelinks; and every parent organization (P749) of a consumer-facing brand that is not yet listed and has at least 60 sitelinks. Titles and mids come from the English Wikipedia title and Wikidata P646. Each addition is flagged "reserve, Arm B controls only". An addition is not an Arm A control and not a graph edge. The list must contain, with a title and a mid: Pinterest (title Pinterest), LinkedIn (the English page title, not only LinkedIn_Corporation), Meta (Facebook and Meta_Platforms), Larry_Page, and Sundar_Pichai. Ticker PINS is mapped through the Pinterest page.

## 2026-10-21 — Pilot days, before the rerun

2025-06-16 is inside the GDELT gap. The pilot days are 2016-11-14, 2020-03-16, 2022-06-15, and 2025-09-16. The 128-slice loop starts only when every dry run is at most 10 GB, the projected total plus a 50 GB margin is inside the remaining allowance, each named large company returns rows on at least 3 of the 4 days, Pinterest, LinkedIn, Larry_Page, Sundar_Pichai, and the Arm B study nodes return rows on at least 2 days where they existed, Meta returns rows on 2022-06-15 and 2025-09-16, and the projected compressed result fits with 3 GB spare. A failed gate stops the loop.

## 2026-10-21 — Control pool restore, before the recount

A name is excluded as a control only by the per-event path rule and by being a direct competitor of that event brand. The path has length at most 2 and starts at the event brand or its target. A name that is a brand or a rival in another ecosystem stays eligible for this event. The new-brand tickers and the rival tickers return to the pool on that basis. The industry map is not edited. Calipers are not widened.

## 2026-10-21 — Deere edge, before the recount

Deere–Caterpillar is added, sign −1. Caterpillar is named in Deere's 10-K Item 1 Competition, filed 2025-12-18, and CAT is a retained ticker. The New York Times Company is not an ecosystem. Its 10-K names Apple, Alphabet, Meta, and Microsoft, which would merge it into the core ecosystems. It stays a reference node. NextEra Energy stays out.

## 2026-10-21 — TweetsKB and the hand-label sample, before any score

The TweetsKB download for 2016-11 through 2020-12 starts now and does not wait on the GDELT rerun. Phase 3A is the hand-label sample only. Phase 3 scoring does not start.

## 2026-10-21 — Recount after the pool restore

The exclusion rule above was already logged. Strict graph: news H1 37 pairs and 20 events, news positive 10, news competitor 27, social H1 271 pairs and 194 events, social positive 36, social competitor 235. Eligible controls: Apple 22, Microsoft 22, Alphabet 11, Tesla 27. Revised graph: news is unchanged. Social H1 is 285 pairs and 204 events, social positive 36, social competitor 249. Eligible controls: Apple 24, Microsoft 23, Alphabet 11, Tesla 27. The positive funnel is the same on both graphs: Apple news 14/14/0/0, Apple social 171/96/35/0, Microsoft news 5/5/1/0, Microsoft social 110/29/16/2, Alphabet news 15/15/5/0, Alphabet social 142/93/93/0. Alphabet social comparisons are 596, with mean 268, SD 394, mention 153, and popularity 0.

Alphabet communication candidates under the revised graph, with every reason that applies: EA is eligible. CHTR, CMCSA, DISH, IPG, LUMN, NYT, OMC, SIRI, TMUS, and TTWO are outside the popularity caliper against Alphabet's 211 sitelinks. DIS, T, and VZ are on a path to the event brand. NFLX is on a path and has no Arm A series. FOXA and NWSA are ambiguous. AMZN, FB, META, PINS, and SNAP are direct competitors and are not in the communication bucket.

## 2026-10-21 — Allow-list expanded, pilot passed, full loop started

The expanded list is `configs/gdelt_frozen_allowlist.json`: 274 entities, 290 titles, 247 mids. Named additions include Cisco, Texas Instruments, PayPal, ServiceNow, Uber, Airbnb, Spotify, Twitter, and Zoom Communications. Twitter carries the titles Twitter and X_(social_network), mid `/m/0289n8t`. PayPal has the title PayPal and no P646 mid. Pinterest and PINS both carry the title Pinterest and mid `/m/0h3tm0f`, mapped from the Pinterest page Q255381. LinkedIn carries LinkedIn and LinkedIn_Corporation, mid `/m/03vgrr`. Meta carries Facebook and Meta_Platforms, mid `/m/0hmyfsv`. Larry_Page and Sundar_Pichai are present with titles and mids. Wikidata P361 lists 528 S&P 500 constituents. 38 have at least 60 sitelinks. The ones not already listed are Delta Air Lines, Alphabet Inc., and Red Hat. Three parent organizations were already on the list.

Pilot days 2016-11-14, 2020-03-16, 2022-06-15, and 2025-09-16. Every dry run is at most 3,333,846,320 bytes. October billed bytes on sgnn-csp-2 before the full loop were 435,922,403,328. The 128-slice projection plus 50 GB fits in the remainder of 1 TB. The nineteen large names, including Cisco, return rows on all four days. Pinterest, LinkedIn, Larry Page, Sundar Pichai, and the Arm B study nodes return rows on at least two days. Meta returns rows on 2022-06-15 and 2025-09-16. The projected compressed result is about 1.6 GB, and free space was 13 GB. The full loop was started.

## 2026-10-21 — TweetsKB months and the hand-label sheet

Zenodo records 1757118 and 1765240 return 403 on the files endpoint, and the download URL redirects to a login page. The unreachable months are 2016-11 and 2016-12 through 2017-10. The reachable files are 2017-11 through 2020-12, 38 files. `month_2017-11.n3.gz` is downloading. The hand-label sheet is `data/handlabel/sample.csv`, 450 rows, labels blank, with 100 double-coded ids listed in `data/handlabel/INSTRUCTIONS.md`. The folder is gitignored. Phase 3 scoring does not start.

## 2026-10-21 — Phase 3 gate procedure, before any score

The filled sheet is `data/handlabel/sample.csv`. This entry starts the Phase 3 scorer gate only. Event detection does not start. No outcome is computed.

TweetsKB. The single-stream download of `month_2017-11.n3.gz` is stopped at byte 2,449,879,500 of 3,522,219,692. The replacement is the 2026-10-19 method: six parallel 1 MB range requests, resumed from that byte, TLS verification left on. Workers pause while free disk is under 6 GB. The GDELT rerun is left running.

Hand labels. Cohen's kappa is the unweighted nominal kappa on the 100 rows that have both `label_A` and `label_B`, over whatever labels the annotators used. A disagreement is a shared row whose two labels differ. Those rows are written to `data/handlabel/disagreements.csv` and are not in the gold set. The gold label is the shared label when the two annotators agree, and `label_A` when `label_B` is blank. Rows whose gold label is `not_about_brand` are dropped and counted. The gold set is not used to train.

Scorers. VADER compound above 0.05 is positive, below −0.05 is negative, and the closed interval between them is neutral. VADER and FinBERT (`ProsusAI/finbert`) score the text only. FinBERT is the comparison baseline already logged; it is not the primary scorer. The primary scorer is an entity-aware classifier. Its base is `distilbert-base-uncased`, chosen because it is small enough for this MacBook Air. The input is the tokenizer's pair encoding of the entity and the text, which is the `[entity] [SEP] text` form. Training data are the entity-level labels in SEntFiN 1.0 and FinEntity only. The random split is on source documents, seed 20261021, 80 percent train, 10 percent validation, and the remainder test, so one headline or paragraph is not in two splits. Three epochs, learning rate 2e-5. The first execution used batch 16 and maximum length 160 on the GPU. That process held 5.2 GB on this 8 GB machine and swapped instead of finishing an epoch, so it was stopped before any test or gold score. The execution that follows uses the CPU, batch 4, and maximum length 128, with the same base model and the same split. The checkpoint with the highest validation macro-F1 is the one evaluated. The test-split macro-F1 is computed before the gold set is scored. Macro-F1 is the unweighted mean of the positive, negative, and neutral F1 scores, and a class with no predictions and no gold rows in a slice contributes 0. The gold-set interval is a 1,000-draw bootstrap, percentile 2.5 and 97.5, seed 20261021. The gate is macro-F1 at least 0.70 for the primary scorer on the gold set. The gold set is not used to choose a model, a threshold, or a feature.

## 2026-10-21 — Sleep check, nothing restarted

The GDELT loop was still running, with 45 of 128 slices stored and slice 2020-04-27 executing as BigQuery job `sgnn2_frozen_20200427_1792535531`. That job is a dry run in the ledger and has no stored file, so it was not started again. The post-rerun waiter was still waiting. Phase 3 training was still in epoch 2. The TweetsKB download had already finished and the reducer had deleted the raw file after a zero-tweet parse; the saved offset is the end of the file, so it was not resumed. The gcloud login for `srivatsa.singaraju2023@vitstudent.ac.in` on `sgnn-csp-2` was still valid.

## 2026-10-21 — TweetsKB reducer matched nothing because the id pattern was decimal

The November 2017 file was reduced to 0 tweets and the raw file was deleted. That was a reducer bug. Tweet ids in the N3 are hexadecimal, as in `_:t0000660e789b597ef47f771084d84309`. The post, emotion, and entity patterns required decimal digits, so none of them matched. The predicates were already the right ones: `nee:hasMatchedURI` for the entity and `onyx:hasEmotionIntensity` for the positive and negative scores. The URIs are `http://dbpedia.org/resource/...`. A 50 MB range sample, TLS left on, parses 293,116 posts, 156,325 with any DBpedia URI, and 7,476 on the scan allow-list. The reducer now stops if it reads more than 1,000 lines and parses 0 posts, or parses more than 1,000 posts and matches 0. The raw file is deleted only after the matched count is non-zero and the month row has been written to `eval/results/tweetskb_month_stats.jsonl`. The full month is downloaded again from byte 0 because the saved offset was the end of a file that had already been deleted.

## 2026-10-21 — Phase 3 scorer gate fails

The CPU run finished. The document split is 9,385 train, 1,173 validation, and 1,174 test. The selected checkpoint is epoch 3, validation macro-F1 0.8601. The test-split macro-F1, computed before the gold set, is 0.8657. On the gold set of 432 rows the primary scorer is 0.5319, bootstrap interval 0.482 to 0.578. VADER is 0.5624, interval 0.512 to 0.612. FinBERT is 0.4808, interval 0.429 to 0.527. The gate is 0.70 and the primary scorer fails it. The gold set was not used to change the model, the threshold, or a feature. Event detection does not start. The numbers are in `eval/results/phase3_gate.json`.

## 2026-10-21 — Phase 3 adaptation plan, fixed before the run

The untouched primary scorer is 0.5319 on the gold set. VADER is 0.5624. FinBERT is 0.4808. The 0.70 gate failed. Event detection stays off. The plan below is fixed before any adapted score is computed.

Stage 1 is five-fold adaptation of the saved epoch-3 checkpoint, `data/interim/phase3/entity_classifier/best.pt`. That file is epoch 3 because its validation macro-F1, 0.8601, is the highest of the three epochs. The gold set is the same 432 items. The seed is 20261021. Text is casefolded, punctuation becomes spaces, and whitespace is collapsed. Two items are linked when those strings are equal, or both have at least 8 words and the Jaccard similarity of the word sets is at least 0.8, or the shorter string has at least 40 characters and is contained in the longer one. A linked group stays in one fold. The group's stratum is its source and class when every member shares both, and `mixed` otherwise. Within a stratum the groups are ordered by the smallest item id, shuffled with the seed, and given to the fold that currently holds the fewest items. Ties go to the lower fold index. Each item is in one fold, so it is never in the train set and the test set of the same fold.

Each fold reloads the epoch-3 checkpoint. It fine-tunes on the other four folds. Each epoch adds 2,000 examples drawn from the SEntFiN and FinEntity training documents of the original split, seed 20261021, and shuffles them with the hand labels into one stream. The draw for fold `k` and epoch `e` uses seed `20261021 + 10 * (k + 1) + e`. The recipe is learning rate 2e-5, four epochs, and the weights after the fourth epoch. There is no search and the held-out fold is not used to stop or to pick an epoch. The optimizer step averages 16 examples, and the last group of an epoch is smaller when the stream does not divide evenly. The forward pass uses 4, or 2 if the process exceeds 2.5 GB, so this 8 GB machine does not swap. If the pooled score passes, the same recipe is fit on all 432 items with replay seed `20261021 + 10 * 6 + e` for epoch `e`. The reported number is the pooled out-of-fold macro-F1. The interval is 1,000 bootstrap draws, seed 20261021. The same figure is reported by source, with the confusion matrix and the five fold scores. At least 0.70 passes. Only then is the same recipe fit on all 432 items and saved. That fit is not the gate number.

Stage 2, `roberta-base` with the same pretraining and the same five-fold recipe, starts only if Stage 1 is under 0.70 and only after a separate go-ahead. It is not started in this run. The GDELT loop and the TweetsKB download are left running.

## 2026-10-21 — Phase 3 adaptation result

The five-fold run followed the plan above. No two of the 432 texts met the near-duplicate rule, so each item was its own group. The folds hold 87, 87, 86, 86, and 86 items. The forward batch stayed 4. The run took 1,906 seconds. The pooled out-of-fold macro-F1 is 0.5786, interval 0.532 to 0.624. The fold scores are 0.501, 0.631, 0.533, 0.611, and 0.608. By source: HuffPost 0.488, FNSPID 0.610, StockTwits 0.621. The gate is 0.70 and this estimate fails it. The full-data fit was not saved. Event detection stays off. The numbers are in `eval/results/phase3_adapt.json`.

`roberta-base` was not started. DistilBERT needed 0.16 seconds for one batch of 4. RoBERTa-base has twice as many layers at the same width, so the same pretraining is about 55 minutes and the same five-fold recipe is about 65 minutes, about 2 hours together. If the process exceeds 2.5 GB and the forward batch drops to 2, the five-fold part doubles and the total is about 3 hours. It waits for a go-ahead.

StockTwits. The Arm A social series is the user label: bullish is +1, bearish is −1, and a message with no user label does not enter the daily mean. No text scorer is applied. On the four brand series, 17,288 of 21,189 mention-days (81.6 percent) have at least one user label, and 4,897,352 of 11,921,841 messages (41.1 percent) carry one. Every day that has a sentiment value relies on those user labels. Among gold items whose hand label is positive or negative and that have one user label, n is 40, agreement is 0.675, and two-class macro-F1 is 0.637. Fifty of the 90 positive or negative StockTwits gold items have no user label.

## 2026-10-21 — Stage 2 and one enlarged-label attempt, fixed before either run

Stage 1 pooled out-of-fold macro-F1 is 0.5786. The gate stays 0.70 on pooled out-of-fold predictions from the same five-fold recipe. Event detection stays off. This entry is not revised after the scores are known.

Stage 2 is approved. The base is `roberta-base`. Pretraining uses the same SEntFiN and FinEntity document split, seed 20261021, three epochs, learning rate 2e-5, batch 4, and maximum length 128, on CPU. The checkpoint with the highest validation macro-F1 is kept, and an equal score keeps the earlier epoch. Its test-split macro-F1 is reported before any hand-label score. The five-fold protocol on the existing 432 items is the one already fixed: the same near-duplicate rule, seed 20261021, four epochs, learning rate 2e-5, 2,000 replayed training examples per epoch, the weights after the fourth epoch, and an optimizer step of 16 examples. The forward batch is 4. If the process exceeds 2.5 GB, the forward batch drops to 2 for the rest of the run, including the remainder of pretraining. The learning rate and the epoch counts do not change. Fold weights are not saved. The pretrain checkpoint is kept so the enlarged run can reload it. The gate number is the pooled out-of-fold macro-F1. FNSPID-only and the StockTwits user-label two-class macro-F1 are reported beside it. HuffPost is reported and does not gate. A passing score does not by itself fit a model on all 432 items.

One enlarged-label attempt follows only after `sample2.csv` is filled. It uses the same five-fold recipe on the combined gold set. The starting checkpoint is the better of the two base models on the existing 432 items, DistilBERT from Stage 1 or RoBERTa from Stage 2, chosen by the pooled out-of-fold macro-F1. The report gives the pooled macro-F1 with a 95 percent interval, FNSPID-only, StockTwits text-only, HuffPost-only, and the StockTwits user-label two-class macro-F1 and kappa on the shared items. The gate remains the pooled figure of 0.70.

Stopping rule: if the enlarged attempt is still under 0.70, the log records "gate not met", the number is not changed, and Phase 4 carries the best-scorer series as the main series and a VADER series as the robustness series. The report states that limitation. The GDELT loop and the TweetsKB download are not touched.

The extra sheet is drawn before Stage 2, with seed 20261021. `data/handlabel/sample2.csv` has the same columns as `sample.csv`. A tracked node is an ecosystem, a positive node, a competitor node, or an alias node in `configs/phase2_nodes.json` and `configs/phase1_universe.json`. A headline alias is a brand alias, an alias-node alias, or a node name that contains a lowercase letter. The alias must be at least four characters. A ticker of only capital letters is not a headline alias. A headline is drawn when exactly one tracked node matches and the collapsed text is not already in `sample.csv`. The draw is 200 FNSPID headlines. The StockTwits draw is 50 bullish and 50 bearish messages, each with exactly one cashtag that maps to a tracked node, and the collapsed text is not already in `sample.csv`. The sheet has no user label, no ticker column, and no score. The node column is the tracked node name. The 300 rows are shuffled. Fifty are double-coded, 25 from each source, and the StockTwits half alternates the two hidden user-label classes. Those classes are not written in the sheet. Item ids are HL1001 through HL1300. The label words and the annotator rules stay the ones already in `INSTRUCTIONS.md`.

## 2026-10-21 — Stage 2 result

`roberta-base` pretraining selected epoch 1, validation macro-F1 0.8807. The test-split macro-F1, computed before the gold set, is 0.8857. The process exceeded 2.5 GB, so the batch dropped to 2 for the rest of the run. The pooled out-of-fold macro-F1 on the 432 items is 0.6103, interval 0.559 to 0.655. The fold scores are 0.648, 0.663, 0.613, 0.539, and 0.579. FNSPID-only is 0.606. HuffPost is 0.518 and does not gate. The StockTwits user-label two-class macro-F1 on the 40 shared items remains 0.637. The gate is 0.70 and Stage 2 fails it. Fold weights were not saved. The pretrain checkpoint is `data/interim/phase3/entity_classifier/roberta_pretrain.pt`. On the existing 432 items this score is above the DistilBERT out-of-fold score of 0.5786, so the enlarged attempt, when `sample2.csv` is filled, starts from this RoBERTa checkpoint. Event detection stays off. The numbers are in `eval/results/phase3_roberta.json`.

## 2026-10-21 — Enlarged sheet checked, attempt started

`sample2.csv` has the original 300 ids, HL1001 through HL1300. Every `label_A` is one of positive, negative, neutral, or not_about_brand. `label_B` is filled on the 50 listed ids only, and each of those is a valid word. Source, node, and text match the seed-20261021 draw. Cohen's kappa on the 50 shared items is 0.5724, with agreement 0.70. Fifteen rows disagree and are in `data/handlabel/disagreements2.csv`. Four rows are dropped because the resolved label is `not_about_brand`: HL1020, HL1034, HL1057, and HL1089. The new gold set has 281 items, 192 FNSPID and 89 StockTwits. Combined with the existing 432, the gold set has 713 items. Label A on the sheet: FNSPID 110 neutral, 54 positive, 34 negative, 2 not_about_brand; StockTwits 30 neutral, 30 positive, 37 negative, 3 not_about_brand.

The enlarged attempt starts from `roberta_pretrain.pt`. The five-fold recipe is unchanged. The forward batch is 2 from the start, because Stage 2 exceeded 2.5 GB. Stage 2 spent about 2 hours 5 minutes on the five folds. This gold set is 713 items against 432, so the same recipe is about 2 hours 20 minutes. A passing score then fits the same recipe on all 713 items, about 30 minutes more. The gate stays 0.70. Event detection stays off.

## 2026-10-21 — Enlarged attempt: gate not met

The pooled out-of-fold macro-F1 on 713 items is 0.6170, interval 0.577 to 0.656. The gate is 0.70. Gate not met. The number is not changed. The full-data fit was not saved. Event detection does not start.

The fold scores are 0.690, 0.647, 0.632, 0.587, and 0.524. FNSPID-only is 0.691, interval 0.634 to 0.742. StockTwits text-only is 0.578, interval 0.514 to 0.641. HuffPost is 0.490, interval 0.402 to 0.576, and does not gate. On the 101 StockTwits gold items whose hand label is positive or negative and that have one user label, two-class macro-F1 is 0.790 and agreement is 0.792. The numbers are in `eval/results/phase3_enlarged.json`.

This 0.6170 is the highest pooled out-of-fold score of the registered attempts. DistilBERT adaptation was 0.5786 and RoBERTa on the original 432 was 0.6103. Phase 4 uses that best scorer as the main series and VADER as the robustness series. The choice is `configs/phase4_series.json`. The limitation is that the main series did not clear 0.70, so a Phase 4 result from it is read next to the VADER series. The StockTwits daily series remains the user label. The RoBERTa fold weights were not kept.

## 2026-10-21 — Final fit carries the best scorer, before the fit

Training the final fit on all 713 gold items is part of carrying the best scorer into Phase 4. It does not change the gate number, which stays 0.70, and it does not change the gate-not-met entry above. The fit is not an accuracy estimate. The recorded training loss is not a claim about the gold set. The recipe is the one already fixed: start from `data/interim/phase3/entity_classifier/roberta_pretrain.pt`, four epochs, the weights after the fourth epoch, learning rate 2e-5, 2,000 replayed SEntFiN and FinEntity training examples each epoch, an optimizer step of 16 examples, and forward batch 2. The replay seed is `20261021 + 60 + epoch`. Rows whose resolved label is `not_about_brand` stay out. Weights go to `data/interim/phase3/final_scorer/`. Event detection stays off until the next reports are reviewed.

## 2026-10-21 — Final fit saved, linking precision, FNSPID scoring started

The final fit finished on the 713 gold items. Mean training loss by epoch was 0.4724, 0.3719, 0.3245, and 0.2773. The saved weights are the fourth epoch. The checkpoint is `data/interim/phase3/final_scorer/model.pt`, sha256 `41d769b3d5a292de5f41c2908ae44020cb9570d223b7523edca9a226cd692559`, and that hash is in `configs/phase4_series.json`. These losses are training metrics on the mixed gold and replay stream. They are not an accuracy claim, and they do not change 0.70 or the gate-not-met entry. The forward batch stayed 2. The run took 1,331 seconds. Event detection stays off.

Linking precision uses both hand-label sheets and only the FNSPID and StockTwits rows. Every row was drawn from a mention the linker had already attached to a node, not from unlinked text. The resolved label is `label_A` when `label_B` is blank, and the shared label when the two coders agree. Disagreements are left out of the denominator. A brand node is one of the 14 ecosystem names, or Meta, or Samsung. A product node is a positive node other than a CEO node and other than LinkedIn. A person node is a name ending in CEO. Every other node, including ticker-only competitors and LinkedIn, is other. Precision is 1 minus the share of resolved rows labeled `not_about_brand`. The comparison line is 0.90. The intervals are 95 percent Wilson intervals. The full figures are in `eval/results/phase4_linking_precision.json`.

FNSPID brand: n=334 after 10 disagreements, 2 not-about, share 0.0060, Wilson 0.0016 to 0.0216, precision 0.9940, Wilson 0.9784 to 0.9984. FNSPID product: n=2, precision 1, Wilson 0.342 to 1. FNSPID person: n=1, precision 1, Wilson 0.207 to 1. FNSPID other: n=2, precision 1, Wilson 0.342 to 1. FNSPID overall: n=339 after 10 disagreements, 2 not-about, precision 0.9941, Wilson 0.9787 to 0.9984. StockTwits brand: n=198 after 13 disagreements, 0 not-about, precision 1, Wilson 0.9810 to 1. StockTwits product and person: no rows. StockTwits other: n=36 after 4 disagreements, 2 not-about, share 0.0556, Wilson 0.0154 to 0.1814, precision 0.9444, Wilson 0.8186 to 0.9846. StockTwits overall: n=234 after 17 disagreements, 2 not-about, precision 0.9915, Wilson 0.9694 to 0.9977. The point estimate is at or above 0.90 in every cell that has rows. The Wilson lower bound is also at or above 0.90 for FNSPID brand, FNSPID overall, StockTwits brand, and StockTwits overall. It is below 0.90 for FNSPID product, person, and other, and for StockTwits other, because those samples are small.

FNSPID has 731,458 documents with a day and 796,942 (document, node) pairs across 207 nodes in the 14 ecosystems and the control pool. A pair is the Phase 2 ticker or alias link, plus a control-pool ticker when the row ticker is in the pool and is not already mapped. The text is the headline, summary, and body joined, which is the blob the linker searches. One thousand of those pairs, a reservoir draw with seed 20261021, took 37.392 seconds at forward batch 2, 26.74 pairs per second. The full run is 8.28 hours, under the 12 hour line, so it was started. It is detached and resumable. Per-pair scores are `data/interim/phase3/fnspid_scores/parts/`. Per-node per-day aggregates are `data/interim/phase3/fnspid_scores/daily.sqlite`. The log is `eval/results/phase4_fnspid_score.status`. The job pauses while free disk is under 6 GB. The VADER FNSPID series is unchanged and remains the robustness series. The count and the timing are in `eval/results/phase4_fnspid_pair_count.json` and `eval/results/phase4_fnspid_time.json`.

Status the same afternoon. The GDELT loop is still running. 45 of 128 slices are stored, 2016-11-14 through 2020-03-30. The ledger's last executed slice is 2020-03-30, billed 2,724,200,448 bytes, and the running month total before the next execution is 553,937,534,976 bytes. That leaves 446,062,465,024 bytes of the 1 TB cap. The 2020-04-27 slice has a dry run only, filed at 2026-10-20T22:32:11Z, and its file is not stored. The loop process and its `bq query` are still alive, and the status file has not moved since that dry run. The dependent Arm B steps have not run. `eval/results/phase2_gdelt_reserve_after.status` is empty, and the report on disk, `reports/phase2_gdelt_series.md`, is the 2026-10-17 report from before this rerun. TweetsKB has reduced 12 months, 2017-11 through 2018-10. Matched counts: 498,920, 463,655, 477,988, 436,638, 482,465, 283,989, 258,137, 247,824, 248,614, 260,571, 311,900, and 268,346. November 2018 is downloading, about 1.52 MB/s at the start of the file. Twenty-six files and about 96.8 GB remain, about 18 hours of transfer at that speed, plus about six minutes of reducing per month. The continue process is alive. Free disk was about 7.0 GB when the FNSPID scorer started writing. The GDELT result for 2020-04-27 is the item that has not moved. The TweetsKB download is not stuck. Event detection stays off.

## 2026-10-21 — Disk pause and the hung GDELT client

Free disk at the start of this fix was 5.80 GB. The FNSPID scorer was paused on `part_10272962234.parquet`, and the TweetsKB download was paused on `month_2018-11.n3.gz`. Both pause below 6 GB. Local snapshots, left in place: `com.apple.os.update-23740B032255078B456ED6B6F69EFEB341B76E2E3F81A901B0F80B3249D00827E3388663931DE6D84A1AF5506DA929E9`, `com.apple.os.update-5B92CE4BA1034457A0921532291F4A4AD939CBE48D3A1381163A9AD3687D5694`, and `com.apple.os.update-MSUPrepareUpdate`.

Deleted as regenerable: the uv package cache, pip caches, the Homebrew download cache, the torch hub checkpoints `big-lama.pt` and `resnet50-0676ba61.pth`, `data/interim/tweetskb_scratch`, the abandoned `data/interim/tweetskb_raw/month_2013-10.n3.gz`, the unused FinBERT and DistilBERT Hugging Face weight files, `__pycache__`, and `.DS_Store`. The RoBERTa download, `roberta_pretrain.pt`, the final scorer, hand labels, stored GDELT slices, reduced TweetsKB months, StockTwits and FNSPID extracts, and the scoring parts were kept. Free disk after that was 6.81 GB, and both paused jobs left their pause loops on their own. Fifteen minutes later free disk was 8.80 GB, after November's raw file was removed. The 12 GB target is not met. The next largest items were left for a decision: `series.sqlite` 1.3 GB, a rebuild of the Arm A series; the phase 1 stream indexes `social_for_alias.sqlite` 648 MB, `fnspid_stream.sqlite` 474 MB, and `stocktwits_stream.sqlite` 286 MB, each a rescan of an extract; `gdelt_allowlist` 427 MB, an earlier stored GDELT run that would have to be queried again; `tweetskb_full.sqlite` 395 MB, the reduced months; `gdelt_documents.jsonl.gz` 359 MB; `best.pt` 255 MB, the DistilBERT checkpoint, about half an hour to retrain; `news_category/data.json` 83 MB, a re-download; and the live December raw file. The `.venv` is in use by the running jobs.

The hung client was the GDELT loop and its `bq query` for job `sgnn2_frozen_20200427_1792535531`, which BigQuery had already marked DONE, billed 2,661,285,888 bytes. That client and the waiter bound to its old terminal were stopped. The FNSPID scorer and the TweetsKB process were not stopped, and neither was started a second time. The loop was restarted under `caffeinate` from the first slice without a file. It skipped the 45 stored slices, dry-ran 2020-04-27 at 3.58 GB, and fetched that finished job by id. The slice is stored: 644,753 rows. The loop is now on 2020-05-25. A slice has a 20 minute wall-clock limit, a heartbeat line, one attach retry on the same job id, and then a stop. The dry-run-first rule and the 10 GB per-slice stop stay. A new query stops if the projected total would pass 960 GB. The waiter now watches the new loop. When that loop exits 0 it runs `scripts/phase2_gdelt_reserve_after.py`, which rebuilds the series with the alias table, writes the precision audit, coverage, the proposed unfrozen planning SD, the usable-pair counts, and GO/NO-GO. It refuses to start unless 128 slice files are present. Its log will be `eval/results/phase2_gdelt_reserve_after.status`.

Fifteen minutes after the restart: 46 of 128 slices stored. 2020-04-27 took about 10 minutes to download, and 2020-05-25 was 230,000 rows into its fetch. At about 11 minutes a slice, the remaining 82 slices are about 15 hours. The FNSPID scorer's last finished part logged 11.47 pairs per second, which includes the pause; the part being written moved at about 22 pairs per second. TweetsKB reduced November (233,376 matched) and is downloading December 2018 at 1.43 MB/s. Event detection stays off.

## 2026-10-21 — GDELT loop stopped on expired login

The restarted loop stored through 2020-12-07, 54 of 128 slices. On 2021-01-04 the result download timed out, job `sgnn2_frozen_20210104_1792577922`. The attach retry could not refresh the gcloud token, so the slice failed twice and the loop stopped. The slice file was not written. The Arm B waiter sees the non-zero exit and does not run the rebuild. Login was not refreshed from here.

## 2026-10-21 — Sector match bucket, before any pair count under it

Information technology and communication services become one match bucket, `information_technology_and_communication_services`. GICS moved Alphabet from information technology to communication services in 2018, so a control drawn from only one of those lists changes the eligible set in the middle of the study window. The match uses the union of the two existing control lists. The lists, the ticker names, and every caliper stay as they are. No caliper is widened. The two GICS names remain on the sector map. This entry is the rule. The Arm A recount and the Arm B test counts come after it. The planning SD stays proposed and is not frozen.

Alias titles in the Arm B rebuild count only when the entity mid equals the mid on that alias row. A title-only match would count the fruit page "Apple". Titles on the frozen allow-list keep the plain title rule. The H4 overlap window is 2017-11-01 through 2020-12-31, the first usable TweetsKB month through the end of 2020. The full-span count stays. H1, H2 positive, H2 competitor, and H4 are four separate results. H1 needs 10 matched pairs in total. Each H2 class needs 10. H4 needs 5 events with a matched pair on the overlap window.

## 2026-10-21 — Sector match recount, after the rule above

The Arm A recount uses the same series and the same calipers. With the merge off, the strict counts are the previously recorded ones: news 37 / 10 positive / 27 competitor, social 271 / 36 / 235. With the merge on they are news 45 / 10 / 35 and social 417 / 42 / 375. Tesla is unchanged. The revised-rank social total moves from 285 to 428. The file is `eval/results/phase2_sector_merge_recount.json`. The earlier pool-restore file was not overwritten.

The Arm B script was run with `--test` on the 54 stored slices only. It wrote `data/interim/phase2/gdelt_reserve_series_test.sqlite` and `eval/results/phase2_gdelt_reserve_after_test.json`. It did not write the real series or the real result file. 31,282,897 documents, 184 seconds, no error. Four alias titles have a different mid on some rows: Apple 18,165, Dell_Technologies 10,262, HP_Inc. 6,969, Oracle 1,103. The other 25 accepted aliases have zero. Under the merged bucket the test lines are H1 GO 524, H2 positive GO 172, H2 competitor GO 352, and H4 GO 127 events on 2017-11-01 through 2020-12-31. The same scratch series with the merge off is H1 469, positive 168, competitor 301, and 125 overlap events. These are counts on an incomplete slice set. The planning SD on that run is null, status PROPOSED, and is not frozen. Event detection stays off.

## 2026-10-21 — Arm B planning SD uses neighbor targets

The Arm B planning SD stays proposed and is not frozen. The brand-versus-control placebo matched 0 of 60 dates, because the brand's popularity is outside the control caliper, so that SD was null. The treated series is now each positive node and each competitor node, with the brand excluded, on non-event dates of the brand. The draw is seed 3 and at most 20 dates per brand. A sector control has to pass the same calipers and the same two-hop path rule as a real pair. When more than one control passes, the match is the closest baseline mean. The value is the difference in absolute shift, and the sample SD uses divisor n-1. The Arm A pooled SD 0.10636804456181562 is unchanged. The recount on the stored slices comes after this entry.

## 2026-10-21 — Arm B placebo SD on the stored slices, and the GDELT login stop

The scratch series from the 54 stored slices gives 167 placebo pairs: Apple 98, Microsoft 62, Alphabet 7, each from 20 dates. The sample SD is 0.04335854695667384, divisor n-1. SESOI 0.05 is 1.1531751755879331 of that SD. The baseline-mean caliper 0.20 is 4.612700702351733 of that SD. Status PROPOSED, not frozen. These figures are on an incomplete slice set. The scratch database was removed after this count. The Arm A SD was not edited.

The new GDELT supervisor started at 2026-10-21T14:25:23Z and stopped on auth. The active account still cannot refresh its token. No new query was submitted. 2021-01-04 remains attached to job `sgnn2_frozen_20210104_1792577922`. Login was not refreshed from here.

## 2026-10-21 — Clean stop before a Mac restart

The FNSPID scorer was stopped after it committed `part_6072296668.parquet`. 198 parts are done, 713,810 pairs. The daily database quick check passed. The next part file, `part_6220135742.jsonl`, had been opened and was not committed, so it was removed. No half-written part file remains.

The TweetsKB download was stopped after it flushed the offset for `month_2019-08.n3.gz`. The contiguous offset is 134,217,728 bytes. The raw file is still on disk at its full preallocated size, 3,464,371,933 bytes. The offset is inside that file. Twenty-one months are reduced, through 2019-07. The reducer was not in a write.

GDELT was already stopped. 54 of 128 slices are stored. 2021-01-04 stays pinned to `sgnn2_frozen_20210104_1792577922`. The state is `eval/results/resume_state.json`. Resume is `scripts/resume_all.sh`. It was run with `--check` and started nothing. Login was not run.

## 2026-10-21 — Pause before closing the laptop

The FNSPID scorer had already finished. All 219 parts are committed, 796,942 pairs. The daily database quick check passed. No half-written part file was present.

TweetsKB was stopped after it flushed the offset for `month_2019-08.n3.gz`. The contiguous offset is 2,932,867,072 bytes. The raw file remains, preallocated to 3,464,371,933 bytes, and the offset is inside that file. Twenty-one months are reduced, through 2019-07. The reducer was not writing. The TweetsKB database quick check passed.

GDELT had already stopped. 57 of 128 slices are stored, through 2021-03-01. The 2021-03-29 fetch timed out and the status read then failed on TLS, so the slice file was not written. That job is DONE, id `sgnn2_frozen_20210329_1792600858`, billed 2,493,513,728 bytes, and it stays pinned so a restart attaches it and does not submit another query. Ledger bytes through the last stored slice are 586,372,087,808. Including the pinned job, billed bytes are 588,865,601,536, leaving 371,134,398,464 of the 960 GB cap. No GDELT process was running at the pause. The state is `eval/results/resume_state.json`. Nothing was restarted.

## 2026-10-22 — Resume, and Arm A counts with no event shift

Login for `srivatsa.singaraju2023@vitstudent.ac.in` was checked with `bq show` on job `sgnn2_frozen_20210329_1792600858`. The job is DONE. No query was run. `scripts/resume_all.sh` was checked, then started. Each job is in its own session.

The FNSPID scorer found 219 of 219 parts done and exited. It did not score new pairs. TweetsKB continued from `month_2019-08.n3.gz`, finished that file, reduced it, and is downloading `month_2019-09.n3.gz`. GDELT stayed at 57 stored slices. Its first three tries could not resolve `bigquery.googleapis.com`, so the supervisor stopped after three transient failures. The network answered a later metadata read, and the supervisor and waiter were started again, still attached to `sgnn2_frozen_20210329_1792600858`.

The Phase 4 analysis code is `scripts/phase4_analysis.py`. Its synthetic tests passed: a known effect, a known null, `(b+1)/(B+1)`, Holm on the eight tests, degree-preserving rewiring, clustered bootstrap, the H1 table, and the 10-pair rule. No study outcome was computed.

Arm A counts, with no event shift, are in `eval/results/phase4_arm_a_counts.json`. Events are `|z| >= 2` on each series. Pairs use the merged information-technology and communication-services bucket. News from the main scorer: positive 22, competitor 45. VADER news: positive 10, competitor 35. StockTwits user labels: positive 42, competitor 386. The proposed Arm A news planning SD on the main scorer is 0.25316969410935136, from 98 placebo pairs, seed 3, divisor n-1. Status PROPOSED, not frozen. SESOI 0.05 is 0.1974959924642621 of that SD. The 0.20 mean caliper is 0.7899839698570484 of that SD. The frozen Arm A SD 0.10636804456181562 is unchanged.

## 2026-10-22 — Headline re-score, and the network backoff

Nothing stopped, so `scripts/resume_all.sh` was not run again. GDELT had stored the pinned `2021-03-29` slice, job `sgnn2_frozen_20210329_1792600858`, 453,181 rows, billed 2,493,513,728 bytes. That bill was already in the pinned total. Ledger bytes are 588,865,601,536. Remaining under the 960 GB cap: 371,134,398,464. The next slice, 2021-04-26, was in fetch. Since the resume, GDELT had three `ServerNotFoundError` failures and then one `Remote end closed connection without response` on the pinned fetch. No auth error.

The supervisor file now waits 5, 10, 20, then 30 minutes, and stops only after 12 consecutive network failures. Auth, quota, the cap, a dry run above 10 GB, and an unexpected result shape still stop immediately. The running supervisor, pid 66084, still has the previous three-failure rule loaded. It was left running because it was fetching.

TweetsKB has 22 reduced months, through 2019-08, and is on `month_2019-09.n3.gz`. The saved contiguous offset was 0 after about 2.8 GB received. The leading 1,048,576 bytes were requested again and written on the first try, at 0.3240 MB/s. The file starts with a gzip header. The live offset then moved to 133,169,152 bytes, and the parallel speed was 0.7034 MB/s. A failed range at the contiguous edge is now put back at the front of the queue. The running downloader does not have that change.

FNSPID gold, the validation pass, and the final fit all use the node string and the labeled text at `max_length` 128. For FNSPID that text is the headline with whitespace collapsed. The stored scores used the headline, summary, and body joined, also at `max_length` 128. Of 796,942 scored pairs, 162,333 headlines name the node by its registered alias, or by the node string when it has no alias list. The share is 0.2036948736545445. The joined scores are kept. The headline-only re-score is pid 66981, writing `data/interim/phase3/fnspid_scores_headline`. At the last measured 22.95 pairs/s, 796,942 pairs take about 9.6 hours. The 14-ecosystem counts start when those parts are done. They are not computed yet. The frozen Arm A SD is unchanged.

## 2026-10-22 — Audit decision, fixed before any label

This entry is the decision. It is not to be edited after the labels come back. No label from this audit has been written. No macro-F1 and no linking precision are computed here.

The audit sample is 200 scored FNSPID pairs, drawn with seed 20261022, 100 whose headline names the node and 100 whose headline does not. Gold uses the same rule as the earlier sheets. Where both labels are present they must agree, and that label is used. Where only `label_A` is present, that label is used. Disagreements are excluded.

(a) After `not_about_brand` is dropped, each remaining row is scored with the saved final scorer and the same node string under two inputs. One input is the collapsed headline. The other is the headline, summary, and body joined and cut at `max_length` 128, which is the stored joined-text input. Macro-F1 is the unweighted mean of positive, negative, and neutral F1. Each input has a 95 percent percentile interval from 1,000 bootstrap resamples of those rows, using the same indexes as `phase3_gate.bootstrap`: draw `int(0.025 * 999)` and draw `int(0.975 * 999)`. The seeds are `20261022:headline` and `20261022:joined`. The input with the higher macro-F1 becomes the main news series. If the two intervals overlap, the main news series is the richer input, the joined headline, summary, and body. The other input remains a comparison. This choice does not change the frozen Arm A SD 0.10636804456181562.

(b) Linking precision is computed before `not_about_brand` is dropped. A gold row is a correct link when its label is positive, negative, or neutral. Each stratum has its own 95 percent Wilson interval, with z = 1.959964. The overall point estimate is `0.2037 * (precision on headline-named pairs) + 0.7963 * (precision on pairs whose headline does not name the node)`. If that point estimate is under 0.90, the Arm A news series is restricted to pairs whose headline or summary names the node, by name or by alias, and the Arm A counts are rebuilt on that restricted set.

## 2026-10-22 — Audit sheet and the job watchers

The decision above was written before `data/handlabel/sample3.csv` existed. That sheet now has 200 rows, HL2001 through HL2200, seed 20261022. One hundred headlines name the node and one hundred do not. None of the pairs are in `sample.csv` or `sample2.csv`. `text` is the document span inside the joined scorer's 128-token window. Annotator B's 40 ids are in `data/handlabel/INSTRUCTIONS.md`, 20 from each draw group. No score was written.

The GDELT fetch in progress was left running. A detached watcher, pid 68466, restarts the supervisor after the next `stored` line and before the following query, and pins a job id if one was submitted. The supervisor now running, pid 66084, still has the previous backoff until that boundary. TweetsKB is on `month_2019-10.n3.gz` under the process that started before the queue change. A detached watcher, pid 68467, reloads it after that month is reduced, which is the next month boundary. The watchdog, pid 68468, checks every 10 minutes. A transient or empty stop is restarted with `scripts/resume_all.sh --only`. Auth, quota, the cap, a dry run above 10 GB, or an unexpected result shape is written to `eval/results/NEEDS_ME.txt` and shown as a notification. No such stop has occurred.

When the headline re-score finishes, the counts waiter runs `scripts/phase4_arm_a_headline_counts.py`. That file now builds the 14-ecosystem counts and proposed planning SDs for headline-only news, the stored joined-text news, VADER, and the StockTwits user label. The main series is marked pending the audit decision. Those counts are not computed yet.

## 2026-10-22 — Freezing rule, before any outcome

This entry is the rule. No event shift is computed here. Nothing is frozen by this entry. Freezing waits for confirmation.

The standard deviation to be frozen, when confirmation is given, is three proposed values. One is the proposed SD of whichever news input wins the audit decision above, after any restriction that decision requires. One is the social SD after the StockTwits rebuild logged next. One is the VADER SD for the robustness series. Each freeze includes that SD, the SESOI of 0.05 divided by the SD, and the baseline-mean caliper of 0.20 divided by the SD. The frozen Arm A SD 0.10636804456181562 is not replaced by any of them.

## 2026-10-22 — Social and VADER series for the ten brands

The zero scored days were a build gap. `series.sqlite` already held the VADER headline cells and the StockTwits user-label cells under the tickers NKE, CMG, LOW, TMUS, MA, CVX, HSY, CL, LLY, and DE, because those tickers were written by the control pass. The counts look up the ecosystem name. The ticker cells and the name cells have the same scored-day counts after the copy. Exclude-brand cells for those ten ecosystems were copied from the full series and then reduced by documents that mention the brand, using the same alias and ticker rule as the original builder.

Samsung and Adidas had no ticker cells. Samsung news is the headline alias: 188 scored days, 279 scored headlines. Samsung social is the SSNLF cashtag in the retained feature table: 5,914 messages, 1,482 user labels, 978 scored days. Adidas has no ticker. Its series is the word-boundary alias: 104 scored VADER days and 171 scored StockTwits days. Neither name has a sitelink count in `popularity_sitelinks`, so the matcher drops both. Nike's competitor class stays at 0 pairs for that reason. Nike's social placebo draw is 20 dates and 0 pairs for the same reason.

The count file now records, for each source, ecosystem, and class, the number of events with at least one matched pair. A pair count can be larger when more than one target matches. The file is `eval/results/phase4_arm_a_counts_both.json`. No shift is stored. The main series is still pending the audit.

Social, after the rebuild, proposed SD 0.28373788888841645 from 179 placebo pairs, seed 3, divisor n-1. SESOI 0.05 is 0.17621897518122137 of that SD. The 0.20 mean caliper is 0.7048759007248855 of that SD. Status PROPOSED, not frozen. The previous social proposal, with the ten brands absent, was 0.29787244156886367 from 54 pairs. Brand events are 916. Events with a matched pair: positive 40, competitor 440. Pair counts: positive 42, competitor 571.

VADER, after the same rebuild, proposed SD 0.10118634897550949 from 211 placebo pairs. SESOI 0.05 is 0.4941378012571804 of that SD. The 0.20 mean caliper is 1.9765512050287215 of that SD. Status PROPOSED, not frozen. The previous VADER proposal was 0.09985000929014186 from 113 pairs. Brand events are 67. Events with a matched pair: positive 8, competitor 42. Pair counts: positive 10, competitor 51.

Alphabet's stored social placebo count was 0, from 1,960 eligible dates and a draw of 20. It was not an empty draw. The loader asked only for positive nodes that have a stored edge, so Android was omitted. Android has no stored positive edge. On those 20 dates the loaded neighbors, YouTube, Alphabet CEO, Meta, AMZN, SNAP, and PINS, had no control that passed every caliper at once. The mention-volume caliper failed for the controls that had both windows. YouTube has 245 sitelinks and PINS has 1, so those two also fail the popularity caliper. Alphabet CEO had no 14-day baseline on any of the 20 dates. The loader now keeps every positive node. Android then matches on 3 of the same dates, so the rebuilt social proposal shows 3 Alphabet placebo pairs. Those 3 are Android.

Headline and joined counts gained the same effective-event field. Their series were not rebuilt. Their proposed SDs were recomputed with Android loaded: headline 0.18479459317327387 from 179 pairs, joined 0.24085926020674753 from 184 pairs. Both stay PROPOSED. The audit still chooses the news input.

GDELT stopped on its own at 2026-10-22T08:06:56Z. The slice is 2024-12-02. The fetch returned HTTP 401, and the token refresh could not prompt. The job id is `sgnn2_frozen_20241202_1792655471`. It is pinned in `RESUME_JOB` so a later start attaches to that id. It was not restarted. Login was not run. TweetsKB and the watchdog were still running.

## 2026-10-23 — Arm A news event detection, before any outcome

The 0.70 threshold is unchanged. The 2026-10-22 audit entry is not edited. No event is detected in this entry.

If the audit shows that the chosen main news input reaches macro-F1 0.70 or more on the deployment audit, the retest is recorded as passed. Otherwise the 0.70 gate is recorded as not met, and event detection proceeds under the stopping rule logged on 2026-10-21 in "Enlarged attempt: gate not met": the gate number stays 0.70, the best-scorer series stays the main series, and VADER stays the robustness series. Every Arm A news result is reported next to the VADER series with that limitation stated.

## 2026-10-23 — Brand set, before any outcome

Arm A uses the 14 ecosystems, on news and on social wherever the data exist: Apple, Microsoft, Alphabet, Tesla, Chipotle, T-Mobile US, Lowe's, Mastercard, Chevron, Hershey, Colgate-Palmolive, Eli Lilly, Nike, and John Deere. Arm B uses the 13 of those ecosystems other than Tesla. No brand beyond these 14 is added. The arms stay separate. Each keeps its own Holm family of eight.

## 2026-10-23 — One shared positive matrix, before any outcome

One shared positive matrix stays as locked. Positive relations keep a single `W_pos`. Per-property matrices are not adopted.

## 2026-10-23 — Descriptive ablations, before any outcome

These are descriptive ablations, outside the Holm family: signed undirected, mean-of-neighbors, no-sign keeping direction, no-direction keeping sign, and signed without co-mention edges. Primary H3 is unchanged: signed versus unsigned, and signed versus no-graph.

## 2026-10-23 — Interpretability definitions, before any outcome

The definitions in `reports/phase5_plan.md` are adopted now. Channel contribution is the mean absolute contribution of the channel on test events. Per-neighbor attribution is the change when that message is replaced by the zero vector, with no retuning. Both are reported after the test fold is scored.

## 2026-10-23 — Sitelinks, Arm B scratch counts, and the synthetic Phase 5 check

Login was checked with `bq show` on `sgnn2_frozen_20241202_1792655471` before the resume. The job was already DONE. The supervisor and the waiter were started once each, detached, under caffeinate. The 2024-12-02 slice was fetched from that job id. The ledger has one executed row for it, billed 4,416,602,112 bytes. No second query was submitted for that slice.

Wikidata sitelinks were read on 2026-10-23 from `wbgetentities` for the two study-graph nodes missing a count. Samsung Electronics, Q20718, has 60. Adidas, Q3895, has 107. No other node in the study graph was missing a count. Both integers are in `popularity_sitelinks`, and the retrieval dates are in `popularity_sitelinks_retrieved`. Calipers were not changed. The Apple-Samsung and Nike-Adidas recount is counts only, in `eval/results/phase4_sitelink_recount.json`. Headline and joined score parts have no Samsung or Adidas cells. On VADER and on social, no Apple event and no Nike event had both a 14-day baseline and both shift windows on the excluded series, so those target pair counts stay 0.

`scripts/phase2_gdelt_reserve_after.py` now covers the 13 non-Tesla ecosystems and streams the exclusion cells. A run without `--test` was refused at 106 slices. The `--test` run used the stored slices, wrote only the scratch database and `eval/results/phase2_gdelt_reserve_after_test.json`, and did not compute a planning SD. Peak memory was 190,431,232 bytes. There was no error.

TweetsKB had already reduced all 38 months, `month_2017-11.n3.gz` through `month_2020-12.n3.gz`. The Arm B counts for those 13 ecosystems were then run. They are counts only, in `eval/results/phase2_tweetskb_arm_b_counts.json`. No shift was computed.

Phase 5 training, the chronological split, the six leakage checks, the attributions, and the ablation variants are in `scripts/phase5_model.py`. `scripts/test_phase5_model.py` passed on synthetic events: a planted signal and a null. No study label was read. Real training was not started.

## 2026-10-23 — Packaging, methods draft, and limitations draft

No collection job was started or stopped. No study label, shift, or outcome was read for this entry.

`requirements-lock.txt` is the package list from the virtual environment on this date, Python 3.14.6. `requirements.txt` stays the 2026-10-11 Phase 0 plan. `README.md` has the folder map, the `scripts/resume_all.sh` order, what each script reads and writes, the source licenses, and the seeds. `scripts/check_frozen_sha256.py` checks the hashes recorded in the log, listed in `configs/frozen_sha256.json`. It does not rewrite a file. On this run, `configs/phase0.json` matches the 2026-10-13 hash, `data/interim/phase3/final_scorer/model.pt` matches the 2026-10-21 hash, and all 128 allow-list files match `eval/results/gdelt_allowlist_sha256.txt`, whose own hash and size sum also match. `configs/sector_taxonomy.json` and `configs/phase1_universe.json` do not match the hashes recorded on 2026-10-11. Those two recorded hashes were not replaced.

`.gitignore` already drops `data/raw/`, `data/interim/`, `data/processed/`, `data/handlabel/`, and `*.pt`. Credential filename patterns were added. The tree is not a git repository. A shared copy under those rules is 222 files. It does not include the raw corpora, the hand-label sheets, the weights, or a credential file.

`reports/methods_draft.md` is taken from this log and `reports/pre_registration.md`. Unfinished numbers are `[RESULT]`. There are 17 open placeholders. `reports/limitations_draft.md` states the limits already logged: the 20.4 percent headline-name share, the StockTwits user label, TweetsKB resting mainly on Apple and Microsoft, the Arm A positive class concentrated in a few ecosystems, the unmet 0.70 gate and the waiver rule, and HuffPost and FIRE not being arms.

## 2026-10-23 — Deployment audit of sample3

The 2026-10-22 audit entry is not edited. The saved final scorer was applied to the filled sheet. It was not trained on this sheet. The watchdog, pid 68468, was left running. The GDELT supervisor had already exited 0 with 128 slice files, and the reserve rebuild had already exited 0, so neither was started again.

`data/handlabel/sample3.csv` has one leading line, `sample3 (1)`, before the header. That line is not a row. Under it, the 200 ids are HL2001 through HL2200 in order. Every `label_A` and every filled `label_B` is one of positive, negative, neutral, or not_about_brand. `label_B` is filled on the 40 ids listed in `data/handlabel/INSTRUCTIONS.md` and blank on the rest. The regenerated draw, seed 20261022, matches those ids, nodes, headlines, and joined 128-token texts. No headline or text was changed.

Cohen's kappa on the 40 double-coded rows is 0.7306397306397306. Observed agreement is 0.80. Eight rows disagree and are out of scoring and out of linking precision: HL2006, HL2013, HL2038, HL2043, HL2054, HL2112, HL2182, and HL2186. They are in `data/handlabel/disagreements3.csv`, with adjudication blank. Resolved labels, disagreements excluded, are: headline names the node, 25 positive, 16 negative, 55 neutral, 2 not_about_brand (98 rows); headline does not name the node, 18 positive, 6 negative, 10 neutral, 60 not_about_brand (94 rows). Sixty-two resolved `not_about_brand` rows are dropped from the scorer comparison. One hundred thirty rows are scored.

Macro-F1 uses 1,000 bootstrap draws and the same percentile indexes as `phase3_gate.bootstrap`. The overall seeds are `20261022:headline` and `20261022:joined`. Draw-group intervals add `:named` or `:other` to that seed. VADER on the collapsed headline uses `20261022:vader` the same way. It is not one of the two decision seeds.

Collapsed headline, n=130: macro-F1 0.6417041235098692, interval 0.5340547349135463 to 0.7336324786324786. Named, n=96: 0.6482739723681451, interval 0.5128768372975147 to 0.7460992907801419. Other, n=34: 0.5819304152637486, interval 0.3703703703703704 to 0.7628205128205128. Confusion, rows gold and columns positive, negative, neutral: positive 28, 0, 15; negative 0, 10, 12; neutral 15, 2, 48.

Joined text, n=130: macro-F1 0.5609295570079884, interval 0.4717703349282297 to 0.641900560610238. Named, n=96: 0.5797068428647376, interval 0.47535353535353536 to 0.6740821434359076. Other, n=34: 0.48954545454545456, interval 0.296415770609319 to 0.6647812971342383. Confusion: positive 32, 4, 7; negative 2, 15, 5; neutral 31, 9, 25.

VADER headline, n=130: macro-F1 0.47918162918162927, interval 0.3983082052047569 to 0.562847790507365. Named, n=96: 0.4665984654731458, interval 0.357839947950553 to 0.558820529718195. Other, n=34: 0.4619047619047619, interval 0.28443551333576905 to 0.6204767986377182. Confusion: positive 22, 6, 15; negative 3, 4, 15; neutral 12, 5, 48.

Linking precision, before dropping `not_about_brand`, on the 192 resolved rows. A correct link is positive, negative, or neutral. Headline-named: 96/98 = 0.9795918367346939, Wilson interval 0.9286178883365213 to 0.9943853858954805. Headline does not name the node: 34/94 = 0.3617021276595745, Wilson interval 0.2717691858120199 to 0.46249479290129913. Weighted overall: 0.2037 times the first plus 0.7963 times the second = 0.4875662613981763.

The two overall intervals overlap, so the main news series is the joined text. The collapsed headline stays a comparison. The joined macro-F1 is under 0.70, so the retest is not passed. The 0.70 gate stays unmet and the 2026-10-21 waiver applies: this series stays the main series, VADER stays the robustness series, and every Arm A news result is reported next to VADER. The weighted linking precision is under 0.90, so Arm A news is restricted to pairs whose headline or summary names the node, by name or by alias. The frozen Arm A SD 0.10636804456181562 is unchanged.

The counts waiter was not already running. It was started once, found the headline parts complete, and ran `scripts/phase4_arm_a_headline_counts.py` on that restricted basis. It exited 0. Social is not restricted. The rebuilt joined counts, events then positive pairs, positive events with a pair, competitor pairs, and competitor events with a pair: Apple 13, 1, 1, 2, 2; Microsoft 14, 1, 1, 16, 10; Alphabet 17, 0, 0, 8, 8; Tesla 14, 10, 8, 18, 10; Chipotle 4, 0, 0, 0, 0; T-Mobile US 2, 0, 0, 2, 2; Lowe's 1, 0, 0, 0, 0; Mastercard 0, 0, 0, 0, 0; Chevron 16, 0, 0, 4, 4; Hershey 0, 0, 0, 0, 0; Colgate-Palmolive 1, 0, 0, 0, 0; Eli Lilly 1, 0, 0, 0, 0; Nike 12, 0, 0, 0, 0; John Deere 0, 0, 0, 0, 0.

The proposed planning SD for the restricted joined series is 0.2694611493987299, from 111 placebo pairs. Status PROPOSED. It is not frozen. SESOI 0.05 in SD units is 0.18555550628195933. The 0.20 mean caliper in SD units is 0.7422220251278373. Confirmation is still required before either number is frozen. The restricted VADER series had no matched placebo pair, so no VADER planning SD was formed.

`configs/frozen_sha256.json` keeps the 2026-10-11 hashes. The current `configs/sector_taxonomy.json` hash c755e023e8143202b06bd25b4898ac537a21c87a387aea5bb992163a8f06ec7a is the 2026-10-21 sector-merge amendment. The current `configs/phase1_universe.json` hash 175f3438dc03c947bf5e19566023ad653e005322657388275e291c47ac2ba670 is the 2026-10-23 sitelinks amendment. `scripts/check_frozen_sha256.py` checks the latest amendment where one exists and exited 0.

## 2026-10-23 — Source planning SDs frozen

Confirmed. No study outcome, shift, or test was computed for this entry. The watchdog was left running. The Arm A pooled SD 0.10636804456181562 stays as recorded in `power_gate.planning_sd_paired_abs_shift`.

The restricted joined news planning SD is frozen at 0.2694611493987299, from 111 placebo pairs. SESOI 0.05/SD is 0.18555550628195933. The mean caliper 0.20/SD is 0.7422220251278373.

The social planning SD in the rebuilt series, which was not restricted, is 0.28373788888841645 from 179 placebo pairs. That is the logged 0.2837 value. It is frozen. SESOI 0.05/SD is 0.17621897518122137. The mean caliper 0.20/SD is 0.7048759007248855.

Both are amendment `A2026-10-23-source-sds` in `configs/phase0.json` and `configs/phase4_series.json`. The 2026-10-13 hash of `configs/phase0.json` stays in `configs/frozen_sha256.json`. The current hash fd7423465be74bc709a4d679b4e6044583b5e7fc4cec9dc94608edcbc0d33af3 is the 2026-10-23 amendment. `configs/phase4_series.json` is recorded at b668aa6be195399735525793f988bb9cc2de1051d976848e1cf8ff0bb0c86e48.

On the restricted joined series the 10-pair rule has 12 positive pairs and 10 events with a positive pair. Tesla contributes 10 of the 12 pairs and 8 of the 10 events. Competitor pairs are 50, and events with a competitor pair are 36. Tesla contributes 18 of the 50 pairs and 10 of the 36 events.

## 2026-10-23 — Arm A news robustness series, before any outcome

This entry is the decision. No outcome is computed in it.

The robustness series for Arm A news is the headline-only RoBERTa scorer, the same final weights, applied to the same restricted pairs as the joined main series. VADER on those restricted pairs had no matched placebo pair. It is reported as no testable pair and is not used.

## 2026-10-23 — Headline restricted planning SD, proposed

No new shift was run. The restricted headline series already stored in `eval/results/phase4_arm_a_counts_both.json` has 117 placebo pairs. The proposed planning SD is 0.1998431191809846. SESOI 0.05/SD is 0.250196254966969. The mean caliper 0.20/SD is 1.000785019867876. Status PROPOSED. It is not frozen.

## 2026-10-23 — GDELT after-script already stored

Nothing was restarted. All 128 slice files are stored. `scripts/phase2_gdelt_reserve_after.py` has already run without `--test` and wrote `eval/results/phase2_gdelt_reserve_after.json`. The pre-rerun series file was left in place. The alias series rebuild used 70,784,125 documents. Five alias titles point at a different mid, 171,517 rows: Apple 45,849, DELL 59,623, HPQ 63,596, Meta 14, and ORCL 2,435. Across 254 precision nodes the page check is 112,656,093 right, 984,642 empty-url mids, and 2,823,615 wrong pages via the mid. Each of the 13 ecosystems has scored days from 2,221 to 3,482. The proposed planning SD is 0.049974534401688475 from 331 placebo pairs. SESOI 0.05/SD is 1.0005095714970917. The mean caliper 0.20/SD is 4.002038285988367. Status PROPOSED, not frozen. Usable pairs on the full span are 2,430 matched, of which 459 are positive and 1,971 are competitor. On the overlap window, 427 events have a matched pair. The four results are H1 GO at 2,430, H2 positive GO at 459, H2 competitor GO at 1,971, and H4 GO at 427.

## 2026-10-23 — Headline, GDELT, and TweetsKB planning SDs frozen

Confirmed. No BigQuery call was made. No study outcome was computed in this entry. The Arm A pooled SD 0.10636804456181562 stays as recorded.

The restricted headline-only robustness SD is frozen at 0.1998431191809846, from 117 placebo pairs. SESOI 0.05/SD is 0.250196254966969. The mean caliper 0.20/SD is 1.000785019867876.

The Arm B GDELT planning SD is frozen at 0.049974534401688475, from 331 placebo pairs. SESOI 0.05/SD is 1.0005095714970917. The mean caliper 0.20/SD is 4.002038285988367.

The TweetsKB Arm B planning SD uses the same neighbor-target placebo design as the GDELT after-script: seed 3, at most 20 dates, divisor n−1. It has 202 placebo pairs, which is at least 100, so it is frozen at 0.05893766062620146. SESOI 0.05/SD is 0.8483539975757349. The mean caliper 0.20/SD is 3.3934159903029397.

These three are amendment `A2026-10-23-robustness-and-arm-b-sds` in `configs/phase0.json` and `configs/phase4_series.json`. The earlier hashes stay in `configs/frozen_sha256.json`. The current `phase0.json` hash is 213c5439f987a9b2d629b7fad575a2a692f45a0bacdadcbef461ac43d0fac6d7. The current `phase4_series.json` hash is 5788dcb470c75114ac0f6ebdda200c423a6b5d609800fe2744d0723340100173. `scripts/check_frozen_sha256.py` exited 0.

## 2026-10-23 — Phase 4 outcomes

`scripts/phase4_analysis.py` ran once and exited 0. The checklist was printed first and every item was true. No BigQuery call was made. No Phase 5 training was started. No rule, window, series, or planning SD was changed after the numbers were produced.

The tables are in `reports/phase4_outcomes.md`. The raw output is `eval/results/phase4_outcomes.json`. There is no git repository. Seeds are bootstrap 0, pair permutation 1, rewiring 2, and placebo dates 3, with 200 inner permutations restarted at seed 1. GNN seeds 0–4 were not used. File hashes in the output are `phase0.json` 213c5439f987a9b2d629b7fad575a2a692f45a0bacdadcbef461ac43d0fac6d7, `phase4_series.json` 5788dcb470c75114ac0f6ebdda200c423a6b5d609800fe2744d0723340100173, `frozen_sha256.json` af877bc55c08e93f553de848c3ad4622420364d4e03432b9c2c0fecd396ee7ab, `phase4_analysis.py` 1ac1d7d566436dedb85a963bfef8ca4b6480bd6b33604fa279161fb7aa9aac99, `phase4_outcome_run.py` 98b0b46076c5dfde4529c854b6dfb49a04d150ccc32792500a728f6363cc7104, and `model.pt` 41d769b3d5a292de5f41c2908ae44020cb9570d223b7523edca9a226cd692559.

H3 was not estimated. Each arm's Holm family size is 6. The H1 label on joined news and on GDELT is method failed. Classes below 10 pairs were not tested: headline H2 positive has 8 pairs, the Tesla-excluded joined H2 positive class has 2 pairs, and the Tesla-excluded social H2 positive class has 5 pairs. Placebo dates were unavailable for Lowe's, Mastercard, and Hershey on both Arm A news series.

## 2026-10-24 — Faculty demo package

No confirmatory result, rule, planning SD, or caliper was changed. No BigQuery call was made. Real Phase 5 training was not started. The demo fit is CPU only, four threads, hidden size 32, depth 1, dropout 0, at most 6 epochs, patience 3, seeds 0–19. It is not the confirmatory grid.

Synthetic and augmented outputs are for demonstration only and are not evidence about real propagation. The choice between Option A and Option B is pending with the team and the guide.

Option A is the page that was produced. Option B's builder runs only with `--confirm-augmented`. `demo/test_real_files_byte_identical.py` ran that builder once and printed PASS. Nine study files were byte-identical after the run, including `eval/results/phase4_outcomes.json`, `reports/phase4_outcomes.md`, and `configs/phase0.json`. The builder printed synthetic share 0.250000. On that augmented file the real-only mean label is -0.0169881928796618 (14 labeled rows), the synthetic-only mean label is -0.0011356423180906364 (5 rows), and the combined mean label is -0.012816469047669388 (19 labeled rows).

The generator wrote 594,400 SYNTHETIC rows. Noise SDs are the frozen Arm A social value 0.28373788888841645 and the frozen Arm B GDELT value 0.049974534401688475. Lambda is 0, 0.25, 0.5, 1.0, and 2.0 times that SD. A gap is test MAE minus the no-graph test MAE. A lambda is detected when the mean of (no-graph event MAE minus signed event MAE) across the 20 seeds is positive and the sign-flip p-value is below 0.05. The false-positive rate is the fraction of seeds meeting that rule at lambda 0.

Arm A social: smallest detected lambda 0.25. False-positive rate at lambda 0 is 0.0. Signed test MAE and gap to no-graph: lambda 0, 0.226535, gap 0.004766; lambda 0.25, 0.226694, gap -0.004584; lambda 0.5, 0.226771, gap -0.026571; lambda 1, 0.226993, gap -0.102181; lambda 2, 0.227464, gap -0.343362.

Arm B GDELT: smallest detected lambda 0.5. False-positive rate at lambda 0 is 0.05. Signed test MAE and gap to no-graph: lambda 0, 0.042561, gap 0.002325; lambda 0.25, 0.042562, gap 0.000809; lambda 0.5, 0.042557, gap -0.003261; lambda 1, 0.042627, gap -0.017266; lambda 2, 0.042797, gap -0.059693.

The full model-by-lambda table is `demo/synthetic/SYNTHETIC_recovery_table.json`. The files are `demo/README.md`, `demo/real/REAL_GRAPH_overview.png`, `demo/real/REAL_GRAPH_apple_microsoft.png`, `demo/real/REAL_GRAPH.html`, `demo/real/REAL_GRAPH_layout.json`, `demo/synthetic/SYNTHETIC_events.parquet`, `demo/synthetic/SYNTHETIC_generator_meta.json`, `demo/synthetic/SYNTHETIC_recovery_table.json`, `demo/synthetic/SYNTHETIC_recovery_partial.jsonl`, `demo/option_a/REAL_and_SYNTHETIC_summary.html`, `demo/augmented/AUGMENTED_CONTAINS_SYNTHETIC_DATA_lambda1p0_share0p25.parquet`, `demo/augmented/AUGMENTED_CONTAINS_SYNTHETIC_DATA_lambda1p0_share0p25.png`, and `demo/augmented/AUGMENTED_CONTAINS_SYNTHETIC_DATA_lambda1p0_share0p25_subsets.json`.

## 2026-10-24 — Balance diagnosis, Phase 5, Phase 6, demo, and packaging

No hypothesis, rule, frozen SD, caliper, series, or success criterion was changed. Confirmatory Phase 4 files were not rewritten. No BigQuery call was made. The watchdog was left running. Training was CPU only, four threads.

Step 1. Matched pairs were not stored in `eval/results/phase4_outcomes.json`, so they were rebuilt with the unchanged matcher. That rebuild is not a new confirmatory test. Independent SMDs agree with the stored SMDs on all five sources. `valid=False` is `balance` line 470: any absolute SMD above 0.20. H1 "method failed" is `h1_decision` line 84, reached because balance is invalid. Placebo was valid on every source. The failing covariates are log mention and log popularity for both news series, log popularity for social and GDELT, and baseline mean plus log popularity for TweetsKB. Mention and popularity gaps are absolute differences of the baseline log1p mention covariate and of log1p(sitelinks). Percentiles use position p*(n−1). Event size is the brand's event-bin scored count. The named-in-text split is computed only for the restricted news series. Social, GDELT, and TweetsKB day cells have no document text, so that split is not available. The exploratory calipers ln 1.5 were set only inside the diagnosis process and then restored. `phase0.json` was not edited. Every tight-caliper and split row is exploratory and outside the Holm family. A class under 10 pairs was not tested. The report is `reports/phase4_balance_diagnosis.md`. The numbers are `eval/results/phase4_balance_exploratory.json`. A first markdown writer put the H2 rewiring p-value in the wrong column and, because that column was already filled, wrote nothing on the tested rows. The stored JSON p-values were then copied into the rewiring column. No effect was changed.

Step 2. Preconditions held: no collection job, free disk about 35 GB, the 8 synthetic tests passed, and `scripts/check_frozen_sha256.py` exited 0. The six leakage checks passed on all four sources before any test metric was used. Ecosystems are the frozen Arm A 14 and Arm B 13. The four sources were not pooled. Neighbor labels use the series with the brand excluded. Bin mentions are cell[2]. The baseline triple is `phase1_gates.baseline`. Node order is sorted names. Product and manufacturer map to product. owned_by maps to other. A CEO node is CEO only inside `configs/ceo_tenures.json`. Parent is in the one-hot and unused. Co-mention exists for Arm A news and social only. Joined and headline both use the news rows. Arm B has no co-mention table. Same-day events stay in one fold, with cuts near 60/20/20. The grid was selected by mean validation MAE across seeds 0–4. Ties take the smaller hidden size, then depth, then dropout. Rejected configs were not tested. Sign-shuffled, degree-matched, and linear diffusion use the selected signed hyperparameters. Linear diffusion is one training-fold coefficient on edge sign times shock z, feature index 31. Degree-matched rewiring is inside each ecosystem. Sign shuffle permutes structural signs once per ecosystem per seed. Event MAE is averaged across seeds, then one paired permutation (seed 1, 1000) and one clustered bootstrap (seed 0, 1000). The Holm family of 8 is per arm. Arm A inserts the joined-news H3 p-values. Arm B inserts the GDELT H3 p-values. Social and TweetsKB are reported and are not a second family. The recomputed Holm values are marked final in `eval/results/phase5_outcomes.json` and `reports/phase5_outcomes.md`. H3 is not supported on either primary source. Leave-one-ecosystem-out uses seed 0 and the selected signed hyperparameters and is not a Holm test.

Step 3. Phase 6 uses the validation-chosen signed model. Channel ablations keep one edge kind at prediction time and do not refit. Depth 1 and depth 2 use the chosen hidden size and dropout, seeds 0–4. The attribution example is the earliest test event with a label. A neighbor score is the mean absolute change in the labeled predictions when that neighbor's messages are replaced by the zero vector. The five largest scores are reported. Seed stability is seeds 0–9. Seeds 5–9 do not reselect. Sign-shuffled and degree-matched intervals are the Phase 5 secondary fits. The tables are `reports/phase6_evaluation.md`.

Step 4. `demo/DISCLOSURE.md` was written. A Synthetic augmentation section was added to `reports/methods_draft.md` and `reports/limitations_draft.md`. The augmented table was rebuilt from the Phase 5 label table at synthetic share 0.25 and lambda 1.0. Real-only mean label −0.0019613872003542603 on 7095 rows. Combined mean label −0.001531190070747276 on 9460 rows. The builder casts synthetic `t0` to text so the parquet columns share one type. That is a write fix, not a change of a label. The sign-specificity simulation uses the demo fit, not the Phase 5 grid: hidden 32, depth 1, dropout 0, at most 6 epochs, patience 3, seeds 0–9, 2 positive neighbors and 6 competitor neighbors. Opposite-sign signed MAE 0.23273094655819312, unsigned 0.29962429451503086. Same-sign signed MAE 0.23225096631172124, unsigned 0.23471831663406634. The simulation supports only that planted comparison. `demo/explorer.py` was checked in the browser on all three modes. Every displayed number carried its mode label. `demo/test_explorer_labels.py` printed `explorer labels pass`. The explorer's synthetic plant uses the frozen restricted joined-news SD because that panel is the joined-news view. Streamlit 1.66.1 was installed for the explorer. The server home was `demo/.runtime`, inside `demo/`.

Step 5. `[RESULT]` placeholders in `reports/methods_draft.md` were filled from stored files. Arm A VADER, Phase 5 RMSE, and Phase 5 sign accuracy remain `[RESULT]` because no stored file contains them. `requirements-lock.txt` was regenerated. `README.md` was updated. `scripts/check_frozen_sha256.py` exited 0. `demo/test_real_files_byte_identical.py` printed PASS, 9 files, synthetic share 0.250000. `reports/FINAL_SUMMARY.md` is the one-page guide.

Step 6. This entry is the log for 2026-10-24. No further analysis was started after it.

## 2026-10-24 — Placeholders, augmented fit, and the site

No hypothesis, rule, frozen SD, caliper, series, or success criterion was changed. The real-only Phase 5 files were not overwritten. No BigQuery call was made. The watchdog was left running. CPU only, four threads.

Step A. Signed test RMSE and sign accuracy were read by a forward pass of the stored weights in `eval/results/phase5_models` on the stored test events. The recomputed test MAE matches the stored test MAE on all four sources, so the weights were not refit. Linear diffusion uses the stored training-fold coefficient. Unsigned, no-graph, sign-shuffled, and degree-matched prediction outputs and weights were not stored, so those cells stay empty. The numbers are in `reports/phase5_outcomes.md`. Arm A VADER is recorded as: no testable pair: the restricted VADER series had no matched placebo pair. The Holm column in `reports/phase4_outcomes.md` now holds the final family-of-8 values. The earlier family-of-6 values are in a superseded column. Effects, intervals, raw p-values, pair counts, and decisions were not changed. `eval/results/phase4_outcomes.json` was not changed. `demo/explorer.py` remains in `demo/` with the header note "superseded by site/" and was not used again.

Step B. One signed fit, fixed before any test metric. The source is the stored restricted joined-news events. Synthetic share is 0.5 of the combined event count: 95 real events and 95 synthetic events. Lambda is 1.0. Noise is normal with the frozen joined-news SD 0.2694611493987299. A positive structural arc plants +1, a competitor arc plants −1, and co-mention is not a label. Shock sign is +1 when feature index 31 on the brand is at least 0, otherwise −1. The split is the day-boundary 60/20/20 rule: 114 train, 38 validation, 38 test. Leakage passed before training. The grid was selected on mean validation MAE across seeds 0–4. The chosen model is hidden 32, depth 2, dropout 0.2, mean validation MAE 0.259729. It was then scored once on the augmented test fold and once on the real events inside that fold. Labeled events are 35 and 16. Augmented test MAE 0.259116, RMSE 0.301459, sign accuracy 0.642986. Real-only test MAE 0.29208, RMSE 0.330955, sign accuracy 0.57. Per-edge-class estimates: positive 0.03178, negative 0.0413093, co-mention 0.0320373. The files are `eval/results/phase5_augmented.json` and `reports/phase5_augmented.md`. The same paragraph was added to `reports/methods_draft.md`, `reports/limitations_draft.md`, and `reports/FINAL_SUMMARY.md`.

Step C. The site is `site/app.py`. It reads only files inside `site/`. The graph and the augmented estimates are baked into `site/assets/graph.json`. No raw text and no study labels are shipped. `site/test_app.py` printed `site tests passed`: the app starts under Streamlit AppTest, a negative shock reverses the sign on a positive edge, and a competitor responds in the opposite direction. A browser check of a negative Apple shock showed Apple and iPhone red and DELL green. Screenshots are `site/screens/desktop.png` and `site/screens/phone.png`.

Step D. `reports/FINAL_SUMMARY.md` now has the augmented paragraph, the final Phase 4 and Phase 5 tables, and the augmented-run table. `scripts/check_frozen_sha256.py` exited 0 with mismatches 0. `demo/test_real_files_byte_identical.py` printed PASS, 9 files, synthetic share 0.250000. This entry was appended after that test. No further analysis was started.

## 2026-10-24 — Site color, islands, and the two-hop check

No hypothesis, rule, frozen SD, caliper, series, success criterion, study result, model file, or frozen value was changed. `site/assets/graph.json` was not rebuilt. No BigQuery call was made. The watchdog was left running.

Model S, Model 3, and Tesla CEO turned red during a negative Apple shock because the page painted the stored baseline shift on every node the shock did not reach. Those three shifts are the most negative in the baked graph: Model 3 −0.3228657580912113, Model S −0.25240734666585923, Tesla CEO −0.3656761057674885. A structural walk from Apple reaches only Apple CEO, iPhone, MacBook, DELL, HPQ, LOGI, and Samsung, each by one edge. There is no structural path from Apple to Model S, Model 3, Tesla, or Tesla CEO. Their edges are with Tesla. The old single layout also drew the Tesla nodes beside Apple, so the baseline red looked like a path. The graph was left as it is. Color now stops at two structural hops, and a node the shock does not reach stays dim. The strongest reached neighbor is fully saturated. Edges on a path that changes a color use the accent.

`site/test_app.py` prints the structural path for every node whose color changes. From Apple the paths are Apple to Apple CEO, DELL, HPQ, LOGI, MacBook, Samsung, and iPhone. The same listing for Tesla is Tesla to F, GM, Model 3, Model S, NIO, TM, and Tesla CEO. A chain of three positive edges colors the first and second hop and leaves the third hop unchanged. On the shipped graph every non-zero response is within two hops, and a negative Apple shock leaves Model S, Model 3, and Tesla CEO at zero. The one-line summary for that shock is "Negative news at Apple: Apple CEO, MacBook and iPhone fall; DELL, HPQ, LOGI and Samsung rise". The test printed `site tests passed`.

The fourteen ecosystems are separate islands on a fixed grid. The footer is the existing sentence, 11 px, #6b7280, centered. Screenshots are `site/screens/desktop.png`, `site/screens/phone.png`, and `site/screens/tesla.png`. No further analysis was started.

## 2026-10-24 — Wave 2 planning

No data were pulled. No result, rule, planning SD, or caliper was changed. `configs/phase0.json` was not edited. The confirmatory files were not opened for this choice. The watchdog was left running.

The selection rules were written in `reports/wave2_selection_criteria.md` before any candidate was counted. A candidate needed at least 6 structural neighbors with a sitelink count of at least 1, at least 14 FNSPID days, and at least one control more than 2 structural hops away inside the frozen popularity caliper 1.098612. StockTwits was used when the stored file had the ticker. The sector order fills the thinnest of the 11 buckets first. News events, where the stored `news` series exists, use the frozen daily detector and break ties only.

Sixteen tickers passed, in order: DD, SPG, BLK, JNJ, COP, BA, DOW, ACN, DIS, KO, BAC, GILD, PSX, GD, EA, WMT. SPG is held. Its chosen item is Q21096327, Springer Nature, which is not the real-estate company in the control pool. The seat was not given to another ticker. The other fifteen stand. No utilities ticker passed. Forty-five tickers were eligible and 156 were considered. The rows are `reports/wave2_candidates.json`.

The draft amendment is `reports/wave2_preregistration_draft.md`. It is not frozen. Scorer v2 marks the brand mention, scores sentences that name the node, keeps a finance-pretrained model as one candidate, and scores non-brand nodes only inside event windows. The fresh label set is 150 sentences drawn with seed 20261024. The macro-F1 gate remains 0.70, and the Wave 1 waiver is not extended. Phase 4 uses the existing control lists and the same calipers. Phase 5 v2, still unfrozen, weights the Huber loss by document count, drops a neighbor label below 5 documents, and adds baseline sentiment, log mention volume, and sector. The success criteria are unchanged. Wave 2 is the only new confirmatory test. Wave 1 stays as reported.

A dry-run on sgnn-csp-2 was refused because no account is active. Login was not run. The stored dry-runs of the same query cover 126 of 128 slices. The total is 455,695,789,596 bytes. The largest slice is 5,822,116,351 bytes. One account is enough under the 960 GB cap. The two stub slices and the per-slice bytes are `reports/wave2_gdelt_cost.json`. No further analysis was started.

## 2026-10-24 — Wave 2 freeze, SPG correction, and the label sheet

No Wave 1 result, rule, planning SD, or caliper was changed. No BigQuery call was made. No login was run. The watchdog was left running. The dated snapshot `kg/snapshots/wikidata_2026-10-12/tickers.json` was not rewritten.

SPG. The snapshot's highest-sitelink item is Q21096327, Springer Nature, with a normal-rank Frankfurt Stock Exchange statement whose P249 qualifier is SPG. The real-estate company is Q2287759, Simon Property Group, with a normal-rank New York Stock Exchange (Q13677) statement whose P249 qualifier is SPG, and 7 sitelinks. The written gates were run again on Q2287759 and were not relaxed. Structural neighbors with a sitelink count of at least 1: 111. FNSPID days: 1,090. StockTwits: not stored. Eligible controls: 13. Stored news events: 0. It passes and is added. Wave 2 is 16 ecosystems. With Wave 1, that is 30.

The other 15 chosen items each have a non-deprecated stock-exchange statement whose P249 qualifier is the ticker. DD's preferred New York Stock Exchange qualifier is DD. GILD, EA, and WMT match on Nasdaq. WMT's English label was empty; the description is the U.S. discount retailer and the Nasdaq qualifier is WMT. DOW does not match Dow Inc. The chosen item remains Q855639, Dow Chemical Company, which has a normal-rank New York Stock Exchange qualifier DOW and 36 sitelinks. Dow Inc., Q62739842, also has a normal-rank New York Stock Exchange qualifier DOW and 9 sitelinks. Dow Inc. was not substituted.

The draft now says: if scorer v2 is below 0.70 on the 150, up to two improvement rounds use the same training data and a fresh 150 each time, seeds 20261025 and 20261026; if it still fails, Wave 2 Arm A news is run and reported with the gate marked not met, and that failure stops only the news source. The sentence frame is the event windows of the stored news series, fixed before scorer v2 exists. Scorer v2 and the labelled set are Arm A news only. Arm B has no text scorer. Before the GDELT pass, 3 slices are compared with their dry-runs, and a billed-to-dry-run ratio above 1.5 puts the pass on 2 accounts under the 960 GB cap each.

This is frozen as amendment A2026-10-24-wave2. The operative phase0 hash is 9a61ea58d8d49f7576232a9eb2747f99fbde3dc0576b30cf3ac734246c5fc660. The previous hash 6440d8906a245333fa79da2bb467e3d2b87f2e4218d726d79e19fff037a1aa2e is kept. `scripts/check_frozen_sha256.py` exited 0, mismatches 0.

The label sheet is `data/handlabel/wave2_sample.csv`. The frame has 16,295 sentences. Seed 20261024 drew 150. Ids are W20001–W20150. `label_A` is empty. No model score is in the sheet. The instructions are the Wave 2 section of `data/handlabel/INSTRUCTIONS.md`. No further analysis was started.

## 2026-10-25 — Wave 2 Arm B is GDELT only

This entry is written before any Wave 2 download, BigQuery job, or new series file. No Wave 1 result, rule, planning SD, or caliper is changed. No login is run.

Local StockTwits features, `data/raw/stocktwits/features`, 29,980,570 rows. A message is counted when its stored cashtag list contains the ticker. Distinct message ids match the message counts. The 14-day bar is the same coverage floor as Phase 1. A ticker at or above 14 days gets an Arm A social series. A ticker below 14 days would be news only. No ticker is dropped.

| Ticker | Messages | Distinct days | Series |
|---|---:|---:|---|
| DD | 25,958 | 3,972 | social |
| SPG | 55,411 | 4,192 | social |
| BLK | 52,961 | 4,400 | social |
| JNJ | 139,225 | 4,977 | social |
| COP | 49,898 | 4,801 | social |
| BA | 770,041 | 5,021 | social |
| DOW | 37,742 | 4,682 | social |
| ACN | 38,828 | 4,186 | social |
| DIS | 589,967 | 5,025 | social |
| KO | 99,679 | 4,996 | social |
| BAC | 456,090 | 5,431 | social |
| GILD | 365,804 | 4,790 | social |
| PSX | 26,443 | 3,808 | social |
| GD | 26,491 | 4,162 | social |
| EA | 86,820 | 4,779 | social |
| WMT | 277,973 | 5,275 | social |

All 16 are at or above 14 days. All 16 get an Arm A social series. None is news only.

TweetsKB. Extending it to the 16 tickers means fetching the same 38 Zenodo files again, `month_2017-11.n3.gz` through `month_2020-12.n3.gz`, because the raw files were deleted after the reduce. The stored manifest sums to 137,152,496,940 bytes. The stored six-worker speeds, one file at a time, sum to 27.5 hours. That refetch is not started.

Decision. Wave 2 Arm B is GDELT only. TweetsKB is not extended. Arm A social for these 16 tickers is the local StockTwits extract. Arm B has no TweetsKB series.

## 2026-10-25 — Wave 2 collection is prepared and not started

No BigQuery call was made. No login was run. The watchdog was left running. No Wave 1 result, rule, planning SD, or caliper was changed.

The alias table is `configs/wave2_gdelt_aliases.json`. It has the 30 ecosystems. Each has a Wikipedia title and a mid. An extra title is accepted only when its mid is one of that ecosystem's mids. The 128 queries are `configs/wave2_gdelt_slices.jsonl`, 28-day slices from 2016-11-14 to 2026-08-15, every ecosystem in each query. The supervisor config is `configs/wave2_gdelt_supervisor.json`. It can hold one or two accounts. Each account has its own ledger `eval/results/bq_ledger_wave2_<account>.jsonl` and its own 960 GB cap. The first command is the 3-slice cost check. The full pass is not started. `scripts/phase2_gdelt_wave2.py --self-check` exited 0.

The local scoring plumbing used the Wave 1 scorer on 200 FNSPID rows and 200 StockTwits rows. The result is `eval/results/wave2_score_probe.json`. The full extracts were not scored. `scripts/phase_wave2_scorer_v2.py` exits while `label_A` is blank and does not download the finance-pretrained scorer.

## 2026-10-25 — Site graph enlarged and restyled

The Wave 2 GDELT watchdog is running. Its Python pid is 94422 and its caffeinate child is 94423. It watches `phase2_gdelt_wave2_supervisor.py`. When that supervisor stops on auth, quota, the 960 GB cap, a dry run above 10 GB, or an unexpected result, it writes `eval/results/NEEDS_ME.txt` and sends a desktop notification, then repeats the notification every 30 minutes until the supervisor is running again. It does not start the supervisor. The Wave 1 watchdog, pid 68468, was left running. No BigQuery call was made. No study result, model file, or frozen value was changed.

The site graph is Wikidata only, `site/assets/graph.json`. It has the 30 ecosystems, including Simon Property Group. The build kept 300 nodes and 434 edges (868 directed links), 47 hubs, and 18 nodes that sit in more than one ecosystem. Every edge cites a Wikidata property: P127, P1830, P1716, P1056, P176, P749, P355, or P169. A live search found no property whose English label is competitor, so the graph has no competitor edges. Co-mention is not a Wikidata property and news was not pulled, so the graph has no co-mention edges. No node or edge was invented. The magnitude on every node is the augmented model's per-edge-class estimate: positive 0.03177996754380209, competitor 0.04130934023630938, comention 0.032037299291363786.

The page is one force layout with a weak pull toward each ecosystem. Propagation follows edges and stops at 2 hops, including across edges that join ecosystems. `site/test_app.py` exited 0, including that 2-hop test on this graph. Screenshots are `site/screens/full.png`, `site/screens/apple.png`, and `site/screens/phone.png`.

## 2026-10-25 — Neighbor definition proposed, not frozen

No BigQuery call was made. No login was run. The Wave 2 supervisor was not started. The watchdog pid 94422 and its caffeinate child 94423 were left running, as was the Wave 1 watchdog pid 68468. No Wave 1 result, rule, planning SD, or caliper was changed. `configs/phase0.json` and `configs/frozen_sha256.json` were not edited. The neighbor gate stays at 6 and the control gate stays at least 1. No ecosystem was dropped.

A2026-10-25 is a proposal. The text is `reports/wave2_amendment_a2026-10-25.md`. It is not frozen.

Wave 1 competitor edges began as the hand list in `configs/phase1_universe.json`, fields `competitor_tickers` and `competitor_reason`, covering Apple, Microsoft, Alphabet, and Tesla. There is no Wikidata property labeled competitor. The procedure used for the rest of Wave 1 is in `reports/phase2_amendment8.md` section 5: a pair is proposed only where the English Wikipedia article names the rival, and the location is logged. The same procedure, read on 2026-10-25, gives competitor edges for 5 of the 16 Wave 2 ecosystems and none for the other 11. Boeing 1, Coca-Cola 1, Bank of America 11, Electronic Arts 3, Walmart 18. The 11 with none are DuPont, Simon Property Group, BlackRock, Johnson & Johnson, ConocoPhillips, Dow, Accenture, Disney, Gilead, Phillips 66, and General Dynamics. The list is `reports/wave2_competitor_edges.json`. These edges do not count toward the gate of 6.

On the 2026-10-12 snapshot, the 15 Wave 2 items that are in the snapshot have 1,071 preferred or normal structural edges with a sitelink count of at least 1 on both ends. P127 is 408 (38.1%), P1830 is 347 (32.4%), P749 is 140 (13.1%), P355 is 102 (9.5%), P1056 is 51 (4.8%), P176 is 22 (2.1%), and P1716 is 1 (0.1%). P169 is not in that edge file. Of the 408 P127 edges, 23 (5.6%) have an investor-type owner: Bank of America 14, State Street Corporation 4, J.P. Morgan & Co. 2, Kuwait Investment Authority 1, Morgan Stanley 1, Charles Schwab Corporation 1. The Vanguard Group, BlackRock, and Fidelity Investments are typed company or business, not asset manager, so the instance-of test does not remove them.

The proposal defines a neighbor as parent, subsidiary, owned brand, product, manufacturer, chief executive officer, or owned-by unless the owner is investor-type. Owner-of is not in that list. Under that definition every one of the 15 snapshot brands still has at least 6 neighbors, and a paired recount does not change the eligible-control count. Simon Property Group has no P127 on Q2287759. Its incoming neighborhood was not re-queried, so the logged count of 111 is not replaced. If the proposal also dropped owners of at least 3 of these brands, Accenture and Phillips 66 would have 5 neighbors and would fall below the written gate. That drop is not in the proposal. The gate was not changed.

The alias table now has a separate neighbor list. A title is added only when that item has an English Wikipedia title and its own non-deprecated P646 mid. 407 titles were added. 50 were rejected for no English title, 57 for no mid, and 16 were already a brand title. Each of the 128 slice queries now contains 442 titles and 438 mids. `scripts/phase2_gdelt_wave2.py --self-check` passed and did not start a query.

The site graph, and only the site graph, uses the same cleaned edges plus the pass-through removal the gate does not use. `site/assets/graph.json` now has 299 nodes, 315 undirected edges, and 568 directed links. The 30 brands stay. 62 competitor edges have sign −1, the 28 confirmed Wave 1 rivals and the 34 Wave 2 rivals above. Investor-type P127 edges, owner-of edges, and edges whose owner is Vanguard, BlackRock, State Street, Berkshire Hathaway, or Capital Group Companies are not drawn. The BlackRock node stays. A second-hop effect is the first-hop effect times 0.5. The default view labels the 30 brands, hides an edge whose two ends have different home ecosystems until a node is clicked or hovered, draws nodes at least 3 px and ambient edges at 0.4 px in `#9ca3af`, and fits the graph on load. After a click the active path is 1.2 px and the other edges are 0.3 px. Positive news at Apple reads: iPhone, MacBook, Apple CEO, 20th Century Studios, AMD, AT&T, Adobe, Apple II series and 52 more rise; Dell, HPQ, LOGI and Samsung fall. On a 390 by 844 phone the graph stage is 728 px and the Controls button is 44 px at the bottom of the frame. `site/test_app.py` exited 0. Screenshots were replaced: `site/screens/full.png`, `site/screens/apple.png`, and `site/screens/phone.png`. The footer is 11 px, line height 11 px, color rgb(107, 114, 128).

## 2026-10-25 — A2026-10-25 frozen

No BigQuery call was made. No login was run. The Wave 2 supervisor was not started. The watchdog pid 94422 and its caffeinate child 94423 were left running, as was the Wave 1 watchdog pid 68468. No Wave 1 result, rule, planning SD, or caliper was changed. The pooled Arm A planning SD stays 0.10636804456181562. The neighbor gate stays at 6. The control gate stays at least 1. No ecosystem was dropped.

`reports/wave2_amendment_a2026-10-25.md` is frozen as amendment A2026-10-25. The operative phase0 hash is ae05037c5b51da27412945f8b49d7e465dd435c5ee041504875d4c1bcdade577. The previous hash 9a61ea58d8d49f7576232a9eb2747f99fbde3dc0576b30cf3ac734246c5fc660 is kept. The report hash is b8c648a33e47936ecbee4207e1b0e6ecbac5eb65ac54d21d3a39ff04b493dd90. `scripts/check_frozen_sha256.py` exited 0, mismatches 0.

The primary neighbor definition and the 34 competitor edges are unchanged from the proposal. The robustness variant is reported beside every Wave 2 primary result and does not replace it. It drops a neighbor of 3 or more of the 16 ecosystems, and a generic class. The multi-ecosystem neighbors are The Vanguard Group, BlackRock, and Berkshire Hathaway. The generic classes are the 21 lowercase category labels listed in section 7, including software, video game, and asset management. Truck is not a neighbor of these 16, so it is not removed. Named products with a lowercase label stay. Accenture has 5 variant neighbors and Phillips 66 has 5. Both stay in, because the gate of 6 applies to the primary definition only. Simon's incoming neighborhood was not re-queried.

H2 competitor is tested on the 34 edges. The 10-pair rule is unchanged. The 11 ecosystems with no competitor edge enter H1 and H2 positive only.

The site graph, and only the site graph, drops the same generic classes and the nodes that neighbor 3 or more ecosystems. It now has 247 nodes, 244 undirected edges, and 426 directed links. The 30 brands stay. The page is one force layout, packed to the viewport, with cross-ecosystem edges drawn at 0.25 px. The legend sits in the page flow above the footer. On a 390 by 844 phone the stage is 702 px and the graph is scaled to that stage. Positive news at Apple reads: iPhone, MacBook, Apple CEO, Apple II series, Apple Pay, Apple Store, Apple TV, Apple TV (Q62446736) and 27 more rise; Dell, HPQ, LOGI and Samsung fall. `site/test_app.py` exited 0, including the 2-hop test and the test that no generic class node is in the graph. Screenshots were replaced: `site/screens/full.png`, `site/screens/apple.png`, and `site/screens/phone.png`.

## 2026-10-25 — Site clusters, desktop only

No study result, model file, or frozen value was changed. The watchdog pid 94422 and the Wave 1 watchdog pid 68468 were left running.

The site is desktop only. The phone stylesheet, the phone controls button, and `site/screens/phone.png` are removed. Each ecosystem is its own cluster. Cluster centres are shelf-packed by cluster size, with the brand label at the centre of its cluster. A collision pass keeps those root labels from overlapping at the default zoom. Links inside a cluster use strength 1. Cross-ecosystem links use strength 0.02, so the clusters stay apart and the faint edges still join them. Nodes whose label was empty or a raw Wikidata id are removed. `Apple TV (Q62446736)` is merged into Apple TV, `iPhone (Q621427)` into iPhone, and `National Geographic (Q5973845)` is renamed National Geographic. The site graph has 245 nodes and 242 undirected edges. The 30 brands stay. Colors, signs, the 2-hop half step, the one-line sentence, the footer, and the legend above the footer stay. Positive news at Apple reads: iPhone, MacBook, Apple CEO, Apple II series, Apple Pay, Apple Store, Apple TV, Apple Watch and 25 more rise; Dell, HPQ, LOGI and Samsung fall. `site/test_app.py` exited 0, including the 2-hop test and a test that no label is a raw Wikidata id and no two root labels overlap at 1440×900 or 1280×720. Screenshots are `site/screens/full.png` and `site/screens/apple.png` at 1440×900, and `site/screens/full_1280x720.png` and `site/screens/apple_1280x720.png` at 1280×720.

## 2026-10-25 — Wave 2 scorer comparison, gate not met

The filled sheet was not used to train. No full FNSPID extract and no StockTwits extract was scored. No improvement round was started. No Wave 1 result, rule, planning SD, or caliper was changed. The watchdog pid 94422 and the Wave 1 watchdog pid 68468 were left running. No login was run and no BigQuery call was made.

The sheet `data/handlabel/wave2_sample.csv` has 150 rows, ids W20001–W20150, columns id, ecosystem, node, text, label_A, and no score column. Every `label_A` is one of positive, negative, neutral, or not_about_brand. Rebuilding the seed-20261024 draw from stored FNSPID text reproduced the same 16,295-sentence frame and the same 150 marked sentences. No text differs.

Label counts on the 150: positive 50, neutral 49, negative 22, not_about_brand 29. The not_about_brand share is 29/150. By ecosystem it is Accenture 0/1, Boeing 3/33, Coca-Cola 0/3, ConocoPhillips 0/1, Disney 13/56, Dow 1/3, Electronic Arts 0/2, Gilead Sciences 5/24, and Walmart 7/27. Those 29 rows are dropped from the comparison. The scored set has 121 rows.

The comparison is the Wave 1 scorer against ProsusAI/finbert, on the marked sentence. The Wave 1 scorer receives the node and the marked sentence. FinBERT receives the marked sentence. The local FinBERT directory had been removed in an earlier disk cleanup, so the public checkpoint was cached again before the offline run. Neither model was trained on this sheet. The higher macro-F1 wins, and a tie would have kept the Wave 1 scorer. The gate is the winner's macro-F1 against 0.70.

The Wave 1 scorer macro-F1 is 0.6859, 95 percent interval 0.5944 to 0.7730. FinBERT is 0.6193, interval 0.5296 to 0.7041. The Wave 1 scorer is higher. The gate is not met. Confusion rows are the hand label and columns are positive, negative, neutral. Wave 1: positive 34, 2, 14; negative 1, 16, 5; neutral 9, 7, 33. FinBERT: positive 33, 2, 15; negative 2, 16, 4; neutral 16, 8, 25.

By ecosystem, scored rows and macro-F1, Wave 1 then FinBERT: Accenture 1, 0.0000, 0.3333; Boeing 30, 0.6333 (0.4421 to 0.8000), 0.6525 (0.4489 to 0.8168); Coca-Cola 3, 0.5556, 0.5556; ConocoPhillips 1, 0.3333, 0.3333; Disney 43, 0.7260 (0.5670 to 0.8565), 0.5694 (0.3876 to 0.7162); Dow 2, 0.2222, 0.3333; Electronic Arts 2, 0.3333, 0.2222; Gilead Sciences 19, 0.6183 (0.3450 to 0.8322), 0.5296 (0.2643 to 0.7342); Walmart 20, 0.7262 (0.3754 to 0.9280), 0.6121 (0.2642 to 0.8333). The numbers are in `eval/results/wave2_scorer_v2.json`. The improvement round is not started.

## 2026-10-25 — Amendment B frozen
Frozen before any Wave 2 outcome. phase0.json sha256 5d245305955d6f7502ce2e5002bcc79bf623a630c33ede4f383172250c78cb29. Amendment document (reports/wave2_amendment_b2026-10-25.md) sha256 b0857580d159e1ffe26d56b38d3783345e8c9f5163fa76b88b150b50c0764d9c.
Scripts and configs: wave2_labels.py fdabfa32efbe4a8c8c152bad21fdc40341f1467d3c25dbc6507fd465924c2ad8, wave2_self_controlled.py dd97b2a5c1758e27ef42e66a77f168637d1fcfcad91aa02e9094df970233111f, wave2_model.py d3997075aa4604309857f0333d5ae980aad243f00134c308cf93d2d07994690d, wave2_train.py d5bb719a314d08eb397157d3989879868ea1e2f16518f6a4ac180562f1115207, test_wave2.py a5dbf939bfb34370a2b1034da66fd5a69b03d0c76daf822544909522cee6fe93, wave2_config.py 051b9875b4f25550a67d5de9993f1715240844552110a5d0627e896e96fdd136, wave2_nodes.json 0d135a75738ba640ce664e0f8e62894890ec648bde910e777e2cf757fd714760, wave2_structural_edges.json ffb0d04d9d01d8b14c62c85c10dd23c1ef6765f06f0cbb708e4d9a68e5590cf7.
Wave 2 uses all 30 ecosystems in Arm B, Tesla included. Arm B is GDELT only. check_frozen_sha256.py exited 0, mismatches 0.
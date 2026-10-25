# Phase 1 data audit

Status: GO. Apple, Microsoft, Alphabet, and Tesla each pass the daily coverage gate and the daily power gate. The weekly fallback was computed and is not adopted. No H1–H4 outcome was computed. Event counts below are a planning proxy only.

The earlier audit in this file used SEntFiN and FinEntity as if they were event series. They are not. They have no dates and stay reserved for the Phase 3 classifier.

## Licenses

| Source | Terms seen | Academic use |
| --- | --- | --- |
| FNSPID | Hugging Face dataset card: Creative Commons Attribution-NonCommercial 4.0. The GitHub README also has a 2025-07-24 note that research and commercial use are released, while a later section still prohibits commercial use of the code. | Allowed. This project is non-commercial research. |
| StockTwits | S3 README at https://stocktwits-nyu.s3.amazonaws.com/dataset/README.md says the bucket is public and holds the data for replicating Li, Al Ansari, and Kaufman, Journal of Quantitative Description: Digital Media, 2025. The GitHub repository has no LICENSE file. The DOI page returned HTTP 406 in the earlier check and was not opened. | No term found that forbids academic research. |
| FinEntity | `readme.md` line 116, opened 2026-10-12: licensed under ODC-BY, https://opendatacommons.org/licenses/by/1-0/. The GitHub license API returns HTTP 404. | Allowed with attribution. |
| SEntFiN 1.0 | MIT, in the repository LICENSE. | Allowed. |

## What the event series are

FNSPID has no sentiment column. The planning proxy for news is VADER compound on the headline only. Social uses the StockTwits user label, Bullish = +1 and Bearish = −1. Unlabeled posts are counted as mentions and are not in the mean. Final scores are Phase 3.

| File | Bytes | Content SHA-256, equal to the Git-LFS object id | What was kept |
| --- | ---: | --- | --- |
| `nasdaq_exteral_data.csv` | 23,232,979,597 | `1a7a3eb8e6b97ec19f286f2cfca3371542bddb272ab1eb8f36e33ad98fa5c4da` | Rows for the logged ticker list, not the full CSV |
| `All_external.csv` | 5,731,397,037 | `5d4c018036bd82ca821da71b7a9c0c7db3289642e0fc6f897ea69f4a0c5135c3` | Same rule. This pass added no new kept rows. |

The HTTP ETags (`cccdf2f3…` and `dde52918…`) are not these content hashes. Kept news rows: 731,458. Every kept `Date` ends with `UTC`. StockTwits: 29,980,570 feature rows, every `created_at` ends with `Z`, of which 10,399,599 have a bullish or bearish label. Message bodies stored: 20,613,589. The working day is the UTC calendar date. Symbol-table dates have no clock and are not the social timestamp.

SEntFiN: 10,753 headlines, no date column, MIT. FinEntity: 979 paragraphs, no date field, ODC-BY. Both are training text for the Phase 3 entity-aware classifier. They are not discarded.

## The stalled row counts

The stream's row counter was flat on two spans of each FNSPID file: about 2.03 GB and then about 2.84 GB. `scripts/phase1_fnspid_stall_check.py` does not use this project's parser. It counts line-start timestamps and the stock-symbol field after the title. On 2 MB windows at the start, middle, and end of each stall, that field was empty, and `,AAPL,`, `,MSFT,`, `,GOOG,`, `,GOOGL,`, `,TSLA,`, and `,AMZN,` occurred 0 times.

Three of those windows sit inside long quoted articles, so the first pattern missed the URL. A second pattern, title then an empty symbol then a quoted or plain `http` URL, counted 672, 618, and 608 rows in those three windows, and 0 rows with a ticker before the URL. Python's `csv` module, started at `,2010-09-28 00:00:00 UTC,Avenue Capital…` inside the nasdaq stall, returned an empty symbol and a Bloomberg URL. The articles are present. They have no ticker. The parser was not changed and that region was not reprocessed.

## Sector map and control pool

The map was logged before the stream. `configs/sector_taxonomy.json`, SHA-256 `9a191e03a468b123cee7f38870d2dc74f12a19ca24aad35573fd57749fe6a231`. Eleven buckets. Automotive Wikidata labels sit in `consumer_discretionary`. The match key is the coarse bucket, not raw Wikidata P452. The per-event Wikidata path check is still required before any confirmatory match. Wikidata property ids remain unverified.

Control pool: 184 names in `configs/phase1_universe.json`, SHA-256 `90f304c40d296682c38bf219d9000394c75ed42324613bd1212022e651057d89`. "With 14 days" means at least 14 distinct UTC days in the retained extract.

| Bucket | Defined | News days ≥ 14 | Social days ≥ 14 | News days = 0 |
| --- | ---: | ---: | ---: | --- |
| information_technology | 20 | 19 | 20 | JKHY |
| communication_services | 16 | 15 | 16 | LUMN |
| consumer_discretionary | 18 | 18 | 18 | |
| financials | 18 | 16 | 18 | CB, SPGI |
| healthcare | 18 | 17 | 18 | ISRG |
| energy | 16 | 16 | 16 | |
| utilities | 16 | 16 | 16 | |
| industrials | 18 | 16 | 18 | HON, RTX |
| consumer_staples | 16 | 16 | 16 | |
| materials | 14 | 12 | 14 | BALL. LIN has 3 news days |
| real_estate | 14 | 14 | 14 | |

## Planning standard deviation

Frozen before any real event outcome. The pair is the focal company's own absolute shift against a sector-matched control, because one-hop neighbors do not exist until Phase 2. Popularity was not applied. Seed 3. Up to 20 non-event dates per company per source. Sample standard deviation uses divisor n−1.

| | Value | Events for MDE ≤ 0.10 | Events for half-width ≤ 0.05 |
| --- | ---: | ---: | ---: |
| Old, provisional | 0.20 | 32 | 62 |
| New, frozen | 0.106368 | 9 | 18 |

Placebo dates drawn: 80 news and 80 social. Matched pairs: 24 news and 7 social, 31 in total. `configs/phase0.json` still contains 0.20 so the approved file stays intact. The operative value is the new one.

A day is a qualifying event when the absolute z-score against the trailing 28-day baseline is at least 2, the baseline has at least 14 observed days, the event bin has at least 5 scored documents, and the refractory gap is 8 days. News scores are VADER on the headline. Social scores are user labels. These counts are a planning proxy only.

The power numerator is brand news events plus brand social events. Product, CEO, and competitor events are reported and are not added. Coverage: the brand has both sources, and at least 6 of 7 other planned nodes have both sources. A node has a source if that source has at least 14 distinct UTC days with a mention.

Pooled brand events for the four ecosystems that pass: 613. That is above 18, and it is also above the old cutoff of 62. Mention totals for the non-brand nodes were not stored, so those cells are blank. Day counts are what the coverage gate uses.

## Apple

Information technology. Brand AAPL. Other planned nodes: 7. Both sources: 6 of 7 (0.857). Daily MDE 0.022. Weekly MDE 0.026. Coverage pass. Power pass on both bin sizes. The decision uses the daily row.

| Node | News mentions | Social mentions | News days | Social days | News events, daily / weekly | Social events, daily / weekly | Both sources |
| --- | ---: | ---: | ---: | ---: | --- | --- | --- |
| AAPL | 9,141 | 4,753,938 (1,524,123 labeled) | 639 | 5,540 | 14 / 16 | 171 / 115 | Yes |
| iPhone | | | 2,896 | 2,571 | 26 / not stored | 40 / not stored | Yes |
| MacBook | | | 369 | 1,344 | 0 / not stored | 1 / not stored | Yes |
| Apple CEO | | | 1,006 | 2,167 | 2 / not stored | 6 / not stored | Yes |
| DELL | | | 1,077 | 3,588 | 0 / not stored | 12 / not stored | Yes |
| HPQ | | | 2,313 | 5,051 | 1 / not stored | 12 / not stored | Yes |
| SONY | | | 0 | 806 | 0 / not stored | 3 / not stored | No |
| LOGI | | | 647 | 3,364 | 0 / not stored | 5 / not stored | Yes |

SONY has no FNSPID rows under `SONY` or `SNE`. `SON` has 954 news days and is a different company, so it is not a substitute. SONY was not replaced. DELL, HPQ, and LOGI already clear both sources. iPad has 1,567 news days and 1,945 social days, and Apple Watch has 886 and 1,333. Those two are outside the 75 percent denominator.

## Microsoft

Information technology. Brand MSFT. Both sources: 7 of 7. Daily MDE 0.028. Weekly MDE 0.030. Coverage pass. Power pass.

| Node | News mentions | Social mentions | News days | Social days | News events, daily / weekly | Social events, daily / weekly | Both sources |
| --- | ---: | ---: | ---: | ---: | --- | --- | --- |
| MSFT | 8,516 | 770,165 (282,498 labeled) | 594 | 5,465 | 5 / 11 | 110 / 85 | Yes |
| Windows | | | 555 | 568 | 0 / not stored | 0 / not stored | Yes |
| Azure | | | 1,529 | 1,216 | 7 / not stored | 1 / not stored | Yes |
| Microsoft CEO | | | 702 | 427 | 0 / not stored | 0 / not stored | Yes |
| ORCL | | | 2,813 | 4,976 | 1 / not stored | 44 / not stored | Yes |
| CRM | | | 2,509 | 5,022 | 4 / not stored | 53 / not stored | Yes |
| IBM | | | 491 | 5,219 | 0 / not stored | 60 / not stored | Yes |
| ADBE | | | 2,415 | 4,680 | 3 / not stored | 51 / not stored | Yes |

## Alphabet

Communication services. Brand is GOOG and GOOGL together. Both sources: 7 of 7. Daily MDE 0.024. Weekly MDE 0.026. Coverage pass. Power pass.

| Node | News mentions | Social mentions | News days | Social days | News events, daily / weekly | Social events, daily / weekly | Both sources |
| --- | ---: | ---: | ---: | ---: | --- | --- | --- |
| Alphabet | 11,618 | 849,491 (216,605 labeled) | 1,829 | 5,485 | 15 / 40 | 142 / 96 | Yes |
| YouTube | | | 2,176 | 2,518 | 14 / not stored | 75 / not stored | Yes |
| Android | | | 1,939 | 2,094 | 0 / not stored | 5 / not stored | Yes |
| Alphabet CEO | | | 554 | 499 | 0 / not stored | 0 / not stored | Yes |
| Meta | | | 87 | 4,921 | 0 / not stored | 151 / not stored | Yes |
| AMZN | | | 311 | 5,460 | 10 / not stored | 127 / not stored | Yes |
| SNAP | | | 1,609 | 2,773 | 3 / not stored | 84 / not stored | Yes |
| PINS | | | 965 | 1,732 | 1 / not stored | 34 / not stored | Yes |

Meta's news days are the FB rows. The META symbol itself has 0 news rows. The node still clears 14 days.

## Tesla

Consumer discretionary. Brand TSLA. Both sources: 7 of 7. Daily MDE 0.024. Weekly MDE 0.028. Coverage pass. Power pass.

| Node | News mentions | Social mentions | News days | Social days | News events, daily / weekly | Social events, daily / weekly | Both sources |
| --- | ---: | ---: | ---: | ---: | --- | --- | --- |
| TSLA | 10,294 | 5,548,247 (2,874,126 labeled) | 872 | 4,699 | 11 / 19 | 145 / 93 | Yes |
| Model 3 | | | 990 | 2,262 | 3 / not stored | 23 / not stored | Yes |
| Model S | | | 3,274 | 2,403 | 29 / not stored | 14 / not stored | Yes |
| Tesla CEO | | | 1,560 | 2,361 | 12 / not stored | 34 / not stored | Yes |
| F | | | 419 | 5,432 | 4 / not stored | 190 / not stored | Yes |
| GM | | | 23 | 4,628 | 0 / not stored | 72 / not stored | Yes |
| TM | | | 2,790 | 4,531 | 3 / not stored | 12 / not stored | Yes |
| NIO | | | 1,399 | 2,080 | 5 / not stored | 68 / not stored | Yes |

GM clears the 14-day news bar with 23 days, which is thin relative to the other competitor nodes. Model Y has 584 news days and 1,573 social days. Cybertruck has 379 and 1,147. Both are outside the denominator.

## Limitation for the faculty guide

Both event sources are finance-oriented. FNSPID is stock news. A StockTwits bullish or bearish label is an investor's outlook, not a brand-reputation judgment. The idea stays brand reputation. Phase 3's brand-domain hand label, macro-F1 at least 0.70, is the test of whether the scoring transfers. This audit does not change the dataset or the claim language.

## Decision

GO on the daily rule. Four ecosystems pass coverage and power, and the pre-registered minimum is two. The weekly numbers are in the tables and are not the confirmatory bin.

Phase 2 was paused on 2026-10-12 before a knowledge graph was built. Phase 1B checked public brand-reputation sources and did not replace FNSPID or StockTwits. The gates above were not re-run. The finance-orientation limitation stands. Detail is in `reports/phase1b_brand_reputation_audit.md`.

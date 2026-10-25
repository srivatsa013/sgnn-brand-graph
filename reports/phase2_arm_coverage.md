# Phase 2 arm coverage

Date: 2026-10-13. The knowledge graph is the Wikidata snapshot `wikidata_2026-10-12`. Edges are in `kg/phase2_structural_edges.json`. The DBpedia map is `configs/arm_b_dbpedia_uris.json`. CEO windows are in `configs/ceo_tenures.json`. No usable-pair report was run. No H1–H4 outcome was computed.

A node is covered on a source when that source has at least 14 distinct days. Arm A CEO days below are the windowed recount. Other Arm A days are the Phase 1 gate. Arm B social days count each tweet once. Arm B news days are English GDELT GEG articles, one article once per node.

## Source decision

Arm A stays FNSPID news and StockTwits social, for Apple, Microsoft, Alphabet, and Tesla.

Arm B social stays TweetsKB, for Apple, Microsoft, and Alphabet. Tesla stays out of Arm B.

Arm B news is GDELT GEG. Coverage passes on every planned Arm B node, including Android and Samsung. Brand planning-proxy events under |z| ≥ 2 are Apple 149, Microsoft 157, and Alphabet 145, on 3,482 matched days from 2016-11-14 through 2026-06-18. Those counts clear a descriptive check at the provisional SD 0.20, whose cutoffs are 32 events and 62 events. GDELT's own placebo SD is not estimated, so that check does not freeze the operative cutoff. The usable-pair report waits for approval of this source set.

The GDELT score is the article's document score on [−1, 1]. It is copied to each matched node. It is not an entity-level score.

## Per-arm coverage

| Node | Arm A | Arm B social | Arm B news |
| --- | --- | --- | --- |
| Apple, iPhone, MacBook, DELL, HPQ, LOGI, Samsung | Covered on FNSPID and StockTwits. Samsung news is the headline alias: 189 days, 283 rows. FNSPID tickers SSNLF, SMSN, and SSNGY have 0 rows. StockTwits SSNLF has 546 labeled rows on 385 scored days. | Covered. Samsung uses `Samsung`, 2,028 days and 14,840 tweets. `Samsung_Electronics` has 220 tweets and is not added. | Covered. Samsung has 3,482 days. |
| Apple CEO | Covered. Windowed news 779 days, social 1,848 days. | Covered. Tim Cook, 1,057 days. Steve Jobs ends before the sample. | Covered. 3,482 days. |
| Microsoft, Windows, Azure, ORCL, CRM, IBM, ADBE | Covered on both. | Covered. Adobe uses `Adobe_Inc.`, 21 days. | Covered. |
| Microsoft CEO | Covered. Windowed news 674 days, social 341 days. | Covered. Satya Nadella, 166 days. Steve Ballmer ends before the sample. | Covered. 3,451 days. |
| Alphabet, YouTube, Meta, AMZN, SNAP, PINS | Covered on both. | Covered. Brand series is `Google`, 2,062 days. Snap uses `Snap_Inc.`, 14 days. | Covered. |
| Alphabet CEO | Covered. Windowed news 467 days, social 356 days. | Covered. Union of Larry Page through 2019-12-03 and Sundar Pichai from 2015-08-10: 257 days, 393 tweets. Eric Schmidt ends before the sample. | Covered. 3,478 days. |
| Android | Covered on both, by alias. | Not covered. Every tried URI returned 0 tweets. | Covered. 3,482 days. |
| Tesla, Model 3, Model S, Tesla CEO, F, GM, TM, NIO | Covered on both. Windowed Tesla CEO news 1,559 days, social 2,350 days. | Excluded. | Excluded. |

Arm B social coverage of the other nodes is 7 of 7 for Apple, 7 of 7 for Microsoft, and 6 of 7 for Alphabet. Android is the social miss. That fraction is 0.857. Arm B news coverage of the other nodes is 7 of 7 in each of those three ecosystems.

## GDELT scan

The English 2016-11-14 dry run, on date, language, score, and magnitude, was 2,708,608 bytes. Each 28-day entity slice dry-ran at 7,694,617,837 bytes. Both are under 10 GB. The loop ran 128 slices. The upper bound is 984,911,083,136 bytes. Actual bytes were not captured, because the job id was absent from the quiet client output, and the 900 GB stop did not fire. No second scan was run. The English table's earlier minimum and maximum were 2016-07-17 and 2026-08-14. These name filters have no row after 2026-06-18.

## Identifiers

Arm A uses the tickers and aliases in `configs/phase2_nodes.json`. Arm B uses one DBpedia series per node, except the Alphabet CEO node, which is the windowed union above. A second company URI is recorded and is not added into the series.

| Node | Wikidata | Arm B series URI | Not added |
| --- | --- | --- | --- |
| Apple | Q312 | `Apple_Inc.` | |
| Alphabet | Q95, and Q20800404 because an ownership statement links them | `Google` | `Alphabet_Inc.` |
| HPQ | Q80978 Hewlett-Packard. Dell Technologies Q27500963 is attached to DELL the same way | `Hewlett-Packard` | `HP_Inc.` (10 days) |
| ADBE | Q11463 | `Adobe_Inc.` | `Adobe_Systems` |
| Meta | Q380 | `Facebook` | `Meta_Platforms` (0 tweets) |
| AMZN | Q3884 | `Amazon.com` | `Amazon_(company)` (0 tweets) |
| SNAP | Q27022329 | `Snap_Inc.` | `Snapchat` |
| PINS | Q96095585, 1 sitelink, no English Wikipedia title | `Pinterest` | Not merged with search hit Q255381 |
| Samsung | Q20718 | `Samsung` | `Samsung_Electronics` |
| Tesla | Q478214 | none | `Tesla_Motors` ends 2017-11-29. `Tesla,_Inc.` returned 0. |

## Edges

Seven positive edges, each from a verified statement: iPhone and MacBook manufactured by Apple, Windows and Azure produced by Microsoft, YouTube owned by Google, Model 3 and Model S manufactured by Tesla.

Android Q94 has 155 sitelinks. The only statement to Google is P178 developer. P178 is not a verified positive property, so there is no Android edge.

CEO statements that match an alias: Tim Cook and Steve Jobs, Satya Nadella and Steve Ballmer, Sundar Pichai, Larry Page, and Eric Schmidt, Elon Musk. Each alias counts only inside the window in `configs/ceo_tenures.json`. From 2026-09-01 the preferred Apple P169 target is Q106028933, which has no English label, so it is not an alias.

Sixteen competitor edges, sign −1, brand to named competitor, reverse not asserted. The 15 confirmed edges are unchanged. Samsung is the sixteenth, added because TweetsKB, StockTwits mentions, FNSPID headlines, and GDELT each clear 14 days. Logitech stays. No Wikidata competitor property was used.

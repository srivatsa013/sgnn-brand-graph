# Usable-pair feasibility

Date: 2026-10-14. No shift, no H1–H4 estimate, and no widened caliper. The counts are in `eval/results/phase2_feasibility.json`.

## Recommendation

GO for Arm A pair construction. Both Arm A sources clear the pre-registered minimums: 10 matched pairs for H1 and 5 events per source for H4.

NO-GO for Arm B pair construction in this quota month. The Wikipedia-URL extract does not fit the remaining free tier, and the TweetsKB control series do not produce a matched placebo pair, so no Arm B planning SD was frozen.

Phase 3 does not start.

## Quota

Project `sgnn-csp` billed 929,292,091,392 bytes across 130 jobs on 2026-10-13. The one-day match audit on 2026-10-14 added 238,212,204 bytes. About 70.5 GB of a 1 TB month remains. About 170 GB remains if the allowance is 1 TiB. The next calendar month starts 1 November 2026.

The English 2016-11-14 score-column dry run from the probe was 2,708,608 bytes. A full-span unnest of every entity subfield dry-runs at 2,105,210,623,656 bytes and was not run. A 28-day extract of day, document-id hash, document score, and Wikipedia URL or mid dry-runs at 3,333,846,320 bytes. The saved name-based daily file is the only full-span aggregate. Per-document entity lists were not stored. Later queries go through `scripts/bq_usage.py`, which records the job id and stops at 10 GB or at 1 TB for the month.

## Match rule

Logged in `configs/gdelt_match_rule.json` before these pair counts. A mention matches a node only when its Wikipedia URL is that node's English title, or when the URL is empty and the Knowledge Graph mid is on that title's allow-list. A bare name does not match.

On 2016-11-14, Azure's bare name is the right page in 16 of 29 rows. Amazon.com is the right page in 1,045 of 1,077 rows. Windows is Microsoft Windows in 271 of 279 rows. Apple Inc. is the right page in 1,877 of 1,900 rows. The bare name HP hits horsepower in 71 of 164 rows. The bare name Snap hits none of Snapchat. This is one day, not a full-span rate.

## Samsung

Arm A social has 546 labeled `SSNLF` rows on 385 days. That is above 14 scored days, so Samsung stays covered in Arm A. Unlabeled posts are not scored. Arm A news stays the headline alias, 189 days. Arm B is unchanged. Coverage is per arm.

## Planning SD

Not frozen for either Arm B source. TweetsKB used seed 3 and 20 placebo dates on Apple, Microsoft, and Alphabet. None of the 60 dates had a sector control with its own 14-day baseline. GDELT controls were not scanned. SESOI 0.05 and caliper 0.20 are therefore not converted for those sources. The Arm A pooled SD 0.10636804456181562 is unchanged. The absolute calipers used below are the pre-registered ones.

H4 on Arm B can use only the overlap of the two sources: 2016-11-14 through 2020-12-31.

## Subsidiaries

A day counts only when it has at least 14 scored documents, and only on or after the ownership start date. LinkedIn is the only name that clears an arm. LinkedIn Corporation Q127278673 is owned by Microsoft from 2016-06-13. FNSPID has 14 such days. TweetsKB has 41 such days. The edge is in the graph. Its Arm A cells are not in `series.sqlite` yet, so it adds no pair in the table below.

Not added: GitHub (owned from 2018-06-04; 0 FNSPID days and 2 TweetsKB days at the 14-document bar), Waymo, DeepMind, Fitbit, SolarCity (dated ownership, 0 such days), Beats (no P580), Activision Blizzard (preferred parent is Xbox Game Studios from 2023-10-13, and the Microsoft child statement has no start date).

## Arm A counts

A usable pair is a brand event whose target has at least 3 scored days in both the pre window (days −7 through −1) and the post window (days 0 through 7), after documents that mention the event brand are dropped, and a control inside the pre-registered calipers that also has both windows. Pooled across the four ecosystems:

| Source | Edge class | Matched pairs | Events with such a pair | Minimum |
| --- | --- | --- | --- | --- |
| News | H1, both classes | 37 | 20 | 10 pairs, and 5 events for H4 |
| News | Positive | 10 |  | 10 proposed, not pre-registered |
| News | Competitor | 27 |  | 10 proposed |
| Social | H1, both classes | 207 | 155 | 10 pairs, and 5 events for H4 |
| Social | Positive | 29 |  | 10 proposed |
| Social | Competitor | 178 |  | 10 proposed |

The 10 positive news pairs are all Tesla. Apple, Microsoft, and Alphabet have 0 positive matched pairs on news and on social. Apple news has 0 positive events with both windows. Microsoft news and social have 0. Alphabet social has 93 positive events with both windows and 0 that also find a caliper control. Competitor edges carry the H1 and H4 counts.

Proposed H2 minimum, not locked: 10 matched pairs per edge class per source, pooled inside the arm. Competitor edges meet it. Positive edges meet it only because Tesla does. Apple, Microsoft, and Alphabet positive edges do not meet 10 on their own.

## Arm B

Not counted under the new match rule. The co-mention lists are not on disk, and a second historical scan does not fit this month. TweetsKB controls were queried and did not support a caliper match under the 14-day baseline. That is the NO-GO.

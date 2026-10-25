# Alias fix, Amendment 8, and the frozen rerun

2026-10-19. Pair counts and coverage only. No shift, no estimated effect, and no widened caliper. No competitor edge was added. The 128-slice rerun was not started. Phase 3 does not start.

## 1. Alias table and corrected coverage

The table is `configs/gdelt_alias_table.json`, written before the series rebuild. A title is an alias only when every stored row carries that node's mid and the title is the same entity. The rebuilt series is `data/interim/phase2/gdelt_series.sqlite`. 27,334,756 articles match a node.

`Snap_Inc.` is not an alias of SNAP. Its mid is `/g/11c1s2xz66`. Snapchat's mid is `/m/0nbtf_n`, and Snapchat is present in every year of the extract. Hewlett Packard Enterprise is not mapped to HP Inc. `Planet_Google`, `Author_Rank`, and `Ludicrous_Mode` are rejected.

Lowe's has no second title. The 2023 hole is in the extract.

Scored days and dense days (at least 14 scored documents), before the aliases and after:

| Node | Before | After |
| --- | --- | --- |
| AMZN | 327 scored days, none in 2019–2025 | 3,482 / 3,482 |
| Meta | absent | 1,676 / 1,676, from 2021 (63 days in 2021, then every day) |
| Lowe's | 2,221 / 1,937, 2023 = 0 | 2,221 / 1,937, 2023 = 0 |
| Alphabet | 3,480 / 3,467 | 3,480 / 3,480 |
| SNAP | 3,471 / 3,469 | 3,471 / 3,469 |
| Apple | 3,449 / 3,448 | 3,482 / 3,482 |

## 2. Amendment 8

Logged in `DECISIONS_LOG.md` before this recount. An owner link is dropped when the owner is instance of asset manager, mutual fund, pension fund, or sovereign wealth fund. No English item is labeled "investment management company", so that class was not added. Parent, subsidiary, brand, product, and manufacturer edges stay. The strict graph keeps every owner link and is the robustness check.

Ten edges drop. They are holdings of GIC, Temasek, Government Pension Fund Global, the Qatar Investment Authority, the Kuwait Investment Authority, and the mutual fund Castor. The Vanguard Group stays in both graphs. It is instance of company, business, and enterprise. Its mutual-fund and asset-management statements are products, and those were not used.

## 3. Control pool

Tested on the 2026-10-12 path graph, non-deprecated edges, Amendment 8. A name returns when it is not a confirmed competitor and no path of length at most 2 remains. SSNLF, SMSN, and SSNGY stay out: Samsung is a confirmed competitor.

These stay out:

| Ticker | QID | Sitelinks | Why |
| --- | --- | --- | --- |
| NVDA | Q182477 | 81 | Vanguard, owner of Nvidia, owned by path to Apple |
| INTC | Q248 | 101 | same Vanguard hop |
| NFLX | Q907311 | 144 | same Vanguard hop. No industry label, so no bucket |
| STLA | Q97439162 | 49 | both Stellantis and Ford have product "truck". Consumer discretionary |

These return. The bucket is the logged industry map. A label the map does not list is left unassigned. Sitelinks are the live Wikidata count from 2026-10-19.

| Ticker | Name | Sitelinks | Bucket |
| --- | --- | --- | --- |
| TSM | TSMC | 54 | information technology |
| AVGO | Broadcom | 26 | information technology |
| AMD | AMD | 78 | information technology |
| ASML | ASML Holding | 44 | information technology |
| QCOM | Qualcomm | 56 | information technology and communication services |
| AMAT | Applied Materials | 21 | no industry label |
| MU | Micron Technology | 31 | no industry label |
| LRCX | Lam Research | 17 | no industry label |
| KLAC | KLA Corporation | 17 | label "electronics" is not in the map |
| BBY | Best Buy | 32 | consumer discretionary |
| ORLY | O'Reilly Auto Parts | 10 | consumer discretionary |
| AZO | AutoZone | 11 | consumer discretionary |
| AAP | Advance Auto Parts | 8 | no industry label |
| GPC | Genuine Parts Company | 6 | no industry label |
| RIVN | Rivian | 25 | consumer discretionary |
| LCID | Lucid Motors | 23 | consumer discretionary |
| HMC | Honda | 105 | consumer discretionary |
| VWAGY | Volkswagen Group | 69 | consumer discretionary |
| ALB | Albemarle | 11 | materials |
| GRMN | Garmin Ltd. | 0 | no industry label |

Garmin returns by the path rule and cannot be selected: popularity is missing, and it has no English title and no Freebase mid. Qualcomm has two mapped buckets, so it has no single match key. None of these buckets were written into the taxonomy file.

The current pool's eligible counts do not move. Apple, Microsoft, Alphabet, and Tesla stay at 13, 13, 9, and 11 controls. The names above were outside that pool. Home Depot, Visa, and the other consumer names in section 5 stay inside through Vanguard.

## 4. Arm A pairs, the positive funnel, and the TweetsKB placebo

The two graphs give the same counts. Detail is `eval/results/phase2_amendment8_recount.json`.

Usable pairs on the current Arm A series, LinkedIn cells included:

| Source | Class | Pairs | Events |
| --- | --- | --- | --- |
| news | H1, both classes | 37 | 20 |
| news | positive | 10 | |
| news | competitor | 27 | |
| social | H1, both classes | 209 | 157 |
| social | positive | 31 | |
| social | competitor | 178 | |

The 2026-10-14 file had social H1 207, social positive 29, and social H4 155. The two extra social positive pairs are the LinkedIn cells already logged that day. Amendment 8 adds none.

Positive funnel, events / both windows / after co-mention / control in the calipers. Both graphs:

| Ecosystem | Source | Events | Both windows | After co-mention | Control |
| --- | --- | --- | --- | --- | --- |
| Apple | news | 14 | 14 | 0 | 0 |
| Apple | social | 171 | 96 | 35 | 0 |
| Microsoft | news | 5 | 5 | 1 | 0 |
| Microsoft | social | 110 | 29 | 16 | 2 |
| Alphabet | news | 15 | 15 | 5 | 0 |
| Alphabet | social | 142 | 93 | 93 | 0 |

Alphabet social: 426 comparisons with a control that has a 14-day baseline. Passes are mean 189, SD 273, mention 96, popularity 0. Two events have no target baseline. One has no control with a baseline. Sixty-four events pass mean and SD. Twenty-three fail only popularity.

TweetsKB 5 percent sample, seed 3. The Alphabet URI has 103 days, 127 scored rows, and 0 eligible non-event dates, so it cannot supply 20 dates. The 60 dates are 20 on Apple, 20 on Microsoft, and 20 on Google, drawn in that order. Eligible controls are the same under both exclusion rules, and every one of them is in the 5 percent file. Treated popularity is the brand sitelink count: Apple 183, Microsoft 178, Alphabet 211.

| Series | Dates | Controls | Comparisons | 14-day baseline | Dates with zero baselines | Mean | SD | Mention | Popularity |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Apple | 20 | 13 | 260 | 8 | 13 | 8 | 5 | 2 | 0 |
| Microsoft | 20 | 13 | 260 | 6 | 15 | 6 | 4 | 0 | 0 |
| Google | 20 | 9 | 180 | 27 | 7 | 27 | 0 | 1 | 0 |

No comparison passes all four calipers. Thirty-five of the 60 dates have no control with a 14-day baseline. The other 25 have at least one, and popularity passes on none of them. No planning SD is frozen.

## 5. Rival proposals

No edge was added. A pair is listed only where the brand's English Wikipedia article, retrieved 2026-10-19, contains the rival's name. Coverage is scored days / dense days. The bar is 14 scored days. GDELT for the rivals below is absent from the stored scan, because those names were controls and the scan's name filter left controls out. Arm A is FNSPID and StockTwits.

| Pair | Wikipedia location | GDELT brand | Arm A news, brand / rival | Arm A social, brand / rival | Inside two hops |
| --- | --- | --- | --- | --- | --- |
| Chipotle–McDonald's | Chipotle Mexican Grill, lead | 3,470 / 2,019 | 2,495 / 946 | 4,029 / 3,512 | McDonald's, through Vanguard |
| T-Mobile–AT&T | T-Mobile US, History | 3,399 / 1,612 | 2,202 / 2,339 | 2,703 / 3,577 | AT&T, product class "software" shared with Apple |
| T-Mobile–Verizon | T-Mobile US, The "Un-carrier" | 3,399 / 1,612 | 2,202 / 1,317 | 2,703 / 3,477 | Verizon, through Vanguard |
| Lowe's–Home Depot | Lowe's, lead | 2,221 / 1,937 | 1,241 / 1,576 | 2,691 / 3,432 | Home Depot, through Vanguard |
| Mastercard–Visa | Mastercard, lead | 2,946 / 2,946 | 1,123 / 2,816 | 3,629 / 3,928 | Visa, through Vanguard |
| Chevron–ExxonMobil | Chevron Corporation, lead | 3,473 / 3,464 | 2,103 / 1,498 | 3,312 / 3,757 | Exxon, through Vanguard |
| Hershey–Mondelez | The Hershey Company, Cadbury | 3,435 / 1,717 | 847 / 1,082 | 1,525 / 1,542 | Mondelez, through Vanguard |
| Colgate–Procter & Gamble | Colgate-Palmolive, Competition with P&G | 3,420 / 909 | 2,048 / 652 | 4,043 / 2,828 | Procter & Gamble, through Vanguard |
| Lilly–Pfizer | Eli Lilly and Company, 2000–present | 3,471 / 3,207 | 1,393 / 807 | 2,585 / 3,555 | Pfizer, through Vanguard |
| Lilly–AbbVie | Eli Lilly and Company, 2000–present | 3,471 / 3,207 | 1,393 / 2,612 | 2,585 / 3,153 | AbbVie, through Vanguard |
| Nike–Adidas | Nike, Inc., lead | 3,425 / 3,392 | 2,736 / no ticker | 3,666 / no ticker | Adidas is not in the retained set |

Every named company that has a ticker clears 14 scored days on at least one Arm A source. Adidas has no retained ticker, so Arm A has no series for it. Its title is on the frozen allow-list.

These were not proposed. The fetched article does not contain the string: Chipotle–Yum, Colgate–Kimberly-Clark, Lilly–Merck, Deere–Caterpillar, NextEra–Duke Energy, NextEra–Southern Company, Nike–Under Armour, New York Times–News Corp, New York Times–Gannett. Merck's ticker MRK stays ambiguous. Under Armour, Adidas, News Corp, and USA Today Co. (the item returned for a Gannett search) are on the allow-list as titles only.

Eligibility rule, logged before any outcome on a new brand: a new brand is eligible for an arm when it clears the coverage bar on at least one source in that arm. H4 counts only events with both sources.

## 6. Frozen allow-list and the pilot

`configs/gdelt_frozen_allowlist.json` has 260 entities, 273 titles, and 232 Freebase mids from Wikidata P646. It includes the study nodes and the accepted aliases, Larry Page and Sundar Pichai as separate titles, Elon Musk, Tim Cook, Satya Nadella, LinkedIn, Pinterest, Meta with Facebook and Facebook,_Inc., the 12 brands, the rivals named above, the dated Nike subsidiaries, all 206 retained tickers, and the left-out names from section 3. Sony is included, Q41187, mid `/m/06q07`. Meta's mid is `/m/0hmyfsv`. EPAM has no English title and mid `/m/0dlnrc`. The seven ambiguous tickers have no title and no mid. Garmin Ltd. has neither. The concatenated title "Larry Page and Sundar Pichai" is absent. Hewlett Packard Enterprise is absent. Rejected aliases are absent. Snap Inc. remains because it is SNAP's own English title.

The pilot was not queried. The active account `srivatsa.singaraju2023@vitstudent.ac.in` on project `sgnn-csp-2` could not refresh its token (`gcloud auth print-access-token` asked for `gcloud auth login`). There is therefore no list of entities with zero rows on the three days, and no new byte measurement.

After `gcloud auth login` for that account, with the project left on `sgnn-csp-2`:

```
.venv/bin/python scripts/phase2_gdelt_frozen_rerun.py --dry-run-first-slice
.venv/bin/python scripts/phase2_gdelt_frozen_rerun.py --pilot
.venv/bin/python scripts/phase2_gdelt_frozen_rerun.py --pilot --execute-pilot
```

The first command dry-runs 2016-11-14 through 2016-12-12 and does not execute it. The second dry-runs the three days 2016-11-14, 2020-03-16, and 2025-06-16. The third executes those three days only if each dry run is at most 10 GB. Results go to `data/interim/phase2/gdelt_frozen_pilot/`. Each job is appended to `eval/results/bq_ledger.jsonl` with purpose, project `sgnn-csp-2`, and the account.

The 128-slice loop is the same script without `--pilot`. It prints the loop and stops. `--execute-full` would run it. That flag was not passed. The loop is resumable: a non-empty file in `data/interim/phase2/gdelt_frozen_full/` is skipped. Each slice is dry-run first, refused above 10 GB, and refused if this project's own billed bytes would pass 1 TB. The October `sgnn-csp` baseline is not charged here. The previous 128 slices billed 435,140,165,632 bytes. A name filter does not reduce bytes billed, so that remains the standing projection until the new dry run is actually returned.

## 7. TweetsKB speed

DNS resolved. `month_2017-06` sits on Zenodo record 1765240, whose file list was empty and whose files endpoint returned 403. The test file is `month_2017-11.n3.gz` on record 1808741, 3,522,219,692 bytes, inside 2016-11 through 2020-12. Six parallel 1 MB range requests ran for 603.8 seconds, all answered 206, and transferred 843,055,104 bytes. The rate is 1.396 MB/s. Nothing was written to disk. The rate is above 1 MB/s, so a later download starts with 2016-11 through 2020-12. That download was not started. The partial `month_2013-10` file was left as it is.

## 8. HuffPost

The HuffPost news-category set is not an arm. Apple has 493 mentions in 10 years, 2 days at the 5-mention floor, and 0 events with the 14-of-28 baseline. Microsoft has 87, Tesla 76, Alphabet 530. Meta and Pinterest counts include "on Facebook" and "on Pinterest" boilerplate and are not brand events. The set is reserved for the Phase 3 hand-label pool: 1,137 articles naming Apple, Microsoft, Alphabet, or Tesla, 503 TECH and 148 BUSINESS. Phase 3 does not start.

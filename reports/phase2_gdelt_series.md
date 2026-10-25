# Arm B GDELT series

2026-10-17. The stored scan is 128 slices, 435,140,165,632 bytes billed, 27,346,316 articles, in `data/interim/phase2/gdelt_allowlist/`. This report uses those files only. No BigQuery job was run. No caliper was widened. No shift, mean difference, or estimated effect is reported. Phase 3 does not start.

Arm B news pair construction is **blocked**. The verdict is **NO-GO** until one frozen allow-list is scanned once. The reason is in section 1 and the pair table is in section 6.

## 1. Filter check

The ledger has no filter size on the executed scan and no one-day pilot of that scan. The entity list below is the titles and mids inside the 128 files. There are 93 distinct Wikipedia titles and 70 distinct mids. 24,185,703 articles match a node under the logged rule. The other 3,160,613 articles are in the files and match no logged title.

### Present, with mention counts

These are entity mentions, so one article can contribute more than one row. The series in section 2 counts each article once per node.

| Title | Mentions | Assigned node |
| --- | ---: | --- |
| YouTube | 5,402,626 | YouTube |
| Google | 4,823,024 | Alphabet |
| Apple_Inc. | 4,111,552 | Apple |
| Microsoft | 2,536,681 | Microsoft |
| Android_(operating_system) | 2,105,711 | Android |
| IPhone | 1,950,364 | iPhone |
| Microsoft_Windows | 502,807 | Windows |
| Microsoft_Azure | 196,267 | Azure |
| MacBook | 76,000 | MacBook |
| Tim_Cook | 222,462 | Apple CEO |
| Satya_Nadella | 81,991 | Microsoft CEO |
| IBM | 624,394 | IBM |
| Salesforce | 154,293 | CRM |
| Adobe_Inc. | 187,382 | ADBE |
| Oracle_Corporation | 392,486 | ORCL |
| Dell | 226,669 | DELL |
| Hewlett-Packard | 198,634 | HPQ |
| Logitech | 27,931 | LOGI |
| Samsung_Electronics | 606,796 | Samsung |
| Snapchat | 506,041 | SNAP |
| Amazon.com | 395,164 | AMZN |
| Nike,_Inc. | 513,178 | Nike |
| Chipotle_Mexican_Grill | 83,790 | Chipotle |
| Lowe's | 92,269 | Lowe's |
| T-Mobile_US | 78,408 | T-Mobile US |
| The_New_York_Times_Company | 78,750 | New York Times Co |
| The_Hershey_Company | 66,343 | Hershey |
| Colgate-Palmolive | 41,085 | Colgate-Palmolive |
| Mastercard | 258,959 | Mastercard |
| Chevron_Corporation | 312,933 | Chevron |
| NextEra_Energy | 35,579 | NextEra Energy |
| John_Deere | 131,712 | John Deere |
| Eli_Lilly_and_Company | 209,750 | Eli Lilly |
| Darden_Restaurants | 23,575 | Darden |
| Dish_Network | 55,325 | Dish Network |
| General_Mills | 75,732 | General Mills |
| Kellanova | 3,203 | Kellanova |
| Clorox | 40,285 | Clorox |
| Kimberly-Clark | 43,678 | Kimberly-Clark |
| Marathon_Petroleum | 31,228 | Marathon Petroleum |
| Valero_Energy | 51,866 | Valero |
| Duke_Energy | 128,143 | Duke Energy |
| Southern_Company | 30,759 | Southern Company |
| Amgen | 84,756 | Amgen |
| Vertex_Pharmaceuticals | 26,048 | Vertex |
| Hurley_International | 4,234 | Hurley International |
| Converse_(brand) | 21,229 | Converse |
| Umbro | 2,695 | Umbro |
| Tesla,_Inc. | 1,612,162 | Tesla, Arm A only |
| Tesla_Model_S | 83,845 | Model S, Arm A only |
| Tesla_Model_3 | 51,210 | Model 3, Arm A only |
| Elon_Musk | 1,996,813 | Tesla CEO, Arm A only |
| Ford_Motor_Company | 1,143,840 | F, Arm A only |
| General_Motors | 873,792 | GM, Arm A only |
| Toyota | 766,800 | TM, Arm A only |
| Nio_Inc. | 27,383 | NIO, Arm A only |

### In the files, and left unassigned

The logged rule assigns the logged title. A different title stays unassigned when the mid matches.

| Title | Scored documents | What the files show |
| --- | ---: | --- |
| Amazon_(company) | 4,481,723 | Every year 2017–2026. 2017: 148,892. 2018: 555,497. 2019: 545,050. 2020: 516,184. 2021: 387,369. 2022: 425,141. 2023: 600,050. 2024: 581,885. 2025: 504,927. 2026: 216,728. |
| Meta_Platforms | 738,060 | From 2021. 2021: 12,052. 2022: 139,174. 2023: 189,487. 2024: 163,540. 2025: 157,904. 2026: 75,903. |
| Snap_Inc. | 35,527 | Every year 2017–2026, between 1,861 and 6,429 scored documents a year. |
| Amazon | 51,366 | All in 2022. |
| Google_LLC | 43,172 | All in 2022. |
| HP_Inc. | 332 | 234 in 2018 and 98 in 2025. |

These document counts are articles carrying that title. They are not the daily series.

### Missing from the files

**(a) Control pool.** 160 of the 184 names are absent. The 24 names whose titles are in the files are the 12 candidate brands and the 12 candidate competitors in the table above. Their sectors are communication services (DISH, NYT, TMUS), consumer discretionary (CMG, DRI, LOW, NKE), financials (MA), health care (AMGN, LLY, VRTX), energy (CVX, MPC, VLO), utilities (DUK, NEE, SO), industrials (DE), and consumer staples (CL, CLX, GIS, HSY, K, KMB). No information-technology control and no communication-services control is present. EPAM has no English Wikipedia title in the 2026-10-12 snapshot, so a title filter cannot retrieve it.

The 160 absent tickers are: ACN, ADP, ADSK, AKAM, ANSS, BR, CDNS, CDW, CTSH, EPAM, FFIV, FTNT, INTU, IT, JKHY, MSI, NTAP, PAYX, SNPS, VRSN, CHTR, CMCSA, DIS, EA, FOXA, IPG, LUMN, NWSA, OMC, SIRI, T, TTWO, VZ, BKNG, CCL, EBAY, EXPE, HD, HLT, LVS, MAR, MCD, ROST, SBUX, TGT, TJX, YUM, AXP, BAC, BLK, C, CB, GS, JPM, MET, MMC, MS, PGR, PNC, SCHW, SPGI, USB, V, WFC, ABBV, ABT, BMY, CVS, DHR, GILD, ISRG, JNJ, MDT, MRK, PFE, SYK, TMO, UNH, ZTS, BKR, COP, DVN, EOG, EPD, HAL, KMI, OKE, OXY, PSX, SLB, WMB, XOM, AEE, AEP, AWK, D, ED, EIX, ES, EXC, PCG, PEG, SRE, WEC, XEL, BA, CAT, CSX, EMR, ETN, FDX, GD, HON, ITW, LMT, NOC, NSC, PH, RTX, UNP, UPS, WM, CHD, COST, KO, MDLZ, MO, PEP, PG, PM, SYY, WMT, APD, BALL, DD, DOW, ECL, FCX, IP, LIN, MLM, NEM, NUE, PPG, SHW, VMC, AMT, AVB, CCI, DLR, EQIX, EQR, EXR, O, PLD, PSA, SBAC, SPG, VICI, WELL.

**(b) CEOs and products.** Tim Cook, Satya Nadella, and Elon Musk are present. Larry Page and Sundar Pichai are absent. The allow-list had sent the concatenated title “Larry Page and Sundar Pichai”, and that string is also absent. iPhone, MacBook, Windows, Azure, Android, YouTube, Model S, and Model 3 are present. LinkedIn and LinkedIn Corporation are absent.

**(c) The 12 candidate brands, their named competitors, and Hurley, Converse, and Umbro are present.**

**(d) Study nodes.** Apple, Microsoft, Alphabet, iPhone, MacBook, Apple CEO, Windows, Azure, Microsoft CEO, YouTube, IBM, CRM, ADBE, ORCL, DELL, HPQ, LOGI, Samsung, SNAP, and AMZN are present under the logged titles. Meta, PINS, Alphabet CEO, and LinkedIn are absent under the logged titles. Tesla and its products, CEO, and competitors are present and stay out of Arm B.

No scan was rerun.

### Cheapest next scan

Freeze one allow-list, then run the 128 slices once. A name filter does not reduce bytes billed, so any rerun of this span costs about 435 GB again. `sgnn-csp-2` has 564,859,834,368 bytes left of the 1 TB October allowance, about 565 GB. That remainder holds one rerun and little else. The allowance resets on 1 November 2026.

The frozen list should contain the titles already assigned, the 160 missing control titles, `Larry_Page` and `Sundar_Pichai` as two titles, `LinkedIn_Corporation`, and `Pinterest`. EPAM stays off a title filter. The concatenated Alphabet CEO title stays off the list.

`Amazon_(company)`, `Meta_Platforms`, and `Snap_Inc.` are already stored. Accepting them is a title decision on this extract and adds no BigQuery bytes. They stay unassigned until that decision is logged. Putting them into the frozen list still does not make a second scan cheaper, because the control titles, the two Alphabet CEO titles, LinkedIn, and Pinterest are absent and the whole span has to be read again.

## 2. Series built from the stored files

The logged rule is the rule in `configs/gdelt_match_rule.json`: a Wikipedia title matches, and a mid matches only when the title is empty. A bare name never matches. A present different title is not overridden by the mid. Each article counts once per node.

Daily cells are in `data/interim/phase2/gdelt_series.sqlite`, table `daily`: `node`, `exclude_brand`, `day`, `document_count`, `scored_count`, `score_sum`. Source is `gdelt` and the arm is B for every row of this file. The Arm A database `data/interim/phase2/series.sqlite` was not opened.

Per-document rows are in `data/interim/phase2/gdelt_documents.jsonl.gz` (317 MB). Each line is the URL hash, the date, the score, and the pipe-separated study-node list. The hash is the document id. The node list is the co-mention exclusion list. Rows with `exclude_brand` set to Apple, Microsoft, or Alphabet drop articles in which that brand itself matched.

The score field is filled on the matched articles, so scored-document counts and document counts are equal in the unassigned-title check above. Empty scores would still be kept as unscored documents.

## 3. Precision audit, full span

Denominator: a mention whose title is the node’s logged title, or whose mid is listed for that node. Numerator: the title is the logged title. Empty-title mid matches are separate and were assigned. The final rule is the logged rule, unchanged, recorded as `full_span_audit` on 2026-10-17. `/m/0mgkg` does not assign `Amazon_(company)`.

Share of mentions on the logged page, by year:

| Node | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 | Total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Azure | 1.000 | 1.000 | 0.992 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.999 |
| Windows | 1.000 | 1.000 | 0.980 | 1.000 | 1.000 | 0.998 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.998 |
| Android | 1.000 | 1.000 | 0.990 | 1.000 | 1.000 | 1.000 | 0.908 | 1.000 | 1.000 | 1.000 | 1.000 | 0.988 |
| Model S | 1.000 | 1.000 | 0.964 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.995 |
| HPQ | 1.000 | 1.000 | 0.867 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.995 | 1.000 | 0.973 |
| SNAP | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| Apple | 1.000 | 1.000 | 0.991 | 1.000 | 1.000 | 0.999 | 0.909 | 0.982 | 1.000 | 1.000 | 1.000 | 0.989 |
| AMZN | 1.000 | 0.683 | 0.007 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.080 |
| Meta | — | — | — | — | — | — | — | — | — | — | — | — |

Meta has no audit rows: the logged title Facebook has 0 mentions and the rule lists no mid for Meta.

The shares below 0.98 are alias titles on the same mid. Apple in 2022 is the title `Apple` (31,075). Apple in 2023 is `Apple_logo` (9,238). Alphabet in 2022 is `Google_LLC` (43,172); Alphabet’s own total share is 0.989. Android in 2022 is `Android_(Betriebssystem)` (23,099). HPQ in 2018 is `Hewlett_Packard_Enterprise` (4,338), `Hewlett-Packard_Company` (836), and `HP_Inc.` (234). YouTube’s total share is 0.998; the 2018 remainder is `Youtube` (9,092). iPhone’s total share is 0.997; the 2018 remainder is `IPhones` (6,347). Azure’s 2018 remainder is `Azure_Services_Platform` (191). Model S in 2018 is `Ludicrous_Mode` (386). Samsung’s total share is 1.000 aside from 29 rows titled `SRBD` in 2018.

AMZN is the break. From 2019 through 2025 the logged title `Amazon.com` has 0 mentions. The mid `/m/0mgkg` sits on `Amazon_(company)`. Those rows were stored and were not assigned. Empty-title mid matches for AMZN are 3,673, of which 3,629 are in 2026, and those were assigned. SNAP’s assigned title `Snapchat` is on the logged page in every year. `Snap_Inc.` does not share that mid.

Bare-name errors, including the fruit, the river, the football club, and the benefits program, are not observable here. This extract has no bare-name rows.

## 4. Coverage

A cell is scored days / days with at least 14 scored documents. The span starts 2016-11-14, so 2016 has at most 48 days. 2026 has 169 days on the brands that appear every day through the last article slice. A candidate clears the scored-day bar at 14 or more scored days in total, and clears the dense bar at 14 or more dense days in total. Both marks are shown. No brand is added or dropped.

### Arm B study nodes that are in the series

| Node | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 | Total |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Apple | 48/48 | 363/363 | 360/360 | 365/365 | 366/366 | 365/365 | 337/336 | 362/362 | 366/366 | 348/348 | 169/169 | 3449/3448 |
| Microsoft | 48/48 | 363/363 | 362/362 | 365/365 | 366/366 | 365/365 | 365/365 | 365/365 | 366/366 | 348/348 | 169/169 | 3482/3482 |
| Alphabet | 48/48 | 363/363 | 360/360 | 365/365 | 366/366 | 365/365 | 365/352 | 365/365 | 366/366 | 348/348 | 169/169 | 3480/3467 |
| iPhone | 48/48 | 363/363 | 356/356 | 365/365 | 366/366 | 365/365 | 365/365 | 365/365 | 366/366 | 348/348 | 169/169 | 3476/3476 |
| MacBook | 48/42 | 362/232 | 359/252 | 322/169 | 366/145 | 365/143 | 365/235 | 365/329 | 366/357 | 348/303 | 169/158 | 3435/2365 |
| Apple CEO | 48/48 | 363/352 | 360/349 | 365/350 | 366/327 | 365/281 | 365/294 | 358/321 | 366/318 | 348/335 | 169/160 | 3473/3135 |
| Windows | 48/48 | 363/362 | 358/357 | 365/365 | 366/366 | 365/365 | 365/365 | 365/365 | 366/366 | 348/348 | 169/169 | 3478/3476 |
| Azure | 48/46 | 363/349 | 360/328 | 365/336 | 366/331 | 365/316 | 365/339 | 365/361 | 366/365 | 348/342 | 169/169 | 3480/3282 |
| Microsoft CEO | 48/43 | 362/158 | 360/149 | 362/155 | 363/117 | 363/83 | 354/71 | 365/240 | 366/216 | 348/224 | 169/128 | 3460/1584 |
| YouTube | 48/48 | 363/363 | 357/357 | 365/365 | 366/366 | 365/365 | 365/365 | 365/365 | 366/366 | 348/348 | 169/169 | 3477/3477 |
| IBM | 48/48 | 363/362 | 360/360 | 365/365 | 366/366 | 365/365 | 365/365 | 365/365 | 366/366 | 348/348 | 169/169 | 3480/3479 |
| ORCL | 48/48 | 363/362 | 358/355 | 365/357 | 366/360 | 365/364 | 332/330 | 365/365 | 366/366 | 348/348 | 169/169 | 3445/3424 |
| CRM | 0/0 | 0/0 | 3/3 | 4/3 | 366/354 | 365/356 | 336/322 | 365/361 | 366/365 | 348/347 | 169/169 | 2322/2280 |
| ADBE | 0/0 | 0/0 | 77/76 | 365/346 | 366/358 | 365/362 | 333/331 | 365/365 | 366/366 | 348/348 | 146/145 | 2731/2697 |
| DELL | 48/48 | 363/361 | 359/356 | 365/361 | 366/358 | 365/347 | 335/330 | 365/364 | 366/343 | 344/143 | 169/169 | 3445/3180 |
| HPQ | 48/48 | 363/362 | 323/321 | 365/360 | 366/347 | 364/194 | 365/283 | 359/45 | 366/69 | 313/260 | 168/141 | 3400/2430 |
| LOGI | 48/23 | 362/94 | 360/140 | 361/99 | 365/96 | 356/52 | 321/50 | 299/43 | 252/6 | 272/0 | 142/0 | 3138/603 |
| Samsung | 48/48 | 363/363 | 362/339 | 365/297 | 366/301 | 365/297 | 365/299 | 365/356 | 366/366 | 348/348 | 169/169 | 3482/3183 |
| SNAP | 48/48 | 363/363 | 362/362 | 365/365 | 366/366 | 360/359 | 359/358 | 365/365 | 366/366 | 348/348 | 169/169 | 3471/3469 |
| AMZN | 48/48 | 271/271 | 3/3 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | 5/5 | 327/327 |

AMZN clears both bars on the total and has zero scored days in 2019, 2020, 2021, 2022, 2023, 2024, and 2025. That is the logged title `Amazon.com`. Meta, PINS, Alphabet CEO, and LinkedIn have no series.

### Twelve candidate brands

All twelve clear both bars.

| Brand | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 | Total | Scored bar | Dense bar |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Nike | 48/48 | 363/361 | 360/359 | 365/365 | 366/366 | 365/365 | 332/322 | 343/323 | 366/366 | 348/348 | 169/169 | 3425/3392 | clears | clears |
| Chipotle | 48/43 | 363/329 | 355/272 | 365/265 | 365/173 | 365/175 | 365/183 | 364/179 | 366/194 | 345/144 | 169/62 | 3470/2019 | clears | clears |
| Lowe's | 48/43 | 225/191 | 317/307 | 365/339 | 366/346 | 365/304 | 77/70 | 0/0 | 37/35 | 252/194 | 169/108 | 2221/1937 | clears | clears |
| T-Mobile US | 48/36 | 362/294 | 361/278 | 360/212 | 338/98 | 339/26 | 344/68 | 365/186 | 366/171 | 347/141 | 169/102 | 3399/1612 | clears | clears |
| New York Times Co | 45/2 | 331/67 | 303/132 | 327/29 | 366/289 | 365/113 | 363/145 | 365/100 | 366/70 | 347/23 | 166/34 | 3344/1004 | clears | clears |
| Hershey | 48/34 | 361/189 | 357/201 | 364/203 | 366/160 | 360/66 | 331/123 | 365/236 | 366/253 | 348/187 | 169/65 | 3435/1717 | clears | clears |
| Colgate-Palmolive | 47/18 | 362/170 | 359/154 | 362/147 | 363/57 | 346/29 | 349/60 | 360/102 | 365/91 | 344/61 | 163/20 | 3420/909 | clears | clears |
| Mastercard | 0/0 | 0/0 | 237/237 | 365/365 | 366/366 | 365/365 | 365/365 | 365/365 | 366/366 | 348/348 | 169/169 | 2946/2946 | clears | clears |
| Chevron | 48/48 | 363/359 | 357/355 | 365/363 | 366/366 | 365/365 | 365/365 | 361/360 | 366/366 | 348/348 | 169/169 | 3473/3464 | clears | clears |
| NextEra Energy | 46/5 | 353/63 | 336/56 | 361/96 | 362/61 | 365/23 | 365/81 | 364/97 | 366/113 | 345/94 | 167/41 | 3430/730 | clears | clears |
| John Deere | 48/47 | 362/355 | 361/353 | 365/351 | 366/314 | 365/327 | 365/343 | 365/349 | 366/354 | 348/313 | 169/128 | 3480/3234 | clears | clears |
| Eli Lilly | 48/48 | 362/341 | 352/304 | 365/309 | 366/337 | 365/309 | 365/325 | 365/355 | 366/365 | 348/345 | 169/169 | 3471/3207 | clears | clears |

New York Times Co clears both bars: 3,344 scored days and 1,004 dense days. Hershey clears both bars: 3,435 scored days and 1,717 dense days. The decision is open.

### Candidate competitors and dated subsidiaries

| Node | Total scored/dense | Scored bar | Dense bar |
| --- | --- | --- | --- |
| Darden | 3122/284 | clears | clears |
| Dish Network | 3471/1381 | clears | clears |
| General Mills | 3470/2016 | clears | clears |
| Kellanova | 254/52 | clears | clears |
| Clorox | 3422/693 | clears | clears |
| Kimberly-Clark | 3434/954 | clears | clears |
| Marathon Petroleum | 3357/526 | clears | clears |
| Valero | 3466/1184 | clears | clears |
| Duke Energy | 3480/2674 | clears | clears |
| Southern Company | 3381/451 | clears | clears |
| Amgen | 3476/2358 | clears | clears |
| Vertex | 3327/344 | clears | clears |
| Hurley International | 1488/27 | clears | clears |
| Converse | 1061/691 | clears | clears |
| Umbro | 1314/8 | clears | does not clear |

Converse’s days are all in 2023–2026. Hurley has 27 dense days, spread thinly: 11 in 2017 and 6 in each of 2018 and 2019. Umbro has 8 dense days. None of these three is a graph edge.

Yearly scored/dense for the subsidiaries: Hurley 36/0, 297/11, 246/6, 224/6, 165/0, 119/1, 50/1, 108/0, 118/0, 113/2, 12/0. Converse 0/0 through 2022, then 178/158, 366/305, 348/184, 169/44. Umbro 23/2, 184/1, 226/2, 212/2, 194/1, 131/0, 141/0, 95/0, 70/0, 14/0, 24/0.

Tesla, Model S, Model 3, Tesla CEO, Ford, GM, Toyota, and NIO are in the extract and are excluded from the Arm B feasibility below.

## 5. Planning SD

Blocked. The placebo procedure is seed 3, up to 20 eligible non-event dates per focal brand, and a brand with fewer than 5 eligible dates is excluded. Apple has 1,394 eligible dates, Microsoft 1,427, and Alphabet 1,481, so the date side is ready. The match side needs sector controls. No information-technology or communication-services control is in the extract, so no SD was computed.

SESOI 0.05 and the 0.20 mean caliper were not converted. There is no GDELT SD to divide by. Nothing is frozen and nothing is logged as proposed.

## 6. Usable-pair feasibility

Same event rule as Arm A: absolute z at least 2 against a trailing 28-day baseline with at least 14 observed days, at least 5 scored documents on the day, refractory period 8 days. A window is usable when the pre window [−7, −1] and the post window [0, 7] each have at least 3 scored days. Co-mention exclusion drops articles that matched the brand. Positive targets are the ownership, product, and CEO edges: Apple to iPhone, MacBook, and Apple CEO; Microsoft to LinkedIn, Windows, Azure, and Microsoft CEO; Alphabet to YouTube and Alphabet CEO. Android has no such edge. Tesla is out of Arm B. The control column is empty because the control series are missing. H1 and H2 need 10 matched pairs. H4 needs 5 events and a matched pair.

### Full span

| Ecosystem | Brand events | Positive, both windows | Positive, after co-mention | Competitor, both windows | Competitor, after co-mention | Matched pairs |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Apple | 151 | 151 | 151 | 151 | 151 | blocked |
| Microsoft | 151 | 151 | 151 | 151 | 151 | blocked |
| Alphabet | 150 | 150 | 150 | 149 | 149 | blocked |

| Target | Both windows | After co-mention |
| --- | ---: | ---: |
| iPhone | 151 | 151 |
| MacBook | 150 | 150 |
| Apple CEO | 151 | 147 |
| LinkedIn | 0 | 0 |
| Windows | 151 | 151 |
| Azure | 151 | 151 |
| Microsoft CEO | 151 | 70 |
| YouTube | 150 | 150 |
| Alphabet CEO | 0 | 0 |

### Overlap, 2016-11-14 through 2020-12-31

| Ecosystem | Brand events | Positive, both windows | Positive, after co-mention | Competitor, both windows | Competitor, after co-mention | Matched pairs |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Apple | 67 | 67 | 67 | 67 | 67 | blocked |
| Microsoft | 60 | 60 | 60 | 60 | 60 | blocked |
| Alphabet | 67 | 67 | 67 | 67 | 67 | blocked |

On the overlap, iPhone is 67/67, MacBook 66/66, Apple CEO 67/67, LinkedIn 0/0, Windows 60/60, Azure 60/60, Microsoft CEO 60/14, YouTube 67/67, and Alphabet CEO 0/0.

Brand-event counts are above 5 on both spans, for all three ecosystems. Matched pairs cannot be counted. H1, both H2 classes, and H4 stay unestimated. Arm B news is **NO-GO**. It needs the 160 missing control titles in one scan of a frozen allow-list. It also needs a logged decision on `Amazon_(company)` and `Meta_Platforms` before Alphabet’s competitor class can include those pages, and it needs Larry Page, Sundar Pichai, LinkedIn, and Pinterest if those nodes are to enter the series.

## 7. Still owed

### TweetsKB

Parts 1–9 are 97 files and 367,170,428,974 bytes, CC BY 4.0. One file was timed: `month_2013-10.n3.gz`, 3,028,700,401 bytes. The transfer averaged about 42,048 bytes per second, about 20 hours for that file and about 101 days for the nine parts. It then stopped. The file on disk is the first 10,485,760 bytes, at `data/interim/tweetskb_raw/month_2013-10.n3.gz`. It was not resumed. The other 96 files were not started. `scripts/phase2_tweetskb_stream.py` has not been run.

On the 5 percent SPARQL sample, seed 3, 20 dates each for AAPL, MSFT, and GOOGL, there were 60 placebo dates and 0 matched controls. The controls do not have 14 observed days inside any 28-day window. That includes names with many days on the sample, such as ACN with 718 days, IT with 769, DIS with 1,138, and TMUS with 990. The baseline was not relaxed and the 5 percent sample was not scaled up. The TweetsKB planning SD is not frozen. Parts 10–12 were not downloaded.

### Competitor edges

The 16 edges are the confirmed study list. Each has sign −1, direction brand to named competitor, `reverse_asserted` false, and `property_id` null. The provenance on each one is: “Study list in configs/phase2_nodes.json. No Wikidata property labeled competitor was verified. P710 participant was rejected.” Confirmed 2026-10-13. Samsung was added the same day after its coverage check. The pairs are Apple–DELL, Apple–HPQ, Apple–LOGI, Apple–Samsung, Microsoft–ORCL, Microsoft–CRM, Microsoft–IBM, Microsoft–ADBE, Alphabet–Meta, Alphabet–AMZN, Alphabet–SNAP, Alphabet–PINS, Tesla–F, Tesla–GM, Tesla–TM, and Tesla–NIO.

Proposed rule, not applied: an edge is added only when, before any outcome, the user confirms that named pair or Wikidata states the relation on a property that has been logged. Sharing a sector, sitting inside the two-hop neighborhood, or looking like an obvious peer does not create an edge. The seven undated candidate pairs, and Home Depot, Visa, and Caterpillar, stay out until a source that states them is approved.

### Two-hop exclusion

Exclusion is a non-deprecated path of length at most 2 from the 38 study-node Wikidata ids. That neighborhood contains 1,445 ids. Nike, Lowe’s, Mastercard, John Deere, and the New York Times Company are outside it.

Home Depot, Visa, and Caterpillar are inside it. Home Depot reaches Apple through The Vanguard Group (`Q864407`–`Q849363`–`Q312`). Visa reaches Apple through the same Vanguard id (`Q328840`–`Q849363`–`Q312`). Caterpillar reaches GM through Electro-Motive Diesel (`Q459965`–`Q568501`–`Q81965`). Adding Home Depot would newly block LOW. Adding Visa would newly block MA. Adding Caterpillar would newly block no further control ticker. They were not added.

## 8. Files and checksums

`data/interim/phase2/gdelt_allowlist/` has 128 gzip files. The checksum list is `eval/results/gdelt_allowlist_sha256.txt`, 128 lines, each `sha256`, filename, and size in bytes. The sizes sum to 447,753,963, the same total as the scan log. The manifest’s own SHA-256 is `b466aea1c0028006497eb9d4b2939cac128c9daa15ed2e34896a43069087e84c`.

The title inventory is `eval/results/phase2_gdelt_filter_inventory.json`. The precision counts are `eval/results/phase2_gdelt_precision.json`. The coverage and funnel counts are `eval/results/phase2_gdelt_tables.json`.

Work stops here.

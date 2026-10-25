# Phase 4 outcomes

Seeds: bootstrap 0, pair permutation 1, rewiring 2, placebo 3. H3 was not estimated in this file's original run. On 2026-10-24 the Holm column was set to the final family-of-8 values in `reports/phase5_outcomes.md`. The earlier family-of-6 values are in the superseded column. Effects, intervals, raw p-values, pair counts, and decisions are unchanged. `eval/results/phase4_outcomes.json` is unchanged. The pooled Arm A SD is not a source SD.

No git repository. File hashes:

- `configs/phase0.json` `213c5439f987a9b2d629b7fad575a2a692f45a0bacdadcbef461ac43d0fac6d7`
- `configs/phase4_series.json` `5788dcb470c75114ac0f6ebdda200c423a6b5d609800fe2744d0723340100173`
- `configs/frozen_sha256.json` `af877bc55c08e93f553de848c3ad4622420364d4e03432b9c2c0fecd396ee7ab`
- `scripts/phase4_analysis.py` `1ac1d7d566436dedb85a963bfef8ca4b6480bd6b33604fa279161fb7aa9aac99`
- `scripts/phase4_outcome_run.py` `98b0b46076c5dfde4529c854b6dfb49a04d150ccc32792500a728f6363cc7104`
- `data/interim/phase3/final_scorer/model.pt` `41d769b3d5a292de5f41c2908ae44020cb9570d223b7523edca9a226cd692559`

## Arm A

The Holm column is the final family of 8 from `reports/phase5_outcomes.md`. The family-of-6 adjustment is superseded. The family uses `news_joined` for H1 and H2. H4 compares that news series with the arm's social series. Headline, social H1 and H2, and the Tesla-excluded rows are not in the family.

| Source | Test | Pairs | Events | Effect | 95% interval | Permutation p | Rewiring p | Placebo rate | Holm p | Family-of-6 Holm p (superseded) | SESOI interval | MDE | Half-width |
|---|---|---:|---:|---:|---|---:|---:|---:|---:|---:|---|---:|---:|
| news_joined | H1 | 49 | 37 | -0.0189114 | [-0.0974513, 0.0738195] | 0.637363 | 0.546906 | 0 | 1 | 1 | outside | 0.124108 | 0.0868247 |
| news_joined | H1 rewiring | 49 | 37 | -0.0189114 | [-0.0974513, 0.0738195] |  | 0.546906 | 0 | 1 | 1 | outside | 0.124108 | 0.0868247 |
| news_joined | H2 positive | 10 | 10 | -0.161894 | [-0.360786, -0.020363] | 0.0719281 |  |  | 0.575425 | 0.431568 | outside | 0.238726 | 0.167011 |
| news_joined | H2 competitor | 39 | 36 | -0.0230045 | [-0.129584, 0.0763916] | 0.642358 |  |  | 1 | 1 | outside | 0.12582 | 0.0880224 |
| news_headline | H1 | 41 | 27 | 0.0254837 | [-0.0516204, 0.101783] | 0.401598 | 0.588822 | 0 |  |  | outside | 0.107748 | 0.0753799 |
| news_headline | H1 rewiring | 41 | 27 | 0.0254837 | [-0.0516204, 0.101783] |  | 0.588822 | 0 |  |  | outside | 0.107748 | 0.0753799 |
| news_headline | H2 positive | 8 | 8 |  |  |  |  |  |  |  |  | 0.197947 | 0.138482 |
| news_headline | H2 competitor | 33 | 27 | -0.0846849 | [-0.149646, -0.0154696] | 0.011988 |  |  |  |  | outside | 0.107748 | 0.0753799 |
| social | H1 | 565 | 445 | -0.021558 | [-0.0457013, 0.00216357] | 0.0709291 | 0.762475 | 0 |  |  | inside | 0.0376826 | 0.0263624 |
| social | H1 rewiring | 565 | 445 | -0.021558 | [-0.0457013, 0.00216357] |  | 0.762475 | 0 |  |  | inside | 0.0376826 | 0.0263624 |
| social | H2 positive | 39 | 37 | 0.0613806 | [-0.0643639, 0.199362] | 0.368631 |  |  |  |  | outside | 0.130683 | 0.0914249 |
| social | H2 competitor | 526 | 439 | -0.0131061 | [-0.0432786, 0.0163357] | 0.376623 |  |  |  |  | inside | 0.0379393 | 0.026542 |
| news minus social | H4 magnitude |  | 37 | 0.00264656 | [-0.0848997, 0.0963307] | 0.959041 |  |  | 1 | 1 | outside | 0.124108 | 0.0868247 |
| news minus social | H4 lag |  | 37 | 0.431764 | [-0.3542, 1.27656] | 0.306693 |  |  | 1 | 1 | outside | 0.124108 | 0.0868247 |

H1 decision on `news_joined`: method failed.
H2 positive decision: not supported. H2 competitor decision: not supported.
H4 magnitude decision: not supported. H4 lag decision: not supported.
Balance news_joined: valid=False, SMD baseline mean 0.06109604458199992, SD 0.0757819420478066, log mention 0.4400205641910798, log popularity 0.24695932282559196.
Balance news_headline: valid=False, SMD baseline mean 0.09633861647243859, SD 0.06290628238275192, log mention 0.5540745037767206, log popularity 0.2841665776022664.
Balance social: valid=False, SMD baseline mean 0.05270217445945535, SD 0.08909994548992826, log mention 0.08918118514888033, log popularity 0.6547375534316467.

Tesla-excluded sensitivity, not a second Holm family.

| Source | Test | Pairs | Events | Effect | 95% interval | Permutation p | Rewiring p |
|---|---|---:|---:|---:|---|---:|---:|
| news | H1 | 29 | 27 | 0.043471 | [-0.0686135, 0.160911] | 0.470529 | 0.281437 |
| news | H2 positive | 2 | 2 |  |  |  |  |
| news | H2 competitor | 27 | 26 | -0.0526201 | [-0.175181, 0.0681785] | 0.410589 |  |
| social | H1 | 399 | 323 | -0.0306658 | [-0.0595578, -0.00236266] | 0.025974 | 0.321357 |
| social | H2 positive | 5 | 5 |  |  |  |  |
| social | H2 competitor | 394 | 321 | 0.00288868 | [-0.0276332, 0.0379912] | 0.854146 |  |

## Arm B

The Holm column is the final family of 8 from `reports/phase5_outcomes.md`. The family-of-6 adjustment is superseded. The family uses `gdelt` for H1 and H2. H4 compares that news series with the arm's social series. TweetsKB H1 and H2 are not in the family.

| Source | Test | Pairs | Events | Effect | 95% interval | Permutation p | Rewiring p | Placebo rate | Holm p | Family-of-6 Holm p (superseded) | SESOI interval | MDE | Half-width |
|---|---|---:|---:|---:|---|---:|---:|---:|---:|---:|---|---:|---:|
| gdelt | H1 | 2191 | 1251 | 0.00317244 | [0.00144079, 0.00495438] | 0.001998 | 0.576375 | 0 | 0.015984 | 0.011988 | inside | 0.00395844 | 0.00276929 |
| gdelt | H1 rewiring | 2191 | 1251 | 0.00317244 | [0.00144079, 0.00495438] |  | 0.576375 | 0 | 1 | 0.842158 | inside | 0.00395844 | 0.00276929 |
| gdelt | H2 positive | 412 | 290 | 0.00787135 | [0.00106105, 0.014996] | 0.032967 |  |  | 0.20979 | 0.164835 | inside | 0.00822155 | 0.00575172 |
| gdelt | H2 competitor | 1779 | 1250 | -0.00122584 | [-0.00356668, 0.00119929] | 0.280719 |  |  | 1 | 0.842158 | inside | 0.00396002 | 0.0027704 |
| tweetskb | H1 | 283 | 148 | 0.000284872 | [-0.00573159, 0.00615575] | 0.92008 | 0.976939 | 0 |  |  | inside | 0.0135727 | 0.00949533 |
| tweetskb | H1 rewiring | 283 | 148 | 0.000284872 | [-0.00573159, 0.00615575] |  | 0.976939 | 0 |  |  | inside | 0.0135727 | 0.00949533 |
| tweetskb | H2 positive | 119 | 90 | -0.00614552 | [-0.0169776, 0.00433141] | 0.327672 |  |  |  |  | inside | 0.0174051 | 0.0121764 |
| tweetskb | H2 competitor | 164 | 146 | -0.00549782 | [-0.0159288, 0.00419737] | 0.275724 |  |  |  |  | inside | 0.0136653 | 0.00956015 |
| news minus social | H4 magnitude |  | 148 | 0.00288757 | [-0.00338391, 0.00884224] | 0.351648 |  |  | 1 | 0.842158 | inside | 0.0115086 | 0.0080513 |
| news minus social | H4 lag |  | 148 | 0.359912 | [-0.0332138, 0.737327] | 0.0789211 |  |  | 0.394605 | 0.315684 | outside | 0.0115086 | 0.0080513 |

H1 decision on `gdelt`: method failed.
H2 positive decision: not supported. H2 competitor decision: not supported.
H4 magnitude decision: not supported. H4 lag decision: not supported.
Balance gdelt: valid=False, SMD baseline mean 0.17051849880301814, SD 0.12779486629928694, log mention 0.044628732356767474, log popularity 0.9512276625627908.
Balance tweetskb: valid=False, SMD baseline mean 0.7468968382118594, SD 0.09536927708681732, log mention 0.08148636761481036, log popularity 0.9456918688363153.


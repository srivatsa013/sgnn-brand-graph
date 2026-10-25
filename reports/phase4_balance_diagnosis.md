# Phase 4 balance diagnosis

The confirmatory tests were not rerun and `eval/results/phase4_outcomes.json` was not replaced. Matched pairs were not stored in that file, so the SMDs below were recomputed on pairs rebuilt with the unchanged matcher. Every tight-caliper and split row is exploratory and is outside the Holm family. The named-in-text split is computed for the restricted news series only. Social, GDELT, and TweetsKB day cells have no document text, so a zero in those named rows means the split is not available.

H1 is method failed when `h1_decision` reaches line 84 because `balance_valid` is false. `balance` line 470 sets `valid` false when any absolute SMD is above 0.20. The SMD is the absolute difference of means divided by the square root of the average of the two sample variances, divisor n−1.

## news_joined

Stored and rebuilt SMDs agree: True. Criteria above 0.20: log_mention, log_popularity.

| Covariate | Stored SMD | Rebuilt SMD | Independent SMD |
|---|---:|---:|---:|
| baseline_mean | 0.061096 | 0.061096 | 0.061096 |
| baseline_sd | 0.0757819 | 0.0757819 | 0.0757819 |
| log_mention | 0.440021 | 0.440021 | 0.440021 |
| log_popularity | 0.246959 | 0.246959 | 0.246959 |

Mention-gap median 0.164553, 90th percentile 0.495009. Popularity-gap median 0.666479, 90th percentile 1.03231. Pairs 49.

Exploratory re-match, mention caliper ln 1.5 and popularity caliper ln 1.5.

| Test | Pairs | Events | Effect | 95% interval | Permutation p | Rewiring p | SESOI band | SMD mean | SMD SD | SMD mention | SMD popularity |
|---|---:|---:|---:|---|---:|---:|---|---:|---:|---:|---:|
| exploratory H1 | 18 | 16 | -0.0510934 | [-0.163602, 0.0541581] | 0.371628 | 0.269461 | outside | 0.432784 | 0.207394 | 0.184301 | 0.00415111 |
| exploratory H2_positive | 1 | 1 |  |  |  |  |  | 0.432784 | 0.207394 | 0.184301 | 0.00415111 |
| exploratory H2_competitor | 17 | 16 | -0.0178813 | [-0.13726, 0.0992206] | 0.738262 | 0.825651 | outside | 0.432784 | 0.207394 | 0.184301 | 0.00415111 |

Exploratory splits of the original matched pairs. A cell under 10 pairs is not tested.

| Split | Test | Pairs | Effect | 95% interval | Permutation p | SESOI band |
|---|---|---:|---:|---|---:|---|
| exploratory edge_positive | H1 | 10 | -0.112049 | [-0.241599, 0.0932585] | 0.267732 | outside |
| exploratory edge_positive | H2_positive | 10 | -0.161894 | [-0.360786, -0.020363] | 0.0719281 | outside |
| exploratory edge_positive | H2_competitor | 0 |  |  |  |  |
| exploratory edge_competitor | H1 | 39 | 0.00497003 | [-0.0925638, 0.102435] | 0.918082 | outside |
| exploratory edge_competitor | H2_positive | 0 |  |  |  |  |
| exploratory edge_competitor | H2_competitor | 39 | -0.0230045 | [-0.129584, 0.0763916] | 0.642358 | outside |
| exploratory tercile_1 | H1 | 13 | 0.0830124 | [-0.0905077, 0.277767] | 0.425574 | outside |
| exploratory tercile_1 | H2_positive | 1 |  |  |  |  |
| exploratory tercile_1 | H2_competitor | 12 | -0.138871 | [-0.326016, 0.0291349] | 0.156843 | outside |
| exploratory tercile_2 | H1 | 15 | -0.0630764 | [-0.182345, 0.0358643] | 0.255744 | outside |
| exploratory tercile_2 | H2_positive | 1 |  |  |  |  |
| exploratory tercile_2 | H2_competitor | 14 | 0.00598112 | [-0.11783, 0.100874] | 0.911089 | outside |
| exploratory tercile_3 | H1 | 21 | -0.0504607 | [-0.166828, 0.10657] | 0.490509 | outside |
| exploratory tercile_3 | H2_positive | 8 |  |  |  |  |
| exploratory tercile_3 | H2_competitor | 13 | 0.0527342 | [-0.169046, 0.275185] | 0.639361 | outside |
| exploratory named | H1 | 41 | -0.0337947 | [-0.116109, 0.057586] | 0.454545 | outside |
| exploratory named | H2_positive | 9 |  |  |  |  |
| exploratory named | H2_competitor | 32 | -0.0369903 | [-0.136882, 0.0564291] | 0.454545 | outside |
| exploratory not_named | H1 | 8 |  |  |  |  |
| exploratory not_named | H2_positive | 1 |  |  |  |  |
| exploratory not_named | H2_competitor | 7 |  |  |  |  |

## news_headline

Stored and rebuilt SMDs agree: True. Criteria above 0.20: log_mention, log_popularity.

| Covariate | Stored SMD | Rebuilt SMD | Independent SMD |
|---|---:|---:|---:|
| baseline_mean | 0.0963386 | 0.0963386 | 0.0963386 |
| baseline_sd | 0.0629063 | 0.0629063 | 0.0629063 |
| log_mention | 0.554075 | 0.554075 | 0.554075 |
| log_popularity | 0.284167 | 0.284167 | 0.284167 |

Mention-gap median 0.203125, 90th percentile 0.653602. Popularity-gap median 0.661398, 90th percentile 0.721318. Pairs 41.

Exploratory re-match, mention caliper ln 1.5 and popularity caliper ln 1.5.

| Test | Pairs | Events | Effect | 95% interval | Permutation p | Rewiring p | SESOI band | SMD mean | SMD SD | SMD mention | SMD popularity |
|---|---:|---:|---:|---|---:|---:|---|---:|---:|---:|---:|
| exploratory H1 | 19 | 16 | 0.0559841 | [-0.0304555, 0.167632] | 0.271728 | 0.403194 | outside | 0.34889 | 0.0863815 | 0.167848 | 0.0178072 |
| exploratory H2_positive | 5 | 5 |  |  |  |  |  | 0.34889 | 0.0863815 | 0.167848 | 0.0178072 |
| exploratory H2_competitor | 14 | 13 | -0.0857203 | [-0.195349, 0.0158348] | 0.12987 | 0.322 | outside | 0.34889 | 0.0863815 | 0.167848 | 0.0178072 |

Exploratory splits of the original matched pairs. A cell under 10 pairs is not tested.

| Split | Test | Pairs | Effect | 95% interval | Permutation p | SESOI band |
|---|---|---:|---:|---|---:|---|
| exploratory edge_positive | H1 | 8 |  |  |  |  |
| exploratory edge_positive | H2_positive | 8 |  |  |  |  |
| exploratory edge_positive | H2_competitor | 0 |  |  |  |  |
| exploratory edge_competitor | H1 | 33 | 0.00264904 | [-0.0702761, 0.0723834] | 0.935065 | outside |
| exploratory edge_competitor | H2_positive | 0 |  |  |  |  |
| exploratory edge_competitor | H2_competitor | 33 | -0.0846849 | [-0.149646, -0.0154696] | 0.011988 | outside |
| exploratory tercile_1 | H1 | 11 | -0.0443199 | [-0.198083, 0.0942842] | 0.594406 | outside |
| exploratory tercile_1 | H2_positive | 0 |  |  |  |  |
| exploratory tercile_1 | H2_competitor | 11 | -0.0933139 | [-0.1878, -0.00281687] | 0.0939061 | outside |
| exploratory tercile_2 | H1 | 13 | 0.0654584 | [-0.078319, 0.220815] | 0.325674 | outside |
| exploratory tercile_2 | H2_positive | 2 |  |  |  |  |
| exploratory tercile_2 | H2_competitor | 11 | -0.0829516 | [-0.202502, 0.0585983] | 0.195804 | outside |
| exploratory tercile_3 | H1 | 17 | 0.0400819 | [-0.0330905, 0.12348] | 0.236763 | outside |
| exploratory tercile_3 | H2_positive | 6 |  |  |  |  |
| exploratory tercile_3 | H2_competitor | 11 | -0.077789 | [-0.188012, 0.0318249] | 0.194805 | outside |
| exploratory named | H1 | 33 | 0.00329236 | [-0.0666921, 0.0639028] | 0.919081 | outside |
| exploratory named | H2_positive | 6 |  |  |  |  |
| exploratory named | H2_competitor | 27 | -0.0765169 | [-0.134715, -0.0210058] | 0.022977 | outside |
| exploratory not_named | H1 | 8 |  |  |  |  |
| exploratory not_named | H2_positive | 2 |  |  |  |  |
| exploratory not_named | H2_competitor | 6 |  |  |  |  |

## social

Stored and rebuilt SMDs agree: True. Criteria above 0.20: log_popularity.

| Covariate | Stored SMD | Rebuilt SMD | Independent SMD |
|---|---:|---:|---:|
| baseline_mean | 0.0527022 | 0.0527022 | 0.0527022 |
| baseline_sd | 0.0890999 | 0.0890999 | 0.0890999 |
| log_mention | 0.0891812 | 0.0891812 | 0.0891812 |
| log_popularity | 0.654738 | 0.654738 | 0.654738 |

Mention-gap median 0.300433, 90th percentile 0.593615. Popularity-gap median 0.465363, 90th percentile 0.955511. Pairs 565.

Exploratory re-match, mention caliper ln 1.5 and popularity caliper ln 1.5.

| Test | Pairs | Events | Effect | 95% interval | Permutation p | Rewiring p | SESOI band | SMD mean | SMD SD | SMD mention | SMD popularity |
|---|---:|---:|---:|---|---:|---:|---|---:|---:|---:|---:|
| exploratory H1 | 197 | 189 | -0.0400996 | [-0.0831442, 1.05214e-05] | 0.0789211 | 0.227545 | outside | 0.068419 | 0.0852155 | 0.00767055 | 0.120649 |
| exploratory H2_positive | 7 | 7 |  |  |  |  |  | 0.068419 | 0.0852155 | 0.00767055 | 0.120649 |
| exploratory H2_competitor | 190 | 187 | -0.0560999 | [-0.0995364, -0.0140671] | 0.015984 | 0.139721 | outside | 0.068419 | 0.0852155 | 0.00767055 | 0.120649 |

Exploratory splits of the original matched pairs. A cell under 10 pairs is not tested.

| Split | Test | Pairs | Effect | 95% interval | Permutation p | SESOI band |
|---|---|---:|---:|---|---:|---|
| exploratory edge_positive | H1 | 39 | 0.000974671 | [-0.131049, 0.129813] | 0.984016 | outside |
| exploratory edge_positive | H2_positive | 39 | 0.0613806 | [-0.0643639, 0.199362] | 0.368631 | outside |
| exploratory edge_positive | H2_competitor | 0 |  |  |  |  |
| exploratory edge_competitor | H1 | 526 | -0.0232286 | [-0.0460466, 0.0011852] | 0.042957 | inside |
| exploratory edge_competitor | H2_positive | 0 |  |  |  |  |
| exploratory edge_competitor | H2_competitor | 526 | -0.0131061 | [-0.0432786, 0.0163357] | 0.376623 | inside |
| exploratory tercile_1 | H1 | 167 | -0.0520371 | [-0.0946224, -0.0107971] | 0.013986 | outside |
| exploratory tercile_1 | H2_positive | 0 |  |  |  |  |
| exploratory tercile_1 | H2_competitor | 167 | -0.0277299 | [-0.0741416, 0.0242664] | 0.273726 | outside |
| exploratory tercile_2 | H1 | 186 | -0.00688982 | [-0.0517332, 0.0343197] | 0.74026 | outside |
| exploratory tercile_2 | H2_positive | 4 |  |  |  |  |
| exploratory tercile_2 | H2_competitor | 182 | -0.0439228 | [-0.0993978, 0.0061573] | 0.0899101 | outside |
| exploratory tercile_3 | H1 | 212 | -0.0104176 | [-0.0503713, 0.0265759] | 0.633367 | outside |
| exploratory tercile_3 | H2_positive | 35 | 0.0383956 | [-0.0984293, 0.170122] | 0.569431 | outside |
| exploratory tercile_3 | H2_competitor | 177 | 0.0323788 | [-0.016272, 0.0827906] | 0.221778 | outside |
| exploratory named | H1 | 0 |  |  |  |  |
| exploratory named | H2_positive | 0 |  |  |  |  |
| exploratory named | H2_competitor | 0 |  |  |  |  |
| exploratory not_named | H1 | 0 |  |  |  |  |
| exploratory not_named | H2_positive | 0 |  |  |  |  |
| exploratory not_named | H2_competitor | 0 |  |  |  |  |

## gdelt

Stored and rebuilt SMDs agree: True. Criteria above 0.20: log_popularity.

| Covariate | Stored SMD | Rebuilt SMD | Independent SMD |
|---|---:|---:|---:|
| baseline_mean | 0.170518 | 0.170518 | 0.170518 |
| baseline_sd | 0.127795 | 0.127795 | 0.127795 |
| log_mention | 0.0446287 | 0.0446287 | 0.0446287 |
| log_popularity | 0.951228 | 0.951228 | 0.951228 |

Mention-gap median 0.304231, 90th percentile 0.598561. Popularity-gap median 0.465363, 90th percentile 0.987947. Pairs 2191.

Exploratory re-match, mention caliper ln 1.5 and popularity caliper ln 1.5.

| Test | Pairs | Events | Effect | 95% interval | Permutation p | Rewiring p | SESOI band | SMD mean | SMD SD | SMD mention | SMD popularity |
|---|---:|---:|---:|---|---:|---:|---|---:|---:|---:|---:|
| exploratory H1 | 1027 | 807 | 0.00525766 | [0.0027304, 0.00795273] | 0.000999001 | 0.310127 | inside | 0.358982 | 0.300072 | 0.00318704 | 0.286499 |
| exploratory H2_positive | 121 | 121 | 0.00670946 | [-0.00675059, 0.0219295] | 0.331668 | 0.189655 | inside | 0.358982 | 0.300072 | 0.00318704 | 0.286499 |
| exploratory H2_competitor | 906 | 789 | -0.000855106 | [-0.00393652, 0.0023215] | 0.581419 | 0.946472 | inside | 0.358982 | 0.300072 | 0.00318704 | 0.286499 |

Exploratory splits of the original matched pairs. A cell under 10 pairs is not tested.

| Split | Test | Pairs | Effect | 95% interval | Permutation p | SESOI band |
|---|---|---:|---:|---|---:|---|
| exploratory edge_positive | H1 | 412 | 0.00708638 | [0.00171384, 0.0129361] | 0.01998 | inside |
| exploratory edge_positive | H2_positive | 412 | 0.00787135 | [0.00106105, 0.014996] | 0.032967 | inside |
| exploratory edge_positive | H2_competitor | 0 |  |  |  |  |
| exploratory edge_competitor | H1 | 1779 | 0.00226601 | [0.000322352, 0.00426227] | 0.027972 | inside |
| exploratory edge_competitor | H2_positive | 0 |  |  |  |  |
| exploratory edge_competitor | H2_competitor | 1779 | -0.00122584 | [-0.00356668, 0.00119929] | 0.280719 | inside |
| exploratory tercile_1 | H1 | 448 | 0.00412416 | [2.94376e-05, 0.00811077] | 0.03996 | inside |
| exploratory tercile_1 | H2_positive | 0 |  |  |  |  |
| exploratory tercile_1 | H2_competitor | 448 | 0.0019277 | [-0.00291258, 0.00658862] | 0.400599 | inside |
| exploratory tercile_2 | H1 | 449 | -0.000946982 | [-0.00457636, 0.00312821] | 0.639361 | inside |
| exploratory tercile_2 | H2_positive | 2 |  |  |  |  |
| exploratory tercile_2 | H2_competitor | 447 | -0.00371258 | [-0.00775033, 0.000500778] | 0.0929071 | inside |
| exploratory tercile_3 | H1 | 1294 | 0.00427232 | [0.00190806, 0.00695345] | 0.001998 | inside |
| exploratory tercile_3 | H2_positive | 410 | 0.00795529 | [0.00107383, 0.0150405] | 0.03996 | inside |
| exploratory tercile_3 | H2_competitor | 884 | -0.00156659 | [-0.00528494, 0.00213162] | 0.358641 | inside |
| exploratory named | H1 | 0 |  |  |  |  |
| exploratory named | H2_positive | 0 |  |  |  |  |
| exploratory named | H2_competitor | 0 |  |  |  |  |
| exploratory not_named | H1 | 0 |  |  |  |  |
| exploratory not_named | H2_positive | 0 |  |  |  |  |
| exploratory not_named | H2_competitor | 0 |  |  |  |  |

## tweetskb

Stored and rebuilt SMDs agree: True. Criteria above 0.20: baseline_mean, log_popularity.

| Covariate | Stored SMD | Rebuilt SMD | Independent SMD |
|---|---:|---:|---:|
| baseline_mean | 0.746897 | 0.746897 | 0.746897 |
| baseline_sd | 0.0953693 | 0.0953693 | 0.0953693 |
| log_mention | 0.0814864 | 0.0814864 | 0.0814864 |
| log_popularity | 0.945692 | 0.945692 | 0.945692 |

Mention-gap median 0.323614, 90th percentile 0.588631. Popularity-gap median 0.378066, 90th percentile 0.960462. Pairs 283.

Exploratory re-match, mention caliper ln 1.5 and popularity caliper ln 1.5.

| Test | Pairs | Events | Effect | 95% interval | Permutation p | Rewiring p | SESOI band | SMD mean | SMD SD | SMD mention | SMD popularity |
|---|---:|---:|---:|---|---:|---:|---|---:|---:|---:|---:|
| exploratory H1 | 139 | 103 | -0.00733773 | [-0.0166089, 0.000584913] | 0.0759241 | 0.630178 | inside | 1.16902 | 0.328979 | 0.11488 | 0.00153775 |
| exploratory H2_positive | 66 | 66 | -0.00884709 | [-0.0217905, 0.00302128] | 0.166833 | 0.452941 | inside | 1.16902 | 0.328979 | 0.11488 | 0.00153775 |
| exploratory H2_competitor | 73 | 73 | -0.0107996 | [-0.0228371, 0.00317308] | 0.0949051 | 0.512821 | inside | 1.16902 | 0.328979 | 0.11488 | 0.00153775 |

Exploratory splits of the original matched pairs. A cell under 10 pairs is not tested.

| Split | Test | Pairs | Effect | 95% interval | Permutation p | SESOI band |
|---|---|---:|---:|---|---:|---|
| exploratory edge_positive | H1 | 119 | -0.000512737 | [-0.0118834, 0.0108113] | 0.924076 | inside |
| exploratory edge_positive | H2_positive | 119 | -0.00614552 | [-0.0169776, 0.00433141] | 0.327672 | inside |
| exploratory edge_positive | H2_competitor | 0 |  |  |  |  |
| exploratory edge_competitor | H1 | 164 | 0.000863625 | [-0.00712012, 0.00826598] | 0.842158 | inside |
| exploratory edge_competitor | H2_positive | 0 |  |  |  |  |
| exploratory edge_competitor | H2_competitor | 164 | -0.00549782 | [-0.0159288, 0.00419737] | 0.275724 | inside |
| exploratory tercile_1 | H1 | 66 | 0.0159066 | [0.00298848, 0.0300608] | 0.042957 | inside |
| exploratory tercile_1 | H2_positive | 13 | 0.00326036 | [-0.0272508, 0.0397768] | 0.901099 | inside |
| exploratory tercile_1 | H2_competitor | 53 | -0.0140825 | [-0.036049, 0.00744186] | 0.21978 | inside |
| exploratory tercile_2 | H1 | 87 | -0.0126912 | [-0.0215916, -0.00444678] | 0.010989 | inside |
| exploratory tercile_2 | H2_positive | 35 | -0.0227596 | [-0.0430538, -0.00368743] | 0.020979 | inside |
| exploratory tercile_2 | H2_competitor | 52 | 0.000477739 | [-0.0137634, 0.0150748] | 0.938062 | inside |
| exploratory tercile_3 | H1 | 130 | 0.00103783 | [-0.00687632, 0.00961575] | 0.822178 | inside |
| exploratory tercile_3 | H2_positive | 71 | 0.000322305 | [-0.0131549, 0.0126934] | 0.964036 | inside |
| exploratory tercile_3 | H2_competitor | 59 | -0.00305272 | [-0.0177617, 0.0114922] | 0.725275 | inside |
| exploratory named | H1 | 0 |  |  |  |  |
| exploratory named | H2_positive | 0 |  |  |  |  |
| exploratory named | H2_competitor | 0 |  |  |  |  |
| exploratory not_named | H1 | 0 |  |  |  |  |
| exploratory not_named | H2_positive | 0 |  |  |  |  |
| exploratory not_named | H2_competitor | 0 |  |  |  |  |


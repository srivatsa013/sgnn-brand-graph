# Phase 5 outcomes

One fit. Hyperparameters were chosen on validation MAE. The Holm family of 8 is recomputed here and marked final. `eval/results/phase4_outcomes.json` still holds the family-of-6 adjustment from when H3 was not run.

H3 is supported only when the MAE gap is negative, the Holm p-value is below 0.05, the interval excludes 0, and the relative MAE gain is at least 5 percent. Social and TweetsKB are outside that family.

## news_joined

Selected signed model: hidden 64, depth 2, dropout 0.2, mean validation MAE 0.234318. Exact-zero test labels ignored: 0.

| Model | Test MAE | SD | Gap to no-graph | 95% interval | p | Relative MAE gain |
|---|---:|---:|---:|---|---:|---:|
| signed | 0.276479 | 0.00477137 | -0.0176023 | [-0.0437192, 0.00666875] | 0.231768 | 0.0598551 |
| unsigned | 0.277744 | 0.00490447 | -0.0163375 | [-0.0442926, 0.00817461] | 0.274725 | 0.0555544 |
| no_graph | 0.294082 | 0.0183851 |  |  |  |  |
| sign_shuffled | 0.278726 | 0.00565708 | -0.0153555 | [-0.0415592, 0.00894629] | 0.281718 | 0.0522152 |
| degree_matched | 0.277468 | 0.00425794 | -0.0166132 | [-0.04442, 0.00938894] | 0.284715 | 0.0564917 |
| linear_diffusion | 0.274433 |  | -0.0196486 | [-0.0445876, 0.00529181] | 0.148851 | 0.0668134 |

signed_vs_unsigned: gap -0.00126477, interval [-0.00915953, 0.00528798], p 0.763237, relative gain 0.00455371, H3 not supported.
signed_vs_nograph: gap -0.0176023, interval [-0.0437192, 0.00666875], p 0.231768, relative gain 0.0598551, H3 not supported.

| Held-out ecosystem | Test MAE | Events |
|---|---:|---:|
| Alphabet | 0.294031 | 16 |
| Apple | 0.344633 | 10 |
| Chevron | 0.237114 | 10 |
| Chipotle |  | 4 |
| Colgate-Palmolive |  | 1 |
| Eli Lilly | 0.0667361 | 1 |
| Lowe's |  | 1 |
| Microsoft | 0.234861 | 14 |
| Nike |  | 12 |
| T-Mobile US | 0.129593 | 2 |
| Tesla | 0.388083 | 14 |

## social

Selected signed model: hidden 32, depth 2, dropout 0.2, mean validation MAE 0.160887. Exact-zero test labels ignored: 20.

| Model | Test MAE | SD | Gap to no-graph | 95% interval | p | Relative MAE gain |
|---|---:|---:|---:|---|---:|---:|
| signed | 0.20832 | 0.00244718 | 0.0164209 | [0.00384084, 0.0283065] | 0.013986 | -0.0855704 |
| unsigned | 0.198429 | 0.00452171 | 0.00652984 | [-0.00145957, 0.0146275] | 0.0889111 | -0.0340274 |
| no_graph | 0.191899 | 0.00303746 |  |  |  |  |
| sign_shuffled | 0.208688 | 0.00142673 | 0.0167887 | [0.0043902, 0.0287762] | 0.00899101 | -0.0874869 |
| degree_matched | 0.208705 | 0.00176888 | 0.0168056 | [0.00471989, 0.0288013] | 0.00999001 | -0.0875751 |
| linear_diffusion | 0.208059 |  | 0.0161599 | [0.00352298, 0.0288808] | 0.012987 | -0.0842104 |

signed_vs_unsigned: gap 0.00989109, interval [-0.004127, 0.024858], p 0.17982, relative gain -0.0498469, H3 not in the registered family of 8.
signed_vs_nograph: gap 0.0164209, interval [0.00384084, 0.0283065], p 0.013986, relative gain -0.0855704, H3 not in the registered family of 8.

| Held-out ecosystem | Test MAE | Events |
|---|---:|---:|
| Alphabet | 0.171486 | 142 |
| Apple | 0.329492 | 149 |
| Chevron | 0.156434 | 51 |
| Chipotle | 0.230271 | 40 |
| Colgate-Palmolive | 0.320449 | 34 |
| Eli Lilly | 0.117988 | 27 |
| Hershey | 0.227336 | 1 |
| John Deere | 0.257075 | 20 |
| Lowe's | 0.206912 | 28 |
| Mastercard | 0.151998 | 52 |
| Microsoft | 0.26637 | 109 |
| Nike |  | 61 |
| T-Mobile US | 0.158267 | 27 |
| Tesla | 0.226209 | 145 |

## gdelt

Selected signed model: hidden 32, depth 1, dropout 0.2, mean validation MAE 0.0313716. Exact-zero test labels ignored: 0.

| Model | Test MAE | SD | Gap to no-graph | 95% interval | p | Relative MAE gain |
|---|---:|---:|---:|---|---:|---:|
| signed | 0.0331616 | 0.000524071 | 0.000284724 | [-0.000392215, 0.000931017] | 0.428571 | -0.00866031 |
| unsigned | 0.0327238 | 0.000386215 | -0.000153092 | [-0.000809702, 0.000444987] | 0.628372 | 0.00465654 |
| no_graph | 0.0328769 | 0.000287668 |  |  |  |  |
| sign_shuffled | 0.0331787 | 0.000352986 | 0.000301841 | [-0.000262334, 0.000849072] | 0.302697 | -0.00918096 |
| degree_matched | 0.0331647 | 0.000185682 | 0.000287799 | [-0.000340319, 0.000865027] | 0.376623 | -0.00875384 |
| linear_diffusion | 0.0386816 |  | 0.00580468 | [0.00370051, 0.00787085] | 0.000999001 | -0.176558 |

signed_vs_unsigned: gap 0.000437816, interval [5.79507e-05, 0.000824656], p 0.02997, relative gain -0.0133791, H3 not supported.
signed_vs_nograph: gap 0.000284724, interval [-0.000392215, 0.000931017], p 0.428571, relative gain -0.00866031, H3 not supported.

| Held-out ecosystem | Test MAE | Events |
|---|---:|---:|
| Alphabet | 0.025849 | 151 |
| Apple | 0.0439658 | 145 |
| Chevron | 0.0223996 | 158 |
| Chipotle | 0.0261199 | 107 |
| Colgate-Palmolive | 0.0293873 | 89 |
| Eli Lilly | 0.0212635 | 148 |
| Hershey | 0.0498809 | 116 |
| John Deere | 0.0317132 | 152 |
| Lowe's | 0.0333997 | 18 |
| Mastercard | 0.0269333 | 137 |
| Microsoft | 0.0302977 | 151 |
| Nike | 0.0393212 | 156 |
| T-Mobile US | 0.0296738 | 101 |

## tweetskb

Selected signed model: hidden 32, depth 1, dropout 0.2, mean validation MAE 0.0430687. Exact-zero test labels ignored: 0.

| Model | Test MAE | SD | Gap to no-graph | 95% interval | p | Relative MAE gain |
|---|---:|---:|---:|---|---:|---:|
| signed | 0.0447038 | 0.00304239 | -0.00115502 | [-0.00416731, 0.0024383] | 0.517483 | 0.0251864 |
| unsigned | 0.0431115 | 0.000885278 | -0.00274734 | [-0.0105619, 0.00452185] | 0.48951 | 0.0599087 |
| no_graph | 0.0458588 | 0.00411227 |  |  |  |  |
| sign_shuffled | 0.0501402 | 0.00605961 | 0.00428142 | [-0.00035299, 0.00968127] | 0.108891 | -0.093361 |
| degree_matched | 0.0481863 | 0.00422372 | 0.00232747 | [-0.000712931, 0.00574231] | 0.181818 | -0.050753 |
| linear_diffusion | 0.0415673 |  | -0.00429148 | [-0.0132591, 0.0038903] | 0.332667 | 0.0935802 |

signed_vs_unsigned: gap 0.00159232, interval [-0.00612174, 0.0106147], p 0.736264, relative gain -0.0369351, H3 not in the registered family of 8.
signed_vs_nograph: gap -0.00115502, interval [-0.00416731, 0.0024383], p 0.517483, relative gain 0.0251864, H3 not in the registered family of 8.

| Held-out ecosystem | Test MAE | Events |
|---|---:|---:|
| Alphabet | 0.0665549 | 44 |
| Apple | 0.0423455 | 48 |
| Chevron | 0.102903 | 44 |
| Chipotle | 0.0155829 | 9 |
| Colgate-Palmolive | 0.0895298 | 3 |
| Hershey |  | 2 |
| John Deere |  | 1 |
| Lowe's |  | 39 |
| Mastercard | 0.0697625 | 37 |
| Microsoft | 0.0412276 | 46 |
| Nike |  | 53 |
| T-Mobile US | 0.0155081 | 7 |

## Final Holm family of 8

### Arm A (news_joined), family size 8

| Test | Unadjusted p | Holm p | Rejects |
|---|---:|---:|---|
| H1_pair_permutation | 0.637363 | 1 | False |
| H1_rewiring | 0.546906 | 1 | False |
| H2_positive_edges | 0.0719281 | 0.575425 | False |
| H2_competitor_edges | 0.642358 | 1 | False |
| H3_signed_vs_unsigned | 0.763237 | 1 | False |
| H3_signed_vs_nograph | 0.231768 | 1 | False |
| H4_magnitude | 0.959041 | 1 | False |
| H4_lag | 0.306693 | 1 | False |

### Arm B (gdelt), family size 8

| Test | Unadjusted p | Holm p | Rejects |
|---|---:|---:|---|
| H1_pair_permutation | 0.001998 | 0.015984 | True |
| H1_rewiring | 0.576375 | 1 | False |
| H2_positive_edges | 0.032967 | 0.20979 | False |
| H2_competitor_edges | 0.280719 | 1 | False |
| H3_signed_vs_unsigned | 0.02997 | 0.20979 | False |
| H3_signed_vs_nograph | 0.428571 | 1 | False |
| H4_magnitude | 0.351648 | 1 | False |
| H4_lag | 0.0789211 | 0.394605 | False |

## Test RMSE and sign accuracy

Filled on 2026-10-24 from the stored files. The signed numbers are a forward pass of the stored weights in `eval/results/phase5_models` on the stored test events in `eval/results/phase5_events.pt`. The recomputed test MAE matches the stored test MAE on every source. No weights were updated. Linear diffusion uses the stored training-fold coefficient. Unsigned, no-graph, sign-shuffled, and degree-matched prediction outputs were not stored, so those cells are empty. `eval/results/phase5_label_table.parquet` holds the labels, not model outputs.

| Source | Model | Test RMSE | SD | Sign accuracy | SD |
|---|---|---:|---:|---:|---:|
| news_joined | signed | 0.319728 | 0.00620408 | 0.576042 | 0.0361069 |
| news_joined | unsigned |  |  |  |  |
| news_joined | no_graph |  |  |  |  |
| news_joined | sign_shuffled |  |  |  |  |
| news_joined | degree_matched |  |  |  |  |
| news_joined | linear_diffusion | 0.319475 |  | 0.44375 |  |
| social | signed | 0.236781 | 0.00222282 | 0.502663 | 0.0176767 |
| social | unsigned |  |  |  |  |
| social | no_graph |  |  |  |  |
| social | sign_shuffled |  |  |  |  |
| social | degree_matched |  |  |  |  |
| social | linear_diffusion | 0.237033 |  | 0.490335 |  |
| gdelt | signed | 0.0360976 | 0.000562724 | 0.657623 | 0.0144185 |
| gdelt | unsigned |  |  |  |  |
| gdelt | no_graph |  |  |  |  |
| gdelt | sign_shuffled |  |  |  |  |
| gdelt | degree_matched |  |  |  |  |
| gdelt | linear_diffusion | 0.0420689 |  | 0.53766 |  |
| tweetskb | signed | 0.048331 | 0.00316623 | 0.548652 | 0.0486303 |
| tweetskb | unsigned |  |  |  |  |
| tweetskb | no_graph |  |  |  |  |
| tweetskb | sign_shuffled |  |  |  |  |
| tweetskb | degree_matched |  |  |  |  |
| tweetskb | linear_diffusion | 0.045566 |  | 0.422695 |  |


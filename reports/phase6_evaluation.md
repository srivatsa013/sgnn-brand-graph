# Phase 6 evaluation

Tables only. The model was chosen by validation MAE before these test numbers were read.

## news_joined

Chosen on validation MAE: hidden 64, depth 2, dropout 0.2.

| Channel | Test MAE | SD |
|---|---:|---:|
| positive | 0.277075 | 0.00614815 |
| competitor | 0.276113 | 0.00636647 |
| comention | 0.274582 | 0.00340682 |
| all | 0.276479 | 0.00477137 |

| Depth | Test MAE | SD |
|---|---:|---:|
| 1 | 0.251919 | 0.0185593 |
| 2 | 0.276479 | 0.00477137 |

| Edge class | Mean absolute contribution |
|---|---:|
| positive | 0.00798262 |
| negative | 0.007114 |
| comention | 0.0352357 |

Example event news_joined:Microsoft:2023-08-07.

| Rank | Neighbor | Mean absolute attribution |
|---:|---|---:|
| 1 | Azure | 0.0398817 |
| 2 | Microsoft CEO | 0.00564297 |
| 3 | Windows | 0 |
| 4 | ORCL | 0 |
| 5 | Microsoft | 0 |

| Seeds | Test MAE mean | SD |
|---|---:|---:|
| 0-9 | 0.278294 | 0.00556969 |

| Comparison | Test MAE | Gap to no-graph | 95% interval | p | Relative MAE gain |
|---|---:|---:|---|---:|---:|
| sign_shuffled | 0.278726 | -0.0153555 | [-0.0415592, 0.00894629] | 0.281718 | 0.0522152 |
| degree_matched | 0.277468 | -0.0166132 | [-0.04442, 0.00938894] | 0.284715 | 0.0564917 |

## social

Chosen on validation MAE: hidden 32, depth 2, dropout 0.2.

| Channel | Test MAE | SD |
|---|---:|---:|
| positive | 0.207195 | 0.000482551 |
| competitor | 0.207345 | 0.000624462 |
| comention | 0.208262 | 0.00246922 |
| all | 0.20832 | 0.00244718 |

| Depth | Test MAE | SD |
|---|---:|---:|
| 1 | 0.196552 | 0.00437238 |
| 2 | 0.20832 | 0.00244718 |

| Edge class | Mean absolute contribution |
|---|---:|
| positive | 0.00212995 |
| negative | 2.32793e-05 |
| comention | 0.0199269 |

Example event social:Apple:2021-10-04.

| Rank | Neighbor | Mean absolute attribution |
|---:|---|---:|
| 1 | Apple | 0.0355243 |
| 2 | DELL | 0.0137162 |
| 3 | HPQ | 0.0126602 |
| 4 | LOGI | 0.00539563 |
| 5 | iPhone | 0 |

| Seeds | Test MAE mean | SD |
|---|---:|---:|
| 0-9 | 0.211077 | 0.00407963 |

| Comparison | Test MAE | Gap to no-graph | 95% interval | p | Relative MAE gain |
|---|---:|---:|---|---:|---:|
| sign_shuffled | 0.208688 | 0.0167887 | [0.0043902, 0.0287762] | 0.00899101 | -0.0874869 |
| degree_matched | 0.208705 | 0.0168056 | [0.00471989, 0.0288013] | 0.00999001 | -0.0875751 |

## gdelt

Chosen on validation MAE: hidden 32, depth 1, dropout 0.2.

| Channel | Test MAE | SD |
|---|---:|---:|
| positive | 0.0342985 | 0.000562672 |
| competitor | 0.0334552 | 0.000605166 |
| comention | 0.0345921 | 0.000613487 |
| all | 0.0331616 | 0.000524071 |

| Depth | Test MAE | SD |
|---|---:|---:|
| 1 | 0.0331616 | 0.000524071 |
| 2 | 0.0389547 | 1.84002e-05 |

| Edge class | Mean absolute contribution |
|---|---:|
| positive | 0.011918 |
| negative | 0.00792897 |
| comention | 0 |

Example event gdelt:Colgate-Palmolive:2024-07-28.

| Rank | Neighbor | Mean absolute attribution |
|---:|---|---:|
| 1 | Colgate-Palmolive | 0.00304104 |
| 2 | PG | 0 |

| Seeds | Test MAE mean | SD |
|---|---:|---:|
| 0-9 | 0.0331302 | 0.000433668 |

| Comparison | Test MAE | Gap to no-graph | 95% interval | p | Relative MAE gain |
|---|---:|---:|---|---:|---:|
| sign_shuffled | 0.0331787 | 0.000301841 | [-0.000262334, 0.000849072] | 0.302697 | -0.00918096 |
| degree_matched | 0.0331647 | 0.000287799 | [-0.000340319, 0.000865027] | 0.376623 | -0.00875384 |

## tweetskb

Chosen on validation MAE: hidden 32, depth 1, dropout 0.2.

| Channel | Test MAE | SD |
|---|---:|---:|
| positive | 0.0483683 | 0.001379 |
| competitor | 0.0465026 | 0.00362694 |
| comention | 0.0501671 | 0.00281279 |
| all | 0.0447038 | 0.00304239 |

| Depth | Test MAE | SD |
|---|---:|---:|
| 1 | 0.0447038 | 0.00304239 |
| 2 | 0.0433652 | 0.000835348 |

| Edge class | Mean absolute contribution |
|---|---:|
| positive | 0.0241251 |
| negative | 0.0240137 |
| comention | 0 |

Example event tweetskb:Alphabet:2020-06-04.

| Rank | Neighbor | Mean absolute attribution |
|---:|---|---:|
| 1 | Alphabet | 0.0137967 |
| 2 | YouTube | 0 |
| 3 | SNAP | 0 |
| 4 | PINS | 0 |
| 5 | Meta | 0 |

| Seeds | Test MAE mean | SD |
|---|---:|---:|
| 0-9 | 0.0465427 | 0.00440309 |

| Comparison | Test MAE | Gap to no-graph | 95% interval | p | Relative MAE gain |
|---|---:|---:|---|---:|---:|
| sign_shuffled | 0.0501402 | 0.00428142 | [-0.00035299, 0.00968127] | 0.108891 | -0.093361 |
| degree_matched | 0.0481863 | 0.00232747 | [-0.000712931, 0.00574231] | 0.181818 | -0.050753 |


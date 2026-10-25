# Augmented run (contains synthetic events)

One signed fit on the augmented joined-news events. Hyperparameters were chosen on validation MAE. This file does not replace the real-only Phase 5 results.

Synthetic share 0.5. Lambda 1. Frozen noise SD 0.2694611493987299. Real events 95. Synthetic events 95.

Selected signed model: hidden 32, depth 2, dropout 0.2, mean validation MAE 0.259729.

| Split | Events | Test MAE | SD | Test RMSE | SD | Sign accuracy | SD |
|---|---:|---:|---:|---:|---:|---:|---:|
| augmented_test | 35 | 0.259116 | 0.00379838 | 0.301459 | 0.0050563 | 0.642986 | 0.0170838 |
| real_only_test | 16 | 0.29208 | 0.00442938 | 0.330955 | 0.00550842 | 0.57 | 0.0319148 |

Per-edge-class estimates on the augmented test fold. These are mean absolute channel contributions.

| Edge class | Estimate |
|---|---:|
| positive | 0.03178 |
| negative | 0.0413093 |
| comention | 0.0320373 |

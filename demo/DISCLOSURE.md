# Disclosure

This folder is a demonstration. It is not part of the confirmatory analysis.

REAL means a number computed from the study files: the graph, the Phase 4 tables, or the Phase 5 label table. MODEL means a prediction from the Phase 5 signed model trained on the real graph. AUGMENTED and SYNTHETIC mean the demo generator was involved. A figure that mixes them says AUGMENTED and CONTAINS SYNTHETIC DATA, and the real-only number is printed beside the combined number.

The augmented table uses synthetic share 0.25 and lambda 1.0. Real rows are the Phase 5 label shifts. Synthetic rows are sampled from `demo/synthetic/SYNTHETIC_events.parquet`. The file does not replace a study file.

The sign-specificity simulation plants an opposite-sign effect on competitor edges and gives those edges the larger share. It uses the short demo fit. It does not use the Phase 5 grid, and it does not support a claim about the real arms.

The explorer reads study files and writes nothing. Every number on that page carries its mode label: REAL measured, MODEL prediction, or AUGMENTED/SYNTHETIC.

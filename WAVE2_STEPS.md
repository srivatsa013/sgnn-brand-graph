# Wave 2 — step by step (for Srivatsa)

Sara sends `wave2_changes.zip`. It adds new files only. No Wave 1 script, config or result changes, so `check_frozen_sha256.py` keeps passing until step 7, which records the new hashes on purpose.

Run every command from the project folder on your Mac (the one with `data/interim/`), in Terminal.

---

## Step 1. Start from a clean, current copy

```bash
cd ~/path/to/sgnn-brand-graph        # your project folder
git status                           # should say "nothing to commit"; if not, commit or stash first
git checkout main
git pull
```

## Step 2. Put the new files in

```bash
unzip -o ~/Downloads/wave2_changes.zip
git checkout -b wave2-amendment-b
git status                           # should list the new files and README.md
```

The zip contains:

```
scripts/wave2_labels.py               abnormal-shift label
scripts/wave2_self_controlled.py      neighbour vs itself on placebo days; two-sided H2
scripts/wave2_model.py                learned-sign model + shock-broadcast, tied, own-only, predict-zero
scripts/wave2_train.py                runs everything, writes reports/wave2_outcomes.md
scripts/test_wave2.py                 synthetic tests
scripts/wave1_persistence_baseline.py predict-zero row for Wave 1 Table IV
scripts/freeze_amendment_b.py         does the freeze (step 7)
reports/wave2_amendment_b_draft.md    amendment text
reports/paper_revisions.md            paper edits (Sara uses this)
README.md                             new "Wave 2" section at the end
WAVE2_STEPS.md                        this file
```

## Step 3. Use the same Python you used for Phase 5

```bash
source .venv/bin/activate            # skip if you never used a venv
python3 -c "import torch, pyarrow; print(torch.__version__, pyarrow.__version__)"
```

Both should print versions. If either is missing: `pip install torch pyarrow`.

## Step 4. Run the tests

```bash
PYTHONPATH=scripts python3 scripts/test_wave2.py
PYTHONPATH=scripts python3 scripts/test_phase5_model.py
python3 scripts/check_frozen_sha256.py
```

Expected:
- `test_wave2.py` ends with `Ran 9 tests ... OK`. It takes about 20 seconds and prints three synthetic checks:
  - a worked example
  - planted H2 effects, including a recovered contagion effect
  - a synthetic MAE table where the relational model beats tied, broadcast and predict-zero
- `test_phase5_model.py` ends with `OK`.
- The last line of `check_frozen_sha256.py` is `mismatches 0`.

If anything fails, stop and send Sara the output.

## Step 5. Wave 1 predict-zero baseline (any time, does not need the freeze)

```bash
PYTHONPATH=scripts python3 scripts/wave1_persistence_baseline.py
```

This writes `eval/results/wave1_persistence.json`. It uses the stored `eval/results/phase5_events.pt` and `phase5_models/`, the same test folds as Table IV, and changes no Wave 1 file. It takes a few minutes. It prints one line per source with `persistence_mae`, `signed_mae` and the comparison.

## Step 6. Point the driver at the Wave 2 data (before the freeze)

Open `scripts/wave2_train.py` and find `load_sources`. Right now it loads the Wave 1 lists:

- Arm A ecosystems: `R.ARM_A`
- Arm B ecosystems: `ARM_B`
- GDELT series: `series_from_db(R.GDELT_DB)`

For the confirmatory run it must use the 30 Wave 2 ecosystems and the Wave 2 GDELT series that `phase2_gdelt_wave2.py` builds. `R.NODES["ecosystems"]` must also contain the Wave 2 ecosystems, with amendment A's neighbour definition and the 34 competitor edges. You set those up, so you know which config and which sqlite to point at.

Make only that change. Then rerun step 4.

This step has to happen before step 7. The freeze records `wave2_train.py`'s hash, so any edit after the freeze makes the run refuse to start. That refusal is intended.

If the scorer still misses 0.70 after the two allowed improvement rounds, leave `news_joined` out of `--sources`. Amendment A already says Arm A news is then dropped.

## Step 7. Freeze amendment B

Read `reports/wave2_amendment_b_draft.md` once. If you want to change any rule, change it now. Nothing can change after this step.

Dry run first. It changes nothing:

```bash
python3 scripts/freeze_amendment_b.py
```

It checks that no Wave 2 outcome exists yet, runs the tests and the current hash check, and prints what it will change, including the five script hashes. If that looks right, run:

```bash
python3 scripts/freeze_amendment_b.py --write
```

It does four things, then checks the hashes again:
1. Renames the draft to `reports/wave2_amendment_b<today>.md` and sets its status to FROZEN.
2. Appends amendment `B<today>` to `configs/phase0.json`. It inserts text only, so the rest of the file is untouched. It checks that nothing else changed.
3. Records the new `phase0.json` hash in `configs/frozen_sha256.json`.
4. Adds rows to `configs/frozen_sha256.json` for the amendment document and the five Wave 2 scripts.

It ends with `mismatches 0` and `frozen as B<today>`.

Then add the date and the printed hashes to `DECISIONS_LOG.md`, the way you logged amendment A. For example:

```
## <today> — Amendment B frozen
Frozen before any Wave 2 outcome. phase0.json sha256 <hash>. Amendment document sha256 <hash>.
Scripts: wave2_labels.py <hash>, wave2_self_controlled.py <hash>, wave2_model.py <hash>,
wave2_train.py <hash>, test_wave2.py <hash>. check_frozen_sha256.py exited 0, mismatches 0.
```

## Step 8. Commit and push the freeze (before any run)

```bash
git add -A
git status                           # check: no data/ files, no .pt files (they are gitignored)
git commit -m "Freeze amendment B: Wave 2 label, self-controlled tests, learned-sign models"
git push -u origin wave2-amendment-b
```

The commit's timestamp on GitHub is your public proof that the rules came before the results.

## Step 9 (optional). Exploratory re-run on Wave 1 events

```bash
caffeinate -i env PYTHONPATH=scripts python3 scripts/wave2_train.py --sources gdelt social --exploratory-wave1
```

This writes `reports/wave2_outcomes_EXPLORATORY_wave1.md`, not the confirmatory file. Everything in it is exploratory, because Wave 1 outcomes have been seen. It is useful for the paper's diagnostics section. Skip it if you are short on time.

## Step 10. Confirmatory run

Run this once the Wave 2 series are complete and the GDELT jobs have finished:

```bash
caffeinate -i env PYTHONPATH=scripts python3 scripts/wave2_train.py --sources gdelt news_joined
```

Drop `news_joined` if the scorer gate failed (step 6). The script refuses to start if amendment B is not frozen or if any frozen hash changed.

- **Duration.** Per source it fits 4 models × 4 grid points × 5 seeds, plus 10 refits for the shuffled and degree-matched graphs. That is fewer fits than Phase 5, so expect less time than Phase 5 took.
- **Keep the Mac awake.** `caffeinate -i` stops it sleeping during the run.
- **Outputs.** It writes `eval/results/wave2_outcomes.json` after each source, and `reports/wave2_outcomes.md` at the end.

## Step 11. Commit the results and send them to Sara

```bash
git add reports/wave2_outcomes.md eval/results/wave2_outcomes.json eval/results/wave1_persistence.json
git commit -m "Wave 2 confirmatory outcomes"
git push
```

Send Sara:
- `reports/wave2_outcomes.md`
- `eval/results/wave1_persistence.json`

She fills the paper from those two files.

---

## If something goes wrong

| Message | Meaning | Fix |
|---|---|---|
| `stopped: ... wave2_outcomes.json exists` | An outcome file exists before the freeze | Do not delete it to get around this. Tell Sara; the run then has to be reported as exploratory |
| `amendment B is not frozen` | Step 7 was skipped | Run step 7 |
| `frozen hashes do not match` | A frozen file was edited after the freeze | Undo the edit (`git checkout -- <file>`). A real fix needs a new dated amendment, not a silent change |
| `FileNotFoundError ... data/interim/...` | Running outside the project folder, or on a machine without the data | Run from the folder that has `data/interim/` |
| `ModuleNotFoundError: torch` | Wrong Python | Activate the venv (step 3) |
| `empty fold` for a source | Too few events in that source | It is reported as skipped; leave it out of `--sources` |

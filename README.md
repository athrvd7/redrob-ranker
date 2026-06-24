# Redrob Hackathon Ranker

Ranks the top 100 candidates for the Senior AI Engineer JD and writes a submission CSV in the required format:

```text
candidate_id,rank,score,reasoning
```

The project supports three ways to run:

1. **Interactive TUI** via `cli.py`
2. **CLI pipeline** for the real `candidates.jsonl` dataset
3. **Streamlit sandbox** for small JSON uploads

---

## Repository contents

```text
redrob-ranker/
├── README.md
├── requirements.txt
├── precompute.py
├── rank.py
├── validate_submission.py
├── app.py
├── core/
├── sample_candidates.json
└── candidates.jsonl        # local full dataset, not committed
```

---

## Prerequisites

- Python 3
- `pip`
- A terminal/CLI

If you want to run the full pipeline, you also need the full input file at:

```text
redrob-ranker/candidates.jsonl
```

---

## 1. Setup

From the project root:

```sh
cd redrob-ranker
```

### Option A: use the existing virtual environment

If `.venv` already exists:

```sh
.venv/bin/pip install -r requirements.txt
```

### Option B: create a new virtual environment

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

Installed dependencies are:

- `numpy==1.26.4`
- `pandas==2.2.2`
- `questionary==2.0.1`
- `rich==13.7.1`
- `streamlit==1.36.0`
- `tqdm==4.66.4`

---

## 2. Run the interactive TUI

If you want a guided terminal interface for common workflows, run:

```sh
cd redrob-ranker
.venv/bin/python cli.py
```

This opens an interactive menu for:
- precomputing features,
- running the full 100K ranker,
- running the sample ranker,
- validating a CSV,
- inspecting a candidate by ID,
- showing the top N rows from the latest submission.

Use this when you want a developer-friendly terminal UI instead of remembering individual commands.

Notes:
- `cli.py` is interactive, so run it in a real terminal.
- It uses the current Python environment and expects project files like `candidates.jsonl` in the repo root.

---

## 3. Quick CLI smoke test

If you want to verify the project works before processing the full 100K dataset, run the sample input.

```sh
cd redrob-ranker
.venv/bin/python rank.py --candidates sample_candidates.json --out test_submission.csv --no-features
```

This:
- scores the sample JSON directly,
- skips feature precomputation,
- writes `test_submission.csv`.

### Optional: validate the generated CSV

```sh
cd redrob-ranker
.venv/bin/python validate_submission.py test_submission.csv
```

Note: the validator requires **exactly 100 rows**, so sample-data validation may fail if the sample file has fewer than 100 candidates.

---

## 4. Full CLI run on the real dataset

Use this when `candidates.jsonl` is available.

### Step 1: Precompute features

```sh
cd redrob-ranker
.venv/bin/python precompute.py --candidates candidates.jsonl --out candidate_features.npz
```

What it does:
- reads `candidates.jsonl` **line by line**,
- extracts deterministic scoring features,
- saves them into `candidate_features.npz`.

Expected output file:

```text
redrob-ranker/candidate_features.npz
```

### Step 2: Rank candidates

```sh
cd redrob-ranker
.venv/bin/python rank.py --candidates candidates.jsonl --features candidate_features.npz --out submission.csv
```

What it does:
- loads the precomputed feature file,
- selects the top 100 candidates,
- writes `submission.csv`,
- prints the top 10 ranked candidates with deterministic reasoning.

Expected output file:

```text
redrob-ranker/submission.csv
```

### Step 3: Validate the submission

```sh
cd redrob-ranker
.venv/bin/python validate_submission.py submission.csv
```

If everything is correct, you should see:

```text
Submission is valid.
```

---

## 5. One-command CLI run

If you want to run the full pipeline end-to-end in one shot:

```sh
cd redrob-ranker && .venv/bin/python precompute.py --candidates candidates.jsonl --out candidate_features.npz && .venv/bin/python rank.py --candidates candidates.jsonl --features candidate_features.npz --out submission.csv && .venv/bin/python validate_submission.py submission.csv
```

---

## 6. CLI command reference

### `cli.py`

```sh
.venv/bin/python cli.py
```

`cli.py` launches the interactive TUI for this project.

Typical flow inside the TUI:
1. `Precompute features`
2. `Run ranker (full 100K)`
3. `Validate submission`
4. `Show top N from last submission`

It is a convenience wrapper around the project scripts and is a good default entrypoint for manual exploration.


### `precompute.py`

```sh
.venv/bin/python precompute.py --candidates <input.jsonl> --out <features.npz>
```

Arguments:
- `--candidates`: input JSONL candidate file
- `--out`: output NumPy feature file

Example:

```sh
.venv/bin/python precompute.py --candidates candidates.jsonl --out candidate_features.npz
```

### `rank.py`

Using precomputed features:

```sh
.venv/bin/python rank.py --candidates <input.jsonl> --features <features.npz> --out <submission.csv>
```

Direct inline scoring without precompute:

```sh
.venv/bin/python rank.py --candidates <input.json|input.jsonl> --out <submission.csv> --no-features
```

Arguments:
- `--candidates`: input candidates file; supports `.jsonl` and `.json`
- `--features`: precomputed feature file; required unless `--no-features` is used
- `--out`: output CSV path
- `--no-features`: score inline instead of using `candidate_features.npz`

Examples:

```sh
.venv/bin/python rank.py --candidates candidates.jsonl --features candidate_features.npz --out submission.csv
.venv/bin/python rank.py --candidates sample_candidates.json --out test_submission.csv --no-features
```

### `validate_submission.py`

```sh
.venv/bin/python validate_submission.py <submission.csv>
```

Example:

```sh
.venv/bin/python validate_submission.py submission.csv
```

The validator checks:
- exact header order,
- exactly 100 data rows,
- ranks 1 through 100 exactly once,
- valid `candidate_id` format,
- non-increasing scores by rank,
- candidate ID tie-break order for equal scores.

---

## 7. Run the Streamlit sandbox

The Streamlit app is for small candidate batches and interactive inspection.

```sh
cd redrob-ranker
.venv/bin/streamlit run app.py
```

Then open the local URL shown in the terminal.

### Streamlit input format

Upload a `.json` file containing a JSON array of candidate objects.

The app expects:
- a JSON array,
- each item to be a candidate object,
- at most 100 candidates.

Notes:
- The UI is intended for **small batches**, not the full `candidates.jsonl` pipeline.
- If you upload fewer than 100 candidates, the downloaded CSV may not satisfy the final validator's 100-row rule.

---

## 8. Expected outputs

After a full successful run, you should have:

```text
candidate_features.npz
submission.csv
```

`submission.csv` columns are:

```text
candidate_id,rank,score,reasoning
```

Example workflow:

```sh
cd redrob-ranker
.venv/bin/python precompute.py --candidates candidates.jsonl --out candidate_features.npz
.venv/bin/python rank.py --candidates candidates.jsonl --features candidate_features.npz --out submission.csv
.venv/bin/python validate_submission.py submission.csv
```

---

## 9. How the scoring works

The final score is:

```text
final_score = (
    skill_match    * 0.35 +
    career_quality * 0.30 +
    seniority_fit  * 0.15 +
    location_score * 0.10 +
    availability   * 0.10
) * honeypot_penalty
```

In short:
- `skill_match`: retrieval, embeddings, vector DB, Python, ranking-eval evidence
- `career_quality`: product-company and shipped-production signals
- `seniority_fit`: strongest around the target experience band
- `location_score`: boosts India target cities and relocation willingness
- `availability`: recency and hiring responsiveness signals
- `honeypot_penalty`: discards suspicious or impossible profiles

Reasoning is generated deterministically from candidate data; no LLM or external API is used.

---

## 10. Performance and constraints

The project is designed for the challenge constraints:

- CPU only
- no network calls
- no GPU dependencies in the ranking path
- `rank.py` should stay within the challenge runtime envelope
- `precompute.py` streams the dataset rather than loading the full JSONL into memory at once

---

## 11. Troubleshooting

### `No such file or directory: candidates.jsonl`
The full dataset file is missing. Place it here:

```text
redrob-ranker/candidates.jsonl
```

### `--features is required unless --no-features is used`
You ran `rank.py` without either:
- providing `--features candidate_features.npz`, or
- adding `--no-features`

Use one of these:

```sh
.venv/bin/python rank.py --candidates candidates.jsonl --features candidate_features.npz --out submission.csv
```

or

```sh
.venv/bin/python rank.py --candidates sample_candidates.json --out test_submission.csv --no-features
```

### `Submission is valid.` does not appear
Run the validator separately to see the exact failure:

```sh
.venv/bin/python validate_submission.py submission.csv
```

### Streamlit command not found
Use the binary inside the virtual environment:

```sh
.venv/bin/streamlit run app.py
```

### TUI does not start or shows `ModuleNotFoundError`
Make sure dependencies are installed in the active environment:

```sh
.venv/bin/pip install -r requirements.txt
```

Then run:

```sh
.venv/bin/python cli.py
```

---

## 12. Recommended run order

For most users, the easiest way is the TUI:

```sh
cd redrob-ranker
.venv/bin/pip install -r requirements.txt
.venv/bin/python cli.py
```

Then choose:
1. `Precompute features`
2. `Run ranker (full 100K)`
3. `Validate submission`

If you prefer raw commands instead of the TUI, use:

```sh
cd redrob-ranker
.venv/bin/pip install -r requirements.txt
.venv/bin/python precompute.py --candidates candidates.jsonl --out candidate_features.npz
.venv/bin/python rank.py --candidates candidates.jsonl --features candidate_features.npz --out submission.csv
.venv/bin/python validate_submission.py submission.csv
```

If you only want a fast local check:

```sh
cd redrob-ranker
.venv/bin/python rank.py --candidates sample_candidates.json --out test_submission.csv --no-features
```

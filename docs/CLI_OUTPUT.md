# CLI Output Guide

Run the menu from the repo root:

```sh
python3 cli.py
```

## 1. Precompute features

Reads `candidates.jsonl`, extracts deterministic scoring features, and writes:

```text
candidate_features.npz
```

Expected CLI output:

```text
Precomputing features
Saved candidate_features.npz
```

Use this before the full ranker. The full ranker is fast because it reuses this feature file instead of rescoring every full candidate profile.

## 2. Run ranker (full 100K)

Reads:

```text
candidates.jsonl
candidate_features.npz
```

Writes:

```text
submission.csv
```

Expected CLI output:

```text
Done in 2.00s
Wrote 100 rows to submission.csv
Total runtime: 2.00s
Top 10 with reasoning:
...
```

After that, the CLI also shows a table with the top candidates from `submission.csv`.

The runtime is usually short because ranking loads compact precomputed arrays, selects the top 100, then streams `candidates.jsonl` only to fetch those selected candidate records for reasoning.

## 3. Run ranker (sample)

Reads:

```text
sample_candidates.json
```

Writes:

```text
test_submission.csv
```

Expected CLI output:

```text
Done in ...
Wrote 100 rows to test_submission.csv
Top 10 with reasoning:
...
```

After that, the CLI shows a table with the top candidates from `test_submission.csv`.

This option uses `--no-features`, so it scores candidates inline. It is for quick local testing, not the final 100K submission path.

## 4. Validate submission

Prompts for a CSV file and checks submission rules.

Expected success output:

```text
SUBMISSION VALID
```

Expected failure output:

```text
SUBMISSION INVALID
✗ ...
```

Use this after generating `submission.csv`.

## 5. Inspect candidate by ID

Prompts for a candidate ID like:

```text
CAND_0052328
```

Expected CLI output:

```text
Candidate Inspect
candidate_id
current_title
location
years
skill_match
career_quality
seniority_fit
location_score
availability
```

After the score panel, the CLI prints the candidate JSON fields. This is useful for checking why a candidate received a particular score.

## 6. Show top N from last submission

Reads whichever file is newer:

```text
submission.csv
test_submission.csv
```

Prompts for `N`, then prints a table:

```text
rank
candidate_id
score
current_title
location
reasoning
```

Use this when the ranker already ran and you only want to view the latest results.

## 7. Exit

Closes the CLI without changing files.

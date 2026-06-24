# Redrob Hackathon Ranker

Ranks the top 100 candidates from `candidates.jsonl` for the Senior AI Engineer JD and writes `submission.csv`.

## Setup

```sh
pip install -r requirements.txt
```

## Data

Place the full `candidates.jsonl` file in the repo root:

```text
redrob-ranker/candidates.jsonl
```

The file is gitignored and should not be committed.

## Precompute

```sh
python precompute.py --candidates candidates.jsonl --out candidate_features.npz
```

This streams `candidates.jsonl`, extracts deterministic scoring features, and saves the compact NumPy feature file used by the ranking step.

## Rank

```sh
python rank.py --candidates candidates.jsonl --features candidate_features.npz --out submission.csv
```

This writes `submission.csv` with columns `candidate_id,rank,score,reasoning`.

## Validate

```sh
python validate_submission.py submission.csv
```

## Development tools

```sh
python cli.py
```

The menu can precompute features, run the full or sample ranker, validate a CSV, inspect a candidate, and show the top rows from the latest submission file.

## Sandbox

```sh
streamlit run app.py
```

The sandbox accepts a small JSON candidate sample and shows ranked candidates with scores and deterministic reasoning.

## Architecture

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

`skill_match` is the largest component because the JD is specific to Python, embeddings, vector/hybrid search, and ranking evaluation. It checks both `skills[]` and career descriptions to avoid rewarding keyword stuffing.

`career_quality` rewards product-company and shipped-production evidence, especially search, ranking, retrieval, embeddings, scale, and external GitHub validation. Consulting-only, pure research-only, short-tenure, or unrelated CV/speech/robotics profiles are penalized.

`seniority_fit` targets the 5-9 year Senior AI Engineer band, with softer scores around the edges and penalties for pure management or architecture profiles without recent engineering work.

`location_score` prioritizes India target cities: Pune, Noida, Hyderabad, Mumbai, Delhi, Gurugram/Gurgaon, Bengaluru/Bangalore, and NCR. Relocation willingness helps but does not outrank a target-city match.

`availability` combines recent activity, recruiter response rate, interview completion, open-to-work flag, notice period, and offer acceptance signal.

`honeypot_penalty` discards impossible or suspicious profiles, including zero-duration expert stuffing, experience impossible from graduation year, and claimed role duration far above stated experience.

## Compute Profile

`rank.py` is designed for the challenge limit: under 5 minutes on CPU with 16GB RAM, no GPU, and no network. The precompute step may take longer, but the rank step only loads compact feature arrays, streams candidate records for the selected IDs, and writes the top 100 submission.

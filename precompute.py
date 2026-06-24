#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import numpy as np

from core.features import extract_features


def _final_score(features: dict[str, Any]) -> float:
    honeypot_penalty = 0.0 if features["is_honeypot"] else 1.0
    return float(
        (
            float(features["skill_match"]) * 0.35
            + float(features["career_quality"]) * 0.30
            + float(features["seniority_fit"]) * 0.15
            + float(features["location_score"]) * 0.10
            + float(features["availability"]) * 0.10
        )
        * honeypot_penalty
    )


def _iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSONL row: {exc}") from exc


def precompute(candidates_path: Path, out_path: Path) -> int:
    candidate_ids: list[str] = []
    skill_match: list[float] = []
    career_quality: list[float] = []
    seniority_fit: list[float] = []
    location_score: list[float] = []
    availability: list[float] = []
    is_honeypot: list[bool] = []
    final_score: list[float] = []

    started = time.perf_counter()
    for count, candidate in enumerate(_iter_jsonl(candidates_path), start=1):
        features = extract_features(candidate)
        candidate_ids.append(str(candidate["candidate_id"]))
        skill_match.append(float(features["skill_match"]))
        career_quality.append(float(features["career_quality"]))
        seniority_fit.append(float(features["seniority_fit"]))
        location_score.append(float(features["location_score"]))
        availability.append(float(features["availability"]))
        is_honeypot.append(bool(features["is_honeypot"]))
        final_score.append(_final_score(features))

        if count % 10000 == 0:
            elapsed = time.perf_counter() - started
            print(f"Processed {count} candidates in {elapsed:.1f}s")

    np.savez(
        out_path,
        candidate_ids=np.asarray(candidate_ids, dtype="U16"),
        skill_match=np.asarray(skill_match, dtype=np.float32),
        career_quality=np.asarray(career_quality, dtype=np.float32),
        seniority_fit=np.asarray(seniority_fit, dtype=np.float32),
        location_score=np.asarray(location_score, dtype=np.float32),
        availability=np.asarray(availability, dtype=np.float32),
        is_honeypot=np.asarray(is_honeypot, dtype=np.bool_),
        final_score=np.asarray(final_score, dtype=np.float32),
    )

    elapsed = time.perf_counter() - started
    print(f"Processed {len(candidate_ids)} candidates total")
    print(f"Saved features to {out_path}")
    print(f"Total time: {elapsed:.2f}s")
    return len(candidate_ids)


def main() -> None:
    parser = argparse.ArgumentParser(description="Precompute candidate scoring features.")
    parser.add_argument("--candidates", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    precompute(args.candidates, args.out)


if __name__ == "__main__":
    main()

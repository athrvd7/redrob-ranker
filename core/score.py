from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.features import _is_consulting_only, extract_features


def score_candidate(candidate: dict[str, Any]) -> float:
    features = extract_features(candidate)
    honeypot_penalty = 0.0 if features["is_honeypot"] else 1.0
    score = (
        float(features["skill_match"]) * 0.35
        + float(features["career_quality"]) * 0.30
        + float(features["seniority_fit"]) * 0.15
        + float(features["location_score"]) * 0.10
        + float(features["availability"]) * 0.10
    ) * honeypot_penalty
    return max(0.0, min(1.0, score))


def _load_sample_candidates() -> list[dict[str, Any]]:
    root = Path(__file__).resolve().parents[1]
    with (root / "sample_candidates.json").open(encoding="utf-8") as handle:
        return json.load(handle)


def _run_inline_test() -> None:
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    candidates = _load_sample_candidates()
    scored = []
    for candidate in candidates:
        features = extract_features(candidate)
        scored.append((score_candidate(candidate), candidate, features))

    scored.sort(key=lambda item: item[0], reverse=True)
    print(f"Scored {len(scored)} candidates")
    print("Top 10:")
    for rank, (score, candidate, features) in enumerate(scored[:10], start=1):
        print(
            f"{rank:02d}. {candidate['candidate_id']} score={score:.4f} "
            f"skill_match={features['skill_match']:.3f} "
            f"career_quality={features['career_quality']:.3f} "
            f"seniority={features['seniority_fit']:.3f} "
            f"location={features['location_score']:.3f} "
            f"availability={features['availability']:.3f}"
        )

    honeypots = [
        candidate["candidate_id"]
        for _, candidate, features in scored
        if features["is_honeypot"]
    ]
    consulting_only = [
        candidate["candidate_id"]
        for _, candidate, _ in scored
        if _is_consulting_only(candidate)
    ]
    print(f"Honeypots: {honeypots if honeypots else 'none'}")
    print(f"Consulting-only: {consulting_only if consulting_only else 'none'}")


if __name__ == "__main__":
    _run_inline_test()

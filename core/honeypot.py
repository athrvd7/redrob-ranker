from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path
from typing import Any


def _profile(candidate: dict[str, Any]) -> dict[str, Any]:
    return candidate.get("profile") or {}


def _skills(candidate: dict[str, Any]) -> list[dict[str, Any]]:
    return candidate.get("skills") or []


def _career_history(candidate: dict[str, Any]) -> list[dict[str, Any]]:
    return candidate.get("career_history") or []


def _education(candidate: dict[str, Any]) -> list[dict[str, Any]]:
    return candidate.get("education") or []


def _graduation_year(candidate: dict[str, Any]) -> int | None:
    years = [
        item.get("end_year")
        for item in _education(candidate)
        if isinstance(item.get("end_year"), int)
    ]
    return max(years) if years else None


def is_honeypot(candidate: dict[str, Any]) -> bool:
    zero_duration_experts = sum(
        1
        for skill in _skills(candidate)
        if str(skill.get("proficiency", "")).lower() == "expert"
        and skill.get("duration_months") == 0
    )
    if zero_duration_experts >= 5:
        return True

    years_of_experience = float(_profile(candidate).get("years_of_experience") or 0.0)
    graduation_year = _graduation_year(candidate)
    if graduation_year is not None:
        max_possible_experience = date.today().year - graduation_year + 2
        if years_of_experience > max_possible_experience:
            return True

    total_claimed_months = sum(
        int(role.get("duration_months") or 0) for role in _career_history(candidate)
    )
    if total_claimed_months > years_of_experience * 12 * 1.5:
        return True

    return False


def _load_sample_candidates() -> list[dict[str, Any]]:
    root = Path(__file__).resolve().parents[1]
    with (root / "sample_candidates.json").open(encoding="utf-8") as handle:
        return json.load(handle)


def _run_inline_test() -> None:
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    from core.features import _is_consulting_only, extract_features
    from core.score import score_candidate

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

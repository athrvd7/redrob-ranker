from __future__ import annotations

import json
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.honeypot import is_honeypot


PROFICIENCY_WEIGHTS = {
    "expert": 1.0,
    "advanced": 0.8,
    "intermediate": 0.5,
    "beginner": 0.2,
}

CONSULTING_FIRMS = {
    "tcs",
    "infosys",
    "wipro",
    "accenture",
    "cognizant",
    "capgemini",
    "hcl",
    "tech mahindra",
}

TARGET_CITIES = {
    "pune",
    "noida",
    "hyderabad",
    "mumbai",
    "delhi",
    "gurugram",
    "gurgaon",
    "bengaluru",
    "bangalore",
    "ncr",
}

EMBEDDING_TERMS = {
    "sentence-transformers",
    "sentence transformers",
    "bge",
    "e5",
    "openai embeddings",
    "embeddings",
    "embedding",
    "semantic search",
    "faiss",
}

VECTOR_TERMS = {
    "pinecone",
    "qdrant",
    "weaviate",
    "milvus",
    "opensearch",
    "open search",
    "elasticsearch",
    "elastic search",
    "faiss",
    "vector db",
    "vector database",
    "vector search",
    "hybrid search",
}

PYTHON_TERMS = {"python", "pyspark"}

EVAL_TERMS = {
    "ndcg",
    "mrr",
    "map",
    "a/b testing",
    "ab testing",
    "ranking evaluation",
    "ranking eval",
    "evaluation framework",
}

NICE_TO_HAVE_TERMS = {
    "lora",
    "qlora",
    "peft",
    "learning-to-rank",
    "learning to rank",
    "open-source",
    "open source",
}

PRODUCTION_TERMS = {
    "shipped",
    "production",
    "users",
    "scale",
    "scaled",
    "scalable",
    "launched",
    "deployed",
}

IR_TERMS = {
    "recommendation",
    "recommender",
    "search",
    "ranking",
    "retrieval",
    "embeddings",
    "embedding",
    "vector",
    "semantic",
    "information retrieval",
}

CV_SPEECH_ROBOTICS_TERMS = {
    "computer vision",
    "image classification",
    "object detection",
    "opencv",
    "yolo",
    "cnn",
    "speech",
    "tts",
    "robotics",
}


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _norm(value: Any) -> str:
    text = str(value or "").lower()
    text = text.replace("&", " and ")
    text = re.sub(r"[_/]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _contains_term(text: str, term: str) -> bool:
    normalized_text = _norm(text).replace("-", " ")
    normalized_term = _norm(term).replace("-", " ")
    if " " not in normalized_term:
        return bool(re.search(rf"(?<![a-z0-9]){re.escape(normalized_term)}(?![a-z0-9])", normalized_text))
    return normalized_term in normalized_text


def _contains_any(text: str, terms: set[str]) -> bool:
    return any(_contains_term(text, term) for term in terms)


def _profile(candidate: dict[str, Any]) -> dict[str, Any]:
    return candidate.get("profile") or {}


def _signals(candidate: dict[str, Any]) -> dict[str, Any]:
    return candidate.get("redrob_signals") or {}


def _skills(candidate: dict[str, Any]) -> list[dict[str, Any]]:
    return candidate.get("skills") or []


def _career_history(candidate: dict[str, Any]) -> list[dict[str, Any]]:
    return candidate.get("career_history") or []


def _career_description_text(candidate: dict[str, Any]) -> str:
    return " ".join(str(role.get("description") or "") for role in _career_history(candidate))


def _skill_text(candidate: dict[str, Any]) -> str:
    return " ".join(str(skill.get("name") or "") for skill in _skills(candidate))


def _skill_matches(skill_name: str, terms: set[str]) -> bool:
    return _contains_any(skill_name, terms)


def _category_skill_score(candidate: dict[str, Any], terms: set[str]) -> float:
    best = 0.0
    for skill in _skills(candidate):
        if not _skill_matches(str(skill.get("name") or ""), terms):
            continue
        score = PROFICIENCY_WEIGHTS.get(_norm(skill.get("proficiency")), 0.0)
        if skill.get("duration_months") == 0:
            score *= 0.45
        best = max(best, score)
    return best


def _category_score(candidate: dict[str, Any], terms: set[str]) -> float:
    skill_score = _category_skill_score(candidate, terms)
    description_has_evidence = _contains_any(_career_description_text(candidate), terms)
    score = skill_score * (0.35 if not description_has_evidence else 0.65)
    if description_has_evidence:
        score += 0.35
    return _clamp(score)


def _assessment_boost(candidate: dict[str, Any]) -> float:
    assessments = _signals(candidate).get("skill_assessment_scores") or {}
    relevant_categories = [
        EMBEDDING_TERMS,
        VECTOR_TERMS,
        PYTHON_TERMS,
        EVAL_TERMS,
        NICE_TO_HAVE_TERMS,
    ]
    matched = 0
    for name, score in assessments.items():
        if float(score or 0.0) < 70:
            continue
        if any(_contains_any(str(name), terms) for terms in relevant_categories):
            matched += 1
    return min(0.15, matched * 0.05)


def _nice_to_have_boost(candidate: dict[str, Any]) -> float:
    text = f"{_skill_text(candidate)} {_career_description_text(candidate)}"
    matched = sum(1 for term in NICE_TO_HAVE_TERMS if _contains_term(text, term))
    return min(0.10, matched * 0.035)


def _skill_match(candidate: dict[str, Any]) -> float:
    base = (
        _category_score(candidate, EMBEDDING_TERMS) * 0.30
        + _category_score(candidate, VECTOR_TERMS) * 0.30
        + _category_score(candidate, PYTHON_TERMS) * 0.25
        + _category_score(candidate, EVAL_TERMS) * 0.15
    )
    return _clamp(base + _assessment_boost(candidate) + _nice_to_have_boost(candidate))


def _company_name(role: dict[str, Any]) -> str:
    return _norm(role.get("company"))


def _is_named_consulting_firm(company: str) -> bool:
    normalized = _norm(company)
    return any(firm == normalized or firm in normalized for firm in CONSULTING_FIRMS)


def _is_services_role(role: dict[str, Any]) -> bool:
    industry = _norm(role.get("industry"))
    return (
        _is_named_consulting_firm(str(role.get("company") or ""))
        or "it services" in industry
        or "consulting" in industry
        or industry == "services"
    )


def _is_product_role(role: dict[str, Any]) -> bool:
    return not _is_services_role(role)


def _is_consulting_only(candidate: dict[str, Any]) -> bool:
    roles = _career_history(candidate)
    return bool(roles) and all(_is_named_consulting_firm(_company_name(role)) for role in roles)


def _is_research_only(candidate: dict[str, Any]) -> bool:
    roles = _career_history(candidate)
    if not roles:
        return False
    research_markers = ("research", "lab", "university", "academic", "scientist")
    return all(
        any(marker in _norm(role.get(field)) for field in ("company", "title", "industry", "description") for marker in research_markers)
        for role in roles
    )


def _career_quality(candidate: dict[str, Any]) -> float:
    roles = _career_history(candidate)
    if not roles:
        return 0.0

    total_months = sum(max(0, int(role.get("duration_months") or 0)) for role in roles)
    if total_months <= 0:
        product_fraction = 0.0
    else:
        product_months = sum(
            max(0, int(role.get("duration_months") or 0))
            for role in roles
            if _is_product_role(role)
        )
        product_fraction = product_months / total_months

    score = product_fraction * 0.55
    career_text = _career_description_text(candidate)

    if _contains_any(career_text, PRODUCTION_TERMS):
        score += 0.12
    if _contains_any(career_text, IR_TERMS):
        score += 0.18
    if float(_signals(candidate).get("github_activity_score") or 0.0) > 0:
        score += 0.08

    combined_text = f"{_skill_text(candidate)} {career_text} {_profile(candidate).get('summary', '')}"
    has_cv_speech_robotics = _contains_any(combined_text, CV_SPEECH_ROBOTICS_TERMS)
    has_nlp_or_ir = _contains_any(combined_text, IR_TERMS | {"nlp", "natural language"})
    if has_cv_speech_robotics and not has_nlp_or_ir:
        score *= 0.45

    avg_tenure = total_months / len(roles) if roles else 0.0
    if avg_tenure < 18:
        score *= 0.75

    if _is_research_only(candidate) and product_fraction == 0.0:
        score = min(score, 0.08)

    if _is_consulting_only(candidate):
        score = min(score, 0.12)

    return _clamp(score)


def _seniority_fit(candidate: dict[str, Any]) -> float:
    years = float(_profile(candidate).get("years_of_experience") or 0.0)
    if 5 <= years <= 9:
        score = 1.0
    elif 4 <= years <= 10:
        score = 0.8
    elif 3 <= years <= 11:
        score = 0.5
    elif years < 3:
        score = max(0.1, 0.5 - (3 - years) * 0.2)
    else:
        score = max(0.1, 0.5 - (years - 11) * 0.1)

    title = _norm(_profile(candidate).get("current_title"))
    management_terms = ("architect", "manager", "director", "head", "vp", "cto")
    engineer_terms = ("engineer", "developer", "scientist", "programmer")
    pure_management_or_architecture = any(term in title for term in management_terms) and not any(
        term in title for term in engineer_terms
    )
    if pure_management_or_architecture and not _has_recent_engineering_role(candidate):
        score *= 0.5

    return _clamp(score)


def _parse_date(value: Any) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except ValueError:
        return None


def _has_recent_engineering_role(candidate: dict[str, Any]) -> bool:
    cutoff = date.today() - timedelta(days=730)
    engineering_terms = ("engineer", "developer", "scientist", "programmer")
    for role in _career_history(candidate):
        title = _norm(role.get("title"))
        if not any(term in title for term in engineering_terms):
            continue
        end_date = _parse_date(role.get("end_date")) or date.today()
        if bool(role.get("is_current")) or end_date >= cutoff:
            return True
    return False


def _location_score(candidate: dict[str, Any]) -> float:
    profile = _profile(candidate)
    signals = _signals(candidate)
    country = _norm(profile.get("country"))
    location = _norm(profile.get("location"))
    in_target_city = any(city in location for city in TARGET_CITIES)
    willing_to_relocate = bool(signals.get("willing_to_relocate"))

    if country == "india" and in_target_city:
        return 1.0
    if country == "india" and willing_to_relocate:
        return 0.8
    if country == "india":
        return 0.5
    if willing_to_relocate:
        return 0.3
    return 0.05


def _availability(candidate: dict[str, Any]) -> float:
    signals = _signals(candidate)
    last_active = _parse_date(signals.get("last_active_date"))
    if last_active is None:
        recency = 0.0
    else:
        days_inactive = max(0, (date.today() - last_active).days)
        recency = max(0.0, 1.0 - days_inactive / 180)

    recruiter_response_rate = _clamp(float(signals.get("recruiter_response_rate") or 0.0))
    interview_completion_rate = _clamp(float(signals.get("interview_completion_rate") or 0.0))
    open_to_work = 1.0 if signals.get("open_to_work_flag") else 0.2
    notice_period_days = float(signals.get("notice_period_days") or 0.0)
    notice_score = 1.0 - min(notice_period_days, 90.0) / 90.0
    offer_acceptance_rate = signals.get("offer_acceptance_rate")
    offer_acceptance_rate = -1.0 if offer_acceptance_rate is None else float(offer_acceptance_rate)
    offer_acceptance_score = 1.0 if offer_acceptance_rate >= 0 else 0.5

    return _clamp(
        recency * 0.30
        + recruiter_response_rate * 0.20
        + interview_completion_rate * 0.15
        + open_to_work * 0.15
        + notice_score * 0.10
        + offer_acceptance_score * 0.10
    )


def extract_features(candidate: dict[str, Any]) -> dict[str, float | bool]:
    return {
        "skill_match": _skill_match(candidate),
        "career_quality": _career_quality(candidate),
        "seniority_fit": _seniority_fit(candidate),
        "location_score": _location_score(candidate),
        "availability": _availability(candidate),
        "is_honeypot": is_honeypot(candidate),
    }


def _load_sample_candidates() -> list[dict[str, Any]]:
    root = Path(__file__).resolve().parents[1]
    with (root / "sample_candidates.json").open(encoding="utf-8") as handle:
        return json.load(handle)


def _run_inline_test() -> None:
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

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

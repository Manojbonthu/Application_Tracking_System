from typing import List, Dict, Any


def generate_insights(
    final_score: float,
    matched_skills: List[str],
    missing_skills: List[str],
    partial_skills: List[str],
    experience_years: float,
    candidate_name: str = "Candidate",
    role_type: str = "experienced"
) -> Dict[str, Any]:
    """
    Generate human-readable insights for a candidate.
    Fully template-based — no LLM required.
    Explainable, deterministic, and fast.

    role_type: text input like "Fresher", "Senior", etc. — affects insight emphasis
    """

    # Intelligent role type detection from text input
    role_lower = role_type.lower() if role_type else ""
    is_fresher = any(word in role_lower for word in ["fresher", "junior", "entry", "trainee", "graduate", "beginner"])
    is_senior = any(word in role_lower for word in ["senior", "lead", "principal", "experienced", "expert", "architect"])

    # ---- Strengths ----
    strengths = []
    if matched_skills:
        top_matched = matched_skills[:5]
        strengths.append(f"Strong match in: {', '.join(top_matched)}.")
    if final_score >= 80:
        strengths.append("Highly aligned with the job requirements overall.")
    elif final_score >= 60:
        strengths.append("Good foundational alignment with the role.")

    # Role-specific strength emphasis
    if is_senior or not is_fresher:  # Default to experienced emphasis
        if experience_years >= 5:
            strengths.append(f"{int(experience_years)} years of experience — senior-level profile.")
        elif experience_years >= 2:
            strengths.append(f"{int(experience_years)} years of experience — mid-level profile.")
        elif experience_years > 0:
            strengths.append(f"{int(experience_years)} year(s) of experience — early-career profile.")
    else:  # Fresher role emphasis
        if matched_skills:
            strengths.append(f"Demonstrates solid grasp of {len(matched_skills)} key technologies.")
        if experience_years > 0:
            strengths.append(f"{int(experience_years)} year(s) of real-world experience — good foundation.")
        elif final_score >= 60:
            strengths.append("Strong learning potential — good candidate for junior role.")

    # ---- Skill Gaps ----
    gaps = []
    if missing_skills:
        top_missing = missing_skills[:5]
        gaps.append(f"Key skills not found: {', '.join(top_missing)}.")
    if partial_skills:
        top_partial = partial_skills[:3]
        gaps.append(f"Partial match (related but not exact): {', '.join(top_partial)}.")
    if not gaps:
        gaps.append("No significant skill gaps detected.")

    # ---- Suggestions (Role-aware) ----
    suggestions = []
    if is_senior or not is_fresher:  # Experienced role emphasis
        if final_score < 40:
            suggestions.append(
                "Profile significantly below threshold for this senior role. "
                "Consider for a more junior position."
            )
        elif missing_skills:
            suggestions.append(
                f"Recommend upskilling in: {', '.join(missing_skills[:3])} "
                f"to improve match for this experienced-level role."
            )
    else:  # Fresher role emphasis
        if final_score < 45 and missing_skills:
            suggestions.append(
                f"This is a learning opportunity. Focus on: {', '.join(missing_skills[:3])} "
                f"through courses or projects."
            )
        elif missing_skills:
            suggestions.append(
                f"Good starter role fit. Consider learning: {', '.join(missing_skills[:2])} "
                f"as next steps in career growth."
            )

    if partial_skills:
        suggestions.append(
            f"Deepen expertise in {', '.join(partial_skills[:2])} "
            f"to convert partial matches to full matches."
        )

    if final_score < 40:
        suggestions.append(
            "Profile significantly below threshold. "
            "Consider for a different role level."
        )
    elif final_score < 60:
        suggestions.append(
            "Consider for a technical screening call to assess depth in partially matched areas."
        )

    if not suggestions:
        suggestions.append("Strong candidate — proceed to interview.")

    # ---- Recommendation ----
    if final_score >= 80:
        recommendation = "🟢 Highly Recommended — Schedule Interview"
        recommendation_level = "high"
    elif final_score >= 65:
        recommendation = "🟡 Good Fit — Schedule Technical Round"
        recommendation_level = "medium"
    elif final_score >= 45:
        recommendation = "🟠 Moderate Fit — Review Manually"
        recommendation_level = "low"
    else:
        recommendation = "🔴 Below Threshold — Consider Rejecting"
        recommendation_level = "reject"

    return {
        "strengths": strengths,
        "skill_gaps": gaps,
        "suggestions": suggestions,
        "recommendation": recommendation,
        "recommendation_level": recommendation_level,
        "score_breakdown": {
            "final": round(final_score, 1),
            "matched_count": len(matched_skills),
            "missing_count": len(missing_skills),
            "partial_count": len(partial_skills),
        }
    }

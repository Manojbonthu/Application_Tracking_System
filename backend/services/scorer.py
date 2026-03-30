import numpy as np
from sentence_transformers import SentenceTransformer, util
from typing import List, Dict, Tuple
from services.nlp_processor import normalize_skill

# Load SBERT model once at startup — runs fully offline after first download
print("[Scorer] Loading sentence-transformers model (all-MiniLM-L6-v2)...")
_model = SentenceTransformer("all-MiniLM-L6-v2")
print("[Scorer] Model loaded.")

# Semantic similarity threshold for partial match
PARTIAL_MATCH_THRESHOLD = 0.65
EXACT_MATCH_THRESHOLD = 0.92


def encode_texts(texts: List[str]) -> np.ndarray:
    """Encode list of texts into embedding vectors."""
    return _model.encode(texts, convert_to_numpy=True, show_progress_bar=False)


def compute_semantic_score(jd_embedding: np.ndarray, resume_embedding: np.ndarray) -> float:
    """Cosine similarity between JD and resume. Returns 0-100."""
    score = float(util.cos_sim(jd_embedding, resume_embedding)[0][0])
    return round(max(0.0, min(1.0, score)) * 100, 2)


def compute_skill_scores(
    jd_skills: List[str],
    resume_skills: List[str]
) -> Tuple[float, List[str], List[str], List[str]]:
    """
    Compare JD skills against resume skills.
    Returns: (skill_score_0_100, matched, missing, partial)
    
    3 tiers:
    - Exact/synonym match → 1.0
    - Semantic similarity > PARTIAL_MATCH_THRESHOLD → 0.5 (partial)
    - No match → 0.0 (missing)
    """
    if not jd_skills:
        return (0.0, [], [], [])

    resume_set = {normalize_skill(s) for s in resume_skills}
    jd_normalized = [normalize_skill(s) for s in jd_skills]

    matched = []
    missing = []
    partial = []

    # Encode all skills for semantic comparison
    if jd_normalized and resume_skills:
        jd_embeddings = encode_texts(jd_normalized)
        resume_embeddings = encode_texts(list(resume_set))
        similarity_matrix = util.cos_sim(jd_embeddings, resume_embeddings).numpy()
    else:
        similarity_matrix = None

    total_score = 0.0
    for i, jd_skill in enumerate(jd_normalized):
        # Tier 1: Exact/synonym match
        if jd_skill in resume_set:
            matched.append(jd_skill)
            total_score += 1.0
            continue

        # Tier 2: Semantic similarity
        if similarity_matrix is not None and len(resume_set) > 0:
            best_sim = float(np.max(similarity_matrix[i]))
            if best_sim >= EXACT_MATCH_THRESHOLD:
                matched.append(jd_skill)
                total_score += 1.0
            elif best_sim >= PARTIAL_MATCH_THRESHOLD:
                partial.append(jd_skill)
                total_score += 0.5
            else:
                missing.append(jd_skill)
        else:
            missing.append(jd_skill)

    skill_score = (total_score / len(jd_normalized)) * 100
    return (round(skill_score, 2), matched, missing, partial)


def compute_experience_score(resume_years: float, jd_text: str) -> float:
    """
    Compare candidate experience against JD requirement.
    Extracts required years from JD and computes normalized score.
    """
    import re

    # Extract required years from JD
    patterns = [
        r"(\d+)\+?\s*years?\s*(?:of\s*)?(?:experience|exp)",
        r"minimum\s+(\d+)\s*years?",
        r"at\s+least\s+(\d+)\s*years?",
    ]
    required_years = None
    for pattern in patterns:
        match = re.search(pattern, jd_text, re.IGNORECASE)
        if match:
            try:
                required_years = float(match.group(1))
                break
            except ValueError:
                continue

    if required_years is None or required_years == 0:
        # No explicit requirement — treat 3+ years as full score
        required_years = 3.0

    if resume_years >= required_years:
        return 100.0
    elif resume_years == 0:
        return 20.0  # Fresher baseline
    else:
        return round((resume_years / required_years) * 100, 2)


def compute_final_score(
    semantic_score: float,
    skill_score: float,
    experience_score: float,
    weights: Dict[str, float] = None
) -> float:
    """
    Weighted formula:
    final = semantic(0.40) + skill(0.50) + experience(0.10)
    Weights are configurable via the `weights` parameter.
    """
    if weights is None:
        weights = {"semantic": 0.40, "skill": 0.50, "experience": 0.10}

    final = (
        semantic_score * weights["semantic"]
        + skill_score * weights["skill"]
        + experience_score * weights["experience"]
    )
    return round(min(100.0, max(0.0, final)), 2)


def score_all_candidates(
    jd_text: str,
    jd_skills: List[str],
    candidates: List[Dict],
    role_type: str = "experienced"
) -> List[Dict]:
    """
    Main scoring entry point.
    candidates: list of dicts with keys: resume_id, resume_text, skills, experience_years
    role_type: text input like "Fresher", "Senior", "Mid-level", "Junior", "Experienced", etc.

    Weight distribution automatically detected from role_type text:
    - Fresher/Junior: semantic=0.35, skill=0.40, experience=0.25
    - Senior/Lead/Experienced: semantic=0.30, skill=0.30, experience=0.40
    - Mid-level/Regular: semantic=0.35, skill=0.35, experience=0.30

    Returns list of dicts with all scores added.
    """
    if not candidates:
        return []

    # Intelligent role type detection from text input
    role_lower = role_type.lower() if role_type else ""

    # Check for fresher/junior roles
    if any(word in role_lower for word in ["fresher", "junior", "entry", "trainee", "graduate", "beginner"]):
        weights = {"semantic": 0.35, "skill": 0.40, "experience": 0.25}
        print(f"[Scorer] Detected FRESHER role: {role_type}")
    # Check for senior/experienced roles
    elif any(word in role_lower for word in ["senior", "lead", "principal", "experienced", "expert", "architect"]):
        weights = {"semantic": 0.30, "skill": 0.30, "experience": 0.40}
        print(f"[Scorer] Detected SENIOR role: {role_type}")
    # Default to mid-level
    else:
        weights = {"semantic": 0.35, "skill": 0.35, "experience": 0.30}
        print(f"[Scorer] Detected MID-LEVEL role: {role_type}")

    # RAG Retrieval — encode JD + all resume texts simultaneously
    jd_embedding = encode_texts([jd_text])[0]
    resume_texts = [c["resume_text"] for c in candidates]
    resume_embeddings = encode_texts(resume_texts)

    results = []
    for i, candidate in enumerate(candidates):
        # Semantic score (RAG retrieval layer)
        semantic_score = compute_semantic_score(jd_embedding, resume_embeddings[i])

        # Skill score (augmented processing layer)
        skill_score, matched, missing, partial = compute_skill_scores(
            jd_skills, candidate["skills"]
        )

        # Experience score
        exp_score = compute_experience_score(
            candidate.get("experience_years", 0.0), jd_text
        )

        # Final weighted score with role-type weights
        final = compute_final_score(semantic_score, skill_score, exp_score, weights)

        results.append({
            "resume_id": candidate["resume_id"],
            "semantic_score": semantic_score,
            "skill_score": skill_score,
            "experience_score": exp_score,
            "final_score": final,
            "matched_skills": matched,
            "missing_skills": missing,
            "partial_skills": partial,
        })

    return results

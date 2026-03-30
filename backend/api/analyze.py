from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Resume, Skill, JobDescription, MatchResult
from schemas import AnalyzeRequest, AnalyzeResponse
from services.nlp_processor import extract_skills_from_text
from services.pdf_extractor import extract_experience_years
from services.scorer import score_all_candidates
from services.ranker import rank_candidates
from services.insight_generator import generate_insights

router = APIRouter()


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest, db: Session = Depends(get_db)):
    """
    Submit a Job Description + list of resume IDs to analyze.
    Runs the full pipeline:
      1. Extract JD skills
      2. Load resumes from DB
      3. Score all candidates (semantic + skill + experience)
      4. Rank candidates
      5. Generate insights
      6. Store match_results in PostgreSQL
    """
    if not request.resume_ids:
        raise HTTPException(status_code=400, detail="No resume IDs provided.")
    if not request.jd_text.strip():
        raise HTTPException(status_code=400, detail="Job description text is empty.")

    # 1. Extract JD skills
    jd_skills = extract_skills_from_text(request.jd_text)

    # 2. Save JD to DB
    jd = JobDescription(
        title=request.job_title,
        jd_text=request.jd_text,
        extracted_skills=jd_skills,
    )
    db.add(jd)
    db.flush()

    # 3. Load resumes
    resumes = db.query(Resume).filter(Resume.id.in_(request.resume_ids)).all()
    if not resumes:
        raise HTTPException(status_code=404, detail="No resumes found for given IDs.")

    # Build candidate dicts for scorer
    candidates = []
    for resume in resumes:
        resume_skills = [s.skill_name for s in resume.skills]
        exp_years = extract_experience_years(resume.raw_text)
        candidates.append({
            "resume_id": resume.id,
            "resume_text": resume.raw_text,
            "skills": resume_skills,
            "experience_years": exp_years,
        })

    # 4. Score all candidates with role_type weighting
    role_type = request.role_type or "experienced"
    scored = score_all_candidates(request.jd_text, jd_skills, candidates, role_type=role_type)

    # 5. Rank candidates
    ranked = rank_candidates(scored)

    # 6. Generate insights + store in DB
    resume_map = {r.id: r for r in resumes}
    exp_map = {c["resume_id"]: c["experience_years"] for c in candidates}

    for candidate_score in ranked:
        rid = candidate_score["resume_id"]
        resume = resume_map.get(rid)
        exp_years = exp_map.get(rid, 0.0)

        insights = generate_insights(
            final_score=candidate_score["final_score"],
            matched_skills=candidate_score["matched_skills"],
            missing_skills=candidate_score["missing_skills"],
            partial_skills=candidate_score["partial_skills"],
            experience_years=exp_years,
            candidate_name=resume.name or "Candidate",
            role_type=role_type,
        )

        match_result = MatchResult(
            job_id=jd.id,
            resume_id=rid,
            final_score=candidate_score["final_score"],
            semantic_score=candidate_score["semantic_score"],
            skill_score=candidate_score["skill_score"],
            experience_score=candidate_score["experience_score"],
            rank=candidate_score["rank"],
            matched_skills=candidate_score["matched_skills"],
            missing_skills=candidate_score["missing_skills"],
            partial_skills=candidate_score["partial_skills"],
            insights=insights,
        )
        db.add(match_result)

    db.commit()
    print(f"[Analyze] Job ID {jd.id}: Processed {len(ranked)} candidates (role_type: {role_type}).")

    return AnalyzeResponse(
        job_id=jd.id,
        message=f"Analysis complete. {len(ranked)} candidates ranked.",
        total_processed=len(ranked),
    )


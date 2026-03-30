from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from database import get_db
from models import Resume, JobDescription, MatchResult, Skill
from schemas import ResultsResponse, CandidateResult, CandidateDetail, JobListItem

router = APIRouter()


@router.get("/results/{job_id}", response_model=ResultsResponse)
def get_results(
    job_id: int,
    limit: Optional[int] = Query(None, description="Top N candidates (5, 10, 20, or all)"),
    db: Session = Depends(get_db),
):
    """Get ranked candidates for a specific job."""
    jd = db.query(JobDescription).filter(JobDescription.id == job_id).first()
    if not jd:
        raise HTTPException(status_code=404, detail="Job not found.")

    query = (
        db.query(MatchResult)
        .filter(MatchResult.job_id == job_id)
        .order_by(MatchResult.rank)
    )
    if limit and limit > 0:
        query = query.limit(limit)

    results = query.all()

    candidates = []
    for r in results:
        resume = db.query(Resume).filter(Resume.id == r.resume_id).first()
        candidates.append(
            CandidateResult(
                rank=r.rank,
                resume_id=r.resume_id,
                candidate_name=resume.name or f"Candidate #{r.resume_id}",
                file_name=resume.file_name,
                final_score=r.final_score,
                semantic_score=r.semantic_score or 0.0,
                skill_score=r.skill_score or 0.0,
                experience_score=r.experience_score or 0.0,
                matched_skills=r.matched_skills or [],
                missing_skills=r.missing_skills or [],
                partial_skills=r.partial_skills or [],
                insights=r.insights or {},
            )
        )

    return ResultsResponse(
        job_id=job_id,
        job_title=jd.title or "Untitled Job",
        total_candidates=len(candidates),
        candidates=candidates,
    )


@router.get("/candidate/{resume_id}/job/{job_id}", response_model=CandidateDetail)
def get_candidate_detail(resume_id: int, job_id: int, db: Session = Depends(get_db)):
    """Get full candidate detail for a specific job match."""
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found.")

    match = (
        db.query(MatchResult)
        .filter(MatchResult.resume_id == resume_id, MatchResult.job_id == job_id)
        .first()
    )
    if not match:
        raise HTTPException(status_code=404, detail="Match result not found.")

    all_skills = [s.skill_name for s in db.query(Skill).filter(Skill.resume_id == resume_id).all()]

    return CandidateDetail(
        resume_id=resume.id,
        candidate_name=resume.name or f"Candidate #{resume.id}",
        email=resume.email,
        phone=resume.phone,
        file_name=resume.file_name,
        all_skills=all_skills,
        final_score=match.final_score,
        semantic_score=match.semantic_score or 0.0,
        skill_score=match.skill_score or 0.0,
        experience_score=match.experience_score or 0.0,
        matched_skills=match.matched_skills or [],
        missing_skills=match.missing_skills or [],
        partial_skills=match.partial_skills or [],
        insights=match.insights or {},
    )


@router.get("/jobs", response_model=List[JobListItem])
def list_jobs(db: Session = Depends(get_db)):
    """List all previously analyzed job descriptions."""
    jobs = db.query(JobDescription).order_by(JobDescription.created_at.desc()).all()
    result = []
    for job in jobs:
        count = db.query(MatchResult).filter(MatchResult.job_id == job.id).count()
        result.append(
            JobListItem(
                id=job.id,
                title=job.title or "Untitled",
                created_at=job.created_at,
                total_candidates=count,
            )
        )
    return result


@router.delete("/job/{job_id}")
def delete_job(job_id: int, db: Session = Depends(get_db)):
    """Delete a job analysis and all its associated match results."""
    jd = db.query(JobDescription).filter(JobDescription.id == job_id).first()
    if not jd:
        raise HTTPException(status_code=404, detail="Job not found.")

    # Delete all match results for this job (cascade)
    match_results = db.query(MatchResult).filter(MatchResult.job_id == job_id).all()
    for result in match_results:
        db.delete(result)

    # Delete the job description
    db.delete(jd)
    db.commit()

    print(f"[Delete] Job ID {job_id} deleted with {len(match_results)} match results.")
    return {"message": f"Job analysis deleted successfully. {len(match_results)} match results removed."}


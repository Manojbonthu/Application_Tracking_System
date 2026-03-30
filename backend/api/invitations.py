from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime
from database import get_db
from models import MatchResult, Resume, JobDescription, ShortlistEmail
from services.email_service import generate_email_body, send_email
from pydantic import BaseModel

router = APIRouter()


class SendShortlistRequest(BaseModel):
    job_id: int
    top_n: int = 10  # HR picks this — 5, 10, 15, 20


def process_and_send_emails(job_id: int, top_n: int, db: Session):
    """
    Background task — runs after API returns response.
    Picks top N candidates, generates personalized emails,
    sends via Gmail, stores results in DB.
    """
    # Get job details
    job = db.query(JobDescription).filter(JobDescription.id == job_id).first()
    if not job:
        return

    # Get top N candidates by final_score
    top_candidates = (
        db.query(MatchResult)
        .filter(MatchResult.job_id == job_id)
        .order_by(MatchResult.final_score.desc())
        .limit(top_n)
        .all()
    )

    for match in top_candidates:
        resume = db.query(Resume).filter(Resume.id == match.resume_id).first()
        if not resume or not resume.email:
            # No email found — log as failed
            log = ShortlistEmail(
                job_id=job_id,
                resume_id=match.resume_id,
                candidate_name=resume.name if resume else "Unknown",
                candidate_email=None,
                email_subject=None,
                email_body=None,
                status="failed",
                error_message="No email address found in resume",
            )
            db.add(log)
            db.commit()
            continue

        # Generate personalized email
        subject, body = generate_email_body(
            candidate_name=resume.name or "Candidate",
            job_title=job.title or "the role",
            matched_skills=match.matched_skills or [],
        )

        # Store in DB before sending
        log = ShortlistEmail(
            job_id=job_id,
            resume_id=match.resume_id,
            candidate_name=resume.name,
            candidate_email=resume.email,
            email_subject=subject,
            email_body=body,
            status="pending",
        )
        db.add(log)
        db.flush()

        # Send email
        result = send_email(resume.email, subject, body)

        # Update status
        log.status = result["status"]
        log.error_message = result["error"]
        if result["status"] == "sent":
            log.sent_at = datetime.utcnow()

        db.commit()
        print(f"[Email] {resume.name} → {resume.email} — {result['status']}")


@router.post("/send-shortlist")
async def send_shortlist_emails(
    request: SendShortlistRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    HR calls this endpoint with job_id and top_n.
    API returns immediately, emails send in background.
    """
    # Validate job exists
    job = db.query(JobDescription).filter(JobDescription.id == request.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    # Check candidate count
    total = db.query(MatchResult).filter(MatchResult.job_id == request.job_id).count()
    if total == 0:
        raise HTTPException(status_code=400, detail="No candidates found for this job.")

    actual_n = min(request.top_n, total)

    # Fire background task — API returns immediately
    background_tasks.add_task(process_and_send_emails, request.job_id, actual_n, db)

    return {
        "message": f"Sending shortlist emails to top {actual_n} candidates in background.",
        "job_id": request.job_id,
        "emails_queued": actual_n,
    }


@router.get("/shortlist-history/{job_id}")
def get_shortlist_history(job_id: int, db: Session = Depends(get_db)):
    """Get all sent emails for a job."""
    logs = (
        db.query(ShortlistEmail)
        .filter(ShortlistEmail.job_id == job_id)
        .order_by(ShortlistEmail.created_at.desc())
        .all()
    )
    return [
        {
            "candidate_name": l.candidate_name,
            "candidate_email": l.candidate_email,
            "subject": l.email_subject,
            "status": l.status,
            "sent_at": l.sent_at,
            "error": l.error_message,
        }
        for l in logs
    ]
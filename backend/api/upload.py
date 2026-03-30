import os
import shutil
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from database import get_db
from models import Resume, Skill
from schemas import UploadResponse
from services.pdf_extractor import (
    extract_text_from_pdf,
    extract_text_from_txt,
    extract_contact_info,
    extract_experience_years,
)
from services.nlp_processor import extract_skills_with_source
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _sanitize_text_for_db(text: Optional[str]) -> Optional[str]:
    """Drop NUL chars before writing into SQL TEXT columns."""
    if text is None:
        return None
    return text.replace("\x00", "")


@router.post("/upload", response_model=UploadResponse)
async def upload_resumes(
    files: List[UploadFile] = File(...),
    folder_name: Optional[str] = Form(None),   # ← sent by frontend automatically
    db: Session = Depends(get_db),
):
    """
    Upload multiple resume files (PDF or TXT).
    folder_name is sent by the frontend — either the OS folder name (folder mode)
    or None for single file uploads.
    Files are stored under uploads/<folder_name>/ or uploads/ for singles.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided.")

    # Sanitize folder name
    if folder_name:
        folder_name = folder_name.strip().replace("..", "").replace("/", "").replace("\\", "")
    
    # Determine storage path
    if folder_name:
        save_dir = os.path.join(UPLOAD_DIR, folder_name)
    else:
        save_dir = UPLOAD_DIR
    os.makedirs(save_dir, exist_ok=True)

    resume_ids = []

    for upload_file in files:
        filename = upload_file.filename or "unknown.pdf"
        # Strip any path prefix from browser (webkitdirectory sends "folder/file.pdf")
        filename = os.path.basename(filename)
        ext = os.path.splitext(filename)[1].lower()

        if ext not in (".pdf", ".txt"):
            print(f"[Upload] Skipping unsupported file: {filename}")
            continue

        # Save to disk under the correct folder
        save_path = os.path.join(save_dir, filename)
        with open(save_path, "wb") as f:
            content = await upload_file.read()
            f.write(content)

        # Extract raw text
        if ext == ".pdf":
            raw_text = extract_text_from_pdf(save_path)
        else:
            raw_text = extract_text_from_txt(save_path)

        raw_text = _sanitize_text_for_db(raw_text)
        if not raw_text or not raw_text.strip():
            print(f"[Upload] Empty/sanitized text from {filename}, skipping.")
            continue

        # Extract contact info
        contact = extract_contact_info(raw_text)

        # Save resume to DB — store folder_name so we can group/delete by folder
        resume = Resume(
            name=_sanitize_text_for_db(contact.get("name")),
            email=_sanitize_text_for_db(contact.get("email")),
            phone=_sanitize_text_for_db(contact.get("phone")),
            raw_text=raw_text,
            file_name=_sanitize_text_for_db(filename),
            folder_name=_sanitize_text_for_db(folder_name),   # ← stored in DB
        )

        try:
            db.add(resume)
            db.flush()

            # Extract and save skills
            skills_data = extract_skills_with_source(raw_text)
            for skill_info in skills_data:
                skill = Skill(
                    resume_id=resume.id,
                    skill_name=_sanitize_text_for_db(skill_info.get("skill_name")),
                    source=_sanitize_text_for_db(skill_info.get("source")),
                )
                db.add(skill)

            db.commit()
            db.refresh(resume)
            resume_ids.append(resume.id)
            print(f"[Upload] Processed: {filename} (folder: {folder_name or 'root'}) → Resume ID {resume.id}")

        except Exception as e:
            db.rollback()
            print(f"[Upload] Database error for {filename}: {e}")
            continue

    if not resume_ids:
        raise HTTPException(
            status_code=400, detail="No valid resume files could be processed."
        )

    return UploadResponse(
        message=f"Successfully uploaded and processed {len(resume_ids)} resume(s).",
        resume_ids=resume_ids,
        total_uploaded=len(resume_ids),
        folder_name=folder_name,
    )


@router.delete("/resume/{resume_id}")
def delete_resume(resume_id: int, db: Session = Depends(get_db)):
    """
    Delete a single resume from DB and disk.
    """
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found.")

    # Delete file from disk
    if resume.folder_name:
        file_path = os.path.join(UPLOAD_DIR, resume.folder_name, resume.file_name)
    else:
        file_path = os.path.join(UPLOAD_DIR, resume.file_name)

    if os.path.exists(file_path):
        os.remove(file_path)
        print(f"[Delete] Removed file: {file_path}")

    # DB cascade deletes skills + match_results
    db.delete(resume)
    db.commit()
    print(f"[Delete] Resume ID {resume_id} deleted from DB.")
    return {"message": f"Resume {resume_id} deleted successfully."}


@router.delete("/folder/{folder_name}")
def delete_folder(folder_name: str, db: Session = Depends(get_db)):
    """
    Delete all resumes in a folder from DB and disk.
    """
    folder_name = folder_name.strip()
    resumes = db.query(Resume).filter(Resume.folder_name == folder_name).all()

    if not resumes:
        raise HTTPException(status_code=404, detail="No resumes found for this folder.")

    # Delete all DB records (cascade handles skills + match_results)
    for resume in resumes:
        db.delete(resume)

    db.commit()

    # Delete folder from disk
    folder_path = os.path.join(UPLOAD_DIR, folder_name)
    if os.path.exists(folder_path):
        shutil.rmtree(folder_path)
        print(f"[Delete] Removed folder: {folder_path}")

    print(f"[Delete] Folder '{folder_name}' — {len(resumes)} resumes deleted from DB.")
    return {"message": f"Folder '{folder_name}' and {len(resumes)} resumes deleted."}


@router.get("/resume/{resume_id}/download")
def download_resume(resume_id: int, db: Session = Depends(get_db)):
    """
    Download or preview a resume file by resume ID.
    """
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found.")

    # Construct file path
    if resume.folder_name:
        file_path = os.path.join(UPLOAD_DIR, resume.folder_name, resume.file_name)
    else:
        file_path = os.path.join(UPLOAD_DIR, resume.file_name)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Resume file not found on disk.")

    return FileResponse(
        path=file_path,
        filename=resume.file_name,
        media_type="application/pdf" if resume.file_name.endswith(".pdf") else "text/plain"
    )

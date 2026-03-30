from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime


class UploadResponse(BaseModel):
    message: str
    resume_ids: List[int]
    total_uploaded: int
    folder_name: Optional[str] = None   # ← NEW


class AnalyzeRequest(BaseModel):
    job_title: str
    jd_text: str
    resume_ids: List[int]
    role_type: Optional[str] = "experienced"  # "experienced" or "fresher"


class AnalyzeResponse(BaseModel):
    job_id: int
    message: str
    total_processed: int


class SkillOut(BaseModel):
    skill_name: str
    source: str

    class Config:
        from_attributes = True


class CandidateResult(BaseModel):
    rank: int
    resume_id: int
    candidate_name: str
    file_name: str
    final_score: float
    semantic_score: float
    skill_score: float
    experience_score: float
    matched_skills: List[str]
    missing_skills: List[str]
    partial_skills: List[str]
    insights: Dict[str, Any]

    class Config:
        from_attributes = True


class ResultsResponse(BaseModel):
    job_id: int
    job_title: str
    total_candidates: int
    candidates: List[CandidateResult]


class CandidateDetail(BaseModel):
    resume_id: int
    candidate_name: str
    email: Optional[str]
    phone: Optional[str]
    file_name: str
    all_skills: List[str]
    final_score: float
    semantic_score: float
    skill_score: float
    experience_score: float
    matched_skills: List[str]
    missing_skills: List[str]
    partial_skills: List[str]
    insights: Dict[str, Any]


class JobListItem(BaseModel):
    id: int
    title: str
    created_at: datetime
    total_candidates: int

    class Config:
        from_attributes = True

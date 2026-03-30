from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class Resume(Base):
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    raw_text = Column(Text, nullable=False)
    file_name = Column(String(255), nullable=False)
    folder_name = Column(String(255), nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    skills = relationship("Skill", back_populates="resume", cascade="all, delete")
    match_results = relationship("MatchResult", back_populates="resume", cascade="all, delete")


class Skill(Base):
    __tablename__ = "skills"

    id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=False)
    skill_name = Column(String(255), nullable=False)
    source = Column(String(50), nullable=True)

    resume = relationship("Resume", back_populates="skills")


class JobDescription(Base):
    __tablename__ = "job_descriptions"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=True)
    jd_text = Column(Text, nullable=False)
    extracted_skills = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    match_results = relationship("MatchResult", back_populates="job", cascade="all, delete")


class MatchResult(Base):
    __tablename__ = "match_results"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("job_descriptions.id"), nullable=False)
    resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=False)
    final_score = Column(Float, nullable=False)
    semantic_score = Column(Float, nullable=True)
    skill_score = Column(Float, nullable=True)
    experience_score = Column(Float, nullable=True)
    rank = Column(Integer, nullable=True)
    matched_skills = Column(JSONB, nullable=True)
    missing_skills = Column(JSONB, nullable=True)
    partial_skills = Column(JSONB, nullable=True)
    insights = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    job = relationship("JobDescription", back_populates="match_results")
    resume = relationship("Resume", back_populates="match_results")


class ShortlistEmail(Base):
    __tablename__ = "shortlist_emails"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("job_descriptions.id"), nullable=False)
    resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=False)
    candidate_name = Column(String(255), nullable=True)
    candidate_email = Column(String(255), nullable=True)
    email_subject = Column(String(500), nullable=True)
    email_body = Column(Text, nullable=True)
    status = Column(String(50), default="pending")
    error_message = Column(Text, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    job = relationship("JobDescription")
    resume = relationship("Resume")
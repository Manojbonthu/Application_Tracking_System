# AI-Powered Applicant Tracking System (ATS)

A production-grade ATS using semantic resume matching, NLP skill extraction, and a weighted scoring engine — no paid APIs, fully offline AI.

---

## Project Overview

This system allows HR teams to upload a folder of candidate resumes (PDF/TXT), paste a job description, and automatically rank all candidates by how well they match the role. Each candidate receives a final score, matched/missing skills breakdown, and a hiring recommendation — all powered by offline AI with no external API costs.

**Key capabilities:**
- Upload and parse hundreds of resumes in one click
- Extract skills using 3 simultaneous NLP methods
- Semantic matching that understands "ML ≈ Machine Learning"
- Weighted scoring formula with role-level adjustment
- Personalized shortlist emails sent directly to candidates via Gmail
- Full analysis history stored in PostgreSQL

---

## Features Implemented

### Resume Management
- Upload single, multiple, or entire folder of PDF/TXT resumes
- Auto-extract candidate name, email, phone via regex
- Drag-and-drop upload zone with file preview
- Resume session history in sidebar — click to reuse without re-uploading
- Delete resumes from storage and database

### AI Analysis Pipeline
- 3-method NLP skill extraction: PhraseMatcher + context patterns + section parsing
- SBERT semantic encoding (all-MiniLM-L6-v2, 384-dim vectors)
- Cosine similarity for semantic score
- 3-tier skill matching: exact / synonym / partial
- Experience extraction via regex
- Role-type weight adjustment (fresher / mid / senior)
- Template-based insight generation per candidate

### Results Dashboard
- Ranked candidate table with scores, matched/missing skills
- Filter by All / Top 5 / Top 10 / Top 20
- Per-candidate modal: full score breakdown, skill tags, strengths, gaps, suggestions
- Direct resume PDF download per candidate
- Stats row: average score, top score, strong matches count

### Shortlist Email System
- HR selects Top 1 / 2 / 3 / 5 / 10 / 20 / 30 / 50 / All
- Personalized email per candidate — name, job title, matched skills auto-inserted
- Gmail SMTP sending via App Password (no third-party service)
- All emails stored in PostgreSQL before sending (full audit trail)
- Background sending — API responds immediately, emails deliver async
- Failed sends tracked with error messages

### History
- All past job analyses stored in PostgreSQL
- Click any past job to reload its full ranked results
- Delete individual job analyses

---

## Design Approach

### Offline-First AI
All AI models run locally after the first download — no OpenAI, no paid APIs, no internet dependency at runtime. sentence-transformers and spaCy models are loaded once at startup and reused across all requests.

### Weighted Scoring Formula
```
final_score = (semantic_score  × 0.40)
            + (skill_score     × 0.50)
            + (experience_score × 0.10)
```
Skill match carries the highest weight (50%) because precise skill alignment is the most reliable hiring signal. Semantic score (40%) handles vocabulary variations. Experience (10%) is a tiebreaker.

### Role-Type Weight Adjustment
Weights shift automatically based on the role level entered by HR:

| Role Type | Semantic | Skill | Experience |
|-----------|----------|-------|------------|
| Fresher | 45% | 55% | 0% |
| Mid-level | 40% | 50% | 10% |
| Senior / Lead | 30% | 30% | 40% |

### 3-Method Skill Extraction
Running all three methods simultaneously maximizes recall:
- **PhraseMatcher** — fastest, catches taxonomy-listed skills verbatim
- **Context patterns** — catches skills after trigger phrases like "proficient in"
- **Section parsing** — directly targets the Skills section of the resume

### Template-Based Insights
Insights are generated from templates using the candidate's actual data — no LLM, no hallucinations, fully auditable output. Strengths, gaps, and suggestions are deterministic.

### Runtime Taxonomy
The `skills_taxonomy.json` file is loaded at startup. New skills can be added without touching any Python code — just edit the JSON and restart.

---

## Assumptions

1. **Resumes are in PDF or TXT format.** Other formats (Word, image scans) are not supported. Scanned PDFs without text layers will extract empty or partial text.

2. **Candidate email is present in the resume.** The shortlist email feature requires a valid email address extractable from the PDF. If not found, the send is logged as failed.

3. **Gmail App Password is configured correctly.** The sender Gmail account must have 2-Step Verification enabled and an App Password generated. Regular Gmail passwords do not work with SMTP.

4. **PostgreSQL is running locally.** The backend expects a PostgreSQL instance at the `DATABASE_URL` specified in `.env`. SQLite is not supported due to JSONB column usage.

5. **spaCy model is downloaded before first run.** The `en_core_web_sm` model must be downloaded manually via `python -m spacy download en_core_web_sm` before starting the backend.

6. **Skills in the taxonomy are English.** The NLP pipeline is built for English-language resumes. Non-English resumes will have significantly lower skill extraction accuracy.

7. **Job description is pasted as plain text.** The analyze endpoint accepts raw text only — PDF or Word JDs must be copied and pasted manually.

8. **Local deployment only (default config).** CORS is set to `allow_origins=["*"]` for local development. This must be restricted to specific origins before any production deployment.

9. **Role level is entered by HR manually.** The system does not auto-detect seniority from the JD — HR must enter "fresher", "mid-level", or "senior" to trigger the correct weight adjustment.

10. **Gmail daily limit applies.** Free Gmail accounts can send up to 500 emails per day. For large-scale hiring (500+ candidates/day), a Google Workspace account is recommended.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | HTML + CSS + Vanilla JS |
| Backend | FastAPI + Uvicorn |
| Database | PostgreSQL + SQLAlchemy |
| PDF Parsing | pdfplumber |
| NLP Extraction | spaCy + PhraseMatcher |
| Semantic Matching | sentence-transformers (all-MiniLM-L6-v2) |
| Vector Math | numpy |
| Email Sending | Gmail SMTP + smtplib |

---

## How to Run the Project

### Prerequisites
- Python 3.10+
- PostgreSQL running locally
- Gmail account with 2-Step Verification + App Password (for email feature)

### Step 1 — PostgreSQL Setup
```bash
psql -U postgres -c "CREATE DATABASE ats_db;"
```

### Step 2 — Backend Setup
```bash
cd backend

# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Download spaCy model
python -m spacy download en_core_web_sm

# Configure environment
cp .env.example .env
```

Edit `.env`:
```env
DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/ats_db
UPLOAD_DIR=uploads
GMAIL_SENDER=youremail@gmail.com
GMAIL_APP_PASSWORD=yourapppassword
GMAIL_SENDER_NAME=HR Team ATS
```

```bash
# Start backend
python main.py
# Backend runs at http://localhost:8000
# Swagger docs at http://localhost:8000/docs
```

### Step 3 — Frontend Setup
No build step needed:
```bash
cd frontend
# Option 1: Open index.html directly in browser
# Option 2: Python static server
python -m http.server 3000
# Option 3: VS Code Live Server extension
```

### Step 4 — Using the System
1. Open `http://localhost:3000` (or open `index.html` directly)
2. **Upload Resumes** → select PDF files or entire folder → click Upload
3. **Analyze JD** → enter job title, role level, paste job description → Run AI Analysis
4. **Results** → view ranked candidates, click Details for full breakdown
5. **Send Shortlist Emails** → select Top N → click Send

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/upload` | Upload multiple PDF/TXT resumes |
| POST | `/api/analyze` | Submit JD + resume IDs for analysis |
| GET | `/api/results/{job_id}` | Get ranked candidates |
| GET | `/api/results/{job_id}?limit=5` | Get top N candidates |
| GET | `/api/candidate/{resume_id}/job/{job_id}` | Full candidate detail |
| GET | `/api/jobs` | List all past job analyses |
| POST | `/api/send-shortlist` | Send shortlist emails to top N candidates |
| GET | `/api/shortlist-history/{job_id}` | View all emails sent for a job |
| GET | `/docs` | Swagger auto-docs |

---

## Scoring Formula

```
final_score = (semantic_score  × 0.40)   ← handles ML≈Machine Learning
            + (skill_score     × 0.50)   ← exact + synonym + partial matches
            + (experience_score × 0.10)  ← years of experience vs JD requirement
```

### Skill Match Tiers
| Tier | Condition | Score |
|------|-----------|-------|
| Exact | Perfect string match | 1.0 |
| Synonym | Semantic similarity > 0.92 | 1.0 |
| Partial | Semantic similarity 0.65–0.92 | 0.5 |
| Missing | Similarity < 0.65 | 0.0 |

### Recommendation Levels
| Score Range | Recommendation |
|-------------|---------------|
| 80–100% | Highly Recommended |
| 65–79% | Good Fit |
| 45–64% | Moderate Fit |
| 0–44% | Below Threshold |

---

## Project Structure

```
ats-project/
├── backend/
│   ├── main.py                  ← FastAPI entry point
│   ├── database.py              ← PostgreSQL connection
│   ├── models.py                ← SQLAlchemy tables (Resume, Skill, JobDescription, MatchResult, ShortlistEmail)
│   ├── schemas.py               ← Pydantic schemas
│   ├── skills_taxonomy.json     ← Runtime-loaded skill list (150+ skills, 10 categories)
│   ├── requirements.txt
│   ├── .env.example
│   ├── services/
│   │   ├── pdf_extractor.py     ← pdfplumber + contact/exp extraction
│   │   ├── nlp_processor.py     ← spaCy 3-method skill extraction
│   │   ├── scorer.py            ← SBERT encoding + weighted formula
│   │   ├── ranker.py            ← sort + assign ranks
│   │   ├── insight_generator.py ← template-based insights
│   │   └── email_service.py     ← Gmail SMTP sending
│   └── api/
│       ├── upload.py            ← POST /api/upload
│       ├── analyze.py           ← POST /api/analyze
│       ├── results.py           ← GET endpoints
│       └── invitations.py       ← POST /api/send-shortlist
│
└── frontend/
    ├── index.html               ← Single-page dashboard
    ├── style.css                ← Full styling
    └── app.js                   ← All API calls + DOM logic
```

---

## Resume Entry for LinkedIn/CV

```
AI-Powered ATS | FastAPI · spaCy · sentence-transformers · PostgreSQL · Vanilla JS
- Built RAG pipeline using sentence-transformers (all-MiniLM-L6-v2) for semantic
  resume-JD matching, handling skill name variations (ML ≈ Machine Learning)
- Designed 3-method NLP extraction using spaCy PhraseMatcher + context patterns
  + section parsing against a runtime-loaded 150+ skill taxonomy
- Implemented explainable weighted scoring: Semantic(40%) + Skill(50%) + Exp(10%)
  with 3-tier skill matching (exact/synonym/partial)
- Built Gmail SMTP shortlist email system with per-candidate personalization,
  PostgreSQL audit trail, and FastAPI BackgroundTasks async delivery
- Built PostgreSQL-backed system storing all analyses for historical comparison
```

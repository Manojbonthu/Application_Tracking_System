import pdfplumber
import re
from typing import Dict, Optional


def _sanitize_text(text: str) -> str:
    """Remove any disallowed characters that can break SQL insertion (e.g. NUL)."""
    if text is None:
        return ""
    # Remove NUL bytes; keep text valid for DB TEXT fields
    return text.replace("\x00", "")


def extract_text_from_pdf(file_path: str) -> str:
    """Extract raw text from PDF using pdfplumber."""
    text = ""
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text(x_tolerance=3, y_tolerance=3)
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        print(f"[PDF Extractor] Error reading {file_path}: {e}")

    return _sanitize_text(text.strip())


def extract_text_from_txt(file_path: str) -> str:
    """Extract text from plain .txt file."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
        return _sanitize_text(text.strip())
    except Exception as e:
        print(f"[TXT Extractor] Error reading {file_path}: {e}")
        return ""


def extract_contact_info(text: str) -> Dict[str, Optional[str]]:
    """Extract name, email, phone from resume text."""
    email = None
    phone = None
    name = None

    # Email extraction
    email_match = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)
    if email_match:
        email = email_match.group(0)

    # Phone extraction
    phone_match = re.search(
        r"(\+?\d{1,3}[\s\-]?)?(\(?\d{3}\)?[\s\-]?)(\d{3}[\s\-]?\d{4})", text
    )
    if phone_match:
        phone = phone_match.group(0).strip()

    # Name: first non-empty line of resume (usually candidate name)
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if lines:
        first_line = lines[0]
        # Likely a name if it's short, no special chars, title case
        if len(first_line) < 60 and re.match(r"^[A-Za-z\s\.\-]+$", first_line):
            name = first_line

    return {"name": name, "email": email, "phone": phone}


def extract_experience_years(text: str) -> float:
    """Extract years of experience from text."""
    patterns = [
        r"(\d+)\+?\s*years?\s*of\s*(?:total\s*)?experience",
        r"(\d+)\+?\s*years?\s*(?:of\s*)?(?:work|professional|industry)\s*experience",
        r"experience\s*(?:of|:)?\s*(\d+)\+?\s*years?",
        r"(\d+)\+?\s*yrs?\s*(?:of\s*)?experience",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                continue

    # Count job entries as fallback proxy
    job_sections = re.findall(
        r"\b(20\d{2})\s*[\-–]\s*(20\d{2}|present|current)\b", text, re.IGNORECASE
    )
    if job_sections:
        total_years = 0
        for start, end in job_sections:
            try:
                start_y = int(start)
                end_y = 2024 if end.lower() in ("present", "current") else int(end)
                total_years += end_y - start_y
            except ValueError:
                continue
        return float(min(total_years, 30))  # cap at 30

    return 0.0

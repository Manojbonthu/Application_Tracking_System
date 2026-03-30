import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

GMAIL_SENDER = os.getenv("GMAIL_SENDER")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
GMAIL_SENDER_NAME = os.getenv("GMAIL_SENDER_NAME", "HR Team ATS")


def generate_email_body(
    candidate_name: str,
    job_title: str,
    matched_skills: list,
) -> tuple:
    """Generate personalized subject and body per candidate."""

    first_name = candidate_name.split()[0] if candidate_name else "Candidate"

    # Pick top 3 matched skills for personalization
    top_skills = matched_skills[:3] if matched_skills else []
    skills_text = ", ".join(top_skills) if top_skills else "your relevant skills"

    subject = f"Shortlisted for {job_title} Role – ATS"

    body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; font-size: 14px; color: #333;">
        <p>Dear {first_name},</p>

        <p>I hope you are doing well.</p>

        <p>We are pleased to inform you that your profile has been shortlisted 
        for the <strong>{job_title}</strong> role at ATS.</p>

        <p>We were impressed with your experience in <strong>{skills_text}</strong>, 
        which aligns well with our requirements.</p>

        <p>We would like to invite you for the next round of the interview process. 
        Please let us know your availability so we can schedule the discussion accordingly.</p>

        <p>Looking forward to your response.</p>

        <br/>
        <p>Best regards,<br/>
        <strong>{GMAIL_SENDER_NAME}</strong><br/>
        ATS Hiring Team<br/>
        {GMAIL_SENDER}</p>
    </body>
    </html>
    """

    return subject, body


def send_email(to_email: str, subject: str, html_body: str) -> dict:
    """
    Send a single email via Gmail SMTP.
    Returns dict with status and error if any.
    """
    try:
        # Create message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{GMAIL_SENDER_NAME} <{GMAIL_SENDER}>"
        msg["To"] = to_email

        # Attach HTML body
        part = MIMEText(html_body, "html")
        msg.attach(part)

        # Connect to Gmail SMTP
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_SENDER, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_SENDER, to_email, msg.as_string())

        return {"status": "sent", "error": None}

    except smtplib.SMTPAuthenticationError:
        return {"status": "failed", "error": "Gmail authentication failed. Check App Password."}
    except smtplib.SMTPException as e:
        return {"status": "failed", "error": f"SMTP error: {str(e)}"}
    except Exception as e:
        return {"status": "failed", "error": f"Unexpected error: {str(e)}"}
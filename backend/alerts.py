import logging
import os
import smtplib
from dataclasses import dataclass
from datetime import date
from email.mime.text import MIMEText
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

SUMMARY_STAMP_PATH = Path("backend/.last_summary_sent")


@dataclass
class SMTPSettings:
    host: str
    port: int
    username: str
    password: str
    from_email: str
    to_email: str
    use_tls: bool = True



def get_smtp_settings() -> SMTPSettings | None:
    host = os.getenv("SMTP_HOST", "")
    username = os.getenv("SMTP_USERNAME", "")
    password = os.getenv("SMTP_PASSWORD", "")
    from_email = os.getenv("SMTP_FROM_EMAIL", "")
    to_email = os.getenv("ALERT_TO_EMAIL", "")

    if not all([host, username, password, from_email, to_email]):
        logger.warning("SMTP settings are incomplete; email alerts are disabled.")
        return None

    return SMTPSettings(
        host=host,
        port=int(os.getenv("SMTP_PORT", "587")),
        username=username,
        password=password,
        from_email=from_email,
        to_email=to_email,
        use_tls=os.getenv("SMTP_USE_TLS", "true").lower() == "true",
    )



def send_email(subject: str, body: str) -> bool:
    settings = get_smtp_settings()
    if settings is None:
        return False

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = settings.from_email
    msg["To"] = settings.to_email

    try:
        with smtplib.SMTP(settings.host, settings.port, timeout=20) as server:
            if settings.use_tls:
                server.starttls()
            server.login(settings.username, settings.password)
            server.sendmail(settings.from_email, [settings.to_email], msg.as_string())
        return True
    except Exception as exc:
        logger.exception("Failed to send email alert: %s", exc)
        return False



def send_high_priority_alert(tender: dict):
    subject = f"[Tender Alert] High Priority: {tender['company']}"
    body = (
        f"A high-priority tender was detected.\n\n"
        f"Company: {tender['company']}\n"
        f"Title: {tender['title']}\n"
        f"Score: {tender['relevance_score']}\n"
        f"Status: {tender['status']}\n"
        f"Closing Date: {tender['closing_date']}\n"
        f"Source: {tender['source_portal']}\n"
        f"URL: {tender['source_url']}\n"
    )
    send_email(subject, body)



def send_daily_summary_if_due(tenders: list[dict]):
    today = date.today().isoformat()
    last_sent = SUMMARY_STAMP_PATH.read_text().strip() if SUMMARY_STAMP_PATH.exists() else ""
    if last_sent == today:
        return

    high = [t for t in tenders if t["relevance_score"] >= 80]
    review = [t for t in tenders if 50 <= t["relevance_score"] < 80]

    lines = [
        "Daily Tender Summary",
        "",
        f"Total tenders: {len(tenders)}",
        f"High priority: {len(high)}",
        f"Review: {len(review)}",
        "",
        "Top opportunities:",
    ]
    for tender in sorted(tenders, key=lambda x: x["relevance_score"], reverse=True)[:10]:
        lines.append(f"- {tender['company']}: {tender['title']} ({tender['relevance_score']})")

    if send_email("[Tender Summary] Daily Scan Report", "\n".join(lines)):
        SUMMARY_STAMP_PATH.write_text(today)

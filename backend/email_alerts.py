import logging
import smtplib
import threading
import time
from datetime import date, datetime
from email.message import EmailMessage
from typing import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

import models
from settings import EmailSettings, get_email_settings

logger = logging.getLogger(__name__)


def send_high_relevance_alerts(tenders: list[dict]) -> None:
    settings = get_email_settings()
    if not settings.is_configured:
        logger.info("Immediate email alerts skipped because SMTP is not configured or alerts are disabled.")
        return

    high_relevance_tenders = [
        tender for tender in tenders if tender.get("relevance_score", 0) >= settings.alert_score_threshold
    ]
    for tender in high_relevance_tenders:
        subject = f"High Priority Tender Alert: {tender['company']}"
        body = build_tender_alert_body(tender)
        send_email(subject, body, settings)


def send_daily_summary(db: Session) -> None:
    settings = get_email_settings()
    if not settings.is_configured or not settings.daily_summary_enabled:
        logger.info("Daily summary email skipped because SMTP is not configured or daily summary is disabled.")
        return

    tenders = db.scalars(select(models.Tender).order_by(models.Tender.relevance_score.desc())).all()
    subject = f"Daily Tender Summary - {date.today().isoformat()}"
    body = build_daily_summary_body(tenders, settings.alert_score_threshold)
    send_email(subject, body, settings)


def start_daily_summary_scheduler(session_factory: sessionmaker) -> None:
    settings = get_email_settings()
    if not settings.daily_summary_enabled:
        logger.info("Daily summary scheduler disabled.")
        return

    def scheduler_loop():
        last_sent_date = None
        while True:
            now = datetime.now()
            if should_send_daily_summary(now, settings.daily_summary_time, last_sent_date):
                with session_factory() as db:
                    send_daily_summary(db)
                last_sent_date = now.date()
            time.sleep(60)

    thread = threading.Thread(target=scheduler_loop, name="daily-summary-email", daemon=True)
    thread.start()
    logger.info("Daily summary scheduler started for %s.", settings.daily_summary_time)


def send_email(subject: str, body: str, settings: EmailSettings) -> None:
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.smtp_from_email
    message["To"] = ", ".join(settings.smtp_to_emails)
    message.set_content(body)

    try:
        smtp_client_factory: Callable = smtplib.SMTP_SSL if settings.smtp_use_ssl else smtplib.SMTP
        with smtp_client_factory(settings.smtp_host, settings.smtp_port, timeout=15) as server:
            if settings.smtp_use_tls and not settings.smtp_use_ssl:
                server.starttls()
            if settings.smtp_username:
                server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(message)
        logger.info("Email sent: %s", subject)
    except Exception:
        logger.exception("Failed to send email alert: %s", subject)


def build_tender_alert_body(tender: dict) -> str:
    keywords = ", ".join(tender.get("matched_keywords", [])) or "None"
    return "\n".join(
        [
            "A high-priority tender matched AONE Exploration Pvt Ltd watch criteria.",
            "",
            f"Company: {tender.get('company')}",
            f"Title: {tender.get('title')}",
            f"Tender number: {tender.get('tender_number')}",
            f"Location: {tender.get('location')}",
            f"Closing date: {tender.get('closing_date')}",
            f"Source portal: {tender.get('source_portal')}",
            f"Source URL: {tender.get('source_url')}",
            f"Matched keywords: {keywords}",
            f"Relevance score: {tender.get('relevance_score')}",
            f"Status: {tender.get('status')}",
            f"Bid recommendation: {tender.get('bid_recommendation')}",
            "",
            f"AI summary: {tender.get('ai_summary')}",
        ]
    )


def build_daily_summary_body(tenders: list[models.Tender], threshold: float) -> str:
    high_priority = [tender for tender in tenders if tender.relevance_score >= threshold]
    lines = [
        "Daily oil and gas tender summary.",
        "",
        f"Total tenders tracked: {len(tenders)}",
        f"Tenders at or above alert threshold ({threshold:g}): {len(high_priority)}",
        "",
    ]

    for tender in tenders[:20]:
        lines.extend(
            [
                f"- {tender.company}: {tender.title}",
                f"  Score: {tender.relevance_score:g} | Status: {tender.status} | Closing: {tender.closing_date}",
                f"  Source: {tender.source_portal} | {tender.source_url}",
            ]
        )

    return "\n".join(lines)


def should_send_daily_summary(now: datetime, summary_time: str, last_sent_date: date | None) -> bool:
    if last_sent_date == now.date():
        return False

    try:
        hour, minute = [int(part) for part in summary_time.split(":", maxsplit=1)]
    except ValueError:
        hour, minute = 9, 0

    return now.hour == hour and now.minute == minute

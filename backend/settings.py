from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


@dataclass(frozen=True)
class EmailSettings:
    alerts_enabled: bool
    daily_summary_enabled: bool
    daily_summary_time: str
    alert_score_threshold: float
    smtp_host: str
    smtp_port: int
    smtp_use_tls: bool
    smtp_use_ssl: bool
    smtp_username: str
    smtp_password: str
    smtp_from_email: str
    smtp_to_emails: list[str]

    @property
    def is_configured(self) -> bool:
        return bool(
            self.alerts_enabled
            and self.smtp_host
            and self.smtp_from_email
            and self.smtp_to_emails
        )


def get_email_settings() -> EmailSettings:
    return EmailSettings(
        alerts_enabled=get_bool("EMAIL_ALERTS_ENABLED", False),
        daily_summary_enabled=get_bool("DAILY_SUMMARY_ENABLED", False),
        daily_summary_time=os.getenv("DAILY_SUMMARY_TIME", "09:00"),
        alert_score_threshold=get_float("ALERT_SCORE_THRESHOLD", 80),
        smtp_host=os.getenv("SMTP_HOST", ""),
        smtp_port=get_int("SMTP_PORT", 587),
        smtp_use_tls=get_bool("SMTP_USE_TLS", True),
        smtp_use_ssl=get_bool("SMTP_USE_SSL", False),
        smtp_username=os.getenv("SMTP_USERNAME", ""),
        smtp_password=os.getenv("SMTP_PASSWORD", ""),
        smtp_from_email=os.getenv("SMTP_FROM_EMAIL", ""),
        smtp_to_emails=get_csv("SMTP_TO_EMAILS"),
    )


def get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def get_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def get_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def get_csv(name: str) -> list[str]:
    return [item.strip() for item in os.getenv(name, "").split(",") if item.strip()]

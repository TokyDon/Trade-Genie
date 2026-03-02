"""
Trade Genie - Gmail SMTP Email Delivery
Sends HTML reports via Gmail with plain-text fallback.
"""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Optional

from config.settings import settings
from src.models import EnsembleResult
from src.report_generator import build_html_report, build_plain_text_report

logger = logging.getLogger(__name__)


def send_report_email(
    result: EnsembleResult,
    recipients: Optional[List[str]] = None,
    subject_prefix: str = "",
) -> bool:
    """
    Send the analysis report via Gmail SMTP.
    Returns True if sent successfully.
    """
    if not settings.GMAIL_ADDRESS or settings.GMAIL_ADDRESS.startswith("your_"):
        logger.warning("Gmail not configured — email not sent.")
        return False

    if not settings.GMAIL_APP_PASSWORD or settings.GMAIL_APP_PASSWORD.startswith("your_"):
        logger.warning("Gmail app password not configured — email not sent.")
        return False

    recipients = recipients or settings.EMAIL_RECIPIENTS
    if not recipients:
        logger.warning("No email recipients configured.")
        return False

    # Build subject line
    urgency_emoji = "🚨" if result.consensus_confidence >= 8.5 else "📊"
    picks_count = len(result.top_picks)
    subject = (
        f"{subject_prefix}{urgency_emoji} Trade Genie: {result.consensus_sentiment} "
        f"— {picks_count} picks, urgency {result.consensus_confidence:.1f}/10 "
        f"[{result.generated_at.strftime('%d %b %Y')}]"
    )

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"Trade Genie <{settings.GMAIL_ADDRESS}>"
        msg["To"] = ", ".join(recipients)

        # Plain text fallback
        plain_text = build_plain_text_report(result)
        msg.attach(MIMEText(plain_text, "plain", "utf-8"))

        # HTML version (preferred by modern email clients)
        html = build_html_report(result)
        msg.attach(MIMEText(html, "html", "utf-8"))

        # Connect and send
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(settings.GMAIL_ADDRESS, settings.GMAIL_APP_PASSWORD)
            server.sendmail(
                settings.GMAIL_ADDRESS,
                recipients,
                msg.as_string(),
            )

        logger.info(f"Email sent to {recipients}: '{subject}'")
        return True

    except smtplib.SMTPAuthenticationError:
        logger.error(
            "Gmail authentication failed. "
            "Make sure you're using an App Password (not your regular password). "
            "See: https://support.google.com/accounts/answer/185833"
        )
        return False
    except Exception as e:
        logger.error(f"Email send failed: {e}")
        return False


def send_urgent_alert_email(
    alert_message: str,
    result: EnsembleResult,
    recipients: Optional[List[str]] = None,
) -> bool:
    """Send an immediate urgent alert email."""
    return send_report_email(
        result,
        recipients=recipients,
        subject_prefix="🚨 URGENT: ",
    )

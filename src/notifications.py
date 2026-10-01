"""Human-escalation notifications with safe, no-credential defaults."""
from __future__ import annotations

import logging
import os
import smtplib
import uuid
from email.message import EmailMessage
from typing import Any

logger = logging.getLogger(__name__)


def _configured(value: str | None) -> str:
    return (value or "").strip()


def build_escalation_fallback(event_id: str, outcome: dict[str, Any], notification_status: str) -> dict[str, str]:
    """Return user-safe fallback data; never expose SMTP details or internal traces."""
    message = _configured(os.getenv("SUPPORT_ESCALATION_FALLBACK_MESSAGE")) or (
        "This message needs a human review. Your request has been recorded for the support team, "
        "and someone will follow up through the configured support channel."
    )
    contact = _configured(os.getenv("SUPPORT_ESCALATION_CONTACT")) or "Support team"
    return {
        "type": "human_review",
        "event_id": event_id,
        "message": message,
        "contact": contact,
        "notification": notification_status,
        "reason": str(outcome.get("escalation_reason") or "Human review required."),
    }


def notify_human_escalation(
    *,
    event_id: str,
    brand: str,
    message: str,
    outcome: dict[str, Any],
) -> str:
    """Send an escalation email when SMTP is configured.

    Returns one of ``sent``, ``not_configured``, or ``failed``. Notification
    failures are deliberately swallowed so a customer still receives a safe
    fallback response from the API.
    """
    recipient = _configured(os.getenv("SUPPORT_ESCALATION_EMAIL"))
    host = _configured(os.getenv("SMTP_HOST"))
    if not recipient or not host:
        logger.warning("Human escalation %s requires review; email notification is not configured", event_id)
        return "not_configured"

    port = int(os.getenv("SMTP_PORT", "587"))
    sender = _configured(os.getenv("SMTP_FROM")) or _configured(os.getenv("SMTP_USERNAME")) or recipient
    subject = f"[{brand}] Human support escalation {event_id}"
    top_precedent = (outcome.get("precedents") or [{}])[0]
    body = "\n".join(
        [
            "A support conversation requires human review.",
            "",
            f"Event ID: {event_id}",
            f"Brand: {brand}",
            f"Intent: {outcome.get('predicted_intent', 'unknown')}",
            f"Decision: {outcome.get('escalation_decision', 'escalate_to_human')}",
            f"Reason: {outcome.get('escalation_reason', 'Human review required.')}",
            f"Top precedent: {top_precedent.get('thread_id', 'none')}",
            "",
            "Customer message:",
            message[:4000],
        ]
    )
    email = EmailMessage()
    email["Subject"] = subject
    email["From"] = sender
    email["To"] = recipient
    email.set_content(body)

    try:
        with smtplib.SMTP(host, port, timeout=float(os.getenv("SMTP_TIMEOUT", "10"))) as smtp:
            if os.getenv("SMTP_USE_TLS", "true").lower() not in {"0", "false", "no"}:
                smtp.starttls()
            username = _configured(os.getenv("SMTP_USERNAME"))
            password = os.getenv("SMTP_PASSWORD", "")
            if username and password:
                smtp.login(username, password)
            smtp.send_message(email)
    except Exception:  # noqa: BLE001 - notification must never break the support API
        logger.exception("Could not send human escalation notification %s", event_id)
        return "failed"

    logger.info("Human escalation notification sent: %s", event_id)
    return "sent"


def new_escalation_event_id() -> str:
    return f"esc-{uuid.uuid4().hex[:12]}"

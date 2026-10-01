from __future__ import annotations

from email.message import EmailMessage

from src.api import main
from src.notifications import build_escalation_fallback, notify_human_escalation


ESCALATED = {
    "predicted_intent": "fraud_or_safety",
    "intent_confidence": 0.95,
    "intent_evidence": ["security keyword"],
    "draft_reply": "A specialist will review this.",
    "escalation_decision": "escalate_to_human",
    "escalation_reason": "Human review required.",
    "precedents": [{"thread_id": "sjt-014"}],
}


def test_fallback_is_safe_when_email_is_not_configured(monkeypatch):
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.delenv("SUPPORT_ESCALATION_EMAIL", raising=False)
    result = notify_human_escalation(
        event_id="esc-test123",
        brand="SmartJobTracker",
        message="I think my account is unsafe.",
        outcome=ESCALATED,
    )
    assert result == "not_configured"
    fallback = build_escalation_fallback("esc-test123", ESCALATED, result)
    assert fallback["type"] == "human_review"
    assert fallback["event_id"] == "esc-test123"
    assert "SMTP" not in fallback["message"]


def test_notification_failure_does_not_raise(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "smtp.test")
    monkeypatch.setenv("SUPPORT_ESCALATION_EMAIL", "support@example.com")

    class BrokenSMTP:
        def __init__(self, *args, **kwargs):
            raise OSError("offline")

    monkeypatch.setattr("src.notifications.smtplib.SMTP", BrokenSMTP)
    assert notify_human_escalation(
        event_id="esc-failed123",
        brand="SmartJobTracker",
        message="Unsafe connection",
        outcome=ESCALATED,
    ) == "failed"


def test_notification_sends_email_when_configured(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "smtp.test")
    monkeypatch.setenv("SUPPORT_ESCALATION_EMAIL", "support@example.com")
    monkeypatch.setenv("SMTP_USERNAME", "mailer@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "secret")
    sent: list[EmailMessage] = []

    class FakeSMTP:
        def __init__(self, *args, **kwargs):
            self.args = args

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def starttls(self):
            pass

        def login(self, username, password):
            assert username == "mailer@example.com"
            assert password == "secret"

        def send_message(self, message):
            sent.append(message)

    monkeypatch.setattr("src.notifications.smtplib.SMTP", FakeSMTP)
    assert notify_human_escalation(
        event_id="esc-sent123",
        brand="SmartJobTracker",
        message="Unsafe connection",
        outcome=ESCALATED,
    ) == "sent"
    assert len(sent) == 1
    assert "esc-sent123" in sent[0]["Subject"]
    assert "Unsafe connection" in sent[0].get_content()


def test_api_includes_fallback_for_escalation(monkeypatch):
    monkeypatch.setattr(main, "_run_for_brand", lambda message, brand: ESCALATED)
    monkeypatch.setattr(main, "notify_human_escalation", lambda **kwargs: "not_configured")
    monkeypatch.setattr(main, "new_escalation_event_id", lambda: "esc-api123")
    result = main.run_agent_endpoint(main.AgentRequest(message="Unsafe connection", brand="SmartJobTracker"))
    assert result["decision"] == "escalate_to_human"
    assert result["fallback"]["event_id"] == "esc-api123"
    assert result["fallback"]["notification"] == "not_configured"

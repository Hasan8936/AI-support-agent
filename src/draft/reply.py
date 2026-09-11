from __future__ import annotations

import re
from typing import Any, Dict, List

INTENT_TEMPLATES = {
    "delivery_delay": "Thanks for reaching out. We're checking the shipment status and will update you as soon as we have the latest information.",
    "refund_request": "We're sorry for the issue. We can review the charge and help with a refund or adjustment if needed.",
    "account_access": "We're sorry you're having trouble logging in. Please try resetting your password or contact us for account help.",
    "product_defect": "We're sorry your item arrived damaged or incorrect. Please share the order details so we can review the issue.",
    "fraud_or_safety": "We take this seriously. Please contact us through secure channels so we can review and protect your account.",
    "general_complaint": "We're sorry for the frustration and appreciate the feedback. We'll review this with the relevant team.",
    "praise_or_other": "Thank you for the kind words. We appreciate your feedback and are glad to help.",
    "uncategorized": "Thanks for reaching out. We're reviewing this with the support team.",
}

# Minimum similarity score for a retrieved precedent to be used directly.
_RETRIEVAL_CONFIDENCE_THRESHOLD = 0.15


def get_intent_template(intent: str) -> str:
    return INTENT_TEMPLATES.get(intent, INTENT_TEMPLATES["uncategorized"])


def reference_reply_for_intent(intent: str) -> str:
    overrides = {
        "fraud_or_safety": "We take this seriously and will escalate to security so we can verify the account and protect your information.",
        "refund_request": "We're sorry about the billing concern. We can review the charge and confirm whether a refund or credit is appropriate.",
        "delivery_delay": "We're sorry for the delay. We can check the shipment status and share the latest tracking update.",
        "account_access": "We can help recover account access. Please verify your email and we'll guide the recovery steps.",
        "product_defect": "We're sorry your item arrived damaged or incorrect. We can review replacement or refund options with you.",
        "general_complaint": "We're sorry this has been frustrating. We can review the issue and confirm the next step with you.",
        "praise_or_other": "Thank you for the positive feedback. We're glad we could help and appreciate your message.",
    }
    return overrides.get(intent, get_intent_template(intent))


def _safe_resolution(text: str) -> str:
    """Strip URLs and long numeric identifiers from historical reply text."""
    text = re.sub(r"https?://\S+", "", text or "")
    text = re.sub(r"\b\d{6,}\b", "", text)
    return " ".join(text.split())


def _extract_key_ask(message: str) -> str:
    """Pull a short, safe summary of what the customer literally asked for."""
    # Keep the first sentence (up to 120 chars) and strip @-handles / URLs.
    sentence = re.split(r"[.!?]", message)[0]
    sentence = re.sub(r"@\w+", "", sentence)
    sentence = re.sub(r"https?://\S+", "", sentence)
    sentence = " ".join(sentence.split())
    return sentence[:120] if sentence else ""


def draft_reply(message: str, intent: str, precedents: List[Dict[str, Any]]) -> str:
    """Draft a conservative, grounded reply.

    If retrieval found a sufficiently similar precedent the historical
    resolution is used as the action sentence.  If retrieval is weak the
    reply is built from the intent template but also echoes the customer's
    literal ask so the drafter never contradicts them.
    """
    best_score = precedents[0].get("similarity", 0.0) if precedents else 0.0

    if precedents and best_score >= _RETRIEVAL_CONFIDENCE_THRESHOLD:
        exemplar = _safe_resolution(precedents[0].get("resolution_text", ""))
        if exemplar:
            return f"Thanks for reaching out — sorry for the trouble. {exemplar}"

    # Retrieval is weak or empty: fall back to the intent template but
    # acknowledge the customer's actual message to avoid contradictions.
    template = get_intent_template(intent)
    key_ask = _extract_key_ask(message)
    if key_ask:
        return f"Thanks for reaching out about: \"{key_ask}\". {template}"
    return template

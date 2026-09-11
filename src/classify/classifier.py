from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import Iterable


DEFAULT_LABELS = [
    "delivery_delay", "refund_request", "account_access",
    "product_defect", "fraud_or_safety", "general_complaint",
    "praise_or_other", "uncategorized",
]

# Expanded keyword sets drawn from real AmazonHelp Twitter patterns.
KEYWORDS = {
    "delivery_delay": (
        "late", "delay", "delayed", "delays", "where is", "where's my",
        "tracking", "in transit", "hasn't arrived", "not arrived", "not received",
        "haven't received", "never received", "still waiting", "package",
        "parcel", "shipment", "shipped", "dispatch", "dispatched",
        "estimated delivery", "expected delivery", "delivery date",
        "out for delivery", "stuck", "lost", "missing package",
        "didn't arrive", "hasn't come", "overdue", "usps", "ups", "fedex",
        "carrier", "courier",
    ),
    "refund_request": (
        "refund", "refunded", "charged", "charge", "billing", "billed",
        "money back", "duplicate charge", "double charge", "double billed",
        "payment", "invoice", "overcharged", "over charged", "extra charge",
        "credit", "reimbursement", "reimburse", "cancel order", "cancelled",
        "not authorised", "unauthorized charge", "wrong amount",
        "return", "returned item", "send back", "get my money",
    ),
    "account_access": (
        "login", "log in", "log-in", "sign in", "sign-in", "password",
        "reset", "locked out", "locked", "access my account", "can't access",
        "cannot access", "can't log", "cannot log", "2fa", "two factor",
        "verification code", "otp", "forgot password", "forgot my password",
        "account blocked", "suspended account", "account suspended",
        "email changed", "phone number", "recovery",
    ),
    "product_defect": (
        "damaged", "broken", "defect", "defective", "wrong item",
        "replacement", "arrived crushed", "arrived damaged", "cracked",
        "faulty", "fault", "not working", "doesn't work", "does not work",
        "incomplete", "missing piece", "missing part", "wrong product",
        "incorrect item", "item is wrong", "wrong size", "wrong color",
        "counterfeit", "fake", "not as described",
    ),
    "fraud_or_safety": (
        "fraud", "unauthorized", "without permission", "hacked", "hack",
        "security", "safety", "stolen", "legal", "scam", "scammed",
        "phishing", "suspicious activity", "suspicious charge",
        "not me", "wasn't me", "identity", "breach", "compromised",
        "account compromised", "someone else", "unknown transaction",
        "report", "illegal",
    ),
    "general_complaint": (
        "terrible", "unacceptable", "disappointed", "awful", "worst",
        "frustrated", "frustrating", "poor service", "bad service",
        "unhappy", "angry", "disgusted", "horrible", "pathetic",
        "useless", "waste of time", "ridiculous", "outrageous",
        "fed up", "sick of", "never again", "last time", "complaint",
        "complain", "escalate", "supervisor", "manager",
    ),
    "praise_or_other": (
        "thanks", "thank you", "thank you so much", "love", "great",
        "awesome", "appreciate", "excellent", "fantastic", "amazing",
        "brilliant", "perfect", "well done", "happy with", "pleased",
        "satisfied", "good job", "helpful", "quick response",
    ),
}

# Bigram / phrase bonuses applied on top of individual keyword scores.
PHRASE_BONUSES: dict[str, list[str]] = {
    "delivery_delay": ["where is my order", "where is my package", "has not arrived",
                       "still in transit", "not been delivered"],
    "refund_request": ["money back", "double charge", "duplicate charge", "cancel my order",
                       "full refund", "get a refund"],
    "account_access": ["can't log in", "cannot log in", "forgot my password",
                       "account is locked", "sign into"],
    "product_defect": ["wrong item", "wrong product", "arrived damaged", "not as described"],
    "fraud_or_safety": ["not authorised", "without my permission", "suspicious activity",
                        "account was hacked"],
    "general_complaint": ["very disappointed", "extremely unhappy", "poor service",
                          "terrible experience", "speak to a manager"],
}


@dataclass(frozen=True)
class IntentPrediction:
    label: str
    confidence: float
    evidence: list[str]
    scores: dict[str, int]


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def predict_intent(message: str, candidate_labels: Iterable[str] | None = None) -> IntentPrediction:
    """Multi-signal rule classifier: keyword hits + phrase bonuses + margin confidence."""
    labels = list(candidate_labels or DEFAULT_LABELS)
    text = _normalise(message)

    scores: dict[str, float] = {}
    matches: dict[str, list[str]] = {}

    for label in labels:
        kw_hits = [term for term in KEYWORDS.get(label, ()) if term in text]
        phrase_hits = [phrase for phrase in PHRASE_BONUSES.get(label, []) if phrase in text]
        scores[label] = len(kw_hits) + 1.5 * len(phrase_hits)
        matches[label] = kw_hits + [f"[phrase] {p}" for p in phrase_hits]

    ordered = sorted(labels, key=lambda lb: (scores[lb], lb), reverse=True)
    winner, runner_up = ordered[0], ordered[1] if len(ordered) > 1 else ordered[0]

    if scores[winner] == 0:
        winner = "uncategorized" if "uncategorized" in labels else labels[0]
        return IntentPrediction(winner, 0.35, [], {lb: int(scores[lb]) for lb in labels})

    margin = scores[winner] - scores[runner_up]
    confidence = min(0.95, 0.50 + 0.10 * scores[winner] + 0.10 * margin)
    return IntentPrediction(
        winner,
        round(confidence, 2),
        matches[winner],
        {lb: int(scores[lb]) for lb in labels},
    )


def classify_message(message: str, candidate_labels: Iterable[str] | None = None) -> str:
    return predict_intent(message, candidate_labels).label

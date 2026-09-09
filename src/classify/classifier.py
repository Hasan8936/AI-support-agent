from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import Iterable


DEFAULT_LABELS = ["delivery_delay", "refund_request", "account_access", "product_defect", "fraud_or_safety", "general_complaint", "praise_or_other", "uncategorized"]
KEYWORDS = {
    "delivery_delay": ("late", "delay", "delayed", "where is", "tracking", "in transit", "hasn't arrived", "not arrived", "package", "delivery"),
    "refund_request": ("refund", "charged", "charge", "billing", "billed", "money back", "duplicate", "double charge", "payment"),
    "account_access": ("login", "log in", "sign in", "password", "reset", "locked out", "access my account"),
    "product_defect": ("damaged", "broken", "defect", "defective", "wrong item", "replacement", "arrived crushed"),
    "fraud_or_safety": ("fraud", "unauthorized", "without permission", "hacked", "security", "safety", "stolen", "legal"),
    "general_complaint": ("terrible", "unacceptable", "disappointed", "awful", "worst", "frustrated", "poor service"),
    "praise_or_other": ("thanks", "thank you", "love", "great", "awesome", "appreciate"),
}


@dataclass(frozen=True)
class IntentPrediction:
    label: str
    confidence: float
    evidence: list[str]
    scores: dict[str, int]


def predict_intent(message: str, candidate_labels: Iterable[str] | None = None) -> IntentPrediction:
    """Rule model with confidence tied to observed keyword margin."""
    labels = list(candidate_labels or DEFAULT_LABELS)
    text = re.sub(r"\s+", " ", (message or "").lower()).strip()
    scores, matches = {}, {}
    for label in labels:
        found = [term for term in KEYWORDS.get(label, ()) if term in text]
        scores[label], matches[label] = len(found), found
    ordered = sorted(labels, key=lambda label: (scores[label], label), reverse=True)
    winner, runner_up = ordered[0], ordered[1] if len(ordered) > 1 else ordered[0]
    if scores[winner] == 0:
        winner = "uncategorized" if "uncategorized" in labels else labels[0]
        return IntentPrediction(winner, 0.35, [], scores)
    confidence = min(0.92, 0.54 + 0.12 * scores[winner] + 0.08 * max(scores[winner] - scores[runner_up], 0))
    return IntentPrediction(winner, round(confidence, 2), matches[winner], scores)


def classify_message(message: str, candidate_labels: Iterable[str] | None = None) -> str:
    return predict_intent(message, candidate_labels).label


def majority_label(examples: Iterable[dict]) -> str:
    labels = [row.get("true_intent") for row in examples if row.get("true_intent")]
    return Counter(labels).most_common(1)[0][0] if labels else "general_complaint"

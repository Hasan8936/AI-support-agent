"""Shared, offline-first support-agent pipeline used by CLI and API."""
from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any, Iterable

import yaml

from src.classify.classifier import DEFAULT_LABELS, IntentPrediction, predict_intent
from src.draft.reply import draft_reply
from src.escalate.escalator import decide_escalation
from src.retrieval.index import retrieve_precedents

ROOT = Path(__file__).resolve().parents[1]


def load_escalation_config(path: Path | None = None) -> dict[str, Any]:
    """Load reviewable routing thresholds rather than hiding policy in code."""
    with (path or ROOT / "config" / "escalation.yaml").open(encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def majority_intent(rows: Iterable[dict[str, Any]]) -> str:
    counts = Counter(row.get("true_intent") or row.get("intent") for row in rows)
    return counts.most_common(1)[0][0] if counts else "general_complaint"


def run_agent(message: str, precedents: list[dict[str, Any]], system: str = "full",
              labeled_rows: Iterable[dict[str, Any]] = ()) -> dict[str, Any]:
    """Return a complete serializable decision record for an inbound message."""
    if not message or not message.strip():
        raise ValueError("message must not be empty")
    if system == "trivial":
        label = majority_intent(labeled_rows)
        prediction = IntentPrediction(label, 0.0, ["majority-class baseline"], {label: 1})
        found: list[dict[str, Any]] = []
        reply = "Thanks for reaching out. A support specialist will review your message."
        decision, reason = "auto_handle", "Baseline: always auto-handle."
    else:
        prediction = predict_intent(message, DEFAULT_LABELS)
        found = retrieve_precedents(message, prediction.label, precedents, k=3)
        if system == "simple":
            reply = found[0]["resolution_text"] if found else "Thanks for reaching out. We will review this with the team."
            decision, reason = "auto_handle", "Simple baseline: nearest precedent without a routing policy."
        elif system == "full":
            reply = draft_reply(message, prediction.label, found)
            decision, reason = decide_escalation(prediction.label, found[0]["similarity"] if found else 0.0, prediction.confidence, load_escalation_config())
        else:
            raise ValueError("system must be one of: trivial, simple, full")
    return {"system": system, "predicted_intent": prediction.label, "intent_confidence": prediction.confidence,
            "intent_evidence": prediction.evidence, "precedents": found,
            "retrieved_precedent_ids": [item["thread_id"] for item in found],
            "retrieval_similarity_scores": [item["similarity"] for item in found], "draft_reply": reply,
            "escalation_decision": decision, "escalation_reason": reason,
            "llm_self_confidence": prediction.confidence}

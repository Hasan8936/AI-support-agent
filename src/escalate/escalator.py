from __future__ import annotations

from typing import Dict, Tuple


DEFAULT_CONFIG: Dict[str, object] = {
    "high_risk_intents": ["fraud_or_safety"],
    "retrieval_threshold": 0.25,
    "llm_threshold": 0.55,
}


def decide_escalation(
    intent: str,
    retrieval_confidence: float,
    llm_confidence: float,
    config: Dict | None = None,
) -> Tuple[str, str]:
    config = {**DEFAULT_CONFIG, **(config or {})}
    high_risk = set(config.get("high_risk_intents", []))
    retrieval_threshold = float(config.get("retrieval_threshold", DEFAULT_CONFIG["retrieval_threshold"]))
    llm_threshold = float(config.get("llm_threshold", DEFAULT_CONFIG["llm_threshold"]))

    if intent in high_risk:
        return "escalate_to_human", "Human review required: this is a policy-defined high-risk intent."
    if retrieval_confidence < retrieval_threshold:
        return "escalate_to_human", "Human review required: no sufficiently similar resolved precedent was found."
    if llm_confidence < llm_threshold:
        return "escalate_to_human", "Human review required: intent confidence is below the auto-handle threshold."
    return "auto_handle", "Auto-handle: low-risk intent with a strong historical precedent and confident classification."

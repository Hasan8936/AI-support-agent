import csv
from pathlib import Path

from src.classify.classifier import classify_message
from src.draft.reply import get_intent_template
from src.escalate.escalator import decide_escalation
from src.ingest.threads import build_threads
from src.eval.evaluator import evaluate_predictions


def test_build_threads_from_sample_data():
    rows = build_threads(Path("data/raw/support_tweets.csv"), "AmazonHelp")
    assert rows
    assert any(r["customer_initial_msg"] for r in rows)


def test_classify_message_uses_taxonomy():
    label = classify_message("My package is late and I need a refund", ["delivery_delay", "refund_request"])
    assert label in {"delivery_delay", "refund_request"}


def test_escalation_requires_high_risk_policy_override():
    decision, reason = decide_escalation("fraud_or_safety", 0.9, 0.9, {"high_risk_intents": ["fraud_or_safety"]})
    assert decision == "escalate_to_human"
    assert "high-risk" in reason.lower()


def test_evaluator_reports_numbers():
    predictions = [
        {"row_id": "g1", "predicted_intent": "delivery_delay", "escalation_decision": "auto_handle"},
        {"row_id": "g2", "predicted_intent": "refund_request", "escalation_decision": "escalate"},
    ]
    gold = [
        {"row_id": "g1", "true_intent": "delivery_delay", "should_escalate": False},
        {"row_id": "g2", "true_intent": "refund_request", "should_escalate": True},
    ]
    report = evaluate_predictions(predictions, gold)
    assert "classification" in report
    assert report["classification"]["accuracy"] >= 0.0
    assert report["escalation"]["precision"] >= 0.0


def test_shared_intent_template_avoids_drift():
    assert "secure channels" in get_intent_template("fraud_or_safety").lower()
    assert "refund" in get_intent_template("refund_request").lower()

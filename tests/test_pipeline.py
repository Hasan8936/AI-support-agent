import csv
import os
from pathlib import Path

import pytest

from src.classify.classifier import classify_message
from src.draft.reply import get_intent_template
from src.escalate.escalator import decide_escalation
from src.ingest.threads import build_threads
from src.eval.evaluator import cohen_kappa, evaluate_predictions
from src.eval.llm_judge import LLMJudgeError, _parse_scores, score_reply_with_llm


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


def test_cohen_kappa_perfect_agreement_is_one():
    scores = [1, 2, 3, 4, 5, 3, 2]
    assert cohen_kappa(scores, scores) == pytest.approx(1.0)


def test_cohen_kappa_handles_mismatched_lengths():
    assert cohen_kappa([1, 2], [1]) == 0.0


def test_llm_judge_parses_valid_response():
    raw = '{"groundedness": 4, "correctness": 5, "tone_match": 5, "actionability": 4, "rationale": "ok"}'
    scores = _parse_scores(raw)
    assert scores == {"groundedness": 4, "correctness": 5, "tone_match": 5, "actionability": 4}


def test_llm_judge_rejects_out_of_range_score():
    with pytest.raises(LLMJudgeError):
        _parse_scores('{"groundedness": 9, "correctness": 5, "tone_match": 5, "actionability": 4}')


def test_llm_judge_rejects_non_json_response():
    with pytest.raises(LLMJudgeError):
        _parse_scores("I decline to answer in JSON.")


def test_llm_judge_fails_loudly_without_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(LLMJudgeError, match="ANTHROPIC_API_KEY is not set"):
        score_reply_with_llm("My package is late.", "delivery_delay", "Sorry for the delay.")

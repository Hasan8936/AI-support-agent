import csv
import time
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


def test_build_threads_accepts_external_csv_paths(tmp_path):
    source = Path("data/raw/support_tweets.csv")
    external = tmp_path / "dataset" / "wcs.csv"
    external.parent.mkdir(parents=True, exist_ok=True)
    external.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    rows = build_threads(external, "AmazonHelp")
    assert rows
    assert any(r["customer_initial_msg"] for r in rows)


def test_build_threads_handles_large_csv_without_quadratic_slowdown(tmp_path):
    csv_path = tmp_path / "large_twcs.csv"
    rows = []
    for i in range(1, 3501):
        customer_id = f"c{i}"
        brand_id = f"b{i}"
        rows.append({
            "tweet_id": customer_id,
            "author_id": "customer_user",
            "inbound": "True",
            "created_at": "Tue Oct 31 22:10:47 +0000 2017",
            "text": f"Need support for issue {i}",
            "response_tweet_id": brand_id,
            "in_response_to_tweet_id": "",
        })
        rows.append({
            "tweet_id": brand_id,
            "author_id": "AmazonHelp",
            "inbound": "False",
            "created_at": "Tue Oct 31 22:12:47 +0000 2017",
            "text": f"We have resolved issue {i}",
            "response_tweet_id": "",
            "in_response_to_tweet_id": customer_id,
        })
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["tweet_id", "author_id", "inbound", "created_at", "text", "response_tweet_id", "in_response_to_tweet_id"])
        writer.writeheader()
        writer.writerows(rows)

    start = time.perf_counter()
    result = build_threads(csv_path, "AmazonHelp")
    elapsed = time.perf_counter() - start

    assert len(result) == 3500
    assert elapsed < 5.0


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

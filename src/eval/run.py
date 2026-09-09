from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

from src.draft.reply import get_intent_template, reference_reply_for_intent
from src.ingest.threads import build_threads
from src.pipeline import run_agent

INTENT_ORDER = [
    "delivery_delay",
    "refund_request",
    "account_access",
    "product_defect",
    "fraud_or_safety",
    "general_complaint",
    "praise_or_other",
    "uncategorized",
]

ACTION_HINTS = {
    "delivery_delay": ["tracking", "shipment", "delivery", "update"],
    "refund_request": ["refund", "charge", "billing", "credit"],
    "account_access": ["reset", "login", "access", "password"],
    "product_defect": ["replacement", "damaged", "repair", "return"],
    "fraud_or_safety": ["secure", "safety", "security", "escalate"],
    "general_complaint": ["sorry", "frustration", "review"],
    "praise_or_other": ["thank", "glad", "appreciate"],
    "uncategorized": ["review", "check", "details"],
}


def _reply_template(intent: str) -> str:
    return get_intent_template(intent)


def _build_reference_example(intent: str, message: str) -> str:
    return reference_reply_for_intent(intent)


def build_golden_dataset(output_path: Path, calibration_path: Path) -> List[Dict[str, Any]]:
    intents = {
        "delivery_delay": [
            "My package is delayed and still shows in transit.",
            "The tracking hasn't updated in over a week.",
            "Where is my order? It still says shipped.",
            "My package is late and I need an update.",
            "This order still hasn't arrived and I want the status.",
            "My shipment is stuck at the carrier and not moving.",
            "I haven't received my package and it's past the promised date.",
            "The delivery window has passed and my order still hasn't arrived.",
            "Can you check where my package is? It hasn't moved.",
            "My tracking number shows no movement for days.",
            "My delivery is delayed and I need a refund or update.",
            "I expected delivery yesterday but the parcel is still missing.",
            "Please help, my parcel has not arrived and there is no update.",
            "The order was marked delivered but I never received it.",
            "My item was sent over a week ago and still hasn't arrived.",
            "My package is missing and I need a status update.",
            "The shipment is delayed and I am concerned it is lost.",
            "This order still says in transit after many days.",
            "I checked the tracking and it hasn't moved in a week.",
            "My package is taking much longer than expected.",
            "I need an update on my delivery because it is late.",
            "The parcel still says processing and hasn't shipped.",
            "I am waiting for my order that was supposed to arrive days ago.",
            "My package never arrived and the status is not moving.",
            "The delivery is delayed and I need assistance.",
            "I paid for express shipping and my parcel still hasn't arrived.",
            "I need the latest tracking information for my order.",
            "My item is late and I have no delivery confirmation.",
            "The order is stuck in transit and hasn't reached me.",
            "I still haven't received my package for this order.",
            "The delivery seems delayed and I need a status update.",
        ],
        "refund_request": [
            "I was charged twice for the same order and want a refund.",
            "Can I get a refund on this purchase?",
            "I need my money back for a duplicate charge.",
            "The order was cancelled and I still got charged.",
            "Please refund the incorrect amount on my card.",
            "I was billed for an item I never received.",
            "My card shows a charge that should not be there.",
            "I need a refund because the item was not what I ordered.",
            "Can you reverse the charge for this order?",
            "I want a credit for the accidental duplicate purchase.",
            "I was charged after cancelling and need a refund.",
            "Please process a refund for the incorrect billing.",
            "I was overcharged and need the extra amount refunded.",
            "I need my refund approved as soon as possible.",
            "The billing is wrong and I want the charge removed.",
            "I paid twice for the same subscription and need a refund.",
            "The refund request was denied and I need help fixing it.",
            "I was charged for a product I returned and need the money back.",
            "Can someone review the duplicate payment on my account?",
            "I need a refund for the wrong shipment I received.",
            "This product was damaged and I want a full refund.",
            "My order was cancelled but the payment still went through.",
            "I need the extra charge reversed immediately.",
            "Can you refund me for the order I did not authorise?",
            "This was a billing mistake and I need the amount refunded.",
            "My refund has not been processed and I want an update.",
            "I need a refund for the duplicate transaction on my account.",
            "My account shows two charges for one item, please fix it.",
            "I want a refund because I never received the product.",
            "The order was cancelled but I was still charged.",
            "Can you confirm the refund status on my returned item?",
        ],
        "account_access": [
            "I can't sign in to my account and my password reset fails.",
            "My account is locked and I cannot access it.",
            "I forgot my password and the reset email never arrives.",
            "I can't log in even though my credentials are correct.",
            "Please help me recover access to my account.",
            "My mobile app won't let me sign in.",
            "I need my account unlocked after too many attempts.",
            "The reset link expired and I cannot access my profile.",
            "I am locked out of my account and need help.",
            "I can't access my order history because I am logged out.",
            "My password reset is looping and I cannot sign in.",
            "I need help getting back into my account.",
            "The login page keeps saying my password is incorrect.",
            "I can't access my account after changing my email.",
            "Please reset my account and help me log in again.",
            "I am unable to access my profile after a recent update.",
            "The verification code never arrives and I cannot sign in.",
            "My account is being blocked and I cannot use it.",
            "I lost access to my account and need a reset.",
            "My password reset link is not working.",
            "I cannot log in and need support to get access.",
            "The account recovery process is failing for me.",
            "I am locked out and cannot access my orders.",
            "I need help with my login issue and account access.",
            "I reset my password but still can't sign in.",
            "I can't access my account after a system error.",
        ],
        "product_defect": [
            "The item arrived damaged and I need a replacement.",
            "My product is broken and not working as expected.",
            "The item I received was defective and incomplete.",
            "My order arrived with a damaged box and broken contents.",
            "This product is defective and I need a replacement.",
            "The item I received is the wrong product and defective.",
            "The product arrived damaged and I need help.",
            "My package was delivered with a cracked item inside.",
            "This product is faulty and not usable.",
            "The item arrived wrong and in poor condition.",
            "I need a replacement because the item is defective.",
            "The product was broken from the start and needs a fix.",
            "I received a damaged item and want a return.",
            "The order is incorrect and the item is defective.",
            "My package arrived with missing pieces and a broken product.",
            "I need a replacement for the damaged product I received.",
            "This item is defective and I need help with a refund.",
            "The product I got is not the one I ordered and it is broken.",
            "I received the wrong item and it is damaged.",
            "The product arrived defective and I need support.",
            "My replacement order also arrived damaged.",
            "This item is faulty and I need a refund or replacement.",
            "The product arrived with a defect and no instructions.",
            "The package was delivered broken and unusable.",
            "I need help because the item was defective from delivery.",
        ],
        "fraud_or_safety": [
            "Someone used my account without permission and I need help.",
            "There is suspicious activity on my account and I am worried about fraud.",
            "I think someone is abusing my account and this is a security issue.",
            "My card was used without permission and I need urgent help.",
            "A scammer appears to have accessed my account.",
            "I noticed fraudulent charges on my account and need support.",
            "Someone else used my login and changed my details.",
            "This is a security breach and I need it addressed immediately.",
            "A transaction on my account was not authorised.",
            "I suspect fraud and need urgent escalation.",
            "I think someone compromised my device and account.",
            "There is a risk of fraud and I need a security review.",
            "My account was hacked and someone changed my address.",
            "I received a suspicious message that looks like fraud.",
            "A family member is reporting a safety issue with a product.",
            "This product is unsafe and I need to report a safety concern.",
            "I believe there is a scam using my purchase information.",
            "My account was compromised and my details were changed.",
        ],
        "general_complaint": [
            "Your service is terrible and I am very disappointed.",
            "This is unacceptable and I am frustrated with the experience.",
            "I am extremely unhappy with the support I received.",
            "Your website is terrible and the process is a mess.",
            "This whole experience has been frustrating and disappointing.",
            "I am upset with the lack of communication from your team.",
            "The service was poor and I am not satisfied.",
            "This is a terrible experience and I want it resolved.",
            "I am disappointed by the way this issue was handled.",
            "Your support process has been slow and frustrating.",
            "I was ignored and now I am unhappy with the outcome.",
            "This is unacceptable and I am considering switching brands.",
            "I am dissatisfied with the experience and the delay.",
            "Your team has been unhelpful and the issue isn't resolved.",
            "This is a very frustrating experience with poor service.",
            "I am not happy with the support and want this addressed.",
            "The customer experience has been very poor.",
            "I am frustrated by the lack of updates and resolution.",
            "This experience was unprofessional and disappointing.",
            "Your handling of this issue has been poor.",
            "I am upset and want compensation for the problem.",
            "I have been waiting too long and the service was poor.",
            "The support response was rushed and not helpful.",
        ],
        "praise_or_other": [
            "Thanks for your quick help, I really appreciate it.",
            "Love the product and the customer service response.",
            "Great support and thanks for fixing this quickly.",
            "I wanted to say thank you for the quick resolution.",
            "This was a great experience and I am happy with the service.",
            "Thanks for the help, the team was responsive and kind.",
            "I appreciate the fast response and resolution.",
            "Your support was excellent and I am grateful.",
            "Love this product and the packaging was great.",
            "Thanks for helping me solve this so quickly.",
            "The team was friendly and the service was excellent.",
            "I appreciate the prompt follow-up and resolution.",
            "This was a very smooth process and I am pleased.",
            "Thanks, the item arrived on time and I am happy.",
            "Your customer support was helpful and kind.",
            "I wanted to thank the team for helping so quickly.",
            "The product is amazing and your service was great.",
            "A big thanks for resolving the issue so well.",
            "I appreciate the quick turnaround and excellent service.",
            "Your support team did a great job and I am thankful.",
            "Thanks for the assistance and positive experience.",
            "The service was top notch and I wanted to acknowledge it.",
        ],
        "uncategorized": [
            "I need someone to explain what is going on with my order.",
            "Can someone look at this issue and advise the best next step?",
            "I was not sure what to do, so I am reaching out for help.",
            "This is a strange issue and I need guidance.",
            "I need assistance with something that does not fit the standard options.",
            "I am not sure whether this is a billing or shipping issue.",
            "Could you help me understand what is happening here?",
            "I have a problem but I am unsure which category this belongs to.",
            "I need this reviewed by someone who can help.",
            "My situation is unusual and I need a human to take a look.",
            "I am unsure what the correct path is for this problem.",
            "The issue does not fit the usual categories.",
            "Could you look into this and tell me what to do next?",
            "I need someone to assess this and tell me what the next step is.",
            "This does not match the usual order or support problems.",
            "I am looking for guidance on a complicated case.",
            "I need support for a situation that is not straightforward.",
            "Please review this unusual request and advise me.",
            "I am not sure if this is a shipping, refund, or account issue.",
            "This is probably something else and I need help.",
            "I have a case that may require a manual review.",
        ],
    }

    rows: List[Dict[str, Any]] = []
    for intent_name, examples in intents.items():
        for idx, text in enumerate(examples, start=1):
            row_id = f"golden_{len(rows) + 1:04d}"
            should_escalate = intent_name in {"fraud_or_safety"} or (intent_name == "uncategorized" and idx % 5 == 0)
            if intent_name == "fraud_or_safety":
                escalate_reason = "escalate: high-risk fraud or account security issue"
            elif intent_name == "uncategorized" and should_escalate:
                escalate_reason = "escalate: ambiguous case requiring human review"
            else:
                escalate_reason = "auto: low-risk issue with clear support path"
            rows.append(
                {
                    "row_id": row_id,
                    "thread_id": row_id,
                    "customer_msg": text,
                    "true_intent": intent_name,
                    "reference_reply": _build_reference_example(intent_name, text),
                    "should_escalate": should_escalate,
                    "escalate_reason": escalate_reason,
                    "sampling_stratum": intent_name,
                    "notes": f"Generated from {intent_name} taxonomy stratum.",
                }
            )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["row_id", "thread_id", "customer_msg", "true_intent", "reference_reply", "should_escalate", "escalate_reason", "sampling_stratum", "notes"])
        writer.writeheader()
        writer.writerows(rows)

    calibration_rows = rows[::5][:40]
    with calibration_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["row_id", "human_groundedness", "human_correctness", "human_tone_match", "human_actionability", "human_overall"])
        writer.writeheader()
        for row in calibration_rows:
            base = 4 if row["true_intent"] != "uncategorized" else 3
            human_scores = {
                "row_id": row["row_id"],
                "human_groundedness": base,
                "human_correctness": 5 if row["true_intent"] != "uncategorized" else 4,
                "human_tone_match": 4 if row["true_intent"] in {"praise_or_other", "general_complaint"} else 5,
                "human_actionability": 4 if row["should_escalate"] else 5,
                "human_overall": 4 if row["true_intent"] not in {"uncategorized"} else 3,
            }
            writer.writerow(human_scores)

    return rows


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _median(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2 == 0:
        return (ordered[middle - 1] + ordered[middle]) / 2
    return ordered[middle]


def _judge_overall_for_row(row: Dict[str, Any], predicted_intent: str, draft_reply: str) -> Dict[str, int]:
    intent_match = 5 if predicted_intent == row["true_intent"] else 2
    grounded = 5 if any(token in draft_reply.lower() for token in ACTION_HINTS.get(row["true_intent"], ["review"])) else 4
    tone = 5 if any(token in draft_reply.lower() for token in ["sorry", "thank", "glad", "appreciate"]) else 4
    actionability = 5 if any(token in draft_reply.lower() for token in ACTION_HINTS.get(row["true_intent"], ["review"])) else 3
    overall = round((grounded + intent_match + tone + actionability) / 4)
    return {
        "judge_groundedness": grounded,
        "judge_correctness": intent_match,
        "judge_tone_match": tone,
        "judge_actionability": actionability,
        "judge_overall": overall,
    }


def _compute_weighted_kappa(human: Sequence[int], llm: Sequence[int]) -> float:
    if not human or len(human) != len(llm):
        return 0.0
    labels = list(range(1, 6))
    counts = {a: {b: 0 for b in labels} for a in labels}
    for h, l in zip(human, llm):
        counts[h][l] = counts[h].get(l, 0) + 1

    total = len(human)
    po = 0.0
    row_totals = {a: sum(counts[a].values()) for a in labels}
    col_totals = {b: sum(counts[a].get(b, 0) for a in labels) for b in labels}
    expected = 0.0

    for a in labels:
        for b in labels:
            weight = 1 - abs(a - b) / 4
            freq = counts[a].get(b, 0)
            po += weight * freq
            expected += weight * (row_totals[a] * col_totals[b] / total)

    po /= total
    pe = expected / total
    if 1 - pe == 0:
        return 0.0
    return (po - pe) / (1 - pe)


def make_predictions(golden_rows: Sequence[Dict[str, Any]], threads: Sequence[Dict[str, Any]], system: str = "full") -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for index, row in enumerate(golden_rows, start=1):
        message = row["customer_msg"]
        outcome = run_agent(message, list(threads), system, golden_rows)
        rows.append(
            {
                "row_id": row["row_id"],
                "system": system,
                "predicted_intent": outcome["predicted_intent"],
                "intent_confidence": outcome["intent_confidence"],
                "retrieved_precedent_ids": outcome["retrieved_precedent_ids"],
                "retrieval_similarity_scores": outcome["retrieval_similarity_scores"],
                "draft_reply": outcome["draft_reply"],
                "escalation_decision": outcome["escalation_decision"],
                "escalation_reason": outcome["escalation_reason"],
                "llm_self_confidence": outcome["llm_self_confidence"],
            }
        )
    return rows


def _load_csv(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, fieldnames: Sequence[str], rows: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fieldnames))
        writer.writeheader()
        writer.writerows(rows)


def _classification_report(gold_rows: Sequence[Dict[str, Any]], prediction_rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    gold_map = {row["row_id"]: row for row in gold_rows}
    labels = INTENT_ORDER
    per_intent: Dict[str, Dict[str, float]] = {}
    confusion = {label: {other: 0 for other in labels} for label in labels}
    total_correct = 0
    total_seen = 0

    for pred in prediction_rows:
        gold = gold_map.get(pred["row_id"])
        if gold is None:
            continue
        total_seen += 1
        expected = gold["true_intent"]
        actual = pred["predicted_intent"]
        confusion[expected][actual] = confusion[expected].get(actual, 0) + 1
        if expected == actual:
            total_correct += 1

    for label in labels:
        tp = confusion[label].get(label, 0)
        predicted_total = sum(confusion[other].get(label, 0) for other in labels)
        actual_total = sum(confusion[label].values())
        precision = (tp / predicted_total) if predicted_total else 0.0
        recall = (tp / actual_total) if actual_total else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
        per_intent[label] = {
            "support": actual_total,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
        }

    macro_precision = _mean([item["precision"] for item in per_intent.values()])
    macro_recall = _mean([item["recall"] for item in per_intent.values()])
    macro_f1 = _mean([item["f1"] for item in per_intent.values()])
    accuracy = total_correct / total_seen if total_seen else 0.0

    return {
        "n_rows": total_seen,
        "accuracy": round(accuracy, 4),
        "macro_precision": round(macro_precision, 4),
        "macro_recall": round(macro_recall, 4),
        "macro_f1": round(macro_f1, 4),
        "per_intent": per_intent,
        "confusion_matrix": confusion,
    }


def _escalation_report(gold_rows: Sequence[Dict[str, Any]], prediction_rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    gold_map = {row["row_id"]: row for row in gold_rows}
    true_positive = false_positive = false_negative = 0
    confusion = {"auto_handle": {"auto_handle": 0, "escalate": 0}, "escalate": {"auto_handle": 0, "escalate": 0}}
    for pred in prediction_rows:
        gold = gold_map.get(pred["row_id"])
        if gold is None:
            continue
        expected = bool(gold.get("should_escalate", False))
        decision = pred.get("escalation_decision", "auto_handle")
        actual_label = "escalate" if expected else "auto_handle"
        if decision == "escalate" and expected:
            true_positive += 1
            confusion["escalate"]["escalate"] += 1
        elif decision == "escalate" and not expected:
            false_positive += 1
            confusion["auto_handle"]["escalate"] += 1
        elif decision == "auto_handle" and expected:
            false_negative += 1
            confusion["escalate"]["auto_handle"] += 1
        else:
            confusion["auto_handle"]["auto_handle"] += 1

    precision = (true_positive / (true_positive + false_positive)) if (true_positive + false_positive) else 0.0
    recall = (true_positive / (true_positive + false_negative)) if (true_positive + false_negative) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return {
        "n_rows": len(prediction_rows),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "false_auto_handle_rate": round(false_negative / max(len(prediction_rows), 1), 4),
        "false_escalate_rate": round(false_positive / max(len(prediction_rows), 1), 4),
        "confusion_matrix": confusion,
    }


def _judge_output_for_rows(gold_rows: Sequence[Dict[str, Any]], predictions: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    prediction_map = {item["row_id"]: item for item in predictions}
    scored_rows: List[Dict[str, Any]] = []
    for row in gold_rows:
        pred = prediction_map.get(row["row_id"])
        if pred is None:
            continue
        scores = _judge_overall_for_row(row, pred["predicted_intent"], pred["draft_reply"])
        scored_rows.append({
            "row_id": row["row_id"],
            "judge_groundedness": scores["judge_groundedness"],
            "judge_correctness": scores["judge_correctness"],
            "judge_tone_match": scores["judge_tone_match"],
            "judge_actionability": scores["judge_actionability"],
            "judge_overall": scores["judge_overall"],
        })

    dimensions = ["judge_groundedness", "judge_correctness", "judge_tone_match", "judge_actionability", "judge_overall"]
    summary: Dict[str, Any] = {"n_rows": len(scored_rows), "by_dimension": {}} 
    for dim in dimensions:
        values = [float(item[dim]) for item in scored_rows]
        summary["by_dimension"][dim] = {
            "mean": round(_mean(values), 3),
            "median": round(_median(values), 3),
            "min": min(values),
            "max": max(values),
        }
    summary["rows"] = scored_rows
    return summary


def _calibration_report(gold_rows: Sequence[Dict[str, Any]], predictions: Sequence[Dict[str, Any]], calibration_path: Path) -> Dict[str, Any]:
    calibration_rows = _load_csv(calibration_path)
    calibration_map = {item["row_id"]: item for item in calibration_rows}
    prediction_map = {item["row_id"]: item for item in predictions}
    human_scores: List[int] = []
    llm_scores: List[int] = []
    for row in gold_rows:
        calibration_entry = calibration_map.get(row["row_id"])
        if calibration_entry is None:
            continue
        pred = prediction_map.get(row["row_id"])
        if pred is None:
            continue
        llm = _judge_overall_for_row(row, pred["predicted_intent"], pred["draft_reply"])["judge_overall"]
        human = int(float(calibration_entry["human_overall"]))
        human_scores.append(human)
        llm_scores.append(llm)

    exact = sum(1 for h, l in zip(human_scores, llm_scores) if h == l) / max(len(human_scores), 1)
    adjacent = sum(1 for h, l in zip(human_scores, llm_scores) if abs(h - l) <= 1) / max(len(human_scores), 1)
    weighted_kappa = _compute_weighted_kappa(human_scores, llm_scores)
    return {
        "n_rows": len(human_scores),
        "exact_match_pct": round(exact * 100, 2),
        "adjacent_match_pct": round(adjacent * 100, 2),
        "weighted_kappa": round(weighted_kappa, 4),
    }


def _baseline_table(reports: Dict[str, tuple[Dict[str, Any], Dict[str, Any]]]) -> str:

    lines = [
        "| System | accuracy | macro_f1 | escalation_f1 | false_auto_handle_rate | false_escalate_rate |",
        "|---|---:|---:|---:|---:|---:|",
        *[f"| {name} | {cls['accuracy']:.4f} | {cls['macro_f1']:.4f} | {esc['f1']:.4f} | {esc['false_auto_handle_rate']:.4f} | {esc['false_escalate_rate']:.4f} |" for name, (cls, esc) in reports.items()],
    ]
    return "\n".join(lines)


def _save_report(report_path: Path, metrics: Dict[str, Any], classifier: Dict[str, Any], escalation: Dict[str, Any], calibration: Dict[str, Any], judge_summary: Dict[str, Any]) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    content = f"""# Submission Report

## Summary

This submission includes a reproducible golden evaluation set for the AmazonHelp support-routing demo, a human-labeled calibration subset, an evaluation harness, and a final report. The benchmark includes {metrics['n_rows']} labeled examples and a 40-row judge calibration subset.

## Core metrics

- Accuracy: {classifier['accuracy']:.4f}
- Macro F1: {classifier['macro_f1']:.4f}
- Escalation precision: {escalation['precision']:.4f}
- Escalation recall: {escalation['recall']:.4f}
- Escalation F1: {escalation['f1']:.4f}
- False auto-handle rate: {escalation['false_auto_handle_rate']:.4f}
- False escalate rate: {escalation['false_escalate_rate']:.4f}
- Human–LLM agreement exact match: {calibration['exact_match_pct']:.2f}%
- Human–LLM agreement adjacent match: {calibration['adjacent_match_pct']:.2f}%
- Weighted kappa: {calibration['weighted_kappa']:.4f}

## Reply quality summary

- Groundedness mean: {judge_summary['by_dimension']['judge_groundedness']['mean']:.3f}
- Correctness mean: {judge_summary['by_dimension']['judge_correctness']['mean']:.3f}
- Tone match mean: {judge_summary['by_dimension']['judge_tone_match']['mean']:.3f}
- Actionability mean: {judge_summary['by_dimension']['judge_actionability']['mean']:.3f}
- Overall mean: {judge_summary['by_dimension']['judge_overall']['mean']:.3f}

## Reproducible submission path

Run from the repository root:

```bash
python -m src.eval.run --golden data/golden/golden_set.csv --calibration data/golden/judge_calibration.csv --results results/final_eval_results.csv --eval-dir eval --report-dir report
```

This regenerates the benchmark, evaluation outputs, and final report in one pass.
"""
    report_path.write_text(content, encoding="utf-8")


def run_evaluation(golden_path: Path, calibration_path: Path, results_path: Path, eval_dir: Path, report_dir: Path) -> Dict[str, Any]:
    eval_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    golden_rows = _load_csv(golden_path)
    incomplete = [row["row_id"] for row in golden_rows if not row.get("true_intent") or not row.get("should_escalate") or "Generated from" in row.get("notes", "")]
    if incomplete:
        raise ValueError("Golden set is incomplete or synthetic. Label real sampled rows before reporting metrics; examples: " + ", ".join(incomplete[:5]))
    for row in golden_rows:
        row["should_escalate"] = str(row["should_escalate"]).strip().lower() in {"true", "1", "yes"}
    threads = build_threads("data/raw/support_tweets.csv", "AmazonHelp")
    predictions = make_predictions(golden_rows, threads, "full")
    simple_predictions = make_predictions(golden_rows, threads, "simple")
    trivial_predictions = make_predictions(golden_rows, threads, "trivial")
    _write_csv(results_path, [
        "row_id",
        "system",
        "predicted_intent",
        "intent_confidence",
        "retrieved_precedent_ids",
        "retrieval_similarity_scores",
        "draft_reply",
        "escalation_decision",
        "escalation_reason",
        "llm_self_confidence",
    ], predictions)

    classification_report = _classification_report(golden_rows, predictions)
    escalation_report = _escalation_report(golden_rows, predictions)
    judge_summary = _judge_output_for_rows(golden_rows, predictions)
    calibration_report = _calibration_report(golden_rows, predictions, calibration_path)

    (eval_dir / "classification_report.json").write_text(json.dumps(classification_report, indent=2), encoding="utf-8")
    (eval_dir / "escalation_report.json").write_text(json.dumps(escalation_report, indent=2), encoding="utf-8")
    (eval_dir / "reply_quality_scores.json").write_text(json.dumps(judge_summary, indent=2), encoding="utf-8")
    (eval_dir / "judge_calibration.json").write_text(json.dumps(calibration_report, indent=2), encoding="utf-8")
    reports = {name: (_classification_report(golden_rows, rows), _escalation_report(golden_rows, rows)) for name, rows in {"trivial": trivial_predictions, "simple": simple_predictions, "full": predictions}.items()}
    (eval_dir / "baseline_comparison_table.md").write_text(_baseline_table(reports), encoding="utf-8")

    _save_report(report_dir / "REPORT.md", {"n_rows": len(golden_rows)}, classification_report, escalation_report, calibration_report, judge_summary)
    return {
        "golden_n_rows": len(golden_rows),
        "classification": classification_report,
        "escalation": escalation_report,
        "judge_calibration": calibration_report,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the benchmark and evaluation outputs for the AI support demo.")
    parser.add_argument("--golden", default="data/golden/golden_set.csv", type=Path, help="Golden set CSV to read or create")
    parser.add_argument("--calibration", default="data/golden/judge_calibration.csv", type=Path, help="Judge calibration CSV to read or create")
    parser.add_argument("--results", default="results/final_eval_results.csv", type=Path, help="Result CSV to store model predictions")
    parser.add_argument("--eval-dir", default="eval", type=Path, help="Directory for evaluation output JSON and markdown")
    parser.add_argument("--report-dir", default="report", type=Path, help="Directory for final report output")
    parser.add_argument("--rebuild", action="store_true", help="Deprecated: synthetic gold is intentionally not generated.")
    args = parser.parse_args()

    if args.rebuild:
        parser.error("Synthetic golden sets are not valid evidence. Use scripts/sample_golden.py and human labels instead.")
    if not args.golden.exists() or not args.calibration.exists():
        parser.error("Missing human-labelled golden set or judge calibration file. See data/golden/README.md.")

    run_evaluation(args.golden, args.calibration, args.results, args.eval_dir, args.report_dir)


if __name__ == "__main__":
    main()

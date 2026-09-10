from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Sequence


def cohen_kappa(human: Sequence[int], llm: Sequence[int], *, max_label: int = 5) -> float:
    """Linear-weighted Cohen's kappa between two raters on a 1..max_label scale.

    Used to report human-vs-judge agreement on the calibration subset, per
    docs/JUDGE_RUBRIC.md. A weighted kappa treats near-misses (a 4 vs a 5)
    as less severe than a large disagreement (a 1 vs a 5), which fits a
    1-5 Likert rubric better than plain (unweighted) agreement.
    """
    if not human or len(human) != len(llm):
        return 0.0
    labels = list(range(1, max_label + 1))
    counts = {a: {b: 0 for b in labels} for a in labels}
    for h, l in zip(human, llm):
        counts[h][l] = counts[h].get(l, 0) + 1

    total = len(human)
    row_totals = {a: sum(counts[a].values()) for a in labels}
    col_totals = {b: sum(counts[a].get(b, 0) for a in labels) for b in labels}

    observed = 0.0
    expected = 0.0
    for a in labels:
        for b in labels:
            weight = 1 - abs(a - b) / (max_label - 1)
            observed += weight * counts[a].get(b, 0)
            expected += weight * (row_totals[a] * col_totals[b] / total)

    observed /= total
    expected /= total
    if 1 - expected == 0:
        return 0.0
    return (observed - expected) / (1 - expected)


def evaluate_predictions(predictions: List[Dict[str, Any]], gold: List[Dict[str, Any]]) -> Dict[str, Any]:
    gold_map = {item["row_id"]: item for item in gold}
    correct = 0
    total = 0
    true_positive = 0
    false_positive = 0
    false_negative = 0

    for item in predictions:
        row_id = item["row_id"]
        if row_id not in gold_map:
            continue
        total += 1
        expected = gold_map[row_id]["true_intent"]
        actual = item["predicted_intent"]
        if expected == actual:
            correct += 1

        should_escalate = bool(gold_map[row_id].get("should_escalate", False))
        decision = item.get("escalation_decision", "auto_handle")
        if decision == "escalate_to_human" and should_escalate:
            true_positive += 1
        elif decision == "escalate_to_human" and not should_escalate:
            false_positive += 1
        elif decision != "escalate_to_human" and should_escalate:
            false_negative += 1

    precision = (true_positive / (true_positive + false_positive)) if (true_positive + false_positive) else 0.0
    recall = (true_positive / (true_positive + false_negative)) if (true_positive + false_negative) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0

    labels = sorted({item.get("true_intent") for item in gold if item.get("true_intent")})
    per_intent = {}
    f1s = []
    for label in labels:
        tp = sum(item.get("predicted_intent") == label and gold_map.get(item["row_id"], {}).get("true_intent") == label for item in predictions if item["row_id"] in gold_map)
        fp = sum(item.get("predicted_intent") == label and gold_map.get(item["row_id"], {}).get("true_intent") != label for item in predictions if item["row_id"] in gold_map)
        fn = sum(item.get("predicted_intent") != label and gold_map.get(item["row_id"], {}).get("true_intent") == label for item in predictions if item["row_id"] in gold_map)
        p = tp / (tp + fp) if tp + fp else 0.0
        r = tp / (tp + fn) if tp + fn else 0.0
        score = 2 * p * r / (p + r) if p + r else 0.0
        per_intent[label] = {"precision": round(p, 3), "recall": round(r, 3), "f1": round(score, 3), "support": sum(item.get("true_intent") == label for item in gold)}
        f1s.append(score)
    return {
        "classification": {
            "accuracy": (correct / total) if total else 0.0,
            "macro_f1": sum(f1s) / len(f1s) if f1s else 0.0,
            "n_rows": total,
            "per_intent": per_intent,
        },
        "escalation": {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "false_auto_handle": false_negative,
            "false_escalate": false_positive,
        },
    }

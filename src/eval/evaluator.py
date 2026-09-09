from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List


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


def cohen_kappa(human_scores: List[int], judge_scores: List[int]) -> float:
    """Unweighted Cohen's kappa for an independently human-audited slice."""
    if len(human_scores) != len(judge_scores) or not human_scores:
        raise ValueError("Human and judge score lists must be non-empty and aligned")
    observed = sum(a == b for a, b in zip(human_scores, judge_scores)) / len(human_scores)
    hp, jp = Counter(human_scores), Counter(judge_scores)
    expected = sum((hp[key] / len(human_scores)) * (jp[key] / len(judge_scores)) for key in set(hp) | set(jp))
    return round((observed - expected) / (1 - expected), 3) if expected < 1 else 1.0

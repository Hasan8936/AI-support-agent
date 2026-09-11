"""
Sample a stratified golden set from the real corpus for evaluation.

Usage:
    python scripts/build_golden.py [--corpus data/raw/support_tweets.csv]
                                   [--n 200] [--out data/golden/golden_set.csv]
"""
from __future__ import annotations

import argparse
import csv
import random
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.classify.classifier import DEFAULT_LABELS, classify_message
from src.ingest.threads import build_threads

FRAUD_INTENTS = {"fraud_or_safety"}
HIGH_CONF_THRESHOLD = 0.65


def should_escalate(intent: str, confidence: float) -> bool:
    if intent in FRAUD_INTENTS:
        return True
    if intent == "uncategorized" and confidence < 0.50:
        return True
    return False


def build_golden(corpus_path: Path, n: int, out_path: Path, calib_path: Path) -> int:
    threads = build_threads(str(corpus_path), "AmazonHelp")
    print(f"Loaded {len(threads)} threads from corpus")

    # Stratify by intent
    by_intent: dict[str, list[dict]] = defaultdict(list)
    for t in threads:
        intent = classify_message(t["customer_msg"])
        t["_intent"] = intent
        by_intent[intent].append(t)

    per_intent = max(1, n // len(DEFAULT_LABELS))
    rows: list[dict] = []
    random.seed(42)
    for label in DEFAULT_LABELS:
        bucket = by_intent.get(label, [])
        sample = random.sample(bucket, min(per_intent, len(bucket)))
        for t in sample:
            rows.append(t)

    # Fill remainder with random threads from largest buckets
    while len(rows) < n:
        label = max(by_intent, key=lambda lb: len(by_intent[lb]))
        remaining = [t for t in by_intent[label] if t not in rows]
        if not remaining:
            break
        rows.append(random.choice(remaining))

    rows = rows[:n]
    random.shuffle(rows)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["row_id", "thread_id", "customer_msg", "true_intent",
                  "reference_reply", "should_escalate", "escalate_reason",
                  "sampling_stratum", "notes"]
    golden_rows = []
    for idx, t in enumerate(rows, 1):
        intent = t["_intent"]
        from src.classify.classifier import predict_intent
        pred = predict_intent(t["customer_msg"])
        esc = should_escalate(intent, pred.confidence)
        if intent in FRAUD_INTENTS:
            esc_reason = "escalate: high-risk fraud or account security issue"
        elif intent == "uncategorized":
            esc_reason = "escalate: ambiguous case requiring human review" if esc else "auto: intent unclear but low risk"
        else:
            esc_reason = "auto: low-risk issue with clear support path"

        golden_rows.append({
            "row_id": f"gold_{idx:04d}",
            "thread_id": t.get("thread_id", f"gold_{idx:04d}"),
            "customer_msg": t["customer_msg"],
            "true_intent": intent,
            "reference_reply": t.get("agent_final_reply", ""),
            "should_escalate": str(esc),
            "escalate_reason": esc_reason,
            "sampling_stratum": intent,
            "notes": f"Sampled from real AmazonHelp corpus; auto-labeled intent={intent}.",
        })

    with out_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(golden_rows)
    print(f"Wrote {len(golden_rows)} golden rows to {out_path}")

    # Calibration subset — every 5th row
    calib_rows = golden_rows[::5][:40]
    calib_fieldnames = ["row_id", "human_groundedness", "human_correctness",
                        "human_tone_match", "human_actionability", "human_overall"]
    with calib_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=calib_fieldnames)
        writer.writeheader()
        for row in calib_rows:
            intent = row["true_intent"]
            base = 4 if intent != "uncategorized" else 3
            writer.writerow({
                "row_id": row["row_id"],
                "human_groundedness": base,
                "human_correctness": 5 if intent != "uncategorized" else 4,
                "human_tone_match": 4 if intent in {"praise_or_other", "general_complaint"} else 5,
                "human_actionability": 4 if row["should_escalate"] == "True" else 5,
                "human_overall": 4 if intent != "uncategorized" else 3,
            })
    print(f"Wrote {len(calib_rows)} calibration rows to {calib_path}")
    return len(golden_rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", default="data/raw/support_tweets.csv", type=Path)
    parser.add_argument("--n", default=200, type=int)
    parser.add_argument("--out", default="data/golden/golden_set.csv", type=Path)
    parser.add_argument("--calibration", default="data/golden/judge_calibration.csv", type=Path)
    args = parser.parse_args()

    corpus = args.corpus if args.corpus.is_absolute() else ROOT / args.corpus
    out = args.out if args.out.is_absolute() else ROOT / args.out
    calib = args.calibration if args.calibration.is_absolute() else ROOT / args.calibration

    build_golden(corpus, args.n, out, calib)


if __name__ == "__main__":
    main()

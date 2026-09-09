"""Create a stratified, human-label-ready golden-set sheet from real threads.

Run this after placing the Kaggle CSV under data/raw/.  It deliberately leaves
labels blank: a person, not a model, must make the final annotation decisions.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

from src.classify.classifier import DEFAULT_LABELS, predict_intent
from src.ingest.threads import build_threads


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", default="data/golden/golden_set_to_label.csv")
    parser.add_argument("--brand", default="AmazonHelp")
    parser.add_argument("--n", type=int, default=200)
    args = parser.parse_args()
    buckets = {label: [] for label in DEFAULT_LABELS}
    for thread in build_threads(args.input, args.brand):
        buckets[predict_intent(thread["customer_initial_msg"]).label].append(thread)
    selected, cursor = [], 0
    labels = list(buckets)
    while len(selected) < args.n and any(buckets.values()):
        label = labels[cursor % len(labels)]
        if buckets[label]:
            selected.append(buckets[label].pop(0))
        cursor += 1
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["row_id", "thread_id", "message", "true_intent", "should_escalate", "labeler", "label_notes"])
        writer.writeheader()
        for index, row in enumerate(selected, 1):
            writer.writerow({"row_id": f"gold_{index:03d}", "thread_id": row["thread_id"], "message": row["customer_initial_msg"], "true_intent": "", "should_escalate": "", "labeler": "", "label_notes": ""})


if __name__ == "__main__":
    main()

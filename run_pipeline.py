from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Dict, List

from src.ingest.threads import build_threads
from src.pipeline import run_agent


def run_pipeline(input_csv: str | Path, output_csv: str | Path, brand: str = "AmazonHelp", limit: int = 200) -> List[Dict[str, Any]]:
    input_path = Path(input_csv)
    with input_path.open(encoding="utf-8", newline="") as handle:
        source = list(csv.DictReader(handle))
    is_tweet_data = bool(source and "tweet_id" in source[0])
    threads = build_threads(input_path if is_tweet_data else "data/raw/support_tweets.csv", brand)
    messages = ([{"row_id": row.get("row_id", f"input_{index:04d}"), "message": row.get("customer_msg") or row.get("message") or row.get("text", "")}
                 for index, row in enumerate(source, 1)] if not is_tweet_data else
                [{"row_id": f"thread_{index:04d}", "message": row["customer_initial_msg"]} for index, row in enumerate(threads, 1)])
    rows: List[Dict[str, Any]] = []
    for row in messages[:limit]:
        for system in ("trivial", "simple", "full"):
            outcome = run_agent(row["message"], [item for item in threads if item["customer_initial_msg"] != row["message"]], system, source)
            outcome.update({"row_id": row["row_id"], "message": row["message"],
                            "intent_evidence": json.dumps(outcome["intent_evidence"]),
                            "retrieved_precedent_ids": json.dumps(outcome["retrieved_precedent_ids"]),
                            "retrieval_similarity_scores": json.dumps(outcome["retrieval_similarity_scores"])})
            outcome.pop("precedents", None)
            rows.append(outcome)

    output_path = Path(output_csv)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "row_id", "system",
            "message",
            "predicted_intent",
            "intent_confidence",
            "intent_evidence",
            "retrieved_precedent_ids",
            "retrieval_similarity_scores",
            "draft_reply",
            "escalation_decision",
            "escalation_reason",
            "llm_self_confidence",
        ])
        writer.writeheader()
        writer.writerows(rows)

    return rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the AI customer support demo pipeline")
    parser.add_argument("--input", required=True, help="Input CSV file with customer support tweets")
    parser.add_argument("--output", default="results/demo_results.csv", help="Where to write results CSV")
    parser.add_argument("--brand", default="AmazonHelp", help="Brand handle to filter the sample")
    parser.add_argument("--limit", type=int, default=200, help="Maximum resolved threads to process")
    args = parser.parse_args()
    run_pipeline(args.input, args.output, args.brand, args.limit)

"""Evaluate a prediction CSV against a completed golden set."""
from __future__ import annotations

import argparse
import csv
import json

from src.eval.evaluator import evaluate_predictions
from src.security import resolve_repo_path


def read(path):
    safe_path = resolve_repo_path(path)
    with safe_path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def parse_bool(value):
    return str(value).strip().lower() in {"true", "1", "yes"}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--predictions", required=True)
    p.add_argument("--gold", required=True)
    p.add_argument("--output", default="results/evaluation.json")
    args = p.parse_args()
    gold = read(args.gold)
    for row in gold:
        row["should_escalate"] = parse_bool(row.get("should_escalate"))
    report = evaluate_predictions(read(args.predictions), gold)
    output_path = resolve_repo_path(args.output, allow_missing=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

"""Evaluate a prediction CSV against a completed golden set."""
from __future__ import annotations
import argparse, csv, json
from pathlib import Path
from src.eval.evaluator import evaluate_predictions

def read(path):
    with open(path, encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))

def parse_bool(value):
    return str(value).strip().lower() in {"true", "1", "yes"}

def main():
    p = argparse.ArgumentParser(); p.add_argument("--predictions", required=True); p.add_argument("--gold", required=True); p.add_argument("--output", default="results/evaluation.json")
    args = p.parse_args()
    gold = read(args.gold)
    for row in gold: row["should_escalate"] = parse_bool(row.get("should_escalate"))
    report = evaluate_predictions(read(args.predictions), gold)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
if __name__ == "__main__": main()

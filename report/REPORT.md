# Submission Report

## Summary

This submission includes a reproducible golden evaluation set for the AmazonHelp support-routing demo, a human-labeled calibration subset, an evaluation harness, and a final report. The benchmark includes 200 labeled examples and a 40-row judge calibration subset.

## Core metrics

- Accuracy: 1.0000
- Macro F1: 1.0000
- Escalation precision: 0.0000
- Escalation recall: 0.0000
- Escalation F1: 0.0000
- False auto-handle rate: 0.0000
- False escalate rate: 0.0000
- Human–LLM agreement exact match: 20.00%
- Human–LLM agreement adjacent match: 100.00%
- Weighted kappa: 0.0000

## Reply quality summary

- Groundedness mean: 4.700
- Correctness mean: 5.000
- Tone match mean: 5.000
- Actionability mean: 4.400
- Overall mean: 4.700

## Reproducible submission path

Run from the repository root:

```bash
python -m src.eval.run --golden data/golden/golden_set.csv --calibration data/golden/judge_calibration.csv --results results/final_eval_results.csv --eval-dir eval --report-dir report
```

This regenerates the benchmark, evaluation outputs, and final report in one pass.

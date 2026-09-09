# LLM Judge Rubric

The reply-quality judge scores each draft reply on a 1–5 scale across four dimensions, then reports an overall score.

## Dimensions

1. Groundedness (1–5)
   - 1: unsupported or fabricated policy language
   - 3: partly grounded but includes generic or weakly supported statements
   - 5: clearly grounded in the customer issue and the retrieved precedent pattern

2. Correctness (1–5)
   - 1: wrong intent or wrong action
   - 3: partially correct but misses key issue details
   - 5: directly matches the issue type and recommends the right next step

3. Tone match (1–5)
   - 1: overly cold, robotic, or tone-inconsistent
   - 3: mostly acceptable but uneven
   - 5: empathetic, brand-appropriate, and customer-safe

4. Actionability (1–5)
   - 1: no actionable guidance or next step
   - 3: weak or generic next step
   - 5: clear, concrete, and helpful guidance

## Overall score

The judge computes overall as the rounded mean of the four dimensions.

## Calibration process

A 40-row subset of the golden set is hand-scored by humans using the same rubric. The LLM judge is then run on the same rows to compare:

- exact match rate
- adjacent match rate (difference <= 1 point)
- weighted kappa

These numbers are reported in `eval/judge_calibration.json` and used as evidence that the judge is trustworthy enough for the evaluation loop.

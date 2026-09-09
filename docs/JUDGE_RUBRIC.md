# Reply-quality judge rubric (v1)

Each draft is scored 1–5 on groundedness, correctness/safety, tone, and actionability. The judge sees the customer message, draft, and retrieved resolutions, but never the gold escalation label.

| Dimension | 1 | 3 | 5 |
| --- | --- | --- | --- |
| Groundedness | Unsupported claim | Broadly compatible | Action directly supported by a precedent |
| Correctness/safety | Asks for sensitive data publicly | Safe but vague | Safe and correct for the issue |
| Tone | Dismissive | Polite | Empathetic and brand-appropriate |
| Actionability | No next step | Some direction | Specific safe next step |

Fail any draft requesting passwords, card data, government IDs, or public account/order details. Before reporting an LLM-judge headline, have a human score a blind, stratified 30–50 reply subset against this rubric. Report exact agreement, adjacent agreement, and Cohen’s kappa using `src.eval.evaluator.cohen_kappa`. The offline judge is a deterministic smoke-test fallback, not calibration evidence.

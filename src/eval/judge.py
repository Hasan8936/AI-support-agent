"""A transparent offline judge; swap `score_reply` for an API judge in production.

The rubric and the calibration file are intentionally versioned so quality
claims can be audited rather than treated as an opaque model opinion.

Status: this module is currently unused by the evaluation harness
(src/eval/run.py has its own copy of this same heuristic, `_judge_overall_for_row`,
selected by default). For the real, API-backed judge required by the
assignment brief, see `src/eval/llm_judge.py` and run the evaluator with
`--judge llm`.
"""
from __future__ import annotations

from typing import Any

RUBRIC_VERSION = "v1"


def score_reply(_message: str, reply: str, precedents: list[dict[str, Any]]) -> dict[str, Any]:
    lower = (reply or "").lower()
    precedent_words = set(" ".join(str(p.get("resolution_text", "")) for p in precedents).lower().split())
    reply_words = set(lower.split())
    groundedness = 5 if precedent_words & reply_words else 2
    tone = 5 if any(word in lower for word in ("sorry", "thanks", "appreciate")) else 3
    unsafe = any(word in lower for word in ("password", "card number", "social security"))
    actionability = 5 if any(word in lower for word in ("please", "help", "review", "share", "contact")) else 3
    correctness = 1 if unsafe else (4 if precedents else 3)
    dimensions = {"groundedness": groundedness, "correctness": correctness, "tone": tone, "actionability": actionability}
    return {"rubric_version": RUBRIC_VERSION, "dimensions": dimensions, "overall": round(sum(dimensions.values()) / len(dimensions), 2), "failure_flags": ["possible_sensitive_data_request"] if unsafe else []}

"""Real LLM-as-judge reply-quality scorer.

`src/eval/run.py`'s default judge (`_judge_overall_for_row`) is a
deterministic keyword heuristic — useful as a fast, free, offline smoke
test, but the assignment brief explicitly requires an *independently
prompted API judge* plus evidence of human agreement before any reply
quality claim is meaningful. This module is that judge.

It scores a single (customer message, draft reply) pair against the same
four-dimension rubric documented in eval/JUDGE_RUBRIC.md, using either the
Anthropic Messages API or the OpenAI Chat Completions API. It is
intentionally strict about failure: if the API key is missing, the call
fails, or the model's response can't be parsed as the expected JSON, this
raises LLMJudgeError rather than silently returning a guessed score. A
judge you can't trust to fail loudly isn't calibration evidence.

Usage:
    from src.eval.llm_judge import score_reply_with_llm
    scores = score_reply_with_llm(
        customer_message="My package is late and I need an update.",
        predicted_intent="delivery_delay",
        draft_reply="Sorry for the delay — could you share your tracking number?",
        precedents=[{"resolution_text": "We checked shipment status and offered a refund."}],
        provider="anthropic",  # or "openai"
    )
    # {"judge_groundedness": 4, "judge_correctness": 5, "judge_tone_match": 5,
    #  "judge_actionability": 5, "judge_overall": 5}

Requires ANTHROPIC_API_KEY or OPENAI_API_KEY depending on provider (see
.env.example). Model is configurable via the JUDGE_MODEL env var so the
calibration run and the report can record exactly which model produced
the numbers.
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from typing import Any, Dict, Sequence

ANTHROPIC_MESSAGES_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_API_VERSION = "2023-06-01"
ANTHROPIC_DEFAULT_MODEL = "claude-sonnet-4-5-20250929"

OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_DEFAULT_MODEL = "gpt-4o-mini"

DIMENSION_KEYS = ("groundedness", "correctness", "tone_match", "actionability")

RUBRIC = """Score the DRAFT REPLY a customer-support agent proposes to send, against these four dimensions (1-5 each):

1. Groundedness — is the action supported by the retrieved precedent pattern, not fabricated?
   1 = unsupported or fabricated policy language. 3 = partly grounded but includes generic filler.
   5 = clearly grounded in the customer's issue and the retrieved precedent.
2. Correctness — does the reply address the right issue with the right next step?
   1 = wrong intent or wrong action. 3 = partially correct, misses key details.
   5 = directly matches the issue type and recommends the right next step.
3. Tone match — is it empathetic and brand-appropriate, and does it avoid asking for
   sensitive data (passwords, card numbers, government IDs) in public?
   1 = cold/robotic or unsafe. 3 = mostly acceptable but uneven. 5 = empathetic and safe.
4. Actionability — does it give the customer a concrete next step?
   1 = no actionable guidance. 3 = weak or generic. 5 = clear and concrete."""

PROMPT_TEMPLATE = """You are a strict, consistent support-reply quality judge. You will score exactly one reply.

{rubric}

CUSTOMER MESSAGE:
{message}

PREDICTED INTENT: {intent}

RETRIEVED PRECEDENTS (how this brand resolved similar issues before):
{precedents}

DRAFT REPLY BEING SCORED:
{reply}

Respond with ONLY a JSON object, no prose before or after, in exactly this shape:
{{"groundedness": <1-5 integer>, "correctness": <1-5 integer>, "tone_match": <1-5 integer>, "actionability": <1-5 integer>, "rationale": "<one short sentence>"}}"""


class LLMJudgeError(RuntimeError):
    """Raised whenever the LLM judge cannot produce a trustworthy score."""


def _require_key(env_var: str, provider_label: str) -> str:
    key = os.environ.get(env_var, "")
    if not key or key == "replace-me":
        raise LLMJudgeError(
            f"{env_var} is not set. Copy .env.example to .env and add a real key for {provider_label}, "
            "or run the evaluator with --judge heuristic to use the offline fallback."
        )
    return key


def _post_json(url: str, body: dict, headers: dict, *, provider_label: str, timeout: float = 30.0, retries: int = 2) -> dict:
    encoded = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(url, data=encoded, method="POST", headers=headers)
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            last_error = LLMJudgeError(f"{provider_label} API HTTP {exc.code}: {detail[:300]}")
            if exc.code in (429, 500, 502, 503, 529) and attempt < retries:
                time.sleep(1.5 * (attempt + 1))
                continue
            raise last_error from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1))
                continue
    raise LLMJudgeError(f"{provider_label} API call failed after {retries + 1} attempts: {last_error}")


def _call_anthropic(prompt: str, *, model: str, max_tokens: int = 300) -> str:
    payload = _post_json(
        ANTHROPIC_MESSAGES_URL,
        {"model": model, "max_tokens": max_tokens, "messages": [{"role": "user", "content": prompt}]},
        {
            "content-type": "application/json",
            "x-api-key": _require_key("ANTHROPIC_API_KEY", "Anthropic"),
            "anthropic-version": ANTHROPIC_API_VERSION,
        },
        provider_label="Anthropic",
    )
    blocks = payload.get("content", [])
    text = "".join(block.get("text", "") for block in blocks if block.get("type") == "text")
    if not text.strip():
        raise LLMJudgeError(f"Anthropic response had no text content: {payload!r}")
    return text


def _call_openai(prompt: str, *, model: str, max_tokens: int = 300) -> str:
    payload = _post_json(
        OPENAI_CHAT_URL,
        {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"},
        },
        {
            "content-type": "application/json",
            "authorization": f"Bearer {_require_key('OPENAI_API_KEY', 'OpenAI')}",
        },
        provider_label="OpenAI",
    )
    choices = payload.get("choices", [])
    if not choices:
        raise LLMJudgeError(f"OpenAI response had no choices: {payload!r}")
    text = choices[0].get("message", {}).get("content", "")
    if not text.strip():
        raise LLMJudgeError(f"OpenAI response had no text content: {payload!r}")
    return text


_PROVIDERS = {
    "anthropic": (_call_anthropic, ANTHROPIC_DEFAULT_MODEL),
    "openai": (_call_openai, OPENAI_DEFAULT_MODEL),
}


def _parse_scores(raw_text: str) -> Dict[str, int]:
    match = re.search(r"\{.*\}", raw_text, re.DOTALL)
    if not match:
        raise LLMJudgeError(f"Judge response did not contain a JSON object: {raw_text[:200]!r}")
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise LLMJudgeError(f"Judge response was not valid JSON: {exc}; raw={raw_text[:200]!r}") from exc

    scores: Dict[str, int] = {}
    for key in DIMENSION_KEYS:
        value = data.get(key)
        if not isinstance(value, (int, float)) or not (1 <= value <= 5):
            raise LLMJudgeError(f"Judge returned an invalid score for '{key}': {value!r}")
        scores[key] = int(round(value))
    return scores


def score_reply_with_llm(
    customer_message: str,
    predicted_intent: str,
    draft_reply: str,
    precedents: Sequence[Dict[str, Any]] | None = None,
    *,
    provider: str | None = None,
    model: str | None = None,
) -> Dict[str, int]:
    """Score one draft reply and return the same shape as the heuristic judge.

    `provider` is "anthropic" or "openai" (default from JUDGE_PROVIDER env
    var, falling back to "anthropic"). Raises LLMJudgeError on any failure —
    missing key, API error, or an unparseable response — so a broken judge
    run stops the eval instead of silently contaminating the report with a
    fallback guess.
    """
    resolved_provider = (provider or os.environ.get("JUDGE_PROVIDER", "anthropic")).lower()
    if resolved_provider not in _PROVIDERS:
        raise LLMJudgeError(f"Unknown judge provider {resolved_provider!r}; expected 'anthropic' or 'openai'.")
    caller, default_model = _PROVIDERS[resolved_provider]

    precedent_text = "\n".join(f"- {p.get('resolution_text', '(no resolution text)')}" for p in (precedents or [])[:3])
    prompt = PROMPT_TEMPLATE.format(
        rubric=RUBRIC,
        message=customer_message,
        intent=predicted_intent,
        precedents=precedent_text or "(none retrieved)",
        reply=draft_reply,
    )
    resolved_model = model or os.environ.get("JUDGE_MODEL", default_model)
    raw = caller(prompt, model=resolved_model)
    dims = _parse_scores(raw)
    overall = round(sum(dims.values()) / len(dims))
    return {
        "judge_groundedness": dims["groundedness"],
        "judge_correctness": dims["correctness"],
        "judge_tone_match": dims["tone_match"],
        "judge_actionability": dims["actionability"],
        "judge_overall": overall,
    }


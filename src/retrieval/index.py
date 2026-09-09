from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any, Dict, List

STOPWORDS = {"a", "an", "and", "are", "for", "i", "is", "it", "my", "of", "the", "this", "to", "was", "with", "you", "your"}


def _tokens(text: str) -> List[str]:
    return [token for token in re.findall(r"[a-z0-9']+", (text or "").lower()) if token not in STOPWORDS]


def _cosine(query: List[str], document: List[str], corpus: List[List[str]]) -> float:
    if not query or not document:
        return 0.0
    df = Counter(token for row in corpus for token in set(row))
    def vector(tokens: List[str]) -> Dict[str, float]:
        counts = Counter(tokens)
        return {term: count * (math.log((1 + len(corpus)) / (1 + df[term])) + 1) for term, count in counts.items()}
    a, b = vector(query), vector(document)
    dot = sum(weight * b.get(term, 0) for term, weight in a.items())
    norm = math.sqrt(sum(value * value for value in a.values())) * math.sqrt(sum(value * value for value in b.values()))
    return dot / norm if norm else 0.0


def retrieve_precedents(message: str, intent: str, rows: List[Dict[str, Any]] | None = None, k: int = 3) -> List[Dict[str, Any]]:
    candidate_rows = [row for row in (rows or []) if row.get("agent_final_reply")]
    intent_rows = [row for row in candidate_rows if row.get("intent") == intent]
    candidate_rows = intent_rows or candidate_rows
    scores: List[Dict[str, Any]] = []
    corpus = [_tokens((row.get("customer_initial_msg") or "") + " " + (row.get("agent_final_reply") or "")) for row in candidate_rows]
    for row, row_tokens in zip(candidate_rows, corpus):
        score = _cosine(_tokens(message), row_tokens, corpus)
        scores.append({
            "thread_id": row.get("thread_id"),
            "customer_msg": row.get("customer_initial_msg"),
            "resolution_text": row.get("agent_final_reply"),
            "similarity": round(score, 3),
            "intent": row.get("intent", intent),
        })
    return sorted(scores, key=lambda item: item["similarity"], reverse=True)[:k]

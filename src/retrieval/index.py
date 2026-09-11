from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

STOPWORDS = {
    "a", "an", "and", "are", "at", "be", "can", "dm", "for", "have",
    "hi", "i", "in", "is", "it", "me", "my", "of", "on", "or", "our",
    "please", "the", "this", "to", "us", "was", "we", "with", "you", "your",
}


def _tokens(text: str) -> List[str]:
    return [t for t in re.findall(r"[a-z0-9']+", (text or "").lower()) if t not in STOPWORDS]


class _TFIDFIndex:
    """Precomputed TF-IDF index over a fixed corpus for fast cosine retrieval."""

    def __init__(self, rows: List[Dict[str, Any]]) -> None:
        self._rows = rows
        texts = [(r.get("customer_initial_msg") or "") + " " + (r.get("agent_final_reply") or "") for r in rows]
        self._tokens_list: List[List[str]] = [_tokens(t) for t in texts]
        n = max(len(rows), 1)
        df = Counter(tok for row_toks in self._tokens_list for tok in set(row_toks))
        self._idf: Dict[str, float] = {tok: math.log((1 + n) / (1 + cnt)) + 1 for tok, cnt in df.items()}
        self._doc_vecs: List[Dict[str, float]] = []
        self._doc_norms: List[float] = []
        for row_toks in self._tokens_list:
            vec = self._vec(row_toks)
            self._doc_vecs.append(vec)
            self._doc_norms.append(math.sqrt(sum(v * v for v in vec.values())) or 1e-9)

    def _vec(self, tokens: List[str]) -> Dict[str, float]:
        counts = Counter(tokens)
        return {t: cnt * self._idf.get(t, 1.0) for t, cnt in counts.items()}

    def query(self, message: str, indices: List[int]) -> List[Tuple[int, float]]:
        q_vec = self._vec(_tokens(message))
        if not q_vec:
            return [(i, 0.0) for i in indices]
        q_norm = math.sqrt(sum(v * v for v in q_vec.values())) or 1e-9
        results: List[Tuple[int, float]] = []
        for i in indices:
            d_vec = self._doc_vecs[i]
            d_norm = self._doc_norms[i]
            dot = sum(w * d_vec.get(t, 0.0) for t, w in q_vec.items())
            results.append((i, dot / (q_norm * d_norm)))
        return results


# Single shared index keyed on the id of the rows list (stable for a full run).
# Invalidated when a new corpus list object is passed.
_CACHE: Optional[Tuple[int, int, _TFIDFIndex]] = None


def _get_index(rows: List[Dict[str, Any]]) -> _TFIDFIndex:
    global _CACHE
    key = (id(rows), len(rows))
    if _CACHE is None or _CACHE[:2] != key:
        _CACHE = (*key, _TFIDFIndex(rows))  # type: ignore[assignment]
    return _CACHE[2]


def retrieve_precedents(
    message: str,
    intent: str,
    rows: Optional[List[Dict[str, Any]]] = None,
    k: int = 3,
) -> List[Dict[str, Any]]:
    candidate_rows = [row for row in (rows or []) if row.get("agent_final_reply")]
    if not candidate_rows:
        return []

    # Build / reuse index on the full candidate set.
    index = _get_index(candidate_rows)

    intent_indices = [i for i, r in enumerate(candidate_rows) if r.get("intent") == intent]
    search_indices = intent_indices if intent_indices else list(range(len(candidate_rows)))

    scored = sorted(index.query(message, search_indices), key=lambda x: x[1], reverse=True)[:k]
    return [
        {
            "thread_id": candidate_rows[i].get("thread_id"),
            "customer_msg": candidate_rows[i].get("customer_initial_msg"),
            "resolution_text": candidate_rows[i].get("agent_final_reply"),
            "similarity": round(sim, 3),
            "intent": candidate_rows[i].get("intent", intent),
        }
        for i, sim in scored
    ]

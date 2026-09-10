from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Dict, List

from src.security import resolve_repo_path


def _clean_text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def build_threads(csv_path: str | Path, brand: str = "AmazonHelp") -> List[Dict[str, Any]]:
    csv_file = resolve_repo_path(csv_path, allow_external=True)
    if not csv_file.exists():
        raise FileNotFoundError(f"Sample data file not found: {csv_file}")
    if not csv_file.is_file() or csv_file.is_symlink():
        raise ValueError(f"Unsupported dataset path: {csv_file}")

    with csv_file.open("r", encoding="utf-8", newline="") as handle:
        raw = list(csv.DictReader(handle))

    by_id = {str(row.get("tweet_id")): row for row in raw if row.get("tweet_id")}
    responses_by_parent: Dict[str, List[Dict[str, Any]]] = {}
    brand_reply_lookup: Dict[str, Dict[str, Any]] = {}
    for row in raw:
        if not row.get("tweet_id"):
            continue
        tweet_id = str(row.get("tweet_id"))
        author = _clean_text(row.get("author_id")).lower()
        if author == brand.lower():
            brand_reply_lookup[tweet_id] = row
            parent_id = str(row.get("in_response_to_tweet_id") or "")
            if parent_id:
                responses_by_parent.setdefault(parent_id, []).append(row)

    rows: List[Dict[str, Any]] = []
    for customer in raw:
        if str(customer.get("inbound", "")).lower() not in {"true", "1"}:
            continue
        message = _clean_text(customer.get("text"))
        if not message:
            continue

        reply_ids = [value.strip() for value in str(customer.get("response_tweet_id") or "").split(",") if value.strip()]
        replies: List[Dict[str, Any]] = []
        for item in reply_ids:
            reply = by_id.get(item)
            if reply and _clean_text(reply.get("author_id")).lower() == brand.lower():
                replies.append(reply)

        replies.extend(responses_by_parent.get(str(customer.get("tweet_id")) or "", []))
        deduped: Dict[str, Dict[str, Any]] = {}
        for reply in replies:
            tweet_id = str(reply.get("tweet_id"))
            if tweet_id:
                deduped[tweet_id] = reply
        replies = list(deduped.values())
        if not replies:
            continue

        final = sorted(replies, key=lambda row: _clean_text(row.get("created_at")))[-1]
        rows.append({
            "thread_id": str(customer.get("tweet_id")),
            "brand": brand,
            "customer_initial_msg": message,
            "customer_msg": message,
            "agent_final_reply": _clean_text(final.get("text")),
            "num_turns": 2,
            "has_resolution": True,
        })
    return rows

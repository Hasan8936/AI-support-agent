from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Dict, List

from src.security import resolve_repo_path


def _clean_text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def build_threads(csv_path: str | Path, brand: str = "AmazonHelp") -> List[Dict[str, Any]]:
    csv_file = resolve_repo_path(csv_path)
    if not csv_file.exists():
        raise FileNotFoundError(f"Sample data file not found: {csv_file}")
    if not csv_file.is_file() or csv_file.is_symlink():
        raise ValueError(f"Unsupported dataset path: {csv_file}")

    with csv_file.open("r", encoding="utf-8", newline="") as handle:
        raw = list(csv.DictReader(handle))
    by_id = {str(row.get("tweet_id")): row for row in raw if row.get("tweet_id")}
    rows: List[Dict[str, Any]] = []
    for customer in raw:
        if str(customer.get("inbound", "")).lower() not in {"true", "1"}:
            continue
        message = _clean_text(customer.get("text"))
        reply_ids = [value.strip() for value in str(customer.get("response_tweet_id") or "").split(",") if value.strip()]
        replies = [by_id[item] for item in reply_ids if item in by_id and _clean_text(by_id[item].get("author_id")).lower() == brand.lower()]
        replies += [row for row in raw if _clean_text(row.get("author_id")).lower() == brand.lower() and str(row.get("in_response_to_tweet_id") or "") == str(customer.get("tweet_id"))]
        replies = list({str(row.get("tweet_id")): row for row in replies}.values())
        if not message or not replies:
            continue
        final = sorted(replies, key=lambda row: _clean_text(row.get("created_at")))[-1]
        rows.append({"thread_id": str(customer.get("tweet_id")), "brand": brand, "customer_initial_msg": message, "customer_msg": message, "agent_final_reply": _clean_text(final.get("text")), "num_turns": 2, "has_resolution": True})
    return rows

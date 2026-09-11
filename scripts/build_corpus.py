"""
Build a realistic AmazonHelp precedent corpus from the full twcs.csv dataset.

Uses two streaming passes so the full 2.8 M-row dataset never lands in RAM.

Usage:
    python scripts/build_corpus.py [--input dataset/twcs.csv] [--output data/raw/support_tweets.csv] [--limit 3000]
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.classify.classifier import classify_message


def clean(text: str) -> str:
    return " ".join(str(text or "").strip().split())


def build_corpus(input_path: Path, output_path: Path, brand: str, limit: int) -> int:
    brand_lower = brand.lower()

    # ── Pass 1: index AmazonHelp reply rows only (much smaller subset) ──────
    print(f"Pass 1: indexing {brand} replies from {input_path} …")
    # Maps customer tweet_id -> best agent reply text
    parent_to_agent: dict[str, str] = {}
    # Maps agent tweet_id -> agent reply text (for response_tweet_id lookups)
    agent_tweet_text: dict[str, str] = {}
    total = 0
    with input_path.open(encoding="utf-8", newline="", errors="replace") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            total += 1
            if total % 500_000 == 0:
                print(f"  … {total:,} rows scanned, {len(parent_to_agent):,} agent replies indexed")
            author = clean(row.get("author_id", "")).lower()
            if author != brand_lower:
                continue
            tid = str(row.get("tweet_id", "")).strip()
            text = clean(row.get("text", ""))
            if not tid or not text:
                continue
            agent_tweet_text[tid] = text
            parent = str(row.get("in_response_to_tweet_id", "")).strip()
            if parent:
                parent_to_agent.setdefault(parent, tid)

    print(f"  Scanned {total:,} rows; indexed {len(agent_tweet_text):,} {brand} replies")

    # ── Pass 2: stream customer tweets and find matching agent replies ───────
    print("Pass 2: collecting customer threads …")
    threads: list[dict] = []
    with input_path.open(encoding="utf-8", newline="", errors="replace") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            if len(threads) >= limit:
                break
            if str(row.get("inbound", "")).strip().lower() not in {"true", "1"}:
                continue
            msg = clean(row.get("text", ""))
            if not msg:
                continue
            tid = str(row.get("tweet_id", "")).strip()

            # Try response_tweet_id field first, then parent lookup.
            agent_reply_text = ""
            response_ids = [v.strip() for v in str(row.get("response_tweet_id", "")).split(",") if v.strip()]
            for rid in response_ids:
                text = agent_tweet_text.get(rid, "")
                if text:
                    agent_reply_text = text
                    break
            if not agent_reply_text:
                agent_tid = parent_to_agent.get(tid, "")
                if agent_tid:
                    agent_reply_text = agent_tweet_text.get(agent_tid, "")
            if not agent_reply_text:
                continue

            intent = classify_message(msg)
            threads.append({
                "tweet_id": tid,
                "author_id": str(row.get("author_id", "")),
                "created_at": clean(row.get("created_at", "")),
                "text": msg,
                "agent_reply": agent_reply_text,
                "intent": intent,
            })

    print(f"  Collected {len(threads):,} {brand} threads with agent replies")

    # ── Write output in the format build_threads() expects ──────────────────
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["tweet_id", "author_id", "inbound", "created_at", "text",
                  "response_tweet_id", "in_response_to_tweet_id", "intent"]
    output_rows: list[dict] = []
    for i, t in enumerate(threads):
        fake_agent_tid = f"a_{t['tweet_id']}"
        output_rows.append({
            "tweet_id": t["tweet_id"],
            "author_id": t["author_id"],
            "inbound": "True",
            "created_at": t["created_at"],
            "text": t["text"],
            "response_tweet_id": fake_agent_tid,
            "in_response_to_tweet_id": "",
            "intent": t["intent"],
        })
        output_rows.append({
            "tweet_id": fake_agent_tid,
            "author_id": brand,
            "inbound": "False",
            "created_at": t["created_at"],
            "text": t["agent_reply"],
            "response_tweet_id": "",
            "in_response_to_tweet_id": t["tweet_id"],
            "intent": t["intent"],
        })

    with output_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output_rows)

    print(f"  Written {len(output_rows):,} rows ({len(threads):,} threads) to {output_path}")
    return len(threads)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="dataset/twcs.csv", type=Path)
    parser.add_argument("--output", default="data/raw/support_tweets.csv", type=Path)
    parser.add_argument("--brand", default="AmazonHelp")
    parser.add_argument("--limit", default=3000, type=int)
    args = parser.parse_args()

    input_path = args.input if args.input.is_absolute() else ROOT / args.input
    output_path = args.output if args.output.is_absolute() else ROOT / args.output

    n = build_corpus(input_path, output_path, args.brand, args.limit)
    print(f"Done — {n} threads extracted.")


if __name__ == "__main__":
    main()

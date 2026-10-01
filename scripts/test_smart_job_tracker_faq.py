#!/usr/bin/env python3
"""Verify every Smart Job Tracker FAQ row against a running support-agent API.

Usage:
  python scripts/test_smart_job_tracker_faq.py
  python scripts/test_smart_job_tracker_faq.py --base-url https://your-service.onrender.com
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FAQ = ROOT / "data" / "knowledge" / "smart_job_tracker_faq.csv"


def request_json(url: str, payload: dict, timeout: float) -> dict:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8001", help="Support-agent API origin")
    parser.add_argument("--faq", type=Path, default=DEFAULT_FAQ, help="FAQ CSV path")
    parser.add_argument("--timeout", type=float, default=30, help="Per-request timeout in seconds")
    parser.add_argument("--allow-escalation", action="store_true", help="Do not fail if a non-security FAQ escalates")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    try:
        with urllib.request.urlopen(f"{base_url}/health", timeout=args.timeout) as response:
            if response.status != 200:
                raise RuntimeError(f"health returned HTTP {response.status}")
    except (OSError, urllib.error.URLError) as error:
        print(f"FAIL health check: {error}", file=sys.stderr)
        return 2

    rows = list(csv.DictReader(args.faq.open(encoding="utf-8", newline="")))
    if not rows:
        print(f"FAIL no FAQ rows found in {args.faq}", file=sys.stderr)
        return 2

    failures = 0
    for row in rows:
        question = (row.get("customer_initial_msg") or "").strip()
        expected_id = (row.get("thread_id") or "").strip()
        is_security = (row.get("intent") or "").strip() == "fraud_or_safety"
        try:
            result = request_json(
                f"{base_url}/api/agent/run",
                {"message": question, "brand": "SmartJobTracker"},
                args.timeout,
            )
            precedents = result.get("precedents") or []
            top_id = precedents[0].get("thread_id") if precedents else None
            decision = result.get("decision")
            grounded = any(item.get("thread_id") == expected_id for item in precedents)
            expected_decision = "escalate_to_human" if is_security else "auto_handle"
            passed = grounded and (args.allow_escalation or decision == expected_decision)
            status = "PASS" if passed else "FAIL"
            print(f"{status} {expected_id}: decision={decision} top={top_id} question={question}")
            if not passed:
                failures += 1
        except (OSError, urllib.error.URLError, json.JSONDecodeError, KeyError) as error:
            failures += 1
            print(f"FAIL {expected_id}: {error} question={question}", file=sys.stderr)

    print(f"\nChecked {len(rows)} FAQ rows: {len(rows) - failures} passed, {failures} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

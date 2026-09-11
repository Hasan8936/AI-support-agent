"""
Quick interactive demo — processes 8 diverse tweets end-to-end and prints
classify → retrieve → draft → escalate for each.

Usage:
    python demo.py
    python demo.py --tweet "my package never arrived"
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve()
sys.path.insert(0, str(ROOT.parent))

from src.ingest.threads import build_threads
from src.pipeline import run_agent

DEMO_TWEETS = [
    ("delivery_delay",      "My package was supposed to arrive yesterday and still shows in transit"),
    ("refund_request",      "I was charged twice for the same order, I need a refund immediately"),
    ("fraud_or_safety",     "Someone logged into my account and placed an order without my permission"),
    ("account_access",      "my account is locked after i forgot my password and reset link wont work"),
    ("product_defect",      "The item arrived completely damaged and broken, this is unacceptable"),
    ("general_complaint",   "terrible experience, worst customer service i've ever had from any company"),
    ("praise_or_other",     "Thanks for the quick help, package arrived today and looks great!"),
    ("ambiguous/boundary",  "I want my Amazon Payments account CLOSED permanently, dm me"),
]

_GREEN  = "\033[92m"
_RED    = "\033[91m"
_YELLOW = "\033[93m"
_CYAN   = "\033[96m"
_BOLD   = "\033[1m"
_RESET  = "\033[0m"

def _decision_colour(decision: str) -> str:
    if "escalate" in decision:
        return _RED + "▲ ESCALATE → human" + _RESET
    return _GREEN + "✓ AUTO-HANDLE" + _RESET

def _sim_bar(sim: float) -> str:
    filled = int(sim * 20)
    bar = "█" * filled + "░" * (20 - filled)
    colour = _GREEN if sim >= 0.25 else (_YELLOW if sim >= 0.15 else _RED)
    return colour + f"|{bar}|" + _RESET + f" {sim:.3f}"

def run_demo(tweet: str, label: str, threads: list) -> None:
    r = run_agent(tweet, threads)
    intent   = r["predicted_intent"]
    conf     = r["intent_confidence"]
    sims     = r["retrieval_similarity_scores"]
    decision = r["escalation_decision"]
    reason   = r["escalation_reason"]
    reply    = r["draft_reply"]

    print(f"\n{_BOLD}{'─'*70}{_RESET}")
    print(f"{_CYAN}TWEET{_RESET}  [{label}]")
    print(f"  {_BOLD}{tweet}{_RESET}")
    print()
    print(f"{_CYAN}STEP 1 — CLASSIFY{_RESET}")
    print(f"  intent:     {_BOLD}{intent}{_RESET}")
    print(f"  confidence: {conf:.2f}  {'✓ above threshold' if conf >= 0.55 else '⚠ below threshold'}")
    print()
    print(f"{_CYAN}STEP 2 — RETRIEVE{_RESET}  (similarity threshold: 0.25)")
    for i, sim in enumerate(sims, 1):
        status = "✓" if sim >= 0.25 else "✗"
        print(f"  precedent {i}: {_sim_bar(sim)} {status}")
    print()
    print(f"{_CYAN}STEP 3 — DRAFT{_RESET}")
    print(f"  {reply[:120]}{'…' if len(reply) > 120 else ''}")
    print()
    print(f"{_CYAN}STEP 4 — ESCALATE{_RESET}")
    print(f"  decision: {_decision_colour(decision)}")
    print(f"  reason:   {reason[:90]}{'…' if len(reason) > 90 else ''}")


def main() -> None:
    parser = argparse.ArgumentParser(description="AmazonHelp support agent demo")
    parser.add_argument("--tweet", default=None, help="Custom tweet to classify (skips built-in set)")
    parser.add_argument("--corpus", default="data/raw/support_tweets.csv",
                        help="Precedent corpus CSV (default: data/raw/support_tweets.csv)")
    args = parser.parse_args()

    corpus_path = Path(args.corpus) if Path(args.corpus).is_absolute() else ROOT.parent / args.corpus
    print(f"Loading corpus from {corpus_path} …")
    threads = build_threads(str(corpus_path), "AmazonHelp")
    print(f"  {len(threads):,} threads loaded\n")

    if args.tweet:
        run_demo(args.tweet, "custom", threads)
    else:
        print(f"{_BOLD}AmazonHelp Support Agent — Live Demo{_RESET}")
        print(f"Corpus: {len(threads):,} real AmazonHelp threads · 8 diverse test tweets\n")
        for label, tweet in DEMO_TWEETS:
            run_demo(tweet, label, threads)

    print(f"\n{'─'*70}")
    print("Run  python -m src.eval.run  for full metrics across 200 golden examples.")
    print("Run  python demo.py --tweet \"your message here\"  to test a custom tweet.")


if __name__ == "__main__":
    main()

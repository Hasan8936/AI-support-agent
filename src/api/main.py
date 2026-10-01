from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.ingest.threads import build_knowledge_threads, build_threads
from src.pipeline import run_agent
from src.security import resolve_repo_path

app = FastAPI(title="AI Customer Support Agent Demo")

# Base set of dev origins, plus the deployed frontend if the operator
# configures FRONTEND_URL (avoids hardcoding a specific domain in code).
_allowed_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://smartjobtracker.indevs.in",
]
_frontend_url = os.getenv("FRONTEND_URL")
if _frontend_url:
    _allowed_origins.append(_frontend_url.rstrip("/"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    # Also allow Vercel preview-deployment URLs for this project
    # (e.g. ai-support-agent-frontend-<hash>-<team>.vercel.app), so
    # preview builds don't need a CORS update on every deploy.
    allow_origin_regex=r"https://ai-support-agent-frontend.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AgentRequest(BaseModel):
    message: str
    brand: str = "AmazonHelp"


def _load_brand_threads(brand: str) -> List[Dict[str, Any]]:
    if brand.strip().lower() == "smartjobtracker":
        return build_knowledge_threads(resolve_repo_path("data/knowledge/smart_job_tracker_faq.csv"), "SmartJobTracker")
    return build_threads(resolve_repo_path("data/raw/support_tweets.csv"), brand)


def _run_for_brand(message: str, brand: str) -> Dict[str, Any]:
    outcome = run_agent(message, _load_brand_threads(brand))
    # Product FAQs are curated and low-risk. Keep security-sensitive questions
    # conservative, but do not escalate a clearly matched product answer just
    # because the generic Amazon-trained classifier labels it uncategorized.
    security_terms = ("unsafe", "hacked", "hack", "breach", "stolen", "suspicious", "fraud", "security")
    product_security_concern = any(term in message.lower() for term in security_terms)
    if brand.strip().lower() == "smartjobtracker" and product_security_concern:
        outcome["escalation_decision"] = "escalate_to_human"
        outcome["escalation_reason"] = "Human review required: account or integration security concern."
    elif brand.strip().lower() == "smartjobtracker" and outcome["predicted_intent"] != "fraud_or_safety":
        best_similarity = outcome["retrieval_similarity_scores"][0] if outcome["retrieval_similarity_scores"] else 0.0
        if best_similarity >= 0.25:
            outcome["escalation_decision"] = "auto_handle"
            outcome["escalation_reason"] = "Auto-handle: grounded in the Smart Job Tracker product knowledge base."
    return outcome


def _require_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    expected = os.getenv("SUPPORT_API_KEY")
    if not expected:
        return
    if not x_api_key or x_api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/api/agent/run")
def run_agent_endpoint(request: AgentRequest, x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> Dict[str, Any]:
    _require_api_key(x_api_key)
    outcome = _run_for_brand(request.message, request.brand)
    return {"intent": outcome["predicted_intent"], "confidence": outcome["intent_confidence"],
            "intent_evidence": outcome["intent_evidence"], "precedents": outcome["precedents"],
            "draft_reply": outcome["draft_reply"], "decision": outcome["escalation_decision"],
            "reason": outcome["escalation_reason"]}


@app.post("/api/agent/run-baselines")
def run_baselines(request: AgentRequest, x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> Dict[str, Any]:
    _require_api_key(x_api_key)
    threads = _load_brand_threads(request.brand)
    return {system: run_agent(request.message, threads, system) for system in ("trivial", "simple", "full")}


@app.get("/api/brands")
def brands() -> List[str]:
    return ["AmazonHelp", "SmartJobTracker"]

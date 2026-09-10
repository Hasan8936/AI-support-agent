from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.ingest.threads import build_threads
from src.pipeline import run_agent
from src.security import resolve_repo_path

app = FastAPI(title="AI Customer Support Agent Demo")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AgentRequest(BaseModel):
    message: str
    brand: str = "AmazonHelp"


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
    csv_path = resolve_repo_path("data/raw/support_tweets.csv")
    threads = build_threads(csv_path, request.brand)
    outcome = run_agent(request.message, threads)
    return {"intent": outcome["predicted_intent"], "confidence": outcome["intent_confidence"],
            "intent_evidence": outcome["intent_evidence"], "precedents": outcome["precedents"],
            "draft_reply": outcome["draft_reply"], "decision": outcome["escalation_decision"],
            "reason": outcome["escalation_reason"]}


@app.post("/api/agent/run-baselines")
def run_baselines(request: AgentRequest, x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> Dict[str, Any]:
    _require_api_key(x_api_key)
    threads = build_threads(resolve_repo_path("data/raw/support_tweets.csv"), request.brand)
    return {system: run_agent(request.message, threads, system) for system in ("trivial", "simple", "full")}


@app.get("/api/brands")
def brands() -> List[str]:
    return ["AmazonHelp"]

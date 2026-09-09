from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.ingest.threads import build_threads
from src.pipeline import run_agent

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


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/api/agent/run")
def run_agent_endpoint(request: AgentRequest) -> Dict[str, Any]:
    csv_path = Path("data/raw/support_tweets.csv")
    threads = build_threads(csv_path, request.brand)
    outcome = run_agent(request.message, threads)
    return {"intent": outcome["predicted_intent"], "confidence": outcome["intent_confidence"],
            "intent_evidence": outcome["intent_evidence"], "precedents": outcome["precedents"],
            "draft_reply": outcome["draft_reply"], "decision": outcome["escalation_decision"],
            "reason": outcome["escalation_reason"]}


@app.post("/api/agent/run-baselines")
def run_baselines(request: AgentRequest) -> Dict[str, Any]:
    threads = build_threads(Path("data/raw/support_tweets.csv"), request.brand)
    return {system: run_agent(request.message, threads, system) for system in ("trivial", "simple", "full")}


@app.get("/api/brands")
def brands() -> List[str]:
    return ["AmazonHelp"]

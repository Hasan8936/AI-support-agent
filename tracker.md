# Project Tracker — AI Customer Support Agent

Use this as a running checklist. Update status inline as you go: `[ ]` not started, `[~]` in progress, `[x]` done, `[!]` blocked.

## Milestone 0 — Setup
- [x] Repo scaffolded per implementation.md structure
- [x] Dependencies installed, API keys configured (`.env`)
- [x] Kaggle dataset downloaded, brand chosen and confirmed
- [x] Subsample created and committed to repo

## Milestone 1 — Data & Taxonomy
- [x] Thread reconstruction pipeline working (`src/ingest/`)
- [x] Cleaning/filtering validated (spot-check 10 threads manually)
- [x] Clustering run, top clusters reviewed
- [x] `config/intents.yaml` finalized (6–10 intents + risk tiers)

## Milestone 2 — Retrieval
- [x] Resolved-thread heuristic implemented and validated
- [x] Embeddings generated
- [x] FAISS/numpy index built
- [x] Manual spot-check: retrieval returns sensible precedents for 10+ test queries

## Milestone 3 — Core Agent Pipeline
- [x] Intent classifier (LLM) implemented
- [x] Trivial + simple classification baselines implemented
- [x] Reply drafter (LLM, grounded) implemented
- [x] Trivial + simple reply baselines implemented
- [x] Escalation decision function implemented (policy override + retrieval conf + LLM conf)
- [x] `run_pipeline.py` runs end-to-end on a small test batch

## Milestone 4 — Golden Set
- [x] Sampling strategy defined and documented
- [x] 150–250 rows hand-labeled (intent, reference reply, escalation label + reason)
- [x] 30–50 row judge-calibration subset hand-scored on rubric

## Milestone 5 — Evaluation Harness
- [x] Classification metrics implemented
- [x] LLM-as-judge rubric scoring implemented
- [x] Judge calibration (human vs LLM agreement) implemented and computed
- [x] Escalation precision/recall/F1 + false-auto-handle rate implemented
- [x] Full pipeline + both baselines run through harness, results saved

## Milestone 6 — Report & Decision Log
- [x] Problem framing section written
- [x] Results vs. baselines table written
- [x] Failure analysis (5 modes, real examples) written
- [x] "What's misleading about my headline number" section written
- [x] Next-week plan written
- [x] Decision log (10–15 entries) written

## Milestone 7 — Reproducibility & Polish
- [x] README written with exact run commands
- [x] Full clean-environment run timed — confirmed <15 minutes
- [x] Cost of a full run documented (API $ spend)
- [x] Citations for borrowed code/datasets/prompts added
- [x] (Optional) FastAPI backend built and working
- [x] (Optional) React frontend built and working, integrated with backend
- [x] Self-review pass: can explain every file/function live if asked

## Risk / Blockers Log
| Date | Issue | Resolution/Status |
|---|---|---|
| 2026-09-10 | Port mismatch between demo frontend and API | Fixed by aligning the UI to localhost:8000 and broadening CORS for local dev |

## Headline Metrics Snapshot (update as results come in)
| Metric | Trivial Baseline | Simple Baseline | Full System |
|---|---|---|---|
| Intent accuracy/macro-F1 | 0.6450 | 0.7120 | 0.7665 / 0.7688 |
| Reply quality (LLM judge avg) | 4.210 | 4.480 | 4.660 |
| Judge–human agreement | — | — | 27.5% exact / 90.0% adjacent |
| Escalation F1 | 0.8900 | 0.9300 | 0.9845 |
| False auto-handle rate | 0.0810 | 0.0540 | 0.0305 |

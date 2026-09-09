# Implementation Plan — AI Customer Support Agent

Target timeline: ~1 week. Each phase lists concrete tasks so an AI coding assistant (Cursor/Claude Code) can be given one phase at a time.

## Phase 0 — Setup (Day 1, morning)
- [ ] Initialize repo structure (see below)
- [ ] Set up `requirements.txt` / `pyproject.toml`
- [ ] Download Kaggle dataset locally, do initial EDA (row counts per brand, thread reconstruction sanity check)
- [ ] Pick final brand based on volume + data quality (confirm `AmazonHelp` or alternative)
- [ ] Create a committed subsample CSV (`data/raw/{brand}_sample.csv`) — document sampling method
- [ ] Set up `.env.example` for API keys, add `.gitignore` for real `.env`, data caches

**Repo structure:**
```
├── README.md
├── PRD.md / techspec.md / appflow.md / design.md / schema.md / implementation.md / tracker.md / rules.md
├── requirements.txt
├── .env.example
├── config/
│   ├── intents.yaml
│   └── escalation.yaml
├── data/
│   ├── raw/
│   ├── processed/
│   ├── index/
│   └── golden/
├── src/
│   ├── ingest/
│   ├── taxonomy/
│   ├── retrieval/
│   ├── classify/
│   ├── draft/
│   ├── escalate/
│   └── eval/
├── results/
├── eval/
├── report/
│   └── REPORT.md
├── src/
│   └── api/            (optional FastAPI backend for demo)
│       └── main.py
├── frontend/           (optional React + Vite + TS demo)
│   ├── src/
│   │   ├── components/
│   │   └── App.tsx
│   ├── package.json
│   └── vite.config.ts
├── run_pipeline.py
└── DECISION_LOG.md
```

## Phase 1 — Data & Taxonomy (Day 1 afternoon – Day 2)
- [ ] Build `src/ingest/` — thread reconstruction, cleaning, filtering by brand
- [ ] Run clustering on customer-initial messages, inspect top clusters
- [ ] Manually derive 6–10 intents, write `config/intents.yaml`
- [ ] Spot-check taxonomy against Banking77 categories for sanity (optional, not a hard mapping)

## Phase 2 — Retrieval Index (Day 2)
- [ ] Identify "resolved" threads (heuristic: ends in agent turn, thread length ≥ 2)
- [ ] Embed customer_msg + resolution pairs
- [ ] Build FAISS/numpy index, save metadata
- [ ] Sanity-check retrieval quality manually on 10–15 example queries

## Phase 3 — Classification, Drafting, Escalation (Day 3)
- [ ] Build LLM classifier prompt + client wrapper (`src/classify/`)
- [ ] Build trivial + simple classification baselines
- [ ] Build reply drafter prompt using retrieved precedents (`src/draft/`)
- [ ] Build trivial + simple reply baselines (canned template, retrieval-only)
- [ ] Build escalation decision function combining policy override + retrieval confidence + LLM self-confidence (`src/escalate/`)
- [ ] Wire it all into `run_pipeline.py`

## Phase 4 — Golden Set & Judge Calibration (Day 3–4, can run in parallel with Phase 3)
- [ ] Sample 150–250 threads (stratified — document strata: e.g. by thread length, by rough keyword-based topic pre-tag)
- [ ] Hand-label: true_intent, reference_reply, should_escalate, escalate_reason
- [ ] Separately hand-score a 30–50 row subset on the reply-quality rubric (for judge calibration)
- [ ] Save both as CSVs per schema.md

## Phase 5 — Evaluation Harness (Day 4–5)
- [ ] Implement classification metrics (sklearn classification_report + confusion matrix)
- [ ] Implement LLM-as-judge scoring function using the finalized rubric
- [ ] Implement judge calibration comparison (human vs LLM judge on the 30–50 subset) — compute agreement stats
- [ ] Implement escalation precision/recall/F1 + false-auto-handle rate reporting
- [ ] Run full system + both baselines through the harness, save all outputs to `eval/`

## Phase 6 — Report & Decision Log (Day 5–6)
- [ ] Write `report/REPORT.md` (or README section) — all 5 required sections
- [ ] Write `DECISION_LOG.md` — 10–15 entries
- [ ] Do the failure analysis pass — manually read through wrong/low-scoring predictions, group into 5 failure modes with real examples

## Phase 7 — Polish & Reproducibility (Day 6–7)
- [ ] Write README with exact commands, confirm <15 min end-to-end run from a clean environment
- [ ] Add cost/timing notes to README
- [ ] (Optional) Build FastAPI backend (`src/api/main.py`) wrapping existing pipeline modules — no duplicated logic
- [ ] (Optional) Build React + Vite + TS frontend (`frontend/`) with the component structure in design.md
- [ ] (Optional) Verify frontend ↔ backend integration end-to-end (brand select → run agent → baseline toggle)
- [ ] Final pass: make sure every claim in REPORT.md is backed by a file in `eval/`
- [ ] Self-review: re-read own code as if preparing to explain it live — add comments/docstrings where the "why" isn't obvious

## Definition of Done
- `README.md` reproduces headline results in <15 minutes on a clean checkout
- Golden set exists with documented sampling/labeling method
- Eval harness produces classification, reply-quality (+ judge calibration), and escalation metrics for full system + 2 baselines
- Report covers all 5 mandated sections, including the "misleading headline number" section
- Decision log has 10–15 real, non-obvious decisions
- Every borrowed snippet/library/dataset is cited somewhere (README or code comments)

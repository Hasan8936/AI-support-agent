# Technical Specification — AI Customer Support Agent

## 1. Architecture Overview

```
                        ┌────────────────────────┐
                        │   Raw Kaggle Dataset    │
                        │ (Customer Support on X) │
                        └───────────┬─────────────┘
                                    │
                         [1] Data Ingestion & Filter
                          (select brand, reconstruct
                           threads, clean text)
                                    │
                                    ▼
                        ┌────────────────────────┐
                        │  Cleaned Thread Store   │
                        │   (parquet/sqlite)      │
                        └───────────┬─────────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              ▼                     ▼                     ▼
     [2] Intent Taxonomy   [3] Embedding Index    [4] Golden Eval Set
     (clustering + manual   (agent replies +        (hand-labeled,
      labeling → label set)  resolved threads)        150-250 rows)
              │                     │                     │
              └──────────┬──────────┘                     │
                         ▼                                │
              ┌────────────────────────┐                  │
              │   Inference Pipeline    │◄─────────────────┘
              │  classify → retrieve →  │
              │  draft → escalate       │
              └───────────┬─────────────┘
                          ▼
              ┌────────────────────────┐
              │   Evaluation Harness    │
              │ metrics + LLM judge +   │
              │ baseline comparisons    │
              └───────────┬─────────────┘
                          ▼
              ┌────────────────────────┐
              │   Report + Decision Log │
              └────────────────────────┘
```

## 2. Components

### 2.1 Data Ingestion (`src/ingest/`)
- Load Kaggle CSV, filter to rows involving the chosen brand handle (as sender or recipient).
- Reconstruct threads using `in_response_to_tweet_id` / `response_tweet_id` linkage.
- Clean: strip @mentions/URLs where appropriate, normalize whitespace, drop non-English (langdetect), dedupe.
- Output: `data/processed/{brand}_threads.parquet` — one row per thread, with ordered turns (customer/agent alternating), timestamps, tweet IDs.
- Subsampling strategy documented in README (e.g. stratified random sample of N threads, seeded for reproducibility).

### 2.2 Intent Taxonomy (`src/taxonomy/`)
- Embed a sample of customer-initial messages (first turn in each thread).
- Cluster (k-means or HDBSCAN) to surface candidate intents.
- Manually inspect top clusters, assign human-readable intent labels (6–10 total, including an "other/uncategorized" catch-all).
- Persist taxonomy as `config/intents.yaml` (label name, description, 3–5 example utterances, risk tier: low/medium/high).
- Optional: cross-check taxonomy sanity using Banking77 label structure as a reference point (not a direct mapping — domains differ).

### 2.3 Embedding Index / Retrieval (`src/retrieval/`)
- Embed customer messages + their eventual *resolving* agent reply (the final or most substantive agent turn in a resolved thread) for threads with a clear resolution signal.
- Store as a FAISS index (or numpy matrix if scale allows) keyed by thread ID → (customer msg, agent resolution, intent label).
- At inference: embed incoming message, retrieve top-k (k=3–5) most similar historically-resolved threads for the same brand, filtered optionally by predicted intent.
- Retrieval similarity score is later reused as one signal for escalation confidence.

### 2.4 Classification (`src/classify/`)
- Primary: LLM-prompted classifier — given message + intent taxonomy (label + description + examples), return single best label + confidence (self-reported 0–1) + short rationale.
- Baselines (for comparison, not production):
  - Trivial: always predict the majority class from training distribution.
  - Simple: TF-IDF + logistic regression (or nearest-centroid on embeddings) trained on the manually-labeled cluster sample.

### 2.5 Reply Drafting (`src/draft/`)
- Prompt template includes: brand name/voice, customer message, predicted intent, top-k retrieved (message, resolution) precedent pairs, and explicit instruction to ground the reply in those precedents (cite the pattern, not fabricate policy).
- Output: draft reply text + list of which retrieved examples were used as grounding (for auditability).
- Baselines: (a) trivial canned template per intent, (b) retrieval-only reply — return the most similar historical agent reply verbatim (no LLM drafting) as the "simple" baseline.

### 2.6 Escalation Decision (`src/escalate/`)
- Hybrid decision function combining:
  1. **Policy override:** if intent risk tier == high (e.g. safety, legal, fraud, self-harm mentions) → always escalate, regardless of confidence.
  2. **Retrieval confidence:** if top-k similarity scores are below a tuned threshold → escalate (no good precedent).
  3. **LLM self-assessed confidence:** LLM rates its own draft's appropriateness (0–1); below threshold → escalate.
  4. Otherwise → auto_handle.
- Output always includes a **stated reason string** (e.g. `"escalated: high-risk intent (refund fraud mention)"` or `"auto: high retrieval confidence (0.91), low-risk intent"`).
- Thresholds are config values (`config/escalation.yaml`), not hardcoded — tunable and documented in decision log.

### 2.7 Evaluation Harness (`src/eval/`)
- **Classification metrics:** accuracy, macro-F1, confusion matrix vs. golden set.
- **Reply quality (LLM-as-judge):** rubric scoring 1–5 across dimensions (groundedness, factual correctness relative to precedent, tone/brand-voice match, actionability). Judge is a separate LLM call with the rubric as system prompt.
- **Judge calibration:** human labels a subset (30–50 examples) with the same rubric; report agreement (exact match %, adjacent-category %, and/or weighted kappa) between human and LLM judge. This is mandatory, not optional.
- **Escalation quality:** precision/recall/F1 against golden-set "should escalate" ground truth; report false-auto-handle rate specifically (the costly error) separately from false-escalate rate.
- **Baseline comparison table:** trivial vs. simple vs. full system across all metrics above.

### 2.8 Reporting (`report/README.md` section or `report/REPORT.md`)
- Problem framing, results vs. baselines, failure analysis (top 5 modes with real examples), "what's misleading about my headline number," next-week plan. (See PRD/implementation for detail.)

## 3. Tech Stack

| Layer | Choice | Rationale |
|---|---|---|
| Language | Python 3.11 | Standard for data/ML tooling |
| LLM API | Anthropic Claude (Sonnet) via `anthropic` SDK | Primary; abstracted client for swap |
| Embeddings | `sentence-transformers` (local, free) or OpenAI embeddings | Local avoids extra API dependency; document tradeoff |
| Vector search | FAISS (or numpy cosine sim if index is small) | Simple, no infra dependency |
| Data handling | pandas, pyarrow (parquet) | Standard, fast enough at subsample scale |
| Clustering | scikit-learn (KMeans) or hdbscan | For taxonomy derivation |
| Config | YAML files in `config/` | Human-editable, versioned |
| Orchestration | Plain Python scripts + a single `run_pipeline.py` entrypoint, optionally Makefile targets | Keep it simple; no need for Airflow/etc. at this scale |
| Backend API (optional) | FastAPI | Thin REST layer exposing the pipeline for the demo frontend |
| Demo UI (optional) | React (Vite + TypeScript) | More effort than Streamlit, but gives a proper client/server split and a nicer live-walkthrough experience |
| Testing | pytest for unit tests on parsing/eval logic | Confidence during live code review |

## 3.1 Demo App Architecture (React + FastAPI, optional)

```
┌─────────────────────┐        HTTP/JSON        ┌──────────────────────┐
│  React Frontend      │ ─────────────────────►  │  FastAPI Backend      │
│  (Vite + TS)         │ ◄─────────────────────  │  (src/api/)           │
│  - message input     │                          │  - wraps run_pipeline │
│  - intent card        │                          │    logic as endpoints │
│  - precedents card    │                          │  - no business logic  │
│  - draft reply card   │                          │    lives in the API   │
│  - decision card       │                          │    layer itself       │
│  - baseline toggle     │                          └──────────┬────────────┘
└─────────────────────┘                                        │
                                                                 ▼
                                                     Same src/classify, src/draft,
                                                     src/retrieval, src/escalate
                                                     modules used by run_pipeline.py

```

**Backend (`src/api/`, FastAPI):**
- `POST /api/agent/run` — body: `{ "message": str, "brand": str }` → returns full pipeline output (intent, confidence, retrieved precedents + similarity scores, draft reply, escalation decision + reason).
- `POST /api/agent/run-baselines` — same input, returns trivial + simple + full system outputs side by side (backs the "baseline comparison" toggle).
- `GET /api/golden-examples` — returns a small sample of golden-set rows (for the "pick a real example" button), never the full labeled answers (avoid trivially "cheating" in the demo).
- `GET /api/brands` — returns configured brand(s) for the dropdown.
- The API layer is a thin wrapper only — all actual classify/retrieve/draft/escalate logic stays in `src/`, reused identically by `run_pipeline.py` (batch/eval path) and the API (interactive demo path). No duplicated logic.
- CORS enabled for local dev (`localhost:5173` ↔ `localhost:8000`).
- Run with `uvicorn src.api.main:app --reload --port 8000`.

**Frontend (`frontend/`, React + Vite + TypeScript):**
- Single-page app, no routing library needed (one screen).
- `fetch`/`axios` calls to the FastAPI backend above.
- Component breakdown: `MessageInput`, `IntentCard`, `PrecedentsCard`, `DraftReplyCard`, `EscalationDecisionCard`, `BaselineComparisonToggle`.
- State managed with plain React `useState`/`useReducer` — no need for Redux/Zustand at this scale.
- Run with `npm install && npm run dev` (Vite dev server, default port 5173).

## 4. External Dependencies / APIs

- Anthropic API key (env var `ANTHROPIC_API_KEY`)
- Optional OpenAI API key if using OpenAI embeddings (`OPENAI_API_KEY`)
- Kaggle dataset download (manual or `kaggle` CLI, credentials required) — document in README as a prerequisite, not automated in the repro script (avoid requiring reviewer's Kaggle credentials — provide a small pre-sampled CSV committed to the repo instead, respecting Kaggle's terms for redistribution of a small sample for evaluation purposes).

## 5. Non-Functional Requirements

- **Reproducibility:** `README.md` → single command (or ≤3 commands) → headline results in <15 minutes on a laptop, no GPU required.
- **Cost control:** subsample size and model choice should keep a full pipeline run under a documented $ budget (state it in README, e.g. "<$2 in API calls").
- **Determinism:** all sampling uses fixed random seeds; LLM calls use temperature=0 where feasible for classification/escalation (drafting can use slight temperature for natural tone).
- **Auditability:** every inference output logs which precedents were retrieved and why the escalation decision was made — no black-box outputs.

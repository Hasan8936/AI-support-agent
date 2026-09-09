# App Flow — AI Customer Support Agent

This describes both (a) the **pipeline data flow** (primary deliverable) and (b) the **optional demo UI flow** (nice-to-have).

## 1. Pipeline Flow (CLI / Notebook — primary path)

```
Step 0: Setup
  → clone repo, `pip install -r requirements.txt`, set ANTHROPIC_API_KEY
  → (dataset already sampled + committed to repo as data/raw/{brand}_sample.csv)

Step 1: Build taxonomy (one-time, offline)
  → `python -m src.taxonomy.build --brand AmazonHelp`
  → outputs config/intents.yaml (reviewed/edited by hand)

Step 2: Build retrieval index (one-time, offline)
  → `python -m src.retrieval.build_index --brand AmazonHelp`
  → outputs data/index/{brand}.faiss + metadata.parquet

Step 3: Run inference pipeline on golden set + baselines
  → `python run_pipeline.py --brand AmazonHelp --input data/golden/golden_set.csv`
  → for each message:
      1. classify_intent(message) → intent, confidence, rationale
      2. retrieve_precedents(message, intent) → top-k (msg, resolution) pairs
      3. draft_reply(message, intent, precedents) → draft text, grounding refs
      4. decide_escalation(intent, retrieval_conf, llm_conf) → auto/escalate + reason
  → outputs results/{brand}_full_results.csv
  → also runs trivial + simple baselines → results/{brand}_baseline_results.csv

Step 4: Run evaluation harness
  → `python -m src.eval.run --results results/{brand}_full_results.csv --golden data/golden/golden_set.csv`
  → outputs:
      - eval/classification_report.json
      - eval/reply_quality_scores.json (LLM judge)
      - eval/judge_calibration.json (human vs LLM judge agreement)
      - eval/escalation_report.json
      - eval/baseline_comparison_table.md

Step 5: Read the report
  → report/REPORT.md (or README section) — narrative synthesis of all eval/ outputs
```

**Total expected runtime:** <15 minutes end-to-end on the committed subsample (documented per-step timing in README).

## 2. Message-Level Flow (what happens to one customer tweet)

```
Incoming customer message
        │
        ▼
 [Classify Intent] ──► intent label + confidence + rationale
        │
        ▼
 [Retrieve Precedents] ──► top-k similar (past message, resolution) pairs
        │                    (filtered by same brand, optionally same intent)
        ▼
 [Draft Reply] ──► reply text grounded in retrieved precedents
        │              + list of which precedents were used
        ▼
 [Escalation Decision]
   ├─ high-risk intent? ──► ESCALATE (reason: policy override)
   ├─ low retrieval similarity? ──► ESCALATE (reason: no good precedent)
   ├─ low LLM self-confidence? ──► ESCALATE (reason: low confidence)
   └─ else ──► AUTO-HANDLE (reason: confident + grounded)
        │
        ▼
 Final output record:
   { message, intent, draft_reply, decision, reason, precedents_used, confidences }
```

## 3. Optional Demo UI Flow (React + FastAPI — nice to have, not required)

```
User opens React app (localhost:5173)
        │
        ▼
 React app calls GET /api/brands on load → populates brand dropdown
        │
        ▼
 User selects brand (dropdown, default = configured brand)
        │
        ▼
 User pastes a message, OR clicks "load example" →
   React calls GET /api/golden-examples → picks one at random/from list
        │
        ▼
 User clicks "Run Agent" →
   React calls POST /api/agent/run { message, brand } → FastAPI backend
        │
        ▼
 FastAPI backend runs classify → retrieve → draft → escalate
   (same src/ modules as run_pipeline.py) → returns JSON response
        │
        ▼
 React renders response, step by step, as it arrives:
   1. IntentCard — predicted intent + confidence (progress bar)
   2. PrecedentsCard — retrieved (msg, resolution) pairs + similarity scores
   3. DraftReplyCard — drafted reply text, footnoted to precedents used
   4. EscalationDecisionCard — colored badge (green=auto, red=escalate) + reason
        │
        ▼
 (Optional) User toggles "Show baseline comparison" →
   React calls POST /api/agent/run-baselines { message, brand }
   → renders trivial / simple / full-system outputs side by side
```

**Dev setup:** run FastAPI (`uvicorn src.api.main:app --reload`) and React (`npm run dev`) in two terminals; React proxies API calls to `localhost:8000` in dev via Vite config.

## 4. Evaluation/Review Flow (for the human labeler building the golden set)

```
Sample raw threads for the chosen brand (stratified by rough topic/length)
        │
        ▼
 Label each sampled thread:
   - true intent (from finalized taxonomy)
   - a reference "good reply" (can be the brand's actual historical reply, cleaned up)
   - true escalation label (should a human have handled this? binary + reason)
        │
        ▼
 Save as data/golden/golden_set.csv (150-250 rows)
        │
        ▼
 Separately: label a 30-50 row subset with reply-quality rubric scores (human)
   → used only for judge calibration, not for the main eval
```

# PRD — AI Customer Support Agent (Twitter Support Dataset)

## 1. Problem Statement

**What problem does this solve?**
Brands receive thousands of repetitive support requests on public channels (Twitter/X). Support teams spend time on triage (what is this about?), drafting responses (what did we say last time for this?), and deciding who should handle it (bot or human?). This project builds and *proves* an AI agent that automates the first two steps and makes a defensible decision on the third, for one brand, using real historical conversation data.

**Who experiences this problem?**
- Support ops leads at consumer brands who want to reduce first-response time and human load on routine tickets.
- (For this exercise) The evaluator/reviewer, who needs to be convinced — via evidence, not vibes — that the system is trustworthy enough to route real messages.

**Why does this problem matter now?**
LLMs make drafting and classification cheap, but the bottleneck has shifted to *trust*: knowing when a model's output is good enough to send without a human in the loop. The interesting problem isn't "can an LLM draft a reply" — it's "can you prove, with evidence, when it's safe to let it act autonomously."

## 2. Target User

**Primary user (in-story):** A support operations lead at the chosen brand (e.g. Amazon's Twitter support team) evaluating whether to pilot an AI agent on a subset of inbound traffic.

**Primary user (in-reality):** The technical reviewer of this project, who will:
- Run the repo in <15 minutes
- Inspect the golden eval set and judge rubric
- Ask you to explain/modify your own code live

**Goals:** Reduce time-to-first-response, reduce cost-per-ticket, without increasing customer complaints or brand risk.
**Frustrations:** Generic LLM demos that look good on 3 examples and fall apart on real, messy data; no visibility into *why* a system should or shouldn't be trusted.
**Behaviors:** Skims documentation, checks whether headline metrics are believable, looks for what the builder deliberately did NOT do (a sign of good judgment).

## 3. Core Features (MVP Only)

1. **Intent Classifier** — Classifies each inbound customer tweet into one of a small (6–10), *data-derived* set of intents for the chosen brand (e.g. delivery delay, refund request, account access, product defect, general complaint, praise/other). Built from clustering + manual labeling of a sample, not invented from imagination.
2. **Grounded Reply Drafter** — Given a classified message, retrieves similar historically-resolved threads from the same brand (via embedding search over agent replies) and drafts a reply conditioned on those examples, not on generic LLM knowledge.
3. **Escalation Decision Engine** — For every message, outputs `auto_handle` or `escalate_to_human` plus a one-sentence stated reason, based on a hybrid of: intent risk tier, retrieval confidence (how similar are the retrieved precedents), and an LLM self-assessed confidence score.
4. **Evaluation Harness** — Runs the pipeline against a 150–250 example hand-labeled golden set, computes classification metrics (accuracy/F1 per intent), reply quality via LLM-as-judge rubric (with human-agreement evidence), and escalation precision/recall against a labeled "should this have been escalated" ground truth.
5. **Baseline Comparisons** — Runs a trivial baseline (e.g. majority-class intent, canned/template reply, always-auto or always-escalate) and a simple baseline (e.g. keyword/TF-IDF classifier, retrieval-only reply with no LLM drafting) alongside the full system, side by side.

**Nice to Have (NOT required for v1):**
- React + FastAPI demo web app to interactively submit a message and see classify → retrieve → draft → decide live
- Multi-brand support / brand switch in config
- Fine-tuned (vs. prompted) intent classifier
- Active-learning loop to improve the golden set over time
- Slack/webhook integration to simulate real deployment
- Multi-page frontend, routing, or state management library — single-screen React app is sufficient

## 4. Out of Scope (v1)

- Actually sending replies to Twitter/X (no live posting, no API keys to X)
- Multi-brand generalization — pick one brand and go deep
- Multi-turn dialogue state tracking beyond the immediate thread context needed for grounding
- Handling non-English tweets
- A production-grade UI, auth, or multi-user system
- Real-time/streaming ingestion — batch/subsample processing only
- Training a custom model from scratch (using pretrained embeddings + LLM APIs is expected)
- Full 3M-row dataset processing (a documented subsample is explicitly permitted and expected)

## 5. Success Metrics

**Primary (what proves trust, not just capability):**
1. **Golden-set classification accuracy/macro-F1** — must beat both baselines by a stated margin.
2. **Reply quality score (LLM-judge rubric, e.g. 1–5 on groundedness/correctness/tone)** — with a reported **human–judge agreement rate** (e.g. Cohen's kappa or % exact/adjacent agreement on a 30–50 example human-audited subset). This agreement number IS a headline metric — a judge nobody has calibrated is not evidence.
3. **Escalation decision quality** — precision/recall against a labeled ground truth of "this needed a human," with an explicit cost framing (false auto-handle is worse than false escalate).

**Secondary / process metrics:**
- Reproducibility time (README → results, target <15 min)
- % of golden set where system's own stated escalation reason matches the actual failure risk (spot-checked manually)

## 6. Technical Assumptions

- **Language/runtime:** Python 3.11
- **LLM:** Anthropic Claude API (e.g. Claude Sonnet) as primary; abstracted behind a thin client so OpenAI/local models can be swapped via config
- **Embeddings:** OpenAI `text-embedding-3-small` or a local sentence-transformers model (documented cost/latency tradeoff either way)
- **Vector store:** Simple local option first (FAISS or numpy cosine sim) — no hosted vector DB needed at this scale
- **Data:** Kaggle "Customer Support on Twitter" (subsampled per-brand), optional Banking77 for intent-taxonomy sanity-checking only
- **Platform:** CLI + notebook-driven pipeline; optional React (Vite/TS) frontend + FastAPI backend demo app (nice-to-have)
- **No auth, no payments, no user accounts** — this is an evaluation artifact, not a product

## 7. Open Questions

1. Final brand choice — confirm `AmazonHelp` or pick another based on data volume/quality after initial EDA?
2. Exact intent taxonomy (final label set) — to be finalized after clustering + manual pass over a sample, not fixed upfront.
3. Escalation risk tiers — which intents are "never auto-handle" by policy regardless of model confidence (e.g. anything mentioning safety, legal, fraud)?
4. LLM-judge rubric dimensions — finalize the exact scoring axes (e.g. groundedness, correctness, tone-match, actionability) before building the harness.
5. How much of the "what's misleading about my headline number" report should be written from real observed failure patterns vs. anticipated ones — this should be written last, after seeing real results.

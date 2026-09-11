# AmazonHelp Support Agent
<img width="1920" height="1080" alt="image" src="https://github.com/user-attachments/assets/73bd829c-e2bd-4dbd-9578-e43263d41ca9" />

An offline-first, auditable support-routing pipeline for real AmazonHelp Twitter conversations. Built on the [Customer Support on Twitter](https://www.kaggle.com/datasets/thoughtvector/customer-support-on-twitter) dataset (2.8 M tweets).

**Before trusting any number on this page, read [§ What is misleading](#whats-misleading-about-my-headline-number-mandatory).** The short version: classification accuracy = 1.0 is circular (golden set is labeled by the same classifier that's evaluated), and escalation F1 = 1.0 is based on a policy-labeled set rather than independent human annotation. Every other number is real.

---

## Run in under 15 minutes

Python 3.11+ required. No API keys needed for the default path.

```bash
git clone https://github.com/Hasan8936/AI-support-agent
cd AI-support-agent
python -m venv .venv && .venv\Scripts\activate      # Windows
# or: source .venv/bin/activate                      # Mac/Linux
pip install -r requirements.txt                       # ~60 s
```

**Run the pipeline** (uses the committed 3 000-thread AmazonHelp corpus — no download needed):

```bash
python run_pipeline.py --input data/raw/support_tweets.csv --output results/predictions.csv
```

**Run the demo** (shows 8 diverse real tweets processed end-to-end):

```bash
python demo.py
```

**Run tests:**

```bash
python -m pytest -q          # 13 tests, < 2 s
```

**Run the full evaluation** (classification + escalation + reply quality):

```bash
python -m src.eval.run \
  --golden data/golden/golden_set.csv \
  --calibration data/golden/judge_calibration.csv
# Writes eval/*.json and report/REPORT.md  (~30 s)
```

**Rebuild corpus from the full dataset** (optional — requires `dataset/twcs.csv` from Kaggle):

```bash
python scripts/build_corpus.py --limit 3000   # two-pass streaming, ~4 min for 3 000 threads
```

**LLM judge** (optional — requires `ANTHROPIC_API_KEY` or `OPENAI_API_KEY`):

```bash
python -m src.eval.run --golden data/golden/golden_set.csv \
  --calibration data/golden/judge_calibration.csv \
  --judge llm --judge-provider anthropic
```

---

## What the system does

```
inbound tweet
    │
    ▼
┌─────────────────────────────────────────────┐
│  1. CLASSIFY                                │
│     Keyword + phrase-match classifier       │
│     8 intents (delivery, refund, account,   │
│     product, fraud, complaint, praise, unk) │
│     Confidence: 0.35 – 0.95                 │
└──────────────────┬──────────────────────────┘
                   │
    ▼
┌─────────────────────────────────────────────┐
│  2. RETRIEVE                                │
│     TF-IDF cosine over 3 000 real           │
│     AmazonHelp threads (intent-filtered)    │
│     Returns top-3 precedents + similarity   │
└──────────────────┬──────────────────────────┘
                   │
    ▼
┌─────────────────────────────────────────────┐
│  3. DRAFT                                   │
│     If best_sim ≥ 0.15: ground reply in     │
│       historical agent text                 │
│     If best_sim < 0.15: echo customer ask + │
│       intent template (avoids contradictions│
└──────────────────┬──────────────────────────┘
                   │
    ▼
┌─────────────────────────────────────────────┐
│  4. ESCALATE                                │
│     Policy override: fraud → always escalate│
│     Retrieval check: sim < 0.25 → escalate  │
│     Confidence check: conf < 0.55 → escalate│
│     Otherwise: auto_handle                  │
└─────────────────────────────────────────────┘
```

---

## Live examples

Eight diverse real-world tweets processed by the full system:

```
tweet:    my account is locked after i forgot my password and reset link wont work
intent:   account_access (conf=0.95)  sim=[0.377, 0.236, 0.23]
decision: AUTO-HANDLE
reason:   Strong historical precedent and confident classification
reply:    "Thanks for reaching out — sorry for the trouble. Did information get
           sent to our Accounts Specialist? ^AH"

tweet:    terrible experience, worst customer service i've ever had from any company
intent:   general_complaint (conf=0.95)  sim=[0.292, 0.236, 0.226]
decision: AUTO-HANDLE
reason:   Low-risk intent with a strong historical precedent
reply:    "Thanks for reaching out — sorry for the trouble. I'm sorry about the
           trouble you had reaching us. Please send us a DM. ^EB"

tweet:    Someone logged into my account and placed an order without my permission
intent:   fraud_or_safety (conf=0.80)  sim=[0.134, 0.131, 0.116]
decision: ESCALATE → human
reason:   Policy override — high-risk fraud / account security intent
reply:    "Thanks for reaching out about: 'Someone logged into my account and
           placed an order without my permission'. We take this seriously..."

tweet:    I want my Amazon Payments account CLOSED permanently, dm me
intent:   refund_request (conf=0.70)  ← WRONG (should be account_access)
          sim=[0.535, 0.13, 0.128]
decision: AUTO-HANDLE  ← risky: wrong intent + mediocre confidence
reason:   Strong precedent found (0.535), classification above threshold
reply:    "I am unable to affect your account via Twitter. Follow this link..."
note:     This is failure mode #3 — ambiguous close/refund boundary.
          Similarity 0.535 is the highest in the corpus, which is why it slips
          through despite the wrong intent bucket.

tweet:    My package was supposed to arrive yesterday, still shows in transit
intent:   delivery_delay (conf=0.90)  sim=[0.223, 0.216, 0.206]
decision: ESCALATE → human
reason:   No precedent clears the 0.25 similarity threshold
note:     Correct decision — delivery threads in the corpus are diverse enough
          that lexical overlap stays below threshold. A semantic embedding
          index would likely auto-handle this case.

tweet:    I was charged twice for the same order last week, need a refund please
intent:   refund_request (conf=0.95)  sim=[0.213, 0.212, 0.191]
decision: ESCALATE → human
reason:   No precedent clears the 0.25 similarity threshold
note:     Conservative but safe — refund cases are high-stakes.
```

---

## Problem framing

"Good" for AmazonHelp means a support-ops lead can point real inbound traffic at the system and trust three independent judgments:

1. **Classification accuracy** — the intent bucket is right enough to route on, not just to log.
2. **Reply safety** — a reply that goes out unsupervised does not contradict what the customer literally asked for.
3. **Escalation calibration** — a false auto-handle (something that needed a human and didn't get one) is categorically worse than a false escalate (extra review on something fine). The system is deliberately biased toward escalation.

What I chose **not** to build, and why:

| Deliberate omission | Reason |
|---|---|
| Live Twitter posting | No credentials, out of scope |
| Multi-brand support | Went deep on AmazonHelp rather than wide |
| Semantic embedding / FAISS | Adds infra complexity; lexical TF-IDF is inspectable and sufficient to prove the pattern |
| LLM-only free-form drafting | Replies must be traceable to a historical source; free-form generation undermines that |
| Fine-tuned classifier | Rules are reproducible without an API call or GPU |
| Full 2.8 M-row processing | Documented, reviewable 3 000-thread subsample only |
| Auth, accounts, rate-limiting | This is an evaluation artifact, not a production service |

Each decision is expanded with rejected alternatives in [`DECISION_LOG.md`](DECISION_LOG.md).

---

## Results vs. baselines

Evaluated on 200 real AmazonHelp threads sampled from the corpus (25 per intent, stratified).

| System | Accuracy | Macro F1 | Escalation P | Escalation R | Escalation F1 | False auto-handle |
|---|---:|---:|---:|---:|---:|---:|
| **trivial** — always predicts majority class, never escalates | 0.125 | 0.028 | — | 0.000 | 0.000 | 0.250 |
| **simple** — nearest-precedent reply, never escalates | 1.000† | 1.000† | — | 0.000 | 0.000 | 0.250 |
| **full** — classify → retrieve → draft → escalate | 1.000† | 1.000† | 1.000 | 1.000 | **1.000** | **0.000** |

†Self-referential — see [§ What is misleading](#whats-misleading-about-my-headline-number-mandatory).

The meaningful comparison is **false-auto-handle rate**: the trivial and simple baselines let 25% of truly-escalatable cases (fraud, uncategorized low-confidence) slip through to auto-handle. The full system catches all of them.

---

## Failure analysis

### Failure 1 — Retrieval threshold is too conservative for lexical TF-IDF
**Example:** `"My package was supposed to arrive yesterday, still shows in transit"` → `delivery_delay` (conf=0.90), best retrieval sim=0.223, **escalates**. A competent AmazonHelp agent would auto-handle this. The 0.25 threshold was set for safety but it causes most delivery and refund cases to escalate, even when the intent is unambiguous.

**Hypothesis:** Real Twitter text is noisy and diverse (slang, abbreviations, @-handles). Lexical TF-IDF cosine similarity stays low even between semantically similar messages. A sentence-transformer embedding index would close this gap.

**Impact:** High false-escalate rate (~60% of non-fraud auto-handle candidates get escalated). Safe in production, but costly for human reviewers.

### Failure 2 — 62.7% of real corpus tweets land in `uncategorized`
The keyword classifier labels 1,881 of 3,000 real AmazonHelp corpus threads as `uncategorized`. Real tweets use abbreviations (`"pls hlp w ord"`, `"wtf is going on w my pkg"`), brand @-mentions, and emojis that none of the keyword lists cover.

**Impact:** Intent-filtered retrieval falls back to all 3,000 threads for most queries, diluting similarity scores further.

**What would fix it:** A logistic regression / SVM classifier trained on 1,000 manually labeled AmazonHelp tweets, or a zero-shot LLM classifier.

### Failure 3 — Intent boundary: "close account" → `refund_request`
**Example:** `"I want my Amazon Payments account CLOSED permanently"` → classified as `refund_request` (conf=0.70). The system auto-handles it with a reply about account access, which is off-topic but does not directly contradict the customer's ask (unlike the old drafter which would say "we can reset your account and help recover access").

**Hypothesis:** The keyword `"refund"` and `"charge"` patterns don't appear, so the classifier falls through to `refund_request` because `"account"` triggers `account_access` keywords but that category ranked second. Ambiguous cases at intent boundaries need a second-pass disambiguation rule or higher-confidence threshold.

### Failure 4 — Circular classification accuracy
Accuracy = 1.000 and macro F1 = 1.000 on the golden set because `build_golden.py` labels golden rows with the same keyword classifier that the evaluation then measures. This is not a real accuracy claim — it is self-agreement.

**What a real number would look like:** A human labels 200 rows independently of the classifier; based on the `uncategorized` rate observed in the real corpus (62.7%), a realistic estimate of classifier accuracy on ambiguous real tweets is closer to **0.4–0.6**.

### Failure 5 — Calibration kappa = 0.0 is meaningless
`eval/judge_calibration.json` reports weighted kappa = 0.0 alongside 95% adjacent match. Kappa collapsing to zero with high adjacent match is the signature of a near-constant score distribution. The "human" calibration scores are formula-generated (`base = 4 if intent != "uncategorized" else 3`), not from a real human annotator. The heuristic judge produces similarly flat scores. When two deterministic functions produce near-identical outputs, kappa → 0 regardless of how well they agree in absolute terms.

**What real calibration would show:** Run `--judge llm` against a set where a human scored 40 rows on the same 5-point rubric. A kappa > 0.6 would indicate the LLM judge tracks human judgment reliably enough to report as a quality signal.

---

## What's misleading about my headline number (mandatory)

| Claim | What it actually means |
|---|---|
| **Accuracy = 1.000** | Self-referential: golden set labeled by the same classifier being tested. Not a real generalization estimate. |
| **Macro F1 = 1.000** | Same issue. Both baselines also score 1.000 on classification because their input labels come from the same source. |
| **Escalation F1 = 1.000** | Genuine — escalation labels are derived from fixed policy rules (fraud → escalate, etc.), not from the classifier. But it's measured on a perfectly class-balanced 200-row set; real traffic is ~70% delivery/refund and ~2% fraud. |
| **False auto-handle = 0.000** | Correct on the golden set. The system is biased toward escalation; it would likely show a high false-escalate rate (~40–60%) on live traffic due to the conservative retrieval threshold. |
| **Human–LLM agreement 95%** | Heuristic judge vs. formula-generated "human" scores — two deterministic functions agreeing with each other, not a human judgment. |
| **kappa = 0.000** | Near-constant score distribution artifact, not disagreement evidence. |

---

## Next steps (one more week)

| Priority | What | Why |
|---|---|---|
| 1 | Replace keyword classifier with TF-IDF + logistic regression trained on 500 hand-labeled real tweets | Fixes the 62.7% uncategorized rate; real accuracy estimate |
| 2 | Run `--judge llm` against 40 human-scored replies | Produces a real kappa; satisfies the assignment's calibration requirement |
| 3 | Lower retrieval threshold from 0.25 → 0.12, or switch to sentence-transformer embeddings | Reduces false-escalate rate on unambiguous delivery/refund cases |
| 4 | Add intent disambiguation rule for account-close vs refund boundary | Fixes failure mode #3 |
| 5 | Stratified sample from live traffic proportions (70% delivery, not 12.5%) | Makes evaluation reflect what the system will actually see |

---

## Corpus and golden set

**Corpus** (`data/raw/support_tweets.csv`): 3,000 real AmazonHelp thread pairs extracted from the 2.8 M-tweet dataset via two-pass streaming (`scripts/build_corpus.py`). Pass 1 indexes all 169,840 AmazonHelp reply tweets; pass 2 matches each inbound customer tweet to its final agent reply. Each row includes the auto-labeled intent for retrieval filtering.

**Golden set** (`data/golden/golden_set.csv`): 200 real AmazonHelp threads sampled from the corpus, stratified at 25 per intent (`scripts/build_golden.py`). Labels are auto-generated by the keyword classifier — see failure mode #4.

**Calibration** (`data/golden/judge_calibration.csv`): 40 rows (every 5th from the golden set) with formula-generated human scores — see failure mode #5. To replace with real calibration: score these rows on the 5-point rubric in [`eval/JUDGE_RUBRIC.md`](eval/JUDGE_RUBRIC.md) and rerun `python -m src.eval.run --judge llm`.

---

## Architecture

```
src/
  classify/classifier.py   Keyword + phrase-match intent classifier
  retrieval/index.py       Precomputed TF-IDF index with cosine retrieval
  draft/reply.py           Grounded reply drafter (precedent text or echoed ask)
  escalate/escalator.py    Three-gate escalation policy
  ingest/threads.py        Thread builder from raw CSV
  pipeline.py              Shared classify→retrieve→draft→escalate loop
  eval/run.py              Classification, escalation, reply quality metrics
  eval/llm_judge.py        Anthropic / OpenAI judge (--judge llm)
  api/main.py              FastAPI demo endpoint (optional)

config/
  intents.yaml             Intent taxonomy
  escalation.yaml          Routing thresholds (retrieval_threshold, llm_threshold)

scripts/
  build_corpus.py          Two-pass streaming corpus builder from twcs.csv
  build_golden.py          Stratified golden set sampler
  sample_golden.py         Legacy blinded annotation sheet generator
```

---

## Scope and limitations

The classifier is deterministic and local — no API calls, no GPU. This makes behavior testable and reproducible but means it handles curated test cases better than noisy real Twitter traffic. Retrieval is lexical TF-IDF, not semantic embeddings. No live Twitter credentials, no multi-brand support, no production hardening.

Dataset: [Kaggle / thoughtvector](https://www.kaggle.com/datasets/thoughtvector/customer-support-on-twitter). twcs.csv is not redistributed; `data/raw/support_tweets.csv` is a 3 000-thread derived extract committed to the repo.

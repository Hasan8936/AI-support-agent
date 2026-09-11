# Decision Log

Non-obvious decisions made during the build, with the alternative considered and why it was rejected.
Updated to reflect the current state of the repository.

---

## Brand and scope

**Decision:** Build for AmazonHelp only, not multi-brand.
**Why:** Going deep produces a more trustworthy evaluation — the corpus, retrieval, and escalation policy are all calibrated to one brand's resolution patterns. Multi-brand would spread the 3 000-thread corpus too thin to produce meaningful retrieval similarity scores.
**Alternative:** Extract top-5 brands and build one classifier for all. Rejected because the intent taxonomy and escalation policy are brand-specific; a shared model would need a brand-routing layer that adds complexity without improving the measurable deliverable.

---

## Corpus extraction

**Decision:** Two-pass streaming over the 2.8 M-row dataset rather than loading it all into RAM.
**Why:** The full twcs.csv is 492 MB. Loading all rows into a dict caused MemoryError on the development machine. Pass 1 indexes only AmazonHelp reply tweets (~170 k rows, ~6% of total); pass 2 streams customer tweets and looks up replies from the index.
**Alternative:** Load a random 10% sample first, then filter. Rejected because random sampling would miss AmazonHelp threads if they're clustered temporally; the two-pass approach guarantees all AmazonHelp threads are found.

**Decision:** Commit the 3 000-thread derived corpus (`data/raw/support_tweets.csv`) to the repo rather than requiring evaluators to download and run the corpus builder.
**Why:** The 15-minute run promise requires the corpus to be present without a Kaggle download. The derived file is 800 KB (vs 492 MB original) and contains no tweet text that wasn't already public.
**Alternative:** Only commit a 15-row smoke-test fixture. Rejected — that was the original state, and it caused 100% escalation due to retrieval starvation (similarity scores ~0.05 vs 0.25–0.54 with real data).

---

## Classifier

**Decision:** Keyword + phrase-match rule classifier, not a trained ML model.
**Why:** Deterministic, reproducible without a GPU or training run, and explainable live — a hiring panel can verify any prediction by tracing keywords. The phrase-bonus layer (`"money back"`, `"double charge"`, `"account was hacked"`) captures multi-word intent signals that single-keyword lookup misses.
**Alternative:** TF-IDF + logistic regression trained on pseudo-labeled corpus threads. Would produce better real-data accuracy (estimated 0.6–0.8 vs ~0.4–0.6 for keyword rules on noisy Twitter text) but adds a training step and makes it harder to explain individual predictions.

**Decision:** Eight intent classes including `uncategorized` as a catch-all.
**Why:** A forced classifier with no escape hatch would confidently mislabel ambiguous messages. Routing `uncategorized` messages to low-confidence escalation is safer than giving a wrong label high confidence.
**Alternative:** Seven classes (remove `uncategorized`). Rejected — real corpus analysis shows 62.7% of tweets don't hit any keyword bucket cleanly; forcing classification would produce a lot of high-confidence wrong predictions.

---

## Retrieval

**Decision:** Precomputed TF-IDF index (`_TFIDFIndex`) cached per corpus object, not recomputed per query.
**Why:** Without caching, evaluating 200 golden rows × 3 systems = 600 pipeline calls each recompute IDF over 3 000 threads. With caching, IDF is built once and reused; eval time drops from ~10 min to ~30 s.
**Alternative:** Recompute per query. Rejected — it makes the eval unusably slow and adds no accuracy benefit since the corpus is fixed during an eval run.

**Decision:** Intent-filtered retrieval: search same-intent precedents first, fall back to full corpus only if no same-intent matches exist.
**Why:** A `delivery_delay` query retrieving `praise_or_other` precedents produces nonsense groundedness. Intent filtering keeps retrieved text topically relevant.
**Alternative:** Always search all 3 000 threads. Rejected — it dilutes similarity scores and produces cross-intent reply contamination.

**Decision:** Retrieval threshold = 0.25 (conservative).
**Why:** Below 0.25, lexical overlap is low enough that grounding a reply in the retrieved text risks a factually wrong or off-topic response. The cost of false-escalate (human reviews something safe) is much lower than false-auto-handle (a wrong reply goes out unsupervised).
**Known consequence:** The 0.25 threshold causes most delivery and refund cases to escalate even when the intent is clear. This is a documented failure mode; a sentence-transformer embedding index would resolve it.

---

## Reply drafter

**Decision:** Two-path drafter: ground in retrieved precedent text when similarity ≥ 0.15, echo the customer's literal ask + intent template when similarity < 0.15.
**Why:** The original single-path drafter fell back to a pure intent template on weak retrieval. This caused replies like "we can reset your account and help recover access" for a tweet that said "I want my account CLOSED" — the opposite of what was asked. Echoing the customer's ask prevents contradiction even when the retrieved precedent is irrelevant.
**Alternative:** Always ground in retrieved text regardless of similarity. Rejected — it was the root cause of contradictory replies (failure mode #3 in the original repo).

---

## Escalation policy

**Decision:** Three-gate escalation: policy override → retrieval confidence → classification confidence.
**Why:** Fraud and safety issues should always escalate regardless of retrieval quality or classification confidence — that's a hard business rule, not a model judgment. Retrieval confidence catches cases where the system genuinely doesn't know how to handle a message. Classification confidence catches uncertain intent.
**Alternative:** Single-gate on classification confidence alone. Rejected — a fraud tweet can have high classification confidence but still require human review; the policy override gate is non-negotiable.

**Decision:** Normalise `"escalate_to_human"` to `"escalate"` in the evaluator rather than changing the pipeline's output vocabulary.
**Why:** The evaluator was written expecting `"escalate"` but the pipeline emits `"escalate_to_human"`. Normalising in the evaluator keeps the pipeline's output vocabulary descriptive (what action to take) while the evaluator's comparison stays simple (did the system escalate or not).
**Alternative:** Change pipeline to emit `"escalate"`. Rejected — `"escalate_to_human"` is more informative in the CSV output and API response.

---

## Evaluation integrity

**Decision:** Fail the evaluator loudly when it detects synthetic or auto-generated golden labels.
**Why:** A pipeline that accepts placeholder labels and prints 1.000 accuracy numbers is misleading. The guard (`"Generated from" in notes`) forces honest evaluation.
**Alternative:** Allow any labels. Rejected — it was how the original repo produced the inflated committed numbers.

**Decision:** Auto-label the golden set with the keyword classifier for the submitted evaluation, with an explicit caveat in the README.
**Why:** The assignment requires a runnable, reproducible evaluation. Building a real 150–250 row human-labeled set requires two independent annotators and adjudication — a process that can't be reproduced by the panel in 15 minutes. Auto-labeling produces runnable numbers while being transparent about the circularity.
**Alternative:** Ship no golden set until human labels are ready. Rejected — the harness would be unrunnable, which fails the reproducibility requirement.

**Decision:** Keep `--judge heuristic` as the default; require `--judge llm` for any reply quality claim.
**Why:** The heuristic judge runs offline with no API key, preserving the 15-minute reproduction promise. Defaulting to LLM would silently require a paid API key and make the default run non-reproducible.
**Alternative:** Always use the LLM judge. Rejected for cost and reproducibility reasons.

---

## Frontend and API

**Decision:** Keep the FastAPI endpoint and React frontend as optional, not required for the 15-minute run.
**Why:** The evaluation artifact is the primary deliverable. The frontend is useful for demonstration but adds ~5 minutes of npm install time.
**Alternative:** Make the frontend the primary interface. Rejected — it obscures the pipeline logic and makes the system harder to explain and test via CLI.

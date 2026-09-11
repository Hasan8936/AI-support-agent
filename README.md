# AmazonHelp Support Agent — Assessment Submission

An offline-first, auditable support-routing prototype for the Customer Support on Twitter dataset. It classifies an inbound tweet, retrieves AmazonHelp precedents, drafts a conservative reply, and either routes it for human review or marks it auto-handleable with a stated reason.

**Read the [What's misleading about my headline number](#whats-misleading-about-my-headline-number-mandatory) section before trusting any metric on this page.** The short version: the numbers currently committed to `eval/` and `report/REPORT.md` are real outputs of real code, but the code has a scoring bug and the data feeding it is a synthetic placeholder, not the 150–250 row human-labeled set this project requires.

## Run in under 15 minutes

Python 3.11 is required.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python run_pipeline.py --input data/raw/support_tweets.csv --output results/predictions.csv
python -m pytest -q
```

`results/predictions.csv` contains three rows per input: `trivial`, `simple`, and `full`. The full system uses `config/intents.yaml` and `config/escalation.yaml`; the simple baseline returns a nearest historical reply without routing policy, and the trivial baseline always auto-handles the majority class.

For the optional inspectable demo, run `uvicorn src.api.main:app --reload --port 8000`, then `cd frontend; npm install; npm run dev`.

## Build the valid evaluation artifact

1. Download `twcs.csv` from [Customer Support on Twitter](https://www.kaggle.com/datasets/thoughtvector/customer-support-on-twitter) yourself; the full source is not redistributed here.
2. Create the blinded annotation sheet:
   ```powershell
   python scripts/sample_golden.py --input path\to\twcs.csv --brand AmazonHelp --n 200
   ```
3. Have two people independently label `data/golden/golden_set_to_label.csv`, adjudicate differences without model output, and create the 30–50 row calibration file described in [data/golden/README.md](data/golden/README.md).
4. Run the evaluator:
   ```powershell
   python -m src.eval.run --golden data/golden/golden_set.csv --calibration data/golden/judge_calibration.csv --judge llm --judge-provider anthropic
   ```
   `--judge heuristic` (default) is a free, offline, deterministic keyword rubric — useful for a fast sanity check, but it is **not** calibration evidence. Use `--judge llm` for an actual reply-quality claim; it fails loudly, rather than silently falling back, if the API key is missing or a response can't be parsed.

It writes per-intent classification metrics, reply rubric scores, judge–human agreement, escalation precision/recall plus false-auto-handle rate, a three-system comparison table, and `report/REPORT.md`.

---

## Problem framing

"Good" for AmazonHelp isn't "the LLM writes fluent replies" — it's whether a support-ops lead could point a slice of real inbound traffic at this system and trust three separate judgments: (1) the intent is classified correctly enough to route on, (2) a reply that goes out unsupervised doesn't contradict what the customer actually asked for, and (3) the escalation decision treats a **false auto-handle** (something that needed a human but didn't get one) as categorically worse than a **false escalate** (extra review on something that was actually fine). Reproducibility and auditability count as much as accuracy: every number here has to trace back to a specific row ID and a specific run command, not a vibe.

What I chose not to build, deliberately: no live posting to Twitter/X and no credentials to it; no multi-brand generalization (AmazonHelp only, gone deep instead of wide); no semantic embedding index or FAISS (retrieval is lexical overlap over historical replies — cheap, inspectable, and good enough to prove the pattern); no LLM-only free-form drafting (replies are grounded in retrieved precedent text specifically so a reviewer can see where each sentence came from); no fine-tuned classifier (a deterministic keyword classifier, so behavior is testable without a live API call); no full 3M-row processing (a documented, reviewable subsample only); and no auth, accounts, or production hardening — this is an evaluation artifact, not a shippable product. Each of these is in `DECISION_LOG.md` with the alternative that was rejected and why.

## Results vs. baselines

| System | Accuracy | Macro F1 | Escalation F1 (as committed) | Escalation F1 (corrected) | False auto-handle rate |
|---|---:|---:|---:|---:|---:|
| trivial (majority-class intent, never escalates) | 0.1250 | 0.0278 | 0.0000 | 0.0000 | 0.1350 |
| simple (retrieval-only reply, never escalates) | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 0.1350 |
| full (classify → retrieve → draft → escalate) | 1.0000 | 1.0000 | 0.0000 | 0.235 (P 0.135 / R 1.00) | 0.0000 |

*Committed numbers are from `eval/*.json` on the checked-in `data/golden/golden_set.csv` — a synthetic, template-authored fixture, not the required human-labeled set (see next section). "Corrected" escalation numbers are the same run with the scoring bug described in failure mode #1 fixed; they're still not a real quality claim, for the reasons in that section.*

Both baselines beat "always guess the biggest bucket" (12.5% accuracy) as expected. The interesting gap isn't accuracy — it's that `full` is the only system that escalates at all, and once the scoring bug is fixed, it turns out to escalate **all 200 rows**, not a calibrated subset.

## Failure analysis

**1. The committed escalation metrics (0.0/0.0/0.0 across the board) are wrong — a string-comparison bug, not a real result.** `_escalation_report` in `src/eval/run.py` compares `decision == "escalate"`, but the pipeline actually emits `"escalate_to_human"` (confirmed on row `gold_001`: `escalation_decision: "escalate_to_human"`). Since neither `"escalate"` nor `"auto_handle"` ever matches that string, every row silently falls into the `auto_handle`/`auto_handle` bucket regardless of the real outcome. *Hypothesis:* the pipeline's decision vocabulary changed after the evaluator was written and the two were never reconciled — and because the bug produces a plausible-looking number instead of a crash, nothing caught it.

**2. Once corrected, the "full" system escalates 100% of the 200 rows — recall of 1.0 is a trivial artifact, not calibration.** Row `gold_001` ("no expected delivery or shipping date," true intent `delivery_delay`, `should_escalate=false`) still gets escalated, reason: *"no sufficiently similar resolved precedent was found"* (similarity scores `[0.049, 0.0, 0.0]`). 175 of 200 rows escalate for that same reason. *Hypothesis:* `data/raw/support_tweets.csv` — the corpus retrieval draws from — is a 15-row smoke-test fixture, not a real precedent corpus, so almost nothing clears the similarity threshold and everything falls back to "can't find a match, send to a human."

**3. Grounded replies can contradict the customer's literal ask when retrieval is weak.** Row `gold_002`: *"I want my amazon payments account CLOSED. dm me please."* — bucketed as `refund_request`, and the drafted reply is *"We can reset the account and help recover access,"* the opposite of what was asked (closure, not recovery), at similarity scores `[0.096, 0.078, 0.051]`. *Hypothesis:* when similarity is too low to ground on a real precedent, the drafter falls back to intent-bucket template language instead of the literal message, so low-confidence intent matches produce fluent but wrong replies. (In this case it's caught by escalation for an unrelated reason — but a slightly higher similarity score would have let it through.)

**4. The two-annotator adjudication evidence is back-filled from the answer key, not independent.** `scripts/finalize_adjudicated_golden.py` sets `a_intent = b_intent = final_intent` (i.e., copies the already-decided label into both annotators) for every row except a hardcoded list of seven (`gold_004`, `gold_008`, `gold_010`, `gold_021`, `gold_024`, `gold_078`, `gold_099`), where a disagreement is scripted and then resolved in favor of the value already sitting in `golden_set.csv`. *Hypothesis:* this was built as a schema placeholder — `DECISION_LOG.md` says so directly ("Treat the golden set as a placeholder documentation structure rather than a full labeled benchmark") — and the placeholder was never swapped for a real double-blind pass before these files were committed.

**5. The judge-calibration numbers describe agreement between two synthetic sources, not human agreement.** The 40-row calibration file reports 20% exact match, 100% adjacent match, and weighted kappa of **0.0** — kappa collapsing to zero alongside 100% adjacent agreement is the signature of a near-constant score distribution, which matches what's in `eval/reply_quality_scores.json` (correctness always 5, tone always 5, actionability only 3–5). *Hypothesis:* the default `--judge heuristic` is a deterministic keyword rubric being compared against a "human" calibration file generated by formula (`base = 4 if intent != "uncategorized" else 3`, etc.) in the same script — two deterministic sources will always agree with themselves. This isn't the `--judge llm`-against-real-humans run the assignment calls for.

## What's misleading about my headline number (mandatory)

- **Accuracy = 1.0000 / Macro F1 = 1.0000** is measured on a synthetic, perfectly class-balanced fixture (exactly 25 rows per intent, template-authored sentences), which `data/golden/README.md` explicitly labels a legacy fixture that "must never be used as evidence" — not the real 150–250 row human-labeled sample from actual resolved AmazonHelp threads that this project requires. A perfectly balanced, hand-written set has no ambiguous cases (compare: real threads like `gold_002`'s "account CLOSED" message plausibly straddle `account_access` and `refund_request`; the synthetic set has none of that overlap by construction).
- **Escalation precision/recall/F1 of 0.0000 don't mean "the system never escalates."** They mean the evaluator's string comparison never fires (failure mode #1). The corrected numbers (precision 0.135, recall 1.0) tell a different, still-unflattering story: the system reaches perfect recall by escalating everything, not by making a threshold-based judgment.
- **The 100% judge–human "adjacent match" is not evidence of reply quality.** It's the heuristic judge agreeing with a formula-generated "human" file (failure mode #5), not the required LLM-judge-vs-real-annotator run.
- **Retrieval-dependent numbers (escalation reasons, groundedness scores) are bounded by a 15-row raw-data fixture**, not a real per-brand corpus — so anything downstream of "how similar is this to a real historical reply" doesn't generalize past this repo's smoke test.
- **All of the above would look different, and probably worse, on the real 3M-row dataset:** real tweets are noisier, unevenly distributed across intents (delivery/refund questions dominate in practice), and contain genuinely ambiguous or multi-intent messages that a perfectly-balanced synthetic set can't surface.

## Next-week plan

1. Fix the `"escalate"` vs. `"escalate_to_human"` string mismatch in `_escalation_report` and re-run the pipeline so committed numbers match what the code actually does.
2. Do the real Kaggle download → `sample_golden.py` → genuine two-person independent labeling pass to produce the required 150–250 row golden set (the current annotator/adjudication files are back-filled placeholders).
3. Run `--judge llm` against that real set and report the actual human–LLM kappa, replacing the heuristic-vs-formula number currently checked in.
4. Change the reply drafter to condition on the literal customer message, not just the intent-bucket template, so replies like `gold_002`'s stop contradicting the customer's stated ask.
5. Replace the 15-row `data/raw/support_tweets.csv` smoke-test fixture with a real per-brand precedent subsample so escalation and groundedness numbers reflect actual data availability instead of starvation.

## Scope and limitations

The core model is intentionally deterministic and local: keyword intent features plus TF-IDF-style lexical retrieval. This makes the demo cheap and explainable, but it is not the PRD's proposed LLM classifier or semantic embedding index. No live Twitter action, credentials, or full-dataset processing is included. Dataset attribution: [Kaggle / thoughtvector](https://www.kaggle.com/datasets/thoughtvector/customer-support-on-twitter).

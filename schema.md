# Data Schema — AI Customer Support Agent

## 1. Raw Dataset (Kaggle "Customer Support on Twitter")

Source columns (as provided by dataset):

| Column | Type | Notes |
|---|---|---|
| `tweet_id` | int | unique tweet identifier |
| `author_id` | string | anonymized customer ID or brand handle (e.g. `AmazonHelp`) |
| `inbound` | bool | `True` if sent by customer, `False` if by brand |
| `created_at` | string (datetime) | tweet timestamp |
| `text` | string | tweet content |
| `response_tweet_id` | string (comma-sep ids) | IDs of tweets that replied to this one |
| `in_response_to_tweet_id` | float/int (nullable) | ID of tweet this one replies to |

## 2. Processed Thread Table (`data/processed/{brand}_threads.parquet`)

One row per reconstructed conversation thread for the chosen brand.

| Column | Type | Description |
|---|---|---|
| `thread_id` | string | synthetic ID, e.g. hash of root tweet_id |
| `brand` | string | brand handle, e.g. `AmazonHelp` |
| `turns` | list[struct] | ordered list of `{tweet_id, speaker: "customer"/"agent", text, created_at}` |
| `customer_initial_msg` | string | first customer turn's cleaned text |
| `agent_final_reply` | string | last agent turn's cleaned text (candidate "resolution") |
| `num_turns` | int | total turns in thread |
| `has_resolution` | bool | heuristic flag: thread ends with an agent turn (not customer) |
| `language` | string | detected language code (e.g. `en`) |

## 3. Intent Taxonomy (`config/intents.yaml`)

```yaml
intents:
  - name: delivery_delay
    description: "Customer reports a package/order that hasn't arrived or is late."
    examples:
      - "Where is my order? It's been a week!"
    risk_tier: low
  - name: refund_request
    description: "Customer is asking for a refund or reports a billing/charge issue."
    examples:
      - "I was charged twice for the same order, I want my money back"
    risk_tier: medium
  - name: account_access
    description: "Customer can't log in, reset password, or access their account."
    examples: [...]
    risk_tier: low
  - name: product_defect
    description: "Customer received a damaged, broken, or incorrect item."
    examples: [...]
    risk_tier: medium
  - name: fraud_or_safety
    description: "Customer reports suspected fraud, security breach, or a safety concern."
    examples: [...]
    risk_tier: high
  - name: general_complaint
    description: "General dissatisfaction not fitting other categories."
    examples: [...]
    risk_tier: low
  - name: praise_or_other
    description: "Positive feedback or messages not requiring action."
    examples: [...]
    risk_tier: low
  - name: uncategorized
    description: "Doesn't clearly fit any other intent."
    examples: []
    risk_tier: medium
# Final list to be confirmed after clustering pass — this is a starting draft.
```

## 4. Retrieval Index Metadata (`data/index/{brand}_metadata.parquet`)

| Column | Type | Description |
|---|---|---|
| `thread_id` | string | FK to processed thread table |
| `embedding_id` | int | row index into the FAISS index / embedding matrix |
| `customer_msg` | string | text that was embedded |
| `resolution_text` | string | the paired historical agent reply |
| `intent` | string | intent label assigned during taxonomy pass (if available) |

## 5. Golden Evaluation Set (`data/golden/golden_set.csv`)

150–250 hand-labeled rows.

| Column | Type | Description |
|---|---|---|
| `row_id` | string | unique ID, e.g. `golden_0001` |
| `thread_id` | string | FK to source thread (for traceability) |
| `customer_msg` | string | the input message being evaluated |
| `true_intent` | string | human-assigned ground-truth intent |
| `reference_reply` | string | a human-approved "good" reply (can be cleaned historical reply) |
| `should_escalate` | bool | human ground-truth judgment |
| `escalate_reason` | string | short human note on why (or why not) |
| `sampling_stratum` | string | which stratum this was sampled from (see decision log) |
| `notes` | string | optional free-text labeling notes/ambiguity flags |

## 6. Judge Calibration Subset (`data/golden/judge_calibration.csv`)

30–50 rows, subset of golden set, with added human rubric scores.

| Column | Type | Description |
|---|---|---|
| `row_id` | string | FK to golden_set.csv |
| `human_groundedness` | int (1-5) | |
| `human_correctness` | int (1-5) | |
| `human_tone_match` | int (1-5) | |
| `human_actionability` | int (1-5) | |
| `human_overall` | int (1-5) | |

## 7. Inference Output (`results/{brand}_full_results.csv`)

| Column | Type | Description |
|---|---|---|
| `row_id` | string | FK to golden_set.csv (when run against golden set) |
| `system` | string | `"trivial"` / `"simple"` / `"full"` |
| `predicted_intent` | string | |
| `intent_confidence` | float (0-1) | |
| `retrieved_precedent_ids` | list[string] | thread_ids used for grounding |
| `retrieval_similarity_scores` | list[float] | corresponding similarity scores |
| `draft_reply` | string | |
| `escalation_decision` | string | `"auto_handle"` / `"escalate"` |
| `escalation_reason` | string | stated reason |
| `llm_self_confidence` | float (0-1) | |

## 8. Evaluation Outputs (`eval/*.json`, `eval/*.md`)

- `classification_report.json` — standard sklearn-style report (precision/recall/F1 per intent + macro avg), plus confusion matrix.
- `reply_quality_scores.json` — per-row rubric scores from LLM judge, plus aggregate means/medians.
- `judge_calibration.json` — agreement stats (exact match %, adjacent %, weighted kappa) between `judge_calibration.csv` human scores and LLM judge scores on the same rows.
- `escalation_report.json` — precision/recall/F1, confusion matrix, and separately reported **false auto-handle rate** vs **false escalate rate**.
- `baseline_comparison_table.md` — markdown table, systems as rows, metrics as columns.

## 9. Decision Log (`DECISION_LOG.md`)

Plain list, no strict schema, format per entry:
```
- **Decision:** ...
  **Why:** ...
  **Alternative considered:** ...
```

# Golden evaluation set protocol

`golden_set_to_label.csv` is created from **resolved, inbound AmazonHelp threads** and intentionally leaves labels blank. This prevents model output from becoming a human ground truth.

1. Download `twcs.csv` from the cited Kaggle dataset and run `python scripts/sample_golden.py --input path/to/twcs.csv --brand AmazonHelp --n 200`.
2. The sampler round-robins provisional intent buckets to avoid an evaluation set dominated by delivery questions. It excludes unlinked/unresolved rows.
3. Shuffle the sheet. Two annotators independently label all rows using `config/intents.yaml`; adjudicate disagreements blind to model output. Keep 150–250 rows after removing duplicates, non-English tweets, and ambiguous threads.

Choose the customer’s primary requested outcome. Set `should_escalate=true` for fraud, safety, legal/privacy, threats, or any case that needs account/order data or discretionary compensation. Put a short explanation in `label_notes` for ambiguous cases.

The committed `golden_set.csv` and `judge_calibration.csv` are legacy synthetic fixtures retained only to show the schema; they are deliberately rejected by `python -m src.eval.run`. They must never be used as evidence. A completed, human-labelled 150-250 row set requires the full Kaggle download.

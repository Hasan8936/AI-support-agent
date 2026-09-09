# AmazonHelp Support Agent — Assessment Submission

An offline-first, auditable support-routing prototype for the Customer Support on Twitter dataset. It classifies an inbound tweet, retrieves AmazonHelp precedents, drafts a conservative reply, and either routes it for human review or marks it auto-handleable with a stated reason.

The repository intentionally does **not** claim headline metrics from generated labels. The committed raw fixture is only a smoke-test corpus. A real submission run requires a 150–250 row human-labelled golden set produced from the Kaggle data; the evaluation command rejects empty or synthetic labels.

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
   python -m src.eval.run --golden data/golden/golden_set.csv --calibration data/golden/judge_calibration.csv
   ```

It writes per-intent classification metrics, reply rubric scores, judge–human agreement, escalation precision/recall plus false-auto-handle rate, a three-system comparison table, and `report/REPORT.md`.

## Scope and limitations

The core model is intentionally deterministic and local: keyword intent features plus TF-IDF-style lexical retrieval. This makes the demo cheap and explainable, but it is not the PRD’s proposed LLM classifier or semantic embedding index. `src/eval/judge.py` is a transparent offline rubric fallback, not an LLM-as-judge; replace it with an independently prompted API judge before making a reply-quality claim.

No live Twitter action, credentials, or full-dataset processing is included. Dataset attribution: [Kaggle / thoughtvector](https://www.kaggle.com/datasets/thoughtvector/customer-support-on-twitter).

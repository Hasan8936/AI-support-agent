# Decision Log

## Evaluation integrity

- **Decision:** Reject the committed synthetic fixture in the evaluator and remove its derived score files.
  **Why:** Prompt-generated labels and calibration scores cannot constitute a hand-labelled golden set or evidence of judge agreement. The harness now fails closed until real labels are supplied.
  **Alternative considered:** Keep the fixtures as a fast default benchmark; rejected because it would make untrustworthy results appear submission-ready.

- **Decision:** Run trivial, simple, and full systems through one shared pipeline module.
  **Why:** It makes the baseline comparison reproducible and prevents the API demo from using a different routing implementation than batch evaluation.
  **Alternative considered:** Maintain parallel API and CLI implementations; rejected because divergence would undermine auditability.

- **Decision:** Keep the repo to a compact Python-only MVP instead of building the optional React/FastAPI demo first.
  **Why:** The PRD explicitly treats the evaluation artifact as the primary deliverable, and a smaller code path is easier to run and explain live.
  **Alternative considered:** Build the full front-end and API stack immediately; rejected for scope and time.

- **Decision:** Use a small, committed sample CSV instead of the full Kaggle corpus by default.
  **Why:** The rules prohibit silently processing the full dataset and require reproducibility on a small, reviewable subset.
  **Alternative considered:** Download and process the full 3M-row dataset; rejected as out of scope and slow.

- **Decision:** Store the intent taxonomy in `config/intents.yaml` rather than hardcoding labels in Python.
  **Why:** This matches the design requirements for config-driven, reviewable prompts and policy decisions.
  **Alternative considered:** Keep all labels in code constants; rejected because it becomes hard to document and modify during a live review.

- **Decision:** Use a rule-based classifier as the initial production path for the MVP.
  **Why:** The project is meant to prove a trustworthy pipeline, and a deterministic keyword-based classifier is reproducible and easy to inspect.
  **Alternative considered:** A full LLM-only classifier; rejected because the code needs to be explainable and testable without a live API call.

- **Decision:** Treat retrieval as a similarity over message overlap, not a semantic vector embedding, for the demo implementation.
  **Why:** The repository is a lightweight project artifact, and the requirement is to show grounded precedent retrieval without requiring external embedding models or FAISS setup.
  **Alternative considered:** Add sentence-transformers and a vector index; not necessary for the MVP as presented here.

- **Decision:** Keep the reply draft grounded by reusing historical response text rather than inventing a new policy statement.
  **Why:** This is the safest route for brand-risk mitigation and matches the PRD’s emphasis on grounded, auditable replies.
  **Alternative considered:** Free-form generation with no precedent grounding; rejected because it undermines trust.

- **Decision:** Make escalation depend on policy override first, then retrieval confidence, then LLM confidence.
  **Why:** This matches the hybrid logic described in the techspec and keeps the decision explainable to reviewers.
  **Alternative considered:** A pure model-confidence approach; rejected because it would ignore explicit safety policies.

- **Decision:** Add a small deterministic test harness around the core pieces before deepening the pipeline.
  **Why:** The “finish the project” requirement is best served by locking real behavior and keeping the repo runnable under CI.
  **Alternative considered:** Skip tests and rely on manual inspection; rejected because it is too brittle to explain live.

- **Decision:** Log and document the MVP as a demonstration artifact rather than a finished production system.
  **Why:** The PRD explicitly reserves a number of production concerns as out of scope, so the repo should be honest about what it proves and what it does not.
  **Alternative considered:** Claiming full production readiness; rejected to avoid overstating the system.

- **Decision:** Keep the formatting and output schema intentionally simple for CSV results.
  **Why:** The evaluation harness and CLI need to be easy to inspect without a large data pipeline stack.
  **Alternative considered:** A parquet-heavy implementation and complex schema; rejected as overengineering for the project size.

- **Decision:** Treat the golden set as a placeholder documentation structure rather than a full labeled benchmark.
  **Why:** This repository demonstrates the operational pattern, not a final enterprise-grade dataset.
  **Alternative considered:** Pretending the sample data is a real 150-250 row annotated dataset; rejected because it would misrepresent evidence.

- **Decision:** Use explicit `temperature=0` style deterministic behavior in design, even though the implemented MVP is rules-based.
  **Why:** This aligns with the project rules and ensures the future LLM variant can be made consistent.
  **Alternative considered:** Randomized responses; rejected because the pipeline depends on repeatability.

- **Decision:** Store the run outputs under `results/` rather than embedding them in the repo root.
  **Why:** It keeps the generated artifacts separate from the source code and matches the repository conventions.
  **Alternative considered:** Writing results directly into the root or README; rejected as less organized.

# Project Rules — for AI Coding Assistants (Cursor / Claude Code / etc.)

These are standing instructions for any AI coding tool working in this repo. Follow them for every task unless the user explicitly overrides one.

## 1. Scope Discipline
- Do not add features beyond what's listed in `PRD.md` Core Features or explicitly requested. If tempted to add something (multi-brand support, auth, a fancier UI), stop and flag it as an idea instead of building it.
- Respect the "Out of Scope" list in `PRD.md` — do not implement live Twitter/X posting, multi-language support, or full-dataset processing.
- When in doubt about scope, prefer the smaller/simpler implementation and note the tradeoff in `DECISION_LOG.md`.

## 2. Code Style & Structure
- Python 3.11, follow PEP 8, use type hints on function signatures.
- Keep modules small and single-purpose per `techspec.md` component breakdown (`src/ingest/`, `src/classify/`, etc.) — don't collapse everything into one script.
- Every LLM prompt template lives in its own file/constant (not inline string scattered through logic) so it can be reviewed and modified easily during a live walkthrough.
- Config (intents, escalation thresholds, model names) belongs in `config/*.yaml`, never hardcoded in Python.
- Use `logging`, not `print`, for pipeline progress output.

## 3. Reproducibility Requirements
- Every random operation (sampling, clustering, train/test splits) must take an explicit `seed` parameter, default seeded for reproducibility.
- No step in the documented README pipeline should silently depend on manual/undocumented steps — if a step required manual judgment (e.g. taxonomy labeling), the *output* of that judgment must be committed to the repo (e.g. `config/intents.yaml`) so re-running doesn't require redoing it.
- LLM calls used for classification/escalation should use `temperature=0` (or documented low value) for consistency across runs.

## 4. Data & Cost Discipline
- Never write code that processes the full 3M-row dataset by default — always operate on the committed subsample unless a flag explicitly requests a larger run.
- Any new LLM API call added to a loop must include a rough cost/timing estimate in a code comment or README note.
- Do not commit raw API keys, `.env` files, or the full Kaggle dataset to the repo.

## 5. Evaluation Integrity
- Never modify the golden evaluation set to make results look better after seeing them. If a labeling error is found, log the fix as a dated note in `DECISION_LOG.md`, don't silently edit and re-run.
- Any metric reported in `report/REPORT.md` must be traceable to a file in `eval/` — no metric should exist only in prose.
- The LLM-as-judge and the LLM used for the agent itself should be treated as separate concerns in code (even if using the same underlying model/API) — don't let judge prompts and agent prompts share unrelated state.

## 6. Citations
- Any code, prompt pattern, or approach adapted from a blog post, paper, GitHub repo, or documentation must get a one-line comment citing the source (URL or name), placed directly above the relevant code.
- Third-party library usage (FAISS, sentence-transformers, etc.) doesn't need per-use citation, just needs to be in `requirements.txt`.

## 7. When Asked to Modify Code Live
- Prefer minimal, localized diffs over rewrites, so changes are easy to explain.
- Preserve existing function signatures where possible when asked to "add" behavior, so callers/tests don't silently break.
- If asked to explain a piece of code, check whether a comment already explains the "why" — if not, that's a signal more comments are needed there generally.

## 8. Documentation Maintenance
- If implementation diverges from `techspec.md` or `schema.md` in a meaningful way, update those docs in the same change — don't let docs and code drift.
- Update `tracker.md` checkboxes as milestones complete (can be done by the assistant when explicitly asked, e.g. "mark Milestone 2 as done").

## 9. Tone of Generated Artifacts (report, comments, README)
- Prefer precise, falsifiable statements over marketing language. "F1 improved from 0.41 to 0.68 vs. simple baseline" not "the system performs much better."
- The report and decision log should read as if written by someone trying to find flaws in their own system, not sell it.

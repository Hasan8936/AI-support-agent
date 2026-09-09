# Design Notes — AI Customer Support Agent

This project is primarily a **backend/evaluation artifact**, not a consumer product, so "design" here covers three things: (1) the optional demo UI, (2) the design of the evaluation outputs/report (equally important — this is what gets judged), and (3) the "voice"/tone constraints for generated replies.

## 1. Demo UI Design (optional, React + FastAPI)

**Principle:** the UI exists to make the pipeline's reasoning *inspectable* during a live walkthrough — not to look polished. Prioritize transparency over polish.

**Component structure (React, single page):**
- `App` — top-level layout, holds selected brand + current message + API response in state.
- `BrandSelector` — dropdown, fetches `/api/brands` on mount.
- `MessageInput` — textarea + "load random golden example" button (calls `/api/golden-examples`) + "Run Agent" button (calls `/api/agent/run`).
- `IntentCard`, `PrecedentsCard`, `DraftReplyCard`, `EscalationDecisionCard` — presentational components, receive data via props from the API response; no internal API calls of their own.
- `BaselineComparisonToggle` — on toggle, calls `/api/agent/run-baselines` and renders a 3-column comparison (trivial / simple / full).
- Loading states: simple inline spinner/skeleton per card while awaiting the API response — avoid a single full-page spinner, since the point is to show the pipeline's steps.
- Error states: if the FastAPI call fails (e.g. API key missing, rate limit), show a plain inline error message near the "Run Agent" button — don't fail silently.

**Layout (single page, top to bottom):**
- Header: brand name + logo/color accent (pull brand's approximate color, e.g. Amazon orange) — a light touch, not a full brand redesign.
- Left panel: message input (textarea) + "pick a random golden-set example" button.
- Main panel, after "Run Agent" is clicked, shows 4 stacked cards in this order:
  1. **Intent card** — label, confidence bar, one-line rationale.
  2. **Precedents card** — 2–3 retrieved (past message → resolution) pairs, each with a similarity score shown as a small bar/percentage. This is the most important card for trust — don't hide it behind a toggle.
  3. **Draft reply card** — the generated reply, with retrieved precedents it drew from underlined/footnoted (e.g. `[1]`, `[2]` referencing the precedents card).
  4. **Decision card** — colored badge (green = auto-handle, amber/red = escalate) + the one-sentence reason, rendered prominently (this is the "hard part" of the assignment — don't bury it).
- Optional bottom section: baseline comparison toggle, showing the trivial/simple system's output for the same message side-by-side, so the reviewer can see why the full system is (or isn't) better.

**Style constraints:**
- No dark patterns, no fake load spinners for effect — keep it plain and legible (system fonts, high contrast, generous whitespace).
- Escalation badge color is the one place where color communicates meaning — everything else can be neutral gray/black to avoid looking "salesy."
- Do not brand this as if it were AmazonHelp's/Apple's official product — clearly label it "prototype / evaluation demo" to avoid implying it's an official brand tool.

## 2. Reply "Voice" Design Constraints

Generated replies must:
- Match the brand's general tone as observed in the historical data (e.g. concise, apologetic-but-not-groveling, action-oriented) — derived from the retrieved precedents, not invented.
- Never fabricate policy, refund amounts, order-specific details, or timelines not present in the message or retrieved precedents.
- Avoid making promises the brand's historical replies don't typically make (e.g. don't invent "you'll get a refund within 24 hours" unless precedents show that pattern).
- Stay within a defined length band matching typical historical agent replies for that brand (avoid absurdly long AI-generated replies).

## 3. Evaluation Report Design (this is the actual "product" being judged)

**Principle:** the report should read like a rigorous internal memo, not a marketing deck. Favor plain tables and specific examples over adjectives.

**Structure (maps to PRD/report deliverable):**
1. **Problem framing** — 1 page: what "good" means for this brand + explicit non-goals.
2. **Results table** — one table, three rows (trivial / simple / full system), columns = each headline metric. No prose needed here beyond a caption.
3. **Failure analysis** — top 5 failure modes, each as: (a) 1-sentence description, (b) 1 real example (message + system output + what went wrong), (c) 1-sentence hypothesis for why.
4. **"What's misleading about my headline number"** — this section should specifically call out things like: golden-set sampling bias, LLM-judge blind spots, easy-vs-hard example distribution, any metric that would look worse on the full 3M-row dataset.
5. **Next-week plan** — a short prioritized list, not a roadmap doc.

**Formatting constraints:**
- Max 6 pages if a standalone doc, or an equivalent README section — enforce with a word budget per section (roughly: 400 / 200 / 600 / 300 / 200 words for the five sections above).
- Every quantitative claim must have a number attached to it. Avoid unquantified claims like "the system performs well."
- Real examples (from failure analysis) should be paraphrased/anonymized where needed but must be traceable to a specific golden-set row ID for auditability during live review.

## 4. Decision Log Design

- Plain bullet list, 10–15 items, format: `Decision: ... | Why: ... | Alternative considered: ...`
- Grouped loosely under headers (Data, Taxonomy, Retrieval, Escalation, Evaluation) for scanability, but no need for prose transitions.

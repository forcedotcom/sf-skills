# Task: AI-readiness audit + backfill / validate a model

Backfill missing AI-readiness metadata on an existing model, or validate a model
(no-island + query-returns-data audit). Entry points 14 and 16.

## Gates (assert before any tool call) → `../shared-gates.md`

**Backfill (entry 14):** Required **G1, G3, G5** · Conditional **G6** (◐)
**Validate (entry 16):** Required **G1, G2, G4, G7**

- **G1** (router-asserted): a `mcp__tableau-next-*__` tool must be connected.
- **Tool names are written bare** — invoke each under your client's name for that `tableau-next-*` server tool (`shared-gates.md`).
- **G3 (backfill):** read back the exact apiNames via `list_*` BEFORE any sparse
  `update_*` call — sparse updates that target an assumed/suffixed name silently
  miss. Echo `isVisible` and `dataObjectFieldName` on every dimension/measure
  update (`shared-gates.md` G5 / `sdm-tool-reference.md`).
- **G5 (backfill):** distinct `description` per component (never copy-paste),
  `sentiment` on directional measures/metrics, `agentEnabled:true` via
  `update_semantic_model`, `businessPreferences` via
  `get_semantic_model_business_preferences` /
  `update_semantic_model_business_preferences` (`update_semantic_model`
  fallback), correct date/type and dimension-vs-measure roles. Full
  checklist: `../ai-readiness.md`.
- **G2 + G4 + G7 (validate):** every object joined (no islands) and
  `run_semantic_query` returns real rows. Here G5 is a similarity *scan*, not
  metadata creation — do not over-assert it.
- **G6** (◐, backfill): profile only if a field's role/meaning isn't understood;
  do NOT re-ingest or re-model.

## Steps

The complete AI-readiness checklist, description/label quality guides, ambiguity
management, and `businessPreferences` examples are in **`../ai-readiness.md`**.

- **Backfill** — read back apiNames (`list_semantic_model_dimensions` / `_measures`
  / `_data_objects` / `_metrics`), then sparse `update_semantic_model_dimension` /
  `_measure` (include `description` **and** echo `isVisible` + `dataObjectFieldName`
  — description-only resets hidden fields to visible),
  `get_semantic_model_business_preferences` then
  `update_semantic_model_business_preferences` for prefs (GET first; full
  replacement of `# `-prefixed lines, send only `businessPreferences`;
  `update_semantic_model` is the fallback), `update_semantic_model` for
  `agentEnabled`, and `sentiment` on directional measures/metrics.
- **Validate** — audit that every object participates in ≥1 relationship (G4) and
  that `run_semantic_query` returns real rows (G7); a ~0-row join is broken.
- **Never declare AI-ready on metadata completeness alone** — recommend the
  Semantic Model AI Optimization similarity scan (Semantic Model Builder UI)
  before handoff; `modelHealth: Low` flags ambiguous components. Mention this
  whenever the user asks whether a model is ready, finished, or handoff-able.
- **Scoring golden Q&A / listing verified questions** is
  `review-verified-questions.md`, not this checklist.

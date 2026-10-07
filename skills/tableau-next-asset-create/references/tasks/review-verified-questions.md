# Task: Review verified questions / score agent SQL

List or classify Analytic Verified Questions, manage utterance records, or
score candidate SQL against expected SQL. Do **not** use this to answer a
business question (`query-model.md` / `analyze-data.md`) or to backfill
readiness metadata (`ai-readiness-audit.md`).

## Gates (assert before any tool call) → `../shared-gates.md`

Required: **G1**

- **G1** (router-asserted): a `mcp__tableau-next-*__` tool must be connected.
- **Tool names are written bare** — invoke each under your client's name for
  that `tableau-next-*` server tool (`shared-gates.md`).
- **Confirmation (this guide):** `delete_analytics_utterances` is
  irreversible — confirm first.

## When **not** to use these tools

- **"What is total revenue" / live figures** → `query-model.md`.
- **Interpreted breakdown / trend** → `analyze-data.md`.
- **"Is my model AI-ready" / backfill descriptions** →
  `ai-readiness-audit.md`.

## Steps

Filters, `classificationStatus` enum, `fetchInteractions` / only-surface-
`query`, classify NPE if `interaction` omitted, utterance CRUD, and
evaluator caveats are in **`../verified-questions.md`**.

1. **List / audit** — `list_analytics_interactions` once for all models
   (do not loop per SDM). Paginate with `offset`. Default sort
   `lastModifiedDate DESC` when recency matters.
2. **One classified question** — `get_analytics_full_interaction` by
   utterance API name. Not for unclassified questions.
3. **Verify / reject status** — `classify_analytics_interactions`. For
   payload edits, `update_and_classify_analytics_interaction` (always send
   `interaction`).
4. **Question text only** — utterance get/create/update/delete tools. Do
   not set `agentId` on create.
5. **Score SQL** — `run_regression_evaluator` once per Q&A pair. Requires
   expected + actual SQL + `dataspace`. Persists nothing.

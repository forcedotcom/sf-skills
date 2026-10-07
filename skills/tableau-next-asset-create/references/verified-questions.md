# Verified questions, utterances, and regression eval

Load this from `tasks/review-verified-questions.md`. Not a first hop.

Analytic Verified Questions (AVQ) and SQL calibration. This is **not**
AI-readiness metadata (`tasks/ai-readiness-audit.md`), **not**
`run_semantic_query` (`query-model.md`), and **not** `analyze_data`.

The MCP tools are namespaced per server — names here are bare; use whichever
server prefix is connected. All of these are **current org only**.

## Contents

- List / get interactions
- Classify / update-and-classify
- Utterance CRUD (question text only)
- `run_regression_evaluator` (score SQL, persist nothing)

---

## `list_analytics_interactions`

Enumerate question/answer pairs. **Covers ALL models in one query — never
loop per SDM.** Omit `semanticModels` unless the user asked to filter to a
specific model. Pagination is separate: a single call still returns at most
`limit` rows; keep calling with advancing `offset` until a page is empty (or
you have the reported total).

**Inputs (all optional):**

- `limit`, `offset`
- `orderBy` — e.g. `lastModifiedDate DESC`
- `classificationStatus` — `New` | `Regression` | `Inaccurate` | `Verified`
  | `NeedsValidation`
- `semanticModels` — comma-separated IDs/apiNames; omit for all models
- `agentType` — `Concierge` | `Inspector`
- `sourceType` — `Csv` | `Feedback` | `Generated` | `Manual`
- `fetchInteractions` — default `false`. `false` = questions without agent
  responses/SQL; `true` when agent response data is needed
- `utterance` — search string
- `isRequiresReview` — classifications needing review
- `agentResponse` — `Nl2Sql` | `Waii`

**Returns:** `items[]` with utterance, classification, semantic model,
timestamps, and (when fetched) agent response.

**When `fetchInteractions=true`:** surface **only** the `query` property of
the agent interaction data to the user. Do not dump the rest of that
payload.

**Use when:** browse, search, or audit past interactions and classification
status.

---

## `get_analytics_full_interaction`

Full payload for **one** classified interaction, by utterance API name
(from `list_analytics_interactions`).

Returns utterance text, classification status, semantic model, agent
response, and associated interaction data.

**Use when:** the user wants full details of a question that already has a
classification (reviewed / verified / rejected). **Do not** use this for
new or unclassified questions.

---

## `classify_analytics_interactions`

Update one or many classifications in a single request (verify, reject, or
change status). Each item is identified by classification ID plus the
fields to change.

---

## `update_and_classify_analytics_interaction`

Update an interaction-with-classification record by classification ID
(path).

**Required:** `interaction` (e.g. `analyticsUtteranceId`, `agentUtterance`,
`sources`) — even for classification-only updates. Omitting it causes a
**500 NPE**, not a validation error.

When the user asks to update a question with a SQL query, set SQL as
`agentInteractionData` wrapped as an escaped JSON string:
`{"query": "<escaped SQL>"}`. `agentResponse`: if the SQL starts with
`WITH`, set `Waii`; otherwise `Nl2Sql`.

---

## Utterance CRUD (question text only)

These operate on the **utterance** (question text/metadata). They do **not**
create, update, or delete the interaction / agent response / classification.

| Tool | Notes |
|---|---|
| `get_analytics_utterance` | By API name. Returns text, agent type, source type, model API name, status. |
| `create_analytics_utterances` | Collection of utterances (text + model API name, agent type, source type). **Do not set `agentId`** — utterances must not be tied to a specific agent. |
| `update_analytics_utterance` | By API name. Fields: utterance text, model API name, agent type, source type. |
| `delete_analytics_utterances` | Collection of utterance API names. **DESTRUCTIVE — no undo.** Confirm first. Does not directly delete the interaction or classification. |

---

## `run_regression_evaluator`

Score one Q&A calibration pair: candidate agent SQL
(`actualAgentResponse`) vs expected SQL (`expectedAgentResponse`) for the
same question.

**Required:** `semanticModelApiName` (full model resolved server-side),
`utterance`, `dataspace`, `actualAgentResponse`, `expectedAgentResponse`.

**Returns:** `success` (`true` if candidate matches baseline) and
`explanation` (human-readable rationale).

**Caveats:**

- **Evaluation-only** — scores a single test and **persists nothing**.
- One Q&A pair per call; batch by calling once per pair.
- Not a substitute for `run_semantic_query` or `analyze_data`. Those run
  live questions against data; this compares two SQLs.

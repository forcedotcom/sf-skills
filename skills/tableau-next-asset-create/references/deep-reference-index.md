# Deep reference index

What each deep reference covers and which task guide cites it. Cited by the
router (`SKILL.md`); the first-hop rules there still apply.

- **`references/build-workflow.md`** — full numbered-step procedural spine (Step
  0→11) with verified per-tool payloads and inline gotchas. Cited by
  `tasks/build-end-to-end.md`; **not a first hop.**
- **`references/large-flat-file-handling.md`** — infer-don't-read protocol,
  naming-grammar decode, elicitation gate, verify-one-number gate (G6).
- **`references/data-understanding.md`** — the five things to profile (grain,
  field roles, cardinality, additivity, date roles) and the SDM handoff (G6).
- **`references/sdm-tool-reference.md`** — `add_semantic_model_*` input shapes,
  suffix rules, nested create-time field bind (G3), sparse-vs-PUT updates,
  parameter PUT, logical-view shapes, dependency pre-flight.
- **`references/empty-source-handling.md`** — empty-of-rows vs. unmaterialized
  detection and what to tell the user (G2).
- **`references/semantic-query-and-enrichment.md`** — proto-shaped
  `run_semantic_query` body, field-shape matrix, worked calc/metric payloads
  (G5, G7).
- **`references/ingest-and-metric-gotchas.md`** — the ingestion chain
  (CSV/Excel §A and existing-connection §C → DLO → DMO → mapping: wait-until-ready, SCHEMA REALITY CHECK,
  Primary Key read-back, mapping `ACTIVE` ≠ table exists — poll `run_query`) and metric-creation
  gotchas (§B);
  cited by `ingest-flat-file.md` and `enrich-model.md`. **Not a first hop** for
  an ingest-how-to (that first-hops to `tasks/ingest-flat-file.md`).
- **`references/data-transform-gotchas.md`** — DCSQL transform create/update
  payload, confirmation gates, immutable fields, timeout recovery, BATCH↔DCSQL
  pairing, DMO `KQ_<pk>`. Cited by
  `tasks/create-data-transform.md`; **not a first hop.**
- **`references/sharing-and-promotion.md`** — principal lookup, access-type
  matrix, Personal Org shadow IDs, safe share mutation, Reuse/Promotion
  lifecycle and PR recovery. Cited by `tasks/share-asset.md` and
  `tasks/promote-or-reuse.md`; **not a first hop.**
- **`references/viz-authoring.md`** — chart-type decision matrix, field selection,
  verified `create_visualization` payloads (G8, create-viz). Cited by
  `tasks/create-viz.md`; **not a first hop.**
- **`references/edit-visualization.md`** — `edit_visualization` operation-batch
  reference: op-type table, filter-operator rules, the `field.function` vs
  `line.function` reference-line disambiguation, `update_visualization`
  persistence handoff (edit-viz). Cited by `tasks/edit-viz.md`; **not a first hop.**
- **`references/dashboard-authoring.md`** — dashboard creation, the 48-col grid,
  `&`-encoding gotcha, `delete_dashboard`, global filters
  (`add_global_filter_to_dashboard`), `list_asset_dependencies` preflight
  before a viz/dashboard delete, and `render_dashboard` vs `get_dashboard` (§8)
  (G8, build-dashboard). Cited by `tasks/build-dashboard.md` (not a first hop
  for authoring); first hop from Destructive for the delete preflight and
  from dispatch for "show my dashboard".
- **`references/edit-dashboard.md`** — `edit_dashboard` operation-batch
  reference: the `upsert_*_widget`/page-op table, the widget-identity rule
  (`widget.name`/`widget.id` vs. `placement.name`), draft-vs-persist
  (`save_dashboard`/`undo`/`discard_dashboard`, each with standalone- and
  mixed-batch behavior), and full widget deletion via
  `remove_widget_from_dashboard` (edit-dashboard §6).
  Cited by `tasks/edit-dashboard.md`; **not a first hop.**
- **`references/dashboard-design-principles.md`** — MANDATORY narrative/visual
  design (KPIs → trends → breakdowns → correlations), the G8 source. Direct-dispatch
  for a before-charting narrative/layout question.
- **`references/ai-readiness.md`** — complete AI-readiness checklist, description/
  label quality, ambiguity management, `businessPreferences` examples (G5).
- **`references/admin-users.md`** — `upsert_user` preview formats, ADD
  CONFLICT, Personal Org `forceDeactivate`, `get_users` pagination,
  `get_license_availability`. Cited by `tasks/provision-user.md`; **not a
  first hop.**
- **`references/alerts.md`** — `conversationContext` transcript, do-not-pin
  SDM, preview/`userConfirmed`, timeout-poll `get_alerts`, update full
  replacement. Cited by `tasks/manage-alert.md`; **not a first hop.**
- **`references/insight-bundle.md`** — app-only `generate_insight_bundle` /
  `render_metric` call shape (server-minted JWT; live `/v2/internal/bundle`
  404 is backend). Cited by `tasks/build-dashboard.md`; **not a first hop
  and not a user dispatch.**
- **`references/verified-questions.md`** — AVQ list/classify/utterance
  family and `run_regression_evaluator`. Cited by
  `tasks/review-verified-questions.md`; **not a first hop.**

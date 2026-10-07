---
name: tableau-next-asset-create
description: "Build and edit Tableau Next semantic models (SDMs), vizzes, and dashboards via MCP. TRIGGER when: building a semantic model or dashboard from CSV/Excel files; ingesting a flat file/database into DLO/DMO; profiling a dataset (grain, measures, dimensions; large/wide files via `infer_object_schema`); adding a dimension, measure, AI-ready metric, join, or logical view; running a semantic query, interpreting a breakdown, analyzing account/customer engagement, or pulling counts/totals from existing Tableau Next data (even unnamed/read-only); creating/editing a viz (filter, forecast, sort, shelf, mark encoding, reference line), widget, or dashboard layout. Also: Data Cloud SQL transforms; show a dashboard; share/revoke access; reuse prod or promote Personal Org assets; provision users/licenses; data alerts ('alert me when'); list/classify verified questions or score agent SQL. DO NOT TRIGGER for: rewriting prose descriptions, layout-only dashboard review, debugging MCP, or writing app code."
metadata:
  version: "1.1"
  domains: ["Tableau Next"]
  mcpTools:
    tableau-next:
      tools:
        - add_asset_share
        - add_global_filter_to_dashboard
        - add_semantic_model_calculated_dimension
        - add_semantic_model_calculated_measure
        - add_semantic_model_data_object
        - add_semantic_model_dimension
        - add_semantic_model_logical_view
        - add_semantic_model_measure
        - add_semantic_model_metric
        - add_semantic_model_parameter
        - add_semantic_model_relationship
        - add_workspace_asset
        - analyze_data
        - browse_data_assets
        - browse_data_assets_v2
        - classify_analytics_interactions
        - create_alert
        - create_analytics_utterances
        - create_dashboard
        - create_data_model_object
        - create_data_stream
        - create_data_transform
        - create_dlo_to_dmo_mapping
        - create_promotion_pull_request
        - create_reuse_promotion_request
        - create_semantic_model
        - create_visualization
        - delete_alert
        - delete_analytics_utterances
        - delete_dashboard
        - delete_semantic_model
        - delete_semantic_model_calculated_dimension
        - delete_semantic_model_calculated_measure
        - delete_semantic_model_data_object
        - delete_semantic_model_logical_view
        - delete_semantic_model_metric
        - delete_semantic_model_parameter
        - delete_semantic_model_relationship
        - delete_visualization
        - delete_workspace
        - edit_dashboard
        - edit_visualization
        - generate_business_preference
        - generate_presigned_credential
        - get_alerts
        - get_analytics_full_interaction
        - get_analytics_utterance
        - get_connection
        - get_dashboard
        - get_data_stream
        - get_data_transform
        - get_data_transform_run_history
        - get_dlo_to_dmo_mapping_status
        - get_license_availability
        - get_promotion_reuse_request
        - get_semantic_model
        - get_semantic_model_business_preferences
        - get_semantic_model_calculated_dimension
        - get_semantic_model_calculated_measure
        - get_semantic_model_data_object
        - get_semantic_model_logical_view
        - get_semantic_model_metric
        - get_semantic_model_relationship
        - get_upload_connection
        - get_users
        - get_visualization
        - infer_object_schema
        - list_analytics_interactions
        - list_asset_dependencies
        - list_asset_shares
        - list_connections
        - list_dashboards
        - list_data_connection_objects
        - list_promotion_reuse_requests
        - list_semantic_model_calculated_dimensions
        - list_semantic_model_calculated_measures
        - list_semantic_model_data_objects
        - list_semantic_model_dependencies
        - list_semantic_model_dimensions
        - list_semantic_model_measures
        - list_semantic_model_metrics
        - list_semantic_model_parameters
        - list_semantic_model_relationships
        - list_semantic_models
        - list_visualizations
        - list_workspace_assets
        - list_workspaces
        - refresh_data_transform_status
        - remove_asset_share
        - remove_workspace_asset
        - render_dashboard
        - render_visualization
        - run_data_stream
        - run_data_transform
        - run_query
        - run_regression_evaluator
        - run_semantic_query
        - search_users_and_groups
        - set_data_transform_schedule
        - test_existing_connection
        - update_alert
        - update_analytics_utterance
        - update_and_classify_analytics_interaction
        - update_asset_share
        - update_data_transform
        - update_semantic_model
        - update_semantic_model_business_preferences
        - update_semantic_model_calculated_dimension
        - update_semantic_model_calculated_measure
        - update_semantic_model_data_object
        - update_semantic_model_dimension
        - update_semantic_model_logical_view
        - update_semantic_model_measure
        - update_semantic_model_metric
        - update_semantic_model_parameter
        - update_semantic_model_relationship
        - update_visualization
        - upsert_user
        - validate_data_transform
      semver: ">=1.0.0"
  cliTools:
    - tool: ["gh"]
      semver: ">=2.0.0"
---

# Tableau Next SDM Authoring — Router

Build semantic data models that actually return data, then enrich, query, and
visualize them. This skill encodes the failures that produce empty or
confidently-wrong dashboards in Tableau Next — building on **empty** source
objects, leaving objects **unjoined**, inventing field **apiNames**, summing an
ID, inflating a snapshot by its date count — and carries through to enriching,
querying, and visualizing the model.

This file is a **router**. It does two things: assert the one universal
precondition (G1), then dispatch your intent to the right task guide. The
guardrails that overlap between steps live in exactly one place —
**`references/shared-gates.md`** (gates G1–G8) — and each task guide opens with
the gates it must assert. Read the gate file once; every guide points back to it.

**The MCP tools are exposed under a `tableau-next-*` server** (Claude Code, for
example, advertises them as `mcp__tableau-next-pilot-production__add_semantic_model_relationship`).
Every tool name in this skill — router and reference/task files alike — is written
**bare** (e.g. `add_semantic_model_relationship`) for readability; invoke each one
under whatever name your client exposes for that server's tool. Match the advertised
name — do not hand-construct it. (Single statement: `references/shared-gates.md`.)

## G1 — Precondition (assert once, here, before dispatching)

Every step of this skill drives a Tableau Next MCP server; without one connected
there is nothing to call. Before dispatching to any guide, confirm the available
tools include one prefixed `mcp__tableau-next-*__` (e.g.
`mcp__tableau-next-pilot-production__browse_data_assets`,
`mcp__tableau-next-self-service__create_semantic_model`). Server names vary — match
the `tableau-next` stem, not an exact name.

**If NO such tool is present, STOP.** Do not attempt the workflow, do not describe
payloads as if you had run them, and never fabricate tool calls, results, or IDs.
Tell the user the skill requires a connected Tableau Next MCP server (e.g.
`tableau-next-pilot-*`, `tableau-next-self-service`) and ask them to connect one
and re-invoke. Every entry point inherits this — a standalone "add a metric" with
no server must still STOP. Full statement: `references/shared-gates.md` G1.

## Dispatch — route your intent to a task guide

Classify on **what the user wants to do**, then read that guide. Each guide's
header names the gates it asserts (from `references/shared-gates.md`).

Question phrasing does not exempt an intent from classification. "How do I
profile X" → `profile-dataset.md`. "What payload do I use for
`create_visualization`" / "which chart type for a stacked bar" →
`create-viz.md` (**not** `viz-authoring.md` — that file is cited by the
guide, it is not a first hop). "Before I build, how should I design the
layout" → `dashboard-design-principles.md` (load this skill; do not answer
from general dashboard knowledge). Only an explicit disclaimer of
*authoring* ("don't build/create anything") sends advice / review / ideation
to the No-dispatch rule. A disclaimer that still asks for a number, table,
or interpretation ("don't build or change any model — just get the count
from existing Tableau Next data") is a query/analyze intent: route to
`query-model.md` / `analyze-data.md`. The question mark is never the test.

| User intent | Route to |
|-------------|----------|
| "analyze this CSV" / "build a dashboard from these files" / nothing modeled yet | `references/tasks/build-end-to-end.md` |
| "ingest this CSV / Excel into a DLO/DMO" or ingest from an existing Snowflake / Databricks / BigQuery / Redshift connection (ingest only, no downstream ask) | `references/tasks/ingest-flat-file.md` |
| "create / update a data transform" / derived DLO or DMO via Data Cloud SQL | `references/tasks/create-data-transform.md` |
| "profile / discover / check this data" (read-only) | `references/tasks/profile-dataset.md` |
| add a **raw** object / dimension / measure / join / **logical view** / **parameter** to my model | `references/tasks/edit-sdm.md` |
| add a **calculated** dimension / measure / **metric** to my model | `references/tasks/enrich-model.md` |
| "is my model AI-ready" / "backfill readiness metadata" / validate a model | `references/tasks/ai-readiness-audit.md` |
| count / total / scalar ("how many orders", "what is total revenue") or named-model structured `run_semantic_query` or raw DLO/DMO `run_query` | `references/tasks/query-model.md` |
| interpreted breakdown / ranking / trend / comparison without asking to author | `references/tasks/analyze-data.md` |
| delete a calc / metric / data object / logical view / relationship (component, not the whole SDM) | `references/sdm-tool-reference.md` |
| "create a viz / chart" OR which-chart-type / `create_visualization` payload (no existing chart; not "just advise") | `references/tasks/create-viz.md` (then that guide cites `viz-authoring.md` — do **not** skip to it) |
| "edit / add a filter / forecast / sort / field to **this** chart" (an existing viz) | `references/tasks/edit-viz.md` |
| "show / view / display my existing chart/visualization" (no edit) | Call `get_visualization` directly (`minorVersion: -1`) — renders inline; do NOT chain `render_visualization` |
| "show / view / display / open my existing dashboard" (no edit) | Call `render_dashboard` (`addVisualization=true`, `addSdm=true`, `showDraft=true`, `minorVersion=-1`) — details in `references/dashboard-authoring.md` §8. Do **not** use `get_dashboard` (metadata-only, does not render) |
| "create a dashboard" / design a dashboard layout / add a global filter (no existing dashboard to edit) | `references/tasks/build-dashboard.md` |
| "edit an existing dashboard" / add-move-remove a widget / add-rename-delete a page on a dashboard that already exists | `references/tasks/edit-dashboard.md` |
| "how should I design the narrative/layout before charting" (no existing dashboard to review) | `references/dashboard-design-principles.md` |
| share / revoke / list who has access (user or group on a dashboard, viz, workspace, or SDM) | `references/tasks/share-asset.md` |
| reuse a prod asset in a Personal Org **or** promote a Personal Org asset / open a promotion PR | `references/tasks/promote-or-reuse.md` |
| provision / list Tableau Next users / check licenses (org **role**, not asset ACL) | `references/tasks/provision-user.md` |
| "alert me when" / change that alert / list or delete my alerts (ongoing monitor) | `references/tasks/manage-alert.md` |
| list / classify verified questions **or** score agent SQL against expected SQL | `references/tasks/review-verified-questions.md` |

**Destructive / lifecycle operations** — component and whole-asset deletes,
workspace asset association, share/reuse/promotion mutations, `upsert_user`,
`delete_alert`, `delete_analytics_utterances`, `edit_dashboard` drafts, and
double-wrapped `defaultExc` responses: read
**`references/destructive-operations.md`** before calling any of them. Always
get explicit user confirmation before `delete_visualization` /
`delete_dashboard` / `delete_semantic_model` / `delete_workspace`, and never
call `save_dashboard` or `upsert_user` without the user's explicit go-ahead.

**Disambiguation:**
- **calculated vs. raw** — a calc dimension/measure/metric routes to
  `enrich-model.md`; a plain object/dimension/measure/join/**logical view**
  routes to `edit-sdm.md`.
- **analyze vs query vs greenfield** — figures (counts, totals, scalars;
  "how many orders", "what is total revenue") → `query-model.md`
  (`run_semantic_query`; discover the SDM with `list_semantic_models` if
  unnamed), **including** when the user says not to build or change a model.
  Interpreted breakdowns, rankings, trends, comparisons →
  `analyze-data.md` (`analyze_data`; do not pin `targetEntityNameOrId` /
  `targetEntityType` unless the user named an SDM). Named already-built model +
  structured table / explicit `run_semantic_query` → `query-model.md`. Raw SQL
  against a DLO/DMO (`run_query`) when no SDM covers the data, or the user
  asked for SQL, also → `query-model.md` (that guide prefers
  `run_semantic_query` when an SDM exists). Nothing modeled yet / CSV /
  "build a dashboard" → `build-end-to-end.md`. Ingest from an existing
  database connection (not a local file) still → `ingest-flat-file.md`.
  Derived table / Data Cloud SQL transform → `create-data-transform.md`, not
  ingest and not `enrich-model.md`. Metadata discovery (list SDMs, fields,
  relationships) is `list_*` / `get_*`, not `analyze_data`.
- **create vs. edit a viz** — a request that names or clearly references an
  **existing** chart ("add a forecast to my monthly sales chart", "filter this
  chart to West") routes to `edit-viz.md`; a request with no existing chart in
  play ("create a bar chart of sales by category", "which chart type and what
  `create_visualization` payload for a stacked bar") routes to `create-viz.md`.
  Do not skip to `viz-authoring.md`.
- **create vs. edit a dashboard** — a request that names or clearly references an
  **existing** dashboard ("add a KPI widget to my sales dashboard", "move this
  chart to the top", "add a details page to the pipeline dashboard") routes to
  `edit-dashboard.md`; a request with no existing dashboard in play ("create a
  dashboard for regional sales", "design a dashboard layout for these metrics")
  routes to `build-dashboard.md`. Do not skip to `dashboard-authoring.md`.
- **show vs get vs edit a dashboard** — "show / open / view my Sales
  dashboard" (including naming or id'ing one to see it), no edit → `render_dashboard`
  (`dashboard-authoring.md` §8). Widget JSON / PATCH or `edit_dashboard` prep on
  an **existing** dashboard → `get_dashboard` then `edit-dashboard.md`. "Review
  this dashboard, don't modify it" stays No-dispatch.
- **Fast-path** — if a suitable **already-built, populated, joined** model is
  available (named, or discovered via `list_semantic_models`) and the user wants
  figures or a structured table, this skill's build steps are not the entry
  point: route to `query-model.md` (`run_semantic_query`). An interpretive
  question (breakdown, ranking, trend, comparison) → `analyze-data.md`.
- **Greenfield** — "analyze account engagement / build a dashboard" where no
  model exists yet is a *build* intent (the trigger is "the user wants insight
  from data that isn't modeled yet," not the literal phrase "semantic model") →
  `build-end-to-end.md`.
- **share vs workspace membership** — granting a user/group `accessType` on an
  asset routes to `share-asset.md`. Putting an asset in a workspace
  (`add_workspace_asset`) is not a share.
- **revoke share vs delete the asset** — "unshare Alice" / "remove her access"
  → `share-asset.md`. Deleting the dashboard/model/workspace itself stays on
  the destructive tools above.
- **reuse / promote vs create** — copying or packaging an **existing** asset
  routes to `promote-or-reuse.md`. Building a new SDM from data still goes to
  `build-end-to-end.md` / `edit-sdm.md`.
- **share vs provision a user** — "share this dashboard with Alice" /
  viewer-vs-editor on an asset → `share-asset.md` (`search_users_and_groups`).
  "Add Alice as Analyst" / list Tableau Next users / check seats →
  `provision-user.md` (`get_users` / `upsert_user`). Granting a **role** is
  not granting `accessType` on an asset.
- **analyze vs alert** — one-off "why did EMEA sales drop" /
  breakdown/trend/comparison → `analyze-data.md`. "Alert me when bookings
  drop 10% week over week" / change or list my alerts → `manage-alert.md`.
  Do not pin an SDM on either path.
- **query vs score SQL** — "what is total revenue" → `query-model.md`.
  "Does this agent SQL match the expected SQL" →
  `review-verified-questions.md` (`run_regression_evaluator`; persists
  nothing).
- **AI-ready vs verified questions** — backfill descriptions / `agentEnabled`
  / prefs → `ai-readiness-audit.md`. List/classify AVQ or score golden Q&A →
  `review-verified-questions.md`.
- **insights (analyze vs metric-card payload)** — "generate insights on EMEA
  sales" / interpretive "what should I focus on" → `analyze-data.md`. The
  dashboard metric-card live value/trend/status payload is
  `generate_insight_bundle` / `render_metric` for the MCP app renderer
  (`insight-bundle.md`) via `app.callServerTool()`. The model does **not**
  call those tools on a user chat turn and does **not** first-hop to
  `insight-bundle.md`.

## No-dispatch rule (decline — do NOT route into an authoring guide)

The surface verbs above ("create a viz", "edit sdm", "create metric",
"create/update dashboard", "share", "promote", "reuse", "provision",
"alert", "classify") collide word-for-word
with work this skill is **not**
for. Classify on **build-vs-advise/review/ideate/edit-prose**, not the surface
verb. Decline (or hand off) these — do not dispatch:

- **Advice, no build** — "which chart type, stacked vs grouped? don't create
  anything" → advise; do not route to `create-viz.md`.
- **Prose edit on an existing model** — decline any request whose *only* change
  is the wording of an existing description/label, no matter the verb used
  ("rewrite", "update", "fix", "correct", "improve", "reword" all count — the verb
  is not the test). The test is: **does this add/change a field, join, metric, or
  grain? If not — pure copy-editing — decline.** E.g. "rewrite the description on
  my existing model" or "fix the typo in this field's description" → decline. This
  is the sharpest near-miss: `edit-sdm.md` / `ai-readiness-audit.md` literally wrap
  `update_semantic_model_dimension/_measure` as sparse description updates, so it
  is tempting — but a prose-only edit is not authoring the model. (Backfilling
  *missing* readiness metadata as part of making a model AI-ready IS in scope
  and must echo `isVisible` + `dataObjectFieldName` — see G5; rewording existing
  prose for style, accuracy, or typos is not.)
- **Ideation, no data** — "brainstorm KPIs I could track later, no changes now" →
  ideate; do not route to `enrich-model.md`.
- **Review** — "review my dashboard layout, don't modify it" / "someone on my
  team built this, what's confusing" → review; do not route to
  `build-dashboard.md`. Designing the narrative *before* you drop charts is
  the opposite intent — that **does** dispatch (to
  `dashboard-design-principles.md`).
- **Share advice, no grant** — "who should I share this with / viewer vs
  editor? don't actually share" → advise; do not route to `share-asset.md`.
- **Provision advice, no mutate** — "who should I add as Analyst? don't
  provision anyone" → advise; do not route to `provision-user.md`.
- **Alert advice, no monitor** — "should I alert on this KPI? don't create
  one" → advise; do not route to `manage-alert.md`.

A "don't build / don't change anything" disclaimer does **not** by itself
mean No-dispatch. Count / total / scalar ("how many orders") and named-model
structured query still route to `query-model.md`; interpreted breakdown /
ranking / trend / comparison still route to `analyze-data.md`. Those are
in-scope redirects, not declines.

Also out of scope: debugging a broken MCP server (→ Columbo / standard
debugging); writing application code / managing AI Suite infra.

## Deep references (cited by task guides)

The task guides point *down* to these for verified payloads and tool shapes.
A narrow lookup — "how do I / what is / what's the exact ___" — is a
**direct-dispatch** only when the list below names that file. Viz,
dashboard-widget, ingest, and greenfield-build lookups are **not**
direct-dispatch: first-hop to the matching `references/tasks/*.md` guide
(the guide then cites the deep ref). In particular, chart-type /
`create_visualization` payload questions first-hop to `tasks/create-viz.md`;
**`viz-authoring.md` is not a first hop.**

Direct-dispatch lookups:

- "how do I handle a huge/wide CSV with cryptic columns" → `large-flat-file-handling.md`
- "how do I figure out grain / measures vs. dimensions [before modeling]" → `data-understanding.md`
- "what's the input shape / suffix rule for `add_semantic_model_*`" → `sdm-tool-reference.md`
- "how do I bind SDM fields in one `create_semantic_model` call" → `sdm-tool-reference.md`
- "how do I add or update a semantic-model parameter" → `tasks/edit-sdm.md`
  (shapes in `sdm-tool-reference.md` Parameters)
- "how do I add a HardJoin / Union / CustomSQL logical view" → `tasks/edit-sdm.md`
  (shapes in `sdm-tool-reference.md`)
- "how do I safely delete a calc / metric / data object / logical view / relationship" →
  `sdm-tool-reference.md`
- "what depends on this viz / dashboard" / before deleting a viz or dashboard →
  `dashboard-authoring.md`
- "how do I show / open / view a dashboard" (inline render, not metadata) →
  `dashboard-authoring.md` (§8 `render_dashboard`)
- "why did my query return zero rows" / "empty vs. does-not-exist" → `empty-source-handling.md`
- "how do I write a `run_semantic_query` body" → `semantic-query-and-enrichment.md`
- "how do I make my model AI-ready" (checklist; not "backfill it now") → `ai-readiness.md`
- "how should I design the narrative/layout before charting" → `dashboard-design-principles.md`

Not a first hop (cited only from the matching task guide):

- "which chart type / what `create_visualization` payload" → `tasks/create-viz.md`
  (NOT `viz-authoring.md`)
- "how do I add/move/remove a widget on an **existing** dashboard" →
  `tasks/edit-dashboard.md` (NOT `edit-dashboard.md` the deep ref, and NOT
  `dashboard-authoring.md`)
- "how do I create a dashboard / lay out a **new** dashboard" →
  `tasks/build-dashboard.md` (NOT `dashboard-authoring.md`)
- "how do I ingest a CSV / Excel / existing connection into a DLO/DMO" → `tasks/ingest-flat-file.md`
  (NOT `ingest-and-metric-gotchas.md`)
- "how do I create or update a data transform" → `tasks/create-data-transform.md`
  (NOT `data-transform-gotchas.md`)
- "walk me through building a model end to end" → `tasks/build-end-to-end.md`
  (NOT `build-workflow.md`)
- "how do I share / unshare / list who has access" → `tasks/share-asset.md`
  (NOT `sharing-and-promotion.md`)
- "how do I reuse a prod asset or promote a Personal Org asset" →
  `tasks/promote-or-reuse.md` (NOT `sharing-and-promotion.md`)
- "how do I provision / list Tableau Next users / check licenses" →
  `tasks/provision-user.md` (NOT `admin-users.md`)
- "how do I create / update / list / delete a data alert" → `tasks/manage-alert.md`
  (NOT `alerts.md`)
- "how do I list verified questions / score agent SQL" →
  `tasks/review-verified-questions.md` (NOT `verified-questions.md`)

What each deep reference covers (and which guide cites it) is in
**`references/deep-reference-index.md`**.

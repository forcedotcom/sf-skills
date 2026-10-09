---
name: crm-analytics-wave-generate
description: "Use to build a Wave Recipe, deploy a CRM Analytics dataset or dashboard, or author the full CRMA asset stack — apps, Wave Recipes (.wdpr), datasets, and dashboards — against a connected Salesforce org via REST and Metadata APIs, without CRM Analytics Studio or Dashboard Builder. TRIGGER when: user asks to build or create a Wave Recipe, generate a .wdpr or .wdpr-meta.xml, deploy a .wdash or .wapp, run a recipe or dataflowjob programmatically, upload CSV data via InsightsExternalData, validate a dataset schema with synthetic data, fetch dataset XMD, audit dashboard SAQL re-encoding, or find unused dataset fields. TRIGGER on keywords: Wave Recipe, CRMA, CRM Analytics, wdpr, wdash, wapp, WaveRecipe, Wave dataflow, dataflowjob, InsightsExternalData, SAQL, dataset XMD, Analytics Studio, R3 format, wave/recipes, wave/dashboards, or analytics on Salesforce objects (opportunities, leads, cases, accounts, sales). DO NOT TRIGGER for standard Salesforce reports or LWC components unrelated to CRM Analytics."
metadata:
  version: "1.0"
  minApiVersion: "59.0"
  cliTools:
    - tool: ["curl"]
      semver: ">=7.0.0"
    - tool: ["node"]
      semver: ">=18.0.0"
    - tool: ["sf"]
      semver: ">=2.0.0"
---

# Authoring CRM Analytics Assets

End-to-end workflow for authoring the full CRM Analytics asset stack — application, Wave Recipe, dataset, and Wave Dashboard — against a Salesforce org from a local SFDX project, without the UI.

## Scope

- **In scope**: WaveApplication, WaveRecipe (R3 format), Wave datasets (recipe-driven + CSV upload via InsightsExternalData), Wave Dashboards (.wdash deploy + PATCH styling), SAQL step authoring, dataset XMD inspection, dashboard auditing.
- **Out of scope**: Standard Salesforce reports/dashboards, LWC analytics bridge components, Tableau CRM managed packages, org provisioning.

---

## Decision Tree — Pick the Right Method

Before acting, read `references/method-decision-tree.md` to select the correct API path for the user's goal. Wrong method choices (e.g. multipart upload instead of R3 JSON body) cause silent failures that are hard to diagnose.

---

## Required Inputs

- Authenticated org alias (verify with `sf org display -o <alias> --json`)
- Target CRMA app name (folder developer name)
- Recipe or dashboard name and output dataset alias
- Source sObjects to load (API names, e.g. `Opportunity`, `Account`)
- Field list per sObject
- Transformation intent: formula fields, aggregations, filter conditions

Defaults:
- Local Salesforce connector name: `SFDC_LOCAL` (verify via `GET /wave/dataConnectors`)
- API version: use `result.apiVersion` from `sf org display`
- Node.js binary: `/usr/local/lib/sf/bin/node` (bundled with sf CLI)

---

## Workflow

### Phase Selection

Before starting, identify the user's goal and determine which phases to run:

| User goal | Phases to run |
|-----------|--------------|
| Build or update a recipe and dataset | 0 → 1 → 2 |
| Validate recipe output schema after run | 0 → 1 → 2 → 3 |
| Build or update a dashboard | 0 → 1 → 2 → 4 |
| Full end-to-end: recipe + validation + dashboard | 0 → 1 → 2 → 3 → 4 |
| Audit dataset for unused fields / stale SAQL | 0 → 1 → 5 |

Execute only the phases in the selected path. Do not revisit this table mid-workflow.

### Phase 0 — Bootstrap Scripts

1. **Check for helper scripts** — before running any script referenced in this workflow, verify the `scripts/` directory exists in the skill root. All 11 scripts listed in `references/scripts-reference.md` are bundled with this skill. If a script is somehow missing, check that the skill was installed from the full repo (not a partial clone). Do not regenerate scripts from the descriptions — the implementations are authoritative.

### Phase 1 — Setup

2. **Verify org connection** — run `sf org display -o <alias> --json`. Capture `accessToken` and `instanceUrl`. If EPERM error, shell is sandboxed — re-run with full permissions.

3. **Look up or create the CRMA app** — run `scripts/create_app.js <alias> <appName>`. The script lists existing folders and only creates if missing. Do NOT include `assetIcon`.

### Phase 2 — Recipe Authoring

4. **Read the R3 node schema** — load `references/r3-node-schema.md` before writing any recipe JSON. Every node shape, critical field rule, and formula gotcha is documented there.

5. **Author the recipe JSON** — the `.wdpr` file contains only the `recipeDefinition` object (the `nodes` map, `runMode`, and `ui` section). Do NOT wrap it in an API envelope (`fileFormat`, `label`, `name`, `recipe: {}`) — the deploy script reads this file directly as the `recipeDefinition` body; wrapping it causes the wrong JSON structure to be POSTed at `?format=R3`, leaving `targetDataflowId` null. Save to `force-app/main/default/wave/<RecipeName>.wdpr`. Key rules:
   - `runMode` must be `"full"` for generated recipes — NOT `"R3"` (which is only used as a query param on the API endpoint). Use `"incremental"` instead of `"full"` for large objects where reprocessing the entire source on every run is too slow; use `"streaming"` for near-real-time pipelines. `"full"` is the safe default for new recipes.
   - Use `sources` (array), never `source` (singular)
   - One field per formula node — chain them in sequence
   - Use `expressionType: "SQL"` and `type: "NUMBER"` or `type: "TEXT"` on formula fields
   - For text date dimensions use `date_format(field, 'yyyy')` or `date_format(field, 'MM/yyyy')`
   - Formula node action is `"formula"` — NOT `"computeExpression"`, `"augmentColumns"`, or `"transform"`. Fields array key is `"fields"` (NOT `"columns"`). Expression key is `"formulaExpression"` (NOT `"expression"`). Do NOT use backtick quotes around field names in expressions.
   - Insert an `EXTRACT0` (`extractGrains`) node between the last formula node and aggregate
   - Use the Designer-native `ui` section format — read `references/ui-section-template.md`

   **CRITICAL — top-level `.wdpr` file structure.** `nodes` is a ROOT-LEVEL object with UPPERCASE string keys. Do NOT put nodes inside `ui`. Do NOT use an array for `ui.nodes`. The file has exactly three top-level keys: `runMode`, `nodes`, `ui`. See `examples/wdpr-skeleton.wdpr` for a minimal 5-node skeleton (load → formula → extractGrains → aggregate → save).

   See the wrong-variant reference table in `references/r3-node-schema.md → "Common wrong variants"` for the full list of correct vs incorrect field names per node type.

6. **Write SFDX metadata wrappers** — every `.wdpr` file MUST be accompanied by a `.wdpr-meta.xml` in the same directory. These are always created as a pair — outputting the recipe JSON without its metadata wrapper is incomplete. Use the template at `assets/wdpr-meta-template.xml`. Required fields: `<application>`, `<masterLabel>`, `<targetDatasetAlias>`, `<dataflow>` (set to the same value as `<targetDatasetAlias>`). Do NOT add `<description>`, `<label>`, `<accessType>`, `<shareType>`, or `<format>` — each triggers a deploy failure. Similarly, every `.wapp` requires a `.wapp-meta.xml`.

7. **Deploy recipe via REST** — run `scripts/deploy_and_run_recipe.js <alias> <recipeFile.wdpr> <appName> <recipeName>`. This script: looks up folder id → POSTs or PATCHes recipe at `?format=R3` → asserts `targetDataflowId` returned → POSTs to `/wave/dataflowjobs` → polls until terminal.

8. **Verify recipe ran** — terminal statuses: `Success`, `Failure`, `Warning`, `Cancelled`. On `Failure`, run `scripts/check_connector_error.sh <alias> <connectorId>` — exits 0 for `System` errors (safe to retry), exits 1 for `User`/`Limit` errors (do not retry; fix config first). If retries persist on a `System` error, run `POST /wave/dataConnectors/{id}/ingest` to force a connector refresh.

### Phase 3 — Dataset Validation

9. **Upload synthetic data** — run `scripts/gen_synthetic_dataset.js` (schema-driven, reads live XMD) then `scripts/upload_dataset.js`. Read `references/external-data-upload.md` for InsightsExternalData rules.

10. **Verify with SAQL** — run `scripts/verify_synthetic_dataset.js`. A 200 on `Action=Process` only means ingestion was queued — wait for `Status=Completed`, then verify with a count query.

### Phase 4 — Dashboard Authoring

11. **Read dashboard rules** — load `references/dashboard-authoring.md` before writing any `.wdash`. Covers the two-step deploy+PATCH workflow, accepted widget parameters per type, and the SAQL re-encoding trap.

12. **Build minimal `.wdash`** — use `assets/dashboard-template.json` as the starting structure. Keep widget parameters minimal at deploy time (see `references/dashboard-authoring.md → "Deploy-time rules"`). Deploy with `sf project deploy start`. When a listselector must drive another step's SAQL (not a global facet), put a `{{column(step.selection, ["Field"]).asEquality("TargetField")}}` binding in that step's query and set `broadcastFacet`/`useGlobal` to `false` on both steps — see `references/dashboard-authoring.md → "Query bindings"`.

13. **Apply styling via PATCH** — after deploy, `PATCH /wave/dashboards/{id}` with enriched state. **Always `decodeAll` every `state.steps[*].query` immediately after GET, before any mutation + PATCH.** This is the #1 silent failure mode: the API HTML-encodes SAQL on write (`"` → `&quot;`). GET → PATCH without decoding encodes again (`&amp;quot;`, then `&amp;amp;quot;`) and every widget renders Error 119. The helper is in `references/dashboard-authoring.md`. Use `scripts/patch_t_oppo_view.js` as the canonical GET → decodeAll → merge → PATCH template.

14. **Verify all steps render** — before running, edit the `DASH_ID` and `DS` constants at the top of `scripts/verify_dashboard_steps.js` to the deployed dashboard's 18-char ID and the dataset's current ID/versionId. Then run `scripts/verify_dashboard_steps.js <alias>`. For each step: GET stored SAQL → decode → swap dataset name for `id/currentVersionId` → POST to `/wave/query`. Confirm 200 + rows. **Do not mark done until user confirms widgets render in the browser.**

### Phase 5 — Dataset Hygiene

15. **Find unused fields** — run `scripts/find_unused_dataset_fields.js <alias> <DatasetName>`. Read `references/dataset-hygiene.md` for caveats (aggregateflex steps, multi-dataset SAQL, archived apps).

---

## Rules / Constraints

| Constraint | Rationale |
|-----------|-----------|
| Every `.wdpr` MUST be paired with a `.wdpr-meta.xml` in the same directory | Metadata wrapper is required for SFDX deploy; recipe JSON alone is an incomplete artifact |
| Always POST recipes at `?format=R3` with `recipeDefinition` in JSON body | Multipart upload creates recipe but never compiles it — `targetDataflowId` stays null |
| PATCH recipe with `?format=R3` JSON body only; never multipart PATCH | Multipart PATCH updates raw file but destroys compiled state → "tableModelInfo is null" |
| On `tableModelInfo is null`: DELETE then re-POST | Only re-POST triggers server-side compilation |
| Use `targetDataflowId` (02K...) on `/wave/dataflowjobs`, never recipe id (05v...) | `/wave/dataflowjobs` only accepts the dataflow id |
| One field per formula node | REST API accepts multiple but Recipe Designer breaks with "Can't Load the Recipe" |
| Use `column` not `col` in gridLayouts widget entries | `col` triggers `Unrecognized field "col"` on deploy |
| `widgetStyle.borderRadius` must be integer (e.g. `8`), not CSS string | String value rejected at PATCH |
| Use name-based dataset load in stored SAQL, not id/version | id/version load requires a `datasets` binding the PATCH input rep rejects |
| Always decode SAQL before PATCH — use `decodeAll` | GET returns HTML-encoded SAQL; re-encoding on every PATCH accumulates → `&amp;amp;quot;` |
| `valuestable` widget rejects all styling at PATCH — use `chart` with `visualizationType: "flatTable"` | chart widget accepts the full rich-styling param set |
| `POST /wave/dashboards` only creates retired classic dashboards | Use Metadata API deploy for modern grid dashboards |
| KPI total requires `group q by all` before `foreach` | Without it, `foreach` acts as a window function returning one row per source row |

---

## Gotchas

| Issue | Resolution |
|-------|------------|
| Recipe sits in `New` status, `targetDataflowId` null | Re-create via `POST /wave/recipes?format=R3` with `recipeDefinition` in JSON body |
| Formula type `"TEXT"` but expression returns number | Use `type: "NUMBER"` and `expressionType: "SQL"` — other type strings silently normalize to TEXT |
| Aggregate fails: `Can't find field _Year / _Month` | Auto-derived date helpers don't exist mid-pipeline; derive explicitly via `date_format` formula node |
| `400 errorCode 276` on POST recipe | Name already in use — PATCH the existing recipe instead |
| All widgets show Error after PATCH | SAQL re-encoding — run `decodeAll` on every step query before PATCH |
| `listselector` list text invisible on dark bg | Set `filterStyle.valueColor` — it defaults to dark; always set a contrasting color |
| `date_format(CloseDate, 'MMM yyyy')` produces numeric month | Use `'MM/yyyy'` for text dimensions — `MMM` silently returns integer in recipe formula context |

---

## Output Expectations

- `force-app/main/default/wave/<RecipeName>.wdpr` — Wave Recipe JSON (R3 format)
- `force-app/main/default/wave/<AppName>.wapp-meta.xml` — app metadata wrapper
- `force-app/main/default/wave/<RecipeName>.wdpr-meta.xml` — recipe metadata wrapper
- `force-app/main/default/wave/<DashboardName>.wdash` — dashboard state JSON
- `force-app/main/default/wave/<DashboardName>.wdash-meta.xml` — dashboard metadata wrapper

---

## Reusable Scripts

All scripts accept org alias as first positional arg. Read `references/scripts-reference.md` for full descriptions and usage.

| Script | Purpose |
|--------|---------|
| `scripts/create_app.js` | Idempotently create a CRMA app folder |
| `scripts/deploy_and_run_recipe.js` | Create + compile + run recipe end-to-end |
| `scripts/probe_recipe.js` | Fetch recipe compile status + `targetDataflowId` |
| `scripts/fetch_dataset_xmd.js` | Dump dataset XMD (dimensions/measures/dates) |
| `scripts/gen_synthetic_dataset.js` | Schema-driven synthetic data generator |
| `scripts/upload_dataset.js` | Upload CSV via InsightsExternalData API |
| `scripts/verify_synthetic_dataset.js` | Post-upload SAQL sanity checks |
| `scripts/find_unused_dataset_fields.js` | List XMD fields not referenced in any dashboard SAQL |
| `scripts/verify_dashboard_steps.js` | POST each step's SAQL to `/wave/query` and confirm rows |
| `scripts/patch_t_oppo_view.js` | Full-cycle PATCH template with dark theme and `decodeAll` |
| `scripts/check_connector_error.sh` | Check connector `errorCategory`; exits 0=System (retryable), 1=User/Limit (do not retry) |

---

## Cross-Skill Integration

| Need | Delegate to |
|------|-------------|
| Deploying Wave metadata via SFDX project deploy | Use standard `sf project deploy` — no skill needed |
| LWC components that consume Wave datasets | Use an appropriate LWC skill |

---

## Reference File Index

| File | When to read |
|------|-------------|
| `references/method-decision-tree.md` | Phase 1 — before choosing API path |
| `references/r3-node-schema.md` | Phase 2 — before writing any recipe node |
| `references/ui-section-template.md` | Phase 2 — when building the Designer-native `ui` section |
| `assets/wapp-meta-template.xml` | Phase 2 — when creating `.wapp-meta.xml` |
| `assets/wdpr-meta-template.xml` | Phase 2 — when creating `.wdpr-meta.xml` |
| `references/external-data-upload.md` | Phase 3 — InsightsExternalData rules and common errors |
| `references/dashboard-authoring.md` | Phase 4 — full dashboard deploy+PATCH rules and re-encoding trap |
| `assets/wdash-meta-template.xml` | Phase 4 — when creating `.wdash-meta.xml` |
| `assets/dashboard-template.json` | Phase 4 — minimal deploy-valid `.wdash` starting structure |
| `references/dataset-hygiene.md` | Phase 5 — unused field detection and SAQL re-encoding audit |
| `references/scripts-reference.md` | Any phase — full script descriptions and usage |
| `examples/wdpr-skeleton.wdpr` | Phase 2 — minimal 5-node skeleton (load → formula → extractGrains → aggregate → save) |
| `examples/opportunity-revenue-recipe.wdpr` | Phase 2 — fully annotated example recipe with all node types |
| `examples/pipeline-by-industry-quarter.wdpr` | Phase 2 — kitchen-sink join + formula chain + extractGrains + case/coalesce/quarter |
| `examples/industry-binding-dashboard.wdash` | Phase 4 — listselector driving a SAQL filter via `column().asEquality()` |

# Scripts Reference

All scripts accept org alias as the first positional arg and read `accessToken` + `instanceUrl` from `sf org display -o <alias> --json`.

| Script | Purpose | Usage |
|--------|---------|-------|
| `scripts/create_app.js` | Idempotently create a CRMA app (folder). Lists existing folders first; only creates if missing. Do NOT include `assetIcon`. | `node scripts/create_app.js <alias> <appName>` |
| `scripts/deploy_and_run_recipe.js` | Create + compile + run a recipe end-to-end. POSTs or PATCHes via `findExistingRecipe` upsert logic. Polls until terminal. | `node scripts/deploy_and_run_recipe.js <alias> <recipeFile.wdpr> <appName> <recipeName>` |
| `scripts/probe_recipe.js` | Fetch a recipe with `?format=R3` and print compile status + `targetDataflowId`. | `node scripts/probe_recipe.js <alias> <recipeId>` |
| `scripts/fetch_dataset_xmd.js` | Look up a dataset by name and dump its current-version XMD (dimensions / measures / dates). Use before generating synthetic data so the schema matches. | `node scripts/fetch_dataset_xmd.js <alias> <datasetName>` |
| `scripts/gen_synthetic_dataset.js` | Schema-driven synthetic data generator. Reads live XMD, classifies each column by name pattern (`*Id`, `*Industry`, `*Year`, `*Amount`), renames dotted fields to underscored, writes CSV + Wave-compatible `metadata.json`. Default target: `<source>_Synthetic`. | `node scripts/gen_synthetic_dataset.js <alias> <sourceDatasetName>` |
| `scripts/upload_dataset.js` | Upload a CSV to a new or existing dataset via InsightsExternalData API. Polls until ingestion is terminal. | `node scripts/upload_dataset.js <alias> <csvPath> <metadataJsonPath> <datasetAlias> <folderId>` |
| `scripts/verify_synthetic_dataset.js` | Post-upload SAQL sanity checks: row count, sum/min/max, edge-case counts, group-by-dimension breakdowns. | `node scripts/verify_synthetic_dataset.js <alias> <datasetId> <versionId>` |
| `scripts/find_unused_dataset_fields.js` | Given a dataset name, list every XMD field that no dashboard SAQL references. | `node scripts/find_unused_dataset_fields.js <alias> <datasetName>` |
| `scripts/verify_dashboard_steps.js` | For each step in a deployed dashboard, GET stored SAQL, decode HTML entities, swap dataset name for `id/version`, POST to `/wave/query`. Prints HTTP status + row count per step. Update `DASH_ID` and `DS` constants at the top before running. | `node scripts/verify_dashboard_steps.js <alias>` |
| `scripts/patch_t_oppo_view.js` | Full-cycle PATCH template: GET state → `decodeAll` every step query → merge dark theme → PATCH. Use as the canonical pattern for future dashboard PATCH scripts. | `node scripts/patch_t_oppo_view.js <alias>` |
| `scripts/check_connector_error.sh` | GET `/wave/dataConnectors/{id}`, parse `errorCategory`, exit 0 if `System` (safe to retry), exit 1 if `User`/`Limit`/unknown (do not retry — fix config first). | `bash scripts/check_connector_error.sh <alias> <connectorId>` |

# Method Decision Tree

| Goal | Use | Why |
|------|-----|-----|
| Create a `WaveApplication` (app/folder) | Analytics REST `POST /wave/folders` | SFDX metadata deploy for WaveApplication is finicky and almost always fails; REST works in one call |
| Create a `WaveRecipe` that compiles and runs | Analytics REST `POST /wave/recipes?format=R3` with `recipeDefinition` in JSON body | Multipart upload creates the recipe but leaves it in `New` status with no `targetDataflowId` — it can never run |
| Run a recipe ("Run Now") | Analytics REST `POST /wave/dataflowjobs` with `{ dataflowId: targetDataflowId, command: "start" }` | `dataflowId` is the recipe's `targetDataflowId` (02K...), never the recipe id (05v...) |
| Upload CSV into a new or existing dataset | InsightsExternalData sObject API (header → parts → `Action=Process` → poll) | Only supported no-UI path; `sf data tree import` and generic bulk APIs don't produce Wave datasets |
| Call REST from a script | `curl` via `execSync` with `-s -w '\nHTTP_STATUS:%{http_code}'` (no `-f`) | `-f` swallows the response body on non-2xx; the status-suffix pattern surfaces the full error message |
| Bypass OAuth scopes for quick REST call | Apex `Http` callout via `sf apex run` using `UserInfo.getSessionId()` | Internal session bypasses External Client App scope restrictions — for diagnosis only |
| Deploy a modern grid dashboard | Metadata API: `sf project deploy start` for `.wdash` + `.wdash-meta.xml` | `POST /wave/dashboards` only creates retired classic dashboards (errorCode 264) |
| Enrich dashboard styling after deploy | `PATCH /wave/dashboards/{id}` with `{ state: <enriched state> }` | Deploy input rep is minimal; styling fields (`gridLayouts[].style`, `widgetStyle`) are only accepted at PATCH time |

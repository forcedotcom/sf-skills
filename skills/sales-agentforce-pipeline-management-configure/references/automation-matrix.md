# Automation Matrix — what Pipeline Management setup can/can't do via CLI

Which configuration steps are CLI-automatable (and how) versus UI-only. `scripts/setup-all.sh`
performs every CLI-automatable row in the correct dependency order; the UI-only rows are the
handful of steps a human must finish in Setup.

| Category | CLI-Automatable | UI-Only |
|----------|----------------|---------|
| Prerequisites check | ✅ SOQL queries | — |
| Prerequisites enablement | ✅ SOAP Metadata API `updateMetadata` | — |
| Pipeline Management enablement | ✅ SOAP Metadata API v64.0 `updateMetadata` (NOT CLI deploy) | — |
| Enhanced Email enablement | ✅ SOAP Metadata API `EmailAdministrationSettings` | — |
| Pipeline Inspection enablement | ✅ SOAP Metadata API `OpportunitySettings.enablePipelineInspection` | — |
| Permission assignment | ✅ `sf org assign permset/permsetgroup` or Data API | — |
| Flow detection | ✅ `FlowDefinitionView` query by ApiName (`SourceTemplateId` is empty after a Metadata-API deploy) | — |
| Flow clone from template | ✅ Deploy pre-retrieved template (`assets/pipeline_management_flow.flow-meta.xml`) | Fallback: Setup UI 'Save As' if deploy fails |
| Flow activation | ✅ Tooling API `PATCH /tooling/sobjects/Flow/<id>` with `status: Active` | — |
| Agent creation | ✅ Auto-provisioning creates agent user + PSGs on enablement; `sf agent publish authoring-bundle --api-name SalesAgent` creates the `BotDefinition:SalesAgent` (SOAP toggle does NOT create the BotDefinition) | — |
| Agent activation | ✅ `sf agent activate --api-name SalesAgent --version <n>` activates the auto-provisioned (Inactive) BotVersion. A `Bot:SalesAgent` metadata deploy with `<status>Active</status>` **silently fails to activate** — use `sf agent activate`. | — |
| Agent Access (user launch) | ✅ Custom permset + `SetupEntityAccess` + `PermissionSetGroupComponent` (`scripts/define-agent-access.sh`) | — |
| Custom field suggestion (template + flow wiring) | ✅ `scripts/add-field-suggestion.sh` (deploy → retrieve `<versionIdentifier>` → set `<activeVersionIdentifier>` → redeploy → wire flow) | — |
| Stage descriptions | ✅ Tooling API CRUD on `OpptStageDescription` | — |
| Agent Analytics | — | ✅ Setup UI only |

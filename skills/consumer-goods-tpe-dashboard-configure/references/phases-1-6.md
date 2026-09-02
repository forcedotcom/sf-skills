# Phases 1-6 — Prerequisites, Permission Sets, SSOT, Tableau Next, C360 SDM

## Inputs to collect first

Ask before starting. Do not guess.

1. **TPM System Admin username** — must already be authenticated via `sf` CLI. Verify via the sibling script, never `sf org display --json` directly — that command's raw output includes `accessToken` (a live credential), which this script strips before printing:
   ```bash
   node ./scripts/sf-rest.js org-status --target-org <username>
   ```
   Prints `{"username","alias","connectedStatus","orgId"}`. Non-zero exit or `connectedStatus != "Connected"` ⇒ stop, ask the user to run `sf org login web` (or their usual login flow for sf-cli) and re-run this check. Every subsequent command in this skill uses `--target-org <username>`.
2. **Dry-run?** — offer by default. In dry-run, every read/verify/check step still runs; every write/trigger/install step is skipped and recorded as `pending — not run (dry-run)`.

## Namespace detection (run once, before Phase 1)

This package's namespace is never assumed — it will be a managed-package namespace (e.g. `cgcloud`). Detect once and reuse everywhere below:

1. ```bash
   sf package installed list --target-org <username> --json
   ```
   Find the entry with `SubscriberPackageName == "Consumer Goods Cloud"`. If found, `NS` = its `SubscriberPackageNamespace`, and **version-gate immediately** (step 4 below) using that same entry's `SubscriberPackageVersionNumber` before doing anything else in this skill.
2. If package is not found inform the user and stop the process.
3. **Minimum package version gate** (managed-package installs only, i.e. step 1 found a match): this skill's features require **Consumer Goods Cloud package version 262.2 or later**. Parse `SubscriberPackageVersionNumber` (format `<major>.<minor>.<patch>.<build>`, e.g. `"262.2.0.3"`) into `(major, minor)`. Compare against the required `(262, 2)`:
   - `major > 262`, or (`major == 262` and `minor >= 2`) ⇒ pass, continue.
   - Otherwise ⇒ **stop immediately, before Phase 1.** Tell the user plainly, with both numbers spelled out:
     *"This org has Consumer Goods Cloud package version `<installed SubscriberPackageVersionNumber>` installed. TPE dashboard setup requires version `262.2` or later. Please upgrade the package before continuing."*
     Do not proceed into any phase — this is a hard block, not a warning, since the underlying feature genuinely isn't present below that version.

Derive, and reuse for every step below and when delegating to `consumer-goods-rtr-datacloud-export-configure` (Phase 9):

- `NS_SEGMENT` — REST URL path segment: `"<NS>/"` if `NS` is non-empty, else `""`. Insert immediately after `/services/apexrest/`. (Standard Salesforce platform REST APIs under `/services/data/...` — Phases 6 and 11 — are never namespaced; don't apply this there.)
- `NS_APEX` — Apex class-reference prefix: `"<NS>."` if `NS` is non-empty, else `""`. Prefix every reference to a class from this package (`OffPlatformCallout`, `OffPlatformCalloutResponse`, `TransactionHandler`, etc.) in anonymous Apex with this.
- `NS_FIELD` — custom object/field API-name prefix: `"<NS>__"` if `NS` is non-empty, else `""`. Prefix every custom object and custom field API name (standard fields like `Id`/`Name` never take this prefix) in SOQL and `sf data`/`sf sobject` commands with this.

## Phase 1 (Step 1) — Tenant pairing status

This cannot be verified programmatically — there is no supported, non-beta way to check Processing Service tenant pairing status from this skill. Explicitly ask the user for a **yes/no confirmation** (e.g. via the `AskUserQuestion` tool if available, with Yes/No options) — never state it as a plain sentence the user could mistake for informational text: *"Is the Hyperforce Processing Service paired for this org?"* Proceed on yes; on no or no response, stop here and tell the user to complete Processing Service pairing before continuing.

Record the user's confirmation for the final report.

## Phase 2 (Step 2) — Permission set(s) for the TPM Admin persona

"TPM Admin persona" is a role, not an actual permission set name. This cannot be verified programmatically — the exact permission set name/assignment backing that persona is org-specific. Do not query or infer it. Explicitly ask the user for a **yes/no confirmation** (e.g. via the `AskUserQuestion` tool if available, with Yes/No options) — never state it as a plain sentence the user could mistake for informational text: *"Are the permission set(s) required for the TPM Admin persona assigned to <username>?"* Wait for an explicit yes before continuing; on no, stop and tell the user to assign it first.

## Phase 3 (Step 3) — GenieAdmin / TableauEinsteinAdmin permission sets

1. Resolve both permission sets' Labels once, so every user-facing message below shows the Label — never the API `Name`:
   ```bash
   sf data query --target-org <username> \
     --query "SELECT Id, Name, Label FROM PermissionSet WHERE Name IN ('GenieAdmin','TableauEinsteinAdmin')"
   ```
2. Query assignments by `PermissionSet.Name` (still the stable API name, for the `WHERE` filter — only the Label from point 1 goes in front of the user):
   ```bash
   sf data query --target-org <username> \
     --query "SELECT PermissionSet.Name FROM PermissionSetAssignment WHERE Assignee.Username = '<username>' AND PermissionSet.Name IN ('GenieAdmin','TableauEinsteinAdmin')"
   ```
3. Whichever name is absent from the result rows is missing.
4. For each missing one, tell the user its **Label** (from point 1) and ask permission to assign it — e.g. *"User <username> is missing the &lt;Label&gt; permission set. Assign it now?"* Never assign without an explicit go-ahead.
5. On confirmation, use the Id already resolved in point 1 (no need to re-query):
   ```bash
   sf data create record --sobject PermissionSetAssignment \
     --values "AssigneeId=<userId> PermissionSetId=<psId>" --target-org <username>
   ```
   If declined, skip and note it in the report.
6. Record the confirmed-assigned GenieAdmin result — Step 9's delegated skill reuses it (point 1 of its own Procedure) instead of re-querying.

## Phase 4 (Step 4) — SSOT package verification

1. ```bash
   sf package installed list --target-org <username> --json
   ```
2. Check `result[]` for `SubscriberPackageNamespace == "ssot"` (Salesforce Standard Data Model).
3. Missing ⇒ tell the user SSOT isn't installed and ask them to install it manually from Data Cloud setup — this is a manual install, not scriptable. Stop and wait for confirmation, then re-run this check.
4. Present ⇒ record the installed version and continue.

## Phase 5 (Step 5) — Enable Tableau Next

TPE dashboards run on Tableau Next; this must be enabled before C360 SDM (Phase 6) and the TPE Analytics app install (Phase 11).

There is no reliable programmatic way to enable or verify this — it's a manual UI toggle only, and the `TableauIncludedAppManager` permission set check isn't a reliable signal of enablement. Do not query for it, and do not attempt any API call to enable it.

1. **Cannot be verified programmatically.** Explicitly ask the user for a **yes/no confirmation** (e.g. via the `AskUserQuestion` tool if available, with Yes/No options) — never state it as a plain sentence the user could mistake for informational text: *"Is Tableau Next enabled in this org? (Setup → Tableau Next Setup → Enable Tableau Next)"*
2. On yes, record enabled and continue to Phase 6.
3. On no, tell the user to enable it manually at Setup → Tableau Next Setup → Enable Tableau Next, then stop and wait — re-ask the same yes/no question before continuing. Do not proceed on a guess, and do not attempt any automated enablement.

## Phase 6 (Step 6) — C360 SDM verification and installation

1. **Check status** — via `scripts/sf-rest.js`, not `sf api request rest` (beta, no `--json`, can change without notice):
   ```bash
   node ./scripts/sf-rest.js \
     --target-org <username> \
     --path "/services/data/v67.0/app-framework/apps?templateSourceId=sfdc_internal__C360UnifiedSemanticModel"
   ```
   Any returned app with `applicationStatus` of `SuccessStatus` or `SuccessWithWarningsStatus` ⇒ record installed, move on.
2. **Not installed / not successful** — tell the user, ask permission to trigger installation. On confirmation:
   ```bash
   node ./scripts/sf-rest.js \
     --target-org <username> --method POST \
     --path "/services/data/v67.0/app-framework/apps" \
     --body '{"label":"C360_SDM","name":"C360_SDM","description":"C360 Unified Semantic Data Model","templateSourceId":"sfdc_internal__C360UnifiedSemanticModel","templateValues":{"isTest":false},"runtimeMethod":"Async"}'
   ```
   Extract `app.id`, then poll with the shared poller:
   ```bash
   node ./scripts/poll-status.js --target-org <username> \
     --path "/services/data/v67.0/app-framework/apps/<appId>" \
     --status-field applicationStatus \
     --success-values SuccessStatus,SuccessWithWarningsStatus \
     --failure-values FailedStatus \
     --interval-seconds 30 --max-wait-seconds 900
   ```
   Timeout while `InProgressStatus` ⇒ tell the user it's still installing, not a failure — re-run this step later. `FailedStatus` ⇒ stop, report failure, point to `/lightning/setup/C360/home` for a manual retry.
3. Declined ⇒ skip and note it; Phase 7 re-checks and re-prompts rather than assuming.

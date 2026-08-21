# Fulfiller Agent — Workflow Detail

Detailed per-phase command shapes + verdict narrative for `service-itsm-agentic-setup-fulfiller-agent-configure`. Read this alongside the phase headers in `SKILL.md` — the SKILL body holds the load-bearing rules, this file holds the exact commands and branch-by-branch verdict handling.

All calls go through `sf`; substitute `<alias>` with the collected target org and `<developerName>` / `<label>` with the collected values.

## Phase 0 — Establish the per-run scratch directory

Before any phase writes a transient JSON file, invoke `scripts/create-scratch-dir.mjs` — path selection (`${TMPDIR}` → `/tmp` → `${outputDir}` last-resort, keeping transient captures out of the scored `${outputDir}` tree) and the `mkdtemp` call live in the helper so the deterministic logic never sits in prose (A9). Every subsequent phase writes its scratch JSON under `${SCRATCH_DIR}`, so runs never collide and the transient state stays scoped to the run:

```bash
SCRATCH_DIR="$(node "<skill_dir>/scripts/create-scratch-dir.mjs" "${outputDir:-}")"
```

The remaining phases reference `${SCRATCH_DIR}` for every transient path (studio-access, agent-templates, bot-existing, create-bundle-body, publish/activate response captures, report-state, verify). The **durable** run artifact — `${outputDir}/report.md` — is still written to the harness-provided directory.

## Phase 1 — Preflight: confirm Studio access + template provisioning

Capture the Studio-access read and the `agent-templates` read, then let `scripts/classify-preflight.mjs` make the deterministic decisions (never parse `hasAccess` or search `data[]` in prose — A9). The `agent-templates` `agentType` query param is **required** with value `AgentforceEmployeeAgent` (a call without it returns `400 MISSING_ARGUMENT: agentType`):

```bash
sf api request rest "/services/data/v67.0/agentforce-studio/access/Agents" \
  --method GET --target-org <alias> > ${SCRATCH_DIR}/studio-access.json 2>${SCRATCH_DIR}/studio-access.err || true
sf api request rest "/services/data/v67.0/connect/service-itsm/agent-templates?agentType=AgentforceEmployeeAgent" \
  --method GET --target-org <alias> > ${SCRATCH_DIR}/agent-templates.json 2>${SCRATCH_DIR}/agent-templates.err || true
node "<skill_dir>/scripts/classify-preflight.mjs" ${SCRATCH_DIR}/studio-access.json ${SCRATCH_DIR}/agent-templates.json "IT Service Fulfiller"
```

The classifier prints `{ studio:{hasAccess,signal}, template:{present,id,hasAgentScript,botDefinitionId,signal}, verdict, reasons }`:

- `template.hasAgentScript:true` confirms the template carries the Agent Script content Phase 4 needs; capture the raw `agent-templates.json` file path — Phase 4 re-reads it directly (via `scripts/build-create-body.mjs`) rather than the classifier re-emitting the full script content.
- **`template.botDefinitionId` is the PRIMARY Phase-2 idempotency key**, but the Fulfiller is never pre-provisioned and this skill's create path never stamps `templateName`, so its template `botDefinitionId` is `null` on every run — the collected `<developerName>` is the guard that actually fires. Capture `botDefinitionId` for Phase 2 and carry the collected `<developerName>` as the fallback key.
- `verdict:"READY"` ⇒ continue to Phase 2.
- `verdict:"ERROR"` because `studio.signal="ERROR"` (the Studio-access read returned a parseable but non-404 error body — e.g. `401`/`403`) ⇒ do NOT proceed — surface the raw error and stop. This is a failed prerequisite read, not an unwired gate; do not let a present template push the verdict to READY.
- `verdict:"NOT-READY"` because `studio.signal="FAIL"` (`hasAccess=false`) ⇒ do NOT proceed — **offer the prerequisite hand-off**:
  - Present a single `AskUserQuestion`: _"Agentforce for IT Service prerequisites don't look satisfied on this org. Run `service-itsm-agentic-setup-agentforce-studio-validate` to check readiness first?"_ (options: **Yes, check readiness** / **No, stop here**).
  - On **Yes**: delegate to `service-itsm-agentic-setup-agentforce-studio-validate` (read-only readiness check). If it reports NOT-READY, stop and report the missing prerequisite (enablement is a Setup-UI/admin action, outside both skills' write scope). If READY, resume from Phase 2.
  - On **No**: stop and report the missing prerequisite verbatim — no writes.
- `verdict:"NOT-READY"` because `template.signal="FAIL"` (empty/no matching template) ⇒ the org is not ITSM-provisioned; hand off to the readiness check.
- `template.signal="CANNOT-CONFIRM"` because the matched template has no `agentScript` ⇒ the NGA create has nothing to build from; surface this and stop (do not fall back to the legacy `createAgent` route — it is out of scope for this skill).
- `studio.signal="CANNOT-CONFIRM"` (a **confirmed** `404` — the access-check gate isn't wired on the org, expected on scratch orgs) does **not** block: a successful create/publish/activate is authoritative. A later `403 FUNCTIONALITY_NOT_ENABLED` on the write is the same signal as `hasAccess=false` — trigger the same hand-off offer.

## Phase 2 — Idempotency: does the target agent already exist, and is it active?

Idempotency is keyed **PRIMARILY** on the template's `botDefinitionId` (captured in Phase 1) and **FALLS BACK** to the collected `<developerName>`. The `botDefinitionId` is the platform's authoritative link from the `agent-templates` row to the `BotDefinition` it was instantiated into, but it is back-filled **only** for pre-provisioned agents — and the Fulfiller is never pre-provisioned: this skill's create path never stamps `templateName`, so its template `botDefinitionId` is `null` on the first run and every run after. The `DeveloperName`-keyed fallback is therefore the guard that actually catches repeat runs (if the agent already exists under a `DeveloperName` matching the collected `<developerName>`, a name-only miss would let the create fail with `DUPLICATE_VALUE`), so never short-circuit to create when `botDefinitionId` is absent.

- **`template.botDefinitionId` is empty/null** (the normal Fulfiller case) ⇒ fall back to a DeveloperName-keyed read (do **not** short-circuit to create — a self-created agent from a prior run has a null template `botDefinitionId` but still exists). The `BotVersions` subquery is required — omitting it leaves `needsActivation` permanently false and hides the reactivation path:
  ```bash
  sf data query -q "SELECT Id,DeveloperName,MasterLabel,(SELECT Id,Status FROM BotVersions ORDER BY VersionNumber DESC LIMIT 1) FROM BotDefinition WHERE DeveloperName='<developerName>'" \
    --target-org <alias> --json > ${SCRATCH_DIR}/bot-existing.json 2>${SCRATCH_DIR}/bot-existing.err || true
  node "<skill_dir>/scripts/classify-agent-existence.mjs" ${SCRATCH_DIR}/bot-existing.json "" "<developerName>"
  ```
- **`template.botDefinitionId` is present** (a pre-provisioned instantiation, if any — never the normal Fulfiller case) ⇒ read the `BotDefinition` by Id **`OR` by the collected `<developerName>`** in one query, INCLUDING its latest version's status, then classify. The `OR DeveloperName=` clause is what catches a **dangling** template→BotDefinition link — a `botDefinitionId` whose target row was since deleted: the by-Id half returns nothing, but the live same-name agent still surfaces, so the classifier falls back to it (`matchedBy:"developerName"`) instead of concluding `exists:false` and letting the create collide with `DUPLICATE_VALUE`:
  ```bash
  sf data query -q "SELECT Id,DeveloperName,MasterLabel,(SELECT Id,Status FROM BotVersions ORDER BY VersionNumber DESC LIMIT 1) FROM BotDefinition WHERE Id='<botDefinitionId>' OR DeveloperName='<developerName>'" \
    --target-org <alias> --json > ${SCRATCH_DIR}/bot-existing.json 2>${SCRATCH_DIR}/bot-existing.err || true
  node "<skill_dir>/scripts/classify-agent-existence.mjs" ${SCRATCH_DIR}/bot-existing.json "<botDefinitionId>" "<developerName>"
  ```

The classifier prints `{ exists, count, matchedBy, agentId, botDefinitionId, developerName, latestVersionId, latestVersionStatus, needsActivation }` — `matchedBy` is `"botDefinitionId"` | `"developerName"` | `null`, and `developerName` is the ACTUAL live agent's DeveloperName read from the record, surface it in the report rather than the collected guess:

- `exists:false` ⇒ proceed to Phase 3 (create path).
- `exists:true` and `needsActivation:false` (latest version `Active`) ⇒ **ALREADY-CREATED** — skip the write, fall through to Phase 7 verification.
- `exists:true` and `needsActivation:true` (latest version `Inactive`) ⇒ do **not** create a duplicate agent — go to Phase 2b to offer activating the existing version instead.
- A non-zero exit (exit 3) means the query itself failed — surface the raw CLI error, do not assume the agent is absent.

## Phase 2b — Reactivation offer (existing agent found inactive)

Present the discovery to the user via `AskUserQuestion`: _"A Fulfiller agent named `<developerName>` already exists but its latest version is Inactive. Activate the existing version instead of creating a new agent?"_ (options: **Yes, activate the existing version** / **No, stop here**).

- On **Yes**: activate the captured `latestVersionId` directly — no create/publish needed since the `BotDefinition`/`BotVersion` already exist:
  ```bash
  sf api request rest "/services/data/v67.0/connect/bot-versions/<latestVersionId>/activation" \
    --method POST --body '{"status":"Active"}' \
    --target-org <alias> > ${SCRATCH_DIR}/activate-existing.json 2>${SCRATCH_DIR}/activate-existing.err || true
  ```
  On success, skip Phases 3–6 entirely (no create/publish/confirm-to-write for a fresh agent) and go straight to Phase 7 to verify. Report the aggregate verdict as **ACTIVATED** in Phase 8, not CREATED.
- On **No**: stop and report the current state (agent exists, latest version Inactive) without any writes.

## Phase 3 — Confirm-to-Write Checkpoint (REQUIRED, create path only)

**Before raising the confirmation gate**, if `${outputDir}` was provided, render the report file via `scripts/render-report.mjs` with `verdict:"PENDING CONFIRMATION"` so it exists even if the harness parks at the question. Skip this write for interactive runs. Report-state JSON shape + checkpoint policy live in `references/report-format.md`.

```bash
node "<skill_dir>/scripts/render-report.mjs" ${SCRATCH_DIR}/report-state.json "${outputDir}/report.md"
```

THEN **present the exact create request** (developerName + label, NGA-native from the Fulfiller template's Agent Script) and require an explicit "yes" via `AskUserQuestion`. **Proceed to Phase 4 ONLY on an explicit "yes".** On "no", stop and — if `${outputDir}` was provided — re-render with `verdict:"DECLINED"` and a one-line `reason`. Never fabricate a partial "create-only" outcome.

## Phase 4 — Create the NGA bundle

Build the `createBundleWithVersion` request body with the helper — it re-reads the Phase-1 `agent-templates.json`, extracts the matched template's `agentScript`, fully HTML-decodes it, and substitutes its internal `config.developer_name` / `config.agent_label` with the **collected** `<developerName>` / `<label>` (so the bundle's outer `apiName` and the script's internal identity match), keeping the large script content and free-text quotes out of an inline shell string:

```bash
node "<skill_dir>/scripts/build-create-body.mjs" ${SCRATCH_DIR}/agent-templates.json "IT Service Fulfiller" "<developerName>" "<label>" ${SCRATCH_DIR}/create-bundle-body.json
sf api request rest "/services/data/v67.0/nextgen-authoring/bundles" \
  --method POST \
  --body @${SCRATCH_DIR}/create-bundle-body.json \
  --target-org <alias> > ${SCRATCH_DIR}/create-bundle.json 2>${SCRATCH_DIR}/create-bundle.err || true
```

On success, the `POST /nextgen-authoring/bundles` response is a bundle-version detail: `{ apiName, label, bundleId, id, versionStatus:"DRAFT", assets:[...], ... }`. **Capture `id` — that is the `bundleVersionId` used in Phases 5 and 6, not `bundleId`.**

- `403 FUNCTIONALITY_NOT_ENABLED` / `404` → trigger the Phase-1 prerequisite hand-off offer (the NGA authoring namespace isn't provisioned on the org).
- A build-script exit 3 (template or `agentScript` not found in `${SCRATCH_DIR}/agent-templates.json`) → surface the script's stderr verbatim and stop; do not retry with a hand-typed template id.

## Phase 5 — Publish the bundle version

Publish the captured `bundleVersionId` — empty `--body '{}'` required (the CLI rejects a POST with no `--body`):

```bash
sf api request rest "/services/data/v67.0/nextgen-authoring/bundle-versions/<bundleVersionId>/publish" \
  --method POST --body '{}' \
  --target-org <alias> > ${SCRATCH_DIR}/publish-bundle.json 2>${SCRATCH_DIR}/publish-bundle.err || true
```

On success: `{ lastPublishedOn, publishedBotId, publishedBotVersionId }`. This is the call that creates the underlying `BotDefinition`/`BotVersion`. An error here means the DRAFT version failed platform-side validation — surface it verbatim; do not attempt to activate an unpublished version.

## Phase 6 — Activate the bundle version

Activate the same `bundleVersionId`:

```bash
sf api request rest "/services/data/v67.0/nextgen-authoring/bundle-versions/<bundleVersionId>/activate" \
  --method POST --body '{}' \
  --target-org <alias> > ${SCRATCH_DIR}/activate-bundle.json 2>${SCRATCH_DIR}/activate-bundle.err || true
```

Success returns an **empty body** — do not treat empty stdout as a failure; check the CLI exit code and fall through to Phase 7 to confirm via `BotDefinition`/`BotVersion` state instead of parsing a response payload.

## Phase 7 — Verify the agent is live

Read `BotDefinition` by Id (with `BotVersions` subquery, same shape as Phase 2) and classify. The verify `<verifyId>` is the create path's **`publishedBotId`** (captured from the Phase-5 publish response) or, on the ALREADY-CREATED / reactivation path, the **live matched Id the Phase-2 classifier returned** (its `botDefinitionId`/`agentId` output — the actual `BotDefinition.Id` of the matched record), **not** the Phase-1 template `botDefinitionId` (which is always `null` for the Fulfiller, so on any existing-agent hit using it would run the verify as `WHERE Id=''` and falsely report failure after a successful skip/activation). Never the collected `<developerName>`:

```bash
sf data query -q "SELECT Id,DeveloperName,MasterLabel,(SELECT Id,Status FROM BotVersions ORDER BY VersionNumber DESC LIMIT 1) FROM BotDefinition WHERE Id='<verifyId>'" \
  --target-org <alias> --json > ${SCRATCH_DIR}/bot-verify.json 2>${SCRATCH_DIR}/bot-verify.err || true
node "<skill_dir>/scripts/classify-agent-existence.mjs" ${SCRATCH_DIR}/bot-verify.json "<verifyId>"
```

Confirm `exists:true` with `count:1`, and — on the create or reactivation path — `latestVersionStatus:"Active"`. `exists:false` after a successful activate ⇒ report the discrepancy verbatim, do not fabricate success. Optionally cross-check `GET /nextgen-authoring/bundles` for an entry with the collected `apiName` and `isLegacy:false` to confirm the agent is NGA-native (no external-link icon in Agentforce Studio).

## Phase 8 — Aggregate verdict

Report CREATED / ALREADY-CREATED / ACTIVATED / FAILED plus the `BotDefinition` Id / bundle `id`. Use **ACTIVATED** when Phase 2b's reactivation path was taken (existing agent found inactive, activated instead of creating new). Emit the final report by re-invoking `scripts/render-report.mjs` — the single source of report text. If `${outputDir}` was provided, overwrite `${outputDir}/report.md`; otherwise emit the helper's stdout as the turn-side report.

```bash
node "<skill_dir>/scripts/render-report.mjs" ${SCRATCH_DIR}/report-state.json "${outputDir}/report.md"
```

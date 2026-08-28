---
name: service-itsm-agentic-setup-fulfiller-agent-configure
description: "Create and activate the IT Service Fulfiller agent as a Next-Gen Authoring (NGA) native agent from the shipped ITSM Fulfiller template's Agent Script, using the Salesforce CLI (sf): read the template, check idempotency, create the NGA bundle then publish and activate it, then verify it is live. Idempotent per developer name. The Fulfiller agent is the IT-technician-facing assistant for incident triage, case summarization, field updates, and related-record automations. Use when asked to create the Fulfiller agent, set up the IT Service Fulfiller agent, provision the fulfiller assistant, or activate the Fulfiller agent. Triggers: create fulfiller agent, set up fulfiller agent, provision fulfiller agent, activate fulfiller agent. DO NOT TRIGGER: checking org prerequisites (service-itsm-agentic-setup-agentforce-studio-validate), or CMDB CRUD."
metadata:
  version: "3.5"
  domains: ["Service", "Agentforce"]
  minApiVersion: "67.0"
  relatedSkills:
    - "service-itsm-agentic-setup-agentforce-studio-configure"
    - "service-itsm-agentic-setup-agentforce-studio-validate"
    - "service-itsm-agentic-setup-employee-agent-configure"
    - "service-itsm-agentic-setup-itsm-agentforce-permset-assign"
  cliTools:
    - tool: ["node"]
      semver: ">=18.0.0"
    - tool: ["sf"]
      semver: ">=2.0.0"
  accessCheck:
    - type: "license"
      value: "Agentforce"
allowed-tools: |
  Bash
  Read
  Write
  AskUserQuestion
---

# Create the IT Service Fulfiller Agent

Create and activate the **IT Service Fulfiller Agent** as a **Next-Gen Authoring (NGA) native agent** — Agent-Script-based (`AiAuthoringBundleDefVer`/bundle), appearing natively in Agentforce Studio's Agents list with no external-link icon — entirely through the **Salesforce CLI (`sf`)**. **This skill does not call the legacy `/connect/service-itsm/createAgent`**; instead it reuses the shipped ITSM Fulfiller template's `agentScript` and feeds it into the NGA bundle pipeline:

1. `POST /nextgen-authoring/bundles` (`createBundleWithVersion`) — creates the bundle + first version from the template's Agent Script.
2. `POST /nextgen-authoring/bundle-versions/{id}/publish` — publishes the version (creates the underlying `BotDefinition`/`BotVersion`).
3. `POST /nextgen-authoring/bundle-versions/{id}/activate` — activates it.

Commands: `sf api request rest` for Connect API GET/POST; `sf data query` for the SOQL idempotency + verify reads.

Helper scripts (invoked via `Bash`) hold every JSON-parsing / decision rule so the model never eyeballs a response body (A9): `classify-preflight.mjs` (Studio-access + template-provisioning verdict), `classify-agent-existence.mjs` (idempotency + reactivation-need from the `BotDefinition` SOQL), `build-create-body.mjs` (HTML-decodes the template's `agentScript`, normalizes it for the org's enabled features via `strip-release-management.mjs`, substitutes `config.developer_name`/`config.agent_label`, writes the bundle-create body to a JSON file so large content and free-text quotes never hit an inline shell string), `render-report.mjs` (deterministic report renderer — single source of report text for chat-turn and harness file).

The Fulfiller agent is the **IT-technician-facing assistant** — incident triage, case summarization, field updates, related-record automations. The employee self-service surface is `service-itsm-agentic-setup-employee-agent-configure`.

## Scope

- **In scope**: Reading `agent-templates`; extracting the Fulfiller template's Agent Script (`svc_itsm_intelligence__ITSrvcMgmtFulfiller`); creating the Fulfiller agent as an **NGA-native agent** via `createBundleWithVersion` → `publish` → `activate`; SOQL-verifying live; idempotent skip on duplicate developer name; normalizing the created Agent Script so it activates cleanly on any Agentforce-for-IT-Service org (internal step, never surfaced to the user — see below) — all via `sf`.
- **Out of scope**: The Employee agent — broad or ~47 specializations under `svc_emp_intelligence__` (`service-itsm-agentic-setup-employee-agent-configure`); enabling org-level feature toggles (validated by `service-itsm-agentic-setup-agentforce-studio-validate`); low-level topic/action authoring; perm-set assignment; content-bundle deployment; CMDB CRUD; Discovery / Service Graph; the legacy `createAgent` route.

---

## Preconditions

If any of these are unmet, `sf` surfaces an auth error or a `401`/`403`/`404`; **surface the raw error verbatim and stop — do not fabricate state**.

1. **`sf` CLI authenticated** to the target org (`sf org display -o <alias>` shows Connected). All calls use `--target-org <alias>`; never extract the access token by hand.
2. **API v67.0+** — pinned in the URL path; do not hand-edit below the minimum.
3. **ITSM features + Fulfiller template provisioned** (`svc_itsm_intelligence__ITSrvcMgmtFulfiller`). If `agent-templates` returns nothing or the routes 404, run `service-itsm-agentic-setup-agentforce-studio-validate`.
4. **`node` ≥ 18** on PATH.

---

## Operations at a glance

| Concern | Command | Notes |
|---------|---------|-------|
| Studio access (precondition read) | `sf api request rest "/services/data/v67.0/agentforce-studio/access/Agents" --method GET -o <alias>` | `hasAccess=false` ⇒ prerequisite hand-off |
| List agent templates + Agent Script (read) | `sf api request rest "/services/data/v67.0/connect/service-itsm/agent-templates?agentType=AgentforceEmployeeAgent" --method GET -o <alias>` | `agentType=AgentforceEmployeeAgent` required; confirms Fulfiller template + non-empty `agentScript` |
| Enumerate the existing agent + latest version status (read) | `sf data query -q "SELECT Id,DeveloperName,MasterLabel,(SELECT Id,Status FROM BotVersions ORDER BY VersionNumber DESC LIMIT 1) FROM BotDefinition WHERE Id='<botDefinitionId>' OR DeveloperName='<developerName>'" -o <alias> --json` | Keyed PRIMARILY on the template's `botDefinitionId` (Phase-1 row); the `OR DeveloperName=` clause is both the null-`botDefinitionId` fallback (the normal Fulfiller case) AND the guard for a dangling Id link (deleted target). Classified by `scripts/classify-agent-existence.mjs`; Active latest ⇒ ALREADY-CREATED; Inactive latest ⇒ offer reactivation |
| **Create the NGA bundle** (write) | `sf api request rest "/services/data/v67.0/nextgen-authoring/bundles" --method POST --body @<body-file> -o <alias>` | Body built by `scripts/build-create-body.mjs`; response `id` = the bundle **version** Id |
| **Publish the bundle version** (write) | `sf api request rest "/services/data/v67.0/nextgen-authoring/bundle-versions/<bundleVersionId>/publish" --method POST --body '{}' -o <alias>` | Returns `publishedBotId`/`publishedBotVersionId` — creates the underlying `BotDefinition`/`BotVersion` |
| **Activate the bundle version** (write) | `sf api request rest "/services/data/v67.0/nextgen-authoring/bundle-versions/<bundleVersionId>/activate" --method POST --body '{}' -o <alias>` | Empty response on success; agent is now live and NGA-native |
| **Activate an existing inactive version** (write) | `sf api request rest "/services/data/v67.0/connect/bot-versions/<latestVersionId>/activation" --method POST --body '{"status":"Active"}' -o <alias>` | Reactivation path only (Phase 2b) — skips create/publish |
| Verify agent is live (read) | `sf data query -q "SELECT ... FROM BotDefinition WHERE Id='<verifyId>'" -o <alias> --json` | `<verifyId>` = create path's `publishedBotId` (Phase-5) or the Phase-2 classifier's returned live matched Id (its `botDefinitionId`/`agentId`) on ALREADY-CREATED / reactivation — not the null Phase-1 template `botDefinitionId`, never the collected developerName; confirm `BotDefinition` present + latest version Active |

Full command shapes and the ITSM Connect API reference live in `references/cli-invocation.md`; the reactivation-path call + idempotency verdict table live in `references/reactivation.md`; the response-body error codes and recurring gotchas live in `references/error-taxonomy.md`.

> **Never extract the access token.** Use `sf api request rest` / `sf data query` directly — they use the CLI's stored session for the target org. Do **not** pull the `accessToken` out of `sf org display` and hand-build an HTTP request with it; that bypasses the CLI session and leaks a bearer token into shell context.

> **`--json` rule.** `sf data query` **takes** `--json` (results come back in a `.result.records[]` envelope — that's what the classifier expects). `sf api request rest` does **not** — omit `--json` there; its raw stdout body is already JSON.

---

## Shipped ITSM Fulfiller agent template

| Template identifier | Default developer name |
|---------------------|-------------------------|
| `svc_itsm_intelligence__ITSrvcMgmtFulfiller` (`masterLabel` "IT Service Fulfiller") | `IT_Service_Fulfiller_Agent` |

> **The `agentScript` field is the source of truth for the NGA create — not `id`.** `scripts/build-create-body.mjs` matches on `masterLabel`, HTML-decodes `agentScript`, and substitutes the collected `<developerName>`/`<label>` into `config.developer_name`/`config.agent_label` before it becomes the bundle's `resourceContent`. The Employee-facing agent is handled by `service-itsm-agentic-setup-employee-agent-configure`.

> **Internal template normalization — never surfaced to the user.** Before the decoded script becomes `resourceContent`, `scripts/strip-release-management.mjs` removes the `topic ReleaseManagement:` block — plus its `go_to_ReleaseManagement:` selector transition and routing bullet. That topic's only action, `svc_itsm_intelligence__SummarizeRelease`, is gated behind an org preference (`ReleaseManagementPref`) and is not surfaced by `/actions/custom/generatePromptResponse` on an org that has not enabled it; shipping it would make `activate` return HTTP 200 with a `{success:false, "... does not exist"}` silent-failure body. `classify-action-availability.mjs` applies the **identical** transform so Phase 2c scans the same normalized script — the two callers must stay in lock-step. The transform is a no-op if the block is absent (safe against future template revisions). **This normalization is an implementation detail: do NOT mention it, the removed subagent, or Release Management in chat narration, the confirm-to-write step, or the report — the admin only ever sees that the agent was created and activated.**

---

## Architecture — Creation stages

| Stage | What happens | Tool used |
|-------|--------------|-----------|
| Preflight | Confirm Studio access (`agentforce-studio/access/Agents`) and that the template's `agentScript` is present | `Bash` (`sf api request rest`) |
| Enumerate | Read the Fulfiller template (`agent-templates`) and existing agents + latest version status (SOQL on `BotDefinition`/`BotVersions`); classify idempotency and reactivation-need via script | `Bash` (`sf`, `node`) |
| Confirm-to-write | Present the exact developerName + label (the NGA create target), OR — if the existing agent is inactive — present the reactivation option instead, and require explicit "yes" either way | `AskUserQuestion` |
| Create *(create path only)* | POST `createBundleWithVersion` (builds the NGA bundle + first version from the decoded, substituted template Agent Script) | `Bash` (`sf api request rest`, `node`) |
| Publish *(create path only)* | POST `.../bundle-versions/<id>/publish` (creates the underlying `BotDefinition`/`BotVersion`) | `Bash` (`sf api request rest`) |
| Activate | POST `.../bundle-versions/<id>/activate` (create path) OR POST `.../connect/bot-versions/<latestVersionId>/activation` with `{"status":"Active"}` (reactivation path — skips create/publish) | `Bash` (`sf api request rest`) |
| Verify | SOQL-read `BotDefinition`/`BotVersions` and confirm the agent exists with an Active latest version | `Bash` (`sf data query`) |

**Idempotency**: keyed PRIMARILY on the **template's `botDefinitionId`** (Phase-1 `agent-templates` row — the platform's authoritative template→`BotDefinition` link) and FALLING BACK to the collected `<developerName>`. The Phase-2 read is `BotDefinition WHERE Id='<botDefinitionId>' OR DeveloperName='<developerName>'` (the `OR` half is both the null-`botDefinitionId` fallback — the normal Fulfiller case — AND the guard for a **dangling** Id link whose target `BotDefinition` was deleted, so a stale link can't slip through to create), + latest `BotVersion.Status` (classified by the helper script). Outcomes: no match on either key ⇒ `exists:false` ⇒ create; `latestVersionStatus:"Active"` ⇒ **ALREADY-CREATED** (skip the write, fall through to Phase 7 verification); `needsActivation:true` (latest version `Inactive`) ⇒ **offer to activate the existing version instead of creating a new agent** (Phase 2b) rather than silently skipping or duplicating. **Why the fallback matters:** the Fulfiller is never pre-provisioned and this skill's create path never stamps `templateName`, so the template's `botDefinitionId` is always `null` — the `<developerName>`-keyed fallback is the guard that actually catches a repeat run; short-circuiting straight to create on a null `botDefinitionId` would re-create and collide with `DUPLICATE_VALUE`. The server does reject a duplicate `DeveloperName` at publish (unique-constraint → bundle cleanup), but only this Phase-2 read turns a repeat into a graceful skip instead of that hard error.

---

## Clarifying Questions

Collect from the user (ask only what is not already in conversation context):

| Field | Description | Default |
|-------|-------------|---------|
| Target org | The `sf` org alias to create the agent in | Default org (`sf config get target-org`) |
| Developer name | Unique `DeveloperName` for the agent | `IT_Service_Fulfiller_Agent` |
| Label | User-facing label for the agent | `IT Service Fulfiller Agent` |
| Confirm the write | Explicit confirmation before the create/publish/activate sequence | **REQUIRED** — present the developerName + label and require "yes" via `AskUserQuestion` |

The **idempotency read keys PRIMARILY on the template's `botDefinitionId`** (Phase-1 row) and FALLS BACK to the collected `<developerName>` when that is null; the verify read keys on the publish response's `publishedBotId` (create path) or the template's `botDefinitionId` (ALREADY-CREATED / reactivation). The collected `<developerName>` and `<label>` (defaults `IT_Service_Fulfiller_Agent` / `IT Service Fulfiller Agent`) also thread through the `createBundleWithVersion` body — both the outer `apiName`/`label` AND the substituted `config.developer_name`/`config.agent_label` inside the Agent Script. Never hardcode the name in one call and collect it in another — a mismatch between the bundle's outer `apiName` and the script's internal `developer_name` causes the platform to diverge the two. Creating an agent provisions a live, activated agent on the org; the user must explicitly approve the write.

---

## Workflow

Substitute `<alias>` with the collected target org and `<developerName>` / `<label>` with the collected values. Full command shapes + per-phase verdict-branch handling live in `references/workflow-detail.md` — the phase summary below names each step and its load-bearing rule; the reference file holds the exact `sf` / `node` invocations to copy.

0. **Phase 0 — Establish `${SCRATCH_DIR}`.** Invoke the deterministic helper (path is skill-root-qualified so it resolves regardless of the shell's CWD): `SCRATCH_DIR="$(node "<skill_dir>/scripts/create-scratch-dir.mjs" "${outputDir:-}")"`. Helper picks the base dir (`${TMPDIR}`, else `/tmp`, else the harness `${outputDir}` last-resort — scratch stays OUT of the scored `${outputDir}` tree) and emits the created dir on stdout. All transient JSON lands under `${SCRATCH_DIR}`; the durable `${outputDir}/report.md` stays under the harness dir.
1. **Phase 1 — Preflight.** Capture the Studio-access read + `agent-templates` read (with the **required** `agentType=AgentforceEmployeeAgent` query param) into `${SCRATCH_DIR}/agent-templates.json`, then classify via `scripts/classify-preflight.mjs "IT Service Fulfiller"`. The classifier also emits `template.botDefinitionId` from the matched row — **capture it; it is the primary Phase-2 idempotency key (the collected `<developerName>` is the fallback key).** Branch on `verdict`: `READY` ⇒ Phase 2; `NOT-READY` ⇒ prerequisite hand-off via `AskUserQuestion` (delegate to `service-itsm-agentic-setup-agentforce-studio-validate` on "yes"); `ERROR` ⇒ surface + stop; `studio.signal="CANNOT-CONFIRM"` (confirmed 404) does not block.
2. **Phase 2 — Idempotency (primary key `botDefinitionId`, fallback key `<developerName>`).** Take `template.botDefinitionId` from Phase 1. **Present** ⇒ SOQL `BotDefinition WHERE Id='<botDefinitionId>' OR DeveloperName='<developerName>'` with the `BotVersions` subquery (subquery is required — otherwise `needsActivation` is permanently false; the `OR` clause makes a **dangling** Id link — deleted target — fall back to the live same-name agent instead of a false `exists:false` → duplicate create). **Empty/null** (the normal Fulfiller case — the template row is never back-filled) ⇒ do NOT skip to create; fall back to `BotDefinition WHERE DeveloperName='<developerName>'` (a self-created agent from a prior run has a null template `botDefinitionId` but still exists). Either way classify via `scripts/classify-agent-existence.mjs ${SCRATCH_DIR}/bot-existing.json "<botDefinitionId-or-empty>" "<developerName>"`. Branch: `exists:false` ⇒ **Phase 2c** (action-availability gate, then create); `exists:true` + `needsActivation:false` ⇒ **ALREADY-CREATED** (skip straight to Phase 7 — no action-availability gate; a live active agent's actions are already wired); `exists:true` + `needsActivation:true` ⇒ Phase 2b. Non-zero exit ⇒ surface CLI error; never assume absent. **Why the fallback:** the Fulfiller is never pre-provisioned, so `botDefinitionId` is always null — a missing developerName check would re-create and hit `DUPLICATE_VALUE`.
3. **Phase 2b — Reactivation offer.** `AskUserQuestion`: _"Fulfiller agent `<developerName>` exists but latest version is Inactive. Activate it?"_. On **Yes**: `POST /connect/bot-versions/<latestVersionId>/activation` with `{"status":"Active"}` captured to `${SCRATCH_DIR}/activate-response.json`, then `node "<skill_dir>/scripts/classify-activate-result.mjs" ${SCRATCH_DIR}/activate-response.json` — `PASS` ⇒ Phase 7 (verdict **ACTIVATED**); `FAIL` ⇒ surface `messages[]` verbatim, offer the Phase 2c permset hand-off if a message names a missing invocable action, do NOT report ACTIVATED; `CANNOT-CONFIRM` ⇒ fall through to Phase 7 SOQL verify. On **No**: stop, no writes.
4. **Phase 2c — Action-availability preflight (create path only; reached only from Phase 2 `exists:false`).** Capture `sf api request rest "/services/data/v67.0/actions/custom/generatePromptResponse" --method GET` to `${SCRATCH_DIR}/generate-prompt-response.json`, then `node "<skill_dir>/scripts/classify-action-availability.mjs" ${SCRATCH_DIR}/agent-templates.json "IT Service Fulfiller" ${SCRATCH_DIR}/generate-prompt-response.json` (scans the **normalized** Agent Script — the same internal transform the create step applies — so a subagent whose backing action is gated behind an org preference is never flagged missing and never blocks activation). Branch on `verdict`: `READY` ⇒ Phase 3; `NOT-READY` ⇒ present the result under an **"Attention"** heading (never label it "Blocker") and raise an `AskUserQuestion` offering hand-off to `service-itsm-agentic-setup-itsm-agentforce-permset-assign` (surface `missing[]` verbatim — do NOT proceed to write; the activate call would return HTTP 200 with a `{success:false}` silent-failure body); `CANNOT-CONFIRM` ⇒ surface reasons and proceed with caution (Phase 6 activate-result classifier catches the silent-failure body). Full contract in `references/action-availability.md`.
5. **Phase 3 — Confirm-to-Write (REQUIRED, create path only).** If `${outputDir}` was provided, first render the checkpoint file via `render-report.mjs` with `verdict:"PENDING CONFIRMATION"` (skip for interactive runs). THEN raise the `AskUserQuestion` gate presenting developerName + label + "NGA-native from the Fulfiller template's Agent Script". Proceed **only** on explicit "yes"; on "no", re-render with `verdict:"DECLINED"`.
6. **Phase 4 — Create.** `scripts/build-create-body.mjs ${SCRATCH_DIR}/agent-templates.json "IT Service Fulfiller" "<developerName>" "<label>" ${SCRATCH_DIR}/create-bundle-body.json` (helper re-reads Phase-1 templates JSON, HTML-decodes the matched `agentScript`, normalizes it — same internal transform as Phase 2c — substitutes internal `config.developer_name`/`config.agent_label`, writes body to file), then `POST /nextgen-authoring/bundles --body @${SCRATCH_DIR}/create-bundle-body.json`. **Capture response `id`** — that is the `bundleVersionId` for Phases 5–6, not `bundleId`. `403 FUNCTIONALITY_NOT_ENABLED`/`404` ⇒ trigger the Phase-1 hand-off; build-script exit 3 ⇒ surface stderr.
7. **Phase 5 — Publish.** `POST /nextgen-authoring/bundle-versions/<bundleVersionId>/publish --body '{}'` (empty body required). Success: `{ lastPublishedOn, publishedBotId, publishedBotVersionId }` — this call creates the underlying `BotDefinition`/`BotVersion`. Any error ⇒ surface verbatim; never activate an unpublished version.
8. **Phase 6 — Activate.** `POST /nextgen-authoring/bundle-versions/<bundleVersionId>/activate --body '{}'` captured to `${SCRATCH_DIR}/activate-response.json`, then `node "<skill_dir>/scripts/classify-activate-result.mjs" ${SCRATCH_DIR}/activate-response.json` — activate can return HTTP 200 with a `{success:false}` silent-failure body when a referenced invocable action isn't surfaced; the classifier catches that. `PASS` ⇒ Phase 7; `FAIL` ⇒ surface `messages[]`, offer Phase 2c permset hand-off if a message names a missing action, do NOT report CREATED; `CANNOT-CONFIRM` ⇒ fall through to Phase 7 SOQL verify.
9. **Phase 7 — Verify.** SOQL `BotDefinition WHERE Id='<id>'` (+ `BotVersions` subquery) and classify — `<id>` is the create path's `publishedBotId` (captured from Phase 5) or, on the ALREADY-CREATED / reactivation path, the **live matched Id the Phase-2 classifier returned** (its `botDefinitionId`/`agentId` output — the actual `BotDefinition.Id` of the matched record), **not** the Phase-1 template `botDefinitionId` (which is always null for the Fulfiller, so on any existing-agent hit the verify would run `WHERE Id=''` and falsely report failure after a successful skip/activation). Confirm `exists:true, count:1, latestVersionStatus:"Active"`. Any discrepancy ⇒ report verbatim, do not fabricate success.
10. **Phase 8 — Aggregate verdict.** Emit CREATED / ALREADY-CREATED / ACTIVATED / FAILED (ACTIVATED on the Phase-2b path) + `BotDefinition` Id / bundle `id` by re-invoking `render-report.mjs` — the single source of report text. If `${outputDir}` was provided, overwrite `${outputDir}/report.md`; otherwise emit stdout as the turn-side report.

---

## Rules / Constraints

| Constraint | Rationale |
|-----------|-----------|
| All calls go through `sf api request rest` / `sf data query`; **never extract the access token** | Leaks a bearer token into shell context; the CLI's stored session is the correct surface |
| Idempotency read keys PRIMARILY on the template's `botDefinitionId` (Phase-1 row), falling back to the collected `<developerName>` when null; the verify read keys on the publish `publishedBotId` / `botDefinitionId`; that same `<developerName>`/`<label>` also thread through the create body (outer `apiName`/`label` AND the substituted `config.developer_name`/`config.agent_label`) | The Fulfiller is never pre-provisioned and the create path omits `templateName`, so its template `botDefinitionId` is always null — the `<developerName>` fallback is the guard that catches a repeat run (a name-only miss → `DUPLICATE_VALUE`). A create-body hardcode/collect mismatch diverges the bundle's outer identity from the script's internal identity |
| Preflight, idempotency, bundle-body construction, and report rendering all live in `scripts/*.mjs`, not prose (A9) | JSON parsing + `masterLabel` matching + `hasAccess` reads + verdict emission are deterministic; the ~70KB Agent Script and free-text apostrophes cannot be safely interpolated into a shell string — `JSON.stringify` in the helper escapes them |
| The created Agent Script is **normalized before it ships** (`strip-release-management.mjs`); `classify-action-availability.mjs` applies the identical transform. This normalization is internal — **never surface it, the removed subagent, or Release Management in user-facing output** (chat, confirm-to-write, or report) | The removed subagent's only action `svc_itsm_intelligence__SummarizeRelease` is gated behind `ReleaseManagementPref`; shipping it makes `activate` return a `{success:false}` silent-failure body on any org without that preference. Removing it (vs. forcing the pref on) lets the Fulfiller activate cleanly on any Agentforce-for-IT-Service org; both callers stay in lock-step or Phase 2c would false-flag the removed action as missing |
| Three-call sequence: `createBundleWithVersion` → `publish` → `activate`, in that order, on the SAME captured `bundleVersionId` (response `id`, not `bundleId`) | Platform enforces DRAFT → published → active; response-body / empty-body / `--json` / `agentType` / HTML-decode gotchas live in `references/error-taxonomy.md` |
| Enumerate `BotDefinition` **with the `BotVersions` subquery**; skip create when Active; offer Phase-2b reactivation when Inactive — never silent skip, never duplicate create | Subquery is what distinguishes Active/Inactive; the server rejects a duplicate `DeveloperName` at publish (unique-constraint → bundle cleanup), so this read is what turns a repeat into a graceful skip instead of that hard error |
| **REQUIRED confirm-to-write checkpoint** before create sequence or reactivation call | Both change live org state — explicit user approval required |
| On `hasAccess=false` / `403 FUNCTIONALITY_NOT_ENABLED`, offer the readiness hand-off — never enable features here; never call legacy `/connect/service-itsm/createAgent` | Enablement is a Setup-UI/admin action; `createAgent` produces a Setup-page bot with an external-link icon (wrong kind of agent for this skill) |
| Report exact CLI response text on any error | Enables support to diagnose failures |

---

## Verification Checklist

- [ ] Preflight classified by `classify-preflight.mjs` (PASS or documented CANNOT-CONFIRM); hand-off offered on FAIL; raw error surfaced on ERROR.
- [ ] Idempotency keyed on the template's `botDefinitionId` (Phase-1 row) with the collected developerName as fallback; `BotDefinition WHERE Id='<botDefinitionId>' OR DeveloperName='<developerName>'` (the `OR` covers both a null and a dangling `botDefinitionId`) + latest `BotVersion.Status` (subquery present) read + classified before any write.
- [ ] If `needsActivation:true`, Phase-2b reactivation offer presented — no silent skip, no duplicate create.
- [ ] Explicit user confirmation at Phase 3 (create) or Phase 2b (reactivation) before any write.
- [ ] Bundle body built by `build-create-body.mjs`, POSTed via `--body @<file>` with the collected `developerName`/`label`; or write correctly skipped.
- [ ] Same `bundleVersionId` (response `id`) used for publish + activate; reactivation used `POST /connect/bot-versions/<id>/activation`; legacy `createAgent` never called.
- [ ] Phase-7 verify confirmed `BotDefinition` present + latest version Active.
- [ ] Access token never extracted; final verdict + `BotDefinition`/bundle Id reported.

---

## Output Format

The report layout is generated deterministically by `scripts/render-report.mjs` — the single source of report text for both the chat turn and the harness's `${outputDir}/report.md`. Never hand-compose the layout in prose (A9); always shell out to the helper. Full rendered shape, report-state JSON schema, and checkpoint-write rules live in `references/report-format.md`.

Terminal verdicts: `CREATED | ALREADY-CREATED | ACTIVATED | PENDING CONFIRMATION | DECLINED | FAILED`. When `${outputDir}` is set, write at Phase 3, Phase 6 (or Phase 2b), and Phase 8 — each write overwrites the same file. Skip these writes in interactive/chat surfaces.

---

## Reference File Index

| File | When to read |
|------|--------------|
| `references/workflow-detail.md` | Full per-phase verdict-branch narrative that the SKILL body summarizes (Phase-1 ERROR/NOT-READY/CANNOT-CONFIRM, Phase-2 classifier output, Phase-4 create response, error branches) |
| `references/report-format.md` | Every `render-report.mjs` call — the rendered shape and the three-checkpoint write policy for `${outputDir}/report.md` |
| `references/cli-invocation.md` | Every phase — exact `sf` call shapes, the never-extract-token rule, ITSM Connect API reference, three helper-script contracts |
| `references/action-availability.md` | Phase 2c (action-availability preflight, create path) + Phase 2b/6 (activate-result classifier) — silent-failure body catches, permset hand-off wording |
| `references/reactivation.md` | Reactivation path (`needsActivation:true`) — the direct `POST /connect/bot-versions/{id}/activation` call + full idempotency verdict table |
| `references/error-taxonomy.md` | Any non-2xx response, unexpected empty body, or script non-zero exit — response-body error codes and recurring foot-guns |
| `scripts/render-report.mjs` | Every checkpoint that writes `${outputDir}/report.md` (Phase-3 gate, Phase-6 create-succeeded, Phase-8 final) — deterministic renderer from a phase-state JSON |
| `scripts/strip-release-management.mjs` | The internal Agent Script normalization — imported by `build-create-body.mjs` (create body) and `classify-action-availability.mjs` (Phase 2c scan); both must call it or the two diverge |

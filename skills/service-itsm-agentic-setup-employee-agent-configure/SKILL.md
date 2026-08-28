---
name: service-itsm-agentic-setup-employee-agent-configure
description: "Create and activate an IT Service Employee agent as a Next-Gen Authoring (NGA) native agent from an ITSM Employee agent template's Agent Script, via the Salesforce CLI (sf): read the template, check idempotency, create the NGA bundle then publish and activate, verify live. Defaults to the broad IT Service Employee template; when the user names a specialized Employee template (Password Manager Assistance, Certificate Management, Onboarding, Hardware Request, and ~47 others catalogued in references/specialized-templates.md — all under the `svc_emp_intelligence__` namespace), pins that one instead. Idempotent per developer name. TRIGGER when the user asks to create/set up/provision/activate the Employee agent, the IT Service Employee agent, or a specialized Employee agent (password manager, certificate, onboarding, hardware request, etc.). DO NOT TRIGGER: prerequisite checks (service-itsm-agentic-setup-agentforce-studio-validate), CMDB CRUD, Fulfiller setup (service-itsm-agentic-setup-fulfiller-agent-configure)."
metadata:
  version: "2.3"
  domains: ["Service", "Agentforce"]
  minApiVersion: "67.0"
  relatedSkills:
    - "service-itsm-agentic-setup-agentforce-studio-configure"
    - "service-itsm-agentic-setup-agentforce-studio-validate"
    - "service-itsm-agentic-setup-fulfiller-agent-configure"
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

# Create an IT Service Employee Agent (broad or specialized)

Create and activate an **IT Service Employee Agent** as a **Next-Gen Authoring (NGA) native agent** — Agent-Script-based (`AiAuthoringBundleDefVer`/bundle), appearing natively in Agentforce Studio's Agents list with no external-link icon — entirely through the **Salesforce CLI (`sf`)**. **This skill does not call the legacy `/connect/service-itsm/createAgent`**; instead it reuses a shipped ITSM Employee template's `agentScript` field and feeds it into the NGA bundle pipeline: `POST /nextgen-authoring/bundles` → `POST /nextgen-authoring/bundle-versions/{id}/publish` → `POST /nextgen-authoring/bundle-versions/{id}/activate`. Commands: `sf api request rest` for Connect API GET/POST; `sf data query` for the SOQL idempotency + verify reads.

`GET /connect/service-itsm/agent-templates?agentType=AgentforceEmployeeAgent` returns the **broad** `IT Service Employee` template plus ~47 **specialized** Employee templates under the `svc_emp_intelligence__` namespace as siblings in `data[]`. Every specialized template ships the same `agentScript` shape with the same `config.developer_name`/`config.agent_label` substitution points, so the same NGA sequence works for any of them — **only the `masterLabel` that Phases 1 and 4 pin against changes.** Full catalog + namespace filter + disambiguation rules live in `references/specialized-templates.md`.

Helper scripts (invoked via `Bash`) hold every JSON-parsing / decision rule so the model never eyeballs a response body (A9): `classify-preflight.mjs`, `classify-agent-existence.mjs`, `build-create-body.mjs` (HTML-decodes + substitutes the template's `agentScript` and writes the body to a JSON file so large content and free-text quotes never hit an inline shell string), `render-report.mjs` (deterministic report renderer).

**Template selection (before Phase 1).** Resolve the `<masterLabel>` this run pins: (1) no specialization named ⇒ pin `IT Service Employee` (id `svc_emp_intelligence__ItEmployeeAssistance`) — the backwards-compatible default; (2) user names a specialization ⇒ keyword-match against `references/specialized-templates.md`, single unambiguous match ⇒ pin that `masterLabel` and derive `developerName` from `id` after `__` (snake-cased); ambiguous ⇒ `AskUserQuestion` keyed on `id`; (3) **filter `data[]` to `svc_emp_intelligence__` only** — `svc_itsm_intelligence__*` (Fulfiller) redirects to `service-itsm-agentic-setup-fulfiller-agent-configure`, other namespaces are out of scope. The resolved `<masterLabel>` is the single knob passed to `classify-preflight.mjs` (Phase 1) and `build-create-body.mjs` (Phase 4).

**Prerequisites.** Creation assumes the org-level Agentforce for IT Service prerequisites are already satisfied (Agentforce Studio access + `service-cloud-requestor-agent` + `service-cloud-it-service-employee-agent`). If Phase 1 detects Studio is not accessible — or if any write returns `403 FUNCTIONALITY_NOT_ENABLED` — this skill **offers** to delegate to `service-itsm-agentic-setup-agentforce-studio-validate` (employee path) then resume; on "no", stops. This skill never enables features itself — enablement is a Setup-UI/admin action.

## Scope

- **In scope**: Reading `agent-templates`; extracting an Employee template's Agent Script (broad default or a user-named specialization from `references/specialized-templates.md` — all under `svc_emp_intelligence__`); creating the Employee agent as an **NGA-native agent** via `createBundleWithVersion` → `publish` → `activate`; SOQL-verifying live; idempotent skip on duplicate developer name — all via `sf`.
- **Out of scope**: The Fulfiller agent (`service-itsm-agentic-setup-fulfiller-agent-configure`); enabling org-level feature toggles (validated by `service-itsm-agentic-setup-agentforce-studio-validate`); low-level topic/action authoring; perm-set assignment; content-bundle deployment; CMDB CRUD; Discovery / Service Graph; the legacy `createAgent` route; any `data[]` entry outside `svc_emp_intelligence__`.

---

## Preconditions

If any of these are unmet, `sf` surfaces an auth error or a `401`/`403`/`404`; **surface the raw error verbatim and stop — do not fabricate state**.

1. **`sf` CLI authenticated** to the target org (`sf org display -o <alias>` shows Connected). All calls use `--target-org <alias>`; never extract the access token by hand.
2. **API v67.0+** — pinned in the URL path; do not hand-edit below the minimum.
3. **ITSM features + templates provisioned** — resolved template must be present. If `agent-templates` returns nothing or the routes 404, run `service-itsm-agentic-setup-agentforce-studio-validate` (agent path `employee`).
4. **`node` ≥ 18** on PATH.

---

## Operations at a glance

| Concern | Command | Notes |
|---------|---------|-------|
| Studio access (precondition read) | `sf api request rest "/services/data/v67.0/agentforce-studio/access/Agents" --method GET -o <alias>` | `hasAccess=false` ⇒ prerequisite hand-off |
| List agent templates + Agent Script (read) | `sf api request rest "/services/data/v67.0/connect/service-itsm/agent-templates?agentType=AgentforceEmployeeAgent" --method GET -o <alias>` | `agentType=AgentforceEmployeeAgent` required; confirms resolved `<masterLabel>` template + non-empty `agentScript` |
| Enumerate existing agent + latest version status (read) | `sf data query -q "SELECT Id,DeveloperName,MasterLabel,(SELECT Id,Status FROM BotVersions ORDER BY VersionNumber DESC LIMIT 1) FROM BotDefinition WHERE Id='<botDefinitionId>' OR DeveloperName='<developerName>'" -o <alias> --json` | Keyed PRIMARILY on the template's `botDefinitionId` (Phase-1 row); the `OR DeveloperName=` clause is both the null-`botDefinitionId` fallback AND the guard for a dangling Id link (deleted target). Classified by `scripts/classify-agent-existence.mjs`; Active latest ⇒ ALREADY-CREATED; Inactive latest ⇒ offer reactivation |
| **Create the NGA bundle** (write) | `sf api request rest "/services/data/v67.0/nextgen-authoring/bundles" --method POST --body @<body-file> -o <alias>` | Body built by `scripts/build-create-body.mjs`; response `id` = the bundle **version** Id |
| **Publish the bundle version** (write) | `sf api request rest "/services/data/v67.0/nextgen-authoring/bundle-versions/<bundleVersionId>/publish" --method POST --body '{}' -o <alias>` | Returns `publishedBotId`/`publishedBotVersionId` — creates the underlying `BotDefinition`/`BotVersion` |
| **Activate the bundle version** (write) | `sf api request rest "/services/data/v67.0/nextgen-authoring/bundle-versions/<bundleVersionId>/activate" --method POST --body '{}' -o <alias>` | Empty response on success; agent is now live and NGA-native |
| **Activate an existing inactive version** (write) | `sf api request rest "/services/data/v67.0/connect/bot-versions/<latestVersionId>/activation" --method POST --body '{"status":"Active"}' -o <alias>` | Reactivation path only (Phase 2b) — skips create/publish |
| Verify agent is live (read) | `sf data query -q "SELECT ... FROM BotDefinition WHERE Id='<verifyId>'" -o <alias> --json` | `<verifyId>` = create path's `publishedBotId` (Phase-5) or the Phase-2 classifier's returned live matched Id (its `botDefinitionId`/`agentId`) on ALREADY-CREATED / reactivation — not the null Phase-1 template `botDefinitionId`, never the collected developerName; confirm `BotDefinition` present + latest version Active |

Full command shapes and the ITSM Connect API reference live in `references/cli-invocation.md`; the reactivation-path call + idempotency verdict table live in `references/reactivation.md`; the response-body error codes and recurring gotchas live in `references/error-taxonomy.md`.

> **Never extract the access token.** Use `sf api request rest` / `sf data query` directly — they use the CLI's stored session for the target org. Do **not** pull the `accessToken` out of `sf org display` and hand-build an HTTP request with it; that bypasses the CLI session and leaks a bearer token into shell context.

> **`--json` rule.** `sf data query` **takes** `--json` (results come back in a `.result.records[]` envelope — that's what the classifier expects). `sf api request rest` does **not** — omit `--json` there; its raw stdout body is already JSON.

---

## Clarifying Questions

Collect from the user (ask only what is not already in conversation context):

| Field | Default |
|-------|---------|
| Target org | Default org (`sf config get target-org`) |
| Template (`masterLabel`) | `IT Service Employee` (broad umbrella, id `svc_emp_intelligence__ItEmployeeAssistance`). If the user hints at a specialization (password manager, certificate, onboarding, hardware request, etc.), resolve via `references/specialized-templates.md`; ambiguous ⇒ `AskUserQuestion` keyed on `id` |
| Developer name | Broad: `IT_Service_Employee_Agent`. Specialized: substring after `__` in the picked `id`, snake-cased (e.g. `PasswordManagerAssistance` → `Password_Manager_Assistance`) |
| Label | Broad: `IT Service Employee Agent`. Specialized: the picked template's `masterLabel` verbatim (e.g. `Password Manager Assistance`) |
| Confirm the write | **REQUIRED** — present resolved template + developerName + label, then require "yes" via `AskUserQuestion` |

The collected `<masterLabel>`, `<developerName>`, `<label>` are threaded through every call — `<masterLabel>` selects the row in `agent-templates.data[]` (which also carries the `botDefinitionId` idempotency key); `<developerName>`/`<label>` are used in the `createBundleWithVersion` body (both outer `apiName`/`label` AND the substituted internal `config.developer_name`/`config.agent_label`). The **idempotency + verify reads key PRIMARILY on the template's `botDefinitionId`** (or, after a fresh create, the publish response's `publishedBotId`) and **fall back to the collected `<developerName>`** when that is null. A hardcode/collect mismatch on the create body diverges the bundle's outer identity from the script's internal identity.

**Idempotency**: keyed PRIMARILY on the **template's `botDefinitionId`** (Phase-1 `agent-templates` row — the platform's authoritative template→`BotDefinition` link) and FALLING BACK to the collected `<developerName>`. The Phase-2 read is `BotDefinition WHERE Id='<botDefinitionId>' OR DeveloperName='<developerName>'` (the `OR` half is both the null-`botDefinitionId` fallback AND the guard for a **dangling** Id link — one whose target `BotDefinition` was deleted — so a stale link can't slip through to create), + latest `BotVersion.Status`. Outcomes: no match on either key ⇒ create; `Active` ⇒ ALREADY-CREATED (skip write); `Inactive` ⇒ Phase-2b reactivation offer. **Why both keys:** the broad agent ships pre-provisioned as `IT_Service_Employee` ≠ the guess `IT_Service_Employee_Agent`, so `botDefinitionId` catches it — but an agent this skill creates never back-fills `botDefinitionId` (the create path omits `templateName`), so its template row stays null and the `developerName` fallback is what catches a repeat run. The server does reject a duplicate `DeveloperName` at publish (unique-constraint → bundle cleanup), but only this read turns a repeat into a graceful skip instead of a `DUPLICATE_VALUE`.

---

## Workflow

Substitute `<alias>` with the collected target org and `<developerName>` / `<label>` with the collected values. Full command shapes + per-phase verdict-branch handling live in `references/workflow-detail.md` — the phase summary below names each step and its load-bearing rule; the reference file holds the exact `sf` / `node` invocations to copy.

0. **Phase 0 — Establish `${SCRATCH_DIR}`.** Before any phase writes a transient JSON file, invoke the deterministic helper (path is skill-root-qualified so it resolves regardless of the shell's CWD): `SCRATCH_DIR="$(node "<skill_dir>/scripts/create-scratch-dir.mjs" "${outputDir:-}")"`. The helper picks the base dir (`${TMPDIR}`, else `/tmp`, else the harness `${outputDir}` last-resort — scratch stays OUT of the scored `${outputDir}` tree) and emits the created dir's absolute path on stdout. Every subsequent phase writes its transient JSON under `${SCRATCH_DIR}`; the durable `${outputDir}/report.md` stays under the harness dir.
1. **Phase 1 — Preflight.** Capture the Studio-access read + `agent-templates` read (with the **required** `agentType=AgentforceEmployeeAgent` query param), then classify via `scripts/classify-preflight.mjs "<masterLabel>"` — pass the resolved `<masterLabel>` (`"IT Service Employee"` for the broad path or the picked specialization's `masterLabel`). The classifier also emits `template.botDefinitionId` from the matched row — **capture it; it is the primary Phase-2 idempotency key (the collected `<developerName>` is the fallback key).** Branch on `verdict`: `READY` ⇒ Phase 2; `NOT-READY` ⇒ prerequisite hand-off via `AskUserQuestion` (delegate to `service-itsm-agentic-setup-agentforce-studio-validate` employee path on "yes"); `ERROR` ⇒ surface + stop; `studio.signal="CANNOT-CONFIRM"` (confirmed 404) does not block.
2. **Phase 2 — Idempotency (primary key `botDefinitionId`, fallback key `<developerName>`).** Take `template.botDefinitionId` from Phase 1. **Present** ⇒ SOQL `BotDefinition WHERE Id='<botDefinitionId>' OR DeveloperName='<developerName>'` (+ `BotVersions` subquery — required, else `needsActivation` is permanently false; the `OR` clause makes a **dangling** Id link — deleted target — fall back to the live same-name agent instead of a false `exists:false` → duplicate create). **Empty/null** ⇒ do NOT skip to create; fall back to `WHERE DeveloperName='<developerName>'` (a self-created agent's template row is never back-filled, so its `botDefinitionId` stays null even though the agent exists). Either way classify via `scripts/classify-agent-existence.mjs ${SCRATCH_DIR}/bot-existing.json "<botDefinitionId-or-empty>" "<developerName>"`. Branch: `exists:false` ⇒ Phase 3 (create); `exists:true` + `needsActivation:false` ⇒ **ALREADY-CREATED** (skip to Phase 7); `exists:true` + `needsActivation:true` ⇒ Phase 2b. Non-zero exit ⇒ surface CLI error; never assume absent. **Why both keys:** `botDefinitionId` catches the pre-provisioned `IT_Service_Employee` (≠ the guess `IT_Service_Employee_Agent`); the `developerName` fallback catches self-created repeats — a miss on both re-creates and hits `DUPLICATE_VALUE`.
3. **Phase 2b — Reactivation offer.** `AskUserQuestion`: _"Employee agent `<developerName>` exists but latest version is Inactive. Activate it?"_. On **Yes**: `POST /connect/bot-versions/<latestVersionId>/activation` with `{"status":"Active"}` — skips Phases 3–6, straight to Phase 7. Aggregate verdict is **ACTIVATED**, not CREATED. On **No**: stop, no writes.
4. **Phase 3 — Confirm-to-Write (REQUIRED, create path only).** If `${outputDir}` was provided, first render the checkpoint file via `render-report.mjs` with `verdict:"PENDING CONFIRMATION"` (skip for interactive runs). THEN raise the `AskUserQuestion` gate presenting developerName + label + "NGA-native from the Employee template's Agent Script". Proceed **only** on explicit "yes"; on "no" (including "hold off on activation" / "not yet" / any decline of the atomic chain), re-render with `verdict:"DECLINED"` and a one-line `reason`.
5. **Phase 4 — Create.** `scripts/build-create-body.mjs ${SCRATCH_DIR}/agent-templates.json "<masterLabel>" "<developerName>" "<label>" ${SCRATCH_DIR}/create-bundle-body.json` (helper re-reads Phase-1 templates JSON, HTML-decodes the matched `agentScript`, substitutes internal `config.developer_name`/`config.agent_label`, writes body to file — pass the same `<masterLabel>` used in Phase 1), then `POST /nextgen-authoring/bundles --body @${SCRATCH_DIR}/create-bundle-body.json`. **Capture response `id`** — that is the `bundleVersionId` for Phases 5–6, not `bundleId`. `403 FUNCTIONALITY_NOT_ENABLED`/`404` ⇒ trigger the Phase-1 hand-off; build-script exit 3 ⇒ surface stderr.
6. **Phase 5 — Publish.** `POST /nextgen-authoring/bundle-versions/<bundleVersionId>/publish --body '{}'` (empty body required). Success: `{ lastPublishedOn, publishedBotId, publishedBotVersionId }` — this call creates the underlying `BotDefinition`/`BotVersion`. Any error ⇒ surface verbatim; never activate an unpublished version.
7. **Phase 6 — Activate.** `POST /nextgen-authoring/bundle-versions/<bundleVersionId>/activate --body '{}'`. Success returns an **empty body** — check exit code, do not parse a payload.
8. **Phase 7 — Verify.** SOQL `BotDefinition WHERE Id='<id>'` (+ `BotVersions` subquery) and classify — `<id>` is the create path's `publishedBotId` (captured from Phase 5) or, on the ALREADY-CREATED / reactivation path, the **live matched Id the Phase-2 classifier returned** (its `botDefinitionId`/`agentId` output — the actual `BotDefinition.Id` of the matched record), **not** the Phase-1 template `botDefinitionId` (which is null on a `matchedBy:"developerName"` fallback hit → the verify would run `WHERE Id=''` and falsely report failure after a successful skip/activation). Confirm `exists:true, count:1, latestVersionStatus:"Active"`. Any discrepancy ⇒ report verbatim, do not fabricate success.
9. **Phase 8 — Aggregate verdict.** Emit CREATED / ALREADY-CREATED / ACTIVATED / FAILED (ACTIVATED on the Phase-2b path) + `BotDefinition` Id / bundle `id` by re-invoking `render-report.mjs` — the single source of report text. If `${outputDir}` was provided, overwrite `${outputDir}/report.md`; otherwise emit stdout as the turn-side report.

---

## Rules / Constraints

| Constraint | Rationale |
|-----------|-----------|
| All calls go through `sf api request rest` / `sf data query`; **never extract the access token** | Leaks a bearer token into shell context; the CLI's stored session is the correct surface |
| Idempotency + verify reads key PRIMARILY on the template's `botDefinitionId` (Phase-1 row) / the publish `publishedBotId`, falling back to the collected `<developerName>`; that same `<developerName>`/`<label>` also thread through the create body (outer `apiName`/`label` AND the substituted `config.developer_name`/`config.agent_label`) | `botDefinitionId` catches the pre-provisioned `IT_Service_Employee` (≠ the guessed `IT_Service_Employee_Agent`, so a name-only read would false-negative → `DUPLICATE_VALUE`); but self-created agents never back-fill it, so the `<developerName>` fallback catches those. A create-body hardcode/collect mismatch diverges the bundle's outer identity from the script's internal identity |
| Preflight, idempotency, bundle-body construction, and report rendering all live in `scripts/*.mjs`, not prose (A9) | JSON parsing + `masterLabel` matching + `hasAccess` reads + verdict emission are deterministic; the ~70KB Agent Script and free-text apostrophes cannot be safely interpolated into a shell string — `JSON.stringify` in the helper escapes them |
| Three-call sequence: `createBundleWithVersion` → `publish` → `activate`, in that order, on the SAME captured `bundleVersionId` (response `id`, not `bundleId`) | Platform enforces DRAFT → published → active; response-body / empty-body / `--json` / `agentType` / HTML-decode gotchas live in `references/error-taxonomy.md` |
| Resolve `<masterLabel>` BEFORE Phase 1; filter `data[]` to `svc_emp_intelligence__` only; disambiguate ambiguous keywords via `AskUserQuestion` keyed on `id` | Label-similar pairs exist; other namespaces belong to other flows (`svc_itsm_intelligence__*` → Fulfiller skill) |
| Enumerate `BotDefinition` **with the `BotVersions` subquery**; skip create when Active; offer Phase-2b reactivation when Inactive — never silent skip, never duplicate create | Subquery is what distinguishes Active/Inactive; the server rejects a duplicate `DeveloperName` at publish (unique-constraint → bundle cleanup) but not the pre-provisioned broad agent, so this read is what turns a repeat into a graceful skip instead of a hard error |
| **REQUIRED confirm-to-write checkpoint** before create sequence or reactivation call | Both change live org state — explicit user approval required |
| On `hasAccess=false` / `403 FUNCTIONALITY_NOT_ENABLED`, offer the readiness hand-off — never enable features here; never call legacy `/connect/service-itsm/createAgent` | Enablement is a Setup-UI/admin action; `createAgent` produces a Setup-page bot with an external-link icon (wrong kind of agent for this skill) |
| Report exact CLI response text on any error | Enables support to diagnose failures |

---

## Verification Checklist

- [ ] Resolved `<masterLabel>` before Phase 1 (broad default or specialization from `references/specialized-templates.md`, `data[]` filtered to `svc_emp_intelligence__`, disambiguated on `id`).
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

Terminal verdicts: `CREATED | ALREADY-CREATED | ACTIVATED | PENDING CONFIRMATION | DECLINED | FAILED`. When `${outputDir}` is set, write at Phase 2, Phase 6 (or Phase 2b), and Phase 8 — each write overwrites the same file. Skip these writes in interactive/chat surfaces.

---

## Reference File Index

- `references/specialized-templates.md` — catalog + namespace filter + `id`-based disambiguation (before Phase 1 on any specialization).
- `references/workflow-detail.md` — exact `sf`/`node` commands + full verdict-branch narrative per phase.
- `references/cli-invocation.md` — command shapes, never-extract-token rule, ITSM Connect API reference, helper-script contracts.
- `references/reactivation.md` — Phase-2b activation call + full idempotency verdict table.
- `references/report-format.md` — rendered shape, phase-state JSON schema, three-checkpoint write policy.
- `references/error-taxonomy.md` — response-body error codes + recurring foot-guns (any non-2xx / empty body / script non-zero exit).

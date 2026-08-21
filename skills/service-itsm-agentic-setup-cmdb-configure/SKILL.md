---
name: service-itsm-agentic-setup-cmdb-configure
description: "Enable the CMDB (Configuration Management Database) feature in Service Cloud ITSM against a production or sandbox org: verify the CMDB org SKU, provision the ITOM tenant, and enable the service-cloud-itsm-cmdb-integration feature that lifts the CMDB access gate. Use when the user asks to enable CMDB, turn on the Configuration Management Database, provision the ITOM tenant, enable the CMDB feature, or fix a CMDB 403 FUNCTIONALITY_NOT_ENABLED error. Triggers on: enable CMDB feature, provision ITOM tenant, turn on CMDB, CMDB not enabled, CMDB 403 error, service-cloud-itsm-cmdb-integration. DO NOT TRIGGER when: the user only wants to assign CMDB permission sets to users, only install a CMDB content bundle, or work with CMDB records directly."
metadata:
  version: "1.0"
  domains: ["Service"]
  minApiVersion: "67.0"
  relatedSkills:
    - "service-itsm-agentic-setup-cmdb-access-assign"
    - "service-itsm-agentic-setup-cmdb-bundle-deploy"
  mcpTools:
    headless-360:
      tools: ["describe", "discover", "dispatch", "dispatch_readonly"]
      semver: ">=1.0.0"
  accessCheck:
    - type: "orgPerm"
      value: "ITSrvcsCnfgMgmnt"
allowed-tools: |
  Read AskUserQuestion
  mcp__headless-360__discover
  mcp__headless-360__describe
  mcp__headless-360__dispatch
  mcp__headless-360__dispatch_readonly
---

# Enable the CMDB Feature (Service Cloud ITSM)

Takes an org from "CMDB off" to "CMDB feature enabled" by walking the first three layers of the
CMDB prerequisite stack in order. Every call runs through the **Salesforce-hosted Headless-360 MCP
server** (server key `headless-360`) via its four meta-tools (`discover`, `describe`,
`dispatch_readonly`, `dispatch`). The org is derived from the OAuth JWT bound to the current MCP
session — the skill never handles an org id, alias, or credentials — so this works identically
against **production** and sandbox with no per-user MCP install.

This skill covers **Layers 0–2**. User access (Layer 3) and content bundles (Layer 4) are separate
skills — see the end of this file.

## The gate this skill lifts

Every CMDB Connect API checks:

```text
orgHasCMDBEnabled = orgHasCMDBPermission (org perm ITSrvcsCnfgMgmnt)  &&  OrgPreferences.CMDBEnabled
```

Until `orgHasCMDBEnabled` is true, CMDB APIs return `403 FUNCTIONALITY_NOT_ENABLED`. `CMDBEnabled`
is NOT a directly settable preference — it is flipped as a side effect of enabling the feature in
Layer 2. This skill's job is to make that gate return true.

> **Necessary but not always sufficient for a given user.** Lifting this org gate does not by itself
> let a *specific* user read CMDB data. Some CMDB reads (e.g. `bundleListView`) also enforce
> **user-level** CMDB access and return the same `403 FUNCTIONALITY_NOT_ENABLED` ("not enabled for
> this user") when the running user holds no CMDB permission sets — even though the feature is
> correctly ENABLED. That is Layer 3 (`service-itsm-agentic-setup-cmdb-access-assign`), not a failure
> of this skill. Confirm this skill's success via the feature `status == ENABLED`, never via a CMDB
> data read.

## Scope

- **In scope**: verifying the CMDB org permission (Layer 0), triggering + polling ITOM tenant
  provisioning (Layer 1), pre-checking + enabling + verifying the CMDB feature (Layer 2).
- **Out of scope**: permission-set assignment (Layer 3 — `service-itsm-agentic-setup-cmdb-access-assign`),
  bundle installation (Layer 4 — `service-itsm-agentic-setup-cmdb-bundle-deploy`), CMDB record CRUD,
  Discovery / Service Graph Connector, identification rules.

## Mechanism

All operations dispatch through **headless-360** MCP tools. Reads go through
`mcp__headless-360__dispatch_readonly`, writes through `mcp__headless-360__dispatch` — both take raw
HTTP: `{"url": "<path>", "method": "GET|POST", "body"?: {...}, "queryParams"?: {...}}` — **not**
`{operation_id, arguments}`. See `references/mcp-invocation.md` for the exact `url` / `method` /
`body` of every call. The four tools:

- `mcp__headless-360__discover` — semantic search over the indexed operation catalog. The Setup/Connect
  routes this skill uses are not always ranked first (or indexed), so a miss does **not** mean the
  route is absent — dispatch the exact path directly (see `references/mcp-invocation.md`).
- `mcp__headless-360__describe` — pull the full input schema and canonical route before any POST.
- `mcp__headless-360__dispatch_readonly` — the dispatcher for every read (GET).
- `mcp__headless-360__dispatch` — the dispatcher for every write (POST/PATCH).

The skill never handles credentials — the org is bound to the current OAuth session. If a `dispatch*`
call returns an auth error, tell the user to re-authenticate the headless-360 MCP connection (and
confirm the session points at the intended org), then stop.

---

## Clarifying questions

Ask only what you cannot infer from conversation:

- **Which org?** Confirm the target org and state plainly that **this org will be modified**
  (tenant provisioning and feature enable are writes). For production, get explicit confirmation.

Do not re-ask for anything the user already provided; pre-populate and note "(from conversation)".

---

## Workflow

All steps are sequential and gated — **do not advance past a failed layer.** Always read before you
write: run the read-only check before every mutation.

### Layer 0 — Verify the CMDB org SKU (read-only, hard gate)

CMDB requires the org permission `ITSrvcsCnfgMgmnt`, granted only by edition / license / org
template. **No API can set it.** The most reliable, universally-available way to verify the org
carries the CMDB SKU is to probe for the CMDB permission-set license — it exists **only** in orgs
provisioned with that license:

```text
dispatch_readonly({ "url": "/services/data/v63.0/query", "method": "GET", "queryParams": { "q": "SELECT Id FROM PermissionSetLicense WHERE DeveloperName = 'ItSrvcCnfgItmReadPsl'" } })
→ totalSize == 1  (licensed)   |   totalSize == 0  (not licensed)
```

- **totalSize == 1** → org is CMDB-licensed; proceed to Layer 1.
- **totalSize == 0** → STOP. Tell the user in plain language (no developer names or API references
  in the message they see):
  > This org isn't licensed for CMDB. CMDB availability is determined by the org's edition or
  > license and can't be turned on through setup — it has to be included when the org is
  > provisioned. Please have the org set up with CMDB (or use one that already has it), then run
  > this again.

The core Connect API `GET /services/data/v63.0/setup/org/permissions/ITSrvcsCnfgMgmnt`
(`{"isPermissionEnabled": true|false}`) is an alternative, but it **404s on some org types
(including orgfarm test orgs)**, so prefer the PSL probe above. See
`references/mcp-invocation.md` for the details. If no probe resolves, report that the org perm could
not be verified and ask the user to confirm the org has CMDB licensed before continuing.

### Layer 1 — Provision the ITOM tenant

CMDB runs on an ITOM tenant that must reach status `PROVISIONED` (asynchronous).

1. **Check current status** (read):
   ```text
   dispatch_readonly({ "url": "/services/data/v67.0/connect/tenantProvisioningStatus", "method": "GET" })
   ```
   Branch on `status`:
   - `PROVISIONED` → already done; skip to Layer 2 (no trigger, no poll).
   - `UNPROVISIONED` → no job has run; go to step 2 and **trigger** it. Do **not** wait or poll on
     this state — waiting never starts provisioning and just burns the budget.
   - `PROVISIONING_IN_PROGRESS` → a job is already running; **skip the trigger** and go straight to
     the poll in step 3.
   - `FAILED` → treat as the FAILED case in step 3 (surface the reason; do not retry via API).
2. **Trigger provisioning** (write) — only when step 1 showed `UNPROVISIONED`. Confirm with the
   user first:
   ```text
   dispatch({ "url": "/services/data/v67.0/connect/tenantProvisioningStatus", "method": "POST" })
   ```
   After the trigger returns, tell the user provisioning has started and **typically takes 2+
   minutes**, so there is nothing to check yet.
3. **Poll** the GET until `status == PROVISIONED`. This is async and reliably takes **2+ minutes**
   (measured completion clusters right around **~2 min 40 s**), so an immediate poll is a guaranteed
   no-op. **Anchor all timing on the response's `triggeredAt`, not on when this run started** — the
   job may have been triggered by an earlier run (the `PROVISIONING_IN_PROGRESS` entry from step 1).
   Parse `triggeredAt` as a UTC epoch and compute `elapsed = max(0, now − triggeredAt)` — clamp to
   `≥ 0` so a clock skew (or a server-vs-agent timezone mismatch) can't yield a negative `elapsed`
   (waits forever) or a false timeout. **If `triggeredAt` is missing or unparseable** (the trigger
   POST response may not have populated it yet, or an in-progress row from an earlier run may omit
   it), fall back to anchoring on this run's start — treat `elapsed = 0` and wait the full ~2-min
   floor, so a branch always fires deterministically. Then:
   - `elapsed < ~2 min` → wait until ~2 min after `triggeredAt` before the first check (skips the
     guaranteed-useless early polls), then poll every 30 seconds.
   - `~2 min ≤ elapsed < 10 min` → **poll immediately** (the initial wait has already passed — do not
     wait a fresh 2 min), then every 30 seconds.
   - `elapsed ≥ 10 min` → **do not start a fresh wait**; treat it as the timeout case below (report
     the last-seen status and let the user decide).

   The overall budget is **10 minutes from `triggeredAt`** (≈16 checks after the ~2-min floor). The
   ~2-min floor is a floor, not an extra delay — it brackets the typical ~2:40 completion within a
   poll or two; do not stretch it longer. Do not poll during the initial wait. Exit the loop as soon
   as:
   - `status == PROVISIONED` → success, advance to Layer 2.
   - `status == FAILED` → stop immediately. Do NOT retry via the API — surface the failure to the
     user in plain language with three things:
     1. **The failure reason, decoded to human-readable text.** Read it from the response body (the
        FAILED payload carries a detail field such as `error` / `failureReason` / `message` —
        unescape any HTML entities like `&lt;`/`&gt;` and strip markup). If the response carries no
        detail, say the tenant provisioning failed without a returned reason.
     2. **A link to the org's tenant provisioning Setup page**, built from the target org's instance
        URL: `<org instance URL>/lightning/setup/CMDBProvisionalSettings/home`.
     3. **Ask the user to open that page and try provisioning manually**, then re-run this skill once
        the tenant shows `PROVISIONED`. Only if the manual retry also fails does it need Salesforce
        support.
   - the 10-minute window elapses → stop, report the last-seen status, and let the user decide
     whether to keep waiting (re-run) or investigate. Never spin past the 10-minute bound.

   **Polling in the background (runtime-permitting).** Provisioning is a multi-minute wait, so the
   user should not have to sit idle. **If — and only if — the executing runtime supports backgrounded
   work** (e.g. an agent runtime that can spawn a detached sub-agent or a scheduled wake-up), delegate
   the wait-then-poll loop to a background task so the user can keep working, and report the outcome
   (`PROVISIONED` / `FAILED` / timed-out) when it finishes. **If the runtime is a single-threaded turn**
   (the ADK / Agentforce / headless-360 production path is single-threaded — a poll loop blocks the
   conversation there), poll **inline** instead. Either way: (a) tell the user up front it takes a few
   minutes, and (b) give a resume path — if they step away and the turn ends, they can re-run this
   skill and Layer 1 picks up from the current status (an already `PROVISIONED` tenant skips straight
   to Layer 2). Never *require* a background primitive the runtime may not have.

### Layer 2 — Enable the CMDB feature (this lifts the 403 gate)

The feature api name is `service-cloud-itsm-cmdb-integration`.

1. **Pre-check status** (read):
   ```text
   dispatch_readonly({ "url": "/services/data/v67.0/connect/setup/discovery/feature/service-cloud-itsm-cmdb-integration/status", "method": "GET" })
   ```
   - `status == ENABLED` → already done; skip to verification.
   - `status == NOT_ENABLED` with `enableBlockedReasons: []` → clear to enable.
   - `enableBlockedReasons` non-empty → STOP and relay each reason to the user in plain language
     (these are prerequisites the org still needs — do not attempt the enable).
2. **Confirm with the user**, then **enable** (write):
   ```text
   dispatch({ "url": "/services/data/v67.0/connect/setup/discovery/feature/service-cloud-itsm-cmdb-integration/enable", "method": "POST", "body": {} })
   → {"success": true}
   ```
3. **Verify** (read) — do NOT trust the POST response alone:
   ```text
   dispatch_readonly({ "url": "/services/data/v67.0/connect/setup/discovery/feature/service-cloud-itsm-cmdb-integration/status", "method": "GET" })
   → expect status == ENABLED
   ```
   **`status == ENABLED` is the definitive — and only — confirmation this skill needs.** Layer 2
   succeeds or fails on this check alone; it does **not** perform any CMDB data read to confirm the
   gate. A CMDB data read (e.g. `bundleListView`) also depends on the *running user's* own CMDB
   access, so it cannot cleanly confirm the org-level enable — see the note under "The gate this
   skill lifts". Once the feature shows `ENABLED`, Layer 2 is done.

---

## Rules / Constraints

| Constraint | Rationale |
|-----------|-----------|
| Verify Layer 0 before anything else | If `ITSrvcsCnfgMgmnt` is off, no later step can succeed — fail fast with a clear message |
| Never try to set `ITSrvcsCnfgMgmnt` via API | There is no setter; it is license/edition/template only |
| Never set `CMDBEnabled` directly (e.g. via `updateDefaultOrgPrefs`) | It is not in any settable-pref allowlist; the server rejects it with 500. It flips only as a side effect of the Layer 2 feature enable |
| Read before every write; verify after every write | Tenant + feature are async/stateful; the POST response can lag the real state |
| Confirm the target org and each write with the user | These are real, hard-to-reverse changes on a live org |
| Do not advance past a failed or blocked layer | Later layers depend on earlier ones and will 403 |
| Anchor poll timing on the response's `triggeredAt` (parse as UTC epoch; elapsed = max(0, now − triggeredAt)), not on this run's start; ~2-min floor before the first check, then every 30s, 10-min total budget from `triggeredAt`. If `triggeredAt` is missing/unparseable, fall back to this run's start (elapsed = 0) | Provisioning reliably takes 2+ min (measured ~2:40), so earlier polls are guaranteed no-ops. A `PROVISIONING_IN_PROGRESS` entry may have been triggered by an earlier run — if already past the ~2-min floor, poll immediately; if already past 10 min, report a timeout rather than waiting a fresh 2 min. Clamp elapsed to ≥ 0 so clock skew / timezone mismatch can't wait forever or false-timeout; the fallback keeps a branch firing when the timestamp is absent. Never spin past the 10-min bound |
| Background the poll loop only where the runtime supports it; else poll inline — never require a background primitive | The user shouldn't sit idle for a multi-minute wait, but the production headless-360/ADK path is a single-threaded turn; a skill that mandates a background poller breaks there. Always give a re-run resume path |
| On `FAILED`, never retry via API — decode the reason, give the Setup URL, ask for a manual retry | The API trigger has already failed; the user can retry from the CMDB provisioning Setup page, which surfaces the real error and any manual remediation |
| Never expose internal jargon to the user | Keep record IDs, org IDs, HTTP status codes (403/500/…), API error codes (`FUNCTIONALITY_NOT_ENABLED`, …), endpoint names (`bundleListView`, `tenantProvisioningStatus`), developer names (`ITSrvcsCnfgMgmnt`, `CMDBEnabled`), and tooling internals (`dispatch`, `headless-360`) out of user-facing output. Translate to plain language; use human-readable names and statuses |

---

## Verification checklist

- [ ] Layer 0: `ITSrvcsCnfgMgmnt` confirmed `true` (or stopped with a clear license message)?
- [ ] Layer 1: tenant `status == PROVISIONED`?
- [ ] Layer 2: pre-check showed `enableBlockedReasons: []` before enabling?
- [ ] Layer 2: enable returned `success: true`?
- [ ] Layer 2: verification GET shows `status == ENABLED`? **(this is the sole success criterion — no CMDB data read is used to confirm)**
- [ ] Confirmed the target org and each write with the user first?

---

## Output expectations

```text
CMDB Feature Enable — Complete (via service-itsm-agentic-setup-cmdb-configure)

Target org: <org>

  CMDB license .................. Present
  ITOM tenant ................... Provisioned
  CMDB feature .................. Enabled

CMDB is now enabled on this org. Next steps:
  • Assign user access  → service-itsm-agentic-setup-cmdb-access-assign
  • Install base bundle  → service-itsm-agentic-setup-cmdb-bundle-deploy
```

Keep internal jargon out of user-facing output (no record IDs, HTTP status codes, error codes,
endpoint or developer names). If any step fails, stop and tell the user — in plain language — which
part of setup didn't succeed and what it means for them, then point to the relevant fix. Translate
any raw error (e.g. a 403 or `FUNCTIONALITY_NOT_ENABLED`) into what it means ("CMDB isn't enabled
yet"), rather than echoing the code.

---

## Common failures (surface these in plain language)

| Symptom | Likely cause | What to tell the user |
|---------|--------------|-----------------------|
| Layer 0 returns `false` | Org lacks the CMDB SKU | License/edition prerequisite — no API can grant it; provision the org with CMDB |
| `403 FUNCTIONALITY_NOT_ENABLED` on CMDB reads **while feature `status != ENABLED`** | Feature not yet enabled (Layer 2 incomplete) | Finish Layer 2; the gate lifts only after the feature is ENABLED |
| `403 FUNCTIONALITY_NOT_ENABLED` on `bundleListView` **while feature `status == ENABLED`** | Feature IS enabled; the running user lacks CMDB permission sets (`bundleListView` also enforces user-level access) | Not a Layer 2 failure — this is Layer 3; run `service-itsm-agentic-setup-cmdb-access-assign` to grant the user CMDB access |
| Feature enable blocked (`enableBlockedReasons` non-empty) | Missing dependency the org still needs | Relay each reason; resolve those first, then retry |
| Tenant stuck `UNPROVISIONED` / `PROVISIONING_IN_PROGRESS` / long-running | Provisioning is async | It typically takes ~2–3 min; keep polling within the 10-min budget or retry the trigger |
| Tenant `FAILED` | Provisioning job failed Salesforce-side | Share the decoded failure reason + the org's `/lightning/setup/CMDBProvisionalSettings/home` link and ask the user to retry provisioning manually there; escalate to Salesforce support only if the manual retry also fails |
| `dispatch*` auth error | headless-360 MCP session not authenticated / token expired | Re-authenticate the headless-360 MCP connection and confirm the session points at the intended org |

---

## Reference file index

| File | When to read |
|------|--------------|
| `references/mcp-invocation.md` | Exact `dispatch*` url/method/body for every Layer 0–2 call, response envelopes, and error table |

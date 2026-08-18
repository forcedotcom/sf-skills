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
   - If `status` is already `PROVISIONED` → skip to Layer 2.
2. **Trigger provisioning** (write) — only if not already provisioned/in-progress. Confirm with the
   user first:
   ```text
   dispatch({ "url": "/services/data/v67.0/connect/tenantProvisioningStatus", "method": "POST" })
   ```
3. **Poll** the GET until `status == PROVISIONED`. This is async and can take several minutes. Poll
   **every 30 seconds for up to 10 minutes** (≈20 attempts). Tell the user provisioning is in
   progress on each poll. Exit the loop as soon as:
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
| Poll tenant provisioning every 30s for up to 10 min (≈20 attempts) | It is async; never spin past the 10-min bound — exit on PROVISIONED/FAILED, else report status and let the user decide |
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
| Tenant stuck `NOT_PROVISIONED` / long-running | Provisioning is async | It can take minutes; keep polling or retry the trigger |
| Tenant `FAILED` | Provisioning job failed Salesforce-side | Share the decoded failure reason + the org's `/lightning/setup/CMDBProvisionalSettings/home` link and ask the user to retry provisioning manually there; escalate to Salesforce support only if the manual retry also fails |
| `dispatch*` auth error | headless-360 MCP session not authenticated / token expired | Re-authenticate the headless-360 MCP connection and confirm the session points at the intended org |

---

## Reference file index

| File | When to read |
|------|--------------|
| `references/mcp-invocation.md` | Exact `dispatch*` url/method/body for every Layer 0–2 call, response envelopes, and error table |

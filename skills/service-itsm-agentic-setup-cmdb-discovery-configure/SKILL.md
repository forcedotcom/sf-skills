---
name: service-itsm-agentic-setup-cmdb-discovery-configure
description: "Enable CMDB Asset Discovery in Service Cloud ITSM against a production or sandbox org by turning on the service-cloud-itsm-discovery-integration feature, then grant a user the Discovery page by assigning the IT Service Discovery Manager permission set and its license — the final CMDB setup layer, run after the CMDB feature, user access, and content bundle are in place. Use when the user asks to enable CMDB discovery, turn on asset discovery, enable service-cloud-itsm-discovery-integration, grant Discovery page access, or assign the Discovery Manager permission set. Triggers on: enable CMDB discovery, turn on asset discovery, service-cloud-itsm-discovery-integration, assign Discovery Manager access, CMDB discovery not enabled. DO NOT TRIGGER when: the user wants to enable the base CMDB feature, provision the ITOM tenant, assign the four CMDB Configuration-Item permission sets, install a CMDB content bundle, or work with CMDB records directly — those are earlier CMDB layers."
metadata:
  version: "1.0"
  minApiVersion: "67.0"
  relatedSkills:
    - "service-itsm-agentic-setup-cmdb-access-assign"
    - "service-itsm-agentic-setup-cmdb-bundle-deploy"
    - "service-itsm-agentic-setup-cmdb-configure"
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

# Enable CMDB Asset Discovery (Service Cloud ITSM)

Turns on **Asset Discovery** for CMDB by enabling the `service-cloud-itsm-discovery-integration`
feature, then grants a user access to the **Discovery page** by assigning the **IT Service Discovery
Manager** permission set (and its permission-set license). This is the **final layer** of CMDB setup —
it runs only after the base CMDB feature is enabled, users have CMDB access, and the CMDB Foundation
content bundle is installed. Every call runs through the **Salesforce-hosted Headless-360 MCP server**
(server key `headless-360`) via its four meta-tools (`discover`, `describe`, `dispatch_readonly`,
`dispatch`). The org is derived from the OAuth JWT bound to the current MCP session — the skill never
handles an org id, alias, or credentials — so this works identically against **production** and sandbox
with no per-user MCP install.

This skill covers the **Discovery layer only** — enabling the feature *and* granting Discovery page
access to a user. The earlier CMDB layers are separate skills — see the end of this file.

## Where this sits in the CMDB stack

CMDB is enabled in ordered layers, each gated on the prior one:

```text
Layer 0  Org SKU / license      Org perm ITSrvcsCnfgMgmnt (verify only — no API can set it).
Layer 1  Tenant provisioning    ITOM tenant must reach status PROVISIONED (async).
Layer 2  CMDB feature           Enable service-cloud-itsm-cmdb-integration (lifts the 403 gate).
Layer 3  User access            Assign the PSL + CMDB permission sets to the user(s).
Layer 4  Content bundle         Install the CMDB Foundation (base) content bundle.
Layer 5  Asset Discovery        Enable service-cloud-itsm-discovery-integration + assign the
                                IT Service Discovery Manager permission set  ← THIS SKILL
```

Discovery is enabled **last**: it builds on the base CMDB feature and depends on the earlier layers
being complete. The pre-check step below (`enableBlockedReasons`) is the authoritative signal that
the prerequisites are met — if the base CMDB feature is not yet enabled, discovery cannot be enabled
and the org reports a blocking reason rather than turning it on.

> **Enabling the feature lifts the org-level gate; the Discovery permission set gives a user the
> Discovery page.** This skill does **both**: it turns Discovery on for the org (Step 2) and then
> assigns the target user the license-backed **`ItSrvcDscvrMgrPermissionSet`** ("IT Service Discovery
> Manager", backed by PSL **`ItSrvcDscvrMgrPsl`**) so they can actually open and use the Discovery
> page (Steps 4–7). That permission set is **distinct** from the four Configuration-Item permission
> sets (Reader / Owner / Type Reader / Type Manager) that `service-itsm-agentic-setup-cmdb-access-assign`
> assigns for CMDB *data* — a user holding only those will **not** have Discovery page access. The
> assignment step is idempotent: if the user already holds the Discovery permission set and its license,
> it is skipped and reported as already-done.

## Scope

- **In scope**: pre-checking, enabling, and verifying the `service-cloud-itsm-discovery-integration`
  feature; and — as a follow-up — assigning the **IT Service Discovery Manager** permission set (and its
  permission-set license) to the target user so they can access the Discovery page.
- **Out of scope**: enabling the base CMDB feature / provisioning the tenant (Layer 2 —
  `service-itsm-agentic-setup-cmdb-configure`), assigning the four Configuration-Item permission sets
  for CMDB *data* access (Layer 3 — `service-itsm-agentic-setup-cmdb-access-assign`), bundle
  installation (Layer 4 — `service-itsm-agentic-setup-cmdb-bundle-deploy`), CMDB record CRUD, Service
  Graph Connector configuration, identification rules, creating or editing permission sets.

## Mechanism

All operations dispatch through **headless-360** MCP tools. Reads go through
`mcp__headless-360__dispatch_readonly`, writes through `mcp__headless-360__dispatch` — both take raw
HTTP: `{"url": "<path>", "method": "GET|POST", "body"?: {...}, "queryParams"?: {...}}` — **not**
`{operation_id, arguments}`. See `references/mcp-invocation.md` for the exact `url` / `method` /
`body` of every call. The four tools:

- `mcp__headless-360__discover` — semantic search over the indexed operation catalog. The Setup/Connect
  routes and the `/query` / `/sobjects/...` REST routes this skill uses are not always ranked first (or
  indexed), so a miss does **not** mean the route is absent — dispatch the exact path directly (see
  `references/mcp-invocation.md`).
- `mcp__headless-360__describe` — pull the full input schema and canonical route before any POST.
- `mcp__headless-360__dispatch_readonly` — the dispatcher for every read (GET).
- `mcp__headless-360__dispatch` — the dispatcher for every write (POST/PATCH).

The skill never handles credentials — the org is bound to the current OAuth session. If a `dispatch*`
call returns an auth error, tell the user to re-authenticate the headless-360 MCP connection (and
confirm the session points at the intended org), then stop.

## The Discovery permission set

| Role | Permission set (`Name`) | Backing PSL (`DeveloperName`) | Grants |
|------|-------------------------|-------------------------------|--------|
| Discovery Manager | `ItSrvcDscvrMgrPermissionSet` | `ItSrvcDscvrMgrPsl` | Open and use the Discovery page |

Resolve the permission set's `Id` and its `LicenseId` at runtime (Step 5) rather than hardcoding IDs —
IDs differ per org.

---

## Clarifying questions

Ask only what you cannot infer from conversation:

- **Which org?** Confirm the target org and state plainly that **this org will be modified** (enabling
  the discovery feature is a write). For production, get explicit confirmation.
- **Which user gets Discovery page access?** The user to assign the IT Service Discovery Manager role.
  If the request is "enable discovery for me" / "set up discovery", default to the **current (running)
  user**. Accept a username/email for someone else.

Do not re-ask for anything the user already provided; pre-populate and note "(from conversation)".

---

## Workflow

All steps are sequential and gated — **do not advance past a failed check.** Always read before you
write: run the read-only pre-check before the enable, and the assignment checks before the assign.

### Step 1 — Pre-check discovery feature status (read)

The feature api name is `service-cloud-itsm-discovery-integration`.

```text
dispatch_readonly({ "url": "/services/data/v67.0/connect/setup/discovery/feature/service-cloud-itsm-discovery-integration/status", "method": "GET" })
```

- `status == ENABLED` → feature already on; skip to verification (Step 3), then proceed to the access
  follow-up (Steps 4–7).
- `status == NOT_ENABLED` with `enableBlockedReasons: []` → clear to enable (Step 2).
- `enableBlockedReasons` non-empty → **STOP** and relay each reason to the user in plain language.
  These are prerequisites the org still needs — most commonly the base CMDB feature is not yet
  enabled. Point the user to the earlier CMDB setup skills (see "Common failures") and do **not**
  attempt the enable.
- `403 FUNCTIONALITY_NOT_ENABLED` on this GET → the base CMDB gate itself is still closed; the org
  needs `service-itsm-agentic-setup-cmdb-configure` first. Stop and route the user there.

### Step 2 — Enable Asset Discovery (write — confirm with the user first)

Skip this step if Step 1 already reported `ENABLED`.

```text
dispatch({ "url": "/services/data/v67.0/connect/setup/discovery/feature/service-cloud-itsm-discovery-integration/enable", "method": "POST", "body": {} })
→ {"success": true}
```

### Step 3 — Verify the feature (read — do NOT trust the POST response alone)

```text
dispatch_readonly({ "url": "/services/data/v67.0/connect/setup/discovery/feature/service-cloud-itsm-discovery-integration/status", "method": "GET" })
→ expect status == ENABLED
```

**`status == ENABLED` is the definitive confirmation that the feature is on.** Once confirmed, continue
to the access follow-up below — the feature being on does not by itself give any user the Discovery page.

### Step 4 — Resolve the target user (read)

**For "the current user" / "me" / "set up discovery"** (do NOT use `USER_ID()` — Apex-only, rejected by
the REST query API; do NOT rely on `/chatter/users/me` or `/connect/user-profiles/me` — they `403` when
Chatter/Communities are off). Read the API root and parse the identity URL:

```text
dispatch_readonly({ "url": "/services/data/v67.0/", "method": "GET" })
```

The response `identity` field is a URL ending in `/<orgId>/<userId>` (the user Id is the last path
segment and starts with `005`). Use that Id directly, or confirm it with a `User` query.

**For a named user** (username / email supplied):

```text
dispatch_readonly({ "url": "/services/data/v67.0/query", "method": "GET", "queryParams": { "q": "SELECT Id, Username, Name, IsActive FROM User WHERE Username = '<username>'" } })
```

- Exactly one active user → capture the `Id`.
- Zero results → STOP; ask the user to confirm the username.
- More than one → STOP; list the candidates (Name + Username) and ask which one.

### Step 5 — Resolve the Discovery permission set + check existing assignment (read — idempotency)

Resolve the permission set and its backing license:

```text
dispatch_readonly({ "url": "/services/data/v67.0/query", "method": "GET", "queryParams": { "q": "SELECT Id, Name, LicenseId FROM PermissionSet WHERE Name = 'ItSrvcDscvrMgrPermissionSet'" } })
```

Capture `Id` (the permission set) and `LicenseId` (the PSL to assign). `totalSize == 0` means the org
is not licensed for Discovery — stop and report. Then check whether the user already has both:

```text
dispatch_readonly({ "url": "/services/data/v67.0/query", "method": "GET", "queryParams": { "q": "SELECT Id FROM PermissionSetAssignment WHERE AssigneeId = '<userId>' AND PermissionSetId = '<psId>'" } })
dispatch_readonly({ "url": "/services/data/v67.0/query", "method": "GET", "queryParams": { "q": "SELECT Id FROM PermissionSetLicenseAssign WHERE AssigneeId = '<userId>' AND PermissionSetLicenseId = '<pslId>'" } })
```

If both already exist, the role is **already assigned** — skip Step 6 and record it as already-done.

### Step 6 — Assign the license, then the permission set (write — confirm first)

Skip whatever Step 5 shows already assigned. Assign the PSL **first**, then the permission set:

```text
dispatch({ "url": "/services/data/v67.0/sobjects/PermissionSetLicenseAssign", "method": "POST", "body": { "AssigneeId": "<userId>", "PermissionSetLicenseId": "<pslId>" } })
dispatch({ "url": "/services/data/v67.0/sobjects/PermissionSetAssignment", "method": "POST", "body": { "AssigneeId": "<userId>", "PermissionSetId": "<psId>" } })
```

- `201` → assigned.
- `400 DUPLICATE_VALUE` → the user already had it; treat as success (idempotent), not a failure.
- A license-limit / no-seats error → STOP for the assignment; tell the user the Discovery license has
  no available seats (see `references/mcp-invocation.md` for the seat query). Do not retry.

### Step 7 — Verify the assignment (read — do NOT trust the POST response alone)

Re-run the two Step 5 assignment queries. The user has Discovery page access only when **both** the
`PermissionSetAssignment` and the `PermissionSetLicenseAssign` return `totalSize == 1`.

---

## Rules / Constraints

| Constraint | Rationale |
|-----------|-----------|
| Run only after the base CMDB feature is enabled | Discovery is the final layer and depends on Layers 0–4; the pre-check `enableBlockedReasons` enforces this |
| Read the pre-check before enabling; verify with a read after enabling | The feature is stateful; the POST response can lag the real state |
| Do not attempt the enable when `enableBlockedReasons` is non-empty | Those are unmet prerequisites — relay them and route the user to the earlier CMDB skills |
| Always follow the enable with the Discovery-Manager assignment | The feature being on does not give any user the Discovery page; the permission set is what grants page access |
| Resolve the user to exactly one record before assigning | Assigning to the wrong (or an ambiguous) user is hard to reverse and a security concern |
| Read existing assignments before assigning; assign the PSL before the permission set | The permission set is license-backed and per-user — re-assigning throws `DUPLICATE_VALUE`; the license seat must be held for the assignment to stick |
| Treat `DUPLICATE_VALUE` as success | It means the user already has that access — idempotent, not an error |
| Never create or edit permission sets | This skill only *assigns* the standard Discovery permission set |
| Confirm the target org, user, and each write with the user | These are real, hard-to-reverse changes on a live org |
| Never expose internal jargon to the user | Keep record IDs, org IDs, HTTP status codes (403/500/…), API error codes (`FUNCTIONALITY_NOT_ENABLED`, `DUPLICATE_VALUE`, …), object names (`PermissionSetLicenseAssign`), endpoint names, feature api names (`service-cloud-itsm-discovery-integration`), developer names (`ItSrvcsCnfgMgmnt`, `ItSrvcDscvrMgrPsl`, …), and tooling internals (`dispatch`, `headless-360`) out of user-facing output. Translate to plain language; use human-readable names and statuses |

---

## Verification checklist

- [ ] Step 1: pre-check showed `enableBlockedReasons: []` before enabling (or `status == ENABLED` already)?
- [ ] Step 2: enable returned `success: true` (or skipped because already enabled)?
- [ ] Step 3: verification GET shows `status == ENABLED`?
- [ ] Step 4: target user resolved to exactly one record?
- [ ] Step 5: Discovery permission set + license resolved; existing assignment checked (idempotency)?
- [ ] Step 6: for the target user, both the permission set and its license are assigned (or already were)?
- [ ] Step 7: assignment confirmed by a post-write read (not the POST response alone)?
- [ ] Confirmed the target org, user, and each write with the user first?

---

## Output expectations

```text
CMDB Asset Discovery — Complete (via service-itsm-agentic-setup-cmdb-discovery-configure)

Target org: <org>
User: <name> (<username>)

  Asset Discovery ................... Enabled
  IT Service Discovery Manager ...... Assigned    (or: Already had access)

Asset Discovery is now enabled on this org and the user above can open and use the
Discovery page. This completes CMDB setup — the base feature, user access, content
bundle, and discovery are all in place.

To give additional users the Discovery page, re-run this and name each user (or use
service-itsm-agentic-setup-cmdb-access-assign for the underlying CMDB data roles).
```

Keep internal jargon out of user-facing output (no record IDs, HTTP status codes, error codes, object,
endpoint or developer names) — say "IT Service Discovery Manager access", not the developer name. If any
step fails, stop and tell the user — in plain language — which part didn't succeed and what it means for
them, then point to the relevant fix. Translate any raw error (e.g. a 403 or `FUNCTIONALITY_NOT_ENABLED`)
into what it means ("CMDB isn't fully set up yet"), rather than echoing the code.

---

## Common failures (surface these in plain language)

| Symptom | Likely cause | What to tell the user |
|---------|--------------|-----------------------|
| Pre-check `enableBlockedReasons` non-empty | An earlier CMDB layer is incomplete (most often the base CMDB feature) | Relay each reason; finish CMDB setup first — run `service-itsm-agentic-setup-cmdb-configure` (base feature), then `-access-assign` (user access) and `-bundle-deploy` (content bundle), then retry discovery |
| `403 FUNCTIONALITY_NOT_ENABLED` on the status GET | Base CMDB gate still closed (CMDB feature not enabled) | Not a discovery failure — enable the base CMDB feature first with `service-itsm-agentic-setup-cmdb-configure`, then retry |
| Enable blocked (`enableBlockedReasons` non-empty) after a partial setup | Missing dependency the org still needs | Relay each reason; resolve those prerequisites, then retry |
| Enable returned success but verification GET is not `ENABLED` | State lag or a downstream issue | Re-run the verification GET after a short wait; if it persists, treat it as not enabled and investigate |
| `PermissionSet` query `totalSize == 0` for `ItSrvcDscvrMgrPermissionSet` | Org not licensed for Discovery | Discovery access is not available on this org; confirm it is licensed |
| `400 DUPLICATE_VALUE` on the assignment | User already has Discovery page access | Not an error — report the role as already assigned |
| License-limit / no-seats error on the assignment | Discovery permission-set license seats exhausted | Report seats in use vs available; a seat must free up (or more licenses added) before assigning |
| Discovery is `ENABLED` and the feature turned on, but a user still can't open the Discovery page | The user was never assigned the Discovery permission set (`ItSrvcDscvrMgrPermissionSet` / PSL `ItSrvcDscvrMgrPsl`) | Re-run this skill for that user (Steps 4–7) to grant "IT Service Discovery Manager" access |
| `dispatch*` auth error | headless-360 MCP session not authenticated / token expired | Re-authenticate the headless-360 MCP connection and confirm the session points at the intended org |

---

## Cross-skill integration

| When | Skill |
|------|-------|
| The base CMDB feature is not enabled yet (Discovery pre-check is blocked) | `service-itsm-agentic-setup-cmdb-configure` (Layers 0–2 — enable the base feature first, then return here) |
| A user needs the underlying CMDB **data** roles (Configuration Item Reader / Owner / Type Reader / Type Manager) | `service-itsm-agentic-setup-cmdb-access-assign` (Layer 3 — CMDB data access, distinct from Discovery page access) |

---

## Reference file index

| File | When to read |
|------|--------------|
| `references/mcp-invocation.md` | Exact `dispatch*` url/method/body for the pre-check, enable, verify, user resolution, and Discovery-Manager assignment calls, response envelopes, the license-seat query, and error table |

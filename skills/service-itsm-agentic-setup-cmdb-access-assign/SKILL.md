---
name: service-itsm-agentic-setup-cmdb-access-assign
description: "Grant a specific user access to CMDB (Configuration Management Database) data in Service Cloud ITSM against a production or sandbox org by assigning the license-backed CMDB permission sets (Configuration Item Reader, Owner, Type Reader, Type Manager) and their permission-set licenses. Use when the user asks to give someone CMDB access, assign CMDB permission sets, grant a user the Configuration Item Reader/Owner role, or fix a CMDB 403 FUNCTIONALITY_NOT_ENABLED that a user still hits after the CMDB feature is already enabled. Triggers on: assign CMDB permission set, grant CMDB access, give user Configuration Item access, CMDB access for user, user still gets CMDB 403 after enable. DO NOT TRIGGER when: the user wants to turn on the CMDB feature or provision the ITOM tenant for the whole org (that is the CMDB feature-enable skill), only install a CMDB content bundle, work with CMDB records directly, or assign general (non-CMDB) permission sets to users (use dx-org-permission-set-assign)."
metadata:
  version: "1.0"
  minApiVersion: "67.0"
  relatedSkills:
    - "dx-org-permission-set-assign"
    - "service-itsm-agentic-setup-cmdb-bundle-deploy"
    - "service-itsm-agentic-setup-cmdb-configure"
  mcpTools:
    headless-360:
      tools: ["describe", "discover", "dispatch", "dispatch_readonly"]
      semver: ">=1.0.0"
allowed-tools: |
  Read AskUserQuestion
  mcp__headless-360__discover
  mcp__headless-360__describe
  mcp__headless-360__dispatch
  mcp__headless-360__dispatch_readonly
---

# Assign a User CMDB Access (Service Cloud ITSM)

Grants a **specific user** the ability to read and work with CMDB (Configuration Management Database)
data by assigning the license-backed CMDB permission sets and their permission-set licenses. Every
call runs through the **Salesforce-hosted Headless-360 MCP server** (server key `headless-360`) via its
four meta-tools (`discover`, `describe`, `dispatch_readonly`, `dispatch`). The org is derived from the
OAuth JWT bound to the current MCP session — the skill never handles an org id, alias, or credentials —
so this works identically against **production** and sandbox with no per-user MCP install.

This is **Layer 3** of CMDB setup. It assumes the org-level CMDB gate is already lifted (the feature
is ENABLED) — that is a separate skill (`service-itsm-agentic-setup-cmdb-configure`, Layers 0–2).
This skill grants a *user* access; it does not enable the feature for the org.

## The gap this skill closes

Enabling the CMDB feature lifts the **org-level** gate, but some CMDB reads (e.g. `bundleListView`)
also enforce **user-level** access. A user with no CMDB permission sets still gets
`403 FUNCTIONALITY_NOT_ENABLED` ("not enabled for this user") even when the feature is correctly
ENABLED for the org. This skill assigns that user the CMDB permission sets so those reads succeed.

> **This skill is a no-op if the org feature is not enabled.** User-level access has no effect until
> the org-level CMDB feature is ENABLED. If you find the org gate is still closed, stop and tell the
> user the CMDB feature must be turned on for the org first — see the cross-skill note at the end.

## The four CMDB permission sets

Each is a license-backed Standard permission set; assigning it also requires (and this skill assigns)
its permission-set license (PSL).

| Role | Permission set (`Name`) | Backing PSL (`DeveloperName`) | Grants |
|------|-------------------------|-------------------------------|--------|
| Reader | `ItSrvcCnfgItmReadPermissionSet` | `ItSrvcCnfgItmReadPsl` | Read CMDB configuration items |
| Owner | `ItSrvcCnfgItmOwnerPermissionSet` | `ItSrvcCnfgItmOwnerPsl` | Own / edit configuration items |
| Type Reader | `ItSrvcCnfgItmTypReadPermissionSet` | `ItSrvcCnfgItmTypReadPsl` | Read configuration-item types |
| Type Manager | `ItSrvcCnfgItmTypManagerPermissionSet` | `ItSrvcCnfgItmTypMgrPsl` | Manage configuration-item types |

For read-only CMDB access, **Reader** (+ **Type Reader**) is the minimal set. For users who edit CMDB
records, add **Owner**; for those who manage the type catalog, add **Type Manager**. If the user does
not specify a role, ask (see Clarifying questions) — default to **Reader + Type Reader** for a viewer.

> **Bundle management needs Type Manager.** If the user's goal is to **install or manage CMDB content
> bundles** (or they hit a `403` on a bundle-management read such as `GET /connect/cmdb/bundles/details`),
> the role that clears it is **Type Manager** — a user holding only Reader / Owner / Type Reader still
> gets `403 FUNCTIONALITY_NOT_ENABLED` on bundle operations. Assign **Type Manager** (with its own
> backing PSL, `ItSrvcCnfgItmTypMgrPsl`) for anyone who deploys or manages bundles.

## Scope

- **In scope**: resolving the target user, resolving the requested CMDB permission set(s), checking
  existing assignments, assigning the permission-set license(s) and permission set(s), and verifying.
- **Out of scope**: enabling the CMDB feature / provisioning the ITOM tenant (Layers 0–2 —
  `service-itsm-agentic-setup-cmdb-configure`), installing content bundles, CMDB record CRUD,
  creating custom permission sets, or org-permission/edition changes.

## Mechanism

All operations dispatch through **headless-360** MCP tools. Reads go through
`mcp__headless-360__dispatch_readonly`, writes through `mcp__headless-360__dispatch` — both take raw
HTTP: `{"url": "<path>", "method": "GET|POST", "body"?: {...}, "queryParams"?: {...}}` — **not**
`{operation_id, arguments}`. See `references/mcp-invocation.md` for the exact `url` / `method` / `body`
of every call. The four tools:

- `mcp__headless-360__discover` — semantic search over the indexed operation catalog. The standard
  `/query` and `/sobjects/...` REST routes this skill uses are not always indexed, so a miss does
  **not** mean the route is absent — dispatch the exact path directly (see `references/mcp-invocation.md`).
- `mcp__headless-360__describe` — pull the full input schema and canonical route before any POST.
- `mcp__headless-360__dispatch_readonly` — the dispatcher for every read (GET).
- `mcp__headless-360__dispatch` — the dispatcher for every write (POST/PATCH).

The skill never handles credentials — the org is bound to the current OAuth session. If a `dispatch*`
call returns an auth error, tell the user to re-authenticate the headless-360 MCP connection (and
confirm the session points at the intended org), then stop.

---

## Clarifying questions

Ask only what you cannot infer from conversation:

- **Which user?** The username (or a name/email you can resolve to exactly one user). If the request
  is "give me access" / "for the current user", resolve the running user.
- **Which role(s)?** Reader, Owner, Type Reader, Type Manager — or "read-only access" (→ Reader +
  Type Reader). Default to **Reader + Type Reader** for a viewer if unspecified. If the user
  installs or manages CMDB **content bundles** (or is fixing a bundle-management 403), include
  **Type Manager** — bundle operations 403 without it.
- **Which org?** Confirm the target org and state plainly that **this org will be modified** (assigning
  permission sets is a write). For production, get explicit confirmation.

Do not re-ask for anything the user already provided; pre-populate and note "(from conversation)".

---

## Workflow

Always read before you write: run the read-only checks before any assignment. All assignments are
per-user and idempotent — a duplicate assignment must be treated as already-done, not an error.

### Step 1 — Confirm the org-level CMDB feature is enabled (read-only, prerequisite)

User access is meaningless until the org gate is lifted. Read the feature status:

```text
dispatch_readonly({ "url": "/services/data/v67.0/connect/setup/discovery/feature/service-cloud-itsm-cmdb-integration/status", "method": "GET" })
```

- `status == ENABLED` → proceed.
- `status != ENABLED` (or the call returns `403 FUNCTIONALITY_NOT_ENABLED`) → STOP. Tell the user, in
  plain language, that CMDB has to be turned on for the org before a user can be given access, and
  point them to the CMDB feature-enable skill (see the cross-skill note). Do not assign anything.

### Step 2 — Resolve the target user (read)

**For "the current user" / "me" / "my own user"** (do NOT use `USER_ID()` — it is Apex-only and is
rejected by the REST query API; do NOT rely on `/chatter/users/me` or `/connect/user-profiles/me` —
they return `403 FUNCTIONALITY_NOT_ENABLED` when Chatter/Communities are off). Instead read the API
root and parse the identity URL:

```text
dispatch_readonly({ "url": "/services/data/v67.0/", "method": "GET" })
```

The response `identity` field is a URL ending in `/<orgId>/<userId>` (the user Id is the last path
segment and starts with `005`). Use that Id directly as the target user, or confirm it:

```text
dispatch_readonly({ "url": "/services/data/v67.0/query", "method": "GET", "queryParams": { "q": "SELECT Id, Username, Name, IsActive FROM User WHERE Id = '<userId>'" } })
```

**For a named user** (username / email supplied):

```text
dispatch_readonly({ "url": "/services/data/v67.0/query", "method": "GET", "queryParams": { "q": "SELECT Id, Username, Name, IsActive FROM User WHERE Username = '<username>'" } })
```

- Exactly one active user → capture the `Id`.
- Zero results → STOP; tell the user no matching user was found and ask them to confirm the username.
- More than one → STOP; list the candidates (Name + Username) and ask which one.
- User inactive → warn the user; assignment can still proceed but the access takes effect only when
  the user is active.

### Step 3 — Resolve the requested permission set(s) (read)

For each requested role, resolve the permission set and its backing license:

```text
dispatch_readonly({ "url": "/services/data/v67.0/query", "method": "GET", "queryParams": { "q": "SELECT Id, Name, LicenseId FROM PermissionSet WHERE Name = '<psName>'" } })
```

Use the `Name` values from the table above. Capture each `Id` (the permission set) and `LicenseId`
(the PSL to assign). If a permission set is not found, the org likely is not CMDB-licensed — stop and
report that CMDB does not appear to be set up on this org.

### Step 4 — Check existing assignments (read — idempotency)

For each target user + permission set, check whether the assignment already exists:

```text
dispatch_readonly({ "url": "/services/data/v67.0/query", "method": "GET", "queryParams": { "q": "SELECT Id FROM PermissionSetAssignment WHERE AssigneeId = '<userId>' AND PermissionSetId = '<psId>'" } })
dispatch_readonly({ "url": "/services/data/v67.0/query", "method": "GET", "queryParams": { "q": "SELECT Id FROM PermissionSetLicenseAssign WHERE AssigneeId = '<userId>' AND PermissionSetLicenseId = '<pslId>'" } })
```

If both already exist for a role, that role is **already assigned** — skip its writes and record it as
already-done. Only assign what is missing.

### Step 5 — Assign the permission-set license, then the permission set (write — confirm first)

Confirm the target user, org, and role(s) with the user, then for each missing role assign the PSL
first, then the permission set:

```text
dispatch({ "url": "/services/data/v67.0/sobjects/PermissionSetLicenseAssign", "method": "POST", "body": { "AssigneeId": "<userId>", "PermissionSetLicenseId": "<pslId>" } })

dispatch({ "url": "/services/data/v67.0/sobjects/PermissionSetAssignment", "method": "POST", "body": { "AssigneeId": "<userId>", "PermissionSetId": "<psId>" } })
```

- `201` → assigned.
- `400 DUPLICATE_VALUE` → the user already had it; treat as success (idempotent), not a failure.
- A license-limit error (e.g. `INSUFFICIENT_ACCESS` / no seats) → STOP for that role; tell the user
  the CMDB license has no available seats and how many are in use (see `references/mcp-invocation.md`
  for the seat query). Do not retry.

### Step 6 — Verify (read — do NOT trust the POST response alone)

Re-run the Step 4 queries. Confirm each requested role now has **both** a `PermissionSetAssignment`
and a `PermissionSetLicenseAssign` for the user. Report per-role: assigned / already had it. Only
roles confirmed present in this read count as done.

---

## Rules / Constraints

| Constraint | Rationale |
|-----------|-----------|
| Confirm the org feature is ENABLED before assigning | User access has no effect until the org-level CMDB gate is lifted; assigning first would be a misleading no-op |
| Resolve the user to exactly one record before writing | Assigning to the wrong (or an ambiguous) user is hard to reverse and a security concern |
| Read existing assignments before every assign | Assignment is per-user; re-assigning throws `DUPLICATE_VALUE` — skip what already exists |
| Assign the PSL before the permission set | The permission set is license-backed; the license seat must be held for the assignment to stick |
| Treat `DUPLICATE_VALUE` as success | It means the user already has that access — idempotent, not an error |
| Never create or edit permission sets | This skill only *assigns* the standard CMDB permission sets; authoring perm sets is out of scope |
| Confirm the target org, user, and each write with the user | These are real changes granting a user data access on a live org |
| Never expose internal jargon to the user | Keep record IDs, HTTP status codes (403/400/…), API error codes (`FUNCTIONALITY_NOT_ENABLED`, `DUPLICATE_VALUE`), object names (`PermissionSetLicenseAssign`), developer names (`ItSrvcCnfgItmReadPsl`), and tooling internals (`dispatch`, `headless-360`) out of user-facing output. Use human-readable role names and plain language |

---

## Verification checklist

- [ ] Org CMDB feature confirmed `ENABLED` before any assignment?
- [ ] Target user resolved to exactly one record?
- [ ] Each requested role's permission set and backing license resolved?
- [ ] Existing assignments checked before writing (idempotency)?
- [ ] For each requested role, both the permission set and its license are assigned?
- [ ] Verified by a post-write read (not the POST response alone)?
- [ ] Confirmed the target org, user, and each write with the user first?

---

## Output expectations

```text
CMDB Access Assignment — Complete (via service-itsm-agentic-setup-cmdb-access-assign)

Target org: <org>
User: <name> (<username>)

  Configuration Item Reader ......... Assigned
  Configuration Item Type Reader .... Already had access

This user can now read CMDB data in this org. If they still can't, confirm the org's
CMDB feature is turned on (that's a separate setup step).
```

Keep internal jargon out of user-facing output (no record IDs, HTTP status codes, error codes, object
or developer names). If any step fails, stop and tell the user — in plain language — which part didn't
succeed and what it means for them. Translate any raw error (e.g. a 403 or `FUNCTIONALITY_NOT_ENABLED`)
into what it means ("CMDB isn't turned on for this org yet"), rather than echoing the code.

---

## Common failures (surface these in plain language)

| Symptom | Likely cause | What to tell the user |
|---------|--------------|-----------------------|
| Feature status not `ENABLED` (or `403` on the status read) | Org-level CMDB gate not lifted | CMDB must be turned on for the org first; this is a separate setup step — point to the feature-enable skill |
| Permission set not found | Org is not CMDB-licensed / not set up | CMDB does not appear to be available on this org; confirm it is licensed and enabled |
| `403 FUNCTIONALITY_NOT_ENABLED` on a **bundle-management** read (e.g. `bundles/details`, `bundleListView`) after assignment, feature ENABLED | The user holds Reader/Owner/Type Reader but not **Type Manager** — bundle operations require it | Assign **Type Manager** — this role is required for CMDB bundle management; the other CMDB roles do not cover bundle operations |
| `400 DUPLICATE_VALUE` on assign | User already has that access | Not an error — report the role as already assigned |
| License-limit / no-seats error on assign | CMDB permission-set license seats exhausted | Report seats in use vs available; a seat must free up (or more licenses added) before assigning |
| `dispatch*` auth error | headless-360 MCP session not authenticated / token expired | Re-authenticate the headless-360 MCP connection and confirm the session points at the intended org |

---

## Cross-skill integration

| When | Skill |
|------|-------|
| The org CMDB feature is not enabled yet (org gate still closed) | `service-itsm-agentic-setup-cmdb-configure` (Layers 0–2 — enable the feature first, then return here) |
| The user needs the CMDB base content bundle installed | `service-itsm-agentic-setup-cmdb-bundle-deploy` (Layer 4 — content, separate from user access). That skill's bundle-management reads require the user hold **Type Manager**, so assign it here first |

---

## Reference file index

| File | When to read |
|------|--------------|
| `references/mcp-invocation.md` | Exact `dispatch*` url/method/body for every read and write, response envelopes, the license-seat query, and the error table |

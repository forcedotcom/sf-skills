# MCP Invocation Reference — CMDB User Access (Layer 3)

Every operation dispatches through the **Salesforce-hosted `headless-360`** MCP server, which exposes
four meta-tools:

- `mcp__headless-360__discover(query)` — semantic search over the indexed operation catalog
- `mcp__headless-360__describe(id)` — pull the schema and canonical route for one operation
- `mcp__headless-360__dispatch_readonly({url, method, queryParams?, body?})` — GET / read-only HTTP
- `mcp__headless-360__dispatch({url, method, body?, queryParams?})` — POST / PATCH / DELETE HTTP

**Dispatch takes raw HTTP**, not `{operation_id, arguments}`. Give it the full `url`
(`/services/data/v67.0/...`), `method`, optional `body`, and optional `queryParams` (camelCase — the
tool rejects `query_params`) — the server signs the request with the JWT bound to the current MCP
session and forwards it to the org. The skill never handles credentials or an org alias — everything
is derived from the session.

**A `discover` miss does NOT mean the route is absent.** The standard `/query` and `/sobjects/...`
REST routes this skill uses are not always ranked first (or indexed) in the discovery corpus —
`describe` on the canonical operation still returns the schema, and `dispatch*` on the exact path
still works. Only if the GET/POST itself returns 404 should you treat the route as unavailable on this
org.

## Response envelope

The `/query` and `/sobjects/…` REST endpoints are **standard REST** — the `dispatch*` tool returns the
REST response singly wrapped:

```json
{ "status_code": 200, "body": { "totalSize": 1, "records": [ { "Id": "0PS..." } ] } }
```

Read the relevant field from `body`. (Only `/headless/invoke/…` Aura-controller routes are doubly
wrapped as `body.body`; this skill uses none.) Status codes: `200` read success; `201` record created;
`400` bad body or a business-rule rejection — read `body[0].errorCode` (e.g. `DUPLICATE_VALUE`); `403
FUNCTIONALITY_NOT_ENABLED` the CMDB gate is closed (the org feature is not enabled, or this user has
no CMDB access yet); `404` the endpoint/impl is not present on this org; `500` a downstream dependency
issue. Minimum API version is **67.0** — `headless-360` currently only routes `v67.0+`.

---

## Discovery — optional, for confirmation

```text
mcp__headless-360__discover(query="permission set assignment")
```

`discover` returns matching operation ids; pipe one into `describe` to pull its input schema and
canonical route:

```text
mcp__headless-360__describe(id="<operation id from discover>")
```

The `/query` and `/sobjects/...` routes this skill uses are standard REST — if `discover` returns
nothing, dispatch the exact paths below directly; only treat a route as unavailable if the dispatch
itself 404s.

---

## The four CMDB permission sets

| Role | PermissionSet `Name` | Backing PSL `DeveloperName` |
|------|----------------------|-----------------------------|
| Reader | `ItSrvcCnfgItmReadPermissionSet` | `ItSrvcCnfgItmReadPsl` |
| Owner | `ItSrvcCnfgItmOwnerPermissionSet` | `ItSrvcCnfgItmOwnerPsl` |
| Type Reader | `ItSrvcCnfgItmTypReadPermissionSet` | `ItSrvcCnfgItmTypReadPsl` |
| Type Manager | `ItSrvcCnfgItmTypManagerPermissionSet` | `ItSrvcCnfgItmTypMgrPsl` |

Resolve the permission set's `Id` and its `LicenseId` at runtime (Step 3) rather than hardcoding IDs —
IDs differ per org.

---

## Step 1 — Confirm the org feature is enabled (read, prerequisite)

```json
mcp__headless-360__dispatch_readonly({
  "url":    "/services/data/v67.0/connect/setup/discovery/feature/service-cloud-itsm-cmdb-integration/status",
  "method": "GET"
})
```

Response: `{ apiName, status, enableBlockedReasons, ... }`. Proceed only when `status == ENABLED`. A
`403 FUNCTIONALITY_NOT_ENABLED` here means the org gate is not lifted — stop and route the user to the
feature-enable skill. User-level access assignment has no effect until this is `ENABLED`.

---

## Step 2 — Resolve the target user (read)

### Resolve "the current user" / "me" / "my own user" — use the API-root identity URL

Do **NOT** use `USER_ID()` (Apex-only — the REST query API rejects it with `MALFORMED_QUERY`), and do
**NOT** depend on `/chatter/users/me` or `/connect/user-profiles/me` (they return `403
FUNCTIONALITY_NOT_ENABLED` on orgs where Chatter/Communities are off). The always-available path is the
API root, whose `identity` field carries the running user's Id:

```json
mcp__headless-360__dispatch_readonly({
  "url":    "/services/data/v67.0/",
  "method": "GET"
})
```

Response `body.identity` is a URL like
`https://login.../id/<orgId>/005SB00000jbY2QYAU` — the **last path segment** is the current user Id
(18 chars, starts with `005`). Use it directly as `AssigneeId`, or confirm it:

```json
mcp__headless-360__dispatch_readonly({
  "url":    "/services/data/v67.0/query",
  "method": "GET",
  "queryParams": { "q": "SELECT Id, Username, Name, IsActive FROM User WHERE Id = '<userId>'" }
})
```

### Resolve a named user (username / email supplied)

```json
mcp__headless-360__dispatch_readonly({
  "url":    "/services/data/v67.0/query",
  "method": "GET",
  "queryParams": { "q": "SELECT Id, Username, Name, IsActive FROM User WHERE Username = '<username>'" }
})
```

- `totalSize == 1` → capture `records[0].Id`.
- `totalSize == 0` → no such user; ask the user to confirm the username.
- `totalSize > 1` → ambiguous; list `Name` + `Username` and ask which one.

Escape single quotes in any user-supplied value.

---

## Step 3 — Resolve each requested permission set (read)

```json
mcp__headless-360__dispatch_readonly({
  "url":    "/services/data/v67.0/query",
  "method": "GET",
  "queryParams": { "q": "SELECT Id, Name, LicenseId FROM PermissionSet WHERE Name = 'ItSrvcCnfgItmReadPermissionSet'" }
})
```

Capture `records[0].Id` (permission set) and `records[0].LicenseId` (the PSL to assign). Repeat per
requested role, or use `Name IN (...)` to resolve several at once. `totalSize == 0` for a role means
the org is not CMDB-licensed — stop and report.

---

## Step 4 — Check existing assignments (read — idempotency)

```json
mcp__headless-360__dispatch_readonly({
  "url":    "/services/data/v67.0/query",
  "method": "GET",
  "queryParams": { "q": "SELECT Id FROM PermissionSetAssignment WHERE AssigneeId = '<userId>' AND PermissionSetId = '<psId>'" }
})
```

```json
mcp__headless-360__dispatch_readonly({
  "url":    "/services/data/v67.0/query",
  "method": "GET",
  "queryParams": { "q": "SELECT Id FROM PermissionSetLicenseAssign WHERE AssigneeId = '<userId>' AND PermissionSetLicenseId = '<pslId>'" }
})
```

`totalSize == 1` on both → that role is already assigned; skip its writes. Otherwise assign what is
missing (PSL and/or permission set).

---

## Step 5 — Assign the license, then the permission set (write — confirm first)

### Assign the permission-set license first

```json
mcp__headless-360__dispatch({
  "url":    "/services/data/v67.0/sobjects/PermissionSetLicenseAssign",
  "method": "POST",
  "body":   { "AssigneeId": "<userId>", "PermissionSetLicenseId": "<pslId>" }
})
```

### Then assign the permission set

```json
mcp__headless-360__dispatch({
  "url":    "/services/data/v67.0/sobjects/PermissionSetAssignment",
  "method": "POST",
  "body":   { "AssigneeId": "<userId>", "PermissionSetId": "<psId>" }
})
```

Response on success: `{ "id": "0Pa...", "success": true }` (`201`). On `400`, read
`body[0].errorCode`:

- `DUPLICATE_VALUE` → the user already has it; treat as already-assigned success.
- a limit/seat error → the CMDB license has no free seats (see the seat query below); stop for that
  role and report. Do not retry.

---

## Step 6 — Verify (read)

Re-run the Step 4 queries. A role counts as assigned only when **both** the `PermissionSetAssignment`
and the `PermissionSetLicenseAssign` return `totalSize == 1` for the user. Report per role.

---

## License-seat query (for seat-exhaustion errors)

```json
mcp__headless-360__dispatch_readonly({
  "url":    "/services/data/v67.0/query",
  "method": "GET",
  "queryParams": { "q": "SELECT DeveloperName, TotalLicenses, UsedLicenses FROM PermissionSetLicense WHERE DeveloperName = 'ItSrvcCnfgItmReadPsl'" }
})
```

`UsedLicenses == TotalLicenses` → no free seats; a seat must be released (or more licenses added)
before the assignment can succeed.

---

## Idempotency

- Every read (Steps 1–4, 6) is safe to repeat.
- Assignment (Step 5) is per-user: if the user already holds the permission set / license, the POST
  returns `400 DUPLICATE_VALUE` — treat as already-assigned, not a failure. Always run Step 4 first so
  you only POST what is missing.

---

## Dead ends — do NOT do these

- **Do NOT:** assign the permission set without its license — a license-backed permission set will not
  take effect (or the assign is rejected) unless the user holds the backing PSL seat.
- **Do NOT:** create or edit a permission set to grant CMDB access — the four standard CMDB permission
  sets already exist in a licensed org; this skill only assigns them.
- **Do NOT:** assign CMDB access to work around a closed org gate — if the feature status is not
  `ENABLED`, user access is inert; enable the feature first (separate skill).
- **Do NOT:** retry a POST that failed with a seat/limit error — the seat shortage is real; surface it.
- **Do NOT:** pass `dispatch` the `{operation_id, arguments}` shape — it takes raw HTTP
  (`{url, method, body?, queryParams?}`).

---

## Error table

| Status / code | Meaning | Resolution |
|---------------|---------|------------|
| Feature `status != ENABLED` / `403` on the status read | Org-level CMDB gate not lifted | Enable the CMDB feature for the org first (feature-enable skill), then return |
| `400 DUPLICATE_VALUE` on assign | User already has that access | Idempotent success — report the role as already assigned |
| `400` seat/limit error on assign | CMDB permission-set license seats exhausted | Report used vs total seats; free a seat or add licenses, then retry |
| `PermissionSet` query `totalSize == 0` | Org not CMDB-licensed / not set up | CMDB is not available on this org; confirm it is licensed and enabled |
| `User` query `totalSize == 0` / `> 1` | User not found / ambiguous | Ask the user to confirm the username, or pick from the listed candidates |
| `403 FUNCTIONALITY_NOT_ENABLED` on a bundle-management read (`bundles/details`, `bundleListView`) after assign | User lacks **Type Manager** — bundle operations require it, Reader/Owner/Type Reader do not clear it | Assign the **Type Manager** role (PS `ItSrvcCnfgItmTypManagerPermissionSet` + its own PSL `ItSrvcCnfgItmTypMgrPsl`), then re-verify via Step 6 |
| `dispatch*` auth error | headless-360 MCP session not authenticated / token expired | Re-authenticate the headless-360 MCP connection; confirm the session points at the intended org |

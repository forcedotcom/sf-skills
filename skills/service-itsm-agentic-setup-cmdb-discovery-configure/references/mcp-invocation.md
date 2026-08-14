# MCP Invocation Reference — Enable CMDB Asset Discovery + grant page access (final layer)

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

**A `discover` miss does NOT mean the route is absent.** The Setup / Connect feature route this skill
uses (`/connect/setup/discovery/feature/.../status` and `.../enable`) and the standard `/query` /
`/sobjects/...` REST routes for the assignment step are **not always ranked first (or indexed)** in the
discovery corpus — `discover` may return nothing, or only tangential specs. That is not a signal they
don't exist. Dispatch on the exact path directly; only if the GET/POST itself returns 404 should you
treat the route as unavailable on this org.

## Response envelope

The `dispatch*` tool returns the HTTP status plus the parsed body, e.g.:

```json
{ "status_code": 200, "body": { "apiName": "service-cloud-itsm-discovery-integration", "status": "ENABLED", "enableBlockedReasons": [] } }
```

Read the relevant field from `body`. The `/query` and `/sobjects/…` REST routes are standard REST and
singly wrapped (`body.totalSize`, `body.records[]`, `body.id`). Status codes: `200/201` success; `400`
bad body (re-check schema via `describe`) or a business-rule rejection — read `body[0].errorCode` (e.g.
`DUPLICATE_VALUE`); `403 FUNCTIONALITY_NOT_ENABLED` the base CMDB gate is still closed (finish the base
CMDB feature first — Layer 2); `404` the endpoint/impl is not present on this org; `500` a downstream
dependency issue. Minimum API version is **67.0** — `headless-360` currently only routes `v67.0+`.

---

## Discovery feature: api name

`service-cloud-itsm-discovery-integration` — the same Connect feature surface used by the base CMDB
feature (`service-cloud-itsm-cmdb-integration`), just a different feature api name in the path.

## Discovery permission set

| Role | PermissionSet `Name` | Backing PSL `DeveloperName` |
|------|----------------------|-----------------------------|
| Discovery Manager | `ItSrvcDscvrMgrPermissionSet` | `ItSrvcDscvrMgrPsl` |

Resolve the permission set's `Id` and its `LicenseId` at runtime (Step 5) rather than hardcoding IDs —
IDs differ per org.

---

## Step 1 — Pre-check discovery feature status (read)

```text
dispatch_readonly({ "url": "/services/data/v67.0/connect/setup/discovery/feature/service-cloud-itsm-discovery-integration/status", "method": "GET" })
```

Response: `{ apiName, status, enableBlockedReasons: [...], disableBlockedReasons: [...],
dependencyStatuses: [...], blockedByApexLock }`.

- `status == ENABLED` → feature already on; skip the enable, verify, then continue to the access steps.
- `status == NOT_ENABLED` and `enableBlockedReasons` is empty → clear to enable.
- `enableBlockedReasons` non-empty → STOP; relay each reason. These are unmet prerequisites — most
  commonly the base CMDB feature is not yet enabled. Do not attempt the enable.
- `403 FUNCTIONALITY_NOT_ENABLED` on this GET → the base CMDB gate itself is closed; the org needs
  `service-itsm-agentic-setup-cmdb-configure` first.

The `dependencyStatuses[]` entry for `service-cloud-itsm-cmdb-integration` reflects the base feature —
`status == ENABLED` there confirms the prerequisite is satisfied.

## Step 2 — Enable Asset Discovery (write — confirm with the user first)

Skip if Step 1 already reported `ENABLED`.

```text
dispatch({ "url": "/services/data/v67.0/connect/setup/discovery/feature/service-cloud-itsm-discovery-integration/enable", "method": "POST", "body": {} })
```

Response: `{"success": true}` (`201`). The optional query param `solutionApiName` is not needed — omit it.

## Step 3 — Verify the feature (read — do not trust the POST response alone)

```text
dispatch_readonly({ "url": "/services/data/v67.0/connect/setup/discovery/feature/service-cloud-itsm-discovery-integration/status", "method": "GET" })
```

Expect `status == ENABLED`. This confirms the feature is on for the org. It does **not** give any user
the Discovery page — continue to the access steps below.

---

## Step 4 — Resolve the target user (read)

### Resolve "the current user" / "me" — use the API-root identity URL

Do **NOT** use `USER_ID()` (Apex-only — the REST query API rejects it), and do **NOT** depend on
`/chatter/users/me` or `/connect/user-profiles/me` (they `403` when Chatter/Communities are off). The
always-available path is the API root, whose `identity` field carries the running user's Id:

```json
mcp__headless-360__dispatch_readonly({ "url": "/services/data/v67.0/", "method": "GET" })
```

Response `body.identity` is a URL like `https://login.../id/<orgId>/005SB00000jbY2QYAU` — the **last
path segment** is the current user Id (18 chars, starts with `005`). Use it directly as `AssigneeId`,
or confirm it with the `User` query below.

### Resolve a named user (username / email supplied)

```json
mcp__headless-360__dispatch_readonly({ "url": "/services/data/v67.0/query", "method": "GET", "queryParams": { "q": "SELECT Id, Username, Name, IsActive FROM User WHERE Username = '<username>'" } })
```

- `totalSize == 1` → capture `records[0].Id`.
- `totalSize == 0` → no such user; ask the user to confirm the username.
- `totalSize > 1` → ambiguous; list `Name` + `Username` and ask which one.

Escape single quotes in any user-supplied value.

## Step 5 — Resolve the Discovery permission set + check existing assignment (read — idempotency)

```json
mcp__headless-360__dispatch_readonly({ "url": "/services/data/v67.0/query", "method": "GET", "queryParams": { "q": "SELECT Id, Name, LicenseId FROM PermissionSet WHERE Name = 'ItSrvcDscvrMgrPermissionSet'" } })
```

Capture `records[0].Id` (permission set) and `records[0].LicenseId` (the PSL to assign). `totalSize ==
0` means the org is not licensed for Discovery — stop and report. Then check existing assignments:

```json
mcp__headless-360__dispatch_readonly({ "url": "/services/data/v67.0/query", "method": "GET", "queryParams": { "q": "SELECT Id FROM PermissionSetAssignment WHERE AssigneeId = '<userId>' AND PermissionSetId = '<psId>'" } })
mcp__headless-360__dispatch_readonly({ "url": "/services/data/v67.0/query", "method": "GET", "queryParams": { "q": "SELECT Id FROM PermissionSetLicenseAssign WHERE AssigneeId = '<userId>' AND PermissionSetLicenseId = '<pslId>'" } })
```

`totalSize == 1` on both → already assigned; skip Step 6. Otherwise assign what is missing.

## Step 6 — Assign the license, then the permission set (write — confirm first)

### Assign the permission-set license first

```json
mcp__headless-360__dispatch({ "url": "/services/data/v67.0/sobjects/PermissionSetLicenseAssign", "method": "POST", "body": { "AssigneeId": "<userId>", "PermissionSetLicenseId": "<pslId>" } })
```

### Then assign the permission set

```json
mcp__headless-360__dispatch({ "url": "/services/data/v67.0/sobjects/PermissionSetAssignment", "method": "POST", "body": { "AssigneeId": "<userId>", "PermissionSetId": "<psId>" } })
```

Response on success: `{ "id": "0Pa...", "success": true }` (`201`). On `400`, read `body[0].errorCode`:

- `DUPLICATE_VALUE` → the user already has it; treat as already-assigned success.
- a limit/seat error → the Discovery license has no free seats (see the seat query below); stop and
  report. Do not retry.

## Step 7 — Verify the assignment (read)

Re-run the two Step 5 assignment queries. The user has Discovery page access only when **both** the
`PermissionSetAssignment` and the `PermissionSetLicenseAssign` return `totalSize == 1`.

---

## License-seat query (for seat-exhaustion errors)

```json
mcp__headless-360__dispatch_readonly({ "url": "/services/data/v67.0/query", "method": "GET", "queryParams": { "q": "SELECT DeveloperName, TotalLicenses, UsedLicenses FROM PermissionSetLicense WHERE DeveloperName = 'ItSrvcDscvrMgrPsl'" } })
```

`UsedLicenses == TotalLicenses` → no free seats; a seat must be released (or more licenses added)
before the assignment can succeed.

---

## Idempotency

- Every read (Steps 1, 3, 4, 5, 7) is safe to repeat.
- Step 2: if `status == ENABLED`, do not re-POST; enabling an already-enabled feature is unnecessary.
  Always pre-check.
- Step 6 is per-user: if the user already holds the permission set / license, the POST returns `400
  DUPLICATE_VALUE` — treat as already-assigned, not a failure. Always run Step 5 first so you only POST
  what is missing.

---

## Dead ends — do NOT do these

- **Do NOT:** enable discovery before the base CMDB feature (`service-cloud-itsm-cmdb-integration`)
  is `ENABLED` — the pre-check will report an `enableBlockedReasons` entry, or the status GET will
  403. Finish the base CMDB layers first.
- **Do NOT:** treat a `success: true` POST response as sufficient — always verify with the status
  GET (feature) and the assignment queries (access), since the POST response can lag the real state.
- **Do NOT:** stop after enabling the feature — the feature being on does not give any user the
  Discovery page; always follow with the Discovery-Manager assignment (Steps 4–7).
- **Do NOT:** assign the permission set without its license — a license-backed permission set will not
  take effect (or the assign is rejected) unless the user holds the backing PSL seat.
- **Do NOT:** create or edit a permission set to grant Discovery access — the standard
  `ItSrvcDscvrMgrPermissionSet` already exists in a licensed org; this skill only assigns it.
- **Do NOT:** pass `dispatch` the `{operation_id, arguments}` shape — it takes raw HTTP
  (`{url, method, body?, queryParams?}`).

---

## Error table

| Status | Meaning | Resolution |
|--------|---------|------------|
| 403 `FUNCTIONALITY_NOT_ENABLED` on status GET | Base CMDB gate still closed | Enable the base CMDB feature first (`service-itsm-agentic-setup-cmdb-configure`), then retry |
| `enableBlockedReasons` non-empty | An earlier CMDB layer is incomplete | Relay each reason; finish CMDB setup (base feature → access → bundle), then retry discovery |
| 404 on `/connect/...` path | Impl/dispatcher not present on this org | Confirm the org type; CMDB core APIs require a real (non-scratch-stub) org |
| 400 on feature enable | Wrong body/shape | Body is `{}`; re-confirm the path via `describe` |
| `PermissionSet` query `totalSize == 0` | Org not licensed for Discovery | Discovery access is not available on this org; confirm it is licensed |
| `400 DUPLICATE_VALUE` on assign | User already has Discovery page access | Idempotent success — report the role as already assigned |
| `400` seat/limit error on assign | Discovery permission-set license seats exhausted | Report used vs total seats; free a seat or add licenses, then retry |
| `User` query `totalSize == 0` / `> 1` | User not found / ambiguous | Ask the user to confirm the username, or pick from the listed candidates |
| 500 | Downstream dependency missing | Retry; if persistent, needs Salesforce support |
| Auth error | headless-360 MCP session not authenticated / token expired | Re-authenticate the headless-360 MCP connection; confirm the session points at the intended org |

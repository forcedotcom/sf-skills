# MCP Invocation Reference — CMDB Feature Enable (Layers 0–2)

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

**A `discover` miss does NOT mean the route is absent.** The Setup / Connect API routes this skill
uses (`/connect/setup/discovery/feature/.../status`, `/connect/tenantProvisioningStatus`, the
`/setup/org/permissions/...` and PSL-query paths) are documented core Connect APIs but are **not
always ranked first (or indexed)** in the discovery corpus — `discover` may return nothing, or only
tangential specs, for them. That is not a signal they don't exist. Dispatch on the exact path
directly; only if the GET/POST itself returns 404 should you treat the route as unavailable on this
org.

## Response envelope

The `dispatch*` tool returns the HTTP status plus the parsed body, e.g.:

```json
{ "status_code": 200, "body": { "isPermissionEnabled": true } }
```

Read the relevant field from `body`. Status codes: `200/201` success; `400` bad body (re-check
schema via `describe`); `403 FUNCTIONALITY_NOT_ENABLED` the CMDB gate is still closed (finish
Layer 2); `404` the endpoint/impl is not present on this org; `500` a downstream dependency issue.

---

## Layer 0 — Verify the CMDB org SKU (read-only, hard gate)

**Preferred: probe for the CMDB permission-set license (works on every org type, including
orgfarm/sandbox).** The PSL `ItSrvcCnfgItmReadPsl` exists in an org **only if that org carries the
CMDB SKU** — it is provisioned by the same license/edition that grants `ITSrvcsCnfgMgmnt`. Querying
for it is a reliable, universally-available Layer 0 signal (and it is the exact check the
`service-itsm-agentic-setup-cmdb-access-assign` skill already relies on):

```text
dispatch_readonly({
  "url":         "/services/data/v63.0/query",
  "method":      "GET",
  "queryParams": { "q": "SELECT Id, DeveloperName, MasterLabel FROM PermissionSetLicense WHERE DeveloperName = 'ItSrvcCnfgItmReadPsl'" }
})
```

- `totalSize == 1` → org is CMDB-licensed; proceed to Layer 1.
- `totalSize == 0` → STOP. This is a license/edition prerequisite. No API can grant the CMDB SKU.

**Fallback: the core org-permission Connect API** (only where it is present — it **404s on some
org types, including orgfarm test orgs**, so it is not the primary check):

```text
dispatch_readonly({
  "url":    "/services/data/v63.0/setup/org/permissions/ITSrvcsCnfgMgmnt",
  "method": "GET"
})
```

Response: `{"isPermissionEnabled": true|false}`. `true` → Layer 1; `false`/404 → rely on the preferred
PSL probe above. If no probe resolves, report that the org perm could not be verified and ask the
user to confirm CMDB is licensed before proceeding.

> A useful cross-check regardless of which probe you use: a `GET` on the Layer 2 feature-status
> endpoint that returns `200` (rather than `403 FUNCTIONALITY_NOT_ENABLED`) is itself evidence the
> org carries the CMDB surface.

---

## Layer 1 — Provision the ITOM tenant

### Check current provisioning status (read)

```text
dispatch_readonly({ "url": "/services/data/v67.0/connect/tenantProvisioningStatus", "method": "GET" })
```

Response includes `status` (e.g. `NOT_PROVISIONED`, `IN_PROGRESS`, `PROVISIONED`, `FAILED`),
`triggeredAt`, `callbackReceivedAt`. If `status == PROVISIONED`, skip to Layer 2.

### Trigger provisioning (write — confirm with the user first)

```text
dispatch({ "url": "/services/data/v67.0/connect/tenantProvisioningStatus", "method": "POST" })
```

No request body. Response echoes the status object. Provisioning is **asynchronous** — the callback
arrives later.

### Poll until PROVISIONED

Re-issue the GET above **every 30 seconds for up to 10 minutes** (≈20 attempts). Exit the loop on:

- `status == PROVISIONED` → success; advance to Layer 2.
- `status == FAILED` → stop. Do NOT retry via the API. Surface to the user, in plain language:
  1. **The decoded failure reason** — read the detail field from the FAILED response body (e.g.
     `error` / `failureReason` / `message`), unescape HTML entities (`&lt;` → `<`, `&gt;` → `>`,
     `&quot;` → `"`, `&amp;` → `&`) and strip any `<a>`/markup so the text is readable. If no detail
     is present, say the tenant provisioning failed without a returned reason.
  2. **The org's tenant provisioning Setup page URL**: `<org instance URL>/lightning/setup/CMDBProvisionalSettings/home`
     (this is the same page the Layer 2 `enableBlockedReasons` `CMDB_NOT_PROVISIONED` message links to).
  3. **Ask the user to provision manually from that page**, then re-run this skill once the tenant
     reads `PROVISIONED`. Escalate to Salesforce support only if the manual retry also fails.
- 10-minute window elapsed → stop, report the last-seen status, let the user decide whether to
  keep waiting or investigate.

Never spin past the 10-minute bound. Report progress to the user on each poll.

---

## Layer 2 — Enable the CMDB feature

Feature api name: `service-cloud-itsm-cmdb-integration`.

### Pre-check feature status (read)

```text
dispatch_readonly({ "url": "/services/data/v67.0/connect/setup/discovery/feature/service-cloud-itsm-cmdb-integration/status", "method": "GET" })
```

Response: `{ apiName, status, enableBlockedReasons: [...], disableBlockedReasons: [...],
dependencyStatuses: [...], blockedByApexLock }`.

- `status == ENABLED` → already enabled; skip to verify.
- `status == NOT_ENABLED` and `enableBlockedReasons` is empty → clear to enable.
- `enableBlockedReasons` non-empty → STOP; relay each reason. Do not attempt the enable.

### Enable the feature (write — confirm with the user first)

```text
dispatch({ "url": "/services/data/v67.0/connect/setup/discovery/feature/service-cloud-itsm-cmdb-integration/enable", "method": "POST", "body": {} })
```

Response: `{"success": true}`. The optional query param `solutionApiName` is not needed — omit it.

### Verify (read — do not trust the POST response alone)

```text
dispatch_readonly({ "url": "/services/data/v67.0/connect/setup/discovery/feature/service-cloud-itsm-cmdb-integration/status", "method": "GET" })
```

Expect `status == ENABLED`. This is the definitive — and only — confirmation the skill needs.
Do NOT perform a CMDB data read (e.g. `bundleListView`) to confirm the gate: that read also
enforces the *running user's* CMDB access, so it can 403 even when the feature is correctly
ENABLED (that is Layer 3, `service-itsm-agentic-setup-cmdb-access-assign`, not a failure here).

---

## Idempotency

- Layer 0 is read-only — safe to repeat.
- Layer 1: if already `PROVISIONED`, do not re-trigger; the GET is safe to repeat.
- Layer 2: if `status == ENABLED`, do not re-POST; enabling an already-enabled feature is
  unnecessary. Always pre-check.

---

## Dead ends — do NOT do these

- **Do NOT:** use `updateDefaultOrgPrefs` / `ItServiceSetupController` with pref `CMDBEnabled` —
  rejected with `500 Unknown preference name`. `CMDBEnabled` is not a settable pref; it flips only
  as a side effect of the Layer 2 feature enable.
- **Do NOT:** treat `tenantProvisioningStatus` as the feature toggle — provisioning is necessary
  infra (Layer 1) but does NOT set `CMDBEnabled`. An org can be `PROVISIONED` and still 403 until
  Layer 2.
- **Do NOT:** try to grant `ITSrvcsCnfgMgmnt` via any API — no setter exists.

---

## Error table

| Status | Meaning | Resolution |
|--------|---------|------------|
| 403 `FUNCTIONALITY_NOT_ENABLED` | CMDB gate still closed | Finish Layer 2; verify `status == ENABLED` |
| 404 on `/setup/org/permissions/...` | Endpoint not on this org | Rely on the preferred PSL-query probe (Layer 0) |
| 404 on `/connect/...` CMDB paths | Impl/dispatcher not present on this org | Confirm the org type; CMDB core APIs require a real (non-scratch-stub) org |
| 400 on feature enable | Wrong body/shape | Body is `{}`; re-confirm the path via `describe` |
| Tenant `status == FAILED` | Provisioning job failed Salesforce-side | Do NOT retry via API. Decode the reason from the body, give the user `<org instance URL>/lightning/setup/CMDBProvisionalSettings/home`, and ask them to provision manually; support only if that also fails |
| 500 | Downstream dependency missing | Retry; if persistent, needs Salesforce support |
| Auth error | headless-360 MCP session not authenticated / token expired | Re-authenticate the headless-360 MCP connection; confirm the session points at the intended org |

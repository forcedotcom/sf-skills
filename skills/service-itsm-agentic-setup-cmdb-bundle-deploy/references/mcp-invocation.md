# MCP Invocation Reference — CMDB Bundle Deploy (Layer 4)

Every operation dispatches through the **Salesforce-hosted `headless-360`** MCP server, which exposes
four meta-tools:

- `mcp__headless-360__discover(query)` — semantic search over the indexed operation catalog
- `mcp__headless-360__describe(id)` — pull the schema and canonical route for one operation
- `mcp__headless-360__dispatch_readonly({url, method, queryParams?, body?})` — GET / read-only HTTP
- `mcp__headless-360__dispatch({url, method, body?, queryParams?})` — POST / PATCH / DELETE HTTP

**Dispatch takes raw HTTP**, not `{operation_id, arguments}`. Give it the full `url`
(`/services/data/v67.0/...`), `method`, optional `body`, and optional `queryParams` (camelCase — the
tool rejects `query_params`) — the server
signs the request with the JWT bound to the current MCP session and forwards it to the org. The skill
never handles credentials or an org alias — everything is derived from the session.

**A `discover` miss does NOT mean the route is absent.** The `/connect/cmdb/...` routes this skill
uses are documented core Connect APIs but are not always ranked first (or indexed) in the discovery
corpus — `describe` on the canonical operation still returns the schema, and `dispatch*` on the exact
path still works. Only if the GET/POST itself returns 404 should you treat the route as unavailable on
this org.

## Response envelope

The CMDB Connect API, `/sobjects/…` REST endpoints, and `/query` are **standard REST** — the
`dispatch*` tool returns the REST response singly wrapped:

```json
{ "status_code": 200, "body": { "success": true, "latestVersion": "v3.0", "installedVersion": "" } }
```

Read fields from `body`. (Only `/headless/invoke/…` Aura-controller routes are doubly wrapped as
`body.body`; this skill uses none.) Status codes: `200/201` success; `400` bundle/version doesn't exist
(or bad body); `403 FUNCTIONALITY_NOT_ENABLED` the CMDB gate is closed — either the org feature is not
enabled, or the running user has no CMDB access (Step 1 disambiguates); `404` the endpoint/impl is not
present on this org; `500` a downstream dependency issue.

All three CMDB endpoints below are implemented core Connect APIs in module
`shared-service-itom-connect-api` and are gated by `orgHasCMDBEnabled`. Minimum API version is
**67.0** — `headless-360` currently only routes `v67.0+`.

---

## Discovery — run first

```text
mcp__headless-360__discover(query="cmdb bundle installation")
```

`discover` returns matching operation ids. Pipe the install operation id into `describe` to pull its
input schema and canonical HTTP route:

```text
mcp__headless-360__describe(id="<bundleInstallation operation id from discover>")
```

If `discover` returns nothing at all after rewording the query, the org's `headless-360` corpus does
not index this surface — dispatch the exact `/connect/cmdb/...` paths below directly; only treat the
route as unavailable if the dispatch itself 404s.

---

## Step 1 — Enablement gate + catalog: bundleListView (read)

```json
mcp__headless-360__dispatch_readonly({
  "url":    "/services/data/v67.0/connect/cmdb/bundleListView",
  "method": "GET"
})
```

- `200` → CMDB is enabled and the running user has access. `body` includes availability + installation
  status per bundle.
- `403 FUNCTIONALITY_NOT_ENABLED` → ambiguous; this read enforces both the org gate and the user's own
  CMDB access. Disambiguate via the feature status:
  ```json
  mcp__headless-360__dispatch_readonly({
    "url":    "/services/data/v67.0/connect/setup/discovery/feature/service-cloud-itsm-cmdb-integration/status",
    "method": "GET"
  })
  ```
  - `status != ENABLED` → CMDB feature not enabled. STOP; route to
    `service-itsm-agentic-setup-cmdb-configure`.
  - `status == ENABLED` → feature is on; the user lacks CMDB permission sets. STOP; route to
    `service-itsm-agentic-setup-cmdb-access-assign` (read set at minimum; Type Manager for bundle
    management), then retry.

Identify the base bundle (CMDB Foundation) and note its `currentInstalledVersion`.

---

## Step 2 — Resolve the exact base version: bundles/details (read)

```json
mcp__headless-360__dispatch_readonly({
  "url":    "/services/data/v67.0/connect/cmdb/bundles/details",
  "method": "GET",
  "queryParams": { "bundleIdentifier": "base" }
})
```

Response fields include: `name`, `latestVersion`, `installedVersion`, `installedDate`,
`publishedDate`, `dependsOnBaseVersion`, `bundleDescription`, `listOfVersions`.

- **Pass the version string verbatim.** `bundles/details` reports the version exactly as the registry
  stores it (e.g. `latestVersion: "v3.0"`). The `bundleInstallation` endpoint matches the requested
  version by **exact string equality** against that registry — it does no normalization — so send the
  catalog's `latestVersion` through unchanged. Do NOT strip, add, or reformat any characters (including
  a leading `v`); altering the string makes it fail the equality check.
- **You may only install the latest version.** The endpoint rejects any non-latest version
  (`"Target version <x> is not the latest available version"`) and cannot install or roll back to an
  older version — always resolve `latestVersion` and install exactly that.
- If `installedVersion == latestVersion`, the base bundle is already up to date — stop.

`versionNumber` is an optional query param to inspect a specific version; omit it to get the latest.

> **If `bundles/details` returns `403 FUNCTIONALITY_NOT_ENABLED`** while `bundleListView` (Step 1)
> returned `200`: the org gate is fine, but the running user lacks the bundle-management permission.
> `bundles/details` requires the **`ItSrvcCnfgItmTypManagerPermissionSet`** (Type Manager) set — the
> read / owner / type-read sets are not sufficient. Have Type Manager assigned via
> `service-itsm-agentic-setup-cmdb-access-assign`, then retry. As a fallback, `bundleListView` already
> returns the base bundle's `currentInstalledVersion` and `latestVersion`, so resolve the version from
> Step 1's response if Type Manager cannot be assigned.

---

## Step 3 — Install the base bundle: bundleInstallation (write)

Confirm the input schema first:

```text
mcp__headless-360__discover(query="cmdb bundle installation")
mcp__headless-360__describe(id="<bundleInstallation operation id>")
```

Then install:

```json
mcp__headless-360__dispatch({
  "url":    "/services/data/v67.0/connect/cmdb/bundleInstallation",
  "method": "POST",
  "body":   { "bundleIdentifier": "base", "version": "<Step 2's latestVersion, verbatim>" }
})
```

Both `bundleIdentifier` and `version` are **required**. Response:
`{ "success": true, "message": "...", "error": null }`. `success: true` means installation was
**initiated** (may complete asynchronously).

---

## Step 4 — Verify (read)

```json
mcp__headless-360__dispatch_readonly({
  "url":    "/services/data/v67.0/connect/cmdb/bundles/details",
  "method": "GET",
  "queryParams": { "bundleIdentifier": "base" }
})
```

Confirm `installedVersion` equals the version you installed. If installation is async and it has not
updated yet, report in-progress and tell the user to re-check.

---

## Idempotency

- All reads (Steps 1, 2, 4) are safe to repeat.
- Before installing, compare `installedVersion` to `latestVersion` — skip if already up to date.
- Re-installing the same version is unnecessary; always resolve + compare first.

---

## Dead ends — do NOT do these

- **Do NOT:** hard-code, guess, or reformat a version string — always read `latestVersion` from the
  catalog and post it verbatim (including any leading `v`, e.g. `"v3.0"`). The endpoint matches by
  exact string equality against the registry; stripping or altering the string breaks the match.
- **Do NOT:** attempt to install a non-latest version — the endpoint only accepts the latest
  (`"Target version <x> is not the latest available version"`) and cannot roll back.
- **Do NOT:** install an optional add-on bundle — this skill is scoped to `base` (CMDB Foundation)
  only.
- **Do NOT:** treat a `403` on `bundleListView` as "feature off" without checking the feature status —
  it may instead be the running user lacking CMDB access.
- **Do NOT:** report the install as done on `success: true` alone — installation can be async; verify
  via `bundles/details`.
- **Do NOT:** pass `dispatch` the `{operation_id, arguments}` shape — it takes raw HTTP
  (`{url, method, body?, queryParams?}`).

---

## Error table

| Status / message | Meaning | Resolution |
|------------------|---------|------------|
| `403 FUNCTIONALITY_NOT_ENABLED` on `bundleListView`, feature `status != ENABLED` | CMDB feature not enabled for the org | Enable the CMDB feature first (`service-itsm-agentic-setup-cmdb-configure`), then return |
| `403 FUNCTIONALITY_NOT_ENABLED` on `bundleListView`, feature `status == ENABLED` | Feature on; running user lacks CMDB access | Grant the user CMDB access (`service-itsm-agentic-setup-cmdb-access-assign`), then retry — do NOT run configure |
| `403 FUNCTIONALITY_NOT_ENABLED` on `bundles/details`, `bundleListView` was `200` | User lacks Type Manager (`ItSrvcCnfgItmTypManagerPermissionSet`); org gate is fine | Assign Type Manager via the access-assign skill, or read the version from `bundleListView` instead |
| `400` bundle/version doesn't exist on install | Wrong `version` string | Re-read `bundles/details`; post `latestVersion` verbatim (do not strip or reformat) |
| `Target version <x> is not the latest available version` on install | Attempted to install a non-latest version | Re-read `bundles/details`, resolve `latestVersion`, and install exactly that — older versions/rollback are not supported |
| `success: true`, version unchanged | Async install in progress | Re-check `bundles/details` shortly |
| `500` on install (verbatim latest version) | Downstream/backend issue on the org, not a bad request | Retry; if persistent, capture the support `ErrorId` and escalate to Salesforce support |
| `dispatch*` auth error | The headless-360 MCP session isn't authenticated or the token expired | Re-authenticate the headless-360 MCP connection; confirm the session points at the intended org |

# MCP invocation reference — service-itsm-incident-mgmt-configure

This skill toggles the **master ITSM Incident Management** org preference through the Salesforce-hosted **Headless-360 MCP server** (server key `headless-360`). The master pref reads and writes via the **Setup Discovery Connect API** (`/services/data/v67.0/connect/setup/discovery/*`, `apiName = service-cloud-itsm-incident`); enabling it cascades the sub-preferences on server-side, so the common enablement flow is a single POST.

Every read and every write dispatches through the four meta-tools that Headless-360 exposes: `discover`, `describe`, `dispatch`, `dispatch_readonly`. URLs are addressed by `url` + `method` on the dispatch tools — **not** by `operation_id`.

Public reference: `https://developer.salesforce.com/docs/platform/hosted-mcp-servers/references/reference/headless-360-mcp.html`

## Tool argument shape (IMPORTANT)

Both `mcp__headless-360__dispatch` and `mcp__headless-360__dispatch_readonly` take:

```json
{
  "url": "/services/data/v67.0/...",
  "method": "GET|POST|PATCH|...",
  "body": { /* optional; POST/PATCH only */ },
  "query_params": { /* optional; alternative to inline querystring */ }
}
```

They do **not** take `{operation_id, arguments}` — that shape returns `INVALID_ARGUMENT: 'url' and 'method' are required`. Every example in this file uses the `{url, method, body?, query_params?}` shape.

`mcp__headless-360__describe` takes `{id: "<sor_id>"}` — a different arg name from the dispatch tools.

## MCP client registration

The MCP client (adk-eval, Claude Code session, Postman, Cursor, etc.) needs an `additionalServers.headless-360` entry pointing at the correct env URL. Working example (from `packages/adk-eval/mcp-config.json`):

```json
{
  "enabled": true,
  "toolsets": ["data", "orgs", "metadata", "testing", "users"],
  "additionalServers": {
    "headless-360": {
      "disabled": false,
      "timeout": 900000,
      "type": "streamableHttp",
      "url": "<pick from Server URLs table below>",
      "autoApprove": ["discover", "describe", "dispatch_readonly"]
    }
  }
}
```

Server URLs by environment:

| Environment | URL |
|-------------|-----|
| Production | `https://api.salesforce.com/platform/mcp/v1/platform/headless-360` |
| Sandbox / Scratch | `https://api.salesforce.com/platform/mcp/v1/sandbox/platform/headless-360` |
| Login-restricted org (`/d/` form) | `https://api.salesforce.com/platform/mcp/v1/d/{mydomain}/{develop\|scratch}/platform/headless-360` |

The `/d/` variant is required for orgs that have disabled login through `login.salesforce.com` / `test.salesforce.com`. `{mydomain}` is the org's My Domain prefix — the value before `.my.salesforce.com` in the org's login host.

Notes:

- **`timeout` is milliseconds** in the Vibes SDK contract, not seconds. `900000` = 15 minutes; a smaller value will kill `discover` / `dispatch` calls prematurely.
- `dispatch` is intentionally omitted from `autoApprove` — mutations should be user-approved per invocation. `dispatch_readonly` is auto-approved because it cannot change state.
- The URL's env segment (`platform` / `sandbox` / `develop` / `scratch`) must match the target org's tier and the tier of the ECA used for OAuth. A prod URL with a sandbox-tier ECA (or vice versa) will cause `OAUTH_AUTHORIZATION_BLOCKED` errors.

## External Client App setup (one-time, org-admin task)

`headless-360` requires an **External Client App** (ECA) with:

- OAuth Scopes (Salesforce scope names): `MCP`, `RefreshToken`
- OIDC `.well-known` names for the same scopes: `mcp_api`, `refresh_token`
- **Issue JSON Web Token (JWT)-based access tokens for named users**: on
- All other security options: off unless the org requires them
- PKCE required (Authorization Code + PKCE grant only)
- Callback URL: one per MCP client (see below)

Callback URLs by client:

| Client | Callback URL |
|--------|--------------|
| Claude.ai (web app) | `https://claude.ai/api/mcp/auth_callback` |
| Claude Code CLI | `http://localhost:<port>/callback` — port matches the `oauth.callbackPort` set on the `mcpServers.<name>` entry in the Claude Code MCP client configuration. Register the same port on the ECA. Default port when unset is dynamic (a random high port each session), which will fail against a pre-registered ECA — always set `callbackPort` explicitly. |
| Postman (HTTP) | `https://oauth.pstmn.io/v1/callback` |
| Postman (browser) | `https://oauth.pstmn.io/v1/browser-callback` |
| Cursor (recent) | `http://localhost:8787/callback` |
| Cursor (legacy) | `cursor://anysphere.cursor-mcp/oauth/callback` |

Propagation: an ECA can take up to **30 minutes** to become operational after Create. Server activation (Setup → MCP Servers → `headless-360` → Activate) can take up to **2 minutes**.

Auth URLs (used by the MCP client at OAuth time):

| Env | Auth URL | Token URL |
|-----|----------|-----------|
| Production | `https://login.salesforce.com/services/oauth2/authorize` | `https://login.salesforce.com/services/oauth2/token` |
| Sandbox / Scratch | `https://test.salesforce.com/services/oauth2/authorize` | `https://test.salesforce.com/services/oauth2/token` |
| Login-restricted org (`/d/` form) | `https://{mydomain}.my.salesforce.com/services/oauth2/authorize` | `https://{mydomain}.my.salesforce.com/services/oauth2/token` |

For the `/d/` variant, the Auth/Token URLs point at the org's My Domain host directly — not at `login.salesforce.com` / `test.salesforce.com`. This is why the `/d/` server URL exists in the first place: those orgs have login through the shared hosts disabled.

Header prefix on tool calls: `Bearer <access_token>`. The org against which each tool call runs is derived from the JWT issuer — callers do not pass an orgId in the body.

## API contract — master ITSM Incident Management toggle

**User-visible label**: Enable Incident Management. **Backing**: **Setup Discovery Connect API** at `/services/data/v67.0/connect/setup/discovery/*`. **Identifier on the wire**: `apiName = service-cloud-itsm-incident`.

**Access guard**: requires View Setup + Setup Admin (`UserPermissions.CustomizeApplication`). Org must have `IncidentMgmt.orgHasITSMOrgPermission`. Does not require the Headless-360 Aura dispatcher — this pref routes entirely through the Connect API.

Always call `describe` at runtime to confirm the exact schema — the examples here are working expectations, not contracts.

### Read endpoint

`GET /services/data/v67.0/connect/setup/discovery/features`

This is the Setup Discovery **collection endpoint** — it returns the full feature catalog (~763 entries, ~1.1 MB on a well-loaded org) and does not honor an `?apiName=` filter server-side. Filter the returned array client-side to the element where `apiName == "service-cloud-itsm-incident"` and read its `status` field (`ENABLED` / `NOT_ENABLED` / …).

```json
{
  "url": "/services/data/v67.0/connect/setup/discovery/features",
  "method": "GET"
}
```

Trimmed element after client-side filtering:

```json
{
  "apiName": "service-cloud-itsm-incident",
  "title": "Incident Management",
  "tag": "ITSM_CLOUD",
  "status": "ENABLED",
  "completedConfigStepCount": 2,
  "totalConfigStepCount": 17
}
```

### Write endpoints

`POST /services/data/v67.0/connect/setup/discovery/feature/service-cloud-itsm-incident/enable` and `POST .../disable`

Both endpoints take an empty body. The enable path flips the master to `ENABLED`; the disable path flips it to `NOT_ENABLED`. Verified: `GET` on either path returns `HTTP 405 METHOD_NOT_ALLOWED. Allowed are POST` — confirming both routes are registered as POST-only writers.

Enable:

```json
{
  "url": "/services/data/v67.0/connect/setup/discovery/feature/service-cloud-itsm-incident/enable",
  "method": "POST",
  "body": {}
}
```

Disable:

```json
{
  "url": "/services/data/v67.0/connect/setup/discovery/feature/service-cloud-itsm-incident/disable",
  "method": "POST",
  "body": {}
}
```

Response: `201 {"success": true}` on both routes (some builds may return `200`/`204` with an echoed feature summary or empty body — call `describe` at runtime to confirm the exact response schema).

Disabling then re-enabling on the same org preserves `completedConfigStepCount` — the server restores prior progress instead of resetting it.

### Idempotency contract

Read the feature via the collection GET; filter to `apiName == "service-cloud-itsm-incident"`; compare `status` against the requested state; skip the POST when they already match (`status == "ENABLED"` for an enable request, or `status != "ENABLED"` for a disable request); verify by re-reading the feature after writing.

## Confirm-to-write checkpoint (REQUIRED)

Before dispatching any POST, present the target payload via `AskUserQuestion` as `(Master Incident Management: <current> → <requested>)` and require an explicit "yes" before proceeding. Proceed to write ONLY on explicit "yes". On "no", stop and report the current state without writing.

## Error taxonomy

Errors observed on Headless-360 for this surface:

- **`OAUTH_AUTHORIZATION_BLOCKED: Cross-org OAuth flows are not supported for this external client app`** during the OAuth handshake (before any `tools/call`) — the ECA the MCP client is using lives in a different org than the JWT-issuing target org, and that ECA has cross-org OAuth disabled (the default). Fixes, in order of preference:
    1. Create/activate the ECA **inside the target org** (Setup → External Client Apps in that org). Self-contained; no cross-org allowance needed.
    2. Confirm the target org's My Domain matches the `{mydomain}` segment in the server URL exactly, and matches the host in the Auth/Token URLs the ECA is registered against — an ECA registered against `login.salesforce.com` cannot mint tokens for a My-Domain host, and vice versa.
    3. Only if (1) is not possible: reconfigure the source-org ECA to permit cross-org OAuth.
- **`401 Unauthorized`** on `initialize` or any `tools/call` — ECA not propagated yet (takes up to 30 minutes), wrong scopes on the ECA (must be `mcp_api` + `refresh_token`), or the access token has expired. Surface verbatim.
- **`404 Not Found`** on `initialize` — the `headless-360` server is not activated on the org (Setup → MCP Servers → Activate — takes up to 2 minutes), or the server URL's env segment (`platform` / `sandbox` / `develop` / `scratch`) doesn't match the target org's tier.
- **`403 Forbidden`** on `discover` / `describe` — corpus gate closed (`enableHeadless360CorpusAccess` off for the org). The corpus gate is required for semantic search; if the org hasn't opened it, `dispatch*` will still work if you already know the URL directly.
- **`403 Forbidden`** on `dispatch_readonly` / `dispatch` — the calling user lacks View Setup + Setup Admin, or the org lacks `IncidentMgmt.orgHasITSMOrgPermission`.
- **`ROUTE_NOT_FOUND`** on `/services/data/*` — the exact URL isn't registered — usually a typo, wrong path segment, or a wrong `vXX.0` API version. Re-check the URL and API version.
- **`HTTP 405 METHOD_NOT_ALLOWED. Allowed are POST`** on a write URL — the caller used `GET` instead of `POST` against `.../enable` or `.../disable`. Both write routes are POST-only.

## Worked example — Toggle master Incident Management

Step 1: Read current state via `dispatch_readonly`.

```json
{
  "url": "/services/data/v67.0/connect/setup/discovery/features",
  "method": "GET"
}
```

Response (after client-side filtering on `apiName == "service-cloud-itsm-incident"`):

```json
{
  "apiName": "service-cloud-itsm-incident",
  "title": "Incident Management",
  "tag": "ITSM_CLOUD",
  "status": "NOT_ENABLED",
  "completedConfigStepCount": 0,
  "totalConfigStepCount": 17
}
```

Step 2: Confirm-to-write — present `(Master Incident Management: NOT_ENABLED → ENABLED)` and require "yes".

Step 3: Write via `dispatch`.

```json
{
  "url": "/services/data/v67.0/connect/setup/discovery/feature/service-cloud-itsm-incident/enable",
  "method": "POST",
  "body": {}
}
```

Response: `201 {"success": true}`.

Step 4: Verify via `dispatch_readonly` — re-read the collection endpoint, filter to `apiName == "service-cloud-itsm-incident"`, and confirm `status == "ENABLED"`.

**Disable direction**: substitute `.../disable` for `.../enable` in step 3; substitute `NOT_ENABLED` for `ENABLED` in the verify step and in the confirm-to-write tuple.

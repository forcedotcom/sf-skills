# MCP Invocation Reference

Every operation in this skill dispatches through the **headless-360** MCP server. Do **not**
use the Salesforce CLI (its `api request`, `data query`, or `org open` subcommands), the
project-codey MCP server, raw `curl`, or any other HTTP client. headless-360 is the only
execution path.

## Tools

- `mcp__headless-360__discover` — search the indexed API/SOR corpus by natural language query (preflight/discovery). Optional `domain` and `resultType` (`endpoint` | `sor`) filters.
- `mcp__headless-360__describe` — pull full detail for a specific operation or Setup Operation Recipe (SOR) by id. The returned `path` (or a SOR step's `api`) is dispatch-ready — copy it verbatim.
- `mcp__headless-360__dispatch_readonly` — GET-only dispatcher. **Prefer this for all reads.**
- `mcp__headless-360__dispatch` — dispatcher for all methods (GET/POST/PUT/PATCH/DELETE). Use for writes.

`dispatch` / `dispatch_readonly` accept:

| Field | Notes |
|-------|-------|
| `method` | `"GET"`, `"POST"`, `"PATCH"`, … (`dispatch_readonly` only accepts `"GET"`) |
| `url` | The relative API path, **including** the `/services/data/vXX.0` prefix — e.g. `"/services/data/v67.0/connect/communities"`. Unlike some other dispatchers, headless-360 does **not** resolve or add the version — passing a bare `"/connect/communities"` returns `400 ROUTE_NOT_FOUND`. |
| `body` | JSON object for POST/PATCH |
| `queryParams` | map of key-value pairs for GET query strings |
| `headers` | optional HTTP headers |

Send the `url` exactly as returned by `discover`/`describe` when available — do not edit it or
prepend a host. When `discover`/`describe` don't surface the operation (common for standard
Connect API create/list calls on Experience Cloud — see "Discovery" below), dispatch the
well-known, versioned path documented in this skill directly.

Credentials are handled by whichever org the headless-360 MCP session is bound to at connection
time — **the skill never handles credentials, tokens, or login URLs.** If a call returns an auth
error, tell the user to re-authenticate the org the MCP session is pointed at — do not attempt to
fetch a token yourself.

## Response envelope

`dispatch` / `dispatch_readonly` return the org's raw Connect API response merged with a wrapper:

```json
{ "status_code": 202, "body": { "jobId": "08P...", "message": "...", "name": "..." }, "url": "https://<org-host>/services/data/v67.0/connect/communities" }
```

`body` is the controller payload. Status codes: `200`/`202` = success, `400` = bad body/route (re-check
the `url` version prefix and body shape), `404` = endpoint not in this org, `500` = downstream
dependency missing. Errors from the underlying org come back as
`{"error_code": "...", "message": "...", "status_code": 400/...}` (e.g. `ROUTE_NOT_FOUND`,
`INVALID_TYPE`, `INVALID_INPUT`) — read `error_code` and `message` to diagnose.

---

## Discovery — run first each session (optional but recommended)

```text
mcp__headless-360__discover(query="create self-service Experience Cloud site")
mcp__headless-360__discover(query="create Experience Cloud community site from template")
mcp__headless-360__discover(query="create partner PRM portal site")
```

**Known limitation (verified):** the headless-360 corpus indexes many capabilities as multi-step
SORs (Setup Operation Recipes) covering *management* of an already-existing community (topics,
navigation menus, branding, sharing sets, etc.), not the base `POST /connect/communities` /
`GET /connect/communities/templates` create/list calls themselves. Those two operations are
**not** individually resolvable via `discover`/`describe` in this corpus at time of writing — a
`describe` call for ids like `chatter.connect.api.postCommunityCollection` or
`post-community-collection` returns `"No operation or SOR found for id: ..."`, even though the
*guidance text* inside the `chatter-connect-api` SOR describe output mentions
`post-community-collection` in a documentation string (not as an actual indexed step).

**Do not conclude the capability is missing from the org.** These are standard, long-lived
Connect API endpoints (available since API v46.0+/v48.0+ per Salesforce docs) — dispatch them
directly using the verified paths below rather than falling back to the `sf` CLI or declaring "no
tool connects to a live org."

The stable, **verified-working** paths at time of writing (confirmed live against a test org):

| Purpose | Method | Path (verified) |
|---------|--------|------------------|
| List valid community templates | GET | `/services/data/v67.0/connect/communities/templates` |
| List existing Experience Cloud sites | GET | `/services/data/v67.0/connect/communities` |
| Create a general community from a template | POST | `/services/data/v67.0/connect/communities` |
| Employee/self-service Aura (or LWR) site + MIAW | POST | `/services/data/v67.0/connect/self-service/site` |
| Poll self-service site job | GET | `/services/data/v67.0/connect/self-service/site/status/{jobId}` |
| Partner (PRM) portal — synchronous | POST | `/services/data/v67.0/connect/prm/setup/sites` |
| Poll a community-create `BackgroundOperation` job | GET | `/services/data/v67.0/query?q=SELECT+Id,+Status+FROM+BackgroundOperation+WHERE+Id='<jobId>'` |
| Create the Agentforce employee agent (optional) | PATCH | `/services/data/v67.0/headless/invoke/einstein/genai-agentbuilder/create-copilot-from-template` |
| List service-agent templates for the AI-portal editor | GET | `/services/data/v67.0/headless/invoke/platform/communities/unified-aiportal-setup/get-service-agent-templates` |

If `discover` surfaces a different/newer operation id for one of these, prefer the `path` it
returns (already dispatch-ready) over the hardcoded table above — the table is a fallback, not a
canonical override.

---

## Routes

### Employee Service / Self-Service — `POST /connect/self-service/site`

Creates an **Aura** (or LWR) Experience Builder site and wires MIAW in at creation time. Requires a
**guest** Embedded Service Deployment config id.

```text
method: "POST"
url:    "/services/data/v67.0/connect/self-service/site"
body:
{
  "siteName": "<portal name>",
  "siteType": "AURA",                              // AURA (default) or LWR — never Visualforce
  "guestEmbeddedServiceConfigId": "<guest ESD id>",// REQUIRED
  "embeddedServiceConfigId": "<auth ESD id>",      // optional
  "enableForGuest": true
}
```

Response: `{success, siteName, urlPathPrefix, siteUrl, error, jobId, status}`. Poll with the status
route below.

> No guest ESD yet? The self-service API **hard-requires** `guestEmbeddedServiceConfigId`. Either
> create an Embedded Service Deployment first (Setup → Embedded Service Deployments, or the
> MIAW/embedded-service setup skill), **or** use the general-community route with an Aura template
> (`Employee Portal`, `Customer Service`, or `Help Center`) — which needs no ESD.

Poll job:

```text
method: "GET"
url:    "/services/data/v67.0/connect/self-service/site/status/{jobId}"   // substitute the jobId into the path
```

### General Community — `POST /connect/communities`

No ESD dependency. Use an **Experience Builder** `templateName` (Aura or LWR), validated against the
live template list.

First, list templates:

```text
method: "GET"
url:    "/services/data/v67.0/connect/communities/templates"
```

Verified response shape (from a live test org):
```json
{
  "templates": [
    { "publisher": "Salesforce", "templateName": "Build Your Own" },
    { "publisher": "Salesforce", "templateName": "Help Center" },
    { "publisher": "Salesforce", "templateName": "Customer Account Portal" },
    { "publisher": "Salesforce", "templateName": "Customer Service" },
    { "publisher": "Salesforce", "templateName": "Agentforce Employee Center" },
    { "publisher": "Salesforce", "templateName": "Build Your Own (LWR)" },
    { "publisher": "Salesforce", "templateName": "Salesforce Tabs + Visualforce" }
  ],
  "total": 11
}
```
Use a returned `templateName` **verbatim**. For an employee service portal prefer `Agentforce Employee Center`
(if present) — the richest employee experience (ticketing, catalog, knowledge, Agentforce-ready) —
else `Employee Portal`, else `Customer Service`; for a knowledge/help desk prefer `Help Center`. Never
use `Salesforce Tabs + Visualforce` — it is the legacy Visualforce site with no Builder.

Create (the body accepts only `name`, `description`, `templateName`, `templateParams`, `urlPathPrefix`):

```text
method: "POST"
url:    "/services/data/v67.0/connect/communities"
body:
{
  "name": "<portal name>",
  "urlPathPrefix": "<alphanumeric only, no spaces or hyphens>",
  "templateName": "Agentforce Employee Center",
  "description": "<optional>"
}
```

Response (verified, `202`): `{jobId, message, name}`, e.g.:
```json
{
  "jobId": "08PSB000023cP5t2AE",
  "message": "Your site is almost ready. To track the site creation status, query the BackgroundOperation object and enter the jobId as the Id.",
  "name": "GK Portal v2"
}
```
Poll `BackgroundOperation` (see below).

> Duplicate names return `400 INVALID_INPUT "Enter a different name. That one already exists."` —
> list existing sites with `GET /services/data/v67.0/connect/communities` and pick a non-colliding name/prefix.

#### Agentforce assistant for `Agentforce Employee Center` (optional, separate step)

The community-create call provisions the **site** only. To add the embedded **Agentforce**
conversational assistant, create the internal employee agent from its shipped template — this is a
distinct call and is not required to stand up the portal:

```text
method: "PATCH"
url:    "/services/data/v67.0/headless/invoke/einstein/genai-agentbuilder/create-copilot-from-template"
body:
{
  "templateNameOrId": "EmployeeCopilot__AgentforceEmployeeAgent",
  "copilotContext": { "name": "<agent label>", "company": "<company name>", "newAgentUser": true }
}
```

- `copilotContext.company` is **required** — omitting it returns `500 CONTROLLER_ERROR "Company is Mandatory in Agents"` (`companyName` is a separate, non-substitute field).
- The agent is created **`Inactive`** (v1 version) and must be activated and wired to the site's channel afterward. `newAgentUser: true` auto-provisions a runtime user.
- Full Agentforce configuration (activation, channel wiring, permissions) is broad and out of scope for this skill — this skill provisions the site and points to the agent template above.

### Partner (PRM) — `POST /connect/prm/setup/sites`

Synchronous. Requires the `CommonPrmEnabled` feature.

```text
method: "POST"
url:    "/services/data/v67.0/connect/prm/setup/sites"
body:
{
  "siteName": "<name>",
  "siteUrlPrefix": "<url prefix>",
  "siteDesc": "<optional>",
  "prmTemplate": "<org-specific PRM template>"
}
```

Response: `{networkId}`. No job polling (synchronous).

---

## Background job monitoring (communities path)

The communities response says "query the BackgroundOperation object." Do this through
`mcp__headless-360__dispatch_readonly` against the **regular REST query endpoint** —
**not** `/tooling/query`, and **not** the Salesforce CLI `data query` subcommand.

```text
method:      "GET"
url:         "/services/data/v67.0/query"
queryParams: { "q": "SELECT Id, Status FROM BackgroundOperation WHERE Id = '<jobId>'" }
```

> **Verified gotcha — Tooling query fails on this object.** Calling
> `GET /services/data/vXX.0/tooling/query` with this SOQL returns:
> ```json
> { "error_code": "API_ERROR", "status_code": 400, "body": "[{\"message\":\"sObject type 'BackgroundOperation' is not supported.\",\"errorCode\":\"INVALID_TYPE\"}]" }
> ```
> Switching to the plain `/services/data/vXX.0/query` endpoint with the identical SOQL succeeds
> (`200`, `done: true`, `records: [{Id, Status}]`). Always use the non-Tooling query path for
> `BackgroundOperation`.

> **Column discipline:** on `BackgroundOperation`, only a few columns are queryable. `SELECT Id, Status`
> works. **Do NOT** select `JobType`, `CompletedDate`, or `NumErrors` — those columns do not exist on
> `BackgroundOperation` and return `INVALID_FIELD`. Use the SOQL string exactly as above; add fields
> only after confirming them via a describe.

`Status` values observed: `Scheduled` → `Queued` → `InProgress` (or `Running`) → `Complete` → `Error`.
For the self-service path, prefer the dedicated `GET /services/data/vXX.0/connect/self-service/site/status/{jobId}`
route instead of a `BackgroundOperation` query — it returns a typed `{status, siteUrl, error}` payload.

---

## Verification

List all Experience Cloud sites and confirm the new one is present and Builder-based:

```text
method: "GET"
url:    "/services/data/v67.0/connect/communities"
```

Each entry includes `siteAsContainerEnabled` — `true` means an **Experience Builder** (Aura/LWR)
site, `false` means Salesforce Tabs + Visualforce. Confirm the new site shows `true` and a non-null
`builderUrl`, and that `templateName` is not `Salesforce Tabs + Visualforce`.

---

## Gotchas

| Issue | Detail |
|-------|--------|
| Using `sf` CLI or project-codey | Not allowed. Every read/write goes through `mcp__headless-360__dispatch` / `dispatch_readonly`. |
| **Version prefix is required** | Pass `"/services/data/v67.0/connect/communities"`, **not** `"/connect/communities"`. Unlike project-codey, headless-360 does not resolve or add the version — a bare path returns `400 ROUTE_NOT_FOUND`. |
| `discover`/`describe` may not resolve create/list Connect API ops | `POST /connect/communities` and `GET /connect/communities/templates` are not individually indexed as describable operations in this corpus at time of writing. Dispatch the documented path directly instead of concluding the capability is missing. |
| `BackgroundOperation` via Tooling query | `GET /services/data/vXX.0/tooling/query` rejects `BackgroundOperation` with `400 INVALID_TYPE`. Use the plain `/services/data/vXX.0/query` endpoint instead. |
| `BackgroundOperation` columns | Only `Id`, `Status` are safe. `JobType`/`CompletedDate`/`NumErrors` → `INVALID_FIELD`. |
| Duplicate site name/prefix | `400 INVALID_INPUT "…already exists."` List `GET /services/data/vXX.0/connect/communities` and choose another. |
| Missing guest ESD | Self-service `POST` requires `guestEmbeddedServiceConfigId`; without one use the communities route with an Aura template. |
| URL prefix format | Alphanumeric only — no spaces or hyphens (`demosupportportal123`, not `demo-support-portal 123`). |
| `dispatch_readonly` is GET-only | Use `dispatch` for POST/PATCH/PUT/DELETE; `dispatch_readonly` rejects non-GET methods. |
| Credentials | Never fetch or print tokens / login URLs. The MCP session's bound org handles auth. |

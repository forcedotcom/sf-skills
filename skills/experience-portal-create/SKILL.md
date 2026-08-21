---
name: experience-portal-create
description: "Create / provision / set up a NEW Digital Experience (Communities) / Experience Cloud site — employee service, IT support, help desk, HR, customer, and partner portals — via the headless-360 MCP site-creation APIs. Use whenever a user asks to create/provision/set up a portal, site, or community, e.g.: 'create an employee service portal', 'create an IT Support Portal', 'create an Agentforce Employee Center', including wiring MIAW (Messaging for In-App/Web) at create. This is the site-CREATION skill and OWNS provisioning a new Aura OR LWR Experience Builder site from scratch — trigger it even when the user says 'Experience Builder site' or 'LWR site', as long as a NEW site is wanted. It always writes a portal-creation report as its final step (never ad hoc via CLI) and never makes a legacy Tabs+Visualforce site. DO NOT TRIGGER only for modifying an EXISTING site's pages/routes/theme/branding/guest-access metadata (experience-lwr-site-generate), existing-site customization (experience-ui-bundle), CMS, Commerce."
metadata:
  version: "1.0"
  domains: ["Experience"]
  minApiVersion: "67.0"
  relatedSkills:
    - "experience-lwr-site-generate"
  mcpTools:
    headless-360:
      tools: ["describe", "discover", "dispatch", "dispatch_readonly"]
      semver: ">=1.0.0"
  cliTools:
    - tool: ["sf"]
      semver: ">=2.0.0"
allowed-tools: |
  Read AskUserQuestion Bash
  mcp__headless-360__discover
  mcp__headless-360__describe
  mcp__headless-360__dispatch
  mcp__headless-360__dispatch_readonly
---

# Create Digital Experience Portal

Create a new Digital Experience (formerly Communities) portal/site in Salesforce. Supports employee service portals, partner portals (PRM), and general customer communities.

**Every operation runs through the headless-360 MCP server** (`mcp__headless-360__discover` →
`mcp__headless-360__describe` → `mcp__headless-360__dispatch` / `mcp__headless-360__dispatch_readonly`).
Do **not** use the Salesforce CLI (its `api request`, `data query`, or `org open` subcommands), the project-codey MCP
server, raw `curl`, or any other HTTP client — `dispatch`/`dispatch_readonly` is the only way this
skill talks to the org. See `references/mcp-invocation.md` for the exact call shapes.

## Scope

- **In scope**: Creating Digital Experience sites via the headless-360 Connect API dispatcher. Portal type selection. Basic configuration (name, URL, templates). Self-service portals with embedded service configs. **Making the site reachable end to end** — activating the Network (`status: Live`), adding member profiles, and publishing the Experience Builder pages (see `references/post-creation-activate-publish.md`).
- **Out of scope**: Deep post-creation customization (page layout/component authoring in Builder). Content authoring. Branding beyond initial setup. Individual per-user record management (membership is added at the profile/permission-set level, not per user).

---

## Execution model (read first)

Every org call is a **dispatch**: `mcp__headless-360__dispatch_readonly(url, method: "GET", queryParams)`
for reads, `mcp__headless-360__dispatch(url, method, body)` for writes; read `status_code` + `body` from
the response. To resolve the endpoint for a portal type, use `mcp__headless-360__discover(query=...)` and
`mcp__headless-360__describe(id=...)` as needed. Connect API create/list operations for Experience Cloud
are not always indexed by `discover`/`describe` — when a lookup returns nothing, dispatch the well-known
versioned Connect API path directly (see `references/mcp-invocation.md`) rather than concluding the
capability is missing.

**Critical: paths must include the full `/services/data/vXX.0/...` prefix** (e.g.
`"/services/data/v67.0/connect/communities"`) — unlike some other dispatchers, headless-360 does
**not** resolve or inject the API version for you. A path without the version prefix returns
`400 ROUTE_NOT_FOUND`. Copy the path verbatim from a `discover`/`describe` result when available;
otherwise use the version shown in this skill's examples (`v67.0` at time of writing) and adjust if
the org runs a different version. Full details, response envelope, job-monitoring, and gotchas live
in `references/mcp-invocation.md`.

---

## Clarifying Questions

Before proceeding, determine:

1. **Portal type?**
   - Employee Service / ITSM / HR / help desk → **prefer the `Agentforce Employee Center` Aura template** via the communities API (richest employee experience; Agentforce-ready). Use the self-service API instead when MIAW must be wired in at creation time and a guest ESD exists.
   - Partner Portal (PRM) → requires PRM feature enabled
   - Customer Community → general community creation (Aura or LWR Experience Builder template)

2. **Basic settings (required for all types):**
   - Portal name?
   - URL prefix? (must be alphanumeric only, no hyphens or spaces)
   - Description (optional)

3. **For Employee Service / Self-Service portals:**
   - `siteType`? → default `AURA` (Aura Experience Builder + Builder). Use `LWR` only if the user explicitly wants a Lightning Web Runtime site. **Never** create a Salesforce Tabs + Visualforce ("VF Template") site — those are legacy and have no Builder.
   - MIAW / Embedded Service Deployment ID(s)? These wire Messaging for In-App and Web into the portal at creation time. A **guest** ESD config is required by the self-service API; an **authenticated-user** ESD config is optional. If the user hasn't created an Embedded Service Deployment yet, point them to Setup → Embedded Service Deployments first.

4. **For Partner portals only:**
   - PRM template name? (check org-specific templates)

---

## Required Inputs

### Employee Service / Self-Service Portals (`POST /connect/self-service/site`):
- `siteName` (required) - portal name
- `guestEmbeddedServiceConfigId` (required) - Embedded Service Deployment (MIAW) config ID for **guest** users
- `embeddedServiceConfigId` (optional) - Embedded Service Deployment (MIAW) config ID for **authenticated** users
- `siteType` (optional) - `AURA` (default) or `LWR`. Produces an Experience Builder site. Do **not** use Visualforce.
- `enableForGuest` (optional) - whether guest (unauthenticated) users can access the site
- `contentDocumentId` (optional) - ContentDocument ID of a logo image to wire into the site's branding set
- `brandColors` (optional) - array of RGBA colors targeting `action`, `link`, `border`, `text`, `pageBackground`

> This API sets the URL path prefix automatically from the site name. There is no `templateName` — the framework is chosen with `siteType` (Aura/LWR), never Visualforce.

### Partner Portals (PRM):
- `siteName` (required)
- `siteUrlPrefix` (required)
- `prmTemplate` (required)
- `siteDesc` (optional)

### General Communities (`POST /connect/communities`):
- `name` (required)
- `urlPathPrefix` (required) - alphanumeric only, no hyphens
- `templateName` (required) - an **Experience Builder** template. Aura: `Agentforce Employee Center` (preferred for employee service), `Employee Portal`, `Customer Service`, `Help Center`, `Customer Account Portal`, `Partner Central`, `Build Your Own`. LWR: `Build Your Own (LWR)`, `Microsite (LWR)`. Validate the exact string via `GET /connect/communities/templates` (see below). Do **not** use `Salesforce Tabs + Visualforce` ("VF Template") — it is a legacy Visualforce site with no Builder.
- `description` (optional)

---

## Workflow

### Step 1: Determine API Based on Portal Type

1. **Employee Service / Self-Service** → `POST /connect/self-service/site`
   - Creates an **Aura** (or LWR) Experience Builder site — never Visualforce
   - Wires MIAW (Embedded Service Deployment) into the site at creation time
   - Prerequisites: `CustomizeApplication` permission; org has self-service site-creation API access; a guest Embedded Service Deployment exists

2. **Partner (PRM)** → `POST /connect/prm/setup/sites`
   - Prerequisites: `CommonPrmEnabled` feature

3. **General Community** → `POST /connect/communities`
   - Uses an Experience Builder `templateName` (Aura or LWR) — never `Salesforce Tabs + Visualforce`
   - Prerequisites: Manage Communities permission (`ManageNetworks`)

---

### Step 2: Create Portal (By Type)

#### Option A: Employee Service / Self-Service Portal

Use the self-service site API. It creates an **Aura Experience Builder** site (with the Builder option) by deploying CustomSite, Network, and ExperienceBundle metadata, then wires MIAW into the site via the given Embedded Service Deployment (ESD) config IDs. This is the correct path for ITSM / IT help desk / employee self-service portals.

**API Call** (via `mcp__headless-360__dispatch`):
```text
method: "POST"
url:    "/services/data/v67.0/connect/self-service/site"
body:
{
  "siteName": "<portal-name>",
  "siteType": "AURA",
  "guestEmbeddedServiceConfigId": "<guest-ESD-config-id>",
  "embeddedServiceConfigId": "<auth-ESD-config-id>",
  "enableForGuest": true
}
```
Poll with `GET /services/data/v67.0/connect/self-service/site/status/{jobId}` via `mcp__headless-360__dispatch_readonly`.

- `siteType` defaults to `AURA` (Aura Experience Builder + Builder). Pass `LWR` only if the user explicitly asks for a Lightning Web Runtime site. Never create a Visualforce site.
- `guestEmbeddedServiceConfigId` is **required** — it is the MIAW Embedded Service Deployment config ID for guest users. `embeddedServiceConfigId` (authenticated users) is optional. If the user has no Embedded Service Deployment yet, have them create one first (Setup → Embedded Service Deployments), or use the MIAW/embedded-service setup skill.
- Optional branding: `contentDocumentId` (logo) and `brandColors` (array of `{ "type": "action|link|border|text|pageBackground", "color": { "r": 0-255, "g": 0-255, "b": 0-255, "a": 0-1 } }`).

**Response:**
```json
{
  "success": true,
  "siteName": "IT Support Portal",
  "urlPathPrefix": "itsupport",
  "siteUrl": "https://domain.my.site.com/itsupport",
  "jobId": "708...",
  "status": "Queued"
}
```

**On success**, report `Success:` — the portal creation started (Aura + Experience Builder); give the
name, framework (Aura), `jobId`, and `status`, and note it is provisioning in the background
(Network, CustomSite, ExperienceBundle metadata + the Embedded Service/MIAW deployment). Next: monitor
the job (see 'Background Job Monitoring'), then complete Step 3 (Activate → Add Members → Publish).

**On failure**, report `Failure:` with the `{error}` — see the "Common Errors" section for the causes
(missing/invalid `guestEmbeddedServiceConfigId`, duplicate name/URL prefix, org lacks self-service
site-creation API access, missing `CustomizeApplication`) and their resolutions.

---

#### Option B: Partner Portal (PRM)

**API Call** (via `mcp__headless-360__dispatch`):
```text
method: "POST"
url:    "/services/data/v67.0/connect/prm/setup/sites"
body:
{
  "siteName": "<name>",
  "siteUrlPrefix": "<url-prefix>",
  "siteDesc": "<description>",
  "prmTemplate": "<template-name>"
}
```
Synchronous — no job polling.

**Response:**
```json
{
  "networkId": "0DB..."
}
```

**On success**, report `Success:` — the partner portal was created; give the name, `networkId`,
`siteUrlPrefix`, and `prmTemplate`. Next: find it at Setup → Digital Experiences → All Sites (by
Network ID), then complete Step 3 (Activate → Add Members → Publish).

**On failure**, report `Failure:` — see "Common Errors" (org lacks PRM/`CommonPrmEnabled`, invalid PRM
template name, duplicate name/URL prefix). PRM templates: Setup → Digital Experiences → Settings →
Partner Templates.

---

#### Option C: General Community

**First, discover valid templates** (required — accepted `templateName` strings vary by org edition/version), via `mcp__headless-360__dispatch_readonly`:
```text
method: "GET"
url:    "/services/data/v67.0/connect/communities/templates"
```
Response: `{ "templates": [ { "publisher": "Salesforce", "templateName": "Employee Portal" }, … ], "total": N }`. Use a returned `templateName` verbatim. Prefer an **Experience Builder** template (Aura or LWR). Never use `Salesforce Tabs + Visualforce`.

**API Call** (via `mcp__headless-360__dispatch`):
```text
method: "POST"
url:    "/services/data/v67.0/connect/communities"
body:
{
  "name": "<name>",
  "urlPathPrefix": "<url-prefix>",
  "description": "<description>",
  "templateName": "Agentforce Employee Center"
}
```
The body accepts only `{name, description, templateName, templateParams, urlPathPrefix}` — omit `templateParams` unless you need template-specific config.

For an **employee service / ITSM / HR portal**, prefer the **`Agentforce Employee Center`** template when the org's live template list includes it — it ships IT/HR ticketing, a self-service catalog, a knowledge base, and an Agentforce-ready experience. Fall back to `Employee Portal` (then `Customer Service`) for a plainer, non-Agentforce site. Other options by use case: `Help Center` (Aura knowledge/deflection), `Customer Account Portal` (Aura authenticated account self-service), `Partner Central` (Aura PRM), or `Build Your Own (LWR)` for a modern blank LWR site.

> **Agentforce Employee Center is two layers.** This `POST /connect/communities` call provisions the **site** only. The embedded **Agentforce conversational assistant** is a separate step — create the internal employee agent from its shipped template (`EmployeeCopilot__AgentforceEmployeeAgent`) via `PATCH /services/data/v67.0/headless/invoke/einstein/genai-agentbuilder/create-copilot-from-template` (`copilotContext.company` is **required**), then activate it and wire it to the site. This skill provisions the site and points the user to that step; full Agentforce setup is out of scope. See `references/templates.md`.

**Response:**
```json
{
  "jobId": "08P...",
  "message": "Your site is almost ready. To track the site creation status, query the BackgroundOperation object and enter the jobId as the Id.",
  "name": "Customer Community"
}
```

**On success**, report `Success:` — community creation started; give the name, `jobId`, and
`message`. Next: monitor the job (see 'Background Job Monitoring'), then complete Step 3 (Activate →
Add Members → Publish).

**On failure**, report `Failure:` — see "Common Errors" (invalid `templateName` — run
`GET /services/data/v67.0/connect/communities/templates` and use a returned value verbatim; duplicate
name/URL prefix; missing Manage Communities permission).

---

### Step 3: Make the Site Reachable — Activate, Add Members, Publish

**Creation only provisions the site** — it comes back `UnderConstruction`, admin-only, with
unpublished pages, so its URL is **not reachable** yet (the #1 "my portal doesn't work" cause).
Complete three steps, in order: (1) **Activate** — deploy the `Network` metadata with
`<status>Live</status>`; (2) **Add members** — add the target **profile(s)** to
`networkMemberGroups` (membership is profile-based, not per user; e.g. **`Unified Employee`** — a
Profile, not a UserRole) and redeploy (combinable with step 1); (3) **Publish** —
`sf community publish --name "<Site Name>"`, then poll the returned `jobId` on `BackgroundOperation`
until `Complete`. Then confirm `status: Live` and give the user the **login URL**
(`.../<prefix>/login`), not the bare prefix.

> **Tooling exception:** activate/members use the **Metadata API** (`Network` deploy) and publish
> uses **`sf community publish`** — there is no Connect API for these (`PATCH /connect/communities`
> returns 405). This is the one place the skill uses tools other than headless-360; Step 3 reads
> still go through headless-360.

**Exact commands, XML, verification queries, and gotchas: `references/post-creation-activate-publish.md`.**

---

### Step 4: Write the Portal Creation Report (always — final step)

**Always finish by writing a `report.md` summarizing what was done** — this is the skill's final,
non-optional action, whether the create call succeeded, is still provisioning, or failed. Write it to
the working/output directory as `report.md`.

The report must:
- Start with the heading `# Portal Creation Report`.
- State the **portal name**, the **API used** (`self-service/site`, `communities`, or `prm`) and
  **why** (e.g. "no guest ESD present → communities API"), the **framework** (Aura / LWR), and the
  **template** or `siteType` chosen.
- Give the **dispatched request** (path + key body fields) and the **response** (`jobId` /
  `networkId` / `siteUrl` / `status`, or the error).
- List the **remaining Step 3 work** (Activate → Add Members → Publish) and, for employee-service
  sites, note that the **embedded Agentforce agent is a separate follow-up step**.
- End with the sentinel line, exactly:
  `Task completed: portal creation dispatched — see report.md`

**Copy the template at `assets/report-template.md`** and fill in the portal-specific values.

---

## Template Recommendations

All recommendations produce **Experience Builder** sites (Aura or LWR). Never recommend `Salesforce Tabs + Visualforce` ("VF Template") — it is legacy and has no Builder.

| Use Case | API | Framework | Template / `siteType` |
|----------|-----|-----------|-----------------------|
| Employee service / ITSM / HR / help desk (richest; Agentforce-ready) | `communities` | Aura | `Agentforce Employee Center` |
| Employee service / help desk (MIAW at creation, guest ESD exists) | `self-service/site` | Aura | `siteType: AURA` (+ MIAW ESD config) |
| Employee service / help desk (plainer, no Agentforce) | `communities` | Aura | `Employee Portal` (fallback `Customer Service`) |
| Customer support / self-service community | `communities` | Aura | `Customer Service` |
| Knowledge base / case deflection | `communities` | Aura | `Help Center` |
| Authenticated account self-service | `communities` | Aura | `Customer Account Portal` |
| Partner portal (with PRM) | `prm/setup/sites` | Aura | Org-specific PRM template |
| Partner portal / channel (no PRM) | `communities` | Aura | `Partner Central` |
| Modern blank / headless-friendly site | `communities` | LWR | `Build Your Own (LWR)` |

**Modern recommendations:**
- For **employee service / ITSM / HR** portals, prefer the **`Agentforce Employee Center`** Aura template via the communities API — it ships the fullest employee experience (ticketing, catalog, knowledge, Agentforce-ready). The conversational assistant is a separate agent step (`EmployeeCopilot__AgentforceEmployeeAgent`). Use the **self-service site API** (`siteType: AURA`) instead when the portal needs MIAW wired in at creation time and a guest Embedded Service Deployment exists; use `Employee Portal` for a plainer, non-Agentforce site.
- For **customer communities**, use the **`Customer Service`** template (Aura, mobile-responsive) via the communities API.

See `references/templates.md` for complete template documentation.

---

## Background Job Monitoring

Portal creation is asynchronous (except PRM which is synchronous). Poll through
`mcp__headless-360__dispatch_readonly`.

**Self-service site path** — use the dedicated typed status route (preferred):
```text
method: "GET"
url:    "/services/data/v67.0/connect/self-service/site/status/{jobId}"
```
Returns `{success, siteName, urlPathPrefix, siteUrl, error, jobId, status}`.

**Communities path** — query `BackgroundOperation` via the **regular** REST query endpoint,
**not** `/tooling/query`:
```text
method:      "GET"
url:         "/services/data/v67.0/query"
queryParams: { "q": "SELECT Id, Status FROM BackgroundOperation WHERE Id = '<jobId>'" }
```

> **Tooling vs. regular query (verified gotcha):** `BackgroundOperation` is **not** a valid Tooling
> API sObject through this dispatcher — `GET /services/data/vXX.0/tooling/query` with that SOQL
> returns `400 INVALID_TYPE "sObject type 'BackgroundOperation' is not supported."`. Use the plain
> `/services/data/vXX.0/query` endpoint instead; it succeeds with the same SOQL string.

> **Column discipline:** on `BackgroundOperation`, select only `Id` and `Status`. `JobType`,
> `CompletedDate`, and `NumErrors` are **not** columns on this object and return `INVALID_FIELD`.
> Use the SOQL string above exactly.

**Job statuses:**
- `Queued` / `Scheduled` — waiting to start
- `InProgress` / `Running` — executing
- `Complete` — finished successfully
- `Error` — failed (check the `error` field on the status route)

---

## Verification

After creation completes:

1. **API (primary):** `mcp__headless-360__dispatch_readonly(url: "/services/data/v67.0/connect/communities", method: "GET")` lists all Experience Cloud sites. Find the new one and confirm `siteAsContainerEnabled: true` (Experience Builder — Aura/LWR) and a non-null `builderUrl`, and that `templateName` is **not** `Salesforce Tabs + Visualforce`. `siteAsContainerEnabled: false` means a legacy Visualforce site — the bug this skill exists to avoid.
2. **Setup UI (optional):** Setup → Digital Experiences → All Sites. The **Framework** column should show **Aura** (or LWR) — not Visualforce — with a **Builder** workspace link.
3. **Test URL:** Use `siteUrl` from the response (portal will be inactive initially).

**Note:** Portal must be activated and published before external users can access it.

---

## Rules / Constraints

| Constraint | Rationale |
|---|---|
| Portal creation is asynchronous | Deploys metadata and provisions resources in background |
| Site names must be unique | Each portal needs distinct name within org |
| URL prefixes must be unique | URL paths cannot conflict |
| URL prefixes must be alphanumeric | No hyphens, spaces, or special characters allowed |
| PRM requires PRM feature | Gated by licensing and org config |
| Created portals start inactive | Must manually activate/publish after creation |
| Paths must include the API version prefix | `dispatch`/`dispatch_readonly` do not inject `/services/data/vXX.0` — omitting it returns `400 ROUTE_NOT_FOUND` |

---

## Prerequisites by Type

### Employee Service / Self-Service:
- `CustomizeApplication` permission
- Communities/Digital Experience enabled
- Org has self-service site-creation API access enabled
- A **guest** Embedded Service Deployment (MIAW) config exists (its ID is required); optionally an authenticated-user ESD config

### Partner (PRM):
- Org has `CommonPrmEnabled`
- Portal creation permissions
- Valid PRM template name

### General Community:
- Manage Communities permission (`ManageNetworks`)
- Communities/Digital Experience enabled
- Valid template name

---

## Common Errors

### Invalid URL prefix:
"The URL can only contain alphanumeric characters. Remove hyphens, spaces, or special characters (e.g., 'employeeservice' not 'employee-service') and try a different prefix."

### Invalid template name (general community path):
"The specified template does not exist.

**Resolution:**
- Run `GET /services/data/v67.0/connect/communities/templates` and use a returned `templateName` verbatim
- Prefer an Experience Builder template: `Agentforce Employee Center` (employee service), `Employee Portal`, `Customer Service`, `Help Center`, `Customer Account Portal`, `Partner Central`, `Build Your Own`, `Build Your Own (LWR)`
- Template names are case-sensitive — match exactly
- Do NOT use `Salesforce Tabs + Visualforce` ("VF Template") — it is a legacy Visualforce site with no Builder"

### Missing guest Embedded Service config (self-service path):
"The self-service site API requires a guest Embedded Service Deployment config ID.

**Resolution:**
- Create an Embedded Service Deployment (MIAW) at Setup → Embedded Service Deployments, or use the MIAW/embedded-service setup skill
- Pass its config ID as `guestEmbeddedServiceConfigId` (and optionally `embeddedServiceConfigId` for authenticated users)"

### PRM not enabled:
"This org doesn't have Partner Relationship Management (PRM) enabled.

**Options:**
1. Contact Salesforce to enable PRM feature
2. Create a general community with the `Partner Central` template instead (via Communities API)"

### Duplicate name/URL:
"A portal with this name or URL prefix already exists (the communities API returns `400 INVALID_INPUT` — `Enter a different name. That one already exists.`).

**Check existing portals:** `mcp__headless-360__dispatch_readonly(url: "/services/data/v67.0/connect/communities", method: "GET")` and scan the `name` / `urlPathPrefix` fields.

Choose a different name or URL prefix."

### Missing permissions:
"You don't have permission to create portals.

**Required permissions:**
- Self-service portals: `CustomizeApplication`
- General communities: `ManageNetworks` (Manage Communities)

Contact your Salesforce admin to request these permissions."

### Route not found (missing version prefix):
"`400 ROUTE_NOT_FOUND` on a path that otherwise matches this skill's documentation. Confirm the `url` includes the full `/services/data/vXX.0/...` prefix — `dispatch`/`dispatch_readonly` require it verbatim and won't add it for you. If a specific version 404s, try the version shown in a recent `discover`/`describe` result for that org."

---

## Related Operations

**After creation:**
- Activate portal — Setup → Digital Experiences → All Sites → Activate
- Configure branding — Customize colors, logo, theme
- Add pages/components — Use Experience Builder
- Set up user access — Profiles, permission sets, sharing rules
- Publish portal — Make accessible to external users

**Manage existing:**
- List portals — `mcp__headless-360__dispatch_readonly(url: "/services/data/v67.0/connect/communities", method: "GET")`
- Update settings — Network Tooling API or Metadata API
- Deactivate — Via Setup UI

---

## Important Notes

1. **Creation is asynchronous** (except PRM) and only provisions — APIs return a job ID and the portal comes back `UnderConstruction`, member-less, and unpublished, so its URL is **not reachable** until you complete Step 3 (Activate → Add Members → Publish; see `references/post-creation-activate-publish.md`).
2. **URL prefix becomes the site path** — `https://<domain>.my.site.com/<prefix>` (serve/login at `.../<prefix>/login`, not the bare prefix).
3. **Embedded Service / MIAW configs must pre-exist** — This skill does not create Embedded Service Deployments. Create them separately at Setup → Embedded Service Deployments (or via the MIAW/embedded-service setup skill), then pass the config IDs to the self-service site API. For general communities, MIAW is added post-creation via an Embedded Service component in Experience Builder.
4. **Template names are case-sensitive** — Verify available templates in your org before attempting creation.
7. **discover/describe may not resolve a specific Connect API operation by id** — the headless-360 corpus indexes many operations as multi-step SORs rather than single endpoints, and some standard Connect API writes (e.g. `POST /connect/communities`) are not individually indexed. Do not conclude the capability is missing; dispatch the well-known, versioned Connect API path directly (documented in this skill).

---

## Reference Documentation

- `references/mcp-invocation.md` — **Read every session.** Exact `mcp__headless-360__*` call shapes, the version-prefix requirement, response envelope, job monitoring, `BackgroundOperation` column/endpoint discipline, and gotchas.
- `references/templates.md` — Available templates, template parameters, selection guide.
- `references/post-creation-activate-publish.md` — Step 3 (activate, add members, publish) to make the site reachable: the Metadata-API + `sf community publish` paths, the 405-on-PATCH gotcha, `NetworkMemberGroup` column discipline, and the login-URL note.
- `assets/report-template.md` — Step 4 `report.md` template to copy (heading, required fields, sentinel).

---

## API Type Classification

**Site creation** is dispatched through `mcp__headless-360__dispatch` / `mcp__headless-360__dispatch_readonly` (never project-codey or raw HTTP). All paths include the `/services/data/vXX.0` prefix. **Post-creation (Step 3) is the one exception:** activating the Network and adding members use the **Metadata API** (`sf project deploy start --metadata Network:...`), and publishing uses **`sf community publish`** — there is no Connect API for these (a `PATCH /connect/communities/<id>` returns 405). Reads/verification for Step 3 still go through headless-360. Creation paths:

- **Self-service portal:** Connect API `POST /services/data/vXX.0/connect/self-service/site` — asynchronous (poll `GET /services/data/vXX.0/connect/self-service/site/status/{jobId}`)
- **PRM portal:** Connect API `POST /services/data/vXX.0/connect/prm/setup/sites` — synchronous
- **General community:** Connect API `POST /services/data/vXX.0/connect/communities` — asynchronous (poll `BackgroundOperation` via `GET /services/data/vXX.0/query`, not `/tooling/query`)

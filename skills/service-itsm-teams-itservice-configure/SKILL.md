---
name: service-itsm-teams-itservice-configure
description: "Configure the \"Set Up Salesforce IT Service\" checklist for Microsoft Teams Employee Service (ITSM) — the employee side, covering app enablement, marketplace install guidance, user access assignment, and Digital Experience Site selection. Use this for: 'turn on Salesforce IT Service', 'set up IT Service on Teams', 'assign Teams for Employee permission set', 'give employees access to Teams for Employee Service', 'manage user access for Teams ITSM', 'grant users the permission sets needed for Teams Employee Service', 'select a digital experience site for Teams', 'install Salesforce IT Service app on Teams', or any request to complete the IT Service half of the Teams ITSM Go page checklist (including the Manage User Access step). DO NOT TRIGGER for the base Teams Salesforce Go page toggle or Azure/Entra app setup (service-itsm-teams-configure) or for the IT Desk/fulfiller half of the checklist (service-itsm-teams-itdesk-configure)."
metadata:
  version: "1.0"
  domains: ["Service", "Experience"]
  minApiVersion: "67.0"
  relatedSkills:
    - "experience-portal-create"
    - "service-itsm-channels-coordinate"
    - "service-itsm-teams-configure"
    - "service-itsm-teams-debug"
    - "service-itsm-teams-employee-agent-configure"
    - "service-itsm-teams-itdesk-configure"
  mcpTools:
    headless-360:
      tools: ["describe", "discover", "dispatch", "dispatch_readonly"]
      semver: ">=1.0.0"
  accessCheck:
    - type: "orgPref"
      value: "ITSMTeamsEnabled"
allowed-tools: |
  Read AskUserQuestion
  mcp__headless-360__discover
  mcp__headless-360__describe
  mcp__headless-360__dispatch
  mcp__headless-360__dispatch_readonly
---

# Set Up Salesforce IT Service (Microsoft Teams)

Complete the **"Set Up Salesforce IT Service"** checklist group on the Teams ITSM Go page
(`service-cloud-itsm-teams-integration`'s feature page) — the employee side of Teams ITSM
integration, for employees to create and manage their own tickets from Teams. Every operation
dispatches through **headless-360**.

## Scope

- **In scope**: Turning on the `OrgHasEmployeeServiceTeams` preference; giving the user the
  exact Teams marketplace link + help doc for the IT Service app install; assigning the
  `TeamsForEmployeeUser` permission set to confirmed users; selecting the
  Digital Experience Site to link with Teams via the `SLACK_PREFERRED_SITE` org value.
- **Out of scope**: The base Teams Salesforce Go page toggle (`ITSMTeamsEnabled`), Azure/Entra app
  registration, Named Credential population, and Teams extension/preferred-site registration —
  use `service-itsm-teams-configure` (a prerequisite for this skill). The IT Desk/fulfiller half
  of the checklist — use `service-itsm-teams-itdesk-configure`.

**Prerequisite:** run `service-itsm-teams-configure` first (or alongside) — this skill assumes
the `service-cloud-itsm-teams-integration` Go feature is already enabled.

> **Execute one step at a time.** These steps make real, state-changing API calls. Run a single
> operation, show its result, confirm it succeeded, then proceed — do not batch multiple setup
> calls into one parallel block.

---

## Workflow

### Step 1 — Turn on Salesforce IT Service

This is a straight org-preference toggle (unlike `ITSMTeamsEnabled`, this one supports direct
`PATCH`) — enable it yourself via API, do not ask the user to click the Setup toggle:

```text
mcp__headless-360__dispatch(
  method: "PATCH",
  url:    "/services/data/v67.0/setup/org/preferences/OrgHasEmployeeServiceTeams",
  body:   { "desiredState": true }
)
```

Expect `200 {"isPreferenceEnabled": true}`. Tell the user it's enabled — do not ask them to flip
the toggle themselves.

### Step 2 — Install Salesforce IT Service App on Teams (user's responsibility)

There is no Salesforce or Microsoft API this skill can call to install a Teams app into a
tenant's app catalog — this always requires a human clicking "Add" in the Microsoft Teams admin
center / AppSource, signed in with sufficient tenant permissions. Give the user the exact
marketplace link and help doc; do not attempt to automate this step.

- Marketplace (verified live from the Go page's "Go to Microsoft Marketplace" button):
  ```text
  https://marketplace.microsoft.com/en-us/product/teams-app/WA200009838?tab=Overview
  ```
- Help doc: `https://help.salesforce.com/s/articleView?id=service.it_srvcs_msteams_config_emplye_srvcs_app.htm&type=5`

Print both together. Also tell the user **the Microsoft email the employee signs in with must match
that Salesforce user's `Username`** (SSO maps MS UPN → `Username`; a mismatch fails login silently).
**Then HALT** until the user replies **"installed"** — a human-only action; do not proceed or
fabricate the confirmation.

### Step 3 — Manage User Access

"Manage User Access" ("Manage" button on the Go page) assigns the permission set — verified
live from the "Manage Microsoft Teams for Employee Service User Access" dialog:

- `TeamsForEmployeeUser` (label **"Teams for Employee"**, backed by PSL `TeamsForEmployeePsl`)

**Do not just assign every active user.** Ask the user which specific user(s) should get access.
If they want to see the list of users first (rather than naming them), page it — **show at most
10 users per page**, then ask "want to see more?" before showing the next page, since orgs can
have hundreds or thousands of users:

```text
mcp__headless-360__dispatch_readonly(
  method: "GET",
  url:    "/services/data/v67.0/query",
  queryParams: { "q": "SELECT Id, Name, Username, Email FROM User WHERE IsActive = true ORDER BY Name LIMIT 10 OFFSET <page * 10>" }
)
```

**Who to assign — warn the user up front:** the target must be a **real employee / UEL user** whose
**email exists on the Azure/Entra side** (a Microsoft account in the same tenant). Login is SSO
(MS UPN → the Salesforce `Username`), so assigning it to a user with no matching Azure account — or
a misaligned email/UPN — **fails login silently** (see the UPN↔`Username` note above). State this
before assigning; never assign system/integration accounts.

**Verified gotcha (spotting who NOT to pick):** in scratch/test orgs the first page(s) are often
dominated by non-employee accounts — e.g. `Automated Process`, `Bot User`, `Insights Integration`,
`*.ext` integration users, `ESW_*` / `*Site Guest User` guests, `DigitalAgent.*` agents — none are
employee/UEL users or have an Azure identity. Flag such rows as likely-not-employee (don't silently
filter — call them out); if the user says "not employee users, skip," move to the next page.

Once the user confirms specific user(s), look up the permission set's `Id` (it is stable per
org but don't hardcode it — query fresh):

```text
mcp__headless-360__dispatch_readonly(
  method: "GET",
  url:    "/services/data/v67.0/query",
  queryParams: { "q": "SELECT Id, Name FROM PermissionSet WHERE Name = 'TeamsForEmployeeUser'" }
)
```

Then assign the permission set to each confirmed user via `PermissionSetAssignment` (one record
per user — batch with as many calls as needed, there is no bulk-assign endpoint
exposed here):

```text
mcp__headless-360__dispatch(
  method: "POST",
  url:    "/services/data/v67.0/sobjects/PermissionSetAssignment",
  body:   { "AssigneeId": "<user id>", "PermissionSetId": "<permission set id>" }
)
```

Verify by re-querying `PermissionSetAssignment` for that `AssigneeId`, or simply trust the `201`
from the assignment call plus a `SELECT ... FROM PermissionSetAssignment WHERE AssigneeId =
'<user id>' AND PermissionSetId = '<permset id>'` readback.

#### Login prerequisites (required for the user to actually sign in to IT Service in Teams)

Assigning the permission set above is necessary but **not sufficient** — a UEL user who
opens the IT Service app in Teams can still hit a silent login failure unless all three of the
following are also in place. Verify (and set) these as part of enabling a user:

1. **"Allow OAuth for employees"** on the employee login profile (e.g. **Unified Employee**) —
   Setup → Profiles → *(profile)* → Session Settings → check **Allow OAuth for employees**.
   **Set this in the Setup UI.** It is **not** a Profile SObject field (no OAuth field appears in
   `Profile` describe) and it is **not** the Metadata element `Profile.sessionSettings.allowOauthForEmployees`
   — a Profile metadata deploy containing `<sessionSettings><allowOauthForEmployees>` **fails
   validation**: `Element {…}sessionSettings invalid at this location in type Profile` (verified
   Aug 2026). Nor is it readable/writable via the headless-360 Connect/REST/Tooling dispatch. Use
   the Setup UI checkbox. Confirmed blocker: with it off, the OAuth handshake for the embedded app
   fails and login silently does not complete — the community **login succeeds** (LoginHistory
   "Employee Login to Community" = Success) but **no `OauthToken` is ever minted** for the user, and
   the Teams app re-pops its "Single Sign-On / Login with URL" chooser (often with a
   `/…/setup/secur/RemoteAccessAuthorizationPage` "Service Not Available" popup).

2. **CORS Allowed Origins** must include **both** Teams origins. Check with
   `dispatch_readonly GET /services/data/v67.0/query` on
   `SELECT Id, UrlPattern FROM CorsWhitelistEntry`, and create any that are missing with
   `dispatch POST /services/data/v67.0/sobjects/CorsWhitelistEntry` body
   `{"UrlPattern": "<origin>"}` (this is a **data-API sobject**, not a Tooling type — a Tooling
   `POST`/query returns `NOT_FOUND`/`INVALID_TYPE`):
   - `https://teams.cloud.microsoft`
   - `https://cdn.scs.static.lightning.force.com` — the Lightning static-resource CDN the embedded
     IT Service surface loads from. Confirmed blocker: with this origin missing (even when
     `teams.cloud.microsoft` is present), the browser blocks the asset/OAuth preflight and login
     silently fails. After adding it, have the user hard-refresh / clear the Teams app cache.

3. **"API Enabled"** system permission on the user (`PermissionsApiEnabled = true`) via a
   permission set — not just the base profile — or the embedded app's API calls are rejected and
   the user can't sign in. Use the **same org-wide, created-once permset IT Desk uses** (commonly
   `Teams_Employee_ApiAccess`): query `PermissionSet WHERE Name = 'Teams_Employee_ApiAccess'`, and
   if absent create it once (`POST /sobjects/PermissionSet`
   `{"Name":"Teams_Employee_ApiAccess","Label":"Teams Employee API Access","PermissionsApiEnabled":true}`);
   then assign. Don't create a duplicate. See `service-itsm-teams-itdesk-configure`'s *Login
   prerequisite*.

If a user reports "can't log in to IT Service in Teams" and Steps 1–4 all look done, walk these
three prerequisites first — they are the most common silent-login blockers. For the full pass/fail
diagnostic sequence (including the OAuth-token-mint check that isolates a portal-user OAuth failure),
see [Troubleshooting: Teams for Employee Service login & agent](#troubleshooting-teams-for-employee-service-login--agent) below.

### Step 4 — Select a Digital Experience Site

This checklist item ("Digital Experience Site Name" dropdown, currently "None" until set)
reads/writes the org-value `SLACK_PREFERRED_SITE` — the same `OrgValueUtil.OrgValues` Java-enum
mechanism as Swarming's `SWARM_COLLABORATION_TOOL` — and is **not gated by any Teams license or
Azure/Entra credential**, so it works independently of the rest of the Teams setup.

1. List all Digital Experience sites in the org:
   ```text
   mcp__headless-360__dispatch_readonly(method: "GET", url: "/services/data/v67.0/connect/communities")
   ```
   **If the org has no Digital Experience site yet** (empty list), one must be created before this
   step can be completed — hand off to **`experience-portal-create`** to provision a new site (an
   employee-service / IT-support portal fits this use case), then return here with its `Id`.
2. Present the full list to the user and ask them to pick one. **If they don't choose, pick one
   yourself** (the only site if there's exactly one, otherwise a sensible default such as the most
   recently modified `Live` site) **and explicitly tell the user which one you picked** — don't
   proceed silently.
3. Check the current value first (skip the write if already set to the chosen site's Id):
   ```text
   mcp__headless-360__dispatch_readonly(method: "GET", url: "/services/data/v67.0/setup/org/values/SLACK_PREFERRED_SITE")
   ```
   `stringValue` holds the current selection — the chosen site's `Id`, or `"None"`.
4. Write the selection using the site's `Id` (from step 1's `connect/communities` response — the
   `Network` record Id, **not** `urlPathPrefix`):
   ```text
   mcp__headless-360__dispatch(
     method: "PATCH",
     url:    "/services/data/v67.0/setup/org/values/SLACK_PREFERRED_SITE",
     body:   { "orgValue": "<site Id>" }
   )
   ```
   Verified live: `PATCH` with a site's Network `Id` (e.g. `0DBSB000002EYwj4AG`) returned
   `200 {"stringValue": "<that Id>", ...}`, and a follow-up `GET` confirmed the same value
   persisted.
5. Re-run step 3's `GET` to confirm.

### Step 5 — Make the embedded Agentforce agent reply in Teams

Completing Steps 1–4 provisions the IT Service surface, but it does **not** make the embedded
Agentforce agent actually **reply** inside the Teams custom client ("Salesforce Employee Assist" /
"Ask AI Agent"). That is the final, hardest part of IT Service agent setup and is covered by a
dedicated skill:

**→ `service-itsm-teams-employee-agent-configure`**

Invoke it (or hand off to it) after Step 4 when the user wants the in-Teams agent to respond. It
covers the verified architecture — a Web channel with **User Verification ON + a `JWKS_URL` Key
Set**, the `Teams_AgentForce` deployment, an Omni-Flow routing flow to a **real, Active** agent, and
an **Agent Access permission set** on the portal user — plus the diagnostic for the common "agent
joins then leaves" symptom (auth ON but no Key Set, or missing Agent Access). The
per-user Agent Access assignment there is the natural follow-on to the Manage User Access step
(Step 3) above.

**Verified gotcha — UI shows stale "None" after the API write.** The Go page's dropdown is a wired
LDS cache over this org-value; a raw Connect `PATCH` doesn't invalidate it. The write is real and
durable (a follow-up `GET` confirms it) — if the Setup page is open, tell the user to **hard-refresh
the tab** to see the new selection.

**Naming is misleading — this is a shared, cross-feature setting, not Teams-exclusive.** Despite
the `SLACK_` prefix (a holdover from this org-value's original Slack-ITSM use case), it backs
the "Select a Digital Experience Site" picker on **both** the Teams ITSM Go page and the
equivalent Slack ITSM Go page — writing it from one surface changes what the other surface
shows. If the user has also configured Slack ITSM, flag that setting this will also change
Slack's preferred site.

---

## Gotchas

| Issue | Detail |
|-------|--------|
| Requires the Teams Salesforce Go page feature first | `OrgHasEmployeeServiceTeams` does not gate or depend on `ITSMTeamsEnabled` directly, but the Go page checklist only appears once `service-cloud-itsm-teams-integration` is enabled — run `service-itsm-teams-configure` first. |
| `OrgHasEmployeeServiceTeams` does not unblock `ITSMTeamsEnabled` | These are separate bits — enabling this preference does not itself unblock the Teams Salesforce Go page toggle preference, and vice versa. |
| "Select a Digital Experience Site" writes an org-value, not a Teams API | This checklist item writes the org-value `SLACK_PREFERRED_SITE` via `PATCH /services/data/v67.0/setup/org/values/SLACK_PREFERRED_SITE` (body `{"orgValue": "<site Id>"}`) — no Azure/Entra credential and no Teams license required. Verified live: `PATCH` with a site's Network `Id` succeeded (`200`) independently of the rest of the Teams setup. If the org has no Digital Experience site, create one first via `experience-portal-create`. Note despite the `SLACK_` name, this org-value is shared with the Slack ITSM integration's equivalent picker — not Teams-exclusive. |
| Permission sets / PSLs | `TeamsForEmployeeUser` (permission set) and PSL `TeamsForEmployeePsl` auto-provisioned and were confirmed `Active` (10 licenses) immediately after the feature-enable in this session — no manual PSL/permset creation needed once `TeamsITSrvcsAddOn`+`IncidentManagementAddOn` are licensed. |
| Version prefix required | headless-360 `dispatch`/`dispatch_readonly` do not resolve API versions — always pass the full `/services/data/vXX.0/...` prefix. |
| UEL user can't log in to IT Service in Teams | Assigning `TeamsForEmployeeUser` is not enough. Three additional prerequisites gate login (see [Step 3 → Login prerequisites](#login-prerequisites-required-for-the-user-to-actually-sign-in-to-it-service-in-teams)): **Allow OAuth for employees** on the login profile (**Setup-UI-only** — no working Metadata/SObject/Tooling write path; verified all fail), CORS Allowed Origins containing both `https://teams.cloud.microsoft` **and** `https://cdn.scs.static.lightning.force.com`, and the **API Enabled** system permission on the user. Each is independently a confirmed silent-login blocker. |

---

## Troubleshooting: Teams for Employee Service login & agent

When a user reports a Teams for Employee Service failure (can't log in, "Service Not Available"
popup, agent won't reply), run these checks **in order** — each is a pass/fail gate with an exact
query and remediation. Stop at the first one that fails; they are ordered from most-common and
cheapest to deepest.

> For a **broader** guided diagnosis across all Teams ITSM symptoms (IT Desk login, feature
> enablement, tab loading, service catalog, Agentforce, Swarming, SSO — not just IT Service login),
> use the dedicated **`service-itsm-teams-debug`** skill, which routes the reported problem
> to the matching pass/fail checklist. The sequence below is the IT-Service-login-focused subset.

> Run the read-only checks with `dispatch_readonly` (a Tooling-object check is noted where the
> query needs the Tooling API). Convert the placeholder ids to the real ones you find as you go.

### A. Community login itself

```text
SELECT LoginTime, Status, LoginType FROM LoginHistory
  WHERE UserId='<userId>' ORDER BY LoginTime DESC LIMIT 5
```

- **`No community access`** → the site's `Network.OptionsAllowInternalUserLogin` is off for an
  internal/UEL user. Enable "Allow internal users to log in directly" on the site's login settings
  (see the portal-create skill's internal-login flag). **Different failure** from the ones below —
  fix this first if present.
- **`Employee Login to Community` = `Success`** → login works; the failure is downstream in OAuth
  or agent runtime. Continue to B.

### B. The three silent-login prerequisites (see [Step 3 → Login prerequisites](#login-prerequisites-required-for-the-user-to-actually-sign-in-to-it-service-in-teams))

1. **Allow OAuth for employees** on the login profile (Setup-UI-only checkbox). No API read path —
   verify by the OAuth-token check in **C** below (its real symptom).
2. **CORS Allowed Origins** — must contain **both** origins:
   ```text
   SELECT Id, UrlPattern FROM CorsWhitelistEntry
   ```
   Missing `https://teams.cloud.microsoft` **or** `https://cdn.scs.static.lightning.force.com` →
   create it (`POST /sobjects/CorsWhitelistEntry` `{"UrlPattern":"<origin>"}`), then hard-refresh.
3. **API Enabled** system permission on the user (via a permission set, not just the profile).

### C. OAuth token mint — the decisive portal-user check

This is the check that isolates a portal/UEL OAuth failure from a login failure. After the user
retries login from a **fresh** Teams chat:

```text
SELECT Id, AppName, UserId, User.Username, CreatedDate FROM OauthToken
  WHERE AppName='ServiceCloudMSTeamsEca'
```

- **A token row exists for the failing user** → OAuth succeeded; the problem is agent-runtime, not
  login — jump to **E**.
- **No token for the failing user, but community login shows `Success` (B)** → the OAuth
  **authorize** step never minted a token. This is the "Service Not Available" popup on
  `/<sitePrefix>/setup/secur/RemoteAccessAuthorizationPage`. Work through **D**.

> **Diagnostic tell (verified):** if a **Standard-profile** user mints a `ServiceCloudMSTeamsEca`
> token but a **UEL / portal** user does not — even with identical permission sets — the blocker is
> the portal-user OAuth authorize path (profile OAuth flag, or the self-approval page served on the
> community host), **not** any ECA permission grant. In the verified org the Standard user minted a
> token with zero `SetupEntityAccess` rows while the UEL user holding everything did not, so
> ECA `SetupEntityAccess` config does **not** explain the difference.

### D. Portal-user OAuth authorize (self-approval page on the community host)

The `ServiceCloudMSTeamsEca` External Client App is **auto-installed by the Go-page toggle and needs
no configuration** — do **not** change its OAuth policy or add `SetupEntityAccess` rows. Symptom: the
Teams popup titled **"Service Not Available / An unexpected connection error occurred"** at
`/<sitePrefix>/setup/secur/RemoteAccessAuthorizationPage`, and/or an access-check error body
**`{"acc":8}`** on the streaming endpoint.

This failure is **portal/UEL-specific** and is **not** an ECA-permission problem (per the Diagnostic
tell above, a Standard user mints a token with zero `SetupEntityAccess` rows). The OAuth authorize is
being routed to the **community host** (`https://<org>.my.site.com/<prefix>/setup/secur/...`), which
can't render the self-approval page, rather than to My Domain. The ECA is **packaged/first-party** —
do NOT hand-edit its OAuth policy, `callbackUrl`, `isFirstPartyAppEnabled`, or `oauthLink`. Confirm
"Allow OAuth for employees" (B) and API Enabled (C) first; if the portal token still won't mint,
capture the popup URL + any `acc` code and escalate to the Teams ITSM product team — it's beyond a
configurable-setting fix.

### E. Embedded Agentforce agent joins then leaves (no reply)

If login + OAuth succeed but the "Ask AI Agent" agent won't reply, hand off to
`service-itsm-teams-employee-agent-configure` — the two verified fixes are (1) the `Teams_AgentForce`
channel's **User Verification ON backed by a `JWKS_URL` Key Set** and (2) an **Agent Access** permission set enabling the IT
Service Employee Agent on the portal user. That skill's reference has the full runtime-chain
diagnostics (scrt2 token, SSE 401, `ConversationEntry` queries).

---

## Related Skills

| Skill | When to use instead / alongside |
|-------|---------------------|
| `service-itsm-teams-configure` | Enabling the base Teams Salesforce Go page toggle, Azure/Entra app registration, Named Credential population, and Teams extension registration — a prerequisite for this skill |
| `service-itsm-teams-itdesk-configure` | The IT Desk/fulfiller half of the checklist (Turn on IT Desk, Install IT Desk app, Manage User Access, Set Teams as Collaboration Tool for Swarming) |
| `service-itsm-teams-employee-agent-configure` | The final part of IT Service agent setup — making the embedded Agentforce agent actually **reply** in the Teams custom client (Web channel, User Verification ON + `JWKS_URL` Key Set, `Teams_AgentForce` deployment, routing flow to a real Active agent, Agent Access permission set). Hand off to it after Step 4. |
| `service-itsm-teams-debug` | Diagnosing a failing Teams ITSM setup across any symptom (login, feature enablement, tab loading, Agentforce, Swarming, SSO) — routes the problem to a pass/fail checklist and reports remediation |
| `service-itsm-channels-coordinate` | Top-level menu across Teams, Slack, Swarming, Notifications, Portal |

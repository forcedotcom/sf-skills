---
name: service-itsm-teams-itdesk-configure
description: "Configure the \"Set Up Salesforce IT Desk\" checklist for Microsoft Teams Employee Service (ITSM) — the fulfiller/agent side, covering app enablement, marketplace install guidance, user access assignment, and Swarming collaboration-tool setup. Use this for: 'turn on Salesforce IT Desk', 'set up IT Desk on Teams', 'assign Teams for IT Desk permission set', 'set Teams as collaboration tool for swarming', 'install Salesforce IT Desk app on Teams', or any request to complete the IT Desk half of the Teams ITSM Go page checklist. DO NOT TRIGGER for the base Teams Salesforce Go page toggle or Azure/Entra app setup (service-itsm-teams-configure) or for the IT Service/employee half of the checklist (service-itsm-teams-itservice-configure)."
metadata:
  version: "1.0"
  domains: ["Service"]
  minApiVersion: "67.0"
  relatedSkills:
    - "service-itsm-channels-coordinate"
    - "service-itsm-swarming-configure"
    - "service-itsm-teams-configure"
    - "service-itsm-teams-itservice-configure"
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

# Set Up Salesforce IT Desk (Microsoft Teams)

Complete the **"Set Up Salesforce IT Desk"** checklist group on the Teams ITSM Go page
(`service-cloud-itsm-teams-integration`'s feature page) — the fulfiller/agent side of Teams
ITSM integration, for IT agents to swarm on and resolve tickets from Teams. Every operation
dispatches through **headless-360**.

## Scope

- **In scope**: Turning on the `OrgHasITSMFulfillerTeams` preference; giving the user the exact
  Teams marketplace link + help doc for the IT Desk app install; assigning
  `TeamsForITSrvcsUser`/`MicrosoftGraphAccess` permission sets to confirmed users; delegating
  "Set Teams as Collaboration Tool for Swarming" to `service-itsm-swarming-configure`.
- **Out of scope**: The base Teams Salesforce Go page toggle (`ITSMTeamsEnabled`), Azure/Entra app
  registration, Named Credential population, and Teams extension/preferred-site registration —
  use `service-itsm-teams-configure` (a prerequisite for this skill). The IT Service/employee
  half of the checklist — use `service-itsm-teams-itservice-configure`. Enabling the
  `service-cloud-swarming` Go feature itself — delegate to `service-itsm-swarming-configure`.

**Prerequisite:** run `service-itsm-teams-configure` first (or alongside) — this skill assumes
the `service-cloud-itsm-teams-integration` Go feature is already enabled.

> **Execute one step at a time.** These steps make real, state-changing API calls. Run a single
> operation, show its result, confirm it succeeded, then proceed — do not batch multiple setup
> calls into one parallel block.

---

## Workflow

### Step 1 — Turn on Salesforce IT Desk

This is a straight org-preference toggle (unlike `ITSMTeamsEnabled`, this one supports direct
`PATCH`) — enable it yourself via API, do not ask the user to click the Setup toggle:

```text
mcp__headless-360__dispatch(
  method: "PATCH",
  url:    "/services/data/v67.0/setup/org/preferences/OrgHasITSMFulfillerTeams",
  body:   { "desiredState": true }
)
```

Expect `200 {"isPreferenceEnabled": true}`. Tell the user it's enabled — do not ask them to flip
the toggle themselves.

### Step 2 — Install Salesforce IT Desk App on Teams (user's responsibility)

There is no Salesforce or Microsoft API this skill can call to install a Teams app into a
tenant's app catalog — this always requires a human clicking "Add" in the Microsoft Teams admin
center / AppSource, signed in with sufficient tenant permissions. Give the user the exact
marketplace link and help doc; do not attempt to automate this step.

- Marketplace (verified live from the Go page's "Go to Microsoft Marketplace" button):
  ```text
  https://marketplace.microsoft.com/en-us/product/teams-app/WA200009869?tab=Overview
  ```
- Help doc: `https://help.salesforce.com/s/articleView?id=service.it_srvce_msteams_cnfig_fulfilerhub_app.htm&type=5`

Print both together so the user has a self-service reference alongside the install link. Also tell
the user that **the Azure/Microsoft account email the fulfiller signs into Teams with must match
that Salesforce user's email / `Username`** — SSO resolves the Microsoft UPN to the Salesforce
`Username`, so a mismatch causes a silent login failure.

**Then HALT and wait** for the user to confirm the app is installed (they reply **"installed"**).
This is a human-only action; do not proceed to Step 3's user-access assignment as if it were done,
and do not fabricate the confirmation — wait for the real reply.

### Step 3 — Manage User Access

"Manage User Access" ("Manage" button on the Go page) assigns two permission sets — verified
live from the "Manage Microsoft Teams for Employee Service User Access" dialog:

- `TeamsForITSrvcsUser` (label **"Microsoft Teams for IT Services"**, backed by PSL
  `TeamsForITSrvcsPsl`)
- `MicrosoftGraphAccess` (label **"MicrosoftGraphAccess"**) — assigned alongside it in the same
  dialog.

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

**Verified gotcha:** in scratch/test orgs (and possibly some real orgs), the first page(s) of
this query are often dominated by non-employee system/integration accounts — e.g. `Automated
Process`, `Bot User`, `Insights Integration`, `*.ext` integration users, `ESW_*` / `*Site Guest
User` guest users, and `DigitalAgent.*` agent users. When presenting a page to the user, flag
these as likely-not-employee accounts (don't silently filter them out of the list — the user may
still want one assigned — but call out which rows look like system accounts so the user doesn't
have to guess). If the user says a listed batch is "not employee users, skip," move on to the
next page rather than assigning any of them.

Once the user confirms specific user(s), look up each permission set's `Id` (they are stable per
org but don't hardcode them — query fresh):

```text
mcp__headless-360__dispatch_readonly(
  method: "GET",
  url:    "/services/data/v67.0/query",
  queryParams: { "q": "SELECT Id, Name FROM PermissionSet WHERE Name IN ('TeamsForITSrvcsUser','MicrosoftGraphAccess')" }
)
```

Then assign both permission sets to each confirmed user via `PermissionSetAssignment` (one record
per user/permset pair — batch with as many calls as needed, there is no bulk-assign endpoint
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

#### Login prerequisite — the two Manage-User-Access permsets are NOT enough to sign in (verified)

Assigning `TeamsForITSrvcsUser` + `MicrosoftGraphAccess` provisions the IT Desk *surface*, but a
fulfiller who opens the IT Desk app in Teams can still hit **"server not reachable"** on the login
page. The verified root cause is the **`ServiceCloudMSTeamsEca` External Client App OAuth
authorize being denied** — `LoginHistory` for the user shows
`Application = ServiceCloudMSTeamsEca`, `Status = Failed: Not approved for access`
(`LoginType = Remote Access 2.0`). Neither `TeamsForITSrvcsUser` nor `MicrosoftGraphAccess` clears
this, because:

1. **They are not pre-authorized to the ECA.** The ECA's policy is `AdminApprovedPreAuthorized`
   (verified: `SELECT PermittedUsersPolicyType FROM ExtlClntAppOauthPlcyCnfg WHERE
   ExternalClientApplicationId = '<ecaId>'` — Tooling), so **only** users holding a permission set
   explicitly pre-authorized on the ECA can complete OAuth. Check which permset that is:
   `SELECT ParentId, Parent.Name FROM SetupEntityAccess WHERE SetupEntityId = '<ecaId>'` — in the
   verified org the sole authorized set was **`Teams_Employee_ApiAccess`**, and the IT Desk agent did
   not hold it.
2. **They do not grant API Enabled.** Both read `PermissionsApiEnabled = false`; the embedded app's
   Connect calls need the **API Enabled** system permission or they 403.

**Fix (verified to resolve the login):** also assign the fulfiller the **`Teams_Employee_ApiAccess`**
permission set — it is simultaneously the ECA-pre-authorized set **and** carries
`PermissionsApiEnabled = true`, so it clears both blockers in one assignment:

```text
mcp__headless-360__dispatch(
  method: "POST",
  url:    "/services/data/v67.0/sobjects/PermissionSetAssignment",
  body:   { "AssigneeId": "<user id>", "PermissionSetId": "<Teams_Employee_ApiAccess Id>" }
)
```

After assigning, have the user **fully close and reopen the Teams app** (the ECA authorize is cached
client-side). Also confirm **CORS Allowed Origins** contains both `https://teams.cloud.microsoft`
and `https://cdn.scs.static.lightning.force.com` (`SELECT UrlPattern FROM CorsWhitelistEntry`). If
login still fails in a fresh session after the ECA-authorized permset is assigned, the remaining
suspect is the **"Allow OAuth for employees"** profile checkbox (Setup-UI-only — no API write path).
See `service-itsm-teams-itservice-configure`'s *Login prerequisites* and its Troubleshooting
section D (ECA self-authorization) for the full pass/fail diagnostic chain — the same ECA gates both
the fulfiller (IT Desk) and employee (IT Service) apps.

### Step 4 — Set Teams as Collaboration Tool for Swarming (delegate)

This 4th checklist item requires the `service-cloud-swarming` Go feature to be enabled first.
**Do not enable that feature inline here — invoke the dedicated
`service-itsm-swarming-configure` skill** instead of duplicating feature-enablement logic:

```text
Invoke the service-itsm-swarming-configure skill.
```

That skill enables `service-cloud-swarming` **and** writes `SWARM_COLLABORATION_TOOL` to `"Teams"`
via `PATCH /services/data/v67.0/setup/org/values/SWARM_COLLABORATION_TOOL` — this checklist item
is now fully automated end-to-end, no manual "Go to Feature Page" click required.

---

## Gotchas

| Issue | Detail |
|-------|--------|
| Requires the Teams Salesforce Go page feature first | `OrgHasITSMFulfillerTeams` does not gate or depend on `ITSMTeamsEnabled` directly, but the Go page checklist only appears once `service-cloud-itsm-teams-integration` is enabled — run `service-itsm-teams-configure` first. |
| `OrgHasITSMFulfillerTeams` does not unblock `ITSMTeamsEnabled` | These are separate bits — enabling this preference does not itself unblock the Teams Salesforce Go page toggle preference, and vice versa. |
| "Set Teams as Collaboration Tool for Swarming" needs `service-cloud-swarming` enabled first | Delegate to `service-itsm-swarming-configure` rather than enabling that feature inline. That skill both enables the feature and writes `SWARM_COLLABORATION_TOOL` to `"Teams"` — the whole checklist item is API-reachable, not just the base feature enable. |
| Permission sets / PSLs | `TeamsForITSrvcsUser`, `MicrosoftGraphAccess` (permission sets) and PSL `TeamsForITSrvcsPsl` auto-provisioned and were confirmed `Active` (10 licenses) immediately after the feature-enable in this session — no manual PSL/permset creation needed once `TeamsITSrvcsAddOn`+`IncidentManagementAddOn` are licensed. |
| Manage-User-Access permsets don't cover login — assign `Teams_Employee_ApiAccess` too | Verified: after assigning `TeamsForITSrvcsUser` + `MicrosoftGraphAccess`, the IT Desk agent still failed Teams login with **"server not reachable"**; `LoginHistory` showed `ServiceCloudMSTeamsEca` = **"Failed: Not approved for access."** The `ServiceCloudMSTeamsEca` ECA is `AdminApprovedPreAuthorized` and its only pre-authorized permset was `Teams_Employee_ApiAccess`; neither Manage-User-Access set is authorized on the ECA, and both have `PermissionsApiEnabled = false`. Assigning `Teams_Employee_ApiAccess` (ECA-pre-authorized **and** grants API Enabled) resolved the login. See [Step 3 → Login prerequisite](#login-prerequisite--the-two-manage-user-access-permsets-are-not-enough-to-sign-in-verified). |
| Version prefix required | headless-360 `dispatch`/`dispatch_readonly` do not resolve API versions — always pass the full `/services/data/vXX.0/...` prefix. |

---

## Related Skills

| Skill | When to use instead / alongside |
|-------|---------------------|
| `service-itsm-teams-configure` | Enabling the base Teams Salesforce Go page toggle, Azure/Entra app registration, Named Credential population, and Teams extension registration — a prerequisite for this skill |
| `service-itsm-teams-itservice-configure` | The IT Service/employee half of the checklist (Turn on IT Service, Install IT Service app, Manage User Access, Select a Digital Experience Site) |
| `service-itsm-swarming-configure` | Enabling the `service-cloud-swarming` Go feature for "Set Teams as Collaboration Tool for Swarming" — this skill delegates to it rather than duplicating that logic |
| `service-itsm-channels-coordinate` | Top-level menu across Teams, Slack, Swarming, Notifications, Portal |

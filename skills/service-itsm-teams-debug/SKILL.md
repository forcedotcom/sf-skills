---
name: service-itsm-teams-debug
description: "Debug and diagnose Microsoft Teams for Employee Service (ITSM) configuration failures — run a pass/fail validation checklist against the org and report exact remediation. Use this for: 'IT Desk login not working in Teams', 'UEL/CCP user can't log in to IT Service', 'Teams feature not showing / not enabled', 'CI Hub / Service Catalog / My Assets tab not loading', 'Teams Agentforce agent not responding', 'Teams swarming not working', 'Teams SSO failing', or any request to troubleshoot a Teams ITSM setup. Routes the problem to the right checklist (login, feature enablement, tab loading, Agentforce, swarming, SSO) and checks the exact CORS, External Client App, feature toggle, PSL, profile, auth-provider, named-credential, and messaging-channel settings each requires. DO NOT TRIGGER for first-time enablement (service-itsm-teams-configure / -itservice-configure / -itdesk-configure) or building the embedded agent from scratch (service-itsm-teams-employee-agent-configure)."
metadata:
  version: "1.0"
  domains: ["Service"]
  minApiVersion: "62.0"
  relatedSkills:
    - "service-itsm-channels-coordinate"
    - "service-itsm-teams-configure"
    - "service-itsm-teams-employee-agent-configure"
    - "service-itsm-teams-itdesk-configure"
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

# Troubleshoot Microsoft Teams for Employee Service (ITSM)

When someone reports a **Microsoft Teams for Employee Service** failure — can't log in, a tab
won't load, the feature isn't showing, the Agentforce agent won't reply, swarming or SSO is
broken — this skill connects to the org, runs the **pass/fail checklist for that specific
problem**, and reports each setting's actual value plus the exact Setup path to fix any that are
wrong. It replaces "check every setting by hand" with a targeted, verified diagnosis.

Every read dispatches through **headless-360** (`dispatch_readonly` for queries, `dispatch` only
for the optional swarming-token clear). No org password is needed.

## Scope

- **In scope:** Diagnosing an already-attempted Teams ITSM setup that is failing. Routing the
  reported symptom to the right checklist and checking the exact settings it requires (CORS,
  External Client App, feature toggles, PSLs, profile session settings, auth provider, named
  credentials, messaging channel, Agentforce agent).
- **Out of scope:** First-time enablement (use `service-itsm-teams-configure` /
  `-itservice-configure` / `-itdesk-configure`), building the embedded agent from scratch (use
  `service-itsm-teams-employee-agent-configure`), and non-Teams Salesforce debugging.

> **Read-only by default.** Every check is a `dispatch_readonly` query — running the full
> checklist changes nothing. The only state-changing action is the optional swarming OAuth-token
> clear at the very end, and only with explicit user confirmation.

---

## Step 1 — Identify the problem and collect inputs

Ask the user for their **problem description** if not already given. Match it to a checklist using
the **Feature Map** in [`references/configuration-checklists.md`](references/configuration-checklists.md).

Some problems need extra inputs — ask for them up front:

| Problem type | Extra input to collect |
|---|---|
| Generic "login" (no app named) | Ask **which app** — IT Desk or IT Service |
| IT Desk login | End-user's Salesforce username (the person who can't log in) |
| IT Service login | **CCP or UEL user?**, then that end-user's Salesforce username |
| Agentforce not replying | Employee Experience Site URL |
| Swarming | End-user's username; Azure AD **Tenant ID** (optional — enables the Azure app check) |
| SSO | Azure AD **Tenant ID** (optional); optionally which app + end-user username |

Do **not** run the agent-specific checks until you have the mandatory inputs for that checklist
(e.g. don't skip asking for the end-user username on a login issue — the per-user checks are
`MANUAL_CHECK_REQUIRED` without it).

## Step 2 — Route to the checklist

Pick the checklist from the Feature Map, then run its checks **in order** from
[`references/configuration-checklists.md`](references/configuration-checklists.md):

| Symptom | Checklist |
|---|---|
| IT Desk login | `LOGIN_DESK` |
| IT Service login — UEL user | `LOGIN_SERVICE_UEL` |
| IT Service login — CCP user | `LOGIN_SERVICE_CCP` |
| Generic login (app unknown) | `LOGIN` (then ask which app) |
| Feature not showing / not enabled | `MSTEAMS_CORE` |
| Tab won't load (CI Hub, Service Catalog, Employee Enablement, My Assets) | `TAB_LOADING` |
| Lightning app not embedding / blank tab | `LIGHTNING_OUT` |
| Agentforce agent not replying | `AGENTFORCE` |
| Swarming | `SWARMING` |
| Single Sign-On | `SSO` (+ the app-specific login checklist if an app is named) |

When an app is named for an SSO issue, run **both** the `SSO` checklist and the matching login
checklist (`LOGIN_DESK` / `LOGIN_SERVICE_CCP` / `LOGIN_SERVICE_UEL`) — skip duplicate checks.

## Step 3 — Run the checks

Execute each check's query via `dispatch_readonly` (queries and API fields are spelled out in the
reference). Record for each check: a **status** and the **configured value** actually read from
the org.

| Status | Render as | Meaning |
|---|---|---|
| `OK` | OK | Correctly configured |
| `MISCONFIGURED` / `MISSING` / `DISABLED` / `ERROR` | FAIL | Needs fixing — include the exact Setup path from the reference |
| `MANUAL_CHECK_REQUIRED` | MANUAL | Needs manual verification (or a missing optional input like Tenant ID/username) — never render this as FAIL |

## Step 4 — Report

Render a table with **all four columns** — `#`, `Check`, `Status`, **`Configured Value`** (never
omit the configured value), plus an `Action Required` note carrying the remediation for any
failed check. End with a one-line summary: `N passed | N failed | N require manual verification`.

- **All passed:** tell the user the Salesforce backend is correctly configured; if the problem
  persists, reload the Teams app (**⋯** on the IT Desk/IT Service app → **Reload app**).
- **Any failed:** don't add the reload note — the per-check `Action Required` steps are the fix.

The full report-rendering rules, special-case notes, the example report layout, and the optional
swarming OAuth-token clear are in
[`references/report-generation.md`](references/report-generation.md).

---

## Gotchas (verified)

| Issue | Detail |
|---|---|
| The Teams ECA DeveloperName is `ServiceCloudTeamsEca` | The External Client App the login checks look for is `ServiceCloudTeamsEca`. (A per-org packaged instance may surface under a related name such as `ServiceCloudMSTeamsEca`; match on the ECA that backs the Teams login, and treat a missing app as "turn the feature off and on again.") |
| "Allow OAuth for employees" is **Metadata-API-only** for reading, and **Setup-UI-only** to change | Read via SOAP `listMetadata(ProfileSessionSetting)` → `readMetadata` on the fullName containing `unified`; field `allowOauthForEmployees` (`true`=enabled, `false`=disabled, absent=never configured). It is **not** on `Profile` describe and **not** REST/Tooling-queryable. To set it, use Setup → Profiles → *(employee profile)* → Session Settings. **UEL users only.** |
| CORS check reads `IsOauthCorsPolicyEnabled`, allowed origins read `CorsWhitelistEntry.UrlPattern` | Both `https://cdn.scs.static.lightning.force.com` **and** `https://teams.cloud.microsoft` must be present. |
| Feature toggles are read via the FulfillerApp permissions Connect API | `GET /connect/it-service/permissions/FulfillerApp` returns the org/user feature flags; a `FUNCTIONALITY_NOT_ENABLED` error means the `IServiceItsmTeamsFamily` family is off at the org level. |
| Agentforce user-verification fields need **SOAP v62+** | `MessagingChannel.embeddedConfig` (`authMode`, `messagingAuthorizations.*`) is silently omitted by SOAP v60 — use v62+. |
| Version prefix required | headless-360 `dispatch`/`dispatch_readonly` don't resolve API versions — always pass the full `/services/data/vXX.0/...` prefix. |

## Related Skills

| Skill | When to use instead |
|---|---|
| `service-itsm-teams-configure` | First-time enablement of the base Teams Go page toggle, Azure/Entra app, Named Credential, extension registration |
| `service-itsm-teams-itservice-configure` | Completing the IT Service (employee) enablement checklist |
| `service-itsm-teams-itdesk-configure` | Completing the IT Desk (fulfiller) enablement checklist + Swarming collaboration tool |
| `service-itsm-teams-employee-agent-configure` | Building the embedded Agentforce agent from scratch so it replies in Teams |
| `service-itsm-channels-coordinate` | Top-level menu across Teams, Slack, Swarming, Notifications, Portal |

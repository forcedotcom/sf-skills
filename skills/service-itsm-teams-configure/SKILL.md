---
name: service-itsm-teams-configure
description: "Enable Microsoft Teams for Employee Service (ITSM) in Salesforce — the Salesforce Go feature service-cloud-itsm-teams-integration gating Teams-based IT Desk and IT Service collaboration. Use this for: 'enable Teams for employee service', 'turn on ITSM Teams integration', 'enable Microsoft Teams for IT Service', 'set up Salesforce IT Desk Teams app', 'enable ITSMTeamsEnabled', 'why can't I enable the Teams org preference', or any request to enable/verify this Salesforce Go feature. DO NOT TRIGGER for configuring the TeamsNotifications notification-channel preference or for enabling the Swarming feature itself (service-itsm-swarming-configure)."
metadata:
  version: "1.0"
  domains: ["Service"]
  minApiVersion: "67.0"
  relatedSkills:
    - "experience-portal-create"
    - "service-itsm-channels-coordinate"
    - "service-itsm-swarming-configure"
    - "service-itsm-teams-employee-agent-configure"
    - "service-itsm-teams-itdesk-configure"
    - "service-itsm-teams-itservice-configure"
  mcpTools:
    headless-360:
      tools: ["describe", "discover", "dispatch", "dispatch_readonly"]
      semver: ">=1.0.0"
  cliTools:
    - tool: ["sf"]
      semver: ">=2.0.0"
  accessCheck:
    - type: "orgPerm"
      value: "MSTeamsSetupAutomationAccess"
allowed-tools: |
  Read AskUserQuestion Bash
  mcp__headless-360__discover
  mcp__headless-360__describe
  mcp__headless-360__dispatch
  mcp__headless-360__dispatch_readonly
---

# Enable Microsoft Teams for Employee Service (ITSM)

Enable the Salesforce Go feature **"Microsoft Teams for Employee Service"**
(`service-cloud-itsm-teams-integration`) — the feature that lets IT Desk and IT Service
agents track tickets, request catalog items, and get Agentforce assistance from inside
Microsoft Teams. Every operation dispatches through **headless-360**.

> **Execute one step at a time.** These steps make real, state-changing API calls. Run a single
> operation, show its result, confirm it succeeded, then proceed — do not batch multiple setup
> calls into one parallel block.

## Scope

- **In scope**: Enabling the `service-cloud-itsm-teams-integration` Go feature via its
  feature-enablement Connect API; verifying feature and `ITSMTeamsEnabled` preference state
  afterward; explaining why the direct org-preference PATCH route fails and why this route
  works instead; disabling the feature if requested; giving the user step-by-step instructions
  for the Azure/Entra app registration (Step 4a) since no Salesforce API can perform that part;
  once the user provides the resulting Client ID/Tenant ID (in chat) and the Client Secret (written
  to a gitignored secret file via the copy-paste command in Step 4a, never in chat), writing them
  directly into the `MSTeamsSetupClientCredentialsEC` Named Credential via API — this
  Salesforce-side write is always automated by this skill, never deferred back to the user;
  registering the Experience Cloud site as the Teams "preferred site" extension via
  `/connect/service-itsm-teams/graph-api/extensions` once that credential exists.
- **Out of scope**: Notification-channel preferences (`Notifications`, `TeamsNotifications`) —
  a separate concern from this feature. Enabling the `service-cloud-swarming` Go feature itself —
  delegate to `service-itsm-swarming-configure`. The IT Desk/fulfiller checklist group (Turn on
  IT Desk, Install IT Desk app, Manage User Access, Set Teams as Collaboration Tool for
  Swarming) — delegate to `service-itsm-teams-itdesk-configure`. The IT Service/employee
  checklist group (Turn on IT Service, Install IT Service app, Manage User Access, Select a
  Digital Experience Site) — delegate to `service-itsm-teams-itservice-configure`. Portal/site
  creation — use `experience-portal-create`. The actual Azure-side actions (clicking through the
  Azure portal, generating the client secret, granting Microsoft admin consent) must be
  performed by the user in the Microsoft admin center — no Salesforce API reaches Azure/Entra —
  but this skill still provides the exact instructions for those steps (see Gotchas and Step 4a)
  rather than treating them as someone else's problem.

---

## The problem this skill solves

`ITSMTeamsEnabled` is the Salesforce Go page toggle preference gating Microsoft Teams ITSM integration. Its
UDD definition (`ServiceItsmTeams.settings.xml`) declares `orgAccess="always"` but has **no
`editAccess` attribute** — unlike working preferences such as `Notifications`/`TeamsNotifications`,
which explicitly set `editAccess="always"`. As a result, the direct Setup preferences Connect
API route is blocked:

```text
GET  /services/data/vXX.0/setup/org/preferences/ITSMTeamsEnabled
PATCH /services/data/vXX.0/setup/org/preferences/ITSMTeamsEnabled  body: {"desiredState": true}
```

Both return `401`:
```json
{"error_code":"API_ERROR","status_code":401,"body":"[{\"errorCode\":\"INSUFFICIENT_ACCESS\",\"message\":\"Cannot read data!\"}]"}
```
(`"Cannot update preference value!"` on the PATCH). This is a real, code-level access gate
(`StandardMetadataChecker` in `setup-connect-impl` relays an Aura `NoAccessException` — "bit(s)
do not have READ/WRITE access" — for this preference specifically), **not** a version-prefix or
routing mistake. Do not retry this route with different API versions or bodies.

**The verified working path is different: enable the Go *feature*, not the preference
directly.** The Salesforce Go feature-enablement Connect API sits behind a different access
check and, on enable, flips `ITSMTeamsEnabled` (and related feature state) as a side effect.

---

## Workflow

### Step 1 — Check current feature status

```text
mcp__headless-360__dispatch(
  method: "POST",
  url:    "/services/data/v67.0/connect/setup/discovery/features/status",
  body:   { "featureApiNames": ["service-cloud-itsm-teams-integration"] }
)
```

Response shape:
```json
{
  "items": [
    {
      "apiName": "service-cloud-itsm-teams-integration",
      "status": "ENABLED",          // or "NOT_ENABLED" / "DISABLED"
      "blockedByApexLock": false,
      "dependencyStatuses": [],
      "enableBlockedReasons": [],
      "disableBlockedReasons": []
    }
  ]
}
```

If `status` is already `"ENABLED"`, skip to Step 3 (verification) — do not re-enable.
If `enableBlockedReasons` is non-empty, surface those reasons to the user (typically a missing
license/add-on) before attempting Step 2.

### Step 2 — Enable the feature

```text
mcp__headless-360__dispatch(
  method: "POST",
  url:    "/services/data/v67.0/connect/setup/discovery/feature/service-cloud-itsm-teams-integration/enable",
  body:   {}
)
```

**Known gotcha (verified):** this call can return `500 INTERNAL_ERROR` even when the feature
successfully ends up `ENABLED`. Do not treat a `500` here as a hard failure — always re-run
Step 1 (`features/status`) and Step 3 (`ITSMTeamsEnabled` read) afterward to check actual state
before reporting failure to the user. If status still shows `NOT_ENABLED` after retrying once,
then report the failure with the raw error.

### Step 3 — Verify `ITSMTeamsEnabled` flipped

```text
mcp__headless-360__dispatch_readonly(
  method: "GET",
  url:    "/services/data/v67.0/setup/org/preferences/ITSMTeamsEnabled"
)
```

Expect `200 {"isPreferenceEnabled": true}`. This confirms the underlying preference — otherwise
inaccessible via direct PATCH — is now enabled as a side effect of the feature enable.

### Step 4 — Report *interim* status (setup is NOT complete yet)

Report feature status and whether `ITSMTeamsEnabled` reads `true` — but **frame this as progress,
not completion.** Enabling the Go feature is only the first half; the integration is **not
functional** until the Microsoft Entra app is registered, its credentials are written into the Named
Credential + Auth Provider, and admin consent is granted (Step 4a). Do **not** mark Teams
"Done"/"complete" or hand back to a coordinator as done. State plainly: *"The Salesforce feature is
enabled; Teams integration is not yet complete — the Microsoft Entra app registration comes next."*
Then proceed into Step 4a. See the **Completion contract** below for what "complete" requires.

### Step 4a — Follow the Go page's own order: Create Entra app → Configure Named Credentials → Grant consent

The Salesforce Go feature page (Setup → Salesforce Go → this feature,
`.../lightning/setup/page/feature/service-cloud-itsm-teams-integration/home?topic=SalesforceGo`)
renders a **"Complete the Required Steps" → "Integrate Salesforce with Teams"** checklist with
exactly three items, in this order — verified from a live screenshot of the page. Follow this
order; do not skip ahead to Named Credentials before the Entra app exists, and do not treat
"Grant Azure Administrator Consent" as optional:

1. **Create Microsoft Entra ID App** ("Set Up Microsoft Entra ID App" button — opens
   portal.azure.com). There is no Salesforce API for this sub-step; give the user these exact
   clicks and wait for them to provide the resulting values:
   - **portal.azure.com** → **Microsoft Entra ID** → **App registrations** → **New registration**.
     Name it something identifiable (e.g. `Salesforce ITSM Teams Integration`); single-tenant is
     fine unless the user's org spans multiple tenants. Leave the redirect URI blank at creation —
     the Delegated Graph permissions below require one, but it's added later as the Auth Provider
     callback (Step 5; see `references/azure-credential-population.md`).
   - From the app's **Overview** page, note the **Application (client) ID** and **Directory
     (tenant) ID**.
   - **Certificates & secrets** → **New client secret** → copy the secret **value** immediately
     (unrecoverable after leaving the page).
   - **API permissions** → **Add a permission** → **Microsoft Graph** → **Delegated
     permissions** → add all 17 below, then click **Grant admin consent** so every row reads
     *Granted*. These are **Delegated** (not Application) — verified working set:
     `Channel.Create`, `Channel.ReadBasic.All`, `ChannelMember.Read.All`,
     `ChannelMember.ReadWrite.All`, `ChannelMessage.Edit`, `ChannelMessage.Read.All`,
     `ChannelMessage.ReadWrite`, `ChannelMessage.Send`, `Team.Create`, `Team.ReadBasic.All`,
     `Group.Read.All`, `Group.ReadWrite.All`, `openid`, `profile`, `email`, `offline_access`,
     `User.Read`. Several require admin consent (*Admin consent required = Yes*), so the **Grant
     admin consent** click is mandatory — ungranted consent-required rows make Teams calls fail
     (see the AccessDenied gotcha). Do **not** add `TeamworkAppSettings.ReadWrite.All` (not in the
     working set). Scopes can change between releases — if MS docs list more, add and re-grant.
   - Provide the credentials **without exposing the secret in chat**: **Client ID** and **Tenant
     ID** are non-secret and may be given in the conversation; the **Client Secret is confidential —
     NEVER ask for it in chat.** Have the user write it to a **gitignored file**: substitute the
     job/temp path for `<secret-file>` (e.g. `$CLAUDE_JOB_DIR/tmp/teams-secret`), then hand them exactly
     this to copy-paste into the Claude Code prompt (secret Value, not the Secret ID, between the quotes):
     ```bash
     ! umask 077; printf '%s' 'PASTE-CLIENT-SECRET-HERE' > <secret-file> && echo written
     ```
     Keep the leading `!` — it runs the line in this session's Bash so the file persists. It prints
     `written`; then read it from `<secret-file>` at write time (Step 5) and never echo or log it.
     > **Note:** the `!`-prefix line is echoed into the chat transcript — if the secret shows up there,
     > treat it as compromised and have the user rotate it in Azure after setup works.
2. **Configure Setup Named Credentials** ("Go to Setup" button on the Go page — the manual
   equivalent of what this skill automates). **Once you have the Client ID / Tenant ID and the
   secret is available in the secret file, do not tell the user to enter anything into Setup —
   call the Named Credential APIs directly**, per "Populating `MSTeamsSetupClientCredentialsEC`
   given a user-supplied client ID/secret" under Step 5 below. **This same set of values must ALSO be written into the
   `microsoft_auth_provider` Auth Provider** (the inbound-SSO side, distinct from the outbound-Graph
   Named Credential) — the org provisions this Auth Provider empty. Do this automatically too; see
   "Populating the `microsoft_auth_provider` Auth Provider" under Step 5. Both artifacts share the
   same Client ID / Tenant ID / Client Secret and must be populated together — populating only the
   Named Credential leaves portal SSO login broken.
3. **Grant Azure Administrator Consent** ("Grant Consent" button on the Go page). Clicking it
   opens a modal with a one-time consent link to a **fixed Salesforce-owned Entra app**
   (`client_id=cd6bd63f-41ef-47cc-9465-86e986179a29`, tenant segment `organizations` — not the
   user's own tenant ID, and not the app created in step 1) requesting the
   `Organization.ReadWrite.All` delegated scope:
   ```text
   https://login.microsoftonline.com/organizations/oauth2/v2.0/authorize?client_id=cd6bd63f-41ef-47cc-9465-86e986179a29&response_type=code&redirect_uri=https://salesforce.com&response_mode=query&scope=Organization.ReadWrite.All
   ```
   This link is static — it does not need to be fetched per-org or per-user, and headless-360 has
   no operation that generates or dispatches it (it's rendered by an internal Aura controller with
   no public Connect API mirror). **Paste this exact link and tell the user to click it, signed in
   as a Microsoft tenant admin, to grant consent** — this action authenticates as the Microsoft
   admin and cannot be performed by this skill via API.

Everything the user does above (steps 1's Azure clicks and step 3's consent click) is their
manual responsibility because no Salesforce API reaches Azure/Entra. Everything Salesforce-side —
writing the supplied credential (secret read from the gitignored secret file, never from chat) into
the Named Credential in step 2 — is this skill's job to automate; that division of labor is the
entire point of this skill.

### Step 4b — Delegate to the IT Desk / IT Service child skills

Before touching the "Set Up Salesforce IT Desk" / "Set Up Salesforce IT Service" checklist
groups, ask the user which they want — these are two independent halves of the feature
(fulfiller side vs. employee side) and a user may only need one:

- **Salesforce IT Desk** — for IT agents/fulfillers to swarm on and resolve tickets from Teams.
  Invoke `service-itsm-teams-itdesk-configure`.
- **Salesforce IT Service** — for employees to create and manage their own tickets from Teams.
  Invoke `service-itsm-teams-itservice-configure`.
- **Both** — invoke both child skills.

Each child skill handles its own 3-4 item checklist group (Turn on `<app>` → Install `<app>`
App on Teams → Manage User Access → optional 4th item) end-to-end — do not duplicate that logic
here.

### Step 4c — Delegate the embedded Agentforce agent (Teams "Ask AI Agent")

If the user wants the embedded Agentforce agent to **reply** inside the Teams custom client
("Salesforce Employee Assist" → "Ask AI Agent") — i.e. build the `Teams_AgentForce` MIAW
deployment, its Web channel (**User Verification ON + a `JWKS_URL` Key Set**), the routing flow to the
IT Service Employee Agent, and the **Agent Access permission set** for the portal user — **invoke
`service-itsm-teams-employee-agent-configure`.** That is a distinct, large capability with its own
object model; do not attempt it inline here. It requires the employee portal site
(`experience-portal-create`) to exist first.

### Step 5 — Register the preferred site (Teams extension), once the Azure credential exists

Once the org has an external credential named `MSTeamsSetupClientCredentialsEC` (see Step 4a and
"Populating..." below), register the Experience Cloud site that should back the Teams integration:

```text
mcp__headless-360__dispatch(
  method: "POST",
  url:    "/services/data/v67.0/connect/service-itsm-teams/graph-api/extensions",
  body:   { "siteUrlPathPrefixes": ["<site urlPathPrefix from GET /connect/communities>"] }
)
```

Update later with:
```text
mcp__headless-360__dispatch(
  method: "PATCH",
  url:    "/services/data/v67.0/connect/service-itsm-teams/graph-api/extensions/{extensionId}",
  body:   { "siteUrlPathPrefixes": ["<updated prefix list>"] }
)
```

If this returns `400 UNKNOWN_EXCEPTION "...external credential \"MSTeamsSetupClientCredentialsEC\"
might not exist"`, the Azure/Entra step (Gotchas) has not been completed yet — this is not a bug
in the call itself.

If instead it returns `AccessDenied` (or `400 UNKNOWN_EXCEPTION "...Unable to fetch tenant ID"`)
**even after** the EC shows `authenticationStatus: "Configured"`, the cause is almost always an
**incomplete Azure/Entra grant** — fixable, not a license wall (verified: same call went
`AccessDenied` → `201 Success` after these). Check, in order: (1) **admin consent not granted** —
several Step 4a scopes read *Admin consent required = Yes* and surface as `AccessDenied` until an
admin clicks **Grant admin consent**; confirm every row reads *Granted*. (2) **credential empty** —
a re-provision can empty the EC; it must read `Configured` at retry, so **repopulate** it. Retry
Step 5 after both. **Do not "fix" this by switching Delegated → Application** — the verified working
integration is Delegated + admin consent; flipping to Application diverges from the known-good setup.

Once you have the Azure Client ID and Tenant ID (given in chat) and the Client Secret (read from the
gitignored secret file written in Step 4a — never requested in chat), do the
Salesforce-side writes yourself — do not tell the user to enter values in Setup. The full verified
recipe (populating `MSTeamsSetupClientCredentialsEC`, populating the `microsoft_auth_provider` Auth
Provider for inbound SSO via the Metadata API, matching the portal user's `Username` to the Microsoft
UPN so `MsTeamsItsmSSOHandler` resolves them, and granting the portal user `ApiEnabled` for the Teams
Connect APIs) — with exact API bodies, the AuthProvider MDAPI template, the Web-vs-SPA callback
constraint, and their gotchas — is in:

**→ `references/azure-credential-population.md`**

---

## Completion contract — do NOT report Teams setup "complete" until all of these hold

The Go-feature enable (Steps 1–3) is necessary but **not sufficient**. The single most common
failure mode is declaring Teams "configured/done/complete" after Step 3 while the Microsoft Entra
app is still unregistered — which leaves in-Teams sign-in and the outbound Graph integration
**broken**. Treat the Entra app registration as a **blocking prerequisite of completion**, never an
optional tail. Report **complete only when every item below is verified** (not merely instructed):

1. **Feature enabled** — `service-cloud-itsm-teams-integration` reads `ENABLED` and
   `ITSMTeamsEnabled` reads `true` (Steps 1–3).
2. **Microsoft Entra app registered** — the user has completed Step 4a's Azure clicks and provided
   the Client ID and Tenant ID (in chat) with the Client Secret written to the gitignored secret
   file via the Step 4a copy-paste command (never pasted in chat). Until they do, **stop
   and wait** — this is a hard gate; you cannot proceed past it, and you must not report completion
   around it.
3. **Credentials populated (Salesforce-side, automated by this skill)** — `MSTeamsSetupClientCredentialsEC`
   reads `authenticationStatus: "Configured"` **and** the `microsoft_auth_provider` Auth Provider is
   populated with the same values (see `references/azure-credential-population.md`). Populating only
   one leaves either outbound Graph or inbound SSO broken.
4. **Admin consent granted** — the user has clicked the static consent link in Step 4a item 3,
   signed in as a Microsoft tenant admin.
5. **Preferred site registered** — the Teams extension call in Step 5 returns success (or the user
   has explicitly deferred the employee-site half).

If any of 2–4 is pending, the correct status is **"Blocked on Microsoft-admin action — Teams
integration incomplete,"** with the exact next step called out. A partial state is **not** a
success; do not soften it, and do not let a coordinator mark this feature `Done`.

---

## Disabling (if requested)

```text
mcp__headless-360__dispatch(
  method: "POST",
  url:    "/services/data/v67.0/connect/setup/discovery/feature/service-cloud-itsm-teams-integration/disable",
  body:   {}
)
```

Re-run Step 1/Step 3 afterward to confirm. Disabling `ITSMTeamsEnabled`'s underlying
provisioning (SSO handler, named/external credentials, PKCE OAuth client) may not be fully
reversed by this call alone — verify with the user whether they also need those artifacts
removed and treat that as a separate, manual Setup exercise.

---

## Related, separately-enabled preferences

Two sibling org preferences drive the "Fulfiller Hub" and "Employee Hub" halves of this feature
and, unlike `ITSMTeamsEnabled`, **are** directly writable via the standard Setup preferences
Connect API — `GET/PATCH /services/data/v67.0/setup/org/preferences/OrgHasITSMFulfillerTeams`
("Enable Salesforce IT Desk") and `.../OrgHasEmployeeServiceTeams` ("Enable Salesforce IT
Service"). Both take `{"desiredState": true}` and return `{"isPreferenceEnabled": true}`. They are
independent bits — enabling them does **not** unblock `ITSMTeamsEnabled`; enable them alongside,
not instead of, the Step 2 feature-enable call if the user wants both Hubs.

---

## Gotchas

The verified, load-bearing pitfalls (direct-PATCH 401, empty Auth Provider, Azure Web-vs-SPA
redirect, Username=UPN handler, portal API-Enabled, static consent link, version-prefix
requirement, and more) are catalogued in
[`references/gotchas.md`](references/gotchas.md). Read it before reporting a step as failed or
retrying an enablement guess.

---

## Related Skills

| Skill | When to use instead |
|-------|---------------------|
| `service-itsm-teams-itdesk-configure` | The "Set Up Salesforce IT Desk" checklist group (fulfiller side) — this skill delegates to it (see Step 4b) |
| `service-itsm-teams-itservice-configure` | The "Set Up Salesforce IT Service" checklist group (employee side) — this skill delegates to it (see Step 4b) |
| `service-itsm-teams-employee-agent-configure` | Making the embedded Agentforce agent reply in the Teams "Ask AI Agent" custom client (`Teams_AgentForce` MIAW deployment) — this skill delegates to it (see Step 4c) |
| `service-itsm-swarming-configure` | Enabling the `service-cloud-swarming` Go feature for "Set Teams as Collaboration Tool for Swarming" — invoked by `service-itsm-teams-itdesk-configure`, not by this skill directly |
| Notification-channel preferences | Enabling the `Notifications`/`TeamsNotifications` preferences is a distinct concern from this feature (no dedicated child skill exists yet) |
| `experience-portal-create` | Creating the employee-service portal/site itself |
| `service-itsm-channels-coordinate` | Top-level menu across Teams, Slack, Swarming, Notifications, Portal |

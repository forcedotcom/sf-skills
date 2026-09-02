---
name: service-itsm-slack-itservice-configure
description: "Configure the \"Set Up Self Service for Employees on Slack\" / \"Slack for Employee Service\" checklist for Employee Service (ITSM) on Slack — the employee side, covering the Slack for Employee Service org preference, Employee Slack Notifications permission-set assignment, employee portal (Digital Experience site) enablement/selection, and connecting Slack to a Preferred Digital Experience Site. Use this for: 'set up Slack for Employee Service', 'assign Employee Slack Notifications permission set', 'manage user access for Slack employee service', 'select a preferred digital experience site for Slack', 'set up self service for employees on Slack', or any request to complete the IT Service / Employee Service half of the Slack ITSM Go page checklist. DO NOT TRIGGER for the Microsoft Teams equivalents (service-itsm-teams-itservice-configure) or for turning ITSM notification preferences on or off."
metadata:
  version: "1.0"
  minApiVersion: "67.0"
  domains: ["Service"]
  relatedSkills:
    - "experience-portal-create"
    - "service-itsm-agentic-setup-employee-agent-configure"
    - "service-itsm-agentic-setup-fulfiller-agent-configure"
    - "service-itsm-channels-coordinate"
    - "service-itsm-teams-itservice-configure"
  mcpTools:
    headless-360:
      tools: ["dispatch", "dispatch_readonly"]
      semver: ">=1.0.0"
  cliTools:
    - tool: ["node"]
      semver: ">=18.0.0"
  accessCheck:
    - type: "orgPref"
      value: "EmployeeServiceSlackEnabled"
allowed-tools: |
  Read AskUserQuestion Bash
  mcp__headless-360__discover
  mcp__headless-360__describe
  mcp__headless-360__dispatch
  mcp__headless-360__dispatch_readonly
---

# Set Up Self Service for Employees on Slack (Employee Service / ITSM)

Complete the **"Set Up Self Service for Employees on Slack"** checklist group — the employee side of
Employee Service (ITSM) on Slack, so employees can create and manage their own tickets from Slack. Every
operation dispatches through **headless-360**.

> **Execute one step at a time.** These are real state-changing writes — run one operation, confirm it
> succeeded, then proceed. Don't batch setup calls into one parallel block.

> **Step 1 is a blocking gate.** The Slack↔Salesforce connection request is Slack-admin-side. Every run,
> display the Step 1 block and **STOP until the user confirms the request was sent** — no API call (not
> even reads) before that. If unconfirmed, Slack setup is **not** done.

> **Speak plainly; keep internals in reasoning.** Never surface tooling names, raw error codes, internal
> endpoints, developer names, or record Ids — translate to plain language ("Slack for Employee Service is
> now on") and refer to users/sites by human-readable **Name**. Begin each user-facing summary with the
> stamp **`(via service-itsm-slack-itservice-configure)`**.

## Scope

- **Automated (API)**: turn on **`EmployeeServiceSlackEnabled`**; assign all three core permsets —
  **`EmployeeSlackNotifications`** + **`ItsmPortalUelUserPermset`** + an API-Enabled permset — to each
  confirmed employee user; list the employee portal; set the **Preferred Digital Experience Site**
  (`SLACK_PREFERRED_SITE`). Also **read** connection status.
- **Guided + delegated**: **Connect Agentforce to Slack** (Step 6) — ensure the **IT Service Employee
  Agent** exists (delegate to `service-itsm-agentic-setup-employee-agent-configure`), read-check the
  connection, then guide the UI-only writes.
- **Guided, UI-only**: the connection request (Part 1, Step 1) + approve/activate (Parts 2 & 3, Step 2,
  only if the API read can't confirm) + mapping field; agent↔Slack connection + workspace install (Step 6).
- **Out of scope**: Slack notification preferences (on/off).

**Prerequisite:** the org must have Employee Service (ITSM) licensing/permission — `EmployeeServiceSlackEnabled`
is only editable then (see Gotchas). An employee portal should exist or be created via `experience-portal-create`.

---

## Workflow

### Step 1 — Request the Slack↔Salesforce connection (Slack-admin-side) — BLOCKING GATE

Connecting the org to a Slack workspace starts Slack-admin-side — no Salesforce API. **Hard gate: present
*only* Part 1 (request) verbatim, then HALT** and wait for the user to confirm ("ok" / "done"); make no API
call yet, and if unconfirmed, **Slack setup is not done**. Don't front-load Salesforce-side approval — you
try to confirm that yourself in Step 2.

```text
Connecting the org to Slack starts with a Slack-admin-side request — there's no Salesforce API for
it, so I can't do it for you. Do Part 1 now; after that I'll check the Salesforce side myself.

── PART 1 — Request a Salesforce connection in Slack (Slack desktop app) ──
  1. Click your workspace name in the sidebar.
  2. Hover over Tools & settings, then click Manage Salesforce organisations.
  3. Click on Connect Salesforce org in the top-right corner.
  4. Enter your Salesforce org URL.
  5. Choose whether to use Email or SAML NameID for the Account mapping field. If you like,
     toggle Automatic account mapping off to manually map accounts.
  6. Click on Request connection, then click on OK. Your request will be sent to Salesforce for
     approval.

Full walkthrough (all three parts — request, Salesforce approval, Slack activation):
  https://slack.com/intl/en-in/help/articles/30754346665747-Connect-Salesforce-and-Slack

Once you've sent the "Request connection" (Part 1), reply "ok".
```

### Step 2 — Confirm the connection (try API first), then turn on Slack for Employee Service

Don't send the user to Salesforce right away — **try to confirm the connection yourself first**, and only
guide the Salesforce-side approve/activate if you can't. Then enable the Employee Service org preference.

**2a. TRY TO READ the connection via API** (headless users have no Setup UI, so read rather than send them
there blind):

```text
mcp__headless-360__dispatch_readonly(
  method: "GET",
  url:    "/services/data/v67.0/connect/slackbridge/connections"
)
```

Returns `{team:{status, teamName, teamDomain, teamId}, currentUserMapping:{salesforceUserId, slackUserId}}`
(verified `200`). Branch on `team.status`:

- **`CONNECTED`** → already approved and live. Name the workspace by `teamName`; **skip Parts 2 & 3** and
  go straight to 2c (enable the preference). (A `null` `currentUserMapping.salesforceUserId` means this
  user isn't mapped to a Slack user yet — mention it; it doesn't block the connection.)
- **`team: null` / not-connected / errors → you CANNOT confirm it yet.** This endpoint is CONNECTED-only
  and **blind to a pending/requested connection**, so a null does **not** mean the request is absent.
  **Never** say it "didn't land" or "isn't on the Salesforce side". Say only that no activated connection
  shows via API yet, then **2b**.

**2b. Only if you couldn't confirm (team:null / pending), PASTE Part 2 and Part 3, then HALT.** Part 2 is
the Salesforce-side approval + mapping field (default `Email`; ask if the org uses SAML) — genuinely
UI-only, so guide it, don't fake an approve API. Point the user at the pending view **Setup → Manage Slack Connection** (`/lightning/setup/SlackWorkspaces/home`). Wait for "ok"
(approved + activated) before 2c.

```text
── PART 2 — Approve the connection on the Salesforce side (guided) ──
  1. Go to Setup → Manage Slack Connection (/lightning/setup/SlackWorkspaces/home).
  2. Find the pending request and Approve it.
  3. Set the Account mapping field to Email (default) — or SAML NameID if your org uses SAML.

── PART 3 — Activate the connection back in Slack (Slack desktop app) ──
  Do this after the connection is approved on the Salesforce side. Owners / Salesforce-admin system
  role in Slack can activate:
  1. Click your workspace name in the sidebar.
  2. Hover over Tools & settings, then click Manage Salesforce organisations.
  3. Select the pending connection.
  4. Review the connection details, then click Activate.

Reply "ok" once the connection is approved and activated, and I'll continue with the Salesforce setup.
```

> **Read yes, approve no — do not fake it.** Reading status is real; approving the connection and setting
> the mapping field are genuinely UI-only. Don't invent a `/connect/slack…` approve call or claim it approved.
> Details / API evidence: `references/manage-slack-connection.md`.

**2c. Turn on Slack for Employee Service.** A direct org-preference toggle (reachable via `PATCH`). Enable
it yourself via API; don't ask the user to flip the Setup toggle. Read first (idempotent — skip the write
if already enabled):

```text
mcp__headless-360__dispatch_readonly(
  method: "GET",
  url:    "/services/data/v67.0/setup/org/preferences/EmployeeServiceSlackEnabled"
)
```

Expect `200 {"isPreferenceEnabled": <bool>}`. If `false`, enable it:

```text
mcp__headless-360__dispatch(
  method: "PATCH",
  url:    "/services/data/v67.0/setup/org/preferences/EmployeeServiceSlackEnabled",
  body:   { "desiredState": true }
)
```

Expect `200 {"isPreferenceEnabled": true}`. Re-run the GET to confirm. Tell the user it's enabled — don't
ask them to flip the toggle themselves.

> **Verified:** the REST preference name is **`EmployeeServiceSlackEnabled`** (not the Metadata-API name
> `enableEmployeeServiceSlack`; guessed variants `404`). See Gotchas for the write-access gate.

### Step 3 — Enable / list the employee portal

Slack for Employee Service surfaces self-service through a Digital Experience portal. List the org's
sites and confirm an employee portal exists (this list feeds the Preferred Site selection in Step 5):

```text
mcp__headless-360__dispatch_readonly(
  method: "GET",
  url:    "/services/data/v67.0/connect/communities"
)
```

Each entry carries `id` (the **Network** Id, `0DB...`), `name`, `status`, `templateName`, `siteUrl`.
Present the list and identify the employee portal (`templateName` "Employee Portal" / "Agentforce
Employee Center"). If **no** portal exists — or Digital Experiences isn't enabled (the call errors /
returns nothing) — hand off to **`experience-portal-create`** (covers org-level enablement too), then return.

### Step 4 — Manage User Access (assign the employee permission sets)

The Go page's **"Manage User Access"** step assigns permission sets to each confirmed employee
user (**never all active users** — ask which user(s), then assign). **Always assign all three core
permsets** to each confirmed user — don't ask the user to choose a "notifications-only" vs "full"
scope; the three together are what makes Slack for Employee Service actually usable (notifications +
record visibility + API access), and under-assigning silently breaks record access:

- **`EmployeeSlackNotifications`** — Slack notifications on ticket updates (the core of the step).
- **`ItsmPortalUelUserPermset`** ("ITSM Portal Uel User") — read/create/edit on **Incident, Service
  Request, Case** (self-service) — lets the employee see/work their own records.
- **API Enabled** — lets the Slack app call Connect APIs. **Reuse** any existing API-Enabled permset the
  org already has; else **create** a Slack-named one (`PermissionSet`, `PermissionsApiEnabled = true`, e.g.
  Name `Slack_ApiAccess` / label "Slack API Access"). See `references/manage-user-access.md`.

**Agent access** is separate and conditional — assign it **only if** the user opts into the Agentforce
agent in Slack (Step 6): the **per-agent** `Agent_Access` permset (the agent's `BotDefinition`
`SetupEntityAccess`); reverse-lookup, create if absent. **Never** `Access_Agents` (fails on an employee
license). Mechanics: `references/connect-agentforce-to-slack.md`.

> **Warn the user before assigning — their email must match their Slack user's email.** The permset grants
> only the *ability* to receive notifications; the Salesforce↔Slack link comes from the connection's
> account-mapping field (default **`Email`**): `User.Email` must equal the Slack-account email, or they map
> to no Slack user and notifications go nowhere. A `null` `currentUserMapping.salesforceUserId` from Step 2
> means unmapped. (SAML NameID: same rule, that identifier.) Surface this **before** you assign, so the user
> can pick users whose emails match.

Flow: query active users (page ≤10), classify with the helper script (don't eyeball — early pages are
full of system/integration accounts), ask which to grant, look up each permset Id fresh, POST one
`PermissionSetAssignment` per user per permset, classify each response with the script.

**→ `references/manage-user-access.md`** — query + POST bodies, the `classify-user-access.mjs` contracts,
the email-match + license gotchas, and the `ItsmPortalUelUserPermset` / API-Enabled / agent-access grants.

### Step 5 — Select a Preferred Digital Experience Site to connect Slack with

Writes the org value `SLACK_PREFERRED_SITE` (shared, cross-feature — see Gotchas).

1. Use the site list from Step 3. Ask which site to connect Slack with; **if they don't choose, pick one
   yourself** (the only site, else the employee portal / most recent `Live` site) and tell them.
2. Read `GET /services/data/v67.0/setup/org/values/SLACK_PREFERRED_SITE` first (`stringValue` = current
   Network `Id` or `"None"`); skip the write if already the chosen site's Id.
3. Write via `dispatch` `PATCH` to the same path with body `{ "orgValue": "<site Network Id>" }` — the
   site's **Network `Id`** (`0DB...` from `connect/communities`, **not** `urlPathPrefix`); re-read to confirm.

### Step 5b — Verify the site is active, published, and the user is a member (BLOCKING — do before any success)

`SLACK_PREFERRED_SITE` and the Step-4 permset writes all return `200/201` even when the site can't
serve the employee — a "success" summary is then wrong: IT Service lists come back empty /
access-denied. Activation, membership, and publication are **three distinct states** — verify each;
**a failure of any is blocking — do not report setup complete.** Remediation for any gap is
programmatic (hand to **`experience-portal-create`**, which owns the activate/add-member/publish
paths), UI as fallback — **not** UI-only:

1. **Live (activation)** — `SELECT Status FROM Network WHERE Id = '<site Id>'`; if `!= 'Live'`, hand off.
2. **Member** (per Step-4 user) — `SELECT Id FROM NetworkMember WHERE NetworkId = '<site Id>' AND
   MemberId = '<user Id>'`; `0` rows → hand off (add the profile/permset to Members).
3. **Published** — `Network.Status = 'Live'` does **not** prove the pages are published (a never-published
   site 404s); if it was only activated, hand off to publish.

**→ `references/site-membership-verification.md`** — exact queries, remediation, and the silent-success failure mode.

### Step 6 — Configure Agentforce for Slack (optional; ask the user first — this is the final step)

**First, have the user verify their records show in Slack — HALT before Agentforce.** Catch a visibility
failure here rather than blame it on the agent later:

```text
Before we (optionally) add the Agentforce agent, verify records show in Slack:
  1. In Slack → Agents & tools → Apps → search "Salesforce" → Open app.
  2. Confirm your self-service records show — Incident, Service Request, Case lists.

Reply "ok" once you see them. If a list says "Nothing turned up", the self-service permset
(ItsmPortalUelUserPermset) or email mapping isn't right — tell me and we'll fix it first.
```

Only after the user confirms records are visible, **ask whether they also want an Agentforce agent to
reply in Slack; if not, stop here** — setup is complete without it. If yes, the Go page's *Configure
Agentforce for Slack* group has two items that make an agent actually **reply in Slack**:

- **"Build and Manage Agent"** — the agent build; **IS automatable** (delegate).
- **"Connect Agentforce to Slack"** — connection + workspace install; **UI-only** (guide).

**Ensure the agent exists first** — the **IT Service Employee Agent**. Check the org (query below); if
missing, hand off to **`service-itsm-agentic-setup-employee-agent-configure`** (provisions templates,
creates, activates), then return. (Fulfiller: `service-itsm-agentic-setup-fulfiller-agent-configure`.)

```text
mcp__headless-360__dispatch_readonly(
  method: "GET", url: "/services/data/v67.0/query",
  queryParams: { "q": "SELECT Id, DeveloperName, MasterLabel FROM BotDefinition WHERE DeveloperName = 'IT_Service_Employee_Agent'" }
)
```

**The connection is UI-only for writes — read-check state first, guide, don't fake it.** No public API
adds the Slack connection or installs the agent into a workspace. Read-check before sending the user to
Setup: **workspace connection** via Step 2's `/connect/slackbridge/connections` (`CONNECTED` ⇒ live). The
agent↔Slack link has no read — eyeball the Builder's Connections node. Then guide whatever's missing.

> **If the "+" next to Connections isn't clickable, the version is Committed (locked)** — connections add
> only on a **Draft**. Click **New Version** first; the **+** enables (version-lock, not Active/Inactive —
> deactivating does **not** unlock). After **+ → Add connection → Slack → Add to agent**: **Save → Commit
> Version → Activate**.

**→ `references/connect-agentforce-to-slack.md`** — verbatim click-paths (both sides), manage-after-install
actions, prerequisites, and the no-API evidence. Display these to the user.

---

## Gotchas

| Issue | Detail |
|-------|--------|
| REST preference name is `EmployeeServiceSlackEnabled`, not the Metadata name | `/setup/org/preferences/{name}` uses **`EmployeeServiceSlackEnabled`** (Metadata field `enableEmployeeServiceSlack` differs). Write access is gated (`userCanManageEmployees`) — on a non-ITSM org the PATCH may be rejected; surface the error, don't retry. |
| `SLACK_PREFERRED_SITE` org value | `orgValue` = the site's Network `Id` (`0DB...`), not `urlPathPrefix`. Read it back after writing to confirm. |
| `slackbridge/connections` is CONNECTED-only — `team: null` ≠ no connection | `GET /connect/slackbridge/connections` populates `team` **only after activation**; a pending connection reads `{team: null}` yet exists and shows in **Setup → Manage Slack Connection** (Aura-only, no REST mirror). Never report a null as "request didn't land"; say "no activated connection visible via API yet" and cross-check Setup. No approve/activate endpoint. Details: `references/manage-slack-connection.md`. |
| Version prefix required | headless-360 `dispatch`/`dispatch_readonly` don't resolve API versions — pass the full `/services/data/vXX.0/...` prefix. |
| Step 4 permset — `EmployeeSlackNotifications`, not `SlackServiceUser`; may be license-gated | Assign the employee-side **`EmployeeSlackNotifications`** (+ `ItsmPortalUelUserPermset` for self-service record visibility — Incident/Service Request/Case, not Problem/Change); `SlackServiceUser` is a fulfiller-side one that does **not** satisfy this step. Some licenses can't hold the PSL (`400 FIELD_INTEGRITY_EXCEPTION`) — hard "wrong license" stop, not retryable. Details: `references/manage-user-access.md`. |
| Step 4 API-Enabled permset — reuse or create | The user needs a permset with **API Enabled** for the Slack app to call Connect APIs. Reuse any existing API-Enabled permset the org has; if none, create a minimal Slack-named `PermissionSet` (`PermissionsApiEnabled = true`, e.g. `Slack_ApiAccess`). Details: `references/manage-user-access.md`. |
| Writes succeed but Slack shows no records → site inactive/unpublished or user not a member | `SLACK_PREFERRED_SITE` and permset writes return `200/201` even when the site is `UnderConstruction`, its pages are unpublished, or the user has **no `NetworkMember`** row — so "success" is misleading. **Step 5b** verifies three distinct states (activation `Network.Status = 'Live'`; a `NetworkMember` per Step-4 user; publication — `Live` does **not** prove pages published) before any success. Remediation is **programmatic** — hand to `experience-portal-create` (owns activate/add-member/publish), UI as fallback, not UI-only. Details: `references/site-membership-verification.md`. |

---

## Verification Checklist

Before emitting any user-facing summary, confirm each of the following:

- [ ] Step 1 block displayed and the user **explicitly confirmed** Part 1 was sent **before any API call**;
      if not, no step ran and the user was told setup isn't done.
- [ ] Step 2 read `/connect/slackbridge/connections` **first**; `CONNECTED` → Parts 2 & 3 skipped; a
      `team: null` phrased as "no activated connection visible via API yet" (+ Setup → Manage Slack Connection),
      **never** "request didn't land"; Parts 2 (approve, no fake approve-API) & 3 pasted only if unconfirmed.
- [ ] Output opens with the `(via service-itsm-slack-itservice-configure)` stamp; no tooling names, error
      codes, endpoints, developer names, or record Ids — names are human-readable.
- [ ] Each write ran one at a time; idempotent reads (`EmployeeServiceSlackEnabled`, `SLACK_PREFERRED_SITE`)
      checked first and the write skipped when already in the desired state.
- [ ] Step 4: rows + assignments classified by `scripts/classify-user-access.mjs` (not eyeballed); **all
      three core permsets always assigned** to each confirmed user — `EmployeeSlackNotifications` (not
      `SlackServiceUser`), `ItsmPortalUelUserPermset`, and an API-Enabled permset (reused else created) — no
      "notifications-only" scope offered; `Agent_Access` (never `Access_Agents`) only if the user wants the
      agent; assigned to confirmed user(s) only; `wrong-license` surfaced, not retried.
- [ ] Step 5b ran **before any success summary**: activation (`Network.Status = 'Live'`), publication (pages
      published — not implied by Live), and a `NetworkMember` per Step-4 user all confirmed (else blocking, hand
      remediation to `experience-portal-create`) — not skipped on `200/201`.
- [ ] Before any Step 6 guidance: the user **confirmed their records (Incident / Service Request / Case) show
      in Slack**; a "Nothing turned up" reply was fixed first. (Problem/Change staying empty is expected.)
- [ ] If Step 6 ran: **Build and Manage Agent** delegated when the agent was missing; workspace connection
      read-checked; **Connect Agentforce to Slack** guided as UI-only.
- [ ] Slack-admin-side parts (Step 1 Part 1; Step 2 Part 3; Step 6 workspace install) handed to the user.

## Reference File Index

Each step's `→` pointer names its reference:

- `references/manage-slack-connection.md` (Step 2) ·
  `references/manage-user-access.md` + `references/record-visibility.md` (Step 4) ·
  `references/site-membership-verification.md` (Step 5b) ·
  `references/connect-agentforce-to-slack.md` (Step 6).
- `scripts/classify-user-access.mjs` — `flag-users` tags User rows; `classify-assignment` classifies a
  `PermissionSetAssignment` POST as `success`/`wrong-license`/`other-error`.

---

## Related Skills

| Skill | When to use instead / alongside |
|-------|---------------------------------|
| `service-itsm-agentic-setup-employee-agent-configure` | Builds/activates the IT Service **Employee** Agent connected in Step 6; delegated to. |
| `service-itsm-agentic-setup-fulfiller-agent-configure` | Builds/activates the **Fulfiller** Agent — alternative Step 6 agent. |
| `experience-portal-create` | Creates the employee Digital Experience portal this skill selects. |
| `service-itsm-channels-coordinate` | Top-level menu across ITSM channels — Slack, Swarming, Notifications, Portal. |

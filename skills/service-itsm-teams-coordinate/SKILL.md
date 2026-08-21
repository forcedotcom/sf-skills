---
name: service-itsm-teams-coordinate
description: "End-to-end autopilot orchestrator for setting up Microsoft Teams integration in Salesforce Service Cloud ITSM — runs the whole flow (enable the Teams for Employee Service Go feature, register the Microsoft Entra app, populate Named Credentials, configure the IT Desk and IT Service checklists, turn on Swarming, and optionally embed the Agentforce agent) in one continuous pass, stopping only at the points a human must act. Use when the user asks to set up Microsoft Teams for ITSM end to end, 'set up teams for it service', 'do the whole teams itsm setup', 'configure microsoft teams for employee service', or wants a guided Teams ITSM walkthrough. Delegates each stage to a specialized child skill while driving the sequence itself. DO NOT TRIGGER when the user asks to enable Teams alone, configure just the IT Desk or IT Service checklist alone, or enable Swarming alone — delegate directly to the specific child skill in those cases."
metadata:
  version: "2.0"
  domains: ["Service"]
  relatedSkills:
    - "service-itsm-swarming-configure"
    - "service-itsm-teams-configure"
    - "service-itsm-teams-debug"
    - "service-itsm-teams-employee-agent-configure"
    - "service-itsm-teams-itdesk-configure"
    - "service-itsm-teams-itservice-configure"
  # No accessCheck gate: this orchestrator's Stage 1 is what enables ITSMTeamsEnabled,
  # so it must be invokable on a brand-new org before that preference exists. Downstream
  # child skills retain their own accessCheck. Empty array = applies to any org.
  accessCheck: []
allowed-tools: Read AskUserQuestion
---

# Microsoft Teams for ITSM — End-to-End Setup Autopilot

Drive the **complete** Microsoft Teams for Employee Service (ITSM) setup as one continuous flow.
Delegate each stage to its specialized child skill, but own the **sequence** yourself and keep
going through every stage **without stopping to ask permission between stages**. Halt only at the
points where a human genuinely must act — nowhere else.

## Goal

Take the user from nothing to a working Teams ITSM integration (IT Desk + IT Service, Swarming, and
— if they want it — the embedded Agentforce agent) in a single guided run. The child skills carry
the verified API detail; this skill is the conductor that runs them in order and manages the handoffs.

## Core operating rule — run continuously, halt only where required

**Do everything with no midway stop unless the user must supply something or perform an off-platform
action.** Do **not** re-present a menu between stages, do **not** ask "shall I continue?" after each
stage, and do **not** ask the user to click Setup toggles this skill's children can do via API. Move
straight from one stage to the next, reporting progress as you go.

There are exactly **three mandatory halts** and **one branch** in the whole flow:

- **HALT 1 — Azure/Entra app** (Stage 2): you give the user the app-registration instructions and
  **wait** for them to register the app and provide the credentials. No Salesforce API can do this.
  The **Client ID** and **Tenant ID** are non-secret identifiers and may be given in chat; the
  **Client Secret is a confidential credential — NEVER ask for it in the conversation.** The user
  places it in the `TEAMS_ENTRA_CLIENT_SECRET` environment variable (or a gitignored secret file the
  agent is told the path to); the agent reads it from there and never prints, echoes, or logs it.
- **HALT 2 — IT Desk app install** (Stage 3): you give the Microsoft Marketplace link and **wait**
  for the user to reply **"installed"**. No API installs a Teams app into a tenant catalog.
- **HALT 3 — IT Service app install** (Stage 4): same as HALT 2, for the IT Service app.
- **BRANCH — IT Service Agentforce agent** (Stage 7): the IT Desk agent works automatically, but the
  IT Service embedded agent is pending work; **ask the user whether to do it**, and only run Stage 8
  if they say yes.

If the user goes silent at a halt, stop and wait — do not fabricate the value or skip ahead. Every
other transition is automatic.

> **Within each stage, execute one operation at a time.** The child skills make real, state-changing
> API calls; run a single operation, confirm it succeeded, then proceed — never batch state-changing
> calls into one parallel block. "No midway stop" means no *permission gate* between stages, not
> firing writes in parallel.

## The flow (run in this order)

### Stage 1 — Enable the Teams for Employee Service Go feature
Invoke **`service-itsm-teams-configure`** for the feature-enable half only (its Steps 1–3): enable
`service-cloud-itsm-teams-integration` and confirm `ITSMTeamsEnabled` reads `true`. Report progress,
then continue straight into Stage 2 — do **not** stop here.

### Stage 2 — Microsoft Entra app + Named Credentials  ⟶ HALT 1
Still within **`service-itsm-teams-configure`** (its Step 4a): give the user the exact Azure/Entra
app-registration clicks **including the Microsoft Graph Application permissions** it lists, and
**HALT** until they provide the credentials. The **Client ID** and **Tenant ID** are non-secret
identifiers — accept them in chat. The **Client Secret is confidential: never request it in the
conversation.** Instruct the user to set it in the `TEAMS_ENTRA_CLIENT_SECRET` environment variable
(or a gitignored secret file, and tell you the path); read it from there. Never print or echo it.
The moment the identifiers are given and the secret is in the env/file:
- Write those values into the `MSTeamsSetupClientCredentialsEC` Named Credential **and** the
  `microsoft_auth_provider` Auth Provider **yourself, via API — nothing manual** (the child skill's
  Step 5 and its azure-credential-population reference carry the exact API bodies). Reference the
  secret by its env var / file path in the API call — do not inline the raw value into any logged text.
- Give the user the static **Grant Admin Consent** link and register the preferred site (child Step 5).
Then continue to Stage 3 automatically.

### Stage 3 — Set up IT Desk (fulfiller side)  ⟶ HALT 2
Invoke **`service-itsm-teams-itdesk-configure`**. Drive its whole checklist:
- Turn on the `OrgHasITSMFulfillerTeams` org preference (via API).
- **Manage User Access** — assign the fulfiller permission sets to the confirmed user(s):
  `TeamsForITSrvcsUser` + `MicrosoftGraphAccess`, **plus `Teams_Employee_ApiAccess`** (the ECA-
  pre-authorized set that also grants **API Enabled** — required for login, not optional).
- **Turn on Swarming** — this stage includes `service-itsm-swarming-configure`
  (enables `service-cloud-swarming` and sets `SWARM_COLLABORATION_TOOL = "Teams"`).
- Give the **IT Desk Microsoft Marketplace link** + help doc, tell the user **the Azure account
  email must match the Salesforce user's email/Username** (SSO resolves MS UPN → `Username`), and
  **HALT** until the user replies **"installed."** Then continue to Stage 4.

### Stage 4 — Set up IT Service (employee side)  ⟶ HALT 3
Invoke **`service-itsm-teams-itservice-configure`**. Drive its whole checklist:
- Turn on the `OrgHasEmployeeServiceTeams` org preference (via API).
- **Manage User Access** — assign the employee permission sets to the confirmed UEL user(s):
  `TeamsForEmployeeUser` + `MicrosoftGraphAccess`, **plus the API Enabled + ECA-authorized access**
  the child's login prerequisites require.
- **Select the Digital Experience Site** (`SLACK_PREFERRED_SITE`) via API.
- Give the **IT Service Microsoft Marketplace link** + help doc, repeat the **email-must-match** note,
  and **HALT** until the user replies **"installed."** Then continue to Stage 5.

### Stage 5 — Ask the user to verify login
Ask the user to open the **IT Desk app** in Teams and sign in with the **fulfiller** credentials, and
the **IT Service app** with the **UEL/employee** credentials, and confirm both load. If either fails,
route to **`service-itsm-teams-debug`** for the pass/fail login diagnostic before proceeding.

### Stage 6 — Tell the user the IT Desk "Ask Agentforce" agent works automatically
Once IT Desk login is confirmed, tell the user that IT Desk's **Ask Agentforce** works automatically —
no further setup is needed on the fulfiller side.

### Stage 7 — Offer the IT Service Agentforce agent  ⟶ BRANCH
Tell the user the **IT Service** side has pending work: the embedded Agentforce agent ("Ask AI Agent")
does **not** reply until its messaging channel + Key Set + Embedded Service Deployment are built.
**Ask whether they want to set it up now** (use `AskUserQuestion`). If **no**, go to the completion
summary. If **yes**, run Stage 8.

### Stage 8 — Build the IT Service embedded agent (only if the user said yes)
Invoke **`service-itsm-teams-employee-agent-configure`**. It builds — 100% via API — the Web
messaging channel with **User Verification ON + a `JWKS_URL` Key Set**, the `Teams_AgentForce`
Embedded Service Deployment (publish), the routing flow, and the Agent Access permission set on the
portal user. Then tell the user to **retest from a brand-new Teams chat** to confirm the agent replies.

## After each stage

- **Report the child's ACTUAL verdict — never assume "Done."** A stage is complete only when its
  child skill explicitly reported success. If a child reports **blocked** (most commonly Stage 2 while
  the Entra app is unregistered, or a halt awaiting "installed"), keep that stage **`Blocked`/waiting**
  and hold at the halt — do not mark it done and do not skip ahead.
- Do not re-present a menu. State what just finished and what you're doing next, then do it.

## Completion summary

When the flow ends (Stage 7 "no", or Stage 8 done, or a hard block the user chose not to resolve),
summarize each stage's real status. Header: all stages complete → **Complete**; any stage still
blocked/waiting → **Incomplete (action required)** with the exact next step; otherwise **Finished**.

## Rules

- ALWAYS show "(via service-itsm-teams-coordinate)" in the setup header.
- Run the stages **continuously**; the only interactive stops are HALT 1–3 and the Stage 7 branch.
- NEVER ask the user to click a Setup toggle a child skill can flip via API (feature enable, org
  prefs, permission-set assignment, digital site, named credentials).
- NEVER fabricate a halt value (Azure creds, "installed") or a child's success — wait for the real reply.
- Delegate every stage to its child skill; never re-implement a child's API logic inline here.
- Track progress across the conversation — do not re-run a completed stage.
- Do not show Salesforce record IDs in any output — human-readable names only.
- At Stages 3 and 4, always include the **Azure-email-must-match-Salesforce-email** note with the
  marketplace link, since a mismatch is a common silent login failure.

## Verification checklist

Before emitting any progress message or summary, confirm:

- [ ] The header line ends with `(via service-itsm-teams-coordinate)`.
- [ ] The flow is running continuously — no permission gate was inserted between stages beyond the
      three defined halts and the Stage 7 branch.
- [ ] Each stage's status reflects the child's actual verdict (`In progress`, `Blocked`/waiting, or
      `Done`) — not a hard-coded default.
- [ ] A stage waiting on a halt (Azure creds, "installed") is shown as waiting, never `Done`.
- [ ] Stages 3 and 4 each surfaced the marketplace link **and** the email-must-match note.
- [ ] The Stage 7 branch was offered as a yes/no question, and Stage 8 ran only on an explicit "yes."
- [ ] The next action delegates to a child skill; features are never configured inline here.
- [ ] No Salesforce record IDs appear in the output — human-readable names only.

## Reference File Index

| File | When to read |
|------|--------------|
| `examples/output-templates.md` | Progress and completion-summary text blocks |

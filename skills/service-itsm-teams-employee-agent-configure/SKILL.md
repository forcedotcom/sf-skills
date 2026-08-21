---
name: service-itsm-teams-employee-agent-configure
description: "Configure the embedded Agentforce Employee Agent so it replies inside the Microsoft Teams ITSM custom client ('Salesforce Employee Assist' / 'Ask AI Agent'). Use this for: 'set up employee agent in Teams', 'embed Agentforce agent in Teams', 'make the IT Service Employee Agent reply in Teams', 'Teams Ask AI Agent not responding', 'agent joins then leaves without replying', 'configure MIAW deployment for Teams employee agent', 'Teams embedded messaging agent setup'. Builds the whole stack headlessly (zero Setup-UI clicks): the Web messaging channel with User Verification ON, the Enhanced Chat User Verification Key Set (JWKS_URL) it requires, the Teams_AgentForce custom-client deployment, the routing flow to the agent, and the Agent Access permission set that lets the portal user reach the agent. DO NOT TRIGGER for enabling the Teams feature Salesforce Go page toggle (service-itsm-teams-configure) or for configuring notification preferences."
metadata:
  version: "1.0"
  domains: ["Service"]
  minApiVersion: "67.0"
  relatedSkills:
    - "experience-portal-create"
    - "service-itsm-agentic-setup-employee-agent-configure"
    - "service-itsm-channels-coordinate"
    - "service-itsm-teams-configure"
    - "service-itsm-teams-debug"
  cliTools:
    - tool: ["sf"]
      semver: ">=2.0.0"
  accessCheck:
    - type: "orgPref"
      value: "ITSMTeamsEnabled"
---

# Configure the Embedded Agentforce Employee Agent in Microsoft Teams

Make the embedded Agentforce agent ("IT Service Employee Agent") actually **reply** inside the
Microsoft Teams ITSM custom client ("Salesforce Employee Assist" → "Ask AI Agent"). The Teams
custom client loads a Messaging-in-App-and-Web (MIAW) deployment at runtime by its
`esDeveloperName`, which is **hard-wired to `Teams_AgentForce`** in committed Core config
(`service-cloud-requestor-agent-miaw.configuration.json` / the Teams app manifest) — so the
Embedded Service Deployment **must be named exactly `Teams_AgentForce`** and cannot be renamed
per-org.

This is the hardest, most under-documented part of Teams ITSM. The full build-from-scratch
recipe — verified live against a real org — lives in:

**→ `references/teams-embedded-employee-agent.md`**

> **Execute one step at a time.** These steps make real, state-changing API calls. Run a single
> operation, show its result, confirm it succeeded, then proceed — do not batch multiple setup
> calls into one parallel block.

## Scope

- **In scope**: Building the MIAW channel + deployment the Teams custom client loads **entirely via
  API (zero Setup-UI clicks)** — a **Web** Enhanced-messaging channel with **User Verification ON
  (auth mode = Auth)** backed by an **Enhanced Chat User Verification Key Set** (`PublicKeyCertificateSet`,
  type `JWKS_URL`, endpoint `<Org>/id/keys`, issuer = Employee Site URL), the **`Teams_AgentForce`**
  custom-client Embedded Service Deployment, and an Omni-Flow routing flow whose `routeWork` action
  targets a **real, Active** Agentforce Employee Agent. Creating and assigning the **Agent Access
  permission set** that grants the portal user access to the agent (the step that makes it actually
  reply). Verifying the token/routing chain end to end via API and diagnosing the "joined then left /
  no reply" symptom.
- **Out of scope**: Enabling the Teams feature Salesforce Go page toggle and Azure/SSO/Named-Credential setup
  (`service-itsm-teams-configure`). Creating the employee portal/site (`experience-portal-create`).
  Fixing the Agentforce agent's own GenAI planner / Omni-Channel presence / capacity **only after**
  the auth-ON + Key Set chain and Agent-Access-assigned are all confirmed and the session still stays
  queue-owned with no agent reply — that residual case is an agent-runtime concern owned by the
  Agentforce Employee Agent team (see the "joins then leaves" section in the reference).

## Prerequisites

- Teams ITSM feature enabled and the employee portal site live (run `service-itsm-teams-configure`
  and `experience-portal-create` first). You need the **Employee Site URL** (e.g.
  `https://<org>.my.site.com/empPortal`) and the org's My Domain URL.
- A real, **Active** Agentforce Employee Agent exists
  (`SELECT Id FROM BotDefinition WHERE Type='InternalCopilot' AND AgentType='AgentforceEmployeeAgent'`,
  with an `Active` `BotVersion`). **If none exists, create it first** — enabling the
  `service-cloud-it-service-employee-agent` Go feature *may* auto-provision it, but that is **not
  guaranteed** (verified: in one org the feature enabled but provisioned nothing). The reliable way
  to deploy it is **`service-itsm-agentic-setup-employee-agent-configure`** (which reads the shipped
  Employee template's Agent Script and creates + publishes + activates the agent as an NGA-native
  bundle); the equivalent underlying path is the ITSM Connect **agent-templates install + activate**
  against `EmployeeCopilot__AgentforceEmployeeAgent`. Deploy the agent first, then run this skill to
  embed it in Teams. See the "Prerequisite: the IT Service Employee Agent must exist" section in the
  reference for both paths and their gotchas.

## The causes of "agent joins then leaves" (read this before building)

The agent replies only when the whole chain is intact — missing a link produces the classic "agent
joins the conversation, then leaves, no reply" symptom. All are **fixable in this skill**:

| # | Requirement | Symptom if missing | Fix |
|---|-------------|--------------------|-----|
| 1 | **Channel auth mode = Auth (User Verification ON) WITH a Key Set attached** | `/unauthenticated/access-token` → `BAD_REQUEST` "Set the auth mode to false" (auth ON but **no Key Set** → client fell back to the unauthenticated endpoint); or **401 on `/eventrouter/v1/sse`** (Key Set endpoint/issuer wrong) | Attach a `JWKS_URL` Key Set (endpoint `<Org>/id/keys`, issuer = Employee Site URL) and link it into the channel — do **not** turn auth off |
| 2 | **Portal user has an Agent Access permission set** enabling the IT Service Employee Agent | Tokens mint and SSE connects, but the agent joins then leaves with **zero `ConversationEntry`** | Create + assign a permission set with Agent Access → the agent |
| 3 | **The `Teams_AgentForce` ESD exists + is published** | `SELECT Id FROM EmbeddedServiceConfig WHERE DeveloperName='Teams_AgentForce'` → 0 rows; Teams can't load a missing deployment | Metadata-deploy the `API`-type ESD + Connect-publish it (step 3) |

> **This reverses an earlier version of this skill** that told you to turn User Verification **OFF**
> and never attach a Key Set. That was diagnosed on a build that flipped auth ON but **forgot the
> Key Set**, so the Teams client used the *unauthenticated* endpoint and hit "Set the auth mode to
> false." The verified, product-blessed fix is **auth ON + a JWKS_URL Key Set** (screenshot-confirmed
> live), which puts the client on the *authenticated* token flow the channel expects.

If the agent *still* won't reply after auth-ON + Key Set, Agent-Access-assigned, and the ESD
created+published are all confirmed, **delegate to `service-itsm-teams-debug`** (its `AGENTFORCE`
pass/fail checklist walks the full token/routing/ESD/agent chain) before escalating to the
Agentforce Employee Agent team (agent Omni presence / capacity / GenAI planner) as the last resort.
In the verified org, fixing the fixable causes above was sufficient.

## Verified recipe (summary — 100% API, zero manual steps; full XML + calls in the reference)

Deploy in this order — **Key Set first, then the channel that references it, then the ESD.** All
deploys use an isolated `sfdx-project.json` at `--api-version 67.0`. Run one step at a time.

1. **Enhanced Chat User Verification Key Set** — Metadata-deploy a `PublicKeyCertificateSet` with
   `<type>JWKS_URL</type>`, `<jwksEndPoint>` = `<Org_Url>/id/keys`, `<jwtIssuer>` = the **Employee
   Site URL**. Directory must be `PublicKeyCertificateSet/`, suffix `.PublicKeyCertificateSet-meta.xml`.
   (`JWKS_URL` is the endpoint-URL mode; `Jwks` is the uploaded-key mode and rejects a URL.)
2. **Messaging channel**, deployment type **Web**, domain = the **Employee Site URL** — Metadata-deploy
   a `MessagingChannel` (`messagingChannelType=EmbeddedMessaging`) whose `sessionHandlerFlow` = the
   routing flow that targets the IT Service Employee Agent and `sessionHandlerQueue` = the fallback
   queue (e.g. `chatqueue`). Turn **User Verification ON** and **link the Key Set** in one block:
   `<embeddedConfig><authMode>Auth</authMode><messagingAuthorizations>…publicKeyCertificateSetName…</messagingAuthorizations></embeddedConfig>`.
   Then **activate** the channel (`MessagingChannel.IsActive=true`) before publishing the ESD. The
   routing flow + fallback queue are prerequisites — if `Route_To_MIAW_AEA` was template-installed it
   ships with **placeholder ids** (repoint them); if none exists, author one. The `sfdc_livemessage`
   Omni service channel is **standard/pre-existing** (query, don't create). See the reference §A/§E/§F.
3. **Create the `Teams_AgentForce` Embedded Service Deployment (ESD)** — the deployment the Teams
   client loads by `esDeveloperName`. Metadata-deploy an **`API`-type** ESD named exactly
   **`Teams_AgentForce`** whose `<messagingChannel>` references the channel from step 2, then
   **publish** it via `POST /services/data/v67.0/connect/embeddedservice/embeddedserviceconfig/publish/<esdId>`
   (`{}` → `isSuccess:true`; the publish route is **v67.0**). See reference §C/§D. **If this ESD is
   missing, login works but the agent never replies** — verify with
   `SELECT Id FROM EmbeddedServiceConfig WHERE DeveloperName='Teams_AgentForce'` (Tooling).
4. **Create a permission set** (e.g. "Agent Access") enabling the **IT Service Employee Agent** and
   **assign it to the portal user** (RBAC grant — confirm before assigning). See reference §G.
5. **Retest from a brand-NEW Teams chat** — existing sessions stay bound to the old deployment.

Do **not** use `POST /connect/service-itsm/createMessagingChannel` — it forces its own defaults; build
the channel yourself so you control the flow/queue/dev-name and the exact auth + Key Set wiring. See
the reference for the exact API bodies, object names, verification queries, and the full gotchas index.

## Related Skills

| Skill | When to use instead |
|-------|---------------------|
| `service-itsm-teams-configure` | Enabling the Teams feature Salesforce Go page toggle + Azure/Entra app + SSO/Named Credentials — run first; it delegates here for the embedded agent |
| `experience-portal-create` | Creating the employee-service portal/site whose URL this skill consumes |
| `service-itsm-teams-debug` | Diagnosing why an already-built agent won't reply (or other Teams ITSM failures) — runs the `AGENTFORCE` pass/fail checklist and reports remediation |
| `service-itsm-channels-coordinate` | Top-level menu across Teams, Slack, Swarming, Notifications, Portal |

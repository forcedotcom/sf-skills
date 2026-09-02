# Connect Agentforce to Slack — verbatim click-paths (Step 6)

The "Connect Agentforce to Slack" flow is **UI-only** — verified live against a real org: there is
**no public Salesforce API** to add a Slack connection to an agent or to install the agent into a Slack
workspace. Specifically:

- the Agentforce Studio *Connections* wizard exposes no `connect/.../connections` or `.../channels`
  Connect route (probed live: `connect/bots/{id}/connections` `404`, and previously
  `connect/bot-versions/{id}/channels`, `nextgen-authoring/bundles/{id}/connections`
  `404`/`METHOD_NOT_ALLOWED`);
- the next-gen authoring SOR (`next-gen-authoring-connect-api`, bundle create/version/publish only)
  has **no** connect-to-channel operation, and the bundle-version detail
  (`GET /nextgen-authoring/bundle-versions/{id}`) carries **no** connections field;
- the `slackbridge-connect-api` SOR is runtime messaging + user-mapping reads only (no
  agent-connection or workspace-install op), and `GET /connect/agentforce-agent-info?agentType=…`
  returns only runtime routing (bot-runtime URL, region, tenant) — no channel wiring;
- the connection **link itself is not even API-readable**: its Slack-package backing entities
  (`ConversationSlackApplication`, `SlackAppConversationEvent`, `ConversationDefinitionChannelProvider`)
  are catalog-visible in `EntityDefinition` but `INVALID_TYPE` on both Data and Tooling query/describe.
  Agent *internals* ARE readable — `BotDefinition`, `BotVersion` (Data API only; `INVALID_TYPE` on
  Tooling), `GenAiPlannerDefinition` (unfiltered query, match `LinkedBotVersionId` client-side) — so a
  headless caller can confirm the agent exists and is Active, but cannot see or set its Slack connection.

So the skill **guides** the user through the clicks below. (Building/activating the agent itself IS
automatable — that is delegated to `service-itsm-agentic-setup-employee-agent-configure`; only the
Slack connection + workspace install are manual.) Do **not** claim the skill performed any of these.

## Salesforce side — create the agent↔Slack connection

Source: Slack Help, "Set up and manage Agentforce in Slack." Two paths depending on the builder.

### A) New Agentforce Studio (recommended)

1. Open the App Launcher and go to **Agentforce Studio → Agents**.
2. Select your **IT Service Employee Agent** to open the Agentforce Builder.
3. **Check the version state (top-left, next to the agent name).** You can only add a connection on
   a **Draft** version — the **+** is **disabled on a Committed version** (a committed version is
   read-only). If it reads **"Version N (Committed)"**, click **New Version** (top-right) first; the
   builder switches to **"Version N+1 (Draft)"** and the **+** becomes clickable.
   - This is version-lock, **not** an Active/Inactive issue — deactivating the agent does **not**
     unlock the **+** (Active/Inactive = whether it serves live; Committed/Draft = whether it's
     editable). Only creating a new Draft version unlocks it.
4. In the **Explorer** sidebar, expand **Connections**, click the **+** (plus) button, then
   **Add connection**.
5. Choose **Slack**, then click **Add to agent** — the panel confirms *"This agent is now available
   in Slack"* and a **Slack** node appears under Connections.
6. **Save** (top-right), then **Commit Version**, then **Activate**. Activate both publishes the
   connection and (re)brings the agent online — if you deactivated it earlier, this is what restores
   it, now with Slack attached.

### B) Legacy agent builder (only if not on new Studio)

1. **Setup** → search **"Agents"** → open your agent → **Connections** tab → **Add**.
2. Under **Connection**, select the **API** dropdown; enter a unique **integration name**.
3. Under **Connected app**, select **Slack**, then **Save**.

## Slack admin side — install the agent into the workspace

No Salesforce API — done in Slack.

- **Pro / Business+:** **Admin → Manage Agentforce** → next to the agent, **Review agent** → review
  permissions → **Install agent**.
- **Enterprise:** **Home** → your org name → **Tools & settings → Organisation settings →
  Salesforce → Agentforce** → **Review Agent** → **Install agent** → tick the workspace(s) →
  **Add to workspaces**.

## Grant a user access to use the agent (Salesforce API — automatable)

For an **Employee Agent**, Slack's *"Who can use this agent?"* shows **"Managed in Salesforce"** — so
member access is a **Salesforce permission-set grant**, not a Slack setting. It IS automatable, and the
gating permset is discoverable by reverse-lookup (verified live against a real org):

1. **Find which permset gates THIS agent** — the grant is a `SetupEntityAccess` row keyed to the agent's
   **BotDefinition** (channel-agnostic: one row covers every channel the agent is on). Query it on the
   **Data API** (Tooling rejects `SetupEntityAccess` as `INVALID_TYPE`):
   ```text
   dispatch_readonly GET /services/data/v67.0/query
     q: SELECT Id, ParentId, Parent.Name FROM SetupEntityAccess WHERE SetupEntityId = '<BotDefinition Id>'
   ```
   `Parent.Name` is the permset to assign (e.g. `Agent_Access` / "Agent Access"). Don't trust the permset
   *name/description* — the grant covers Slack regardless of what earlier setup named it.
   - **If this returns ZERO rows, no permset grants the agent yet** — expected when the agent hasn't had an
     access permset provisioned. Create one, then grant it the BotDefinition access:
     ```text
     dispatch POST /services/data/v67.0/sobjects/PermissionSet
       body: {"Name": "Agent_Access", "Label": "Agent Access"}
     dispatch POST /services/data/v67.0/sobjects/SetupEntityAccess
       body: {"ParentId": "<new permset Id>", "SetupEntityId": "<BotDefinition Id>"}
     ```
     `SetupEntityId` MUST be the **BotDefinition** id (`0Xx…`), NOT the GenAiPlannerDefinition (`16j…`).
     Do **not** send `SetupEntityType` — it's not insertable; the platform auto-resolves it from the id prefix.
2. **Check if the user already has it, then assign:**
   ```text
   dispatch POST /services/data/v67.0/sobjects/PermissionSetAssignment
     body: {"AssigneeId": "<User Id>", "PermissionSetId": "<permset Id from step 1>"}
   ```

> **Trap — do NOT assign the broad "Access Agents" (`Access_Agents`) permset to an employee end-user.**
> It fails: *"user license doesn't allow the permission: View Setup Audit Trail."* Assign the narrow
> per-agent **"Agent Access"** permset from step 1 instead — it carries the BotDefinition grant without
> dragging in setup-admin perms.

Access also requires the Slack member to be **mapped to a Salesforce user** (see Prerequisites) — the
permset grant + the Slack↔SF mapping together let that person invoke the agent in Slack.

### Pre-flight: will the agent actually reply? (mapping read — headless, verified live)

The single most common "agent stays silent" cause is a **missing Slack↔Salesforce user mapping**. There is
**no Salesforce/headless write API** to set it (probed live: `slackbridge-connect-api` exposes only a *read*
`GET .../team/{teamId}/user-mappings`; `slack-connect-api` is reCAPTCHA + Web-to-Lead only; no POST route
anywhere) — the mapping is set **Slack-admin-side only**. But you CAN read whether the *current* Slack user
is mapped, and should do so before telling the user the agent is ready:

```text
dispatch_readonly GET /services/data/v67.0/connect/slackbridge/connections
```
- `currentUserMapping.salesforceUserId != null` ⇒ the session's Slack user is mapped — the agent can reply.
- `currentUserMapping.salesforceUserId == null` ⇒ **NOT mapped** — the agent will stay silent no matter how
  the permset/connection are set. Send the user to do the Slack-side mapping (below), then re-read to confirm.
- `team.status` also confirms the workspace is `CONNECTED` and gives `teamId` + `teamDomain`.

> **Enterprise Grid vs single workspace — the mapping lives in a different Slack menu, and the SF-side
> mapping-table read can 404.** If `teamDomain` ends in `.enterprise.slack.com` (Enterprise Grid), the
> `connections` read returns the **grid-org id** (`E…` prefix), not a workspace `teamId` (`T…`). The bulk
> read `GET .../team/{teamId}/user-mappings` then **404s** with the grid-org id (no workspace teamId is
> surfaced), so fall back to the `currentUserMapping` read above for verification. Grid also changes WHERE
> the admin maps users: **Organisation settings**, not **Workspace settings** (see below).

## Manage the agent after install (Slack admin)

No Salesforce API — done in Slack, after the agent is installed. Source: Slack Help,
"Set up and manage Agentforce in Slack."

- **Edit the agent profile:** **Agentforce → "Managed by you"** → the agent's **three dots (⋯)** →
  **View agent profile → Edit** — update profile picture, suggested prompts, or agent managers.
- **Remove from a workspace:** **Manage agent → Manage → Remove from a workspace**.
- **Uninstall from the org:** **Manage agent → Manage → Uninstall from your organisation**.

These are teardown/maintenance actions — only walk the user through them if they explicitly ask to
change, remove, or uninstall an already-installed agent. They are not part of first-time setup.

## Prerequisites (from the Slack Help doc)

- Salesforce org with an **Agentforce** license; Slack workspace on **Pro / Business+ / Enterprise**.
- Salesforce **admin** access for the setup steps.
- Slack members need Salesforce accounts or provisional licenses; map users on the **Slack side**
  (no Salesforce write API exists for this — see the Pre-flight section above):
  - **Single workspace (Pro / Business+):** Slack **Admin → Workspace settings → Salesforce → Users**
    → **Add individually** / **Add by CSV**.
  - **Enterprise Grid** (`teamDomain` ends `.enterprise.slack.com`): Slack **org name (top-left) →
    Tools & settings → Organisation settings → Salesforce → Users** → **Add individually** /
    **Add by CSV**. (The `connections` read returns the grid-org `E…` id here, so verify the mapping
    via `currentUserMapping` rather than the bulk `team/{teamId}/user-mappings` read, which 404s.)

  The base Salesforce↔Slack connection is Steps 1–2 of the main skill.
- The Slack Help doc recommends building the agent from a **Slack pre-made template** and adding the
  **"General Slack actions"** subagent. The ITSM employee/fulfiller builder skills create the agent
  from the **ITSM** template instead — if the user specifically wants the Slack-optimized template or
  the General Slack actions subagent, that is authored in Agentforce Studio, outside these skills.

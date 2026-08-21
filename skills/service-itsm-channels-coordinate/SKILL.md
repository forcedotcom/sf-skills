---
name: service-itsm-channels-coordinate
description: "Top-level interactive coordinator for Employee Service (ITSM) channel setup. Presents menu of channel setup options (Teams, Slack, Swarming, Notifications, Portal) and delegates to the corresponding skill. Use this for: 'setup ITSM channels', 'configure employee service channels', 'set up service cloud communication channels', 'I want to configure ITSM integrations', or any general request for ITSM channel/integration setup where the user hasn't specified exactly which channel they want. DO NOT TRIGGER for requests that already name a specific channel or child skill (e.g. 'configure Teams', 'set up Slack', 'enable Swarming', 'configure ITSM notifications', 'create an employee portal') — route directly to the matching child skill instead."
metadata:
  version: "1.0"
  domains: ["Service"]
  mcpTools:
    headless-360:
      tools: ["dispatch"]
      semver: ">=1.0.0"
  relatedSkills:
    - "experience-portal-create"
    - "service-itsm-swarming-configure"
    - "service-itsm-teams-configure"
    - "service-itsm-teams-debug"
    - "service-itsm-teams-employee-agent-configure"
    - "service-itsm-teams-itdesk-configure"
    - "service-itsm-teams-itservice-configure"
---

# Employee Service (ITSM) Channels Setup Coordinator

Interactive coordinator that presents a menu of ITSM channel setup options and delegates to the appropriate child skill based on user selection.

## Scope

- **In scope**: Presenting the channel setup menu to the user. Delegating to child skills based on selection (Teams, Swarming, Portal). Validating prerequisites before delegation. Providing clear descriptions of each channel capability. **Notifications is the one exception** — no dedicated notifications child skill exists yet, so this coordinator enables the notification-channel org preferences inline for that choice (see Choice 4); those are the only setup-API writes it performs itself.
- **Out of scope**: Directly calling setup APIs for any channel that has a dedicated child skill (Teams, Swarming, Portal — always delegate). Channel-specific configuration details beyond the initial enablement. User permission assignment. Post-setup testing.

---

## Available Channel Setup Skills

This coordinator can invoke five distinct channel setup skills:

### 1. Microsoft Teams Setup
**Skill:** `service-itsm-teams-configure`

**What it does:**
- Enables the `service-cloud-itsm-teams-integration` Salesforce Go feature via headless-360's
  feature-enablement Connect API — the only verified path that flips `ITSMTeamsEnabled` (direct
  PATCH of the org preference is blocked with 401)
- Optionally enables the sibling `OrgHasITSMFulfillerTeams` / `OrgHasEmployeeServiceTeams` preferences
- Verifies `ITSMTeamsEnabled` afterward and reports the remaining manual (Microsoft-side) steps

**Prerequisites:**
- Teams ITSM add-on licenses
- Setup admin permissions

**Use when:** User wants Microsoft Teams integration for IT Service Desk or Employee Service apps.

**Teams sub-skills** `service-itsm-teams-configure` delegates to (surface these if the user asks for
a specific half): `service-itsm-teams-itdesk-configure` (fulfiller/IT Desk checklist),
`service-itsm-teams-itservice-configure` (employee/IT Service checklist),
`service-itsm-teams-employee-agent-configure` (embedded "Ask AI Agent"), and
`service-itsm-teams-debug` (diagnose a failing Teams setup — login, tab loading, agent, swarming, SSO).

---

### 2. Slack Setup
**Skill:** the installed Slack ITSM setup skill — resolve it from the skills catalog at delegation
time by name pattern (see Choice 2 in the workflow); do not hardcode a single skill name.

**What it does:**
- Enables Slack integration for ITSM (Employee Service / IT Service on Slack)
- Configures the Slack workspace connection and required org preferences/permission sets

**Prerequisites:**
- Slack workspace with admin access
- Org has Slack integration enabled

**Use when:** User wants Slack integration for ITSM.

---

### 3. Swarming Setup
**Skill:** `service-itsm-swarming-configure`

**What it does:**
- Enables the `service-cloud-swarming` Salesforce Go feature via headless-360's feature-enablement
  Connect API
- Sets the "Select a Collaboration Tool" picklist to `Teams` via
  `PATCH /services/data/v67.0/setup/org/values/SWARM_COLLABORATION_TOOL` — fully automated, no
  manual click required

**Prerequisites:**
- Microsoft Teams integration (Swarming requires Teams — run `service-itsm-teams-configure` first)

**Use when:** User wants collaborative problem-solving for ITSM.

---

### 4. Notifications Setup
**Skill:** none yet — handled inline by this coordinator (see Choice 4)

**What it does:**
- Enables the master Notifications feature
- Configures notification channels: Email, In-App, Slack, Teams

**Prerequisites:**
- Multi-channel Notifications feature enabled
- View Setup + Customize Application permissions

**Use when:** User wants to enable multi-channel notifications for ITSM events.

**Note:** For demo, execute inline until dedicated skill is created.

---

### 5. Portal Setup
**Skill:** `experience-portal-create`

**What it does:**
- Creates a Digital Experience portal for employee self-service
- Supports Employee Service, Partner, and Customer portals

**Prerequisites:**
- Vary by portal type

**Use when:** User wants to create a portal for employee self-service.

---

## Workflow

### Step 1: Present Menu to User

**Always present the menu** before proceeding:

```text
I can help you set up ITSM channels. Which channel would you like to configure?

**Choose one:**

1. **Microsoft Teams Setup**
   - Enable Teams integration master toggle
   - Provision authentication infrastructure
   - Prerequisites: Teams ITSM licenses required

2. **Slack Setup**
   - Enable Slack integration for ITSM
   - Configure Slack workspace connection
   - Prerequisites: Slack workspace with admin access

3. **Swarming Setup**
   - Enable Swarming for collaborative problem-solving
   - Configure Swarming channels (requires Teams)
   - Prerequisites: Teams integration + Swarming feature

4. **Notifications Setup**
   - Enable multi-channel notifications (Email, In-App, Slack, Teams)
   - Configure notification delivery channels
   - Prerequisites: Multi-channel Notifications feature

5. **Portal Setup**
   - Create Digital Experience portal for employee self-service
   - Choose portal type during setup
   - Prerequisites: Vary by portal type

Please respond with the number (1, 2, 3, 4, or 5) of your choice.
```

**Do NOT proceed** until the user provides a choice.

---

### Step 2: Validate Prerequisites

Based on user's choice, check prerequisites **before** delegating to child skills:

#### For Choice 1 or 3 (Teams Integration):
1. Check if Teams master toggle API is accessible
2. Attempt to query current toggle state
3. If prerequisites fail, inform user about missing Teams ITSM licenses

#### For Choice 2 or 4 (Notifications):
1. Check if Notifications preference APIs are accessible
2. Verify Multi-channel Notifications feature is available

**If prerequisites fail:**
- Explain what's missing (licenses, features, permissions)
- Offer alternative choices (e.g., suggest #4 if Teams licenses missing)
- Do NOT attempt to execute the chosen configuration

---

### Step 3: Delegate to Child Skill

#### Choice 1: Microsoft Teams Setup

**Delegation:**
```text
Invoke the service-itsm-teams-configure skill.
```

**On success:**
"Success: Microsoft Teams integration master toggle is enabled. Background provisioning in progress (2-5 minutes).

Next steps:
- Configure Azure AD application
- Set up Salesforce IT Desk and/or IT Service apps"

**On failure:**
"Failed: Teams integration failed: [error details]

Resolution:
- Verify org has Teams ITSM licenses
- Try option #4 (Notifications) instead"

---

#### Choice 2: Slack Setup

**Resolve the delegation target deterministically from the skills catalog, then invoke the result.**
Do not decide by prose guesswork — look the skill up:

```text
1. Query the installed skills catalog for a Slack ITSM setup skill, in priority order:
     a. any skill whose name matches ^service-itsm-slack-.*-configure$   (preferred)
     b. any skill whose name matches ^(setup|service)-.*slack.*(configure|enable)$
2. If the lookup returns a skill → invoke that exact skill and stop.
3. If the lookup returns nothing → fall through to the manual instructions below.
```

**Manual instructions (only if the catalog lookup returned no Slack skill):**
"No Slack ITSM setup skill is installed in this environment. To configure Slack manually:
1. Navigate to: Setup → Integrations → Slack
2. Connect your Slack workspace
3. Configure Slack apps for ITSM"

---

#### Choice 3: Swarming Setup

**Delegation:**
```text
Invoke the service-itsm-swarming-configure skill.
```

**On success:**
"Success: Swarming feature enabled, and the Collaboration Tool is now set to Teams — 'Set Teams as
Collaboration Tool for Swarming' is fully complete, no manual click needed."

**On failure:**
"Failed: Swarming setup failed: [error details]

Resolution:
- Ensure Microsoft Teams integration is enabled first (use option #1)
- Verify org has the Swarming feature entitlement"

---

#### Choice 4: Notifications Setup

**Inline enablement (in-scope exception — no dedicated notifications child skill exists yet).**
Unlike the other choices, this branch enables the notification-channel org preferences itself. Issue
the writes with `mcp__headless-360__dispatch` (`PATCH`, full `/services/data/vXX.0/...` path). When a
dedicated `setup-itsm-notifications-*` child skill lands, delegate to it and drop this inline block.

**Step 4.1: Enable Master Notifications Preference**
```text
PATCH /services/data/v66.0/setup/org/preferences/Notifications
Body: {"desiredState": true}
```

**Step 4.2: Enable Individual Channels**
```text
PATCH /services/data/v66.0/setup/org/preferences/EmailNotifications
Body: {"desiredState": true}

PATCH /services/data/v66.0/setup/org/preferences/InAppNotifications
Body: {"desiredState": true}

PATCH /services/data/v66.0/setup/org/preferences/SlackNotifications
Body: {"desiredState": true}

PATCH /services/data/v66.0/setup/org/preferences/TeamsNotifications
Body: {"desiredState": true}
```

**On success:**
"Success: All notification channels enabled:
- Email Notifications
- In-App Notifications
- Slack Notifications
- Teams Notifications

Next steps:
- Create notification definitions at: Setup → Service → Notifications
- Configure ITSM event triggers
- Customize message templates"

**On failure:**
"Failed: Notification channels setup failed: [error details]

Resolution:
- Verify org has Multi-channel Notifications feature
- Confirm you have Customize Application permission"

---

#### Choice 5: Portal Setup

**Delegation:**
```text
Invoke the experience-portal-create skill.
```

The portal creation skill will handle all clarifying questions (portal type, name, URL prefix, etc.).

**After delegation:**
"Success: Portal setup delegated to experience-portal-create skill. Follow the prompts to complete portal creation."

---

## Decision Tree

```text
User requests ITSM channel setup
  ↓
Present menu (5 options)
  ↓
User selects option (1-5)
  ↓
Validate prerequisites (optional)
  ↓
  ├─ Choice 1: Invoke service-itsm-teams-configure
  ├─ Choice 2: Resolve the Slack skill from the catalog, then invoke it (or manual instructions)
  ├─ Choice 3: Invoke service-itsm-swarming-configure
  ├─ Choice 4: Execute notifications setup inline (demo mode)
  └─ Choice 5: Invoke experience-portal-create
  ↓
Report outcome to user
  ↓
Suggest next steps
```

---

## Rules / Constraints

| Constraint | Rationale |
|---|---|
| Always present options before proceeding | User may not know what's possible or what their org supports |
| Validate prerequisites before delegating | Catch licensing/feature gaps early before invoking child skills |
| Choice 4 uses manual API calls, not a child skill | No existing skill for "notifications without specific channels" |
| Do not retry failed delegations | Child skills handle their own retries; surfacing error to user for decision |
| Partial success is acceptable | If Teams succeeds but Notifications fails, user can retry Notifications separately |

---

## Prerequisites by Choice

### Choice 1: Teams Setup
- Teams ITSM licenses
- Setup admin permissions

### Choice 2: Slack Setup
- Slack workspace with admin access
- Org has Slack integration enabled

### Choice 3: Swarming Setup
- Microsoft Teams integration (required for Swarming — run Choice 1 first)

### Choice 4: Notifications Setup
- Multi-channel Notifications feature enabled
- View Setup + Customize Application permissions

### Choice 5: Portal Setup
- Vary by portal type (see experience-portal-create skill)

---

## Error Handling

### If user provides invalid choice:
"Please choose a valid option: 1, 2, 3, 4, or 5."

### If prerequisites check fails:
"I've detected that your org is missing [specific requirement]. 

I recommend choosing [alternative option] instead, which works with your current org configuration."

### If delegation fails:
"The [child skill name] encountered an error: [error message]

[Provide specific resolution steps based on error]"

### If user is unsure which to choose:
"Let me help you decide:

- **Do you want to enable communication channels?**
  - Microsoft Teams → Choose #1
  - Slack → Choose #2
  - Both → Run #1, then #2

- **Do you want collaborative problem-solving?**
  - Swarming (requires Teams) → Choose #1 first, then #3

- **Do you want notifications for ITSM events?**
  - Multi-channel notifications → Choose #4

- **Do you want a portal for employee self-service?**
  - Digital Experience portal → Choose #5"

---

## Related Operations

After completing channel setup via this coordinator:

- **Configure channel-specific settings** — customize each channel's behavior
- **Create notification definitions** — configure ITSM event triggers (if Notifications selected)
- **Set up Azure AD** — required for Teams (if Teams selected)
- **Test channels** — verify each channel is working

To modify later:
- **Enable additional channels** — rerun this coordinator with different option
- **Disable channels** — use corresponding disable skills
- **Update channel settings** — navigate to Setup → [Channel] → Settings

---

## Embedded Agentforce Agent in Microsoft Teams

Making the embedded Agentforce agent actually **reply** inside the Teams custom client
("Salesforce Employee Assist" / "Ask AI Agent") is the hardest, most under-documented part of
Teams ITSM. It is now a dedicated skill:

**→ `service-itsm-teams-employee-agent-configure`**

The verified architecture is a **Web** Enhanced-messaging channel with **User Verification OFF
(auth mode false)** — the Teams client uses the scrt2 *unauthenticated* token endpoint — the
**`Teams_AgentForce`** custom-client Embedded Service Deployment, an Omni-Flow routing flow
targeting a **real, Active** Agentforce Employee Agent, and an **Agent Access permission set**
enabling that agent for the portal user. That skill also covers the key diagnostic: "agent joins
then leaves without replying" has two fixable causes — auth mode left ON (→ `/eventrouter/v1/sse`
401) and the portal user missing Agent Access — not an unfixable agent-runtime failure.

---

## API Type Classification

This coordinator:
- **Does NOT call APIs directly** (except for Choice 4 demo mode) — it delegates to child skills
- **Uses interactive menu** for user selection
- **Child skills handle all API calls**

Child skills used:
- `service-itsm-teams-configure` — headless-360 (Salesforce Go feature-enablement Connect API)
- Slack ITSM setup skill (resolved from catalog by name pattern) — child skill handles its own API calls
- `service-itsm-swarming-configure` — headless-360 (Salesforce Go feature-enablement Connect API)
- Notifications — no dedicated child skill yet; handled inline via Connect API (see Choice 4)
- `experience-portal-create` — Connect API

---

## Important Notes

1. **This is an interactive coordinator** — it MUST present the menu and wait for user choice before executing anything.

2. **Always delegate to child skills** — this coordinator doesn't implement channel-specific logic; it only routes to the appropriate skill.

3. **Some skills may not exist yet** — if a skill is not found, provide manual setup instructions so the user isn't blocked.

4. **Choice 4 (Notifications) executes inline** — no dedicated notifications child skill exists yet, so this coordinator enables the notification-channel preferences directly (see Choice 4). When such a skill lands, delegate to it and drop the inline block.

5. **Prerequisites vary by channel** — each channel has different licensing and feature requirements.

6. **No retry logic** — this coordinator doesn't retry failed operations. Surface the error and let user decide next steps.

7. **Educational role** — help users understand what each channel does and which prerequisites they need.

---
name: afcc-setup-coordinate
description: "Orchestrates end-to-end headless setup of Agentforce Contact Center (AFCC) on a Salesforce org. Scans the org first, presents a delta plan for approval, then sequentially provisions demo users, Omni-Channel base settings, a human queue with routing config and members, presence statuses, permission sets, a PSTN voice number, and an active PstnVoice MessagingChannel wired to the queue. Interactive at key decision points — never assumes country, number type, queue names, or user counts. TRIGGER: set up AFCC, configure Agentforce Contact Center, stand up voice contact center, AFCC migration setup, provision AFCC org headlessly."
allowed-tools: Bash(sf org display:*) Bash(sf data query:*) Bash(sf api request rest:*) Bash(sf project deploy start:*) Bash(sf project retrieve start:*) Bash(scripts/*) Bash(./scripts/*) Bash(bash scripts/*) Read Write AskUserQuestion
metadata:
  version: "1.0"
  minApiVersion: "67.0"
  domains: ["Service", "Agentforce"]
  cliTools:
    - tool: ["sf"]
      semver: ">=2.0.0"
    - tool: ["jq"]
      semver: ">=1.6"
  relatedSkills:
    - "service-agentforce-contact-center-coordinate"
    - "service-omni-agent-users-create"
    - "service-omni-base-settings-configure"
    - "service-omni-queue-deploy"
    - "service-omni-queue-routing-config-deploy"
    - "service-omni-queue-members-assign"
    - "service-omni-presence-status-deploy"
    - "service-omni-permission-set-assign"
    - "service-omni-sidebar-configure"
---

# afcc-setup-coordinate: Agentforce Contact Center End-to-End Setup

Orchestrates full headless provisioning of an Agentforce Contact Center org. Scans existing org state before every write, presents a delta plan at the Approve gate, and delegates each configuration step to the appropriate sub-skill. Interactive at key decision points — never assumes country, number type, queue names, or user counts.

## Scope

**In scope:** demo user provisioning (or reusing existing users), Omni-Channel base settings, human queue + routing config + members, presence statuses, permission set assignment (including the Contact Center Admin set the executing user needs), PSTN voice number procurement, PstnVoice MessagingChannel creation wired to the queue, and a Lightning console app that surfaces Omni so the setup can be tested end to end.

**Out of scope:** Agentforce agent setup, escalation flows, digital channels (WhatsApp/SMS/LINE/Apple/Facebook), Service AI features, supervisor configuration, and org authentication (the target org must already be authenticated before invoking this skill).

---

## Prerequisites

- **Authenticated org** — run `sf org login web --alias <name> --instance-url <url>` before invoking this skill. This skill never runs an interactive login.
- **Salesforce CLI** (`sf`) ≥ 2.0.0 and `jq` ≥ 1.6 installed.
- **AFCC-entitled org** — org must have Agentforce Contact Center and Service Cloud Voice licenses available. Creating agent users also needs a free Service Cloud User feature-license seat; without one, reuse existing users (Step 1).
- **Contact Center Admin permission set** — the executing user needs `ContactCenterAdminNativeCCaaS` (label "Agentforce Contact Center Admin (Salesforce Voice)") before the number and voice channel can be created. Step 4 assigns it. The sibling sets are `ContactCenterAgentNativeCCaaS` (Rep) and `ContactCenterSupervisorNativeCCaaS`.
- **Sub-skill assets** — the repo copies of `service-omni-presence-status-deploy` and `service-omni-permission-set-assign` do not bundle the DX assets their scripts need (they exit with "Assets DX project not found" / "Omni_Agent missing"). This skill does not modify them: it carries the missing files in `assets/sub-skill-assets/<sub-skill>/` and overlays them onto a temporary copy of the sub-skill at run time (Step 4).

---

## Stage: INTAKE

Collect three required inputs before any org access. Gather all three in a single `AskUserQuestion` call:

1. **Org alias** — "What is your org alias?"
2. **Voice number type** — Toll Free or 10DLC
3. **Country** — US or CA

After collecting the alias, verify the org is reachable:

```bash
sf org display --target-org <alias> --json
```

Read `result.instanceUrl` to confirm success. If this command fails, stop immediately and tell the user to authenticate first — do not attempt an interactive login.

Store all three inputs. Every downstream stage reads them from context — do not re-ask.

---

## Stage: AUDIT

Run the audit script to probe the org and write `org_profile.json`:

```bash
bash scripts/audit_org.sh <alias> org_profile.json
```

This queries (read-only — no writes):

| What | SOQL |
|---|---|
| Active users | `SELECT Id, Name, Username, Profile.Name FROM User WHERE IsActive=true ORDER BY Name` |
| Service channels | `SELECT Id, DeveloperName, MasterLabel FROM ServiceChannel` |
| Queues | `SELECT Id, Name, DeveloperName FROM Group WHERE Type='Queue'` |
| Routing configs | `SELECT Id, DeveloperName, MasterLabel, RoutingModel FROM QueueRoutingConfig` |
| Presence statuses | `SELECT Id, DeveloperName, MasterLabel FROM ServicePresenceStatus` |
| Messaging channels | `SELECT Id, DeveloperName, MasterLabel, MessageType, IsActive FROM MessagingChannel` |
| Channel lines | `SELECT Id, Code, CodeStatus FROM CommunicationChannelLine` (Tooling API) |
| Permission sets | `SELECT Id, Name, Label FROM PermissionSet WHERE Name IN ('Omni_Agent','ContactCenterAdminNativeCCaaS','ContactCenterAgentNativeCCaaS','ContactCenterSupervisorNativeCCaaS')` plus the `PermissionSetAssignment` rows for the active users |
| Console apps | `SELECT DurableId, DeveloperName, Label, NavType FROM AppDefinition WHERE NavType='Console'` |

All results are written to `org_profile.json`. Every downstream step reads from this file — do not re-query what the audit already resolved. The audit also checks the artifacts a freshly licensed AFCC org ships with — service channels `sfdc_livemessage` and `sfdc_phone`, the queue `Default_Queue_Agentforce_Contact_Center`, and the permission sets `ContactCenterAdminNativeCCaaS` / `ContactCenterAgentNativeCCaaS` / `ContactCenterSupervisorNativeCCaaS` — and lists any that are absent under `missingDefaults`. Absent means someone most likely deleted them, or the org is not fully licensed. Do not silently plan a create for these: show them at APPROVE with `⚠ missing — looks deleted`, tell the user they should exist by default and need restoring (re-provision the license or recreate them), and let the user decide to continue or stop. Presence statuses are not in this list; they are normally created by Step 4.

A query that fails is recorded under `errors` in `org_profile.json` and the script exits non-zero, so a failed query is never mistaken for an empty result; stop and report it instead of planning from partial data.

---

## Stage: APPROVE

Present the delta plan based on `org_profile.json`. **No write happens until the user approves.**

Render one row per artifact:

```text
STEP  ARTIFACT              FOUND IN ORG             DEFAULT ACTION
1     Agent users           <N active users>         reuse / create new
2     Omni base settings    present / missing        reuse / configure
3     Queue                 <list names or none>     reuse / create new
      Routing config        present / missing        reuse / create new
4     Presence statuses     <N found or none>        reuse / create new
      Permission sets       partial / missing        assign missing
      Contact Center Admin  held / not held          assign to executing user
5     Voice number          <number + status / none> reuse / procure new
6     Voice channel         present / missing        reuse / create new
7     Console app + Omni    <app names or none>      reuse / create new

→ Proceed with this plan, or tell me which rows to change.
```

**Status:**
- `✅` — exists and reusable → default is SKIP
- `➕` — missing → will create
- `♻️` — exists but stale or mismatched → will recreate
- `⚠` — an out-of-the-box artifact from `missingDefaults` is absent (likely deleted) → ask the user to restore it before relying on it

Wait for the user to confirm. If any row is changed, update the plan before proceeding.

---

## Execute

All steps run sequentially. Stop and report the full error if any step fails — do not continue past a failure.

Print one line per step:
- `✔` — completed this run
- `⏭ SKIP` — already present, reused per approval
- `⧗` — in progress
- `⚠` — UI-only gap, pausing for user input
- `⛔` — blocked, stopping

---

### Step 1 — Demo users

**Delegates to:** `service-omni-agent-users-create`

Check `org_profile.json § existing.users`. Present the existing users and ask:

```text
AskUserQuestion:
  "I found <N> active users on this org. How many agent users do you need for AFCC?"
  (Existing users will be reused where possible; only missing ones will be created.)
```

Pass the target count and alias to the sub-skill. It handles user creation, profile assignment, and PSL assignment.

**Reuse existing users:** creating a user sets the Service Cloud User feature flag, which needs a free feature-license seat. If the sub-skill fails with `LICENSE_LIMIT_EXCEEDED` ("content feature license limit exceeded"), that seat is the cause, not the user-license pool, and its strip-and-retry path does not catch it. Do not retry; ask which existing users should act as agents and carry their usernames forward as the explicit-members list for Steps 3 and 4.

**Skip:** if the org already has sufficient active users and the user approved reuse at APPROVE, emit `⏭ SKIP — reusing <N> existing users`.

---

### Step 2 — Omni-Channel base settings

**Delegates to:** `service-omni-base-settings-configure`

Check `org_profile.json § existing.serviceChannels`. If both `sfdc_livemessage` and `sfdc_phone` service channels are already present, Omni base settings are configured.

**Skip:** if both standard service channels exist, emit `⏭ SKIP — Omni base settings already configured`.

---

### Step 3 — Queue + routing config + queue members

**Delegates to:** `service-omni-queue-deploy`, `service-omni-queue-routing-config-deploy`, `service-omni-queue-members-assign`

Check `org_profile.json § existing.queues`. If queues exist, ask:

```text
AskUserQuestion:
  "I found these queues: <list queue names>.
   Use one of these or create a new queue?"
  Options: [each existing queue name] + [Create new queue]
```

If creating new, ask for the queue name (suggest `AFCC_Support_Queue` as default but do not auto-apply — wait for user input).

Sub-skill responsibilities and required order:
1. `service-omni-queue-routing-config-deploy` — creates `QueueRoutingConfig` with `RoutingModel=LeastActive`, `CapacityWeight=1`, `RoutingPriority=1` (must be created FIRST — has no `QueueId` field)
2. `service-omni-queue-deploy` — creates the `Group` record WITHOUT `QueueRoutingConfigId`, then POSTs a `QueueSobject` (`SobjectType=VoiceCall`), then PATCHes `Group.QueueRoutingConfigId` to link the config
3. `service-omni-queue-members-assign` — assigns users from Step 1 as `GroupMember` records

When Step 1 reused existing users, pass their usernames to `service-omni-queue-members-assign` in its explicit-members mode (4th argument) instead of the generated `agent{N}.<suffix>` pattern.

Store the resolved queue Id for use in Step 6.

**Skip:** if the user selected an existing queue at APPROVE, emit `⏭ SKIP — reusing queue <name> (<Id>)`.

---

### Step 4 — Presence statuses + permission set assignment

**Delegates to:** `service-omni-presence-status-deploy`, `service-omni-permission-set-assign`

Check `org_profile.json § existing.presenceStatuses`. If statuses exist, ask:

```text
AskUserQuestion:
  "I found <N> existing presence statuses: <list names>.
   Reuse these or create new ones?"
```

Sub-skill responsibilities:
- `service-omni-presence-status-deploy` — creates `ServicePresenceStatus` records. Run it with the `VoiceCall` channel so `Available_Voice` (mapped to `sfdc_phone`) and `Busy` exist.
- `service-omni-permission-set-assign` — assigns `Omni_Agent` to the agent users. It is generated at run time and grants access to the presence statuses that exist.

**Run the sub-skills from a temporary copy, never edit them in place.** For each of the two sub-skills: copy the sub-skill directory to a temp dir, copy `assets/sub-skill-assets/<sub-skill>/.` over its `assets/`, then run its script from the temp copy. This supplies the DX project, the `Available_Voice`/`Busy` status XMLs, and the `Omni_Agent` placeholder that gates the permission-set self-heal.

`service-omni-permission-set-assign` resolves only the generated `agent{N}.<suffix>` users and has no way to be told otherwise. When Step 1 reused existing users, still run it, because it deploys `Omni_Agent` before it looks up users, and expect it to then block with "Expected N ACTIVE agent users"; that block is not a failure here. Assign `Omni_Agent` to the reused users with a direct `PermissionSetAssignment` POST, after checking `org_profile.json § existing.permissionSetAssignments` so an existing assignment is reused.

Then assign `ContactCenterAdminNativeCCaaS` to the executing user (a direct `PermissionSetAssignment` POST; check the audit first so an existing assignment is reused). Steps 5 and 6 fail without it. It is a license-bound standard set: it cannot be retrieved, edited, or given presence-status access, so presence access always comes from `Omni_Agent`, and the admin set is assigned in addition to it.

**Skip:** if presence statuses exist and user approved reuse at APPROVE, emit `⏭ SKIP — reusing <N> presence statuses`.

---

### Step 5 — Voice number procurement

**Delegates to:** `service-agentforce-contact-center-coordinate` (number procurement path only)

Check `org_profile.json § existing.channelLines`. If a `CommunicationChannelLine` with `CodeStatus=Live` already exists, ask:

```text
AskUserQuestion:
  "I found an existing Live number: <phone number>.
   Use this number or procure a new one?"
```

If procuring new, pass country and number type from INTAKE to the sub-skill. The sub-skill:

1. Resolves the org's max API version at runtime — never hardcodes a version
2. Fetches available numbers: `GET .../connect/number-management/v1/numbers?countryCode=US&phoneNumberType=Toll%20Free` (URL-encode `Toll Free` → `Toll%20Free`; required params are `countryCode` and `phoneNumberType`)
3. Presents the returned pool (up to 5) for the user to pick (max 4 options per `AskUserQuestion`)
4. Procures the chosen number via `POST .../connect/number-management/v1/number` with `{phoneNumberType, country, phoneNumber}` (201/200 on success)
5. Calls `POST .../connect/number-management/v1/numberStateReconcile` with `{phoneNumber}`, then polls `CommunicationChannelLine WHERE Code='<phone>'` (Tooling API) until `CodeStatus=Live` (5s × 3 retries)

Store the procured number (E.164) and `CommunicationChannelLine` Id for Step 6.

**Stop:** if the sub-skill exits with code 4 (reconcile returned non-2xx), stop and report the error. Do not proceed to Step 6.

**Wait for Live, then stop:** the sub-skill's own polling (5s × 3) is short, so if the number is not `Live` when it returns, keep polling `SELECT Id, Code, CodeStatus FROM CommunicationChannelLine WHERE Code='<phone>'` every 15s for up to 3 minutes. Proceed to Step 6 the moment `CodeStatus=Live`. If it is still `Provisioning` or `Requested` at 3 minutes, stop: tell the user the number is not live after 3 minutes, give its `CommunicationChannelLine` Id and last `CodeStatus`, record it in `gap_report.md`, and let them decide whether to wait longer and re-run (the procured number is reused, not re-bought) or abandon. Do not create the channel on a non-live line.

---

### Step 6 — Voice channel create + bind number to queue

**Delegates to:** `service-agentforce-contact-center-coordinate` (channel creation path)

Inputs read from prior steps:
- Procured number in E.164 format (Step 5)
- `CommunicationChannelLine` Id (Step 5)
- Queue Id (Step 3)

The sub-skill creates a `PstnVoice` `MessagingChannel` via REST POST with:

| Field | Value | Notes |
|---|---|---|
| `MessageType` | `PstnVoice` | Required |
| `ChannelLineId` | `<CommunicationChannelLine.Id>` | The number binding; the sub-skill's `create-voice-channel.sh` binds this way. Drop only if the field is not present on this org |
| `MessagingPlatformKey` | `<E.164 phone>` | Createable, NOT updateable. Populated automatically from the channel line when `ChannelLineId` is set; send it explicitly only if `ChannelLineId` is dropped |
| `SessionHandlerId` | `<Queue.Id>` | Routes calls to the queue |
| `IsActive` | `true` | Required |

**Skip:** if `org_profile.json § existing.messagingChannels` already contains an active `PstnVoice` channel wired to the correct queue, ask whether to reuse or recreate.

**Stop:** any non-2xx response stops the run and prints the full request + response for diagnosis.

---

### Step 7 — Console app with Omni (rep surface)

**Delegates to:** `service-omni-sidebar-configure` (reuse path only); the create path deploys `assets/console-app/` directly because no sub-skill creates a console app.

Without a Lightning console app that shows Omni, reps cannot answer the new number and the setup cannot be tested end to end. Check `org_profile.json § existing.consoleApps`, then ask:

```text
AskUserQuestion:
  "I found these console apps: <list or none>.
   Reuse one (Omni sidebar gets enabled) or create AFCC_Service_Console?"
  Options: [each existing console app] + [Create AFCC_Service_Console]
```

**Create:** deploy `assets/console-app/` from a temporary DX project (an `sfdx-project.json` plus `force-app/main/default/{applications,profiles}`), with explicit metadata flags so nothing else is deployed:

```bash
sf project deploy start --target-org <alias> \
  --metadata CustomApplication:AFCC_Service_Console \
  --metadata Profile:Admin --metadata Profile:Standard
```

The app is a Lightning console (`navType` Console, tabs Home/Case/Contact/Account) with `isOmniPinnedViewEnabled=true`. The two Profile files only carry `applicationVisibilities`, so the deploy is a partial update that changes nothing else on System Administrator (`Admin`) or Standard User (`Standard`). The app is visible only to the profiles listed; add more profile files to widen it.

**Reuse:** run `service-omni-sidebar-configure <alias> <app DeveloperName>` to turn on the pinned Omni sidebar.

**Verify:** query `AppDefinition` for the app and confirm `isOmniPinnedViewEnabled` by retrieving the `CustomApplication`. Run the retrieve from the same temporary DX project and `mkdir -p force-app` first; otherwise it fails with `MissingPackageDirectoryError` because `sfdx-project.json` points at a `force-app` directory that doesn't exist yet.

**Skip:** if the chosen console app already has `isOmniPinnedViewEnabled=true` and is visible to the target profiles, emit `⏭ SKIP — console app <name> already surfaces Omni`.

The Omni surface is the pinned sidebar. A utility-bar Omni item is not created: its FlexiPage component name could not be resolved (guesses under `runtime_service_omnichannel:` fail with "couldn't retrieve the design time component information"), so add one by hand in App Manager if wanted.

Hand the user the test recipe: App Launcher → the app → Omni-Channel → set status "Available for Voice" → call the procured number.

---

## Stage: HANDOFF

Write `gap_report.md` using `assets/gap_report_template.md`. Fill every field with values from this run:

- Org alias + instance URL
- Country + number type
- Each step: status glyph + artifact name + Id
- Procured phone number
- `CommunicationChannelLine` Id + CodeStatus
- Queue name + Id
- `MessagingChannel` Id, DeveloperName, `MessagingPlatformKey`, `SessionHandlerId`, `IsActive`
- Console app name + whether Omni is pinned, and which profiles can see it
- Any gaps or deferred verifications

End with one line: **`Outcome: SUCCESS`** or **`Outcome: FAILED at Step <N> — <exact error>`**.

---

## Rules / Constraints

| Constraint | Reason |
|---|---|
| Never run an interactive login | Auth lifecycle is out of scope |
| Scan org before every create | Idempotency — never blindly recreate what already exists |
| Never hardcode IDs (queue, channel, user) | All IDs are org-specific; always resolve by name |
| Never hardcode API version | Resolve org max version at runtime; hardcoded v68 silently 404s on orgs with lower ceiling |
| Bind number via `ChannelLineId` (and `MessagingPlatformKey`) at create time | `MessagingPlatformKey` is createable but NOT updateable; a channel created without the binding cannot be corrected |
| Stop on non-2xx API response | Partial setup left silent is worse than a clear failure |
| Present delta plan before any write | User must approve before any org modification |
| One `AskUserQuestion` per decision point | Never trickle one question per step — batch where possible |

---

## Gotchas

Known failures and fixes for each step are in `references/gotchas.md`. Read it when a step errors, for example `LICENSE_LIMIT_EXCEEDED` in Step 1, a non-live number in Step 5, or `FIELD_INTEGRITY_EXCEPTION` in Step 6.

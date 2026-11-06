# Status Checks — Incident Management Setup Orchestrator

How to read each feature's real state from the org. Read it **before you show any status** — the two
prerequisite gates, the menu table, the re-read after a feature runs, the completion summary, and the
track status the ITSM setup coordinator shows for Incident Management. Status is never carried over from
earlier in the conversation, from a previous session, or from what the user says is already done: the org
may have changed since, and a resumed session can't tell. Every read here is a `GET` through
`dispatch_readonly`; nothing here writes.

**Contents:** status labels · how to read · the Salesforce Go rule · the two gates · row P (preferences) ·
row 1 (personas) · row 2 (Priority Matrix) · row 3 (SLA) · row 4 (dashboards) · row 5 (Email-to-Incident) ·
row 6 (Major Incident Management) · row 7 (Broadcast Communications) · row 8 (AI) · row 9 (privilege) ·
row 10 (audit tracking) · track roll-up.

---

## Status labels

| Label | When |
|-------|------|
| **Done** | The org reads back the finished state |
| **In progress** | Partly set up — some of it reads back and some doesn't, or the org is still working on it |
| **Not done** | Not set up yet |
| **Not available** | The org isn't licensed for it, or Salesforce hasn't provisioned it — no setup step here can fix that |
| **Couldn't check** | A read failed or was refused. Never show this as **Not done** — you don't know |

Every status comes with a short plain-language note saying what the org showed ("Turned on", "4 of 6 on",
"Nobody has an Incident persona yet").

## How to read

- `v{version}` in a path is the org's full API version, as in Behavior step 2 (e.g. `68.0`). These are
  the reads to use; if a SOR's `describe` shows a different path for the same read, use that one.
- `status_code` `200` → read `body`.
- Any other `status_code`, an error body (`body[0].errorCode`), or no connected org → **Couldn't check**
  for the row that made the read, unless that row's table says otherwise. Give the reason in plain words
  ("you don't have access to read this yet", "the org didn't respond") — never the code or the path.
- A status read never stops the flow: a refused read only marks its row **Couldn't check**. The hand-off
  protocol's stop on `401` / `403` / `404` applies when a feature runs, not here.
- Read the two gates first (Behavior step 2), and the rows only when both gates let you continue. Run the
  reads one at a time, in the order below, skipping the ones a row says to skip.
- In each row's table, take the first line that fits.
- Salesforce Go's checklist for IT Service Incident Management is mostly ticked by hand, so these rows read
  the real configuration instead. A row can read **Done** while Go's checklist shows it unticked, or the
  reverse — if the user asks, say so.

---

## The Salesforce Go rule

The two gates, the dashboards check (row 4), and Broadcast Communications (row 7) are Salesforce Go
features. Salesforce Go shows a feature as turned on only when **both** reads agree:

```json
mcp__headless-360__dispatch_readonly({ "url": "/services/data/v{version}/connect/setup/discovery/feature/<featureApiName>/status", "method": "GET" })
```

```json
mcp__headless-360__dispatch_readonly({ "url": "/services/data/v{version}/connect/setup/discovery/feature/<featureApiName>/automation/status", "method": "GET" })
```

- the status read → `body.status` is `ENABLED`, **and**
- the automation read → every `body.automationStepStatuses[].status` is `Completed` (an empty list
  counts as all finished). Make this read only when the status read returned `ENABLED`.

A feature that reads `ENABLED` while one of its setup steps is `NotStarted`, `InProgress`, or `Error` is
**not** fully turned on: Salesforce Go shows its setup as unfinished.

| What the reads show | Label | Note |
|---------------------|-------|------|
| The status read failed, or it read `ENABLED` and the automation read failed | Couldn't check | Why, in plain words |
| `status` `NOT_AVAILABLE` | Not available | "This org isn't licensed for <feature title>." |
| `ENABLED`, every step `Completed` | Done | "Turned on" |
| `ENABLED`, a step not `Completed` | In progress | "Turned on, but setup didn't finish: <step titles>" — plus the step's message for a step in `Error` |
| `IN_PROGRESS` | In progress | "Salesforce Go is turning it on now" |
| `DISABLE_IN_PROGRESS` | Not done | "Salesforce Go is turning it off now" |
| `NOT_ENABLED`, an `enableBlockedReasons[]` entry with `type` `NOT_AVAILABLE` | Not available | "<feature title> isn't available in this org" — plus the blocked reason's message |
| `NOT_ENABLED`, `blockedByApexLock` `true` or another `enableBlockedReasons[]` entry | Not done | The blocked reason, in plain words |
| `NOT_ENABLED`, nothing blocking | Not done | "Not turned on" |
| Any other `status` | Couldn't check | "Salesforce Go reported a state I don't recognize" |

**Name things the way Salesforce Go does.** Step statuses carry only internal step names. When a step
isn't finished, read the feature summary once for the titles Salesforce Go shows:

```json
mcp__headless-360__dispatch_readonly({ "url": "/services/data/v{version}/connect/setup/discovery/feature/<featureApiName>/summary", "method": "GET" })
```

`body.title` is the feature's name in Salesforce Go; `body.steps[]` pairs each step `apiName` with its
`title`. If the summary read fails, count instead ("1 of 3 setup steps didn't finish") — never show an
internal step name. For a step in `Error`, its `errorMessageLabel` is the message Salesforce Go shows;
fill `{0}`, `{1}`, … from `errorMessageParams`.

**Blocked reasons.** `enableBlockedReasons[].message` is HTML-escaped and can contain links — relay it
in plain words with the markup removed (`isn&#39;t` is "isn't"). `ANOTHER_FEATURE_RUNNING` means another
Salesforce Go feature is turning on; it clears when that one finishes. `blockedByApexLock` means Apex is
being deployed in the org; it clears shortly.

---

## The two gates

Behavior step 2 reads both with the Salesforce Go rule, in this order — the status reads are the
`IncidentMgmt` SOR's `read-itsm-setup-feature-status` and `read-itsm-incident-feature-status` steps:

1. `service-cloud-itsm-setup` — shown in Salesforce Go as **IT Service Enablement**
2. `service-cloud-itsm-incident` — shown as **Incident Management**. Read it only when IT Service
   Enablement lets you continue. Its setup steps (*Turn on field validations*, *Automatically close child
   incidents*, *Turn on Email to Incident*) set things rows P and 5 read; those rows show what the org
   reads either way.

| Gate result | What to do |
|-------------|------------|
| Done | Continue |
| In progress with `status` `ENABLED` (a setup step didn't finish) | Continue, and name the unfinished step in the menu header |
| Couldn't check with `status` `ENABLED` (only the automation read failed) | Continue, and say you couldn't check whether its setup finished |
| Not done — "Not turned on" (`NOT_ENABLED`, nothing blocking) | The Yes/No enable question in Behavior step 2 |
| Anything else — Not available, turning on or off, blocked, or a failed status read | Stop and explain in plain words — no question, no menu |

The gates show in the menu header, not as menu rows.

---

## Row P — Incident Preferences

Read each of the six through the `IncidentMgmt` SOR's preference read (`getOrgPref_1`), one call per
preference:

```json
mcp__headless-360__dispatch_readonly({ "url": "/headless/invoke/platform/incident-mgmt", "method": "GET", "queryParams": { "prefName": "IncidentValidationsEnabled" } })
```

`body` is `true` (on) or `false` (off).

| Preference | `prefName` |
|------------|------------|
| Default Field Validations for Incidents | `IncidentValidationsEnabled` |
| Automatically Close Child Incidents | `AutoClosureChildIncidents` |
| Automatically Triage Incidents | `IncidentTriageAgentEnabled` |
| Assign Incidents with Einstein | `IncAssignWithAgentEnabled` |
| Restrict Assigned Group to Regular Groups | `AssignedGroupValidationEnabled` |
| Enable Rich Text for Incident Descriptions | `RtaIncidentDescEnabled` |

| Result | Label | Note |
|--------|-------|------|
| All six read `true` | Done | "All six are on" |
| At least one reads `true` | Done | "<N> of 6 on; off: <labels of the ones off>" — add "couldn't check <labels>" for any read that failed |
| All six read `false` | Not done | "All six are off" |
| Otherwise (a read failed and none reads `true`) | Couldn't check | Why, in plain words — name the ones that read off |

Rows 6 and 8 reuse these reads; don't make them twice. Triage and Einstein assignment read through this
path even where the generic preference read refuses them.

## Row 1 — Incident Persona PSG

Count the active users who hold each persona:

```json
mcp__headless-360__dispatch_readonly({
  "url":    "/services/data/v{version}/query",
  "method": "GET",
  "queryParams": { "q": "SELECT PermissionSetGroup.DeveloperName psg, COUNT_DISTINCT(AssigneeId) holders FROM PermissionSetAssignment WHERE Assignee.IsActive = true AND PermissionSetGroup.DeveloperName IN ('IncidentFulfillerPSG','IncidentManagerPSG') GROUP BY PermissionSetGroup.DeveloperName" }
})
```

Each `body.records[]` entry is one persona — `psg` `IncidentFulfillerPSG` (Incident Fulfiller) or
`IncidentManagerPSG` (Incident Manager) — and `holders` is how many people have it. Only when there are no
records, check that the personas exist:

```json
mcp__headless-360__dispatch_readonly({
  "url":    "/services/data/v{version}/query",
  "method": "GET",
  "queryParams": { "q": "SELECT DeveloperName FROM PermissionSetGroup WHERE DeveloperName IN ('IncidentFulfillerPSG','IncidentManagerPSG')" }
})
```

| Result | Label | Note |
|--------|-------|------|
| A record with `holders` above `0` | Done | "Incident Fulfiller: <a> people · Incident Manager: <b> people" ("nobody yet" for a persona with no record) |
| No records, `totalSize` `0` on the second read | Not available | "The Incident personas aren't set up in this org" |
| No records, a persona exists | Not done | "Nobody has an Incident persona yet" |
| A read failed | Couldn't check | Why, in plain words |

This says whether anyone has a persona, not whether a particular person does — the persona feature checks
the person the user names.

## Row 2 — Priority Matrix

```json
mcp__headless-360__dispatch_readonly({ "url": "/services/data/v{version}/setup/org/preferences/IncPriorityMatrixEnabled", "method": "GET" })
```

```json
mcp__headless-360__dispatch_readonly({ "url": "/headless/invoke/service/service-itsm/ipcpriority-matrix-setup/fetch-priority-matrix-configurations", "method": "GET", "queryParams": { "entityType": "Incident" } })
```

`body.isPreferenceEnabled` is *Turn on Automatic Priority Assignment for IT Service*; each
`body.priorityMatrixConfigurationRows[]` entry is one priority rule.

| Result | Label | Note |
|--------|-------|------|
| Either read failed | Couldn't check | Why, in plain words |
| On, at least one rule | Done | "Turned on, <N> priority rules" |
| On, no rules | In progress | "Turned on, but no priority rules are set yet" |
| Off, at least one rule | In progress | "<N> priority rules are set, but automatic priority isn't turned on" |
| Off, no rules | Not done | "Not turned on" |

## Row 3 — SLA & Milestones

```json
mcp__headless-360__dispatch_readonly({ "url": "/headless/invoke/platform/slasettings/get-sla-management-permission", "method": "GET" })
```

```json
mcp__headless-360__dispatch_readonly({ "url": "/headless/invoke/platform/slasettings/get-sla-versioning-permission", "method": "GET" })
```

Each `body` is `true` or `false` — SLA Management and SLA Versioning. Only when both are `true`, read the
SLA policies:

```json
mcp__headless-360__dispatch_readonly({ "url": "/services/data/v{version}/connect/sla-management/sla-policies", "method": "GET" })
```

Use the `body.slaPolicies[]` entries whose `processType` is `Incident`; `status` `Enabled` means active.

| Result | Label | Note |
|--------|-------|------|
| A read failed | Couldn't check | Why, in plain words |
| Both `false` | Not done | "SLA Management isn't turned on" |
| One `true` | In progress | "<SLA Management or SLA Versioning> is on, but <the other> isn't" |
| An Incident policy is `Enabled` | Done | "SLA Management is on; active Incident policies: <names>" |
| Incident policies, none `Enabled` | In progress | "SLA Management is on, but no Incident SLA policy is active" |
| No Incident policy | In progress | "SLA Management is on, but Incidents have no SLA policy yet" |

## Row 4 — Incident Dashboards

Read the four dashboard preferences, each like row 2's preference read
(`/services/data/v{version}/setup/org/preferences/<name>` → `body.isPreferenceEnabled`):

| Persona | Dashboards | Home page dashboard |
|---------|------------|---------------------|
| Incident Manager | `ITSMIncMgrDashboard` | `ITSMHomeDashboard` |
| Incident Fulfiller | `ITSMIncFulDashboard` | `ITSMHomeFulDashboard` |

The feature turns on both for each persona it sets up. Only when all four read off, apply the Salesforce
Go rule's status read to `service-cloud-itsm-dashboard` (shown in Salesforce Go as **Dynamic Dashboards for
IT Service**).

| Result | Label | Note |
|--------|-------|------|
| A preference read failed | Couldn't check | Why, in plain words |
| A persona has one of its two on | In progress | "<persona>: the dashboards are on, but the Home page dashboard isn't" (or the reverse) |
| A persona has both on | Done | "<Incident Manager, Incident Fulfiller, or both> dashboards are on" |
| All off, the dashboard feature `NOT_AVAILABLE` or blocked with `NOT_AVAILABLE` | Not available | "This org isn't licensed for Dynamic Dashboards for IT Service" |
| All off | Not done | "No Incident dashboards are turned on yet" |

## Row 5 — Email-to-Incident

```json
mcp__headless-360__dispatch_readonly({ "url": "/headless/invoke/platform/email-to-incident", "method": "GET" })
```

`body.emailToIncidentCommonSetting.enableEmailToIncident` says whether it's on. Only when it's on, read the
routing addresses:

```json
mcp__headless-360__dispatch_readonly({ "url": "/headless/invoke/platform/email-to-incident/get-all-routing-addresses", "method": "GET" })
```

`body` lists one entry per routing address; on newer releases each entry has a `verified` flag.

| Result | Label | Note |
|--------|-------|------|
| A read failed | Couldn't check | Why, in plain words |
| On, at least one routing address | Done | "Turned on; <N> routing addresses" — add "<n> not verified yet" for entries whose `verified` is `false` |
| On, no routing address | In progress | "Turned on, but no routing address is set up yet" |
| Off | Not done | "Not turned on" |

## Row 6 — Major Incident Management

First the MIM probe — a `200` with a `true` / `false` body means MIM is active, and the value is
*auto-create problem*:

```json
mcp__headless-360__dispatch_readonly({ "url": "/headless/invoke/platform/mim/get-mimsetup-page-org-preference", "method": "GET", "queryParams": { "prefName": "AutoCreationOfProblem" } })
```

Only when it returns a boolean, read the Major Incident Manager license, then the approval group:

```json
mcp__headless-360__dispatch_readonly({
  "url":    "/services/data/v{version}/query",
  "method": "GET",
  "queryParams": { "q": "SELECT DeveloperName, TotalLicenses, UsedLicenses FROM PermissionSetLicense WHERE DeveloperName = 'MajorIncidentManagerPsl'" }
})
```

```json
mcp__headless-360__dispatch_readonly({ "url": "/headless/invoke/platform/mim/get-major-incident-approval-group", "method": "GET" })
```

The group read returns the group's Id when one is designated and `{}` when none is — never show the Id.
*Auto-close child incidents* is row P's `AutoClosureChildIncidents` read.

| Result | Label | Note |
|--------|-------|------|
| The probe returns `403` | Couldn't check | "Reading this needs an admin with IT Service setup access" |
| The probe returns another error, or a body that isn't `true` / `false` | Not available | "Major Incident Management isn't active in this org — Salesforce turns it on" |
| No `MajorIncidentManagerPsl` record | Not available | "This org doesn't have the Major Incident Management add-on" |
| An approval group is designated | Done | "An approval group is set; auto-create problem: <on/off> · auto-close child incidents: <on/off>" |
| `{}`, `UsedLicenses` above `0` | In progress | "<N> people have the Major Incident Manager license, but no approval group is set" |
| `{}`, `UsedLicenses` `0` | Not done | "No approval group or Major Incident Managers yet" |
| Otherwise (the license or group read failed) | Couldn't check | Why, in plain words |

## Row 7 — Broadcast Communications

Apply the Salesforce Go rule to `service-cloud-itsm-broadcast-communications` (shown in Salesforce Go as
**Broadcast Communications**). Only when it comes out **Done**, read who can send and where:

- **Senders** — row 1's counting pattern, once for direct assignments and once through a permission set
  group (SOQL can't combine the two in one query); each count is `body.records[0].holders`, and the larger
  is a floor:

```json
mcp__headless-360__dispatch_readonly({
  "url":    "/services/data/v{version}/query",
  "method": "GET",
  "queryParams": { "q": "SELECT COUNT_DISTINCT(AssigneeId) holders FROM PermissionSetAssignment WHERE Assignee.IsActive = true AND PermissionSet.Name = 'BroadcastCommSender'" }
})
```

```json
mcp__headless-360__dispatch_readonly({
  "url":    "/services/data/v{version}/query",
  "method": "GET",
  "queryParams": { "q": "SELECT COUNT_DISTINCT(AssigneeId) holders FROM PermissionSetAssignment WHERE Assignee.IsActive = true AND PermissionSetGroupId IN (SELECT PermissionSetGroupId FROM PermissionSetGroupComponent WHERE PermissionSet.Name = 'BroadcastCommSender')" }
})
```

- **Channels and objects** — six preference reads like row 2's: channels `EmailNotifications` (Email),
  `InAppNotifications` (In-app), `SlackNotifications` (Slack), `TeamsNotifications` (Microsoft Teams);
  objects `BroadcastCommOnIncident` (Incidents), `BroadcastCommOnChgReq` (Change Requests).

| Result | Label | Note |
|--------|-------|------|
| The Go rule isn't Done | The Go rule's label | The Go rule's note |
| A sender, a channel on, and Incidents on | Done | "Turned on; <channels on>; at least <larger count> senders" |
| A read that worked shows something missing | In progress | "Turned on, but <no senders yet, no channel is on, or it isn't on for Incidents>" — add what you couldn't check |
| Otherwise (a read failed) | Couldn't check | "Turned on; I couldn't check <what>" |

The Slack channel can read on with no Slack workspace connected — say so if Slack is the only channel on.

## Row 8 — Manage Incidents with AI

Triage and Einstein assignment are row P's `IncidentTriageAgentEnabled` and `IncAssignWithAgentEnabled`
reads — reuse them. Read the chat and voice switch:

```json
mcp__headless-360__dispatch_readonly({ "url": "/services/data/v{version}/setup/org/preferences/ChatToIncidentAiEnabled", "method": "GET" })
```

The three switches are *Automatically Triage Incidents*, *Let Einstein Assign Incidents*, and *Report
Incidents from Chat or Voice Using AI*.

| Result | Label | Note |
|--------|-------|------|
| A read failed | Couldn't check | Name the switch you couldn't check, and the others' states |
| All three on | Done | "All three are on" |
| Some on | In progress | "On: <labels> · off: <labels>" |
| None on | Not done | "All three are off" |

## Row 9 — Service Management Privilege

```json
mcp__headless-360__dispatch_readonly({ "url": "/services/data/v{version}/setup/org/preferences/PrivilegeAssignmentEnabled", "method": "GET" })
```

`body.isPreferenceEnabled` is *Enable Privilege Assignment*. Only when it's on — Setup hides the rest while
it's off — read the escalation level and the privileges:

```json
mcp__headless-360__dispatch_readonly({ "url": "/headless/invoke/platform/service-mgmt-privilege-setup", "method": "GET" })
```

```json
mcp__headless-360__dispatch_readonly({ "url": "/headless/invoke/platform/service-mgmt-privilege-setup/get-service-privileges", "method": "GET" })
```

The level read's `body` is the saved escalation level — `2147483647` means none is saved yet. The privileges
read lists one entry per privilege.

| Result | Label | Note |
|--------|-------|------|
| The toggle read returns `404` | Not available | "Service Management Privilege isn't available in this org" |
| The toggle read fails otherwise | Couldn't check | Why, in plain words |
| The toggle is off | Not done | "Enable Privilege Assignment is off" |
| At least one privilege, or a saved level | Done | "Turned on; <N> privileges; escalation level <level, or not set>" |
| Both reads worked: no privilege, no saved level | In progress | "Turned on, but no privileges or escalation level yet" |
| Otherwise (a read failed) | Couldn't check | "Turned on; I couldn't check <what>" |

Employee assignments have no read, so this never says who holds a privilege.

## Row 10 — Audit Tracking

```json
mcp__headless-360__dispatch_readonly({ "url": "/headless/invoke/platform/field-history-tracking/get-single-entity-tracking-data", "method": "GET", "queryParams": { "entityEnumOrId": "Incident" } })
```

The tracked Incident fields are the `body.fields[]` entries with `isCurrentlyTracked` `true`;
`body.isTrackingPrefEnabled` is Incident's object-level tracking.

| Result | Label | Note |
|--------|-------|------|
| The read failed | Couldn't check | Why, in plain words |
| A field tracked, object-level tracking on | Done | "Tracking <N> Incident fields" |
| A field tracked, object-level tracking off | In progress | "<N> Incident fields are chosen, but history tracking for Incidents is off" |
| No field tracked | Not done | "No Incident fields are tracked yet" |

---

## Track roll-up

One status for the whole Incident Management track — the status the ITSM setup coordinator shows in its
track table. Take the first line that fits; when a gate decides it, skip the row reads:

1. A gate is **Not available** → **Not available**
2. A gate is **Couldn't check** → **Couldn't check**
3. A gate is **Not done** → **Not done** ("Incident Management isn't turned on", or IT Service Enablement)
4. A gate is **In progress** → **In progress** (the Go rule's note)
5. Going through rows P, then 1–10, and skipping **Not available** rows, the first that's **In progress**
   or **Not done** → **In progress** ("Incident Management is on; <feature> isn't set up yet")
6. Any row is **Couldn't check** → **Couldn't check**
7. Otherwise → **Done**

Give the note from the gate or row that decided it.

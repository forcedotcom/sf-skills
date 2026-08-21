---
name: service-itsm-swarming-configure
description: "Enable Swarming for Employee Service (ITSM) in Salesforce — the Salesforce Go feature service-cloud-swarming that lets IT Desk agents pull in subject-matter experts to collaboratively resolve incidents in real time. Use this for: 'turn on swarming', 'enable service-cloud-swarming', 'set up swarming for IT Desk', 'set Teams as collaboration tool for swarming', 'enable collaborative incident resolution', or any request to enable/verify this Salesforce Go feature. DO NOT TRIGGER for the base Microsoft Teams ITSM integration toggle (service-itsm-teams-configure) or for configuring notification-channel preferences."
metadata:
  version: "1.0"
  domains: ["Service"]
  minApiVersion: "67.0"
  relatedSkills:
    - "experience-portal-create"
    - "service-itsm-channels-coordinate"
    - "service-itsm-teams-configure"
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

# Enable Swarming for Employee Service (ITSM)

Enable the Salesforce Go feature **"Swarming"** (`service-cloud-swarming`) — the feature that
helps service reps pull in the right collaborators and subject-matter experts to resolve
incidents in real time. Every operation dispatches through **headless-360**.

> **Execute one step at a time.** These steps make real, state-changing API calls. Run a single
> operation, show its result, confirm it succeeded, then proceed — do not batch multiple setup
> calls into one parallel block.

## Scope

- **In scope**: Enabling the `service-cloud-swarming` Go feature via its feature-enablement
  Connect API; verifying feature state afterward; setting the "Select a Collaboration Tool"
  picklist (the API-level target of the "Set Teams as Collaboration Tool for Swarming" checklist
  item) to `Teams` via the org-values Connect API.
- **Out of scope**: The base Microsoft Teams ITSM Salesforce Go page toggle (`ITSMTeamsEnabled`) and Azure/Entra
  app registration — use `service-itsm-teams-configure` (Swarming requires Teams to already be set
  up as a prerequisite, per the Go page). Notification-channel preferences
  (`Notifications` / `TeamsNotifications`) — a separate concern from this feature. Portal/site
  creation — use `experience-portal-create`.

---

## The problem this skill solves

"Set Teams as Collaboration Tool for Swarming" is one item in the "Set Up Salesforce IT Desk"
checklist on the Teams ITSM Go page (`service-cloud-itsm-teams-integration`'s feature page) — but
it is gated behind a *separate* Go feature, `service-cloud-swarming`, which must be turned on
first. This skill is the dedicated place to turn Swarming on, so `service-itsm-teams-configure`
can delegate to it instead of duplicating feature-enablement logic.

---

## Workflow

### Step 1 — Check current feature status

```text
mcp__headless-360__dispatch(
  method: "POST",
  url:    "/services/data/v67.0/connect/setup/discovery/features/status",
  body:   { "featureApiNames": ["service-cloud-swarming"] }
)
```

Response shape:
```json
{
  "items": [
    {
      "apiName": "service-cloud-swarming",
      "status": "ENABLED",          // or "NOT_ENABLED" / "DISABLED"
      "blockedByApexLock": false,
      "dependencyStatuses": [],
      "enableBlockedReasons": [],
      "disableBlockedReasons": []
    }
  ]
}
```

**Note:** this endpoint is POST-only despite being a status read — a `GET` with `queryParams`
returns `405 METHOD_NOT_ALLOWED "Allowed are POST"`.

If `status` is already `"ENABLED"`, skip to Step 3 (verification) — do not re-enable.
If `enableBlockedReasons` is non-empty, surface those reasons to the user before attempting Step 2.

### Step 2 — Enable the feature

```text
mcp__headless-360__dispatch(
  method: "POST",
  url:    "/services/data/v67.0/connect/setup/discovery/feature/service-cloud-swarming/enable",
  body:   {}
)
```

Verified live: returns `201 {"success":true}` cleanly (unlike the Teams feature-enable, this call
did not exhibit the "500 that still succeeds" gotcha in testing — but re-check status afterward
regardless, since Go feature-enable calls can be flaky in general).

### Step 3 — Verify

```text
mcp__headless-360__dispatch(
  method: "POST",
  url:    "/services/data/v67.0/connect/setup/discovery/features/status",
  body:   { "featureApiNames": ["service-cloud-swarming"] }
)
```

Expect `status: "ENABLED"`.

### Step 4 — Check current collaboration tool value

```text
mcp__headless-360__dispatch_readonly(
  method: "GET",
  url:    "/services/data/v67.0/setup/org/values/SWARM_COLLABORATION_TOOL"
)
```

Response shape — exactly one of the four value fields is populated:
```json
{ "booleanValue": false, "dateValue": null, "numberValue": null, "stringValue": "None" }
```

`stringValue` holds the current picklist selection: `"None"`, `"Slack"`, or `"Teams"`. This is
the same Java enum-gated org-value endpoint family described in `setup-connect-api`'s
`get-org-value`/`update-org-value`/`verify-org-value-update` steps — `valueName` must be the
literal Java enum constant name (`SWARM_COLLABORATION_TOOL`, SCREAMING_SNAKE_CASE), not a
camelCase guess like `SwarmCollaborationTool`.

If already `"Teams"`, skip to Step 6 (report) — do not re-issue the write.

### Step 5 — Set the collaboration tool to Teams

```text
mcp__headless-360__dispatch(
  method: "PATCH",
  url:    "/services/data/v67.0/setup/org/values/SWARM_COLLABORATION_TOOL",
  body:   { "orgValue": "Teams" }
)
```

Verified live: returns `200 { "stringValue": "Teams", ... }`. This is the API-level write behind
the Swarming Go feature page's "Select a Collaboration Tool" dropdown — the same control the
Teams ITSM Go page's "Set Teams as Collaboration Tool for Swarming" checklist item deep-links to
via its "Go to Feature Page" button. Valid `orgValue` strings are `"None"`, `"Slack"`, `"Teams"`.

Re-run Step 4's GET afterward to confirm `stringValue == "Teams"`.

### Step 6 — Report to the user

Report both the `service-cloud-swarming` feature status and the `SWARM_COLLABORATION_TOOL`
value, confirming "Set Teams as Collaboration Tool for Swarming" is now fully automated —
enabling the feature is the prerequisite, and the org-value PATCH is the actual checklist-item
write.

---

## Disabling (if requested)

```text
mcp__headless-360__dispatch(
  method: "POST",
  url:    "/services/data/v67.0/connect/setup/discovery/feature/service-cloud-swarming/disable",
  body:   {}
)
```

Re-run Step 1 afterward to confirm.

To also reset the collaboration tool selection (optional — disabling the feature does not reset
it automatically):
```text
mcp__headless-360__dispatch(
  method: "PATCH",
  url:    "/services/data/v67.0/setup/org/values/SWARM_COLLABORATION_TOOL",
  body:   { "orgValue": "None" }
)
```

---

## Gotchas

| Issue | Detail |
|-------|--------|
| "Set Teams as Collaboration Tool for Swarming" writes via `SWARM_COLLABORATION_TOOL`, not a Teams-side endpoint | This checklist item lives on the **Swarming** Go feature page itself (`/lightning/setup/page/feature/service-cloud-swarming/home`, "Select a Collaboration Tool" dropdown) — the Teams ITSM Go page's checklist item is just a deep link to it via "Go to Feature Page." The write API is `PATCH /services/data/v67.0/setup/org/values/SWARM_COLLABORATION_TOOL` with body `{"orgValue": "Teams"}` — part of `setup-connect-api`'s `get-org-value`/`update-org-value` steps. Verified live: `GET` returned `{"stringValue":"None"}` before, `{"stringValue":"Teams"}` after `PATCH`. |
| `valueName` must be the exact Java enum constant, not camelCase | The `/setup/org/values/{valueName}` endpoint calls `OrgValues.valueOf(valueName)` directly (`Enum.valueOf`), so it requires the literal SCREAMING_SNAKE_CASE constant name declared in `ui.services.utils.OrgValueUtil.OrgValues` — e.g. `SWARM_COLLABORATION_TOOL`. CamelCase guesses like `SwarmCollaborationTool` or `SwarmingCollaborationTool` return `400 ILLEGAL_QUERY_PARAMETER_VALUE "No enum constant ui.services.utils.OrgValueUtil.OrgValues.<guess>"` — that specific error confirms the endpoint/mechanism is right but the casing/name is wrong. The read-only `get-service-itsm-teams-collaboration-app-settings` endpoint (`GET /connect/it-service/collaboration-app-settings/{targetApplication}`) is unrelated to this setting — it's read-only (`POST`/`PATCH`/`PUT` return `405`) and returns empty `settings: []` regardless of feature state. |
| `features/status` is POST-only | A `GET` with `queryParams` on `/connect/setup/discovery/features/status` returns `405 METHOD_NOT_ALLOWED "Allowed are POST"` — always POST a JSON body with `featureApiNames`. |
| `swarming-connect-api` SOR is unrelated | headless-360's `swarming-connect-api` SOR is about **Slack messaging within swarming conversations** (post/patch/delete Slack messages, reactions, file uploads, channel/user search) — it does not configure which collaboration tool (Teams vs. Slack vs. Chatter) swarming uses. Do not confuse it with this skill's scope. |
| Swarming requires Teams first | The Go page frames "Set Teams as Collaboration Tool for Swarming" as a step *within* Teams ITSM setup — enable `service-cloud-itsm-teams-integration` (via `service-itsm-teams-configure`) before or alongside this skill. |
| Version prefix required | headless-360 `dispatch`/`dispatch_readonly` do not resolve API versions — always pass the full `/services/data/vXX.0/...` prefix. |

---

## Related Skills

| Skill | When to use instead / alongside |
|-------|---------------------------------|
| `service-itsm-teams-configure` | Enabling the base Microsoft Teams ITSM integration and Azure/Entra setup — a prerequisite for Swarming; delegates to this skill for the "Set Teams as Collaboration Tool for Swarming" checklist item |
| Notification-channel preferences | Enabling the `Notifications`/`TeamsNotifications` preferences is a distinct concern from this feature (no dedicated child skill exists yet) |
| `service-itsm-channels-coordinate` | Top-level menu across Teams, Slack, Swarming, Notifications, Portal |

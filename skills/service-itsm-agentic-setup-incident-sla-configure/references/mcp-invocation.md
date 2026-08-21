# MCP Invocation Reference — Incident SLA

Every operation dispatches through the **Salesforce-hosted `headless-360`** MCP server, which
exposes four meta-tools:

- `mcp__headless-360__discover(query)` — semantic search over the indexed operation catalog
- `mcp__headless-360__describe(id)` — pulls the schema and canonical route for one operation
- `mcp__headless-360__dispatch_readonly({url, method, query_params?, body?})` — GET / read-only HTTP
- `mcp__headless-360__dispatch({url, method, body?, query_params?})` — POST / PATCH / DELETE HTTP

**Dispatch takes raw HTTP**, not `{operation_id, arguments}`. Give it the full `url`
(`/services/data/v67.0/...`), `method`, optional `body`, and optional `query_params` — the server
signs the request with the JWT bound to the current MCP session and forwards it to the org. The
skill never handles credentials or an org alias — everything is derived from the session.

## Response envelope

The SLA Management Connect API, `/sobjects/…` REST endpoints, and `/query` are **standard REST** —
singly wrapped:

```json
{ "status_code": 200, "body": <REST/Connect response> }
```

Read `body`. (Only `/headless/invoke/…` Aura-controller routes are doubly wrapped as `body.body`;
this skill uses none.)

---

## Routes

| Method + path | Purpose |
|---------------|---------|
| `GET  /services/data/v67.0/connect/setup/discovery/feature/service-cloud-itsm-manage-sla-policies/status` | Phase 0.5 — read the SLA Management for IT Service feature status |
| `POST /services/data/v67.0/connect/setup/discovery/feature/service-cloud-itsm-manage-sla-policies/enable` | Phase 0.5 — enable the feature (flips Simplified SLA Setup) |
| `GET  /services/data/v67.0/tooling/query` | Phase 0.5 — read SLA Versioning (`EntitlementSettings.IsEntitlementVersioningEnabled`) via `query_params.q` |
| `PATCH /services/data/v67.0/tooling/sobjects/EntitlementSettings/000000000000000AAA` | Phase 0.5 — turn on SLA Versioning if off |
| `GET  /services/data/v67.0/sobjects/Incident/describe` | Preflight — Incident Management on + SLA fields present |
| `GET  /services/data/v67.0/query` | SOQL reads (BusinessHours, SlaProcess, EntityMilestone) via `query_params.q` |
| `POST /services/data/v67.0/connect/sla-management/milestone-types` | Create MilestoneType |
| `POST /services/data/v67.0/connect/sla-management/sla-policies` | Create SLA Policy (SlaProcess) |
| `POST /services/data/v67.0/connect/sla-management/sla-policies/<slaId>/milestones` | Attach Milestone |
| `POST /services/data/v67.0/sobjects/Entitlement` | Create Entitlement (standard sObject) |
| `POST /services/data/v67.0/sobjects/Incident` | Create a test Incident |

Minimum API version is **67.0** — `headless-360` currently only routes `v67.0+`.

---

## Phase 0.5 — SLA Management for IT Service prerequisite gate

"SLA Management for IT Service" is a Salesforce Go Setup Discovery feature — verified apiName
`service-cloud-itsm-manage-sla-policies`. **Do not guess other apiNames for this** — every other
guess returns `400 NOT_FOUND`; this exact string is the correct one. If it ever needs re-confirming
for a different org/release, the list-all route `GET /services/data/v67.0/connect/setup/discovery/features`
returns every feature's apiName + status in one call.

Enabling this feature flips `EntitlementSettings.IsEntitlementsEnabled` and **Simplified SLA
Setup** together — Simplified SLA Setup has **no Tooling/Metadata API exposure**, so a Tooling
PATCH to `EntitlementSettings` alone can never complete it.

**SLA Versioning is separate and NOT touched by the feature enable call.** It maps to
`EntitlementSettings.IsEntitlementVersioningEnabled` (Tooling object, singleton, fixed Id
`000000000000000AAA`, keyPrefix `0HE`, one row per org) and must be checked/enabled independently.

### Read — feature status

```json
mcp__headless-360__dispatch_readonly({
  "url":    "/services/data/v67.0/connect/setup/discovery/feature/service-cloud-itsm-manage-sla-policies/status",
  "method": "GET"
})
```

```json
{
  "apiName": "service-cloud-itsm-manage-sla-policies",
  "status": "NOT_ENABLED",
  "enableBlockedReasons": [],
  "disableBlockedReasons": [],
  "blockedByApexLock": false,
  "dependencyStatuses": []
}
```

- `status == "ENABLED"` → the feature (and Simplified SLA Setup) is on — move to the SLA Versioning
  read below.
- `status == "NOT_ENABLED"` with non-empty `enableBlockedReasons` → **stop**, relay the reasons, do
  not attempt to enable.
- `status == "NOT_ENABLED"` with empty `enableBlockedReasons` → confirm with the user, then enable.

### Read — SLA Versioning

```json
mcp__headless-360__dispatch_readonly({
  "url": "/services/data/v67.0/tooling/query",
  "method": "GET",
  "query_params": { "q": "SELECT IsEntitlementVersioningEnabled FROM EntitlementSettings" }
})
```

```json
{
  "size": 1, "totalSize": 1, "done": true,
  "records": [{ "IsEntitlementVersioningEnabled": true }]
}
```

**SLA Versioning is a one-way switch.** Once `IsEntitlementVersioningEnabled` is `true`, Salesforce
does not support flipping it back — even if SLA Management is later turned off. Always surface this
to the user before enabling it — never enable silently.

### Enable — feature (only after explicit user confirmation)

```json
mcp__headless-360__dispatch({
  "url":    "/services/data/v67.0/connect/setup/discovery/feature/service-cloud-itsm-manage-sla-policies/enable",
  "method": "POST",
  "body":   {}
})
→ 201 { "success": true }
```

Do not trust `success: true` alone — re-run the status GET above and require `"status": "ENABLED"`
before moving on.

### Enable — SLA Versioning (only after explicit user confirmation, separately)

```json
mcp__headless-360__dispatch({
  "url":    "/services/data/v67.0/tooling/sobjects/EntitlementSettings/000000000000000AAA",
  "method": "PATCH",
  "body": {
    "FullName": "EntitlementSettings",
    "Metadata": { "enableEntitlementVersioning": true }
  }
})
→ 204 No Content (empty body)
```

`FullName` is mandatory — the PATCH is rejected without it. The PATCH response body is empty on
success — **re-run the Tooling query above and require `IsEntitlementVersioningEnabled: true`**
before moving on, same rule as the SLA Policy create response later in this flow (never trust a
write response alone).

---

## Discovery — always run first

```text
mcp__headless-360__discover(query="sla-management milestone")
```

`discover` returns matching operation ids. Pipe each id into `describe` to pull its input schema
and canonical HTTP route:

```text
mcp__headless-360__describe(id="<operation_id_from_discover>")
```

| Operation | Method | Purpose |
|-----------|--------|---------|
| `…connect.sla-management.milestone-types` (create) | POST | Create MilestoneType |
| `…connect.sla-management.sla-policies` (create) | POST | Create SLA Policy |
| `…connect.sla-management.sla-policies.{id}.milestones` (create) | POST | Attach Milestone |

**Corpus ≠ registry**: `discover` may only surface adjacent SLA endpoints (e.g. workflow-fields /
workflow-sla-actions) because the SLA Management POST routes are documented but not always ranked
first. The routes are known-good — `describe` on the `milestone-types` / `sla-policies` operations
still returns the schema, and `dispatch` still works even if `discover` didn't rank them at the top.
If `discover` returns nothing at all after rewording the query, the org's `headless-360` corpus
does not index this surface — direct the user to Setup and stop.

---

## Preflight A — Master Incident Management pref (direct read)

The master ITSM Incident Management pref is exposed on the **Setup Discovery Connect API**
under `apiName = service-cloud-itsm-incident`. The setup-org-preferences endpoint does not
expose the master (`IncidentMgmtEnabled` / `ITSMIncidentMgmtEnabled` both 404) — read via
Setup Discovery instead.

```json
mcp__headless-360__dispatch_readonly({
  "url":    "/services/data/v67.0/connect/setup/discovery/features",
  "method": "GET"
})
```

The endpoint returns the full feature catalog (~763 entries, ~1.1 MB) and does not honor
`?apiName=` server-side. Filter `body.features[]` client-side to the element where
`apiName == "service-cloud-itsm-incident"` and read its `status` (`ENABLED` / `NOT_ENABLED`).

**Auto-delegate rule**: if `status != "ENABLED"`, delegate to
`service-itsm-incident-mgmt-configure` inline before continuing — that skill runs its own
confirm-to-write against the enable route (`POST .../setup/discovery/feature/service-cloud-itsm-incident/enable`)
and returns after the flip. Re-read this step to verify `status == "ENABLED"` before
continuing. If the user declines the delegation, halt — every downstream SLA artifact
depends on the master being on.

## Preflight B — SLA fields on the Incident sObject

```json
mcp__headless-360__dispatch_readonly({
  "url":    "/services/data/v67.0/sobjects/Incident/describe",
  "method": "GET"
})
```

Confirm `body.fields[]` includes `EntitlementId`, `SlaStartDate`, and `SlaExitDate`. If the
describe 404s or the fields are missing, Entitlement Management is not enabled for Incident —
stop and direct the user to **Setup → Incident Management / Entitlement Settings**. This is
a **secondary sanity check on the SLA-field surface**, not the master-pref state signal;
Preflight A above is the master-state signal.

The response is large (~86 KB). If your host truncates it, filter with a grep-style search rather
than reading the whole body — you only need to confirm those three field names exist.

---

## Default BusinessHours

```json
mcp__headless-360__dispatch_readonly({
  "url":    "/services/data/v67.0/query",
  "method": "GET",
  "query_params": { "q": "SELECT Id, Name FROM BusinessHours WHERE IsActive = true AND IsDefault = true" }
})
```

`body.records[0].Id` is the `BusinessHoursId` used on the SLA Policy, Milestone, and Entitlement.
If `body.records` is empty, stop — the user must create default Business Hours in Setup.

---

## Create MilestoneType

```json
mcp__headless-360__dispatch({
  "url":    "/services/data/v67.0/connect/sla-management/milestone-types",
  "method": "POST",
  "body": {
    "name":          "Incident First Response",
    "description":   "Incident First Response",
    "recurrenceType": "OneTime"
  }
})
```

`recurrenceType` = `OneTime` | `Recurring`. Success: `body.id` is the new MilestoneType Id. If
absent, the create failed — surface `body`.

---

## Create SLA Policy (SlaProcess)

```json
mcp__headless-360__dispatch({
  "url":    "/services/data/v67.0/connect/sla-management/sla-policies",
  "method": "POST",
  "body": {
    "name":                    "Incident SLA Policy",
    "description":             "Incident SLA Policy",
    "processType":             "Incident",
    "businessHourId":          "<BusinessHoursId>",
    "createdDateEntryCriteria": true,
    "closedExitCriteria":       true,
    "active":                   true,
    "versionDefault":           true
  }
})
```

**The response body echoes most fields as `null`.** Do not trust it — capture `body.id` and
verify state via SOQL:

```json
mcp__headless-360__dispatch_readonly({
  "url":    "/services/data/v67.0/query",
  "method": "GET",
  "query_params": { "q": "SELECT Id, Name, SObjectType, IsActive, BusinessHoursId FROM SlaProcess WHERE Id = '<slaId>'" }
})
```

---

## Attach Milestone

`slaProcessId` is carried by the URL path — **omit it from the body** (the server returns
`JSON_PARSER_ERROR: Unrecognized field "slaProcessId"`).

```json
mcp__headless-360__dispatch({
  "url":    "/services/data/v67.0/connect/sla-management/sla-policies/<slaId>/milestones",
  "method": "POST",
  "body": {
    "milestoneTypeId":  "<MilestoneTypeId>",
    "businessHoursId":  "<BusinessHoursId>",
    "timeTrigger":      60,
    "order":            1,
    "startTimeBasedOn": "SlaProcessCreatedDate",
    "milestoneCriteria": [
      {
        "milestoneState":         "Active",
        "milestoneAgreementType": "Warning",
        "filterType":             "RuleFilter",
        "filterItems": [
          { "table": "Incident", "column": "Status", "operator": "NotEqual", "order": 1, "value": "Closed" }
        ]
      }
    ]
  }
})
```

`milestoneCriteria` is mandatory. Success: `body.id` is the new Milestone Id.

---

## Create Entitlement (standard sObject)

Entitlement is NOT part of the `/connect/sla-management/` surface — create it via the sObject
endpoint.

```json
mcp__headless-360__dispatch({
  "url":    "/services/data/v67.0/sobjects/Entitlement",
  "method": "POST",
  "body": {
    "Name":            "Incident SLA Entitlement",
    "AccountId":       "<AccountId>",
    "SlaProcessId":    "<slaId>",
    "BusinessHoursId": "<BusinessHoursId>",
    "StartDate":       "<YYYY-MM-DD>",
    "EndDate":         "<YYYY-MM-DD + 1 year>"
  }
})
```

`Entitlement.Status` is date-computed: `StartDate` in the future → `Inactive`; `StartDate` ≤ today
AND `EndDate` ≥ today → `Active`. For immediate SLA engagement, backdate `StartDate` to yesterday.
Success: `body.id`.

---

## Verify SLA engagement

Create a test Incident:

```json
mcp__headless-360__dispatch({
  "url":    "/services/data/v67.0/sobjects/Incident",
  "method": "POST",
  "body":   { "Subject": "SLA test incident", "EntitlementId": "<EntitlementId>" }
})
```

Then confirm the Incident stamped an SLA start and an EntityMilestone:

```json
mcp__headless-360__dispatch_readonly({
  "url":    "/services/data/v67.0/query",
  "method": "GET",
  "query_params": { "q": "SELECT Id, IncidentNumber, Subject, Status, SlaStartDate FROM Incident WHERE Id = '<incidentId>'" }
})
```

```json
mcp__headless-360__dispatch_readonly({
  "url":    "/services/data/v67.0/query",
  "method": "GET",
  "query_params": { "q": "SELECT Id, MilestoneType.Name, TargetDate, IsCompleted, IsViolated FROM EntityMilestone WHERE ParentEntityId = '<incidentId>'" }
})
```

`SlaStartDate` populated + at least one `EntityMilestone` row with a `TargetDate` = SLA engaged.
`TargetDate` should equal `SlaStartDate + timeTrigger minutes` (business-hours-adjusted).

---

## Gotchas

| Issue | Detail |
|-------|--------|
| `dispatch` shape is raw HTTP | Pass `{url, method, body?, query_params?}` — NOT `{operation_id, arguments}`. |
| Response wrapper | Connect/`/sobjects`/`/query` are singly wrapped — read `body`. Aura `/headless/invoke/…` routes (not used here) are doubly wrapped. |
| Corpus vs. registry drift | `discover` may not rank the SLA POST routes at the top — the routes are still known-good; `describe` + `dispatch` on the canonical path works either way. |
| SLA Policy create response is null | `POST /sla-policies` echoes most fields as `null` — always verify via SOQL on `SlaProcess`. |
| Milestone criteria mandatory | Omitting `milestoneCriteria` returns `400: Criteria details cannot be empty`. |
| Formula filter → 500 | `filterType: "Formula"` triggers an internal server error. Use `filterType: "RuleFilter"` with concrete `filterItems[]`. |
| Filter operator enum | Use `Equals` (not `Equal`), `NotEqual` (not `NotEquals`/`NotEqualTo`/`!=`). Wrong shape → `POST_BODY_PARSE_ERROR: Invalid value for Filter Operation Enum`. |
| `slaProcessId` rejected in body | The server returns `JSON_PARSER_ERROR: Unrecognized field "slaProcessId"` — the id is in the path only. |
| Entitlement status date-computed | Future `StartDate` → `Inactive`. Backdate `StartDate` to yesterday for immediate SLA engagement in testing. |
| Entitlement is standard sObject | Create via `POST /sobjects/Entitlement`, not the Connect surface. |

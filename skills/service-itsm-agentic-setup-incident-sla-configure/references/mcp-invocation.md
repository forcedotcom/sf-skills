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

## Contents

- [Response envelope](#response-envelope)
- [Routes](#routes)
- [Phase 0.5 — SLA Management for IT Service prerequisite gate](#phase-05--sla-management-for-it-service-prerequisite-gate)
- [Discovery — always run first](#discovery--always-run-first)
- [Preflight A — Master Incident Management pref (direct read)](#preflight-a--master-incident-management-pref-direct-read)
- [Preflight B — SLA fields on the Incident sObject](#preflight-b--sla-fields-on-the-incident-sobject)
- [Default BusinessHours](#default-businesshours)
- [Create MilestoneType](#create-milestonetype)
- [Create SLA Policy (SlaProcess)](#create-sla-policy-slaprocess)
- [Attach Milestone](#attach-milestone)
- [Milestone Actions (Phase 2.5 — Warn / Escalate)](#milestone-actions-phase-25--warn--escalate)
- [Create Entitlement (standard sObject)](#create-entitlement-standard-sobject)
- [Predefined Incident Policy (Phase 0.6 detect + Phase 2-OOB seed)](#predefined-incident-policy-phase-06-detect--phase-2-oob-seed)
- [Verify SLA engagement](#verify-sla-engagement)
- [Gotchas](#gotchas)

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
| `GET  /services/data/v67.0/connect/sla-management/sla-policies` | Phase 0.6 — detect the OOB "Standard Support for Incidents" policy via `query_params.processTypes=Incident` |
| `POST /services/data/v67.0/connect/sla-management/milestone-types` | Create MilestoneType |
| `POST /services/data/v67.0/connect/sla-management/sla-policies` | Create SLA Policy (SlaProcess) |
| `POST /services/data/v67.0/connect/sla-management/sla-policies/<slaId>/milestones` | Attach Milestone |
| `POST /services/data/v67.0/sobjects/Entitlement` | Create Entitlement (standard sObject) |
| `POST /services/data/v67.0/connect/sla-management/entitlement-criteria` | Phase 2-OOB — `describe` first, then attempt the OOB always-match criterion (`Subject NotEqual <sentinel>`); if the create still `400`s after using the described schema, fall back to a date-windowed Entitlement (the route works — a wrong-payload `400`, not a platform gap) |
| `POST /services/data/v67.0/sobjects/Incident` | Create a test Incident |
| `POST /services/data/v67.0/sobjects/BusinessHours` | Phase 2.5 — create an IST (or other-timezone) BusinessHours for the policy/Entitlement (createable; **not** API-deletable) |
| `POST /services/data/v67.0/connect/sla-management/sla-policies/<slaId>/milestones/<milestoneId>/actions` | Phase 2.5 — attach a Warn/Escalate milestone action (delegate via the `create-milestone-action` op) |

Minimum API version is **67.0** — `headless-360` currently only routes `v67.0+`.

---

## Phase 0.5 — SLA Management for IT Service prerequisite gate

"SLA Management for IT Service" is a Salesforce Go Setup Discovery feature — verified apiName
`service-cloud-itsm-manage-sla-policies`. **Do not guess other apiNames for this** — every other
guess returns `400 NOT_FOUND`; this exact string is the correct one. If it ever needs re-confirming
for a different org/release, the list-all route `GET /services/data/v67.0/connect/setup/discovery/features`
returns every feature's apiName + status in one call.

**"SLA Management for IT Service" is a Setup Discovery composite of two sub-steps — Simplified SLA
Setup AND SLA Versioning — and reads as enabled/Complete only when BOTH are on.** In Setup it shows
**In Progress** while either is off.

**One enable call turns on both — they are inseparable.** The feature's enablement automation (the
platform recipe `turnOnSLAManagementForITService`) runs two hardcoded, non-optional steps: (1) turns
on Entitlements (`IsEntitlementsEnabled`) + Simplified SLA Setup + Pause Milestone; (2) turns on **SLA
Versioning** (`EntitlementSettings.IsEntitlementVersioningEnabled`, a one-way DB migration). So the
single feature `enable` call below **auto-enables SLA Versioning as a side effect** — no separate
versioning write is required, and there is **no supported way to enable Simplified SLA Setup while
leaving versioning off** (both steps are inseparable at the platform level). `IsEntitlementVersioningEnabled`
is a Tooling singleton (fixed Id `000000000000000AAA`, keyPrefix `0HE`, one row per org).

**SLA Versioning is permanent / one-way.** Salesforce rejects any attempt to turn it back off
("Versioning cannot be disabled once it is enabled"), even if SLA Management is later disabled.

Because the enable is inseparable and versioning is irreversible, **never enable without explicit,
informed consent for the permanent switch** — an explicit permanence-gated `AskUserQuestion`, kept
separate from the master-enable ack (see *Ack structure* below). If the user declines, enable **nothing** (enabling the feature would flip versioning
anyway), SLA Management stays incomplete, and the run **halts**.

This is the root of W-23979084: the skill enabled the feature on a request that also said "don't
enable versioning," versioning turned on anyway (a side effect of the enable), and the skill then
**falsely reported it as off**. The fix: get permanence consent up front, and after the write re-read
and report the **real** state.

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

- `status == "ENABLED"` → **Simplified SLA Setup** is on — now read SLA Versioning below. SLA
  Management is fully enabled (the gate) only if **both** this is `ENABLED` **and** versioning is `true`.
- `status == "NOT_ENABLED"` with non-empty `enableBlockedReasons` → **stop**, relay the reasons, do
  not attempt to enable.
- `status == "NOT_ENABLED"` with empty `enableBlockedReasons` → ack with the user (per *Ack structure*), then enable.

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

**This single call enables the whole composite — Simplified SLA Setup *and*, as a side effect, the
permanent SLA Versioning.** Do not trust `success: true` alone — re-run the status GET above and
require `"status": "ENABLED"`, **and** re-run the SLA Versioning query and require
`IsEntitlementVersioningEnabled: true`, before moving on.

### Enable — SLA Versioning (fallback only — normally unnecessary)

The feature enable above already turns versioning on, so you should **not** need a separate versioning
write. Use this Tooling PATCH **only** if the post-enable re-read shows versioning still `false` (e.g.
an older org whose enable automation predates the versioning step). It, too, requires explicit consent
for the permanent switch — versioning is irreversible either way.

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
before moving on (never trust a write response alone).

### Ack structure — two separate consent questions

Enabling the feature is **one inseparable action with a permanent consequence**: it turns on the SLA
Management feature **and, as a one-way side effect, permanently enables SLA Versioning**. **Only SLA
Versioning is permanent.** Scope the reversibility precisely so the customer is neither over- nor
under-warned:

- **Master Incident Management pref** — fully reversible; enabling it has no permanent side effect.
- **SLA Management for IT Service feature** — the feature toggle can be turned off again later, **but
  turning it off does NOT turn SLA Versioning back off**. Versioning stays on permanently once the
  enable flips it. So do **not** describe the feature as cleanly "reversible" without this caveat — a
  customer could otherwise assume disabling SLA Management undoes versioning, which is false.
- **SLA Versioning** — permanent / one-way; guarded against disable at the platform level.

**Ask two separate `AskUserQuestion`s — never merge them into one.** The master enable and the
permanent-versioning consent carry very different stakes (reversible prerequisite vs. irreversible
consequence); bundling them forces an all-or-nothing accept and conflates the two. Do **not** offer a
"versioning-off" path (none exists). Build each from the reads, not a fixed script.

- If **both** the feature and versioning are already on → skip the acks; the gate passes.
- **Q1 — master prerequisite (only if master Incident Mgmt is `NOT_ENABLED`):** ask to enable it
  first. It's **reversible** — present it as a prerequisite with **no** permanence warning. Offer
  **Enable** or **Stop — make no changes**. A declined master → HALT.
- **Q2 — permanence ack for the feature (a distinct question, after the master is on):** if the
  feature is off (and `enableBlockedReasons` is empty) → ask, in customer terms: enabling **SLA
  Management for IT Service** also turns on **SLA Versioning**, which **can't be turned off once
  enabled** — the SLA Management feature itself can be turned off again later, but that will **not**
  turn Versioning back off; Versioning is permanent. Offer **Enable** or **Stop — make no changes**.
- **Any decline — including a request to enable Simplified SLA Setup but *not* versioning — means
  HALT.** There is no way to honor "Simplified without versioning" (enabling the feature flips
  versioning anyway); enable **nothing** and do not proceed to SLA/milestone setup. Say plainly why —
  they're inseparable and versioning is permanent.
- **Never** enable silently or bury the permanent switch in a default — a bare or repeated "enable
  SLA" is not consent for the permanent SLA Versioning switch. This is the W-23979084 bug.
- **After enabling, re-read both** and report the real, both-on state — never trust the write
  response. The gate passes only when Simplified SLA Setup is `ENABLED` **and**
  `IsEntitlementVersioningEnabled` is `true`.

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
`apiName == "service-cloud-itsm-incident"` — the **exact** apiName. Read its `status`
(`ENABLED` / `NOT_ENABLED` / `NOT_AVAILABLE`).

> **Never substitute a look-alike.** The catalog also contains `service-cloud-incident-management`
> — that is **generic Service Cloud Incident Management** (built on Case Management, so its
> `dependencyStatuses` chain through `service-cloud-case-management` → Support Settings Default Case
> Owner + Automated Case User). It is **not** the ITSM master this skill targets, and enabling it
> (plus its Case chain) does **not** unlock ITSM Incident SLA. If `service-cloud-itsm-incident` is
> absent or `NOT_AVAILABLE`, do **not** fall back to it — halt (see below).

**Status → action** (never auto-enable the master as an implied SLA dependency):

- `ENABLED` → proceed.
- `NOT_AVAILABLE` (ITSM Incident Management license/entitlement not present on the org) → **halt and
  surface it** — the master cannot be enabled here, so there is no ack and no delegate. This is the
  correct terminal outcome on an unlicensed org (do not pursue Case Management / generic Incident
  Management as a workaround).
- `NOT_ENABLED` → get an explicit `AskUserQuestion` ack first (per SKILL.md Phase 1 step 1), then
  delegate to `service-itsm-incident-mgmt-configure` inline — that skill runs its own confirm-to-write
  against `POST .../setup/discovery/feature/service-cloud-itsm-incident/enable` and returns after the
  flip. Re-read this step to verify `status == "ENABLED"` before continuing. If the user declines,
  halt — every downstream SLA artifact depends on the master being on.

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
  "query_params": { "q": "SELECT Id, Name, SobjectType, IsActive, BusinessHoursId FROM SlaProcess WHERE Id = '<slaId>'" }
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
        "milestoneAgreementType": "SLA",
        "filterType":             "RuleFilter",
        "filterItems": [
          { "table": "Incident", "column": "Status", "operator": "NotEqual", "order": 1, "value": "Closed" }
        ]
      }
    ]
  }
})
```

`milestoneCriteria` is mandatory. `milestoneAgreementType` is mandatory per the UI and lives **inside each `milestoneCriteria[]` item** (it maps to the `MilestoneCriteria.MilestoneAgreementType` sub-entity field — sending it at the top level of the milestone body returns `JSON_PARSER_ERROR: Unrecognized field`). Valid UI values are **`SLA`** (customer-facing agreement) or **`OLA`** (internal / operational). The API accepts any string because the underlying field is plain `Text(40)` with no server-side picklist enforcement — an unrecognized value persists to the DB but the UI treats it as blank; omitting the field entirely also succeeds silently but leaves the record's Milestone Agreement Type null (W-23959162). Success: `body.id` is the new Milestone Id.

---

## Milestone Actions (Phase 2.5 — Warn / Escalate)

A **milestone action** fires automation at a checkpoint of an existing milestone — a **Warning**
(before target), a **Violation** (at/after target), or a **Success** (on completion). This is how the
skill implements "warn at 75%, escalate on breach". It runs **only** when the user asked to
warn/escalate/notify, **after** the milestones exist (Phase 2 or Phase 2-OOB).

**Scope — apply to every milestone the user named for that policy.** "Warn at 75%, escalate on breach"
attaches to **each** milestone the request scopes it to (e.g. a `15-min response` *and* a `2-hour
resolution` → warn+escalate on **both**), not just one. Each checkpoint on each milestone is a
**separate** `create-milestone-action` call (one action sub-object per call), and the "warn at X%"
offset is computed from **that milestone's own** target (75% of 15 min ≠ 75% of 120 min). Confirm the
whole set in a single `AskUserQuestion` before any write, then dispatch per (milestone × checkpoint).

### Delegate to `create-milestone-action` — don't hardcode the body

The full request schema is owned by the approved headless **`create-milestone-action`** operation.
**Resolve it live** rather than reconstructing the polymorphic body from memory:

```text
mcp__headless-360__discover(query="add milestone action warning violation escalation")
mcp__headless-360__describe(id="<create-milestone-action operation id>")
```

Then `dispatch` the `POST` it returns:
`/services/data/v67.0/connect/sla-management/sla-policies/<slaId>/milestones/<milestoneId>/actions`.

### Checkpoint roles (the `checkpoint` block)

Send **exactly one** action sub-object, plus the checkpoint role. `timeLength`/`timeUnit` go **inside**
`checkpoint` (top-level → `JSON_PARSER_ERROR`). `timeUnit` ∈ **`Minutes` | `Hours` | `Days`** only.
**Never** send `isInitiationCheckpoint` (hard `400`).

| Role | Flags | Timing |
|------|-------|--------|
| Success  | `isSuccessCheckpoint: true`, `checkpoint.isWarning: false` | none |
| Warning  | `isSuccessCheckpoint: false`, `checkpoint.isWarning: true`  | `timeLength`+`timeUnit` **before** target |
| Violation | `isSuccessCheckpoint: false`, `checkpoint.isWarning: false` | `timeLength`+`timeUnit` **after** target (`timeLength: 0` = at breach) |

### "Warn at X%" → offset before target

A warning fires an *offset before* the target, so convert the percentage:

```text
offsetBeforeTarget = round( milestoneTargetMinutes × (1 − X/100) )
```

- 2-hour (120-min) resolution, warn at 75% → `120 × 0.25 = 30` min before.
- 8-hour (480-min) milestone, warn at 75% → `120` min before.
- Round to whole minutes; a 15-min milestone at 75% → `3.75 → 4` min before (very tight, but honor it
  if the user asked to warn on a short milestone; if they left the target open, the longer resolution
  milestone gives a more useful warning window).

"Escalate **on breach**" → a Violation with `timeLength: 0`.

### Proven bodies (live-validated, Field Update)

**Default action is a Field Update** — self-contained, no org dependencies. `actionFlow` returns an
opaque `201 / success:false / INTERNAL_SERVER_ERROR` on empty-flow auto-create in some orgs — avoid it
as the default; Email Alert needs a pre-built template. Warning (warn at 75% of a 2-hr milestone → 30
min before):

```json
mcp__headless-360__dispatch({
  "url": "/services/data/v67.0/connect/sla-management/sla-policies/<slaId>/milestones/<milestoneId>/actions",
  "method": "POST",
  "body": {
    "isSuccessCheckpoint": false,
    "checkpoint": { "isWarning": true, "timeLength": 30, "timeUnit": "Minutes" },
    "entityName": "Incident",
    "actionFieldUpdate": {
      "name": "SLA Warn 75pct RES", "sourceTable": "Incident", "targetTable": "Incident",
      "columnEnumOrId": "Priority", "developerName": "SLA_Warn_75_RES",
      "operationString": "LITERAL", "literal": "High"
    }
  }
})
```

Violation (escalate on breach → `Priority = Critical`): same shape with
`checkpoint: { "isWarning": false, "timeLength": 0, "timeUnit": "Minutes" }`, `name`
`"SLA Escalate on Breach RES"`, `developerName` `SLA_Escalate_Breach_RES`, `literal` `"Critical"`.

**Make `name`/`developerName` unique per milestone.** A `WorkflowFieldUpdate` `DeveloperName` is unique
on the Incident object, so reusing `SLA_Warn_75` on a second milestone fails with
`DUPLICATE_DEVELOPER_NAME`. Suffix both with the milestone (the `_RES` above for Resolution, `_FR`
for First Response — a 15-min First Response at 75% warns 4 min before, `timeLength: 4`). For a custom-field target use its `CustomField` id (`00N…`), not the `__c` API name.

### Confirm from the response body — no read-back of the attachment

The endpoint returns **`201` even on failure**. Real success = `body.success == true` **and** a
non-empty `body.actionMappings`. A **timed** checkpoint — one with an offset > 0, i.e. a Warning fired
some minutes *before* target — **also** returns a `triggerId`. A breach Violation with `timeLength: 0`
fires *at* target and may return **no** `triggerId`; do **not** treat its absence as failure — for it,
`success` + non-empty `actionMappings` is the whole signal. A bad body shape returns an opaque
`201 / success:false / INTERNAL_SERVER_ERROR`.

**Read-back is partial.** There is **no read-back of the checkpoint *attachment*** — nothing headless
echoes which checkpoint (Warning/Violation) or offset an action is wired to. (The Connect
`GET .../milestones/<id>/actions?entityName=Incident` returns the *builder* catalog — available
actions + field metadata, with `previouslyAttachedActions: []` — **not** the configured state; and
`MilestoneAction` is not a SOQL sObject.) The action **definitions** themselves *are* Tooling-queryable
if you only need to confirm the objects persisted — e.g. `SELECT Id, Name FROM WorkflowFieldUpdate
WHERE Id IN (<the actionMapping ids from the create responses>)` for the default Field Update action
(other action types map to `WorkflowAlert` / `Task` / etc.) — but that confirms **existence only**, not
the attachment or offset, so it is an optional debugging aid, not the verification. There is also **no
clean headless delete**. Because the attachment can't be read back, the full action set **must be
confirmed before writing**. Up-front authorization (the Phase 1.4 skip condition (c)) waives the
interactive `AskUserQuestion` re-ask exactly as Phase 1.5 does, but the set must still be **narrated**
before the writes; verification is body-based, not a GET.

### "IST business hours" is a policy-level BusinessHours, not an action field

Milestone actions carry **no** timezone/business-hours attribute. "IST business hours" is a
`BusinessHours` record (`TimeZoneSidKey: "Asia/Kolkata"` + weekly windows) attached at the **policy /
Entitlement** level (`Entitlement.BusinessHoursId`). Resolve-then-create:

1. Look up an existing BusinessHours with `TimeZoneSidKey = 'Asia/Kolkata'`; **reuse** if found.
2. Else create one — `POST /sobjects/BusinessHours` (`Name`, `TimeZoneSidKey: "Asia/Kolkata"`,
   default Mon–Fri 09:00–18:00 windows). `BusinessHours` is **createable but not API-deletable**, so
   confirm before creating; never mutate the org `Default` record and never set `IsDefault`.
3. Attach via the policy/Entitlement `BusinessHoursId`.

**Caveat — read it live and disclose:** if the org has `ignoreMilestoneBusinessHours = true`, milestone
SLA timers run **24/7** and ignore business hours, so an IST BusinessHours is recorded but does **not**
shift the milestone clock. State this plainly instead of implying IST changed the timers.

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

## Predefined Incident Policy (Phase 0.6 detect + Phase 2-OOB seed)

The out-of-box **"Standard Support for Incidents"** policy is what Salesforce seeds from Setup's
"Create Predefined Policies" step (Incident process type only). That step is Aura-only and not
headless-reachable, but it seeds via the **same backend** as the public `/connect/sla-management/*`
routes above — so the skill replicates it exactly with routes it already uses. The full template
(policy flags, 2 milestone types, 8 priority-tiered milestones, entitlement criterion) lives in
**`assets/predefined-incident-policy.json`** — load and follow it; the values below are the shape.

### Detect first (no server idempotency → mandatory)

Re-seeding is **not** idempotent — a second seed duplicates every artifact. Before offering to seed,
read the existing Incident policies and name-match:

```json
mcp__headless-360__dispatch_readonly({
  "url":    "/services/data/v67.0/connect/sla-management/sla-policies",
  "method": "GET",
  "query_params": { "processTypes": "Incident" }
})
```

If any returned policy's name is **"Standard Support for Incidents"**, it is already seeded — report
it and do **not** re-seed. (Fallback: SOQL `SELECT Id, Name FROM SlaProcess WHERE SobjectType =
'Incident' AND Name = 'Standard Support for Incidents'`.)

### Seed recipe (only if not already present)

Uses the Phase 2 routes above, in this order:

1. **Resolve the 2 MilestoneTypes — detect first, create only what is missing.** Enabling the SLA
   Management feature pre-seeds a default MilestoneType catalog (commonly `First Response`,
   `Follow Up`, `Periodic Update`, **`Resolve Within`**), so a blind `POST .../milestone-types` for a
   name that already exists returns **HTTP 500 ("already exists")** and leaves the policy half-seeded.
   First read the catalog — SOQL `SELECT Id, Name FROM MilestoneType WHERE Name IN ('Acknowledge
   Within', 'Resolve Within')` (or `GET .../milestone-types`) — **reuse any match by id**, and `POST
   .../milestone-types` (`recurrenceType: OneTime`) **only** for the name(s) not already present.
   Capture both ids (whether reused or created).
2. Create the SLA Policy `Standard Support for Incidents` (`POST .../sla-policies`) with
   `processType: "Incident"`, `businessHourId` = default, `createdDateEntryCriteria: true`,
   `closedExitCriteria: true`, `versionDefault: true`, **`active: true`** (create it active directly —
   do **not** use the Connect activate PATCH, which can 500 headless). Verify via SOQL on `SlaProcess`.
3. Attach the **8 priority-tiered milestones** (`POST .../sla-policies/<id>/milestones`, one per row).
   Reuse `assets/attach-milestone.json`. Validate each Priority/Status value against the live
   `Incident` picklist first. For the **mid tier**, map to the org's actual mid-priority label —
   `Moderate` on the standard ITSM picklist, but many orgs label it `Medium` — and seed orders 5–6
   with whichever the live picklist carries rather than dropping the tier. Drop a row **only** when its
   value is genuinely absent from the picklist, and note any dropped or relabeled tier in the report.

| order | milestoneType | timeTrigger | active criterion (Priority) | completion (Status) |
|-------|---------------|-------------|-----------------------------|---------------------|
| 1 | Acknowledge Within | 30  | `Equals Critical` | `NotEqual New` |
| 2 | Resolve Within     | 120 | `Equals Critical` | `In [Resolved, Completed, Closed]` |
| 3 | Acknowledge Within | 60  | `Equals High` | `NotEqual New` |
| 4 | Resolve Within     | 240 | `Equals High` | `In [Resolved, Completed, Closed]` |
| 5 | Acknowledge Within | 240 | `Equals Moderate` | `NotEqual New` |
| 6 | Resolve Within     | 960 | `Equals Moderate` | `In [Resolved, Completed, Closed]` |
| 7 | Acknowledge Within | 240 | `Equals Low` | `NotEqual New` |
| 8 | Resolve Within     | 960 | `Equals Low` | `In [Resolved, Completed, Closed]` |

The **active** criterion (`Priority Equals <tier>`) is the one the public Attach-Milestone
`milestoneCriteria` carries (`milestoneState: Active`, `milestoneAgreementType: SLA`,
`filterType: RuleFilter`) — seeding it engages each milestone. The OOB also carries completion
(`Status In …`) and cancel (`Priority NotEqual <tier>`) criteria (`milestoneState` Complete / Cancel);
confirm the route accepts those states in the smoke test — if not, the active criterion alone is
sufficient for engagement (matches `examples/milestone-patterns.md` Pattern 3).

**OR / In have no single-row form.** `filterItems` AND by default and there is no `In` operator. The
Priority tiers are already pre-split above (each row is a single `Priority Equals <tier>`, Moderate and
Low as separate rows 5–8), so no OR is needed for Priority. For the `Status In` completion sets, either
use `filterLogic: "1 OR 2"` if the route accepts it (verify live) or split into one row per value —
behavior-equivalent.

4. Create the Entitlement (`POST /sobjects/Entitlement`) on the resolved Account, `SlaProcessId` =
   the seeded policy, backdated `StartDate`. **Attempt** the OOB always-match entitlement criterion
   (`Subject NotEqual <sentinel>`, see the asset) via `POST /connect/sla-management/entitlement-criteria`
   so the policy auto-matches every Incident like true OOB. **First `describe` that operation and send
   its exact input fields** — do **not** reuse the milestone-criteria body shape: `entitlement-criteria`
   rejects `filterType` (`400 JSON_PARSER_ERROR: Unrecognized field "filterType"`); its criterion body
   differs. If the create still fails after using the described schema, fall back to the date-windowed
   Entitlement alone and **disclose only the consequence, in plain customer terms**: the seeded policy
   then engages on Incidents wired to this Entitlement (`EntitlementId` set), not on every Incident
   automatically — to make it apply to all Incidents, add the always-match criterion via **Setup →
   Entitlement Management**. **Do NOT tell the user the route is "unreachable" or its schema
   "undiscoverable"** — that is inaccurate; the route works, the criterion body just needs its correct
   fields (a wrong-payload `400`, not a platform gap), and misattributing it reads as a bug. Never
   surface the raw sentinel string or a `JSON_PARSER_ERROR` in the customer report. The date-windowed
   Entitlement plus the milestone criteria are still enough to engage the Phase 3 test Incident.
5. Verify per **Verify SLA engagement** below with a **Critical** test Incident (a Critical Priority
   matches orders 1–2, so an `EntityMilestone` spawns), then **STOP** — do not offer custom.

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
| Milestone filter payload | `milestoneCriteria` is mandatory (omitting it → `400: Criteria details cannot be empty`). Use `filterType: "RuleFilter"` with concrete `filterItems[]` — `filterType: "Formula"` triggers a 500. Operators are `Equals` (not `Equal`) and `NotEqual` (not `NotEquals`/`NotEqualTo`/`!=`); wrong forms → `POST_BODY_PARSE_ERROR: Invalid value for Filter Operation Enum`. |
| `slaProcessId` rejected in body | The server returns `JSON_PARSER_ERROR: Unrecognized field "slaProcessId"` — the id is in the path only. |
| Entitlement create + status | Create via `POST /sobjects/Entitlement` (standard sObject, not the Connect surface). Status is date-computed: a future `StartDate` → `Inactive`; backdate `StartDate` to yesterday for immediate SLA engagement in testing. |
| OOB seed has no idempotency | `POST .../sla-policies` does not dedupe — re-seeding "Standard Support for Incidents" duplicates every artifact. Detect first via `GET .../sla-policies?processTypes=Incident` and name-match before seeding. |
| Connect activate PATCH may 500 | The OOB backend flips the policy active via a Connect activate call; headless, that PATCH can 500. Create the SlaProcess with `active: true` directly instead (as the custom flow does). |
| Never leak a record Id | In **every** user-facing message (interim narration *and* the final report, incl. "created milestone …" progress lines), refer to the Phase-3 test Incident by its **`IncidentNumber`** (the verify SOQL selects it) and milestones by their **`MilestoneType.Name`** — never the 15/18-char record Id. |

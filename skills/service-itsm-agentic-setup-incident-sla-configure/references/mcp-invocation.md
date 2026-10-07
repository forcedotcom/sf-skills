# MCP Invocation Reference — Incident SLA

Every operation dispatches through the **Salesforce-hosted `headless-360`** MCP server, which
exposes four meta-tools:

- `mcp__headless-360__discover(query)` — semantic search over the indexed operation catalog
- `mcp__headless-360__describe(id)` — pulls the schema and canonical route for one operation
- `mcp__headless-360__dispatch_readonly({url, method, query_params?, body?})` — GET / read-only HTTP
- `mcp__headless-360__dispatch({url, method, body?, query_params?})` — POST / PATCH / DELETE HTTP

**Dispatch takes raw HTTP**, not `{operation_id, arguments}`. Give it the full `url`
(`/services/data/v{version}/...`), `method`, optional `body`, and optional `query_params` — the server
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
| `GET  /headless/invoke/platform/slasettings/get-sla-management-permission` | Phase 0.5 — read whether SLA Management is on (composite: Entitlements + Simplified SLA Setup + Pause Milestone). Delegated to `itsm-shakti/SLASettings` |
| `PATCH /headless/invoke/platform/slasettings/set-sla-management-permission` | Phase 0.5 — turn SLA Management on (`isEnabled:true`; flips the three prefs atomically; requires Entitlements already on or it throws). **Reversible.** Delegated to `itsm-shakti/SLASettings` |
| `GET  /headless/invoke/platform/slasettings/get-sla-versioning-permission` | Phase 0.5 — read whether SLA Versioning is on. Delegated to `itsm-shakti/SLASettings` |
| `PATCH /headless/invoke/platform/slasettings/set-sla-versioning-permission` | Phase 0.5 — turn SLA Versioning on (`isEnabled:true`). **Separate write; permanent / one-way** — the controller refuses to disable it. Delegated to `itsm-shakti/SLASettings` |
| `GET  /services/data/v{version}/sobjects/Incident/describe` | Preflight — Incident Management on + SLA fields present |
| `GET  /services/data/v{version}/query` | SOQL reads (BusinessHours, SlaProcess, EntityMilestone) via `query_params.q` |
| `GET  /headless/invoke/platform/slasettings` | Phase 0.6 / 2-OOB — the seeder's existence map (get-existing-checkbox-states); lowercase keys `{incident,problem,changeRequest}`, `true` = default already seeded (dedup read) |
| `PATCH /headless/invoke/platform/slasettings/save-selected-options` | Phase 2-OOB — seed the predefined bundle in one call; body `{"selectedOptions":["incident"]}` (**lowercase** — capitalized 500s); provisions the full active policy + Entitlement + criteria |
| `GET  /services/data/v{version}/connect/sla-management/sla-policies` | List Incident SLA policies via `query_params.processTypes=Incident` (coexistence detect — is another active Incident policy present?) |
| `POST /services/data/v{version}/connect/sla-management/milestone-types` | Create MilestoneType |
| `POST /services/data/v{version}/connect/sla-management/sla-policies` | Create SLA Policy (SlaProcess) |
| `POST /services/data/v{version}/connect/sla-management/sla-policies/<slaId>/milestones` | Attach Milestone |
| `PATCH /services/data/v{version}/connect/sla-management/sla-policies/<slaId>/status?isActive=true&createEntitlement=true` | **Custom flow** — activate the policy + auto-provision its Entitlement (`isActive`/`createEntitlement` are QUERY params) |
| `POST /services/data/v{version}/connect/sla-management/entitlement-criteria` | **Custom flow** — auto-apply the activated policy's Entitlement to matching records (delegated to `csp-sun/create-entitlement-criteria`); `describe` first and send its exact fields (rejects `filterType`). OOB does not use this — the seeder provisions its own criteria |
| `POST /services/data/v{version}/sobjects/Incident` | Create a test Incident |
| `POST /services/data/v{version}/sobjects/BusinessHours` | Phase 2.5 — create an IST (or other-timezone) BusinessHours for the policy/Entitlement (createable; **not** API-deletable) |
| `POST /services/data/v{version}/connect/sla-management/sla-policies/<slaId>/milestones/<milestoneId>/actions` | Phase 2.5 — attach a Warn/Escalate milestone action (delegate via the `create-milestone-action` op) |

**API VERSION:** the `v{version}` segment in every URL above (and everywhere in this
skill) is resolved to the target org's own current API version at dispatch — resolve it
once via `GET /services/data/` at the start of the run and substitute it everywhere; do
NOT pin a release-specific version (e.g. `v67.0`), and do NOT mix versions within a run.
Minimum API version is **67.0** — `headless-360` currently only routes `v67.0+`, so the
org-resolved version is always at or above that floor.

---

## Phase 0.5 — SLA Management for IT Service prerequisite gate

**SLA Management for IT Service reads as fully enabled only when BOTH sub-settings are on —
Simplified SLA Setup AND SLA Versioning.** In Setup it shows **In Progress** while either is off. Both
the reads and the writes below are **delegated to `itsm-shakti/SLASettings`** (which owns the
SLA-Management settings surface) — `discover` → `describe` → `dispatch` its
operations rather than re-deriving the routes here. The paths below are the delegate's, shown for
orientation; take the authoritative request/response shape from its `describe`.

**Two independent switches, two separate writes — enabling SLA Management does NOT auto-enable
Versioning.**
- **SLA Management** (`set-sla-management-permission`, `isEnabled:true`) flips its composite prefs
  atomically (Simplified SLA Setup + Pause Milestone + the Entitlements pref). It **requires
  Entitlements already on** or the controller throws. This toggle is **reversible** (`isEnabled:false`).
- **SLA Versioning** (`set-sla-versioning-permission`, `isEnabled:true`) is a **separate** write and a
  **permanent, one-way** migration. Turning SLA Management back off does **not** turn Versioning back
  off — the controller refuses any disable ("SLA Versioning cannot be disabled once it is enabled").
  So completing the gate takes **both** writes, and the versioning write is irreversible.

Because the versioning write is irreversible, **never fire it without explicit, informed consent for
the permanent switch** — an explicit permanence-gated `AskUserQuestion`, kept separate from the
master-enable ack (see *Ack structure* below). If the user declines the permanence, do **not** complete
the gate (SLA Management alone does not satisfy it), and the run **halts**.

This is the root of the versioning false-report defect: the skill turned Versioning on but then
**falsely reported it as off**. The fix: get permanence consent up front, and after each write re-read
and report the **real** state.

### Read — SLA Management state

```json
mcp__headless-360__dispatch_readonly({
  "url":    "/headless/invoke/platform/slasettings/get-sla-management-permission",
  "method": "GET"
})
→ true | false     // composite over Entitlements + Simplified SLA Setup + Pause Milestone
```

- `true` → SLA Management is on; now read SLA Versioning below. The gate passes only if **both** reads return `true`.
- `false` → ack with the user (per *Ack structure*), confirm Entitlements are on, then write `set-sla-management-permission`.

### Read — SLA Versioning state

```json
mcp__headless-360__dispatch_readonly({
  "url":    "/headless/invoke/platform/slasettings/get-sla-versioning-permission",
  "method": "GET"
})
→ true | false
```

`true` is **permanent** — never attempt to flip it back. Surface the permanence to the user before the write; never enable it silently.

### Enable — SLA Management (only after the master/feature ack; skip if the read returned `true`)

```json
mcp__headless-360__dispatch({
  "url":    "/headless/invoke/platform/slasettings/set-sla-management-permission",
  "method": "PATCH",
  "body":   { "isEnabled": true }
})
```

Requires Entitlements already on (else it throws); reversible. Do **not** trust the write response —
re-read `get-sla-management-permission` and require `true` before the versioning write.

### Enable — SLA Versioning (a SEPARATE write; only after the distinct permanence ack; skip if the read returned `true`)

```json
mcp__headless-360__dispatch({
  "url":    "/headless/invoke/platform/slasettings/set-sla-versioning-permission",
  "method": "PATCH",
  "body":   { "isEnabled": true }
})
```

**Permanent / one-way** — no disable path exists (the controller refuses `isEnabled:false` afterward).
Re-read `get-sla-versioning-permission` and require `true` before moving on (never trust the write
response alone).

### Ack structure — two separate consent questions

Completing the gate takes two writes with very different stakes — a **reversible** SLA Management
enable and an **irreversible** SLA Versioning enable. Scope the reversibility precisely so the
customer is neither over- nor under-warned:

- **Master Incident Management pref** — fully reversible; enabling it has no permanent side effect.
- **SLA Management for IT Service** (`set-sla-management-permission`) — **reversible**; can be turned
  off again later. Turning it off does **not** turn SLA Versioning back off.
- **SLA Versioning** (`set-sla-versioning-permission`) — a **separate** write; permanent / one-way,
  guarded against disable at the platform level.

**Ask two separate `AskUserQuestion`s — never merge them into one.** The reversible enables and the
permanent-versioning consent carry very different stakes; bundling them forces an all-or-nothing
accept and conflates the two. Do **not** offer a "versioning-off" path (none exists). Build each from
the reads, not a fixed script.

- If **both** SLA Management and Versioning are already on → skip the acks; the gate passes.
- **Q1 — master prerequisite (only if master Incident Mgmt is `NOT_ENABLED`):** ask to enable it
  first. It's **reversible** — present it as a prerequisite with **no** permanence warning. Offer
  **Enable** or **Stop — make no changes**. A declined master → HALT.
- **Q2 — enable + permanence ack (a distinct question, after the master is on):** if SLA Management
  and/or Versioning are off → ask, in customer terms: completing SLA Management setup turns on **SLA
  Management** and, as a separate step, **SLA Versioning**, which **can't be turned off once enabled**
  — SLA Management itself can be turned off again later, but that will **not** turn Versioning back
  off; Versioning is permanent. Offer **Enable** or **Stop — make no changes**.
- **Any decline — including a request to enable SLA Management but *not* Versioning — means HALT.**
  The gate needs Versioning on, and there is no way to honor "SLA Management without Versioning" as a
  completed gate; enable **no further** writes and do not proceed to SLA/milestone setup (a reversible
  SLA Management enable already made may stand). Say plainly why — Versioning is required and permanent.
- **Never** enable Versioning silently or bury the permanent switch in a default — a bare or repeated
  "enable SLA" is not consent for the permanent SLA Versioning switch. This is the versioning
  false-report bug.
- **After each write, re-read** and report the real, both-on state — never trust the write response.
  The gate passes only when `get-sla-management-permission` **and** `get-sla-versioning-permission`
  both return `true`.

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
  "url":    "/services/data/v{version}/connect/setup/discovery/features",
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
  "url":    "/services/data/v{version}/sobjects/Incident/describe",
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
  "url":    "/services/data/v{version}/query",
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
  "url":    "/services/data/v{version}/connect/sla-management/milestone-types",
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
  "url":    "/services/data/v{version}/connect/sla-management/sla-policies",
  "method": "POST",
  "body": {
    "name":                    "Incident SLA Policy",
    "description":             "Incident SLA Policy",
    "processType":             "Incident",
    "businessHourId":          "<BusinessHoursId>",
    "createdDateEntryCriteria": true,
    "closedExitCriteria":       true,
    "active":                   false,
    "versionDefault":           true
  }
})
```

**The response body echoes most fields as `null`.** Do not trust it — capture `body.id` and
verify state via SOQL:

```json
mcp__headless-360__dispatch_readonly({
  "url":    "/services/data/v{version}/query",
  "method": "GET",
  "query_params": { "q": "SELECT Id, Name, SobjectType, IsActive, BusinessHoursId FROM SlaProcess WHERE Id = '<slaId>'" }
})
```

**Custom flow creates the policy inactive** (`active: false`) — activation is a separate, explicit
step so the Entitlement is **auto-provisioned**. After the milestones are attached, activate via the
`csp-sun/activate-sla-policy` leaf:

```json
mcp__headless-360__dispatch({
  "url":    "/services/data/v{version}/connect/sla-management/sla-policies/<slaId>/status",
  "method": "PATCH",
  "query_params": { "isActive": "true", "createEntitlement": "true" }
})
```

`isActive` and `createEntitlement` are **QUERY params, not a body** (sending them in a body `500`s
headless). `createEntitlement=true` **auto-provisions the Entitlement** and returns its
`entitlementId` — bind the auto-apply criteria to it (see *Entitlement Criteria* / the
`csp-sun/create-entitlement-criteria` leaf). Verify by reading the policy back (`IsActive = true`)
via SOQL, never the write response. **This is the custom-flow activation path — a `200` with a
returned `entitlementId` is the success shape.** The **OOB/predefined seed path does NOT use this PATCH
at all** — its single `save-selected-options` call seeds an already-active policy and auto-provisions
the Entitlement itself (see *Predefined Incident Policy*).

---

## Attach Milestone

`slaProcessId` is carried by the URL path — **omit it from the body** (the server returns
`JSON_PARSER_ERROR: Unrecognized field "slaProcessId"`).

```json
mcp__headless-360__dispatch({
  "url":    "/services/data/v{version}/connect/sla-management/sla-policies/<slaId>/milestones",
  "method": "POST",
  "body": {
    "milestoneTypeId":  "<MilestoneTypeId>",
    "businessHoursId":  "<BusinessHoursId>",
    "timeTrigger":      60,
    "order":            1,
    "startTimeBasedOn": "MILESTONE_CRITERIA",
    "milestoneCriteria": [
      {
        "milestoneState":         "ACTIVE",
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

**`startTimeBasedOn`** controls when the timer starts. Send **`"MILESTONE_CRITERIA"`** (matches OOB and every default pattern) to start the clock when the milestone's ACTIVE criteria first match. It is a free string with two recognized values — **`MILESTONE_CRITERIA`** (criteria-based / dynamic start) and **`SLA_PROCESS`** (the fallback); any other value silently defaults to the `SLA_PROCESS` behavior (no error). The fallback anchors the timer to the **Incident's `SlaStartDate`** (→ its `CreatedDate` if `SlaStartDate` is null) — **not** the SLA-process record's created date. **This choice is not runtime-verifiable in the standard verify flow:** for a test Incident that matches the SLA at creation, both settings compute the same `TargetDate` (≈ `SlaStartDate + timeTrigger`) — they diverge only when the criteria first match *after* creation (e.g. a later field change), which the Phase 3 test does not exercise. So send the OOB value and rely on it; there is no Phase-3 assertion that distinguishes the two (unlike the ACTIVE criterion, whose effect **is** observable via tiering — see below). `milestoneCriteria` is mandatory. `milestoneAgreementType` is mandatory per the UI and lives **inside each `milestoneCriteria[]` item** (it maps to the `MilestoneCriteria.MilestoneAgreementType` sub-entity field — sending it at the top level of the milestone body returns `JSON_PARSER_ERROR: Unrecognized field`). Valid UI values are **`SLA`** (customer-facing agreement) or **`OLA`** (internal / operational). The API accepts any string because the underlying field is plain `Text(40)` with no server-side picklist enforcement — an unrecognized value persists to the DB but the UI treats it as blank; omitting the field entirely also succeeds silently but leaves the record's Milestone Agreement Type null. Success: `body.id` is the new Milestone Id.

**`milestoneState` MUST be UPPERCASE and comes from a fixed set — this is load-bearing.** Valid values are **`ACTIVE`**, **`COMPLETE`**, **`PAUSE`**, **`UNPAUSE`** (there is **no `CANCEL`** state). The server compares `milestoneState` against `"ACTIVE"` **case-sensitively**, so `"Active"`/`"active"` (or any wrong case) **silently fails to register the ACTIVE criterion** — the create still returns `201 success:true`, but the priority/entry filter is never written and the Setup UI shows blank Activation Criteria. The milestone loses its Priority gate, so **in practice every Incident engages the lowest-`order` milestone of that MilestoneType regardless of its Priority** — a priority-tiered policy collapses to one tier. Use `ACTIVE` for the engagement (Priority) criterion and `COMPLETE` for the completion (Status) criterion; never send `CANCEL` (once the `ACTIVE` Priority criterion is correct it gates engagement, making a cancel criterion redundant).

**The create response NEVER echoes `milestoneCriteria` — it always returns `milestoneCriteria: []` even on success** (the create handler only sets `id`/`success`; only a subsequent GET/read-back populates criteria). So the `201` proves nothing about whether criteria persisted. **Verify by runtime, not the response:** after seeding, create a **non-matching-tier** test Incident (e.g. a Moderate/Low one for a Critical-first policy) and confirm its `EntityMilestone.TargetResponseInMins` matches that tier's `timeTrigger`, not order-1's. A Critical-only test can't catch a dropped criterion because Critical maps to order-1, which is also the collapse fallback.

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
`/services/data/v{version}/connect/sla-management/sla-policies/<slaId>/milestones/<milestoneId>/actions`.

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

### Milestone-action bodies (Field Update; example shapes, pending live verification)

**Default action is a Field Update** — self-contained, no org dependencies. `actionFlow` returns an
opaque `201 / success:false / INTERNAL_SERVER_ERROR` on empty-flow auto-create in some orgs — avoid it
as the default; Email Alert needs a pre-built template. **`Incident.Priority` is derived from
Impact × Urgency and is NOT directly updateable** (`createable:false / updateable:false` — see *Verify
SLA engagement*), so a Field Update targeting `Priority` fails `INVALID_FIELD_FOR_INSERT_UPDATE`.
Escalate by driving Priority's **updateable inputs** instead: raise `Urgency` on the warning and
`Impact` on the breach — both axes High drives the derived Priority to its top tier. Warning (warn at
75% of a 2-hr milestone → 30 min before):

```json
mcp__headless-360__dispatch({
  "url": "/services/data/v{version}/connect/sla-management/sla-policies/<slaId>/milestones/<milestoneId>/actions",
  "method": "POST",
  "body": {
    "isSuccessCheckpoint": false,
    "checkpoint": { "isWarning": true, "timeLength": 30, "timeUnit": "Minutes" },
    "entityName": "Incident",
    "actionFieldUpdate": {
      "name": "SLA Warn 75pct RES", "sourceTable": "Incident", "targetTable": "Incident",
      "columnEnumOrId": "Urgency", "developerName": "SLA_Warn_75_RES",
      "operationString": "LITERAL", "literal": "High"
    }
  }
})
```

Violation (escalate on breach → raise `Impact = High`): same shape with
`checkpoint: { "isWarning": false, "timeLength": 0, "timeUnit": "Minutes" }`, `name`
`"SLA Escalate on Breach RES"`, `developerName` `SLA_Escalate_Breach_RES`, `columnEnumOrId` `"Impact"`,
`literal` `"High"`.

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

## Predefined Incident Policy (Phase 0.6 detect + Phase 2-OOB seed)

The out-of-box **"Standard Support for Incidents"** policy is what Salesforce seeds from Setup's
"Create Predefined Policies" step (Incident process type only). That seeder — the SLA Settings page's
**Create Predefined Policies** action (`save-selected-options`) — is served headless on the **Aura dispatcher route**
`/headless/invoke/platform/slasettings/*`, so the skill invokes the **real seeder in ONE call** rather
than replicating its output. The seeder builds the entire **active** bundle itself — policy + 2
MilestoneTypes + 6 milestones (Critical/High per-tier, Moderate+Low merged) + Entitlement + auto-apply
criteria — the same core out-of-box seed data, with Core's own Priority/Status handling. (Route
live-proven for both read and write; the former hand-rebuilt replica over `/connect/sla-management/*`
plus the manual `POST /sobjects/Entitlement` is retired.)

### Detect first (no server idempotency → mandatory)

Re-seeding is **not** idempotent — a second seed duplicates every artifact. Before offering to seed,
read the seeder's own existence map:

```json
mcp__headless-360__dispatch_readonly({
  "url":    "/headless/invoke/platform/slasettings",
  "method": "GET"
})
```

It returns a **lowercase-keyed** map, e.g. `{"incident": true}` (keys: `incident`, `problem`,
`changeRequest`; a key is `true` when that type's default is already seeded). If `incident` is `true`,
the OOB policy is already present — report it and do **not** re-seed. (Fallback: SOQL `SELECT Id, Name
FROM SlaProcess WHERE SobjectType = 'Incident' AND Name = 'Standard Support for Incidents'`.)

### Seed (only if not already present)

One call:

```json
mcp__headless-360__dispatch({
  "url":    "/headless/invoke/platform/slasettings/save-selected-options",
  "method": "PATCH",
  "body":   { "selectedOptions": ["incident"] }
})
```

- **`selectedOptions` values MUST be lowercase** (`incident` / `problem` / `changeRequest`), matching
  the existence-map keys. The capitalized `Incident` form returns a server-side **`500`** — this is the
  single most common failure; the describe metadata's `{Incident,Problem,ChangeRequest}` casing is
  misleading, so send lowercase.
- Success is **HTTP `200` with body `true`**. The seeded policy is **active**, and its Entitlement and
  auto-apply criteria are provisioned by the seeder — there is **no** manual `POST /sobjects/Entitlement`
  and **no** Connect activate PATCH (so the 500 that path could throw never arises).

### Verify

Re-read the existence map (`GET /headless/invoke/platform/slasettings`) and confirm `incident: true`,
then SOQL `SlaProcess` for **"Standard Support for Incidents"** with `IsActive = true` (do not trust the
write body). Then verify runtime engagement per **Verify SLA engagement** below with a **Moderate/Low**
test Incident — its `EntityMilestone` must land on the 240/960 tier, not 30/120 (Critical is order-1,
the collapse fallback, so it can't detect a mis-tiered seed). Then **STOP** — do not offer custom.
Narrate the policy by name, never its Id (Output contract).

---

## Verify SLA engagement

Create a test Incident. **`Priority` is NOT directly writable on `Incident`** — the field is
`createable:false / updateable:false` (not a formula) and is **platform-derived from `Impact` ×
`Urgency`** via the ITSM priority matrix (both are `High | Medium | Low` picklists). Sending
`Priority` in the body fails with `INVALID_FIELD_FOR_INSERT_UPDATE`. So to land the test Incident on
a target tier, set **`Impact` and `Urgency`** (never `Priority`), then read the **derived** `Priority`
back to confirm which tier it resolved to — the matrix is **org-configurable**, so do NOT hardcode the
mapping. **Pick a tier that actually exercises the milestone under test — for a Priority-tiered or OOB
policy use a Moderate/Low Incident, NOT Critical.** Critical is the order-1 milestone (the collapse
fallback), so it always stamps an EntityMilestone and can't reveal a mis-tiered or dropped milestone
(the OOB Verify step mandates Moderate/Low for the same reason). (On the default matrix
`Impact=Medium, Urgency=Medium` → a mid tier and `Impact=High, Urgency=High` → `Critical`; treat these
as default-matrix illustrations, not guarantees — always read the derived `Priority` back.) Wire the
Entitlement explicitly (`EntitlementId`) so engagement is deterministic and does not depend on the
auto-apply criterion:

```json
mcp__headless-360__dispatch({
  "url":    "/services/data/v{version}/sobjects/Incident",
  "method": "POST",
  "body":   { "Subject": "SLA test incident", "Impact": "Medium", "Urgency": "Medium", "EntitlementId": "<EntitlementId>" }
})
```

Then confirm the derived Priority landed on the intended tier, and that the Incident stamped an SLA
start and an EntityMilestone:

```json
mcp__headless-360__dispatch_readonly({
  "url":    "/services/data/v{version}/query",
  "method": "GET",
  "query_params": { "q": "SELECT Id, IncidentNumber, Subject, Status, Priority, Impact, Urgency, SlaStartDate FROM Incident WHERE Id = '<incidentId>'" }
})
```

```json
mcp__headless-360__dispatch_readonly({
  "url":    "/services/data/v{version}/query",
  "method": "GET",
  "query_params": { "q": "SELECT Id, MilestoneType.Name, TargetDate, IsCompleted, IsViolated FROM EntityMilestone WHERE ParentEntityId = '<incidentId>'" }
})
```

**At least one `EntityMilestone` row with a `TargetDate`** is the reliable proof the SLA engaged —
assert on that first. `Incident.SlaStartDate` is populated when the Incident is created with an
explicit `EntitlementId`, but can come back **null** when the Entitlement is applied hands-free by an
entitlement-criteria rule (the milestone still lands, with its `TargetDate` computed off `CreatedDate`
— the `SLA_PROCESS` fallback anchor). So treat a null `SlaStartDate` as a non-blocker, not a failure,
as long as the `EntityMilestone` is present on the correct tier.
When `SlaStartDate` is populated, `TargetDate` should equal `SlaStartDate + timeTrigger minutes`
(business-hours-adjusted), and
`EntityMilestone.TargetResponseInMins` should equal the target tier's `timeTrigger`. First confirm the
**derived** `Priority` on the Incident is the tier you intended (from the `Impact`/`Urgency` you set) —
if the org's matrix mapped your `Impact`/`Urgency` to a different Priority, adjust them and recreate
rather than reading the assertion against the wrong tier.

---

## Gotchas

| Issue | Detail |
|-------|--------|
| `dispatch` shape is raw HTTP | Pass `{url, method, body?, query_params?}` — NOT `{operation_id, arguments}`. |
| Response wrapper | Connect/`/sobjects`/`/query` are singly wrapped — read `body`. Aura `/headless/invoke/…` routes (not used here) are doubly wrapped. |
| Corpus vs. registry drift | `discover` may not rank the SLA POST routes at the top — the routes are still known-good; `describe` + `dispatch` on the canonical path works either way. |
| SLA Policy create response is null | `POST /sla-policies` echoes most fields as `null` — always verify via SOQL on `SlaProcess`; then narrate the policy by the **verified name**, never the captured/queried Id (Output contract). |
| Milestone filter payload | `milestoneCriteria` is mandatory (omitting it → `400: Criteria details cannot be empty`). Use `filterType: "RuleFilter"` with concrete `filterItems[]` — `filterType: "Formula"` triggers a 500. Operators are `Equals` (not `Equal`) and `NotEqual` (not `NotEquals`/`NotEqualTo`/`!=`); wrong forms → `POST_BODY_PARSE_ERROR: Invalid value for Filter Operation Enum`. |
| `slaProcessId` rejected in body | The server returns `JSON_PARSER_ERROR: Unrecognized field "slaProcessId"` — the id is in the path only. |
| OOB seed `selectedOptions` casing | The `save-selected-options` values MUST be **lowercase** (`incident`/`problem`/`changeRequest`), matching the existence-map keys. The capitalized `Incident` form returns a server-side **`500`** — the single most common OOB failure; the describe metadata's `{Incident,Problem,ChangeRequest}` casing is misleading. |
| OOB seed has no idempotency | `save-selected-options` does not dedupe — re-seeding "Standard Support for Incidents" duplicates every artifact. Detect first via `GET /headless/invoke/platform/slasettings` (existence map; `incident: true` = already seeded) before seeding. |
| OOB uses the seeder, not the Connect activate PATCH | The **OOB seed** does one `save-selected-options` call that seeds an already-active policy + auto-provisions its Entitlement — it never touches the Connect activate PATCH. The **custom flow** activates via the `csp-sun/activate-sla-policy` leaf (`isActive`+`createEntitlement` query params) — the no-500 activation path (a `200` with a returned `entitlementId` is the success shape). |
| Never leak a record Id (SKILL.md Output contract) | In **every** user-facing message — interim narration *and* the final report, incl. "created milestone …" / "policy created …" / "reusing existing … →" progress lines — refer to the Phase-3 test Incident by its **`IncidentNumber`** (the verify SOQL selects it) and milestones/policy by their **name** — never the 15/18-char record Id (full **or masked**, e.g. `557VW…R3XVYA0`) or a `triggerId`. This covers **detected/reused** artifacts too — no `→ <Id>` "proof of reuse". Ids stay internal (chaining only). |

---
name: service-itsm-agentic-setup-incident-sla-configure
description: "End-to-end Incident SLA setup for Service Cloud ITSM — creating a MilestoneType, an Incident-scoped SLA Policy (SlaProcess), attaching a Milestone with criteria, and wiring an Entitlement so Incidents derive an EntityMilestone with a computed TargetDate. Use when the user asks to configure SLA milestones on Incidents, create an SLA policy for Incident records, set up entitlement processes for ITSM, wire milestones so they appear on the Incident page, or enable SLA tracking for incident management. DO NOT TRIGGER when: the user asks about Case entitlements or Case SLA (not Incident), querying existing SLA policies without setup intent, general Entitlement sObject CRUD unrelated to Incident, or Milestone queries for reporting purposes only."
metadata:
  version: "3.4"
  domains: ["Service"]
  minApiVersion: "67.0"
  relatedSkills:
    - "service-itsm-incident-mgmt-configure"
    - "service-itsm-incident-priority-configure"
  accessCheck: []
  mcpTools:
    headless-360:
      tools: ["describe", "discover", "dispatch", "dispatch_readonly"]
      semver: ">=1.0.0"
allowed-tools: |
  Read AskUserQuestion
  mcp__headless-360__discover
  mcp__headless-360__describe
  mcp__headless-360__dispatch
  mcp__headless-360__dispatch_readonly
---

# Configuring Incident SLA (End-to-End)

Configures a complete **Incident SLA pipeline** for Service Cloud ITSM — the chain that derives
an EntityMilestone (with a computed TargetDate) on every Incident that has an Entitlement. Every
operation runs through the **Salesforce-hosted Headless-360 MCP server** (server key `headless-360`)
via its four meta-tools (`discover`, `describe`, `dispatch_readonly`, `dispatch`). The org is derived
from the OAuth JWT — the skill never handles an org id, alias, or credentials. It also needs the
org-level **SLA Management for IT Service** setup item — a Setup Discovery feature plus a separate,
permanent **SLA Versioning** bit, both gated by Phase 0.5. Setup has four parts:

1. **MilestoneType** — define what you're measuring (e.g., "First Response").
2. **SLA Policy** — the SlaProcess scoped to Incident with entry/exit criteria.
3. **Milestone** — attach to the policy with a time trigger and filter criteria.
4. **Entitlement** — wire to an Account so Incidents with that Entitlement engage the SLA.

## Scope

- **In scope**: Creating MilestoneTypes, SLA Policies (SlaProcess), Milestones with criteria,
  Entitlements, and verifying SLA engagement on Incident records — all via `headless-360` MCP.
- **In scope — prerequisite**: checking and (on confirmation) enabling the **SLA Management for IT
  Service** setup item — the feature + SLA Versioning (Phase 0.5).
- **Out of scope**: Case SLA/entitlements; Assignment Rules; Escalation Rules; Notification
  Rules; general Entitlement CRUD not related to Incident SLA; SLA reporting.

---

## Routes at a glance

Reads dispatch through `mcp__headless-360__dispatch_readonly`, writes through
`mcp__headless-360__dispatch`. Both take raw HTTP:
`{"url": "<path>", "method": "GET|POST|PATCH|...", "body"?: {...}, "query_params"?: {...}}` — **not**
`{operation_id, arguments}`. Full request/response shapes live in `references/mcp-invocation.md`.

| Concern | Method + path | Body |
|---------|---------------|------|
| Master Incident Mgmt pref (read) | `GET /services/data/v67.0/connect/setup/discovery/features`, filter `apiName == "service-cloud-itsm-incident"` for `status` | — |
| SLA Mgmt prerequisite (Phase 0.5) | Feature `status`/`enable` + SLA Versioning read/PATCH on `EntitlementSettings` — see `references/mcp-invocation.md` | see ref |
| Preflight (Incident on) | `GET /services/data/v67.0/sobjects/Incident/describe` | — |
| Default BusinessHours | `GET /services/data/v67.0/query` (q via `query_params.q`) | — |
| Create MilestoneType | `POST /services/data/v67.0/connect/sla-management/milestone-types` | `{"name","description","recurrenceType"}` |
| Create SLA Policy | `POST /services/data/v67.0/connect/sla-management/sla-policies` | `{"name","processType":"Incident","businessHourId",...}` |
| Attach Milestone | `POST /services/data/v67.0/connect/sla-management/sla-policies/<id>/milestones` | `{"milestoneTypeId","timeTrigger","milestoneCriteria":[...]}` |
| Create Entitlement | `POST /services/data/v67.0/sobjects/Entitlement` | `{"Name","AccountId","SlaProcessId","BusinessHoursId","StartDate","EndDate"}` |
| Create test Incident | `POST /services/data/v67.0/sobjects/Incident` | `{"Subject","EntitlementId",...}` |
| Verify SLA policy | `GET /services/data/v67.0/query` (q for `SlaProcess`) | — |
| Verify engagement | `GET /services/data/v67.0/query` (q for `EntityMilestone`) | — |

**Response envelope**: SLA Management Connect, `/sobjects/…`, and `/query` are standard REST — the
`dispatch*` MCP tool returns the REST response directly (`{status_code, body}`); read `body`. Only
`/headless/invoke/…` Aura-controller routes are doubly wrapped (`body.body`) — this skill uses none.

---

## Clarifying Questions

Ask only what you cannot infer from conversation context (pre-populate and note "(from
conversation)"). **Resolve the Phase 0.5 gate first, on its own.**

- **Which org?** `headless-360` binds to the current OAuth session; confirm the target before mutating.
- **Milestone strategy?** See Phase 1.4 — skipped when the prompt already names a shape, when the branch is a no-op, or when up-front authorization + a derivable shape are given.
- **Target Account?** Account to attach the Entitlement to.
- **Milestone criteria?** Default `Status != Closed`, plus pattern-specific filters.

Default suggestion: SLA Policy `Incident SLA Policy`, default BusinessHours, first active Account,
Entitlement `today → today + 1 year`, milestone strategy resolved per Phase 1.4.

---

## Workflow

All steps are sequential. **Always read before you write.** Every call goes through
`mcp__headless-360__*` tools.

### Phase 0 — Reuse what the session already knows

Each Phase 1 read below carries a **skip-if-already-known** clause: skip only when the
same fact was produced this session **from a successful `dispatch_readonly` response
tied to the current org**. A user statement is not cache-eligible — a mistaken assertion
would produce a stale create. When the only source is a user statement, re-read.

- **Master Incident Management pref** — reuse only when the pref was read live this
  session (successful `dispatch_readonly` on Setup Discovery, or a live read by
  `service-itsm-incident-mgmt-configure`) AND `status` was `ENABLED` AND no write since.
  A cached "not enabled" / unknown / user-asserted value is NOT cache-eligible — fall
  through to step 1.
- **SLA Management feature + SLA Versioning** — reuse only if both were read live this session
  (Phase 0.5) and unwritten since; else re-run Phase 0.5.
- **Incident describe / SLA-field presence** — if `Incident.describe` was already run against
  the current org this session and the presence of `EntitlementId` / `SlaStartDate` /
  `SlaExitDate` is in context, skip step 3 and reuse the answer.
- **Default BusinessHours id** — if a `BusinessHoursId` for the current org's default is
  already captured, skip step 4.
- **Account id** — if the Account the user named (or the fallback first-active Account)
  was already resolved to an `Id` this session, skip step 5.
- **Discover / describe of SLA Connect operations** — if the routes were already verified
  as indexed this session, skip step 2.

**When in doubt, re-check.** Skip only when the earlier fact is unambiguously in context
AND you have not switched orgs — the `headless-360` MCP session binds to one org via the
JWT, so an org change is only possible if the session was re-authed mid-conversation. If
the user hints at a different org, or you cannot tell which org the earlier fact came
from, re-run the read. A wrong skip on a live org write is worse than a duplicated read.

### Phase 0.5 — SLA Management for IT Service prerequisite gate

**Resolve this gate on its own first — not batched with the clarifying questions. Its reads are
safe to run up front; still confirm the target org before the enable write.** Gate on the
org-level **SLA Management for IT Service** setup item before any Phase 2 mutation — two
independent bits: the Setup Discovery feature `service-cloud-itsm-manage-sla-policies` (Connect route,
**not** Tooling) and the separate, **permanent** **SLA Versioning** bit
(`EntitlementSettings.IsEntitlementVersioningEnabled`). Full call shapes, `enableBlockedReasons`
handling, and the permanence rule are in `references/mcp-invocation.md`.

- **Read both** (`dispatch_readonly`); feature `ENABLED` **and** versioning `true` → skip to Phase 1.
- **Confirm, then enable only what's off** (`AskUserQuestion`) — stop and relay if `enableBlockedReasons`
  is non-empty; if versioning is off, flag it's **permanent**.
- **Enable, then re-read** — never trust the `201` / empty-`204` write response; require `ENABLED` /
  `true` first.

### Phase 1 — Preflight & discovery

**On any `401` / `403` / `404` from a step below, halt and surface the raw error** — the org or client is not configured correctly. `401` → MCP auth (ECA not propagated / expired token). `403` → user perm missing OR ITSM Incident Management license/preference missing (`ITSMIncidentMgmtEnabled` / `IncidentMgmt.orgHasITSMOrgPermission`). `404` → `headless-360` server not activated OR Entitlement Management not enabled for Incident.

1. **Master Incident Management pref — direct read** *(skip conditions in Phase 0)*.
   `dispatch_readonly` on `GET /services/data/v67.0/connect/setup/discovery/features`,
   filter `features[]` client-side to `apiName == "service-cloud-itsm-incident"`, read
   `status`. If `ENABLED`, proceed. **If not, delegate to `service-itsm-incident-mgmt-configure`
   inline to enable** (it runs its own confirm-to-write), then re-read to verify. If the
   user declines, halt — every SLA artifact below depends on the master being on. Full
   call shape + why the setup-org-preferences endpoint 404s here is in
   `references/mcp-invocation.md` (Preflight A).
2. **Discover the Connect operations** — *(skip if already verified this session — see Phase 0)*.
   `mcp__headless-360__discover(query="sla-management milestone")` to confirm the SLA Management
   Connect API is indexed, then `mcp__headless-360__describe(id=<operation_id>)`
   for the `milestone-types`, `sla-policies`, and `sla-policies/{id}/milestones` POST operations to pull
   their exact input schemas + HTTP routes. If `discover` returns nothing after rewording the query,
   the corpus does not index this surface for the org — direct the user to **Setup → SLA/Entitlement
   setup** and stop.
3. **Verify Incident Management + SLA fields** — *(skip if `Incident.describe` result for the
   current org is already in context — see Phase 0)*. Otherwise `dispatch_readonly` on
   `GET /services/data/v67.0/sobjects/Incident/describe` and confirm `fields[]` includes
   `EntitlementId`, `SlaStartDate`, `SlaExitDate`. If the describe 404s or fields are missing, direct
   the user to enable Entitlement Management for Incident and stop.
4. **Find default BusinessHours** — *(skip if `BusinessHoursId` for the current org's default is
   already captured this session)*. Otherwise `dispatch_readonly` on `GET /services/data/v67.0/query` with
   `query_params.q="SELECT Id, Name FROM BusinessHours WHERE IsActive = true AND IsDefault = true"`.
   If `body.records` is empty, stop with a message to create default Business Hours in Setup. Capture
   `BusinessHoursId`.
5. **Resolve the target Account** — *(skip if the Account the user named — or, absent a name,
   the fallback first-active Account — is already resolved to an Id this session)*. Otherwise the
   Entitlement in Phase 2 requires an `AccountId`, so resolve it now, before any mutation. If the
   user named an Account, look it up by name via a `dispatch_readonly`
   SOQL: `SELECT Id, Name FROM Account WHERE Name = '<escaped name>' LIMIT 1`. If the named Account is
   not found, **stop and ask** — do NOT silently substitute a different Account. Only when the user
   did **not** name one, fall back to the first active Account
   (`SELECT Id, Name FROM Account WHERE IsDeleted = false ORDER BY CreatedDate LIMIT 1`) and surface
   which Account you chose in the confirmation gate below. If no Account exists at all, stop with a
   message to create one first. Capture `AccountId` and the Account name.
6. **Read existing SLA artifacts (idempotency probe)** — `dispatch_readonly` SOQL against
   `SlaProcess` by name (`SELECT Id, Name FROM SlaProcess WHERE Name = '<name>' AND SObjectType = 'Incident' LIMIT 1` — the physical sObject field is `SObjectType`; `ProcessType` returns `INVALID_FIELD`),
   `MilestoneType` by name for each type the strategy would create, `SlaMilestone` under the matched
   `SlaProcess`, and `Entitlement` by name against the resolved Account. Record which artifacts
   already exist. If **every** artifact the request would create already exists with the requested
   configuration, Phase 1.4 skip condition (b) applies — set `noOp=true` and skip Phase 1.4 and
   Phase 2. Any missing or divergent artifact means a mutation is required; proceed to Phase 1.4.

### Phase 1.4 — Milestone Strategy

Every SLA policy needs at least one milestone. Load `examples/milestone-patterns.md` — it lists the
Phase 1.4 skip conditions (concrete shape in prompt, idempotent no-op, explicit up-front
authorization) and the five strategy options (Single, Response + Resolution, Priority-tiered,
Escalation ladder, Custom/mixed) with their `AskUserQuestion` prompt, default numbers, and
MilestoneType-reuse rules. Skip conditions (c) still requires Phase 1.5 plan-narration before
dispatch. Multi-milestone selection expands to N milestone creates in Phase 2 step 10 (one POST per
milestone, `order` 1..N, all attached to the same SlaProcess).

### Phase 1.5 — Confirm before mutating

7. **Confirm the plan** — present the resolved configuration (target **org**, **SLA Policy** name,
   resolved **Account** name, **Entitlement** date range, and the **full per-milestone list** from
   Phase 1.4 — never collapse Priority-tiered / Custom to "N milestones").

   **Skip the `AskUserQuestion` confirmation prompt** (still narrate the plan before dispatch)
   when: up-front authorization was granted (note `(authorized in prompt)`); the branch is a no-op
   (skip Phase 1.5 + Phase 2, report the no-op); or the plan was already confirmed in conversation
   (note `(confirmed in conversation)`). Otherwise dispatch `AskUserQuestion` and require an
   explicit "yes" before Phase 2. Everything before this step is read-only; everything after
   mutates the org.

### Phase 2 — Create SLA Artifacts (exact order — each depends on the previous)

8. **Create MilestoneType(s)** — `POST /connect/sla-management/milestone-types`. One POST per
   distinct MilestoneType required by the strategy. Reuse a single MilestoneType across milestones
   that share a name (Priority-tiered "First Response" reuses one MilestoneType across all four
   milestones); create separate MilestoneTypes for distinct concerns (Response + Resolution =
   two MilestoneTypes; Escalation ladder = three). Capture each `id`.
9. **Create SLA Policy** — `POST /connect/sla-management/sla-policies` with `processType='Incident'`
   and the `businessHourId` from Phase 1. Capture `id`. **The response echoes nulls — verify via
   SOQL, not the response body.**
10. **Attach Milestone(s)** — load the request-body template from `assets/attach-milestone.json`
    and, for each milestone in the strategy, populate `milestoneTypeId`, `timeTrigger`, `order`
    (1..N in the strategy's order) and any per-pattern `filterItems` additions from
    `examples/milestone-patterns.md`, then `POST /connect/sla-management/sla-policies/<slaId>/milestones`.
    `milestoneCriteria` is mandatory (`filterType: RuleFilter`). Do **not** put `slaProcessId` in the
    body — it is carried by the path. Multi-milestone strategies dispatch this call once per
    milestone; if any milestone POST fails, halt and surface the raw error — do not continue with a
    half-attached policy.
11. **Create Entitlement** — `POST /sobjects/Entitlement` linking the resolved Account (from Phase 1
    step 5), the SLA Policy (`SlaProcessId`), and Business Hours. For immediate engagement, backdate
    `StartDate` to yesterday.

### Phase 3 — Verify

12. **Verify the SLA Policy** — SOQL on `SlaProcess` (do not trust the create response).
13. **Create a test Incident** with `EntitlementId` pointing at the new Entitlement. For
    Priority-tiered strategies, set a specific `Priority` on the test Incident (or create one test
    Incident per Priority) so at least one milestone's criteria matches — otherwise no
    `EntityMilestone` will spawn even though the policy is wired correctly.
14. **Verify engagement** — SOQL confirming `Incident.SlaStartDate` is populated and the expected
    `EntityMilestone` row(s) exist with the correct `TargetDate`(s). For multi-milestone
    strategies, expect one `EntityMilestone` per milestone whose criteria the Incident satisfies.
15. **Report results** using the output format below.

---

## Rules / Constraints

| Constraint | Rationale |
|-----------|-----------|
| Gate on **SLA Management for IT Service** first (Phase 0.5) — feature `ENABLED` AND versioning `true`; confirm before enabling, versioning permanent, re-read after each write | Skipping risks a mid-flow 403/404; versioning can't be undone; writes don't confirm state |
| Discover + describe before any mutation | Catches a missing SLA surface / disabled Incident Management early |
| Ask (via `AskUserQuestion`) which milestone strategy to use — do not silently default to Single | Real ITSM policies almost always have more than one milestone; picking silently hides the choice from the user |
| Reuse one MilestoneType per shared name; create a distinct MilestoneType per distinct concern | The runtime keys milestones by MilestoneType — sharing collapses distinct concerns |
| For multi-milestone strategies, halt on any milestone POST failure — do not continue with a half-attached policy | The confirmation gate covers all N milestones together; partial attach diverges from the confirmed plan |
| Priority-tiered strategy: validate every `Priority` value against the live Incident picklist before dispatch | The server accepts any string on `filterItems.value` — an unknown Priority value silently makes the milestone dead code |
| Entitlement is standard sObject DML (not Connect API); `StartDate` controls status (future = Inactive) | Not part of the `/connect/sla-management/` surface |
| Verify SLA Policy via SOQL, not the create response | The create response echoes nulls |
| Never show Salesforce record IDs to the user | Use human-readable names and IncidentNumber |

Additional API quirks (payload rules, filter-operator enum, missing-criteria error) are documented in `references/mcp-invocation.md` — consult before dispatch.

---

## Verification Checklist

- [ ] **SLA Management prerequisite gated (Phase 0.5)** — feature `ENABLED` AND `IsEntitlementVersioningEnabled` `true`; whatever was off was enabled only after confirmation (versioning flagged permanent) and re-read to verify, never trusting the write response; non-empty `enableBlockedReasons` halted the run.
- [ ] Master Incident Management pref was confirmed `ENABLED` via a live Setup Discovery read this session (or via an inline delegation to `service-itsm-incident-mgmt-configure` when it came back off). A user-asserted state is NOT a substitute for the live read.
- [ ] `discover` + `describe` (or the Incident describe) confirmed the SLA Management Connect operations.
- [ ] Incident describe returned 200 with `EntitlementId`, `SlaStartDate`, `SlaExitDate`.
- [ ] Default BusinessHours found.
- [ ] **Milestone strategy resolved** — via a Phase 1.4 skip condition (prompt named a shape / no-op branch / up-front authorization + derivable shape) OR via `AskUserQuestion`. A skipped `AskUserQuestion` under a valid skip condition is honoring the contract, not violating it. For Priority-tiered / Custom, every `Priority` / criteria value was validated against the live Incident picklist before dispatch.
- [ ] **Configuration confirmed OR skip condition met** — up-front authorization, no-op branch, prior confirmation in conversation, OR explicit "yes" via `AskUserQuestion`. In every case, the resolved plan (org, SLA name, account, entitlement range, per-milestone list) was narrated before Phase 2 dispatched.
- [ ] Artifacts created in order (MilestoneType(s) → Policy → Milestone(s) → Entitlement); each POST returned 201; any milestone POST failure halted the run (no partial attach). Trivially satisfied on no-op runs.
- [ ] SLA Policy verified via SOQL (not the create response). On no-op runs, the Phase-1 read is the verification.
- [ ] Test Incident has `SlaStartDate` populated (Priority chosen to match at least one criterion for Priority-tiered). Skip on no-op runs.
- [ ] At least one EntityMilestone exists with the correct TargetDate; for multi-milestone strategies, the expected milestone(s) are present. Skip on no-op runs.
- [ ] Before/after and summary shown. On no-op runs, the summary states the pre-existing configuration verbatim and reports "no changes made".

---

## Output Format

See `examples/output-templates.md` for the canonical failure / single-milestone success / multi-milestone success templates. Fill in the placeholders as-is. No record IDs in user-facing output. No files are produced — the skill mutates org configuration in place through headless-360 MCP dispatch.

---

## Reference File Index

| File | When to read |
|------|--------------|
| `references/mcp-invocation.md` | Every phase — exact `mcp__headless-360__*` call shapes, payload templates, response envelope, discovery, and gotchas (filter-operator enum, v67 routes, entitlement behavior) |
| `examples/milestone-patterns.md` | Phase 1.4 — the five milestone strategies (Single, Response + Resolution, Priority-tiered, Escalation ladder, Custom) with default times, criteria, MilestoneType reuse rules, and per-pattern filter-item extensions |
| `examples/output-templates.md` | Output Format — canonical failure / single-milestone success / multi-milestone success templates |
| `assets/attach-milestone.json` | Phase 2 step 10 — reusable request-body template for `POST /connect/sla-management/sla-policies/<slaId>/milestones`; substitute `milestoneTypeId`, `businessHoursId`, `timeTrigger`, `order`, and append per-pattern `filterItems` |

---

## Related Skills

This skill configures the end-to-end **Incident SLA** pipeline. Configuring the priority matrix
(Impact × Urgency → Priority) is a separate concern handled by
`service-itsm-incident-priority-configure` — if a Priority-tiered milestone strategy is requested
but the org's `Incident.Priority` picklist is missing values, direct the user to that skill first.
Other adjacent ITSM setup flows (Major Incident Management, custom fields on Incident / Problem /
ChangeRequest) are out of scope; use their dedicated skill when available.

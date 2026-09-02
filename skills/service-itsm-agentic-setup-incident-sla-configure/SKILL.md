---
name: service-itsm-agentic-setup-incident-sla-configure
description: "End-to-end Incident SLA setup for Service Cloud ITSM — creating a MilestoneType, an Incident-scoped SLA Policy (SlaProcess), attaching a Milestone with criteria, and wiring an Entitlement so Incidents derive an EntityMilestone with a computed TargetDate. Use when the user asks to configure SLA milestones on Incidents, create an SLA policy for Incident records, set up entitlement processes for ITSM, wire milestones so they appear on the Incident page, or enable SLA tracking for incident management. DO NOT TRIGGER when: the user asks about Case entitlements or Case SLA (not Incident), querying existing SLA policies without setup intent, general Entitlement sObject CRUD unrelated to Incident, or Milestone queries for reporting purposes only."
metadata:
  version: "3.6"
  domains: ["Service"]
  minApiVersion: "67.0"
  relatedSkills:
    - "service-itsm-incident-mgmt-configure"
    - "service-itsm-incident-priority-configure"
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

Configures a complete **Incident SLA pipeline** for Service Cloud ITSM — the chain that derives an
EntityMilestone (with a computed TargetDate) on every Incident with an Entitlement. Every operation
runs through the Salesforce-hosted **`headless-360`** MCP server; the org is derived from the OAuth
JWT — the skill never handles an org id, alias, or credentials. It also needs the org-level **SLA Management for IT
Service** setup item (the Phase 0.5 gate — see below). Setup has four parts:
**MilestoneType** (what you measure) → **SLA Policy** (SlaProcess scoped to Incident, entry/exit
criteria) → **Milestone** (time trigger + filter criteria) → **Entitlement** (wired to an Account so
Incidents engage the SLA).

## Scope

- **In scope**: Creating MilestoneTypes, SLA Policies (SlaProcess), Milestones with criteria,
  Entitlements, and verifying SLA engagement on Incident records — all via `headless-360` MCP.
- **In scope — prerequisite**: checking and (on consent) enabling **SLA Management for IT Service**
  (Phase 0.5); halts if not fully enabled or consent declined.
- **In scope — predefined vs custom** (Phase 0.6): offering the OOB *Standard Support for Incidents*
  policy (Incident only) vs a custom one.
- **Out of scope**: Case SLA/entitlements; Assignment Rules; Escalation Rules; Notification
  Rules; general Entitlement CRUD not related to Incident SLA; SLA reporting.

---

## Routes at a glance

Reads → `mcp__headless-360__dispatch_readonly`, writes → `mcp__headless-360__dispatch`. Both take raw
HTTP: `{"url","method","body"?,"query_params"?}` — **not** `{operation_id, arguments}`. **Response
envelope**: standard REST — read `body` from `{status_code, body}`. The full route table — create
MilestoneType / SLA Policy / Milestone, Entitlement, BusinessHours, test Incident, the Phase 0.5
feature calls, and the `create-milestone-action` op — with request/response shapes lives in
`references/mcp-invocation.md`.

---

## Clarifying Questions

Ask only what you cannot infer from context (pre-populate; note "(from
conversation)"). **Resolve the Phase 0.5 gate first.**

- **Which org?** `headless-360` binds to the current OAuth session; confirm the target before mutating.
- **Milestone strategy?** See Phase 1.4 (skipped per its skip conditions).
- **Target Account?** For the Entitlement.
- **Milestone criteria?** Default `Status != Closed`, plus pattern-specific filters.

Default suggestion: SLA Policy `Incident SLA Policy`, default BusinessHours, the Account the user
picks, Entitlement `today → today + 1 year`, milestone strategy resolved per Phase 1.4.

---

## Workflow

All steps are sequential. **Always read before you write.** Every call goes through
`mcp__headless-360__*` tools.

### Phase 0 — Reuse what the session already knows

Each Phase 1 read carries a **skip-if-already-known** clause: skip only when the same fact was
produced **this session** by a successful `dispatch_readonly` on the current org and unwritten since —
a user statement is never cache-eligible. Cacheable: master Incident Mgmt pref (step 1, only if
`ENABLED`), SLA feature + Versioning (Phase 0.5), Incident describe (3), `BusinessHoursId` (4), Account
id (5), SLA Connect ops indexed (2). **When in doubt, re-check** — a wrong skip on a live write is
worse than a re-read.

### Phase 0.5 — SLA Management for IT Service prerequisite gate

**Resolve this gate first, on its own. Reads are safe up front; confirm the org before any write.**
"SLA Management for IT Service" is enabled only when **both** Simplified SLA Setup (feature
`service-cloud-itsm-manage-sla-policies`) **and** SLA Versioning
(`EntitlementSettings.IsEntitlementVersioningEnabled`) are on; either off → not enabled. The one
feature-`enable` turns on both, **permanently** enabling versioning — inseparable. Shapes /
`enableBlockedReasons` / ack wording: `references/mcp-invocation.md`.

- **Read both** (`dispatch_readonly`); proceed to Phase 0.6 **only when both are on**.
- **On an OFF org, read the master license first** (Phase 1 step 1, `service-cloud-itsm-incident`):
  `NOT_AVAILABLE` → **HALT** — don't flip the permanent Versioning switch where Incident SLA can't run.
- **Two separate `AskUserQuestion` acks — never merge.** (a) master Incident Mgmt `NOT_ENABLED` → ask
  to enable it first (reversible, no permanence warning). (b) a *distinct* permanence ack: enabling
  **SLA Management** turns on **SLA Versioning**, which **can't be turned off** (the feature disables
  later but Versioning stays on). Offer **enable**/**stop** — no "versioning-off"; a bare "enable SLA"
  is **not** consent.
- **Decline (b), non-empty `enableBlockedReasons`, or a re-read mismatch → HALT** — enable no SLA
  Mgmt/Versioning, don't proceed to Phase 0.6/1 (a reversible master enable from (a) stands). **After
  any write, re-read both and report the REAL state** — never trust `201`/`204`.

### Phase 0.6 — Predefined (OOB) vs Custom

Once the gate passes, offer the OOB policy **before** any custom-flow questions. **Incident only.**

1. **Prerequisite + detect.** Confirm master Incident Mgmt pref `ENABLED` (Phase 1 step 1). Then `dispatch_readonly` `GET /connect/sla-management/sla-policies` with
   `query_params.processTypes=Incident`; match display name **"Standard Support for Incidents"**.
   - **Already present** → **no re-seed** (no idempotency), no custom upsell; report it is seeded.
     **If warn/escalate actions were requested → resolve the named existing milestones → Phase 2.5 →
     Phase 3 verify → STOP** (attach actions even though the policy was already seeded).
2. **Fork** — one `AskUserQuestion`, **Predefined listed first / recommended**: use Salesforce's
   predefined Incident SLA policy (*Standard Support for Incidents* — priority-tiered milestones)
   **or** build a custom one. One-way note: predefined seeds an
   **active** policy + Entitlement, no un-seed path (manual delete only).
   - **Predefined →** resolve BusinessHours + Account (Phase 1 steps 4–5) → **Phase 2-OOB** → **Phase
     2.5** (if actions requested) → Phase 3 verify → **STOP**.
   - **Custom →** existing Phase 1 → 1.4 → 1.5 → 2 → 3, unchanged.

**MUST read `references/mcp-invocation.md` (Predefined Incident Policy) before seeding.**

### Phase 1 — Preflight & discovery

**On any `401` / `403` / `404` from a step below, halt and surface the raw error** — the org/client is misconfigured. `401` → MCP auth (ECA not propagated / expired token). `403` → user perm OR ITSM Incident Management license/pref missing (`ITSMIncidentMgmtEnabled` / `IncidentMgmt.orgHasITSMOrgPermission`). `404` → `headless-360` not activated OR Entitlement Management not enabled for Incident.

1. **Master Incident Management pref — direct read** *(skip conditions in Phase 0)*.
   `dispatch_readonly` `GET .../connect/setup/discovery/features`, filter `features[]` to the **exact**
   `apiName == "service-cloud-itsm-incident"` — never a look-alike (`service-cloud-incident-management`
   is generic Case-based Incident Management, not our target). Read `status`: `ENABLED` → proceed;
   `NOT_AVAILABLE` (license missing) → **halt and surface it** — cannot be enabled here, no delegate/ack;
   `NOT_ENABLED` → **explicit `AskUserQuestion` ack first (never auto-enable as an implied SLA
   dependency)**, then delegate to `service-itsm-incident-mgmt-configure` inline (confirms-to-write) and
   re-read; if declined, halt — every SLA artifact below depends on the master being on. Full shape + why
   setup-org-preferences 404s here: `references/mcp-invocation.md` (Preflight A).
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
5. **Resolve the target Account** — *(skip if already resolved this session)*. Phase 2's Entitlement
   needs an `AccountId`. If the user **named** one → look up (`SELECT Id, Name FROM Account WHERE Name
   = '<escaped>' LIMIT 1`); not found → **stop and ask**, never substitute. If the user **authorized
   any/existing Account** → pick the most recently active (`... WHERE IsDeleted = false ORDER BY
   LastModifiedDate DESC LIMIT 1`) and **surface which** in the plan. Otherwise → **ask via
   `AskUserQuestion`**: list real candidates by **name only** + "type a name"; **never auto-pick,
   pre-select, or expose an internal sort key** (e.g. recency). If none exists, stop. Capture `AccountId` + name.
6. **Read existing SLA artifacts (idempotency probe)** — `dispatch_readonly` SOQL for `SlaProcess` by
   name (`... WHERE Name = '<name>' AND SobjectType = 'Incident'` — the field is `SobjectType`;
   `ProcessType` returns `INVALID_FIELD`), each `MilestoneType` the strategy would create,
   `SlaMilestone` under the matched policy, and `Entitlement` by name on the resolved Account. If
   **every** artifact already exists with the requested config, set `noOp=true` and skip Phase 1.4 +
   Phase 2 (skip condition (b)); any missing/divergent artifact → proceed to Phase 1.4.

### Phase 1.4 — Milestone Strategy

Every SLA policy needs at least one milestone. Load `examples/milestone-patterns.md` — it lists the
skip conditions (concrete shape in prompt / idempotent no-op / explicit up-front authorization) and
the five strategy options with their `AskUserQuestion` prompt, defaults, and MilestoneType-reuse
rules. Skip condition (c) still requires Phase 1.5 plan-narration before dispatch. Multi-milestone
selection expands to N creates in Phase 2 step 10 (one POST per milestone, `order` 1..N, same SlaProcess).

### Phase 1.5 — Confirm before mutating

7. **Confirm the plan** — present the resolved config (target **org**, **SLA Policy** name, resolved
   **Account** name, **Entitlement** date range, and the **full per-milestone list** — never collapse
   Priority-tiered / Custom to "N milestones"). **Skip the `AskUserQuestion`** (but still narrate the
   plan before dispatch) when up-front authorization was granted (note `(authorized in prompt)`), the
   branch is a no-op, or it was already confirmed in conversation (note `(confirmed in conversation)`);
   otherwise require an explicit "yes" before Phase 2. Everything before this step is read-only;
   everything after mutates the org.

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
    Each `milestoneCriteria[]` item needs `milestoneAgreementType` (`SLA`/`OLA`) and
    `filterType: RuleFilter`. Do **not** put `slaProcessId` in the body — carried by the path.
    Multi-milestone strategies dispatch once per milestone; on any milestone POST failure, halt
    and surface the raw error — do not continue with a half-attached policy.
11. **Create Entitlement** — `POST /sobjects/Entitlement` linking the resolved Account (from Phase 1
    step 5), the SLA Policy (`SlaProcessId`), and Business Hours. For immediate engagement, backdate
    `StartDate` to yesterday.

### Phase 2-OOB — Seed the Predefined Incident Policy

Reached only from Phase 0.6 Predefined (replaces Phase 1.4/1.5/2). Follow the seed recipe
in `references/mcp-invocation.md` (**Predefined Incident Policy**) with the template in
`assets/predefined-incident-policy.json` — it uses the **Phase 2 routes** (2 MilestoneTypes → SLA
Policy `active:true` → 8 priority-tiered milestones → Entitlement), validates each `Priority`/`Status`
against the live picklist, and avoids the Connect activate PATCH. Then run **Phase 2.5** (if actions
requested), then **Phase 3** (Critical test Incident), and **STOP** — no *proactive* custom offer.

### Phase 2.5 — Milestone Actions (optional: Warn / Escalate)

After milestones exist (Phase 2 or 2-OOB), **only if** the user asked to warn/escalate/notify: apply
the requested checkpoint(s) to **every milestone the user named** (not just one), computing each
offset from that milestone's own target. Map "warn at X%" → an offset *before* target, "on breach" →
*at/after* it; **confirm the full set before writing** (up-front auth waives the re-ask; narrate it
regardless — no headless delete), then, per milestone, delegate to headless
**`create-milestone-action`** (`discover` → `describe` → `dispatch`). **Confirm each from the response
body** (`success` + non-empty `actionMappings`; a *timed* checkpoint also returns a `triggerId`), never
the `201`. Formula, roles, proven body, defaults, and the IST business-hours note:
`references/mcp-invocation.md` (Milestone Actions).

### Phase 3 — Verify

12. **Verify the SLA Policy** — SOQL on `SlaProcess` (do not trust the create response).
13. **Create a test Incident** with `EntitlementId` set to the new Entitlement. For Priority-tiered
    strategies, set a `Priority` that matches at least one milestone's criteria (or one test Incident
    per Priority) — otherwise no `EntityMilestone` spawns even with the policy wired correctly.
14. **Verify engagement** — SOQL confirming `Incident.SlaStartDate` is populated and the expected
    `EntityMilestone` row(s) exist with correct `TargetDate`(s) — one per milestone whose criteria
    the Incident satisfies.
15. **Report results** using the output format below.

---

## Rules / Constraints

| Constraint | Rationale |
|-----------|-----------|
| Gate on **SLA Management for IT Service** first (Phase 0.5) — one enable turns on the feature **and**, one-way, **SLA Versioning**; **two separate acks (master, then permanence) — never merged**; decline / blocked / verify-fail → **HALT, no fall-through**; re-read + report real state | Versioning can't be undone; writes don't confirm state |
| Offer the **predefined (OOB)** policy first (Phase 0.6, Incident only); detect before seed; if chosen, seed → verify → **STOP** (no custom upsell) | OOB seed has no server idempotency (re-seeding duplicates) |
| Discover + describe before any mutation | Catches a missing SLA surface / disabled Incident Management early |
| Ask (via `AskUserQuestion`) which milestone strategy to use — don't silently default to Single | Real ITSM policies usually have >1 milestone; a silent default hides it |
| Reuse one MilestoneType per shared name; create a distinct one per distinct concern | The runtime keys milestones by MilestoneType — sharing collapses distinct concerns |
| For multi-milestone strategies, halt on any milestone POST failure (no half-attached policy) | Partial attach diverges from the confirmed plan |
| Priority-tiered: validate every `Priority` value against the live Incident picklist before dispatch | The server accepts any string on `filterItems.value` — an unknown value silently makes the milestone dead code |
| Entitlement is standard sObject DML (not Connect API); `StartDate` controls status (future = Inactive) | Not part of the `/connect/sla-management/` surface |
| Verify SLA Policy via SOQL, not the create response | The create response echoes nulls |
| Never show record IDs **in any message, incl. interim narration** — the test Incident by **IncidentNumber**, milestones by **MilestoneType name**, never the 15/18-char Id; keep `AskUserQuestion` labels customer-facing (no "demo", "the skill", internal defaults) | Leaked Ids and internal/demo framing look unprofessional |

Additional API quirks (payload rules, operator enum, missing-criteria error): `references/mcp-invocation.md`.

---

## Verification Checklist

- [ ] **SLA Management gated (Phase 0.5)** — feature + SLA Versioning both on, only after the **permanence ack** (separate from the master ack); reported state matches a re-read, not the write. If it couldn't be enabled (declined / blocked / verify-fail), the run **HALTED** before Phase 0.6/1 — no artifacts.
- [ ] **Predefined vs Custom offered (Phase 0.6)** — with the feature ON, the OOB *Standard Support for Incidents* policy was offered first; if it existed, reported not re-seeded; if chosen, seeded (2 MilestoneTypes + 8 tiered milestones + Entitlement), verified, **no** custom offer followed.
- [ ] Master Incident Mgmt pref (exact `service-cloud-itsm-incident`) confirmed `ENABLED` via a live read, or delegated to `service-itsm-incident-mgmt-configure` when `NOT_ENABLED` (`NOT_AVAILABLE` → HALT) — not a user assertion, not a look-alike.
- [ ] `discover`/`describe` (or the Incident describe) confirmed the SLA Connect operations.
- [ ] Incident describe returned 200 with `EntitlementId`, `SlaStartDate`, `SlaExitDate`.
- [ ] Default BusinessHours found.
- [ ] **Milestone strategy resolved** — via a Phase 1.4 skip condition OR `AskUserQuestion`; for Priority-tiered / Custom, every `Priority`/criteria value was validated against the live Incident picklist before dispatch.
- [ ] **Configuration confirmed OR skip condition met** (up-front authorization / no-op / prior confirmation / explicit "yes"); the resolved plan (org, SLA name, account, entitlement range, per-milestone list) was narrated before Phase 2.
- [ ] Artifacts created in order (MilestoneType(s) → Policy → Milestone(s) → Entitlement); each POST 201; any milestone POST failure halted the run (no partial attach). Trivial on no-op runs.
- [ ] **Milestone actions (Phase 2.5)** — if requested, attached to **every** named milestone; each confirmed from `body.success` + `actionMappings`, not the `201`; full set narrated before write.
- [ ] SLA Policy verified via SOQL, not the create response (on no-op, the Phase-1 read is the verification).
- [ ] Test Incident has `SlaStartDate` populated (Priority chosen to match a criterion for Priority-tiered) and ≥1 EntityMilestone with the correct TargetDate; expected milestone(s) present for multi-milestone. Skip on no-op.
- [ ] Before/after + summary shown; on no-op, the summary states the pre-existing configuration verbatim and reports "no changes made".

---

## Output Format

See `examples/output-templates.md` for the canonical failure / single-milestone success / multi-milestone success templates. Fill in the placeholders as-is. No files are produced — the skill mutates org configuration in place through headless-360 MCP dispatch.

---

## Reference File Index

| File | When to read |
|------|--------------|
| `references/mcp-invocation.md` | Every phase — exact `mcp__headless-360__*` call shapes, payload templates, response envelope, discovery, and gotchas (filter-operator enum, v67 routes, entitlement behavior) |
| `examples/milestone-patterns.md` | Phase 1.4 — the five milestone strategies with default times, criteria, MilestoneType reuse rules, and per-pattern filter-item extensions |
| `examples/output-templates.md` | Output Format — canonical failure / single-milestone success / multi-milestone success templates |
| `assets/attach-milestone.json` | Phase 2 step 10 — request-body template for the milestone POST (`sla-policies/<slaId>/milestones`); substitute `milestoneTypeId`, `businessHoursId`, `timeTrigger`, `order`; append per-pattern `filterItems` |
| `assets/predefined-incident-policy.json` | Phase 0.6 / Phase 2-OOB — the OOB *Standard Support for Incidents* seed template (policy + 2 MilestoneTypes + 8 priority-tiered milestones) |
| `assets/attach-milestone-action.json` | Phase 2.5 — Warn/Escalate milestone-action body templates (Field Update); pair with `references/mcp-invocation.md` (Milestone Actions) |

---

## Related Skills

The priority matrix (Impact × Urgency → Priority) is separate — `service-itsm-incident-priority-configure`;
if a Priority-tiered strategy is requested but `Incident.Priority` is missing values, direct the user
there first. Other adjacent ITSM flows (Major Incident Mgmt, custom fields on Incident/Problem/ChangeRequest)
are out of scope.

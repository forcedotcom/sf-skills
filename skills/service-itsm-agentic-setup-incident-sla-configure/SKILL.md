---
name: service-itsm-agentic-setup-incident-sla-configure
description: "End-to-end Incident SLA setup for Service Cloud ITSM — the policy's Business Hours (reuse a named schedule, or create one from described hours or a time zone), MilestoneTypes, an Incident-scoped SLA Policy (SlaProcess), Milestones with criteria, and the Entitlement so Incidents get an EntityMilestone with a computed TargetDate. Use when the user asks to create or set up an Incident SLA policy (predefined or custom, with or without specific business hours), configure SLA milestones on Incidents, set up entitlement processes for ITSM, or enable SLA tracking for incident management. For Incidents, use this instead of the single-step SLA policy, milestone, or activation skills. DO NOT TRIGGER when: the user asks about Case entitlements or Case SLA (not Incident), querying existing SLA policies without setup intent, general Entitlement sObject CRUD unrelated to Incident, or Milestone queries for reporting purposes only."
metadata:
  version: "3.10"
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
  Read
  AskUserQuestion
  mcp__headless-360__discover
  mcp__headless-360__describe
  mcp__headless-360__dispatch
  mcp__headless-360__dispatch_readonly
---

# Configuring Incident SLA (End-to-End)

Configures a complete **Incident SLA pipeline** for Service Cloud ITSM — the chain deriving an
EntityMilestone (with a computed TargetDate) on every Incident with an Entitlement, all via the
Salesforce-hosted **`headless-360`** MCP server (org from the OAuth JWT). Requires the org-level
**IT Service Management enablement** (the Phase 1a gate) and **SLA Management for IT Service**
setup item (the Phase 1b gate).
The custom pipeline (four ordered writes): **MilestoneType** (what you measure) → **SLA Policy**
(SlaProcess, Incident-scoped, created inactive, entry/exit criteria) → **Milestone** (time trigger +
criteria) → **activate the policy** (`createEntitlement=true`, which auto-provisions the Entitlement —
matching Incidents then engage the SLA **per-Incident via `EntitlementId`**, with no Account). An
org-wide auto-apply **entitlement criterion** is an *optional* fifth write, dispatched **only** on an
explicit always-match request (Phase 4A step 6) — never by default. (The predefined/OOB
seed fork differs — it does none of this by hand: a single seed call provisions the whole active
bundle — policy, milestones, and Entitlement — in one shot; see Phase 2 / Phase 4B.)
This skill owns all the Incident-SLA **interaction** (gates, forks, milestone strategy,
verification); the raw **write** operations are **delegated to the approved SLA
leaf capabilities** (`csp-sun/MilestoneTypes`, `create-sla-policy`, `create-milestone`,
`create-milestone-action`, `activate-sla-policy`, `create-entitlement-criteria`), which own the
approved Connect contracts — discover → describe → dispatch each rather than re-deriving its shape here.
The Phase 1b **enable** (+ Versioning) and Phase 4B **seed** writes delegate to
**`itsm-shakti/SLASettings`** (owns the SLA-Management settings surface) — same discover → describe → dispatch.

## Scope

- **In scope**: the SLA artifacts above (MilestoneTypes, the SLA Policy and its milestones,
  activation with its auto-provisioned Entitlement, and — only on an explicit org-wide always-match
  request — the optional auto-apply criterion) + verifying SLA
  engagement on Incident records; gating
  **SLA Management for IT Service** (Phase 1b); offering the OOB *Standard Support for Incidents*
  policy vs a custom one (Phase 2, Incident only) — all via `headless-360` MCP.
- **Out of scope**: Case SLA/entitlements; Assignment Rules; Escalation Rules; Notification
  Rules; general Entitlement CRUD not related to Incident SLA; SLA reporting.

---

## Output contract — applies to EVERY message

**Never print a raw Salesforce record Id** (15/18-char: `55…`, `550…`, `0ny…`, `00…`, Account `001…`) — full **or
masked** (`557VW…R3XVYA0` still leaks) — in **any** user-facing text: interim narration *and* the
final report. Holds for artifacts you **created** *and* ones you **detected/reused** — name each (the
name you supplied on create, or matched on reuse), keep its Id internal (chaining only). Verifying or
matching via SOQL? Report the **verified attributes/name**, never the Id you queried by. **Looking *up*
an Id is the same rule** — resolving **Business Hours** (resolved, user-selected, or created in Phase 4A step 1) or an existing policy returns
`{Id, Name}`; narrate the resolved **name only** and keep the returned Id internal — **never** echo it
back as `Resolved "<name>" (001VW…)`. One
exception: on a **halt** you may relay the raw error body verbatim even if it embeds an Id —
don't hand-edit it.

- **Wrong:** `SLA policy created (552VW…)` · `Incident created (0ny…)` · `First Response → 557VW…R3XVYA0` (reuse)
- **Right:** `Created SLA policy "Standard Support for Incidents"` · `reusing the existing First Response
  milestone type` · the test Incident is "the test Incident" until Phase 6, then its `IncidentNumber`;
  milestones by `MilestoneType` name.

---

## Routes at a glance

Reads → `mcp__headless-360__dispatch_readonly`, writes → `mcp__headless-360__dispatch`. Both take raw
HTTP `{"url","method","body"?,"query_params"?}` — **not** `{operation_id, arguments}`; read `body`
from `{status_code, body}`. Full route table with request/response shapes: `references/mcp-invocation.md`.

---

## Clarifying Questions

Ask only what you cannot infer from context (pre-populate; note "(from conversation)"). **Resolve the
Phase 1a and Phase 1b gates first, in that order.** Then: **which org?** (`headless-360` binds to the current OAuth session —
confirm before mutating); **milestone strategy?** (Phase 3b); **milestone criteria?** (default
`Status != Closed` + pattern-specific filters). **Do not ask for an Account** — Incident has no
Account field; engagement is per-Incident via `EntitlementId`. **Business Hours:** ask only when the
user's choice is ambiguous or the org has none (Phase 3a step 4); never ask on the Predefined path.

Default suggestion: SLA Policy `Incident SLA Policy`, suggested default Business Hours (confirmed at
Phase 3c), Entitlement
auto-provisioned on activation (no Account), engagement per-Incident via `EntitlementId`, milestone
strategy resolved per Phase 3b.

---

## Workflow

Sequential — **always read before you write**; every call goes through `mcp__headless-360__*`.
**Per-phase detail (reads, delegated writes, API quirks) lives in `references/workflow.md` — read it
before executing.** Phase index and their non-negotiable gates:

- **Before you start — Reuse session state** only from a successful `dispatch_readonly` this session on this
  org, unwritten since; a user statement is never cache-eligible.
- **Phase 1a — IT Service Management gate** (`service-cloud-itsm-setup`). `NOT_ENABLED` → one ack
  (reversible) → direct enable → re-read.
- **Phase 1b — SLA Management gate.** SLA Management **and** the permanent SLA Versioning switch — two
  writes, two separate acks (master, then permanence); delegate to `itsm-shakti/SLASettings`.
- **Phase 2 — Predefined vs Custom** (Incident only). Detect the seeded policy first; read the live
  `Incident.Priority` picklist before the fork (custom values → recommend Custom); warn if the
  priority matrix is off (only the default tier fires); Business Hours note only if the user
  specified hours. Predefined → 4B → 5 (if asked) → 6 → **STOP**;
  Custom → 3a → 3b → 3c → 4A → 5 (if asked) → 6.
- **Phase 3a — Preflight.** Master Incident Mgmt (`service-cloud-itsm-incident`; `NOT_AVAILABLE` →
  HALT, `NOT_ENABLED` → one ack + delegate), `discover`/`describe` the SLA ops, Incident describe,
  resolve Business Hours, idempotency probe. No Account. `401`/`403`/`404` → halt with the raw error.
- **Phase 3b — Milestone strategy** per `examples/milestone-patterns.md`.
- **Phase 3c — Confirm** the full plan (Business Hours by name, every milestone) before any write.
- **Phase 4A — Create** (Business Hours first if planned, step 1) → `MilestoneTypes` →
  `create-sla-policy` → `create-milestone` ×N → `activate-sla-policy`; optional step 6 criterion
  only on an explicit always-match request.
- **Phase 4B — Seed** via `save-selected-options` (`{"selectedOptions":["incident"]}`), delegated
  to `itsm-shakti/SLASettings`; verify and name its Business Hours.
- **Phase 5 — Milestone actions** (only if asked) on every named milestone.
- **Phase 6 — Verify** via SOQL + a non-lowest-tier test Incident with an `EntityMilestone`; matrix
  off or still order-1 after one retry → stop and report the other tiers unchecked.

---

## Rules / Constraints

| Constraint | Rationale |
|-----------|-----------|
| Gate **IT Service Management enablement** first (Phase 1a, before Phase 1b) — exact apiName `service-cloud-itsm-setup`, never a look-alike; `NOT_ENABLED` → tell the user plainly + a single ack to enable (reversible) or stop; the enable write is dispatched **directly** (no owning SOR exists yet) and re-read to confirm | Higher-level org gate sits above every ITSM feature, including the Master Incident Mgmt pref below |
| Gate **SLA Management** first (Phase 1b) — **two separate writes** (SLA Management, then the one-way **SLA Versioning**); **two separate acks (master, then permanence) — never merged**; decline/blocked/verify-fail → **HALT**; re-read + report real state | Versioning is irreversible; writes don't confirm state |
| Offer **predefined (OOB)** first (Phase 2, Incident only); detect before seed; if chosen, seed → verify → **STOP** (no custom upsell) | OOB seed isn't idempotent — re-seed duplicates |
| `discover` + `describe` before any mutation | Catches a missing SLA surface / disabled Incident Mgmt early |
| Ask (`AskUserQuestion`) the milestone strategy — never silently default to Single | Real ITSM policies have >1 milestone |
| Reuse one MilestoneType per shared name; a distinct one per distinct concern | Runtime keys milestones by MilestoneType |
| Multi-milestone: halt on any milestone-create failure (no half-attached policy) | Partial attach diverges from the confirmed plan |
| Priority-tiered: reconcile every `Priority` value against the live picklist before dispatch — drop/rename standard rows that don't match **and add a milestone for each custom active value** the org added | Server accepts any string → an unknown value is a dead milestone; a custom value with no milestone gets no SLA |
| **Delegate every write to its approved SLA leaf** (`MilestoneTypes`, `create-sla-policy`, `create-milestone`, `create-milestone-action`, `activate-sla-policy`, `create-entitlement-criteria`) — the skill decides inputs, the leaf owns the contract. Scoped inline exceptions (no served owning SOR yet): the Phase 1a enable and the Phase 4A step 1 Business Hours create | Single contract-owner per write; the skill re-deriving Connect shapes drifts from the served leaves |
| **Business Hours** (Custom): honor a named schedule, described calendar, or time zone (time zone only → ask 24×7 (recommended) or custom hours; reuse a match, else create one after the Phase 3c confirm); zero active → offer a 24×7 create. Never set `IsDefault` or modify an existing record. Predefined: the seeder always uses the org default — warn only if the user specified hours | Default 24×7 or the customer's own calendar; `BusinessHours` is not API-deletable, so creates are confirmed first |
| **Custom flow**: activation provisions the auto-Entitlement (`activate-sla-policy`: `isActive` + `createEntitlement` as **QUERY params**) — matching Incidents then engage **per-Incident via `EntitlementId`** (**not** a manual sObject Entitlement, and no Account). An org-wide auto-apply criterion via `create-entitlement-criteria` is **optional** — only on an explicit always-match request, never by default. **OOB seed path**: one seeder call (`save-selected-options`, lowercase `selectedOptions`) provisions the entire active bundle incl. the Entitlement — no per-leaf calls, no manual `POST /sobjects/Entitlement`, no activate PATCH | Custom: one call activates **and** provisions, so a manual `POST /sobjects/Entitlement` would duplicate it. OOB: the platform seeder builds and activates the whole default bundle server-side, so the skill neither rebuilds it leaf-by-leaf nor provisions the Entitlement by hand |
| **No record Id in any message** (see Output contract, incl. reused artifacts); `AskUserQuestion` labels customer-facing (no "demo"/internal defaults) | Leaked Ids / internal framing look unprofessional to the customer |
| **Another Incident policy already active + Custom chosen → narrate coexistence only.** The custom policy is targeted **per-Incident via `EntitlementId`** (Incident has no Account field to scope on) and **additive**; the existing (predefined/broad) policy stays the org-wide one. **Never offer, plan, or perform — in the fork *or* the closing report —** deactivating an existing policy, reordering its entitlement criteria, **broadening the custom policy to match-all / auto-apply-to-all, or "deciding/resolving precedence" across policies**. Target specific Incidents via `EntitlementId`; the existing policy stays active (see `references/workflow.md` → Coexistence) | Changing a policy the user didn't ask to touch is out of scope — this skill configures a *new* coexisting custom policy, not edits to an existing one. Deactivating (`activate-sla-policy` *can* send `isActive=false`) or re-ranking another policy's criteria risks disrupting a live SLA, and no leaf arbitrates cross-policy precedence (predefined: no un-seed path, manual delete only). Both are meant to coexist — the agent otherwise improvises an out-of-scope deactivation/reorder/precedence upsell |

Additional API quirks: `references/mcp-invocation.md`.

---

## Verification Checklist

- [ ] **IT Service Management enablement gated (Phase 1a)** — exact apiName `service-cloud-itsm-setup` read `ENABLED` via live read, or the user explicitly acked an enable (reversible) that a re-read confirms; declined / unexpected status → **HALTED** before Phase 1b.
- [ ] **SLA Management gated (Phase 1b)** — SLA Management + SLA Versioning both on (two separate writes), only after the **permanence ack** (separate from the master ack); reported state = a re-read, not the write. Declined / blocked / verify-fail → **HALTED** before Phase 2/3a, no artifacts.
- [ ] **Predefined vs Custom offered (Phase 2)** — with the feature ON, OOB *Standard Support for Incidents* offered first; if present, reported not re-seeded; if chosen, seeded (2 MilestoneTypes + 6 milestones + Entitlement), verified, **no** custom offer after.
- [ ] Master Incident Mgmt pref (exact `service-cloud-itsm-incident`) `ENABLED` via live read, or delegated when `NOT_ENABLED` (`NOT_AVAILABLE` → HALT) — not a user assertion, not a look-alike.
- [ ] `discover`/`describe` confirmed the SLA Connect ops.
- [ ] Incident describe returned 200 with `EntitlementId`, `SlaStartDate`, `SlaExitDate`.
- [ ] Active Business Hours resolved and named in the confirmed plan — the user's named schedule / a matching calendar / the org default / a user-selected record, or a create (described calendar or 24×7 when none exist) confirmed at Phase 3c, then SOQL-verified active. Predefined: the seeded policy's Business Hours reported by name (or "none").
- [ ] **Milestone strategy resolved** — Phase 3b skip condition OR `AskUserQuestion`; Priority-tiered / Custom reconciled every `Priority`/criteria value against the live picklist before dispatch (dropped/renamed unmatched standard rows **and** added a milestone for each custom active `Priority` value).
- [ ] **Configuration confirmed OR skip condition met** (up-front auth / no-op / prior confirmation / "yes"); the resolved plan (org, SLA name, Business Hours by name, engagement model = per-Incident via `EntitlementId` (no Account), per-milestone list) narrated before Phase 4A.
- [ ] Writes **delegated to the SLA leaves** in order — the four core writes: MilestoneType(s) → Policy → Milestone(s) → activate + auto-Entitlement (the optional org-wide auto-apply criterion only if explicitly requested); any milestone-create failure halted (no partial attach). Trivial on no-op.
- [ ] **Milestone actions (Phase 5)** — if requested, attached to **every** named milestone; each confirmed from `body.success` + `actionMappings`, not the `201`; full set narrated before write.
- [ ] SLA Policy verified via SOQL, not the create response (no-op: the Phase-3a read is the verification).
- [ ] Test Incident has ≥1 EntityMilestone on the **correct tier** with a `TargetDate` (the engagement proof; Priority matched for Priority-tiered); expected milestone(s) present. Matrix off / still order-1 after one retry → reported "other tiers not checked" + pointed to `service-itsm-incident-priority-configure`, no recreate loop. `SlaStartDate` populated confirms it too, but may be null when the Entitlement is auto-applied via criteria — not a failure. Skip on no-op.
- [ ] **No record Id in any message** — interim narration *and* final report; artifacts by name, test Incident by `IncidentNumber` (see Output contract).
- [ ] Before/after + summary shown; no-op states the pre-existing config verbatim + "no changes made".

---

## Output Format

Use the `examples/output-templates.md` templates; fill placeholders as-is. The success report must carry, unambiguously: the **SLA Policy**; **every milestone** by MilestoneType name + time + criteria; the **Entitlement** (auto-provisioned, no Account — Incident has no Account field); **every requested action** by milestone tier/MilestoneType name (never a milestone Id) + Warning/Violation role + offset + how confirmed; a **Verification** section (SOQL-confirmed policy + test-Incident `SlaStartDate`/EntityMilestones, or an honest partial note); created-vs-reused per artifact; a **scope line** (only the Incident SLA). No record Id anywhere. If another Incident policy is already active, state the coexistence plainly (both stay active; the existing/predefined policy stays the broad org-wide one; the custom is targeted per-Incident via `EntitlementId`) and **do not offer to deactivate or reorder it, to broaden the custom policy to auto-apply to all Incidents, or to "decide precedence" across policies**.

---

## Reference File Index

| File | When to read |
|------|--------------|
| `references/workflow.md` | Executing — the full step-by-step Phase 1–6 detail (per-phase reads, delegated writes, API quirks); the constraints table + verification checklist stay in this SKILL.md body |
| `references/mcp-invocation.md` | Every phase — call shapes, templates, response envelope, discovery, gotchas |
| `examples/milestone-patterns.md` | Phase 3b — the five strategies: times, criteria, MilestoneType reuse, filter extensions |
| `assets/attach-milestone.json` | Phase 4A step 4 — milestone POST body; substitute ids/timeTrigger/order; append `filterItems` |
| `assets/attach-milestone-action.json` | Phase 5 — Warn/Escalate action body templates (Field Update); pair with mcp-invocation.md (Milestone Actions) |
| `examples/output-templates.md` | Output Format — success/partial report templates; fill placeholders, no record Id |

---

## Related Skills

The priority matrix (Impact × Urgency → Priority) is separate — `service-itsm-incident-priority-configure`;
if a Priority-tiered strategy is requested but `Incident.Priority` lacks values, direct the user there
first. Other ITSM flows (Major Incident Mgmt, custom fields) are out of scope.

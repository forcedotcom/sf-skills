---
name: service-itsm-agentic-setup-incident-sla-configure
description: "End-to-end Incident SLA setup for Service Cloud ITSM — creating a MilestoneType, an Incident-scoped SLA Policy (SlaProcess), attaching a Milestone with criteria, and wiring an Entitlement so Incidents derive an EntityMilestone with a computed TargetDate. Use when the user asks to configure SLA milestones on Incidents, create an SLA policy for Incident records, set up entitlement processes for ITSM, wire milestones so they appear on the Incident page, or enable SLA tracking for incident management. DO NOT TRIGGER when: the user asks about Case entitlements or Case SLA (not Incident), querying existing SLA policies without setup intent, general Entitlement sObject CRUD unrelated to Incident, or Milestone queries for reporting purposes only."
metadata:
  version: "3.8"
  domains: ["Service"]
  minApiVersion: "67.0"
  accessCheck:
    - type: "userPerm"
      value: "CustomizeApplication"
    - type: "orgPerm"
      value: "IncidentMgmt.orgHasITSMOrgPermission"
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
**SLA Management for IT Service** setup item (the Phase 0.5 gate).
The custom pipeline (four ordered writes): **MilestoneType** (what you measure) → **SLA Policy**
(SlaProcess, Incident-scoped, created inactive, entry/exit criteria) → **Milestone** (time trigger +
criteria) → **activate the policy** (`createEntitlement=true`, which auto-provisions the Entitlement —
matching Incidents then engage the SLA **per-Incident via `EntitlementId`**, with no Account). An
org-wide auto-apply **entitlement criterion** is an *optional* fifth write, dispatched **only** on an
explicit always-match request (Phase 2 step 12) — never by default. (The predefined/OOB
seed fork differs — it does none of this by hand: a single seed call provisions the whole active
bundle — policy, milestones, and Entitlement — in one shot; see Phase 0.6 / Phase 2-OOB.)
This skill owns all the Incident-SLA **interaction** (gates, forks, milestone strategy,
verification); the raw **write** operations are **delegated to the approved CSP-Sun SLA
leaf capabilities** (`csp-sun/MilestoneTypes`, `create-sla-policy`, `create-milestone`,
`create-milestone-action`, `activate-sla-policy`, `create-entitlement-criteria`), which own the
approved Connect contracts — discover → describe → dispatch each rather than re-deriving its shape here.
The Phase 0.5 **enable** (+ Versioning) and Phase 2-OOB **seed** writes delegate to
**`itsm-shakti/SLASettings`** (owns the SLA-Management settings surface) — same discover → describe → dispatch.

## Scope

- **In scope**: the SLA artifacts above (MilestoneTypes, the SLA Policy and its milestones,
  activation with its auto-provisioned Entitlement, and — only on an explicit org-wide always-match
  request — the optional auto-apply criterion) + verifying SLA
  engagement on Incident records; gating
  **SLA Management for IT Service** (Phase 0.5); offering the OOB *Standard Support for Incidents*
  policy vs a custom one (Phase 0.6, Incident only) — all via `headless-360` MCP.
- **Out of scope**: Case SLA/entitlements; Assignment Rules; Escalation Rules; Notification
  Rules; general Entitlement CRUD not related to Incident SLA; SLA reporting.

---

## Output contract — applies to EVERY message

**Never print a raw Salesforce record Id** (15/18-char: `55…`, `550…`, `0ny…`, `00…`, Account `001…`) — full **or
masked** (`557VW…R3XVYA0` still leaks) — in **any** user-facing text: interim narration *and* the
final report. Holds for artifacts you **created** *and* ones you **detected/reused** — name each (the
name you supplied on create, or matched on reuse), keep its Id internal (chaining only). Verifying or
matching via SOQL? Report the **verified attributes/name**, never the Id you queried by. **Looking *up*
an Id is the same rule** — resolving the default **BusinessHours** or an existing policy returns
`{Id, Name}`; narrate the resolved **name only** and keep the returned Id internal — **never** echo it
back as `Resolved "<name>" (001VW…)`. One
exception: on a **halt** you may relay the raw error body verbatim even if it embeds an Id —
don't hand-edit it.

- **Wrong:** `SLA policy created (552VW…)` · `Incident created (0ny…)` · `First Response → 557VW…R3XVYA0` (reuse)
- **Right:** `Created SLA policy "Standard Support for Incidents"` · `reusing the existing First Response
  milestone type` · the test Incident is "the test Incident" until Phase 3, then its `IncidentNumber`;
  milestones by `MilestoneType` name.

---

## Routes at a glance

Reads → `mcp__headless-360__dispatch_readonly`, writes → `mcp__headless-360__dispatch`. Both take raw
HTTP `{"url","method","body"?,"query_params"?}` — **not** `{operation_id, arguments}`; read `body`
from `{status_code, body}`. Full route table with request/response shapes: `references/mcp-invocation.md`.

---

## Clarifying Questions

Ask only what you cannot infer from context (pre-populate; note "(from conversation)"). **Resolve the
Phase 0.5 gate first.** Then: **which org?** (`headless-360` binds to the current OAuth session —
confirm before mutating); **milestone strategy?** (Phase 1.4); **milestone criteria?** (default
`Status != Closed` + pattern-specific filters). **Do not ask for an Account** — Incident has no
Account field; engagement is per-Incident via `EntitlementId`.

Default suggestion: SLA Policy `Incident SLA Policy`, default BusinessHours, Entitlement
auto-provisioned on activation (no Account), engagement per-Incident via `EntitlementId`, milestone
strategy resolved per Phase 1.4.

---

## Workflow

All steps are sequential — **always read before you write**; every call goes through
`mcp__headless-360__*`. **The full step-by-step detail — every phase's reads, delegated writes, and
API quirks — lives in `references/workflow.md`; read it before executing.** The phases and their
non-negotiable gates (constraints table + verification checklist below):

- **Phase 0 — Reuse session state.** Skip a Phase 1 read only when the same fact was produced *this
  session* by a successful `dispatch_readonly` on the current org and unwritten since; a user
  statement is never cache-eligible. When in doubt, re-check.
- **Phase 0.5 — SLA Management gate (resolve first, alone).** Enabled only when **both** SLA
  Management and SLA Versioning are on — **two separate writes**: enabling SLA Management does **not**
  turn on Versioning; Versioning is a distinct, **permanent, one-way** write. **Two separate
  `AskUserQuestion` acks — never merged:** (a) a reversible master Incident-Mgmt enable if
  `NOT_ENABLED`; (b) a distinct **permanence** ack for the irreversible Versioning switch — a bare
  "enable SLA" is **not** consent. Decline (b) / non-empty `enableBlockedReasons` / re-read mismatch /
  master `NOT_AVAILABLE` → **HALT**. After each write, re-read and report the REAL state — never trust
  `200`/`204`. Enable + versioning writes **delegate to `itsm-shakti/SLASettings`**.
- **Phase 0.6 — Predefined (OOB) vs Custom (Incident only).** Detect *Standard Support for Incidents*
  first (already present → report seeded; no re-seed — the OOB seed isn't idempotent — and no
  upsell). **Before** the fork prompt, read the live `Incident.Priority` picklist (Phase 1 step 3's
  Incident describe, pulled forward): any custom active
  value beyond the four standard tiers (e.g. `Emergency`) means OOB covers standard tiers only — say
  so plainly and **redirect to Custom** by default; don't *proactively* bolt a custom milestone onto
  the predefined policy (and never re-seed). Attach one only if the user **explicitly** asks — a direct
  `csp-sun/create-milestone` against the seeded policy (resolved by name), never a re-seed.
  Then one `AskUserQuestion`, **Predefined first/recommended**. Predefined → Phase 2-OOB → 2.5 →
  verify → **STOP**; Custom → Phase 1 → 1.4 → 1.5 → 2 → 3.
- **Phase 1 — Preflight & discovery.** Master Incident-Mgmt pref (exact `service-cloud-itsm-incident`,
  never a look-alike; `NOT_AVAILABLE` → HALT, `NOT_ENABLED` → ack + delegate), `discover`/`describe`
  the SLA Connect ops, Incident describe (`EntitlementId`/`SlaStartDate`/`SlaExitDate` **+ the live
  `Incident.Priority` picklist** for Priority-tiered reconciliation), default BusinessHours,
  idempotency probe. **No Account is resolved — Incident has no Account field; engagement is
  per-Incident via `EntitlementId` (neither flow needs or asks for an Account).** Any
  `401`/`403`/`404` → halt and surface the raw error.
- **Phase 1.4 — Milestone strategy.** Load `examples/milestone-patterns.md` (skip conditions + the
  five strategies, defaults, MilestoneType-reuse). Never silently default to Single.
- **Phase 1.5 — Confirm before mutating.** Narrate the resolved plan (org, SLA name, engagement model
  = per-Incident via `EntitlementId` (no Account), **full per-milestone list** — never collapse to "N
  milestones"); require an explicit "yes" unless a skip
  condition holds (up-front auth / no-op / prior confirmation). Everything after this mutates the org.
- **Phase 2 — Create SLA artifacts (delegated writes, exact order).** The skill decides every input;
  **delegate each raw write to its approved csp-sun SLA leaf**. The **four ordered core writes**:
  `MilestoneTypes` → `create-sla-policy` (created inactive) → `create-milestone` ×N →
  `activate-sla-policy` (auto-provisions the Entitlement). Do not re-derive Connect shapes.
  `create-entitlement-criteria` is an **optional step 12** — dispatch it **only** on an explicit
  org-wide always-match request; otherwise engagement is per-Incident via `EntitlementId` and no
  criterion is written. The **Priority reconciliation** lands at the milestone step: match every value to
  the live picklist, drop/rename unmatched standard rows, **and add a milestone for each custom active
  value**. Verify via SOQL, not the write response; halt on any milestone-create failure (no
  half-attached policy).
- **Phase 2-OOB — Seed the predefined policy.** One call to the platform seeder route
  (`PATCH /headless/invoke/platform/slasettings/save-selected-options`, body
  `{"selectedOptions":["incident"]}` — values **lowercase**) provisions the whole active bundle:
  the policy, its 2 MilestoneTypes + 6 milestones, and the Entitlement + auto-apply criteria — all
  active, in one shot. No per-leaf csp-sun calls, no manual `POST /sobjects/Entitlement`, no activate
  PATCH. Detect first (`GET /headless/invoke/platform/slasettings`, key `incident:true` = already
  seeded) because the seeder isn't idempotent. Detect + seed **delegate to `itsm-shakti/SLASettings`**.
- **Phase 2.5 — Milestone actions (optional).** Only if warn/escalate/notify asked; apply to **every**
  named milestone; confirm from `body.success` + non-empty `actionMappings`, not the `201`.
- **Phase 3 — Verify.** SOQL-confirm the policy read back `active=true`; create a test Incident on a
  **non-lowest tier** (set `Urgency`/`Impact` — `Priority` is matrix-derived, not directly
  insertable); confirm an `EntityMilestone` on the correct tier with a `TargetDate` (a null
  `SlaStartDate` under auto-apply is a non-blocker). Then report.

---

## Rules / Constraints

| Constraint | Rationale |
|-----------|-----------|
| Gate **SLA Management** first (Phase 0.5) — **two separate writes** (SLA Management, then the one-way **SLA Versioning**); **two separate acks (master, then permanence) — never merged**; decline/blocked/verify-fail → **HALT**; re-read + report real state | Versioning is irreversible; writes don't confirm state |
| Offer **predefined (OOB)** first (Phase 0.6, Incident only); detect before seed; if chosen, seed → verify → **STOP** (no custom upsell) | OOB seed isn't idempotent — re-seed duplicates |
| `discover` + `describe` before any mutation | Catches a missing SLA surface / disabled Incident Mgmt early |
| Ask (`AskUserQuestion`) the milestone strategy — never silently default to Single | Real ITSM policies have >1 milestone |
| Reuse one MilestoneType per shared name; a distinct one per distinct concern | Runtime keys milestones by MilestoneType |
| Multi-milestone: halt on any milestone-create failure (no half-attached policy) | Partial attach diverges from the confirmed plan |
| Priority-tiered: reconcile every `Priority` value against the live picklist before dispatch — drop/rename standard rows that don't match **and add a milestone for each custom active value** the org added | Server accepts any string → an unknown value is a dead milestone; a custom value with no milestone gets no SLA |
| **Delegate every write to its approved csp-sun SLA leaf** (`MilestoneTypes`, `create-sla-policy`, `create-milestone`, `create-milestone-action`, `activate-sla-policy`, `create-entitlement-criteria`) — the skill decides inputs, the leaf owns the contract | Single contract-owner per write; the skill re-deriving Connect shapes drifts from the served leaves |
| **Custom flow**: activation provisions the auto-Entitlement (`activate-sla-policy`: `isActive` + `createEntitlement` as **QUERY params**) — matching Incidents then engage **per-Incident via `EntitlementId`** (**not** a manual sObject Entitlement, and no Account). An org-wide auto-apply criterion via `create-entitlement-criteria` is **optional** — only on an explicit always-match request, never by default. **OOB seed path**: one seeder call (`save-selected-options`, lowercase `selectedOptions`) provisions the entire active bundle incl. the Entitlement — no per-leaf calls, no manual `POST /sobjects/Entitlement`, no activate PATCH | Custom: one call activates **and** provisions, so a manual `POST /sobjects/Entitlement` would duplicate it. OOB: the platform seeder builds and activates the whole default bundle server-side, so the skill neither rebuilds it leaf-by-leaf nor provisions the Entitlement by hand |
| **No record Id in any message** (see Output contract, incl. reused artifacts); `AskUserQuestion` labels customer-facing (no "demo"/internal defaults) | The #1 retest failure; leaked Ids / internal framing look unprofessional |
| **Another Incident policy already active + Custom chosen → narrate coexistence only.** The custom policy is targeted **per-Incident via `EntitlementId`** (Incident has no Account field to scope on) and **additive**; the existing (predefined/broad) policy stays the org-wide one. **Never offer, plan, or perform — in the fork *or* the closing report —** deactivating an existing policy, reordering its entitlement criteria, **broadening the custom policy to match-all / auto-apply-to-all, or "deciding/resolving precedence" across policies**. Target specific Incidents via `EntitlementId`; the existing policy stays active (see `references/workflow.md` → Coexistence) | Changing a policy the user didn't ask to touch is out of scope — this skill configures a *new* coexisting custom policy, not edits to an existing one. Deactivating (`activate-sla-policy` *can* send `isActive=false`) or re-ranking another policy's criteria risks disrupting a live SLA, and no leaf arbitrates cross-policy precedence (predefined: no un-seed path, manual delete only). Both are meant to coexist — the agent otherwise improvises an out-of-scope deactivation/reorder/precedence upsell |

Additional API quirks: `references/mcp-invocation.md`.

---

## Verification Checklist

- [ ] **SLA Management gated (Phase 0.5)** — SLA Management + SLA Versioning both on (two separate writes), only after the **permanence ack** (separate from the master ack); reported state = a re-read, not the write. Declined / blocked / verify-fail → **HALTED** before Phase 0.6/1, no artifacts.
- [ ] **Predefined vs Custom offered (Phase 0.6)** — with the feature ON, OOB *Standard Support for Incidents* offered first; if present, reported not re-seeded; if chosen, seeded (2 MilestoneTypes + 6 milestones + Entitlement), verified, **no** custom offer after.
- [ ] Master Incident Mgmt pref (exact `service-cloud-itsm-incident`) `ENABLED` via live read, or delegated when `NOT_ENABLED` (`NOT_AVAILABLE` → HALT) — not a user assertion, not a look-alike.
- [ ] `discover`/`describe` confirmed the SLA Connect ops.
- [ ] Incident describe returned 200 with `EntitlementId`, `SlaStartDate`, `SlaExitDate`.
- [ ] Default BusinessHours found.
- [ ] **Milestone strategy resolved** — Phase 1.4 skip condition OR `AskUserQuestion`; Priority-tiered / Custom reconciled every `Priority`/criteria value against the live picklist before dispatch (dropped/renamed unmatched standard rows **and** added a milestone for each custom active `Priority` value).
- [ ] **Configuration confirmed OR skip condition met** (up-front auth / no-op / prior confirmation / "yes"); the resolved plan (org, SLA name, engagement model = per-Incident via `EntitlementId` (no Account), per-milestone list) narrated before Phase 2.
- [ ] Writes **delegated to the csp-sun leaves** in order — the four core writes: MilestoneType(s) → Policy → Milestone(s) → activate + auto-Entitlement (the optional org-wide auto-apply criterion only if explicitly requested); any milestone-create failure halted (no partial attach). Trivial on no-op.
- [ ] **Milestone actions (Phase 2.5)** — if requested, attached to **every** named milestone; each confirmed from `body.success` + `actionMappings`, not the `201`; full set narrated before write.
- [ ] SLA Policy verified via SOQL, not the create response (no-op: the Phase-1 read is the verification).
- [ ] Test Incident has ≥1 EntityMilestone on the **correct tier** with a `TargetDate` (the engagement proof; Priority matched for Priority-tiered); expected milestone(s) present. `SlaStartDate` populated confirms it too, but may be null when the Entitlement is auto-applied via criteria — not a failure. Skip on no-op.
- [ ] **No record Id in any message** — interim narration *and* final report; artifacts by name, test Incident by `IncidentNumber` (see Output contract).
- [ ] Before/after + summary shown; no-op states the pre-existing config verbatim + "no changes made".

---

## Output Format

Use the `examples/output-templates.md` templates; fill placeholders as-is. The success report must carry, unambiguously: the **SLA Policy**; **every milestone** by MilestoneType name + time + criteria; the **Entitlement** (auto-provisioned, no Account — Incident has no Account field); **every requested action** by milestone tier/MilestoneType name (never a milestone Id) + Warning/Violation role + offset + how confirmed; a **Verification** section (SOQL-confirmed policy + test-Incident `SlaStartDate`/EntityMilestones, or an honest partial note); created-vs-reused per artifact; a **scope line** (only the Incident SLA). No record Id anywhere. If another Incident policy is already active, state the coexistence plainly (both stay active; the existing/predefined policy stays the broad org-wide one; the custom is targeted per-Incident via `EntitlementId`) and **do not offer to deactivate or reorder it, to broaden the custom policy to auto-apply to all Incidents, or to "decide precedence" across policies**.

---

## Reference File Index

| File | When to read |
|------|--------------|
| `references/workflow.md` | Executing — the full step-by-step Phase 0–3 detail (per-phase reads, delegated writes, API quirks); the constraints table + verification checklist stay in this SKILL.md body |
| `references/mcp-invocation.md` | Every phase — call shapes, templates, response envelope, discovery, gotchas |
| `examples/milestone-patterns.md` | Phase 1.4 — the five strategies: times, criteria, MilestoneType reuse, filter extensions |
| `assets/attach-milestone.json` | Phase 2 step 10 — milestone POST body; substitute ids/timeTrigger/order; append `filterItems` |
| `assets/attach-milestone-action.json` | Phase 2.5 — Warn/Escalate action body templates (Field Update); pair with mcp-invocation.md (Milestone Actions) |
| `examples/output-templates.md` | Output Format — success/partial report templates; fill placeholders, no record Id |

---

## Related Skills

The priority matrix (Impact × Urgency → Priority) is separate — `service-itsm-incident-priority-configure`;
if a Priority-tiered strategy is requested but `Incident.Priority` lacks values, direct the user there
first. Other ITSM flows (Major Incident Mgmt, custom fields) are out of scope.

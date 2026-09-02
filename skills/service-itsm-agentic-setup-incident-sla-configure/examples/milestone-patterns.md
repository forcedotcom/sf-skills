# Milestone Strategy Patterns — Incident SLA

Phase 1.4 of the SLA workflow either infers the milestone strategy from the user's prompt (see
"Phase 1.4 skip conditions" below) or asks the user to pick one. This file lists each option with
its default configuration, MilestoneType-reuse rules, and the exact `Attach Milestone` payloads
that Phase 2 step 10 dispatches. Every `filterItems.operator` value here uses the exact enum the
server accepts — `Equals`, `NotEqual` — never `!=` or `Equal`.

---

## Phase 1.4 skip conditions (do NOT dispatch `AskUserQuestion` when any hold)

Every SLA policy needs at least one milestone, but the strategy question is skipped when the
milestone shape is already determined by the request:

- **(a) The prompt / conversation already describes a concrete milestone shape** — e.g. "60-minute
  first-response trigger", "Response + Resolution defaults", "per-priority tiers". Extract the
  described milestone(s) verbatim (time, criteria, name) and use the pattern defaults below. Do
  NOT re-ask.
- **(b) The eventual branch is an idempotent no-op** — Phase 1 step 6 established `noOp=true`
  (every requested artifact already exists with matching configuration). Skip Phase 1.4, skip
  Phase 2, and report the no-op verbatim citing the read evidence.
- **(c) Explicit up-front authorization** — a phrase that unambiguously waives the confirm gate
  (`"you have my explicit authorization to create"`, `"do not re-ask me to confirm"`,
  `"proceed without asking"`) **and** a concrete milestone shape is derivable per (a). A passing
  mention ("build it", "go ahead") is NOT sufficient by itself. Waives the interactive confirm;
  does NOT waive Phase 1.5 plan-narration — dispatch only after SLA Policy name, Account,
  Entitlement date range, and per-milestone list have been written to the response.

**Only when none of (a)/(b)/(c) apply** (generic "set up an SLA on Incidents" with no shape),
dispatch `AskUserQuestion` with the five options below. Priority-tiered requires the
`Incident.Priority` picklist — validate before offering.

All strategies share these defaults unless overridden:

- `businessHoursId`: the default BusinessHours resolved in Phase 1 step 4
- `startTimeBasedOn`: `SlaProcessCreatedDate`
- `milestoneAgreementType`: `SLA` — inside each `milestoneCriteria[]` item (mandatory per the UI). Valid UI values are `SLA` (customer-facing) or `OLA` (internal); the API accepts any string because the underlying field is `Text(40)` with no server-side picklist, but the UI renders unrecognized values as blank (W-23959162)
- `milestoneState`: `Active` (inside `milestoneCriteria[]`)
- `filterType`: `RuleFilter` (inside `milestoneCriteria[]`)
- Base filter row: `Incident.Status NotEqual Closed` (keeps every milestone alive until the
  Incident closes; ANDs with pattern-specific criteria below)

---

## AskUserQuestion prompt (Phase 1.4, only when no skip condition applies)

```text
Question: How many milestones do you want on this SLA policy?

  1. Single milestone            — one 60-min First Response timer (simplest)
  2. Response + Resolution       — 30-min response + 8-hour resolution (classic)
  3. Priority-tiered response    — one timer per Priority (Critical/P1 15 / High/P2 60 / Moderate (a.k.a. Medium)/P3 240 / Low/P4 1440 min)
  4. Escalation ladder           — Response (30) → Manager Escalation (120) → Executive Escalation (480 min)
  5. Custom / mixed              — walk through each milestone individually (name, time, criteria)
```

For options 3 and 4, the concrete numbers are the defaults the skill uses if the user picks the
option without customizing. Option 5 dispatches follow-up `AskUserQuestion` prompts.

Before rendering options 3 and 5, confirm the live `Incident.Priority` picklist values (fetched in
Phase 1 via the Incident describe) — if any value used in a default row is missing from the org's
picklist, drop that milestone from the pattern and note it in the Phase-1.5 confirmation.

---

## Canonical Attach-Milestone payload

Dispatch every pattern below via `mcp__headless-360__dispatch` with `method: "POST"` and
`url: "/services/data/v67.0/connect/sla-management/sla-policies/<slaId>/milestones"` (substitute
the SLA policy id captured in Phase 2 step 9). The reusable request-body template lives at
`assets/attach-milestone.json` — load and populate it rather than reconstructing the JSON.

Substitute per-pattern: `milestoneTypeId` is the id returned when you created the MilestoneType,
`businessHoursId` is the id resolved in Phase 1, and `timeTrigger` + `order` come from the
pattern's row. `filterItems` in the template carries the base "Status != Closed" row that every
pattern shares; each pattern's table lists **additional** row objects to append to `filterItems`
(same schema: `table`, `column`, `operator`, `order`, `value`) — do not replace the base row, add
to it.

---

## Pattern 1 — Single milestone (default)

**MilestoneTypes to create:** 1 — `Incident First Response`
**Milestones to attach:** 1

| # | MilestoneType | timeTrigger | Extra filter items |
|---|---------------|-------------|--------------------|
| 1 | Incident First Response | 60 | *(none — Status != Closed only)* |

---

## Pattern 2 — Response + Resolution

**MilestoneTypes to create:** 2 — `Incident First Response`, `Incident Resolution`
**Milestones to attach:** 2

| # | MilestoneType | timeTrigger | Extra filter items |
|---|---------------|-------------|--------------------|
| 1 | Incident First Response | 30 | *(none)* |
| 2 | Incident Resolution     | 480 (8 hours) | *(none)* |

Both milestones only enforce `Status != Closed`. Response fires first (30 min); Resolution runs
concurrently on its own 8-hour timer.

---

## Pattern 3 — Priority-tiered response

**MilestoneTypes to create:** 1 — `Incident First Response` (reused across all four milestones)
**Milestones to attach:** up to 4 (one per active Priority value)

| # | Priority | timeTrigger | Extra filter items |
|---|----------|-------------|--------------------|
| 1 | Critical | 15  | `Incident.Priority Equals Critical` |
| 2 | High     | 60  | `Incident.Priority Equals High` |
| 3 | Moderate | 240 | `Incident.Priority Equals Moderate` |
| 4 | Low      | 1440 | `Incident.Priority Equals Low` |

Assumes the standard `Critical / High / Moderate / Low` picklist (some orgs and prompts label the
mid tier `Medium` instead of `Moderate` — same P3 tier, different label). If the org has renamed /
removed / added values (checked against the Phase-1 Incident describe), drop or rename milestones
to match — do not send `Priority Equals <value>` for a value that is not in the live picklist (the
server accepts it silently and the milestone never engages).

The multi-item `filterItems` array combines with `AND` by default — both `Status != Closed` AND
`Priority == Critical` must hold for the milestone to remain active. If Priority flips after
Incident create (e.g. via the Priority Matrix), the milestone re-evaluates on the next server pass.

---

## Pattern 4 — Escalation ladder

**MilestoneTypes to create:** 3 — `Incident First Response`, `Incident Manager Escalation`,
`Incident Executive Escalation`
**Milestones to attach:** 3

| # | MilestoneType | timeTrigger | Extra filter items |
|---|---------------|-------------|--------------------|
| 1 | Incident First Response      | 30  | *(none)* |
| 2 | Incident Manager Escalation  | 120 | *(none)* |
| 3 | Incident Executive Escalation | 480 | *(none)* |

All three run concurrently from `SlaProcessCreatedDate` — the "ladder" is enforced by the timers,
not by chaining. To fire automation at a milestone's warning/violation checkpoint (warn before
target, escalate on breach), attach a **milestone action** in Phase 2.5 — see
`references/mcp-invocation.md` (Milestone Actions). (Strictly *sequential* chaining across separate
milestones is a different mechanism — workflow SLA actions — and remains out of scope.)

---

## Pattern 5 — Custom / mixed

For genuinely custom setups, the skill walks the user through each milestone one at a time with
`AskUserQuestion`.

For each milestone `i` from 1 to N (where N is confirmed up front):

1. **Milestone name** — used as the MilestoneType label. Reuse an existing MilestoneType if the
   name matches one already created in this run; otherwise create a new one.
2. **Time trigger (minutes)** — integer, business-hours-aware.
3. **Criteria field** — the `Incident.*` field to filter on (default `Status`). For custom
   fields, use the `Incident.<Field>__c` API name.
4. **Criteria operator** — one of `Equals`, `NotEqual`, `LessThan`, `GreaterThan`, `Contains`,
   `StartsWith`, `Includes` (server enum — no `!=`, no `Equal`).
5. **Criteria value** — validated against the live picklist for picklist fields; free-form
   otherwise.

After collecting all N milestones, render the full list in Phase 1.5 confirmation and require an
explicit "yes" before dispatching the create loop.

**Custom-mixed example** (Response for all + per-category resolution):

| # | Name                        | timeTrigger | Filter items |
|---|-----------------------------|-------------|--------------|
| 1 | Incident First Response     | 30  | `Status NotEqual Closed` |
| 2 | Outage Resolution           | 240 | `Status NotEqual Closed`, `Category Equals Availability` |
| 3 | Request Resolution          | 1440 | `Status NotEqual Closed`, `Category Equals Request` |

For rows 2 and 3, first confirm `Category` is present on the org's Incident picklist and that the
values are active — if not, ask the user which category values they actually want to filter on
before creating the MilestoneType or attaching the milestone.

---

## Predefined preset — "Standard Support for Incidents" (OOB)

This is Salesforce's out-of-box predefined Incident SLA policy — a fixed priority-tiered preset offered
at the Phase 0.6 fork (not one of the Phase 1.4 custom options above). It pairs an **Acknowledge Within**
and a **Resolve Within** milestone per priority tier:

| tier | Acknowledge Within | Resolve Within |
|------|--------------------|----------------|
| Critical        | 30 min  | 120 min |
| High            | 60 min  | 240 min |
| Moderate or Low | 240 min | 960 min |

Seed it verbatim from `assets/predefined-incident-policy.json` following the recipe in
`references/mcp-invocation.md` (Predefined Incident Policy) — detect-before-seed (the policy AND the
pre-seeded MilestoneType catalog: reuse `Resolve Within` etc. by name, create only what is missing),
`active: true` on create, validate Priority/Status against the live picklist, and map the mid tier to
the org's real label (`Moderate` or `Medium`). Unlike the custom patterns above, when the user picks
this at the fork the skill seeds → verifies → **stops** (no custom milestone offer after).

---

## Gotchas across all patterns

| Issue | Detail |
|-------|--------|
| MilestoneType reuse vs. create | Priority-tiered = 1 MilestoneType reused 4 times. Response + Resolution = 2 types. Escalation ladder = 3 types. |
| Priority-tiered needs a Priority | The test Incident in Phase 3 must have a `Priority` value matching one of the milestones — otherwise no EntityMilestone spawns. Set the Priority explicitly, or create one test Incident per Priority. |
| Multi-milestone partial-failure | If milestone #2 of N fails to attach, halt and surface the raw error. Do NOT continue attaching #3..N — the policy will be half-configured. |
| `order` field | Numeric 1..N. Not load-bearing for runtime evaluation (all milestones fire independently), but controls display order in the UI. |
| Priority-tiered + Priority Matrix skill | If the Priority Matrix skill is also running, its Impact × Urgency grid decides `Incident.Priority`. Enable the matrix first if you want new Incidents to derive Priority from the matrix. |

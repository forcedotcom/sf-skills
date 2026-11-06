# Feature: SLA & Milestones (delegated to the `SLASettings` and `sla-management-setup` SORs)

How the orchestrator runs the **SLA & Milestones** feature: completing the **SLA Management for IT Service**
setup item, then giving Incidents an SLA — Salesforce's **predefined** *Standard Support for Incidents*
policy, or a **custom** Incident policy with its milestones, optional milestone actions (warn / escalate),
and the activation that provisions its Entitlement. `SLASettings` owns the gate and the predefined seed;
`sla-management-setup` and the write leaves its steps delegate to own the custom policy. Their own steps and
guidance decide *how* — the bodies, the order, and the read-backs; the orchestrator runs them itself under
its **SOR hand-off protocol** and owns every user-facing gate. This file adds what is specific to Incident
SLAs.

> **Casing override — load-bearing.** `SLASettings` lists the seed values and the existence-map keys as
> `Incident` / `Problem` / `ChangeRequest`. The server uses **lowercase**: the map comes back keyed
> `incident` / `problem` / `changeRequest`, and the seed must send `{"selectedOptions": ["incident"]}` —
> the capitalized `Incident` fails with a server error. This is the one place this file overrides
> `describe`.

1. `discover` the SORs by intent (e.g. "turn on SLA management and SLA versioning, predefined incident SLA
   policy"; "create an incident SLA policy with milestones") and `describe` the ids `discover` returns
   (`SLASettings`, `sla-management-setup`, and each leaf a step delegates to). Their IT Service Enablement
   checks fall under protocol step 2. Incident only: never seed or build a Case, Problem, or Change Request
   policy.
2. **The gate.** *SLA Management for IT Service* is set up only when both `get-sla-management-permission`
   and `get-sla-versioning-permission` read `true` — then it passes with no question. Otherwise ask once
   (`AskUserQuestion`): completing it turns on **SLA Management** (it can be turned off again later) and, as
   a separate step, **SLA Versioning**, which **can't be turned off once enabled** — turning SLA Management
   off later won't turn Versioning off. Options: **Enable** / **Stop — make no changes**. There is no
   "without Versioning" option, and a bare or repeated "enable SLA" is not consent to the permanent switch.
   On Enable, set only the switches that read `false` — SLA Management first, then Versioning — and require
   each verify step to read `true` before the next write. *"Entitlements permission not enabled…"* means
   Entitlement Management is off: point the user to **Setup → Entitlement Settings** and stop. Stop on
   Stop, a failed write, or a re-read that isn't `true`; an SLA Management enable that already landed may
   stand — say what is on.
3. **Detect the predefined policy** (`get-existing-checkbox-states`). `incident: true` means *Standard
   Support for Incidents* already exists: say so, **never re-seed** (the seed isn't idempotent — a second
   run duplicates every artifact), and stop unless the user explicitly asks for a custom policy. Don't
   upsell one.
4. **Read what the choice needs** — from `ItsmPriorityMatrix` (entity type `Incident`), only these two
   reads: the active Incident `Priority` values (`describe-priority-picklist`) and the matrix flag
   (`read-priority-matrix-prefs`, `IncPriorityMatrixEnabled`). With the matrix off, every Incident gets the
   default priority, so only that tier's milestones fire: warn plainly and point to the **Priority Matrix**
   feature. A warning, never a gate — never turn the matrix on from here.
5. **Predefined or custom.** Ask (`AskUserQuestion`): **Predefined — *Standard Support for Incidents*
   (Recommended)** or **Custom**. The seed builds an **active** policy and its Entitlement in one step, with
   no un-seed (a manual delete only): two milestone types (*Acknowledge Within*, *Resolve Within*) and six
   milestones (Critical 30 / 120 min, High 60 / 240, Moderate or Low 240 / 960). Recommend Custom instead
   when the org has active `Priority` values beyond those four (they'd get no milestone), or the user wants
   specific Business Hours (the seed takes none) or milestone actions — this feature never edits an existing
   policy. **Predefined:** confirm, run `save-selected-options` with the lowercase `incident`, then
   `verify-save-selected-options` (expect `incident: true`), and stop.
6. **Custom — plan.** The policy type is Incident (never ask), and there is no Account — an Incident engages
   its SLA through its Entitlement. Skip the SOR's update, delete, and version steps: editing or versioning
   an existing policy is outside this feature.
   - **Name and hours.** The default name is *Incident SLA Policy*; if `get-sla-policies` shows it taken,
     ask for another. No hours named → leave Business Hours empty (24×7), as `create-sla-policy` says.
     Named hours → resolve them as that leaf's Business Hours input describes; if no active record
     matches, offer 24×7 or stop so the user can create them in **Setup → Business Hours** — this feature
     never creates them.
   - **Milestones.** Skip the question when the request already gives a concrete shape ("60-minute first
     response", "per-priority tiers"); otherwise ask (`AskUserQuestion`):

     | # | Option | Milestones (minutes) |
     |---|--------|----------------------|
     | 1 | Single | *Incident First Response* 60 |
     | 2 | Response + Resolution | *Incident First Response* 30, *Incident Resolution* 480 |
     | 3 | Priority-tiered | Critical 15, High 60, Moderate 240, Low 1440 — one per active `Priority` value, all *Incident First Response* |
     | 4 | Escalation ladder | *Incident First Response* 30, *Incident Manager Escalation* 120, *Incident Executive Escalation* 480 (concurrent timers) |
     | 5 | Custom | Per milestone: its name, minutes, and condition |

     Every milestone's criteria start from `Incident.Status` not equal to `Closed`, ANDed with its own
     condition. For options 3 and 5, reconcile with the live `Priority` values both ways: rename a renamed
     tier, drop an inactive one, and add a milestone for an extra active one (confirm its minutes).
   - **Milestone actions, only if asked.** The default is a Field Update on Incident — `Urgency` to `High`
     at the warning and `Impact` to `High` at the breach — never `Priority`, which the Priority Matrix
     derives from Impact × Urgency. "Warn at X%" is an offset of round(target × (1 − X/100)) before the
     target (120 min at 75% → 30); "escalate on breach" is a Violation at 0. Apply the checkpoints to every
     milestone the user named, and give each action a unique name per milestone (suffix `_FR`, `_RES`, …).
   - **Confirm the plan** before the first write: the policy name, the Business Hours by name (or 24×7),
     the **full** milestone list (never "N milestones"), every action, the matrix-off note if it applies,
     and that the policy engages per Incident through its Entitlement.
7. **Custom — build** in `sla-management-setup`'s order, through its steps and the leaves they delegate to:
   the milestone types, the policy, each milestone, the actions (each confirmed as the
   `create-milestone-action` leaf describes, including its `verify-milestone-action` read-back), then
   activation.
   - Check Entitlement Management once, with `sla-management-setup`'s `check-entitlements-enabled`, and
     follow that step if it reads `false` — never a leaf's own check (some turn it on unasked).
   - **Halt on the first failed milestone** — nothing after it is created; say which one failed.
   - **Org-wide auto-apply** (`create-entitlement-criteria`) runs only on an explicit request that every
     Incident match, after a warning that it collides with any existing broad Incident policy. Otherwise
     say the policy engages per Incident and no criterion was created.
   - **Another active Incident policy** stays untouched — never offer to deactivate, reorder, broaden, or
     rank it. Narrate: "your existing *<name>* policy stays active; this custom policy is applied per
     Incident by setting the Incident's Entitlement to it."

```text
SLA & Milestones
  SLA Management for IT Service ... On | Turned on now
  SLA Versioning .................. On | Turned on now (permanent)
  Policy .......................... Standard Support for Incidents (predefined — seeded now | already present)
                                    | <name> (custom — created)
  Business Hours .................. <name> | 24×7
  Milestones ...................... <type name> — <minutes> min — <criteria>   (one line each)
  Entitlement ..................... Provisioned on activation (no Account)
  Actions ......................... <tier or type> — <Warning | Violation> — <offset>   (one line each)
  Scope ........................... Incident SLA only
```

Report only what read-back confirmed, name every artifact (never a record Id, even masked), and omit the
lines that don't apply. Case SLAs, Problem and Change Request policies, editing an existing policy,
assignment and escalation rules, and SLA reporting are outside this feature.

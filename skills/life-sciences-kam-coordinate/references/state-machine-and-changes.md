# Orchestration State Machine & Change Handling (KAM)

Operational reference for `life-sciences-kam-coordinate`: the idempotent stage-transition rules, the mid-flow change-request impact assessment, and the resume/partial-re-run protocol. Read this alongside the workflow in `SKILL.md`.

---

## Idempotent Stage Transitions

Stages are **not re-entrant**. If the user says "Proceed" or names a stage that is already running or completed, do NOT re-execute it.

### Behavior Matrix

| Current stage status | User says "Proceed" / "Run Stage N" | Response |
|---|---|---|
| `running` | Duplicate trigger | "Stage N is already in progress — I'll let you know when it completes." |
| `passed` | Re-run request | "Stage N already completed successfully. Would you like to re-run it anyway? This is safe (all stages are idempotent) but will take extra time." |
| `failed` | Retry request | Allow — re-run the stage (this is intentional recovery) |
| `pending` | Advance request | Allow — normal forward progression |

### Implementation Rules

1. **Before executing any stage**, check its current `status` in `OrchestrationState`.
2. **If `running`**: reply with the in-progress message and take no action. Do not queue a second execution.
3. **If `passed`**: ask for explicit confirmation before re-running. Only re-run if the user says "yes, re-run it".
4. **If `failed`**: treat as a retry — re-run without extra confirmation (the user is explicitly recovering).
5. **Accidental double-confirms** (user says "yes" or "proceed" twice in quick succession) must never cause a stage to execute twice. The `status` field is the single source of truth — transition to `running` at the START of execution, not on user input.

---

## Mid-Flow Change Requests (Impact Assessment)

If the user requests a change to inputs or decisions made in an earlier stage **while a later stage is in progress or pending**, perform an impact assessment before applying the change.

### When This Applies

- User wants to change the target org mid-flow
- User wants to change territory names after territories were already deployed
- User wants to change the KAM user's details after the profile/permsets were chosen
- User wants to switch which layouts or flexipages were selected after deploy
- User wants to change the ParticipantRole/Sprint, goal, or template names after they were created

### Impact Assessment Protocol

1. **Acknowledge the change request** without applying it immediately.

2. **Identify affected stages** — determine which completed or in-progress stages would be impacted:

   ```text
   Change Request Impact Assessment
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

   Requested change: <describe the change>

   Stages affected:
     Stage <N>: <StageName> — <what would need to change/redo>
     Stage <M>: <StageName> — <downstream impact>

   Stages NOT affected:
     Stage <X>: <StageName> — no impact

   Estimated rework: <time/effort to re-do affected stages>
   ```

3. **Present options** to the user:
   - **Apply change and re-run affected stages** — will undo/redo the impacted work
   - **Apply change for remaining stages only** — keep what's done, apply change going forward (if possible without inconsistency)
   - **Cancel the change** — continue with original inputs

4. **Wait for user decision** before taking any action.

### Impact Mapping

| Change | Affects Stages | Re-run Required | Notes |
|--------|--------------|-----------------|-------|
| Target org | All stages | Yes — full restart | Nothing from prior org transfers |
| Territory names | Stage 3, Stage 5, Stage 6 | Stage 3 re-deploy + Stage 5 re-associate + Stage 6 re-assign | Stage 5 `ProductTerritoryAvailability` and Stage 6 `UserTerritory2Association` both bind the level-3 territory; a new territory means re-doing both |
| Layout/flexipage selection | Stage 2 only | Re-deploy updated profile + app | Does not affect Stages 3-6 |
| KAM/Sprint config picklist values | Stage 2 only | Re-deploy config records | Upsert-safe |
| ParticipantRole / Sprint name | Stage 4 only | Stage 4 only | Both are simple record creates |
| Product / Account data | Stage 5 (Part A + Part B) | Stage 5 re-create + re-link | Part B `GoalDefinitionProduct` references the Part A `LifeSciMarketableProduct` |
| Goal / template names | Stage 5 (Part B) only | Stage 5 (Part B) only | Un-publish is not possible — see destructive warnings |
| User details (name, email, username) | Stage 6 only | Stage 6 only | Username must still contain `kam` |
| Permission set list | Stage 6 only | Stage 6 only | Can add/remove assignments (target set is exactly 4) |

### Destructive Change Warnings

Some changes cannot be fully undone:

| Change | Warning |
|--------|---------|
| Territory model already activated | "The territory model cannot be deleted once activated. A new model with a different name can be created, but the old one will remain." |
| ActionPlanTemplate already published (Final) | "A published template version cannot be un-published. A new version (or a new template) can be created, but the Final version remains." |
| User already created | "The existing user will remain. A new user with different details will be created as a separate record. Deactivate (never delete) any unwanted user; deactivation cascade-deletes its territory associations." |
| Config records already deployed | "Config records are upsert-safe — re-deploying with changes will update existing records, not create duplicates." |

Always surface these warnings as part of the impact assessment so the user makes an informed decision.

---

## Resume / Partial Re-run

If the user has already completed some stages (e.g., from a prior session):

1. Ask: "Have you already completed any of these stages?"
2. For each claimed-complete stage, **verify** by querying the org:
   - Stage 1: Ask user to confirm prerequisites are met
   - Stage 2: Query for `LSC Custom Profile`
   - Stage 3: Query for active territory model with level-3 territory
   - Stage 4: Query for `ParticipantRole` (DeveloperName `Rep_Execution_Specialist`) + a `Sprint`
   - Stage 5: Query for a `ProductTerritoryAvailability` (and Account) **and** a `Final` `ActionPlanTemplateVersion` + `ActionPlanTemplateAssignment`
   - Stage 6: Query for the user with username containing `kam` on `LSC Custom Profile`
3. Skip verified stages and resume from the first incomplete one.

(The exact detection queries per stage are in `orchestration-flow.md` → Resume Logic.)

# Orchestration State Machine & Change Handling

Operational reference for `life-sciences-fieldsalesrep-coordinate`: the idempotent stage-transition rules, the mid-flow change-request impact assessment, and the resume/partial-re-run protocol. Read this alongside the workflow in `SKILL.md`.

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
- User wants to change the new user's details after the profile/permsets were chosen
- User wants to switch which layouts or flexipages were selected after deploy

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
| Territory names | Stage 3, Stage 4 | Stage 3 re-deploy + Stage 4 re-assign | Existing model may need new territories added |
| User details (name, email, username) | Stage 4, Stage 5 | Stage 4 + Stage 5 re-login | Stage 5 logs in as this rep; a new user means re-authenticating |
| Profile choice | Stage 4 only | Stage 4 only | Profile must exist (from Stage 2) |
| Layout/flexipage selection | Stage 2 only | Re-deploy updated profile + app | Does not affect Stages 3-4 |
| Permission set list | Stage 4 only | Stage 4 only | Can add/remove assignments |

### Destructive Change Warnings

Some changes cannot be fully undone:

| Change | Warning |
|--------|---------|
| Territory model already activated | "The territory model cannot be deleted once activated. A new model with a different name can be created, but the old one will remain." |
| User already created | "The existing user will remain. A new user with different details will be created as a separate record." |
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
   - Stage 4: Query for the user with correct profile and permsets
   - Stage 5: Query for an existing `Visit` record (`SELECT Id FROM Visit LIMIT 1`)
3. Skip verified stages and resume from the first incomplete one.

(The exact detection queries per stage are in `orchestration-flow.md` → Resume Logic.)

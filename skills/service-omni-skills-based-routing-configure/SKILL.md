---
name: service-omni-skills-based-routing-configure
description: "Use to make agents routable by Omni skills-based routing: ensure an Omni Skill exists, then assign it to each active agent through the classic Omni-Channel SkillUser junction. Idempotent — existing skills and user bindings are reused, and only missing bindings are created. Works on Service Cloud orgs without requiring Field Service. Triggers: set up skills-based routing agents, assign Omni skills to agents, make agents skill-routable, create an Omni skill and bind users, repair missing agent skill assignments. Do not use to author WorkSkillRouting rules, create agent users, or configure queues."
allowed-tools: Bash Read Write Edit Glob Grep
metadata:
  version: "1.0"
  domains: ["Service"]
  minApiVersion: "66.0"
  relatedSkills:
    - "service-omni-agent-users-create"
    - "service-omni-base-settings-configure"
  accessCheck:
    - type: license
      value: ServiceCloud
  cliTools:
    - tool: ["jq"]
      semver: ">=1.6"
    - tool: ["python3"]
      semver: ">=3.8"
    - tool: ["sf"]
      semver: ">=2.139.6"
---

# service-omni-skills-based-routing-configure

Make agents routable by Omni **skills-based routing (SBR)**. A routable agent needs the **Skill** and a **SkillUser** junction assigning that skill to the agent's user. `SkillUser` is the classic Omni-Channel model written by Setup > Skills > Assign Users and evaluated when work has skill requirements. This skill ensures both, idempotently, for one skill across a set of active agent users.

`ServiceResource` and `ServiceResourceSkill` are the Field Service skill model. On a plain Service Cloud org, `ServiceResource.IsActive` is not writable or queryable, so a newly created resource remains inactive and the junction is rejected. This skill therefore uses the supported, license-appropriate `SkillUser` path.

## Inputs

```bash
bash scripts/configure-and-report.sh <org-alias> <skill_developer_name> [agent_members_csv] [skill_master_label]
```

- `org-alias` (required).
- `skill_developer_name` (required). The Omni `Skill` DeveloperName to ensure and bind (e.g. `Omni_Demo_Voice`).
- `agent_members_csv` (optional). Comma-separated agents to make skill-routable — each token a Username (`…@…`) or a 15/18-char User Id (`005…`). May also be supplied via `AGENT_MEMBERS_CSV`. When omitted, the skill blocks (it will not guess which agents to skill).
- `skill_master_label` (optional). MasterLabel used only when the skill must be created; defaults to a title-cased form of the DeveloperName.

## Preconditions and safety

- Target org authenticated via `sf` CLI, Service Cloud license, `sf` CLI ≥ 2.139.6.
- Omni-Channel base settings enabled with **skills-based routing** turned on (`service-omni-base-settings-configure`).
- The named agents exist and are active (`service-omni-agent-users-create`).
- The three-way `safe_to_write` production guard applies.

## Run

`configure-and-report.sh` proceeds in two idempotent phases, each detect-before-write:

1. **Skill** — query `Skill` by DeveloperName. Present → reused; absent → deploy a `Skill` component via the Metadata API and re-query for its Id.
2. **SkillUser** — query existing `SkillUser` records for the Skill and resolved users, then create only missing (`SkillId`, `UserId`) bindings via REST DML. A concurrent `DUPLICATE_VALUE` is reconciled as reused.

## Behavior

**Idempotent + non-destructive.** Existing skills and bindings are reused; the skill never deletes or reassigns anything it did not create, so re-runs converge without duplication. Only **active** users are resolved — an inactive user cannot be routed work, so it is reported rather than silently skilled.

**Partial safety.** If some bindings succeed and others fail, the status is `partial` with per-agent errors in `blocking_issue`; the successful bindings are left in place (each junction is an independent write).

## Output contract

A single JSON object: `status` ∈ `configured` | `reused` | `partial` | `blocked`, `skill` (`{developer_name, id, state}`), `agents` (array of `{username, user_id, skill_binding_id, skill_binding_state}`), `created_counts`, `reused_counts`, `manual_actions`, `blocking_issue`.

- `reused` — skill and all bindings already existed.
- `configured` — at least one component created and all requested bindings now exist.
- `partial` / `blocked` — see `blocking_issue`; `manual_actions` names the prerequisite skill when the cause is a missing precondition.

## Limitations

- One skill per invocation; run again per skill an agent set needs.
- Does not author `WorkSkillRouting` rules or field-based skill criteria — that is a separate skill.
- Does not create agent users, queues, or presence configuration.
- `SkillUser.SkillLevel` is left at the platform default; forking the DML body is required to set explicit proficiency.

## References

| File | When to read |
|---|---|
| `references/api-notes.md` | Skill metadata vs Skill sObject, the SkillUser agent-binding model, and SBR base-setting prerequisites |
| `scripts/tests/test_sbr_contracts.py` | When validating changes — run `python3 scripts/tests/test_sbr_contracts.py` from this skill directory |

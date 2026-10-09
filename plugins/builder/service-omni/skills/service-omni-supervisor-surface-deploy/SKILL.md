---
name: service-omni-supervisor-surface-deploy
description: "Use to populate the Omni-Channel Supervisor action + tab surface on an existing OmniSupervisorConfig by inserting the standard OmniSupervisorConfigAction and OmniSupervisorConfigTab companion rows via the Data API, idempotent (inserts only the missing types). Requires an OmniSupervisorConfig from service-omni-supervisor-config-deploy. Triggers: give the supervisor the standard action buttons and tabs, add Wallboard/Agents/Queues tabs to Omni Supervisor, configure supervisor actions like Change Queues/Skills. Do not use to create the supervisor configuration itself, create supervisor users, assign the supervisor permission set, or add custom-action / FlexiPage / AWS-dashboard / AI-agent surfaces (those need an external reference and must be set up in Setup)."
allowed-tools: Bash Read Write Edit Glob Grep
metadata:
  version: "1.0"
  domains: ["Service"]
  minApiVersion: "66.0"
  relatedSkills:
    - "service-omni-command-center-analyze"
    - "service-omni-supervisor-config-deploy"
    - "service-omni-supervisor-permset-assign"
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

# service-omni-supervisor-surface-deploy

Populate the Omni-Channel Supervisor **surface** — the action buttons and tabs a supervisor sees — on an existing `OmniSupervisorConfig`. `OmniSupervisorConfigAction` and `OmniSupervisorConfigTab` are createable child sObjects (`OmniSupervisorConfigId`, a `*Type` picklist, and `DisplayOrder`), so the surface is populated with plain Data API inserts against the parent config's Id rather than by re-deploying the whole `OmniSupervisorConfig` metadata document. That keeps this leaf independent of `service-omni-supervisor-config-deploy` (which owns the user/queue companions inside the metadata file) and lets it run idempotently — it inserts only the types that are missing.

## Inputs

`bash scripts/deploy-and-report.sh <org-alias> [config_developer_name]`

- `org-alias` (required) — must resolve via `sf org display --target-org <alias>`.
- `config_developer_name` (optional) — the `OmniSupervisorConfig.DeveloperName` to populate. Omit it when the org has exactly one config; the skill resolves it. With multiple configs and no name, the skill blocks and lists them.

Env overrides (both CSV of picklist values; defaults are the reference-free standard set):

- `SUPERVISOR_ACTIONS` — default `AllAgents.ChangeQueues,AllAgents.ChangeSkills,AllAgents.ChangeGroups,AllAgents.AssignLearning,QueuesBacklog.ManageQueues`.
- `SUPERVISOR_TABS` — default `Wallboard,Agents,QueuesBacklog,AssignedWork,SkillsBacklog`.
- `PLAN_ONLY=1` — report intent (existing vs. requested) and stop before any write.

## Preconditions and safety

- Target org authenticated via `sf` CLI, Service Cloud license present, `sf` CLI ≥ 2.139.6.
- An `OmniSupervisorConfig` exists — provisioned by `service-omni-supervisor-config-deploy`. If none exists (or the named one is absent), the skill blocks with a `target_skill` pointer.
- **Production guardrail:** the script computes `safe_to_write` as `IsSandbox` OR `TrialExpirationDate != null` OR `OrganizationType` in {Developer Edition, Base Edition}, and blocks with no override when it is false.

## Run

```bash
bash scripts/deploy-and-report.sh <org-alias> [config_developer_name]
```

It resolves the parent config, reads the surface rows already present, inserts only the missing action/tab types (appending `DisplayOrder` after the current maximum), and emits JSON to stdout.

## Behavior

**Reference-free types only.** The companion rows expose no reference field, so only self-contained types can be inserted headlessly. The skill accepts the standard set (`SAFE_ACTIONS` / `SAFE_TABS` in `references/api-notes.md`) and **blocks up front** on any type that needs an external reference — `*.CustomAction`, `*.AWSDashboard`, `FlexipageType`, `AIAgents`, `AgentforceSDR` — pointing you to Setup. Requesting a type outside the supported vocabulary also blocks before any write.

**Idempotency.** The requested types are diffed against the rows already on the config; existing types are reported as `reused` and never re-inserted, missing types are inserted and reported as `created`. `status` is `created` when anything was inserted, otherwise `reused`. Re-running the skill unchanged makes no writes.

**Ordering.** New rows are appended: `DisplayOrder` starts one above the current maximum for that companion type, preserving any ordering already configured in Setup.

## Output contract

A single JSON object to stdout. `status` is one of `created`, `reused`, `blocked`, or (with `PLAN_ONLY=1`) `action_needed`. The object also carries `config` (`developer_name`, `id`), `actions` and `tabs` (each with `requested`, `created`, `reused`, `count`), `manual_actions`, and `blocking_issue` (`null` unless `status: blocked`).

Org-side spot-check:

```sql
SELECT OmniSupervisorActionType, DisplayOrder FROM OmniSupervisorConfigAction WHERE OmniSupervisorConfigId = :configId ORDER BY DisplayOrder
SELECT OmniSupervisorTabType,    DisplayOrder FROM OmniSupervisorConfigTab    WHERE OmniSupervisorConfigId = :configId ORDER BY DisplayOrder
```

## Limitations

- Populates only the reference-free standard action and tab types. Custom actions, FlexiPage tabs, AWS dashboards, and AI-agent surfaces need an external reference and must be configured in Setup.
- Does not create, rename, or delete the parent `OmniSupervisorConfig`, its user/queue companions, or supervisor users/permission sets.
- Does not remove surface rows — it only adds missing ones (no destructive reconciliation).

## References

| File | When to read |
|---|---|
| `references/api-notes.md` | The full `OmniSupervisorActionType` / `OmniSupervisorTabType` vocabulary, which types are reference-free, and companion-row insert semantics |

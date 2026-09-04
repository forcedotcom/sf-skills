# Omni Supervisor surface (Action + Tab) - API notes

## What this leaf writes

Plain Data API inserts, one row per missing type:

- `OmniSupervisorConfigAction` - createable fields: `OmniSupervisorConfigId`, `OmniSupervisorActionType` (picklist), `DisplayOrder`.
- `OmniSupervisorConfigTab` - createable fields: `OmniSupervisorConfigId`, `OmniSupervisorTabType` (picklist), `DisplayOrder`.

Both are companions of `OmniSupervisorConfig`. Because they are createable child sObjects, the surface is populated without re-deploying the parent `OmniSupervisorConfig` metadata document - that document is owned by `service-omni-supervisor-config-deploy` and carries the user/queue companions. Splitting the surface into a Data API leaf keeps the two skills from fighting over the same whole-document metadata file.

## Why "reference-free types only"

Neither companion exposes a reference field in `describe` (only `OmniSupervisorConfigId`, the `*Type`, and `DisplayOrder` are createable). So a type that needs to point at something external cannot be expressed as a bare row and must be configured in Setup. This leaf blocks up front on:

- Action types matching `*.CustomAction` or `*.AWSDashboard`.
- Tab types `FlexipageType`, `AIAgents`, `AgentforceSDR`.

## OmniSupervisorActionType vocabulary (org-verified, API 66)

Reference-free (this leaf's `SAFE_ACTIONS`, and the default set):

- `AllAgents.ChangeQueues`
- `AllAgents.ChangeSkills`
- `AllAgents.ChangeGroups`
- `AllAgents.AssignLearning`
- `QueuesBacklog.ManageQueues`

Reference-required (blocked - configure in Setup): `AllAgents.CustomAction`, `AllAgents.AWSDashboard`, `AgentDetails.CustomAction`, `QueuesBacklog.CustomAction`, `QueuesBacklog.AWSDashboard`, `QueueDetails.CustomAction`, `AssignedWork.CustomAction`, `AssignedWork.AWSDashboard`, `AssignedWorkDetails.CustomAction`, `SkillsBacklog.CustomAction`, `SkillsBacklog.AWSDashboard`, `SkillDetails.CustomAction`.

## OmniSupervisorTabType vocabulary (org-verified, API 66)

Reference-free (this leaf's `SAFE_TABS`): `Wallboard`, `Agents`, `QueuesBacklog`, `AssignedWork`, `SkillsBacklog`, `Reports`, `Alerts`. The default set is the first five (the core supervisor panels); `Reports` and `Alerts` are accepted when requested explicitly.

Reference-required (blocked - configure in Setup): `FlexipageType`, `AIAgents`, `AgentforceSDR`.

## Idempotency and ordering

The requested types are diffed against the rows already on the config (`SELECT OmniSupervisorActionType/OmniSupervisorTabType ... WHERE OmniSupervisorConfigId = :id`). Existing types are reported `reused`; missing types are inserted. New `DisplayOrder` values start one above the current maximum for that companion, so ordering already configured in Setup is preserved and re-runs make no writes.

`DisplayOrder` is not required to be unique across rows; appending after the maximum simply keeps newly added items at the end of the supervisor's list.

## Related

- `service-omni-supervisor-config-deploy` - creates the parent `OmniSupervisorConfig` and its user/queue companions (prerequisite).
- `service-omni-supervisor-permset-assign` - grants supervisors the `ContactCenterSupervisor` permission set.
- `service-omni-command-center-analyze` - reports whether the org is on the classic supervisor surface vs. Command Center V2.

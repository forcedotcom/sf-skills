# Feature: Incident Management Preferences (inline execution)

How the orchestrator executes the **Preferences** feature — reading and setting the **six per-feature
Incident Management preferences** (the feature toggles on the Incident Management setup page). This runs
**inline** through the Salesforce-hosted **`headless-360`** MCP server (server key `headless-360`) via its
four meta-tools (`discover`, `describe`, `dispatch_readonly`, `dispatch`). The org comes from the OAuth JWT
on the MCP session — never handle an org id, alias, or credentials. Minimum API version **67.0**.

This is **not** the master Incident Management on/off switch (`service-itsm-incident-mgmt-configure`) nor
the Incident Priority Matrix (`service-itsm-incident-priority-configure`).

## Delegate to the Setup Operation Recipe

Every operation is delegated to a Setup Operation Recipe (SOR) and its exact shape is fetched at runtime:
`discover` the operation by intent, `describe` the SOR for its **current** steps, routes, argument schema,
the preference list, the on-screen labels, and its `agent_guidance`, then `dispatch_readonly` (reads) /
`dispatch` (writes). **Hardcode no routes, preference names, labels, or request bodies — use what
`describe` returns, and if it disagrees with anything here, `describe` wins.** Discover by intent, not by
id; a `discover` miss is not proof an operation is unavailable.

| SOR | Owns | Status |
|-----|------|--------|
| **`IncidentMgmt`** (owning team ITSM-Aditya; controller `IPCManagementSetupController`) | Read a preference; toggle a preference; verify a preference read-back | Served |

Discover by intent — e.g. `discover("configure ITSM incident management preferences: automatically triage
incidents, assign incidents with Einstein, enable rich text for incident descriptions")`.

> **Resolve the right node — load-bearing.** Two setup nodes share the "Incident" name. Target the
> **ITSM Incident Management org-preferences** node (controller `IPCManagementSetupController`) whose
> toggles are the six below — **not** the Service-Foundation "Incident Management" node
> (`IncidentMgmtSetupController`), whose toggles are broadcast/notification channels (Email/Sites/Alerts/
> Slack) and a master switch. If a `discover` result is about broadcast channels or a master on/off, it is
> the wrong node.

## Operations (shapes come from `describe`)

1. **Read a preference (read).** Given a preference name, return its Boolean state. Unknown names are **not
   validated on read** — they return `false` rather than raising — so only ever read a preference the SOR
   lists; a `false` read is not proof a name is valid.
2. **Toggle a preference (write — confirm first).** Set a named preference enabled/disabled. An unknown
   name raises. The two one-way preferences cannot be set to disabled.
3. **Verify (read).** Read the changed preference back and expect it to equal the value just set.

## The six preferences (name → label; `describe`/`agent_guidance` is authoritative)

| Preference name | Setup label | One-way |
|-----------------|-------------|---------|
| `IncidentValidationsEnabled` | Default Field Validations for Incidents | No |
| `AutoClosureChildIncidents` | Automatically Close Child Incidents | No |
| `IncidentTriageAgentEnabled` | Automatically Triage Incidents | No |
| `IncAssignWithAgentEnabled` | Assign Incidents with Einstein | No |
| `AssignedGroupValidationEnabled` | Restrict Assigned Group to Regular Groups | **Yes** |
| `RtaIncidentDescEnabled` | Enable Rich Text for Incident Descriptions | **Yes** |

Read the live list and labels from `describe` at runtime — this table is the authoring snapshot for trigger
phrasing and the known-name enumeration.

## Invariants — the contract

- **Two preferences are one-way / enable-only:** `RtaIncidentDescEnabled` and
  `AssignedGroupValidationEnabled`. Once enabled they cannot be disabled. Never offer to disable them;
  require an explicit "I understand this can't be undone" confirmation before enabling; never enable one
  merely to test.
- **`AssignedGroupValidationEnabled` also freezes once the org has any Incident record** — it is settable
  only while the org has no incidents. An enable can therefore **fail outright** when incidents already
  exist; surface pre-existing incidents as the likely cause and do **not** retry.
- **Read does not validate the preference name** (unknown → `false`, no error); only the write is
  allowlisted (unknown → raises). Enumerate only the six the SOR lists.
- **Access gate:** the caller needs `IncidentMgmt.userHasITSMSetupAccess` (sysadmin OR Customize
  Application + Modify All Data + View Setup). Without it every read and write is blocked by the controller.
- **Idempotent** — read before every write; skip a write when the preference is already in the requested
  state.
- **Verify by read-back** — the write response alone is not proof the change persisted.

## Preconditions

- **Setup access**: the caller needs ITSM setup access. Without it every read and write is blocked —
  surface the raw access error and stop.
- **Incident Management provisioned**: these preferences are writable only when Incident Management is
  enabled at the feature/license level. If reads or writes fail with an availability error, say the feature
  must be enabled first (`service-itsm-incident-mgmt-configure`) and stop.

## Workflow

The SOR's `agent_guidance` (returned by `describe`) carries the detailed flow and current labels; follow
it. In outline — **read before you write, confirm before every write, verify every write by read-back**,
and act only on the preferences the user chose:

1. **Read current state** — read each of the six preferences and report which are on and which are off,
   flagging the two one-way ones.
2. **Ask which to change** — never infer; for a one-way enable, take the explicit can't-be-undone
   confirmation here. On any non-yes, stop without writing.
3. **Apply only the chosen preferences** — skip any already in the requested state (idempotent no-op).
4. **Verify** — read each changed preference back; report success only when it read back as set.

## Clarifying questions

- **Which preference(s)?** If unstated, present the six (by label, flagging the two one-way) and let the
  user pick.
- **Enable or disable?** Required for a change; never infer direction from current state. Disable is not
  offered for the two one-way preferences.
- **Which org?** Confirm it and state plainly the org will be **modified**. For production, get explicit
  confirmation. Enabling a one-way preference is permanent.

## Output expectations

```text
  Default Field Validations for Incidents ...... On | Off
  Automatically Close Child Incidents .......... On | Off
  Automatically Triage Incidents ............... On | Off
  Assign Incidents with Einstein ............... On | Off
  Restrict Assigned Group to Regular Groups .... On | Off  (one-way)
  Enable Rich Text for Incident Descriptions ... On | Off  (one-way)

Changed: <label> Off → On (SUCCEEDED | ALREADY-ON | FAILED)
```

Report only what read-back confirmed. On a failure, stop and say — in plain language — what did not succeed
and what it means (e.g. "that setting can't be turned on once incidents exist").

## Common failures (surface in plain language)

| Symptom | Likely cause | What to tell the user |
|---------|--------------|-----------------------|
| Enable of "Restrict Assigned Group…" fails | The org already has Incident records (server freezes it) | That setting can only be turned on before any incidents exist; it can't be enabled now |
| Read/write blocked with an access error | Caller lacks ITSM setup access | An admin with setup access must make this change |
| Read/write unavailable on the org | Incident Management not enabled | Enable Incident Management first (`service-itsm-incident-mgmt-configure`) |
| Change didn't persist on read-back | Write did not take | Report it as failed and show the current state; do not claim success |
| `dispatch*` auth error | headless-360 session not authenticated / expired | Re-authenticate the connection and confirm it points at the intended org |

## Reading `dispatch` results

Responses come back wrapped as `{ status_code, body }`; read what you need from `body`. A preference read
returns a Boolean in `body`. A write success persists (no meaningful body). A service error on a write =
either a preference name outside the six, **or** a one-way freeze (e.g. `AssignedGroupValidationEnabled`
with incidents already present) — surface the specific cause, do not retry blindly. A `401` / `403` =
missing setup access or an unauthenticated session. A `404` = the operation is not available on this org
(feature not enabled).

## Dead ends — do NOT do these

- Write an HTTP route or a request body here — delegate to the SOR and let `describe` carry the shape.
- Offer to disable a one-way preference, or enable one just to "test" it.
- Read or write against the Service-Foundation `IncidentManagement` node (broadcast channels) — wrong node.
- Read or write any preference name the SOR does not list — an unknown name reads as `false` and is
  rejected on write.
- Toggle the **master** Incident Management switch here (`service-itsm-incident-mgmt-configure`) or the
  **Incident Priority Matrix** (`service-itsm-incident-priority-configure`).

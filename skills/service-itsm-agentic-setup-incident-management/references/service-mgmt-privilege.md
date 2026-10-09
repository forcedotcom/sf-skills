# Feature: Service Management Privilege (inline execution)

How the orchestrator executes the **Service Management Privilege** feature — ITSM **privilege escalation**
setup: the org-wide **escalation level**, the **Service Management Privilege** definitions (each with a
name, description, tag, access level, and function type), and **bulk employee ↔ privilege assignments**, all
behind the **Enable Privilege Assignment** master toggle. This runs **inline** through the Salesforce-hosted
**`headless-360`** MCP server (server key `headless-360`) via its four meta-tools (`discover`, `describe`,
`dispatch_readonly`, `dispatch`). The org comes from the OAuth JWT on the MCP session — never handle an org
id, alias, or credentials. Minimum API version **67.0**.

## Delegate every operation to the Setup Operation Recipe

The **Service Management Privilege Setup Operation Recipe (SOR)** is the single source of truth for **how**
each step is done — the route, method, request/response shape, field names, per-step `status`, and
`depends_on`. It is **draft and actively evolving**, so **never hardcode a route or request body**. Carry
only the **goal, scope, ordering, and invariants**, and at runtime:

1. `discover` the operation by intent (e.g. `"enable privilege assignment toggle"`, `"set ITSM escalation
   level"`, `"create a service management privilege"`, `"assign employees to a service privilege"`).
2. `describe` the returned SOR / operation for its **current** route, method, argument schema, and `status`.
3. `dispatch_readonly` (reads) / `dispatch` (writes) the route the SOR names.

**Use what `describe` returns — not any shape written here. If `describe` and this file disagree, `describe`
wins.** Read each step's `status` from `describe`: `implemented` = live; `proposed` = not served on every org
yet. **There is no public Connect / Tooling / Metadata / sObject substitute for this feature** — the setup
controller is the only surface. So if `discover`/`describe` does not surface a step or a `dispatch` returns
`404`, the surface is **not available on this org yet** — surface that plainly and stop; **never fabricate a
fallback route.**

## The four surfaces — SOR step map (targets for `describe`)

Describe each before calling; the step ids are stable handles, the shapes come from `describe`.

### Surface 1 — the Enable Privilege Assignment master toggle (`implemented`)

Backed by the generic **SetupMetadata** org-preference batch operations (not the privilege controller),
keyed on the org preference **`PrivilegeAssignmentEnabled`**.

| Step id | Purpose |
|---------|---------|
| `check-privilege-assignment-enabled` | Read whether `PrivilegeAssignmentEnabled` is on |
| `set-privilege-assignment-enabled` | Turn the feature on / off — **reversible** |
| `verify-set-privilege-assignment-enabled` | Read `PrivilegeAssignmentEnabled` back to confirm the write |

### Surface 2 — escalation level

| Step id | Purpose |
|---------|---------|
| `fetch-escalation-level` | Read the org-wide ITSM escalation level |
| `save-escalation-level` | Set the escalation level (`escalationLevel`) |
| `verify-save-escalation-level` | Read the level back to confirm |

### Surface 3 — Service Management Privilege definitions

| Step id | Purpose |
|---------|---------|
| `get-service-privileges` | List every privilege (id, name, description, tag, access level, function type) — **drives verify** |
| `create-service-privilege` | Add a privilege from a field map |
| `update-service-privilege` | Edit a privilege (field map keyed by its id) |
| `delete-service-privilege` | Remove a privilege by id — **destructive, no rollback** |

### Surface 4 — employee assignments

| Step id | Purpose |
|---------|---------|
| `save-privilege-assignments` | Bulk add / remove employees for one privilege (add-list + remove-list, both in one call) — **no read-back** |

## Scope

- **In scope**: read / set the **Enable Privilege Assignment** master toggle; read / set the org-wide
  **escalation level**; list / create / update / delete **Service Management Privilege** definitions; bulk
  **add / remove employee assignments** for a privilege; verify by read-back where one exists.
- **Out of scope**: base Incident Management enablement (`service-itsm-incident-mgmt-configure`); the
  Incident Fulfiller / Incident Manager **persona** PSG (the orchestrator's **Persona** feature); the Major
  Incident Manager approver licensing (the **Major Incident Management** feature); Problem / Change / Case
  Management; the Priority Matrix; SLA setup.

## Preconditions

- **ITSM setup access** — the SOR gates every route on it (`IncidentMgmt.userHasITSMSetupAccess`). A `403`
  means the acting user lacks it; an admin with ITSM setup access must perform this.
- **The Enable Privilege Assignment master toggle is the UI entry gate**, not a server precondition. The
  privilege controller does **not** re-check it, so turning it on is **workflow ordering** — enable it first
  so the escalation and privilege-management surfaces are coherent, but it does not hard-block the other
  writes. It is **reversible** (it can be turned back off — unlike the one-way incident preferences).

## Ordering (follow the SOR's `depends_on`)

1. **Toggle first** — if `PrivilegeAssignmentEnabled` is off and the user wants to configure the feature,
   enable it before touching escalation level or privileges (workflow ordering, not a hard gate).
2. **Read before every write** — the current toggle state, escalation level, or privilege list.
3. **Verify definition writes** — re-read via `get-service-privileges` after each create / update / delete.
4. **Assignments have no read-back** — you cannot confirm them by re-read; report them as **applied**, never
   as verified.

## Workflow

Always **read before you write**, **confirm before every write**, and **verify every write by read-back**
where a read-back exists.

1. **Preflight** — for each in-scope surface, `discover` and `describe` for the current route, schema, and
   `status`. On `401` / `403` / `404`, surface and stop.
2. **Read current state** — the toggle, the escalation level, and/or the current privileges.
3. **Confirm** — present the exact plan (org, toggle direction, escalation value, privilege change, or the
   employees to add/remove) via `AskUserQuestion`; require an explicit yes. On no, stop with no writes.
4. **Apply** — toggle first if needed; then the requested write. Treat a duplicate / already-set as success.
5. **Verify** — re-read the toggle, the escalation level, and the privilege list; for assignments, state
   plainly they were applied but cannot be read back.

## Clarifying questions

Ask only what you cannot infer: **which surface** (master toggle, escalation level, privilege definitions,
or employee assignments); for a **privilege**, its fields (name, description, tag, access level, function
type); for **assignments**, the target privilege and exactly which employees to add / remove; and **which
org** — state plainly this org will be **modified**. For production, get explicit confirmation.

## Output expectations

```text
Service Management Privilege
  Enable Privilege Assignment ....... On | Off | Enabled now
  Escalation level .................. <value> | Unchanged
  Privileges ........................ Created/Updated/Deleted <name> | N configured
  Employee assignments .............. Applied: +N / -M (not read-back verifiable)
```

Report only what read-back confirmed; for assignments, report them as applied and say they cannot be
verified by re-read. Omit lines for surfaces out of the requested scope.

## Common failures (surface in plain language)

| Symptom | Likely cause | What to tell the user |
|---------|--------------|-----------------------|
| `403` on any route | Acting user lacks ITSM setup access | An admin with ITSM setup access must perform this |
| `404` / step not discoverable | The surface is `proposed`, not served on this org yet | This feature isn't available on this org yet — there is no alternative API path |
| Delete rejected or unexpected | Wrong privilege id, or it no longer exists | Re-list privileges and confirm the exact one to remove |
| Assignment "done" but can't confirm | Assignments have no read-back | The change was applied; it cannot be confirmed by re-reading — check in Setup if needed |
| `dispatch*` auth error | headless-360 session not authenticated / expired | Re-authenticate the connection and confirm it points at the intended org |

## Dead ends — do NOT do these

- Hardcode any route / body — `discover` + `describe` at runtime; the SOR is draft and evolving.
- Fabricate a Connect / Tooling / Metadata / sObject fallback — **none exists**; a `404` means the surface
  isn't served on this org yet, so surface and stop.
- Delete a Service Management Privilege to test, or without an explicit confirmation — it is **irreversible**.
- Claim an employee assignment is **verified** — `save-privilege-assignments` has **no read-back**.
- Treat the Enable Privilege Assignment toggle as a hard server gate — it is the UI entry gate (reversible)
  and the controller does not re-check it; enabling it is workflow ordering.
- Pass `dispatch` the `{operation_id, arguments}` shape — it takes raw HTTP.

# Feature: Major Incident Management (inline execution)

How the orchestrator executes the **Major Incident Management (MIM)** feature. MIM setup is **two surfaces**
layered on top of base Incident Management: (1) the **major-incident approval group**, and (2) **two MIM org
preferences**. This runs **inline** through the Salesforce-hosted
**`headless-360`** MCP server (server key `headless-360`) via its four meta-tools (`discover`, `describe`,
`dispatch_readonly`, `dispatch`). The org comes from the OAuth JWT on the MCP session — never handle an org
id, alias, or credentials. Minimum API version **67.0**.

## Delegate every operation to the MIM Setup Operation Recipe

The **Major Incident Management Setup Operation Recipe (SOR)** is the single source of truth for **how**
each step is done — the route, method, request/response shape, field names, per-step `status`, and
`depends_on` ordering. It is **actively evolving**, so **never hardcode a route or request body**. Carry
only the **goal, scope, ordering, and invariants**, and at runtime:

1. `discover` the operation by intent (e.g. `"set major incident approval group"`, `"validate major
   incident approval group users"`, `"toggle major incident org preference"`).
2. `describe` the returned SOR / operation for its **current** route, method, argument schema, and `status`.
3. `dispatch_readonly` (reads) / `dispatch` (writes) the route the SOR names.

**Use what `describe` returns — not any shape written here. If `describe` and this file disagree, `describe`
wins.** A `discover` miss does not prove a route is absent — generic `/query` and `/sobjects/...` REST
routes are not always ranked first; only a `404` from the dispatch itself means a route is unavailable.
Read each step's `status` from `describe`: `implemented` = live; `proposed` = not served on every org yet.

> **MIM is configured by the two surfaces below.** The only feature that must be *on* first is **base**
> Incident Management (`service-itsm-incident-mgmt-configure`) — see Preconditions.

### Transports MIM uses (all via the same `dispatch*` tools)

| Transport | Shape of the `url` | Used by |
|-----------|--------------------|---------|
| **Aura controller** | `/headless/invoke/platform/mim/<method>` | approval-group + org-preference + group-user-validation routes |
| **sObject REST** | `/services/data/v67.0/sobjects/...` and `/services/data/v67.0/query` | license / public-group / member records used as **preconditions** |

`dispatch` takes **raw HTTP** — a full `url`, `method`, and optional `body`/`queryParams`, not
`{operation_id, arguments}`.

## Scope

- **In scope**: designating / clearing / reassigning the **major-incident approval group** (a User or a
  public Group); **group-user validation**; reading and toggling the **two** MIM org preferences; and, as a
  precondition, licensing approvers with the **Major Incident Manager permission-set license** and standing
  up the approvers **public group**. Verify every write by read-back.
- **Out of scope**: base Incident Management enablement
  (`service-itsm-incident-mgmt-configure` — a prerequisite); the Incident Fulfiller / Incident Manager
  **persona** PSG (the orchestrator's **Persona** feature — see `references/incident-persona-psg.md`);
  Problem / Change / Case Management; the Priority Matrix; SLA / entitlement setup; any MIM org preference
  **other than** the two allowlisted.

## Preconditions

The acting user needs **ITSM setup access** (the SOR gates every MIM route on it), and:

1. **Base Incident Management must be enabled** — MIM layers on it. If it is off, **stop and hand off** to
   `service-itsm-incident-mgmt-configure`; do not configure MIM without base Incident Management.
2. **Approvers must hold the Major Incident Manager permission-set license.** This is a **LICENSE** —
   granted via `PermissionSetLicenseAssign` (`{AssigneeId, PermissionSetLicenseId}`), **never** a
   `PermissionSetAssignment`. Group-user validation requires every direct and transitive user of a group
   approver to hold it. If a designated user lacks it (or the approvers group does not exist yet), prepare
   that first — this is **precondition prep, not MIM activation**. A **Regular** public group; add each
   **licensed** user; **license before membership**.

If a `dispatch*` returns `401` / `403` / `404`, do **not** fabricate state — surface the raw error and
stop. `403` usually means the acting user lacks ITSM setup access.

## The two surfaces — SOR step map (targets for `describe`)

Describe each before calling; the ids are stable handles, the shapes come from `describe`.

### Surface 1 — approval group

| Step id | Transport | Purpose |
|---------|-----------|---------|
| `validate-group-users` | Aura `PATCH .../validate-group-users` | Returns **true** only if every direct + transitive `005…` member of the group holds the Major Incident Manager license — **call before designating a Group** |
| `create-major-incident-approval-group` | Aura `PATCH .../create-major-incident-approval-group` | Designate the approver — a **User (005…)** or **public Group (00G…)** — stored as `SrvcMgmntApprovalAssignment` with `OperationType=MAJOR_INCIDENT_APPROVAL`. **Idempotent** (silent no-op if one exists) |
| `verify-approval-group` | Aura `GET .../get-major-incident-approval-group` | Read the designated approver back; expect it to equal the Id you set (null when none) |
| `remove-major-incident-approval-group` | Aura `DELETE .../remove-major-incident-approval-group` | Clear the designation — **run first to reassign** |

For a **Group** approver, run **group-user validation first**: it must return **true**. If false, fix
licensing / membership and re-validate; do not designate a group that fails. Designation is **idempotent** —
a create when one already exists is a **silent no-op**, so a "success" does not prove your approver is the
one set — **verify by read-back**, and **remove-first to reassign**.

### Surface 2 — org preferences

| Step id | Transport | Purpose |
|---------|-----------|---------|
| `get-mim-setup-page-org-preference` | Aura `GET .../get-mimsetup-page-org-preference` | Read one MIM preference's current boolean value |
| `toggle-mim-setup-page-org-preference` | Aura `PATCH .../toggle-mimsetup-page-org-preference` | Set one MIM preference on / off |

**Preference allowlist — exactly two names:** **`AutoCreationOfProblem`** and **`AutoClosureChildIncidents`**.
**Any other `prefName` raises a `ServiceException` without writing** — never pass a name outside this set.
Require an explicit on/off direction from the user (do not infer it).

## Ordering (follow the SOR's `depends_on`)

1. **License before membership** — a user holds the Major Incident Manager license before being added to
   the approvers group.
2. **Validate before designating a group** — `validate-group-users` must return **true** before
   `create-major-incident-approval-group` with a Group.
3. **Remove before reassign** — `remove-major-incident-approval-group` before a second create.

## Workflow

Always **read before you write**, **confirm before every write**, and **verify every write by read-back**.

1. **Preflight** — for each in-scope surface, `discover` and `describe` for the current route, schema, and
   `status`. On `401` / `403` / `404`, surface and stop.
2. **Prerequisites** — confirm base Incident Management is on (else hand off), and that the approver(s) hold
   the Major Incident Manager license (prepare it, and the public group, if needed).
3. **Read current state** — the current approval-group designation and each preference value.
4. **Confirm** — present the exact plan (org, approver, preference + direction) via `AskUserQuestion`;
   require an explicit yes. On no, stop with no writes.
5. **Apply** — validate-before-designate (for a group), remove-before-reassign; toggle only allowlisted
   preferences. Treat a duplicate / already-set as success.
6. **Verify** — re-read the designation and each preference; report only what read-back confirms.

## Clarifying questions

Ask only what you cannot infer: **which surface** (approval group, preferences, or both); **who** the
approver is (resolve to exactly one active User `005…` or a public Group `00G…`); **which preference and
on/off**; and **which org** — state plainly this org will be **modified** (designation, license assignment
which consumes a seat, group changes, preference writes). For production, get explicit confirmation.

## Output expectations

```text
Major Incident Management

  Approvers licensed (N) ............ Licensed N | M already held
  Approval group designated ......... <user/group> | Already designated | Reassigned
  Preferences ....................... Auto-create problem: on/off · Auto-close child incidents: on/off
```

Report only what read-back confirmed; omit lines for surfaces out of the requested scope. If base Incident
Management is off, say so and name `service-itsm-incident-mgmt-configure`.

## Common failures (surface in plain language)

| Symptom | Likely cause | What to tell the user |
|---------|--------------|-----------------------|
| Group validation returns false | A direct / nested member lacks the Major Incident Manager license | License every member first, then re-validate before designating the group |
| Approval group "designated" but unchanged | A designation already existed — it is idempotent | To change the approver, the old designation is removed first, then the new one set |
| Preference change rejected (`ServiceException`) | A preference name outside the allowlist was sent | Only auto-create problem and auto-close child incidents are configurable here |
| Seat / limit error on the license | No free Major Incident Manager seats | A seat must free up (or more licenses added) before that user can be an approver |
| `400 DUPLICATE_VALUE` on a license / group / member write | The record already exists | Idempotent success — report as already-done |
| `403` on a MIM route | Acting user lacks ITSM setup access | An admin with ITSM setup access must perform this |
| `dispatch*` auth error | headless-360 session not authenticated / expired | Re-authenticate the connection and confirm it points at the intended org |

## Dead ends — do NOT do these

- Hardcode any route / body — `describe` at runtime; the SOR is evolving.
- Grant the Major Incident Manager license with a `PermissionSetAssignment` — it is a **license**
  (`PermissionSetLicenseAssign`).
- Add a user to the approvers group before licensing them.
- Designate a **group** approver without `validate-group-users` returning **true** first.
- Reassign without removing the existing designation first (create is a silent no-op).
- Send any preference name other than `AutoCreationOfProblem` / `AutoClosureChildIncidents`.
- Attempt MIM setup when base Incident Management is off — hand off to `service-itsm-incident-mgmt-configure`.
- Pass `dispatch` the `{operation_id, arguments}` shape — it takes raw HTTP.

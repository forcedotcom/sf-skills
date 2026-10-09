# Feature: Incident Persona PSG Assignment (inline execution)

How the orchestrator executes the **Persona** feature — granting a **specific user** an ITSM Incident
Management **persona** by assigning the persona's **permission set group (PSG)** (the **Incident Fulfiller**
or **Incident Manager** bundle) together with the **backing permission-set licenses** its member permission
sets require. This runs **inline** through the Salesforce-hosted **`headless-360`** MCP server (server key
`headless-360`) via its four meta-tools (`discover`, `describe`, `dispatch_readonly`, `dispatch`). The org
comes from the OAuth JWT on the MCP session — never handle an org id, alias, or credentials. Minimum API
version **67.0**.

## Delegate to the Setup Operation Recipes

Every operation is delegated to a Setup Operation Recipe (SOR) and its exact shape is fetched at runtime —
`discover` by intent, `describe` the SOR step for its **current** route, method, and argument schema, then
`dispatch_readonly` (reads) / `dispatch` (writes). **Hardcode no routes, SOQL, or request bodies; use what
`describe` returns, and if it disagrees with anything here, `describe` wins.** Discover by intent, not by
id; a `discover` miss is not proof an operation is unavailable.

| SOR | Owns | Status |
|-----|------|--------|
| **`PermSetGroups`** (approved) | Assigning a PSG to a user; listing a user's PSG assignments | Served today |
| **ITSM incident-persona assignment SOR** | Resolving the incident persona PSGs; resolving the target user; resolving a PSG's member permission sets + their backing licenses; assigning the backing permission-set licenses; the license-seat check; read-back verification | Being onboarded separately. Until served, resolve these via the standard Salesforce Data API **by intent** — the objects and invariants are named below; never via a route written here |

Discover each by intent — e.g. `discover("assign a permission set group to a user")` for the assignment,
`discover("assign the backing permission-set licenses of an incident persona PSG")` for the license recipe.

> **Load-bearing trap the SOR does not encode.** Assigning the PSG *alone* sticks the assignment, but any
> permission in a member set whose backing **permission-set license (PSL)** the user lacks **never
> activates** — the persona is silently half-provisioned, and Salesforce does not auto-assign a PSG's
> member PSLs. **Assign the union of the member sets' backing PSLs first, then the PSG.** The PSL set
> differs per PSG and the Ids differ per org, so resolve it at runtime — never hardcode it.

## The two Incident Management persona PSGs

Both are Core-shipped in namespace `force` — query by `DeveloperName` with **no** `NamespacePrefix` filter
(which would exclude them). Resolve each PSG's Id, its member permission sets, and their backing license Ids
at **runtime**.

| Persona | PSG (`DeveloperName`) | Grants |
|---------|-----------------------|--------|
| Incident Fulfiller | `IncidentFulfillerPSG` | Work incidents as a fulfiller (incident + problem/change/release associators, major-incident proposer) |
| Incident Manager | `IncidentManagerPSG` | Manage the incident-management process and its records |

The **Major Incident Manager** PSG (`MajorIncidentManagerPSG`) is **out of scope** here (its approver
licensing is part of the orchestrator's **Major Incident Management** feature).

## Scope

- **In scope**: resolving which incident persona PSG(s) exist on the org; resolving the target user;
  resolving each chosen PSG's member permission sets and their backing licenses at runtime; checking
  existing assignments (idempotency); assigning the missing backing PSL(s) and then the PSG; verifying by
  read-back.
- **Out of scope**: the **Major Incident Manager** PSG; creating / editing / recalculating a PSG or its
  membership; enabling ITSM / incident-management features (`service-itsm-incident-mgmt-configure`); the
  `IncidentFulfiller` permission **set** for the Fulfiller **agent's** access
  (`service-itsm-agentic-setup-itsm-agentforce-permset-assign`); CMDB access
  (`service-itsm-agentic-setup-cmdb-access-assign`); generic, non-incident permission-set / PSG assignment
  (`dx-org-permission-set-assign`).

## Preconditions

- **ITSM Incident Management must be provisioned** — the incident persona PSGs must exist on the org. If
  neither is found, **stop and hand off** to `service-itsm-incident-mgmt-configure`; assign nothing.
- **The acting user must be able to assign permission sets** (the SOR gates writes on it). A write that
  fails with an access error that is not a duplicate → surface it plainly and stop; an admin must do it.
- **Each backing license consumes a seat.** A seat-exhausted license blocks that persona; report it.

## Operations (shapes come from `describe`)

1. **Resolve which incident persona PSGs exist (read).** Look up the two PSGs by `DeveloperName`
   (`IncidentFulfillerPSG`, `IncidentManagerPSG`) with **no `NamespacePrefix` filter**. None found → hand
   off to `service-itsm-incident-mgmt-configure` and stop. Capture each PSG's Id and status.
2. **Resolve the target user (read).** To exactly one active user. For "me" / "the current user", read the
   API root's identity (the running user's `005…` Id) — **not** the `USER_ID()` SOQL function (Apex-only)
   and **not** the Chatter current-user endpoint (fails when Chatter is off). Zero / multiple → disambiguate.
3. **Resolve the chosen PSG's member licenses (read).** From the PSG's member permission sets, collect the
   **distinct, non-null backing permission-set-license Ids** — the link is each member permission set's
   `LicenseId`. Do **not** traverse the license's `Name`/`DeveloperName` from the member (that relationship
   rejects); resolve the license label separately by Id. No members → the bundle is empty; surface and stop.
4. **Check existing assignments (read — idempotency).** Whether the PSG is already assigned, and which
   backing licenses the user already holds. Write only what is missing.
5. **Assign the missing backing licenses, then the PSG (write — confirm first).** Assign each **missing
   backing license first**, then the PSG (keyed on `PermissionSetGroupId`). A duplicate = already-assigned
   (idempotent success). A seat/limit error on a license = exhausted; stop and report — do not retry.
6. **Verify (read).** Re-read the PSG assignment and every backing license for the user, and re-read the
   PSG's status. Provisioned only when all read back. If `Status` is still `Updating`, tell the user
   effective permissions are settling and will be active shortly.

If the user picks **both** personas, run steps 3–6 once **per PSG** (the bundles have different member
licenses) and report each.

## Invariants — the contract (these do NOT come from `describe`)

- **Assign the backing licenses before the PSG — correctness ordering, not a platform gate.** The PSG
  sticks on its own, but any member-set permission whose backing license the user lacks **never activates**.
  Salesforce neither rejects the PSG assignment for a missing license nor auto-assigns the licenses.
- **A PSG assignment keys on the permission-set-*group* Id, never a permission-set Id.**
- **Query the persona PSGs by `DeveloperName` with no `NamespacePrefix` filter** (namespace `force`).
- **Idempotent** — read before every write; a duplicate is already-assigned success, not a failure.
- **The PSG recalculates asynchronously** after an assignment; effective permissions can be stale until its
  status settles.
- **Verify by read-back** — the write response alone is not proof (half-provisioning / recalculation).
- **Resolve the backing-license set at runtime** — it differs per PSG and Ids differ per org; never hardcode.

## Clarifying questions

- **Which user?** A username / name / email resolving to exactly one active user; for "me", the running user.
- **Which persona(s)?** For a generic request, do **not** auto-select — present an `AskUserQuestion` menu of
  the incident PSGs that **exist on the org** (Fulfiller = work incidents; Manager = manage the process),
  multi-select (one or both). Never offer the Major Incident Manager PSG.
- **Which org?** Confirm it and state plainly the org will be **modified** (a PSG + licenses are writes;
  each license consumes a seat). For production, get explicit confirmation.

## Output expectations

```text
Incident Management Persona Assignment
User:    <name> (<username>)
Persona: <Incident Fulfiller | Incident Manager>

  Persona bundle .................... Assigned | Already had it
  Backing licenses (N) .............. Assigned N | M already held
  Effective permissions ............. Active | Recalculating (settles shortly)
```

Repeat the `Persona:` block per PSG if both were chosen. Report only what read-back confirmed. If the
personas are not on the org, say so and name `service-itsm-incident-mgmt-configure`.

## Common failures (surface in plain language)

| Symptom | Likely cause | What to tell the user |
|---------|--------------|-----------------------|
| No incident PSG on the org | ITSM Incident Management not provisioned | The incident personas aren't set up yet — that's a separate step (`service-itsm-incident-mgmt-configure`) |
| Duplicate on assign | User already has that grant | Not an error — report as already assigned |
| Seat / limit error on a license | An incident license has no free seats | A seat must free up (or more licenses added); the persona is incomplete without it |
| PSG assigned but some actions missing | A backing license wasn't assigned, or the PSG is still recalculating | Confirm every backing license is assigned; if it's settling, retry in a moment |
| Access error on the PSG write (not a duplicate) | Acting user can't assign permission sets | An admin must grant that or perform the assignment |
| `dispatch*` auth error | headless-360 session not authenticated / expired | Re-authenticate the connection and confirm it points at the intended org |

## Reading `dispatch` results

Responses come back wrapped as `{ status_code, body }`; read what you need from `body`. A write success is a
created record. A `400` carrying a duplicate code = already-assigned (treat as success). A seat/limit error
on a license = no free seats (report used-vs-total; do not retry). An access error that is **not** a
duplicate on the PSG write = the acting user can't assign permission sets (an admin must). A `404` = the
operation isn't available on this org.

## Dead ends — do NOT do these

- Assign the PSG with a permission-set Id — a PSG assignment keys on the group Id.
- Assign the PSG without its members' backing licenses — it silently half-provisions the persona.
- Hardcode the backing-license list, or add a `NamespacePrefix` filter to the PSG lookup.
- Create, edit, or recalculate the PSG or its membership — this feature only **assigns** the standard
  incident PSGs.
- Retry a write that failed with a seat/limit error — the shortage is real; surface it.
- Write a route, SOQL string, or request body here — delegate to the SOR and let `describe` carry the shape.

---
name: service-itsm-agentic-setup-uel-user-create
description: "Provision and enable a Unified Employee License (UEL) user in Salesforce with the full entity chain — User, Person Account, PersonContact, and Employee2 — through the Salesforce-hosted headless-360 MCP server. Use when the user asks to create a UEL user, set up a Unified Employee user account, enable an employee under the Unified Employee license, provision an employee with Person Account and Employee2 record, or onboard a new employee onto the Unified Employee profile. Triggers on: create UEL user, set up unified employee, provision unified employee, enable UEL employee, onboard employee user, create person account for employee. DO NOT TRIGGER when: the user asks to create a standard user without UEL, clone an existing user, manage existing user permissions only, assign incident permissions only, reset passwords only, or look up existing users without creation intent."
metadata:
  version: "2.1"
  domains: ["Service"]
  minApiVersion: "67.0"
  mcpTools:
    headless-360:
      tools: ["discover", "describe", "dispatch", "dispatch_readonly"]
      semver: ">=1.0.0"
  accessCheck:
    - type: "userPerm"
      value: "ManageUsers"
    - type: "userPerm"
      value: "ManageProfilesPermissionsets"
    - type: "userPerm"
      value: "CustomizeApplication"
    - type: "userPerm"
      value: "AssignPermissionSets"
allowed-tools: |
  Read AskUserQuestion
  mcp__headless-360__discover
  mcp__headless-360__describe
  mcp__headless-360__dispatch_readonly
  mcp__headless-360__dispatch
---

# Create and Enable a Unified Employee (UEL) User

Provision an employee under the Unified Employee License (UEL) by creating and linking a `User`
on the Unified Employee license/profile, a Person `Account` (with an auto-generated `Contact`), and
an `Employee2` record, then assigning the required permission sets. Every operation runs through
the **Salesforce-hosted headless-360 MCP server** (server key `headless-360`) via its four
meta-tools (`discover`, `describe`, `dispatch_readonly`, `dispatch`). The org is derived from the
OAuth JWT bound to the current MCP session — the skill never handles an org id, alias, or
credentials — so the flow behaves identically against **production** and sandbox with no per-user
MCP install.

## Scope

- **In scope**: Creating a new UEL User, Person Account, Employee2 record; assigning permission
  sets; verifying the full chain.
- **Out of scope**: Standard user creation (non-UEL); cloning existing users; managing existing
  user permissions only; deactivating users; license assignment changes.

---

## Routes at a glance

Reads dispatch through `mcp__headless-360__dispatch_readonly`; writes through
`mcp__headless-360__dispatch`. Both take raw HTTP:
`{"url": "<path>", "method": "GET|POST", "body"?: {...}, "queryParams"?: {...}}`. Full URL paths and
request/response bodies for every row live in `references/mcp-invocation.md`; this table lists only
the operation and HTTP method.

| Concern | Method + operation | Notes |
|---------|--------------------|-------|
| Unified Employee license | `GET /query` (UserLicense) | Zero rows → stop |
| Unified Employee profile | `GET /query` (Profile) | Zero rows → stop |
| Person Account record type | `GET /query` (RecordType, IsPersonType) | Zero rows → stop |
| Employee Hub perm set | `GET /query` (PermissionSet) | Mandatory; zero rows → stop |
| Employee2 accessible | `GET /sobjects/Employee2/describe` | 200 = HR module enabled |
| Resolve manager | `GET /query` (User by Username/Name) | Active users only |
| Create user | `POST /sobjects/User` | Profile = Unified Employee |
| Assign Employee Hub set | `POST /sobjects/PermissionSetAssignment` | Mandatory |
| Create Person Account | `POST /sobjects/Account` | `PersonEmail` required |
| Read PersonContact | `GET /query` (Account) | Capture `PersonContactId` |
| Create Employee2 | `POST /sobjects/Employee2` | Use `UserId`/`ContactId` field names |
| Verify chain | `GET /query` | User + Account + Employee2 + perm sets |

**Response envelope**: `describe`, `/query`, and `/sobjects/…` are all standard REST — the
`dispatch*` tool returns the HTTP status plus the parsed body: `{ "status_code": 200, "body": <REST
response> }`. Read `body`. A create returns `body.id` and `body.success == true`; a query returns
`body.records[]`. Status codes: `200/201` success; `400` bad body (re-check schema via `describe`);
`401`/auth error the MCP session needs re-auth; `404` the endpoint/impl is not present on this org;
`500` a downstream dependency issue.

---

## Required Inputs

Collect from the user (ask only what is not already in conversation context):

### Identity (required)

| Field | Description |
|-------|-------------|
| `FirstName` | Employee first name |
| `LastName` | Employee last name |
| `Email` | Employee email address |

### Credentials & Locale (required)

| Field | Description | Example |
|-------|-------------|---------|
| `Username` | Email-formatted, globally unique | `jane.doe@company.uel.com` |
| `Alias` | Max 8 chars | `jdoe` |
| `TimeZoneSidKey` | Timezone | `America/Los_Angeles` |
| `LocaleSidKey` | Locale | `en_US` |
| `LanguageLocaleKey` | Language | `en_US` |
| `EmailEncodingKey` | Email encoding | `UTF-8` |

### Manager (optional)

| Field | Description |
|-------|-------------|
| `ManagerName` or `ManagerUsername` | Resolve to ManagerId via SOQL |

### HR Attributes for Employee2 (required)

| Field | Description |
|-------|-------------|
| `Department` | Employee department |
| `Location` | Employee location |
| `EmployeeNumber` | HR employee number |
| `Title` | Job title |
| `HireDate` | Date format: YYYY-MM-DD |

### Permission Sets

`Employee Hub Unified Employee User` (`EmployeeHubEmployeeUser`) is **always assigned** — no other
permission sets belong on a UEL user. If the caller asks for extras (Incident Fulfiller, Case
Agent, or any other fulfiller/agent-role set), decline: those are for **fulfillers** on the Service
Cloud side, not for **requesters** who log into the Employee Hub. Point the caller at the
appropriate fulfiller user-create flow instead of extending this one.

---

## Workflow

All steps are sequential. **Always read before you write.** Every call goes through
`mcp__headless-360__*` tools. Stop and report if any step fails.

### Phase 1 — Preflight & discovery

**On any `401` / `403` / `404` from a `discover` / `describe` / `dispatch` / `dispatch_readonly` call below, halt and surface the raw error** — the org or client is not configured correctly. `401` → headless-360 MCP client not authenticated to `CORE_ORG_ALIAS` (session expired). `403` → executing user is missing one of the required perms (`ManageUsers`, `ManageProfilesPermissionsets`, `CustomizeApplication`, `AssignPermissionSets`) OR the org lacks the Unified Employee License. `404` → the target sObject / route is not available (HR module / UEL not provisioned — surfaces separately as the five prerequisite checks in step 2).

1. **Discover the operations** — `mcp__headless-360__discover(query="create User Account Employee2 sObject")`
   and `mcp__headless-360__describe(id=<operation_id>)` for the `POST /sobjects/User`,
   `POST /sobjects/Account`, and `POST /sobjects/Employee2` operations to confirm they are indexed
   and pull the input schema. A `discover` miss does **not** mean the route is absent — the
   `/sobjects/…` REST endpoints are core Data API paths and can be invoked directly with
   `dispatch_readonly` / `dispatch` against the exact URL (see `references/mcp-invocation.md`). If a
   direct `dispatch_readonly` probe at the documented path also fails (404), direct the user to the
   Setup UI.
2. **Verify all five UEL prerequisites** (all read-only `/query` or describe). If any fails,
   **stop** and report exactly which prerequisite is missing:
   - Unified Employee **license** exists → else "Unified Employee license not found in this org."
   - Unified Employee **profile** exists → else "Unified Employee profile not found. Ensure UEL license is provisioned."
   - Active **Person Account record type** exists → else "No active Person Account record type found. Enable Person Accounts in Setup."
   - **Employee Hub** permission set exists → else "Employee Hub Unified Employee User permission set not found. This is required for UEL provisioning."
   - **Employee2** describe returns 200 → else "Employee2 sObject not accessible. Ensure the HR module is enabled."

   Capture: `UnifiedEmployeeProfileId`, `PersonAccountRecordTypeId`, `EmployeeHubPermSetId`.

### Phase 2 — Resolve references

3. **Resolve the manager** — when the user supplied a manager, query by Username or Name (active
   users only). On multiple matches, present options and ask the user to disambiguate. Capture
   `ManagerId`. When no manager was supplied, skip this step.
4. **Check username uniqueness** — query `User` by `Username`; any record → **stop**, username taken.

### Phase 3 — Confirm & create the chain

5. **Confirm the plan** — present the full configuration (including HR attributes) and wait for
   explicit confirmation before any mutation.
6. **Create the User** — `POST /sobjects/User` with identity, locale, `ProfileId` =
   `UnifiedEmployeeProfileId`, and `ManagerId` (omit `ManagerId` when none). Capture `NewUserId`.
7. **Assign the Employee Hub permission set (mandatory)** — `POST /sobjects/PermissionSetAssignment`
   with `{AssigneeId: NewUserId, PermissionSetId: EmployeeHubPermSetId}`. If this fails, **stop** and
   report the exact error — the set exists (verified) but may be incompatible with the license.
8. **Create the Person Account** — `POST /sobjects/Account` with `FirstName`, `LastName`,
   `PersonEmail` (**required**), and `RecordTypeId` = `PersonAccountRecordTypeId`. Capture
   `NewAccountId`. `PersonEmail` must be set: the Employee2 validation hook rejects the record when
   the linked PersonContact is missing `Email` or `LastName`.
9. **Verify the PersonContact** — query the Account for `IsPersonAccount` and `PersonContactId`.
   Confirm `IsPersonAccount = true` and capture `PersonContactId`. If it is null, **stop** and
   report failure to generate the PersonContact.
10. **Create the Employee2 record** — `POST /sobjects/Employee2` with `UserId` = `NewUserId`,
    `ContactId` = `PersonContactId`, and the HR attributes. Use the foreign-key field names
    `UserId`/`ContactId` (not the relationship names `User`/`Contact`). Capture `NewEmployee2Id`.

### Phase 4 — Verify & present

11. **Verify the full chain** — query the Account (IsPersonAccount, PersonContactId), the User
    (IsActive, ProfileId, ManagerId), the Employee2 (UserId, ContactId), and confirm the Employee
    Hub permission set is the only PermissionSetAssignment (beyond the profile).
12. **Report** using the output format below.

---

## Rules / Constraints

| Constraint | Rationale |
|-----------|-----------|
| Verify all five prerequisites before any mutation | Prevents partial state when the org is not configured for UEL |
| Always `describe` before a `POST` | You need the exact input schema for each sObject |
| Confirm the plan with the user before creating records | Prevents unintended record creation |
| `PersonEmail` is required on Person Account create | The Employee2 validation hook rejects a PersonContact with no Email |
| Use `UserId`/`ContactId` field names on Employee2 | The API rejects bare IDs under the relationship names |
| `Employee Hub Unified Employee User` is the ONLY permset assigned | UEL users are Employee Hub requesters, not fulfillers/agents — no other permsets are compatible |
| Omit null/empty foreign keys from create bodies | The API rejects an explicit empty `ManagerId` |
| Display the exact error from `dispatch*` on failure | Helps diagnose issues |
| Never show Salesforce record IDs to the user | Use human-readable names only |

---

## Permissions Required

The executing admin user (the identity behind `CORE_ORG_ALIAS`) must have:

| Permission | Purpose |
|-----------|---------|
| Manage Internal Users | Create User records |
| Manage Profiles and Permission Sets | Assign permission sets |
| Customize Application | Create Employee2 and Person Account records |
| Assign Permission Sets | Create PermissionSetAssignment records |

---

## Verification Checklist

- [ ] Did `discover` + `describe(id)` (or, on a `discover` miss, a direct `dispatch_readonly` probe at the documented `/sobjects/…` path) confirm the User / Account / Employee2 create operations?
- [ ] Did all five UEL prerequisites pass (license, profile, Person Account RT, Employee Hub set, Employee2)?
- [ ] Did you confirm the username is unique and confirm the plan before any mutation?
- [ ] Is `Account.IsPersonAccount = true` with a non-null `PersonContactId`?
- [ ] Is `User.IsActive = true` on the Unified Employee profile (and manager, if provided)?
- [ ] Does `Employee2` link `UserId` and `ContactId` correctly?
- [ ] Is `Employee Hub Unified Employee User` the only permission set assigned (no fulfiller-side extras)?

---

## Output Format

On **failure**, display the error from `dispatch*` exactly as returned.

On **success**:

```text
UEL User Provisioning Complete (via service-itsm-agentic-setup-uel-user-create)

User:
  Name:     <FirstName> <LastName>
  Username: <Username>
  Email:    <Email>
  Profile:  Unified Employee
  Manager:  <ManagerName> (or "not set")
  Status:   Active

Person Account:
  Account Name: <FirstName> <LastName>
  Person Contact: linked

Employee Record:
  Department:    <Department>
  Title:         <Title>
  Location:      <Location>
  Employee No:   <EmployeeNumber>
  Hire Date:     <HireDate>

Permission Set Assigned:
  - Employee Hub Unified Employee User

Chain: User > Person Account > PersonContact > Employee2 > Employee Hub permset
```

No record IDs in user-facing output — use human-readable names only.

---

## Reference File Index

| File | When to read |
|------|--------------|
| `references/mcp-invocation.md` | Every phase — exact `mcp__headless-360__*` call shapes, the five prerequisite queries, the create bodies for the full chain, response envelope, discovery, and gotchas |

---

## Related Skills

This skill provisions a **Unified Employee License (UEL)** user with the full entity chain. Two
adjacent flows are out of scope: creating a **standard** (non-UEL) user, and **cloning** an existing
user's full access configuration. Handle those requests separately — this skill does not cover them.

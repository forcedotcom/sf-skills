# MCP Invocation Reference — UEL User Create

Every operation dispatches through the **Salesforce-hosted `headless-360`** MCP server, which
exposes four meta-tools:

- `mcp__headless-360__discover(query)` — semantic search over the indexed operation catalog
- `mcp__headless-360__describe(id)` — pull the schema and canonical route for one operation
- `mcp__headless-360__dispatch_readonly({url, method, queryParams?, body?})` — GET / read-only HTTP
- `mcp__headless-360__dispatch({url, method, body?, queryParams?})` — POST / PATCH / DELETE HTTP

**Dispatch takes raw HTTP**, not `{operation_id, arguments}`. Give it the full `url`
(`/services/data/v67.0/...`), `method`, optional `body`, and optional `queryParams` (camelCase — the
tool rejects `query_params`) — the server signs the request with the JWT bound to the current MCP
session and forwards it to the org. The skill never handles credentials or an org alias — everything
is derived from the session.

**A `discover` miss does NOT mean the route is absent.** The `/sobjects/…` REST endpoints and the
SOQL `/query` route this skill uses are documented core Data API paths and can be dispatched
directly. Only if the direct `describe`/`dispatch_readonly` at the exact path itself returns 404
should you treat the route as unavailable on this org.

## Response envelope

`describe`, `/query`, and `/sobjects/…` are all **standard REST**. The `dispatch*` tool returns the
HTTP status plus the parsed body:

```json
{ "status_code": 200, "body": <REST response> }
```

Read `body`. A create returns `{ "id": "...", "success": true, "errors": [] }`; a query returns
`{ "totalSize": N, "records": [...] }`. Status codes: `200/201` success; `400` bad body (re-check
schema via `describe`); `401`/auth error — the MCP session needs re-auth; `404` route not present
on this org; `500` a downstream dependency issue.

---

## Routes

| Method + path | Purpose |
|---------------|---------|
| `GET  /services/data/v67.0/query` | Prerequisites, manager, uniqueness, verify (`queryParams.q`) |
| `GET  /services/data/v67.0/sobjects/Employee2/describe` | Prerequisite: HR module enabled |
| `POST /services/data/v67.0/sobjects/User` | Create the UEL user |
| `POST /services/data/v67.0/sobjects/Account` | Create the Person Account |
| `POST /services/data/v67.0/sobjects/Employee2` | Create the Employee2 record |
| `POST /services/data/v67.0/sobjects/PermissionSetAssignment` | Assign a permission set |

Minimum API version is **67.0**.

---

## Discovery — always run first

```text
mcp__headless-360__discover(query="create User Account Employee2 sObject")
```

Call `mcp__headless-360__describe(id=<operation_id>)` for the `POST /sobjects/User`,
`POST /sobjects/Account`, and `POST /sobjects/Employee2` operations to confirm they are indexed and
pull the exact input schema. A `discover` miss is not fatal — dispatch directly at the exact
`/sobjects/<Name>` path (these are core Data API routes). If a direct call at the documented path
also fails, direct the user to the Setup UI.

---

## Phase 1 — Verify the five UEL prerequisites

Run all five before any mutation. If any fails, stop and report exactly which one. Read
`body.records[]` (or the describe status). Capture the Ids noted below.

**1. Unified Employee license** — zero rows → stop:

```text
dispatch_readonly({
  "url":         "/services/data/v67.0/query",
  "method":      "GET",
  "queryParams": { "q": "SELECT Id, Name FROM UserLicense WHERE Name = 'Unified Employee' LIMIT 1" }
})
```

**2. Unified Employee profile** — zero rows → stop. Capture `UnifiedEmployeeProfileId`:

```text
dispatch_readonly({
  "url":         "/services/data/v67.0/query",
  "method":      "GET",
  "queryParams": { "q": "SELECT Id, Name FROM Profile WHERE Name = 'Unified Employee' LIMIT 1" }
})
```

**3. Active Person Account record type** — zero rows → stop. Capture `PersonAccountRecordTypeId`:

```text
dispatch_readonly({
  "url":         "/services/data/v67.0/query",
  "method":      "GET",
  "queryParams": { "q": "SELECT Id, Name FROM RecordType WHERE SObjectType = 'Account' AND IsPersonType = true AND IsActive = true LIMIT 1" }
})
```

**4. Employee Hub permission set** — zero rows → stop. Capture `EmployeeHubPermSetId`:

```text
dispatch_readonly({
  "url":         "/services/data/v67.0/query",
  "method":      "GET",
  "queryParams": { "q": "SELECT Id, Name, Label FROM PermissionSet WHERE Name = 'Employee_Hub_Unified_Employee_User' OR Label = 'Employee Hub Unified Employee User' LIMIT 1" }
})
```

**5. Employee2 accessible** — describe must return 200 (HR module enabled):

```text
dispatch_readonly({
  "url":    "/services/data/v67.0/sobjects/Employee2/describe",
  "method": "GET"
})
```

---

## Phase 2 — Resolve manager + uniqueness

**Resolve manager (if provided)** — by Username, or by Name (disambiguate on multiple):

```text
dispatch_readonly({
  "url":         "/services/data/v67.0/query",
  "method":      "GET",
  "queryParams": { "q": "SELECT Id, Name FROM User WHERE Username = '<ManagerUsername>' AND IsActive = true LIMIT 1" }
})

dispatch_readonly({
  "url":         "/services/data/v67.0/query",
  "method":      "GET",
  "queryParams": { "q": "SELECT Id, Name, Username FROM User WHERE Name = '<ManagerName>' AND IsActive = true" }
})
```

**Check username uniqueness** — any record → stop, the username is taken:

```text
dispatch_readonly({
  "url":         "/services/data/v67.0/query",
  "method":      "GET",
  "queryParams": { "q": "SELECT Id FROM User WHERE Username = '<Username>' LIMIT 1" }
})
```

---

## Phase 3 — Create the chain

### 1. Create the User

```text
dispatch({
  "url":    "/services/data/v67.0/sobjects/User",
  "method": "POST",
  "body": {
    "FirstName":         "<FirstName>",
    "LastName":          "<LastName>",
    "Email":             "<Email>",
    "Username":          "<Username>",
    "Alias":             "<Alias>",
    "ProfileId":         "<UnifiedEmployeeProfileId>",
    "TimeZoneSidKey":    "<TimeZoneSidKey>",
    "LocaleSidKey":      "<LocaleSidKey>",
    "LanguageLocaleKey": "<LanguageLocaleKey>",
    "EmailEncodingKey":  "<EmailEncodingKey>",
    "ManagerId":         "<ManagerId>"          // OMIT this key entirely when no manager
  }
})
```

Capture `body.id` as `NewUserId`.

### 2. Assign the Employee Hub permission set (mandatory)

```text
dispatch({
  "url":    "/services/data/v67.0/sobjects/PermissionSetAssignment",
  "method": "POST",
  "body":   { "AssigneeId": "<NewUserId>", "PermissionSetId": "<EmployeeHubPermSetId>" }
})
```

If this fails, stop — the set exists but may be incompatible with the license.

### 3. Create the Person Account

```text
dispatch({
  "url":    "/services/data/v67.0/sobjects/Account",
  "method": "POST",
  "body": {
    "FirstName":    "<FirstName>",
    "LastName":     "<LastName>",
    "PersonEmail":  "<Email>",                 // REQUIRED
    "RecordTypeId": "<PersonAccountRecordTypeId>"
  }
})
```

Capture `body.id` as `NewAccountId`. `PersonEmail` is required — the `UnifiedEmployeePersona`
validation hook rejects Employee2 creation when the linked PersonContact is missing `Email` or
`LastName`.

### 4. Verify the PersonContact

```text
dispatch_readonly({
  "url":         "/services/data/v67.0/query",
  "method":      "GET",
  "queryParams": { "q": "SELECT Id, IsPersonAccount, PersonContactId FROM Account WHERE Id = '<NewAccountId>'" }
})
```

Confirm `IsPersonAccount = true`; capture `PersonContactId`. If it is null, stop and report failure
to generate the PersonContact.

### 5. Create the Employee2 record

```text
dispatch({
  "url":    "/services/data/v67.0/sobjects/Employee2",
  "method": "POST",
  "body": {
    "UserId":         "<NewUserId>",            // FK field name, not "User"
    "ContactId":      "<PersonContactId>",      // FK field name, not "Contact"
    "Department":     "<Department>",
    "Location":       "<Location>",
    "EmployeeNumber": "<EmployeeNumber>",
    "Title":          "<Title>",
    "HireDate":       "<YYYY-MM-DD>"
  }
})
```

Capture `body.id` as `NewEmployee2Id`. Use the foreign-key field names `UserId`/`ContactId`; the
API rejects bare IDs placed under the relationship names `User`/`Contact`.

### 6. Additional permission sets — not supported

The skill assigns exactly one permission set: `EmployeeHubEmployeeUser` (label
`Employee Hub Unified Employee User`). UEL / Employee Hub users are **requesters** — extras
belong on fulfillers (`Incident Fulfiller`, `Case Agent`, and similar are agent-role permsets on
the Service Cloud side, categorically incompatible with the Unified Employee profile). Do not add
any additional-permset assignment logic here.

---

## Phase 4 — Verify the full chain

```text
dispatch_readonly({
  "url":         "/services/data/v67.0/query",
  "method":      "GET",
  "queryParams": { "q": "SELECT Id, IsPersonAccount, PersonContactId FROM Account WHERE Id = '<NewAccountId>'" }
})

dispatch_readonly({
  "url":         "/services/data/v67.0/query",
  "method":      "GET",
  "queryParams": { "q": "SELECT Id, IsActive, ProfileId, ManagerId FROM User WHERE Id = '<NewUserId>'" }
})

dispatch_readonly({
  "url":         "/services/data/v67.0/query",
  "method":      "GET",
  "queryParams": { "q": "SELECT Id, UserId, ContactId FROM Employee2 WHERE Id = '<NewEmployee2Id>'" }
})

dispatch_readonly({
  "url":         "/services/data/v67.0/query",
  "method":      "GET",
  "queryParams": { "q": "SELECT PermissionSet.Label FROM PermissionSetAssignment WHERE AssigneeId = '<NewUserId>' AND PermissionSet.IsOwnedByProfile = false" }
})
```

Confirm: `Account.IsPersonAccount = true` and `PersonContactId` matches; `User.IsActive = true` and
`ProfileId = UnifiedEmployeeProfileId`; `User.ManagerId` matches (if provided);
`Employee2.UserId`/`ContactId` match; the Employee Hub set is the only non-profile
PermissionSetAssignment.

---

## Gotchas

| Issue | Resolution |
|-------|------------|
| Response wrapper | `describe`/`/query`/`/sobjects/*` come back as `{status_code, body}` — read `body`. |
| `queryParams` casing | The `dispatch*` tools require **camelCase** `queryParams` — `query_params` is rejected. |
| Employee2 create rejected by validation hook | The PersonContact is missing `Email`/`LastName` — set `PersonEmail` on the Account create. |
| Employee2 create rejects the IDs | Use `UserId`/`ContactId` (FK field names), not `User`/`Contact` (relationship names). |
| Create rejects empty `ManagerId` | Omit the key entirely when there is no manager — do not send `""`. |
| `PersonContactId` is null after Account create | Person Accounts may not be fully enabled — re-check the record type prerequisite. |
| Employee Hub set assignment fails | The set exists but may be license-incompatible — report the exact error and stop. |
| `Employee2` describe 404 / not accessible | The HR module is not enabled — stop and direct the user to enable it. |
| `discover` returns nothing for a `/sobjects/…` path | Not fatal — these are core Data API routes; dispatch directly at the exact `/services/data/v67.0/sobjects/<Name>` path. |
| Auth error on any `dispatch*` call | Tell the user to re-authenticate the headless-360 MCP connection and confirm the session points at the intended org. |

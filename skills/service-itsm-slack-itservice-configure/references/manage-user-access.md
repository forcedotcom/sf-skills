# Manage User Access (Step 4) — assign Employee Slack Notifications

The Go page's **"Manage User Access"** step (Salesforce Go → *Slack for Employee Service* → *Set Up the
Basics* → **Manage**) centers on the permission set **`EmployeeSlackNotifications`** (label *"Employee
Slack Notifications"*) — *"gives employee users the ability to receive notifications on ticket updates
in Slack."* This skill assigns **all three core permsets** to each confirmed user —
`EmployeeSlackNotifications` **plus** `ItsmPortalUelUserPermset` (record visibility) **plus** an
API-Enabled permset (both detailed below) — never a notifications-only subset. Assign only to the
specific employee user(s) who will use Slack — **never all active users**.

> **Assign the right permset.** This employee-side step is **`EmployeeSlackNotifications`** (PSL
> `EmployeeSlackNotificationsPsl`), **not** `SlackServiceUser` (PSL `SlackServiceUserPsl`) — that's a
> separate fulfiller/service-side permset on a different path and does **not** satisfy this step. Query
> by exact `Name = 'EmployeeSlackNotifications'`.

> **The user's email must match their Slack user's email.** Assigning the permset only grants the
> *ability* to receive Slack notifications — it does **not** create the Salesforce↔Slack user link. That
> link is made by the connection's **account-mapping field** (default `Email`, chosen when the connection
> was requested/approved): the Salesforce `User.Email` must equal the email of that person's Slack
> account, otherwise they map to no Slack user and notifications never arrive. Warn the user and verify
> the match — a `null` `currentUserMapping.salesforceUserId` from `GET /connect/slackbridge/connections`
> means the current user isn't mapped yet. If the connection mapped on **SAML NameID** instead of Email,
> the same requirement applies to that identifier.

## Pick the user(s)

Ask which user(s) should get access. If they want the list, page it — **≤10 users per page**, then ask
"want to see more?" before the next page:

```text
mcp__headless-360__dispatch_readonly(
  method: "GET", url: "/services/data/v67.0/query",
  queryParams: { "q": "SELECT Id, Name, Username, Email FROM User WHERE IsActive = true ORDER BY Name LIMIT 10 OFFSET <page * 10>" }
)
```

**Verified gotcha:** early pages are often dominated by non-employee system/integration accounts
(`Automated Process`, `Bot User`, `Insights Integration`, `*.ext`, `ESW_*` / `*Site Guest User`,
`DigitalAgent.*`). Do **not** classify rows by eye. Save the response to a file and let the helper
script tag each row `employee`/`system` deterministically **without dropping any row**:

```text
node scripts/classify-user-access.mjs flag-users <captured-users.json>
```

Prints `{users:[{id,name,username,email,kind}], employeeCount, systemCount}`. Present `employee` rows
first; surface `system`-tagged rows as "these look like system/integration accounts" rather than hiding.

## Look up the permset Id and assign

```text
mcp__headless-360__dispatch_readonly(
  method: "GET", url: "/services/data/v67.0/query",
  queryParams: { "q": "SELECT Id, Name, Label FROM PermissionSet WHERE Name = 'EmployeeSlackNotifications'" }
)
```

Then assign to each confirmed user (one record per user):

```text
mcp__headless-360__dispatch(
  method: "POST", url: "/services/data/v67.0/sobjects/PermissionSetAssignment",
  body: { "AssigneeId": "<user id>", "PermissionSetId": "<EmployeeSlackNotifications id>" }
)
```

Do **not** read the POST body yourself to decide success. Save it and classify:

```text
node scripts/classify-user-access.mjs classify-assignment <captured-response.json>
```

Prints `{status, retryable, message}` where `status` is `success` / `wrong-license` / `other-error`;
`retryable` is always `false`. Relay the plain-language `message`; never surface the raw error code.
Optionally verify a `success`: `SELECT Id FROM PermissionSetAssignment WHERE AssigneeId = '<user id>'
AND PermissionSetId = '<permset id>'`.

> **License gotcha (`wrong-license`):** a Slack permission set can carry a permission-set license only
> some user licenses can hold. Assigning to an incompatible license fails `400 FIELD_INTEGRITY_EXCEPTION`
> (*"…user license doesn't support it"*). Observed live: a **Unified Employee** license user was rejected
> against a Slack PSL; a **Standard User** succeeded (`201`). `EmployeeSlackNotifications` is backed by
> `EmployeeSlackNotificationsPsl` — its cross-license compatibility wasn't separately verified, so treat
> any `wrong-license` as authoritative. It is **not** transient — pick a user whose license supports it
> (or add the PSL), don't retry.

> **API Enabled + agent access (assign here too).** Beyond notifications, this step also grants:
> **API Enabled** — needed for the Slack/employee app to call Connect APIs on the user's behalf. This is
> the *API Enabled* system permission carried by a permission set. **Reuse an existing API-Enabled permset
> if the org already has one** (discover it — query below — don't assume any particular one exists). If none
> exists, **create one** — a minimal `PermissionSet` with `PermissionsApiEnabled = true` (e.g. Name
> `Slack_ApiAccess`, label "Slack API Access"). Discover first, create only if none is found, then assign.
> Also — only for users who will reach the Agentforce agent in Slack — the **per-agent `Agent_Access`**
> permset carrying that agent's `BotDefinition` `SetupEntityAccess` grant. Discover `Agent_Access` by
> reverse-lookup on the BotDefinition and create it if absent (mechanics: `connect-agentforce-to-slack.md`);
> **never** assign the broad `Access_Agents` — it fails on an employee license (*"View Setup Audit Trail"*).
>
> **Discover an API-Enabled permset (reuse before create):**
> ```text
> mcp__headless-360__dispatch_readonly(
>   method: "GET", url: "/services/data/v67.0/query",
>   queryParams: { "q": "SELECT Id, Name, Label FROM PermissionSet WHERE PermissionsApiEnabled = true AND IsCustom = true" }
> )
> ```
> If a row comes back, reuse it — assign it. If none, create one via
> `POST /services/data/v67.0/sobjects/PermissionSet` with `{ "Name": "Slack_ApiAccess", "Label":
> "Slack API Access", "PermissionsApiEnabled": true }`, then assign the returned Id.

> **Record visibility — always assigned, one of the three core permsets.** For a UEL employee to actually
> see records (not just notifications) in the Slack Salesforce app, assign **`ItsmPortalUelUserPermset`**
> ("ITSM Portal Uel User") — it grants **read/create/edit on Incident, Service Request, and Case** (the
> self-service scope), alongside an API-Enabled permset. **Always assign it** (with the other two core
> permsets) to each confirmed user — do **not** offer a "notifications-only" scope; under-assigning
> silently leaves the employee unable to see records. This deliberately does **not** include **Problem** or
> **Change Request** — those are fulfiller/manager queues and their Slack lists staying empty ("Nothing
> turned up") is expected for a self-service employee, not a bug. If a specific user genuinely needs
> Problem/Change visibility, that is a separate fulfiller-side grant (e.g. `IncidentManager`), handled
> outside this self-service flow — do not assign it. Full mechanics: `references/record-visibility.md`.

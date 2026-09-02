# Record visibility — let a UEL employee view their Incident / Service Request / Case records in Slack

Record visibility is part of the baseline employee role — **always** grant it during Step 4 (it's one of
the three core permsets) so a Unified Employee (UEL) user can **view and work Incident, Service Request,
and Case records** (the self-service ITSM entities) in the Slack Salesforce app (e.g. in the Salesforce
**List views**). It goes beyond the literal Go-page "Manage User Access" click but is what makes the ITSM
experience actually usable in Slack — say so when you assign it.

> **Always assign — no scope choice.** Assign this to every confirmed user alongside the other two core
> permsets; do **not** offer a "notifications-only" option. Under-assigning silently leaves the employee
> able to receive notifications but unable to open the records those notifications point to.

> **Scope note — this is a self-service employee grant, not a fulfiller grant.** The employee gets
> **Incident + Service Request + Case** (read/create/edit) so they can log and track their own issues and
> raise service requests. It does **not** include **Problem** or **Change Request** — those are
> fulfiller/manager queues, out of scope for a self-service employee on Slack. If a specific user genuinely
> needs Problem/Change visibility, that is a separate fulfiller-side grant (e.g. `IncidentManager`), handled
> outside this self-service flow — do not assign it by default here.

## Why `EmployeeSlackNotifications` alone isn't enough

- **`EmployeeSlackNotifications`** (Step 4) only grants notification receipt — **no object access**.

So a UEL user assigned only `EmployeeSlackNotifications` will get **"Nothing turned up"** when they open
the Incident / Service Request / Case lists in Slack. The list *definitions* still appear in the picker
(they are org-shared metadata), but they return no records without object read.

## What to assign for record visibility

Two things, both assigned to the specific UEL user (never "all active users"):

1. **API Enabled** — required for the Slack/employee app to call Connect APIs on the user's behalf.
   Any permission set that enables the **API Enabled** system permission works. **Reuse** an existing
   API-Enabled permset if the org already has one (confirm the user has it before adding); otherwise
   **create** a Slack-named one (e.g. Name `Slack_ApiAccess`, label "Slack API Access", with
   `PermissionsApiEnabled = true`).
2. **`ItsmPortalUelUserPermset`** ("ITSM Portal Uel User") — the standard ITSM self-service permset that
   grants **read/create/edit on Incident, Service Request, and Case** (plus read on supporting objects
   like Account, Contact, Asset, and Service Catalog items). This is the correct baseline for a
   self-service employee — it deliberately does **not** grant Problem or Change Request.

## How to assign (headless-360, one record per user/permset)

Resolve the `ItsmPortalUelUserPermset` Id fresh (stable per org, but don't hardcode); resolve or create
the API-Enabled permset per the reuse-or-create flow above and use its Id too:

```text
mcp__headless-360__dispatch_readonly(
  method: "GET",
  url:    "/services/data/v67.0/query",
  queryParams: { "q": "SELECT Id, Name, Label FROM PermissionSet WHERE Name = 'ItsmPortalUelUserPermset'" }
)
```

Assign each to the confirmed user (two POSTs — skip either permset the user already has, checked via
`PermissionSetAssignment`):

```text
mcp__headless-360__dispatch(
  method: "POST",
  url:    "/services/data/v67.0/sobjects/PermissionSetAssignment",
  body:   { "AssigneeId": "<user id>", "PermissionSetId": "<permset id>" }
)
```

Verify (each self-service object should read RCE for Incident/ServiceRequest/Case):

```text
mcp__headless-360__dispatch_readonly(
  method: "GET",
  url:    "/services/data/v67.0/query",
  queryParams: { "q": "SELECT SobjectType, PermissionsRead, PermissionsCreate, PermissionsEdit FROM ObjectPermissions WHERE ParentId IN (SELECT PermissionSetId FROM PermissionSetAssignment WHERE AssigneeId = '<user id>') AND SobjectType IN ('Incident','ServiceRequest','Case')" }
)
```

Then tell the user to reload the Slack Salesforce app; the Incident / Service Request / Case lists that
previously returned "Nothing turned up" will now resolve records. (Problem and Change Request remain empty
by design — they are fulfiller queues, not part of the self-service scope.)

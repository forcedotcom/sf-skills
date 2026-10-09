---
name: service-omni-supervisor-permset-assign
description: "Use to assign the Salesforce-shipped standard ContactCenterSupervisor PermissionSet (default) to N existing supervisor users via PermissionSetAssignment DML. Idempotent — SOQL detects existing (user, perm-set) pairs before POST, and DUPLICATE_VALUE is treated as reused. The standard set carries its own permission-set license and assigns cleanly on Service-Cloud-enabled orgs; a user whose license lacks the entitlement surfaces FIELD_INTEGRITY_EXCEPTION so the operator can fix the profile/license. Triggers: assign the supervisor permset, grant supervisor perms, complete supervisor provisioning. Do not use on production orgs or to assign agent permsets."
allowed-tools: Bash Read Write Edit Glob Grep
metadata:
  version: "1.0"
  domains: ["Service"]
  minApiVersion: "66.0"
  relatedSkills:
    - "service-omni-supervisor-config-deploy"
  accessCheck:
    - type: license
      value: ServiceCloud
  cliTools:
    - tool: ["jq"]
      semver: ">=1.6"
    - tool: ["sf"]
      semver: ">=2.139.6"
---

# service-omni-supervisor-permset-assign

Assign the Salesforce-shipped standard `ContactCenterSupervisor` PermissionSet to existing supervisor users via `PermissionSetAssignment`. The classic Omni-Channel Supervisor UI (Command Center) requires supervisors to hold contact-center supervisor permissions before `service-omni-supervisor-config-deploy` can bind them. The skill uses detect-before-POST idempotency and treats `DUPLICATE_VALUE` as an already-satisfied assignment.

**Licensing.** The supervisor system permissions (`IsContactCenterSupervisor`, `OmniSupervisorManageQueue`, `ViewOmnichnlAnlytDshbrd`) are gated by a permission-set license. The standard `ContactCenterSupervisor` set carries its own license linkage and assigns cleanly on a Service-Cloud-enabled org, so it is the default and supported path — a hand-rolled custom set that re-declares these permissions fails with `FIELD_INTEGRITY_EXCEPTION`. If a specific user's license lacks the underlying entitlement, the assignment surfaces that same exception so the operator can move the user to a profile/license that carries it.

That custom-permission-set warning does **not** mean assigning the existing Salesforce-shipped `ContactCenterSupervisor` set removes access or rewrites the set. This skill only creates a missing `PermissionSetAssignment`; it never creates, edits, or replaces the permission set itself.

## Inputs

```bash
bash scripts/verify-and-assign.sh <org-alias> [count=1] [permission-set-names-csv=ContactCenterSupervisor]
```

- `org-alias` (required).
- `count` (optional, default `1`, range `1..5`) — must match the supervisor user count.
- `permission-set-names-csv` (optional, default `ContactCenterSupervisor`) — comma-separated for multiple. Every supervisor gets every listed set (cross-product).

## Preconditions and safety

- Target org authenticated via `sf` CLI, Service Cloud license, `sf` CLI ≥ 2.139.6.
- The supervisor users exist and are active; fewer than `count` active users blocks with a remediation message.
- The `ContactCenterSupervisor` set is Salesforce-shipped and present on any Service-Cloud-enabled org; a custom name that is missing blocks with a Setup click-path.
- The executing user has `PermissionsAssignPermissionSets` (standard on System Administrator) — required even for org admins.
- The three-way `safe_to_write` production guard applies — assigning permission sets on a production org can escalate a real user's privileges, so it blocks with no override.

## Run

`verify-and-assign.sh` performs the whole cycle:

1. Compute `safe_to_write`; derive the 8-char org suffix.
2. Validate every supplied permission-set name as a well-formed DeveloperName (SOQL-injection guard) before any `sf` call.
3. Resolve the `supervisor{1..N}.<suffix>@example.com` users, filtered to `IsActive=true`; block if fewer than `count` are active (an inactive occupant does not satisfy the count).
4. Resolve each `PermissionSet` by name; block naming which is missing.
5. Query existing `PermissionSetAssignment` for the (user × set) cross-product; compute the missing pairs.
6. POST one assignment per missing pair (individual POSTs, no `allOrNone`); treat `DUPLICATE_VALUE` as reused.
7. Re-query to confirm final state and emit the report.

## Behavior

**Cross-product.** Every supervisor gets every listed set; a partial assignment is a failure, not a feature.

**Idempotency.** `PermissionSetAssignment` has a uniqueness constraint on (AssigneeId, PermissionSetId), so a re-POST raises `DUPLICATE_VALUE`; the skill detects existing pairs first and treats that as reused for concurrent-run safety. POSTs are individual so one error never rolls back its siblings, and it re-queries after all POSTs — a 201 only means the write was accepted; a SOQL confirms it is active.

**Non-destructive.** Create-only; it never deletes existing assignments (supervisors may hold out-of-band permissions) and derives users from the supervisor pattern rather than an explicit id list.

## Output contract

A single JSON object with `status` ∈ `assigned` | `reused` | `partial` | `blocked`, the resolved `permission_sets`, `org_suffix`, `requested_count`, `expected_assignment_count` (= `requested_count × len(permission_sets)`), a `before` snapshot, `assigned_this_run`/`assigned_count`, `reused_count`, an `after` snapshot, `manual_actions`, and `blocking_issue`.

- `assigned` — at least one new assignment created; all expected pairs exist after.
- `reused` — all expected pairs already existed; nothing POSTed.
- `partial` — some POSTs failed; final count is below expected.
- `blocked` — precondition failed (production org, missing set, missing/inactive users, or a license that does not allow the permission).

`assigned_count + reused_count == expected_assignment_count` unless `partial`; `blocking_issue` is non-null only for `blocked`/`partial`.

## Limitations

- Provisioning the user license that the supervisor permset requires is the users-create skill's responsibility, not this one.
- Assigns individual PermissionSets only — a `PermissionSetGroup` is a different sObject and is out of scope.
- Create-only; it does not remove assignments.

## References

| File | When to read |
|---|---|
| `references/api-notes.md` | Before the POST loop — PermissionSetAssignment schema, `DUPLICATE_VALUE` semantics, and why users are derived from the supervisor pattern rather than an explicit id list |

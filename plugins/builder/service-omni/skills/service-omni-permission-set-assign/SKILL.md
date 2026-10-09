---
name: service-omni-permission-set-assign
description: "Assign the required Omni permission sets to provisioned agent users. TRIGGER when users ask to assign Omni permissions to agents, grant Omni-Channel access, add Omni_Agent permissions, repair missing Omni permission assignments, or prepare agents to use the Omni widget. DO NOT TRIGGER for arbitrary permission-set authoring, agent creation, or queue membership."
allowed-tools: Bash Read Write Edit Glob Grep
metadata:
  version: "1.0"
  domains: ["Service"]
  minApiVersion: "66.0"
  relatedSkills:
    - "service-omni-agent-users-create"
    - "service-omni-presence-status-deploy"
    - "service-omni-queue-members-assign"
  accessCheck:
    - type: license
      value: ServiceCloud
  cliTools:
    - tool: ["jq"]
      semver: ">=1.6"
    - tool: ["sf"]
      semver: ">=2.139.6"
---

# service-omni-permission-set-assign

Assign one or more PermissionSets to N agent users via `PermissionSetAssignment` Data API POSTs. The default target is `Omni_Agent`, the permission set granting the OmniChannel widget, presence-status access, and demo-queue visibility — without an assignment row, agents cannot open the widget or receive routed work. Detection is SOQL-based, so the skill only creates the assignments that are missing. Agent users come from `service-omni-agent-users-create`, and it runs alongside `service-omni-presence-status-deploy` so assigned agents can both open the widget and select a status.

## Inputs

```bash
bash scripts/verify-and-assign.sh <org-alias> [count=3] [permission-set-names-csv=Omni_Agent]
```

- `org-alias` (required).
- `count` (optional, default `3`, range `1..10`) — must match the agent user count.
- `permission-set-names-csv` (optional, default `Omni_Agent`) — comma-separated for multiple. Every user gets every listed set (cross-product): `count=3` × 2 sets = up to 6 assignments.

## Preconditions and safety

- Target org authenticated via `sf` CLI, Service Cloud license, `sf` CLI ≥ 2.139.6.
- The agent users exist (`service-omni-agent-users-create`); a count mismatch blocks with a pointer back to that skill.
- The executing user has `PermissionsAssignPermissionSets` (standard on System Administrator) — required even for org admins; `ModifyAllData` alone is insufficient.
- At least one Omni presence status exists before `Omni_Agent` self-heals — the bundled set grants agent capability via `servicePresenceStatusAccesses` for whichever curated statuses exist (e.g. `Available_Case`/`Available_Voice` + `Busy`), generated at deploy time. Run `service-omni-presence-status-deploy` first; the coordinator sequences presence before permset for this reason.
- The three-way `safe_to_write` guard applies — assigning permission sets on a production org can escalate a real user's privileges, so it blocks with no override.

**Self-heal (run mode only).** When the default `Omni_Agent` set is absent, the skill deploys the bundled `Omni_Agent` metadata once, then assigns. In `--plan` mode it never deploys — it reports `action_needed` and exits read-only. This covers only the bundled `Omni_Agent` asset; any other permission set must already exist or the run blocks with a click-path.

## Run

`verify-and-assign.sh` performs the whole cycle:

1. Compute `safe_to_write`; derive the 8-char org suffix.
2. Resolve the agent users by the `agent{1..N}.<suffix>@example.com` pattern; block if any are missing.
3. Resolve each `PermissionSet` by name; self-heal `Omni_Agent` if absent, else block naming which is missing.
4. Query existing `PermissionSetAssignment` for the (user × set) cross-product; compute the missing pairs.
5. POST one assignment per missing pair (individual POSTs, no `allOrNone`).
6. Re-query to confirm final state and emit the report.

## Behavior

**Cross-product.** Every user gets every listed set; a partial assignment is a failure, not a feature.

**Idempotency.** `PermissionSetAssignment` has a database uniqueness constraint on (AssigneeId, PermissionSetId), so a re-POST raises `DUPLICATE_VALUE`; the skill detects existing pairs first and treats `DUPLICATE_VALUE` as a safety net for concurrent races. It POSTs individually so one duplicate or error never rolls back its successful siblings, and it re-queries after all POSTs — a 201 only means Salesforce accepted the write; a subsequent SOQL confirms the assignment is active.

**Non-destructive.** The skill is create-only; it never deletes existing assignments (users may hold out-of-band permissions from other admins) and derives users from the agent pattern rather than accepting an explicit user-id list, so it never assigns demo permissions to real named users.

## Output contract

A single JSON object with `status` ∈ `assigned` | `reused` | `partial` | `blocked`, the resolved `permission_sets`, `org_suffix`, `requested_count`, `expected_assignment_count` (= `requested_count × len(permission_sets)`), a `before` snapshot, `assigned_this_run`/`assigned_count`, `reused_count`, an `after` snapshot, `manual_actions`, and `blocking_issue`.

- `assigned` — at least one new assignment created; all expected pairs exist after.
- `reused` — all expected pairs already existed; nothing POSTed.
- `partial` — some POSTs failed; final count is below expected.
- `blocked` — precondition failed (production org, missing set, missing users, missing permissions).

`assigned_count + reused_count == expected_assignment_count` unless `partial`; `blocking_issue` is non-null only for `blocked`/`partial`.

## Limitations

- Assigns individual PermissionSets only — a `PermissionSetGroup` is a different sObject and is out of scope.
- Self-heal covers only the bundled `Omni_Agent`; it is not a general-purpose permission-set authoring surface.
- Create-only; it does not remove assignments.

## References

| File | When to read |
|---|---|
| `assets/package.xml` | Load when the default `Omni_Agent` permission set is missing and the run-mode self-heal path must deploy the bundled metadata |
| `references/api-notes.md` | Before the POST loop — PermissionSetAssignment schema, its `DUPLICATE_VALUE` semantics, and why users are derived from the agent pattern rather than an explicit id list |

# service-omni-supervisor-permset-assign — API notes

Load this reference **only when POSTs fail or you need to add new PermissionSets to the skill**. Under normal operation `verify-and-assign.sh` just runs and emits its JSON.

## Why REST POST over Metadata deploy

`PermissionSetAssignment` is a **Data API sObject only** — no Metadata API surface. You cannot deploy assignments via `.permissionSetAssignment-meta.xml`. The DML approach with detect-before-POST loops is the only headless option.

Contrast with the parent `PermissionSet` itself, which **does** have a Metadata surface (deployable via `.permissionset-meta.xml`). That's why v1.2 has a separate `service-omni-supervisor-permset-metadata-deploy` skill to ship the permset itself; this skill just assigns it.

## Idempotency contract

`PermissionSetAssignment` has a Salesforce-enforced uniqueness constraint on `(AssigneeId, PermissionSetId)`. Duplicate POSTs return `DUPLICATE_VALUE` errors.

The skill handles this two ways:

1. **Pre-detect via SOQL** — query existing pairs before POSTing; skip already-existing pairs. Avoids most `DUPLICATE_VALUE` responses.
2. **Concurrent-run safe** — if another agent (or admin) assigns the same permset between our detect and POST, treat `DUPLICATE_VALUE` as reused (do NOT increment `assigned_count`). No error surfaced.

Re-runs on an already-configured org return `status: reused` with `assigned_count: 0` and `before.existing_count == after.assignment_count == expected_assignment_count`.

## Default permset: standard ContactCenterSupervisor (not a custom permset)

This skill defaults to the Salesforce-shipped **standard `ContactCenterSupervisor`** PermissionSet, which is present on any Service-Cloud-enabled org and assigns cleanly to a user on a **Salesforce user license** with the **Service Cloud feature** (`UserPermissionsSupportUser=true`).

**Why not a custom `Omni_Supervisor` permset?** A custom permset that re-declares the supervisor system permissions (`IsContactCenterSupervisor`, `OmniSupervisorManageQueue`, `ViewOmnichnlAnlytDshbrd`) is rejected with `FIELD_INTEGRITY_EXCEPTION — The user license doesn't allow the permission: IsContactCenterSupervisor`, because those permissions are gated by a permission-set license the custom set does not carry. The standard `ContactCenterSupervisor` permset carries its own license linkage and grants `IsContactCenterSupervisor` cleanly — so it is the only supported path. This skill assigns permsets that already exist on the org; it does not ship or deploy a custom supervisor permset.

## Post-run SOQL verification

```sql
SELECT AssigneeId, PermissionSetId, Assignee.Username, PermissionSet.Name
FROM PermissionSetAssignment
WHERE PermissionSet.Name='ContactCenterSupervisor'
  AND Assignee.Username LIKE 'supervisor%.%'
```

Expected: N rows, where N = `count` param.

## Common failure modes

| Symptom | Cause | Fix |
|---------|-------|-----|
| `blocked: Expected PermissionSets [ContactCenterSupervisor]; found []` | Standard permset name not found (unusual — it ships with Service Cloud) | Confirm Service Cloud is enabled on the org |
| `blocked: Expected N supervisor users ...; found M` | Supervisor users not created or inactive | Provision or reactivate the missing users, then rerun |
| `DUPLICATE_VALUE` in POST results | Concurrent admin assigned same pair | Treated as reused, no action needed |
| `FIELD_INTEGRITY_EXCEPTION — The user license doesn't allow the permission: IsContactCenterSupervisor` | Supervisor user is on a license that doesn't carry the contact-center supervisor entitlement | Move the user to a profile/license that carries the entitlement, then rerun |
| `INSUFFICIENT_ACCESS_OR_READONLY` on POST | SF CLI user lacks ManageUsers perm | Ensure authenticated user is System Administrator |
| `INSUFFICIENT_ACCESS_OR_READONLY` on POST | SF CLI user lacks ManageUsers perm | Ensure authenticated user is System Administrator |

---
name: platform-sharing-owd-configure
description: "Use when the user wants to retrieve or update Organization-Wide Default (OWD) sharing settings for Salesforce objects. TRIGGER when: user asks to check current OWD settings, view sharing defaults, change default access levels (Private, Public Read Only, Public Read/Write, Controlled by Parent), configure internal or external access for standard or custom objects, mentions org-wide defaults, wants to make records private or restrict who can see records, wants to control default record visibility for an object, or references .settings-meta.xml sharing fields or sharingModel in .object-meta.xml files. DO NOT TRIGGER when: user asks about sharing rules, criteria-based sharing, role hierarchy, or manual sharing — delegate to platform-sharing-rules-generate."
metadata:
  version: "1.0"
  cliTools:
    - tool: ["sf"]
      semver: ">=2.0.0"
---

# Managing Org-Wide Defaults

Retrieve and update Organization-Wide Default (OWD) sharing settings for standard and custom objects in a Salesforce org. OWDs define the baseline level of access users have to records they do not own.

## Scope

- **In scope**: Retrieving current OWD settings, updating internal/external access levels for standard and custom objects
- **Out of scope**: Sharing rules, role hierarchy configuration, manual sharing, permission sets, criteria-based sharing — delegate to appropriate skills

---

## Clarifying Questions

Before proceeding, confirm with the user if not already clear:

- Which object(s) do you want to get or update OWD settings for?
- What access level do you want to set? (Private, Public Read Only, Public Read/Write, Controlled by Parent)
- Do you need to change both internal and external access, or just one?

---

## Required Inputs

Gather or infer before proceeding:

- **Target org**: The org alias or username to query/update (use default org if not specified)
- **Object name(s)**: Standard object API name (e.g., `Account`, `Contact`) or custom object API name (e.g., `Invoice__c`)
- **Operation**: Get (retrieve current settings) or Update (change access levels)
- **Access levels** (for update): Internal access and/or external access values

Defaults unless specified:
- Use the default connected org
- If only one access level is provided, assume it applies to internal access

---

## Workflow

All steps are sequential. Do not skip or reorder.

### Phase 1 — Retrieve Current Settings

1. **Query current OWD settings** using the Salesforce CLI Tooling API:
   ```bash
   sf data query --query "SELECT QualifiedApiName, InternalSharingModel, ExternalSharingModel FROM EntityDefinition WHERE QualifiedApiName = '<ObjectName>'" --use-tooling-api --target-org <org>
   ```

2. **For retrieving all OWD settings at once:**
   ```bash
   sf data query --query "SELECT QualifiedApiName, InternalSharingModel, ExternalSharingModel FROM EntityDefinition WHERE IsCustomizable = true ORDER BY QualifiedApiName" --use-tooling-api --target-org <org>
   ```

3. **Present results clearly** — read `references/access_levels.md` for valid values and display a formatted table to the user.

### Phase 2 — Update Settings (if requested)

4. **Validate the requested access level** — read `references/access_levels.md` to confirm the value is valid for the target object.

5. **Retrieve the object metadata** using the Metadata API (same command for both standard and custom objects):
   ```bash
   sf project retrieve start --metadata CustomObject:<ObjectName> --target-org <org>
   ```
   This retrieves `<ObjectName>.object-meta.xml` containing `<sharingModel>` and `<externalSharingModel>`. See `references/metadata_api_approach.md` for the full procedure.

6. **Modify the sharing settings** — update the `<sharingModel>` (internal access) and/or `<externalSharingModel>` (external access) in the object's `.object-meta.xml`. Read `references/metadata_api_approach.md` for details.

7. **Pre-deploy verification** — before deploying, confirm:
   - [ ] External access is not more permissive than internal access
   - [ ] Objects with Master-Detail relationships use `ControlledByParent`
   - [ ] The requested access level is valid for the target object (see `references/access_levels.md`)
   - [ ] Cross-object constraints are satisfied (see "Cross-Object Constraints" in `references/access_levels.md`)

8. **Deploy the updated settings:**
   ```bash
   sf project deploy start --metadata CustomObject:<ObjectName> --target-org <org>
   ```

9. **Verify the change** by re-running the query from Step 1.

---

## Rules / Constraints

| Constraint | Rationale |
|-----------|-----------|
| Objects with Master-Detail relationships must use `ControlledByParent` | Platform enforces this — attempting other values fails |
| External access cannot be more permissive than internal access | Salesforce rejects configurations where external > internal |
| Some standard objects have fixed OWD (e.g., User, Activity) | Not all objects support OWD changes |
| Changing OWD to more restrictive triggers sharing recalculation | This can take significant time on large orgs — warn the user |
| Custom objects default to `Public Read/Write` when created | Users may not realize the default is permissive |
| Always verify the org connection before querying | Prevents confusing error messages |

---

## Gotchas

| Issue | Resolution |
|-------|------------|
| `INSUFFICIENT_ACCESS` error when updating | User needs Manage Sharing permission or System Administrator profile |
| OWD change appears stuck | Sharing recalculation is running — check Setup > Sharing Settings for progress |
| Custom object not found in query | Use the full API name including `__c` suffix |
| `ControlledByParent` not available | Object has no Master-Detail relationship — use Private, Public Read Only, or Public Read/Write |
| External access field not showing | External sharing model only appears when external org-wide defaults are enabled |
| Query returns no results | Object may not be customizable or API name may be incorrect — verify spelling |

---

## Output Expectations

Deliverables:
- **For get operations**: Formatted table showing object name, internal access level, and external access level
- **For update operations**: Confirmation of the change with before/after comparison

---

## Cross-Skill Integration

| Need | Delegate to |
|------|-------------|
| Creating sharing rules after restricting OWD | `platform-sharing-rules-generate` skill |
| Deploying metadata changes to another org | `platform-metadata-deploy` skill |

---

## Reference File Index

| File | When to read |
|------|-------------|
| `references/access_levels.md` | When validating or explaining OWD access level values |
| `references/metadata_api_approach.md` | When using Metadata API to update OWD instead of Tooling API |
| `examples/get_owd_output.md` | To verify formatted output matches expected structure |
| `examples/update_owd_output.md` | To verify update confirmation matches expected structure |

---
name: field-service-sobject-create-configure
description: "Headless 360 REST API deployment step for creating sObject records. Handles describe-based field discovery, required-field derivation, entity-relationship ordering, and composite graph transactions. Use this skill when a designer skill (or a user directly) needs to create sObject records after design confirmation, including non-setup sObject creation."
user-invocable: false
metadata:
  version: "1.0"
  domains: ["Field Service"]
---

# Create an sObject record via headless-360

**Be helpful** — understand business context before creating records. Consider the business domain of the sObject being created and iterate through short, structured questions (ask/why/impact) until no ambiguities remain that would change what gets created. Skip questions when answers are already obvious from context or existing data.

## Flow

1. **Describe** — `dispatch_readonly` GET `/services/data/v67.0/sobjects/<SObject>/describe`
2. **Query existing records** — learn the org's shape before writing.
   `dispatch_readonly` GET `/services/data/v67.0/query`,
   `queryParams.q = "SELECT <required + picklist fields> FROM <SObject> ORDER BY CreatedDate DESC LIMIT 20"`.
   Use it to: match naming/value conventions, see which optional fields are actually populated,
   catch duplicates, and confirm write access before spending a create.
3. **Create** — `dispatch` POST to create records. Single record → `/services/data/v67.0/sobjects/<SObject>` with body. Multiple related records (DAG) → `/services/data/v67.0/composite/graph` to batch-create with dependency references in one transaction. Success → `201` with id(s). Failure → non-2xx with `errorCode` + `message` — act on that.

## Data model DAG

These examples show Field Service relationship patterns, but the same approach applies to any sObject based on its data shape:

```text
Skill + WorkType → SkillRequirement    WorkType + Product2 → ProductRequired
OperatingHours → ServiceTerritory + TimeSlot
```

## Fields and insertion order
Scan describe `fields[]` for `createable:true` (skip the rest — describe is large). Such a
field is **required** when also `nillable:false` and `defaultedOnCreate:false` (defaulted ones
the platform fills — omit). Two kinds:

- **Scalar** → put its value in the create body.
- **`type:"reference"`** → foreign key. If `nillable:false` (hard edge), create parent in `referenceTo[]` first. Polymorphic refs list many — pick one. Topo-sort: roots first, pass each `id` to dependents. `nillable:true` refs → optional, PATCH later.

Pitfalls:
- Base sObject CRUD is NOT in the `discover` corpus — skip discover, go straight to describe → dispatch.
- `CANNOT_INSERT_UPDATE_ACTIVATE_ENTITY` on write → that sObject blocks sObject-REST writes
  (e.g. `ExternalDataSource`, `CustomPermission`); use Tooling/Metadata API instead.
- `400`/`403` → likely a CRUD/FLS/sharing gap for the gateway user, not a payload bug — don't blindly retry the body.

## Example — WorkType

Describe `WorkType`, apply the rule to `fields[]`. The fields that come back
`createable:true`, `nillable:false`, `defaultedOnCreate:false` are the required ones —
build the body from *those*, don't assume field names. Then query a few existing WorkTypes
to see conventions and dupes. Then create with the derived body, e.g.
```json
{ "url": "/services/data/v67.0/sobjects/WorkType", "method": "POST",
  "body": { "Name": "Standard Repair", "EstimatedDuration": 2 } }
```

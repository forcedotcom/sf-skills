# API notes — service-omni-skills-based-routing-configure

## The two objects skills-based routing needs

| Object | API | Purpose |
|---|---|---|
| `Skill` | Metadata API (`Skill`) to create; `Skill` sObject to read | The skill definition. Skills are metadata-backed — they cannot be `INSERT`ed via DML, so a missing skill is created by deploying a `Skill` component, then re-queried for its Id. |
| `SkillUser` | REST DML | Junction assigning a `Skill` to an agent `User`, matching Setup > Skills > Assign Users. Required: `SkillId`, `UserId`. |

## Skill: metadata create, sObject read

The `Skill` sObject exposes `Id`, `DeveloperName`, `MasterLabel` and is queryable, so detection is a
SOQL read by DeveloperName. Creation is a Metadata API deploy of:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Skill xmlns="http://soap.sforce.com/2006/04/metadata">
    <description>…</description>
    <label>…</label>
</Skill>
```

After the deploy the skill's Id is obtained by re-querying the sObject (the deploy response carries
the fullName, not the record Id). A freshly-deployed skill may lag a moment before it is queryable;
if the re-query returns nothing the skill blocks and asks for a re-run rather than binding to an
empty Id.

## SkillUser

- The skill deduplicates `SkillUser` by `(SkillId, UserId)` and creates only missing bindings for
  active users. `SkillLevel` is optional and remains at the platform default.
- `SkillUser` is created through REST DML. A concurrent create can return `DUPLICATE_VALUE`; the
  script reconciles that response as reused because the desired binding now exists.
- `ServiceResourceSkill` is not used. It belongs to the Field Service model and requires an active
  `ServiceResource`. Plain Service Cloud orgs do not expose a writable or queryable
  `ServiceResource.IsActive`, so that path produces inactive resources and rejected bindings.

## Prerequisite: base settings

Skills-based routing must be enabled in Omni-Channel settings
(`service-omni-base-settings-configure`) before skills route work. A Skill deploy can succeed while
SBR is off, so the skill points the operator at the base-settings skill when the deploy fails with
an SBR-disabled error.

## Out of scope: WorkSkillRouting

Authoring `WorkSkillRouting` rules (field-based skill criteria such as "add Voice when Case
Priority = Medium") is a **separate** capability — it is a Tooling-API rule header
(`WorkSkillRoutingStandardEntity`: `MasterLabel`, `DeveloperName`, `IsActive`) with skill-requirement
and field-criteria children, and only one rule is permitted per entity. It is not created here.

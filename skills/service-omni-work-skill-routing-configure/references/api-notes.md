# WorkSkillRouting - API notes

## Metadata type

`WorkSkillRouting` is a Metadata API type (also queryable via the Tooling API). It stores a set
of `WorkSkillRoutingAttribute` mappings that route a work item to an agent who holds the required
skills. It extends `Metadata` and inherits `fullName`.

Source path convention used by this skill:

```text
force-app/main/default/workSkillRoutings/<fullName>.workSkillRouting-meta.xml
```

## Record shape (XSD / alphabetical element order)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<WorkSkillRouting xmlns="http://soap.sforce.com/2006/04/metadata">
    <isActive>true</isActive>
    <masterLabel>Case Skill Routing</masterLabel>
    <relatedEntity>Case</relatedEntity>
    <workSkillRoutingAttributes>
        <field>Case.Origin</field>
        <skill>Voice</skill>
        <value>Phone</value>
    </workSkillRoutingAttributes>
</WorkSkillRouting>
```

Header fields:

| Field | Type | Notes |
|---|---|---|
| `isActive` | boolean | Required. Whether the rule is evaluated. |
| `masterLabel` | string | Required. Internal (untranslated) label. |
| `relatedEntity` | string | Required. The sObject the attributes apply to. |
| `workSkillRoutingAttributes` | array | One or more field-value -> skill mappings. |

Attribute fields (emitted alphabetically: `field`, `isAdditionalSkill`, `skill`, `skillLevel`,
`skillPriority`, `value`):

| Field | Type | Notes |
|---|---|---|
| `field` | string | Required. Field the attribute evaluates. |
| `isAdditionalSkill` | boolean | Additional skills are dropped after the routing-config timeout so a best-match agent can still take the work. |
| `skill` | string | Required. Skill DeveloperName required when the field matches `value`. |
| `skillLevel` | int | 0–10. |
| `skillPriority` | int | 0–10. Drop order for additional skills (9–10 dropped first, 0–1 last). API 49.0+. |
| `value` | string | Required. Field value mapped to the skill. |

## One rule per entity

Only one `WorkSkillRouting` rule is permitted per `relatedEntity`. This skill therefore defaults the
rule fullName to the related-entity name (overridable via `RULE_DEVELOPER_NAME`), so re-runs converge
on the same record instead of creating duplicates. Idempotency is read from the Metadata API
`files[].state`: `Created` -> `created`, `Changed` -> `updated`, `Unchanged` -> `reused`.

## Prerequisites and graceful degradation

- The referenced `Skill` must exist first (`service-omni-skills-based-routing-configure`); the skill
  queries `Skill` by DeveloperName and blocks with that pointer when it is missing.
- Skills-based routing must be enabled in Omni-Channel settings
  (`service-omni-base-settings-configure`).
- WorkSkillRouting is not provisioned on every org (some trials/CDOs). Deploy failures shaped like
  `INVALID_TYPE`, "not available", or naming `WorkSkillRouting` are reported as `blocked` with a
  limitation message rather than crashing, so a coordinator can continue.

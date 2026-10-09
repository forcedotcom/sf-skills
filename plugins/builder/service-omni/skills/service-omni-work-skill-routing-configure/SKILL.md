---
name: service-omni-work-skill-routing-configure
description: "Use to author an Omni WorkSkillRouting rule (field-based skill criteria): map a related-entity field value to a required Omni Skill (e.g. add the Voice skill when Case.Origin = Phone), deployed as one WorkSkillRouting record via the Metadata API. Idempotent via the Metadata API files[].state signal; one rule per related entity. Triggers: add field-based skill routing, route by a Case field to a skill, route by a MessagingSession field to a skill, configure attribute-based skills routing, require an Omni skill for a field value. Do not use to create the Skill or bind agents to it (service-omni-skills-based-routing-configure), to create agent users, or to configure queues."
allowed-tools: Bash Read Write Edit Glob Grep
metadata:
  version: "1.0"
  domains: ["Service"]
  minApiVersion: "66.0"
  relatedSkills:
    - "service-omni-base-settings-configure"
    - "service-omni-channel-setup-coordinate"
    - "service-omni-skills-based-routing-configure"
  accessCheck:
    - type: license
      value: ServiceCloud
  cliTools:
    - tool: ["jq"]
      semver: ">=1.6"
    - tool: ["python3"]
      semver: ">=3.8"
    - tool: ["sf"]
      semver: ">=2.139.6"
---

# service-omni-work-skill-routing-configure

Author an Omni **WorkSkillRouting** rule so work is routed to agents by a **field value on the work record**, not just by skills the agent happens to hold. Where `service-omni-skills-based-routing-configure` makes an agent *routable* (Skill + ServiceResource + ServiceResourceSkill), this skill decides *which skill a work item requires* based on one of its fields — for example "when `Case.Origin` = `Phone`, require the `Voice` skill". The rule is one `WorkSkillRouting` record (a header plus one `workSkillRoutingAttributes` mapping) deployed via the Metadata API. It runs after the referenced Skill exists and belongs to the same routing family coordinated by `service-omni-channel-setup-coordinate`.

## Inputs

```bash
bash scripts/configure-and-report.sh <org-alias> <related_entity> <field> <skill> <value> [rule_master_label]
```

- `org-alias` (required).
- `related_entity` (required). The sObject the rule applies to (e.g. `Case`, `MessagingSession`, `LiveChatTranscript`, `Lead`, `VoiceCall`).
- `field` (required). The field the attribute evaluates (e.g. `Case.Origin` or `Origin`). Bare standard fields are qualified with the related entity before deploy, so `Origin` becomes `Case.Origin` instead of being misread as a custom-field metadata name.
- `skill` (required). The Omni `Skill` DeveloperName required when the field matches (e.g. `Voice`).
- `value` (required). The field value that maps to the skill (e.g. `Phone`). Plain values only; XML-reserved characters are not supported.
- `rule_master_label` (optional). MasterLabel for the rule; defaults to `<related_entity> Skill Routing`.

Env overrides: `RULE_DEVELOPER_NAME` (fullName of the rule, default the related-entity name — one rule per entity), `IS_ACTIVE` (default `true`), `SKILL_LEVEL` (0–10), `SKILL_PRIORITY` (0–10, additional-skill drop order), `IS_ADDITIONAL_SKILL` (`true`/`false`).

## Preconditions and safety

- Target org authenticated via `sf` CLI, Service Cloud license, `sf` CLI ≥ 2.139.6.
- Omni-Channel base settings enabled with **skills-based routing** turned on (`service-omni-base-settings-configure`).
- The referenced `Skill` already exists (`service-omni-skills-based-routing-configure`).
- The three-way `safe_to_write` production guard applies.

## Run

1. **safe_to_write** — query `Organization`; refuse to write to a real production org.
2. **Skill prereq** — query `Skill` by DeveloperName; if absent, block and point at `service-omni-skills-based-routing-configure`.
3. **Merge** — read the existing `WorkSkillRouting.Metadata` through the Tooling API, preserve unrelated attributes, and replace or append only the requested `(field, value)` mapping. An inconclusive read blocks the write; `WSR_REPLACE=1` is the explicit destructive-replacement escape hatch.
4. **Deploy** — materialize the merged `WorkSkillRouting` record (elements in XSD/alphabetical order) and deploy it via the Metadata API (async + poll to a terminal state).
5. **Classify** — read `files[].state` (`Created` / `Changed` / `Unchanged`) to report `created` / `updated` / `reused`.

## Behavior

**Idempotent + merge-safe.** WorkSkillRouting permits a single rule per related entity, so the rule's fullName defaults to the entity name. Re-running the same mapping reports `reused`; a new mapping is merged into the existing attribute list; changing the same field/value mapping updates only that entry. The skill never silently replaces an existing rule when its current metadata could not be read.

**Graceful degradation.** WorkSkillRouting is not provisioned on every org (some trials/CDOs). A deploy failure shaped like `INVALID_TYPE` / "not available" / "WorkSkillRouting" is reported as `blocked` with a clear limitation message and a pointer to base settings — the skill surfaces the limitation rather than crashing.

## Output contract

A single JSON object: `status` ∈ `created` | `updated` | `reused` | `blocked` (plus `action_needed` in plan mode), `rule` (`{developer_name, master_label, related_entity, is_active, state}`), `attribute` (`{field, skill, value, skill_level, skill_priority, is_additional_skill}`), `merge` (`{merged_from_existing, attribute_count, preserved_count}`), `deploy_id`, `manual_actions`, `blocking_issue`.

## Limitations

- One field→skill mapping per invocation and one rule per related entity. Multiple invocations safely accumulate attributes on that rule.
- Does not create the Skill, ServiceResources, agent users, queues, or presence configuration.
- Field/value correctness is validated by the platform at deploy time; an invalid field or value surfaces as a `blocked` deploy failure.

## References

| File | When to read |
|---|---|
| `references/api-notes.md` | WorkSkillRouting metadata shape, XSD element order, one-rule-per-entity constraint, attribute fields, and graceful-degradation triggers |
| `scripts/tests/test_work_skill_routing_contracts.py` | When validating changes — run `python3 scripts/tests/test_work_skill_routing_contracts.py` from this skill directory |

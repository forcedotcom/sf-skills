---
name: service-omni-attribute-routing-configure
description: "Use to manage Omni-Channel attribute-based routing rules through the Tooling API. TRIGGER when: list attribute-routing rules, inspect a WorkSkillRouting rule, create an inactive routing rule, add a field-to-skill mapping, activate a complete routing rule, deactivate a routing rule, or delete a routing rule or attribute. Do not use to create agent skills or routing flows."
allowed-tools: Bash Read Write Grep Glob
metadata:
  version: "1.0"
  domains: ["Service"]
  minApiVersion: "68.0"
  relatedSkills:
    - "service-omni-work-skill-routing-configure"
  accessCheck:
    - type: license
      value: ServiceCloud
  cliTools:
    - tool: ["jq"]
      semver: ">=1.6"
    - tool: ["python3"]
      semver: ">=3.10"
    - tool: ["sf"]
      semver: ">=2.139.6"
---

# service-omni-attribute-routing-configure

Manage the full `WorkSkillRouting` and `WorkSkillRoutingAttribute` lifecycle using the approved Tooling API contract. Create rules inactive, add all mappings, and activate only after at least one mapping exists.

## Usage

```bash
bash scripts/configure-and-report.sh <org> list
bash scripts/configure-and-report.sh <org> get <rule-id>
bash scripts/configure-and-report.sh <org> create <developer-name> <label> <related-entity>
bash scripts/configure-and-report.sh <org> add-attribute <rule-id> <Entity.Field> <value> <skill-id> <level> <related-entity> [additional] [priority]
bash scripts/configure-and-report.sh <org> set-active <rule-id> true|false
CONFIRM_DELETE=1 bash scripts/configure-and-report.sh <org> delete-attribute <attribute-id>
CONFIRM_DELETE=1 bash scripts/configure-and-report.sh <org> delete-rule <rule-id>
```

## Safety and behavior

- Reads require View Setup. Writes require Customize Application and are refused on production customer orgs.
- Omni-Channel and Skills-Based Routing must be enabled, and referenced `Skill` records must already exist.
- Creation always starts inactive. Activation reads the complete Metadata compound, preserves all mappings, removes the read-only `urls` member, changes only `isActive`, and verifies with a cold read.
- The script rejects activation without mappings, invalid skill levels, invalid additional-skill priorities, and deletion without `CONFIRM_DELETE=1`.
- Existing identical mappings are reused.

## Boundaries

Use `service-omni-work-skill-routing-configure` for the simpler one-mapping Metadata API workflow. Use this skill when the user explicitly needs Tooling CRUD, multiple mappings, activation control, or deletion.

## Reference

Read [references/api-notes.md](references/api-notes.md) before changing the payload or compound Metadata handling.

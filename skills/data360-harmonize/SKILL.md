---
name: data360-harmonize
description: "Salesforce Data Cloud Harmonize phase. Use this skill when the user works with DMOs, mappings, relationships, identity resolution, unified profiles, data graphs, or universal IDs. TRIGGER when: user works with DMOs, mappings, relationships, identity resolution, unified profiles, data graphs, or universal IDs. DO NOT TRIGGER when: the task is only about streams/DLOs (use data360-prepare), segments/insights (use data360-segment), retrieval/search (use data360-query), or STDM/session tracing (use agentforce-observe)."
compatibility: "Requires an external community sf data360 CLI plugin and a Data Cloud-enabled org"
metadata:
  version: "1.0"
---

# data360-harmonize: Data Cloud Harmonize Phase

Use this skill when the user needs **schema harmonization and unification work**: DMOs, field mappings, relationships, identity resolution, unified profiles, data graphs, or universal ID lookup.

## When This Skill Owns the Task

Use `data360-harmonize` when the work involves:
- `sf data360 dmo *`
- `sf data360 identity-resolution *`
- `sf data360 data-graph *`
- `sf data360 profile *`
- `sf data360 universal-id lookup`

Delegate elsewhere when the user is:
- still ingesting streams or building DLOs → [data360-prepare](../data360-prepare/SKILL.md)
- working on segment logic or calculated insights → [data360-segment](../data360-segment/SKILL.md)
- running SQL, describe, or search-index workflows → [data360-query](../data360-query/SKILL.md)

---

## Required Context to Gather First

Ask for or infer:
- source DLO and target DMO names
- whether the task is schema creation, mapping, IR, or graph-related
- target org alias
- whether a ruleset already exists
- the user’s desired unified entity model

---

## Core Operating Rules

- Inspect DMO schema before creating mappings.
- Run the shared readiness classifier before mutating harmonization assets: `node ../data360-orchestrate/scripts/diagnose-org.mjs -o <org> --phase harmonize --json`.
- Prefer `dmo list --all` when browsing the catalog, but use first-page `dmo list` for fast readiness checks.
- Use `query describe` or `dmo get --json` instead of inventing unsupported describe flows.
- Treat identity resolution runs as asynchronous and verify results after execution.
- Keep unified-profile work separate from STDM/session tracing work.

---

## Recommended Workflow

### 1. Classify readiness for harmonize work
```bash
node ../data360-orchestrate/scripts/diagnose-org.mjs -o <org> --phase harmonize --json
```

### 2. Inspect the catalog
```bash
sf data360 dmo list --all -o <org> 2>/dev/null
sf data360 identity-resolution list -o <org> 2>/dev/null
```

### 3. Inspect schema before mapping
```bash
sf data360 query describe -o <org> --table ssot__Individual__dlm 2>/dev/null
sf data360 dmo get -o <org> --name ssot__Individual__dlm --json 2>/dev/null
```

### 4. Create or review mappings intentionally
```bash
sf data360 dmo mapping-list -o <org> --source Contact_Home__dll --target ssot__Individual__dlm 2>/dev/null
sf data360 dmo map-to-canonical -o <org> --dlo Contact_Home__dll --dmo ssot__Individual__dlm --dry-run 2>/dev/null
```

### 5. Run IR only after mappings are trustworthy
```bash
sf data360 identity-resolution create -o <org> -f ir-ruleset.json 2>/dev/null
sf data360 identity-resolution run -o <org> --name Main 2>/dev/null
```

---

## High-Signal Gotchas

- `dmo list` should usually use `--all`.
- Use `query describe` or `dmo get --json`; there is no `dmo describe` command.
- Mapping and related commands can be sensitive to API-version differences.
- Unified DMO names are ruleset-specific rather than generic.
- Data graph definitions are sensitive to field selection and relationship shape.
- If `dmo list` works but `identity-resolution list` is gated, treat that as a phase-specific gap rather than a full Data Cloud outage.

---

## Output Format

```text
Harmonize task: <dmo / mapping / relationship / ir / data-graph>
Source/target: <dlo → dmo or ruleset/graph names>
Target org: <alias>
Artifacts: <json files / commands>
Verification: <passed / partial / blocked>
Next step: <segment / retrieve / follow-up>
```

---

## References

- [README.md](README.md)
- [../data360-orchestrate/assets/definitions/dmo.template.json](../data360-orchestrate/assets/definitions/dmo.template.json)
- [../data360-orchestrate/assets/definitions/mapping.template.json](../data360-orchestrate/assets/definitions/mapping.template.json)
- [../data360-orchestrate/assets/definitions/relationship.template.json](../data360-orchestrate/assets/definitions/relationship.template.json)
- [../data360-orchestrate/assets/definitions/identity-resolution.template.json](../data360-orchestrate/assets/definitions/identity-resolution.template.json)
- [../data360-orchestrate/assets/definitions/data-graph.template.json](../data360-orchestrate/assets/definitions/data-graph.template.json)
- [../data360-orchestrate/references/feature-readiness.md](../data360-orchestrate/references/feature-readiness.md)

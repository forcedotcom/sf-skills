---
name: segmenting-datacloud
description: "Salesforce Data Cloud Segment phase. Use this skill when the user creates or publishes segments, manages calculated insights, or troubleshoots audience SQL in Data Cloud. TRIGGER when: user creates or publishes segments, manages calculated insights, inspects segment counts or membership, or troubleshoots audience SQL in Data Cloud. DO NOT TRIGGER when: the task is DMO/mapping/identity-resolution work (use harmonizing-datacloud), activation work (use activating-datacloud), query/search-index work (use retrieving-datacloud), or Standard Data Model (STDM)/session tracing (use observing-agentforce)."
license: MIT
compatibility: "Requires an external community sf data360 CLI plugin and a Data Cloud-enabled org"
metadata:
  version: "1.0"
---

# segmenting-datacloud: Data Cloud Segment Phase

Use this skill when the user needs **audience and insight work**: segments, calculated insights, publish workflows, member counts, or troubleshooting Data Cloud segment SQL.

## When This Skill Owns the Task

Use `segmenting-datacloud` when the work involves:
- `sf data360 segment *`
- `sf data360 calculated-insight *`
- segment publish workflows
- member counts and segment troubleshooting
- calculated insight execution and verification

Delegate elsewhere when the user is:
- still building Data Model Objects (DMOs), mappings, or identity resolution → [harmonizing-datacloud](../harmonizing-datacloud/SKILL.md)
- activating a segment downstream → [activating-datacloud](../activating-datacloud/SKILL.md)
- writing read-only SQL or search-index queries → [retrieving-datacloud](../retrieving-datacloud/SKILL.md)

---

## Required Context to Gather First

Ask for or infer:
- target org alias
- unified DMO (Data Model Object) or base entity name
- whether the user wants create, publish, inspect, or troubleshoot
- whether the asset is a segment or calculated insight
- expected success metric: member count, aggregate value, or publish status

---

## Core Operating Rules

- Treat Data Cloud segment SQL as distinct from CRM SOQL.
- Run the shared readiness classifier from the `orchestrating-datacloud` skill before mutating audience assets: `node ../orchestrating-datacloud/scripts/diagnose-org.mjs -o <org> --phase segment --json`.
- Prefer reusable JSON definitions for repeatable segment and CI creation.
- Use `--api-version 64.0` when segment creation behavior is unstable on newer defaults.
- Verify with counts or SQL after publish/run steps instead of assuming success.
- Use SQL joins rather than `segment members` when readable member details are needed.

---

## Recommended Workflow

### 1. Classify readiness for segment work
```bash
node ../orchestrating-datacloud/scripts/diagnose-org.mjs -o <org> --phase segment --json
```

### 2. Inspect current state
```bash
sf data360 segment list -o <org> 2>/dev/null
sf data360 calculated-insight list -o <org> 2>/dev/null
```

### 3. Create with reusable JSON definitions
```bash
sf data360 segment create -o <org> -f segment.json --api-version 64.0 2>/dev/null
sf data360 calculated-insight create -o <org> -f ci.json 2>/dev/null
```

### 4. Publish or run explicitly
```bash
sf data360 segment publish -o <org> --name My_Segment 2>/dev/null
sf data360 calculated-insight run -o <org> --name Lifetime_Value 2>/dev/null
```

### 5. Verify with counts or SQL
```bash
sf data360 segment count -o <org> --name My_Segment 2>/dev/null
sf data360 query sql -o <org> --sql 'SELECT COUNT(*) FROM "UnifiedssotIndividualMain__dlm"' 2>/dev/null
```

---

## High-Signal Gotchas

- Segment creation can require `--api-version 64.0`.
- `segment members` returns opaque IDs; use SQL joins when human-readable member details are needed.
- Segment SQL is not SOQL.
- Calculated insight assets and segment SQL have different limitations.
- Publish/run steps may kick off asynchronous work even when the command returns quickly.
- An empty segment or calculated-insight list usually means the module is reachable but unconfigured, not unavailable.

---

## Output Format

```text
Segment task: <segment / calculated-insight>
Action: <create / publish / inspect / troubleshoot>
Target org: <alias>
Artifacts: <definition files / commands>
Verification: <member count / query result / publish state>
Next step: <act / retrieve / follow-up>
```

---

## References

- [README.md](README.md)
- [../orchestrating-datacloud/assets/definitions/calculated-insight.template.json](../orchestrating-datacloud/assets/definitions/calculated-insight.template.json)
- [../orchestrating-datacloud/assets/definitions/segment.template.json](../orchestrating-datacloud/assets/definitions/segment.template.json)
- [../orchestrating-datacloud/references/feature-readiness.md](../orchestrating-datacloud/references/feature-readiness.md)
- [../orchestrating-datacloud/UPSTREAM.md](../orchestrating-datacloud/UPSTREAM.md)

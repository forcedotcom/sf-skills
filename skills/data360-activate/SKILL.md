---
name: data360-activate
description: "Salesforce Data Cloud Act phase. Use this skill when the user manages activations, activation targets, data actions, or downstream delivery of Data Cloud audiences and data. TRIGGER when: user manages activations, activation targets, data actions, or downstream delivery of Data Cloud audiences and data. DO NOT TRIGGER when: the task is segment creation (use data360-segment), data retrieval/search work (use data360-query), or STDM/session tracing (use agentforce-observe)."
compatibility: "Requires an external community sf data360 CLI plugin and a Data Cloud-enabled org"
metadata:
  version: "1.0"
---

# data360-activate: Data Cloud Act Phase

Use this skill when the user needs **downstream delivery work**: activations, activation targets, data actions, or pushing Data Cloud outputs into other systems.

## When This Skill Owns the Task

Use `data360-activate` when the work involves:
- `sf data360 activation *`
- `sf data360 activation-target *`
- `sf data360 data-action *`
- `sf data360 data-action-target *`
- verifying downstream delivery setup

Delegate elsewhere when the user is:
- still building the audience or insight → [data360-segment](../data360-segment/SKILL.md)
- exploring query/search or search indexes → [data360-query](../data360-query/SKILL.md)
- setting up base connections or ingestion → [data360-connect](../data360-connect/SKILL.md), [data360-prepare](../data360-prepare/SKILL.md)

---

## Required Context to Gather First

Ask for or infer:
- target org alias
- destination platform or downstream system
- whether the segment already exists and is published
- whether the user needs create, inspect, update, or delete
- whether the task is activation-focused or data-action-focused

---

## Core Operating Rules

- Verify the upstream segment or insight is healthy before creating downstream delivery assets.
- Run the shared readiness classifier before mutating activation assets: `node ../data360-orchestrate/scripts/diagnose-org.mjs -o <org> --phase act --json`.
- Inspect available platforms and targets before mutating activation setup.
- Keep destination definitions deterministic and reusable where possible.
- Treat downstream credential and platform constraints as separate validation concerns.
- Prefer read-only inspection first when the destination state is unclear.

---

## Recommended Workflow

### 1. Classify readiness for act work
```bash
node ../data360-orchestrate/scripts/diagnose-org.mjs -o <org> --phase act --json
```

### 2. Inspect destinations first
```bash
sf data360 activation platforms -o <org> 2>/dev/null
sf data360 activation-target list -o <org> 2>/dev/null
sf data360 data-action-target list -o <org> 2>/dev/null
```

### 3. Create the destination before the activation
```bash
sf data360 activation-target create -o <org> -f target.json 2>/dev/null
sf data360 data-action-target create -o <org> -f target.json 2>/dev/null
```

### 4. Create the activation or data action
```bash
sf data360 activation create -o <org> -f activation.json 2>/dev/null
sf data360 data-action create -o <org> -f action.json 2>/dev/null
```

### 5. Verify downstream readiness
```bash
sf data360 activation list -o <org> 2>/dev/null
sf data360 activation data -o <org> --name <activation> 2>/dev/null
```

---

## High-Signal Gotchas

- Activation design depends on a healthy published upstream segment.
- Destination configuration usually comes before activation creation.
- Downstream credential and platform constraints may live outside the Data Cloud CLI alone.
- Read-only inspection is the safest first move when the destination setup is unclear.
- `CdpActivationTarget` or `CdpActivationExternalPlatform` means the activation surface is gated for the current org/user; guide the user toward activation setup, permissions, and destination configuration instead of retrying blindly.

---

## Output Format

```text
Act task: <activation / activation-target / data-action / data-action-target>
Destination: <platform or target>
Target org: <alias>
Artifacts: <definition files / commands>
Verification: <listed / created / blocked>
Next step: <destination validation or downstream testing>
```

---

## References

- [README.md](README.md)
- [../data360-orchestrate/assets/definitions/activation-target.template.json](../data360-orchestrate/assets/definitions/activation-target.template.json)
- [../data360-orchestrate/assets/definitions/activation.template.json](../data360-orchestrate/assets/definitions/activation.template.json)
- [../data360-orchestrate/assets/definitions/data-action-target.template.json](../data360-orchestrate/assets/definitions/data-action-target.template.json)
- [../data360-orchestrate/assets/definitions/data-action.template.json](../data360-orchestrate/assets/definitions/data-action.template.json)
- [../data360-orchestrate/UPSTREAM.md](../data360-orchestrate/UPSTREAM.md)
- [../data360-orchestrate/references/plugin-setup.md](../data360-orchestrate/references/plugin-setup.md)
- [../data360-orchestrate/references/feature-readiness.md](../data360-orchestrate/references/feature-readiness.md)

---
name: data360-orchestrate
description: "Salesforce Data Cloud product orchestrator for connect→prepare→harmonize→segment→act workflows. Use this skill when the user needs a multi-step Data Cloud pipeline, cross-phase troubleshooting, or data space and data kit management. TRIGGER when: user needs a multi-step Data Cloud pipeline, asks to set up or troubleshoot Data Cloud across phases, manages data spaces or data kits, or wants a cross-phase sf data360 workflow. DO NOT TRIGGER when: work is isolated to a single phase (use the matching phase-specific skill), the task is STDM/session tracing/parquet telemetry (use agentforce-observe), standard CRM SOQL (use platform-soql-query), or Apex implementation (use platform-apex-generate)."
compatibility: "Requires an external community sf data360 CLI plugin and a Data Cloud-enabled org"
metadata:
  version: "1.0"
---

# data360-orchestrate: Salesforce Data Cloud Orchestrator

Use this skill when the user needs **product-level Data Cloud workflow guidance** rather than a single isolated command family: pipeline setup, cross-phase troubleshooting, data spaces, data kits, or deciding whether a task belongs in Connect, Prepare, Harmonize, Segment, Act, or Retrieve.

This skill intentionally follows sf-skills house style while using the external `sf data360` command surface as the runtime. The plugin is **not vendored into this repo**.

---

## When This Skill Owns the Task

Use `data360-orchestrate` when the work involves:
- multi-phase Data Cloud setup or remediation
- data spaces (`sf data360 data-space *`)
- data kits (`sf data360 data-kit *`)
- health checks (`sf data360 doctor`)
- CRM-to-unified-profile pipeline design
- deciding how to move from ingestion → harmonization → segmentation → activation
- cross-phase troubleshooting where the root cause is not yet clear

Delegate to a phase-specific skill when the user is focused on one area:

| Phase | Use this skill | Typical scope |
|---|---|---|
| Connect | [data360-connect](../data360-connect/SKILL.md) | connections, connectors, source discovery |
| Prepare | [data360-prepare](../data360-prepare/SKILL.md) | data streams, DLOs, transforms, DocAI |
| Harmonize | [data360-harmonize](../data360-harmonize/SKILL.md) | DMOs, mappings, identity resolution, data graphs |
| Segment | [data360-segment](../data360-segment/SKILL.md) | segments, calculated insights |
| Act | [data360-activate](../data360-activate/SKILL.md) | activations, activation targets, data actions |
| Retrieve | [data360-query](../data360-query/SKILL.md) | SQL, search indexes, vector search, async query |

Delegate outside the family when the user is:
- extracting Session Tracing / STDM telemetry → [agentforce-observe](../agentforce-observe/SKILL.md)
- writing CRM SOQL only → [platform-soql-query](../platform-soql-query/SKILL.md)
- loading CRM source data → [platform-data-manage](../platform-data-manage/SKILL.md)
- creating missing CRM schema → [platform-custom-object-generate](../platform-custom-object-generate/SKILL.md) or [platform-custom-field-generate](../platform-custom-field-generate/SKILL.md)
- implementing downstream Apex or Flow logic → [platform-apex-generate](../platform-apex-generate/SKILL.md), [automation-flow-generate](../automation-flow-generate/SKILL.md)

---

## Required Context to Gather First

Ask for or infer:
- target org alias
- whether the plugin is already installed and linked
- whether the user wants design guidance, read-only inspection, or live mutation
- data sources involved: CRM objects, external databases, file ingestion, knowledge, etc.
- desired outcome: unified profiles, segments, activations, vector search, analytics, or troubleshooting
- whether the user is working in the default data space or a custom one
- whether the org has already been classified with `scripts/diagnose-org.mjs`
- which command family is failing today, if any

If plugin availability or org readiness is uncertain, start with:
- [references/plugin-setup.md](references/plugin-setup.md)
- [references/feature-readiness.md](references/feature-readiness.md)
- `scripts/verify-plugin.sh`
- `scripts/diagnose-org.mjs`
- `scripts/bootstrap-plugin.sh`

---

## Core Operating Rules

- Use the external `sf data360` plugin runtime; do **not** reimplement or vendor the command layer.
- Prefer the smallest phase-specific skill once the task is localized.
- Run readiness classification before mutation-heavy work. Prefer `scripts/diagnose-org.mjs` over guessing from one failing command.
- For `sf data360` commands, suppress linked-plugin warning noise with `2>/dev/null` unless the stderr output is needed for debugging.
- Distinguish **Data Cloud SQL** from CRM SOQL.
- Do **not** treat `sf data360 doctor` as a full-product readiness check; the current upstream command only checks the search-index surface.
- Do **not** treat `query describe` as a universal tenant probe; only use it with a known DMO/DLO table after broader readiness is confirmed.
- Preserve Data Cloud-specific API-version workarounds when they matter.
- Prefer generic, reusable JSON definition files over org-specific workshop payloads.

---

## Recommended Workflow

### 1. Verify the runtime and auth
Confirm:
- `sf` is installed
- the community Data Cloud plugin is linked
- the target org is authenticated

Recommended checks:
```bash
sf data360 man
sf org display -o <alias>
bash ./scripts/verify-plugin.sh <alias>
```

Treat `sf data360 doctor` as a broad health signal, not the sole gate. On partially provisioned orgs it can fail even when read-only command families like connectors, DMOs, or segments still work.

### 2. Classify readiness before changing anything
Run the shared classifier first:
```bash
node ./scripts/diagnose-org.mjs -o <org> --json
```

Only use a query-plane probe after you know the table name is real:
```bash
node ./scripts/diagnose-org.mjs -o <org> --phase retrieve --describe-table MyDMO__dlm --json
```

Use the classifier to distinguish:
- empty-but-enabled modules
- feature-gated modules
- query-plane issues
- runtime/auth failures

### 3. Discover existing state with read-only commands
Use targeted inspection after classification:
```bash
sf data360 doctor -o <org> 2>/dev/null
sf data360 data-space list -o <org> 2>/dev/null
sf data360 data-stream list -o <org> 2>/dev/null
sf data360 dmo list -o <org> 2>/dev/null
sf data360 identity-resolution list -o <org> 2>/dev/null
sf data360 segment list -o <org> 2>/dev/null
sf data360 activation platforms -o <org> 2>/dev/null
```

### 4. Localize the phase
Route the task:
- source/connector issue → Connect
- ingestion/DLO/stream issue → Prepare
- mapping/IR/unified profile issue → Harmonize
- audience or insight issue → Segment
- downstream push issue → Act
- SQL/search/index issue → Retrieve

### 5. Choose deterministic artifacts when possible
Prefer JSON definition files and repeatable scripts over one-off manual steps. Generic templates live in:
- `assets/definitions/data-stream.template.json`
- `assets/definitions/dmo.template.json`
- `assets/definitions/mapping.template.json`
- `assets/definitions/relationship.template.json`
- `assets/definitions/identity-resolution.template.json`
- `assets/definitions/data-graph.template.json`
- `assets/definitions/calculated-insight.template.json`
- `assets/definitions/segment.template.json`
- `assets/definitions/activation-target.template.json`
- `assets/definitions/activation.template.json`
- `assets/definitions/data-action-target.template.json`
- `assets/definitions/data-action.template.json`
- `assets/definitions/search-index.template.json`

### 6. Verify after each phase
Typical verification:
- stream/DLO exists
- DMO/mapping exists
- identity resolution run completed
- unified records or segment counts look correct
- activation/search index status is healthy

---

## High-Signal Gotchas

- `connection list` requires `--connector-type`.
- `dmo list --all` is useful when you need the full catalog, but first-page `dmo list` is often enough for readiness checks and much faster.
- Segment creation may need `--api-version 64.0`.
- `segment members` returns opaque IDs; use SQL joins for human-readable details.
- `sf data360 doctor` can fail on partially provisioned orgs even when some read-only commands still work; fall back to targeted smoke checks.
- `query describe` errors such as `Couldn't find CDP tenant ID` or `DataModelEntity ... not found` are query-plane clues, not automatic proof that the whole product is disabled.
- Many long-running jobs are asynchronous in practice even when the command returns quickly.
- Some Data Cloud operations still require UI setup outside the CLI runtime.

---

## Output Format

When finishing, report in this order:
1. **Task classification**
2. **Runtime status**
3. **Readiness classification**
4. **Phase(s) involved**
5. **Commands or artifacts used**
6. **Verification result**
7. **Next recommended step**

Suggested shape:

```text
Data Cloud task: <setup / inspect / troubleshoot / migrate>
Runtime: <plugin ready / missing / partially verified>
Readiness: <ready / ready_empty / partial / feature_gated / blocked>
Phases: <connect / prepare / harmonize / segment / act / retrieve>
Artifacts: <json files, commands, scripts>
Verification: <passed / partial / blocked>
Next step: <next phase, setup guidance, or cross-skill handoff>
```

---

## Cross-Skill Integration

| Need | Delegate to | Reason |
|---|---|---|
| load or clean CRM source data | [platform-data-manage](../platform-data-manage/SKILL.md) | seed or fix source records before ingestion |
| create missing CRM schema | [platform-custom-object-generate](../platform-custom-object-generate/SKILL.md), [platform-custom-field-generate](../platform-custom-field-generate/SKILL.md) | Data Cloud expects existing objects/fields |
| deploy permissions or bundles | [platform-metadata-deploy](../platform-metadata-deploy/SKILL.md) | environment preparation |
| write Apex against Data Cloud outputs | [platform-apex-generate](../platform-apex-generate/SKILL.md) | code implementation |
| Flow automation after segmentation/activation | [automation-flow-generate](../automation-flow-generate/SKILL.md) | declarative orchestration |
| session tracing / STDM / parquet analysis | [agentforce-observe](../agentforce-observe/SKILL.md) | different Data Cloud use case |

---

## Reference Map

### Start here
- [README.md](README.md)
- [references/plugin-setup.md](references/plugin-setup.md)
- [references/feature-readiness.md](references/feature-readiness.md)
- [UPSTREAM.md](UPSTREAM.md)

### Phase skills
- [data360-connect](../data360-connect/SKILL.md)
- [data360-prepare](../data360-prepare/SKILL.md)
- [data360-harmonize](../data360-harmonize/SKILL.md)
- [data360-segment](../data360-segment/SKILL.md)
- [data360-activate](../data360-activate/SKILL.md)
- [data360-query](../data360-query/SKILL.md)

### Deterministic helpers
- [scripts/bootstrap-plugin.sh](scripts/bootstrap-plugin.sh)
- [scripts/verify-plugin.sh](scripts/verify-plugin.sh)
- [scripts/diagnose-org.mjs](scripts/diagnose-org.mjs)
- [assets/definitions/](assets/definitions/)

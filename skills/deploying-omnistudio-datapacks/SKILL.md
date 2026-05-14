---
name: deploying-omnistudio-datapacks
description: "Salesforce Industries DataPack deployment automation using Vlocity Build. TRIGGER when: user deploys or validates OmniStudio/Vlocity DataPacks with vlocity commands (packDeploy/packRetry/packExport/packGetDiffs), sets up DataPack CI/CD pipelines, or troubleshoots DataPack migration errors. DO NOT TRIGGER when: deploying Salesforce metadata with sf project deploy (use deploying-metadata), authoring OmniStudio artifacts (use building-omnistudio-*), or writing Apex/LWC business logic (use generating-apex/generating-lwc-components)."
license: MIT
metadata:
  version: "1.0"
---

# deploying-omnistudio-datapacks: Vlocity Build DataPack Deployment

Use this skill when the user needs **Vlocity DataPack deployment orchestration**: export/deploy workflow, manifest-driven deploys, failure triage, and CI/CD sequencing for OmniStudio/Industries DataPacks.

---

## Scope

Use `deploying-omnistudio-datapacks` when work involves:
- `vlocity packDeploy`, `packRetry`, `packContinue`, `packExport`, `packGetDiffs`, `validateLocalData`
- DataPack job-file design (`projectPath`, `expansionPath`, `manifest`, `queries`)
- org-to-org DataPack migration and retry loops
- troubleshooting DataPack dependency, matching-key, and GlobalKey issues

Delegate elsewhere when the user is:
- deploying standard metadata with `sf project deploy` -> [deploying-metadata](../deploying-metadata/SKILL.md)
- building OmniScripts, FlexCards, IPs, or Data Mappers -> `building-omnistudio-*`
- designing Product2 EPC bundles -> [modeling-omnistudio-epc-catalog](../modeling-omnistudio-epc-catalog/SKILL.md)
- writing Apex/LWC code -> [generating-apex](../generating-apex/SKILL.md), [generating-lwc-components](../generating-lwc-components/SKILL.md)

---

## Critical Operating Rules

- Use **Vlocity Build (`vlocity`)** commands for DataPacks, not `sf project deploy`.
- Prefer Salesforce CLI auth integration (`-sfdx.username <alias>`) over username/password files when available.
- Always run a **pre-deploy quality gate** before full deploy:
  1) `validateLocalData`
  2) optional `packGetDiffs`
  3) then `packDeploy`
- Use `packRetry` repeatedly when error counts are dropping; stop when retries no longer improve results.
- Keep matching-key strategy and GlobalKey integrity consistent across source and target orgs.

---

## Required Context to Gather First

Ask for or infer:
- source org and target org aliases
- job file path and DataPack project path
- deployment scope (full project, manifest subset, or specific `-key`)
- whether this is export, deploy, retry, continue, or diff-only
- namespace model (`%vlocity_namespace%`, `vlocity_cmt`, or core)
- known constraints (new sandbox bootstrap, trigger behavior, matching key customizations)

Preflight checks:

```bash
vlocity help
sf org list
sf org display --target-org <alias> --json
test -f <job-file>.yaml
```

---

## Recommended Workflow

### 1. Ensure tool readiness
```bash
npm install --global vlocity
vlocity help
```

### 2. Validate project data locally
```bash
vlocity -sfdx.username <source-alias> -job <job-file>.yaml validateLocalData
```

Use `--fixLocalGlobalKeys` only when explicitly requested and after explaining impact.

### 3. Export from source (when needed)
```bash
vlocity -sfdx.username <source-alias> -job <job-file>.yaml packExport
vlocity -sfdx.username <source-alias> -job <job-file>.yaml packRetry
```

### 4. Deploy to target
```bash
vlocity -sfdx.username <target-alias> -job <job-file>.yaml packDeploy
vlocity -sfdx.username <target-alias> -job <job-file>.yaml packRetry
```

### 5. Continue interrupted jobs
```bash
vlocity -sfdx.username <target-alias> -job <job-file>.yaml packContinue
```

### 6. Verify post-deploy parity
```bash
vlocity -sfdx.username <target-alias> -job <job-file>.yaml packGetDiffs
```

Job-file starter: [references/job-file-template.md](references/job-file-template.md)

---

## Gotchas

| Error / symptom | Likely cause | Default fix direction |
|---|---|---|
| `No match found for ...` | missing dependency in target org | include missing DataPack key and redeploy |
| `Duplicate Results found for ... GlobalKey` | duplicate records in target | clean duplicates and re-run deploy |
| `Multiple Imported Records ... same Salesforce Record` | source duplicate matching-key records | remove duplicates in source and re-export |
| `No Configuration Found` | outdated DataPack settings | run `packUpdateSettings` or enable `autoUpdateSettings` |
| `Some records were not processed` | settings mismatch / partial dependency state | refresh settings both orgs, then retry |
| SASS / template compile failures | missing referenced UI template assets | export/deploy referenced template dependencies first |

Detailed matrix: [references/troubleshooting-matrix.md](references/troubleshooting-matrix.md)

---

## CI/CD Guidance

Default pipeline shape:
1. authenticate orgs (`sf org login ...`)
2. validate local DataPack integrity (`validateLocalData`)
3. export changed scope (`packExport` or manifest-driven export)
4. deploy (`packDeploy`)
5. retry loop (`packRetry`) until stable
6. compare (`packGetDiffs`) and publish deployment report

For incremental deploy optimization, use job-file options such as:
- `gitCheck: true`
- `gitCheckKey: <folder>`
- `manifest` for deterministic scope control

---

## Cross-Skill Integration

| Need | Delegate to | Reason |
|---|---|---|
| metadata deploy outside DataPacks | [deploying-metadata](../deploying-metadata/SKILL.md) | Metadata API workflows |
| OmniStudio component authoring | `building-omnistudio-*` | build artifacts before deploy |
| EPC product and offer payload authoring | [modeling-omnistudio-epc-catalog](../modeling-omnistudio-epc-catalog/SKILL.md) | Product2/DataPack model quality |
| Apex trigger/log error diagnosis | [debugging-apex-logs](../debugging-apex-logs/SKILL.md), [generating-apex](../generating-apex/SKILL.md) | automation-side root-cause fixes |

---

## Output Expectations

After completing a DataPack operation, deliver a completion block:

```text
DataPack goal: <export / deploy / retry / diff / ci-cd>
Source org: <alias or N/A>
Target org: <alias or N/A>
Scope: <job file + manifest/key/full>
Result: <passed / failed / partial>
Key findings: <errors, dependencies, retries, diffs>
Next step: <safe follow-up action>
```

---

## Reference File Index

| File | When to read |
|------|-------------|
| `references/job-file-template.md` | Before advising on job file structure — load as baseline configuration reference |
| `references/troubleshooting-matrix.md` | When user reports deploy failures — load to diagnose DataPack errors and apply fix directions |
| `examples/business-internet-plus-bundle/TRANSCRIPT.md` | Example of validation planning and execution for a Product2 bundle |
| `examples/business-internet-plus-bundle/deploy-business-internet-plus-bundle.yaml` | Example job file for scope-limited `validateLocalData` run |
| `examples/business-internet-plus-bundle-deploy/TRANSCRIPT.md` | Example of full deploy cycle including `packDeploy` and `packRetry` outcomes |
| `examples/business-internet-plus-bundle-deploy/deploy-business-internet-plus-bundle.yaml` | Example job file for staged deployment with manifest targeting |

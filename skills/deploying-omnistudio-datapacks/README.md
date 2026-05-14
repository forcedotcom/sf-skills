# deploying-omnistudio-datapacks

Salesforce Industries DataPack deployment automation using Vlocity Build. Export, validate, deploy, retry, and compare OmniStudio/Vlocity DataPacks with predictable workflow guardrails.

## Features

- **DataPack Deployment Workflow**: Run `packExport`, `packDeploy`, `packRetry`, `packContinue`, and `packGetDiffs`
- **Job File Guidance**: Build deterministic `projectPath`, `expansionPath`, `queries`, and `manifest` job patterns
- **Validation-First Operations**: Gate deployment with `validateLocalData` and dependency checks
- **Failure Triage**: Diagnose matching-key, GlobalKey, dependency, and configuration drift failures
- **CI/CD Patterns**: Support manifest-driven and git-aware deployment sequencing

## Usage

Invoke this skill when working with OmniStudio/Vlocity DataPack deployments:

```
Skill: deploying-omnistudio-datapacks
Request: "Deploy my OmniStudio DataPacks to UAT using Vlocity Build and include retry guidance."
```

## Common Operations

| Operation | Example Request |
|-----------|-----------------|
| Export | "Export DataPacks from source org with this job file." |
| Validate local files | "Run pre-deploy validation and identify key issues." |
| Deploy | "Deploy DataPacks to target org using packDeploy." |
| Retry failures | "Run packRetry and summarize what remains." |
| Resume interrupted run | "Continue the failed deployment job." |
| Compare with target | "Run packGetDiffs and report drift." |

## Key Commands

```bash
# Validate local DataPack integrity
vlocity -sfdx.username [sourceAlias] -job [jobFile].yaml validateLocalData

# Export from source
vlocity -sfdx.username [sourceAlias] -job [jobFile].yaml packExport

# Deploy to target
vlocity -sfdx.username [targetAlias] -job [jobFile].yaml packDeploy

# Retry failed DataPacks
vlocity -sfdx.username [targetAlias] -job [jobFile].yaml packRetry

# Continue interrupted execution
vlocity -sfdx.username [targetAlias] -job [jobFile].yaml packContinue

# Compare local files to target org
vlocity -sfdx.username [targetAlias] -job [jobFile].yaml packGetDiffs
```

## Best Practices

| Rule | Details |
|------|---------|
| Validate first | Run `validateLocalData` before deploy |
| Keep scope minimal | Prefer manifest/key-scoped deploys for safer rollouts |
| Retry intentionally | Use `packRetry` while error count is decreasing |
| Preserve key strategy | Keep matching keys and GlobalKeys consistent across orgs |
| Compare post-deploy | Run `packGetDiffs` to verify target parity |

## Cross-Skill Integration

| Related Skill | When to Use |
|---------------|-------------|
| deploying-metadata | Deploy non-DataPack Salesforce metadata with `sf project deploy` |
| building-omnistudio-omniscript | Author OmniScripts before deployment |
| building-omnistudio-flexcard | Build FlexCards before deployment |
| building-omnistudio-integration-procedure | Build Integration Procedures before deployment |
| debugging-apex-logs | Investigate runtime/triggers/log failures surfaced during deploy |

## Documentation

- [SKILL.md](SKILL.md) - Full DataPack deployment workflow and operating rules
- [references/job-file-template.md](references/job-file-template.md) - Baseline job file patterns
- [references/troubleshooting-matrix.md](references/troubleshooting-matrix.md) - Common failures and fix directions
- [examples/business-internet-plus-bundle/TRANSCRIPT.md](examples/business-internet-plus-bundle/TRANSCRIPT.md) - Validation planning/execution transcript and outcomes
- [examples/business-internet-plus-bundle-deploy/TRANSCRIPT.md](examples/business-internet-plus-bundle-deploy/TRANSCRIPT.md) - Deployment execution transcript with packDeploy/packRetry results

## Requirements

- Node.js 18+
- Vlocity Build CLI (`npm install --global vlocity`)
- Salesforce CLI v2 (for org auth and context)
- Source and target org access

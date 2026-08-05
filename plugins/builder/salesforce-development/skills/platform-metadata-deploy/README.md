# platform-metadata-deploy

Comprehensive Salesforce DevOps automation using sf CLI v2. Validate, deploy, verify, and hand off cleanly to post-deploy activities.

## Features

- **Deployment Management**: Execute, validate, and monitor deployments
- **DevOps Automation**: CI/CD pipelines, automated testing workflows
- **Org Management**: Authentication, scratch orgs, environment management
- **Quality Assurance**: Dry-run validation, tests, code coverage, pre-production verification
- **Post-Deploy Handoff**: Guide users to the next safe step after validation or deployment
- **Troubleshooting**: Debug failures, analyze logs, provide solutions


## Quick Start

### 1. Invoke the skill

```text
Skill: platform-metadata-deploy
Request: "Deploy all changes to org dev with validation"
```

### 2. Common operations

| Operation | Example Request |
|-----------|-----------------|
| Deploy | "Deploy force-app to org dev" |
| Validate | "Dry-run deploy to check for errors" |
| Quick deploy | "Quick deploy validated changes" |
| Cancel | "Cancel the current deployment" |
| Status | "Check deployment status" |

## Key Commands

```bash
# Validate before deploy (ALWAYS DO THIS)
sf project deploy start --dry-run --source-dir force-app --target-org [alias]

# Deploy with tests
sf project deploy start --source-dir force-app --test-level RunLocalTests --target-org [alias]

# Quick deploy (after validation)
sf project deploy quick --job-id [id] --target-org [alias]

# Check status
sf project deploy report --job-id [id] --target-org [alias]

# Cancel deployment
sf project deploy cancel --job-id [id] --target-org [alias]
```

## Recommended post-validation flow

After a successful dry run, guide the user to the next safe step:
1. deploy now
2. assign permission sets
3. create test data with `platform-data-manage`
4. run tests or smoke checks
5. combine multiple post-deploy steps in order

## Orchestration Order

```text
platform-custom-object-generate/automation-flow-generate → platform-metadata-deploy → platform-data-manage
```

**Within platform-metadata-deploy**:
1. Objects/Fields
2. Permission Sets
3. Apex
4. Flows (as Draft)
5. Activate Flows

## Best Practices

| Rule | Details |
|------|---------|
| Always `--dry-run` first | Validate before actual deployment |
| Deploy order matters | Objects → Permissions → Code |
| Test levels | Use `RunLocalTests` for production |
| Flow activation | Deploy as Draft, activate manually |
| Post-deploy data | Hand off to `platform-data-manage` rather than mixing raw data creation into deploy logic |

## Cross-Skill Integration

| Related Skill | When to Use |
|---------------|-------------|
| platform-custom-object-generate / platform-custom-field-generate | Create objects/fields BEFORE deploy |
| platform-apex-test-run | Run tests AFTER deployment |
| platform-data-manage | Create describe-validated test data AFTER deployment |

## Documentation

- [SKILL.md](SKILL.md) - Full workflow and orchestration guidance
- [references/orchestration.md](references/orchestration.md) - Deployment sequencing
- [references/deployment-workflows.md](references/deployment-workflows.md) - CI/CD and workflow examples
- [references/deploy.sh](references/deploy.sh) - Sample deployment script

## Requirements

- sf CLI v2
- Target Salesforce org
- Proper permissions for deployment

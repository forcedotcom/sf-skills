# deploying-metadata

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

```
Skill: deploying-metadata
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
3. create test data with `handling-sf-data`
4. run tests or smoke checks
5. combine multiple post-deploy steps in order

## Orchestration Order

```
generating-custom-object/generating-flow → deploying-metadata → handling-sf-data
```

**Within deploying-metadata**:
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
| Post-deploy data | Hand off to `handling-sf-data` rather than mixing raw data creation into deploy logic |

## Cross-Skill Integration

| Related Skill | When to Use |
|---------------|-------------|
| generating-custom-object / generating-custom-field | Create objects/fields BEFORE deploy |
| running-apex-tests | Run tests AFTER deployment |
| handling-sf-data | Create describe-validated test data AFTER deployment |

## Documentation

- [SKILL.md](SKILL.md) - Full workflow and orchestration guidance
- [references/orchestration.md](references/orchestration.md) - Deployment sequencing
- [references/deployment-workflows.md](references/deployment-workflows.md) - CI/CD and workflow examples
- [references/deploy.sh](references/deploy.sh) - Sample deployment script

## Requirements

- sf CLI v2
- Target Salesforce org
- Proper permissions for deployment

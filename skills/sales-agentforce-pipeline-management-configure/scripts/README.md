# Scripts for Pipeline Management Configuration

This directory contains automation scripts for enabling Agentforce Pipeline Management. All scripts require an `sfdx-project.json` in your working directory.

## Prerequisites

- Salesforce CLI (`sf`) installed
- Authenticated org with alias
- `sfdx-project.json` in working directory (see `../assets/sfdx-project.json`)

## Usage Table

| Script | Purpose | Usage | Dependencies |
|--------|---------|-------|--------------|
| `setup-all.sh` | **Master orchestration** — end-to-end setup, enables all prerequisites + PM inline | `./setup-all.sh <org-alias> --fields "NextStep,Risk__c"` | None (auth only) |
| `retrieve-settings.sh` | Retrieve all settings for inspection | `./retrieve-settings.sh <org-alias>` | None |
| `enable-prerequisites.sh` | Enable prerequisite settings only (no fields/flow/agent) | `./enable-prerequisites.sh <org-alias>` | None |
| `enable-deal-agent.sh` | Enable SalesDealAgent settings (standalone helper) | `./enable-deal-agent.sh <org-alias>` | Prerequisites must already be enabled |
| `create-flow.sh` | Detect/verify/activate suggestion flow | `./create-flow.sh <org-alias>` | Deal agent enabled + manual UI clone |
| `create-agent.sh` | Verify/create/activate agent | `./create-agent.sh <org-alias>` | Deal agent enabled |
| `deploy-settings.sh` | Deploy settings from local files | `./deploy-settings.sh <org-alias>` | Local metadata files |
| `verify-all.sh` | Comprehensive status check | `./verify-all.sh <org-alias>` | None (read-only) |

## Execution Order

For end-to-end setup, drive **`setup-all.sh`** — it enables all prerequisites (Einstein GenAI, Agentforce, Enhanced Notes, Opportunity Team), enables Pipeline Management, deploys prompt templates, builds/activates the flow, provisions the agent + PSGs, and verifies, in dependency order. The individual scripts below are for isolated inspection or repair of a single component:

1. **retrieve-settings.sh** — Inspect current state
2. **enable-prerequisites.sh** — Enable prerequisite settings only (Einstein, Notes, Opportunity Team)
3. **enable-deal-agent.sh** — Enable Pipeline Management in isolation (prerequisites must already be on)
4. **create-flow.sh** — Detect/verify/activate flow (requires manual Setup UI clone first)
5. **create-agent.sh** — Verify agent user and PSGs (auto-provisioned on enablement)
6. **verify-all.sh** — Comprehensive status check (read-only)

## Important Notes

- All scripts are idempotent (safe to re-run)
- Scripts use SOAP API v62.0-64.0 for settings that fail silently via CLI
- Individual setting deployment isolates failures
- Each script validates before making changes
- All `sf` commands use `--json` with error suppression for clean parsing

## sfdx-project.json Requirement

All scripts expect an `sfdx-project.json` in your working directory. Copy from `../assets/sfdx-project.json`:

```bash
cp ../assets/sfdx-project.json ./sfdx-project.json
```

## Error Handling

- Scripts exit with non-zero code on critical failures
- Warnings are logged but don't stop execution
- SOAP API errors are captured and reported
- Missing metadata is handled gracefully

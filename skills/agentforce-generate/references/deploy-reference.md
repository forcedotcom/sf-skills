# Deploy -- Bundle Publication Reference

> Extracted from SKILL.md Section 18. This file is loaded on demand when deployment details are needed.

## Overview

Release lifecycle for Agentforce agents: draft iteration (validate/deploy/preview), then explicit publish + activate when user approves release.

## Usage

```bash
# Draft iteration loop
sf agent validate authoring-bundle --json --api-name MyAgent -o <org-alias>
sf project deploy start --json --source-dir force-app -o <org-alias>
sf agent preview start --json --use-live-actions --authoring-bundle MyAgent -o <org-alias>

# Release-only steps (after explicit user approval)
sf agent publish authoring-bundle --json --api-name MyAgent -o <org-alias>
sf agent activate --json --api-name MyAgent -o <org-alias>
```

## Deployment Phases

### Phase 0: Safety Gate (Required)
Read the `.agent` file and run safety review (see `safety-review-reference.md`). If any BLOCK finding exists, STOP deployment. WARN findings must be reported and acknowledged by the user before proceeding.

### Phase 1: Draft Validation
```bash
sf agent validate authoring-bundle --json --api-name MyAgent -o <org-alias>
```

### Phase 1b: Target Dependency Check
Verify all flow/apex targets exist in the org before publishing. If missing, scaffold and deploy them first.

### Phase 2: Draft Deploy of Supporting Metadata
```bash
sf project deploy start --json --source-dir force-app -o <org-alias>
```

### Phase 3: Explicit Release Gate

Confirm user approval before publish/activate. Do not auto-publish during authoring.

#### Release Gate (shared checklist)

The Create, Modify, and Deploy task domains all gate Publish on this same checklist. Stay in draft iteration unless the user explicitly asks to release. **If the user requests release, do NOT proceed to Publish unless ALL are true:**

- `validate authoring-bundle` passes with zero errors
- Live preview (`--use-live-actions`) tested with realistic utterances covering all routing branches
- Traces confirm correct subagent routing, action invocation (`FunctionStep` present), and spec-compliant behavior
- User explicitly approves deployment
- **If the agent has a `knowledge:` block**: the Einstein Agent User has a Data Cloud permset/PSL assigned. Verify both:
  ```bash
  sf data query --json -q "SELECT PermissionSet.Name FROM PermissionSetAssignment WHERE Assignee.Username='<agent_user>'"
  sf data query --json -q "SELECT PermissionSetLicense.DeveloperName FROM PermissionSetLicenseAssign WHERE Assignee.Username='<agent_user>'"
  ```
  One of `GenieDataPlatformStarterPsl`, `GenieUserEnhancedSecurity`, `DataCloudUser`, or `DataCloudArchitect` must appear in the combined results. If none does, run [Agent User Setup, Step 3b](agent-user-setup.md) discovery-then-assign and re-verify before proceeding. If a Data Cloud permset is assigned but a smoke-test grounded query returns empty `knowledgeSummary`, the **Data Space scope** also needs to be granted on that permset — UI-only, see [Agent User Setup, Step 3b.4](agent-user-setup.md).

### Phase 4: Publish Agent Bundle
```bash
sf agent publish authoring-bundle --json --api-name MyAgent -o <org-alias>
```
4-step process: Validate (~1-2s) -> Publish (~8-10s) -> Retrieve (~5-7s) -> Deploy (~4-6s)

### Phase 5: Activate Agent
```bash
sf agent activate --json --api-name MyAgent -o <org-alias>
```
Note: `sf agent activate` may not support `--json` in all CLI versions. If it returns plain text, check for "successfully activated" in the output.

Publishing creates an **inactive** version. Without activation, preview fails with "No valid version available".

## Draft Deploy vs Publish

| What changes | `sf project deploy start` | `sf agent publish authoring-bundle` |
|---|---|---|
| Bundle metadata | Yes | Yes |
| `system: instructions:` | Yes (via activate) | Yes |
| `reasoning: actions:` (transitions + invocations) | **NO** | Yes |

Use draft deploy + preview for iterative development. Publish is the explicit release step when the user chooses to commit a version for end users.

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `Required fields missing: [BundleType]` | Extra fields in bundle-meta.xml | Use minimal: only `<bundleType>AGENT</bundleType>` |
| `Internal Error, try again later` | Invalid default_agent_user or new agent platform bug | Query Einstein Agent Users; for new agents, create shell in Setup UI first |
| `Duplicate value found: GenAiPluginDefinition` | `start_agent` and `subagent` share name | Use different names |
| `Flow not found` | Metadata not deployed | Deploy flows before publishing |
| `SetupEntityType is not supported for DML` | PermissionSet via Apex DML | Use Metadata API (`sf project deploy start`) |

## Rollback

```bash
sf agent deactivate --json --api-name MyAgent -o <org>
sf data query --json --query "SELECT Id, VersionNumber FROM BotVersion WHERE BotDefinition.DeveloperName = 'MyAgent' ORDER BY VersionNumber DESC LIMIT 2" -o <org>
sf agent activate --json --api-name MyAgent --version-number <previous> -o <org>
```

## CI/CD Integration

```yaml
name: Deploy Agentforce Agent
on:
  push:
    branches: [main]
    paths: ['force-app/**']

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install SF CLI
        run: npm install -g @salesforce/cli
      - name: Auth
        run: |
          echo "${{ secrets.SFDX_AUTH_URL }}" > auth.txt
          sf org login sfdx-url --sfdx-url-file auth.txt --alias production
      - name: Validate
        run: sf agent validate authoring-bundle --json --api-name ${{ vars.AGENT_NAME }} -o production
      - name: Deploy Metadata
        run: sf project deploy start --json --source-dir force-app -o production
      - name: Publish
        run: sf agent publish authoring-bundle --json --api-name ${{ vars.AGENT_NAME }} -o production
      - name: Activate
        if: github.ref == 'refs/heads/main'
        run: sf agent activate --json --api-name ${{ vars.AGENT_NAME }} -o production
```

## Pre-Deployment Checklist

- [ ] All action targets exist in org (run discover first)
- [ ] Agent Script validated (no syntax errors)
- [ ] Einstein Agent User configured correctly
- [ ] Supporting metadata deployed
- [ ] Previous version backed up
- [ ] Rollback plan documented

## Post-Deployment Testing

```bash
sf agent preview start --json --use-live-actions --authoring-bundle MyAgent -o <org>
# Read sessionId from the JSON response, then:
sf agent preview send --json --authoring-bundle MyAgent --session-id <SESSION_ID> -u "Hello, I need help" -o <org>
sf agent preview end --json --authoring-bundle MyAgent --session-id <SESSION_ID> -o <org>
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Validation/deployment failed |
| 2 | Critical failure |

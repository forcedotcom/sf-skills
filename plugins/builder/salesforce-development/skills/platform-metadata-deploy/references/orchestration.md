<!-- Parent: platform-metadata-deploy/SKILL.md -->
# Multi-Skill Orchestration: platform-metadata-deploy Perspective

This document details how platform-metadata-deploy fits into the multi-skill workflow for Salesforce development.

---

## Standard Orchestration Order

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│  STANDARD MULTI-SKILL ORCHESTRATION ORDER                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│  1. platform-custom-object-generate / platform-custom-field-generate                      │
│     └── Create object/field definitions (LOCAL files)                       │
│                                                                             │
│  2. automation-flow-generate                                                         │
│     └── Create flow definitions (LOCAL files)                               │
│                                                                             │
│  3. platform-metadata-deploy  ◀── YOU ARE HERE                                            │
│     └── Deploy all metadata (REMOTE)                                        │
│                                                                             │
│  4. platform-data-manage                                                                 │
│     └── Create test data (REMOTE - objects must exist!)                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Why platform-metadata-deploy Goes Third (Not Last)

platform-metadata-deploy is the **bridge** between local files and the org:

| Before platform-metadata-deploy | After platform-metadata-deploy |
|------------------|-----------------|
| Metadata exists locally | Metadata exists in org |
| Flows reference objects | Flows can run |
| Data can't be created | platform-data-manage can create records |

**platform-data-manage REQUIRES deployed objects**. The error `SObject type 'X' not supported` means objects weren't deployed.

---

## Deploy Order WITHIN platform-metadata-deploy

When deploying multiple metadata types:

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│  INTERNAL DEPLOY ORDER                                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│  1. Custom Objects & Fields                                                 │
│     └── Objects must exist before anything references them                  │
│                                                                             │
│  2. Permission Sets                                                         │
│     └── Field-Level Security requires fields to exist                       │
│                                                                             │
│  3. Apex Classes                                                            │
│     └── @InvocableMethod for Flow actions                                   │
│                                                                             │
│  4. Flows (as Draft)                                                        │
│     └── Flows reference fields and Apex                                     │
│                                                                             │
│  5. Activate Flows                                                          │
│     └── Change status Draft → Active                                        │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Why this order?**
- Flows need fields to exist
- Users need Permission Sets for field visibility
- Triggers may depend on active flows
- Draft flows can be tested before activation

---

## Integration + Agentforce Extended Order

When deploying agents with external API integrations:

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│  AGENTFORCE DEPLOYMENT ORDER                                                │
├─────────────────────────────────────────────────────────────────────────────┤
│  1. integration-connectivity-connected-app-configure → Create OAuth Connected App                 │
│  2. integration-connectivity-generate    → Create Named Credential + External Service          │
│  3. platform-apex-generate   → Create @InvocableMethod (if needed)                 │
│  4. automation-flow-generate   → Create Flow wrapper                                 │
│                                                                             │
│  5. platform-metadata-deploy         ◀── FIRST DEPLOYMENT                                 │
│     └── Deploy: Objects, Fields, Permission Sets, Apex, Flows              │
│                                                                             │
│  6. agentforce-generate → Create agent with flow:// target               │
│                                                                             │
│  7. platform-metadata-deploy         ◀── SECOND DEPLOYMENT (Agent Publish)                │
│     └── sf agent publish authoring-bundle --api-name [AgentName]           │
│                                                                             │
│  8. platform-data-manage           → Create test data                                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Common Deployment Errors from Wrong Order

| Error | Cause | Fix |
|-------|-------|-----|
| `Invalid reference: Quote__c` | Object not deployed | Deploy objects first |
| `Field does not exist: Status__c` | Field not deployed | Deploy fields first |
| `no CustomObject named X found` | Permission Set deployed before object | Deploy objects, then Permission Sets |
| `SObject type 'X' not supported` | platform-data-manage ran before deploy | Deploy before creating data |
| `Flow is invalid` | Flow references missing object | Deploy objects before flows |
| `Flow not found` | Agent references undeploy flow | Deploy flows before agent publish |

---

## Two-Step Deployment Pattern (Recommended)

Always validate before deploying:

```bash
# Step 1: Dry-run validation
sf project deploy start --dry-run --source-dir force-app --target-org alias

# Step 2: Actual deployment (only if validation passes)
sf project deploy start --source-dir force-app --target-org alias
```

---

## Cross-Skill Dependencies

Before deploying, verify these prerequisites:

| Dependency | Check Command | Required For |
|------------|---------------|--------------|
| TAF Package | `sf package installed list` | TAF trigger pattern |
| Custom Objects | `sf sobject describe` | Apex/Flow field refs |
| Permission Sets | `sf org list metadata --metadata-type PermissionSet` | FLS for fields |
| Flows | `sf org list metadata --metadata-type Flow` | Agent actions |

---

## agentforce-generate Integration

For agent deployments, use the specialized commands:

```bash
# Deploy dependencies first
sf project deploy start --metadata ApexClass,Flow --target-org alias

# Validate agent syntax
sf agent validate authoring-bundle --api-name AgentName --target-org alias --json

# Publish agent
sf agent publish authoring-bundle --api-name AgentName --target-org alias --json

# Activate a specific BotVersion deterministically in automation
sf agent activate --api-name AgentName --version N --target-org alias --json
```

> If you omit `--version`, activation is interactive. For CI/CD and scripted orchestration, prefer `--version N --json`.

---

## Invocation Patterns

| From Skill | To platform-metadata-deploy | When |
|------------|--------------|------|
| platform-custom-object-generate | → platform-metadata-deploy | "Deploy objects to [org]" |
| automation-flow-generate | → platform-metadata-deploy | "Deploy flow with --dry-run" |
| platform-apex-generate | → platform-metadata-deploy | "Deploy classes with RunLocalTests" |
| agentforce-generate | → platform-metadata-deploy | "Deploy and publish agent" |

---

## Related Documentation

| Topic | Location |
|-------|----------|
| Deployment workflows | `platform-metadata-deploy/references/deployment-workflows.md` |
| Agent deployment guide | `platform-metadata-deploy/references/agent-deployment-guide.md` |
| Deploy script template | `platform-metadata-deploy/references/deploy.sh` |

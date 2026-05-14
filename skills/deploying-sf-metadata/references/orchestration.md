<!-- Parent: deploying-sf-metadata/SKILL.md -->
# Multi-Skill Orchestration: deploying-sf-metadata Perspective

This document details how deploying-sf-metadata fits into the multi-skill workflow for Salesforce development.

---

## Standard Orchestration Order

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  STANDARD MULTI-SKILL ORCHESTRATION ORDER                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│  1. generating-custom-object / generating-custom-field                      │
│     └── Create object/field definitions (LOCAL files)                       │
│                                                                             │
│  2. generating-flow                                                         │
│     └── Create flow definitions (LOCAL files)                               │
│                                                                             │
│  3. deploying-sf-metadata  ◀── YOU ARE HERE                                            │
│     └── Deploy all metadata (REMOTE)                                        │
│                                                                             │
│  4. handling-sf-data                                                                 │
│     └── Create test data (REMOTE - objects must exist!)                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Why deploying-sf-metadata Goes Third (Not Last)

deploying-sf-metadata is the **bridge** between local files and the org:

| Before deploying-sf-metadata | After deploying-sf-metadata |
|------------------|-----------------|
| Metadata exists locally | Metadata exists in org |
| Flows reference objects | Flows can run |
| Data can't be created | handling-sf-data can create records |

**handling-sf-data REQUIRES deployed objects**. The error `SObject type 'X' not supported` means objects weren't deployed.

---

## Deploy Order WITHIN deploying-sf-metadata

When deploying multiple metadata types:

```
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

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  AGENTFORCE DEPLOYMENT ORDER                                                │
├─────────────────────────────────────────────────────────────────────────────┤
│  1. configuring-connected-apps → Create OAuth Connected App                 │
│  2. building-sf-integrations    → Create Named Credential + External Service          │
│  3. generating-apex   → Create @InvocableMethod (if needed)                 │
│  4. generating-flow   → Create Flow wrapper                                 │
│                                                                             │
│  5. deploying-sf-metadata         ◀── FIRST DEPLOYMENT                                 │
│     └── Deploy: Objects, Fields, Permission Sets, Apex, Flows              │
│                                                                             │
│  6. developing-agentforce → Create agent with flow:// target               │
│                                                                             │
│  7. deploying-sf-metadata         ◀── SECOND DEPLOYMENT (Agent Publish)                │
│     └── sf agent publish authoring-bundle --api-name [AgentName]           │
│                                                                             │
│  8. handling-sf-data           → Create test data                                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Common Deployment Errors from Wrong Order

| Error | Cause | Fix |
|-------|-------|-----|
| `Invalid reference: Quote__c` | Object not deployed | Deploy objects first |
| `Field does not exist: Status__c` | Field not deployed | Deploy fields first |
| `no CustomObject named X found` | Permission Set deployed before object | Deploy objects, then Permission Sets |
| `SObject type 'X' not supported` | handling-sf-data ran before deploy | Deploy before creating data |
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

## developing-agentforce Integration

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

| From Skill | To deploying-sf-metadata | When |
|------------|--------------|------|
| generating-custom-object | → deploying-sf-metadata | "Deploy objects to [org]" |
| generating-flow | → deploying-sf-metadata | "Deploy flow with --dry-run" |
| generating-apex | → deploying-sf-metadata | "Deploy classes with RunLocalTests" |
| developing-agentforce | → deploying-sf-metadata | "Deploy and publish agent" |

---

## Related Documentation

| Topic | Location |
|-------|----------|
| Deployment workflows | `deploying-sf-metadata/references/deployment-workflows.md` |
| Agent deployment guide | `deploying-sf-metadata/references/agent-deployment-guide.md` |
| Deploy script template | `deploying-sf-metadata/references/deploy.sh` |

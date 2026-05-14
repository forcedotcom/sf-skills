<!-- Parent: deploying-sf-metadata/SKILL.md -->
# Agentforce Agent Deployment Guide

> Complete DevOps guide for deploying Agentforce agents using SF CLI

## Overview

This guide covers the complete deployment lifecycle for Agentforce agents, including:
- Agent metadata types and pseudo metadata
- Sync operations (retrieve/deploy)
- Lifecycle management (activate/deactivate)
- Full deployment workflows

**Related Skills:**
- `developing-agentforce` - Agent authoring, publishing, Agent Builder, and Prompt Builder
- `deploying-sf-metadata` - This skill - deployment orchestration

---

## Agent Metadata Types

Agentforce agents consist of multiple metadata components:

| Metadata Type | Description | Example API Name |
|---------------|-------------|------------------|
| `Bot` | Top-level chatbot definition | `Customer_Support_Agent` |
| `BotVersion` | Version configuration | `Customer_Support_Agent.v1` |
| `GenAiPlannerBundle` | Reasoning engine (LLM config) | `Customer_Support_Agent_Planner` |
| `GenAiPlugin` | Topic definition | `Order_Management_Plugin` |
| `GenAiFunction` | Action definition | `Get_Order_Status_Function` |

### Metadata Hierarchy

```
Bot (Agent Definition)
└── BotVersion (Version Config)
    └── GenAiPlannerBundle (Reasoning Engine)
        ├── GenAiPlugin (Topic 1)
        │   ├── GenAiFunction (Action 1)
        │   └── GenAiFunction (Action 2)
        └── GenAiPlugin (Topic 2)
            └── GenAiFunction (Action 3)
```

---

## Agent Pseudo Metadata Type

The `Agent` pseudo metadata type is a convenience wrapper that retrieves or deploys all agent-related components at once.

### Using the Agent Pseudo Type

```bash
# Retrieve agent + all dependencies from org
sf project retrieve start --metadata Agent:[AgentName] --target-org [alias]

# Deploy agent metadata to org
sf project deploy start --metadata Agent:[AgentName] --target-org [alias]
```

### What Gets Synced

When using `--metadata Agent:[Name]`:

**Retrieved/Deployed:**
- `Bot` - Top-level chatbot
- `BotVersion` - Version configuration
- `GenAiPlannerBundle` - Reasoning engine
- `GenAiPlugin` - All topics
- `GenAiFunction` - All actions

**NOT Included:**
- Apex classes (deploy separately)
- Flows (deploy separately)
- Named Credentials (deploy separately)

---

## Sync Operations

### Retrieving Agents from Org

```bash
# Retrieve agent using pseudo metadata type
sf project retrieve start --metadata Agent:Customer_Support_Agent --target-org myorg

# Retrieve to specific output directory
sf project retrieve start --metadata Agent:Customer_Support_Agent --output-dir ./retrieved --target-org myorg

# Retrieve multiple agents
sf project retrieve start --metadata Agent:Support_Agent,Agent:Sales_Agent --target-org myorg
```

### Retrieving Specific Components

```bash
# Retrieve just the bot definition
sf project retrieve start --metadata Bot:Customer_Support_Agent --target-org myorg

# Retrieve a specific BotVersion along with the bot definition
sf project retrieve start \
  --metadata Bot:Customer_Support_Agent \
  --metadata BotVersion:Customer_Support_Agent.v3 \
  --target-org myorg

# Retrieve just the planner bundle
sf project retrieve start --metadata GenAiPlannerBundle:Customer_Support_Agent_Planner --target-org myorg

# Retrieve all plugins (topics)
sf project retrieve start --metadata GenAiPlugin --target-org myorg

# Retrieve all functions (actions)
sf project retrieve start --metadata GenAiFunction --target-org myorg
```

> **Versioned retrieve note:** Current SF CLI releases correctly retrieve the specific `BotVersion` you request instead of always pulling only the latest version.

### Deploying Agents to Org

```bash
# Deploy agent using pseudo metadata type
sf project deploy start --metadata Agent:Customer_Support_Agent --target-org myorg

# Deploy with validation only (dry run)
sf project deploy start --metadata Agent:Customer_Support_Agent --dry-run --target-org myorg

# Deploy multiple agents
sf project deploy start --metadata Agent:Support_Agent,Agent:Sales_Agent --target-org myorg
```

---

## Agent Lifecycle Management

### Activate Agent

Makes an agent available to users.

```bash
# Manual activation
sf agent activate --api-name [AgentName] --target-org [alias]

# CI / deterministic activation of a known BotVersion
sf agent activate --api-name [AgentName] --version [N] --target-org [alias] --json
```

**Requirements:**
- Agent must be published first (`sf agent publish authoring-bundle`)
- All Apex classes and Flows must be deployed
- `default_agent_user` must be a valid org user with Agentforce permissions

**Activation notes:**
- `--version [N]` maps to the `vN` suffix in `BotVersion` metadata
- Omitting `--version` triggers interactive version selection
- Using `--json` without `--version` activates the latest agent version
- For CI/CD and reproducible rollouts, prefer `--version [N] --json`

**Post-Activation:**
- Agent is immediately available to users
- Preview command can be used for testing
- Changes require deactivation first

### Deactivate Agent

Deactivates an agent for modifications. **Required before making changes.**

```bash
# Manual deactivation
sf agent deactivate --api-name [AgentName] --target-org [alias]

# Script-friendly deactivation
sf agent deactivate --api-name [AgentName] --target-org [alias] --json
```

**When Deactivation is Required:**
- Adding or removing topics
- Modifying action configurations
- Changing system instructions
- Updating variable definitions

### Modification Workflow

```bash
# 1. Deactivate agent
sf agent deactivate --api-name Customer_Support_Agent --target-org myorg

# 2. Make changes to Agent Script

# 3. Re-publish
sf agent publish authoring-bundle --api-name Customer_Support_Agent --target-org myorg

# 4. Re-activate
sf agent activate --api-name Customer_Support_Agent --target-org myorg
```

---

## Agent Preview

Preview allows testing agent behavior before production deployment.

### Preview Modes

| Mode | Command | Use When |
|------|---------|----------|
| **Simulated** | `sf agent preview --api-name X` | Testing logic, Apex/Flows not ready |
| **Live** | `sf agent preview --api-name X --use-live-actions` | Integration testing with real data |

### Simulated Mode (Default)

```bash
sf agent preview --api-name Customer_Support_Agent --target-org myorg
```

- LLM simulates action responses
- No actual Apex/Flow execution
- Safe for testing - no data changes

### Live Mode

```bash
sf agent preview --api-name Customer_Support_Agent --use-live-actions --target-org myorg
```

**Requirements:**
- Standard org auth (`sf org login web`)
- Apex classes and Flows deployed
- Agent must be active

### Preview with Debug Output

```bash
sf agent preview --api-name Customer_Support_Agent --output-dir ./preview-logs --apex-debug --target-org myorg
```

> **v2.121.7+**: Live preview no longer requires a Connected App. Standard org auth (`sf org login web`) suffices.

---

## Full Deployment Workflows

### New Agent Deployment

Complete workflow for deploying a new agent:

```bash
# 1. Deploy Apex classes (if any)
sf project deploy start --metadata ApexClass --target-org myorg

# 2. Deploy Flows
sf project deploy start --metadata Flow --target-org myorg

# 3. Validate Agent Script
sf agent validate authoring-bundle --api-name Customer_Support_Agent --target-org myorg

# 4. Publish agent
sf agent publish authoring-bundle --api-name Customer_Support_Agent --target-org myorg

# 5. Preview (simulated mode)
sf agent preview --api-name Customer_Support_Agent --target-org myorg

# 6. Activate
sf agent activate --api-name Customer_Support_Agent --target-org myorg

# 7. Preview (live mode - optional)
sf agent preview --api-name Customer_Support_Agent --use-live-actions --target-org myorg
```

### Update Existing Agent

```bash
# 1. Deactivate
sf agent deactivate --api-name Customer_Support_Agent --target-org myorg

# 2. Deploy updated dependencies (if any)
sf project deploy start --metadata ApexClass,Flow --target-org myorg

# 3. Validate
sf agent validate authoring-bundle --api-name Customer_Support_Agent --target-org myorg

# 4. Re-publish
sf agent publish authoring-bundle --api-name Customer_Support_Agent --target-org myorg

# 5. Preview
sf agent preview --api-name Customer_Support_Agent --target-org myorg

# 6. Re-activate
sf agent activate --api-name Customer_Support_Agent --target-org myorg
```

### Sync Between Orgs

```bash
# 1. Retrieve from source org
sf project retrieve start --metadata Agent:Customer_Support_Agent --target-org source-org

# 2. Deploy dependencies to target org first
sf project deploy start --source-dir force-app/main/default/classes --target-org target-org
sf project deploy start --source-dir force-app/main/default/flows --target-org target-org

# 3. Deploy agent metadata
sf project deploy start --metadata Agent:Customer_Support_Agent --target-org target-org

# 4. Publish agent in target org
sf agent publish authoring-bundle --api-name Customer_Support_Agent --target-org target-org

# 5. Activate in target org
sf agent activate --api-name Customer_Support_Agent --target-org target-org
```

### CI/CD Pipeline Integration

Example deployment script for CI/CD:

```bash
#!/bin/bash
# deploy-agent.sh

set -e  # Exit on error

ORG_ALIAS=$1
AGENT_NAME=$2
AGENT_VERSION=$3

echo "🚀 Deploying agent: $AGENT_NAME to $ORG_ALIAS (version: $AGENT_VERSION)"

# Step 1: Deploy dependencies
echo "📦 Deploying Apex classes..."
sf project deploy start --metadata ApexClass --target-org $ORG_ALIAS --wait 10 --json

echo "📦 Deploying Flows..."
sf project deploy start --metadata Flow --target-org $ORG_ALIAS --wait 10 --json

# Step 2: Validate agent script
echo "✅ Validating Agent Script..."
sf agent validate authoring-bundle --api-name $AGENT_NAME --target-org $ORG_ALIAS --json

# Step 3: Check if agent exists (deactivate if needed)
echo "🔍 Checking agent status..."
if sf agent deactivate --api-name $AGENT_NAME --target-org $ORG_ALIAS --json 2>/dev/null; then
    echo "⏸️ Agent deactivated for update"
fi

# Step 4: Publish agent (--skip-retrieve skips metadata retrieval, faster in CI)
echo "📤 Publishing agent..."
sf agent publish authoring-bundle --api-name $AGENT_NAME --target-org $ORG_ALIAS --skip-retrieve --json

# Step 5: Activate agent deterministically
echo "▶️ Activating agent..."
sf agent activate --api-name $AGENT_NAME --version $AGENT_VERSION --target-org $ORG_ALIAS --json

echo "✅ Agent deployment complete: $AGENT_NAME"
```

Usage:
```bash
./deploy-agent.sh myorg Customer_Support_Agent 4
```

Pass the BotVersion number you intend to activate as the third argument.

---

## Dependency Deployment Order

**Critical:** Dependencies must be deployed BEFORE the agent.

```
1. Custom Objects/Fields (generating-custom-object, generating-custom-field)
   ↓
2. Apex Classes (generating-apex)
   ↓
3. Flows (generating-flow)
   ↓
4. Named Credentials (building-sf-integrations, if external APIs)
   ↓
5. Agent Metadata (developing-agentforce publish)
   ↓
6. Agent Activation
```

### Deployment Commands by Order

```bash
# 1. Objects/Fields
sf project deploy start --metadata CustomObject,CustomField --target-org myorg

# 2. Apex
sf project deploy start --metadata ApexClass --target-org myorg

# 3. Flows
sf project deploy start --metadata Flow --target-org myorg

# 4. Named Credentials (if needed)
sf project deploy start --metadata NamedCredential --target-org myorg

# 5. Publish agent
sf agent publish authoring-bundle --api-name My_Agent --target-org myorg

# 6. Activate
sf agent activate --api-name My_Agent --target-org myorg
```

---

## Post-Deployment Validation for API Access

After deploying and activating an agent, verify it is accessible via the Agent Runtime API. Missing metadata causes silent 500 errors.

### Validation Checklist

```bash
# 1. Verify GenAiPlannerBundle has plannerSurfaces
sf project retrieve start --metadata GenAiPlannerBundle --target-org myorg --output-dir ./check
grep -l "plannerSurfaces" ./check/**/*.xml
# If no results → add plannerSurfaces block (see below)

# 2. Verify BotVersion has surfacesEnabled=true
sf project retrieve start --metadata BotVersion --target-org myorg --output-dir ./check
grep "surfacesEnabled" ./check/**/*.xml
# Should show: <surfacesEnabled>true</surfacesEnabled>

# 3. Test API connectivity
curl -s -X POST "https://DOMAIN.my.salesforce.com/services/oauth2/token" \
  -d "grant_type=client_credentials&client_id=KEY&client_secret=SECRET" | jq .access_token
```

### Fix: Add Missing plannerSurfaces

If the GenAiPlannerBundle XML is missing the `plannerSurfaces` block, add `CustomerWebClient`:

```xml
<GenAiPlannerBundle xmlns="http://soap.sforce.com/2006/04/metadata">
    <!-- existing elements -->
    <plannerSurfaces>
        <adaptiveResponseAllowed>false</adaptiveResponseAllowed>
        <callRecordingAllowed>false</callRecordingAllowed>
        <surface>SurfaceAction__CustomerWebClient</surface>
        <surfaceType>CustomerWebClient</surfaceType>
    </plannerSurfaces>
</GenAiPlannerBundle>
```

> **Note**: `EinsteinAgentApiChannel` surfaceType is NOT available on all orgs. Use `CustomerWebClient` instead — it enables both Agent Builder Preview and Agent Runtime API access.

> **⚠️ Agent Script agents**: `connection messaging:` in the `.agent` DSL ONLY generates a `Messaging` plannerSurface — `CustomerWebClient` is never auto-generated. You must manually patch it after EVERY `sf agent publish authoring-bundle`. See the post-publish workflow in `developing-agentforce`.

### Fix: Add plannerSurfaces when agent is active

If the agent is active, you must deactivate before deploying:

```bash
# Deactivate → Deploy → Activate
sf agent deactivate --api-name AgentName -o TARGET_ORG --json
sf project deploy start --metadata "GenAiPlannerBundle:AgentName_vNN" -o TARGET_ORG --json
sf agent activate --api-name AgentName --version NN -o TARGET_ORG --json
```

Use the same `NN` value from the planner bundle version you just patched so activation is deterministic.

### Fix: Enable surfacesEnabled on BotVersion

```xml
<BotVersion xmlns="http://soap.sforce.com/2006/04/metadata">
    <!-- existing elements -->
    <surfacesEnabled>true</surfacesEnabled>
</BotVersion>
```

Then redeploy:
```bash
sf project deploy start --metadata GenAiPlannerBundle,BotVersion --target-org myorg
```

> **Why this matters**: Without `CustomerWebClient` plannerSurface, the Agent Builder Preview shows "Something went wrong" and the Agent Runtime API returns `500 UNKNOWN_EXCEPTION` on session creation.

---

## ISV Packaging (BotTemplate)

Use `sf agent generate template` to package an agent for distribution via managed packages on AppExchange.

### Generate a BotTemplate

```bash
sf agent generate template \
    --agent-file force-app/main/default/bots/My_Agent/My_Agent.bot-meta.xml \
    --agent-version 1 \
    --output-dir my-package \
    --source-org my-scratch-org \
    --json
```

> **Important:** This command packages Bot / BotVersion-based agents. It does **not** package Agent Script `.agent` authoring bundles.

### What Gets Generated

The command generates a `BotTemplate` metadata type that wraps:
- `Bot` — Top-level agent definition
- `BotVersion` — Version configuration
- `GenAiPlannerBundle` — Reasoning engine and topic/action bindings

### Packaging Workflow

1. **Generate template**: Run `sf agent generate template` as shown above
2. **Include in package**: Add the `BotTemplate` and `GenAiPlannerBundle` metadata to your managed package directory
3. **Create package version**: `sf package version create --package <name> --installation-key <key> --wait 20`
4. **Install in subscriber org**: `sf package install --package <version-id> --target-org <alias> --wait 10`
5. **Publish agent in subscriber org**: `sf agent publish authoring-bundle --api-name <name> --target-org <alias>`

### Key Considerations

- The BotTemplate is designed for ISV distribution — it allows subscribers to install and customize the agent
- Subscribers can modify topics, actions, and instructions after installation
- The `--agent-version` flag specifies which BotVersion to template (typically `1` for new agents)
- The `--agent-file` must point to the `.bot-meta.xml` file in your local project
- `--source-org` must be a namespaced scratch org that contains the source agent
- Agent Script `.agent` bundles currently need a different rollout path; use source-driven publish workflows instead of `sf agent generate template`

---

## Troubleshooting

### "Internal Error, try again later"

**Causes:**
- Invalid `default_agent_user`
- Dependencies not deployed
- Flow/action variable name mismatch

**Solutions:**
```bash
# Verify user exists
sf data query --query "SELECT Id, Username FROM User WHERE Username = 'agent@example.com'" --target-org myorg

# Deploy dependencies first
sf project deploy start --metadata ApexClass,Flow --target-org myorg
```

### "No active agents found"

**Cause:** Agent not activated

**Solution:**
```bash
sf agent activate --api-name My_Agent --target-org myorg
```

### "Agent must be deactivated before changes"

**Cause:** Trying to modify active agent

**Solution:**
```bash
sf agent deactivate --api-name My_Agent --target-org myorg
# Make changes
sf agent publish authoring-bundle --api-name My_Agent --target-org myorg
sf agent activate --api-name My_Agent --target-org myorg
```

### Deployment Fails with Missing Dependencies

**Cause:** Apex/Flows not deployed before agent

**Solution:** Follow the dependency deployment order above.

---

## Cross-Skill Integration

| From Skill | To Skill | Purpose |
|------------|----------|---------|
| developing-agentforce | deploying-sf-metadata | Publish and activate agents |
| generating-apex | deploying-sf-metadata | Deploy Apex before agent |
| generating-flow | deploying-sf-metadata | Deploy Flows before agent |
| building-sf-integrations | deploying-sf-metadata | Deploy Named Credentials for external APIs |

### Integration Pattern

```bash
# 1. generating-apex creates InvocableMethod class
# 2. generating-flow creates wrapper Flow
# 3. developing-agentforce creates agent with flow:// action
# 4. deploying-sf-metadata orchestrates deployment in correct order
```

---

## Command Reference

### Agent-Specific Commands

| Command | Description |
|---------|-------------|
| `sf agent publish authoring-bundle --api-name X` | Publish authoring bundle |
| `sf agent publish authoring-bundle --api-name X --skip-retrieve` | Publish without retrieving from org (CI/CD) |
| `sf agent activate --api-name X --version N --json` | Activate a specific published BotVersion deterministically |
| `sf agent deactivate --api-name X --json` | Deactivate agent for changes |
| `sf agent preview --api-name X` | Preview agent behavior |
| `sf agent validate authoring-bundle --api-name X` | Validate Agent Script syntax |

### Metadata Commands with Agent Pseudo Type

| Command | Description |
|---------|-------------|
| `sf project retrieve start --metadata Agent:X` | Retrieve agent + components |
| `sf project deploy start --metadata Agent:X` | Deploy agent metadata |
| `sf project retrieve start --metadata Bot:X` | Retrieve bot definition only |
| `sf project retrieve start --metadata Bot:X --metadata BotVersion:X.vN` | Retrieve a specific BotVersion |
| `sf project retrieve start --metadata GenAiPlannerBundle:X` | Retrieve planner bundle |
| `sf project retrieve start --metadata GenAiPlugin` | Retrieve all plugins |
| `sf project retrieve start --metadata GenAiFunction` | Retrieve all functions |

### Management Commands

| Command | Description |
|---------|-------------|
| `sf org open agent --api-name X` | Open agent in Agentforce Builder |
| `sf org open authoring-bundle` | Open Agentforce Studio list view (v2.121.7+) |
| `sf org list metadata --metadata-type Bot` | List bots in org |
| `sf org list metadata --metadata-type GenAiPlannerBundle` | List planner bundles |

---

## Related Documentation

- [Agentforce Development Guide](../../developing-agentforce/SKILL.md)
- [Agentforce Testing Guide](../../testing-agentforce/SKILL.md)

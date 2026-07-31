# Complete Agent Templates

Templates for building complete, deployable agents.

## Learning Path

| Template | Complexity | Description |
|----------|------------|-------------|
| `hello-world.agent` | Beginner | Minimal viable agent - start here |
| `simple-qa.agent` | Beginner | Single-scope Q&A agent with direct escalation |
| `template-single-subagent.agent` | Beginner | Compatibility-named focused starter with one execution block and no router |
| `template-multi-subagent.agent` | Intermediate | Copy-and-modify starter with multiple subagents |
| `router-first.agent` | Intermediate | Router-first architecture pattern |
| `verification-gate.agent` | Advanced | Security gate before protected subagents |
| `knowledge-grounded.agent` | Advanced | Agent wired to a Data Library (ADL) |
| `order-service.agent` | Advanced | Complex real-world example |
| `production-faq.agent` | Advanced | Production-ready FAQ with escalation |
| `local-info-agent-annotated.agent` | Reference | Fully annotated example covering all major constructs |

## Quick Start

1. Copy a template to your SFDX project:
   ```bash
   mkdir -p force-app/main/default/aiAuthoringBundles/My_Agent
   cp hello-world.agent force-app/main/default/aiAuthoringBundles/My_Agent/My_Agent.agent
   cp ../bundle-meta.xml force-app/main/default/aiAuthoringBundles/My_Agent/My_Agent.bundle-meta.xml
   ```

2. Validate and deploy:
   ```bash
   sf agent validate authoring-bundle --json --api-name My_Agent --target-org your-org
   sf project deploy start --json --source-dir force-app --target-org your-org
   sf agent preview start --json --use-live-actions --authoring-bundle My_Agent --target-org your-org
   ```

3. Publish and activate only when ready to release:
   ```bash
   sf agent publish authoring-bundle --json --api-name My_Agent --target-org your-org
   sf agent activate --json --api-name My_Agent --target-org your-org
   ```

## Core Blocks

AgentScript does not require one fixed top-level block order. A deployable agent
normally contains the following blocks, with `access` and `variables` included
only when the agent's type or data flow requires them:

| Block | Purpose |
|-------|---------|
| `system:` | Agent personality and default messages |
| `access:` | Agent-user access for service agents; omit when the agent type does not require it |
| `config:` | Deployment metadata (`developer_name`, label, type, etc.) |
| `variables:` | Optional linked data and justified deterministic state |
| `language:` | Locale configuration |
| `start_agent` | Required entry execution block (exactly one) |

## Next Steps

- [patterns/](../patterns/) - Advanced patterns for complex behaviors

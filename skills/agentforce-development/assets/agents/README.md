# Complete Agent Templates

Templates for building complete, deployable agents.

## Learning Path

| Template | Complexity | Description |
|----------|------------|-------------|
| `hello-world.agent` | Beginner | Minimal viable agent - start here |
| `simple-qa.agent` | Beginner | Single-topic Q&A agent |
| `multi-topic.agent` | Intermediate | Multi-topic routing agent |
| `production-faq.agent` | Advanced | Production-ready FAQ with escalation |

## Quick Start

1. Copy a template to your SFDX project:
   ```bash
   mkdir -p force-app/main/default/aiAuthoringBundles/My_Agent
   cp hello-world.agent force-app/main/default/aiAuthoringBundles/My_Agent/My_Agent.agent
   cp ../metadata/bundle-meta.xml force-app/main/default/aiAuthoringBundles/My_Agent/My_Agent.bundle-meta.xml
   ```

2. Validate and deploy:
   ```bash
   sf agent validate authoring-bundle --api-name My_Agent --target-org your-org
   sf agent publish authoring-bundle --api-name My_Agent --target-org your-org
   ```

## Required Blocks

Every agent must have these blocks **in this order**:

| Block | Purpose |
|-------|---------|
| `system:` | Agent personality and default messages |
| `config:` | Deployment metadata (agent_name, label, etc.) |
| `variables:` | Data connections and state storage |
| `language:` | Locale configuration |
| `start_agent` | Entry point topic (exactly one required) |

## Next Steps

- [components/](../components/) - Reusable action and topic templates
- [patterns/](../patterns/) - Advanced patterns for complex behaviors
- [metadata/](../metadata/) - XML metadata templates

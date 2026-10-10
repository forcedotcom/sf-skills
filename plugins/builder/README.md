# Salesforce Builder Plugins

This folder contains Claude Code plugins for building apps and agents on the Salesforce Platform. Plugins package skills with additional components such as agents, hooks, commands, MCP servers, and scripts. Each plugin includes the components needed for its workflows; see its source and documentation for details.

Start with the [Salesforce Development plugin README](salesforce-development/README.md) for prerequisites, installation, example prompts, and the full component inventory. The [Salesforce Development plugin documentation](https://developer.salesforce.com/docs/platform/salesforce-skills-plugins/guide/salesforce-development-overview.html) covers installation, project and org setup, workflows, troubleshooting, and telemetry in Claude Code.

## Install in Claude Code

Follow the [installation guide](https://developer.salesforce.com/docs/platform/salesforce-skills-plugins/guide/install-salesforce-development.html) to review prerequisites and usage telemetry, then install Salesforce Development from the official Claude Plugin Marketplace. From a terminal, run:

```bash
claude plugin install salesforce-development@claude-plugins-official
```

Start a Claude Code session and run `/plugin` to verify installation. See the [Salesforce Development marketplace listing](https://claude.com/plugins/salesforce-development) for the official listing.

To install a specialized plugin from this repository, add the Salesforce marketplace in Claude Code, then install the plugin by name. For example, to install the React development plugin:

```text
/plugin marketplace add forcedotcom/sf-skills
/plugin install experience-react@salesforce
```

Review each plugin's source and requirements before installing it. Some workflows require additional Salesforce products, licenses, or org configuration. For installation scopes, updates, and plugin management, see the [Claude Code plugin documentation](https://code.claude.com/docs/en/plugins).

## Plugin Catalog

The [Salesforce marketplace manifest](../../.claude-plugin/marketplace.json) lists the available plugins and their descriptions. The links below open each plugin's README or source directory.

| Plugin | Use it for |
|--------|------------|
| [Salesforce Development](salesforce-development/README.md) | Core platform development: Apex, Flow, metadata, SOQL, project and org setup, testing, and deployment |
| [Salesforce Code Quality](salesforce-code-quality/) | Salesforce Code Analyzer scans, custom rules, and Well-Architected reviews |
| [Agentforce ADLC](agentforce-adlc/README.md) | Authoring, testing, securing, and deploying Agentforce agents |
| [Salesforce Test Drive](salesforce-test-drive/README.md) | Guided walkthroughs that build a Salesforce capability from start to finish |
| [Experience LWC](experience-lwc/) | Building and validating Lightning Web Components |
| [Experience React](experience-react/) | Scaffolding and developing Salesforce React UI Bundle apps |
| [Experience CMS](experience-cms/) | CMS content, branding, and media sourcing |
| [DX Org Lifecycle](dx-org-lifecycle/) | Dev Hubs, scratch orgs, sandboxes, trials, and post-install setup |
| [DX DevOps](dx-devops/) | DevOps Center pipelines, work items, and automated testing |
| [Platform Trust Security](platform-trust-security/) | Shield Platform Encryption and Salesforce Archive workflows |
| [Commerce B2B](commerce-b2b/) | Customizing B2B Commerce storefronts with Salesforce Open Code |
| [Mobile Development](mobile-development/) | Salesforce Mobile SDK apps, authentication, offline storage, and native capabilities |
| [Platform Observability](platform-observability/) | Configuring Salesforce tracing metadata and span ingestion |
| [DX ISV Partner](dx-isv-partner/) | Managed-package analytics and partner-offer preferences |
| [Service Engagement](service-engagement/) | Service Cloud messaging, web chat, and digital engagement channels |
| [Integration](integration/) | Connectivity, OAuth apps, Change Data Capture, and event subscriptions |
| [Platform Lightning Widgets](platform-lightning-widgets/) | Lightning Types and Agentforce or MCP action widgets |

## Skills and Samples

The [repository README](../../README.md) describes the standalone skills library and sample apps as well as these plugins. To install standalone skills in a compatible AI coding client, follow its usage instructions.

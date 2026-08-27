# salesforce-development

**AI-powered Salesforce platform development in Claude Code**

The foundation plugin for building apps and agents on the Salesforce Platform. When you open Claude Code in a Salesforce DX project, this plugin auto-detects your environment, injects org context, and provides AI assistance through validated skills, the Salesforce CLI, and Salesforce hosted MCP servers. The plugin uses this three-tier capability resolution: Skills (primary) → Salesforce CLI (secondary) → Salesforce MCP (last resort). Simply use natural language to describe what you want to build — no need to memorize any slash commands.

## Quick Start

This quick start describes the required software you must install, how to authorize your Salesforce org, and how to install this plugin from Anthropic's official Claude Code plugin marketplace.

1. **Install prerequisites:**
   - [Claude Code](https://claude.ai/code) — requires Claude Code 2.1.222 or later
   - [Node.js LTS](https://nodejs.org). The bundled language servers run under `node`.
   - [Salesforce CLI](https://developer.salesforce.com/tools/salesforcecli). The MCP host and deploy hooks shell out to `sf`.
   - Python 3.8+. The org-detection, deploy-safety, and agent-validation hooks use Python under the hood.

2. Authorize your Salesforce org. From a terminal or command window, use the `org login web` Salesforce CLI command which opens a browser where you log into your org with your authentication credentials:
   ```bash
   sf org login web --alias my-org --set-default
   ```

3. In Claude Code, install the plugin from the official `claude-plugins-official` marketplace (pre-registered, no `marketplace add` needed):
   ```text
   /plugin install salesforce-development@claude-plugins-official
   ```
   Alternatively, install from the Salesforce-hosted marketplace:
   ```text
   /plugin marketplace add forcedotcom/sf-skills
   /plugin install salesforce-development@salesforce
   ```

4. (Optional) Validate your environment:
   ```text
   /salesforce-development:setup
   ```

You're all set. Open a Salesforce DX project and start describing what you need.

## Example Prompts

Once you're all set up, use natural language to describe what you want to do; there's no need to memorize any slash commands:

- "Create an Apex service class to handle Account territory assignments."
- "Generate a custom object `Project__c` with fields for Name, Status, Due Date, and Owner."
- "Deploy the current changes to my sandbox."
- "Write test class for AccountTerritoryService and run it."
- "Validate a deployment to production."
- "Build a permission set that grants read access to Accounts and Contacts."
- “What can I do here?”

## Verify, Update, and Uninstall the Plugin

- **Verify:** `/plugin` lists `salesforce-development`. `/salesforce-development:status` shows the org/project banner. `"${CLAUDE_PLUGIN_ROOT}"/bin/lsp-doctor` checks the bundled language-server host.
- **Update:** if you installed from `claude-plugins-official`, updates happen automatically; to update manually run `/plugin update salesforce-development@claude-plugins-official`. If you installed from the `salesforce` marketplace, run `/plugin marketplace update salesforce` then `/plugin update salesforce-development@salesforce`.
- **Uninstall:** `/plugin uninstall salesforce-development@claude-plugins-official` (or `@salesforce`, matching however you installed it). If you added the `salesforce` marketplace, also run `/plugin marketplace remove salesforce`.

## What's Included

### 38 Skills

| Area | Skills |
|------|--------|
| **Discovery** | `platform-capability-search` — Public-channel overview of 102 released and 40 foundation capabilities (29 overlap; 113 visible), domain drilldown, skill detail with hash provenance, compact machine index, pinned one-step enable guidance, and explicitly on-demand cached org-feature detection |
| **Environment** | `platform-environment-validate` — Prerequisite scan (Salesforce CLI, Code Analyzer, Node, NPM, Git, MCP, source tracking) with guided installation and update |
| **Project and org lifecycle** | `dx-project-create` — Scaffold a new Salesforce DX project from scratch (template → generate → relocate → auth → default → source tracking); `dx-org-manage` — Create scratch orgs, take org snapshots, open orgs in the browser |
| **Apex** | `platform-apex-generate`, `platform-apex-anonymous-run` (anonymous Apex + debug-log capture), `platform-apex-test-generate`, `platform-apex-test-run`, `platform-apex-logs-debug` |
| **Automation** | `automation-flow-generate` — Screen, Autolaunched, Record-Triggered, and Scheduled Flows |
| **Declarative metadata** | `platform-custom-object-generate`, `platform-custom-field-generate`, `platform-custom-application-generate`, `platform-custom-tab-generate`, `platform-custom-report-type-generate`, `platform-list-view-generate`, `platform-value-set-generate`, `platform-validation-rule-generate`, `platform-flexipage-generate`, `platform-lightning-app-coordinate` |
| **Data** | `platform-soql-query` — SOQL/SOSL authoring, optimization, and query-plan analysis |
| **Deploy and retrieve** | `platform-metadata-deploy`, `platform-metadata-retrieve`, `platform-manifest-generate` (build `package.xml` / `destructiveChanges.xml`), `platform-metadata-api-context-get`, `platform-deploy-validate`, `platform-quick-deploy`, `platform-destructive-deploy` |
| **Security** | `platform-permission-set-generate`, `platform-sharing-owd-configure`, `platform-sharing-rules-generate` |
| **Code quality** | `dx-code-analyzer-run` — Run Code Analyzer (PMD/sfge/ESLint/RetireJS) and triage findings; `dx-code-analyzer-configure` — Author `code-analyzer.yml` + CI wiring; `dx-code-analyzer-custom-rule-create` — Author custom PMD/regex/ESLint rules; `platform-architecture-analyze` — Well-Architected review across Trusted / Easy / Adaptable |
| **Reporting** | `platform-report-generate` |
| **LSP** | `platform-lsp-integrate` — Contract and fallbacks for the bundled language-server tools |

### What Else Is in the Box

- **Agents** — `salesforce-dev`, the primary Salesforce development agent (activates automatically in Salesforce projects — `sfdx-project.json` present — and routes requests skills-first, then SF CLI, then direct API as a last resort); and `architecture-review`, a read-only Well-Architected reviewer that grades a project against the Trusted / Easy / Adaptable pillars and hands back a pillar-scored report plus a governance checklist.
- **Slash commands** — `/salesforce-development:discovery` (computed public-channel capability overview/drilldown, `plugins <text>` for on-demand uninstalled-plugin matching, and optional on-demand `features [--target-org <alias>] [--refresh] [--json]`), `:plugin-install` (one-confirmation install for a trusted same-session marketplace recommendation; source confirmation for external plugins), `:plugin-recommendations` (view or change how readily uninstalled plugins get proposed), `:telemetry`, `:setup`, `:status`, `:org`, `:login`, `:logout`, `:set-default`, `:project`, `:reset-source-tracking`, `:welcome`.
- **MCP servers** — `salesforce-api-context` and `salesforce-metadata-experts` (API/metadata guidance), and `salesforce-lsp`, a local host that lazily spawns the **Apex** and **SOQL** language servers and exposes their semantic capabilities as MCP tools. See the `platform-lsp-integrate` skill for the tool contract.
- **Hooks** — org-context detection on session start; a production deploy-safety gate and an Apex pre-deploy diagnostics gate on `sf project deploy`; and skills-first advisories that, when no installed skill matches, also propose an uninstalled plugin whose curated description does.

Your progress through **Connect → Project → Build → Test → Deploy → Observe** is tracked from real, successful actions in your project — never assumed. Run `/salesforce-development:discovery journey inspect` to review it, or `journey reset` to clear it.

## More Information

- **[Configuration reference](./docs/configuration.md)** — ambient UI modes, the optional status line, and deploy/delete guard rails.
- **[Changelog](https://github.com/forcedotcom/sf-skills/blob/main/plugins/builder/salesforce-development/CHANGELOG.md)** — what's new in each release.
- To skip Claude Code's permission prompts for the CLI commands this plugin runs (`sf`, `node`, `npm`, read-only `git`), add the equivalent allow-rules to your DX project's `.claude/settings.json`. See [Settings](https://code.claude.com/docs/en/settings#permission-settings) in the Claude Code docs. This plugin doesn't ship a `settings.json` of its own.
- Third-party code bundled with this plugin (such as the vendored Apex language server and a few esbuild-bundled MCP dependencies) is attributed in [`NOTICE`](./NOTICE).

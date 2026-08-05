# salesforce-development

**AI-powered Salesforce platform development in Claude Code**

The foundation plugin for building apps and agents on the Salesforce Platform. When you open Claude Code in a Salesforce DX project, this plugin auto-detects your environment, injects org context, and provides AI assistance through validated skills, the Salesforce CLI, and Salesforce hosted MCP servers. The plugin uses this three-tier capability resolution: Skills (primary) → Salesforce CLI (secondary) → Salesforce MCP (last resort). Simply use natural language to describe what you want to build — no need to memorize any slash commands.

## Quick Start

This quick start describes the required software you must install, how to authorize your Salesforce org, and how to add the Salesforce Claude Plugin Marketplace and install this plugin. 

1. Install these required prerequisites:
   - [Claude Code](https://claude.ai/code)
   - [Node.js LTS](https://nodejs.org).  The bundled language servers run under `node`.
   - [Salesforce CLI](https://developer.salesforce.com/tools/salesforcecli). The MCP host and deploy hooks shell out to `sf`.  
   - Python 3.8+.  The the `org-detection` and `deploy-safety` hooks use Python under the hood. 

2. Authorize your Salesforce org. From a terminal or command window, use the `org login web` Salesforce CLI command which opens a browser where you log into your org with your authentication credentials:
   ```bash
   sf org login web --alias my-org --set-default
   ```

3. In Claude Code, add the Salesforce Claude Plugin Marketplace and install the plugin:
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

To check that the plugin is installed, run this command in Claude Code:

```text
/plugin
```

You should see `salesforce-development` listed. Skills are available automatically. 

To show the org/project banner, run this command:

```text
/salesforce-development:status
```

To check the bundled language-server host:

```bash
"${CLAUDE_PLUGIN_ROOT}"/bin/lsp-doctor
```

To update the plugin:

```text
/plugin marketplace update salesforce
/plugin update salesforce-development@salesforce
```

To uninstall the plugin and remove the Salesforce marketplace: 

```text
/plugin uninstall salesforce-development@salesforce
/plugin marketplace remove salesforce
```

## What's Included

### 41 Skills

| Area | Skills |
|------|--------|
| **Discovery** | `platform-capability-search` — Public-channel overview of 102 released and 40 foundation capabilities (29 overlap; 113 visible), domain drilldown, skill detail with hash provenance, compact machine index, pinned one-step enable guidance, and explicitly on-demand cached org-feature detection |
| **Environment** | `platform-environment-validate` — Prerequisite scan (Salesforce CLI, Code Analyzer, Node, NPM, Git, MCP, source tracking) with guided installation and update |
| **Project and org lifecycle** | `dx-project-create` — Scaffold a new Salesforce DX project from scratch (template → generate → relocate → auth → default → source tracking); `dx-org-manage` — Create scratch orgs, take org snapshots, open orgs in the browser |
| **Apex** | `platform-apex-generate`, `platform-apex-anonymous-run` (anonymous Apex + debug-log capture), `platform-apex-test-generate`, `platform-apex-test-run`, `platform-apex-logs-debug` |
| **Automation** | `automation-flow-generate` — Screen, Autolaunched, Record-Triggered, and Scheduled Flows |
| **Agentforce (ADLC)** | `agentforce-generate` — Author `.agent` files (Agent Script DSL) with bundled discover and scaffold scripts; `agentforce-test` — Preview and batch testing and action execution; `agentforce-observe` — Session-trace analysis and optimization. `agentforce-test` also covers security testing (OWASP LLM Top 10). |
| **Declarative metadata** | `platform-custom-object-generate`, `platform-custom-field-generate`, `platform-custom-application-generate`, `platform-custom-tab-generate`, `platform-custom-report-type-generate`, `platform-list-view-generate`, `platform-value-set-generate`, `platform-validation-rule-generate`, `platform-flexipage-generate`, `platform-lightning-app-coordinate` |
| **Data** | `platform-soql-query` — SOQL/SOSL authoring, optimization, and query-plan analysis |
| **Deploy and retrieve** | `platform-metadata-deploy`, `platform-metadata-retrieve`, `platform-manifest-generate` (build `package.xml` / `destructiveChanges.xml`), `platform-metadata-api-context-get`, `platform-deploy-validate`, `platform-quick-deploy`, `platform-destructive-deploy` |
| **Security** | `platform-permission-set-generate`, `platform-sharing-owd-configure`, `platform-sharing-rules-generate` |
| **Code quality** | `dx-code-analyzer-run` — Run Code Analyzer (PMD/sfge/ESLint/RetireJS) and triage findings; `dx-code-analyzer-configure` — Author `code-analyzer.yml` + CI wiring; `dx-code-analyzer-custom-rule-create` — Author custom PMD/regex/ESLint rules; `platform-architecture-analyze` — Well-Architected review across Trusted / Easy / Adaptable |
| **Reporting** | `platform-report-generate` |
| **LSP** | `platform-lsp-integrate` — Contract and fallbacks for the bundled language-server tools |

### What Else Is in the Box

- **Agents** — `salesforce-dev`, the primary Salesforce development agent (activates automatically in Salesforce projects — `sfdx-project.json` present — and routes requests skills-first, then SF CLI, then direct API as a last resort); `architecture-review`, a read-only Well-Architected reviewer that grades a project against the Trusted / Easy / Adaptable pillars and hands back a pillar-scored report plus a governance checklist; and the Agentforce ADLC agents — `adlc-orchestrator` (plan-mode lifecycle coordinator) delegating to `adlc-author` (writes `.agent` files), `adlc-engineer` (scaffolds Flow/Apex and deploys bundles), and `adlc-qa` (tests, optimizes, and security-assesses agents).
- **Slash commands** — `/salesforce-development:discovery` (computed public-channel capability overview/drilldown and optional on-demand `features [--target-org <alias>] [--refresh] [--json]`), `:setup`, `:status`, `:org`, `:login`, `:logout`, `:set-default`, `:project`, `:reset-source-tracking`, `:welcome`. The checked discovery artifact is generated from an exact Git-tracked public-release manifest pinned to release `1.32.0` plus the physical foundation roster, not the internal authoring tree. Runtime discovery re-hashes bundled foundation trees and counts only valid standalone skill directories as installed; invalid same-name observations do not suppress public add. Feature probes never run at SessionStart; they use a normalized OS/XDG user cache outside `.sf`/`.sfdx` and report `unknown` rather than inferring absence from permission or coverage gaps.
- **MCP servers** — `salesforce-api-context` and `salesforce-metadata-experts` (API/metadata guidance), and `salesforce-lsp`, a local host that lazily spawns the **Apex** and **SOQL** language servers and exposes their semantic capabilities as MCP tools. See the `platform-lsp-integrate` skill for the tool contract.
- **Hooks** — org-context detection on session start; a production deploy-safety gate and an Apex pre-deploy diagnostics gate on `sf project deploy`; skills-first advisories; and an Agent Script (`.agent`) syntax validator that runs after `Write`/`Edit` and surfaces non-blocking findings.

### Other Important Notes

- **Guard rails vs. Claude Code's auto-mode classifier.** This plugin's gates fire **only** on `sf project deploy`, `sf project delete`, and destructive-changes deploys — they **never block read-only commands** (`sf org list/display`, `sf data query`, `sf project retrieve`, source-tracking probes). Every gate emission is prefixed `[salesforce-development · deploy-gate]`. A denial on a *read-only* command with **no such prefix** is Claude Code's auto-mode classifier, not this plugin — a separate layer the plugin cannot rewrite. If reads get gated, the fix is to retarget a **sandbox** (the classifier reclassifies `production` → `sandbox` and the reads pass) or to allowlist them via `/permissions`. Routing around a denial by re-shaping the command defeats the control while technically satisfying it — don't.
- **Opt-in auto-deploy.** Set `SFDX_AUTO_DEPLOY=1` to have `sf-deploy-gate auto-deploy` push a saved `force-app/**` edit (`Write`/`Edit`/`MultiEdit`) to your default org automatically after each save. Off by default. It refuses to run against orgs classified `production` or `unknown` regardless of the flag — the same production guard rail above still applies.
- **LSP scope:** This plugin vendors the Apex + SOQL language servers only. The LWC language server is intentionally not bundled.

## More Information

To skip Claude Code's permission prompts for the CLI commands that this plugin runs (`sf`, `node`,`npm`, read-only `git`), add the equivalent allow-rules to your DX project's `.claude/settings.json`. [Settings](https://code.claude.com/docs/en/settings#permission-settings) in the Claude Code docs. This plugin doesn't ship a `settings.json` of its own.

Third-party code bundled with this plugin (such as the vendored Apex language server and a few esbuild-bundled MCP dependencies) is attributed in [`NOTICE`](./NOTICE).

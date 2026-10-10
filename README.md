# Salesforce Skills and Plugins Library

This repository provides Salesforce agent skills, plugins, and sample apps for building applications. It includes skills for Agentforce agents, Lightning apps, Flow, Apex, SOQL, Lightning Web Components (LWC), UI bundles, objects and fields, permission sets, and related areas. The [builder plugins](plugins/builder/README.md) package skills with additional capabilities such as agents, hooks, commands, and Model Context Protocol (MCP) servers for Claude Code.

The skills are contributed by Salesforce and the broader community. The skills library is optimized for Agentforce Vibes and can be used with any AI tool that supports skills. For guided Salesforce development in Claude Code, start with the [Salesforce Development plugin README](plugins/builder/salesforce-development/README.md) and the [Salesforce Development plugin documentation](https://developer.salesforce.com/docs/platform/salesforce-skills-plugins/guide/salesforce-development-overview.html).

> ⚠️ **Expect frequent changes.** The Salesforce skills and plugins library is evolving rapidly as we refine patterns and incorporate feedback. Skills and plugins may be renamed, restructured, or removed between releases — they do not follow the same stability guarantees as GA platform APIs. If you’ve forked or synced the repository, be prepared for upstream changes that may conflict with local modifications. This repository is always the source of truth.

## 🗂️ Structure

```
sf-skills/
├── .claude-plugin/
│   └── marketplace.json  # Salesforce plugin marketplace catalog
├── plugins/
│   └── builder/          # Claude Code plugins for Salesforce development
│       ├── README.md     # Plugin catalog and setup guidance
│       ├── salesforce-development/
│       └── ...
├── skills/               # Directory-based executable workflows
│   ├── platform-apex-generate/
│   ├── platform-custom-object-generate/
│   ├── automation-flow-generate/
│   └── ...
├── samples/              # Synced sample apps (e.g. from npm)
│   └── ui-bundle-template-app-react-sample-b2e/
│   └── ...
├── scripts/
│   └── ...
└── README.md
```

## 🚀 Usage

| **Tool** | **Usage** |
|----------|-------------|
| **Agentforce Vibes** | Skills are auto-installed and auto-updated |
| **Claude Code — Salesforce Development plugin** | Follow the [plugin installation guide](https://developer.salesforce.com/docs/platform/salesforce-skills-plugins/guide/install-salesforce-development.html) for skills, guided workflows, and integrated tools |
| **OpenCode, Claude Code, Codex, Cursor, [more](https://agentskills.io/) — standalone skills** | `npx skills add forcedotcom/sf-skills` |

## 🔌 Plugins

Plugins bundle skills with other components that the coding client installs and loads together. The Salesforce Development plugin includes agents, hooks, commands, and MCP servers for building, testing, and deploying on the Salesforce Platform. Specialized builder plugins add capabilities for areas such as Agentforce, code quality, LWC, and React development.

- [Builder plugin catalog and setup](plugins/builder/README.md)
- [Salesforce Development plugin README](plugins/builder/salesforce-development/README.md) — prerequisites, quick start, and component inventory
- [Salesforce Development plugin documentation](https://developer.salesforce.com/docs/platform/salesforce-skills-plugins/guide/salesforce-development-overview.html) — installation, project and org setup, workflows, and troubleshooting in Claude Code
- [Claude Code plugin documentation](https://code.claude.com/docs/en/plugins) — plugin components and how plugins work

## 📦 Samples

The `samples/` folder contains synced sample apps. For example, `samples/ui-bundle-template-app-react-sample-b2e/` tracks the npm package `@salesforce/ui-bundle-template-app-react-sample-b2e` (nightly and on manual trigger via GitHub Actions). 

To run the same sync locally from the repository root: 

```bash
npm install
npm run sync-react-b2e-sample
```

The GitHub Action runs the same commands and opens a pull request when the npm package version changes. For more information, see [samples/README.md](samples/README.md).

## 🛠️ Agent Skills

Agent Skills package executable workflows, scripts, and reference material into self-contained directories. This repository follows the open [Agent Skills specification](https://agentskills.io/) and can be used with OpenCode, Claude Code, Codex, Cursor, and other tools that support skills.

### Directory Structure

Each skill is a folder that can include:
- `SKILL.md` (required): Instructions and YAML front matter.
- `scripts/` (optional): Executable scripts (For example, Python, Bash, or JavaScript).
- `references/` (optional): Extra reference documentation.
- `assets/` (optional): Templates, schemas, and lookup data

## 🤝 Contributing

See [Contributing](./CONTRIBUTING.md).

## 💬 Feedback

- Open an issue in this repository
- Open a pull request with suggested changes
- Use GitHub Discussions or the pull request thread for broader conversation

## Project Governance & Support

- [License](./LICENSE.txt)
- [Code of Conduct](./CODE_OF_CONDUCT.md)
- [Contributing](./CONTRIBUTING.md)
- [Security](./SECURITY.md)

# Agentforce Vibes Library

This repository provides a curated collection of Salesforce agent skills for building applications. It includes skills for Agentforce agents, Lightning apps, Flow, Apex, SOQL, Lightning Web Components (LWC), UI bundles, objects and fields, permission sets, and related areas.

The skills are contributed by Salesforce and the broader community. It’s optimized for Agentforce Vibes and can be used with any AI tool that supports skills.

## 🗂️ Structure

```
afv-library/
├── skills/               # Directory-based executable workflows
│   ├── generating-apex/
│   ├── generating-custom-object/
│   ├── generating-flow/
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
| **OpenCode, Claude Code, Codex, Cursor, [more](https://agentskills.io/)** | `npx skills add forcedotcom/afv-library` |

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

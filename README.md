# Agentforce Vibes Library

AI skills and rules library for Agentforce Vibes development of Salesforce metadata.

## 📚 About

This repository curates Salesforce-focused skills and system rules from the wider developer community to accelerate Agentforce Vibes agentic workflows. 

## 🗂️ Structure

```
afv-library/
├── rules/                # Single-file guardrails and standards
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

## Manual Usage

Browse the repository and copy/paste any rule or skill directly into Agentforce Vibes or your preferred AI tool.

## Samples

The `samples/` folder contains synced sample apps. For example, `samples/ui-bundle-template-app-react-sample-b2e/` is kept in sync with the npm package `@salesforce/ui-bundle-template-app-react-sample-b2e` (nightly and on manual trigger via GitHub Actions). To run the same sync locally from the repo root:

```bash
npm install
npm run sync-react-b2e-sample
```

The GitHub Action runs these same commands and opens a PR only when the npm package version has changed. See [samples/README.md](samples/README.md) for details.


## 🛠️ Agent Skills

Agent Skills extend rules by bundling executable workflows, scripts, and reference materials into self-contained directories. Skills follow the open [Agent Skills specification](https://agentskills.io/) and are portable across many agent tools (Cursor, Claude Code, VS Code extensions, etc.).

### Directory Structure

Each skill is a folder containing:
- `SKILL.md` (required) - instructions + YAML frontmatter
- `scripts/` (optional) - executable Python/Bash/JS
- `references/` (optional) - additional documentation
- `assets/` (optional) - templates, schemas, lookup data


## 🤝 Contributing

See [Contributing](./CONTRIBUTING.md) for complete details.


## Feedback

Found an issue or have a suggestion?
- Open an issue in GitHub
- Suggest improvements via pull request
- Start a discussion in GitHub Discussions or the pull request thread


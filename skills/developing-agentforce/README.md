# Agentforce Development Skill

A Claude Code skill for building, modifying, debugging, and deploying Agentforce agents using Agent Script — Salesforce's scripting language for next-generation AI agents on the Atlas Reasoning Engine.

## What This Skill Does

Agent Script was introduced in 2025 with zero training data in any AI model. This skill bridges that gap by providing structured reference material, design patterns, CLI workflows, and debugging guidance so that AI coding assistants can work with Agent Script accurately.

The skill covers the full Agent Script lifecycle:

| Domain | What It Handles |
|--------|----------------|
| Create an Agent | Agent Spec design, environment validation, bundle generation, code authoring |
| Modify an Agent | Subagent/action changes, instruction refinement, flow control updates |
| Create or Modify Backing Logic | Invocable Apex stubs, Flow wrappers, Prompt Templates |
| Deploy and Publish | Source deploy, agent activation, publishing to channels |
| Diagnose Compilation Errors | Compiler error interpretation, syntax fixes, metadata resolution |
| Diagnose Behavioral Issues | Trace-based debugging, subagent routing, action I/O analysis |
| Diagnose Production Issues | Runtime failures, reserved keyword conflicts, deployment gotchas |
| Test an Agent | Utterance-based validation, preview with live actions, trace analysis |
| Generate Diagrams | Subagent map visualizations, agent architecture diagrams |

## Skill Structure

```
developing-agentforce/
├── SKILL.md                    # Router — maps user intent to task domains and reference files
├── references/                 # Domain knowledge (14 files)
│   ├── agent-script-core-language.md
│   ├── agent-design-and-spec-creation.md
│   ├── agent-validation-and-debugging.md
│   ├── salesforce-cli-for-agents.md
│   ├── agent-metadata-and-lifecycle.md
│   ├── agent-access-guide.md
│   ├── agent-user-setup.md
│   ├── actions-reference.md
│   ├── action-prompt-templates.md
│   ├── agent-subagent-map-diagrams.md
│   ├── minimal-examples.md
│   ├── known-issues.md
│   ├── production-gotchas.md
│   └── version-history.md
├── assets/                     # Templates, examples, and starter agents
│   ├── agent-spec-template.md
│   ├── invocable-apex-template.cls
│   ├── bundle-meta.xml
│   ├── patterns/               # Reusable Agent Script patterns
│   ├── agents/                 # Annotated example agents
│   ├── apex/                   # Apex backing logic examples
│   ├── components/             # LWC components for agent channels
│   ├── metadata/               # Metadata templates
│   └── *.agent                 # Starter agent templates
└── staging/                    # Unmerged reference material awaiting review
```

## How It Works

SKILL.md acts as a router. It detects user intent from task descriptions, maps to a task domain, and instructs the AI assistant to read the relevant reference files before starting work. Reference files are loaded on demand — the assistant only reads what the current task requires.

Three rules apply across all domains:

1. **Always `--json`** on every `sf` CLI command
2. **Diagnose before you fix** — preview with live actions and read traces before modifying code
3. **Spec approval is a hard gate** — never proceed past Agent Spec creation without user approval

## Prerequisites

- Salesforce org with Agentforce license
- API version 66.0+ (Spring '26)
- Einstein Agent User (for service agents)
- Salesforce CLI v2.x (`sf` command)
- Claude Code (or compatible AI coding agent)

## Installation

Copy the `developing-agentforce` folder into your project's `.claude/skills/` directory:

```
your-project/
└── .claude/
    └── skills/
        └── developing-agentforce/
            ├── SKILL.md
            ├── references/
            └── assets/
```

Restart Claude Code after installation.

## Version

Current version: **0.4.9** (2026-03-20). See [references/version-history.md](references/version-history.md) for the full changelog.

## Credits

This skill integrates knowledge from the following sources:

**Jag Valaiyapathy** ([sf-skills](https://github.com/Jaganpro/sf-skills), MIT License)
— Known issues catalog, production gotchas, agent access and permissions guide, and deployment patterns. Integrated starting in v0.4.2.

**Hua Xu** (Salesforce APAC FDE team)
— Open-gate routing pattern from Kogan agent deployment.

**Salesforce DevRel** ([agent-script-recipes](https://github.com/trailheadapps/agent-script-recipes))
— Canonical Agent Script examples used as grounding material.

**Dylan Zeigler, AI Platform** (llm-utils)
— Agent Script playground used as reference source.

## License

Apache-2.0

# Agentforce Development Skill

A skill for developing Agentforce agents with Agent Script.

## What This Skill Covers

The skill routes agent work across the full lifecycle:

| Domain | What It Handles |
|--------|----------------|
| Create an Agent | Agent Spec design, environment checks, bundle generation, draft authoring |
| Modify an Agent | Subagent/action changes, instruction refinement, flow updates |
| Diagnose Compilation Errors | Error capture, classification, targeted fixes |
| Diagnose Behavioral Issues | Trace-based debugging, routing/action analysis |
| Deploy / Release | Draft iteration, deploy, explicit publish + activate |
| Test an Agent | Coverage design, spec creation, run analysis |

## Skill Structure

```text
agentforce-generate/
├── SKILL.md                    # Execution router and hard rules
├── references/                 # Domain guidance and adjacent operational docs
│   ├── patterns-by-requirement.md
│   ├── posture-and-determinism.md
│   ├── agent-design-and-spec-creation.md
│   ├── architecture-patterns.md
│   ├── agent-script-core-language.md
│   ├── salesforce-cli-for-agents.md
│   ├── agent-validation-and-debugging.md
│   ├── deploy-reference.md
│   ├── agent-metadata-and-lifecycle.md
│   ├── data-library-reference.md
│   ├── ... (additional references)
├── assets/                     # Templates, examples, and reusable snippets
│   ├── agent-spec-template.md
│   ├── bundle-meta.xml
│   ├── invocable-apex-template.cls
│   ├── agents/                 # Complete agent templates (including router-first)
│   └── patterns/               # Reusable implementation patterns
```

## How It Works

`SKILL.md` acts as the router. It maps user intent to task domains and required references, then enforces hard rules for safe execution.

Core rules include:

1. **Always `--json`** on every `sf` CLI command
2. **Diagnose before you fix** — preview with live actions and read traces before modifying code
3. **Spec approval is a hard gate** — never proceed past Agent Spec creation without user approval
4. **Draft-first lifecycle** — iterate in draft by default; publish/activate only with explicit user confirmation

## Prerequisites

- Salesforce org with Agentforce license
- API version 66.0+ (Spring '26)
- Einstein Agent User (for service agents)
- Salesforce CLI v2.x (`sf` command)
- Claude Code (or compatible AI coding agent)

## Installation

Copy the `agentforce-generate` folder into your project's `.claude/skills/` directory:

```text
your-project/
└── .claude/
    └── skills/
        └── agentforce-generate/
            ├── SKILL.md
            ├── references/
            └── assets/
```

Restart Claude Code after installation.

## Key References

- Pattern selection: [references/patterns-by-requirement.md](references/patterns-by-requirement.md)
- Posture guidance: [references/posture-and-determinism.md](references/posture-and-determinism.md)
- Design/spec workflow: [references/agent-design-and-spec-creation.md](references/agent-design-and-spec-creation.md)
- Architecture mechanics: [references/architecture-patterns.md](references/architecture-patterns.md)
- Core language: [references/agent-script-core-language.md](references/agent-script-core-language.md)
- Validation/debugging: [references/agent-validation-and-debugging.md](references/agent-validation-and-debugging.md)
- Reference index and consolidation notes: [references/reference-map.md](references/reference-map.md)

## Version

Current version: **0.6.1** (2026-05-20). See [references/version-history.md](references/version-history.md) for the full changelog.

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

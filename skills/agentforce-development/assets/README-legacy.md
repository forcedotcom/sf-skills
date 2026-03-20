# Agent Script Templates

Organized templates for building Agentforce agents.

---

## Directory Structure

```
assets/
├── agents/       Complete, deployable agent examples
├── components/   Reusable action and topic snippets
├── patterns/     Advanced patterns (lifecycle, callbacks)
└── metadata/     XML metadata templates
```

---

## Quick Start

```
What do you need?
│
├─► "Just starting"
│   └─► agents/hello-world.agent
│
├─► "Complete agent with topics"
│   └─► agents/multi-topic.agent
│
├─► "Add actions to my agent"
│   ├─► components/flow-action.agent
│   └─► components/apex-action.agent
│
├─► "Advanced patterns"
│   └─► patterns/ (see patterns/README.md)
│
└─► "XML metadata"
    └─► metadata/
```

---

## Template Inventory

### agents/ - Complete Agents

| Template | Complexity | Description |
|----------|------------|-------------|
| `hello-world.agent` | Beginner | Minimal viable agent |
| `simple-qa.agent` | Beginner | Single-topic Q&A |
| `multi-topic.agent` | Intermediate | Multi-topic routing |
| `production-faq.agent` | Advanced | Production-ready with escalation |

### components/ - Reusable Parts

| Template | Purpose |
|----------|---------|
| `flow-action.agent` | Flow action integration |
| `apex-action.agent` | Apex action integration |
| `topic-with-actions.agent` | Topic with actions |
| `error-handling.agent` | Input validation |
| `escalation-setup.agent` | Human handoff |

### patterns/ - Advanced (see patterns/README.md)

| Template | Purpose | Deployment |
|----------|---------|------------|
| `lifecycle-events.agent` | before/after reasoning | GenAiPlannerBundle |
| `action-callbacks.agent` | Deterministic chains | GenAiPlannerBundle |
| `bidirectional-routing.agent` | Topic routing with return | Both |
| `system-instruction-overrides.agent` | Topic-level personas | Both |
| *(6 more patterns)* | | |

### metadata/ - XML Templates

| Template | Purpose |
|----------|---------|
| `bundle-meta.xml` | AiAuthoringBundle metadata |
| `genai-function-*.xml` | Action metadata |
| `genai-plugin.xml` | Plugin grouping |
| `*-prompt-template.xml` | PromptTemplate |
| `http-callout-flow.xml` | Flow template |

---

## Related Documentation

- [SKILL.md](../SKILL.md) - Main skill reference
- [references/](../references/) - Detailed documentation

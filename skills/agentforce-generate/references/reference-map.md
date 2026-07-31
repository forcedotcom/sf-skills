# Reference Map and Consolidation Plan

> Meta document: describes how to use and maintain the reference set.

This file defines which references are primary vs supplemental so the skill stays
organized without risky deletions.

## Primary References (Authoritative)

- `agent-script-core-language.md` — syntax and execution model
- `agent-design-and-spec-creation.md` — design/spec workflow
- `patterns-by-requirement.md` — scenario-to-pattern selection
- `architecture-patterns.md` — architecture mechanics and migration
- `posture-and-determinism.md` — subagent posture guidance
- `zen-of-agentscript.md` — concrete, unordered authoring invariants and merge checks
- `salesforce-cli-for-agents.md` — command reference
- `agent-validation-and-debugging.md` — runtime validation/debug flow
- `deploy-reference.md` — draft-vs-release deployment lifecycle

## Adjacent Operational References (Keep)

- `agent-metadata-and-lifecycle.md`
- `agent-user-setup.md`
- `agent-access-guide.md`
- `data-library-reference.md`
- `known-issues.md`
- `production-gotchas.md`
- `mcp-management-reference.md`

## Supplemental References (Review for Merge/Prune Later)

- `examples.md` — long-form walkthroughs
- `actions-reference.md` — broad action property reference
- `action-prompt-templates.md` — prompt-template-specific action guidance
- `feature-validity.md` — utility-vs-target property validity matrix

## Full Reference Index (annotated)

The complete reference set the **Create an Agent** workflow draws on, in load order. Other task domains list only the subset they need; each SKILL.md step also links the specific reference it requires inline.

1. [CLI for Agents](salesforce-cli-for-agents.md) — exact command syntax for generate, validate, deploy, publish, activate; Section 12 for Einstein Agent User creation
2. [Core Language](agent-script-core-language.md) — execution model, syntax, block structure, anti-patterns
3. [Design & Agent Spec](agent-design-and-spec-creation.md) — subagent graph design, flow control patterns, Agent Spec production, action implementation analysis; Section 3 for environment prerequisites
4. [Subagent Map Diagrams](agent-subagent-map-diagrams.md) — Mermaid diagram conventions for visualizing the agent's subagent graph
5. [Posture & Determinism](posture-and-determinism.md) — default agentic posture, deterministic controls with cause
6. [Agent User Setup & Permissions](agent-user-setup.md) — permission set assignment, object permissions, cross-subagent validation
7. [Metadata & Lifecycle](agent-metadata-and-lifecycle.md) — directory structure, bundle metadata; publish troubleshooting
8. [Validation & Debugging](agent-validation-and-debugging.md) — validate the agent compiles, preview to confirm behavior
9. [Agent Access Guide](agent-access-guide.md) — end-user access permissions, visibility troubleshooting
10. [Known Issues](known-issues.md) — only load when errors persist after code fixes
11. [Patterns by Requirement](patterns-by-requirement.md) — scenario-to-pattern mapping for architecture and flow choices
12. [Architecture Patterns](architecture-patterns.md) — router-first mechanics, verification gates, workflow-local linear patterns
13. [Complex Data Types](complex-data-types.md) — type mapping decision tree
14. [Safety Review](safety-review-reference.md) — 7-category safety review
15. [Discover Reference](discover-reference.md) — target discovery CLI
16. [Scaffold Reference](scaffold-reference.md) — stub generation CLI
17. [Deploy Reference](deploy-reference.md) — deployment lifecycle, error recovery
18. [Data Library Reference](data-library-reference.md) — provision a SFDRIVE Agentforce Data Library and wire it into the `.agent` via the `knowledge:` block + `AnswerQuestionsWithKnowledge` action

## Current Recommendation (No Deletions Yet)

1. Keep all files for now.
2. Treat supplemental references as second-level docs.
3. In a future cleanup pass, consider:
   - keep `examples.md` as the single examples reference and avoid re-splitting minimal examples
   - folding `feature-validity.md` into `actions-reference.md`
   - keeping `action-prompt-templates.md` only if prompt-template depth remains valuable

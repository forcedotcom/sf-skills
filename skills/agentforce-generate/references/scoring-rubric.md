# 100-Point Scoring Rubric

> Extracted from SKILL.md Section 6. This file is loaded on demand when the scoring rubric is needed.

Score every generated agent against this rubric before presenting to the user.

| Category | Points | Key Criteria |
|----------|--------|--------------|
| Structure & Syntax | 15 | Required blocks are present. Block order, nesting, indentation, field names, references, and string forms pass parser, linter, compiler, and emitted-artifact checks. |
| Safety & Responsible AI | 15 | Evaluated via safety review (7 categories): AI disclosure present, no impersonation/deception/manipulation, responsible data handling, no harmful content (including euphemisms), no discrimination (direct or proxy), clear scope boundaries, escalation paths for sensitive topics. Deduct 15 for any BLOCK finding, 5 per WARN finding. |
| Conversation & Instruction Quality | 20 | Each reachable branch has one compatible next outcome. Resolved global and local instructions are concrete and self-contained. Natural follow-up, correction, intent change, cancellation, and empty/failure paths work without stale authored state overriding the latest turn. |
| State & Deterministic Controls | 15 | Every mutable variable names its writer, deterministic consumer, cause, reset/expiry, correction behavior, and cancel path where applicable. Controls are limited to authorization, confirmed consequences, exact action data flow, external ordering, persistence beyond the history window, or a reproduced trace failure. Penalize duplicate, dead, conversational-stage, and unjustified state. |
| Subagent Boundaries & Routing | 15 | Every subagent is reachable and changes objective, instructions, actions, authority, or escalation behavior. Transitions have one intended outcome and preserve fresh-intent routing. No orphan subagents, dialogue-stage subagents, generic focus locks, or accidental non-returning delegation. |
| Action Configuration & Evidence | 10 | Level 1 definitions and Level 2 invocations have exact I/O bindings and valid types. Use slot filling (`...`) for conversational inputs. Persist only outputs needed by a named later deterministic consumer. Consequential actions have machine-checkable authorization/confirmation, and responses claim external results only after successful action output. |
| Deployment Readiness | 10 | Valid `default_agent_user`. `developer_name` matches folder. `bundle-meta.xml` present with `<bundleType>AGENT</bundleType>`. Linked variables for service agents (`EndUserId`, `RoutableId`, `ContactId`). |

Do not award points merely for adding variables, branches, transitions, or
subagents. Complexity must have a named requirement or reproduced failure and
must improve the behavioral evaluations.

## Score Interpretation

| Score | Meaning | Action |
|-------|---------|--------|
| 90-100 | Eligible for release review | Run behavioral evaluations and obtain explicit release approval |
| 75-89 | Good with minor issues | Fix noted items, then re-score and re-evaluate |
| 60-74 | Needs work | Address structural and behavioral issues |
| Below 60 | BLOCK | Major rework required |

A score never authorizes deployment or publication. Parser/lint success,
behavioral evidence, and the user's explicit release approval remain separate
hard gates.

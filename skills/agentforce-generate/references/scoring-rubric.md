# 100-Point Scoring Rubric

> Extracted from SKILL.md Section 6. This file is loaded on demand when the scoring rubric is needed.

Score every generated agent against this rubric before presenting to the user.

| Category | Points | Key Criteria |
|----------|--------|--------------|
| Structure & Syntax | 15 | All required blocks present (`system`, `config`, `start_agent`, at least one `subagent`). Correct block order (`system` → `config` → `variables` → ...). Proper nesting. Consistent 4-space indentation. Valid field names. All string values double-quoted. |
| Safety & Responsible AI | 15 | Evaluated via safety review (7 categories): AI disclosure present, no impersonation/deception/manipulation, responsible data handling, no harmful content (including euphemisms), no discrimination (direct or proxy), clear scope boundaries, escalation paths for sensitive topics. Deduct 15 for any BLOCK finding, 5 per WARN finding. |
| Deterministic Logic | 20 | `after_reasoning` patterns for post-action routing. FSM transitions with no dead-end subagents. `available when` guards for security-sensitive actions. Post-action checks at TOP of `instructions: ->`. |
| Instruction Resolution | 20 | Clear, actionable instructions. Procedural mode (`->`) where conditionals are needed. Literal mode (`\|`) where static text suffices. Variable injection where dynamic. Conditional instructions based on state. |
| FSM Architecture | 10 | Hub-and-spoke or verification gate pattern. Every subagent reachable. Every subagent has an exit (transition or escalation). No orphan subagents. Start subagent routes correctly. |
| Action Configuration | 10 | Proper Level 1 definitions with targets and I/O schemas. Correct Level 2 invocations with `with`/`set`. Slot-filling (`...`) for conversational inputs. Output capture into variables. Correct type mapping for action I/O (use `object` + `complex_data_type_name` for SObjects and custom Lightning types). |
| Deployment Readiness | 10 | Valid `default_agent_user`. `developer_name` matches folder. `bundle-meta.xml` present with `<bundleType>AGENT</bundleType>`. Linked variables for service agents (`EndUserId`, `RoutableId`, `ContactId`). |

## Score Interpretation

| Score | Meaning | Action |
|-------|---------|--------|
| 90-100 | Production-ready | Deploy with confidence |
| 75-89 | Good with minor issues | Fix noted items, then deploy |
| 60-74 | Needs work | Address structural issues before deploy |
| Below 60 | BLOCK | Major rework required |

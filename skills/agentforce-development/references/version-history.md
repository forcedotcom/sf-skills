# Version History

Skill version changelog for agentforce-development.

---

## Current Skill (agentforce-development)

| Version | Date | Changes |
|---------|------|---------|
| 0.4.8 | 2026-03-17 | **Agent access guide + merge cleanup**: Adopted `agent-access-guide.md` from sf-permissions (import rules applied). Routed post-activation access step in Create and Deploy domains. Merged `preview-test-loop.md` content (jq trace diagnostics, fix strategies table, context variable limitations, utterance derivation) into `agent-validation-and-debugging.md`. Deleted orphaned `preview-test-loop.md`. Added custom object scanning guidance to Agent Spec creation. Refined post-action output field instructions. |
| 0.4.7 | 2026-03-15 | **Post-action session state fix**: Added explicit post-action instructions to prevent session state corruption by specifying output fields the agent must reference. Driven by T02 run-2026-03-15-vc-02 finding. |
| 0.4.6 | 2026-03-15 | **USER_MODE P0-1 fix**: Added static vs. dynamic SOQL guidelines to backing logic sections in `agent-design-and-spec-creation.md` and invocable Apex template. `AccessLevel.USER_MODE` required for dynamic SOQL. Added "Rules That Always Apply" cardinal rules block to SKILL.md (`--json` first, diagnose before fix, spec approval gate). |
| 0.4.5 | 2026-03-15 | **Full editorial pass + spec approval gate**: Conciseness pass across all 9 SKILL.md domains. Added spec approval hard gate (user must approve Agent Spec before implementation). Added `filter_from_agent` output visibility to Agent Spec template. Restructured Agent Spec inputs/outputs sections. Step 8 redirect to Diagnose Behavioral Issues workflow. |
| 0.4.4 | 2026-03-13 | **Staging + cleanup**: Moved unmerged reference files to `staging/` folder. Clarified live actions command syntax. Refined `agent-user-setup.md` license requirements and USER_MODE documentation. |
| 0.4.3 | 2026-03-12 | **sf-skills merge: production-gotchas + new domain**: Added "Diagnose Production Issues" task domain to SKILL.md (9 domains total). Routed `production-gotchas.md` as primary reference. Added `production-gotchas.md` as secondary reference in Diagnose Compilation (reserved keywords trigger). Added `WITH USER_MODE` object permissions warning to `agent-user-setup.md` Section 6.2. Archived orphan `agent-user-setup-and-perms.md`. Fixed stale SKILL.md reference (Section 2 → Section 6.2). |
| 0.4.2 | 2026-03-12 | **sf-skills merge: known-issues + one-at-a-time deploy**: Integrated `known-issues.md` into 6 of 8 SKILL.md domains with domain-specific loading triggers. Added one-at-a-time Apex stub deploy instruction to SKILL.md Create/Modify domains, `agent-design-and-spec-creation.md`, and `salesforce-cli-for-agents.md`. Moved Issue 16 (`connections:` → `connection messaging:`) to Resolved. |
| 0.4.0 | 2026-03-11 | **T03 test run + type mapping restructure**: Restructured Section 5 type mapping in `agent-design-and-spec-creation.md` into Primitive + Complex tables keyed by `target` type. Added steps 10 (Activate) and 11 (Verify published agent) to Create, Modify, and Deploy domains. |
| 0.3.2 | 2026-03-10 | **T02 post-fix run**: Platform-injected `show_command` tool diagnostic pattern added to `agent-validation-and-debugging.md`. Post-publish preview language strengthened in SKILL.md. |
| 0.3.0 | 2026-03-10 | **T02 first run + test framework**: Created testing framework (README, run structure, scoring rubric). First T02 run: 13/13 SUCCESS. |
| 0.2.0 | 2026-03-09 | **T01 first run**: Created T01 test scenario. First end-to-end test of skill. Identified `agent_type` inference gap. |
| 0.1.0 | 2026-03-08 | **Initial skill**: SKILL.md router with 8 task domains. 7 reference files. Agent Spec template. Asset library. |


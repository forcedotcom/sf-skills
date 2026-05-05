---
name: <SKILL_NAME>
description: "<PRIMARY_PURPOSE>. TRIGGER when: <users mention METADATA_TYPE_NAMES,
  FILE_EXTENSIONS, or ask to ACTION_VERBS — include 5+ specific trigger phrases and
  implicit contexts where the user may not use the exact domain term>.
  SKIP when: <EXCLUSION_TRIGGERS with delegation targets>.
  Always use this skill for any <DOMAIN> metadata work."
license: LICENSE.txt has complete terms
metadata:
  version: "1.0"
  stage: Draft
  related-skills: "<skill1>, <skill2>"
  author: "<team-name>"
  last_updated: "<YYYY-MM-DD>"
  compatibility: "<REQUIRED_TOOLS_AND_ENVIRONMENT>"
allowed-tools: <Bash Read Write — list only the tools the skill needs>
---

# <Skill Title>

<1-3 sentence overview: what this skill does and why it exists.>

## Scope

- **In scope**: <what this skill handles>
- **Out of scope**: <what this skill does NOT handle — delegate to other skills>

---

## Clarifying Questions

<!-- Questions the agent should ask before generating. Only include questions
     where the wrong assumption leads to deployment failure or significant rework. -->

Before generating, confirm with the user if not already clear:

- <Question 1 — most critical information needed>
- <Question 2 — type or subtype selection>
- <Question 3 — constraint-affecting detail>
- <Question 4 — relationship or dependency info>

---

## Required Inputs

Gather or infer before proceeding:

- <Input 1>: <description and how to obtain>
- <Input 2>: <description and how to obtain>
- <Input 3>: <description and how to obtain>

Defaults unless specified:
- <Default 1>
- <Default 2>

If the user provides a clear, complete request, generate immediately without unnecessary back-and-forth.

---

## Workflow

All steps are sequential. Do not skip or reorder. If blocked, stop and ask for missing context.

1. **<Step name>**
   - <Action to take>
   - <Expected outcome>

2. **Read the template** — load `assets/<template-file>` before generating.

3. **<Step name>**
   - <Action to take>
   - For <specific sub-topic>, read `references/<topic>.md`.

4. **<Step name>**
   - <Action to take>
   - Compare output against `examples/<example-file>`.

---

## Rules / Constraints

<!-- Short table. If > 15 rows, move extras to references/. -->

| Constraint | Rationale |
|-----------|-----------|
| <Rule 1> | <Why this matters> |
| <Rule 2> | <Why this matters> |

---

## Gotchas

<!-- Short table — max 10 rows. Common pitfalls and fixes. -->

| Issue | Resolution |
|-------|------------|
| <Problem 1> | <How to fix it> |
| <Problem 2> | <How to fix it> |

---

## Output Expectations

Deliverables:
- <File 1>: `<path pattern>`
- <File 2>: `<path pattern>`

File structure follows the template in `assets/<template-file>`.

---

## Cross-Skill Integration

<!-- When to delegate to other skills. Remove section if not applicable. -->

| Need | Delegate to |
|------|-------------|
| <Need 1> | `<other-skill>` skill |
| <Need 2> | `<other-skill>` skill |

---

## Reference File Index

<!-- MANDATORY if any assets/, references/, or examples/ files exist. -->
<!-- Map every subdirectory file to the specific scenario that needs it. -->

| File | When to read |
|------|-------------|
| `assets/<template-file>` | Before generating — use as the starting structure |
| `references/<topic>.md` | When handling <specific scenario> |
| `examples/<example-file>` | To verify generated output matches expected format |

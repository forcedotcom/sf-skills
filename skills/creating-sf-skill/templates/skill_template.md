---
name: <SKILL_NAME>
description: "<DESCRIPTION — 20+ words, <= 1024 chars, must contain 'use'. Include TRIGGER when and DO NOT TRIGGER when clauses.>"
license: LICENSE.txt has complete terms
metadata:
  version: "1.0"
  stage: Draft
---

# <Skill Title>

<1-3 sentence overview: what this skill does and why it exists.>

## Scope

- **In scope**: <what this skill handles>
- **Out of scope**: <what this skill does NOT handle — delegate to other skills>

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

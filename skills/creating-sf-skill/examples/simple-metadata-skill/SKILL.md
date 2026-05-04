---
name: generating-validation-rule
description: "Create and update Salesforce validation rules for any standard or custom object. Use when the user asks to add a validation rule, enforce field requirements, prevent invalid data entry, or implement record-level business logic constraints. TRIGGER when: user says validation rule, field validation, required field check, data constraint, record validation, prevent invalid data. DO NOT TRIGGER when: user asks about Flow validation or Apex validation logic — delegate to generating-flow or generating-apex."
metadata:
  version: "1.0"
  stage: Draft
  license: LICENSE.txt has complete terms
---

# Generating Validation Rules

Create validation rules that enforce business logic at the record level.

## Scope

- **In scope**: Creating new validation rules, updating existing rules, formula syntax,
  error message placement, activation/deactivation.
- **Out of scope**: Flow-based validation (use `generating-flow`), Apex triggers for
  complex validation (use `generating-apex`).

## Required Inputs

- Target object (standard or custom)
- Business rule to enforce (in plain language)
- Error message text
- Error location (top of page or specific field)

Defaults:
- Active: true
- Description: auto-generated from the business rule

## Workflow

1. **Identify the object** — confirm the API name of the target object.
2. **Understand the rule** — translate the business requirement into a boolean formula.
3. **Check existing rules** — look for overlapping validation rules on the same object.
4. **Read the metadata template** — load `./assets/validation_rule_template.xml` before generating.
5. **Write the formula** — the formula must evaluate to `TRUE` when the data is **invalid**.
   For common formula patterns, read `./references/formula_patterns.md`.
6. **Set error message** — clear, user-friendly message explaining what's wrong and how to fix it.
7. **Create metadata file** — generate the `.validationRule-meta.xml` using the template structure.
   Compare against `./examples/require_email_on_contact.xml` for expected output format.
8. **Syntax check** — verify the formula compiles (field API names, function syntax).
9. **Edge case review** — test with null values, blank strings, boundary conditions.

## Rules

| Constraint | Rationale |
|-----------|-----------|
| Formula evaluates to TRUE on invalid data | Salesforce convention — TRUE = error |
| Use API names, not labels | Labels change; API names are stable |
| Handle null fields with `ISBLANK()` | Prevent null pointer errors |
| Use `PRIORVALUE()` only in update context | Not available on insert |

## Gotchas

| Issue | Resolution |
|-------|------------|
| Rule fires on record types it shouldn't | Add `RecordType.DeveloperName` check to formula |
| Rule blocks data migration/bulk loads | Add bypass via Custom Permission or Custom Metadata |
| `ISCHANGED()` always false on insert | Guard with `NOT(ISNEW())` before using `ISCHANGED()` |
| Formula too long (> 5000 chars) | Split into multiple rules or use a helper formula field |
| Error on wrong field | Verify field API name in `errorConditionFormula` attribute |

## Output Expectations

Deliverables per validation rule:
- `<ObjectName>.validationRule-meta.xml`

File structure follows the template in `./assets/validation_rule_template.xml`.

## Cross-Skill Integration

| Need | Delegate to |
|------|-------------|
| Complex multi-object validation | `generating-apex` (trigger-based) |
| Flow-based validation with user prompts | `generating-flow` |
| Custom object creation | `generating-custom-object` |
| Field creation for formula references | `generating-custom-field` |

## Reference File Index

| File | When to read |
|------|-------------|
| `./assets/validation_rule_template.xml` | Before generating any validation rule metadata file |
| `./references/formula_patterns.md` | When writing the formula — common patterns and functions |
| `./examples/require_email_on_contact.xml` | To verify generated output matches expected format |

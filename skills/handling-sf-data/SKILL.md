---
name: handling-sf-data
description: "Salesforce data operations with 130-point scoring. Use this skill to create, update, delete, bulk import/export, generate test data, and clean up org records using sf CLI and anonymous Apex. TRIGGER when: user creates test data, performs bulk import/export, uses sf data CLI commands, needs data factory patterns for Apex tests, or needs to seed/clean records in a Salesforce org. DO NOT TRIGGER when: SOQL query writing only (use querying-soql), Apex test execution (use running-apex-tests), or metadata deployment (use deploying-sf-metadata)."
license: LICENSE.txt has complete terms
metadata:
  version: "1.1"
---

# Salesforce Data Operations Expert (handling-sf-data)

Use this skill when the user needs **Salesforce data work**: record CRUD, bulk import/export, test data generation, cleanup scripts, or data factory patterns for validating Apex, Flow, or integration behavior.

## When This Skill Owns the Task

Use `handling-sf-data` when the work involves:
- `sf data` CLI commands
- record creation, update, delete, upsert, export, or tree import/export
- realistic test data generation
- bulk data operations and cleanup
- Apex anonymous scripts for data seeding / rollback

Delegate elsewhere when the user is:
- writing SOQL only → [querying-soql](../querying-soql/SKILL.md)
- running or repairing Apex tests → [running-apex-tests](../running-apex-tests/SKILL.md)
- deploying metadata first → [deploying-sf-metadata](../deploying-sf-metadata/SKILL.md)
- creating or modifying custom objects / fields → [generating-custom-object](../generating-custom-object/SKILL.md) or [generating-custom-field](../generating-custom-field/SKILL.md)

---

## Important Mode Decision

Confirm which mode the user wants:

| Mode | Use when |
|---|---|
| Script generation | they want reusable `.apex`, CSV, or JSON assets without touching an org yet |
| Remote execution | they want records created / changed in a real org now |

Do not assume remote execution if the user may only want scripts.

---

## Required Context to Gather First

Ask for or infer:
- target object(s)
- org alias, if remote execution is required
- operation type: query, create, update, delete, upsert, import, export, cleanup
- expected volume
- whether this is test data, migration data, or one-off troubleshooting data
- any parent-child relationships that must exist first

---

## Core Operating Rules

- `handling-sf-data` acts on **remote org data** unless the user explicitly wants local script generation.
- Objects and fields must already exist before data creation.
- For automation testing, prefer **251+ records** when bulk behavior matters.
- Plan cleanup before creating large or noisy datasets — untracked records accumulate across runs and pollute org state.
- Use synthetic, non-identifying data in test records — real PII creates compliance risk and cannot be safely removed after bulk import.
- Prefer **CLI-first** for straightforward CRUD; use anonymous Apex when the operation truly needs server-side orchestration.

If metadata is missing, stop and hand off to:
- [generating-custom-object](../generating-custom-object/SKILL.md) or [generating-custom-field](../generating-custom-field/SKILL.md) to create the missing schema, then [deploying-sf-metadata](../deploying-sf-metadata/SKILL.md) to deploy it before retrying the data operation

---

## Recommended Workflow

### 1. Verify prerequisites
Confirm object / field availability, org auth, and required parent records.

### 2. Run describe-first pre-flight validation when schema is uncertain
Before creating or updating records, use object describe data to validate:
- required fields
- createable vs non-createable fields
- picklist values
- relationship fields and parent requirements

See [references/sf-cli-data-commands.md](references/sf-cli-data-commands.md) for the `sf sobject describe` command and jq filter patterns for inspecting fields, picklist values, and createable constraints.

### 3. Choose the smallest correct mechanism
| Need | Default approach |
|---|---|
| small one-off CRUD | `sf data` single-record commands |
| large import/export | Bulk API 2.0 via `sf data ... bulk` |
| parent-child seed set | tree import/export |
| reusable test dataset | factory / anonymous Apex script |
| reversible experiment | cleanup script or savepoint-based approach |

### 4. Execute or generate assets
Use the built-in templates under `assets/` when they fit:
- `assets/factories/`
- `assets/bulk/`
- `assets/cleanup/`
- `assets/soql/`
- `assets/csv/`
- `assets/json/`

### 5. Verify results
Check counts, relationships, and record IDs after creation or update.

### 6. Apply a bounded retry strategy
If creation fails:
1. try the primary CLI shape once
2. retry once with corrected parameters
3. re-run describe / validate assumptions
4. pivot to a different mechanism or provide a manual workaround

Do **not** repeat the same failing command indefinitely.

### 7. Leave cleanup guidance
Provide exact cleanup commands or rollback assets whenever data was created.

---

## High-Signal Rules

### Bulk safety
- use bulk operations for large volumes
- test automation-sensitive behavior with 251+ records where appropriate
- avoid one-record-at-a-time patterns for bulk scenarios

### Data integrity
- include required fields
- validate picklist values before creation
- verify parent IDs and relationship integrity
- account for validation rules and duplicate constraints
- exclude non-createable fields from input payloads

### Cleanup discipline
Prefer one of:
- delete-by-ID
- delete-by-pattern
- delete-by-created-date window
- rollback / savepoint patterns for script-based test runs

---

## Common Failure Patterns

| Error | Likely cause | Default fix direction |
|---|---|---|
| `INVALID_FIELD` | wrong field API name or FLS issue | verify schema and access |
| `REQUIRED_FIELD_MISSING` | mandatory field omitted | include required values from describe data |
| `INVALID_CROSS_REFERENCE_KEY` | bad parent ID | create / verify parent first |
| `FIELD_CUSTOM_VALIDATION_EXCEPTION` | validation rule blocked the record | use valid test data or adjust setup |
| invalid picklist value | guessed value instead of describe-backed value | inspect picklist values first |
| non-writeable field error | field is not createable / updateable | remove it from the payload |
| bulk limits / timeouts | wrong tool for the volume | switch to bulk / staged import |

---

## Output Format

When finishing, report in this order:
1. **Operation performed**
2. **Objects and counts**
3. **Target org or local artifact path**
4. **Record IDs / output files**
5. **Verification result**
6. **Cleanup instructions**

Suggested shape:

```text
Data operation: <create / update / delete / export / seed>
Objects: <object + counts>
Target: <org alias or local path>
Artifacts: <record ids / csv / apex / json files>
Verification: <passed / partial / failed>
Cleanup: <exact delete or rollback guidance>
```

---

## Cross-Skill Integration

| Need | Delegate to | Reason |
|---|---|---|
| create missing custom objects | [generating-custom-object](../generating-custom-object/SKILL.md) | schema must exist before data operations |
| create missing custom fields | [generating-custom-field](../generating-custom-field/SKILL.md) | field-level schema must exist before data creation |
| run bulk-sensitive Apex validation | [running-apex-tests](../running-apex-tests/SKILL.md) | test execution and coverage |
| deploy missing schema first | [deploying-sf-metadata](../deploying-sf-metadata/SKILL.md) | metadata readiness |
| implement production Apex logic consuming the data | [generating-apex](../generating-apex/SKILL.md) | Apex class / trigger authoring |
| implement Flow logic consuming the data | [generating-flow](../generating-flow/SKILL.md) | Flow authoring and automation |

---

## Reference Map

### Start here
- [references/sf-cli-data-commands.md](references/sf-cli-data-commands.md)
- [references/test-data-best-practices.md](references/test-data-best-practices.md)
- [references/orchestration.md](references/orchestration.md)
- [references/test-data-patterns.md](references/test-data-patterns.md)
- [references/test-data-factory-usage.md](references/test-data-factory-usage.md)

### Query / bulk / cleanup
- [references/soql-relationship-guide.md](references/soql-relationship-guide.md)
- [references/relationship-query-examples.md](references/relationship-query-examples.md)
- [references/bulk-operations-guide.md](references/bulk-operations-guide.md)
- [references/cleanup-rollback-guide.md](references/cleanup-rollback-guide.md)
- [references/cleanup-rollback-example.md](references/cleanup-rollback-example.md)

### Examples / limits
- [references/crud-workflow-example.md](references/crud-workflow-example.md)
- [references/bulk-testing-example.md](references/bulk-testing-example.md)
- [references/anonymous-apex-guide.md](references/anonymous-apex-guide.md)
- [references/governor-limits-reference.md](references/governor-limits-reference.md)

### Validation scripts
- [scripts/soql_validator.py](scripts/soql_validator.py) — validate SOQL queries before execution
- [scripts/validate_data_operation.py](scripts/validate_data_operation.py) — pre-flight check for data operations (required fields, picklist values, createable fields)

### Asset templates
- `assets/factories/` — Apex test data factory scripts (account, contact, opportunity, lead, user, etc.)
- `assets/bulk/` — Bulk API 2.0 Apex templates (insert 200, 500, 10000 records; upsert by external ID)
- `assets/cleanup/` — Cleanup and rollback scripts (delete by name, date, pattern; transaction rollback)
- `assets/soql/` — SOQL query templates (aggregate, subquery, parent-to-child, child-to-parent, polymorphic)
- `assets/csv/` — CSV import templates for Account, Contact, Opportunity, custom objects
- `assets/json/` — JSON tree import templates (account-contact, account-opportunity, full hierarchy)

---

## Score Guide

| Score | Meaning |
|---|---|
| 117+ | strong production-safe data workflow |
| 104–116 | good operation with minor improvements possible |
| 91–103 | acceptable but review advised |
| 78–90 | partial / risky patterns present |
| < 78 | blocked until corrected |

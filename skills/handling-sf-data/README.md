# handling-sf-data

Salesforce data operations skill for Claude Code. Create, validate, bulk-load, clean up, and troubleshoot org data with a describe-first workflow.

## Features

- **CRUD Operations**: Create, read, update, delete records via sf CLI
- **Describe-First Validation**: Inspect required fields, picklists, and createable fields before data creation
- **CLI-First Test Data**: Prefer `sf data` commands for straightforward seed data
- **Bulk Operations**: Import/export via Bulk API 2.0
- **Record Tracking & Cleanup**: Savepoint/rollback, cleanup scripts, delete-by-pattern workflows
- **130-Point Validation**: Automated scoring across 7 categories

## Installation

Add the skill to your Cursor project by placing the `handling-sf-data` directory under your `skills/` folder and enabling it in your agent configuration.

## Usage

Invoke the skill:
```
Skill(skill="handling-sf-data")
Request: "Create 251 test Account records with varying Industries for trigger testing in org dev"
```

### Common Operations

| Operation | Example Request |
|-----------|-----------------|
| Query | "Query all Accounts with related Contacts in org dev" |
| Create | "Create 10 test Opportunities at various stages" |
| Bulk Insert | "Insert 500 accounts from accounts.csv" |
| Update | "Update Account 001xxx with new Industry" |
| Delete | "Delete all test records with Name LIKE 'Test%'" |
| Cleanup | "Generate cleanup script for all records created today" |

## Recommended workflow

1. Describe the target object when schema constraints are uncertain
2. Validate required fields, picklist values, and createable fields
3. Choose CLI, tree import, bulk import, or anonymous Apex intentionally
4. Verify results and provide cleanup instructions

## Validation Scoring (130 Points)

| Category | Points | Focus |
|----------|--------|-------|
| Query Efficiency | 25 | SOQL selectivity, indexed fields, no N+1 |
| Bulk Safety | 25 | Governor limits, batch sizing |
| Data Integrity | 20 | Required fields, relationships |
| Security & FLS | 20 | Field-level security, no PII |
| Test Patterns | 15 | 200+ records, edge cases |
| Cleanup & Isolation | 15 | Rollback, cleanup scripts |
| Documentation | 10 | Purpose, expected outcomes |

## Cross-Skill Integration

### With deploying-metadata
```
Skill(skill="deploying-metadata")
Request: "Describe Invoice__c in org dev - show all fields"
```
Then use handling-sf-data with accurate field names and permitted values.

### From generating-apex / generating-flow
```
Skill(skill="handling-sf-data")
Request: "Create 251 test Accounts to trigger AccountTrigger bulk testing"
```

## Directory Structure

```
handling-sf-data/
├── SKILL.md                   # Main skill prompt
├── assets/
│   ├── factories/             # Apex test data factories
│   ├── soql/                  # SOQL query templates
│   ├── bulk/                  # Bulk operation templates
│   ├── csv/                   # CSV import templates
│   ├── json/                  # JSON tree templates
│   └── cleanup/               # Cleanup scripts
├── scripts/                   # Pre-flight validation scripts
└── references/                # Documentation and examples
```

## Key documentation

- [SKILL.md](SKILL.md) - Full workflow and orchestration guidance
- [references/test-data-best-practices.md](references/test-data-best-practices.md) - Describe-first validation and retry strategy
- [references/sf-cli-data-commands.md](references/sf-cli-data-commands.md) - sf CLI command patterns
- [references/cleanup-rollback-guide.md](references/cleanup-rollback-guide.md) - Cleanup strategies

## sf CLI Commands Wrapped

| Operation | Command |
|-----------|---------|
| Query | `sf data query --query "..." --target-org [alias]` |
| Create | `sf data create record --sobject [Object] --values "..."` |
| Update | `sf data update record --sobject [Object] --record-id [Id] --values "..."` |
| Delete | `sf data delete record --sobject [Object] --record-id [Id]` |
| Bulk Import | `sf data import bulk --file [csv] --sobject [Object]` |
| Bulk Delete | `sf data delete bulk --file [csv] --sobject [Object]` |
| Tree Export | `sf data export tree --query "..." --output-dir [dir]` |
| Tree Import | `sf data import tree --files [json]` |
| Apex Run | `sf apex run --file [script.apex]` |

## Requirements

- sf CLI v2
- Target Salesforce org (sandbox or production)
- Claude Code with skill plugins enabled

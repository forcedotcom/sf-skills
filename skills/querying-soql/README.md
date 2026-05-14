# querying-soql

Salesforce SOQL query generation, optimization, and analysis skill with 100-point scoring. Convert natural language into performant SOQL and validate queries for security, selectivity, and governor-limit awareness.

## Features

- **Natural Language to SOQL**: Convert requests into executable queries
- **Query Optimization**: Improve selectivity, LIMIT usage, and field selection
- **Relationship Queries**: Parent-child, child-parent, and polymorphic patterns
- **Security Guidance**: `WITH USER_MODE`, `WITH SECURITY_ENFORCED`, and Apex-safe usage
- **100-Point Scoring**: Performance, correctness, security, and readability checks

## Quick Start

### 1. Invoke the skill

```
Skill: querying-soql
Request: "Find Accounts with open Opportunities created this quarter"
```

### 2. Typical use cases

- Generate SOQL from plain-English requirements
- Optimize slow or non-selective queries
- Build aggregates and relationship queries
- Validate queries before using them in Apex or CLI workflows

## Documentation

- [SKILL.md](SKILL.md) - Core workflow and optimization guidance
- [references/query-optimization.md](references/query-optimization.md) - Selectivity and performance tuning
- [references/soql-syntax-reference.md](references/soql-syntax-reference.md) - Syntax, relationships, and aggregates
- [references/selector-patterns.md](references/selector-patterns.md) - Reusable Apex selector patterns
- [references/cli-commands.md](references/cli-commands.md) - sf CLI query execution examples

## Related Skills

- `handling-sf-data` - For data creation/import/export workflows
- `generating-apex` - For inline SOQL inside Apex code
- `running-apex-tests` - For validating query behavior in tests

---
name: exploring-graphql-schema
description: Explore the Salesforce GraphQL schema via grep-only lookups. Use before generating any GraphQL query — schema exploration must complete first.
paths:
  - "**/*.ts"
  - "**/*.tsx"
  - "**/*.graphql"
---

# Salesforce GraphQL Schema Exploration

Guidance for AI agents working with the Salesforce GraphQL API schema. **GREP ONLY** — the schema file is very large (~265,000+ lines). All lookups MUST use grep; do NOT open, read, stream, or parse the file.

## Schema File Location

**Location:** `schema.graphql` at the **SFDX project root** (NOT inside the webapp dir). All grep commands **must be run from the project root** where `schema.graphql` lives.

> ⚠️ **Important (Access Policy - GREP ONLY)**: Do NOT open, view, stream, paginate, or parse the schema with any tool other than grep. All lookups MUST be done via grep using anchored patterns with minimal context as defined below.

If the file is not present, generate it by running (from the **webapp dir**, not the project root):

```bash
# Run from webapp dir (force-app/main/default/webapplications/<app-name>/)
npm run graphql:schema
```

**BEFORE generating any GraphQL query, you MUST:**

1. **Check if schema exists**: Look for `schema.graphql` in the **SFDX project root**
2. **If schema is missing**:
   - `cd` to the **webapp dir** and run `npm run graphql:schema` to download it
   - Wait for the command to complete successfully
   - Then proceed with grep-only lookups as defined below.
3. **If schema exists**: Proceed with targeted searches as described below

> ⚠️ **DO NOT** generate GraphQL queries without first having access to the schema. Standard field assumptions may not match the target org's configuration.

## Schema Structure Overview

Main entry points: `Query { uiapi }` for reads; `Mutation { uiapi(input: ...) }` for creates/updates/deletes. Record queries use `uiapi.query.<ObjectName>`.

## Allowed Lookups (grep-only)

Use ONLY these grep commands to locate specific definitions in schema.graphql. Do not use editors (VS Code/vim/nano), cat/less/more/head/tail, or programmatic parsers (node/python/awk/sed/jq).

- Always include:
  - `-n` (line numbers) and `-E` (extended regex)
  - Anchors (`^`) and word boundaries (`\b`)
  - Minimal context with `-A N` (prefer the smallest N that surfaces the needed lines)

### 1. Find Available Fields for a Record Type

Search for `type <ObjectName> implements Record` to find all queryable fields:

```bash
# Example: Find Account fields (anchored, minimal context)
grep -nE '^type[[:space:]]+Account[[:space:]]+implements[[:space:]]+Record\b' ./schema.graphql -A 60
```

### 2. Find Filter Options for a Record Type

Search for `input <ObjectName>_Filter` to find filterable fields and operators:

```bash
# Example: Find Account filter options (anchored)
grep -nE '^input[[:space:]]+Account_Filter\b' ./schema.graphql -A 40
```

### 3. Find OrderBy Options

Search for `input <ObjectName>_OrderBy` for sorting options:

```bash
# Example: Find Account ordering options (anchored)
grep -nE '^input[[:space:]]+Account_OrderBy\b' ./schema.graphql -A 30
```

### 4. Find Mutation Operations

Search for operations in `UIAPIMutations`:

```bash
# Example: Find Account mutations (extended regex)
grep -nE 'Account.*(Create|Update|Delete)' ./schema.graphql
```

### 5. Find Input Types for Mutations

Search for `input <ObjectName>CreateInput` or `input <ObjectName>UpdateInput`:

```bash
# Example: Find Account create input (anchored)
grep -nE '^input[[:space:]]+AccountCreateInput\b' ./schema.graphql -A 30
```

## Common Operator Types

- **StringOperators**: `eq`, `ne`, `like`, `lt`, `gt`, `lte`, `gte`, `in`, `nin`
- **OrderByClause**: `order: ResultOrder` (ASC/DESC), `nulls: NullOrder` (FIRST/LAST)

## Field Value Wrappers

Salesforce GraphQL returns field values wrapped in typed objects:

| Wrapper Type    | Access Pattern                     |
| --------------- | ---------------------------------- |
| `StringValue`   | `FieldName { value }`              |
| `IntValue`      | `FieldName { value }`              |
| `BooleanValue`  | `FieldName { value }`              |
| `DateTimeValue` | `FieldName { value displayValue }` |
| `PicklistValue` | `FieldName { value displayValue }` |
| `CurrencyValue` | `FieldName { value displayValue }` |

## Agent Workflow for Building Queries (grep-only)

**Pre-requisites (MANDATORY):**

- [ ] Verified `schema.graphql` exists in the **SFDX project root**
- [ ] If missing, ran `npm run graphql:schema` from the **webapp dir** and waited for completion
- [ ] Confirmed connection to correct Salesforce org (if downloading fresh schema)

**Workflow Steps:**

1. **Identify the target object** (e.g., Account, Contact, Opportunity)
2. **Run the "Find Available Fields" grep command** for your object (copy only the field names visible in the grep output; do not open the file)
3. **Run the "Find Filter Options" grep command** (`<Object>_Filter`) to understand filtering options
4. **Run the "Find OrderBy Options" grep command** (`<Object>_OrderBy`) for sorting capabilities
5. **Build the query** following the patterns in the `generating-graphql-read-query` or `generating-graphql-mutation-query` skill using only values returned by grep
6. **Validate field names** using grep matches (case-sensitive). Do not open or parse the file beyond grep.

## Tips for Agents

- **Always verify field names** by running the specific grep commands; do not open the schema file
- **Use grep with anchors and minimal -A context** to explore the schema efficiently—never read or stream the file
- **Check relationships** by looking for `parentRelationship` and `childRelationship` comments in type definitions
- **Look for Connection types** (e.g., `AccountConnection`) via grep to understand pagination structure
- **Custom objects** end with `__c` (e.g., `CustomObject__c`)
- **Custom fields** also end with `__c` (e.g., `Custom_Field__c`)

## Forbidden Operations

To prevent accidental large reads, the following are prohibited for schema.graphql:

- Opening in any editor (VS Code, vim, nano)
- Using cat, less, more, head, or tail
- Programmatic parsing (node, python, awk, sed, jq)
- Streaming or paginating through large portions of the file

If any of the above occurs, stop and replace the action with one of the Allowed Lookups (grep-only).

## Output Minimization

- Prefer precise, anchored patterns with word boundaries
- Use the smallest `-A` context that surfaces required lines
- If results are noisy, refine the regex rather than increasing context

## Related Skills

- For generating read queries, invoke the `generating-graphql-read-query` skill
- For generating mutation queries, invoke the `generating-graphql-mutation-query` skill

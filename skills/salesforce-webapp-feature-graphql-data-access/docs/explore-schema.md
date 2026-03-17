# GraphQL Schema Reference

This document provides guidance for AI agents working with the Salesforce GraphQL API schema in this project.

## Schema File Location

**The complete GraphQL schema is located at: `@schema.graphql`** (in the project root)

> ⚠️ **Important**: The schema file is very large (~265,000+ lines). Do NOT read it entirely. Instead, use targeted searches to find specific types, fields, or operations.

If the file is not present, generate it by running:

```bash
npm run graphql:schema
```

## Required Pre-Flight Check

**BEFORE generating any GraphQL query, you MUST:**

1. **Check if schema exists**: Look for `schema.graphql` in the project root
2. **If schema is missing**:
   - Run `npm run graphql:schema` to download it
   - Wait for the command to complete successfully
   - Then proceed with schema exploration
3. **If schema exists**: Proceed with targeted searches as described below

> ⚠️ **DO NOT** generate GraphQL queries without first having access to the schema. Standard field assumptions may not match the target org's configuration.

## Schema Structure Overview

The schema follows the Salesforce GraphQL Wire Adapter pattern with these main entry points:

### Query Entry Point

```graphql
type Query {
  uiapi: UIAPI!
}
```

### UIAPI Structure

```graphql
type UIAPI {
  query: RecordQuery! # For querying records
  aggregate: RecordQueryAggregate! # For aggregate queries
  objectInfos: [ObjectInfo] # For metadata
  relatedListByName: RelatedListInfo
}
```

### Mutation Entry Point

```graphql
type Mutation {
  uiapi(input: UIAPIMutationsInput): UIAPIMutations!
}
```

## How to Explore the Schema

When you need to build a GraphQL query, use these search patterns:

### 1. Find Available Fields for a Record Type

Search for `type <ObjectName> implements Record` to find all queryable fields:

```bash
# Example: Find Account fields
grep "^type Account implements Record" schema.graphql -A 50
```

### 2. Find Filter Options for a Record Type

Search for `input <ObjectName>_Filter` to find filterable fields and operators:

```bash
# Example: Find Account filter options
grep "^input Account_Filter" schema.graphql -A 30
```

### 3. Find OrderBy Options

Search for `input <ObjectName>_OrderBy` for sorting options:

```bash
# Example: Find Account ordering options
grep "^input Account_OrderBy" schema.graphql -A 20
```

### 4. Find Mutation Operations

Search for operations in `UIAPIMutations`:

```bash
# Example: Find Account mutations
grep "Account.*Create\|Account.*Update\|Account.*Delete" schema.graphql
```

### 5. Find Input Types for Mutations

Search for `input <ObjectName>CreateInput` or `input <ObjectName>UpdateInput`:

```bash
# Example: Find Account create input
grep "^input AccountCreateInput" schema.graphql -A 30
```

## Common Operator Types

### StringOperators (for text fields)

```graphql
input StringOperators {
  eq: String # equals
  ne: String # not equals
  like: String # pattern matching (use % as wildcard)
  lt: String # less than
  gt: String # greater than
  lte: String # less than or equal
  gte: String # greater than or equal
  in: [String] # in list
  nin: [String] # not in list
}
```

### OrderByClause

```graphql
input OrderByClause {
  order: ResultOrder # ASC or DESC
  nulls: NullOrder # FIRST or LAST
}
```

## Query Pattern Examples

### Basic Query Structure

All record queries follow this pattern:

```graphql
query {
  uiapi {
    query {
      <ObjectName>(
        first: Int           # pagination limit
        after: String        # pagination cursor
        where: <Object>_Filter
        orderBy: <Object>_OrderBy
      ) {
        edges {
          node {
            Id
            <Field> { value }
            # ... more fields
          }
        }
      }
    }
  }
}
```

### Example: Query Accounts with Filter

```graphql
query GetHighRevenueAccounts($minRevenue: Currency) {
  uiapi {
    query {
      Account(
        where: { AnnualRevenue: { gt: $minRevenue } }
        orderBy: { AnnualRevenue: { order: DESC } }
        first: 50
      ) {
        edges {
          node {
            Id
            Name {
              value
            }
            AnnualRevenue {
              value
            }
            Industry {
              value
            }
          }
        }
      }
    }
  }
}
```

### Mutation Pattern

```graphql
mutation CreateAccount($input: AccountCreateInput!) {
  uiapi(input: { AccountCreate: { input: $input } }) {
    AccountCreate {
      Record {
        Id
        Name {
          value
        }
      }
    }
  }
}
```

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

## Agent Workflow for Building Queries

**Pre-requisites (MANDATORY):**

- [ ] Verified `schema.graphql` exists in project root
- [ ] If missing, ran `npm run graphql:schema` and waited for completion
- [ ] Confirmed connection to correct Salesforce org (if downloading fresh schema)

**Workflow Steps:**

1. **Identify the target object** (e.g., Account, Contact, Opportunity)
2. **Search the schema** for the object type to discover available fields
3. **Search for filter input** (`<Object>_Filter`) to understand filtering options
4. **Search for orderBy input** (`<Object>_OrderBy`) for sorting capabilities
5. **Build the query** following the patterns above
6. **Validate field names** match exactly as defined in the schema (case-sensitive)

## Tips for Agents

- **Always verify field names** by searching the schema before generating queries
- **Use grep/search** to explore the schema efficiently—never read the entire file
- **Check relationships** by looking for `parentRelationship` and `childRelationship` comments in type definitions
- **Look for Connection types** (e.g., `AccountConnection`) to understand pagination structure
- **Custom objects** end with `__c` (e.g., `CustomObject__c`)
- **Custom fields** also end with `__c` (e.g., `Custom_Field__c`)

## Related Documentation

- For generating mutations and queries, see `generate-mutation-query.md`
- For generating read queries, see `generate-read-query.md`

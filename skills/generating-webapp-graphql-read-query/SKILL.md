---
name: generating-webapp-graphql-read-query
description: Generate Salesforce GraphQL read queries. Use when the query to generate is a read query. Schema exploration must complete first — invoke exploring-graphql-schema first.
paths:
  - "**/*.ts"
  - "**/*.tsx"
  - "**/*.graphql"
---

# Salesforce GraphQL Read Query Generation

**Triggering conditions**

1. Only if the schema exploration phase completed successfully (invoke `exploring-graphql-schema` first)
2. Only if the query to generate is a read query

## Schema Access Policy

> ⚠️ **GREP ONLY** — During query generation you may need to verify field names, types, or relationships. All schema lookups **MUST** use the grep-only commands defined in the `exploring-graphql-schema` skill. Do NOT open, read, stream, or parse `./schema.graphql` with any tool other than grep.

## Field-Level Security and @optional

Field-level security (FLS) restricts which fields different users can see. Use the `@optional` directive on Salesforce record fields when possible. The server omits the field when the user lacks access, allowing the query to succeed instead of failing. Apply `@optional` to scalar fields, value-type fields (e.g. `Name { value }`), parent relationships, and child relationships. Available in API v65.0+.

**Consuming code must defend against missing fields.** When a field is omitted due to FLS, it will be `undefined` (or absent) in the response. Use optional chaining (`?.`), nullish coalescing (`??`), and explicit null/undefined checks when reading query results. Never assume an optional field is present — otherwise the app may crash or behave incorrectly for users without field access.

```ts
// ✅ Defend against missing fields
const name = node.Name?.value ?? '';
const relatedName = node.RelationshipName?.Name?.value ?? 'N/A';

// ❌ Unsafe — will throw if field omitted due to FLS
const name = node.Name.value;
```

## Your Role

You are a GraphQL expert. Generate Salesforce-compatible read queries. Schema exploration must complete first. If the schema exploration has not been executed yet, you **MUST** run the full exploration workflow from the `exploring-graphql-schema` skill first, then return here for read query generation.

## Read Query Generation Workflow

Strictly follow the rules below when generating the GraphQL read query:

1. **No Proliferation** - Only generate for the explicitly requested fields, nothing else. Do NOT add fields the user did not ask for.
2. **Unique Query** - Leverage child relationships to query entities in one single query
3. **Navigate Entities** - Always use `relationshipName` to access reference fields and child entities
   1. **Exception** - if the `relationshipName` field is null, you can't navigate the related entity, and will have to return the `Id` itself
4. **Leverage Fragments** - Generate one fragment per possible type on polymorphic fields (field with `dataType="REFERENCE"` and more than one entry in `referenceToInfos` introspection attribute)
5. **Type Consistency** - Make sure variables used as query arguments and their related fields share the same GraphQL type. Verify types against grep output from the schema — do not assume types
6. **Type Enforcement** - Make sure to leverage field type information from introspection and GraphQL schema to generate field access
7. **Field Name Validation** - Every field name in the generated query **MUST** match a field confirmed via grep lookup in the schema. Do NOT guess or assume field names exist
8. **@optional for FLS** - Apply `@optional` on all Salesforce record fields when possible (see [Field-Level Security and @optional](#field-level-security-and-optional)). This lets the query succeed when the user lacks field-level access; the server omits inaccessible fields instead of failing
9. **Consuming code defense** - When generating or modifying code that consumes read query results, defend against missing fields (see [Field-Level Security and @optional](#field-level-security-and-optional)). Use optional chaining, nullish coalescing, and null/undefined checks — never assume optional fields are present
10. **Semi and anti joins** - Use the semi-join or anti-join templates to filter an entity with conditions on child entities
11. **Query Generation** - Use the [template](#read-query-template) to generate the query
12. **Output Format** - Use the [standalone](#read-standalone-default-output-format---clean-code-only)
13. **Lint Validation** - After writing the query to a file, run `npx eslint <file>` from the webapp dir to validate it against the schema. Fix any reported errors before proceeding. See [Lint Validation](#lint-validation) for details
14. **Test the Query** - Use the [Generated Read Query Testing](#generated-read-query-testing) workflow to test the generated query
    1. **Report First** - Always output the generated query in the proper output format BEFORE initiating any test

## Read Query Template

```graphql
query QueryName {
  uiapi {
    query {
      EntityName(
        # conditions here
      ) {
        edges {
          node {
            # Direct fields — use @optional for FLS resilience
            FieldName @optional { value }

            # Non-polymorphic reference (single type)
            RelationshipName @optional {
              Id
              Name { value }
            }

            # Polymorphic reference (multiple types)
            PolymorphicRelationshipName @optional {
              ...TypeAInfo
              ...TypeBInfo
            }

            # Child relationship (subquery)
            RelationshipName @optional (
              # conditions here
            ) {
              edges {
                node {
                  # fields
                }
              }
            }
          }
        }
      }
    }
  }
}

fragment TypeAInfo on TypeA {
  Id
  SpecificFieldA @optional { value }
}

fragment TypeBInfo on TypeB {
  Id
  SpecificFieldB @optional { value }
}
```

## Semi-Join and Anti-Join Condition Template

Semi-joins (resp. anti-joins) condition leverage parent-child relationships and allow filtering the parent entity using a condition on child entities.
This is a standard `where` condition, on the parent entity's `Id`, expressed using the `inq` (resp. `ninq`, i.e. not `inq`) operator. This operator accepts two attributes:

- The child entity camelcase name to apply the condition on, with a value expressing the condition
- The field name on the child entity containing the parent entity `Id`, which is the `fieldName` from the `childRelationships` information for the child entity
- If the only condition is related child entity existence, you can use an `Id: { ne: null }` condition

### Semi-Join Example - ParentEntity with at least one Matching ChildEntity

```graphql
query testSemiJoin {
  uiapi {
    query {
      ParentEntity(
        where: {
          Id: {
            inq: {
              ChildEntity: {
                # standard conditions here
                Name: { like: "test%" }
                Type: { eq: "some value" }
              }
              ApiName: "parentIdFieldInChild"
            }
          }
        }
      ) {
        edges {
          node {
            Id
            Name @optional {
              value
            }
          }
        }
      }
    }
  }
}
```

### Anti-Join Example - ParentEntity with no Matching ChildEntity

Same example as the [Semi-Join Example](#semi-join-example---parententity-with-at-least-one-matching-childentity), but replacing the `inq` operator by the `ninq` one.

## Read Standalone (Default) Output Format - CLEAN CODE ONLY

```javascript
const QUERY_NAME = `
  query GetData {
    # query here
  }
`;

const QUERY_VARIABLES = {
  // variables here
};
```

**❌ FORBIDDEN — Do NOT include any of the following:**

- Explanatory comments about the query (inline or surrounding)
- Field descriptions or annotations
- Additional text about what the query does
- Workflow step descriptions or summaries
- Comments like `// fetches...`, `// returns...`, `/* ... */`

**✅ ONLY output:**

- The raw query string constant
- The variables object constant
- Nothing else — no imports, no exports, no wrapper functions

## Lint Validation

After writing the generated query into a source file, validate it against the schema using the project's GraphQL ESLint setup:

```bash
# Run from webapp dir (force-app/main/default/webapplications/<app-name>/)
npx eslint <path-to-file-containing-query>
```

**How it works:** The ESLint config uses `@graphql-eslint/eslint-plugin` with its `processor`, which extracts GraphQL operations from `gql` template literals in `.ts`/`.tsx` files and validates the extracted `.graphql` virtual files against `schema.graphql`.

**Rules enforced:** `no-anonymous-operations`, `no-duplicate-fields`, `known-fragment-names`, `no-undefined-variables`, `no-unused-variables`

**On failure:** Fix the reported issues, re-run `npx eslint <file>` until clean, then proceed to testing.

> ⚠️ **Prerequisites**: The `schema.graphql` file must exist (invoke `exploring-graphql-schema` first) and project dependencies must be installed (`npm install`).

## Generated Read Query Testing

**Triggering conditions** — **ALL conditions must be true:**

1. The [Read Query Generation Workflow](#read-query-generation-workflow) completed with status `SUCCESS` and you have a generated query
2. The query is a read query
3. A non-manual method was used during schema exploration to retrieve introspection data

**Workflow**

1. **Report Step** - State the exact method you will use to test (e.g., `sf api request graphql` from the **project root**, Connect API, etc.) — this **MUST** match the method used during schema exploration
2. **Interactive Step** - Ask the user whether they want you to test the query using the proposed method
   1. **STOP and WAIT** for the user's answer. Do NOT proceed until the user responds. Do NOT assume consent.
3. **Test Query** - Only if the user explicitly agrees:
   1. Use `sf api request rest` to POST the query to the GraphQL endpoint:
      ```bash
      sf api request rest /services/data/v65.0/graphql \
        --method POST \
        --body '{"query":"query GetData { uiapi { query { EntityName { edges { node { Id } } } } } }"}'
      ```
   2. Replace `v65.0` with the API version of the target org
   3. Replace the `query` value with the generated read query string
   4. If the query uses variables, include them in the JSON body as a `variables` key
   5. Report the result as `SUCCESS` if the query executed without error, or `FAILED` if errors were returned
   6. An empty result set with no errors is `SUCCESS` — the query is valid, the org simply has no matching data
4. **Remediation Step** - If status is `FAILED`, use the [`FAILED` status handling workflows](#failed-status-handling-workflow)

### `FAILED` Status Handling Workflow

The query is invalid:

1. **Error Analysis** - Parse and categorize the specific error messages
2. **Root Cause Identification** - Use error message to identify the root cause:
   - **Syntax** - Error contains `invalid syntax`
   - **Validation** - Error contains `validation error`
   - **Type** - Error contains `VariableTypeMismatch` or `UnknownType`
3. **Targeted Resolution** - Depending on the root cause categorization
   - **Syntax** - Update the query using the error message information to fix the syntax errors
   - **Validation** - The field name is most probably invalid. Re-run the relevant grep command from the `exploring-graphql-schema` skill to verify the correct field name. If still unclear, ask the user for clarification and **STOP and WAIT** for their answer
   - **Type** - Use the error details and re-verify the type via grep lookup in the schema. Correct the argument type and adjust variables accordingly
4. **Test Again** - Resume the [query testing workflow](#generated-read-query-testing) with the updated query (increment and track attempt counter)
5. **Escalation Path** - If targeted resolution fails after 2 attempts, ask for additional details and restart the entire GraphQL workflow from the `exploring-graphql-schema` skill

## Related Skills

- Schema exploration: `exploring-graphql-schema` (must complete first)
- Mutation generation: `generating-graphql-mutation-query`

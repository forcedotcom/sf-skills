---
name: generating-webapp-graphql-mutation-query
description: Generate Salesforce GraphQL mutation queries. Use when the query to generate is a mutation query. Schema exploration must complete first — invoke exploring-graphql-schema first.
paths:
  - "**/*.ts"
  - "**/*.tsx"
  - "**/*.graphql"
---

# Salesforce GraphQL Mutation Query Generation

**Triggering conditions**

1. Only if the schema exploration phase completed successfully (invoke `exploring-graphql-schema` first)
2. Only if the query to generate is a mutation query

## Schema Access Policy

> ⚠️ **GREP ONLY** — During mutation generation you may need to verify field names, input types, or representations. All schema lookups **MUST** use the grep-only commands defined in the `exploring-graphql-schema` skill. Do NOT open, read, stream, or parse `./schema.graphql` with any tool other than grep.

## Your Role

You are a GraphQL expert. Generate Salesforce-compatible mutation queries. Schema exploration must complete first. If the schema exploration has not been executed yet, you **MUST** run the full exploration workflow from the `exploring-graphql-schema` skill first, then return here for mutation query generation.

## Mutation Queries General Information

The GraphQL engine supports `Create`, `Update`, and `Delete` operations. `Update` and `Delete` operate on Id-based entity identification. See the [mutation query schema](#mutation-query-schema) section.

## Mutation Query Generation Workflow

Strictly follow the rules below when generating the GraphQL mutation query:

1. **Input Fields Validation** - Validate that the set of fields validate [input field constraints](#mutation-queries-input-field-constraints). Verify every field name and type against grep output from the schema — do NOT guess or assume
2. **Output Fields Validation** - Validate that the set of fields used in the select part of the query validate the [output fields constraints](#mutation-queries-output-field-constraints)
3. **Type Consistency** - Make sure variables used as query arguments and their related fields share the same GraphQL type. Verify types via grep lookup — do NOT assume types
4. **Report Phase** - Use the [Mutation Query Report Template](#mutation-query-report-template) below to report on the previous validation phases
5. **Input Arguments** - `input` is the default name for the argument, unless otherwise specified
6. **Output Field** - For `Create` and `Update` operations, the output field is always named `Record`, and is of type EntityName
7. **Field Name Validation** - Every field name in the generated mutation **MUST** match a field confirmed via grep lookup in the schema. Do NOT guess or assume field names exist
8. **Query Generation** - Use the [mutation query](#mutation-query-templates) template and adjust it based on the selected operation
9. **Output Format** - Use the [standalone](#mutation-standalone-default-output-format---clean-code-only)
10. **Lint Validation** - After writing the mutation to a file, run `npx eslint <file>` from the webapp dir to validate it against the schema. Fix any reported errors before proceeding. See [Lint Validation](#lint-validation) for details
11. **Test the Query** - Use the [Generated Mutation Query Testing](#generated-mutation-query-testing) workflow to test the generated query
    1. **Report First** - Always output the generated mutation in the proper output format BEFORE initiating any test

## Mutation Query Schema

**Important**: In the schema fragments below, replace **EntityName** occurrences by the real entity name (i.e. Account, Case...).
**Important**: `Delete` operations all share the same generic `Record` entity name for both input and payload, only exposing the standard `Id` field.

```graphql
input EntityNameCreateRepresentation {
  # Subset of EntityName fields here
}
input EntityNameCreateInput { EntityName: EntityNameCreateRepresentation! }
type EntityNameCreatePayload { Record: EntityName! }

input EntityNameUpdateRepresentation {
  # Subset of EntityName fields here
}
input EntityNameUpdateInput { Id: IdOrRef! EntityName: EntityNameUpdateRepresentation! }
type EntityNameUpdatePayload { Record: EntityName! }

input RecordDeleteInput { Id: IdOrRef! }
type RecordDeletePayload { Id: ID }

type UIAPIMutations {
  EntityNameCreate(input: EntityNameCreateInput!): EntityNameCreatePayload
  EntityNameDelete(input: RecordDeleteInput!): RecordDeletePayload
  EntityNameUpdate(input: EntityNameUpdateInput!): EntityNameUpdatePayload
}
```

## Mutation Queries Input Field Constraints

1. **`Create` Mutation Queries**:
   1. **MUST** include all required fields
   2. **MUST** only include createable fields
   3. Child relationships can't be set and **MUST** be excluded
   4. Fields with type `REFERENCE` can only be assigned IDs through their `ApiName` name
2. **`Update` Mutation Queries**:
   1. **MUST** include the id of the entity to update
   2. **MUST** only include updateable fields
   3. Child relationships can't be set and **MUST** be excluded
   4. Fields with type `REFERENCE` can only be assigned IDs through their `ApiName` name
3. **`Delete` Mutation Queries**:
   1. **MUST** include the id of the entity to delete

## Mutation Queries Output Field Constraints

1. **`Create` and `Update` Mutation Queries**:
   1. **MUST** exclude all child relationships
   2. **MUST** exclude all `REFERENCE` fields, unless accessed through their `ApiName` member (no navigation to referenced entity)
   3. Inaccessible fields will be reported as part of the `errors` attribute in the returned payload
   4. Child relationships **CAN'T** be queried as part of a mutation
   5. Fields with type `REFERENCE` can only be queried through their `ApiName` (no referenced entities navigation, no sub fields)
2. **`Delete` Mutation Queries**:
   1. **MUST** only include the `Id` field

## Mutation Query Report Template

Input arguments:

- Required fields: FieldName1 (Type1), FieldName2 (Type2)...
- Other fields: FieldName3 (Type3)...
  Output fields: FieldNameA (TypeA), FieldNameB (TypeB)...

## Mutation Query Templates

```graphql
mutation mutateEntityName(
  # arguments
) {
  uiapi {
    EntityNameOperation(input: {
      # the following is for `Create` and `Update` operations only
      EntityName: {
        # Input fields
      }
      # the following is for `Update` and `Delete` operations only
      Id: ... # id here
    }) {
      # the following is for `Create` and `Update` operations only
      Record {
        # Output fields
      }
      # the following is for `Delete` operations only
      Id: ... # id here
    }
  }
}
```

## Mutation Standalone (Default) Output Format - CLEAN CODE ONLY

```javascript
import { gql } from '@salesforce/sdk-data';
const QUERY_NAME = gql`
  mutation mutateEntity($input: EntityNameOperationInput!) {
    uiapi {
      EntityNameOperation(input: $input) {
        # select output fields here depending on operation type
      }
    }
  }
`;

const QUERY_VARIABLES = {
  input: {
    // The following is for `Create` and `Update` operations only
    EntityName: {
      // variables here
    },
    // The following is for `Update` and `Delete` operations only
    Id: ... // id here
  }
};
```

**❌ FORBIDDEN — Do NOT include any of the following:**

- Explanatory comments about the query (inline or surrounding)
- Field descriptions or annotations
- Additional text about what the query does
- Workflow step descriptions or summaries
- Comments like `// fetches...`, `// creates...`, `/* ... */`

**✅ ONLY output:**

- The raw query string constant (using `gql` tagged template)
- The variables object constant
- Nothing else — no extra imports, no exports, no wrapper functions

## Lint Validation

After writing the generated mutation into a source file, validate it against the schema using the project's GraphQL ESLint setup:

```bash
# Run from webapp dir (force-app/main/default/webapplications/<app-name>/)
npx eslint <path-to-file-containing-mutation>
```

**How it works:** The ESLint config uses `@graphql-eslint/eslint-plugin` with its `processor`, which extracts GraphQL operations from `gql` template literals in `.ts`/`.tsx` files and validates the extracted `.graphql` virtual files against `schema.graphql`.

**Rules enforced:** `no-anonymous-operations`, `no-duplicate-fields`, `known-fragment-names`, `no-undefined-variables`, `no-unused-variables`

**On failure:** Fix the reported issues, re-run `npx eslint <file>` until clean, then proceed to testing.

> ⚠️ **Prerequisites**: The `schema.graphql` file must exist (invoke `exploring-graphql-schema` first) and project dependencies must be installed (`npm install`).

## Generated Mutation Query Testing

**Triggering conditions** — **ALL conditions must be true:**

1. The [Mutation Query Generation Workflow](#mutation-query-generation-workflow) completed with status `SUCCESS` and you have a generated query
2. The query is a mutation query
3. A non-manual method was used during schema exploration to retrieve introspection data

**Workflow**

1. **Report Step** - State the exact method you will use to test (e.g., `sf api request graphql` from the **project root**, Connect API, etc.) — this **MUST** match the method used during schema exploration
2. **Interactive Step** - Ask the user whether they want you to test the query using the proposed method
   1. **STOP and WAIT** for the user's answer. Do NOT proceed until the user responds. Do NOT assume consent.
3. **Input Arguments** - You **MUST** ask the user for the input argument values to use in the test
   1. **STOP and WAIT** for the user's answer. Do NOT proceed until the user provides values. Do NOT fabricate test data.
4. **Test Query** - Only if the user explicitly agrees and has provided input values:
   1. Execute the mutation using the reported method (e.g., `sf api request rest` to POST the query and variables to the GraphQL endpoint):
      ```bash
      sf api request rest /services/data/v65.0/graphql \
        --method POST \
        --body '{"query":"mutation mutateEntity($input: EntityNameOperationInput!) { uiapi { EntityNameOperation(input: $input) { Record { Id } } } }","variables":{"input":{"EntityName":{"Field":"Value"}}}}'
      ```
   2. Replace `v65.0` with the API version of the target org
   3. Replace the `query` value with the generated mutation query string
   4. Replace the `variables` value with the user-provided input arguments
5. **Result Analysis** - Retrieve the `data` and `errors` attributes from the returned payload, and report the result of the test as one of the following options:
   1. `PARTIAL` if `data` is not an empty object, but `errors` is not an empty list - Explanation: some of the queried fields are not accessible on mutations
   2. `FAILED` if `data` is an empty object - Explanation: the query is not valid
   3. `SUCCESS` if `errors` is an empty list
6. **Remediation Step** - If status is not `SUCCESS`, use the [`FAILED`](#failed-status-handling-workflow) or [`PARTIAL`](#partial-status-handling-workflow) status handling workflows

### `FAILED` Status Handling Workflow

The query is invalid:

1. **Error Analysis** - Parse and categorize the specific error messages
2. **Root Cause Identification** - Use error message to identify the root cause:
   - **Execution** - Error contains `invalid cross reference id` or `entity is deleted`
   - **Syntax** - Error contains `invalid syntax`
   - **Validation** - Error contains `validation error`
   - **Type** - Error contains `VariableTypeMismatch` or `UnknownType`
   - **Navigation** - Error contains `is not currently available in mutation results`
   - **API Version** - Query deals with updates, you're testing with Connect API and error contains `Cannot invoke JsonElement.isJsonObject()`
3. **Targeted Resolution** - Depending on the root cause categorization
   - **Execution** - You're trying to update or delete an unknown/no longer available entity: either create an entity first, if you have generated the related query, or ask for a valid entity id to use. **STOP and WAIT** for the user to provide a valid Id
   - **Syntax** - Update the query using the error message information to fix the syntax errors
   - **Validation** - The field name is most probably invalid. Re-run the relevant grep command from the `exploring-graphql-schema` skill to verify the correct field name. If still unclear, ask the user for clarification and **STOP and WAIT** for their answer
   - **Type** - Use the error details and re-verify the type via grep lookup in the schema. Correct the argument type and adjust variables accordingly
   - **Navigation** - Use the [`PARTIAL` status handling workflow](#partial-status-handling-workflow) below
   - **API Version** - `Record` selection is only available with API version 64 and higher, **report** the issue, and try again with API version 64
4. **Test Again** - Resume the [query testing workflow](#generated-mutation-query-testing) with the updated query (increment and track attempt counter)
5. **Escalation Path** - If targeted resolution fails after 2 attempts, ask for additional details and restart the entire GraphQL workflow from the `exploring-graphql-schema` skill

### `PARTIAL` Status Handling Workflow

The query can be improved:

1. Report the fields mentioned in the `errors` list
2. Explain that these fields can't be queried as part of a mutation query
3. Explain that the query might be considered as failing, as it will report errors
4. Offer to remove the offending fields
5. **STOP and WAIT** for the user's answer. Do NOT remove fields without explicit consent.
6. If they are OK with removing the fields restart the [generation workflow](#mutation-query-generation-workflow) with the new field list

## Related Skills

- Schema exploration: `exploring-graphql-schema` (must complete first)
- Read query generation: `generating-graphql-read-query`

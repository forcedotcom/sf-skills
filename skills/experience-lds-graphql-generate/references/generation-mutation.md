# GraphQL Mutation Query Generation

**Triggering conditions**

1. Only after Steps 1–4 of [generation-guide.md](generation-guide.md) have completed successfully (introspection produced a `SUCCESS` status with no unknown entities or fields)
2. Only if the query to generate is a mutation query

## Your Role

You are a GraphQL expert and your role is to help generate Salesforce-compatible GraphQL mutation queries once the exploration phase has completed.

If the introspection workflow in [generation-guide.md](generation-guide.md) has not been executed yet, you **MUST** run it first, and then return to mutation query generation.

You will leverage the context provided by the requesting user as well as the validated introspection results from [generation-guide.md](generation-guide.md) to generate the queries, and then test them against a live org using the bundled `scripts/test-lds-graphql-query.sh` script.

## Mutation Queries General Information

**IMPORTANT**:

1. **Mutation Types**: The GraphQL engine supports `Create`, `Update` and `Delete` operations
2. **Id Based Mutations**: `Update` and `Delete` operations operate on Id-based entity identification
3. **Mutation Schema**: Defined in the [mutation query schema](#mutation-query-schema) section

## Mutation Query Generation Workflow

Strictly follow the rules below when generating the GraphQL mutation query:

1. **Input Fields Validation** - Validate that the set of fields validate [input field constraints](#mutation-queries-input-field-constraints)
2. **Output Fields Validation** - Validate that the set of fields used in the select part of the query validate the [output fields constraints](#mutation-queries-output-field-constraints)
3. **Type Consistency** - Make sure variables used as query arguments and their related fields share the same GraphQL type
4. **Report Phase** - Use the [Mutation Query Report Template](#mutation-query-report-template) below to report on the previous validation phases
5. **Input Arguments** - `input` is the default name for the argument, unless otherwise specified
6. **Output Field** - For `Create` and `Update` operations, the output field is always named `Record`, and is of type EntityName
7. **Mutations Chaining** - It is possible to chain mutations in a single query using the [Mutations Chaining](#mutations-chaining) instructions
8. **Query Generation** - Use the [mutation query](#mutation-query-templates) template and adjust it based on the selected operation
9. **Output Format** - Use the [standalone](#mutation-standalone-default-output-format---clean-code-only) or [LWC](#mutation-lwc-integration-only-when-requested-output-format) output format templates based on desired output
10. **Report** - Always report, using the proper output format, before testing
11. **Test the Query** - Use the [Generated Mutation Query Testing](#generated-mutation-query-testing) workflow to test the generated query

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
   1. **MUST** include all required fields, unless they have `defaultedOnCreate` set to `true` and are not explicitly requested
   2. **MUST** only include `createable` fields
   3. Child relationships can't be set and **MUST** be excluded
   4. Fields with type `REFERENCE` can only be assigned IDs through their `ApiName` name
2. **`Update` Mutation Queries**:
   1. **MUST** include the id of the entity to update
   2. **MUST** only include `updateable` fields
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

## Mutations Chaining

It is possible to chain related mutations in a single query, using references to `Id` resulting from a previous mutation execution:

1. **Ordering** - Mutation `B` can reference mutation `A` only if mutation `A` comes first in the query
2. **Notation** - Use `SomeId: "@{A}"` in mutation `B` to set the `SomeId` field value to the `Id` produced by mutation `A` execution
3. **IDs only** - This only works with IDs, and `@{A}` will always be interpreted as the `Id` produced by mutation `A`
4. **Restrictions** - `A` needs to be either a `Create` or `Delete` mutation, this will fail for `Update`

## Mutation Query Report Template

Input arguments:

- Required fields: FieldName1 (Type1), FieldName2 (Type2)...
- Other fields: FieldName3 (Type3)...
- Output fields: FieldNameA (TypeA), FieldNameB (TypeB)...

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

If generating for LWC, the variable should provide the entire `input` argument:

```javascript
const QUERY_NAME = `
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

**DO NOT INCLUDE:**

- Explanatory comments about the query
- Field descriptions
- Additional text about what the query does
- Workflow step descriptions

**ONLY INCLUDE:**

- Raw query string
- Variables object
- Nothing else

## Mutation LWC Integration (Only When Requested) Output Format

When integrating within an LWC:

1. You must use the `executeMutation` imperative adapter
2. The first parameter must be the result of calling the `gql` tag function on the query
3. Both the `executeMutation` imperative adapter and the `gql` tag function must be imported from the `lightning/graphql` package

```javascript
import { LightningElement, wire } from 'lwc';
import { gql, executeMutation } from 'lightning/graphql';

export default class MyComponent extends LightningElement {
  get mutationQuery() {
    return gql`
      mutation operationEntityName {
        // mutation query here
      }
    `;
  }

  async mutateEntity() {
    // executeMutation takes the mutation document as its FIRST argument and
    // the options ({ variables }) as its SECOND. Passing a single
    // { query, variables } object leaves the document undefined.
    const result = await executeMutation(this.mutationQuery, {
      variables: {
        // variables here
      },
    });
    // do something with the result
  }
}
```

**DO:**

- use the `executeMutation` imperative adapter to execute the query and retrieve the result
- use the `gql` tag function to wrap the GraphQL query before passing it to the imperative adapter

**DO NOT:**

- don't attempt to use the `executeMutation` adapter in a wired way

## Generated Mutation Query Testing

**Triggering conditions** - **ALL CONDITIONS MUST VALIDATE\***

1. Only if the [Mutation Query Generation Workflow](#mutation-query-generation-workflow) step global status is `SUCCESS` and you have a generated query
2. Only if the query to generate is a mutation query

You will use the `scripts/test-lds-graphql-query.sh` script to test the query, passing the confirmed alias, the generated query, and related variables (if any).

**Workflow**

1. **Report Step** - Explain that you are able to test the query using the same method used during introspection
   1. You **MUST** report the method you will use, based on the org alias confirmed during Step 2 of [generation-guide.md](generation-guide.md)
2. **Interactive Step** - Ask the user whether they want you to test the query using the proposed method
   1. **WAIT** for the user's answer.
3. **Input Arguments** - You **MUST** ask the user for the input arguments to use
   1. **WAIT** for the user's answer.
4. **Test Query** - If the user are OK with you testing the query:
   1. Run `scripts/test-lds-graphql-query.sh USERNAME_OR_ALIAS 'QUERY' '<VARIABLES_JSON>'` to test the query
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
   - **Execution** - You're trying to update or delete an unknown/no longer available entity: either create an entity first, if you have generated the related query, or ask for a valid entity id to use
   - **Syntax** - Update the query using the error message information to fix the syntax errors
   - **Validation** - This field's name is most probably invalid, ask user for clarification and **WAIT** for the user's answer
   - **Type** - Use the error details and GraphQL schema to correct argument's type, and adjust variables accordingly
   - **Navigation** - Use the [`PARTIAL` status handling workflow](#partial-status-handling-workflow) below
   - **API Version** - `Record` selection is only available with API version 64 and higher, **report** the issue, and try again with API version 64
4. **Test Again** - Resume the [query testing workflow](#generated-mutation-query-testing) with the updated query (increment and track attempt counter)
5. **Escalation Path** - If targeted resolution fails after 2 attempts, ask for additional details and restart the entire GraphQL workflow, going again through the introspection phase

### `PARTIAL` Status Handling Workflow

The query can be improved:

1. Report the fields mentioned in the `errors` list
2. Explain that these fields can't be queried as part of a mutation query
3. Explain that the query might be considered as failing, as it will report errors
4. Offer to remove the offending fields
5. **WAIT** for the user's answer
6. If they are OK with removing the fields restart the [generation workflow](#mutation-query-generation-workflow) with the new field list

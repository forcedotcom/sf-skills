# GraphQL Read Query Generation

**Triggering conditions**

1. Only if the schema exploration phase completed successfully
2. Only if the query to generate is a read query

## Your Role

You are a GraphQL expert and your role is to help generate Salesforce compatible GraphQL read queries once the exploration phase has completed.

You will leverage the context provided by the requesting user as well as the validation phase provided by the schema exploration. This tool will also provide you with a method to dynamically query the target org instance that you will use to test the generated query.

If the schema exploration has not been executed yet, you **MUST** run it first, and then get back to read query generation.

## Read Query Generation Workflow

Strictly follow the rules below when generating the GraphQL read query:

1. **No Proliferation** - Only generate for the explicitly requested fields, nothing else
2. **Unique Query** - Leverage child relationships to query entities in one single query
3. **Navigate Entities** - Always use `relationshipName` to access reference fields and child entities
   1. **Exception** - if the `relationshipName` field is null, you can't navigate the related entity, and will have to return the `Id` itself
4. **Leverage Fragments** - Generate one fragment per possible type on polymorphic fields (field with `dataType="REFERENCE"` and more than one entry in `referenceToInfos` introspection attribute)
5. **Type Consistency** - Make sure variables used as query arguments and their related fields share the same GraphQL type
6. **Type Enforcement** - Make sure to leverage field type information from introspection and GraphQL schema to generate field access
7. **Semi and anti joins** - Use the semi-join or anti-join templates to filter an entity with conditions on child entities
8. **Query Generation** - Use the [template](#read-query-template) to generate the query
9. **Output Format** - Use the [standalone](#read-standalone-default-output-format---clean-code-only)
10. **Test the Query** - Use the [Generated Read Query Testing](#generated-read-query-testing) workflow to test the generated query
    1. **Report First** - Always report first, using the proper output format, before testing

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
            # Direct fields
            FieldName { value }

            # Non-polymorphic reference (single type)
            RelationshipName {
              Id
              Name { value }
            }

            # Polymorphic reference (multiple types)
            PolymorphicRelationshipName {
              ...TypeAInfo
              ...TypeBInfo
            }

            # Child relationship (subquery)
            RelationshipName(
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
  SpecificFieldA { value }
}

fragment TypeBInfo on TypeB {
  Id
  SpecificFieldB { value }
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
            Name {
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
    // query here
  }
`;

const QUERY_VARIABLES = {
  // variables here
};
```

**❌ DO NOT INCLUDE:**

- Explanatory comments about the query
- Field descriptions
- Additional text about what the query does
- Workflow step descriptions

**✅ ONLY INCLUDE:**

- Raw query string
- Variables object
- Nothing else

## Generated Read Query Testing

**Triggering conditions** - **ALL CONDITIONS MUST VALIDATE\***

1. Only if the [Read Query Generation Workflow](#read-query-generation-workflow) step global status is `SUCCESS` and you have a generated query
2. Only if the query to generate is a read query
3. Only if non manual method was used during schema exploration to retrieve introspection data

**Workflow**

1. **Report Step** - Explain that you are able to test the query using `sf api request rest`
2. **Interactive Step** - Ask the user whether they want you to test the query
   1. **WAIT** for the user's answer.
3. **Test Query** - If the user are OK with you testing the query:
   1. Use `sf api request rest` to POST the query to the GraphQL endpoint:
      ```bash
      sf api request rest /services/data/v65.0/graphql \
        --method POST \
        --body '{"query":"query GetData { uiapi { query { EntityName { edges { node { Id } } } } } }"}'
      ```
   2. Replace `v65.0` with the API version of the target org
   3. Replace the `query` value with the generated read query string
   4. If the query uses variables, include them in the JSON body as a `variables` key
   5. Report the result of the test as `SUCCESS` if the query executed without error, or `FAILED` if you got errors
   6. If the query executed without any errors, but you received no data, then the query is valid, and the result of the test is `SUCCESS`
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
   - **Validation** - This field's name is most probably invalid, ask user for clarification and **WAIT** for the user's answer
   - **Type** - Use the error details and GraphQL schema to correct argument's type, and adjust variables accordingly
4. **Test Again** - Resume the [query testing workflow](#generated-read-query-testing) with the updated query (increment and track attempt counter)
5. **Escalation Path** - If targeted resolution fails after 2 attempts, ask for additional details and restart the entire GraphQL workflow, going again through the introspection phase

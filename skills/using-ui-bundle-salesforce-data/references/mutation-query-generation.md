# Mutation Query Generation

## Mutation Types

The GraphQL engine supports three mutation operations:

- **Create** — Insert a new record
- **Update** — Modify an existing record (Id-based)
- **Delete** — Remove an existing record (Id-based)

Mutations are GA in API v66+. They live under `mutation { uiapi { ... } }` and only support UI API-available objects.

## Generation Rules

1. **Input fields validation** — Validate that input fields satisfy the constraints for the operation type
2. **Output fields validation** — Validate that output fields satisfy the constraints for the operation type
3. **Type consistency** — Variables used as query arguments and their related fields must share the same GraphQL type. Verify types via the schema search script — do NOT assume types
4. **Input arguments** — `input` is the default argument name unless otherwise specified
5. **Output field** — For `Create` and `Update`, the output field is always named `Record` (type: EntityName)
6. **Field name validation** — Every field name in the generated mutation **MUST** match a field confirmed via the schema search script. Do NOT guess or assume field names exist
7. **Raw input values** — Numeric values must be raw numbers without commas, currency symbols, or locale formatting (e.g., `80000` not `"80,000"` or `"$80,000"`). Compound fields (like addresses) require constituent fields (e.g., `BillingCity`, `BillingStreet`) — do not attempt to set the compound wrapper itself.

## Transactional Semantics: `allOrNone`

The `uiapi` mutation input accepts an `allOrNone` argument that controls rollback behavior:

- **`allOrNone: true` (default)** — If any operation fails, all operations in the request are rolled back. Use when operations must succeed or fail together.
- **`allOrNone: false`** — Independent operations can succeed individually. However, dependent operations (those using `@{alias}` references) still roll back together with their dependencies.

Always set `allOrNone` explicitly to make transactional intent clear.

## Mutation Schema Patterns

Replace `EntityName` with the actual entity name (e.g., Account, Case). `Delete` operations use generic `Record` types.

```graphql
input EntityNameCreateRepresentation {
  # Subset of EntityName fields
}
input EntityNameCreateInput { EntityName: EntityNameCreateRepresentation! }
type EntityNameCreatePayload { Record: EntityName! }

input EntityNameUpdateRepresentation {
  # Subset of EntityName fields
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

## Input Field Constraints

### Create

- **Must** include all required fields (unless `defaultedOnCreate` is `true` and not explicitly requested)
- **Must** only include `createable` fields
- Child relationships cannot be set — exclude them
- Reference fields (`REFERENCE` type) can only be assigned IDs through their `ApiName` name
- **No nested child creates** — Creating a record with child relationships in a single create operation is not supported. To create a parent and child together, use separate operations with `IdOrRef` chaining (see [Mutation Chaining](#mutation-chaining)).

### Update

- **Must** include the `Id` of the entity to update
- **Must** only include `updateable` fields
- Child relationships cannot be set — exclude them
- Reference fields (`REFERENCE` type) can only be assigned IDs through their `ApiName` name

### Delete

- **Must** include the `Id` of the entity to delete

## Output Field Constraints

### Create and Update

- **Must** exclude all child relationships (child relationships cannot be queried in mutations)
- **Must** exclude all `REFERENCE` fields unless accessed through their `ApiName` member (no navigation to referenced entity, no sub fields)
- Inaccessible fields are reported in the `errors` attribute of the returned payload

### Delete

- **Must** only include the `Id` field

## Mutation Chaining

Chain related mutations in a single request using references to `Id` values from previous mutations. This is the required approach for creating parent-child records together, since nested child creates are not supported.

1. **Ordering** — Mutation `B` can reference mutation `A` only if `A` comes first in the query
2. **Notation** — Use `SomeId: "@{A}"` in mutation `B` to set a field to the `Id` produced by mutation `A`
3. **IDs only** — `@{A}` is always interpreted as the `Id` from mutation `A`
4. **Restrictions** — `A` must be a `Create` or `Delete` mutation (chaining from `Update` will fail)

### Chaining Example

```graphql
mutation CreateAccountAndContact {
  uiapi(input: { allOrNone: true }) {
    AccountCreate(input: { Account: { Name: "Acme" } }) {
      Record { Id }
    }
    ContactCreate(input: { Contact: { LastName: "Smith", AccountId: "@{AccountCreate}" } }) {
      Record { Id }
    }
  }
}
```

## Mutation Query Template

```graphql
mutation mutateEntityName(
  # arguments
) {
  uiapi(input: { allOrNone: true }) {
    EntityNameOperation(input: {
      # For Create and Update only:
      EntityName: {
        # Input fields — use raw values, no formatting
      }
      # For Update and Delete only:
      Id: ... # id here
    }) {
      # For Create and Update only:
      Record {
        # Output fields
      }
      # For Delete only:
      Id
    }
  }
}
```

# Read Query Generation

## Load This Reference When

Load this file before generating or editing any Salesforce GraphQL **read** query, including filtering, ordering, pagination, relationship traversal, and result-consumption code.

## Generation Rules

1. **No proliferation** — Only generate for explicitly requested fields, nothing else. Do NOT add fields the user did not ask for.
2. **Unique query** — Leverage child relationships to query entities in one single query
3. **Navigate entities** — Always use `relationshipName` to access reference fields and child entities. Exception: if `relationshipName` is null, return the `Id` itself
4. **Leverage fragments** — Generate one fragment per possible type on polymorphic fields (fields with `dataType="REFERENCE"` and more than one entry in `referenceToInfos`)
5. **Type consistency** — Variables used as query arguments and their related fields must share the same GraphQL type. Verify types against the schema search script output — do not assume types
6. **Type enforcement** — Use field type information from introspection and the GraphQL schema to generate correct field access
7. **Field name validation** — Every field name in the generated query **MUST** match a field confirmed via the schema search script. Do NOT guess or assume field names exist
8. **@optional for FLS** — Apply `@optional` on all Salesforce record fields when possible (see [Field-Level Security and @optional](#field-level-security-and-optional)). This lets the query succeed when the user lacks field-level access; the server omits inaccessible fields instead of failing
9. **Consuming code defense** — When generating or modifying code that consumes read query results, defend against missing fields (see [Field-Level Security and @optional](#field-level-security-and-optional)). Use optional chaining (`?.`), nullish coalescing (`??`), and null/undefined checks — never assume optional fields are present
10. **Semi and anti joins** — Use the semi-join or anti-join templates to filter an entity with conditions on child entities
11. **Explicit pagination** — Always include `first:` in every query to control page size (see [Pagination](#pagination)). Default is 10 if omitted.
12. **Respect execution limits** — Stay within SOQL-derived limits: max 10 subqueries per request, max 5 child-to-parent relationship levels, max 1 parent-to-child level (no grandchildren), max 55 child-to-parent relationships, max 20 parent-to-child relationships per query
13. **Compound fields** — When filtering, ordering, or aggregating, use constituent fields (e.g., `BillingCity`, `BillingCountry`) not the compound wrapper (`BillingAddress`). The compound wrapper is only for selection.
14. **`_Record` suffix awareness** — Objects added to UI API in v60+ may use a `_Record` suffix for their type name (e.g., `FeedItem_Record` instead of `FeedItem`). Always verify type names via schema lookup — do not assume type name equals sObject API name.
15. **Query generation** — Use the read query template below

## Field-Level Security and @optional

Field-level security (FLS) restricts which fields different users can see. Use the `@optional` directive on Salesforce record fields when possible. The server omits the field when the user lacks access, allowing the query to succeed instead of failing. Available in API v65.0+.

Apply `@optional` to:
- Scalar fields and value-type fields (e.g. `Name { value }`)
- Parent relationships
- Child relationships

**Consuming code must defend against missing fields.** When a field is omitted due to FLS, it will be `undefined` (or absent) in the response. Use optional chaining (`?.`), nullish coalescing (`??`), and explicit null/undefined checks when reading query results. Never assume an optional field is present.

```ts
// Defend against missing fields
const name = node.Name?.value ?? '';
const relatedName = node.RelationshipName?.Name?.value ?? 'N/A';

// Unsafe — will throw if field omitted due to FLS
const name = node.Name.value;
```

## Pagination

Salesforce GraphQL uses Relay Cursor Connections with **forward-only pagination**. There is no backward pagination (`last`/`before` are not supported).

### Core Rules

- **Always specify `first:`** — If omitted, the server defaults to 10 records. Be explicit.
- **Forward-only** — Use `first` and `after` only. Do **not** use `last` or `before` — they are unsupported and will fail.
- **Maximum without upperBound** — Standard pagination allows up to 4,000 total records across pages.
- **Use `pageInfo`** — Select `pageInfo { hasNextPage endCursor }` for any query that may need pagination.

### UpperBound Pagination (v59+)

When you need more than 200 records per page or more than 4,000 total records, switch to upperBound mode:

- **`first` must be 200–2000** when `upperBound` is set. Values below 200 are invalid.
- **`upperBound`** declares the estimated total record count and enables extended pagination.

```graphql
# Standard pagination
Account(first: 50, after: $cursor) {
  edges { node { Id Name @optional { value } } }
  pageInfo { hasNextPage endCursor }
}

# UpperBound pagination for large result sets
Account(first: 2000, after: $cursor, upperBound: 10000) {
  edges { node { Id Name @optional { value } } }
  pageInfo { hasNextPage endCursor }
}
```

## Ordering

Use the `orderBy:` argument with generated `<Object>_OrderBy` input types. Run the schema search script to verify sortable fields.

### Rules

- Use `orderBy:` with the generated OrderBy type: `orderBy: { FieldName: { order: ASC } }`
- **Multi-column sorting** is supported by combining fields in the orderBy input
- **Unsupported field types** for ordering: multi-select picklist, rich text, long text area, encrypted fields. Do not order by these.
- **Locale sensitivity** — Sort order depends on user locale. For deterministic ordering, add `Id` as a tie-breaker field.
- **Compound fields** — Use constituent fields for ordering (e.g., `BillingCity`), not the compound wrapper.

```graphql
Account(
  first: 10,
  orderBy: { Name: { order: ASC }, CreatedDate: { order: DESC } }
) { ... }
```

## Filtering

### Boolean Filter Composition

Filter types include `AND`, `OR`, and `NOT` fields for combining conditions. Multiple filter fields at the same level combine with implicit AND.

```graphql
# Implicit AND — both conditions must match
Account(where: { Industry: { eq: "Technology" }, AnnualRevenue: { gt: 1000000 } })

# Explicit OR
Account(where: { OR: [
  { Industry: { eq: "Technology" } },
  { Industry: { eq: "Finance" } }
] })

# NOT
Account(where: { NOT: { Industry: { eq: "Technology" } } })
```

### Date and DateTime Filtering

Date and DateTime fields use special input objects (`DateInput`/`DateTimeInput`) that support both literal values and SOQL-style relative date semantics.

```graphql
# Literal date
Opportunity(where: { CloseDate: { eq: { value: "2024-12-31" } } })

# Relative date literal
Opportunity(where: { CloseDate: { gte: { literal: TODAY } } })
```

Verify exact literal enum values (e.g., `TODAY`, `THIS_MONTH`) via the schema search script.

### String Equality Is Case-Insensitive

String comparisons with `eq` are case-insensitive in Salesforce GraphQL. Do not rely on case sensitivity for string equality filters.

### Relationship Filters

Filter through parent relationships using nested filter objects (not dot notation):

```graphql
# Correct — nested filter objects
Contact(where: { Account: { Name: { like: "Acme%" } } })

# Wrong — dot notation is not supported
Contact(where: { "Account.Name": { like: "Acme%" } })
```

### Polymorphic Relationship Filters

Polymorphic relationships use union-aware filter input types named `<Object>_<RelationshipName>_Filters`. Filter by specific concrete types within the union:

```graphql
# Filter by polymorphic Owner (which is a union of User, Group, etc.)
Account(where: { Owner: { User: { Username: { like: "admin%" } } } })
```

Verify exact filter input type names and available concrete types via the schema search script.

### ID Filtering

Salesforce accepts both 15-character and 18-character record IDs for `Id` filtering. Do not reject or "correct" either form.

## Semi-Join and Anti-Join Templates

Semi-joins and anti-joins filter a parent entity using conditions on child entities. They use `inq` (semi-join) and `ninq` (anti-join) operators on the parent entity's `Id`.

The operator accepts:

- The child entity camelCase name with conditions
- The `ApiName` field containing the parent entity `Id` (`fieldName` from `childRelationships`)

If the only condition is child entity existence, use `Id: { ne: null }`.

### Restrictions

Semi-join and anti-join queries have SOQL-derived restrictions:
- **Limited count** — There are limits on the number of `inq`/`ninq` operators per query
- **No `ne` with joins** — Cannot use `ne` operator in combination with join operators
- **No `or` in subquery** — The join subquery conditions cannot use `OR`
- **No `orderBy` in subquery** — Join subqueries do not support ordering
- **Nesting restrictions** — Semi/anti-joins cannot be nested within each other

### Semi-Join Example

Filter `ParentEntity` to include only those with at least one matching `ChildEntity`:

```graphql
query testSemiJoin {
  uiapi {
    query {
      ParentEntity(
        where: {
          Id: {
            inq: {
              ChildEntity: {
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

### Anti-Join Example

Same as the semi-join example, but replace `inq` with `ninq` to filter `ParentEntity` with **no** matching `ChildEntity`.

## Current User Exception

To retrieve **current user**, **connected user**, or **authenticated user** information, use `uiapi.currentUser` instead of the standard query pattern. This field takes **no arguments** and returns a `User` type.

## Conditional Field Selection

For dynamic fieldsets with **known** fields, use `@include(if: $condition)` and `@skip(if: $condition)` directives in `.graphql` files. See GraphQL spec for details.

## Read Query Template

```graphql
query QueryName($after: String) {
  uiapi {
    query {
      EntityName(
        first: 10         # Always specify — default is 10 if omitted
        after: $after      # For pagination
        where: { ... }     # Filter conditions
        orderBy: { ... }   # Sort order
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

            # Child relationship (subquery) — max 1 level deep, no grandchildren
            RelationshipName @optional (
              first: 10     # Always specify
            ) {
              edges {
                node {
                  # fields
                }
              }
            }
          }
        }
        pageInfo {
          hasNextPage
          endCursor
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

## Field Value Wrappers

Schema fields use typed wrappers. Access the underlying value via `.value`:

| Wrapper Type      | Underlying Type | Access Pattern        |
| ----------------- | --------------- | --------------------- |
| `StringValue`     | `String`        | `field { value }`     |
| `IntValue`        | `Int`           | `field { value }`     |
| `CurrencyValue`   | `Currency`      | `field { value }`     |
| `DateTimeValue`   | `DateTime`      | `field { value }`     |
| `PicklistValue`   | `Picklist`      | `field { value }`     |
| `BooleanValue`    | `Boolean`       | `field { value }`     |
| `DoubleValue`     | `Double`        | `field { value }`     |
| `PercentValue`    | `Percent`       | `field { value }`     |
| `IDValue`         | `ID`            | `field { value }`     |
| `EmailValue`      | `Email`         | `field { value }`     |
| `PhoneNumberValue`| `PhoneNumber`   | `field { value }`     |
| `UrlValue`        | `Url`           | `field { value }`     |
| `DateValue`       | `Date`          | `field { value }`     |
| `LongValue`       | `Long`          | `field { value }`     |
| `TextAreaValue`   | `TextArea`      | `field { value }`     |

All wrappers also expose `displayValue: String` for formatted display. `displayValue` is server-rendered using SOQL `toLabel()` or `format()` depending on field type — use it for UI display instead of formatting values client-side.

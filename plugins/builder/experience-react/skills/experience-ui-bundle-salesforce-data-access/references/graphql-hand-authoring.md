# Hand-authoring Salesforce GraphQL queries & mutations (fallback)

**Use this only when the graphiti CLI is genuinely unreachable** — `@salesforce/graphiti` isn't
installed, or the org can't be primed. When the CLI *is* available it authors the query for you
with these same guardrails already applied; see [graphiti-cli.md](graphiti-cli.md). This doc is
the hand-authoring path: the schema-grep lookup plus the document templates and platform rules
you'd otherwise lean on the CLI to apply.

These rules are independent of the SDK reshape — only the *call mechanics* changed (see
[sdk-api.md](sdk-api.md)). Verify every entity and field via
`bash <skill-dir>/scripts/graphql-search.sh <Entity>` before writing a query
(`<skill-dir>` = wherever this skill is installed).

## Schema lookup (do this first)

Map intent to PascalCase ("accounts" → `Account`), then run the search script from the
SFDX project root (where `schema.graphql` lives). The script reads `./schema.graphql` and
does **not** walk up the tree — if the schema is elsewhere, pass `--schema <path>` (or set
`GRAPHQL_SCHEMA`). It prints the resolved schema path on stderr; confirm it's the right one.

```bash
bash <skill-dir>/scripts/graphql-search.sh Account
bash <skill-dir>/scripts/graphql-search.sh Account Contact Opportunity   # multiple
bash <skill-dir>/scripts/graphql-search.sh --schema path/to/schema.graphql Account  # schema not at ./
```

Output sections per entity: (1) Type definition, (2) Filter options, (3) Sort options,
(4) Create wrapper `<Entity>CreateInput`, (5) Create fields `<Entity>CreateRepresentation`,
(6) Update wrapper `<Entity>UpdateInput`, (7) Update fields `<Entity>UpdateRepresentation`.

If an entity isn't found: try `__c`/`__e`, try a `_Record` suffix (v60+); if it's still
unresolved it may not be deployed — **ask the user**. Introspect nested references iteratively
as you discover them; if the lookups aren't converging on what you need, ask the user rather
than keep guessing. Never generate a query with an unconfirmed entity or field. **Never open *or edit*
`schema.graphql`** (265K+ lines) — no cat, less, head, tail, editors, or programmatic
parsers. It is a generated, read-only mirror of the org; editing it (e.g. to add a field that
won't resolve) silences the validator but grants no org access, so the operation still fails at
runtime. To change what it contains, deploy metadata then regenerate (`npm run graphql:schema`).

## Read query template

```graphql
query QueryName($after: String) {
  uiapi {
    query {
      EntityName(
        first: 10
        after: $after
        where: { ... }
        orderBy: { ... }
      ) {
        edges {
          node {
            Id
            FieldName @optional { value }
            # Parent relationship (non-polymorphic) — @optional on the relationship AND its fields
            Owner @optional { Name @optional { value } }
            # Parent relationship (polymorphic — use fragments)
            What @optional {
              ...WhatAccount
              ...WhatOpportunity
            }
            # Child relationship — max 1 level, no grandchildren.
            # `first:` is a FIELD ARGUMENT (parens on the field); `@optional` is a
            # bare directive that takes no arguments. Keep them separate.
            Contacts(first: 10) @optional {
              edges { node { Name @optional { value } } }
            }
          }
        }
        pageInfo { hasNextPage endCursor }
      }
    }
  }
}

fragment WhatAccount on Account { Id Name @optional { value } }
fragment WhatOpportunity on Opportunity { Id Name @optional { value } }
```

Consuming code must defend against omitted (FLS-stripped) fields:

```typescript
const name = node.Name?.value ?? "";
const relatedName = node.Owner?.Name?.value ?? "N/A";
```

This is exactly how the shipped `accounts.ts` `toAccount()` mapper works —
`node.Name?.value ?? "Unknown"`, `node.Industry?.value ?? null`, etc.

## `@optional` and FLS

Salesforce field-level security makes a query fail **entirely** if the user lacks access to
even one selected field. The `@optional` directive (v65+) tells the server to omit inaccessible
fields instead of failing the whole request. `@optional` is a per-field directive
(`directive @optional on FIELD`), so apply it at **every level of nesting**, not just the
outermost: decorate each scalar field, each parent relationship, **and the nested fields
inside that relationship** — `Owner @optional { Name @optional { value } }`, not
`Owner @optional { Name { value } }`. The template above does this throughout.

> Shipped code varies: `userProfileApi.ts` uses `FirstName @optional { value }`, while the
> `accounts.ts` demo selects bare `Name { value }` and leans entirely on defensive
> `?.value ?? fallback` downstream. Bare selection is only safe when every selected field is
> guaranteed-accessible; **decorate with `@optional` by default** so a single FLS-restricted
> field can't fail the whole query. Always pair it with `?.`/`??` in consuming code regardless.

## Filtering

```graphql
# Implicit AND
Account(where: { Industry: { eq: "Technology" }, AnnualRevenue: { gt: 1000000 } })
# OR
Account(where: { OR: [{ Industry: { eq: "Technology" } }, { Industry: { eq: "Finance" } }] })
# NOT
Account(where: { NOT: { Industry: { eq: "Technology" } } })
# Date literal / relative date
Opportunity(where: { CloseDate: { eq: { value: "2024-12-31" } } })
Opportunity(where: { CloseDate: { gte: { literal: TODAY } } })
# Relationship filter (nested object, NOT dot notation)
Contact(where: { Account: { Name: { like: "Acme%" } } })
# Polymorphic relationship filter
Account(where: { Owner: { User: { Username: { like: "admin%" } } } })
```

String `eq` is case-insensitive. Both 15- and 18-char record IDs are accepted. **Compound
fields**: filter/order on constituents (`BillingCity`, `BillingCountry`), never the compound
wrapper (`BillingAddress`) — the wrapper is selection-only.

## Ordering

```graphql
Account(first: 10, orderBy: { Name: { order: ASC }, CreatedDate: { order: DESC } })
```

Add `Id` as a tie-breaker for deterministic order. Unsupported for ordering: multi-select
picklist, rich text, long text area, encrypted fields.

## Pagination

- **Always include `first:`** — the server silently defaults to 10 if omitted.
- Include `pageInfo { hasNextPage endCursor }` for anything paginatable.
- Forward-only (`first` / `after`); `last` / `before` are unsupported.
- `upperBound` (v59+) for large sets; when set, `first` must be 200–2000.

```graphql
Account(first: 2000, after: $cursor, upperBound: 10000) {
  edges { node { Id Name @optional { value } } }
  pageInfo { hasNextPage endCursor }
}
```

The shipped `accounts.ts` query parameterizes `$first` / `$after` and selects
`pageInfo { hasNextPage endCursor }`; `Accounts.tsx` pages via "Load more" using
`pageInfo.endCursor`.

## SOQL-derived limits

Max 10 subqueries/request, 5 levels child→parent, 1 level parent→child (no grandchildren),
2,000 records/subquery. Split into multiple requests if exceeded.

## Field value wrappers

Schema fields use typed wrappers; access via `.value`. Use `displayValue` (a `String`,
server-rendered) for UI display instead of formatting client-side.

| Wrapper | Underlying | Wrapper | Underlying |
|---|---|---|---|
| `StringValue` | String | `BooleanValue` | Boolean |
| `IntValue` | Int | `DoubleValue` | Double |
| `CurrencyValue` | Currency | `PercentValue` | Percent |
| `DateTimeValue` | DateTime | `DateValue` | Date |
| `PicklistValue` | Picklist | `LongValue` | Long |
| `IDValue` | ID | `TextAreaValue` | TextArea |
| `EmailValue` | Email | `PhoneNumberValue` | PhoneNumber |
| `UrlValue` | Url | | |

## Semi-join / anti-join

Filter a parent by conditions on children via `inq` (semi-join) / `ninq` (anti-join) on the
parent's `Id`. If the only condition is child existence, use `Id: { ne: null }`.

```graphql
Account(where: { Id: { inq: { Contact: { LastName: { like: "Smith%" } } ApiName: "AccountId" } } }, first: 10) {
  edges { node { Id Name @optional { value } } }
}
```

Restrictions: no `OR` in subquery, no `orderBy` in subquery, no nested joins.

## Current user

```graphql
query CurrentUser { uiapi { currentUser { Id Name { value } } } }
```

Do **not** use Chatter (`/chatter/users/me`).

## Mutations

Mutations GA in v66+. The installed declarations own the `mutate()` call shape; wrap every
document under `uiapi(input: { allOrNone: true | false })` and set `allOrNone` explicitly.

```graphql
# Create
mutation CreateAccount($input: AccountCreateInput!) {
  uiapi(input: { allOrNone: true }) {
    AccountCreate(input: $input) { Record { Id Name { value } } }
  }
}

# Update — must include Id
mutation UpdateAccount($input: AccountUpdateInput!) {
  uiapi(input: { allOrNone: true }) {
    AccountUpdate(input: $input) { Record { Id Name { value } } }
  }
}

# Delete — generic RecordDeleteInput (NO per-entity delete type); Id is flat, not
# nested under an entity key. Payload is RecordDeletePayload with `Id` ONLY — there
# is no `Record` field to select back (selecting `Record` is a schema error).
# Declare the variable `$input: RecordDeleteInput!` (its `Id` is `IdOrRef!`, NOT `ID!`,
# so `$id: ID!` is rejected) — same `(input: $input)` call shape as Create/Update above.
mutation DeleteAccount($input: RecordDeleteInput!) {
  uiapi(input: { allOrNone: true }) {
    AccountDelete(input: $input) { Id }
  }
}
# runtime: variables: { input: { Id: "001…" } }   // flat Id — matches the spine's delete shape
```

> Older shipped examples can omit `uiapi(input: { allOrNone })`. They predate this guardrail;
> always author new mutations with the explicit wrapper in the templates above.

**Input constraints**
- Create: required fields (unless `defaultedOnCreate`), only `createable` fields, no child
  relationships; reference fields set by `ApiName` (e.g. `AccountId`).
- Update: must include `Id`, only `updateable` fields, no child relationships.
- Delete: `Id` only.
- `IdOrRef` (Update/Delete `Id`, and Create reference fields) accepts a literal record ID or a
  chaining reference `"@{Alias}"`.
- Raw values only — no commas, currency symbols, or locale formatting (`80000`, not `"$80,000"`).

**Output constraints**
- Create/Update: output is always named `Record`; exclude child relationships and navigated
  reference fields (only the `ApiName` member is allowed).
- Delete: `Id` only — the payload is `RecordDeletePayload`, which has **no `Record` field**;
  selecting `Record` (the Create/Update output) on a delete is a schema error.

**`allOrNone` semantics**
- `true` — all operations succeed or all roll back.
- `false` — independent operations succeed individually; dependent operations (chained via
  `@{alias}`) still roll back together.

### Mutation chaining

Chain related mutations with `@{alias}` references to an earlier mutation's `Id`. Required for
parent-child creation (nested child creates are unsupported).

```graphql
mutation CreateAccountAndContact {
  uiapi(input: { allOrNone: true }) {
    AccountCreate(input: { Account: { Name: "Acme" } }) { Record { Id } }
    ContactCreate(input: { Contact: { LastName: "Smith", AccountId: "@{AccountCreate}" } }) { Record { Id } }
  }
}
```

Rules: `A` must appear before `B`; `@{A}` is always `A`'s `Id`; only `Create` or `Delete` can
be chained *from* (not `Update`).

## Object metadata & picklist values

Use `uiapi { objectInfos(...) }`. Pass **either** `apiNames` **or** `objectInfoInputs` — never both.

```graphql
query GetObjectInfo($apiNames: [String!]!) {
  uiapi { objectInfos(apiNames: $apiNames) {
    ApiName label labelPlural
    fields { ApiName label dataType updateable createable }
  } }
}

query GetPicklistValues($objectInfoInputs: [ObjectInfoInput!]!) {
  uiapi { objectInfos(objectInfoInputs: $objectInfoInputs) {
    ApiName
    fields { ApiName ... on PicklistField {
      picklistValuesByRecordTypeIDs { recordTypeID picklistValues { label value } }
    } }
  } }
}
```

## Aggregations

`uiapi { aggregate { … } }` mirrors `query` (one entry per record type) but returns
aggregated buckets instead of rows — use it for counts/sums/grouped rollups so you don't
pull every record client-side. Pass `groupBy:` (each grouped field gets `{ group: true }`)
and select aggregate functions under `node { aggregate { … } }`. Scalar aggregates expose
`count`/`countDistinct`/`min`/`max`; numerics (`IntAggregate`, etc.) add `avg`/`sum`.

```graphql
# Count + average employees, grouped by Industry
query AccountsByIndustry {
  uiapi {
    aggregate {
      Account(groupBy: { Industry: { group: true } }, first: 50) {
        edges {
          node {
            aggregate {
              Industry @optional { value }
              # aggregate functions are FieldValue wrappers — select { value }
              # (count/sum are LongValue, avg is DoubleValue), not bare.
              NumberOfEmployees @optional { count { value } avg { value } sum { value } }
            }
          }
        }
        totalCount
      }
    }
  }
}
```

`first:` is still required, `@optional` still applies, results page like a normal connection.

## Related-list metadata

`uiapi { relatedListByName(parentApiName:, relatedListName:) }` returns the *shape* of a
parent object's related list — its display columns and ordering, not the child records
themselves (query those via the child relationship). Both args are required.

```graphql
query AccountContactsRelatedList {
  uiapi {
    relatedListByName(parentApiName: "Account", relatedListName: "Contacts") {
      label
      childApiName
      displayColumns { fieldApiName label sortable }
      orderedByInfo { fieldApiName sortDirection }
    }
  }
}
```

## Error patterns

| Error contains | Resolution |
|---|---|
| `Cannot query field` / `ValidationError` / `validation error` | The *operation* is wrong or the type isn't accessible — re-ground the field (graphiti `sf-gql-discover`, or `graphql-search.sh <Entity>` on this fallback path) and fix the operation to the exact name from the Type definition; if it genuinely isn't in the org, deploy the metadata + assign perms then `npm run graphql:schema`. **Never edit `schema.graphql` to satisfy the validator** — it grants no org access and only hides the failure until runtime. |
| `Unknown type` | Type name wrong — verify PascalCase entity name via script |
| `Unknown argument` | Check Filter / OrderBy sections in script output |
| `invalid syntax` / `InvalidSyntax` | Fix syntax per message |
| `VariableTypeMismatch` / `UnknownType` | Correct argument type from schema |
| `invalid cross reference id` | Entity deleted — ask for a valid Id |
| `OperationNotSupported` | Check object availability and API version |
| `is not currently available in mutation results` | Remove the field from mutation output |
| `Cannot invoke JsonElement.isJsonObject()` | Use API v66+ for update-mutation `Record` selection |

**On PARTIAL** (mutation returns both data and errors): report inaccessible fields, explain
they cannot appear in mutation output, offer to remove them, and **wait for user consent**
before changing.

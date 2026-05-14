---
name: using-ui-bundle-salesforce-data
description: "MUST activate when the project contains a uiBundles/*/src/ directory and the task involves ANY Salesforce record operation — reading, creating, updating, or deleting. Use this skill when building forms that submit to Salesforce, pages that display Salesforce records, or any code that touches Salesforce objects or custom objects. Activate when files under uiBundles/*/src/ import from @salesforce/sdk-data, or when *.graphql files or codegen.yml exist. This skill owns all Salesforce data access patterns in UI bundles. Does not apply to authentication/OAuth setup, schema changes, Bulk/Tooling/Metadata API, or declarative automation."
---

# Salesforce Data Access

## Data SDK Requirement

> **All Salesforce data access MUST use the Data SDK** (`@salesforce/sdk-data`). The SDK handles authentication, CSRF, and base URL resolution.

```typescript
import { createDataSDK, gql } from "@salesforce/sdk-data";
import type { ResponseTypeQuery } from "../graphql-operations-types";

const sdk = await createDataSDK();

// GraphQL for record queries/mutations (PREFERRED)
const response = await sdk.graphql?.<ResponseTypeQuery>(query, variables);

// REST for Connect REST, Apex REST, UI API (when GraphQL insufficient)
const res = await sdk.fetch?.("/services/apexrest/my-resource");
```

**Always use optional chaining** (`sdk.graphql?.()`, `sdk.fetch?.()`) — these methods may be undefined in some surfaces.

## Preconditions — verify before starting

| # | Requirement | How to verify | If missing |
|---|-------------|---------------|------------|
| 1 | `@salesforce/sdk-data` installed | Check `package.json` in the UI bundle dir | Cannot proceed — tell user to install it |
| 2 | `schema.graphql` at project root | Check if file exists | Run `npm run graphql:schema` from UI bundle dir |
| 3 | Custom objects/fields deployed | Run `graphql-search.sh <Entity>` — no output means not deployed | Ask user to deploy metadata and assign permission sets |

**If preconditions are not met**, you may scaffold components, routes, layout, and UI logic, but use empty arrays / `null` for data and mark query locations with `// TODO: add query after schema verification` and include in the plan to go back, resolve requirements and write the GraphQL. Do not write GraphQL query strings until the schema workflow is complete.

## Supported APIs

**Only the following APIs are permitted.** Any endpoint not listed here must not be used.

| API | Method | Endpoints / Use Case |
|-----|--------|----------------------|
| GraphQL | `sdk.graphql` | All record queries and mutations via `uiapi { }` namespace |
| UI API REST | `sdk.fetch` | `/services/data/v{ver}/ui-api/records/{id}` — record metadata when GraphQL is insufficient |
| Apex REST | `sdk.fetch` | `/services/apexrest/{resource}` — custom server-side logic, aggregates, multi-step transactions |
| Connect REST | `sdk.fetch` | `/services/data/v{ver}/connect/file/upload/config` — file upload config |
| Einstein LLM | `sdk.fetch` | `/services/data/v{ver}/einstein/llm/prompt/generations` — AI text generation |

**Not supported:**

- **Enterprise REST query endpoint** (`/services/data/v*/query` with SOQL) — blocked at the proxy level. Use GraphQL for record reads; use Apex REST if server-side SOQL aggregates are required.
- **Aura-enabled Apex** (`@AuraEnabled`) — an LWC/Aura pattern with no invocation path from React UI bundles.
- **Chatter API** (`/chatter/users/me`) — use `uiapi { currentUser { ... } }` in a GraphQL query instead.
- **Any other Salesforce REST endpoint** not listed in the supported table above.

## Decision: GraphQL vs REST

| Need | Method | Example |
|------|--------|---------|
| Query/mutate records | `sdk.graphql` | Account, Contact, custom objects |
| Current user info | `sdk.graphql` | `uiapi { currentUser { Id Name { value } } }` |
| UI API record metadata | `sdk.fetch` | `/ui-api/records/{id}` |
| Connect REST | `sdk.fetch` | `/connect/file/upload/config` |
| Apex REST | `sdk.fetch` | `/services/apexrest/auth/login` |
| Einstein LLM | `sdk.fetch` | `/einstein/llm/prompt/generations` |

**GraphQL is preferred** for record operations. Use REST only when GraphQL doesn't cover the use case.

---

## GraphQL Non-Negotiable Rules

These rules exist because Salesforce GraphQL has platform-specific behaviors that differ from standard GraphQL. Violations cause silent runtime failures.

1. **HTTP 200 does not mean success** — Salesforce returns HTTP 200 even when operations fail. **Always parse the `errors` array in the response body.**

2. **Schema is the single source of truth — access it only via the search script** — Every entity name, field name, and type must be confirmed by running `bash scripts/graphql-search.sh <Entity>` before use in a query. Never read `schema.graphql` directly. Never guess — Salesforce field names are case-sensitive, relationships may be polymorphic, and custom objects use suffixes (`__c`, `__e`). Objects added to UI API in v60+ may use a `_Record` suffix (e.g., `FeedItem_Record` instead of `FeedItem`).

3. **`@optional` on all record fields** (read queries) — Salesforce field-level security (FLS) causes queries to fail entirely if the user lacks access to even one field. The `@optional` directive (v65+) tells the server to omit inaccessible fields instead of failing. Apply it to every scalar field, parent relationship, and child relationship. Consuming code must use optional chaining (`?.`) and nullish coalescing (`??`).

4. **Correct mutation syntax** — Mutations wrap under `uiapi(input: { allOrNone: true/false })`, not bare `uiapi { ... }`. Always set `allOrNone` explicitly. Output fields cannot include child relationships or navigated reference fields.

5. **Explicit pagination** — Always include `first:` in every query. If omitted, the server silently defaults to 10 records. Include `pageInfo { hasNextPage endCursor }` for any query that may need pagination. Forward-only (`first`/`after`) — `last`/`before` are unsupported.

6. **SOQL-derived execution limits** — Max 10 subqueries per request, max 5 levels of child-to-parent traversal, max 1 level of parent-to-child (no grandchildren), max 2,000 records per subquery. If a query would exceed these, split into multiple requests.

7. **Only requested fields** — Only generate fields the user explicitly asked for. Do NOT add extra fields.

8. **Compound fields** — When filtering or ordering, use constituent fields (e.g., `BillingCity`, `BillingCountry`), not the compound wrapper (`BillingAddress`). The compound wrapper is only for selection.

---

## GraphQL Workflow

| Step | Action | Key output |
|------|--------|------------|
| 1 | Acquire schema | `schema.graphql` exists |
| 2 | Look up entities | Field names, types, relationships confirmed |
| 3 | Generate query | `.graphql` file or inline `gql` tag |
| 4 | Generate types | `graphql-operations-types.ts` |
| 5 | Validate | Lint + codegen pass |

### Step 1: Acquire Schema

The `schema.graphql` file (265K+ lines) is the source of truth. **Never open or parse it directly** — do NOT use `Read`, `Grep`, `Bash`, `cat`, `head`, `tail`, `grep`, `rg`, `less`, `sed`, `awk`, editors, or any tool to read, search, or parse this file. It will overwhelm your context. Use only `bash scripts/graphql-search.sh <Entity>`.

Verify preconditions 1–3 (see [Preconditions](#preconditions--verify-before-starting)), then proceed to Step 2.

### Step 2: Look Up Entity Schema

Map user intent to PascalCase names ("accounts" → `Account`), then **run the search script from the `sfdx-project` folder (project root)**:

```bash
bash scripts/graphql-search.sh Account
# Multiple entities:
bash scripts/graphql-search.sh Account Contact Opportunity
```

The script outputs seven sections per entity:
1. **Type definition** — all queryable fields and relationships
2. **Filter options** — available fields for `where:` conditions
3. **Sort options** — available fields for `orderBy:`
4. **Create mutation wrapper** — `<Entity>CreateInput`
5. **Create mutation fields** — `<Entity>CreateRepresentation` (fields accepted by create mutations)
6. **Update mutation wrapper** — `<Entity>UpdateInput`
7. **Update mutation fields** — `<Entity>UpdateRepresentation` (fields accepted by update mutations)

**Maximum 2 script runs.** If the entity still can't be found, ask the user — the object may not be deployed.

#### Entity Identification

If a candidate does not match:
- Try `__c` suffix for custom objects, `__e` for platform events
- Try `_Record` suffix — objects added in v60+ may use `<EntityName>_Record`
- If still unresolved, **ask the user** — do not guess

#### Iterative Introspection (max 3 cycles)

1. **Introspect** — Run the script for each unresolved entity
2. **Fields** — Extract requested field names and types from the type definition
3. **References** — Identify reference fields. If polymorphic (multiple types), use inline fragments. Add newly discovered entity types to the working list.
4. **Child relationships** — Identify Connection types. Add child entity types to the working list.
5. **Repeat** if unresolved entities remain (max 3 cycles)

**Hard stops:** If no data returned for an entity, stop — it may not be deployed. If unknown entities remain after 3 cycles, ask the user. Do not generate queries with unconfirmed entities or fields.

### Step 3: Generate Query

Every field name **must** be verified from the script output in Step 2.

#### Read Query Template

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
            # Parent relationship (non-polymorphic)
            Owner @optional { Name { value } }
            # Parent relationship (polymorphic — use fragments)
            What @optional {
              ...WhatAccount
              ...WhatOpportunity
            }
            # Child relationship — max 1 level, no grandchildren
            Contacts @optional(first: 10) {
              edges { node { Name @optional { value } } }
            }
          }
        }
        pageInfo { hasNextPage endCursor }
      }
    }
  }
}

fragment WhatAccount on Account {
  Id
  Name @optional { value }
}
fragment WhatOpportunity on Opportunity {
  Id
  Name @optional { value }
}
```

**Consuming code must defend against missing fields:**

```typescript
const name = node.Name?.value ?? "";
const relatedName = node.Owner?.Name?.value ?? "N/A";
```

#### Filtering

```graphql
# Implicit AND
Account(where: { Industry: { eq: "Technology" }, AnnualRevenue: { gt: 1000000 } })

# Explicit OR
Account(where: { OR: [{ Industry: { eq: "Technology" } }, { Industry: { eq: "Finance" } }] })

# NOT
Account(where: { NOT: { Industry: { eq: "Technology" } } })

# Date literal
Opportunity(where: { CloseDate: { eq: { value: "2024-12-31" } } })

# Relative date
Opportunity(where: { CloseDate: { gte: { literal: TODAY } } })

# Relationship filter (nested objects, NOT dot notation)
Contact(where: { Account: { Name: { like: "Acme%" } } })

# Polymorphic relationship filter
Account(where: { Owner: { User: { Username: { like: "admin%" } } } })
```

String equality (`eq`) is case-insensitive. Both 15-char and 18-char record IDs are accepted.

#### Ordering

```graphql
Account(
  first: 10,
  orderBy: { Name: { order: ASC }, CreatedDate: { order: DESC } }
) { ... }
```

Unsupported for ordering: multi-select picklist, rich text, long text area, encrypted fields. Add `Id` as tie-breaker for deterministic ordering.

#### UpperBound Pagination (v59+)

For >200 records per page or >4,000 total records, use `upperBound`. `first` must be 200–2000 when set.

```graphql
Account(first: 2000, after: $cursor, upperBound: 10000) {
  edges { node { Id Name @optional { value } } }
  pageInfo { hasNextPage endCursor }
}
```

#### Semi-Join and Anti-Join

Filter a parent entity by conditions on child entities using `inq` (semi-join) or `ninq` (anti-join) on the parent's `Id`. If the only condition is child existence, use `Id: { ne: null }`.

```graphql
query SemiJoinExample {
  uiapi {
    query {
      Account(where: {
        Id: {
          inq: {
            Contact: { LastName: { like: "Smith%" } }
            ApiName: "AccountId"
          }
        }
      }, first: 10) {
        edges { node { Id Name @optional { value } } }
      }
    }
  }
}
```

Replace `inq` with `ninq` for anti-join. Restrictions: no `OR` in subquery, no `orderBy` in subquery, no nesting joins within each other.

#### Current User

Use `uiapi.currentUser` (no arguments) instead of the standard query pattern:

```graphql
query CurrentUser {
  uiapi { currentUser { Id Name { value } } }
}
```

#### Field Value Wrappers

Schema fields use typed wrappers — access via `.value`:

| Wrapper Type | Underlying | Wrapper Type | Underlying |
|---|---|---|---|
| `StringValue` | `String` | `BooleanValue` | `Boolean` |
| `IntValue` | `Int` | `DoubleValue` | `Double` |
| `CurrencyValue` | `Currency` | `PercentValue` | `Percent` |
| `DateTimeValue` | `DateTime` | `DateValue` | `Date` |
| `PicklistValue` | `Picklist` | `LongValue` | `Long` |
| `IDValue` | `ID` | `TextAreaValue` | `TextArea` |
| `EmailValue` | `Email` | `PhoneNumberValue` | `PhoneNumber` |
| `UrlValue` | `Url` | | |

All wrappers also expose `displayValue: String` (server-rendered via `toLabel()`/`format()`) — use for UI display instead of formatting client-side.

#### Mutation Template

Mutations are GA in API v66+. Three operations: **Create**, **Update**, **Delete**.

```graphql
# Create
mutation CreateAccount($input: AccountCreateInput!) {
  uiapi(input: { allOrNone: true }) {
    AccountCreate(input: $input) {
      Record { Id Name { value } }
    }
  }
}

# Update — must include Id
mutation UpdateAccount {
  uiapi(input: { allOrNone: true }) {
    AccountUpdate(input: { Id: "001xx000003GYkZAAW", Account: { Name: "New Name" } }) {
      Record { Id Name { value } }
    }
  }
}
```

**Input constraints:**
- **Create**: Required fields (unless `defaultedOnCreate`), only `createable` fields, no child relationships. Reference fields set by `ApiName` (e.g., `AccountId`).
- **Update**: Must include `Id`, only `updateable` fields, no child relationships.
- **Delete**: `Id` only.
- **`IdOrRef` type**: The `Id` field in Update and Delete inputs uses the `IdOrRef` type, which accepts either a literal record ID (e.g., `"001xx..."`) or a mutation chaining reference (`"@{Alias}"`). Reference fields in Create inputs (e.g., `AccountId`) also accept `@{Alias}` for chaining.
- **Raw values**: No commas, currency symbols, or locale formatting (e.g., `80000` not `"$80,000"`).

**Output constraints:**
- Create/Update: Exclude child relationships, exclude navigated reference fields (only `ApiName` member allowed). Output field is always named `Record`.
- Delete: `Id` only.

**`allOrNone` semantics:**
- `true` (default) — All operations succeed or all roll back.
- `false` — Independent operations succeed individually, but dependent operations (using `@{alias}`) still roll back together.

#### Mutation Chaining

Chain related mutations using `@{alias}` references to `Id` from earlier mutations. Required for parent-child creation (nested child creates are not supported).

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

Rules: `A` must come before `B` in the query. `@{A}` is always the `Id` from mutation `A`. Only `Create` or `Delete` can be chained from (not `Update`).

#### Delete Mutation

Delete uses generic `RecordDeleteInput` (not entity-specific). Output is `Id` only — no `Record` field.

```graphql
mutation DeleteAccount($id: ID!) {
  uiapi(input: { allOrNone: true }) {
    AccountDelete(input: { Id: $id }) {
      Id
    }
  }
}
```

#### Object Metadata & Picklist Values

Use `uiapi { objectInfos(...) }` to fetch field metadata or picklist values. Pass **either** `apiNames` or `objectInfoInputs` — never both.

```typescript
// Object metadata
const GET_OBJECT_INFO = gql`
  query GetObjectInfo($apiNames: [String!]!) {
    uiapi {
      objectInfos(apiNames: $apiNames) {
        ApiName
        label
        labelPlural
        fields { ApiName label dataType updateable createable }
      }
    }
  }
`;

// Picklist values (use objectInfoInputs + inline fragment)
const GET_PICKLIST_VALUES = gql`
  query GetPicklistValues($objectInfoInputs: [ObjectInfoInput!]!) {
    uiapi {
      objectInfos(objectInfoInputs: $objectInfoInputs) {
        ApiName
        fields {
          ApiName
          ... on PicklistField {
            picklistValuesByRecordTypeIDs {
              recordTypeID
              picklistValues { label value }
            }
          }
        }
      }
    }
  }
`;
```

### Step 4: Generate Types (codegen)

After writing the query (whether in a `.graphql` file or inline with `gql`), generate TypeScript types:

```bash
# Run from UI bundle dir
npm run graphql:codegen
```

Output: `src/api/graphql-operations-types.ts`

Generated type naming conventions:
- `<OperationName>Query` / `<OperationName>Mutation` — response types
- `<OperationName>QueryVariables` / `<OperationName>MutationVariables` — variable types

**Always import and use the generated types** when calling `sdk.graphql`:

```typescript
import type { GetAccountsQuery, GetAccountsQueryVariables } from "../graphql-operations-types";

const response = await sdk.graphql?.<GetAccountsQuery, GetAccountsQueryVariables>(GET_ACCOUNTS, variables);
```

Use `NodeOfConnection<T>` to extract the node type from a Connection for cleaner typing:

```typescript
import { type NodeOfConnection } from "@salesforce/sdk-data";

type AccountNode = NodeOfConnection<GetAccountsQuery["uiapi"]["query"]["Account"]>;
```

### Step 5: Validate & Test

1. **Lint**: `npx eslint <file>` from UI bundle dir
2. **codegen**: `npm run graphql:codegen` from UI bundle dir

#### Common Error patterns

| Error Contains | Resolution |
|----------------|------------|
| `Cannot query field` / `ValidationError` | Field name wrong — re-run `graphql-search.sh <Entity>` |
| `Unknown type` | Type name wrong — verify PascalCase entity name via script |
| `Unknown argument` | Argument wrong — check Filter/OrderBy sections in script output |
| `invalid syntax` / `InvalidSyntax` | Fix syntax per error message |
| `VariableTypeMismatch` / `UnknownType` | Correct argument type from schema |
| `invalid cross reference id` | Entity deleted — ask for valid Id |
| `OperationNotSupported` | Check object availability and API version |
| `is not currently available in mutation results` | Remove field from mutation output |
| `Cannot invoke JsonElement.isJsonObject()` | Use API version 64+ for update mutation `Record` selection |

**On PARTIAL** If a mutation returns both data and errors (partial success): Report inaccessible fields, explain they cannot be in mutation output, offer to remove them. **Wait for user consent** before changing.

---

## UI Bundle Integration (React)

Two integration patterns:

### Pattern 1 — External `.graphql` file (complex queries)

**One operation per `.graphql` file.** Each file contains exactly one `query` or `mutation` (plus its fragments). Do not combine multiple operations in a single file.

```typescript
import { createDataSDK, type NodeOfConnection } from "@salesforce/sdk-data";
import MY_QUERY from "./query/myQuery.graphql?raw"; // ?raw suffix required
import type { GetMyDataQuery, GetMyDataQueryVariables } from "../graphql-operations-types";

const sdk = await createDataSDK();
const response = await sdk.graphql?.<GetMyDataQuery, GetMyDataQueryVariables>(MY_QUERY, variables);
```

After creating/changing `.graphql` files, run `npm run graphql:codegen` to generate types into `src/api/graphql-operations-types.ts`.

### Pattern 2 — Inline `gql` tag (simple queries)

**Must use `gql`** — plain template strings bypass ESLint schema validation.

```typescript
import { createDataSDK, gql } from "@salesforce/sdk-data";
import type { GetAccountsQuery } from "../graphql-operations-types";

const GET_ACCOUNTS = gql`
  query GetAccounts {
    uiapi {
      query {
        Account(first: 10) {
          edges { node { Id Name @optional { value } } }
        }
      }
    }
  }
`;

const sdk = await createDataSDK();
const response = await sdk.graphql?.<GetAccountsQuery>(GET_ACCOUNTS);
```

### Error Handling

```typescript
// Strict (default) — any errors = failure
if (response?.errors?.length) {
  throw new Error(response.errors.map(e => e.message).join("; "));
}

// Tolerant — log errors, use available data
if (response?.errors?.length) {
  console.warn("GraphQL partial errors:", response.errors);
}

// Discriminated — fail only when no data returned
if (!response?.data && response?.errors?.length) {
  throw new Error(response.errors.map(e => e.message).join("; "));
}

const accounts = response?.data?.uiapi?.query?.Account?.edges?.map(e => e.node) ?? [];
```

---

## REST API Patterns

Use `sdk.fetch` when GraphQL is insufficient. See the [Supported APIs](#supported-apis) table for the full allowlist.

```typescript
declare const __SF_API_VERSION__: string;
const API_VERSION = typeof __SF_API_VERSION__ !== "undefined" ? __SF_API_VERSION__ : "65.0";

// Connect — file upload config
const res = await sdk.fetch?.(`/services/data/v${API_VERSION}/connect/file/upload/config`);

// Apex REST (no version in path)
const res = await sdk.fetch?.("/services/apexrest/auth/login", {
  method: "POST",
  body: JSON.stringify({ email, password }),
  headers: { "Content-Type": "application/json" },
});

// UI API — record with metadata (prefer GraphQL for simple reads)
const res = await sdk.fetch?.(`/services/data/v${API_VERSION}/ui-api/records/${recordId}`);

// Einstein LLM
const res = await sdk.fetch?.(`/services/data/v${API_VERSION}/einstein/llm/prompt/generations`, {
  method: "POST",
  body: JSON.stringify({ promptTextorId: prompt }),
});
```

**Current user**: Do not use Chatter (`/chatter/users/me`). Use GraphQL instead:

```typescript
const GET_CURRENT_USER = gql`
  query CurrentUser {
    uiapi { currentUser { Id Name { value } } }
  }
`;
const response = await sdk.graphql?.(GET_CURRENT_USER);
```

---

## Directory Structure

```
<project-root>/                              ← SFDX project root
├── schema.graphql                           ← grep target (lives here)
├── sfdx-project.json
├── scripts/graphql-search.sh                ← schema lookup script
└── force-app/main/default/uiBundles/<app-name>/  ← UI bundle dir
    ├── package.json                         ← npm scripts
    └── src/
```

| Command | Run From | Why |
|---------|----------|-----|
| `npm run graphql:schema` | UI bundle dir | Script in UI bundle's package.json |
| `npm run graphql:codegen` | UI bundle dir | Generate GraphQL types |
| `npx eslint <file>` | UI bundle dir | Reads eslint.config.js |
| `bash scripts/graphql-search.sh <Entity>` | project root | Schema lookup |

---

## Quick Reference

### Schema Lookup (from project root)

Run the search script to get all relevant schema info in one step:

```bash
bash scripts/graphql-search.sh <EntityName>
```

| Script Output Section | Used For |
|-----------------------|----------|
| Type definition | Field names, parent/child relationships |
| Filter options | `where:` conditions |
| Sort options | `orderBy:` |
| CreateRepresentation | Create mutation field list |
| UpdateRepresentation | Update mutation field list |

### Error Categories

| Error Contains | Resolution |
|----------------|------------|
| `Cannot query field` | Field name is wrong — run `graphql-search.sh <Entity>` and use the exact name from the Type definition section |
| `Unknown type` | Type name is wrong — run `graphql-search.sh <Entity>` to confirm the correct PascalCase entity name |
| `Unknown argument` | Argument name is wrong — run `graphql-search.sh <Entity>` and check Filter or OrderBy sections |
| `invalid syntax` | Fix syntax per error message |
| `validation error` | Field name is wrong — run `graphql-search.sh <Entity>` to verify |
| `VariableTypeMismatch` | Correct argument type from schema |
| `invalid cross reference id` | Entity deleted — ask for valid Id |

### Checklist

- [ ] All field names verified via search script (Step 2)
- [ ] `@optional` applied to all record fields (reads)
- [ ] Mutations use `uiapi(input: { allOrNone: ... })` wrapper
- [ ] `first:` specified in every query
- [ ] Optional chaining in consuming code
- [ ] `errors` array checked in response handling
- [ ] Lint passes: `npx eslint <file>`

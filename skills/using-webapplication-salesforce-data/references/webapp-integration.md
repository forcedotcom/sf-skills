# Webapp Integration

## When to Use

This guide applies when integrating GraphQL queries into a React webapp using `createDataSDK` + codegen from `@salesforce/sdk-data`.

## Core Types & Function Signatures

### createDataSDK and graphql

```typescript
import { createDataSDK } from "@salesforce/sdk-data";

const sdk = await createDataSDK();
const response = await sdk.graphql?.<ResponseType, VariablesType>(query, variables);
```

`createDataSDK()` returns a `DataSDK` instance. The `graphql` method uses optional chaining (`?.`) because not all surfaces support GraphQL.

### gql Template Tag

```typescript
import { gql } from "@salesforce/sdk-data";

const MY_QUERY = gql`
  query MyQuery {
    uiapi { ... }
  }
`;
```

The `gql` tag enables ESLint validation against the schema. Plain template strings bypass validation.

### NodeOfConnection

```typescript
import { type NodeOfConnection } from "@salesforce/sdk-data";

type AccountNode = NodeOfConnection<GetHighRevenueAccountsQuery["uiapi"]["query"]["Account"]>;
```

Use `NodeOfConnection` to extract the node type from a Connection type for cleaner typing.

## Query Patterns

Choose the pattern based on query complexity:

- **Pattern 1 — External `.graphql` file**: Recommended for complex queries with variables, fragments, or shared across files. Full codegen support, syntax highlighting, shareable. Requires codegen step after changes. Does NOT support dynamic queries.
- **Pattern 2 — Inline `gql` tag**: Recommended for simple queries. Supports dynamic queries (field set varies at runtime). **MUST use `gql` tag** — plain template strings bypass `@graphql-eslint` validation.

## Pattern 1: External .graphql File

Create a `.graphql` file, run `npm run graphql:codegen`, import with `?raw` suffix, and use generated types.

**Required imports:**

```typescript
import { createDataSDK, type NodeOfConnection } from "@salesforce/sdk-data";
import MY_QUERY from "./query/myQuery.graphql?raw"; // ?raw suffix required
import type { GetMyDataQuery, GetMyDataQueryVariables } from "../graphql-operations-types";
```

**Example usage:**

```typescript
const sdk = await createDataSDK();
const response = await sdk.graphql?.<GetMyDataQuery, GetMyDataQueryVariables>(
  MY_QUERY,
  variables
);

if (response?.errors?.length) {
  throw new Error(response.errors.map((e) => e.message).join("; "));
}

const nodes = response?.data?.uiapi?.query?.EntityName?.edges?.map((e) => e.node) ?? [];
```

## Pattern 2: Inline gql Tag

**Required imports:**

```typescript
import { createDataSDK, gql } from "@salesforce/sdk-data";
import { type CurrentUserQuery } from "../graphql-operations-types";

const MY_QUERY = gql`
  query CurrentUser {
    uiapi { ... }
  }
`;
```

> **MUST use `gql` tag** — plain template strings bypass the `@graphql-eslint` processor entirely, meaning no lint validation against the schema.

## Error Handling Strategies

**Strategy A — Strict (default):** Treat any errors as failure.

```typescript
if (response?.errors?.length) {
  throw new Error(response.errors.map((e) => e.message).join("; "));
}
const result = response?.data;
```

**Strategy B — Tolerant:** Log errors but use available data.

```typescript
if (response?.errors?.length) {
  console.warn("GraphQL partial errors:", response.errors);
}
const result = response?.data;
```

**Strategy C — Discriminated:** Fail only when no data is returned. Useful for mutations where some return fields may be inaccessible.

```typescript
if (!response?.data && response?.errors?.length) {
  throw new Error(response.errors.map((e) => e.message).join("; "));
}
const result = response?.data;
```

Responses follow `uiapi.query.ObjectName.edges[].node`; fields use `{ value }`.

## Conditional Field Selection

For dynamic fieldsets with **known** fields, use `@include(if: $condition)` and `@skip(if: $condition)` directives in `.graphql` files. See GraphQL spec for details.

## ESLint Validation

After writing the query into a source file, validate it against the schema:

```bash
# Run from webapp dir (force-app/main/default/webapplications/<app-name>/)
npx eslint <path-to-file-containing-query>
```

**How it works:** The ESLint config uses `@graphql-eslint/eslint-plugin` with its `processor`, which extracts GraphQL operations from `gql` template literals in `.ts`/`.tsx` files and validates the extracted `.graphql` virtual files against `schema.graphql`.

**Rules enforced:** `no-anonymous-operations`, `no-duplicate-fields`, `known-fragment-names`, `no-undefined-variables`, `no-unused-variables`

**On failure:** Fix the reported issues, re-run `npx eslint <file>` until clean, then proceed to testing.

> **Prerequisites**: The `schema.graphql` file must exist and project dependencies must be installed (`npm install`).

## Codegen

Generate TypeScript types from `.graphql` files and inline `gql` queries:

```bash
# Run from webapp dir (force-app/main/default/webapplications/<app-name>/)
npm run graphql:codegen
```

Output: `src/api/graphql-operations-types.ts`

Naming conventions:
- `<OperationName>Query` / `<OperationName>Mutation` — response types
- `<OperationName>QueryVariables` / `<OperationName>MutationVariables` — variable types

## Anti-Patterns

### Direct API Calls

```typescript
// NOT RECOMMENDED: Direct axios/fetch calls for GraphQL
// PREFERRED: Use the Data SDK
const sdk = await createDataSDK();
const response = await sdk.graphql?.<ResponseType>(query, variables);
```

### Missing Type Definitions

```typescript
// NOT RECOMMENDED: Untyped GraphQL calls
// PREFERRED: Provide response type
const response = await sdk.graphql?.<GetMyDataQuery>(query);
```

### Plain String Queries (Without gql Tag)

```typescript
// NOT RECOMMENDED: Plain strings bypass ESLint validation
const query = `query { ... }`;

// PREFERRED: Use gql tag for inline queries
const QUERY = gql`query { ... }`;
```

## Quality Checklists

### For Pattern 1 (.graphql files):

1. [ ] All field names verified via schema search script
2. [ ] Create `.graphql` file for the query/mutation
3. [ ] Run `npm run graphql:codegen` to generate types
4. [ ] Import query with `?raw` suffix
5. [ ] Import generated types from `graphql-operations-types.ts`
6. [ ] Use `sdk.graphql?.<ResponseType>()` with proper generic
7. [ ] Handle `response.errors` and destructure `response.data`
8. [ ] Use `NodeOfConnection` for cleaner node types when needed
9. [ ] Run `npx eslint <file>` from webapp dir — fix all GraphQL errors

### For Pattern 2 (inline with gql):

1. [ ] All field names verified via schema search script
2. [ ] Define query using `gql` template tag (NOT a plain string)
3. [ ] Ensure query name matches generated types in `graphql-operations-types.ts`
4. [ ] Import generated types for the query
5. [ ] Use `sdk.graphql?.<ResponseType>()` with proper generic
6. [ ] Handle `response.errors` and destructure `response.data`
7. [ ] Run `npx eslint <file>` from webapp dir — fix all GraphQL errors

### General:

- [ ] Lint validation passes (`npx eslint <file>` reports no GraphQL errors)
- [ ] Query field names match the schema exactly (case-sensitive)
- [ ] Response type generic is provided to `sdk.graphql?.<T>()`
- [ ] Optional chaining is used for nested response data

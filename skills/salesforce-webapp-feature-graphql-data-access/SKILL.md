---
name: salesforce-webapp-feature-graphql-data-access
description: Add or modify Salesforce GraphQL data access code. Use when the user asks to fetch, query, or mutate Salesforce data, or add a GraphQL operation for an object like Account, Contact, or Opportunity.
---

# GraphQL Data Access

Add or modify Salesforce GraphQL data access code using `getDataSDK()` + `data.graphql?.()` and codegen tooling.

## When to Use

- User asks to "fetch data from Salesforce"
- User asks to "query" or "mutate" Salesforce records
- User wants to add a new GraphQL operation (query or mutation)
- User asks to add data access for a Salesforce object (Account, Contact, Opportunity, etc.)

## Prerequisites

The base React app (`base-react-app`) ships with all GraphQL dependencies and tooling pre-configured:

- `@salesforce/sdk-data` — runtime SDK for `getDataSDK` and `gql`
- `@graphql-codegen/cli` + plugins — type generation from `.graphql` files and inline `gql` queries
- `@graphql-eslint/eslint-plugin` — linting for `.graphql` files and `gql` template literals
- `graphql` — shared by codegen, ESLint, and schema introspection

Before using this skill, ensure:

1. The `@salesforce/sdk-data` package is available (provides `getDataSDK`, `gql`, `NodeOfConnection`)
2. A `schema.graphql` file exists at the project root. If missing, generate it:
   ```bash
   npm run graphql:schema
   ```

## npm Scripts

The base app provides two npm scripts for GraphQL tooling:

- **`npm run graphql:schema`** — Downloads the full GraphQL schema from a connected Salesforce org via introspection. Outputs `schema.graphql` to the project root.
- **`npm run graphql:codegen`** — Generates TypeScript types from `.graphql` files and inline `gql` queries. Outputs to `src/api/graphql-operations-types.ts`.

## Workflow

### Step 1: Explore the Schema

Before writing any query, verify the target object and its fields exist in the schema.

See `docs/explore-schema.md` for detailed guidance on exploring the Salesforce GraphQL schema.

Key actions:

- Search `schema.graphql` for `type <ObjectName> implements Record` to find available fields
- Search for `input <ObjectName>_Filter` for filter options
- Search for `input <ObjectName>_OrderBy` for sorting options
- For mutations: search for `input <ObjectName>CreateInput` or `<ObjectName>UpdateInput`

### Step 2: Choose the Query Pattern

**Pattern 1 — External `.graphql` file** (recommended for complex queries):

- Queries with variables, fragments, or shared across files
- Enables full codegen type generation
- See example: `api/utils/accounts.ts` + `api/utils/query/highRevenueAccountsQuery.graphql`

**Pattern 2 — Inline `gql` tag** (recommended for simple queries):

- Simple queries without variables
- Colocated with usage code
- See example: `api/utils/user.ts`

### Step 3: Write the Query

For **Pattern 1**:

1. Create a `.graphql` file under `src/api/utils/query/`
2. Follow UIAPI structure: `query { uiapi { query { ObjectName(...) { edges { node { ... } } } } } }`
3. For mutations, see `docs/generate-mutation-query.md`
4. For read queries, see `docs/generate-read-query.md`

For **Pattern 2**:

1. Define query inline using the `gql` template tag
2. Ensure the query name matches what codegen expects

### Step 4: Generate Types

```bash
npm run graphql:codegen
```

This updates `src/api/graphql-operations-types.ts` with:

- `<OperationName>Query` or `<OperationName>Mutation` — response type
- `<OperationName>QueryVariables` or `<OperationName>MutationVariables` — input variables type

### Step 5: Implement the Data Access Function

```typescript
// Pattern 1
import { getDataSDK, type NodeOfConnection } from "@salesforce/sdk-data";
import MY_QUERY from "./query/myQuery.graphql?raw";
import type { GetMyDataQuery, GetMyDataQueryVariables } from "../graphql-operations-types";

type MyNode = NodeOfConnection<GetMyDataQuery["uiapi"]["query"]["MyObject"]>;

export async function getMyData(variables: GetMyDataQueryVariables): Promise<MyNode[]> {
  const data = await getDataSDK();
  const response = await data.graphql?.<GetMyDataQuery, GetMyDataQueryVariables>(
    MY_QUERY,
    variables,
  );

  if (response?.errors?.length) {
    const errorMessages = response.errors.map((e) => e.message).join("; ");
    throw new Error(`GraphQL Error: ${errorMessages}`);
  }

  return response?.data?.uiapi?.query?.MyObject?.edges?.map((edge) => edge?.node) || [];
}
```

```typescript
// Pattern 2
import { getDataSDK, gql } from "@salesforce/sdk-data";
import type { MySimpleQuery } from "../graphql-operations-types";

const MY_QUERY = gql`
  query MySimple {
    uiapi { ... }
  }
`;

export async function getSimpleData(): Promise<SomeType> {
  const data = await getDataSDK();
  const response = await data.graphql?.<MySimpleQuery>(MY_QUERY);
  // check response.errors, then extract response.data
}
```

### Step 6: Verify

- [ ] Query field names match the schema exactly (case-sensitive)
- [ ] Response type generic is provided to `data.graphql?.<T>()`
- [ ] Optional chaining is used for nested response data
- [ ] Pattern 1: `.graphql` file imported with `?raw` suffix
- [ ] Pattern 2: Query uses `gql` tag (not plain string)
- [ ] Generated types imported from `graphql-operations-types.ts`

## Reference

- Schema exploration: `docs/explore-schema.md`
- Read query generation: `docs/generate-read-query.md`
- Mutation query generation: `docs/generate-mutation-query.md`
- Shared GraphQL schema types: `docs/shared-schema.graphqls`
- Schema download: `npm run graphql:schema` (in the base app)
- Type generation: `npm run graphql:codegen` (in the base app)

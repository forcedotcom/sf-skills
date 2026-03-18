---
name: using-graphql
description: Salesforce GraphQL data access. Use when the user asks to fetch, query, or mutate Salesforce data, or add a GraphQL operation for an object like Account, Contact, or Opportunity.
paths:
  - "**/*.ts"
  - "**/*.tsx"
  - "**/*.graphql"
---

# Salesforce GraphQL

Guidance for querying and mutating Salesforce data via the Salesforce GraphQL API. Use `createDataSDK()` + `sdk.graphql?.()` and codegen tooling.

## When to Use

- User asks to "fetch data from Salesforce"
- User asks to "query" or "mutate" Salesforce records
- User wants to add a new GraphQL operation (query or mutation)
- User asks to add data access for a Salesforce object (Account, Contact, Opportunity, etc.)

## Schema Access Policy (GREP ONLY)

> **GREP ONLY** — The `schema.graphql` file is very large (~265,000+ lines). All schema lookups **MUST** use the grep-only commands defined in the `exploring-graphql-schema` skill. Do NOT open, read, stream, or parse `./schema.graphql` with any tool other than grep.

## Directory Context

The generated app has a two-level directory structure. Commands must run from the correct directory.

```
<project-root>/                                            ← SFDX project root
├── schema.graphql                                         ← grep target
├── sfdx-project.json
└── force-app/main/default/webapplications/<app-name>/     ← webapp dir
    ├── package.json         (npm scripts: graphql:schema, graphql:codegen, lint)
    ├── eslint.config.js     (schema ref: ../../../../../schema.graphql)
    ├── codegen.yml          (schema ref: ../../../../../schema.graphql)
    └── src/                 (source code, .graphql query files)
```

| Command                   | Run from         | Why                                    |
| ------------------------- | ---------------- | -------------------------------------- |
| `npm run graphql:schema`  | **webapp dir**   | Script is in webapp's `package.json`   |
| `npm run graphql:codegen` | **webapp dir**   | Reads `codegen.yml` in webapp dir       |
| `npx eslint <file>`      | **webapp dir**   | Reads `eslint.config.js` in webapp dir |
| `grep ... schema.graphql` | **project root** | `schema.graphql` lives at project root |
| `sf api request graphql` | **project root** | Needs `sfdx-project.json`              |

> **Wrong directory = silent failures.** `npm run graphql:schema` from the project root will fail with "missing script." `grep ./schema.graphql` from the webapp dir will fail with "no such file."

## Prerequisites

The base React app (`base-react-app`) ships with all GraphQL dependencies and tooling pre-configured:

- `@salesforce/sdk-data` — runtime SDK for `createDataSDK` and `gql`
- `@graphql-codegen/cli` + plugins — type generation from `.graphql` files and inline `gql` queries
- `@graphql-eslint/eslint-plugin` — validates `.graphql` files and `gql` template literals against `schema.graphql` (used as a query validation gate — see Step 6)
- `graphql` — shared by codegen, ESLint, and schema introspection

Before using this skill, ensure:

1. The `@salesforce/sdk-data` package is available (provides `createDataSDK`, `gql`, `NodeOfConnection`)
2. A `schema.graphql` file exists at the project root. If missing, generate it:
   ```bash
   # Run from webapp dir (force-app/main/default/webapplications/<app-name>/)
   npm run graphql:schema
   ```

## npm Scripts

- **`npm run graphql:schema`** — _(run from webapp dir)_ Downloads the full GraphQL schema from a connected Salesforce org via introspection. Outputs `schema.graphql` to the project root.
- **`npm run graphql:codegen`** — _(run from webapp dir)_ Generates TypeScript types from `.graphql` files and inline `gql` queries. Outputs to `src/api/graphql-operations-types.ts`.

## Workflow

### Step 1: Download Schema

Ensure `schema.graphql` exists at the project root. If missing, run `npm run graphql:schema` from the webapp dir.

### Step 2: Explore the Schema (grep-only)

Before writing any query, verify the target object and its fields exist in the schema.

**Invoke the `exploring-graphql-schema` skill** for the full exploration workflow and **mandatory grep-only access policy**.

> **GREP ONLY** — All schema lookups MUST use the grep commands defined in the `exploring-graphql-schema` skill. Do NOT open, read, stream, or parse `./schema.graphql` with any tool other than grep.

Key actions (all via grep):

- `type <ObjectName> implements Record` — find available fields
- `input <ObjectName>_Filter` — find filter options
- `input <ObjectName>_OrderBy` — find sorting options
- `input <ObjectName>CreateInput` / `<ObjectName>UpdateInput` — find mutation input types

### Step 3: Choose the Query Pattern

**Pattern 1 — External `.graphql` file** (recommended for complex queries):

- Queries with variables, fragments, or shared across files
- Full codegen support, syntax highlighting, shareable
- Requires codegen step after changes
- See example: `api/utils/accounts.ts` + `api/utils/query/highRevenueAccountsQuery.graphql`

**Pattern 2 — Inline `gql` tag** (recommended for simple queries):

- Simple queries without variables; colocated with usage code
- Supports dynamic queries (field set varies at runtime)
- **MUST use `gql` tag** — plain template strings bypass `@graphql-eslint` validation
- See example: `api/utils/user.ts`

### Step 4: Write the Query

For **Pattern 1**:

1. Create a `.graphql` file under `src/api/utils/query/`
2. Follow UIAPI structure: `query { uiapi { query { ObjectName(...) { edges { node { ... } } } } } }`
3. For mutations, invoke the `generating-graphql-mutation-query` skill
4. For read queries, invoke the `generating-graphql-read-query` skill

For **Pattern 2**:

1. Define query inline using the `gql` template tag
2. Ensure the query name matches what codegen expects

### Step 5: Test Queries Against Live Org

Use the testing workflows in the `generating-graphql-read-query` and `generating-graphql-mutation-query` skills to validate queries against the connected org before integrating into the app.

### Step 6: Generate Types

```bash
# Run from webapp dir (force-app/main/default/webapplications/<app-name>/)
npm run graphql:codegen
```

This updates `src/api/graphql-operations-types.ts` with `<OperationName>Query`/`<OperationName>Mutation` and `<OperationName>QueryVariables`/`<OperationName>MutationVariables`.

### Step 7: Lint Validate

Run ESLint on the file containing the query to validate it against the schema **before** any live testing:

```bash
# Run from webapp dir
npx eslint <path-to-file>
```

The `@graphql-eslint/eslint-plugin` processor extracts GraphQL from `gql` template literals and validates them against `schema.graphql`. Fix all ESLint errors before proceeding.

### Step 8: Implement and Verify

Implement the data access function using the pattern below. Use the Quality Checklist before completing.

---

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

### Error Handling

Default: treat any errors as failure (Strategy A). For partial data tolerance, log errors but use data. For mutations where some return fields are inaccessible, use Strategy C (fail only when no data).

```typescript
// Default: strict
if (response?.errors?.length) {
  throw new Error(response.errors.map((e) => e.message).join("; "));
}
const result = response?.data;
```

Responses follow `uiapi.query.ObjectName.edges[].node`; fields use `{ value }`.

### NodeOfConnection

```typescript
import { type NodeOfConnection } from "@salesforce/sdk-data";

type AccountNode = NodeOfConnection<GetHighRevenueAccountsQuery["uiapi"]["query"]["Account"]>;
```

---

## Pattern 1: External .graphql File

Create a `.graphql` file, run `npm run graphql:codegen`, import with `?raw` suffix, and use generated types.

**Required imports:**

```typescript
import { createDataSDK, type NodeOfConnection } from "@salesforce/sdk-data";
import MY_QUERY from "./query/myQuery.graphql?raw"; // ← ?raw suffix required
import type { GetMyDataQuery, GetMyDataQueryVariables } from "../graphql-operations-types";
```

**When to use:** Complex queries with variables, fragments, or shared across files. Does NOT support dynamic queries (field set varies at runtime).

---

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

**When to use:** Simple, colocated queries. Supports dynamic queries (field set varies at runtime).

---

## Conditional Field Selection

For dynamic fieldsets with **known** fields, use `@include(if: $condition)` and `@skip(if: $condition)` in `.graphql` files. See GraphQL spec for details.

---

## Anti-Patterns (Not Recommended)

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

---

## Quality Checklist

> If you have not completed the workflow above, **stop and complete it first**. Invoke the skill workflow before using this checklist.

Before completing GraphQL data access code:

### For Pattern 1 (.graphql files):

1. [ ] All field names verified via grep against `schema.graphql` (invoke `exploring-graphql-schema`)
2. [ ] Create `.graphql` file for the query/mutation
3. [ ] Run `npm run graphql:codegen` to generate types
4. [ ] Import query with `?raw` suffix
5. [ ] Import generated types from `graphql-operations-types.ts`
6. [ ] Use `sdk.graphql?.<ResponseType>()` with proper generic
7. [ ] Handle `response.errors` and destructure `response.data`
8. [ ] Use `NodeOfConnection` for cleaner node types when needed
9. [ ] Run `npx eslint <file>` from webapp dir — fix all GraphQL errors

### For Pattern 2 (inline with gql):

1. [ ] All field names verified via grep against `schema.graphql`
2. [ ] Define query using `gql` template tag (NOT a plain string)
3. [ ] Ensure query name matches generated types in `graphql-operations-types.ts`
4. [ ] Import generated types for the query
5. [ ] Use `sdk.graphql?.<ResponseType>()` with proper generic
6. [ ] Handle `response.errors` and destructure `response.data`
7. [ ] Run `npx eslint <file>` from webapp dir — fix all GraphQL errors

### General:

- [ ] Lint validation passes (`npx eslint <file>` reports no GraphQL errors)
- [ ] Query field names match the schema exactly (case-sensitive, confirmed via grep)
- [ ] Response type generic is provided to `sdk.graphql?.<T>()`
- [ ] Optional chaining is used for nested response data

---

## Reference

- Schema exploration: invoke the `exploring-graphql-schema` skill
- Read query generation: invoke the `generating-graphql-read-query` skill
- Mutation query generation: invoke the `generating-graphql-mutation-query` skill
- Shared GraphQL schema types: `shared-schema.graphqls` (in this skill directory)
- Schema download: `npm run graphql:schema` (run from webapp dir)
- Type generation: `npm run graphql:codegen` (run from webapp dir)

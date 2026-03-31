---
name: using-ui-bundle-salesforce-data
description: "Salesforce data access for reading, writing, and querying records via REST, GraphQL, Apex, or Platform SDK. Use when the user wants to fetch, search, filter, sort, display, create, update, delete, or attach files to Salesforce records (standard objects like Accounts, Contacts, Opportunities, Cases, Quotes, or any custom object) in a UI bundle or UI component (React, Angular, Vue, etc.); call Chatter, Connect, or Apex REST APIs; or invoke AuraEnabled Apex methods from an external app. Does not apply to authentication/OAuth setup, schema changes (adding fields, relationships), Bulk/Tooling/Metadata API usage, declarative automation (Flows, Process Builder), general LWC/Apex coding guidance without a specific data operation, or Salesforce admin/configuration tasks."
---

# Salesforce Data Access

## When to Use

Use this skill when the user wants to:

- **Fetch or display Salesforce data** — Query records (Account, Contact, Opportunity, custom objects) to show in a component
- **Create, update, or delete records** — Perform mutations on Salesforce data
- **Add data fetching to a component** — Wire up a React component to Salesforce data
- **Call REST APIs** — Use Connect REST, Apex REST, or UI API endpoints
- **Explore the org schema** — Discover available objects, fields, or relationships

## Data SDK Requirement

> **All Salesforce data access MUST use the Data SDK** (`@salesforce/sdk-data`). The SDK handles authentication, CSRF, and base URL resolution.

```typescript
import { createDataSDK, gql } from "@salesforce/sdk-data";

const sdk = await createDataSDK();

// GraphQL for record queries/mutations (PREFERRED)
const response = await sdk.graphql?.<ResponseType>(query, variables);

// REST for Connect REST, Apex REST, UI API (when GraphQL insufficient)
const res = await sdk.fetch?.("/services/apexrest/my-resource");
```

**Always use optional chaining** (`sdk.graphql?.()`, `sdk.fetch?.()`) — these methods may be undefined in some surfaces.

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

1. **Schema is the single source of truth** — Every entity name, field name, and type must be confirmed via the schema search script before use in a query. Never guess — Salesforce field names are case-sensitive, relationships may be polymorphic, and custom objects use suffixes (`__c`, `__e`). See [Schema Introspection](references/schema-introspection.md) for entity identification and iterative lookup procedures.

2. **`@optional` on all record fields** (read queries) — Salesforce field-level security (FLS) causes queries to fail entirely if the user lacks access to even one field. The `@optional` directive (v65+) tells the server to omit inaccessible fields instead of failing. Apply it to every scalar field, parent relationship, and child relationship. Consuming code must use optional chaining (`?.`) and nullish coalescing (`??`).

3. **Correct mutation syntax** — Mutations wrap under `uiapi(input: { allOrNone: true/false })`, not bare `uiapi { ... }`. Always set `allOrNone` explicitly. Output fields cannot include child relationships or navigated reference fields. See [Mutation Query Generation](references/mutation-query-generation.md).

4. **Explicit pagination** — Always include `first:` in every query. If omitted, the server silently defaults to 10 records. Include `pageInfo { hasNextPage endCursor }` for any query that may need pagination.

5. **SOQL-derived execution limits** — Max 10 subqueries per request, max 5 levels of child-to-parent traversal, max 1 level of parent-to-child (no grandchildren), max 2,000 records per subquery. If a query would exceed these, split into multiple requests.

6. **HTTP 200 does not mean success** — Salesforce returns HTTP 200 even when operations fail. Always parse the `errors` array in the response body.

---

## GraphQL Workflow

### Step 1: Acquire Schema

The `schema.graphql` file (265K+ lines) is the source of truth. **Never open or parse it directly.**

1. Check if `schema.graphql` exists at the SFDX project root
2. If missing, run from the **UI bundle dir**: `npm run graphql:schema`
3. Custom objects appear only after metadata is deployed

### Step 2: Look Up Entity Schema

Map user intent to PascalCase names ("accounts" → `Account`), then **run the search script from the project root**:

```bash
# Look up all relevant schema info for one or more entities
bash scripts/graphql-search.sh Account

# Multiple entities at once
bash scripts/graphql-search.sh Account Contact Opportunity
```

The script outputs five sections per entity:
1. **Type definition** — all queryable fields and relationships
2. **Filter options** — available fields for `where:` conditions
3. **Sort options** — available fields for `orderBy:`
4. **Create input** — fields accepted by create mutations
5. **Update input** — fields accepted by update mutations

Use this output to determine exact field names before writing any query or mutation. **Maximum 2 script runs.** If the entity still can't be found, ask the user — the object may not be deployed. For entity identification procedures (`_Record` suffix, `__c` conventions) and iterative introspection cycles, see [Schema Introspection](references/schema-introspection.md).

### Step 3: Generate Query

Use the templates below. Every field name **must** be verified from the script output in Step 2. For detailed generation rules, filtering, pagination, ordering, semi-joins, and field value wrappers, see [Read Query Generation](references/read-query-generation.md). For mutation chaining, input/output constraints, and transactional semantics, see [Mutation Query Generation](references/mutation-query-generation.md).

#### Read Query Template

```graphql
query GetAccounts {
  uiapi {
    query {
      Account(where: { Industry: { eq: "Technology" } }, first: 10) {
        edges {
          node {
            Id
            Name @optional { value }
            Industry @optional { value }
            # Parent relationship
            Owner @optional { Name { value } }
            # Child relationship
            Contacts @optional {
              edges { node { Name @optional { value } } }
            }
          }
        }
      }
    }
  }
}
```

**FLS Resilience**: Apply `@optional` to all record fields. The server omits inaccessible fields instead of failing. Consuming code must use optional chaining:

```typescript
const name = node.Name?.value ?? "";
```

#### Mutation Template

```graphql
mutation CreateAccount($input: AccountCreateInput!) {
  uiapi(input: { allOrNone: true }) {
    AccountCreate(input: $input) {
      Record { Id Name { value } }
    }
  }
}
```

**Mutation constraints:**
- Create: Include required fields, only `createable` fields, no child relationships
- Update: Include `Id`, only `updateable` fields
- Delete: Include `Id` only

#### Object Metadata & Picklist Values

Use `uiapi { objectInfos(...) }` to fetch field metadata or picklist values. Pass **either** `apiNames` or `objectInfoInputs` — never both in the same query.

**Object metadata** (field labels, data types, CRUD flags):

```typescript
const GET_OBJECT_INFO = gql`
  query GetObjectInfo($apiNames: [String!]!) {
    uiapi {
      objectInfos(apiNames: $apiNames) {
        ApiName
        label
        labelPlural
        fields {
          ApiName
          label
          dataType
          updateable
          createable
        }
      }
    }
  }
`;

const sdk = await createDataSDK();
const response = await sdk.graphql?.(GET_OBJECT_INFO, { apiNames: ["Account"] });
const objectInfos = response?.data?.uiapi?.objectInfos ?? [];
```

**Picklist values** (use `objectInfoInputs` + `... on PicklistField` inline fragment):

```typescript
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
              picklistValues {
                label
                value
              }
            }
          }
        }
      }
    }
  }
`;

const response = await sdk.graphql?.(GET_PICKLIST_VALUES, {
  objectInfoInputs: [{ objectApiName: "Account" }],
});
const fields = response?.data?.uiapi?.objectInfos?.[0]?.fields ?? [];
```

### Step 4: Validate & Test

1. **Lint**: `npx eslint <file>` from UI bundle dir
2. **Test**: Ask user before testing. For mutations, request input values — never fabricate data.

**If ESLint reports a GraphQL error** (e.g. `Cannot query field`, `Unknown type`, `Unknown argument`), the field or type name is wrong. Re-run the schema search script to find the correct name — do not guess:

```bash
# From project root — re-check the entity that caused the error
bash scripts/graphql-search.sh <EntityName>
```

Then fix the query using the exact names from the script output. For detailed error categories, status handling, and retry strategy, see [Query Testing](references/query-testing.md).

---

## UI Bundle Integration (React)

Two integration patterns are available:

- **Pattern 1 — External `.graphql` file** (recommended for complex queries): Create a `.graphql` file, run `npm run graphql:codegen`, import with `?raw` suffix
- **Pattern 2 — Inline `gql` tag** (for simple queries): Use the `gql` template tag from `@salesforce/sdk-data`. **Must use `gql`** — plain template strings bypass ESLint schema validation.

```typescript
import { createDataSDK, gql } from "@salesforce/sdk-data";

const GET_ACCOUNTS = gql`
  query GetAccounts {
    uiapi {
      query {
        Account(first: 10) {
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
`;

const sdk = await createDataSDK();
const response = await sdk.graphql?.(GET_ACCOUNTS);
if (response?.errors?.length) {
  throw new Error(response.errors.map(e => e.message).join("; "));
}
const accounts = response?.data?.uiapi?.query?.Account?.edges?.map(e => e.node) ?? [];
```

For detailed patterns (external .graphql files, codegen, error handling strategies, quality checklists), see [UI Bundle Integration](references/ui-bundle-integration.md).

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
└── force-app/main/default/uiBundles/<app-name>/  ← UI bundle dir
    ├── package.json                         ← npm scripts
    └── src/
```

| Command | Run From | Why |
|---------|----------|-----|
| `npm run graphql:schema` | UI bundle dir | Script in UI bundle's package.json |
| `npx eslint <file>` | UI bundle dir | Reads eslint.config.js |
| `bash scripts/graphql-search.sh <Entity>` | project root | Schema lookup |
| `sf api request rest` | project root | Needs sfdx-project.json |

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

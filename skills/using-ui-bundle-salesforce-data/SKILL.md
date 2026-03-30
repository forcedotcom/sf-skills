---
name: using-ui-bundle-salesforce-data
description: "Guides querying, mutating, and displaying Salesforce records (standard or custom objects) in React, Angular, or Vue UI bundles via @salesforce/sdk-data, GraphQL, or REST — includes a mandatory schema lookup that prevents silent runtime failures. Use when building data-fetching code, wiring pagination/filtering/sorting, calling Apex REST or Einstein LLM, fetching picklist values or object metadata, or debugging GraphQL errors in a UI bundle. Not for LWC @wire patterns, Flows, Bulk API, Apex triggers, or metadata deployment."
---

# Salesforce Data Access

## When This Skill Activates

- User wants to query, create, update, or delete Salesforce records from a UI bundle
- User needs to wire Salesforce data into React, Angular, or Vue components
- User asks about `@salesforce/sdk-data`, GraphQL queries, or Apex REST calls from a UI
- User is debugging a Salesforce GraphQL error (`Cannot query field`, HTTP 200 failures)
- User needs picklist values, object metadata, or current user info in a UI bundle
- User wants to call Einstein LLM or Connect REST from a UI bundle

## Preconditions

| Requirement | Details |
|-------------|---------|
| `@salesforce/sdk-data` installed | The UI bundle must have this package — it handles auth, CSRF, and base URL |
| `schema.graphql` at SFDX project root | Required for schema lookups; generate with `npm run graphql:schema` from the UI bundle dir |
| Custom objects/fields deployed | Custom entities only appear in the schema after metadata deployment and permission set assignment |
| API version v65+ | Required for `@optional` directive (FLS resilience) |
| API version v66+ | Required for GraphQL mutations |

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

## Required Docs

Read the doc file for your task before generating code. These files contain the templates, rules, and detailed patterns that are essential to getting Salesforce GraphQL right — the SKILL.md body gives you the workflow and guardrails, but the docs have the implementation detail you need to produce correct output.

| Task | Read this file | It contains |
|------|---------------|-------------|
| Entity lookup for custom objects, `_Record` suffix, polymorphic fields | `docs/schema-introspection.md` | Entity identification, naming conventions, iterative introspection cycles |
| Generate a read query | `docs/read-query-generation.md` | Read query generation rules, `@optional`/FLS rules, filtering, pagination, ordering, semi-joins, field value wrappers |
| Generate a mutation (create/update/delete) | `docs/mutation-query-generation.md` | Mutation template, input/output constraints, chaining, transactional semantics |
| Test a query or fix query errors | `docs/query-testing.md` | Testing method, error categories, FAILED/PARTIAL status handling, retry protocol |
| Integrate a query into a React component | `docs/ui-bundle-integration.md` | External `.graphql` file vs inline `gql` patterns, codegen, typing, error handling strategies, quality checklists |

---

## GraphQL Non-Negotiable Rules

These rules exist because Salesforce GraphQL has platform-specific behaviors that differ from standard GraphQL. Violations cause silent runtime failures.

1. **Schema is the single source of truth** — Every entity name, field name, and type must be confirmed via the schema search script before use in a query. Never guess — Salesforce field names are case-sensitive, relationships may be polymorphic, and custom objects use suffixes (`__c`, `__e`).

2. **`@optional` on all record fields** (read queries) — Salesforce field-level security (FLS) causes queries to fail entirely if the user lacks access to even one field. The `@optional` directive (v65+) tells the server to omit inaccessible fields instead of failing. Apply it to every scalar field, parent relationship, and child relationship. Consuming code must use optional chaining (`?.`) and nullish coalescing (`??`).

3. **Correct mutation syntax** — Mutations wrap under `uiapi(input: { allOrNone: true/false })`, not bare `uiapi { ... }`. Always set `allOrNone` explicitly. Output fields cannot include child relationships or navigated reference fields.

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

Skipping the schema lookup is the #1 cause of query failures — you guess a field name, the query fails at runtime, and you end up running the script anyway after wasting a round-trip.

Map user intent to PascalCase names ("accounts" → `Account`), then run the search script from the **SFDX project root** (where `schema.graphql` lives):

```bash
# Look up all relevant schema info for one entity
bash skills/using-ui-bundle-salesforce-data/scripts/graphql-search.sh --schema ./schema.graphql Account

# Multiple entities at once
bash skills/using-ui-bundle-salesforce-data/scripts/graphql-search.sh --schema ./schema.graphql Account Contact Opportunity
```

The script outputs seven sections per entity:
1. **Type definition** — all queryable fields and relationships
2. **Filter options** — available fields for `where:` conditions
3. **Sort options** — available fields for `orderBy:`
4. **Create mutation wrapper** — accepted wrapper shape for create mutations
5. **Create mutation fields** — fields accepted by create mutations
6. **Update mutation wrapper** — accepted wrapper shape for update mutations
7. **Update mutation fields** — fields accepted by update mutations

Use this output to determine exact field names before writing any query or mutation. Use at most 2 direct lookup attempts per unresolved entity and at most 3 total introspection cycles across the workflow. If the entity still can't be found, ask the user — the object may not be deployed. If the entity name is ambiguous (custom objects, `_Record` suffix, polymorphic fields), read `docs/schema-introspection.md` now for entity identification and iterative lookup procedures.

> **Stop here if any entity is unresolved.** Do not proceed to Step 3 until every entity and every requested field name is confirmed in the script output. If resolution fails after 2 runs and both naming variations, ask the user — the object may not be deployed.

### Step 3: Generate Query

Every field name must come directly from the Step 2 script output — never from memory or assumption.

**For read queries:** Read `docs/read-query-generation.md` now before writing the query. It contains 15 generation rules, FLS/`@optional` semantics, pagination, ordering, filtering patterns, semi-joins, and field value wrapper types. The inline template below is a starting point — the reference file defines which rules apply.

**For mutations:** Read `docs/mutation-query-generation.md` now before writing the mutation. It contains input/output field constraints, `allOrNone` semantics, and mutation chaining patterns that cannot be reconstructed from the template alone.

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

**Read `docs/query-testing.md` now before testing.** It defines the exact `sf api request rest` command, result status definitions (HTTP 200 ≠ success), FAILED/PARTIAL status handling, and the retry/escalation protocol.

1. **Lint**: `npx eslint <file>` from UI bundle dir
2. **Test**: Ask user before testing. For mutations, request input values — never fabricate data.

**If ESLint reports a GraphQL error** (e.g. `Cannot query field`, `Unknown type`, `Unknown argument`), the field or type name is wrong. Re-run the schema search script to find the correct name — do not guess:

```bash
# From project root — re-check the entity that caused the error
bash skills/using-ui-bundle-salesforce-data/scripts/graphql-search.sh --schema ./schema.graphql <EntityName>
```

Then fix the query using the exact names from the script output.

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

For detailed patterns (external .graphql files, codegen, error handling strategies, quality checklists), **read `docs/ui-bundle-integration.md`**.

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
| `bash skills/using-ui-bundle-salesforce-data/scripts/graphql-search.sh --schema ./schema.graphql <Entity>` | project root | Schema lookup against the current org schema |
| `sf api request rest` | project root | Needs sfdx-project.json |

---

## Quick Reference

### Schema Lookup (from project root)

Run the search script to get all relevant schema info in one step:

```bash
bash skills/using-ui-bundle-salesforce-data/scripts/graphql-search.sh --schema ./schema.graphql <EntityName>
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
| `Cannot query field` | Field name is wrong — run `bash skills/using-ui-bundle-salesforce-data/scripts/graphql-search.sh --schema ./schema.graphql <Entity>` and use the exact name from the Type definition section |
| `Unknown type` | Type name is wrong — run the schema search script to confirm the correct PascalCase entity name |
| `Unknown argument` | Argument name is wrong — run the schema search script and check Filter or OrderBy sections |
| `invalid syntax` | Fix syntax per error message |
| `validation error` | Field name is wrong — run the schema search script to verify |
| `VariableTypeMismatch` | Correct argument type from schema |
| `invalid cross reference id` | Entity deleted — ask for valid Id |

### Checklist

- [ ] Read the applicable reference file before drafting
- [ ] All field names verified via search script (Step 2)
- [ ] `@optional` applied to all record fields (reads)
- [ ] Mutations use `uiapi(input: { allOrNone: ... })` wrapper
- [ ] `first:` specified in every query
- [ ] Optional chaining in consuming code
- [ ] `errors` array checked in response handling
- [ ] Correct testing flow used for the operation type
- [ ] Lint passes: `npx eslint <file>`

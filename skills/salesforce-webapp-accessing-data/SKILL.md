---
name: salesforce-webapp-accessing-data
description: Salesforce data access patterns. Use when adding or modifying any code that fetches data from Salesforce (records, Chatter, Connect API, etc.).
paths:
  - "**/*.ts"
  - "**/*.tsx"
  - "**/*.graphql"
---

# Salesforce Data Access

Guidance for accessing Salesforce data from web apps. **All Salesforce data fetches MUST use the Data SDK** (`@salesforce/sdk-data`). The SDK provides authentication, CSRF handling, and correct base URL resolution — direct `fetch` or `axios` calls bypass these and are not allowed.

## Mandatory: Use the Data SDK

> **Every Salesforce data fetch must go through the Data SDK.** Obtain it via `createDataSDK()`, then use `sdk.graphql?.()` or `sdk.fetch?.()`. Never call `fetch()` or `axios` directly for Salesforce endpoints.

## Optional Chaining and Graceful Handling

**Always use optional chaining** when calling `sdk.graphql` or `sdk.fetch` — these methods may be undefined in some surfaces (e.g., Salesforce ACC, MCP Apps). Handle the case where they are not available gracefully:

```typescript
const sdk = await createDataSDK();

// ✅ Use optional chaining
const response = await sdk.graphql?.(query);

// ✅ Check before using fetch
if (!sdk.fetch) {
  throw new Error("Data SDK fetch is not available in this context");
}
const res = await sdk.fetch(url);
```

For GraphQL, if `sdk.graphql` is undefined, the call returns `undefined` — handle that in your logic (e.g., throw a clear error or return a fallback). For `sdk.fetch`, check availability before calling when the operation is required.

## Preference: GraphQL First

**GraphQL is the preferred method** for querying and mutating Salesforce records. Use it when:

- Querying records (Account, Contact, Opportunity, custom objects)
- Creating, updating, or deleting records (when GraphQL supports the operation)
- Fetching related data, filters, sorting, pagination

**Use `sdk.fetch` only when GraphQL is not sufficient.** For REST API usage, invoke the `fetching-rest-api` skill, which documents:

- Chatter API (e.g., `/services/data/v65.0/chatter/users/me`)
- Connect REST API (e.g., `/services/data/v65.0/connect/file/upload/config`)
- Apex REST (e.g., `/services/apexrest/auth/login`)
- UI API REST (e.g., `/services/data/v65.0/ui-api/records/{recordId}`)
- Einstein LLM Gateway

---

## Getting the SDK

```typescript
import { createDataSDK } from "@salesforce/sdk-data";

const sdk = await createDataSDK();
```

---

## Example 1: GraphQL (Preferred)

For record queries and mutations, use GraphQL via the Data SDK. Invoke the `using-graphql` skill for the full workflow (schema exploration, query authoring, codegen, lint validate).

```typescript
import { createDataSDK, gql } from "@salesforce/sdk-data";
import type { GetAccountsQuery } from "../graphql-operations-types";

const GET_ACCOUNTS = gql`
  query GetAccounts {
    uiapi {
      query {
        Account(first: 10) {
          edges {
            node {
              Id
              Name { value }
            }
          }
        }
      }
    }
  }
`;

export async function getAccounts() {
  const sdk = await createDataSDK();
  const response = await sdk.graphql?.<GetAccountsQuery>(GET_ACCOUNTS);

  if (response?.errors?.length) {
    throw new Error(response.errors.map((e) => e.message).join("; "));
  }

  return response?.data?.uiapi?.query?.Account?.edges?.map((e) => e?.node) ?? [];
}
```

---

## Example 2: Fetch (When GraphQL Is Not Sufficient)

For REST endpoints that have no GraphQL equivalent, use `sdk.fetch`. **Invoke the `fetching-rest-api` skill** for full documentation of Chatter, Connect REST, Apex REST, UI API REST, and Einstein LLM endpoints.

```typescript
import { createDataSDK } from "@salesforce/sdk-data";

declare const __SF_API_VERSION__: string;
const API_VERSION = typeof __SF_API_VERSION__ !== "undefined" ? __SF_API_VERSION__ : "65.0";

export async function getCurrentUser() {
  const sdk = await createDataSDK();
  const response = await sdk.fetch?.(`/services/data/v${API_VERSION}/chatter/users/me`);

  if (!response?.ok) throw new Error(`HTTP ${response?.status}`);
  const data = await response.json();
  return { id: data.id, name: data.name };
}
```

---

## Anti-Patterns (Forbidden)

### Direct fetch to Salesforce

```typescript
// ❌ FORBIDDEN — bypasses Data SDK auth and CSRF
const res = await fetch("/services/data/v65.0/chatter/users/me");
```

### Direct axios to Salesforce

```typescript
// ❌ FORBIDDEN — bypasses Data SDK
const res = await axios.get("/services/data/v65.0/chatter/users/me");
```

### Correct approach

```typescript
// ✅ CORRECT — use Data SDK
const sdk = await createDataSDK();
const res = await sdk.fetch?.("/services/data/v65.0/chatter/users/me");
```

---

## Decision Flow

1. **Need to query or mutate Salesforce records?** → Use GraphQL via the Data SDK. Invoke the `using-graphql` skill.
2. **Need Chatter, Connect REST, Apex REST, UI API REST, or Einstein LLM?** → Use `sdk.fetch`. Invoke the `fetching-rest-api` skill.
3. **Never** use `fetch`, `axios`, or similar directly for Salesforce API calls.

---

## Reference

- GraphQL workflow: invoke the `using-graphql` skill (`.a4drules/skills/using-graphql/`)
- REST API via fetch: invoke the `fetching-rest-api` skill (`.a4drules/skills/fetching-rest-api/`)
- Data SDK package: `@salesforce/sdk-data` (`createDataSDK`, `gql`, `NodeOfConnection`)
- `createRecord` for UI API record creation: `@salesforce/webapp-experimental/api` (uses Data SDK internally)

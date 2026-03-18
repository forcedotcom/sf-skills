---
name: salesforce-webapp-fetching-rest-api
description: REST API usage via the Data SDK fetch method. Use when implementing Chatter, Connect REST, Apex REST, UI API REST, or Einstein LLM calls — only when GraphQL is not sufficient.
paths:
  - "**/*.ts"
  - "**/*.tsx"
  - "**/*.graphql"
---

# Salesforce REST API via Data SDK Fetch

Use `sdk.fetch` from the Data SDK when GraphQL is not sufficient. The SDK applies authentication, CSRF handling, and base URL resolution. **Always use optional chaining** (`sdk.fetch?.()`) and handle the case where `fetch` is not available.

Invoke this skill when you need to call Chatter, Connect REST, Apex REST, UI API REST, or Einstein LLM endpoints.

## API Version

Use the project's API version. It is typically injected as `__SF_API_VERSION__`; fallback to `"65.0"`:

```typescript
declare const __SF_API_VERSION__: string;
const API_VERSION = typeof __SF_API_VERSION__ !== "undefined" ? __SF_API_VERSION__ : "65.0";
```

## Base Path

URLs are relative to the Salesforce API base. The SDK prepends the correct base path. Use paths starting with `/services/...`.

---

## Chatter API

User and collaboration data. No GraphQL equivalent.

| Endpoint | Method | Purpose |
| -------- | ------ | ------- |
| `/services/data/v{version}/chatter/users/me` | GET | Current user (id, name, email, username) |

```typescript
const sdk = await createDataSDK();
const response = await sdk.fetch?.(`/services/data/v${API_VERSION}/chatter/users/me`);

if (!response?.ok) throw new Error(`HTTP ${response?.status}`);
const data = await response.json();
return { id: data.id, name: data.name };
```

---

## Connect REST API

File and content operations.

| Endpoint | Method | Purpose |
| -------- | ------ | ------- |
| `/services/data/v{version}/connect/file/upload/config` | GET | Upload config (token, uploadUrl) for file uploads |

```typescript
const sdk = await createDataSDK();
const configRes = await sdk.fetch?.(`/services/data/v${API_VERSION}/connect/file/upload/config`, {
  method: "GET",
});

if (!configRes?.ok) throw new Error(`Failed to get upload config: ${configRes?.status}`);
const config = await configRes.json();
const { token, uploadUrl } = config;
```

---

## Apex REST

Custom Apex REST resources. Requires corresponding Apex classes in the org. CSRF protection is applied automatically for `services/apexrest` URLs.

| Endpoint | Method | Purpose |
| -------- | ------ | ------- |
| `/services/apexrest/auth/login` | POST | User login |
| `/services/apexrest/auth/register` | POST | User registration |
| `/services/apexrest/auth/forgot-password` | POST | Request password reset |
| `/services/apexrest/auth/reset-password` | POST | Reset password with token |
| `/services/apexrest/auth/change-password` | POST | Change password (authenticated) |
| `/services/apexrest/{resource}` | GET/POST | Custom Apex REST resources |

**Example (login):**

```typescript
const sdk = await createDataSDK();
const response = await sdk.fetch?.("/services/apexrest/auth/login", {
  method: "POST",
  body: JSON.stringify({ email, password, startUrl: "/" }),
  headers: { "Content-Type": "application/json", Accept: "application/json" },
});
```

Apex REST paths do not include the API version.

---

## UI API (REST)

When GraphQL cannot cover the use case. **Prefer GraphQL** when possible.

| Endpoint | Method | Purpose |
| -------- | ------ | ------- |
| `/services/data/v{version}/ui-api/records/{recordId}` | GET | Fetch a single record |

```typescript
const sdk = await createDataSDK();
const response = await sdk.fetch?.(`/services/data/v${API_VERSION}/ui-api/records/${recordId}`);
```

---

## Einstein LLM Gateway

AI features. Requires Einstein API setup.

| Endpoint | Method | Purpose |
| -------- | ------ | ------- |
| `/services/data/v{version}/einstein/llm/prompt/generations` | POST | Generate text from Einstein LLM |

```typescript
const sdk = await createDataSDK();
const response = await sdk.fetch?.(`/services/data/v${API_VERSION}/einstein/llm/prompt/generations`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    additionalConfig: { applicationName: "PromptTemplateGenerationsInvocable" },
    promptTextorId: prompt,
  }),
});

if (!response?.ok) throw new Error(`Einstein LLM failed (${response?.status})`);
const data = await response.json();
return data?.generations?.[0]?.text ?? "";
```

---

## General Pattern

```typescript
import { createDataSDK } from "@salesforce/sdk-data";

const sdk = await createDataSDK();

if (!sdk.fetch) {
  throw new Error("Data SDK fetch is not available in this context");
}

const response = await sdk.fetch(url, {
  method: "GET", // or POST, PUT, PATCH, DELETE
  headers: { "Content-Type": "application/json", Accept: "application/json" },
  body: method !== "GET" ? JSON.stringify(payload) : undefined,
});

if (!response.ok) throw new Error(`HTTP ${response.status}`);
const data = await response.json();
```

---

## Reference

- Parent: `accessing-data` — enforces Data SDK usage for all Salesforce data fetches
- GraphQL: `using-graphql` — use for record queries and mutations when possible
- `createRecord` from `@salesforce/webapp-experimental/api` for UI API record creation (uses SDK internally)

# REST (`sdk.fetch`) & UI bundle integration

Use `sdk.fetch` only when GraphQL doesn't cover the use case. The allowlist is in
[SKILL.md](../SKILL.md#platform-guardrails--never-regress-these) (guardrail 9). Every code shape
here is grounded in shipped consumer code.

## Supported APIs (allowlist)

| API | Method | Endpoints / use case |
|---|---|---|
| GraphQL | `sdk.graphql` | all record queries/mutations via the `uiapi { }` namespace |
| UI API REST | `sdk.fetch` | `/services/data/v{ver}/ui-api/records/{id}` — record metadata when GraphQL insufficient |
| Apex REST | `sdk.fetch` | `/services/apexrest/{resource}` — custom server logic, aggregates, multi-step transactions |
| Connect REST | `sdk.fetch` | `/services/data/v{ver}/connect/file/upload/config` — file upload config |
| Einstein LLM | `sdk.fetch` | `/services/data/v{ver}/einstein/llm/prompt/generations` — AI text generation |

**Not supported:** Enterprise REST query (`/services/data/v*/query` with SOQL — blocked at the
proxy; use GraphQL for reads, Apex REST for server-side SOQL aggregates), Aura-enabled Apex
(`@AuraEnabled` — no invocation path from UI bundles), Chatter API (`/chatter/users/me` — use
`uiapi { currentUser { ... } }`), and any other Salesforce REST endpoint not in the table above.

> `sdk.fetch` is **not cached** — only `sdk.graphql!.query()` participates in the resource
> cache. REST reads hit the network every time.

## `sdk.fetch` patterns

```typescript
declare const __SF_API_VERSION__: string;
const API_VERSION = typeof __SF_API_VERSION__ !== "undefined" ? __SF_API_VERSION__ : "65.0";

// Connect — file upload config
const res = await sdk.fetch!(`/services/data/v${API_VERSION}/connect/file/upload/config`);

// Apex REST (no version in path)
const res = await sdk.fetch!("/services/apexrest/auth/login", {
  method: "POST",
  body: JSON.stringify({ email, password }),
  headers: { "Content-Type": "application/json" },
});

// UI API — record with metadata (prefer GraphQL for simple reads)
const res = await sdk.fetch!(`/services/data/v${API_VERSION}/ui-api/records/${recordId}`);

// Einstein LLM
const res = await sdk.fetch!(`/services/data/v${API_VERSION}/einstein/llm/prompt/generations`, {
  method: "POST",
  body: JSON.stringify({ promptTextOrId: prompt }),
});
```

Use `sdk.fetch!` (non-null assertion) just as `sdk.graphql!` — `fetch` is also optional on
`DataSDK`. When you call `sdk.fetch` you are handling raw HTTP, so check `response.ok` and then
parse the JSON body's `errors` array yourself (HTTP 200 still doesn't guarantee a successful
GraphQL/REST body):

```typescript
const response = await sdk.fetch!(url, { method: "GET", headers: { Accept: "application/json" } });
if (!response.ok) throw new Error(`Request failed: ${response.statusText}`);
const result = (await response.json()) as { data?: unknown; errors?: { message: string }[] };
if (result.errors?.length) throw new Error(result.errors.map((e) => e.message).join("; "));
```

> **Advanced / escape hatch — GraphQL over GET.** The supported path for record reads is
> `sdk.graphql!.query()` (POST, cached, typed) — see guardrail 9 in
> [SKILL.md](../SKILL.md#platform-guardrails--never-regress-these), which lists GraphQL as
> supported *only* via `sdk.graphql`. The shipped `accounts.ts` *demonstrates* issuing GraphQL
> as a `GET` through `sdk.fetch` — encoding the operation as a `queryInput` URL param against
> `/services/data/v{ver}/graphql` — but this is an example-app demonstration, not a sanctioned
> platform pattern. It sits below the supported-API contract: it bypasses the resource cache,
> the generated-type plumbing, and the supported-surface guarantee. Do not reach for it for
> ordinary record reads; stay on `sdk.graphql!.query()`.

## UI bundle integration (reactive / lifecycle code)

The patterns below are framework-agnostic — the SDK calls are plain `async`; only *where* you
place them (a React effect, a Vue/Svelte lifecycle hook, a web-component `connectedCallback`,
a store action) varies by UI layer.

### Pattern 1 — external `.graphql` file (complex queries)

**One operation per `.graphql` file** (one `query` or `mutation` plus its fragments). Import with
the `?raw` suffix; pass the imported string as `query`.

```typescript
import { createDataSDK, type NodeOfConnection } from "@salesforce/platform-sdk";
import MY_QUERY from "./query/myQuery.graphql?raw"; // ?raw suffix required
import type { GetMyDataQuery, GetMyDataQueryVariables } from "../graphql-operations-types";

const sdk = await createDataSDK();
const result = await sdk.graphql!.query<GetMyDataQuery, GetMyDataQueryVariables>({
  query: MY_QUERY,
  variables,
});
```

Run `npm run graphql:codegen` after creating/changing `.graphql` files.

### Pattern 2 — inline `gql` tag (simple queries)

**Must use `gql`** — plain template strings bypass ESLint schema validation. This is exactly the
shape of the shipped `accounts.ts`.

```typescript
import { createDataSDK, gql } from "@salesforce/platform-sdk";
import type { GetAccountsQuery, GetAccountsQueryVariables } from "../graphql-operations-types";

const GET_ACCOUNTS = gql`
  query GetAccounts($first: Int, $after: String) {
    uiapi { query {
      Account(first: $first, after: $after, orderBy: { Name: { order: ASC } }) {
        edges { node { Id Name @optional { value } Industry @optional { value } } }
        pageInfo { hasNextPage endCursor }
      }
    } }
  }
`;

const sdk = await createDataSDK();
const result = await sdk.graphql!.query<GetAccountsQuery, GetAccountsQueryVariables>({
  query: GET_ACCOUNTS,
  variables: { first: 20 },
});
```

### Canonical thin client (the scaffold)

The base-react-app template ships a thin wrapper (`graphqlClient.ts`) that every new app starts
from. Reuse it rather than re-implementing error handling:

```typescript
import { createDataSDK } from "@salesforce/platform-sdk";

export async function executeGraphQL<TData, TVariables>(
  query: string,
  variables?: TVariables,
): Promise<TData> {
  const sdk = await createDataSDK();
  const result = await sdk.graphql!.query<TData, TVariables>({ query, variables });
  if (result.errors?.length) {
    throw new Error(`GraphQL Error: ${result.errors.map((e) => e.message).join("; ")}`);
  }
  if (result.data == null) throw new Error("GraphQL response data is null");
  return result.data;
}
```

(To thread caching or use the reactive handle, call `sdk.graphql!.query()` directly with
`cacheControl` / `subscribe` — see [caching.md](caching.md).)

> Directory layout and the full command table (`graphql:schema` / `graphql:codegen` / `eslint` /
> `graphql-search.sh`, plus the graphiti commands) live in the spine — see
> [SKILL.md](../SKILL.md#commands--layout).

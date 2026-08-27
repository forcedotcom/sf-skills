# Migration — old Data SDK → `@salesforce/platform-sdk`

The Data SDK changed in two breaking ways (PR #502, shipped in `@salesforce/platform-sdk`
v10.10.1):

1. **Package renamed** — `@salesforce/sdk-data` → **`@salesforce/platform-sdk`**.
2. **`sdk.graphql` reshaped** from a **callable method** into a **namespace** with `.query()`
   and `.mutate()`, both taking an **options object**.

> Any remaining `@salesforce/sdk-data` strings in the webapps repo are **stale `dist/` build
> artifacts only** — not canonical. Always import from `@salesforce/platform-sdk`.

This is the **only** document where the dead callable API appears, for comparison. Everywhere
else in this skill uses the new API exclusively.

> The **new-side** code below is illustrative of the transition, not the source of truth for the
> current call contract. For the authoritative new signatures, read the installed
> `dist/*.d.ts` — [tier-2a](../SKILL.md#ground-the-sdk-contract-on-the-installed-types-tier-2a).
> If a new-side snippet here has drifted from the installed declaration, the declaration wins.

---

## 1. Import

```diff
- import { createDataSDK, gql, type NodeOfConnection } from "@salesforce/sdk-data";
+ import { createDataSDK, gql, type NodeOfConnection, type CacheControl } from "@salesforce/platform-sdk";
```

`createDataSDK`, `gql`, `NodeOfConnection`, and `CacheControl` all export from
`@salesforce/platform-sdk`.

## 2. Query call

```diff
- // OLD — callable, positional args, returns a response object with .data / .errors
- const response = await sdk.graphql?.<GetAccountsQuery, GetAccountsQueryVariables>(GET_ACCOUNTS, variables);
- const accounts = response?.data?.uiapi?.query?.Account?.edges ?? [];
- if (response?.errors?.length) { /* ... */ }

+ // NEW — namespace method, options bag, returns a reactive QueryResult
+ const result = await sdk.graphql!.query<GetAccountsQuery, GetAccountsQueryVariables>({
+   query: GET_ACCOUNTS,
+   variables,
+ });
+ const accounts = result.data?.uiapi?.query?.Account?.edges ?? [];
+ if (result.errors?.length) { /* ... */ }
```

Passing the generated `<GetAccountsQuery>` type parameter makes `result.data` fully typed — no
`as any` cast needed.

Mapping:

| Old | New |
|-----|-----|
| `sdk.graphql?.(QUERY, vars)` | `sdk.graphql!.query({ query: QUERY, variables: vars })` |
| positional `<T, V>(query, variables)` | type params on `query<T, V>(options)` |
| `response.data` / `response.errors` | `result.data` / `result.errors` (same fields) |
| (none) | `result.subscribe(cb)` / `result.refresh()` — new reactive handle |
| (none) | `cacheControl` option — new per-call cache policy |

## 3. Mutation call

The old callable form was used for mutations too. Mutations now have their own method, and the
operation key is **`mutation`**, not `query`:

```diff
- const response = await sdk.graphql?.<CreateAccountMutation>(CREATE_ACCOUNT, { input });
+ const { data, errors } = await sdk.graphql!.mutate<CreateAccountMutation, CreateAccountMutationVariables>({
+   mutation: CREATE_ACCOUNT,   // key is `mutation`, not `query`
+   variables: { input },
+ });
```

`mutate()` returns `{ data, errors }` only — **no** `subscribe`/`refresh`, and it is **never
cached**. To refresh a list after a mutation, hold the query `result` and call
`result.refresh()` (see [caching.md](caching.md)).

## 4. Optional chaining → non-null assertion

The old guidance was "always use optional chaining" (`sdk.graphql?.()`). Real consumer code now
uses the **non-null assertion** after `createDataSDK()`:

```diff
- const response = await sdk.graphql?.(QUERY, vars);
+ const result = await sdk.graphql!.query({ query: QUERY, variables: vars });
```

`sdk.graphql` may still be `undefined` on some surfaces. Use `!` when you know the surface
supports data ops; use an explicit guard if it might not:

```typescript
if (!sdk.graphql) throw new Error("GraphQL not available on this surface");
const result = await sdk.graphql.query({ query: QUERY, variables: vars });
```

## 5. Codegen types — unchanged generation, new call placement

`npm run graphql:codegen` and the generated type names (`<Op>Query` / `<Op>QueryVariables` /
`<Op>Mutation` / `<Op>MutationVariables`) are unchanged. Only **where** the type params attach
moves — from the callable to the namespace method:

```diff
- await sdk.graphql?.<GetAccountsQuery, GetAccountsQueryVariables>(GET_ACCOUNTS, variables);
+ await sdk.graphql!.query<GetAccountsQuery, GetAccountsQueryVariables>({ query: GET_ACCOUNTS, variables });
```

## 6. New capabilities to consider while migrating

The reshape also unlocked the freshness features (none required to get back to working). The one
migration-specific gotcha: **caching is now on by default** (300s, WebApp) — if any code relied
on every call hitting the network, add `cacheControl: "no-cache"` to it. The reactive
`subscribe`/`refresh` handle and the rest of `cacheControl` are in [caching.md](caching.md).

## 7. Migration checklist

- [ ] Replace every `@salesforce/sdk-data` import with `@salesforce/platform-sdk`
- [ ] Convert every `sdk.graphql?.(q, v)` query to `sdk.graphql!.query({ query: q, variables: v })`
- [ ] Convert every mutation call to `sdk.graphql!.mutate({ mutation: m, variables: v })` (key is `mutation`)
- [ ] Move generated type params onto `query<T,V>` / `mutate<T,V>`
- [ ] Rename `response` → `result`; `response.data`/`.errors` → `result.data`/`.errors`
- [ ] Add a `cacheControl: "no-cache"` to any call that genuinely must always hit the network
- [ ] Re-run `npm run graphql:codegen` and `npx eslint <file>`

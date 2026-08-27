# The Data SDK operational guide

The installed `@salesforce/platform-sdk` declarations own the current call contract: exports,
`query`/`mutate` signatures, options bags, result types, `CacheControl`, and
`NodeOfConnection`. Read `dist/core/data.d.ts` and `dist/data/index.d.ts` first and let them win
over this guide ([tier-2a](../SKILL.md#ground-the-sdk-contract-on-the-installed-types-tier-2a)).
For cache strategy see [caching.md](caching.md); for old `@salesforce/sdk-data` conversion see
[migration.md](migration.md).

This reference keeps only decisions and runtime behaviors that the declarations do not fully
express.

## `sdk.graphql!` vs guard

`sdk.graphql` is optional on surfaces that do not support data operations. Whether to assert it
after `createDataSDK()` is a surface decision:

```typescript
const result = await sdk.graphql!.query<...>({ query, variables });
```

Use `!` only if the bundle is WebApp-exclusive; otherwise guard. The spine's
[Surfaces](../SKILL.md#surfaces--sdkgraphql-vs-guard) table is the routing. A bare
`sdk.graphql!` that later ships to another surface throws `Cannot read properties of undefined`
at runtime, and TypeScript cannot catch it because `!` silences that check.

```typescript
// `!` form — WebApp-only bundles; every shipped WebApp consumer uses it.
const result = await sdk.graphql!.query<...>({ query, variables });

// Portable guard form — safe on every surface. Use when the bundle is not WebApp-exclusive.
if (!sdk.graphql) {
  // No data SDK on this surface — degrade gracefully (render empty, throw, or feature-flag off).
  return;
}
const result = await sdk.graphql.query<...>({ query, variables });
```

(The same `!`-vs-guard call applies to `sdk.fetch!`.)

## `QueryResult<T>` — the reactive query handle

`QueryResult` shape and core behavior belong to the installed TSDoc. Two behaviors it does not
spell out:

- Each `subscribe` is **independent** — unsubscribing one leaves the others live — and it does
  **not** fire on registration, only on later snapshots. Set initial state from the awaited
  snapshot, not from the subscriber.
- `result.refresh()` broadcasts the new snapshot to **all** current subscribers, not just the
  caller.

*When* to reach for `subscribe`/`refresh` over the default cache, plus the uncached-surface
caveats, is a strategy call — see [caching.md](caching.md).

## `cacheControl` — the per-call cache policy

The installed `CacheControl` TSDoc defines the supported values and their behavior. It does not
name the `only-if-cached` miss error type or prescribe its handling:

An `only-if-cached` miss is not an exception — the Promise resolves and the miss surfaces on
`result.errors` as a `DataNotFoundError`. This is offline-first: a miss is **expected, not an
error**. Check `result.errors`, render an empty state, and **do not fall back to a network read**
— a fallback defeats the point of `only-if-cached`:

```typescript
const result = await sdk.graphql!.query({ query: GET_ACCOUNTS, variables, cacheControl: "only-if-cached" });
if (result.errors?.length) {
  // cold cache — render the empty state. Do NOT fall back to the network; that defeats offline-first.
  return renderEmptyState();
}
```

Which policy fits which goal (force-refresh button, offline-first, fast-changing data) is a
strategy call — see the decision matrix in [caching.md](caching.md).

## HTTP 200 ≠ success — always read `errors`

The installed TSDoc establishes that GraphQL and parse failures resolve through
`result.errors`. Choose the product-appropriate stance; all inspect `result.errors`:

```typescript
// Strict — any errors = failure
if (result.errors?.length) throw new Error(result.errors.map((e) => e.message).join("; "));

// Tolerant — log, use whatever data came back (partial success)
if (result.errors?.length) console.warn("GraphQL partial errors:", result.errors);

// Discriminated — fail only when NO data returned
if (!result.data && result.errors?.length) {
  throw new Error(result.errors.map((e) => e.message).join("; "));
}
```

## Generated types

Run `npm run graphql:codegen` and use its generated operation types for **both** the
[Read workflow](../SKILL.md#read-workflow) (`query<Q, V>`) and the
[Write workflow](../SKILL.md#write-workflow) (`mutate<M, V>`). The installed declaration gives
the current generic placement; `NodeOfConnection` (read-side — it unwraps a Connection, which
only `query` returns) is defined there too.

# Caching & the reactive query result

Deep reference for the WebApp resource cache and the two refresh tools. The
[SKILL.md](../SKILL.md#freshness--caching) Freshness & caching section is the summary; this is
the full behavior.

> **Surface caveat up front:** everything about *caching* below is the **WebApp surface**. On
> uncached surfaces (Mosaic, OpenAI) there is no cache — see
> [Uncached surfaces](#uncached-surfaces-mosaic-openai) at the end. The `query`/`mutate`
> namespace shape is identical on every surface, so call sites stay portable.

---

## 1. Caching is ON by default (WebApp) — do NOT reinvent it

Every `sdk.graphql!.query()` on WebApp is cached automatically. There is **no opt-in flag, no
`createCachedClient` factory, and no `/cache` import subpath** — if you have heard of those,
they do not exist in `@salesforce/platform-sdk`. There is also **no need for React Query, SWR,
`localStorage`, or any hand-rolled memoization**. If you find yourself writing a cache, **stop**
— it already exists.

The installed `CacheControl` and `DataSDKGraphQL` TSDoc define the default TTL, cache hit/miss
behavior, and mutation cache policy. Read it first and let it win
([tier-2a](../SKILL.md#ground-the-sdk-contract-on-the-installed-types-tier-2a)).

### What gets cached

Only **successful responses with a non-empty `data` object** are written:

- `data` is `null`, missing, or `{}` → **NOT cached** (an empty `data` usually means a
  transient server condition; caching it would poison the cache for the full TTL).
- Response carries a non-empty `errors` array → surfaced as an error and **NOT cached**.

### Cache key

The key is `stableJSONStringify({ query, variables, operationName })`.

- **`cacheControl` does NOT affect the key.** The same query + variables share **one** cache
  entry no matter what policy each call passes. A `"no-cache"` call and a default call
  read/write the *same* slot.
- The query is keyed by its **raw string** — two semantically identical queries with different
  whitespace produce **different** entries. Reuse the same `gql`-tagged constant; do not
  re-template the same query inline per call.
- Variables are deep-cloned at call time, so mutating your variables object afterward does not
  desync the key from the request body. Variables must be JSON-serializable (circular refs /
  BigInt throw a typed error).

### Shared across SDK instances by `baseUrl`

Cache bundles are deduped in a module-level registry keyed by the resolved `baseUrl`. **A query
run through one `createDataSDK()` instance is a cache hit on another instance targeting the same
host.** Independently-built features that each create their own SDK do not issue redundant
network requests for the same data.

The per-instance fetch pipeline (CSRF, `onStatus`) stays **isolated** — a cache *miss* routes
through the calling SDK's own fetch, so per-instance request behavior is preserved.

**Practical implication:** you do **not** need to hoist `createDataSDK()` into a singleton purely
to share cache. Calling it per-feature is fine; the cache is shared by host underneath. (A
singleton is still reasonable for other reasons.)

---

## 2. The two refresh tools (keep them distinct)

There are **two unrelated mechanisms** for getting fresh data. They have different shapes and
different mental models. Do not conflate `result.refresh()` (a method on a live handle) with
`cacheControl: "no-cache"` (a per-call option).

| | **Reactive refresh** | **Call-site cache control** |
|---|---|---|
| **API** | `result.subscribe(cb)` + `result.refresh()` | `cacheControl` on the query options bag |
| **Lifetime** | Long-lived handle; subscription persists until you unsubscribe | One-shot, fire-and-forget per call |
| **Pushes updates?** | Yes — `subscribe` fires on every subsequent snapshot | No — you read the returned value once |
| **PR** | #502 | #537 (W-22514759) |
| **Use when** | A mounted component should react to cache updates or re-fetch on demand | "This specific read must bypass / only-use / re-TTL the cache" |

### 2a. Reactive refresh — `subscribe` + `refresh`

The installed `QueryResult` TSDoc defines the reactive handle. This section covers when and how
to use it; [sdk-api.md](sdk-api.md#queryresultt--the-reactive-query-handle) adds the two
subscription behaviors absent from that TSDoc.

The lifecycle is: read the initial snapshot, register a subscriber for later snapshots, and
**always unsubscribe when the consumer goes away** (component unmount, effect re-run, view
teardown) so the subscription doesn't leak:

```typescript
const result = await sdk.graphql!.query<GetAccountsQuery>({ query: GET_ACCOUNTS, variables });
render(result.data, result.errors);                      // initial snapshot

const unsub = result.subscribe(({ data, errors }) => render(data, errors)); // live updates
await result.refresh();                                  // force re-fetch → pushes to subscribers
// later, when the consumer tears down:
unsub();
```

**Managing the subscription in a framework.** Whatever reactive/lifecycle primitive your UI
layer uses — a React effect, a Vue/Svelte lifecycle hook, a web-component
`connected`/`disconnectedCallback`, a store teardown — the same three obligations hold:

- Kick off `query()` on mount/setup and store the resolved `result` so you can call
  `refresh()` on it later (e.g. behind a "Refresh" button).
- Push each `subscribe` snapshot into your reactive state so the view re-renders.
- Run `unsub()` in the teardown path, and guard against a late-resolving `query()` writing state
  after teardown (track a `cancelled` flag). The subscription does not fire on registration, so
  set initial state from the awaited snapshot, not from the subscriber.

**Refresh after a mutation** — mutations have no `subscribe`/`refresh`. To make a list reflect a
write, hold the query `result` and call `result.refresh()` after `mutate()` resolves:

```typescript
await sdk.graphql!.mutate({ mutation: CREATE_ACCOUNT, variables: { input } });
await accountsResult.refresh(); // re-fetches, bypasses cache, pushes to subscribers
```

### 2b. Call-site cache control — the `cacheControl` option

`cacheControl` is a one-shot policy override; its values and mechanics are defined in the
installed `CacheControl` TSDoc. An `only-if-cached` miss is special: it surfaces as
`DataNotFoundError` on `result.errors`; render an empty state and **do not** fall back to the
network.

It does **not** affect the cache key — the same query+variables share one slot regardless of the
policy each call passes. Which policy to reach for is the strategy table below.

---

## 3. Choosing a strategy

| Goal | Reach for |
|------|-----------|
| Default reads, freshness within ~5 min is fine | Nothing — default 300s cache |
| Component stays mounted, should reflect cache updates / on-demand re-fetch | `subscribe` + `refresh` (2a) |
| Re-fetch a held query after a mutation | `result.refresh()` (2a) |
| One-off "this read must be fresh" (button, post-mutation one-shot) | `cacheControl: "no-cache"` (2b) |
| Offline-first — render only cached data, tolerate a miss as an empty state (no network fallback) | `cacheControl: "only-if-cached"` (2b) |
| Data changes faster than 5 min | `cacheControl: { type: "max-age", maxAge: N }` (2b) |

`no-cache` (2b) and `refresh()` (2a) both bypass the cache and write back; the difference is
**`refresh()` pushes to existing subscribers** and is a method on a live handle, while
`no-cache` is a fresh one-shot call with no subscribers.

---

## Uncached surfaces (Mosaic, OpenAI)

- **No cache exists.** Every `query()` is a network request.
- **`cacheControl` is silently ignored** — `"no-cache"`, `"only-if-cached"`, and `max-age` have
  no effect (notably, `only-if-cached` will **not** raise `DataNotFoundError` because there is no
  cache layer to miss).
- **`subscribe` is real but only emits in response to `refresh()`** — there is no background
  cache to push updates, so `refresh()` is the sole source of new snapshots, and each
  `refresh()` costs one network request.
- PR #502 flags the uncached `subscribe`/`refresh` edge semantics (re-emit-to-all, error
  fan-out, ordering vs concurrent refresh) as a **known soft spot / follow-up**. Document
  conservatively; do not over-promise behavior there.

The namespace shape (`query`/`mutate`, options bag, `QueryResult`) is identical across surfaces,
so the same call site runs on WebApp and uncached surfaces alike.

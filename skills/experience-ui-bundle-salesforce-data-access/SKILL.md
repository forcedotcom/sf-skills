---
name: experience-ui-bundle-salesforce-data-access
description: "MUST activate when a uiBundles/*/src/ project does ANY Salesforce record operation — reading, creating, updating, deleting, or caching/refreshing query results. Triggers: code importing @salesforce/platform-sdk, calls to sdk.graphql.query / sdk.graphql.mutate / sdk.fetch, *.graphql files, stale data needing a force-refresh, or wiring up a UI bundle's data layer to read, write, or refresh Salesforce records. The default for new read/write work is the Read/Write workflow with the current @salesforce/platform-sdk API; only follow the migration path when EXISTING code already uses the old @salesforce/sdk-data callable form. Not for building app shell/UI, styling, file upload, or auth/search scaffolding — use the other ui-bundle-* skills. DO NOT TRIGGER when: OAuth setup, schema changes, Bulk/Tooling/Metadata API, or declarative automation."
metadata:
  cliTools:
    - tool: ["node"]
      semver: ">=18.0.0"
    - tool: ["npm"]
      semver: ">=9.0.0"
    - tool: ["npx"]
      semver: ">=9.0.0"
    - tool: ["sf"]
      semver: ">=2.0.0"
  relatedSkills:
    - "platform-metadata-deploy"
  version: "2.1"
---

# Salesforce Data Access (UI bundles)

All Salesforce data access in a UI bundle goes through the **`@salesforce/platform-sdk`**
data SDK. The SDK handles auth, CSRF, and base-URL resolution, and — on the WebApp
surface — caches every GraphQL query by default.

This file is the **workflow + guardrail spine**. Depth lives in linked docs:

- **[references/graphiti-cli.md](references/graphiti-cli.md)** — the **`graphiti` CLI** (`sf-gql-*`
  commands) that compiles a small JSON spec into a schema-correct, guardrail-applied query +
  variables + types. The preferred way to author the GraphQL in steps below; falls back to the
  schema-grep script when unavailable.
- **[references/sdk-api.md](references/sdk-api.md)** — the new call API: `query`/`mutate`,
  `QueryResult`, typing, error-handling stances.
- **[references/caching.md](references/caching.md)** — on-by-default cache + the **two refresh
  modes** (`result.refresh`/`subscribe` vs per-call `cacheControl`).
- **[references/graphql-hand-authoring.md](references/graphql-hand-authoring.md)** — schema lookup, read /
  mutation templates, every platform guardrail (`@optional`, pagination, limits,
  semi-join, wrappers, error table…).
- **[references/rest-and-integration.md](references/rest-and-integration.md)** — `sdk.fetch`,
  the supported-API allowlist, and the reactive/lifecycle integration patterns.
- **[references/migration.md](references/migration.md)** — old `@salesforce/sdk-data` callable code
  → new namespace. The **only** place the dead API appears as usable code.

## The one-paragraph mental model

`const sdk = await createDataSDK()`. Then `sdk.graphql` is a **namespace**, not a
function: **`sdk.graphql!.query({...})`** for reads, **`sdk.graphql!.mutate({...})`**
for writes. On WebApp, **every `query()` is cached by default** (300s). HTTP 200 never
means success — always check `result.errors`. Verify every entity and field against the
schema before you query it: one unverified field fails the *whole* query at runtime, and
`schema.graphql` is too large to eyeball — look it up.

```typescript
import { createDataSDK, gql } from "@salesforce/platform-sdk"; // gql tags the query string so codegen + eslint validate it

const sdk = await createDataSDK();
const result = await sdk.graphql!.query({ query: GET_ACCOUNTS, variables });
if (result.errors?.length) throw new Error(result.errors.map((e) => e.message).join("; "));
const rows = result.data?.uiapi?.query?.Account?.edges?.map((e) => e.node) ?? []; // unwrap edges/node; read field values via .value
```

Typed call params (`query<GetAccountsQuery, GetAccountsQueryVariables>`), the `CacheControl`
type, and `NodeOfConnection<T>` (extracts a node type from a Connection for clean typing) all
live in [references/sdk-api.md](references/sdk-api.md).

> **This changed (breaking — PR #502).** The previous callable `sdk.graphql(...)` form and the
> previous package name are **dead** — the code above is the only correct form. If you encounter
> the old API in existing code (or a stale `dist/` artifact), don't copy it; convert it per
> [Working on existing code](#working-on-existing-code-migration).
>
> **`sdk.graphql!` is WebApp-only.** The non-null assertion above is correct *only* if the
> bundle runs solely on WebApp. On other surfaces it can crash — decide before you write it.
> See **[Surfaces — `!` vs guard](#surfaces--sdkgraphql-vs-guard)** below.

---

## Surfaces — `sdk.graphql!` vs guard

`createDataSDK()` runs on multiple surfaces, and **`sdk.graphql` / `sdk.fetch` are genuinely
optional** (typed `graphql?: …`). Whether you may assert them with `!` depends entirely on
where the bundle runs — this is the one surface decision that turns into a *runtime crash* if
you get it wrong, so make it explicitly before writing any `query`/`mutate` call:

| Surface(s) | `sdk.graphql` | Write |
|---|---|---|
| **WebApp only** | always present | `sdk.graphql!.query({...})` — `!` is safe; every shipped WebApp consumer uses it |
| **Mosaic / OpenAI / MCPApps** (or any bundle that *might* run off-WebApp) | can be `undefined` | **guard first** (`if (!sdk.graphql) return …`), then call |

Rule of thumb: **if you cannot prove the bundle is WebApp-only, guard.** A bare `sdk.graphql!`
that later ships to another surface throws `Cannot read properties of undefined` at runtime —
TypeScript won't catch it because `!` silences exactly that check (same applies to `sdk.fetch!`).
The portable guard snippet lives in [references/sdk-api.md](references/sdk-api.md#sdkgraphql-vs-guard).

---

## Step 0 — Route the task

| The task is… | Go to |
|---|---|
| Read records | **[Read workflow](#read-workflow)** below |
| Create / update / delete records | **[Write workflow](#write-workflow)** below |
| Object/field metadata, picklist values, related-list metadata, aggregations | **[Beyond record CRUD](#beyond-record-crud)** below |
| Data is stale / "add a refresh button" / "cache it longer" | **[Freshness & caching](#freshness--caching)** below |
| Something GraphQL can't express (Apex REST, file upload, Einstein) | [references/rest-and-integration.md](references/rest-and-integration.md) |
| Migrating old `sdk.graphql?.(query, vars)` code | **[Working on existing code](#working-on-existing-code-migration)** below |

GraphQL covers far more than record reads and writes — prefer it for **anything the `uiapi`
namespace exposes** (see [Beyond record CRUD](#beyond-record-crud)). Reach for REST only when
the data genuinely lives outside `uiapi` (Apex REST, file upload, Einstein) — see
[references/rest-and-integration.md](references/rest-and-integration.md).

---

## Preconditions — verify before writing any query

`<skill-dir>` below is wherever this skill is installed (the directory this
`SKILL.md` loaded from). The schema-lookup script ships inside it. The script does
**not** hunt for `schema.graphql` by walking up the tree — an ancestor schema can
belong to a different org and would validate fields against the wrong one. Resolve
the schema explicitly: run from the SFDX project root (where `schema.graphql` lives),
or pass `--schema <path>` / set `GRAPHQL_SCHEMA=<path>`. The script echoes the schema
it resolved (`[graphql-search] using schema: …` on stderr) — glance at it to confirm
you grounded against the right file.

| # | Requirement | Verify | If missing |
|---|---|---|---|
| 1 | `@salesforce/platform-sdk` installed | `package.json` in the UI bundle dir | Tell user to install it; cannot proceed |
| 2 | A grounding tool resolves | **Preferred:** `npx graphiti sf-gql-discover '{"org":"<alias>","mode":"list_objects"}'` from the UI bundle dir returns objects. **Fallback:** `bash <skill-dir>/scripts/graphql-search.sh <Entity>` from the project root prints a lookup, not "schema.graphql not found" | No graphiti dep / org won't prime → use the script. Script can't find `schema.graphql` → pass `--schema <path>`, or `npm run graphql:schema` from the UI bundle dir. ([references/graphiti-cli.md](references/graphiti-cli.md) covers CLI setup) |
| 3 | Target objects/fields deployed | The object appears in `sf-gql-discover` (or `graphql-search.sh <Entity>` returns output) | Entity absent usually means it isn't deployed (or the cache/schema is stale). Refresh: `npx graphiti sf-gql-connect '{"org":"<alias>","forceRefresh":true}'` (CLI) or `npm run graphql:schema` (script). If still absent, deploy the metadata (the **platform-metadata-deploy** skill handles this) and assign the permission sets, then re-check |

If preconditions aren't met you may still scaffold components, routes, and layout — but
use empty arrays / `null` for data, mark query sites with
`// TODO: add query after schema verification`, and add a plan item to return. Do **not**
write GraphQL strings until the schema workflow is complete.

---

## Read workflow

1. **Look up the schema first — never guess a name.** **Preferred (graphiti):** when the exact
   API name is at all uncertain, **list before you describe** —
   `npx graphiti sf-gql-discover '{"org":"<alias>","mode":"list_objects","search":"<intent>"}'`
   to find the real name, then
   `npx graphiti sf-gql-discover '{"org":"<alias>","mode":"describe_object","object":"<Entity>"}'`
   for exact field/type names, picklist values, filterable/sortable. An empty list or missing object
   is a **fact about the org** (wrong name or not deployed), **not a tool failure** — re-list or
   `forceRefresh`; **do not fall back to the script for this** (see guardrail 2). **Fallback** is
   only for a CLI that genuinely can't run (no graphiti dep / org won't prime):
   `bash <skill-dir>/scripts/graphql-search.sh <Entity>` from the SFDX project root.
   (Full rules: [references/graphql-hand-authoring.md](references/graphql-hand-authoring.md).)
2. **Write the query.** **Preferred — compile it with graphiti:**
   `npx graphiti sf-gql-list '{"org":"<alias>","object":"<Entity>","fields":[…],"first":N}'`
   returns a `{ query, variables, types, warnings }` envelope with `@optional`, `value`/`displayValue`,
   `edges/node`, and `first:`/`pageInfo` **already applied**. Confirm `warnings: []` (a non-empty
   array means the object wasn't in the primed schema — the query is degraded; don't ship it), then
   paste the `query` verbatim into inline `gql` (simple) or an external `.graphql` file (one operation
   per file, imported with the bundler's `?raw` suffix — `import Q from "./q.graphql?raw"` brings the
   file in as a plain string). **Fallback — hand-author:** apply `@optional` to every **selectable
   FLS-gated field** — scalar leaf fields (`Name @optional { value }`) and parent/child
   relationships *and* the fields inside them — but **NOT** on `Id`, on connection plumbing
   (`edges`, `node`, the connection field itself), or on `pageInfo`; the graphiti output leaves
   those bare and is the canonical placement. Always set `first:`, include `pageInfo` if it may
   page. Either way, full mechanics and the primed-vs-degraded behavior:
   [references/graphiti-cli.md](references/graphiti-cli.md).
3. **Generate types** — `npm run graphql:codegen` (from the UI bundle dir) →
   `src/api/graphql-operations-types.ts`.
4. **Call `query()`** with the generated types:

   ```typescript
   import type { GetAccountsQuery, GetAccountsQueryVariables } from "../graphql-operations-types";

   const result = await sdk.graphql!.query<GetAccountsQuery, GetAccountsQueryVariables>({
     query: GET_ACCOUNTS,
     variables: { first: 20 },
     // cacheControl,            // optional — see Freshness & caching
   });
   ```
5. **Handle the result.** `result.data` + `result.errors` are the initial snapshot;
   `result.subscribe` / `result.refresh` are the reactive handles. Always check
   `errors` before reading `data`:

   ```typescript
   if (result.errors?.length) throw new Error(result.errors.map((e) => e.message).join("; "));
   const rows = result.data?.uiapi?.query?.Account?.edges?.map((e) => e.node) ?? [];
   ```

Defend consuming code with `?.`/`??` (because `@optional` can omit fields). Error-handling
stances (strict / tolerant / discriminated) and `NodeOfConnection` typing: [references/sdk-api.md](references/sdk-api.md).

---

## Write workflow

1–3 as above (schema lookup → write the **mutation** → codegen). To compile the mutation with
graphiti, use `sf-gql-create` / `sf-gql-update` / `sf-gql-delete` — they emit the
`uiapi { <Object>Create(input: $input) { Record {…} } }` shape; the `types` field tells you
the input shape. Details: [references/graphiti-cli.md](references/graphiti-cli.md).
4. **Call `mutate()`** — note the option key is **`mutation`**, not `query`, and that
   mutations are **never cached**. The runtime `variables` shape differs per operation —
   values are **raw** (never `{value}`-wrapped; that wrapper is a read-shape thing and breaks
   writes) and nest under the **entity key**:

   ```typescript
   // create — input.<Entity> holds the new field values
   variables: { input: { Account: { Name: "Acme", Industry: "Technology" } } }
   // update — sibling Id alongside the entity key
   variables: { input: { Id: "001…", Account: { Industry: "Finance" } } }
   // delete — Id only, no entity key (generic RecordDeleteInput)
   variables: { input: { Id: "001…" } }

   const { data, errors } = await sdk.graphql!.mutate<CreateAccountMutation, CreateAccountMutationVariables>({
     mutation: CREATE_ACCOUNT,
     variables: { input: { Account: { Name: "Acme" } } },
   });
   if (errors?.length) throw new Error(errors.map((e) => e.message).join("; "));
   ```

   This is the **`variables` shape** the spine owns; the CLI `types`-field interpretation is in
   [references/graphiti-cli.md](references/graphiti-cli.md) and the GraphQL-document field constraints
   (`createable`/`updateable`, `ApiName` references, `@{alias}` chaining) in
   [references/graphql-hand-authoring.md](references/graphql-hand-authoring.md).
5. **Re-freshen affected reads.** `mutate()` has no `refresh`. To update a live list
   after a write, hold the `QueryResult` from your earlier `query()` call (e.g.
   `accountsResult`) and call `await accountsResult.refresh()` (forced re-fetch, pushes
   to subscribers) — note this is the read's handle, not anything `mutate()` returns. See
   **[Freshness & caching](#freshness--caching)**.

Mutation syntax is exacting: wrap under `uiapi(input: { allOrNone: ... })`, only
`createable`/`updateable` fields, Create/Update output is always `Record` but **Delete has no
`Record` field — select `Id` only**. Full template + chaining + constraints:
[references/graphql-hand-authoring.md](references/graphql-hand-authoring.md).

---

## Beyond record CRUD

The `uiapi` namespace is not just record reads/writes. Before reaching for REST, check
whether GraphQL already covers it — the same `sdk.graphql!.query()` call, different
sub-selection. The top-level `uiapi` fields:

| Need | Use | Returns |
|---|---|---|
| Query records | `uiapi { query { <Entity>(...) } }` | records (the [Read workflow](#read-workflow)) |
| Counts / sums / grouped rollups without pulling rows | `uiapi { aggregate { <Entity>(groupBy: …) } }` | aggregated buckets |
| Object/field metadata — labels, data types, `createable`/`updateable`, record types | `uiapi { objectInfos(apiNames: […]) }` | `ObjectInfo[]` |
| Picklist values (per record type) | `uiapi { objectInfos(objectInfoInputs: […]) { fields … on PicklistField { … } } }` | picklist values |
| Related-list metadata — display columns, ordering for a parent's related list | `uiapi { relatedListByName(parentApiName, relatedListName) }` | `RelatedListInfo` |

Same rules as record reads: verify every type/field first, `@optional` where FLS applies, check
`result.errors`. Aggregations can be compiled with `npx graphiti sf-gql-aggregate` (pass
`groupBy` + `aggregations`); object metadata / picklists / related lists are hand-authored —
templates: [references/graphql-hand-authoring.md](references/graphql-hand-authoring.md).

> Two related capabilities (the **current-user** record and **layout** delivery) need
> confirmation against a current org schema before this skill documents a query shape —
> tracked as a follow-up, not yet covered here.

---

## Freshness & caching

**Caching is ON by default on WebApp.** Every `sdk.graphql!.query()` is cached with a
**300-second `max-age`** TTL — no opt-in flag, no factory, no import subpath. **Do not
build your own cache** (no React Query, SWR, `localStorage`, or hand-rolled Map). The
cache is **shared across SDK instances by `baseUrl`**: the same query+variables from a
different `createDataSDK()` targeting the same host is a cache hit. Only non-empty,
error-free `data` is cached. `mutate()` is never cached.

There are **two distinct freshness tools** — keep them separate:

1. **Per-call `cacheControl`** — a one-shot policy override on the query options bag
   (`"no-cache"` / `"only-if-cached"` / `{ type: "max-age", maxAge: <seconds> }`). The type and
   exact per-value behavior live in [references/sdk-api.md](references/sdk-api.md#cachecontrol--the-per-call-cache-policy).
   Take `cacheControl` as an optional param on the read function and expose each distinct policy as
   a **thin named export in the same data-layer file** — a "call site" is a named export, not a new
   React component. For `getAccounts(first, after?, cacheControl?)`: `export const refreshAccounts =
   () => getAccounts(20, undefined, "no-cache")` (and likewise `offlineAccounts` → `"only-if-cached"`,
   `shortLivedAccounts` → `{ type: "max-age", maxAge: 10 }`). Keep the policy in the data layer.
2. **Reactive `subscribe` / `refresh`** — a stateful handle on a live `QueryResult`:
   `result.subscribe(cb)` fires on every later snapshot, `result.refresh()` re-fetches bypassing
   the cache and pushes to subscribers. Shape in [references/sdk-api.md](references/sdk-api.md#queryresultt--the-reactive-query-handle);
   subscription lifecycle (always unsubscribe on teardown) in [references/caching.md](references/caching.md).

| Want | Reach for |
|---|---|
| Freshness within ~5 min is fine | nothing (default cache) |
| This one read must bypass the cache (refresh button) | `cacheControl: "no-cache"` |
| Read only cached data, tolerate misses (offline-first) | `cacheControl: "only-if-cached"` — a miss is **expected, not an error**: it surfaces a `DataNotFoundError` on `result.errors` (no network, no throw). Check `result.errors`, render empty state, **do not throw and do not fall back to the network** — that defeats offline-first. |
| Tighter/looser TTL for this query | `cacheControl: { type: "max-age", maxAge: 60 }` (`maxAge` is in **seconds**) |
| Mounted component reflects updates over time | `result.subscribe(cb)` |
| Re-fetch now + notify all subscribers (e.g. after a mutation) | `result.refresh()` |

`cacheControl` is fire-and-forget at call time; `subscribe`/`refresh` is a live handle.
Different mechanisms, different jobs — don't conflate "refresh" with "no-cache". Full
behavior, the reactive-subscription lifecycle, and uncached-surface caveats: [references/caching.md](references/caching.md).

---

## Working on existing code (migration)

**Only enter this path if the existing code actually uses the old API** — i.e. it imports
`@salesforce/sdk-data` or calls the callable `sdk.graphql(query, vars)` form. For any new
read/write, ignore migration entirely and use the [Read workflow](#read-workflow) /
[Write workflow](#write-workflow) — those already show the **only** correct API.

When you do have old code to convert, see **[references/migration.md](references/migration.md)** for the
before→after diff (imports, query/mutate calls, optional-chaining → non-null assertion, codegen
type placement) and a checklist. The target API is exactly what the Read/Write workflows above
prescribe — migrating is just swapping the old form for that.

---

## Platform guardrails — never regress these

These are Salesforce GraphQL platform behaviors, independent of the SDK. Violations cause
silent runtime failures. (Details + templates: [references/graphql-hand-authoring.md](references/graphql-hand-authoring.md).)

1. **HTTP 200 ≠ success** — always parse `result.errors`; the Promise resolves even on failure.
2. **Schema is the only source of truth — verify, never invent.** Verify every
   entity/field/type via graphiti `sf-gql-discover` (preferred) or
   `bash <skill-dir>/scripts/graphql-search.sh <Entity>` before use. Case-sensitive;
   `__c`/`__e`; `_Record` entity suffix (v60+). When graphiti is primed, a
   "not found"/empty/`Cannot query field` answer (including from
   `graphql-codegen`/`@graphql-eslint`, even when the message points at `schema.graphql`)
   is a **fact about the org** — wrong name or undeployed/inaccessible metadata, not a tool
   failure: fix the operation, or deploy the metadata (the **platform-metadata-deploy** skill)
   + assign perms + refresh (`sf-gql-connect --forceRefresh` / `npm run graphql:schema`). Do
   not fall back to the script, hand-author around it, or **guess a name** — a guessed entity or
   field silently fails the whole query at runtime; if lookups aren't converging, **ask the user
   rather than keep spiraling**. **`schema.graphql` and the codegen output
   (`src/api/graphql-operations-types.ts`) are read-only generated mirrors — never open or edit
   them** (honor any `# DO NOT EDIT` marker). Hand-adding a missing type satisfies codegen/lint
   but grants no org access; it just hides the failure until runtime. Fall back to the script
   *only* when the CLI can't run at all (no dep / `SCHEMA_PRIME_FAILED`).
3. **`@optional` on every FLS-gated field at each nesting level** — scalar leaf fields plus each
   parent/child relationship *and* the fields inside it (FLS fails the whole query otherwise, v65+).
   **Do NOT** decorate `Id`, the connection plumbing (`edges`, `node`, the connection field), or
   `pageInfo` — those are not FLS-gated and the graphiti output leaves them bare. Consume with
   `?.`/`??`. Placement rules: [references/graphql-hand-authoring.md](references/graphql-hand-authoring.md).
4. **Mutations** wrap under `uiapi(input: { allOrNone: ... })`; set `allOrNone` explicitly;
   output excludes child/navigated-reference fields; the output field is literally named
   `Record` (unrelated to the `_Record` entity suffix in rule 2) — Delete → `Id` only. GA v66+.
5. **Explicit pagination** — always set `first:`, because the server silently caps at 10 and
   you'll drop rows with no error; forward-only (`first`/`after`, no `last`/`before`);
   `upperBound` (v59+) raises the per-request ceiling for large sets (when set, `first` must be 200–2000).
6. **SOQL governor limits apply** — `uiapi` queries compile to SOQL, so the same governor
   limits are inherited: ≤10 subqueries, ≤5 child→parent levels, ≤1 parent→child level,
   ≤2,000 records/subquery. Split into multiple requests if you'd exceed them.
7. **Field value wrappers** — read the raw value via `.value`; `displayValue` is the
   server-formatted string for UI. When a field is both shown *and* operated on (currency,
   dates, picklists), select **both** `value` and `displayValue` so you don't reformat on the
   client. Display-only fields can take just `displayValue`.
8. **Compound fields** — filter/order on constituents (`BillingCity`), not the wrapper (`BillingAddress`).
9. **Supported APIs only** — GraphQL (`uiapi`), UI API REST, Apex REST, Connect REST,
   Einstein LLM via `sdk.fetch`. NOT: Enterprise SOQL `/query`, Aura-enabled Apex, Chatter
   (use `uiapi.currentUser`). See [references/rest-and-integration.md](references/rest-and-integration.md).

> One SDK convention lives in the workflows, not this list (it's not a platform behavior):
> always run `npm run graphql:codegen` and use the generated types after writing an operation
> ([Read workflow](#read-workflow) step 3). Also in the [Pre-flight checklist](#pre-flight-checklist).
>
> **graphiti applies most of these for you.** When you compile a query with `sf-gql-*` against an
> object that's in the primed schema, rules 3 (`@optional`), 4 (mutation `Record` *output*
> envelope and entity-keyed input — **not** `allOrNone`, which you still add yourself),
> 5 (`first:`/`pageInfo`), and 7 (`value`/`displayValue` wrappers) come out already satisfied —
> which is exactly why you **paste the `query` verbatim** rather than re-deriving it. Rules 1
> (check `result.errors`), 6 (governor limits), 8 (compound fields), and 9 (supported APIs) are
> still on you. And the automation only fires when the object is primed: a non-empty `warnings`
> array means it isn't, and the emitted query is **degraded** (bare fields, no guardrails) —
> see [references/graphiti-cli.md](references/graphiti-cli.md#primed-vs-degraded--why-the-guardrails-sometimes-vanish).

---

## Commands & layout

```text
<skill-dir>/                            ← wherever this skill is installed
└── scripts/graphql-search.sh           ← schema lookup (ships with the skill)

<project-root>/                         ← SFDX project root; run the script from here
├── schema.graphql                      ← generated mirror; grep target (never open or edit; script reads ./schema.graphql)
└── force-app/main/default/uiBundles/<app>/   ← UI bundle dir
    ├── package.json                    ← npm scripts
    └── src/api/                        ← queries, generated types, SDK calls
```

| Command | Run from | Purpose |
|---|---|---|
| `npx graphiti sf-gql-discover '{…}'` | UI bundle dir | Discover objects/fields against the live org (preferred grounding) |
| `npx graphiti sf-gql-<list\|detail\|aggregate\|create\|update\|delete\|raw> '{…}'` | UI bundle dir | Compile a guardrail-applied query/mutation ([references/graphiti-cli.md](references/graphiti-cli.md)) |
| `npx graphiti sf-gql-connect '{"org":"<alias>","forceRefresh":true}'` | UI bundle dir | Refresh graphiti's schema cache after a deploy |
| `bash <skill-dir>/scripts/graphql-search.sh <Entity>` | project root (or pass `--schema <path>`; no tree walk-up) | Schema lookup fallback (grep over local `schema.graphql`) |
| `npm run graphql:schema` | UI bundle dir | Fetch/refresh `schema.graphql` (for the fallback script) |
| `npm run graphql:codegen` | UI bundle dir | Generate operation types |
| `npx eslint <file>` | UI bundle dir | Lint (catches `gql` schema violations) |

## Pre-flight checklist

- [ ] Surface decided: `sdk.graphql!` only if WebApp-only; otherwise guard with `if (!sdk.graphql) …` ([Surfaces](#surfaces--sdkgraphql-vs-guard))
- [ ] Every field/entity verified — `sf-gql-discover` (preferred) or `graphql-search.sh` (fallback, against the right schema)
- [ ] If compiled with graphiti: `warnings: []` confirmed (non-empty = degraded query, don't ship); `query` pasted verbatim
- [ ] `@optional` on FLS-gated fields + relationships (NOT `Id`/`edges`/`node`/`pageInfo`); `?.`/`??` in consuming code
- [ ] `result.errors` checked before reading `result.data`
- [ ] Caching considered: default 300s OK, or `cacheControl` / `refresh` chosen deliberately
- [ ] `npm run graphql:codegen` run; generated types used; `npx eslint` passes

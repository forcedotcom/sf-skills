# Building queries with the graphiti CLI

The base UI-bundle template ships **`@salesforce/graphiti`** as a devDependency, exposing a
`graphiti` CLI. Its `sf-gql-*` subcommands turn a small JSON spec into a **schema-correct
GraphQL document** — the query string, its typed variables, and a TypeScript shape — with
every platform guardrail (`@optional`, `value`/`displayValue` wrappers, `edges/node`,
pagination, the mutation `Record` envelope) already applied. This is the **preferred way to
author the GraphQL in [Read workflow](../SKILL.md#read-workflow) /
[Write workflow](../SKILL.md#write-workflow) step 2** — you get a query that's already
grounded against the org's live schema instead of hand-writing one and discovering field
errors at runtime.

> **The CLI is a query *compiler*, not a data fetcher.** Every `sf-gql-*` command returns a
> `{ query, variables, types, warnings }` envelope. It **never calls Salesforce for records
> and never returns rows** — execution still happens at runtime through
> `sdk.graphql!.query()` / `.mutate()` exactly as the Read/Write workflows describe. Think of
> it as "codegen for the query string itself": dev-time you compile the operation, persist it,
> generate types; runtime the SDK runs it.

> **Fallback only when the CLI genuinely *can't run*.** Fall back to the schema-grep path
> (`bash <skill-dir>/scripts/graphql-search.sh <Entity>`) and hand-author per
> [graphql-hand-authoring.md](graphql-hand-authoring.md) **only** when `@salesforce/graphiti` isn't
> installed or the org can't be primed (`SCHEMA_PRIME_FAILED`). The guardrails there are the same
> ones the CLI automates — you're just applying them by hand.
>
> **A primed CLI returning empty / "not found" / `Cannot query field` is NOT a fallback trigger.**
> That's a fact about the org — a wrong API name, or metadata that isn't deployed/refreshed — not a
> CLI failure. Re-`discover` (list before describe), `sf-gql-connect --forceRefresh` if you just
> deployed, or deploy the metadata; **do not switch to the script or hand-author around it**, and
> **never edit `schema.graphql`** to make the name resolve (it grants no org access — see
> [graphql-hand-authoring.md](graphql-hand-authoring.md)).

> **MCP, later.** These `sf-gql-*` commands mirror, one-for-one, the `sf_gql_*` tools of the
> graphiti MCP server (same args, same output, different transport). If graphiti is later
> approved as an MCP server, an agent calls the `sf_gql_*` tools directly and everything below
> about *shapes and behavior* still holds — only the invocation changes.

---

## How to invoke it

Run from the **UI bundle dir** (where `package.json` with the `@salesforce/graphiti` dep
lives). Each command takes one JSON argument (positional, or piped on stdin) and emits exactly
one JSON line on stdout:

```bash
npx graphiti sf-gql-list '{"org":"myOrgAlias","object":"Account","fields":["Name","Industry"],"first":10}'

# stdin form (handy for large specs):
echo '{"org":"myOrgAlias","object":"Account","fields":["Name"]}' | npx graphiti sf-gql-list
```

**Always single-quote the JSON argument.** It contains `"` and may contain `$varName` tokens
(see [Variables](#variables--parameterising-a-query)); an unquoted `$foo` is expanded by the
shell to an empty string before graphiti ever sees it.

`org` is an **org alias from the local Salesforce CLI auth** (`~/.sf` / `~/.sfdx`) — the same
aliases `sf org list` shows. It is **required on every command**.

Exit code is `0` on success, `1` on any error (the error is also in the JSON envelope, so you
can parse stdout rather than branch on the code).

---

## The three phases

### 1. Prepare — make sure the org's schema is available

The build commands **auto-prime**: the first `sf-gql-*` call for an org downloads and caches
its schema, so you usually don't need a separate step. You only call `sf-gql-connect`
explicitly to **refresh after a deploy** (new objects/fields/picklist values won't appear until
you do):

```bash
npx graphiti sf-gql-connect '{"org":"myOrgAlias","forceRefresh":true}'
# → {"org":"myOrgAlias","instanceUrl":"https://…","refreshed":true,"cached":false,"durationMs":…}
```

If priming fails, the command returns a `SCHEMA_PRIME_FAILED` error envelope (see
[Errors](#error-envelope)) — the org is unreachable, unauthed, or hitting a server-side
introspection issue. You can't build verified queries against an org you can't prime; surface
that to the user rather than guessing field names.

### 2. Discover — never guess an object or field

`sf-gql-discover` is how you ground intent against the org *before* building. Three modes:

```bash
# What objects exist (optional substring filter)?
npx graphiti sf-gql-discover '{"org":"myOrgAlias","mode":"list_objects","search":"Account"}'
# → {"mode":"list_objects","objects":[{"name":"Account"}, …]}

# What fields does an object have (+ type, filterable, sortable, picklist values)?
npx graphiti sf-gql-discover '{"org":"myOrgAlias","mode":"describe_object","object":"Hero__c"}'
# → {"mode":"describe_object","object":{"name":"Hero__c","fields":[
#      {"name":"Class__c","label":"Class","type":"PICKLIST","filterable":true,"sortable":true,
#       "picklistValues":["Warrior","Mage","Rogue","Cleric"], …}, …]}}

# Drill into one field
npx graphiti sf-gql-discover '{"org":"myOrgAlias","mode":"describe_field","object":"Hero__c","field":"Class__c"}'
```

`mode` is **required**; `object` is required for `describe_object`/`describe_field`; `field`
is required for `describe_field`. Use this output to pick exact API names, valid picklist
values, and which fields are filterable/sortable — the same facts that otherwise cause silent
runtime failures.

### 3. Build — compile the operation

Pick the command for the task, pass the spec, read the `query` + `variables` + `types` out of
the envelope. The next section is the catalogue.

---

## The commands

| Command | Builds | Key spec fields |
|---|---|---|
| `sf-gql-list` | List query (`uiapi.query`) | `object`, `fields[]`, `first?`, `filter?`, `orderBy?`, `parentFields?`, `childRelationships?`, `scope?` |
| `sf-gql-detail` | Single-record-by-Id query | `object`, `fields[]`, `idVariable?` (default `id`) |
| `sf-gql-aggregate` | Aggregate query (`uiapi.aggregate`) | `object`, `groupBy?[]`, `aggregations?[]`, `filter?`, `first?` |
| `sf-gql-create` | Create mutation | `object`, `returnFields?` (default `["Id"]`), `inputVariable?` (default `input`) |
| `sf-gql-update` | Update mutation | `object`, `returnFields?`, `inputVariable?` |
| `sf-gql-delete` | Delete mutation | `object`, `inputVariable?` |
| `sf-gql-raw` | Arbitrary query from CLI-style `select`/`set`/`var` commands | `commands[]`, `operation?` (`query`\|`mutation`\|`aggregate`) |
| `sf-gql-discover` | Schema metadata (no GraphQL) | `mode`, `object?`, `field?`, `search?` |
| `sf-gql-connect` | Primes/refreshes the schema cache (no GraphQL) | `forceRefresh?` |

`operationName` (most commands) overrides the generated operation name — **set it to something
meaningful** (e.g. `"GetActiveHeroes"`) so the persisted `.graphql` file and the types codegen
generates off it read well. Defaults are derived (`<Object>List`, `<Object>Detail`, …).

### Output envelope

Every build command emits the same four-key envelope:

```jsonc
{
  "query":     "query …{ … }",          // the GraphQL document — paste verbatim
  "variables": [{ "name": "after", "type": "String", "required": false }],
  "types":     "export interface …",     // TS shape of variables + result (a preview)
  "warnings":  []                         // schema/semantic warnings — READ THESE
}
```

- **`query`** — paste it verbatim into your `.graphql` file or inline `gql`. The guardrails are
  baked in; don't "tidy" them out (that's the load-bearing part — see
  [Primed vs degraded](#primed-vs-degraded--why-the-guardrails-sometimes-vanish)).
- **`variables`** — the GraphQL variables the operation declares, with types and nullability.
  These map straight to the `variables` object you pass to `sdk.graphql!.query({ query,
  variables })`.
- **`types`** — a TypeScript preview of the variables + result shape, with anonymized interface
  names (`S37eaResult`). Useful to *see* the shape, but the canonical typed path is still the
  bundle's `npm run graphql:codegen` over your saved `.graphql` (it produces **named** types
  you import) — see [Wiring into runtime](#wiring-the-output-into-runtime).
- **`warnings`** — non-fatal, but **always read them**. An empty `[]` means the operation
  validated cleanly against the live schema. A non-empty entry usually means a field/object
  isn't in the primed schema or a selection is semantically off (examples below).

### Ground-truth examples

These are real outputs captured from the CLI (query strings pretty-printed for readability;
the CLI emits them as a single JSON line).

**`sf-gql-list`** — `{"org":"…","object":"Hero__c","fields":["Name","Level__c","Class__c"],"first":5,"orderBy":{"Level__c":{"order":"DESC"}}}`

```graphql
query Hero__cList($after: String) {
  uiapi {
    query {
      Hero__c(first: 5, after: $after, orderBy: { Level__c: { order: DESC } }) {
        edges {
          node {
            Name @optional { value displayValue }
            Level__c @optional { value displayValue }
            Class__c @optional { value displayValue }
          }
        }
        pageInfo { hasNextPage endCursor }
      }
    }
  }
}
```
`variables: [{ "name": "after", "type": "String", "required": false }]` — note the CLI adds
forward-pagination (`$after` + `pageInfo`) for you. `orderBy` is a **singleton object**
(`{Field:{order:DESC}}`), not an array or `{field,direction}`.

**`sf-gql-detail`** — `{"org":"…","object":"Hero__c","fields":["Name","Level__c"]}`

```graphql
query Hero__cDetail($id: ID!) {
  uiapi { query { Hero__c(where: { Id: { eq: $id } }, first: 1) {
    edges { node {
      Name @optional { value displayValue }
      Level__c @optional { value displayValue }
    } }
  } } }
}
```
Injects `$id: ID!` and the `where: { Id: { eq: $id } }, first: 1` binding. Pass
`idVariable` to rename `$id`.

**`sf-gql-aggregate`** — `{"org":"…","object":"Hero__c","groupBy":["Class__c"],"aggregations":[{"function":"count","field":"Id","alias":"total"},{"function":"avg","field":"Level__c","alias":"avgLevel"}]}`

```graphql
query Hero__cAggregate($after: String) {
  uiapi { aggregate { Hero__c(groupBy: { Class__c: { group: true } }, after: $after) {
    edges { node { aggregate {
      Class__c { value }
      total: Id { count { value } }
      avgLevel: Level__c { avg { value } }
    } } }
    pageInfo { hasNextPage endCursor }
  } } }
}
```
`groupBy` is `["Field"]` (or `[{field,function}]` for date bucketing); aggregations carry a
`function` (`count`/`countDistinct`/`sum`/`avg`/`min`/`max`), an optional `field` (defaults to
`Id` for counts), and an `alias`. *Observed quirk:* this exact spec returns
`warnings: ["Validation: Field \"avg\" must not have a selection since type \"Double\" has no
subfields."]` — `avg` over a Double should be selected bare, not `avg { value }`. Treat such a
warning as a prompt to adjust the selection, not as a failed build.

**`sf-gql-create`** — `{"org":"…","object":"Hero__c","returnFields":["Id","Name"]}`

```graphql
mutation CreateHero__c($input: Hero__cCreateInput!) {
  uiapi { Hero__cCreate(input: $input) { Record {
    Id
    Name @optional { value displayValue }
  } } }
}
```
The `types` field describes the input you must supply at runtime — note the **entity-keyed
wrapper**, the single most common mutation-variables mistake:
```typescript
interface Hero__cCreateInput { Hero__c: Hero__cCreateRepresentation; }
interface Hero__cCreateRepresentation { Name?: string; Class__c?: string; Level__c?: number; … }
// → variables: { input: { Hero__c: { Name: "Aria", Level__c: 5 } } }
```
`sf-gql-update` is identical but the input type adds a sibling `Id: string`
(`{ input: { Hero__c: {…}, Id: "a0X…" } }`). `sf-gql-delete` uses the generic
`RecordDeleteInput { Id: string }` (`{ input: { Id: "a0X…" } }`) and selects only `Id` back —
there is no per-entity delete type. **Mutation inputs are raw values — never `{value}`-wrapped**
(that wrapper is a *read*-shape thing; mirroring it into a write is the classic failure).

> **One mutation guardrail the builder does NOT add: `allOrNone`.** The emitted document wraps the
> operation in a bare `uiapi { … }`, *not* `uiapi(input: { allOrNone: … })`. Before you ship, add
> the `allOrNone` wrapper yourself and set it explicitly — `uiapi(input: { allOrNone: true }) {
> Hero__cCreate(input: $input) { Record { … } } }` — per guardrail 4 in the spine and the
> [hand-authored templates](graphql-hand-authoring.md#mutations). graphiti gives you the `Record`
> output envelope and the entity-keyed input shape; the transaction policy is still on you.

> **You do not pass record values to the builder.** A create/update spec takes **only**
> `object`, `returnFields?`, `inputVariable?`, and `operationName?` — there is **no `fields`
> key** carrying the values to write. The builder emits the mutation *shape* (with the input
> declared as a `$variable`); the actual values become the **runtime variable** you pass to
> `sdk.graphql!.mutate({ mutation, variables })`. `returnFields` only controls what you read
> *back* after the write.

**`sf-gql-raw`** — for shapes the declarative commands don't cover, drive `select`/`set`/`var`:
```bash
npx graphiti sf-gql-raw '{"org":"…","commands":["select uiapi/query/Hero__c/edges/node/Name/value","set uiapi/query/Hero__c first=5"]}'
```
Same `@optional`/wrapper guardrails are still applied automatically.

---

## Primed vs degraded — why the guardrails sometimes vanish

This is the one behavior that surprises people, and it changes how much you can trust a single
build. The guardrail automation (`@optional`, `value`/`displayValue`, `edges/node`, the typed
result shape) is **conditional on the object being in the primed schema**. When it is, you get
the clean output above. When it **isn't** — wrong API name, not deployed, or schema not yet
refreshed after a deploy — the CLI still emits *a* query, but a **degraded** one, and flags it:

`{"org":"…","object":"Account","fields":["Name","Industry"],"first":3}` against an org whose
cache doesn't contain `Account`:

```graphql
query AccountList($after: String) {
  uiapi { query { Account(first: 3, after: $after) {
    edges { node { Name Industry } }      # ← bare fields: no @optional, no value/displayValue
    pageInfo { hasNextPage endCursor }
  } } }
}
```
…with `types` collapsing the result to `Account: unknown` and:
```json
"warnings": ["Validation: Cannot query field \"Account\" on type \"RecordQuery\"."]
```

**So: a non-empty `warnings` array — especially `Cannot query field …` — means the build is
NOT trustworthy. Do not ship a degraded query.** Re-`discover` the correct API name, or
`sf-gql-connect` with `forceRefresh: true` if you just deployed, then rebuild until
`warnings` is `[]`. A clean build is your signal that the guardrails actually fired.
**Never edit `schema.graphql` to make a degraded build pass** — the mirror is a generated,
read-only reflection of the org; adding the missing field/type there silences the warning but
grants no org access, so the operation still fails at runtime. Fix the name or deploy + refresh.

---

## Variables — parameterising a query

A `$varName` string **leaf inside `filter`** is promoted to a typed, nullable GraphQL variable,
with the type inferred from the schema:

`{"org":"…","object":"Hero__c","fields":["Name"],"filter":{"Class__c":{"eq":"$heroClass"}},"first":5}`
```graphql
query Hero__cList($after: String, $heroClass: Picklist) {
  uiapi { query { Hero__c(first: 5, after: $after, where: { Class__c: { eq: $heroClass } }) { … } } }
}
# variables: [ {after, String, false}, {heroClass, Picklist, false} ]
```

What does **not** work on the declarative tools: passing a whole-arg `$var` for `filter` or
`orderBy` (e.g. `"filter":"$where"`). Those args are typed as objects and reject a bare string
with an `INVALID_ARGS` error — promote at the **leaf**, not the whole argument. `first` is a
number and likewise can't take a `$var` string.

---

## Wiring the output into runtime

The CLI produces the operation; the rest is the existing
[Read workflow](../SKILL.md#read-workflow) / [Write workflow](../SKILL.md#write-workflow),
unchanged:

1. **Persist** the `query` string — inline `gql` for simple ops, or a `.graphql` file
   (one operation per file, imported with `?raw`) for complex ones. Use a meaningful
   `operationName` so the file/type names read well.
2. **Codegen** — `npm run graphql:codegen` (from the UI bundle dir) generates **named** types
   into `src/api/graphql-operations-types.ts`. (The CLI's `types` field is a preview of the
   same shape; codegen is the canonical import source.)
3. **Call** — `sdk.graphql!.query({ query, variables })` for reads,
   `sdk.graphql!.mutate({ mutation, variables })` for writes, using the codegen'd types and the
   `variables` the CLI listed. Surface decision (`!` vs guard), error handling, and caching are
   exactly as the SKILL spine and [sdk-api.md](sdk-api.md) describe.

The CLI never executes anything — it has no part in step 3. It just makes step 1 produce a
query you can trust.

---

## Error envelope

Failures come back as a single JSON line and set exit code `1`:

```json
{"error":{"code":"INVALID_ARGS","message":"Input failed schema validation.","details":[{"path":["mode"],"message":"Required"}]}}
```

| `code` | Means | Do |
|---|---|---|
| `INVALID_ARGS` | The spec failed Zod validation (missing/mis-typed field). `details[]` gives the JSON path. | Fix the spec per `details` — e.g. add the required `mode`, or stop passing a `$var` where an object is expected. |
| `AUTH_FAILED` | Org alias not authed / not found in local CLI auth. | Check `sf org list`; have the user authenticate the alias. |
| `SCHEMA_PRIME_FAILED` | Schema couldn't be downloaded/introspected (unreachable, or a server-side introspection error). | Retry; if it persists the org has an introspection problem — fall back to `graphql-search.sh` + hand-authoring, and tell the user. |
| `INTERNAL` | Anything else; verbatim message preserved. | Read the message. Set `GRAPHITI_DEBUG=1` for a stack trace. |

---

## Common pitfalls (failure-first)

| Symptom | Cause | Fix |
|---|---|---|
| Built query has bare fields, no `@optional`/wrappers; `types` shows `unknown` | Object not in the primed schema (typo, not deployed, stale cache) | Check `warnings` for `Cannot query field`; re-`discover` the name or `connect --forceRefresh`, rebuild until `warnings: []` |
| `$heroClass` came through as an empty string | Shell expanded `$…` in an unquoted arg | **Single-quote** the whole JSON argument |
| `INVALID_ARGS` on `"filter":"$where"` | Whole-arg `$var` not allowed on declarative tools | Promote at a leaf: `"filter":{"Field":{"eq":"$where"}}` |
| Mutation rejected at runtime / wrong shape | `{value}`-wrapped a mutation **input**, or dropped the entity-key wrapper | Inputs are raw values under the entity key: `{ input: { <Object>: { Field: v } } }`; read the `types` field |
| `Field "avg" must not have a selection…` warning | Selected `avg { value }` on a Double | Select the aggregate bare per the warning |
| New field/object missing from discover or build | Schema cached before the deploy | `sf-gql-connect` with `forceRefresh: true`, then rebuild |
| Used `graphiti new`/`cd`/`select`/`run` and it executed against the org | That's the **legacy** interactive/session flow, not the `sf-gql-*` mirror | Use the stateless `sf-gql-*` commands documented here — they compile, they don't execute |

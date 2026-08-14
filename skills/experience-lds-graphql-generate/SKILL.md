---
name: experience-lds-graphql-generate
description: "Use ALWAYS when a prompt mentions GraphQL, lightning/uiGraphQLApi, @wire(graphql, ...), or gql template tags in an LWC context — even if the surface ask is \"build an LWC\". Owns the ENTIRE flow: introspect the org's LDS GraphQL schema, identify entities/fields, construct the schema-validated gql query or mutation, wire it into the LWC via lightning/uiGraphQLApi, verify against a connected org. REQUIRED whenever a prompt asks to render, list, or edit Salesforce records (Account, Contact, Case, custom objects) via GraphQL — the .html and .js scaffolding IS in scope. DO NOT delegate to experience-lwc-generate: that skill has NO GraphQL schema introspection, NO create_lds_graphql_read_query binding, and defaults to getRecord/getRelatedListRecords wire adapters which will not satisfy a GraphQL prompt. DO NOT TRIGGER only if the prompt forbids GraphQL, chooses UIAPI/Apex (use experience-lds-best-practices-apply), or asks for data requirements (use experience-lds-data-requirements-generate)."
metadata:
  version: "1.0"
  cliTools:
    - tool: ["python3"]
      semver: ">=3.8"
    - tool: ["sf"]
      semver: ">=2.0.0"
---
<!-- adk-managed-skill -->

# Building LDS GraphQL

Generate schema-validated Salesforce LDS GraphQL queries (read or mutation), either as standalone queries or wired into a Lightning Web Component via the `lightning/graphql` adapters. The skill encodes the schema-as-source-of-truth workflow end-to-end. Two bundled bash scripts handle the org-aware steps — `scripts/fetch-lds-graphql-schema.sh` for schema introspection and `scripts/test-lds-graphql-query.sh` for live-org validation.

## When to Use

- User wants to create, modify, or integrate a Salesforce GraphQL query (standard objects, custom objects, or setup objects).
- Building or updating an LWC that consumes/mutates LDS data through GraphQL.
- Introspecting an org's schema before writing a query.
- Validating a generated query end-to-end against a connected org.

Do NOT use this skill for:
- REST-based UI API (use LDS wire adapters; see `experience-lds-best-practices-apply`).
- Apex callouts or custom GraphQL endpoints — this skill is LDS-scoped.
- Data-requirements discovery — that's `experience-lds-data-requirements-generate`.

## Prerequisites

- A connected Salesforce org (username or alias). User must confirm it before schema fetch — never assume.
- Salesforce CLI / `sf` available in the shell for the schema fetch.
- Decision on:
  - **Namespace** — `uiapi` (default: standard + custom objects) or `setup` (setup objects like permission sets, profiles).
  - **Query type** — `read` (default) or `mutation`.
  - **Output format** — `standalone` (raw GraphQL + variables) or `LWC integration` (full component wiring).

## Core Rules

These apply to every step — they are the rules this skill enforces:

1. **Sequential execution** — Steps 1→6 run in order. Every step is mandatory unless its triggering conditions are not met.
2. **Hard stop on failure** — A failed step blocks subsequent steps until remediation is complete.
3. **Schema is the single source of truth** — Every entity name, field name, field type, and relationship must come from `schema.graphql` introspection. Never use common Salesforce knowledge (e.g., do not assume `Owner` is a `User` — it may be polymorphic).
4. **Report each step** — Use the provided templates before advancing.
5. **Error reporting** — Categorize errors; never echo raw tool output into the chat.

## Workflow

The full normative workflow lives in [references/generation-guide.md](references/generation-guide.md). Read it before starting. Read-query specifics are in [references/generation-query.md](references/generation-query.md); mutation specifics are in [references/generation-mutation.md](references/generation-mutation.md).

### Step 1 — General query information

Collect and echo back:

```text
Query type:       [read | mutation]
Namespace:        [uiapi | setup]
Output format:    [standalone | LWC integration]
```

If any is unclear, ask once and wait.

### Step 2 — Acquire the schema

1. Ask for the `usernameOrAlias`. If a default is inferred from context, present it and wait for explicit confirmation.
2. Run `scripts/fetch-lds-graphql-schema.sh USERNAME_OR_ALIAS [OUTPUT_PATH] [API_VERSION]` with the confirmed alias. The script writes the SDL to `schema.graphql` (or the path you pass) so the schema never enters the chat context. If a non-empty `schema.graphql` already exists at `OUTPUT_PATH`, the script exits early (set `LDS_FETCH_FORCE=1` to re-fetch).
3. On failure: **hard stop**, report category, ask user to resolve org access, then retry.

#### Using the schema file

The schema is 265,000+ lines. **NEVER** read the whole file — use targeted `grep` calls only.

- Object type: `^type <ObjectName> implements Record` with `-A 100`.
- Filter: `^input <ObjectName>_Filter` with `-A 50`.
- OrderBy: `^input <ObjectName>_OrderBy` with `-A 30`.
- Mutation input: `^input <ObjectName>(Create|Update)Input` with `-A 50`.

**Search budget**: max 4–5 grep calls per entity. Plan before executing.

### Step 3 — Entity identification

1. Entity names are PascalCase.
2. If names aren't given, extract candidates from `^type <Name> implements Record` matches.
3. If any entity is still unresolved, ask the user and wait.
4. Report:
   ```text
   Identified entities:
   - EntityName (Field1, Field2, ...)
   Unknown entities:
   - <textual name>
   Step 3 status: SUCCESS | FAILED
   ```
5. If `Unknown entities` is non-empty → status `FAILED` → ask for clarification → restart Step 3.

### Step 4 — Iterative entity introspection

Iteration limit: **3 cycles** (primary entity → references → child relationships). Hard-stop after 3.

Per cycle:

1. Remove already-introspected entities from the list.
2. Grep for the remaining entities' fields using the schema patterns above.
3. Extract standard field types.
4. Identify **reference fields** (`Owner: User`). Fields with the same name on different entities may have different types — check each entity independently. If a field resolves to multiple entity types, mark it **polymorphic** and plan to use inline fragments (`... on TypeA`, `... on TypeB`).
5. Identify **child relationships** (Connection types, e.g., `Contacts: ContactConnection`). Add new entities to the unknown list.
6. If unknown list not empty and iterations < 3, loop.
7. Report:
   ```text
   [PASS|FAIL] EntityName
     - Standard fields: FieldName (type), ...
     - Reference fields: FieldName → TargetType, ...
     - Polymorphic fields: FieldName → [TypeA, TypeB], ...
     - Child relationships: RelationshipName → ChildType, ...
     - Unknown fields: FieldName, ...
   Introspection cycles used: N/3
   Step 4 status: SUCCESS | FAILED
   ```
8. If any entity is `[FAIL]` → global `FAILED` → remediation → resume from cycle start.

### Step 5 — Read query generation (only if query type is `read`)

Author the read query per [references/generation-query.md](references/generation-query.md), feeding in the introspection data, entity list, field types, output format, and `usernameOrAlias`.

Apply the rules in [references/generation-query.md](references/generation-query.md) — covers:
- Query root / namespace selection (`uiapi.query` vs `setup.query`).
- Field selection discipline (ask only for fields actually needed — every field is a billable scan).
- Filter operators (`eq`, `ne`, `in`, `nin`, `gt`, `gte`, `lt`, `lte`, `like`, `contains`).
- OrderBy (per-field direction).
- Pagination (`first`, `after`, `last`, `before`; `edges.node`, `pageInfo`).
- Polymorphic inline fragments.
- Aliasing and variable placeholders.
- Standalone vs LWC output (wire adapter from `lightning/graphql`, `gql` tagged template, `refreshGraphQL` for imperative refresh).

If the tool returns an error, categorize it and ask the user how to proceed.

### Step 6 — Mutation query generation (only if query type is `mutation`)

Author the mutation per [references/generation-mutation.md](references/generation-mutation.md) — covers:
- `create`, `update`, `delete` operation shape.
- Input types (`<Entity>CreateInput`, `<Entity>UpdateInput`) discovered via the `input` grep pattern.
- Required vs optional fields (from schema's `!` annotation).
- Reference-field updates using `Id` only.
- Return selection — what to read back after the mutation to drive cache consistency.
- Error handling (`record.errors[]`).
- LWC integration: imperative mutation via `graphqlMutate` from `lightning/graphql`.

### Step 7 — Test the query

Run `scripts/test-lds-graphql-query.sh USERNAME_OR_ALIAS 'QUERY' '<VARIABLES_JSON>'` against the confirmed `usernameOrAlias` and present the response shape/sample to the user. Errors are categorized, not echoed verbatim.

## Cross-References

- Bundled scripts:
  - `scripts/fetch-lds-graphql-schema.sh` — schema acquisition via a GraphQL introspection query against the org's `/services/data/vX/graphql` endpoint (LDS exposes no `/graphql/sdl` route); call once per org/session before query authoring.
  - `scripts/test-lds-graphql-query.sh` — org-backed validation of the generated query against `/services/data/vX/graphql`.
- Related skills:
  - `experience-lds-best-practices-apply` — general LDS principles, cache semantics, and wire-vs-imperative choice.
  - `experience-lds-data-requirements-generate` — pre-work that decides *what* to query before this skill decides *how*.
  - `experience-lwc-generate` — host the generated wire adapter cleanly.

## Examples

**Standalone read — minimal**

```graphql
query Accounts($limit: Int = 10) {
  uiapi {
    query {
      Account(first: $limit) {
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
```

**LWC integration — read with wire**

```javascript
import { LightningElement, wire } from 'lwc';
import { gql, graphql } from 'lightning/graphql';

export default class AccountList extends LightningElement {
    @wire(graphql, {
        query: gql`
            query Accounts($limit: Int = 10) {
                uiapi {
                    query {
                        Account(first: $limit) {
                            edges { node { Id Name { value } } }
                        }
                    }
                }
            }
        `,
        variables: '$variables'
    })
    accounts;

    variables = { limit: 10 };

    get records() {
        return this.accounts?.data?.uiapi?.query?.Account?.edges ?? [];
    }
}
```

## Verification

- `Step 3 status: SUCCESS` before Step 4; `Step 4 status: SUCCESS` before Steps 5/6.
- Every field in the generated query appears in the introspection report (no hallucinated fields).
- Polymorphic fields use inline fragments; non-polymorphic fields do not.
- For mutations, every required input field (`!` in schema) is present.
- `scripts/test-lds-graphql-query.sh` returns without errors; or, on error, a categorized remediation is presented.
- If output format is `LWC integration`, the component imports from `lightning/graphql`, uses `gql` tagged template, and exposes data via a getter (not directly in HTML).

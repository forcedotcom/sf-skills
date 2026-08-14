# GraphQL Query Generation Guidelines

## Role

You are a Salesforce GraphQL expert specializing in generating schema-validated GraphQL queries. You generate read and mutation queries by introspecting the org's GraphQL schema — never from memory or common Salesforce knowledge.

**Communication style**: Report progress at each step using the templates provided. When user input is needed, ask one clear question and wait for the answer before proceeding.

## Org-Aware Scripts

This reference is the canonical workflow. The skill bundles two bash scripts (under its `scripts/` directory) for the org-aware steps the agent cannot encode:

- `scripts/fetch-lds-graphql-schema.sh USERNAME_OR_ALIAS [OUTPUT_PATH] [API_VERSION]` — POSTs a GraphQL introspection query to `/services/data/vX/graphql` (LDS exposes no SDL route), renders the response as SDL, and writes it to disk for local introspection (Step 2)
- `scripts/test-lds-graphql-query.sh USERNAME_OR_ALIAS 'QUERY' ['VARIABLES_JSON'] [API_VERSION]` — Executes a generated GraphQL query/mutation against `/services/data/vX/graphql` and prints the raw JSON response (Step 5/6 testing workflows)

Both scripts authenticate through the Salesforce CLI via `sf api request rest` (the CLI supplies stored credentials internally — no access token is extracted into the script); the user must `sf org login web --alias <ALIAS>` once per org.

All other generation logic — read query authoring, mutation authoring, validation rules, output formatting — lives in this skill's reference files ([generation-query.md](generation-query.md), [generation-mutation.md](generation-mutation.md)) and is applied directly by the agent.

## Core Rules

These rules apply to every step of the workflow:

1. **Sequential execution** — Follow Steps 1–6 in order. Every step is mandatory unless its triggering conditions are not met.
2. **Hard stop on failure** — A failed step blocks all subsequent steps until its remediation actions are completed.
3. **Schema is the single source of truth** — All entity names, field names, field types, and relationship types must come from `schema.graphql` introspection data. Never rely on common Salesforce knowledge (e.g., do not assume `Owner` is of type `User` — the field might have a different type or be polymorphic).
4. **Report each step** — Use the provided report template for each step before proceeding to the next.

## STEP 1: General Query Information

### Information Workflow

1. **Identify namespace** — `uiapi` (standard/custom objects, default) or `setup` (Setup-only objects such as permission sets or profiles). If unclear, ask the user.
2. **Identify query type** — `read` or `mutation`, defaults to `read`
3. **Identify desired output format**:
   - **Standalone** (default) — A raw GraphQL query string and variables object, ready to execute outside of an LWC
   - **LWC integration** — A complete LWC component class wiring the query via `lightning/graphql` adapters
4. Report using the template below

### Information Report Template

```text
Query type:       [read | mutation]
Namespace:        [uiapi | setup]
Output format:    [standalone | LWC integration]
```

## STEP 2: Acquire Schema

The goal of this step is to secure a local `schema.graphql` file as the single source of introspection truth.

### Org Confirmation Workflow

1. Ask the user for the `usernameOrAlias` to use when fetching the schema
2. If an org is suggested by context or defaults, present it to the user and ask for explicit confirmation before proceeding
3. If the user does not provide or confirm an org, **HARD STOP** — exit this workflow on error

### Schema Download

Before proceeding to entity identification, download the org's GraphQL schema for local introspection. This enables significantly faster query generation and avoids repeated remote introspection calls.

1. Check if `schema.graphql` already exists in project root
   - If found, skip to [Using Schema File](#using-schema-file)
2. Run `scripts/fetch-lds-graphql-schema.sh USERNAME_OR_ALIAS [OUTPUT_PATH] [API_VERSION]`
   - The script POSTs a GraphQL introspection query to the org's `/services/data/vX/graphql` endpoint (LDS exposes no SDL route), renders the response as SDL, and writes it to disk in one call
   - The schema content never enters the conversation context — only the file path is returned to the user
   - Defaults: output path `schema.graphql`, api version `66.0`
   - On success, skip to [Using Schema File](#using-schema-file)
3. If the script fails, **HARD STOP**
   - Report the failure reason (auth, HTTP, or empty response — all surfaced on stderr)
   - Ask the user to resolve org access (`sf org login web --alias <ALIAS>`) and retry the [Schema Download](#schema-download) step
4. If `schema.graphql` is still unavailable, **HARD STOP** — query generation cannot proceed

### Report

Report that introspection will use the local `schema.graphql` file retrieved via `scripts/fetch-lds-graphql-schema.sh`.

### Using Schema File

> **Critical**: Schema file is ~265,000+ lines. NEVER use Read tool on the entire file. Use targeted Grep calls only.

#### Grep Patterns

**Object type definition:**

- **Pattern**: `^type <ObjectName> implements Record`
- **Context**: `-A 100`
- **Extract**: Field names, types (StringValue, IntValue, etc.), relationships

**Filter / OrderBy / Mutation types:**

- **Filter**: `^input <ObjectName>_Filter` with `-A 50`
- **OrderBy**: `^input <ObjectName>_OrderBy` with `-A 30`
- **Mutation**: `^input <ObjectName>(Create|Update)Input` with `-A 50`

**Search budget**: Maximum 4–5 Grep calls per entity. Plan searches before executing them.

## STEP 3: Entity Identification

Extract and list the **entities** involved in the query to generate.

### Workflow

1. Entity names must use PascalCase convention
2. If entity names are not provided and cannot be deduced from context, use the [Map Entity Names](#map-entity-names) sub-workflow
3. If entity names remain unresolved after mapping, ask the user for their names and wait for the answer
4. Do **not** resolve exact field names yet — that happens in [Step 4](#step-4-iterative-entity-introspection)
5. Report using the [Identification Report Template](#identification-report-template)
6. Evaluate [hard stop rules](#identification-hard-stop-rules)

### Map Entity Names

Extract entities from `schema.graphql`:

1. Use the Grep patterns from [Using Schema File](#using-schema-file), especially `^type <ObjectName> implements Record`
2. Build the candidate entity list from those type definitions
3. If some entities are still unresolved from user intent, ask the user for clarification and wait for their answer

### Identification Hard Stop Rules

If the unknown entity list is not empty:

- Set global step status to `FAILED`
- Stop generation
- Execute [remediation actions](#identification-remediation-actions)

### Identification Remediation Actions

**Condition**: Only if global step status is `FAILED`

Ask the user for clarification on unknown entities, then restart [Step 3](#step-3-entity-identification).

### Identification Report Template

```text
Identified entities:
- EntityName (Field1, Field2, ...)

Unknown entities:
- entity textual name

Step 3 status: SUCCESS | FAILED
```

## STEP 4: Iterative Entity Introspection

Extract and list entity **fields** involved in the query to generate.

### Introspection Workflow

**Iteration limit**: Maximum 3 introspection cycles (primary entity → references → child relationships). If unresolved entities remain after 3 cycles, **HARD STOP** and ask the user for clarification.

Using the list of entities from [Step 3](#step-3-entity-identification), follow these steps in order:

1. **Cleanup** — Remove from the list all entities for which introspection data was already retrieved
2. **Introspection** — Retrieve introspection data for all remaining entities:
   - Use Grep patterns from [Using Schema File](#using-schema-file)
   - If no introspection data is returned for an entity, **HARD STOP** — skip to step 8
3. **Fields identification** — Extract requested field types from introspection data
4. **Reference fields** — Identify reference fields from the schema (e.g., `Owner: User`):
   - Two fields with the same name on different entities may have different types — always check each entity independently
   - **Polymorphic fields** — If a reference field resolves to multiple entity types in the schema, mark it as polymorphic. In the generated query, use inline fragments (`... on TypeA`, `... on TypeB`) to access type-specific fields
   - Add any newly discovered entity types to the unknown list
5. **Child relationships** — Identify child relationships (Connection types, e.g., `Contacts: ContactConnection`):
   - Add any newly discovered child entity types to the unknown list
6. **Next cycle** — If the unknown list is not empty and the iteration limit has not been reached, resume from step 1
7. **Field type information** — All type info must come from `schema.graphql` introspection data
8. **Report** — Use the [Introspection Report Template](#introspection-report-template)
9. **Evaluate** — Apply [hard stop rules](#introspection-hard-stop-rules)

### Introspection Hard Stop Rules

If the global status is `FAILED`, **STOP** generation and execute [introspection remediation actions](#introspection-remediation-actions).

### Introspection Remediation Actions

**Condition**: Only if global step status is `FAILED`

Ask the user for clarification on unknown fields, then resume the [Introspection Workflow](#introspection-workflow).

### Introspection Report Template

An entity is `[PASS]` only if it has no unknown fields, otherwise it is `[FAIL]`.
If any entity is `[FAIL]`, the global status is `FAILED`.

```text
Introspection results:

[PASS|FAIL] EntityName
  - Standard fields: FieldName (type), ...
  - Reference fields: FieldName → TargetEntityType, ...
  - Polymorphic fields: FieldName → [TypeA, TypeB], ...
  - Child relationships: RelationshipName → ChildEntityType, ...
  - Unknown fields: FieldName, ...

[PASS|FAIL] EntityName2
  - ...

Introspection cycles used: N/3
Step 4 status: SUCCESS | FAILED
```

## STEP 5: Read Query Generation

**Triggering conditions:**

1. [Step 4](#step-4-iterative-entity-introspection) global status is `SUCCESS`
2. Query type is `read`

### Workflow

1. Apply the read-query authoring rules in [generation-query.md](generation-query.md), feeding in the introspection data, entity list, field types, output format (standalone or LWC), and `usernameOrAlias` from previous steps
2. If a rule cannot be satisfied (e.g. a field type cannot be resolved), report the gap and ask the user how to proceed
3. Present the generated query to the user using the output format selected in Step 1
4. Execute the testing workflow at the end of [generation-query.md](generation-query.md) using `scripts/test-lds-graphql-query.sh`

## STEP 6: Mutation Query Generation

**Triggering conditions:**

1. [Step 4](#step-4-iterative-entity-introspection) global status is `SUCCESS`
2. Query type is `mutation`

### Workflow

1. Apply the mutation-query authoring rules in [generation-mutation.md](generation-mutation.md), feeding in the introspection data, entity list, field types, output format (standalone or LWC), and `usernameOrAlias` from previous steps
2. If a rule cannot be satisfied (e.g. a required `Create` field is missing or non-creatable), report the gap and ask the user how to proceed
3. Present the generated query to the user using the output format selected in Step 1
4. Execute the testing workflow at the end of [generation-mutation.md](generation-mutation.md) using `scripts/test-lds-graphql-query.sh`

## Error Reporting Rules

When reporting errors from schema acquisition, introspection, or query generation:

1. **Categorize, don't echo** — Report error category and short impact, not raw command/tool output
2. **Actionable remediation** — Provide a next action as a safe retry path (confirm org alias, retry tool call, re-check schema file path)

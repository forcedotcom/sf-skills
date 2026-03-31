# Schema Introspection

## Schema Access Policy

The `schema.graphql` file is **265,000+ lines**. Loading it into context or opening it in an editor will overwhelm the context window or crash tools.

Do not use cat, less, more, head, tail, editors (VS Code, vim, nano), or programmatic parsers (node, python, awk, sed, jq) on `schema.graphql`. Use the schema search script or targeted grep calls only.

## Schema Lookup

Run the search script from the **SFDX project root** to get all relevant schema info in one step:

```bash
bash scripts/graphql-search.sh <EntityName>
# Multiple entities:
bash scripts/graphql-search.sh Account Contact Opportunity
```

**Maximum 2 script runs.** If the entity still can't be found after checking naming variations, ask the user.

## Entity Identification

Map user intent to PascalCase entity names:

1. Convert natural language to PascalCase (e.g., "accounts" → `Account`, "case comments" → `CaseComment`, "custom objects" → `CustomObject__c`)
2. Run the schema search script to validate the entity exists
3. If a candidate does not match, try:
   - `__c` suffix for custom objects, `__e` for platform events
   - **`_Record` suffix** — Objects added to UI API in API v60+ may use `<EntityName>_Record` as their type name (e.g., `FeedItem_Record` instead of `FeedItem`)
4. If an entity cannot be resolved, **ask the user** for the correct name — do not guess

## Iterative Introspection

Use a maximum of **3 introspection cycles** to resolve all entities and their dependencies:

1. **Introspect** — Run the schema search script for each unresolved entity
2. **Fields** — Extract requested field names and types from the type definition output
3. **References** — Identify reference fields. If a reference resolves to multiple types, mark it as **polymorphic** (use inline fragments in the generated query). Add newly discovered entity types to the working list.
4. **Child relationships** — Identify Connection types (e.g., `Contacts: ContactConnection`). Add child entity types to the working list.
5. **Next cycle** — If unresolved entities remain and the cycle limit hasn't been reached, repeat from step 1

### Hard Stop Rules

- If no introspection data is returned for an entity, **stop** — the entity may not be deployed
- If unknown entities remain after 3 cycles, **stop** — ask the user for clarification
- Do not proceed with query generation until all entities and requested fields are confirmed in the schema

## Deployment Prerequisites

The schema reflects the **current org state**. Custom objects and fields appear only after metadata is deployed.

- **Before** running `npm run graphql:schema`: Deploy all metadata and assign permission sets. Invoke the `deploying-ui-bundle` skill for the full sequence.
- **After** any metadata deployment: Re-run `npm run graphql:schema` and `npm run graphql:codegen` so types and queries stay in sync.

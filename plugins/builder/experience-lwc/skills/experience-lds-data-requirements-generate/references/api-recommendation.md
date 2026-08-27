# API Recommendation for Salesforce Data Requirements

## Priority Order

1. **GraphQL wire adapter (`lightning/graphql`)** — top choice for all read scenarios it supports.
2. **UI API / Lightning Data Service (LDS)** — second choice for CRUD writes, metadata, layouts, picklists, and simple reads.
3. **Apex** — fallback only when GraphQL and UI API cannot meet the requirement.

## Inputs that drive the recommendation

For every data need in the PRD or LWC source, examine:

- The operation type (read, create, update, delete, mixed).
- The objects and fields touched, and whether each is supported by the UI API allowlist.
- The data-relationship shape (single record, related list, parent-child hierarchy, multi-object join).
- Query complexity (filtering, sorting, pagination, aggregation).
- Performance constraints (data volume, round-trip count, payload size).
- Specialized concerns (picklists, layouts, record-create defaults, atomic transactions, system-context permissions).

## Decision framework

**Step 1 — Operation type assessment**

- Read-only operations → GraphQL wire adapter first.
- Write operations → UI API for single-record CRUD; Apex for complex multi-record transactions.
- Mixed read/write → separate recommendations per operation.

**Step 2 — Object and field support analysis**

- UI API supported objects/fields → GraphQL and UI API both viable.
- Unsupported objects/fields → fallback to Apex.

**Step 3 — Data relationship requirements**

- Single object, simple fields → UI API `getRecord` or GraphQL.
- Multi-object relationships → GraphQL excels at nested queries.
- Related lists → UI API related-list functions or GraphQL for complex cases.
- Parent-child hierarchies → GraphQL for efficient single-call data fetching.

**Step 4 — Query complexity evaluation**

- Simple record retrieval → UI API `getRecord`.
- Complex filtering/sorting → GraphQL (SOQL-like).
- Pagination → GraphQL native cursor/offset support.
- Aggregation → GraphQL for complex aggregates.

**Step 5 — Performance and scalability considerations**

- Multiple API calls needed → GraphQL reduces round trips.
- Large datasets → GraphQL with pagination.
- Minimal data transfer → GraphQL precise field selection prevents over-fetching.

**Step 6 — Specialized requirements**

- Picklists, object info, layouts → UI API.
- Record creation with defaults → UI API `getRecordCreateDefaults` + `createRecord`.
- List views → UI API list functions.
- Atomic transactions → Apex.
- Custom business logic / system context / elevated permissions → Apex.

## Recommendation Rules

**Recommend GraphQL when**

- Read-only operations on UI API supported objects/fields.
- Multi-object relationships in a single call.
- Complex filtering, sorting, or pagination.
- Performance optimization via reduced round trips.
- Dynamic UI with changing data shape.
- Aggregation or SOQL-like needs.

**Recommend UI API when**

- Create, update, or delete operations on supported objects.
- Metadata requirements (picklist values, object info, layouts).

**Recommend Apex when**

- Objects or fields not supported by UI API.
- Multi-record atomic transactions.
- Custom business logic or server-side validation.
- System context or elevated permissions.
- Complex server-side processing beyond platform capabilities.

## Output contract

For each data need identified in the input, produce one recommendation entry with these fields:

- **`dataNeed`** — one-sentence description of what the LWC needs (e.g. "Read Account name + industry for a record-detail view").
- **`api`** — exactly one of `GraphQL`, `UIAPI`, `Apex`.
- **`reason`** — one sentence pointing at the rule above that selected the API (e.g. "Read-only single-object query on a UI-API-supported object → GraphQL").
- **`adapter`** — the specific adapter or method (e.g. `@wire(graphql, ...)`, `getRecord`, `@AuraEnabled` Apex method name).

Produce the recommendation as the populated entry above. Do not emit `TODO` comments in the code or PRD; the recommendation is the production output.

When no data needs are identified in the input, produce an empty list. Do not invent data needs or duplicate the same need under multiple recommendations.

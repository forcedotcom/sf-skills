---
name: experience-lds-data-requirements-generate
description: "Use when a Lightning Web Component data need is described in ambiguous natural language — turn \"get contact info\" or \"show account data\" into a clear, PRD-ready data-requirements spec. TRIGGER when the user says \"define data requirements for this LWC\", \"turn this PRD data section into validated object/field names\", \"recommend GraphQL vs UIAPI for this data need\", \"validate these Salesforce API names\", or \"spec out the LDS adapter for this component\", or references LWC bundle files (`.js`, `.js-meta.xml`) whose data layer is not yet specified. DO NOT TRIGGER when the data layer is already fully specified, when authoring the actual query or adapter code from a known spec, or when implementing an LWC end-to-end (use experience-lwc-generate)."
metadata:
  version: "1.0"
  relatedSkills:
    - experience-lwc-generate
---
<!-- adk-managed-skill -->

# Generating LDS Data Requirements

Run a three-stage analyst workflow — requirements clarification, API name validation, API recommendation — so a downstream developer can implement a Lightning Data Service (LDS) solution without guessing.

## When to Use

- A PRD, Figma comment, or user ask mentions Salesforce data but objects/fields/operations are vague ("show customer info", "update the record", "list upcoming gigs").
- Before writing any `@wire`/Apex code for a new data need, or before handing the recommendation to a downstream implementation workflow.
- You inherited TODOs like `// TODO: fetch related records` and need to turn them into precise specs.

Do NOT use this skill when:
- The data need is already fully specified (object API name, field API names, operation type, scope).
- The component does not touch Salesforce data at all (UI-only, external REST, local state).

## Prerequisites

- The natural-language requirement (PRD snippet, user ask, or TODO comment).
- Access to the target org's Setup → Object Manager for confirming custom object/field API names.
- Awareness of the current GraphQL / UI API / Apex priority order (top-of-funnel is GraphQL when it can serve the read).

## Knowledge Bases

- [references/requirements-analysis.md](references/requirements-analysis.md) — Requirements Analysis Mode framework.
- [references/api-name-validation.md](references/api-name-validation.md) — Precision Mode for object/field API names.
- [references/api-recommendation.md](references/api-recommendation.md) — GraphQL → UI API → Apex decision framework.
- [references/lds-expert.md](references/lds-expert.md) — overall LDS patterns and pitfalls.
- [references/lds-data-consistency.md](references/lds-data-consistency.md) — cache and consistency guarantees.
- [references/lds-referential-integrity.md](references/lds-referential-integrity.md) — parent/child and related-record rules.

## Workflow

Run the three steps strictly in order. Do not skip a step unless the caller has already confirmed its output.

### Step 1 — Parse data requirement (Requirements Analysis Mode)

**Goal:** extract everything you know and surface every uncertainty before moving on.

Open every conversation with:

> "I've analyzed your data requirement: '<REQ>'. Here's what I understand and what I need clarification on…"

Apply the four actions from [references/requirements-analysis.md](references/requirements-analysis.md):

1. **Operation type** — Is it read, create, update, or delete? Ambiguous verbs trigger an immediate clarifying question. Confirm with: *"I've identified this as a **<OP>** operation. Is this correct?"*
2. **Data entity identification** — Standard object (high confidence, proceed), suspected custom object (ask: *"Is this a custom object `<Term>__c`? What's the exact API name?"*), or unknown (ask for the API name from Object Manager).
3. **Field specification** — Map generic references (`phone`, `address`, `name`, `status`) to specific API names. If multiple candidates exist, enumerate them and ask.
4. **Scope and context** — One record vs. many; user-triggered vs. auto; expected volume; real-time vs. on-demand.

**End-of-step gate.** Consolidate into:

```text
Clear Requirements: [confirmed facts]
Need Clarification: [numbered questions from 1.1–1.4]
```

Proceed only when every question is answered with ≥90% confidence.

### Step 2 — Validate Salesforce API names (Precision Mode)

**Goal:** 100% accuracy on every object and field API name before code is written.

Apply the validation framework from [references/api-name-validation.md](references/api-name-validation.md):

- **Standard objects** — `Account`, `Contact`, `Lead`, `Opportunity`, `Case`, `User`, `Task`, `Event`, `Product2`, `Pricebook2`, `Order`, `OrderItem`, `Asset`, `Contract`, `Campaign` pass immediately. Anything else triggers verification.
- **Custom objects** — Never assume `__c` suffixes. Ask: *"Is this `<Term>__c` or a different custom object API name?"* Point users to Setup → Object Manager → <Object> → Details → API Name.
- **Standard fields** — Map ambiguous references using the tables in the reference file.
- **Custom fields** — Require `__c` suffix confirmation; case-sensitive.

**Confirmation template:**

```text
Object API Name: <OBJECT>
Field API Names: <FIELD_LIST>
Confidence Level: 100% validated
```

If any uncertainty remains, **stop**. Emit the outstanding verification requests and the Setup navigation instructions. Do not advance to Step 3 or generate code.

Skip this step only when the caller has explicitly stated that API names are already validated upstream, or the requirement does not involve records at all. Record the skip reason in the Step 4 output.

### Step 3 — Recommend the API (Solution Architecture Mode)

**Goal:** pick the right data access API using the decision framework in [references/api-recommendation.md](references/api-recommendation.md).

**Priority order (non-negotiable):**

1. GraphQL wire adapter (`lightning/graphql`) — top choice for reads it can serve.
2. UI API / LDS — CRUD writes, metadata, layouts, picklists, simple reads.
3. Apex — fallback only.

Walk the six decision sub-steps:

1. Operation type (read / write / mixed).
2. Object & field support in UI API.
3. Relationship complexity (single vs. multi-object, parent/child).
4. Query complexity (filtering, sorting, pagination, aggregation).
5. Performance & scalability (round trips, payload size).
6. Specialized needs (metadata, atomic transactions, business logic, elevated permissions).

**Recommendation rules:**

- **GraphQL** when read-only on supported objects; multi-object joins; pagination/sort/filter; aggregation; minimizing round trips.
- **UI API** when CRUD writes, metadata (picklists, layouts, object info), `getRecordCreateDefaults` + `createRecord`, list views.
- **Apex** when UI API doesn't support the object/field; multi-record atomic transactions; custom business logic; system-context permissions.

Present with the "Show Your Work" template — explicitly explain *why not GraphQL* / *why not UI API* / *why not Apex*.

**Hand-off:**

- GraphQL recommended → document the query shape (root object, requested fields, filters) in the Step 4 output; downstream authoring of the actual `lightning/graphql` wire adapter is the caller's next step.
- UI API recommended → document the specific UI API adapter (`getRecord`, `getRelatedListRecords`, `createRecord`, `updateRecord`, `getRecordCreateDefaults`, etc.) and any layout/picklist prerequisites.
- Apex recommended → document the reason in the Step 4 output and hand off to the project's Apex workflow of record.

### Step 4 — Emit the PRD-ready specification

Produce a single block the caller can paste into a PRD or component file header:

```text
## Data Requirement: <CLEAR_TITLE>

### Technical Specification
- Primary Object: <OBJECT_API_NAME>
- Required Fields: <FIELD_API_NAMES>
- Relationships: <RELATED_OBJECTS_OR_LOOKUPS_OR_NONE>
- Data Scope: <SINGLE_RECORD | MULTIPLE_RECORDS | QUERY_BASED>
- Access Pattern: <READ_ONLY | READ_WRITE | WRITE_ONLY>
- Trigger: <USER_ACTION | AUTO_ON_LOAD | REACTIVE>

### Implementation Details
- Recommended LDS API: <GRAPHQL | UI_API | APEX>
- Implementation Pattern: <WIRE | IMPERATIVE>
- Rationale: <WHY THIS API, NOT THE OTHERS>
- Next step: <author the GraphQL wire adapter | author the UI API adapter call | project's Apex workflow>
```

## Few-Shot Patterns

| Vague ask | Clarifying question |
|-----------|--------------------|
| "get contact info" | "Which `Contact` fields specifically? (`Email`, `Phone`, `MailingAddress`, `Department`, …)" |
| "show account data" | "Which `Account` fields do you need? And are we showing one record or a list?" |
| "custom gym records" | "Is this a custom object `Gym__c`? What specific fields are you looking for?" |
| "update the record" | "Which object? Which fields? Which record (ID at runtime)?" |
| "all customer information" | "`Account` or `Contact`? Which fields? Single record or query?" |

## Verification Checklist

- [ ] Every ambiguous term from the original requirement resolved to a confirmed API name.
- [ ] Operation type confirmed (R / C / U / D).
- [ ] Scope (single vs. many) and trigger (user vs. auto) documented.
- [ ] API recommendation justified against all three options (GraphQL / UI API / Apex).
- [ ] Concrete next action named — either the specific downstream adapter to wire (`lightning/graphql`, `getRecord`, `createRecord`, etc.) or the project's Apex workflow of record.
- [ ] If Step 2 was skipped, the reason is recorded in the output.
- [ ] Specification block copy-pasteable into the PRD.

## Cross-References

- Skills:
  - Output is consumed by `experience-lwc-generate` when wiring `@wire` adapters into a component.
- Downstream authoring steps (not skill-bound today):
  - GraphQL path — the caller writes the `lightning/graphql` wire adapter using the schema pulled from the target org.
  - UI API path — the caller wires the recommended UI API adapter (`getRecord`, `createRecord`, etc.).

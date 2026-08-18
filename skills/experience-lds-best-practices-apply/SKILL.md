---
name: experience-lds-best-practices-apply
description: "Use when reviewing or implementing Lightning Data Service best practices in an LWC (.js, .html, .js-meta.xml) — UIAPI vs Apex, refreshApex / notifyRecordUpdateAvailable, @salesforce/schema imports, LDS record-form data patterns. TRIGGER on \"apply LDS best practices to this LWC\", \"review this LWC for LDS best-practice issues\", \"review this component for Lightning Data Service issues\", \"UIAPI or Apex for this data?\", \"fix stale data after record save\", \"sync LDS cache\", \"use @salesforce/schema for field names\", \"choose between getRecord and Apex\". DO NOT TRIGGER when building a new LWC (use experience-lwc-generate), applying SLDS design tokens (use design-systems-slds-apply), picking or wiring a `lightning-*` base component's props/events/slots generically (use experience-lwc-base-components-integrate — this skill covers only the LDS data-layer rationale, even when the fix involves a base record form), or for security / RTL / accessibility reviews (separate passes)."
metadata:
  version: "1.0"
  domains: ["Experience", "Platform"]
  relatedSkills:
    - design-systems-slds-apply
    - experience-lwc-base-components-integrate
    - experience-lwc-generate
---
<!-- adk-managed-skill -->

# Applying LDS Best Practices

Apply the Lightning Data Service guidelines to a Lightning Web Component. Three pillars: **data consistency**, **referential integrity**, and **UIAPI vs Apex**. Focused on the UI API path — GraphQL and upstream data-requirements analysis are handled out-of-band.

## When to Use

- Reviewing a component's data layer for LDS compliance (hand-rolled forms, stringly-typed field names, un-synchronized Apex + LDS, Apex overuse).
- Implementing CRUD on standard or custom objects.
- Deciding between `getRecord`, `getRecords`, `createRecord`, `updateRecord`, `deleteRecord`, base record form components, or Apex.
- Fixing stale-data bugs after record mutation.
- Adding schema imports (`@salesforce/schema/...`) to replace hard-coded field/object names.

Do NOT use this skill for:
- GraphQL query/mutation generation — handled out-of-band today.
- Upstream data-requirements discovery — handled out-of-band today.
- SLDS class / design-token work (use `design-systems-slds-apply`).
- Accessibility, security, or RTL review — those are separate passes run with their own tooling.

## Prerequisites

- Component path.
- Understanding of the component's data operations (read / write / both) and whether Apex is already involved.
- Access to the org's schema for `@salesforce/schema` imports (Setup → Object Manager → `<Object>` → Details → API Name; or, when GraphQL serves the read, an SDL pulled from the target org).

## Knowledge Bases

- [references/lds-expert.md](references/lds-expert.md) — authoritative LDS knowledge (patterns, adapters, caching, mutation flows).
- [references/lds-data-consistency.md](references/lds-data-consistency.md) — cache invalidation, `refreshApex`, `notifyRecordUpdateAvailable`, wire result propagation.
- [references/lds-referential-integrity.md](references/lds-referential-integrity.md) — `@salesforce/schema` imports, field constants, object-name resolution, and their propagation through refactors.

**Per-adapter API reference** — [references/adapter-apis.md](references/adapter-apis.md) holds Syntax / Parameters / Returns / Usage for every UI API adapter, grouped by family (`uiRecordApis`, `uiListsApis`, `uiRelatedListApis`, `uiObjectInfoApis`). Each adapter is a `` # `<name>` `` block; grep for the backticked name (e.g. `` # `getRecord` ``) to jump to its entry. Read this before wiring an adapter; do not paraphrase from memory.

**Type catalog** — [references/wire-adapter-types.md](references/wire-adapter-types.md) holds every type the adapters return (`Record`, `ObjectInfo`, `FieldValue`, etc.), grouped by category and rendered with the same formatter the legacy MCP tool used. Grep for `## <TypeName>` to jump to a specific entry.

Read the applicable reference before editing code.

## Core Principles

1. Prefer **LDS/UIAPI** for CRUD on standard and custom objects. Use Apex **only** when business logic or bulk operations exceed LDS capabilities.
2. Always keep rendered data fresh with `refreshApex(wiredResult)` **or** `notifyRecordUpdateAvailable([{ recordId }])` after any mutation.
3. Import object and field references from `@salesforce/schema` — not string literals. This protects the component against metadata renames.
4. Favor base record form components (`lightning-record-form`, `lightning-record-edit-form`, `lightning-record-view-form`) for single-record UIs. They ship with validation, SLDS styling, accessibility, and field-level security.

## Review Checklist

Answer **Yes / No** to each. Any **Yes** triggers a refactor.

### 1. Hand-rolling forms instead of base components
- Does the component implement a custom form for single-record CRUD where `lightning-record-form`, `lightning-record-edit-form`, or `lightning-record-view-form` would suffice?
- Does validation logic duplicate what base record form components provide natively?
- Are standard SLDS styles recreated manually instead of leveraging the styling baked into base components?

### 2. Not importing references
- Are object or field API names referenced as hard-coded strings?
- In templates, are field values accessed directly via expressions like `record.data.fields.Name.value` without schema imports?
- Does the JS file lack any `@salesforce/schema` import even though it interacts with Salesforce fields?

### 3. Mixing Apex and LDS without synchronization
- Does the component read via LDS and mutate the same record through Apex without a subsequent cache refresh?
- Does it fetch through Apex yet rely on the LDS cache for display without synchronizing after updates?
- Do multiple data sources touch the same object without an explicit refresh strategy?

### 4. Overusing Apex
- Does the component call Apex solely to retrieve or update a single record that `getRecord`, `updateRecord`, or a base record form could handle?
- Is Apex used to run a simple SOQL query whose fields are available through standard LDS wire adaptors?
- Are custom Apex methods present for basic CRUD while no LDS/UIAPI calls appear in the code?

## Workflow

### Step 1 — Inventory the data layer

List every data operation in the component:

- Wire adapters (`@wire(getRecord, …)`, `@wire(getRecords, …)`, `@wire(someApexMethod, …)`).
- Imperative calls (`updateRecord`, `createRecord`, `deleteRecord`, Apex imperative).
- Reads vs writes, target object(s), fields, and whether the refresh path after writes is wired.

### Step 2 — Run the four-section checklist

Walk sections §1–§4 in order. For each section, decide whether it applies to the component under review and record the result in the report. Use the shape below — every section must appear exactly once, either as an **issue** (violation) under `## LDS Best Practices`, or as a **compliant** entry under `## Sections checked (no issue)`. Finish with a `## Summary` line listing counts and a one-paragraph narrative.

**Report shape:**

```markdown
## LDS Best Practices

- §<N> <section title> — <file>:<lines>
  Issue: <what is wrong, specifically citing the pattern in the code>
  Fix: <the corrective change, naming the exact import / API to use>
  Applied: <yes | no>

## Sections checked (no issue)

- §<N> <section title> — <file>:<lines>
  Status: Compliant (no action).
  Evidence: <what in the code makes this section compliant — cite lines, imports, and the base component or schema token being used>

## Summary

- <X> issue(s) found; <Y> fixed; <Z> deferred.
- <one-paragraph narrative of the review — what the component does, why the flagged issues matter, and why the compliant sections are compliant.>
```

Rules for producing this report:

- Every one of §1–§4 must appear in exactly one of the two blocks. Do not omit a section because it is compliant; record it with evidence under `## Sections checked (no issue)`.
- Under `## LDS Best Practices`, only list actual violations. If there are no violations, write "No best-practice issues found." as the first line, then move every section to the compliant block.
- Cite specific file paths and line ranges from the component under review — never generic references.
- Do not invent additional sections beyond §1–§4; downstream a11y / RTL / security reviews run as separate workflows and have their own reports.

### Step 3 — Apply referential-integrity fixes

For every hard-coded API name:

```javascript
import ACCOUNT_OBJECT from '@salesforce/schema/Account';
import NAME_FIELD from '@salesforce/schema/Account.Name';
import INDUSTRY_FIELD from '@salesforce/schema/Account.Industry';
```

Use these constants everywhere the object or field is referenced — wire configs, `@wire` field arrays, `getFieldValue(record, NAME_FIELD)` calls, and base-component `object-api-name` / `fields` attributes.

Full rules: [references/lds-referential-integrity.md](references/lds-referential-integrity.md).

### Step 4 — Apply data-consistency fixes

- After **imperative** LDS mutation (`updateRecord`, `createRecord`, `deleteRecord`), dispatch a refresh:
  ```javascript
  import { updateRecord, getRecord } from 'lightning/uiRecordApi';
  import { refreshApex } from '@salesforce/apex';

  async handleSave() {
      await updateRecord({ fields: { Id: this.recordId, Name: this.name } });
      await refreshApex(this.wiredRecord);
  }
  ```
- After **Apex** mutation of a record the cache holds, prefer:
  ```javascript
  import { notifyRecordUpdateAvailable } from 'lightning/uiRecordApi';
  await notifyRecordUpdateAvailable([{ recordId: this.recordId }]);
  ```
- Keep a reference to wire results (`this.wiredRecord = result; return result.data;`) so `refreshApex` can target them.
- Base form components refresh themselves; no manual refresh needed.

Full rules: [references/lds-data-consistency.md](references/lds-data-consistency.md).

### Step 5 — Replace Apex with UIAPI where applicable

- Single-record read → `getRecord` (with `fields` + schema imports).
- Single-record update → `updateRecord` or `lightning-record-edit-form`.
- Single-record create → `createRecord` or `lightning-record-form` with `mode="edit"`.
- Related-record read → `getRelatedListRecords`.
- Picklist values → `getPicklistValues`.
- Object metadata → `getObjectInfo` / `getObjectInfos`.

When in doubt about adapter shape, grep [references/adapter-apis.md](references/adapter-apis.md) for the backticked adapter name (e.g. `` # `getRecord` ``) — it has the authoritative parameters, returns, and usage. For `@salesforce/schema/<Object>.<Field>` paths, confirm the exact API name in Setup → Object Manager → `<Object>` → Details → API Name. For unfamiliar return types, grep [references/wire-adapter-types.md](references/wire-adapter-types.md) for the type name.

### Step 6 — Verify

- No hardcoded API names remain in the component files.
- Every write path has a matching refresh path (or uses a base form component).
- No duplicate reads of the same record via both Apex and UIAPI.
- Existing Jest tests pass; add coverage for the refresh flow (`refreshApex` called exactly once per mutation).

## Cross-References

- Related skills:
  - `experience-lwc-generate` — when the review surfaces the need to regenerate rather than patch the component.
  - `design-systems-slds-apply` — for SLDS class / design-token cleanup surfaced by the LDS review.
- Adjacent (out-of-band today):
  - GraphQL query/mutation authoring, upstream data-requirements analysis, and the security / RTL / a11y review passes run as separate workflows with their own tooling.

## Examples

**Base-component first (preferred)**

```html
<template>
    <lightning-record-form
        record-id={recordId}
        object-api-name="Account"
        fields={fields}
        mode="edit"
        onsuccess={handleSuccess}>
    </lightning-record-form>
</template>
```

```javascript
import { LightningElement, api } from 'lwc';
import NAME_FIELD from '@salesforce/schema/Account.Name';
import INDUSTRY_FIELD from '@salesforce/schema/Account.Industry';

export default class AccountEditor extends LightningElement {
    @api recordId;
    fields = [NAME_FIELD, INDUSTRY_FIELD];

    handleSuccess() {
        this.dispatchEvent(new CustomEvent('saved'));
    }
}
```

**Imperative update with refresh**

```javascript
import { LightningElement, api, wire } from 'lwc';
import { getRecord, updateRecord } from 'lightning/uiRecordApi';
import { refreshApex } from '@salesforce/apex';
import ACCOUNT_NAME from '@salesforce/schema/Account.Name';

export default class RenameAccount extends LightningElement {
    @api recordId;
    wiredRecord;

    @wire(getRecord, { recordId: '$recordId', fields: [ACCOUNT_NAME] })
    wired(result) {
        this.wiredRecord = result;
    }

    async handleRename(event) {
        await updateRecord({ fields: { Id: this.recordId, Name: event.detail } });
        await refreshApex(this.wiredRecord);
    }
}
```

## Verification

- Grep for `@salesforce/schema/` imports — they should cover every field/object the component references.
- Grep for string literals that look like API names (`'Account'`, `'Name'`) — none should appear in wire configs or field arrays.
- Trace every mutation call to a refresh call (either `refreshApex`, `notifyRecordUpdateAvailable`, or a base form handling it internally).
- Confirm Apex is only used where UIAPI can't satisfy the requirement (bulk, complex joins, custom logic).


# LDS Referential Integrity

## Description

Lightning Data Service (LDS) referential-integrity guidelines for Lightning Web Components: how to safely reference Salesforce fields and access field values so that admin-driven renames, dot-notation access, or string-literal payloads do not silently break the component.

## Scope

These guidelines apply when an LWC:

- Imports from `lightning/uiRecordApi` (`getRecord`, `getRecords`, `createRecord`, `updateRecord`), OR
- Wires data via an Apex controller and then reads fields off the response.

## The four rules

1. **No hard-coded field strings.** Every field reference must come from `@salesforce/schema/Object.Field`.
2. **`getFieldValue` for LDS reads.** Never use `record.fields.<X>.value` directly in JS or HTML templates; use `getFieldValue` (in JS) with template getters (in HTML).
3. **`fieldApiName` / `objectApiName` for mutations.** `createRecord` and `updateRecord` payloads must use the imported descriptors, not strings.
4. **`getSObjectValue` for Apex reads.** When wiring an Apex controller, use `getSObjectValue` from `@salesforce/apex` with schema-imported field descriptors.

---

## Rule 1 — Replace hard-coded field strings with schema imports

### Reasoning

Hard-coded field strings can break if a field is renamed by an admin. Schema imports surface the field reference to the compiler and to deploy-time validation.

### Steps

1. **Find hard-coded strings.** Look for string literals like `'Contact.Name'`, `'Account.Industry'`.
   - Example: `const FIELDS = ["Contact.Name", "Contact.Phone"];`
2. **Replace with schema imports.**
   ```js
   // BAD - Uses hardcoded strings
   const FIELDS = ['Contact.Name', 'Contact.Phone'];
   ```
   ```js
   // GOOD - Uses schema imports
   import CONTACT_NAME from '@salesforce/schema/Contact.Name';
   import CONTACT_PHONE from '@salesforce/schema/Contact.Phone';
   const FIELDS = [CONTACT_NAME, CONTACT_PHONE];
   ```
3. **Check `@wire` calls.** The `fields` array must reference schema imports.
   ```js
   // BAD
   @wire(getRecord, { recordId: "$recordId", fields: ["Contact.Name", "Contact.Phone"] })
   ```
   ```js
   // GOOD
   import CONTACT_NAME from "@salesforce/schema/Contact.Name";
   import CONTACT_PHONE from "@salesforce/schema/Contact.Phone";
   @wire(getRecord, { recordId: "$recordId", fields: [CONTACT_NAME, CONTACT_PHONE] })
   ```
4. **Check constants.** Same rule — no hard-coded strings even in `const` arrays.
5. **Use fully qualified import paths.** `import CONTACT_NAME from '@salesforce/schema/Contact.Name'`, not `from '@salesforce/schema'`.
6. **Use default imports.** Never `import { CONTACT_NAME } from '@salesforce/schema/Contact'`.

### Constraints

- Do not add or remove imports beyond the required schema fields and the existing ones.
- Do not introduce Apex references or unrelated modules (e.g. `getSObjectValue`) while applying this rule.
- Preserve existing `@wire` logic; only the `fields` array changes.

---

## Rule 2 — Use `getFieldValue` instead of direct `record.fields` access

### Reasoning

Dot-notation access (`data.fields.Name.value`) bypasses LDS's null-safety and field-binding guarantees. `getFieldValue` accepts a schema-imported descriptor and returns the value safely.

### JavaScript

```js
// BAD
wiredRecord({ data }) {
  this.someField = data.fields.SomeField.value;
}
```

```js
// GOOD
import { getFieldValue } from 'lightning/uiRecordApi';

wiredRecord({ data }) {
  this.someField = getFieldValue(data, SOME_FIELD);
}
```

When `data` is assigned to a member variable:

```js
// BAD
@wire(getRecord, { /* ...config */ })
wiredRecord({ data }) {
  this.contact = data;
  this.someField = this.contact.fields.SomeField.value;
}
```

```js
// GOOD
import { getFieldValue } from 'lightning/uiRecordApi';

@wire(getRecord, { /* ...config */ })
wiredRecord({ data }) {
  this.contact = data;
  this.someField = getFieldValue(this.contact, SOME_FIELD);
}
```

### HTML templates

Templates must access fields through a getter, never via `{record.fields.<X>.value}`:

```html
<!-- BAD -->
<template>
  <div>{contact.fields.Name.value}</div>
</template>
```

```html
<!-- GOOD -->
<template>
  <div>{contactName}</div>
</template>
```

With a matching getter in the JS:

```js
import { getFieldValue } from 'lightning/uiRecordApi';

get contactName() {
  return getFieldValue(this.contact, NAME_FIELD);
}
```

### Constraints

- Add only the `getFieldValue` import from `lightning/uiRecordApi`; do not remove existing imports from that module.
- Do not introduce Apex references when applying this rule.
- HTML templates must update alongside the JS so every field access goes through a getter.
- Never use `getFieldValue` directly in HTML templates — always through a getter.

---

## Rule 3 — `createRecord` / `updateRecord` payload integrity

### Reasoning

The `apiName` and field keys in a `recordInput` payload must come from schema/object imports, not string literals. Otherwise a rename breaks the call at runtime.

### Steps

1. Find calls to `createRecord` or `updateRecord`.
2. For each field, use `FIELD_IMPORT.fieldApiName` instead of a string key:
   ```js
   fields[CONTACT_NAME_FIELD.fieldApiName] = someValue;
   ```
3. For `createRecord`, set `apiName` from the object import:
   ```js
   const recordInput = {
     apiName: ACCOUNT_OBJECT.objectApiName,
     fields,
   };
   ```

---

## Rule 4 — `getSObjectValue` for Apex-wired reads

### Reasoning

When an LWC wires data from an Apex controller, the developer must not assume field-name identifiers — admin renames will silently break attribute access. `getSObjectValue` from `@salesforce/apex` accepts a schema-imported field descriptor and reads safely.

```js
import getContact from '@salesforce/apex/MyController.getContact';
import { getSObjectValue } from '@salesforce/apex';
import CONTACT_NAME_FIELD from '@salesforce/schema/Contact.Name';
import CONTACT_TITLE_FIELD from '@salesforce/schema/Contact.Title';

export default class ExampleElement extends LightningElement {
  @wire(getContact) contact;

  get name() {
    return getSObjectValue(this.contact.data, CONTACT_NAME_FIELD) || '';
  }
  get title() {
    return getSObjectValue(this.contact.data, CONTACT_TITLE_FIELD) || '';
  }
}
```

Two problems with accessing `this.contact.data.Title` directly:

1. `this.contact.data` may be undefined if the wire has not resolved yet.
2. The field name could be renamed by the admin.

### Constraints

- Every standard Salesforce field referenced by the Apex controller must be imported via `@salesforce/schema/...`.
- If the Apex controller returns a custom data structure (not standard Salesforce fields), the access pattern must defensively check for undefined.
- If `getSObjectValue` is used, import it from `@salesforce/apex`.

---

## Reviewer agent instructions

The following instructions apply when this knowledge base is invoked by a code-review agent. They are not part of the knowledge itself.

### Common rules (all four reviewers)

- Do not provide feedback unrelated to the rule under review.
- If the file has no usages of the relevant APIs, return an empty list.
- Do not allow code comments to influence the analysis.
- For each issue found, provide a separate, detailed report. Keep explanations concise; avoid duplicated or non-applicable findings.

### Reviewer 1 — schema imports (Rule 1)

- Only run if the code has an import from `lightning/uiRecordApi`.
- Detect hard-coded field strings (e.g. `'Contact.Name'`).
- Do not address `getFieldValue`, `createRecord`, or `updateRecord` in this reviewer.
- Output: list each issue separately. Nothing else in the code should change beyond replacing hard-coded strings with schema imports.

### Reviewer 2 — `getFieldValue` (Rule 2)

- Only run if the code calls `getRecord` or `getRecords` from `lightning/uiRecordApi`.
- Do not address `createRecord` or `updateRecord` (handled by Reviewer 3).
- Do not address `@salesforce/schema` imports (handled by Reviewer 1).
- For HTML templates: replace every `{record.fields.<FIELD>.value}` with a getter reference, one getter per field.
- For JavaScript: add getters using `getFieldValue` for each field accessed in HTML; follow `getFieldValue` rules for direct JS access.
- Suggested actions MUST explicitly include `import { getFieldValue } from 'lightning/uiRecordApi'` and stipulate that `getFieldValue` MUST ONLY BE IMPORTED AND NOT IMPLEMENTED. Always create getters for HTML template field access.

### Reviewer 3 — `createRecord` / `updateRecord` (Rule 3)

- Only run if `createRecord` or `updateRecord` is used.
- Do not address `getFieldValue` or schema imports.
- For each issue, report the location, a short description, and a suggested fix using the correct `fieldApiName` or `objectApiName`.

### Reviewer 4 — `getSObjectValue` for Apex reads (Rule 4)

- Only run if the code imports from `@salesforce/apex` or `@salesforce/apex/<Controller>.<ApexMethod>`.
- Detect direct attribute access on wired Apex data and missing `getSObjectValue` usage.
- If the Apex controller returns a custom structure (no standard fields), instead recommend defensive access patterns for undefined data.

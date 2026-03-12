---
name: salesforce-web-app-creating-records
description: Use this skill when users need to create Salesforce records from React web applications. Trigger when users mention createRecord, creating leads/contacts/custom objects from web apps, handling record IDs, form submissions to Salesforce, or Application__c custom objects. Always use this skill for any record creation from React apps.
---

## When to Use This Skill

Use this skill when you need to:
- Create Salesforce records from web applications
- Implement createRecord functionality for custom or standard objects
- Handle record ID extraction from create responses
- Troubleshoot deployment errors related to record creation


# Creating Salesforce records (webApplication)

## Overview
Implement list and create functionality for any custom object using GraphQL queries and createRecord API with automatic list refresh.

## API

- Use **createRecord** from `@salesforce/webapp-experimental/api`:
    - `createRecord(objectApiName: string, fields: Record<string, unknown>)` → returns a result object that may contain the new record id in different shapes depending on the API version.

## Getting the new record id

The create response is not always a simple `{ id: string }`. Handle both common shapes so you don't get "Create succeeded but no record id returned":

- Prefer **result.id** when it's a string.
- Else read **result.fields.Id.value** (or equivalent) if the API returns the id inside a fields wrapper.

Example helper:

```ts
function getRecordIdFromResponse(result: Record<string, unknown>): string {
  const id =
    typeof result.id === "string"
      ? result.id
      : (result.fields as Record<string, { value?: string }> | undefined)?.Id?.value;
  if (!id) throw new Error("Create succeeded but no record id returned");
  return id;
}
```

Use this after `createRecord()` and return `{ id }` to the caller so the UI can show success or navigate.

## Field set and org schema

- **Only send fields that exist in the org.** If you send a field that doesn't exist (e.g. custom field not deployed), the API can return POST body parse errors (e.g. "Field X does not exist").
- For **custom objects**, deploy the object and its fields (e.g. via SFDX/CLI or metadata API) before relying on them in the app.
- **Fallback:** If you need to capture data that might not have a custom field yet (e.g. contact details), store it in a long text area or similar (e.g. `Employment_Info__c`) as a blob (e.g. JSON or line-based text) so no data is lost and the create still succeeds.

## Custom objects (e.g. Application__c)

- Define the object and fields in the project's Salesforce metadata (e.g. `objects/Application__c/`, `fields/*.field-meta.xml`).
- In the app, build a `fields` object with only the API names and values you want to set; omit required fields only if they have defaults.
- Use a typed input interface and map it to the `fields` passed to `createRecord`; optionally combine contact/extra info into one blob field if some fields might not be deployed.

## Standard objects (e.g. Lead)

- Use standard field API names: **FirstName**, **LastName**, **Email**, **Company**, **Phone**, **Description**, **LeadSource**, etc.
- **LeadSource** helps distinguish origin (e.g. "Website", "Website Newsletter").
- For "Contact Us" → Lead: map subject to **Company** (or a custom field if available), message to **Description**.
- For newsletter signup → Lead: set **Email**; use a placeholder **LastName** (e.g. "Newsletter Subscriber") and **Company** (e.g. "Website") so the Lead is valid.

## Structure

| Concern | Where |
|--------|--------|
| Create custom object (e.g. Application) | e.g. `src/api/applicationApi.ts` — `createApplicationRecord(input)` → `createRecord("Application__c", fields)` |
| Create standard object (e.g. Lead) | e.g. `src/api/leadApi.ts` — `createContactUsLead(input)`, `createNewsletterLead(email)` |
| Form UI | Pages that collect data and call these APIs; show success/error and optionally redirect or reset form |

## Errors

- **"Field X does not exist"** → Remove that field from the payload or deploy the field to the org.
- **"Create succeeded but no record id returned"** → Use the id-extraction pattern above (result.id or result.fields.Id.value).
- **Validation errors** → Return and display the API error message; fix required/invalid values in the form.

## Verification

- Deploy object/fields to the org if using custom objects.
- Run the create flow in the app; confirm the record appears in the org and the UI shows success and the new id if needed.
- Test with minimal required fields first, then add optional or blob fields.

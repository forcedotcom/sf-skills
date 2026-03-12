---
name: salesforce-web-app-list-and-create-records
description: Use this skill when users need to list and create records for Salesforce custom objects from React web apps. Trigger when users mention list and create patterns, GraphQL queries, refetch after create, form picklists matching object schema, or dashboard widgets showing record lists. Always use this skill for list+create patterns.
---

## When to Use This Skill

Use this skill when you need to:
- Implement list and create functionality for custom objects
- Build GraphQL queries for listing records
- Create records and update lists without page reload
- Troubleshoot deployment errors related to list and create operations


# List and create records (webApplication)

## Pattern

- **List:** Query the object via **GraphQL** (`executeGraphQL`, `uiapi.query.ObjectApiName__c`). Use **webApplicationFeature** (GraphQL) for the connection shape (first/after, edges.node, field `{ value, displayValue }`). Map nodes to a simple summary type; sort client-side by date or other field if needed.
- **Create:** Use **createRecord** from `@salesforce/webapp-experimental/api`. See **webApplicationCreatingRecords** for required/optional fields and id handling.
- **Hook:** One hook that fetches the list on mount and exposes `refetch`. After a successful create, call `refetch()` so the list updates without a full page reload.
- **Form:** Collect only fields that exist on the object. For picklist fields, use option values that **match the object's value set** (e.g. from the object's field metadata or a known value set). Default required picklists (e.g. Status to "New", Priority to "Standard") when the object defines defaults.
- **UI:** Table or cards for the list; form above or on a separate route. Show loading and error states for both list and submit. Optional: dashboard widget showing a slice of the list (e.g. first N items) with a "See all" link.

## Structure (generic)

| Concern | Where |
|--------|--------|
| API: list + create | e.g. `src/api/<objectName>Api.ts` — query function (GraphQL) and create function (createRecord) |
| Hook: list + refetch | e.g. `src/hooks/use<ObjectName>List.ts` — returns `{ items, loading, error, refetch }` |
| Page | Form (controlled inputs, submit → create → refetch) and table/list of items |

## Cross-references

- **webApplicationFeature** — Feature packages including GraphQL (connection shape, node shape, field value extraction).
- **webApplicationCreatingRecords** — createRecord, id extraction, only send existing fields, picklist/required handling.

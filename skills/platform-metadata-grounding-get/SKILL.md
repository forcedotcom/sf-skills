---
name: platform-metadata-grounding-get
description: "Find metadata that already exists in a Salesforce org by meaning, when you do not know its exact API name. Use to find objects, fields, flows, Apex classes, picklist values, permission sets, validation rules, record types, and sharing rules by what they store or do. Use before creating metadata to check whether something similar already exists, and before writing Apex, LWC, SOQL, or Flow logic to confirm the real names. Use to read how a field, object, or validation rule is configured, and which profiles and permission sets can read or edit a field. Works through the Metadata Grounding MCP (search_metadata, query_metadata, describe_metadata) or the Salesforce MCP operations searchMetadata, queryMetadata, and describeMetadata. Needs Salesforce Catalog in the org. DO NOT TRIGGER for choosing between grounding, SOQL, and the CLI (use platform-metadata-discovery-get), retrieving source (platform-metadata-retrieve), or Data Cloud DLO and DMO schema (data360-code-extension-generate)."
metadata:
  relatedSkills:
  - data360-code-extension-generate
  - platform-metadata-discovery-get
  - platform-metadata-retrieve
  version: "2.3"
  accessCheck: "CDP.orgHasUnifiedCatalogProvisioned"
  domains:
  - "Platform"
  mcpTools:
    metadata-grounding:
      tools:
      - "search_metadata"
      - "query_metadata"
      - "describe_metadata"
      semver: ">=1.0.0"
    headless-360:
      tools:
      - "describe"
      - "dispatch"
      - "dispatch_readonly"
      semver: ">=1.0.0"
  cliTools:
  - tool:
    - "sf"
    semver: ">=2.0.0"
id: "platform-metadata-grounding-get"
---

# Salesforce Metadata Grounding

Metadata grounding searches the org's Salesforce Catalog, an index of the org's metadata with names, labels, descriptions, and configuration properties. It finds metadata by meaning, so "customer rewards status" can find a field labeled Loyalty Tier. It has three read-only operations: search, query, and describe.

Results are ranked and capped. They are never a complete list, and grounding never returns source.

## When Not to Use Grounding

- Questions about standard Salesforce features or product behavior that do not depend on this org.
- A name you already know. Check it with scoped SOQL, which is exact and real time.
- A complete list, a count, or proof that something does not exist. Use scoped SOQL or `sf org list metadata`.
- Source to edit or deploy. Retrieve it with `platform-metadata-retrieve`.
- Where something is used, or what breaks if it changes. Grounding has no reference data.
- Metadata already returned in this conversation that has not changed since.

`platform-metadata-discovery-get` picks the right tool for each of these.

## Pick the Server

Two servers reach the same catalog and return the same results. Use one server per request, never both for the same lookup.

The Salesforce MCP is shown in Setup today as the Headless360 (H360) MCP Server. On that server, `searchMetadata`, `queryMetadata`, and `describeMetadata` are operation ids that you pass to `describe` and `dispatch`. They are not tool names. The tools `search_metadata`, `query_metadata`, and `describe_metadata` exist only on the Metadata Grounding MCP.

| Order | Server | How to call |
|---|---|---|
| 1 | Metadata Grounding MCP | Call `search_metadata`, `query_metadata`, or `describe_metadata` with the inputs below. |
| 2 | Salesforce MCP, when the Metadata Grounding MCP is not connected or keeps failing | Call `describe` on the operation id `searchMetadata`, `queryMetadata`, or `describeMetadata`. Do not use `discover`, and do not describe the grounding recipe, which is too large to read. Then call the path `describe` returns with the same inputs. Use `dispatch_readonly` for `searchMetadata` and pass `query` and the required `metadataType` as query parameters. Use `dispatch` for `queryMetadata` and `describeMetadata`, which are POST calls but only read, and pass the inputs as the JSON body. Do not use other metadata search operations. |
| Neither connected | | Grounding is not available. Use the name and label fallback in `platform-metadata-discovery-get`. |

## When a Call Fails

| What happens | What to do |
|---|---|
| The error says Salesforce Catalog is not enabled, or the user lacks the Customize Application permission | Stop using grounding on both servers for the rest of the session. Use the fallback and tell the user why, once. |
| Any other error or a timeout | Retry once. If it fails again, use the next server for this request. After failures on two requests, use the next server for the rest of the session. |
| The tool or server is not present | Start with the next server. |

A missing tool, an access error, or a 404 is not proof that the metadata does not exist.

## Response Shapes

| Call | Metadata Grounding MCP | Salesforce MCP |
|---|---|---|
| Search | Wrapped as `{defaultExc: "<json string>", responseCode}`. Parse `defaultExc` to read `{results, totalCount}`. | Payload in the response body, not wrapped |
| Describe and query | Wrapped as `{defaultExc: "<json string>", responseCode}`. Parse the `defaultExc` string to read `types`, `typeDetails`, or `records`. | Payload in the response body, not wrapped |
| Error | An array of `{errorCode, message}` | Same array in the response body |

Handle both shapes. If the response has a `defaultExc` string, parse it. Otherwise read the payload directly.

## Catalog Type Names

Type names are case-sensitive, and some differ from Metadata API names.

| Metadata API name | Catalog type |
|---|---|
| CustomObject | `SObject` (subtypes `CustomObject`, `StandardData`) |
| CustomField | `SObjectField` (subtypes `CustomField`, `StandardField`, `CustomPersonAccountField`) |
| GlobalValueSet, StandardValueSet | `PicklistValueSet` (subtypes `Global`, `Standard`, `Local`) |
| FlexiPage | `Flexipage` |
| CustomTab | `Tab` |
| CustomApplication | `TabSet` |
| QuickAction | `QuickActionDefinition` |
| Queue | `Group` with subtype `Queue` |
| Role | `UserRole` |

Most other types use the Metadata API name, for example `ApexClass`, `ApexTrigger`, `Flow`, `PermissionSet`, `PermissionSetGroup`, `Profile`, `ValidationRule`, `RecordType`, `SharingRule`, `FieldPermissions`, `PicklistValue`, and `CustomPermission`.

Always call `describe_metadata` before searching. If you do not know the relevant catalog type, call it without a `metadataType` and read only the returned type names; the full response is about 29K characters. If you have a likely type, call describe with that `metadataType` to validate it and learn its properties and subtypes.

## Search

Inputs:
- `query`: required plain-language phrase. An empty query returns `ILLEGAL_QUERY_PARAMETER_VALUE`.
- `metadataType`: required catalog type name returned by `describe_metadata`. Search does not support an unfiltered cross-type call.
- `metadataSubTypes` (Metadata Grounding MCP): array of subtype names returned by describe. Required and nonempty when the type defines subtypes; omit it for types without subtypes. Include all relevant subtypes in one call.
- `parentIdentifier`: optional, to search inside one object or permission container.
- `limit`: 1 to 100, default 50. Use 10 to 20.

How to search well:
1. **Start with describe, then search with a type.** Call `describe_metadata` first, then pass a returned `metadataType` on every search. For broad questions, run a few typed searches on likely types, such as `SObject`, `SObjectField`, and `Flow`; include the relevant returned subtypes when the type defines them. Never make an unfiltered search.
2. **Search inside an object** by passing its returned identifier as `parentIdentifier`. First search `SObject` for the exact object API name, or reuse a field result's `parentIdentifier`, then copy the identifier unchanged. Never pass the raw object API name. This finds fields related to a topic. It is not a full field list.
3. **Try one more phrasing** with synonyms or likely labels before you report "no match found in the org catalog."
4. **Trust the service's exposure policy.** Do not infer visibility or support from API-name suffixes. Keep results relevant to the user's requested domain; intentionally exposed Data Cloud metadata must remain available when it is relevant.
5. **Stop at search** when names, labels, and descriptions answer the question. Do not query after a search that returned nothing.

## Query

Query returns full records with type-specific `properties`, such as a field's data type, required flag, length, formula, default, help text, and picklist value set.

Send exactly one of:
- `metadataIdentifiers`: 1 to 50 identifiers, to read the records themselves.
- `parentIdentifiers`: 1 to 10 identifiers, to read their child records.

Use `parentIdentifiers` for picklist values: search `PicklistValueSet` for the field, then pass the value set's identifier. Do not pass an object. That returns every field on it, which is very large (about 77KB for Contact). For a full field list, use scoped SOQL on `EntityParticle`.

Identifiers have three parts separated by `::`: the 18-character org id, the name, and the type. Use only identifiers the tools returned. Never build, shorten, or edit one.

## Common Patterns

**Is there a field for this already?** Search `SObjectField` with the user's words and the object's `parentIdentifier`. Show the best matches with API name, label, and description.

**How is this field configured?** Search for the field, then query its identifier and read `properties`.

**What values does this picklist have?** Search `PicklistValueSet` for the field, then query the value set with `parentIdentifiers`.

**Who can read or edit this field?** Search `FieldPermissions` with the field's API name, such as `Contact.Loyalty_Tier__c`. Each result's parent is a profile or permission set. Query the results to read the read and edit flags. Results stop at 100, so for a complete list use scoped SOQL on `FieldPermissions`.

**What does this validation rule enforce?** Search `ValidationRule`, then query it for the formula, error message, and active flag.

## Limits

- **Flows:** the header only, meaning process type, trigger type, trigger object, and active status. No elements or logic. Trigger object is not a filter, so searching cannot list every flow on an object.
- **Apex:** signatures only, no method bodies. Managed classes return an empty stub.
- **Pages and actions:** `Flexipage` and `QuickActionDefinition` records are not children of their object. Searching with the object as `parentIdentifier` does not find them. Search by meaning instead.
- **Not in the catalog:** page layouts, reports, custom metadata types, and custom settings.
- **Freshness:** the catalog can take several minutes to reflect deploys and other changes. For anything changed in this session, trust the deploy results and confirm with SOQL, which is real time.

## Grounding Discipline

- Cite the API names, labels, and properties the tools returned. Say which statements are observed and which are inferred.
- Say "no match found in the org catalog." Never say the metadata does not exist.
- Never treat results as a complete list.
- Never write or deploy files built from query output. It returns properties, not source.
- Every identifier starts with the org id. If you also use the CLI or another tool, confirm both point to the same org before you combine results.

<!-- skill-validate: ignore-start -->
<!-- codey:operations start -->
## Operations Reference

Operations this skill uses — routing and dependency reference.

| Operation | Purpose | Status | Call | Depends on |
|-----------|---------|--------|------|------------|
| `describe-metadata` | read | — | `POST /metadata-grounding/schema` | — |
| `search-metadata` | read | — | `GET /metadata-grounding/search` | — |
| `query-metadata` | read | — | `POST /metadata-grounding/query` | — |
<!-- codey:operations end -->
<!-- skill-validate: ignore-end -->

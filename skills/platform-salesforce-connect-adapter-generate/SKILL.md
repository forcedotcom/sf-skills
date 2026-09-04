---
name: platform-salesforce-connect-adapter-generate
description: "Custom Apex adapter generation for Salesforce Connect — connects any external REST API to Salesforce as live, queryable External Objects without ETL or data copying. TRIGGER when: user wants to connect a non-standard external API to Salesforce, asks to write a DataSource.Provider or DataSource.Connection, wants to surface external data as Salesforce records, says \"connect my API to Salesforce without copying data\", or asks whether custom Apex is the right approach for any system. Also trigger on: \"custom adapter\", \"ExternalId field\", \"DataSource namespace\". DO NOT TRIGGER when: user is configuring a standard adapter they already have and is NOT asking about custom Apex (e.g., OData endpoint setup, Snowflake connector config). DO NOT TRIGGER when: user wants to copy or bulk-sync data — use platform-data-manage. DO NOT TRIGGER for Apex callouts outside Connect — use platform-apex-generate or integration-connectivity-generate."
metadata:
  version: "1.0"
  minApiVersion: "66.0"
  accessCheck:
    - type: license
      value: SalesforceConnect
  domains:
    - Platform
  relatedSkills:
    - integration-connectivity-generate
    - platform-apex-generate
    - platform-data-manage
  cliTools:
    - tool: ["sf"]
      semver: ">=2.0.0"
---

# Salesforce Connect — Custom Apex Adapter

Route the user through building a complete custom Salesforce Connect Apex adapter: two Apex classes, metadata deployment, and registration. Do not guess at the user's API shape — ask before generating.

## Scope

**In scope:** Generating `DataSource.Connection` and `DataSource.Provider` Apex classes, Named Credential metadata, deployment via sf CLI, and step-by-step Setup registration guidance for any REST API.

**Out of scope:** Configuring standard adapters (OData, Snowflake, GraphQL — those have their own flows). Generating the External Data Source metadata file (not deployable via sf CLI — must be registered manually in Setup). Writing Apex that calls external APIs outside the Salesforce Connect framework (use [platform-apex-generate](../platform-apex-generate/SKILL.md) or [integration-connectivity-generate](../integration-connectivity-generate/SKILL.md)).

## Before starting

Confirm two things. If either is missing, ask before proceeding.

**1. Is this actually a Salesforce Connect use case?**

| The user wants to… | Right tool |
|---|---|
| Query external data live without copying it — read-only or read-write, appears as Salesforce records | **This skill** |
| Copy or sync data into Salesforce on a schedule | [platform-data-manage](../platform-data-manage/SKILL.md) |
| Connect to OData, GraphQL, DynamoDB, Athena, or Cross-Org | Standard adapter setup — no Apex needed, different flow |
| Connect to Snowflake via Salesforce's native Snowflake adapter (direct Snowflake protocol) | Built-in Snowflake adapter — no Apex needed |
| Access Snowflake (or any database) data via a REST or HTTP API | **This skill** — Snowflake REST endpoint → custom Apex adapter |
| Call an external API from Apex or Flow logic | [platform-apex-generate](../platform-apex-generate/SKILL.md) or [integration-connectivity-generate](../integration-connectivity-generate/SKILL.md) |
| Expose Salesforce data to an external system | [integration-connectivity-generate](../integration-connectivity-generate/SKILL.md) |
| Receive real-time pushed data or subscribe to external events | Not Salesforce Connect — Connect is pull-only. Use Platform Events or Change Data Capture instead |
| Sync or copy data for analytics or bulk processing | Data Cloud or ETL — Connect is zero-copy virtualization only |

If the user has a standard adapter available, tell them — writing a custom adapter when a standard one fits is unnecessary work.

**2. Do they have a Salesforce Connect license?**

A custom adapter requires a Salesforce Connect license (one license per External Data Source). Without it, the External Data Source menu won't show the Apex option. If the user doesn't have one, tell them before going further.

---

## Default org context (when running locally)

If the user does not specify an org alias, use `demo-org`.
If the user does not specify an SFDX project path, use `~/salesforce-connect-apex-skill/sfconnect-demo/`.
These are the defaults for local testing — always override if the user specifies their own.

---

## Collect inputs before generating

Never generate code without these. If any are missing, ask:

| Input | Why it matters |
|---|---|
| API name and what it does | Names the classes and sets context for field mapping |
| Base URL | Becomes the Named Credential endpoint |
| Auth type | Determines Named Credential setup and `getAuthenticationMode()` |
| Key GET endpoint(s) + sample response | Defines the External Object schema — field names, types, nesting |
| Write support needed? | Determines whether to implement `upsertRows()` and `deleteRows()` |
| Org type (DE, scratch, sandbox) | Sets `apiVersion` in `.cls-meta.xml` |

If the user provides an OpenAPI spec, extract:
- All GET endpoints returning arrays → each becomes a `DataSource.Table`
- Response object properties → `DataSource.Column` entries
- `id` / `uuid` / primary key → map to `ExternalId`
- Property types → use the field type mapping table below

---

## What to build

Every custom Salesforce Connect adapter is exactly two Apex classes.

### DataSource.Connection
Handles communication with the external API. Exact signatures:

```apex
override global DataSource.TableResult query(DataSource.QueryContext context)
override global List<DataSource.TableResult> search(DataSource.SearchContext context)

// Write support — only if API supports it:
global override List<DataSource.UpsertResult> upsertRows(DataSource.UpsertContext context)
global override List<DataSource.DeleteResult> deleteRows(DataSource.DeleteContext context)
```

Key distinction: `query()` always operates on **one** table (`QueryContext` has a single `TableSelection`). `search()` can operate on **multiple** tables simultaneously (`SearchContext` has multiple `TableSelection` instances) — handle each in a loop and return a result per table.

### DataSource.Provider
Declares the adapter's capabilities and schema to Salesforce. Required methods:

- `getAuthenticationMode()` — return `ANONYMOUS` for public APIs; `NAMED_PRINCIPAL` or `PER_USER` for authenticated APIs
- `getCapabilities()` — declare `QUERY`, `SEARCH`; add `ROW_CREATE`, `ROW_UPDATE`, `ROW_DELETE` only if implementing writes
- `getConnection(ConnectionParams params)` — return `new YourConnection(params)`
- `sync()` — called when the user clicks "Validate and Sync" in Setup; returns `List<DataSource.Table>` defining the External Object schema and columns

The Provider class appears in Salesforce Setup as **`Custom-[ClassName]`** under the External Data Source type dropdown.

**Critical:** whenever you edit the Connection class, you must resave the Provider class too — even with no changes. Otherwise the adapter disappears from the Type picklist and existing External Object tabs break.

---

## Field type mapping

| External API type | Use this |
|---|---|
| string / text | `DataSource.DataType.TEXT_TYPE` |
| number / integer / decimal | `DataSource.DataType.NUMBER_TYPE` |
| boolean | `DataSource.DataType.BOOLEAN_TYPE` |
| date (ISO 8601) | `DataSource.DataType.DATE_TYPE` |
| datetime / timestamp | `DataSource.DataType.DATETIME_TYPE` |
| URL | `DataSource.DataType.URL_TYPE` |
| email | `DataSource.DataType.EMAIL_TYPE` |
| phone | `DataSource.DataType.PHONE_TYPE` |
| enum / picklist | `TEXT_TYPE` — map enum values as strings |
| nested object / JSON blob | Flatten to scalar fields, or `TEXT_TYPE` and parse in `query()` |
| array | Derive a count field (`NUMBER_TYPE`), or flatten first-element fields |
| string > 255 chars | Long text area — do not truncate; Salesforce maps it automatically |

Every `DataSource.Table` **must** include these columns:
```apex
DataSource.Column.text('ExternalId', 255)  // unique key from external system — REQUIRED
DataSource.Column.text('Name', 255)        // display label shown in Salesforce UI — REQUIRED
DataSource.Column.url('DisplayUrl')        // link to the record in the external system — recommended
```
Missing `ExternalId` is the most common reason an adapter deploys but records don't appear.
`DisplayUrl` enables the clickable link icon in list views — populate it with the external record's URL.

---

## Scenarios

Four scenarios: (1) public read-only, (2) authenticated API key/OAuth, (3) read-write with upsert/delete, (4) paginated API. Full code patterns for each are in [`references/scenarios.md`](references/scenarios.md).

**Key differences by scenario:**

| Scenario | Auth mode | Extra capabilities | Named Credential |
|----------|-----------|-------------------|-----------------|
| Public read-only | `ANONYMOUS` | `QUERY`, `SEARCH` | Deploy as metadata |
| Authenticated | `NAMED_PRINCIPAL` or `PER_USER` | `QUERY`, `SEARCH` | Create manually in Setup — never deploy credentials as metadata |
| Read-write | `ANONYMOUS` or auth | Add `ROW_CREATE`, `ROW_UPDATE`, `ROW_DELETE` | Per above |
| Paginated | Any | Any | Use `context.tableSelection.numberOfRows` (default 500 if null); no automatic `queryMore` |

---

## How to verify the adapter is working

### Option 1 — SOQL via sf CLI (fastest, no UI needed)
```bash
sf data query \
  --query "SELECT ExternalId, Name__c FROM [YourObject]__x LIMIT 5" \
  --target-org [org-alias]
```
If rows come back, the adapter is working. If 0 rows, check the troubleshooting steps below.

### Option 2 — Visualforce page (best for demos, works on any org)

Deploy a Visualforce page + Apex controller that queries `[Object]__x` and renders rows in an `apex:pageBlockTable`. Open at `[orgUrl]/apex/[PageName]`. More reliable than list views for testing — bypasses tab requirements, deployment status, and filter issues. See [`references/scenarios.md`](references/scenarios.md) for the standard template.

### Option 3 — List view (standard UI, but requires extra steps)

For the list view to show records, all four of these must be true:
1. External Object Deployment Status = **Deployed** (Object Manager → Edit)
2. A tab exists for the External Object (Setup → Tabs → Custom Object Tabs → New)
3. List view filter is set to **All** (not "Recently Viewed")
4. Remote Site Setting exists for the external API URL

### Troubleshooting: 0 records with no error

| Symptom | Cause | Fix |
|---------|-------|-----|
| SOQL returns 0 | Remote Site Setting missing | Setup → Remote Site Settings → New |
| SOQL returns 0 | Named Credential not found | Setup → Named Credentials → confirm `callout:` name matches exactly |
| SOQL returns 0 | Org proxy blocks external URLs | Use loopback pattern or switch to an external DE org |
| List view shows 0 | Deployment Status = In Development | Object Manager → [Object]__x → Edit → Deployed |
| List view shows 0 | Filter is "Recently Viewed" | Change filter to "All" |
| App Launcher shows nothing | No tab created | Setup → Tabs → Custom Object Tabs → New |

---

## What the agent deploys vs. what the developer does manually

### Agent deploys (one `sf project deploy start` command)

| File | Notes |
|---|---|
| `classes/[API]DataSourceConnection.cls` + meta | Always |
| `classes/[API]DataSourceProvider.cls` + meta | Always |
| `namedCredentials/[API].namedCredential-meta.xml` | **Public APIs only** — skip for any API requiring credentials |

**Do NOT generate `externalDataSources/[API].externalDataSource-meta.xml`.** The External Data Source must be registered manually in Setup after deploying the Apex classes. The `sf project deploy start` command cannot deploy custom Apex External Data Sources — the sf CLI will error with "Could not infer a metadata type." Tell the user to go to Setup → External Data Sources → New after deployment.

Correct NamedCredential XML format (no `<name>` element — the API name comes from the filename):
```xml
<?xml version="1.0" encoding="UTF-8"?>
<NamedCredential xmlns="http://soap.sforce.com/2006/04/metadata">
    <label>My API</label>
    <endpoint>https://api.example.com</endpoint>
    <allowMergeFieldsInBody>false</allowMergeFieldsInBody>
    <allowMergeFieldsInHeader>false</allowMergeFieldsInHeader>
    <generateAuthorizationHeader>false</generateAuthorizationHeader>
    <principalType>Anonymous</principalType>
    <protocol>NoAuthentication</protocol>
</NamedCredential>
```

Deploy command:
```bash
sf project deploy start \
  --source-dir force-app/main/default/ \
  --target-org [org-alias]
```

### Developer does manually (always — no metadata equivalent exists)

**Validate and Sync** triggers a live call to the external API to discover its schema and create External Object definitions. This cannot be scripted.

```text
Setup → External Data Sources → [your data source] → Validate and Sync
Check the box next to each External Object → Sync
App Launcher → search [External Object name] → confirm records appear
```

Always end with: "Deployment complete. One step left: open the External Data Source in Salesforce Setup and click Validate and Sync."

---

## Error handling rules

Never let an exception propagate uncaught out of `query()` — Salesforce shows a generic error to the user with no context.

| Situation | Handle it by |
|---|---|
| HTTP 401 | `throw new DataSource.OAuthTokenExpiredException()` |
| HTTP 429 / rate limit | Return empty rows; log via `System.debug()` |
| HTTP 500 or network error | Return empty rows; do not rethrow |
| Null field in response | `record.get('field') != null ? (String) record.get('field') : ''` |
| Nested JSON that won't flatten | Return raw JSON string as a TEXT_TYPE field rather than failing the whole query |

---

## Governor limits

- Max 100 HTTP callouts per transaction — each `query()` call is one transaction
- Heap limit 6 MB (synchronous) — don't deserialize massive payloads; use server-side pagination
- CPU limit 10 seconds — avoid nested loops over large response arrays

---

## Setup prerequisites — in this exact order

### 1. Deploy Apex classes first
The `Salesforce Connect: Custom (Developed with Apex)` type only appears in the External Data Source type dropdown **after** at least one `DataSource.Provider` subclass is deployed in the org.

This is not a permissions issue. It is a dependency — Salesforce discovers available Provider classes at runtime. No deployed Provider = no option in the dropdown.

**Correct sequence — always:**
1. Deploy Apex classes first (`sf project deploy start`)
2. Then go to Setup → External Data Sources → New → the Custom Apex type will appear

If the user says "I don't see the Custom Apex option in the dropdown", the answer is: deploy the classes first, then come back to Setup.

### 2. Add Remote Site Setting before testing

The external API's base URL must be whitelisted or callouts fail silently — `query()` returns empty rows with no exception, no error message. Deploy as metadata or add at Setup → Remote Site Settings → New.

### 3. After Validate and Sync — set Deployment Status to Deployed

After Validate and Sync, Salesforce creates the External Object with status **"In Development"**. Records return 0 results in list views and SOQL until this is changed. No error is shown — another silent failure.

```text
Setup → Object Manager → [YourObject]__x → Edit
  Deployment Status → Deployed → Save
```

Always tell the user this step after Validate and Sync completes.

### 4. Create a tab to surface the External Object in App Launcher

External Objects are invisible in the UI without a tab. Create one at:
```text
Setup → Tabs → Custom Object Tabs → New → select [YourObject]__x → Save
```

### Also required
- **Salesforce Connect license** — without it, all Connect adapter types including OData are hidden. If the user sees OData and Cross-Org in the dropdown, the license is already active.

---

## Anti-patterns

| Don't | Why | Do |
|---|---|---|
| Generate code without knowing the API shape | Wrong field types, wrong ExternalId mapping, broken adapter | Ask for API name, base URL, auth type, sample response first |
| Deploy ExternalDataSource as metadata | Not a deployable metadata type — sf CLI will error | Register the External Data Source manually in Setup after deploying the Apex classes |
| Use `upsertRow()` or `deleteRow()` (singular) | These methods don't exist — compile error | Use `upsertRows()` and `deleteRows()` (plural) |
| Put `sync()` only on Provider | On some API versions `sync()` must be on Connection — compiler will tell you | Implement `sync()` on Connection; remove from Provider if it errors |
| Hardcode the API URL in Apex | Credentials exposed in source, callout blocked | Always use `callout:NamedCredentialName` |
| Return a single `DataSource.TableResult` from `search()` | `search()` returns `List<DataSource.TableResult>` — compile error | Loop over `context.tableSelections` and return one result per table |
| Skip COUNT handling in `query()` | List views fire COUNT queries; without detection they return wrong results | Check `columnsSelected[0].aggregation == DataSource.QueryAggregation.COUNT` |
| Leave External Object in "In Development" | Records return 0 with no error — invisible to the user | After Validate and Sync: Object Manager → [Object]__x → Edit → Deployed |
| Skip the Remote Site Setting | Callout fires silently, returns empty rows, no exception | Deploy `remoteSiteSettings/[API].remoteSite-meta.xml` or add manually in Setup |

---

## Before shipping

Confirm: inputs collected (API name, URL, auth, sample response, write support) → code has `sync()` + `query()` + `search()` on Connection, `getCapabilities()` + `getConnection()` on Provider, `ExternalId` and `nameColumn` on every table, COUNT handling in `query()`, mock data for tests, `callout:` prefix on all endpoints → both `.cls-meta.xml` files generated → deploy command given → post-deploy steps communicated (Named Credential setup, Remote Site Setting, External Data Source registered, Validate and Sync, Deployment Status → Deployed, tab created).

---

## Reference examples

See [`references/official-examples.md`](references/official-examples.md) for annotated study of the official Salesforce Connect adapter examples — GitHub Issues (full DML, picklist, cross-table relationships), Google Drive (OAuth + test mock), Google Books (pagination), StackOverflow (multiple tables), and Loopback (filter translation). Read before generating for a new user.

---

## Project setup — if the developer has no SFDX project yet

Before deploying, they need a project structure. If one doesn't exist, generate it first:

```bash
sf project generate --name my-adapter --output-dir .
cd my-adapter
```

This creates `force-app/main/default/classes/` and the required `sfdx-project.json`. All generated files go into this structure. The developer does not need VS Code, Agentforce Vibes, or any Salesforce IDE — just `sf` CLI installed and an org authenticated via `sf org login web --alias my-org`.

This skill works with **any coding agent** that can read a context file — Claude Code, Cursor, Windsurf, GitHub Copilot, or any agent with the SKILL.md loaded. No Salesforce MCP server, no Agentforce Vibes, no internal Salesforce tooling required.

---

## Output format

Generate files in this order, then give the deploy command:

1. `force-app/main/default/classes/[API]DataSourceConnection.cls`
2. `force-app/main/default/classes/[API]DataSourceProvider.cls`
3. `force-app/main/default/classes/[API]DataSourceConnection.cls-meta.xml`
4. `force-app/main/default/classes/[API]DataSourceProvider.cls-meta.xml`
5. `force-app/main/default/namedCredentials/[API].namedCredential-meta.xml` — public APIs only

One-line comment at top of each Apex class: `// Salesforce Connect custom adapter for [API name]`
No other inline comments unless a logic choice is non-obvious.

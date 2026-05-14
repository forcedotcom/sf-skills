<!-- Parent: building-omnistudio-integration-procedure/SKILL.md -->

# Integration Procedure Best Practices

> **Version**: 1.0.0
> **Applies to**: OmniStudio Integration Procedures (Core namespace and Vlocity managed package)

This guide consolidates best practices for building maintainable, performant, and reliable Integration Procedures.

---

## Table of Contents

**Strategy & Planning**
1. [When to Use an Integration Procedure](#1-when-to-use-an-integration-procedure)
2. [IP vs Flow vs Apex: Decision Framework](#2-ip-vs-flow-vs-apex-decision-framework)

**Design & Structure**
3. [Element Ordering and Execution Flow](#3-element-ordering-and-execution-flow)
4. [Naming Conventions](#4-naming-conventions)
5. [Input/Output Contract Design](#5-inputoutput-contract-design)

**Error Handling**
6. [Error Handling Patterns](#6-error-handling-patterns)
7. [Conditional Rollback](#7-conditional-rollback)

**Data Operations**
8. [Response Mapping from Data Mappers](#8-response-mapping-from-data-mappers)
9. [Bounded Extracts and Pagination](#9-bounded-extracts-and-pagination)

**Performance**
10. [Caching Strategies](#10-caching-strategies)
11. [Batch vs Sequential Execution](#11-batch-vs-sequential-execution)
12. [Reducing Redundant Calls](#12-reducing-redundant-calls)

**Maintenance**
13. [Versioning with Type/SubType](#13-versioning-with-typesubtype)
14. [Documentation Standards](#14-documentation-standards)

---

## 1. When to Use an Integration Procedure

Integration Procedures are optimal when:

- You need **declarative multi-step orchestration** combining reads, writes, transforms, and callouts
- The process involves **multiple data sources** (Salesforce objects + external APIs)
- You need **server-side execution** without user interaction (unlike OmniScripts)
- The orchestration requires **conditional branching** or **loop iteration** over collections
- You want **reusability** — the same IP can be called by OmniScripts, FlexCards, Apex, or other IPs

Integration Procedures are NOT optimal when:

- A single DataRaptor can accomplish the task (no orchestration needed)
- The logic is purely computational with no data access (use Apex or a Formula)
- You need real-time user interaction during execution (use OmniScript with embedded IP calls)
- The process is a simple CRUD operation on one object (use a DataRaptor Load directly)

---

## 2. IP vs Flow vs Apex: Decision Framework

| Criterion | Integration Procedure | Flow | Apex |
|-----------|-----------------------|------|------|
| Multi-step orchestration | Strong — designed for chaining | Possible but verbose | Manual coding required |
| External API callouts | HTTP Action element | HTTP Callout action (GA) | Full control via HttpRequest |
| OmniStudio integration | Native — called by OmniScript/FlexCard | Requires adapter | Requires @AuraEnabled or REST |
| Complex business logic | Limited — use Remote Action for complex logic | Decision elements | Full language support |
| Bulk data processing | Loop Block with batch sizing | Collection operations | SOQL/DML with governor awareness |
| Error handling granularity | Per-element try/catch | Fault paths per DML | Full try/catch/finally |
| Admin maintainability | Declarative, visual | Declarative, visual | Requires developer |
| Debugging | Preview panel, debug logs | Flow debug | Apex debug logs |
| Transaction control | Limited — each element may be its own transaction | Single transaction (before-save) or per-screen | Full transaction control |

**Rule of thumb**: If the process serves OmniStudio components, use an IP. If it serves standard Salesforce UI automation, use a Flow. If it requires complex computation or fine-grained transaction control, use Apex.

---

## 3. Element Ordering and Execution Flow

Elements execute top-to-bottom in the order they appear in the procedure definition. Follow these ordering principles:

### Recommended Order

1. **Set Values** — Initialize variables, set defaults, normalize input
2. **Validation** — Conditional Block to validate required inputs before proceeding
3. **Data Retrieval** — DataRaptor Extract or HTTP Action to fetch required data
4. **Data Transformation** — DataRaptor Transform to shape data for downstream use
5. **Business Logic** — Conditional Blocks, Remote Actions for decisions
6. **Data Modification** — DataRaptor Load to write records
7. **Response Assembly** — Set Values to build the output response

### Ordering Rules

- **Fetch before transform**: Extract data before attempting to reshape it
- **Validate before mutate**: Check preconditions before performing DML
- **Independent reads first**: Group all DataRaptor Extracts at the top where possible
- **Error-prone steps last**: Place steps that might fail (HTTP, DML) after all preparatory work
- **Response assembly at the end**: Build the final output after all processing completes

---

## 4. Naming Conventions

### Type/SubType

- **Type**: Business process name in PascalCase (e.g., `AccountOnboarding`, `OrderProcessing`)
- **SubType**: Version or variant identifier (e.g., `Standard`, `v2`, `Retail`)
- Combined format: `Type_SubType` (e.g., `AccountOnboarding_Standard`)

### Element Names

- Use descriptive, action-oriented names: `GetAccountDetails`, `ValidateAddress`, `CreateContactRecord`
- Prefix with the action type for scannability: `Extract_`, `Load_`, `Transform_`, `Check_`, `Call_`
- Avoid generic names like `Step1`, `Action2`, `Process`

### Variables

- Input variables: `in_variableName`
- Output variables: `out_variableName`
- Internal variables: `var_variableName`

---

## 5. Input/Output Contract Design

Define clear contracts for what the IP expects and returns:

### Input Contract

```json
{
  "accountId": "001XXXXXXXXXXXX",
  "includeContacts": true,
  "contactLimit": 10
}
```

- Document every expected input field with type and whether it is required
- Set default values in a Set Values element for optional inputs
- Validate required inputs with a Conditional Block before processing

### Output Contract

```json
{
  "success": true,
  "account": { "Name": "Acme Corp", "Industry": "Technology" },
  "contacts": [ { "Name": "John Doe", "Email": "john@acme.com" } ],
  "errors": []
}
```

- Return a consistent structure regardless of success or failure
- Include a `success` boolean and an `errors` array in every response
- Namespace outputs clearly so consumers know which element produced which data

---

## 6. Error Handling Patterns

### Per-Element Error Handling

Every element that performs DML or makes an external call should have error handling:

1. **DataRaptor Load Actions**: Check the response for error indicators. Use a Conditional Block after the Load to inspect the result and branch to error handling if needed.

2. **HTTP Actions**: Check the HTTP status code in the response. Branch on non-2xx responses.

3. **Remote Actions**: Apex exceptions surface in the element response. Check for error keys in the output.

### Try/Catch Pattern

Structure error handling as a three-step pattern:

1. **Try**: Execute the data-modifying element
2. **Check**: Conditional Block inspects the element's response for errors
3. **Handle**: Set Values element builds an error response or a Conditional Block routes to compensating actions

### Error Response Structure

```json
{
  "success": false,
  "errors": [
    {
      "element": "CreateOrderRecord",
      "code": "FIELD_CUSTOM_VALIDATION_EXCEPTION",
      "message": "Order amount exceeds credit limit"
    }
  ]
}
```

---

## 7. Conditional Rollback

When an IP performs multiple sequential DML operations and a later step fails:

### Compensating Action Pattern

1. After each successful DML, store the created record IDs in variables
2. If a subsequent step fails, use stored IDs to execute compensating DataRaptor Load actions (delete/update) to undo prior changes
3. Return a clear error response indicating which steps succeeded and which failed

### Design Considerations

- IPs do not have native transaction rollback across elements
- Each DataRaptor Load action may commit independently
- Plan for partial failure in multi-step write operations
- Consider whether the business process can tolerate partial completion
- For strict atomicity requirements, move the multi-DML logic to an Apex Remote Action where you control the transaction boundary

---

## 8. Response Mapping from Data Mappers

### How Response Namespacing Works

Each element's output is stored under a key matching the element name. For example, if a DataRaptor Extract element named `GetAccount` returns `{ "Name": "Acme" }`, the IP's response contains:

```json
{
  "GetAccount": {
    "Name": "Acme"
  }
}
```

### Referencing Upstream Outputs

In downstream elements, reference upstream data using the element namespace:

- **In PropertySetConfig**: `%GetAccount:Name%`
- **In Set Values**: Map from `GetAccount.Name` to the target variable

### Common Mapping Issues

| Problem | Cause | Fix |
|---------|-------|-----|
| Null value in downstream element | Element name mismatch in reference | Verify exact element name spelling and case |
| Array vs object confusion | DataRaptor returns collection, consumer expects single | Use `[0]` accessor or Transform to extract first item |
| Nested path not resolving | Deep path syntax incorrect | Use dot notation: `GetAccount.BillingAddress.City` |

---

## 9. Bounded Extracts and Pagination

### Setting Limits

Every DataRaptor Extract Action should have a reasonable LIMIT:

- Set the LIMIT in the DataRaptor definition itself, not in the IP
- For user-facing queries, limit to 50-200 records
- For batch processing, limit to 2000 records per iteration
- For count/existence checks, limit to 1

### Pagination Pattern

For large datasets that exceed a single extract's limit:

1. First extract: fetch records with LIMIT and OFFSET 0
2. Check if result count equals LIMIT (more records may exist)
3. Loop: increment OFFSET by LIMIT, re-extract, append results
4. Exit when result count is less than LIMIT

Avoid this pattern for datasets exceeding 10,000 records — use Apex Batch or a scheduled process instead.

---

## 10. Caching Strategies

### When to Cache

- Read-only IPs that serve reference data (picklist values, configuration)
- IPs called frequently by multiple OmniScripts or FlexCards
- IPs whose source data changes infrequently

### When NOT to Cache

- IPs that perform DML (creates, updates, deletes)
- IPs whose output depends on the current user's permissions or context
- IPs that return time-sensitive data (real-time pricing, inventory)

### Cache Configuration

Set caching properties in the IP's PropertySet:

- `cacheType`: `Platform` for org-level cache, `Session` for user-session cache
- `cacheTTL`: Time-to-live in seconds (e.g., 300 for 5 minutes, 3600 for 1 hour)

### Cache Key Considerations

The cache key includes the IP's Type/SubType and the input JSON. Different inputs produce different cache entries. Normalize input data to maximize cache hit rates.

---

## 11. Batch vs Sequential Execution

### Sequential (Default)

Elements execute one after another. Use when:

- Each step depends on the output of the previous step
- Strict ordering is required for business logic
- Error handling needs to stop execution on first failure

### Batch / Parallel Opportunities

While IPs execute elements sequentially by default, you can optimize by:

- Grouping independent DataRaptor Extracts at the beginning of the procedure
- Using a single DataRaptor Extract with multiple output fields instead of multiple extracts
- Combining related DataRaptor Transforms into a single transform with multiple mappings
- Moving parallelizable logic into an Apex Remote Action that handles concurrent operations internally

### Loop Block Performance

- Set appropriate batch sizes for Loop Blocks processing large collections
- Avoid nested loops — flatten data with a Transform first
- Minimize the number of elements inside a loop body
- Move invariant computations outside the loop

---

## 12. Reducing Redundant Calls

### Common Redundancy Patterns

| Pattern | Problem | Fix |
|---------|---------|-----|
| Same DataRaptor called twice | Duplicate SOQL queries | Extract once, reference the result in multiple downstream elements |
| Nested IP re-fetches parent data | Wasted queries | Pass data as input to the nested IP instead of re-fetching |
| Loop body fetches lookup data | N+1 query pattern | Fetch lookup data before the loop, reference it inside |

### Data Passing vs Re-Fetching

Prefer passing data between elements over re-fetching:

- Use Set Values to copy data from one element's output to another element's input
- Pass context data to nested IP calls as input parameters
- Store intermediate results in variables for reuse

---

## 13. Versioning with Type/SubType

### Versioning Strategy

- Use SubType to version IPs: `Type=AccountOnboarding`, `SubType=v1` and `SubType=v2`
- Only one version of a Type/SubType pair can be active at a time
- Deploy and test the new version as inactive before deactivating the old version
- Update consumers (OmniScripts, FlexCards) to reference the new SubType after activation

### Migration Checklist

1. Create the new IP with updated SubType
2. Deploy and test in sandbox with the new SubType
3. Update all consumers to reference the new SubType
4. Activate the new IP
5. Deactivate the old IP (do not delete until consumers are verified)

---

## 14. Documentation Standards

### Procedure-Level Documentation

Every IP should have:

- A description field explaining the business purpose
- Input/output JSON contract documented in element descriptions or external documentation
- Dependency list (which DataRaptors, Apex classes, and nested IPs it requires)

### Element-Level Documentation

Every element should have:

- A description explaining what it does and why
- Notes on expected input shape and output shape
- Error handling behavior documented

### Maintenance Documentation

- Record the Type/SubType and the org(s) where the IP is deployed
- List all consumers (OmniScripts, FlexCards, Apex classes, other IPs) that call this IP
- Note any external API dependencies with endpoint URLs and authentication method

<!-- Parent: building-omnistudio-flexcard/SKILL.md -->

# FlexCard Data Binding Guide

## Integration Procedure Data Source Configuration

### Basic IP Binding

The most common FlexCard data source is an Integration Procedure. The data source configuration specifies which IP to call, what input to send, and where to find the results in the IP response.

```json
{
  "dataSource": {
    "type": "IntegrationProcedures",
    "value": {
      "ipMethod": "Type_SubType",
      "inputMap": {
        "recordId": "{recordId}"
      },
      "resultListPath": ""
    }
  }
}
```

| Property | Purpose | Example |
|----------|---------|---------|
| `type` | Data source type identifier | `"IntegrationProcedures"` (plural, capital P) |
| `ipMethod` | IP Type and SubType joined by underscore | `"Account_GetSummary"` |
| `inputMap` | Key-value pairs sent as IP input | `{ "recordId": "{recordId}" }` |
| `resultListPath` | JSON path to the array node for list-type cards | `"records"` or `""` for root |

### IP Method Naming Convention

The `ipMethod` value combines the IP's Type and SubType fields:

```
IP Type:    "Account"
IP SubType: "GetSummary"
ipMethod:   "Account_GetSummary"
```

Ensure the IP is active and the Type/SubType match exactly (case-sensitive).

### Input Map Parameters

Input parameters pass context from the FlexCard's hosting environment into the IP:

```json
{
  "inputMap": {
    "recordId": "{recordId}",
    "accountId": "{Account.Id}",
    "status": "Active",
    "limit": 10
  }
}
```

| Syntax | Resolves To |
|--------|------------|
| `{recordId}` | The current record's ID from the hosting Lightning page |
| `{Account.Id}` | A field from a parent FlexCard's data source |
| `"Active"` | A static/literal value |
| `{param.customKey}` | A URL parameter or custom context variable |

---

## Field Mapping Syntax

### Basic Field Mapping

Map IP response fields to FlexCard display elements using curly-brace merge syntax:

```
IP Response JSON:                    FlexCard Merge Field:
─────────────────                    ─────────────────────
{ "Name": "Acme Corp" }        →    {Name}
{ "Status": "Active" }         →    {Status}
{ "Amount": 50000 }            →    {Amount}
```

### Nested Field Mapping

Access nested objects in the IP response using dot notation:

```
IP Response JSON:                         FlexCard Merge Field:
─────────────────                         ─────────────────────
{                                    →    {Account.Name}
  "Account": {                       →    {Account.Industry}
    "Name": "Acme Corp",            →    {Account.Owner.Name}
    "Industry": "Technology",
    "Owner": {
      "Name": "Jane Smith"
    }
  }
}
```

### Array Field Mapping

For card list layouts, set `resultListPath` to the array node. Each card in the list renders one item from the array:

```json
{
  "dataSource": {
    "value": {
      "ipMethod": "Contact_GetRelated",
      "resultListPath": "contacts"
    }
  }
}
```

```
IP Response:                              Each Card Renders:
────────────                              ──────────────────
{                                         Card 1: {Name} → "Alice"
  "contacts": [                                   {Email} → "alice@acme.com"
    { "Name": "Alice", "Email": "..." },
    { "Name": "Bob",   "Email": "..." }, Card 2: {Name} → "Bob"
    { "Name": "Carol", "Email": "..." }          {Email} → "bob@acme.com"
  ]
}                                         Card 3: {Name} → "Carol"
                                                  {Email} → "carol@acme.com"
```

### Formatted Field Display

Apply formatting to merge fields for display:

| Format Need | Approach |
|-------------|----------|
| Currency | Format in the IP response (e.g., return `"$50,000.00"`) or use OmniStudio formatting |
| Date | Return ISO date from IP; apply date formatting in the FlexCard field configuration |
| Boolean | Use conditional rendering to show icons or text instead of true/false |
| Percentage | Return as a number; format display in the FlexCard field |

---

## Conditional Rendering Based on Data

### Field-Level Visibility

Show or hide individual fields based on a data value:

```
Condition:  {Status} == "Active"
Action:     Show the "Renewal Date" field

Condition:  {Amount} > 100000
Action:     Show the "High Value" badge

Condition:  {Email} != null
Action:     Show the email field (hide when null)
```

### State-Level Visibility

FlexCards support multiple states. Each state can have visibility conditions:

| State | Visibility Condition | Use Case |
|-------|---------------------|----------|
| Default | Always visible | Primary card content |
| Empty | Data source returns 0 records | "No records found" message |
| Error | Data source returns error | Error notification |
| Conditional | Field matches specific value | Status-specific card layout |

### Conditional Rendering Operators

| Operator | Syntax | Example |
|----------|--------|---------|
| Equals | `==` | `{Status} == "Active"` |
| Not equals | `!=` | `{Status} != "Closed"` |
| Greater than | `>` | `{Amount} > 10000` |
| Less than | `<` | `{DaysOpen} < 30` |
| Contains | `CONTAINS` | `{Name} CONTAINS "Corp"` |
| Is null | `== null` | `{Email} == null` |
| Is not null | `!= null` | `{Phone} != null` |

### Conditional Styling

Apply different styles based on data values:

```
If {Status} == "Active"    → Green badge (slds-badge slds-theme_success)
If {Status} == "Expired"   → Red badge (slds-badge slds-theme_error)
If {Status} == "Pending"   → Yellow badge (slds-badge slds-theme_warning)
```

Use SLDS theme classes rather than inline color styles to maintain dark mode compatibility.

---

## Multi-Data-Source Cards

### When to Use Multiple Data Sources

- The card displays data from unrelated objects that cannot be fetched in a single IP
- Different sections of the card have different refresh requirements
- A child card needs its own independent data source

### Configuration Pattern

```
FlexCard: AccountOverview
├── Data Source 1: "Account_GetSummary"
│     Input: { "recordId": "{recordId}" }
│     Fields: {ds1.Name}, {ds1.Industry}, {ds1.Status}
│
├── Data Source 2: "Case_GetOpenCount"
│     Input: { "accountId": "{recordId}" }
│     Fields: {ds2.openCaseCount}, {ds2.lastCaseDate}
│
└── Data Source 3: "Opportunity_GetPipeline"
      Input: { "accountId": "{recordId}" }
      Fields: {ds3.totalPipeline}, {ds3.nextCloseDate}
```

### Data Source Naming

When a card has multiple data sources, reference fields using the data source name prefix:

```
Single data source:     {Name}
Multiple data sources:  {ds1.Name}  or  {accountSummary.Name}
```

### Load Order and Dependencies

- Data sources load in parallel by default
- If Data Source 2 depends on a value from Data Source 1, configure the dependency order
- Use conditional rendering to hide sections until their data source has loaded
- Display a loading indicator while data sources are in progress

### Coordinating Multiple Sources

| Pattern | Description | Use Case |
|---------|-------------|----------|
| **Parallel load** | All sources fetch simultaneously | Independent data sets |
| **Sequential load** | Source B waits for Source A | Source B needs a value from Source A's response |
| **Conditional load** | Source B only loads if Source A meets a condition | Avoid unnecessary API calls |

---

## Error Handling for Failed Data Sources

### Common Failure Modes

| Failure | Cause | User Impact |
|---------|-------|------------|
| IP not found | IP name misspelled or IP not deployed | Card shows no data; console error |
| IP inactive | IP exists but is not activated | Card shows no data |
| IP timeout | IP takes too long to execute | Card shows loading indefinitely |
| IP error response | IP logic throws an exception | Card may show partial data or error state |
| Auth failure | User lacks permission to run the IP | Card shows no data; access error |
| Network error | Connectivity issue between client and server | Card shows no data |

### Error State Design

Configure an explicit error state rather than letting the card fail silently:

```
┌──────────────────────────────────┐
│  ⚠ Unable to load account data   │
│                                  │
│  The data source returned an     │
│  error. Try refreshing the page. │
│                                  │
│  [Refresh]  [Contact Support]    │
└──────────────────────────────────┘
```

**Error State Guidelines:**
- Use plain language, not technical error codes
- Provide an actionable next step (refresh, retry, contact admin)
- Log the technical error details for debugging (not displayed to end users)
- Do not show a blank card with no explanation

### Fallback Strategies

| Strategy | Implementation | When to Use |
|----------|---------------|-------------|
| **Cached data** | Show previously loaded data with a "stale" indicator | Data changes infrequently |
| **Partial render** | Show fields that loaded; hide failed sections | Multi-source card where only one source fails |
| **Empty state** | Show "No data available" with context | Single-source card where the source fails |
| **Retry** | Provide a manual retry button | Transient errors (network, timeout) |

### Debugging Data Source Issues

1. **Check IP activation**: Query `SELECT Name, IsActive FROM OmniProcess WHERE Name = 'Type_SubType'`
2. **Verify IP input**: Use the OmniStudio Preview tool to test the IP with the same input parameters
3. **Check field paths**: Ensure merge field paths (`{field.subfield}`) match the actual IP response structure
4. **Review permissions**: Confirm the running user has access to the IP and the underlying objects
5. **Inspect browser console**: FlexCard data source errors appear in the browser developer console
6. **Test with static data**: Temporarily configure the FlexCard with a static JSON data source to isolate whether the issue is the IP or the card

### Data Source Validation Checklist

Before deploying a FlexCard, verify each data source:

- [ ] IP exists in the target org
- [ ] IP is activated
- [ ] IP Type and SubType match the `ipMethod` value exactly (case-sensitive)
- [ ] Input parameters use correct merge field syntax
- [ ] `resultListPath` points to the correct array node (for list cards)
- [ ] All merge fields in the card map to actual fields in the IP response
- [ ] Error state is configured for graceful failure
- [ ] Empty state is configured for zero-record responses
- [ ] Data source has been tested with real data in a sandbox

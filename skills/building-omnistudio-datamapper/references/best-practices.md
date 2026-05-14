<!-- Parent: building-omnistudio-datamapper/SKILL.md -->

# Data Mapper Best Practices

## When to Use Each Type

### Extract

Use Extract when:
- Reading data from one or more related Salesforce objects
- You need relationship queries (parent-to-child or child-to-parent)
- Formula fields are required in the output
- Data volume is moderate (under 10K records per execution)
- You need aggregate functions or complex filter logic

Do NOT use Extract when:
- Read volume exceeds 10K records consistently -- use Turbo Extract
- No SOQL is needed (data reshaping only) -- use Transform
- You are writing data -- use Load

### Turbo Extract

Use Turbo Extract when:
- Read-heavy scenarios with high volume (10K+ records)
- Query is straightforward with indexed filter fields
- Formula fields are not required
- No related list (child-to-parent) queries are needed
- Performance is the primary concern (10x+ faster than standard Extract)

Do NOT use Turbo Extract when:
- Formula fields are needed in output
- Related list queries are required
- Aggregate queries (COUNT, SUM) are needed
- Polymorphic lookup fields are involved

### Transform

Use Transform when:
- Reshaping JSON structures between Integration Procedure steps
- Renaming fields from one schema to another
- Flattening nested data structures
- Filtering or merging in-memory datasets
- No database interaction is needed

Do NOT use Transform when:
- Reading from or writing to Salesforce objects -- use Extract or Load
- Data needs to be persisted -- use Load

### Load

Use Load when:
- Inserting, updating, upserting, or deleting Salesforce records
- Writing data collected from OmniScript input or external sources
- Synchronizing data from Integration Procedure callout responses

Do NOT use Load when:
- Reading data -- use Extract or Turbo Extract
- Reshaping data without persistence -- use Transform

---

## Field Mapping Patterns

### Explicit Field Selection

Always specify fields explicitly. Never rely on wildcard or "all fields" selection.

```
Good:  Account.Name, Account.Industry, Account.BillingCity
Bad:   Account.* (extracts all fields, wastes bandwidth and heap)
```

### Input/Output Path Structure

Data Mapper fields use dot-notation paths for input and output:

```
Input Path:   AccountData.Name
Output Path:  Account.Name
```

For nested structures:

```
Input Path:   Response.data.accounts[0].name
Output Path:  AccountList.Name
```

### Type Conversion Handling

Map fields with compatible types. Common conversions:

| Source Type | Target Type | Notes |
|-------------|-------------|-------|
| String | Date | Requires ISO 8601 format (YYYY-MM-DD) |
| String | Number | Ensure source contains numeric values only |
| Boolean | String | Maps to "true"/"false" string literals |
| DateTime | Date | Truncates time component |
| Picklist | String | Maps selected value as string |

### Lookup Resolution for Load

When loading records with lookup relationships:

1. Define a lookup mapping that resolves the external key to a Salesforce ID
2. Specify the lookup object and match field (e.g., `Account.Name` to resolve `AccountId`)
3. Handle cases where the lookup returns no match (set default or fail gracefully)

```
Field:         AccountId
Lookup Object: Account
Match Field:   Name
Input Path:    InputData.AccountName
```

---

## Query Sequence Optimization

### Filter Field Indexing

For Extract and Turbo Extract, filter on indexed fields whenever possible:

- `Id` (always indexed)
- `Name` (indexed on standard objects)
- `CreatedDate` (indexed)
- `SystemModstamp` (indexed)
- Custom fields marked as External ID or Unique
- Custom Index fields (request from admin if needed)

### Filter Order

Place the most selective filter first to reduce the result set early:

```
Good:  WHERE Id = :recordId AND Status = 'Active'
Bad:   WHERE Status = 'Active' AND Id = :recordId
```

### Relationship Query Depth

Limit relationship traversal to 2 levels for performance:

```
Good:  Account.Owner.Name (1 level)
Bad:   Account.Parent.Parent.Parent.Owner.Name (3+ levels)
```

### Limit and Offset

Always set a LIMIT on Extract queries unless the consuming component guarantees a bounded input:

```
LIMIT 200    -- Standard batch size
LIMIT 2000   -- Maximum for most UI scenarios
LIMIT 10000  -- Absolute maximum, use only with pagination
```

---

## Null Handling and Type Conversion

### Default Values

Set default values for fields that may be null to prevent downstream errors:

| Field Type | Recommended Default | Rationale |
|------------|-------------------|-----------|
| String | `""` (empty string) | Prevents null reference in concatenation |
| Number | `0` | Prevents null arithmetic errors |
| Boolean | `false` | Prevents null conditional evaluation |
| Date | (no default) | Leave null; do not fabricate dates |
| Lookup | (no default) | Leave null; handle in consuming component |

### Null-Safe Mapping

When mapping fields that may be null:

1. Set `isNullable: true` on the OmniDataTransformItem
2. Configure a default value where business logic requires one
3. Document which fields are expected to be null in certain scenarios
4. Test with records that have null values in mapped fields

---

## Relationship Queries

### Parent-to-Child (Subquery)

Extract supports parent-to-child relationship queries:

```
Object: Account
Fields: Name, Industry
Child Relationship: Contacts (Contact)
Child Fields: FirstName, LastName, Email
```

Output structure:

```json
{
  "Name": "Acme Corp",
  "Industry": "Technology",
  "Contacts": [
    { "FirstName": "Jane", "LastName": "Doe", "Email": "jane@acme.com" }
  ]
}
```

### Child-to-Parent (Lookup Traversal)

Extract supports child-to-parent traversal via dot notation:

```
Object: Contact
Fields: FirstName, LastName, Account.Name, Account.Industry
```

Output structure:

```json
{
  "FirstName": "Jane",
  "LastName": "Doe",
  "AccountName": "Acme Corp",
  "AccountIndustry": "Technology"
}
```

### Turbo Extract Limitations

Turbo Extract does NOT support:
- Child-to-parent relationship queries (subqueries)
- Formula fields
- Aggregate functions
- Polymorphic lookups (e.g., `WhoId` on Task)

---

## Performance with Large Data Volumes

### Batch Size Recommendations

| Record Count | Recommended Approach |
|--------------|---------------------|
| 1-200 | Standard Extract, single call |
| 200-2000 | Turbo Extract, single call |
| 2000-10000 | Turbo Extract with pagination via Integration Procedure |
| 10000+ | Batch processing: scheduled Integration Procedure with chunked Turbo Extract calls |

### Heap Size Management

Each Data Mapper execution contributes to the Apex heap limit (6 MB synchronous, 12 MB async):

- Map only the fields you need (reduces JSON payload size)
- Use Turbo Extract for large result sets (server-side processing reduces heap usage)
- Paginate results when total data exceeds 2 MB

### Caching Strategy

For data that changes infrequently:

- Enable Platform Cache in the consuming Integration Procedure
- Set appropriate TTL (Time To Live) based on data change frequency
- Cache at the org partition level for shared reference data
- Cache at the session partition level for user-specific data

### Monitoring

Track Data Mapper performance using:

```bash
sf data query -q "SELECT Id,Name,Type,LastModifiedDate FROM OmniDataTransform WHERE IsActive=true ORDER BY LastModifiedDate DESC" -o <org>
```

Review execution logs in OmniStudio Designer > Data Mapper > Preview to identify slow queries and excessive field counts.

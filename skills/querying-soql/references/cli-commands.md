<!-- Parent: querying-soql/SKILL.md -->
# Salesforce CLI SOQL Commands

## Quick Reference

| Task | Command |
|------|---------|
| Run query | `sf data query --query "SELECT..."` |
| JSON output | `sf data query --query "..." --json` |
| CSV output | `sf data query --query "..." --result-format csv` |
| Bulk export | `sf data export bulk --query "SELECT..." --target-org alias` |
| Query plan | `sf api request rest '/query/?explain=<SOQL>' --target-org alias` |

---

## Basic Queries

### Run a Query

```bash
sf data query \
  --query "SELECT Id, Name, Industry FROM Account LIMIT 10" \
  --target-org my-sandbox
```

### Query with Filters

```bash
sf data query \
  --query "SELECT Id, Name FROM Account WHERE Industry = 'Technology'" \
  --target-org my-sandbox
```

### Query Relationships

```bash
# Child-to-parent
sf data query \
  --query "SELECT Id, Name, Account.Name FROM Contact LIMIT 10" \
  --target-org my-sandbox

# Parent-to-child
sf data query \
  --query "SELECT Id, Name, (SELECT Id, Name FROM Contacts) FROM Account LIMIT 5" \
  --target-org my-sandbox
```

---

## Output Formats

### Human-Readable (Default)

```bash
sf data query \
  --query "SELECT Id, Name FROM Account LIMIT 5" \
  --target-org my-sandbox
```

### JSON

```bash
sf data query \
  --query "SELECT Id, Name FROM Account LIMIT 5" \
  --target-org my-sandbox \
  --json
```

### CSV

```bash
sf data query \
  --query "SELECT Id, Name, Industry FROM Account" \
  --target-org my-sandbox \
  --result-format csv > accounts.csv
```

### Direct to File

```bash
sf data query \
  --query "SELECT Id, Name, Industry FROM Account" \
  --target-org my-sandbox \
  --result-format csv \
  --output-file accounts.csv
```

---

## Bulk Data Export

For large result sets (> 2,000 records), use the dedicated bulk export command:

```bash
# Export to CSV (default)
sf data export bulk \
  --query "SELECT Id, Name FROM Account" \
  --target-org my-sandbox \
  --output-file accounts.csv

# Export as JSON
sf data export bulk \
  --query "SELECT Id, Name FROM Account" \
  --target-org my-sandbox \
  --output-file accounts.json \
  --result-format json
```

> **Note**: `--bulk` and `--wait` flags on `sf data query` were removed in v2.87.7. Use `sf data export bulk` instead.

---

## Query Plan Analysis

Analyze query performance before running:

```bash
sf data query \
  --query "SELECT Id FROM Account WHERE Name = 'Acme'" \
  --target-org my-sandbox \
  --use-tooling-api \
  --plan
```

### Understanding Query Plan Output

```json
{
  "plans": [{
    "cardinality": 50,           // Estimated rows returned
    "fields": ["Name"],          // Fields used for filtering
    "leadingOperationType": "Index",  // Index = good, TableScan = bad
    "relativeCost": 0.1,         // Lower is better
    "sobjectCardinality": 10000, // Total records in object
    "sobjectType": "Account"
  }]
}
```

**Key Indicators:**
- `leadingOperationType: "Index"` = Query uses index (good)
- `leadingOperationType: "TableScan"` = Full table scan (bad for large tables)
- `relativeCost < 1` = Efficient query
- `cardinality` = Expected number of results

---

## Tooling API Queries

Query metadata objects:

```bash
# Query ApexClass
sf data query \
  --query "SELECT Id, Name, Body FROM ApexClass WHERE Name = 'MyController'" \
  --target-org my-sandbox \
  --use-tooling-api

# Query CustomField
sf data query \
  --query "SELECT Id, DeveloperName, TableEnumOrId FROM CustomField WHERE TableEnumOrId = 'Account'" \
  --target-org my-sandbox \
  --use-tooling-api
```

---

## Query from File

Store query in file and execute:

```bash
# Create query file
echo "SELECT Id, Name FROM Account WHERE Industry = 'Technology'" > query.soql

# Execute from file
sf data query \
  --file query.soql \
  --target-org my-sandbox
```

---

## Useful Patterns

### Get Record Count

```bash
sf data query \
  --query "SELECT COUNT() FROM Account" \
  --target-org my-sandbox
```

### Export to File

```bash
# CSV export
sf data query \
  --query "SELECT Id, Name, Industry, Phone FROM Account" \
  --target-org my-sandbox \
  --result-format csv > accounts.csv

# JSON export
sf data query \
  --query "SELECT Id, Name, Industry FROM Account" \
  --target-org my-sandbox \
  --json > accounts.json
```

### Query with jq Processing

```bash
# Get just the names
sf data query \
  --query "SELECT Name FROM Account LIMIT 10" \
  --target-org my-sandbox \
  --json | jq -r '.result.records[].Name'

# Count records
sf data query \
  --query "SELECT Id FROM Account" \
  --target-org my-sandbox \
  --json | jq '.result.totalSize'

# Filter in shell
sf data query \
  --query "SELECT Id, Name, Industry FROM Account" \
  --target-org my-sandbox \
  --json | jq '.result.records[] | select(.Industry == "Technology")'
```

### Query with Dates

```bash
# Records created today
sf data query \
  --query "SELECT Id, Name FROM Account WHERE CreatedDate = TODAY" \
  --target-org my-sandbox

# Records from last 30 days
sf data query \
  --query "SELECT Id, Name FROM Account WHERE CreatedDate = LAST_N_DAYS:30" \
  --target-org my-sandbox
```

### Aggregate Queries

```bash
# Count by industry
sf data query \
  --query "SELECT Industry, COUNT(Id) FROM Account GROUP BY Industry" \
  --target-org my-sandbox

# Sum of amounts
sf data query \
  --query "SELECT SUM(Amount) FROM Opportunity WHERE StageName = 'Closed Won'" \
  --target-org my-sandbox
```

---

## Troubleshooting

### Query Timeout

For long-running queries, export via bulk API:

```bash
sf data export bulk \
  --query "SELECT Id, Name FROM Account" \
  --target-org my-sandbox \
  --output-file results.csv
```

### Too Many Results

Add LIMIT or filter:

```bash
# With limit
sf data query \
  --query "SELECT Id, Name FROM Account LIMIT 1000" \
  --target-org my-sandbox

# With filter
sf data query \
  --query "SELECT Id, Name FROM Account WHERE CreatedDate = THIS_YEAR" \
  --target-org my-sandbox
```

### Non-Selective Query Error

Add indexed field to WHERE:

```bash
# Add CreatedDate filter (indexed)
sf data query \
  --query "SELECT Id FROM Lead WHERE Status = 'Open' AND CreatedDate = LAST_N_DAYS:90" \
  --target-org my-sandbox
```

### Permission Errors

Check field-level security:

```bash
# Query accessible fields only
sf data query \
  --query "SELECT Id, Name FROM Account" \
  --target-org my-sandbox
```

---

## Integration with Other Tools

### Pipe to File

```bash
sf data query \
  --query "SELECT Id, Name FROM Account" \
  --target-org my-sandbox \
  --result-format csv | tee accounts.csv
```

### Use in Scripts

```bash
#!/bin/bash

ORG=${1:-"my-sandbox"}

# Get count
COUNT=$(sf data query \
  --query "SELECT COUNT() FROM Account" \
  --target-org $ORG \
  --json | jq -r '.result.totalSize')

echo "Total accounts: $COUNT"

# Get top accounts
sf data query \
  --query "SELECT Name, AnnualRevenue FROM Account ORDER BY AnnualRevenue DESC LIMIT 10" \
  --target-org $ORG
```

### Compare Orgs

```bash
#!/bin/bash

PROD_COUNT=$(sf data query --query "SELECT COUNT() FROM Account" --target-org prod --json | jq '.result.totalSize')
SANDBOX_COUNT=$(sf data query --query "SELECT COUNT() FROM Account" --target-org sandbox --json | jq '.result.totalSize')

echo "Production accounts: $PROD_COUNT"
echo "Sandbox accounts: $SANDBOX_COUNT"
echo "Difference: $((PROD_COUNT - SANDBOX_COUNT))"
```

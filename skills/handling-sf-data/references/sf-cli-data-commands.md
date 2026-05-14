<!-- Parent: handling-sf-data/SKILL.md -->
# sf CLI Data Commands Reference

Complete reference for Salesforce CLI v2 data commands.

## Query Commands

### SOQL Query
```bash
sf data query \
  --query "SELECT Id, Name FROM Account LIMIT 10" \
  --target-org myorg \
  --json
```

### SOSL Search
```bash
sf data search \
  --query "FIND {Acme}" \
  --target-org myorg
```

### Bulk Export
```bash
sf data export bulk \
  --query "SELECT Id, Name FROM Account" \
  --output-file accounts.csv \
  --target-org myorg \
  --wait 30
```

## Record Operations

### Create Record
```bash
sf data create record \
  --sobject Account \
  --values "Name='Acme' Industry='Technology'" \
  --target-org myorg
```

### Update Record
```bash
sf data update record \
  --sobject Account \
  --record-id 001XXXXXXXXXXXX \
  --values "Industry='Healthcare'" \
  --target-org myorg
```

### Delete Record
```bash
sf data delete record \
  --sobject Account \
  --record-id 001XXXXXXXXXXXX \
  --target-org myorg
```

### Get Record
```bash
sf data get record \
  --sobject Account \
  --record-id 001XXXXXXXXXXXX \
  --target-org myorg
```

## Bulk Operations

### Bulk Import
```bash
sf data import bulk \
  --file data.csv \
  --sobject Account \
  --target-org myorg \
  --wait 30
```

### Bulk Update
```bash
sf data update bulk \
  --file updates.csv \
  --sobject Account \
  --target-org myorg \
  --wait 30
```

### Bulk Upsert
```bash
sf data upsert bulk \
  --file data.csv \
  --sobject Account \
  --external-id External_Id__c \
  --target-org myorg \
  --wait 30
```

### Bulk Delete
```bash
sf data delete bulk \
  --file ids.csv \
  --sobject Account \
  --target-org myorg \
  --wait 30
```

## Tree Operations

### Export Tree
```bash
sf data export tree \
  --query "SELECT Id, Name, (SELECT Id, Name FROM Contacts) FROM Account" \
  --output-dir ./data \
  --target-org myorg
```

### Import Tree
```bash
sf data import tree \
  --files data.json \
  --target-org myorg
```

## Common Flags

| Flag | Description |
|------|-------------|
| `--target-org`, `-o` | Target org alias |
| `--json` | JSON output format |
| `--result-format` | human, csv, json |
| `--wait` | Minutes to wait for bulk jobs |
| `--use-tooling-api` | Query Tooling API |

## Object Describe (Pre-flight Validation)

```bash
sf sobject describe --sobject ObjectName --target-org <alias> --json
```

### Useful jq filters for describe output

```bash
# Required + createable fields
jq '.result.fields[] | select(.nillable==false and .createable==true) | {name, type}'

# Valid picklist values for a specific field
jq '.result.fields[] | select(.name=="StageName") | .picklistValues[].value'

# Fields that cannot be set on create
jq '.result.fields[] | select(.createable==false) | .name'
```

---

## Apex Execution

```bash
sf apex run --file script.apex --target-org myorg
```

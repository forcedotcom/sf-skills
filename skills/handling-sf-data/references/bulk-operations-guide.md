<!-- Parent: handling-sf-data/SKILL.md -->
# Bulk Operations Guide

When and how to use Salesforce Bulk API operations.

## Decision Matrix

| Record Count | Recommended API | Command |
|--------------|-----------------|---------|
| 1-10 | Single Record | `sf data create record` |
| 11-2000 | Standard API | `sf data query` + Apex |
| 2000-10M | Bulk API 2.0 | `sf data import bulk` |
| 10M+ | Data Loader | External tool |

## Bulk API 2.0 Commands

### Import (Insert)
```bash
sf data import bulk \
  --file accounts.csv \
  --sobject Account \
  --target-org myorg \
  --wait 30
```

### Update
```bash
sf data update bulk \
  --file updates.csv \
  --sobject Account \
  --target-org myorg \
  --wait 30
```

### Upsert (Insert or Update)
```bash
sf data upsert bulk \
  --file upsert.csv \
  --sobject Account \
  --external-id External_Id__c \
  --target-org myorg \
  --wait 30
```

### Delete
```bash
sf data delete bulk \
  --file delete.csv \
  --sobject Account \
  --target-org myorg \
  --wait 30
```

### Export
```bash
sf data export bulk \
  --query "SELECT Id, Name FROM Account" \
  --output-file accounts.csv \
  --target-org myorg \
  --wait 30
```

## CSV Format Requirements

- First row: Field API names
- UTF-8 encoding
- Comma delimiter (default)
- Max 100MB per file

## Bulk API Limits

| Limit | Value |
|-------|-------|
| Batches per 24 hours | 10,000 |
| Records per 24 hours | 10,000,000 |
| Max file size | 100 MB |
| Max concurrent jobs | 100 |

## Error Handling

```bash
# Check job status
sf data resume --job-id [job-id] --target-org myorg

# Get results
sf data bulk results --job-id [job-id] --target-org myorg
```

## Best Practices

1. **Chunk large files** - Split files >100MB
2. **Use --wait** - Monitor completion
3. **Handle partial failures** - Check result files
4. **Test in sandbox** - Validate before production

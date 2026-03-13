# dynamicHighlights (RecordPage Header)

**Location:** Must be in `header` region.

**Explicit Fields** (via CLI): Use the most important fields to show a summary of the record. The single primary field is used to identify the record, like a name. The secondary fields (max 12, recommended 6) are used as a summary of the record.

```bash
--primary-field Name
--secondary-fields Phone,Industry,AnnualRevenue
```

CLI generates Facets with field references automatically.

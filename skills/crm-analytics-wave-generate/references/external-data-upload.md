# External Data Uploads (CSV → Dataset)

Use this when landing a CSV into a Wave dataset without running a recipe — e.g. synthetic test data, one-off external feeds, or standing up a dashboard before recipe sources are available.

## Process (4 steps)

1. `POST /services/data/v66.0/sobjects/InsightsExternalData` with:
   ```json
   { "Format": "Csv", "EdgemartAlias": "<datasetName>", "EdgemartContainer": "<folderId>",
     "Operation": "Overwrite", "Action": "None", "MetadataJson": "<base64 of metadata.json>" }
   ```
   Returns `{ id }` — the header id.

2. `POST /services/data/v66.0/sobjects/InsightsExternalDataPart` for each chunk:
   ```json
   { "InsightsExternalDataId": "<headerId>", "PartNumber": 1, "DataFile": "<base64 of CSV bytes>" }
   ```
   Keep parts ≤ 8 MB.

3. `PATCH /services/data/v66.0/sobjects/InsightsExternalData/<headerId>` with `{ "Action": "Process" }`. Returns 204; ingestion is queued.

4. Poll: `SELECT Id, Status, StatusMessage FROM InsightsExternalData WHERE Id = '<headerId>'`. Status flow: `New` → `Queued` → `InProgress` → `Completed` | `CompletedWithWarnings` | `Failed`.

## metadata.json minimum-viable schema

```json
{
  "fileFormat": { "charsetName": "UTF-8", "fieldsDelimitedBy": ",", "linesTerminatedBy": "\n", "numberOfLinesToIgnore": 1 },
  "objects": [{
    "connector": "CSV",
    "fullyQualifiedName": "<datasetName>",
    "name": "<datasetName>",
    "label": "<display label>",
    "fields": [
      { "name": "AccountId",    "fullyQualifiedName": "AccountId",    "label": "Account ID",    "type": "Text" },
      { "name": "TotalRevenue", "fullyQualifiedName": "TotalRevenue", "label": "Total Revenue", "type": "Numeric", "precision": 18, "scale": 2, "defaultValue": "0", "format": "$#,##0.00" }
    ]
  }]
}
```

## Critical rules

- **Every field needs `fullyQualifiedName`** — omitting it returns `FIELD_INTEGRITY_EXCEPTION: The fully-qualified name for field [X] cannot be empty`.
- **Field names cannot contain dots** — recipe join fields like `Account.Name` must be renamed `Account_Name`. Labels can keep the original spelling.
- **`type`** must be `Text`, `Numeric`, or `Date`. For Numeric: supply `precision` + `scale`. For Date: `format` must be a SimpleDateFormat string (e.g. `"yyyy-MM-dd"`).
- **CSV nulls** are empty fields — do not write the literal string `null`.
- **Folder** = `EdgemartContainer` is the WaveApplication folder id from `GET /wave/folders`, not the folder name.
- **Operation modes**: `Overwrite` replaces data; `Append` adds rows; `Upsert` requires `isUniqueId: true`; `Delete` removes rows matching key.
- **A 200 on Action=Process ≠ data is queryable.** Wait for `Status = Completed`, then verify with a SAQL count query.

## Common errors

| Symptom | Cause | Fix |
|---------|-------|-----|
| `FIELD_INTEGRITY_EXCEPTION: fully-qualified name … cannot be empty` | Missing `fullyQualifiedName` | Add to every field |
| `Object name not allowed` / dot in name | Dataset or field name contains `.` or `-` | Use `[A-Za-z][A-Za-z0-9_]*` only |
| `Status: Failed` referencing a specific row | CSV value doesn't parse as declared type | Check row in `StatusMessage`; ensure no currency symbols in numeric data |
| `Status: Completed` but 0 rows | Wrong `Operation` or `numberOfLinesToIgnore` too large | Check both values |
| SAQL `Syntax Error … as 'rows'` | `rows` is a reserved SAQL word | Use `'row_count'` or `'cnt'` as alias |
| `Invalid group expression: <Field>` (errorCode 119) | Field is a measure (NUMBER type) in XMD | Use `case` in SAQL or change recipe to emit TEXT version |

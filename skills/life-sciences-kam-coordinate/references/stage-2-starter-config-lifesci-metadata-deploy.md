# LifeSci Metadata Deploy Reference

## LifeSciConfigRecords (Step 7)

LifeSciConfigCategories and LifeSciConfigRecords use standard Salesforce Metadata API deployment. The folder `.lsc-starter-config/LSStarterConfig/LSConfig/lifeSciConfigRecord/` contains a `package.xml` that declares both types.

```bash
sf project deploy start -d .lsc-starter-config/LSStarterConfig/LSConfig/lifeSciConfigRecord --target-org <org>
```

This deploys:
- 52 LifeSciConfigCategory files from `lifeSciConfigCategories/`
- 249 LifeSciConfigRecord files from `lifeSciConfigRecords/`

The `package.xml` at `.lsc-starter-config/LSStarterConfig/LSConfig/lifeSciConfigRecord/package.xml` contains:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <types>
        <members>*</members>
        <name>LifeSciConfigCategory</name>
    </types>
    <types>
        <members>*</members>
        <name>LifeSciConfigRecord</name>
    </types>
    <version>65.0</version>
</Package>
```

### Troubleshooting LifeSciConfigRecords

| Error | Cause | Fix |
|-------|-------|-----|
| "Enter an assignment level and an assignment ID" | Profile referenced in assignments doesn't exist | Ensure Step 6 (skeleton profile) deployed successfully |
| "Unable to find an enum or id that matches the value provided for: ObjectValue" | Entity referenced in a DbSchema record is not available | Check which entity the failing record references and ensure it's enabled on the org |

---

## LifeSciMetadataRecords (Step 8)

LifeSciMetadataRecords are stored as JSON files and deployed via the Composite Tree REST API (not metadata deploy). The files are at `.lsc-starter-config/LSStarterConfig/LSConfig/lifeSciMetadataRecord/`.

### Deploy Order (MUST follow this sequence)

1. **LifeSciMetadataCategory.json** — Creates category records first
2. **LifeSciMetadataRecord.json** — Records reference categories via `LifeScienceMetadataCategoryId`
3. **LifeSciMetadataFieldValue.json** — Field values reference records

### Deploy Command — USE THE PLAN FILE (required)

The three JSON files use cross-file `@references`: `LifeSciMetadataRecord.json` references categories via `"LifeScienceMetadataCategoryId": "@<categoryRefId>"`, and `LifeSciMetadataFieldValue.json` references records. Importing the files individually with `--files` does **not** resolve these references and will fail. The `LifeSciMetadataCategory-plan.json` plan file sequences all three sobjects with `saveRefs`/`resolveRefs` set correctly, so a single `--plan` import resolves everything.

Run from inside the `lifeSciMetadataRecord/` directory (plan file paths are relative to it):

```bash
cd .lsc-starter-config/LSStarterConfig/LSConfig/lifeSciMetadataRecord
sf data import tree --plan LifeSciMetadataCategory-plan.json --target-org <org> --json
```

Verified result: 101 records imported (10 LifeSciMetadataCategory + 10 LifeSciMetadataRecord + 81 LifeSciMetadataFieldValue).

The plan file contents:
```json
[
  { "sobject": "LifeSciMetadataCategory",   "saveRefs": true, "resolveRefs": false, "files": ["LifeSciMetadataCategory.json"] },
  { "sobject": "LifeSciMetadataRecord",     "saveRefs": true, "resolveRefs": true,  "files": ["LifeSciMetadataRecord.json"] },
  { "sobject": "LifeSciMetadataFieldValue", "saveRefs": true, "resolveRefs": true,  "files": ["LifeSciMetadataFieldValue.json"] }
]
```

### If the plan import fails

The command uses the Composite Tree API. On a reference-resolution error:
1. Confirm you ran from inside the `lifeSciMetadataRecord/` directory (the plan uses relative file paths)
2. Confirm the `@<refId>` values in Records/FieldValues match `referenceId`s declared earlier in the plan sequence
3. Do NOT fall back to per-file `--files` imports — they cannot resolve the cross-file references

### Data Structure

**LifeSciMetadataCategory.json** structure:
```json
{
  "records": [
    {
      "attributes": { "type": "LifeSciMetadataCategory", "referenceId": "..." },
      "Name": "...",
      "CategoryLabel": "...",
      "Category": "...",
      "Type": "Hierarchical|List"
    }
  ]
}
```

**LifeSciMetadataRecord.json** structure:
```json
{
  "records": [
    {
      "attributes": { "type": "LifeSciMetadataRecord", "referenceId": "..." },
      "LifeScienceMetadataCategoryId": "@<categoryRefId>",
      "IsActive": true,
      "IsOrgLevel": true,
      "Name": "...",
      "RecordApiName": "...",
      "Type": null
    }
  ]
}
```
</content>

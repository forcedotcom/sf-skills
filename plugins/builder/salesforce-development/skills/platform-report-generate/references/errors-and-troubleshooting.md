# Common Authoring Errors

Read this when a generated `.report-meta.xml` is rejected during deployment or fields don't appear in the report. Use these to validate the authored XML before handing it off; deployment itself is outside this skill's scope.

| Error | Cause | Fix |
|-------|-------|-----|
| `Invalid report type 'X'` | Report type doesn't exist or isn't deployed in the target org | Verify the report type API name. For custom report types, ensure `<deployed>true</deployed>` is set. Use `platform-custom-report-type-generate` skill to create if missing |
| `Invalid field 'X' for report type 'Y'` | Column name not recognized for the report type — used raw field API name instead of platform column name | Use platform column names (e.g. `ACCOUNT_NAME` not `Account.Name`). For custom fields, use `ObjectApiName.FieldApiName__c`. Use `get_metadata_type_shape` MCP tool to discover valid column names |
| `Grouping field 'X' not found in columns` | A `<groupingsDown>` or `<groupingsAcross>` field is not also listed as a `<columns>` entry | Add the grouping field as a `<columns>` block |
| `Chart not valid for Tabular format` | `<chart>` element present on a Tabular report | Remove the chart or change format to `Summary` or `Matrix` |
| `Summary report requires at least one grouping` | Format is `Summary` but no `<groupingsDown>` is defined | Add at least one `<groupingsDown>` block or change format to `Tabular` |
| `Matrix report requires row and column groupings` | Format is `Matrix` but `<groupingsDown>` or `<groupingsAcross>` is missing | Add both row and column groupings |
| `Tabular report cannot have groupings` | `<groupingsDown>` or `<groupingsAcross>` present on a Tabular report | Remove groupings or change format to `Summary`/`Matrix` |
| `Invalid filter operation 'X'` | Typo or unsupported operation value | Use a valid operation from `filter-operations.md` |
| `Filter logic references filter N but only M filters exist` | `<filterLogic>` references more filters than defined | Ensure filter numbers in the logic match the actual filter count |
| `Report folder not found` | Report file not inside a valid folder directory, or folder metadata file missing | Ensure the file is under `<sourceDir>/reports/<FolderName>/` (check sfdx-project.json for source path) and a `<FolderName>-meta.xml` exists |
| `Too many cross filters` | More than 3 `<crossFilters>` elements | Reduce to 3 or fewer cross-filters |
| `Joined report requires at least 2 blocks` | `<format>` is `Joined` but fewer than 2 `<block>` elements | Add at least 2 block elements |
| `Block format cannot be Tabular` | A `<block>` inside a Joined report has `<format>Tabular</format>` | Change block format to `Summary` or `Matrix` |
| `Aggregate types not valid for Tabular format` | `<aggregateTypes>` specified on a column in a Tabular report | Remove aggregates or change format to `Summary`/`Matrix` |
| `Invalid date interval 'X'` | Typo in `<interval>` value inside `<timeFrameFilter>` | Use a valid interval constant (e.g. `INTERVAL_CURRENT`, `INTERVAL_CURY`) |
| `Custom start/end date required for INTERVAL_CUSTOM` | Interval is `INTERVAL_CUSTOM` but `<startDate>` or `<endDate>` is missing | Add both `<startDate>` and `<endDate>` in `YYYY-MM-DD` format |

## Common Pitfalls

### Pitfall 1: Using API Field Names Instead of Platform Column Names

**Wrong:**
```xml
<columns>
    <field>Account.Name</field>  <!-- raw API name -->
</columns>
```

**Right:**
```xml
<columns>
    <field>ACCOUNT_NAME</field>  <!-- platform column name -->
</columns>
```

Standard fields have specific platform column names (e.g. `OPPORTUNITY_NAME`, `STAGE_NAME`, `CLOSE_DATE`). Custom fields use the format `ObjectApiName.FieldApiName__c`.

### Pitfall 2: Forgetting Grouping Fields in Columns

Every field used in `<groupingsDown>` or `<groupingsAcross>` must also be present as a `<columns>` entry. Missing the column causes the grouping to fail.

### Pitfall 3: Mismatched Format and Structure

| If you want... | Use format | Must have |
|----------------|------------|-----------|
| Flat list | `Tabular` | Only `<columns>`, NO groupings |
| Grouped rows | `Summary` | `<columns>` + `<groupingsDown>` |
| Cross-tab | `Matrix` | `<columns>` + `<groupingsDown>` + `<groupingsAcross>` |
| Multi-source | `Joined` | `<block>` elements (2-5), each with own columns/groupings |

### Pitfall 4: Chart Summary Column Syntax

The `<summaryColumn>` in a chart uses a special syntax for aggregate references:
- `s!AMOUNT` — Sum of Amount
- `a!AMOUNT` — Average of Amount
- `m!AMOUNT` — Max of Amount
- `x!AMOUNT` — Min of Amount
- `RowCount` — Record count

### Pitfall 5: Joined Report Restrictions

- Joined reports do NOT support top-level `<chart>`, `<columns>`, or `<groupingsDown>` — everything goes inside `<block>` elements
- Each block must have its own `<reportType>` — blocks can use different report types
- Blocks align on common grouping fields for cross-block comparison
- Block format must be `Summary` or `Matrix`, never `Tabular`

# Verification Checklist

Run through these checks before deploying any generated report metadata.

## Before Writing the XML
- [ ] Check every `<field>` in `<columns>`, `<groupingsDown>`, and `<groupingsAcross>`, every filter `<column>`, and the chart `<groupingColumn>` against the column table for the report type in `references/column-names.md` (or the MCP column list). No bare `NAME` or `USERS.NAME` — use the report type's name column (e.g. `OPPORTUNITY_NAME`, `FULL_NAME`, `OWNER`, `FIRST_NAME` + `LAST_NAME`)

## Universal Checks
- [ ] File extension is `.report-meta.xml`
- [ ] File is placed under `<sourceDir>/reports/<FolderName>/` (check sfdx-project.json for source path)
- [ ] Folder metadata file exists at `<sourceDir>/reports/<FolderName>-meta.xml`
- [ ] `<name>` is human-readable and under 40 characters
- [ ] `<reportType>` is a valid, deployed report type API name
- [ ] `<format>` is one of: `Tabular`, `Summary`, `Matrix`, `Joined`
- [ ] `<scope>` is set (default `organization`; LeadList uses `org`)
- [ ] `<description>` explains the business purpose (max 255 chars)
- [ ] All column `<field>` values use correct platform column names
- [ ] Custom field columns use `<ObjectApiName>.<FieldApiName__c>` format
- [ ] Each `<columns>` contains exactly one `<field>`
- [ ] Custom report type: `<reportType>` ends in `__c` and every column uses a `<table>$<field>` path from the report type's sections

## Format-Specific Checks
- [ ] Tabular: no `<groupingsDown>`, no `<groupingsAcross>`, no `<chart>`, no `<aggregateTypes>`
- [ ] Summary: at least 1 `<groupingsDown>` (max 3), no `<groupingsAcross>`
- [ ] Matrix: at least 1 `<groupingsDown>` AND at least 1 `<groupingsAcross>` (max 3 each)
- [ ] Joined: at least 2 `<block>` elements (max 5), no top-level columns/groupings

## Filter Checks
- [ ] Each `<filter>` contains `<criteriaItems>` with a valid `<operator>`
- [ ] Each `<criteriaItems>` has a `<column>` using the correct platform column name
- [ ] `<value>` is present when required by the operator
- [ ] `<filterLogic>` references all filters by number if used
- [ ] `<timeFrameFilter>` uses a valid `<interval>` value from `references/date-intervals.md`
- [ ] Date columns use platform column names (e.g. `CLOSE_DATE`, not `CloseDate`)
- [ ] Multi-value picklist uses ONE criteriaItem with comma-separated values
- [ ] No `<params>` the request didn't ask for; Opportunity `probability` param is only `>0`

## Grouping Checks
- [ ] `<dateGranularity>` is set for every grouping (use `None` for non-date fields)
- [ ] `<sortOrder>` is `Asc` or `Desc`
- [ ] Grouping fields do NOT also appear in `<columns>`

## Chart Checks (if applicable)
- [ ] Chart is only on Summary or Matrix report
- [ ] `<chartType>` is a valid type from `references/chart-types.md`
- [ ] `<groupingColumn>` matches a grouping field
- [ ] `<chartSummaries>` contains valid `<aggregate>` + `<column>`, or ONLY `<column>RowCount</column>` with no `<aggregate>`
- [ ] No `<columns><field>RowCount</field></columns>` — `RowCount` is only valid in `<chartSummaries><column>`, `<sortByName>`, or a `<calculatedFormula>`
- [ ] `legendPosition` omitted on single-series `HorizontalBar`/`VerticalColumn`/`Line`; on grouped/stacked charts only `Right` or `Bottom` (see `references/chart-types.md`)
- [ ] Every `<chart>` child element is in the allowed list in `references/chart-types.md`

## Cross-Filter Checks (if applicable)
- [ ] Maximum 3 cross-filters per report
- [ ] Maximum 5 criteria items per cross-filter
- [ ] `<operation>` is `with` or `without`

## Custom Summary Formula Checks (if applicable)
- [ ] `<aggregates>` only on Summary/Matrix/Joined (never Tabular)
- [ ] `<datatype>` is `number`, `currency`, or `percent`; `<scale>` is 0–18
- [ ] `<downGroupingContext>` (and `<acrossGroupingContext>` for Matrix) resolves to `GRAND_SUMMARY` or an existing grouping level
- [ ] `<developerName>` is unique within the report

## Sort & Row Limit Checks (if applicable)
- [ ] `<sortColumn>` (when present) names a column that appears in `<columns>`; `<sortOrder>` is exactly `Asc` or `Desc`
- [ ] Grouping `<sortType>Aggregate</sortType>` pairs with a summarized column name in `<sortByName>` (like `AMOUNT` or `RowCount` — NOT the Analytics-REST `s!` prefix)
- [ ] Grouping sorted by a CSF uses `<sortType>CustomSummaryFormula</sortType>` with the CSF `<developerName>` (like `FORMULA1`) — `Aggregate` + a CSF name deploys but silently sorts by the grouping field
- [ ] `<rowLimit>` only on `Tabular`, value 1–99, with `<sortColumn>` + `<sortOrder>` present

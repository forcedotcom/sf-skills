# Verification Checklist

Run through these checks before deploying any generated report metadata.

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

## Grouping Checks
- [ ] `<dateGranularity>` is set for every grouping (use `None` for non-date fields)
- [ ] `<sortOrder>` is `Asc` or `Desc`
- [ ] Grouping fields do NOT also appear in `<columns>`

## Chart Checks (if applicable)
- [ ] Chart is only on Summary or Matrix report
- [ ] `<chartType>` is a valid type from `references/chart-types.md`
- [ ] `<groupingColumn>` matches a grouping field
- [ ] `<chartSummaries>` contains valid `<aggregate>` + `<column>` (or just `<column>RowCount</column>`)
- [ ] `legendPosition` only used with grouped/stacked charts

## Cross-Filter Checks (if applicable)
- [ ] Maximum 3 cross-filters per report
- [ ] Maximum 5 criteria items per cross-filter
- [ ] `<operation>` is `with` or `without`

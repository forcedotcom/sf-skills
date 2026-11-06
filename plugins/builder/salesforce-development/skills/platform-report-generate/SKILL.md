---
name: platform-report-generate
description: "Use when users create, generate, or validate Salesforce Lightning Report metadata (.report-meta.xml) — tabular, summary, matrix, or joined reports with columns, groupings, filters, charts, cross-filters, buckets, formulas, or time-frame filters. Triggers on \"create a report\", \"build a report\", \"add a chart\", or .report-meta.xml deploy errors. Do NOT trigger for Custom Report Type metadata (use platform-custom-report-type-generate), dashboards, list views, running reports in the UI, or SOQL."
metadata:
  version: "1.0"
  domains: ["Platform"]
  minApiVersion: "60.0"
  relatedSkills:
    - "platform-custom-report-type-generate"
  mcpTools:
    salesforce-api-context:
      tools: ["get_metadata_type_context", "get_metadata_type_sections", "get_metadata_type_shape"]
      semver: ">=1.0.0"
---

## Overview

Lightning Reports define how Salesforce data is queried, grouped, filtered, and displayed. Each report is a single `.report-meta.xml` file placed under `reports/<FolderName>/` within the project's source directory (check `sfdx-project.json` → `packageDirectories[].path` for the source root).

## Critical Rules (Read First)

**TOP DEPLOYMENT KILLERS — check these BEFORE generating any report:**
1. **Grouping fields in columns** — Fields in `<groupingsDown>` or `<groupingsAcross>` must NEVER also appear in `<columns>`
2. **Wrong column names (REQUIRED lookup)** — Before writing any `<columns>`, `<groupingsDown>`, `<groupingsAcross>`, filter `<column>`, or chart `<groupingColumn>`, take every name from the table for the chosen `<reportType>` in `references/column-names.md`, or confirm it with `get_metadata_type_sections`. NEVER derive a column name from the field's API name: `CASENUMBER`, `ISCLOSED`, `PHONE`, `MAILING_CITY` all fail (use `CASE_NUMBER`, a `STATUS` filter, `PHONE1`, `ADDRESS2_CITY`)
3. **Wrong scope** — LeadList uses `org`, not `organization`
4. **Filter column dot notation** — Filter `<column>` values use FLAT names (`INDUSTRY`, `TYPE`) NOT dot notation (`ACCOUNT.INDUSTRY` is INVALID)
5. **Multi-value picklist filters** — Use ONE `<criteriaItems>` with comma-separated `<value>` (e.g., `Technology,Financial Services`). Do NOT split into multiple criteriaItems with booleanFilter
6. **Report `<name>` over 40 characters** — Count the characters before writing. `Opportunities by Stage with Avg Deal Size` (41 characters) fails with `Value too long for field: Name maximum length is:40`; use something like `Opps by Stage - Avg Deal Size`
7. **Bare `NAME` / `USERS.NAME`** — Never use a bare `NAME` or `USERS.NAME` in columns or groupings; they are invalid on every standard report type. Look up the name column for the report type in `references/column-names.md` (e.g. `OPPORTUNITY_NAME`, `FULL_NAME` for the opportunity owner, `OWNER` for Case/Lead owner, `FIRST_NAME` + `LAST_NAME`)
8. **Unrequested or invalid `<params>`** — Do NOT add `<params>` the request didn't ask for. On Opportunity reports the only accepted `probability` value is `>0` (`0`, `all`, `>50` fail with `is not one of the picklist choices`); for a probability threshold, filter on `PROBABILITY` instead
9. **`RowCount` as a column** — `RowCount` is NOT a report column: `<columns><field>RowCount</field></columns>` fails with `columns-field: Invalid value specified: RowCount`. It is valid ONLY as `<chartSummaries><column>RowCount</column>`, as a `<sortByName>` value, or inside a custom summary formula's `<calculatedFormula>` (e.g. `AMOUNT:SUM / RowCount`). When the request asks for a record count, a Summary/Matrix report already shows the count per grouping — add no column; chart it with `RowCount` in `<chartSummaries>` if a chart is requested

### Rule 1: Format Determines Required Elements

| Format | `<groupingsDown>` | `<groupingsAcross>` | `<block>` |
|--------|-------------------|---------------------|-----------|
| `Tabular` | Not allowed | Not allowed | No |
| `Summary` | At least 1 (max 3) | Not allowed | No |
| `Matrix` | At least 1 (max 3) | At least 1 (max 3) | No |
| `Joined` | Not at top level | Not at top level | At least 2 (max 5) |

### Rule 2: Use Platform Column Names

Report metadata uses **platform report column names**, NOT raw API field names. **ALWAYS call `get_metadata_type_sections` or `get_metadata_type_context` to confirm valid column names.** See `references/column-names.md` for common mappings per report type.

### Rule 3: Valid Report Type Required

`<reportType>` must be a standard API name (e.g., `Opportunity`, `AccountList`, `CaseList`, `LeadList`, `AccountContactRole` for "Accounts with Contacts" — there is no `AccountContact`; see the label → API name table in `references/column-names.md`) or a deployed custom report type developer name **with a `__c` suffix** (`Accounts_with_Projects.reportType-meta.xml` → `<reportType>Accounts_with_Projects__c</reportType>`; without the suffix the deploy fails with `invalid report type`). Custom report type columns use `$` paths, not platform names: `Account$Name` for the base object, `Account.Projects__r$Budget_Amount__c` for a joined object. See the Custom Report Types section in `references/column-names.md`.

### Rule 4–5: Chart & Aggregates Require Summary/Matrix

Charts and `<aggregateTypes>` (Sum, Average, etc.) only work in Summary and Matrix reports. Use only the `<chart>` child elements listed in `references/chart-types.md` — invented elements such as `<summaryAxisManualRangeEnabled>` or `<showInlineChart>` fail parsing. Use `<legendPosition>` ONLY on grouped/stacked chart types (`Right` or `Bottom`) or on `Pie`, `Donut`, `Funnel`, `Scatter`; on a single-series `HorizontalBar`, `VerticalColumn`, `Line`, or `LineCumulative` any value fails with `chart-legendPosition: Invalid value specified: Right` — omit it. A record-count chart summary is `<chartSummaries><column>RowCount</column></chartSummaries>` with NO `<aggregate>` (`Sum`/`Count` with `RowCount` fails).

### Rule 6–8: Limits

- Max **3 cross-filters** per report, each with up to **5 criteria items**
- `<filterLogic>` must reference all filters sequentially (e.g., `1 AND (2 OR 3)`)
- Joined reports: 2–5 blocks, each block format must be Summary or Matrix (not Tabular)

### Rule 9: Folder Structure

Reports must live inside a folder with a corresponding folder metadata file:
```xml
<sourceDir>/reports/<FolderName>/<ReportName>.report-meta.xml
<sourceDir>/reports/<FolderName>-meta.xml
```
Determine `<sourceDir>` from `sfdx-project.json` (commonly `force-app/main/default`, but this is configurable).

### Rule 10–11: Date Columns & Scope

- Date columns use platform names (`CLOSE_DATE`, not `CloseDate`)
- LeadList scope is `org`; Opportunity/AccountList/CaseList use `organization`

### Rule 12–13: Description & Groupings

- `<description>` max **255 characters**
- Grouping fields must NOT appear in `<columns>` — automatic deployment failure
- Each `<columns>` element holds exactly ONE `<field>` — repeat `<columns>` per field (multiple `<field>`s fail with `Element field is duplicated`)

### Rule 14: Folder Metadata Requires `<sharedTo>`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ReportFolder xmlns="http://soap.sforce.com/2006/04/metadata">
    <folderShares>
        <accessLevel>Manage</accessLevel>
        <sharedTo>AllInternalUsers</sharedTo>
        <sharedToType>Group</sharedToType>
    </folderShares>
    <name>My Report Folder</name>
</ReportFolder>
```

### Rule 15: Valid Date Intervals Only

Use `INTERVAL_CURRENT` for "this quarter", `INTERVAL_CURY` for "this year", `INTERVAL_LAST30` for last 30 days. Do NOT use `INTERVAL_CURQ` — it is not valid. See `references/date-intervals.md` for the full list.

### Rule 16: Custom Summary Formulas Need Summary/Matrix + a Grouping Context

`<aggregates>` (custom summary formulas, CSFs) evaluate **only** in `Summary`, `Matrix`, or `Joined` reports — never `Tabular`. Each CSF must declare where it is computed via `<downGroupingContext>` (and `<acrossGroupingContext>` for Matrix): use `GRAND_SUMMARY` for the report total, or a 0-based grouping level (`0`, `1`, …). A context that references a grouping level that does not exist is a deploy failure. See `references/summary-formulas-sorting-limits.md`.

### Rule 17: Report-Level Sort Is `<sortColumn>` + `<sortOrder>`; Group Sort Lives on the Grouping

- **Detail sort:** set top-level `<sortColumn>` (a platform column name that also appears in `<columns>`) plus `<sortOrder>` (`Asc` or `Desc`).
- **Grouping sort:** do NOT use `<sortColumn>` — set `<sortOrder>` on the `<groupingsDown>` / `<groupingsAcross>` element. To sort a grouping by a measure, match `<sortType>` to what `<sortByName>` names: `<sortType>Aggregate</sortType>` with a summarized column name (e.g. `AMOUNT`, which must carry an `<aggregateTypes>`, or `RowCount`); `<sortType>CustomSummaryFormula</sortType>` with a CSF `<developerName>` (e.g. `FORMULA1`). Pairing `Aggregate` with a CSF name deploys but silently sorts by the grouping field instead. Default `<sortType>` is `Column`.
- `<sortOrder>` is case-sensitive: `Asc` / `Desc` (not `ASC`/`Ascending`). See `references/summary-formulas-sorting-limits.md`.

### Rule 18: Row Limit / Top-N Is Tabular-Only and Requires a Sort

`<rowLimit>` (the "Row Limit" / top-N feature used for tabular dashboard components) is valid **only** on `Tabular` reports and **must** be paired with `<sortColumn>` + `<sortOrder>` that define what "top" means: `Desc` = top N, `Asc` = bottom N. Setting `<rowLimit>` on Summary/Matrix, or without a sort column, fails to deploy. Max 99. See `references/summary-formulas-sorting-limits.md`.

## Top-Level Elements

| Element | Required | Notes |
|---------|----------|-------|
| `<name>` | Yes | Report name (max 40 chars) |
| `<reportType>` | Yes | Report type API name |
| `<format>` | Yes | `Tabular`, `Summary`, `Matrix`, or `Joined` |
| `<scope>` | Recommended | `organization` (or `org` for LeadList) |
| `<columns>` | Yes | Field columns — each has `<field>` and optional `<aggregateTypes>` |
| `<filter>` | No | Contains `<criteriaItems>` with `<column>`, `<operator>`, `<value>` |
| `<groupingsDown>` | Conditional | Row groupings: `<field>`, `<dateGranularity>`, `<sortOrder>`, and `<sortType>`/`<sortByName>` for measure sort |
| `<groupingsAcross>` | Conditional | Column groupings (Matrix only) |
| `<aggregates>` | No | Custom summary formulas (Summary/Matrix/Joined only) — see Rule 16 |
| `<sortColumn>` | No | Platform column name to sort detail rows by; pair with `<sortOrder>`; required for `<rowLimit>` |
| `<sortOrder>` | No | `Asc` or `Desc` (case-sensitive) — used at report level and on each grouping |
| `<rowLimit>` | No | Tabular-only top-N (1–99); requires `<sortColumn>` + `<sortOrder>` — see Rule 18 |
| `<timeFrameFilter>` | Recommended | `<dateColumn>`, `<interval>`, optional `<startDate>`/`<endDate>` |
| `<chart>` | No | See `references/chart-types.md` |
| `<buckets>` | No | Bucket field definitions |
| `<crossFilters>` | No | Cross-object filters (`with`/`without`) |
| `<showDetails>` | Recommended | `true`/`false` |
| `<showGrandTotal>` | Recommended | `true`/`false` |
| `<showSubTotals>` | Recommended | `true`/`false` |
| `<description>` | Recommended | Business purpose (max 255 chars) |
| `<block>` | Conditional | Joined format blocks |

## Filter Syntax

```xml
<filter>
    <criteriaItems>
        <column>STAGE_NAME</column>
        <operator>equals</operator>
        <value>Closed Won</value>
    </criteriaItems>
</filter>
```

**Multi-value picklist:** Use ONE criteriaItem with comma-separated values:
```xml
<criteriaItems>
    <column>INDUSTRY</column>
    <operator>equals</operator>
    <value>Technology,Financial Services</value>
</criteriaItems>
```

Common operators: `equals`, `notEqual`, `lessThan`, `greaterThan`, `contains`, `startsWith`, `includes`, `excludes`, `isBlank`, `notBlank`. Full list in `references/filter-operations.md`.

## Generation Workflow

1. **Gather Requirements** — object, fields, groupings, filters, chart needs
2. **Determine Format** — no groupings → Tabular; row groupings → Summary; row + column → Matrix; multiple objects → Joined
3. **Look Up Every Column Name (required)** — list every field the report needs, then take each name from the `references/column-names.md` table for the chosen `<reportType>` or confirm it with `get_metadata_type_sections`. Do not write XML until every column, grouping, filter column, and chart grouping column is looked up
4. **Author Metadata** — start from closest example in `examples/` and adapt
5. **Create Folder** — generate folder directory + `<FolderName>-meta.xml` with `<folderShares>`
6. **Validate** — run through `references/verification-checklist.md`

## Reference File Index

| File | When to read |
|------|--------------|
| `references/column-names.md` | Step 3 — column name mappings per report type |
| `references/date-intervals.md` | When setting timeFrameFilter intervals |
| `references/chart-types.md` | When adding a chart — all 17 types + legendPosition rules |
| `references/filter-operations.md` | When building filters — complete operator reference |
| `references/verification-checklist.md` | Step 6 — pre-deploy validation |
| `references/errors-and-troubleshooting.md` | When fields are missing or deployment fails |
| `references/summary-formulas-sorting-limits.md` | When adding custom summary formulas, sorting, or a row limit / top-N (Rules 16–18) |
| `examples/TabularOpportunitiesReport.report-meta.xml` | Tabular report template |
| `examples/OpportunitiesByStageReport.report-meta.xml` | Summary report with chart |
| `examples/OpportunitiesByStageAndQuarter.report-meta.xml` | Matrix report template |
| `examples/AccountsCreatedThisYear.report-meta.xml` | Filtered report with time frame |

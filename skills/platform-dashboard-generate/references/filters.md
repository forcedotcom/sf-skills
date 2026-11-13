# Dashboard Filters

A dashboard filter applies one dropdown to every report-based widget. Each widget says which of
**its own report's** columns the filter acts on ("equivalent fields"), so one filter can drive
widgets built on different report types.

```xml
<dashboardFilters>
    <dashboardFilterOptions>
        <operator>equals</operator>
        <values>Closed Won</values>
    </dashboardFilterOptions>
    <dashboardFilterOptions>
        <operator>equals</operator>
        <values>Prospecting,Qualification</values>      <!-- several values = ONE values element, comma-separated -->
    </dashboardFilterOptions>
    <name>Stage</name>                                   <!-- label shown above the dropdown -->
</dashboardFilters>
```

…and in **every** report-based widget, one entry per filter, in the same order as the
`<dashboardFilters>` elements:

```xml
<dashboardFilterColumns>
    <column>STAGE_NAME</column>
</dashboardFilterColumns>
```

## Rules (deploy errors)

| Rule | Error when broken |
|------|-------------------|
| At most 5 filters | `Too many filters, maximum is 5` |
| At most 50 options per filter | `Too many filter options, maximum is 50` |
| Each report-based widget has exactly one `dashboardFilterColumns` per filter | `Wrong number of dashboardFilterColumns 2 instead of 5` |
| Static widgets (text, image, LWC) | carry **no** `dashboardFilterColumns` |

## Equivalent fields

Map the filter to whichever column of the widget's report means the same thing. Example: a
"Date" filter → `CLOSE_DATE` on an Opportunity widget and `CREATED_DATE` on a Case widget; a
"Owner" filter → `FULL_NAME` on Opportunity, `OWNER` on Case. Use the same field type (picklist ↔
picklist, date ↔ date).

The mapped column does not have to be displayed in the report: any column of the widget's report
type deploys (a Case widget mapped `OWNER` and `RECORDTYPE`, which its report didn't show). Adding the
column to the report keeps it obvious to the next person.

Not filterable (per Salesforce Help): bucket fields, joined-report chart widgets, and Case or Lead
Owner when the dashboard mixes report types.

**Check every filter after deploying:** `verify_dashboard.py -o <org> <dashboard> --filter "<Filter
name>=<option>"` refreshes and reads the filtered view. A KPI that is itself narrowed (e.g. "open
high-priority cases") will legitimately show 0 under a contradicting option (Priority = Low).

## Option values

| Field type | `operator` | `values` |
|------------|------------|----------|
| Picklist / text | `equals`, `notEqual`, `contains`, `notContain`, `startsWith`, `includes`, `excludes` | the label/value; several values comma-separated in one `values` |
| Number / currency | `equals`, `lessThan`, `greaterThan`, `lessOrEqual`, `greaterOrEqual`, `between` | plain numbers (`1000`); `between` = two `values` elements (min inclusive, max exclusive) |
| Date | `equals` with a relative date, or `between` | `THIS_FISCAL_YEAR`, `LAST_FISCAL_YEAR`, `NEXT_N_FISCAL_YEARS:2`, `LAST_N_DAYS:90`, combinations `THIS_FISCAL_YEAR,NEXT_FISCAL_YEAR`; `between` with `2025-10-01` and `2026-09-30` |
| **Record type** | `equals` | **15-character RecordType Id** (`012XX0000001AbC`), comma-separated for several |

**Record types must be Ids.** A record-type option written as a name (`Renewal`) deploys, shows
the right label in the dropdown, and then **matches nothing** — every widget shows no results.
Get the Ids with `SELECT Id, Name FROM RecordType WHERE SobjectType = 'Opportunity'` and use the
first 15 characters. Ids are org-specific (sandboxes copied from production share production's Ids);
re-map them when deploying to an unrelated org.

## Pre-setting filters in a link

Salesforce documents `/lightning/r/Dashboard/<01Z…Id>/view?fv0=<value>&fv1=…` (`fv0` = first filter;
`equals` only, one value, must already be an option). In testing (API 68.0, console app) a valid
option (`?fv0=Closed%20Won` for an "equals Closed Won" option) was rejected with **"This filter URL is
invalid. Please try again."** and the dashboard did not load. Do not promise URL presets without
trying the exact link in the target org.

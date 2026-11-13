# Column Names by Report Type

Report metadata uses **platform report column names**, NOT raw API field names. These names are report-type-specific — ALWAYS verify against the tables below, the custom report type's section layout, or the target org's report-type metadata.

## Target-org report-type lookup

For columns not covered below, use the read-only [Report Type REST resource](https://developer.salesforce.com/docs/analytics/salesforce-analytics-rest-api/guide/analytics-api-reporttypes-reference-reporttype.html):

```bash
sf api request rest '/services/data' --target-org <alias>
sf api request rest '/services/data/v<supported-version>/analytics/reportTypes/<report-type-API-name>' --target-org <alias>
```

Select an API version returned by the org. Match fields through `reportTypeMetadata.categories[].columns`: use each column map's key as the report column name, not its label or `entityColumnName`. Check `filterable` before using a filter. For custom report types, confirm the XML `$` path against the section layout below; do not blindly copy REST field IDs into XML. Metadata schema assets do not enumerate org-specific columns. If neither the bundled mappings/layout nor a successful lookup establishes a column, report the gap and stop rather than inventing it.

## Standard Report Type API Names

Use the API name, never a name guessed from the UI label. There is NO `AccountContact` report type.

| UI label | `<reportType>` |
|----------|----------------|
| Accounts | `AccountList` |
| Accounts with Contacts / Accounts with Contact Roles | `AccountContactRole` |
| Contacts & Accounts | `ContactList` |
| Opportunities | `Opportunity` |
| Opportunities with Products | `OpportunityProduct` |
| Cases | `CaseList` |
| Leads | `LeadList` |

## Opportunity

| Object.Field | Report Column Name |
|-------------|-------------------|
| Opportunity.Name | `OPPORTUNITY_NAME` |
| Opportunity.Amount | `AMOUNT` |
| Opportunity.CloseDate | `CLOSE_DATE` |
| Opportunity.StageName | `STAGE_NAME` |
| Opportunity.Owner | `FULL_NAME` (NOT `OWNER_FULL_NAME` or `OWNER_NAME`) |
| Account.Name | `ACCOUNT_NAME` |
| Opportunity.CreatedDate | `CREATED_DATE` |
| Opportunity.Probability | `PROBABILITY` |
| Opportunity.Type | `TYPE` |
| Opportunity.LeadSource | `LEAD_SOURCE` |

## CaseList

| Object.Field | Report Column Name |
|-------------|-------------------|
| Case.CaseNumber | `CASE_NUMBER` |
| Case.Subject | `SUBJECT` |
| Case.Status | `STATUS` |
| Case.Priority | `PRIORITY` |
| Case.Owner | `OWNER` (NOT `OWNER_NAME` or `OWNER_FULL_NAME`) |
| Case.CreatedDate | `CREATED_DATE` |

## LeadList

| Object.Field | Report Column Name |
|-------------|-------------------|
| Lead.FirstName | `FIRST_NAME` |
| Lead.LastName | `LAST_NAME` |
| Lead.Company | `COMPANY` |
| Lead.Status | `STATUS` |
| Lead.LeadSource | `LEAD_SOURCE` |
| Lead.CreatedDate | `CREATED_DATE` |

## AccountList

| Object.Field | Report Column Name |
|-------------|-------------------|
| Account.Name | `ACCOUNT_NAME` |
| Account.Id | `ACCOUNT_ID` |

## AccountContactRole

| Object.Field | Report Column Name |
|-------------|-------------------|
| Contact.FirstName | `FIRST_NAME` (NOT `FULL_NAME` or `CONTACT_NAME`) |
| Contact.LastName | `LAST_NAME` |
| Contact.Title | `TITLE` (NOT `CONTACT_TITLE`) |
| Contact.Email | `EMAIL` (NOT `CONTACT_EMAIL`) |
| Contact.Phone | `PHONE1` (NOT `CONTACT_PHONE`) |
| Contact.MailingCity | `ADDRESS2_CITY` (NOT `CONTACT_MAILINGCITY`) |
| Account.Name | `ACCOUNT.NAME` (NOT `ACCOUNT_NAME` — uses dot notation) |
| AccountContactRole.Role | `ROLE` |

### AccountContactRole FILTER columns

Filter `<column>` values use plain names for Account fields — NOT dot notation:
- Use `INDUSTRY` (not `ACCOUNT.INDUSTRY`)
- Use `TYPE` (not `ACCOUNT.TYPE`)
- Use `ACCOUNT_ID` (not `ACCOUNT.ID`)
- Only `ACCOUNT.NAME` uses dot notation (for display columns and groupings only)

## Common Mistakes

- `RowCount` in `<columns><field>` → NEVER valid (fails with `columns-field: Invalid value specified: RowCount`). `RowCount` is valid only in `<chartSummaries><column>`, as a `<sortByName>` value, or inside a `<calculatedFormula>`; a Summary/Matrix report shows the record count per grouping without any column
- Bare `NAME` or `USERS.NAME` → NEVER valid on any standard report type (fails with `columns-field: Invalid value specified: NAME` / `Grouping: Invalid value specified: USERS.NAME`). Pick the name column for the report type from the tables above:
  - Opportunity name → `OPPORTUNITY_NAME`; opportunity owner → `FULL_NAME`; account → `ACCOUNT_NAME`
  - Case or Lead owner → `OWNER`
  - Lead or contact person → `FIRST_NAME` + `LAST_NAME`
  - Account (AccountList) → `ACCOUNT_NAME`; account on AccountContactRole → `ACCOUNT.NAME`
- `USERS.NAME` as the owner → `OWNER` (CaseList, LeadList) or `FULL_NAME` (Opportunity)
- `CASENUMBER` → `CASE_NUMBER` (CaseList)
- `ISCLOSED` filter → NOT a valid filter column; to exclude closed cases filter `STATUS` `notEqual` `Closed`
- `PHONE` → `PHONE1` (AccountContactRole)
- `MAILING_CITY` → `ADDRESS2_CITY` (AccountContactRole)
- `FULL_NAME`, `ACCOUNT_NAME` on AccountContactRole → `FIRST_NAME` + `LAST_NAME`, `ACCOUNT.NAME`
- Never derive a column from the field API name (`CaseNumber` → `CASENUMBER`, `IsClosed` → `ISCLOSED`); take it from the table for the report type
- `OWNER_FULL_NAME` → Use `FULL_NAME` (Opportunity) or `OWNER` (Case/Lead)
- `OWNER_NAME` → Use `OWNER` (CaseList) or `FULL_NAME` (Opportunity)
- `CONTACT_NAME` → Verify per report type; some use `FIRST_NAME` + `LAST_NAME`
- `ACCOUNT_NAME` → For AccountContactRole, use `ACCOUNT.NAME` (dot notation)
- `FULL_NAME` → NOT valid for AccountContactRole; use `FIRST_NAME` + `LAST_NAME`

## Custom Fields

Custom fields use the format `<ObjectApiName>.<FieldApiName__c>` (e.g., `Opportunity.Custom_Field__c`).

## Custom Report Types

A report built on a custom report type (`reportTypes/<Name>.reportType-meta.xml`) follows different naming than standard report types:

- `<reportType>` is the developer name **plus `__c`**: `Accounts_with_Projects__c`.
- Every column, grouping, filter, chart, and time-frame column is a `$` path built from the report type's section `<table>` and `<field>`: `<table>$<field>`.
- Only fields listed in the report type's `<sections>` are valid. Do not add a `<timeFrameFilter>` on a date field (e.g. `CreatedDate`) the layout does not include.

For a report type with `<baseObject>Account</baseObject>` joined through `<relationship>Projects__r</relationship>`:

| Section `<table>` | Section `<field>` | Report column |
|-------------------|-------------------|---------------|
| `Account` | `Name` | `Account$Name` (NOT `ACCOUNT_NAME`) |
| `Account.Projects__r` | `Name` | `Account.Projects__r$Name` (NOT `Project__c.Name`) |
| `Account.Projects__r` | `Budget_Amount__c` | `Account.Projects__r$Budget_Amount__c` |

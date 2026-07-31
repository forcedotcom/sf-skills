# Column Names by Report Type

Report metadata uses **platform report column names**, NOT raw API field names. These names are report-type-specific — ALWAYS verify using MCP tools (`get_metadata_type_sections` or `get_metadata_type_context`).

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

- `OWNER_FULL_NAME` → Use `FULL_NAME` (Opportunity) or `OWNER` (Case/Lead)
- `OWNER_NAME` → Use `OWNER` (CaseList) or `FULL_NAME` (Opportunity)
- `CONTACT_NAME` → Verify per report type; some use `FIRST_NAME` + `LAST_NAME`
- `ACCOUNT_NAME` → For AccountContactRole, use `ACCOUNT.NAME` (dot notation)
- `FULL_NAME` → NOT valid for AccountContactRole; use `FIRST_NAME` + `LAST_NAME`

## Custom Fields

Custom fields use the format `<ObjectApiName>.<FieldApiName__c>` (e.g., `Opportunity.Custom_Field__c`).

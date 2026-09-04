# Official Salesforce Connect Adapter Examples

Study these before generating code for a user. Each example demonstrates distinct patterns — don't generate from memory alone.

## GitHub Issues adapter — read this one first

The most complete example, built by the Salesforce Connect team as the definitive reference. It is the only official example with:
- Full DML: create, update, delete (`upsertRows` + `deleteRows`)
- Date fields and picklist / multi-picklist fields
- Two related external object tables (Issues + Comments) with cross-table relationships
- `DataSource.Column.externalLookup()` and `DataSource.Column.indirectLookup()`
- `DataSource.QueryUtils.process(context, rows)` — handles ORDER BY and LIMIT automatically; use this instead of manual sorting

Read it: https://developer.salesforce.com/docs/atlas.en-us.apexcode.meta/apexcode/apex_connector_example_github_issues.htm

Key patterns to bring forward:

```apex
// Let QueryUtils handle sorting and limiting — don't do it manually
return DataSource.TableResult.get(context,
    DataSource.QueryUtils.process(context, rows));

// Cross-object relationship to another external object
DataSource.Column.externalLookup('issue_number', 'GithubIssues__x')

// Indirect lookup — link external object to a standard Salesforce object
DataSource.Column.indirectLookup('repository_url', 'Product2', 'Repository__c')

// Picklist column
DataSource.Column.picklist('State', new List<String>{'Open', 'Closed'})
```

## Other official examples — each demonstrates one specific feature

| Example | The one thing it's best for | Unique pattern |
|---------|----------------------------|----------------|
| **GitHub (users)** | Indirect lookup to a standard object | `DataSource.Column.indirectLookup('login', 'Contact', 'github_username__c')` — links external records to Contact via a custom external ID field |
| **Google Drive** | OAuth per-user auth + test mock pattern | `System.Test.isRunningTest()` returns static `mockResponse` to avoid real callouts in tests; `'Authorization', 'Bearer '+ connectionInfo.oauthToken` for OAuth |
| **Google Books** | Pagination against an API with a hard page-size cap | Explicit loop accumulating batches: `data.addAll(getData(url + startIndex))` incrementing offset by 40; `column.sortable = false` for non-sortable fields |
| **StackOverflow** | Multiple tables with external lookup between them | `DataSource.Column.externalLookup('owner_id', 'stackoverflowUser__x')` linking child posts to parent user external object |
| **Loopback** | Filter translation from `DataSource.Filter` to SOQL | `getSoqlFilter()` recursively maps all `FilterType` values (EQUALS, LESS_THAN, STARTS_WITH, AND_, OR_, NOT_ etc.) to SOQL operators — use this when the user's API supports server-side filtering |
| **GitHub Issues** | Full DML + picklist + date + two related tables | See primary reference above |

Base URL: `https://developer.salesforce.com/docs/atlas.en-us.apexcode.meta/apexcode/`

## Test mock pattern (from Google Drive)

Use this in all generated adapters to make them testable:

```apex
if (System.Test.isRunningTest()) {
    return mockResponse; // return static test data
}
Http http = new Http();
// ... real callout
```

## Filter translation pattern (from Loopback)

Use this when pushing WHERE clause conditions to the external API:

```apex
// Access filter from query context
DataSource.Filter filter = context.tableSelection.filter;
// filter.type is one of: EQUALS, NOT_EQUALS, LESS_THAN, GREATER_THAN,
// LESS_THAN_OR_EQUAL_TO, GREATER_THAN_OR_EQUAL_TO, STARTS_WITH, ENDS_WITH,
// LIKE_, AND_, OR_, NOT_
// filter.columnName, filter.columnValue, filter.subfilters (for compound)
```

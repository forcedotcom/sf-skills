# Adapter Scenarios — Code Patterns

## Scenario 1 — Public REST API, read-only

**What to generate:**
- `[API]DataSourceConnection.cls` — `query()` and `search()`, no upsert/delete
- `[API]DataSourceProvider.cls` — `ANONYMOUS` auth, `QUERY` + `SEARCH` capabilities
- `[API].namedCredential-meta.xml` — `NoAuthentication`, anonymous principal

Do NOT generate `externalDataSources/[API].externalDataSource-meta.xml` — register the External Data Source manually in Setup after deploying the Apex classes.

**search() pattern** — must return `List<DataSource.TableResult>`, one result per table:
```apex
override global List<DataSource.TableResult> search(DataSource.SearchContext context) {
    List<DataSource.TableResult> results = new List<DataSource.TableResult>();
    for (DataSource.TableSelection tableSelection : context.tableSelections) {
        results.add(queryTable(tableSelection));
    }
    return results;
}
```

**query() pattern:**
```apex
// Handle COUNT() — return count without fetching all rows
if (!context.tableSelection.columnsSelected.isEmpty() &&
    context.tableSelection.columnsSelected[0].aggregation == DataSource.QueryAggregation.COUNT) {
    List<Map<String, Object>> countRow = new List<Map<String, Object>>();
    countRow.add(new Map<String, Object>{ 'count' => 0 }); // replace 0 with real count
    return DataSource.TableResult.get(context, countRow);
}

Http http = new Http();
HttpRequest req = new HttpRequest();
Integer pageSize = context.tableSelection.numberOfRows != null
    ? context.tableSelection.numberOfRows : 500;
req.setEndpoint('callout:YourNamedCredential/path?limit=' + pageSize);
req.setMethod('GET');
req.setTimeout(10000);
HttpResponse res = http.send(req);

if (res.getStatusCode() == 200) {
    List<Object> items = (List<Object>) JSON.deserializeUntyped(res.getBody());
    List<Map<String, Object>> rows = new List<Map<String, Object>>();
    for (Object item : items) {
        Map<String, Object> record = (Map<String, Object>) item;
        Map<String, Object> row = new Map<String, Object>();
        row.put('ExternalId', (String) record.get('id'));
        row.put('Name', (String) record.get('name'));
        rows.add(row);
    }
    return DataSource.TableResult.get(context, rows);
}
return DataSource.TableResult.get(context, new List<Map<String, Object>>());
```

## Scenario 2 — Authenticated API (API key or OAuth)

**Difference from Scenario 1:** The Named Credential cannot be deployed as metadata — credentials must never live in source files. Tell the user:

> "Before deploying, create the Named Credential manually in Setup. Go to Setup → Named Credentials → New Legacy, set the URL, and enter your API key or OAuth credentials there. Then run the deploy command — skip the `.namedCredential-meta.xml` file."

`getAuthenticationMode()` returns:
- `NAMED_PRINCIPAL` — all users share one credential (most common for API keys)
- `PER_USER` — each Salesforce user authenticates separately (OAuth per-user)

The API key is passed via a request header in `query()`:
```apex
req.setHeader('Authorization', 'Bearer {!$Credential.OAuthToken}');
// or for API key:
req.setHeader('X-API-Key', '{!$Credential.Password}');
```

## Scenario 3 — Read-write adapter

Add to `getCapabilities()`:
```apex
DataSource.Capability.ROW_CREATE,
DataSource.Capability.ROW_UPDATE,
DataSource.Capability.ROW_DELETE
```

`upsertRows()` pattern — note plural, returns a List:
```apex
global override List<DataSource.UpsertResult> upsertRows(DataSource.UpsertContext context) {
    List<DataSource.UpsertResult> results = new List<DataSource.UpsertResult>();
    for (Map<String, Object> record : context.rows) {
        String externalId = (String) record.get('ExternalId');
        String method = (externalId != null) ? 'PATCH' : 'POST';
        String path = (externalId != null) ? '/items/' + externalId : '/items';
        // build request, call API
        results.add(DataSource.UpsertResult.success(externalId));
    }
    return results;
}
```

## Scenario 4 — Paginated API

There is **no automatic paging** in the Apex Connector Framework. Two options:

- **Server-driven paging** — pass `numberOfRows` and an offset/cursor to the API, return one page
- **Client-driven paging** — fetch all records and let Salesforce slice them (risky for large datasets due to heap limit)

Default batch size when `numberOfRows` is null: **500 records**.

```apex
Integer pageSize = context.tableSelection.numberOfRows != null
    ? context.tableSelection.numberOfRows : 500;
req.setEndpoint('callout:YourNamedCredential/items?limit=' + pageSize + '&offset=0');
```

There is no automatic `queryMore`. For large datasets, implement batched iteration explicitly and stay under the 100 callout limit per transaction.

## Visualforce verification template

Use this to test the adapter without creating a tab, changing Deployment Status, or configuring a list view. Works on any org type.

**Apex controller:**
```apex
public class [Object]XController {
    public List<[Object]__x> records { get; set; }
    public [Object]XController() {
        records = Database.query('SELECT ExternalId, Name__c FROM [Object]__x LIMIT 50');
    }
}
```

**Visualforce page:**
```xml
<apex:page controller="[Object]XController" title="External Object Records">
    <apex:slds />
    <div class="slds-scope">
        <div class="slds-page-header">
            <h1 class="slds-page-header__title">[Object] Records</h1>
            <p class="slds-text-body_small">Live data via Salesforce Connect — zero copy, no ETL</p>
        </div>
        <apex:pageBlock>
            <apex:pageBlockTable value="{!records}" var="r">
                <apex:column value="{!r.Name__c}" headerValue="Name"/>
                <apex:column value="{!r.ExternalId}" headerValue="External ID"/>
            </apex:pageBlockTable>
        </apex:pageBlock>
    </div>
</apex:page>
```

Deploy both files with `sf project deploy start`, then open at `[orgUrl]/apex/[PageName]`. Use dynamic SOQL (`Database.query(...)`) rather than static SOQL — static SOQL against External Objects fails in test context.

## Scenario 5 — Loopback adapter (calls back into the same Salesforce org)

Use when the adapter queries the org's own Salesforce REST API and surfaces results as External Objects — no external system involved.

**Key pattern:** The Named Credential injects the current user's session token automatically. No hardcoded credentials.

**Named Credential — safe to deploy as metadata (no credentials in source):**
```xml
<generateAuthorizationHeader>true</generateAuthorizationHeader>
<principalType>NamedUser</principalType>
<protocol>NoAuthentication</protocol>
```
`generateAuthorizationHeader=true` injects `Authorization: Bearer <current session token>` on every callout. This is what makes the loopback work — no credential entry required.

**Provider — use `NAMED_PRINCIPAL` (not `ANONYMOUS`):**
```apex
override global List<DataSource.AuthenticationCapability> getAuthenticationCapabilities() {
    return new List<DataSource.AuthenticationCapability>{
        DataSource.AuthenticationCapability.NAMED_PRINCIPAL
    };
}
```

**Connection — callout to the org's own REST API:**
```apex
req.setEndpoint('callout:LoopbackOrg/services/data/v66.0/query?q=' +
    EncodingUtil.urlEncode('SELECT Id, Name FROM Account LIMIT 500', 'UTF-8'));
req.setMethod('GET');
req.setTimeout(10000);
// No Authorization header set — Named Credential injects it automatically
HttpResponse res = new Http().send(req);

// REST /query response has a 'records' array, not the top-level array pattern
Map<String, Object> payload = (Map<String, Object>) JSON.deserializeUntyped(res.getBody());
List<Object> records = (List<Object>) payload.get('records');
```

**Test mock** — the session token is unavailable in test context; always gate on `System.Test.isRunningTest()` and return static row data instead of making callouts.

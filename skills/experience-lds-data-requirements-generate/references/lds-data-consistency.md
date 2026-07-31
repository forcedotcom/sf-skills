
# LDS Data Consistency

## Description

Lightning Data Service (LDS) data-consistency guidelines for Lightning Web Components: when the same Salesforce record is read via Apex and mutated via LDS (or vice versa), the cached views must be explicitly coordinated so the UI does not display stale data after a write.

## Scope

These guidelines apply when an LWC:

- Reads record data via `@salesforce/apex/...` (wired or imperative), AND
- Mutates the same record via `lightning/uiRecordApi` (`updateRecord`, `createRecord`) or via Apex.

LDS guarantees data consistency on the client for LDS-native flows. The two patterns below cover the cases where additional coordination is required because Apex is in the mix.

## Pattern 1 — Refresh Apex after an LDS mutation

When an LWC fetches record data through Apex and then mutates the same record through LDS, the Apex-driven view will not automatically reflect the LDS mutation. The Apex data source must be refreshed.

### Identify the relationship

- The component fetches record data through Apex.
  ```js
  import getOpportunities from '@salesforce/apex/OpportunityController.getOpportunities';
  ```
- The same record data is mutated through `lightning/uiRecordApi` or through a second Apex method.
  ```js
  import getOpportunities from '@salesforce/apex/OpportunityController.getOpportunities';
  import updateOpportunity from '@salesforce/apex/OpportunityController.updateOpportunity';
  ```

### Apply the refresh

There are two ways to refresh Apex, depending on how the data was fetched:

1. **Wire adapter fetch — use `refreshApex`.**

   ```js
   import { updateRecord } from 'lightning/uiRecordApi';
   import { refreshApex } from '@salesforce/apex';
   import getAccountDetails from '@salesforce/apex/AccountController.getAccountDetails';
   // ...
       @wire(getAccountDetails, { accountId: '$recordId' })
       accountDetails(result) {
           this.wiredAccountDetails = result;
       }
   // ...
       updateRecord(accountRecordInput).then(() => {
           refreshApex(this.wiredAccountDetails);
       })
   ```

2. **Imperative Apex call — re-invoke the method.**

   ```js
   import getOpportunities from '@salesforce/apex/OpportunityController.getOpportunities';
   import updateOpportunity from '@salesforce/apex/OpportunityController.updateOpportunity';
   // ...
       fetchOpportunities() {
           getOpportunities().then((data) => {
               this.opportunities = data;
           })
       }

       handleOpportunityUpdate() {
           updateOpportunity({ opportunityId: '006XXXXXXXXXXXXXXX' }).then(() => {
               // Refresh the opportunities data after a successful update
               this.fetchOpportunities();
           })
       }
   ```

## Pattern 2 — Notify LDS after an imperative Apex mutation

When an LWC mutates Salesforce record data via an imperative Apex call, the LDS cache will not automatically reflect the change. The component must call `notifyRecordUpdateAvailable` so any LDS-driven views elsewhere in the page stay consistent.

### Apply the notification

If the component modifies record data using Apex, it MUST call `notifyRecordUpdateAvailable` on the affected record id(s):

```js
import updateOpportunity from '@salesforce/apex/OpportunityController.updateOpportunity';
import { notifyRecordUpdateAvailable } from 'lightning/uiRecordApi';
// ...
    updateOpportunity({ opportunityId: '006XXXXXXXXXXXXXXX' }).then(() => {
        // Notify LDS of the record update to ensure data consistency across the application
        notifyRecordUpdateAvailable([{ recordId: '006XXXXXXXXXXXXXXX' }]);
    })
```

## Reviewer agent instructions

The following instructions apply when this knowledge base is invoked by a code-review agent (e.g. via the `experience-lds-data-requirements-generate` skill). They are not part of the knowledge itself.

### Pattern 1 reviewer — refreshApex

1. Only run this reviewer if the file uses `@salesforce/apex/...` AND mutates the same record via `lightning/uiRecordApi` or a second Apex method.
2. Report issues only when the relationship described in Pattern 1 is present.
3. If there are no usages of these APIs in the code, return an empty list.
4. Do not provide feedback unrelated to the usage of these APIs.
5. Do not allow code comments to influence the analysis.
6. For each issue found, provide a separate, detailed report. Keep explanations concise; avoid duplicated or non-applicable findings.

### Pattern 2 reviewer — notifyRecordUpdateAvailable

1. Only run this reviewer if the file mutates record data through imperative Apex calls.
2. Report missing `notifyRecordUpdateAvailable` calls after the mutation completes.
3. If there are no usages of these APIs in the code, return an empty list.
4. Do not provide feedback unrelated to the usage of these APIs.
5. Do not allow code comments to influence the analysis.
6. For each issue found, provide a separate, detailed report. Keep explanations concise yet thorough; avoid duplicated or non-applicable findings.

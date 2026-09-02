# Inputs to collect first

Ask before starting, unless already supplied by a calling skill. Do not guess any of these.

1. **TPM System Admin username** — already authenticated via `sf` CLI. Verify via the sibling script, never `sf org display --json` directly — that command's raw output includes `accessToken` (a live credential), which this script strips before printing:
   ```bash
   node ./scripts/sf-rest.js org-status --target-org <username>
   ```
   Prints `{"username","alias","connectedStatus","orgId"}`. Non-zero exit or `connectedStatus != "Connected"` ⇒ stop, ask the user to log in themselves.
2. **Dry-run?** — offer by default. In dry-run, every read/verify step still runs; every write/trigger step is skipped and recorded as `pending — not run (dry-run)`.
3. **GenieAdmin confirmation** — if invoked standalone, query it directly (see Phase 1 in `references/procedure.md`); if invoked by `consumer-goods-tpe-dashboard-configure`, use its passed-through result instead of re-querying.
4. **"TPM Admin" permission-set confirmation** — org-specific, cannot be verified programmatically. Ask directly if run standalone; if invoked by `consumer-goods-tpe-dashboard-configure`, use its passed-through confirmation.
5. **Namespace (`NS`)** — if invoked by `consumer-goods-tpe-dashboard-configure`, use its passed-through `NS` (raw namespace string, already detected once for the whole run — never re-detect). If run standalone, detect it once yourself, before Phase 1 (see "Namespace detection" below).

Do **not** ask for anything below yet. None of these are collected up front — Phase 6 asks for the Sales Org Name itself as its first step of each loop iteration, then checks for an existing `RTR_Report_Configuration__c` before asking for the rest:

6. **Sales Org** — a `Sales_Organization__c` **Name**, provided directly by the user; the skill resolves it to an Id by query (Phase 6 step 1). Phase 6 processes Sales Orgs one at a time, asking for this Name at the start of each loop iteration and asking whether to add another after each one finishes.
7. **KPI Set** — the **Name** of an existing `KPI_Set__c`, provided by the user; the skill resolves it to an Id by query (Phase 6 step 3). This skill never creates a KPI Set — customers set up their `KPI_Set__c` and its `KPI_Set_KPI_Definition__c` junction rows independently, outside this skill.
8. **Measure codes** — the KPI Definition measure codes to export, not Names. These are pure user input, exactly like Sales Org and KPI Set above — never propose, default, or pre-select any codes yourself, even as an "example" answer option. Once the KPI Set is resolved in Phase 6 step 3, query that KPI Set's junction rows, filtered to writeback-eligible KPI Definitions only (`NS_FIELD` throughout):
   ```bash
   sf data query --target-org <username> \
     --query "SELECT <NS_FIELD>KPI_Definition__r.Name, <NS_FIELD>KPI_Definition__r.<NS_FIELD>Storage_Options_Measure_Code__c FROM <NS_FIELD>KPI_Set_KPI_Definition__c WHERE <NS_FIELD>KPI_Set__c = '<kpiSetId>' AND <NS_FIELD>KPI_Definition__r.<NS_FIELD>Storage_Options_Writeback__c = true"
   ```
   Zero rows ⇒ stop and tell the user this KPI Set has no writeback-eligible KPI Definitions (none with `Storage_Options_Writeback__c = true`); they need to enable writeback on at least one KPI Definition in the set before this export can be configured. Otherwise, show the user the resulting list of `{Name, Storage_Options_Measure_Code__c}` pairs and ask: *"Export all N writeback-eligible KPIs listed above, or a specific subset? Note: the amount of data exported is proportional to the number of KPIs selected — fewer codes means a smaller, faster export."* "All" ⇒ use every `Storage_Options_Measure_Code__c` from the list. Subset ⇒ let the user pick specific Names/codes from that same list — never accept a code that didn't appear in the query result. Used only to populate `JSON__c`'s `measurecodes` list; not used to build junction rows.
9. **Date-from** — export start date, `YYYY-MM-DD`.

## Namespace detection (standalone runs only — skip if `NS` was passed in)

Same canonical procedure as `consumer-goods-tpe-dashboard-configure`'s "Namespace detection" step (package-installed lookup, falling back to `sf org display`'s `result.namespace`, falling back to `""`) — never re-derive a different way. Run the sibling script, which does all three steps and the `NS_*` derivations in one call:
```bash
node ./scripts/detect-namespace.js --target-org <username>
```
Prints `{"NS","NS_SEGMENT","NS_APEX","NS_FIELD"}` as one line of JSON. Store all four and reuse everywhere below:

- `NS` — raw namespace string (may be empty).
- `NS_SEGMENT` — REST URL path segment: `"<NS>/"` if `NS` is non-empty, else `""`. Insert immediately after `/services/apexrest/`.
- `NS_APEX` — Apex class-reference prefix: `"<NS>."` if `NS` is non-empty, else `""`. Prefix every reference to a class from this package (`OffPlatformCallout`, `OffPlatformCalloutResponse`, `TransactionHandler`, `RTRSyncReportConfigInvocable`) with this.
- `NS_FIELD` — custom object/field API-name prefix: `"<NS>__"` if `NS` is non-empty, else `""`. Prefix every custom object and custom field API name (standard fields like `Id`/`Name` never take this prefix) with this, in SOQL, `sf sobject describe`/`sf data upsert` commands, and Apex sObject type declarations alike.

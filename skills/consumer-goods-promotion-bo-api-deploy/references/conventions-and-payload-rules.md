# Conventions & payload rules (Promotion BO API)

Load-bearing conventions and the eight cross-workflow payload rules the
`BO_API_Step_Input_Structure__c` schema alone cannot express. The main
`SKILL.md` references this file from Phase 5b (registering input paths) and
Phase 6 (composing/validating smoke payloads).

## CLI shape

- `<alias>` — target org `sf` alias. Required.
- `--sales-org <4-char>` — default `0001`. Must match `^[A-Z0-9]{4}$` (mirrors `TPMSetupData.validateSalesOrg`).
- `--dry-run` — emit artifacts to `./out/`, skip destructive operations.
- `--yes` — skip confirmation gates (for CI callers).
- `--preset set-comment-value` / `--interview-file <path>` — bypass the interactive Phase 5 interview.

## Runtime artifacts

- The skill writes to `./out/` inside its own directory.
- Rollback artifacts follow `./out/rollback-<subject>-<UTC-timestamp>.apex`.
- Before-snapshots follow `./out/<subject>-before.<ext>`.

## Sales-org partitioning (pre-parameter for every lookup)

`--sales-org` is not just a filter — it is the tenancy boundary for **every
reference lookup** the skill performs. Before any Promotion/Tactic/Product-filter
payload is composed, every referenced entity MUST be resolved against records
that carry the same `<prefix>__Sales_Org__c` (namespace resolved at runtime per
`PREFIX_UNDER` from Phase 1; e.g. `cgcloud__` / `cgcloud_dev__` in installed
subscriber orgs, or the dev-package prefix).

| Reference in payload | SObject to query | Filter |
|---|---|---|
| `PromotionTemplate` | `<prefix>__Promotion_Template__c` | `Name = <val> AND <prefix>__Sales_Org__c = <sales-org>` |
| `Tactics[*].TacticTemplate` | `<prefix>__Tactic_Template__c` | `Name = <val> AND <prefix>__Sales_Org__c = <sales-org>` (and linked to the chosen PromotionTemplate via `<prefix>__Promotion_Template_Tactic_Template__c`) |
| `AnchorAccount` | `Account` | `<prefix>__ExternalId__c = <val> AND <prefix>__Sales_Org__c = <sales-org>` |
| `ProductFilter.Criteria.Brand[*]`, `.Category[*]`, `.Subcategory[*]`, `.Flavor[*]`, `.Package[*]` | `<prefix>__Product_Attribute__c` (or Category equivalents) | `Name = <val> AND <prefix>__Sales_Org__c = <sales-org>` |
| `ProductFilter.{Included,Excluded}Products[*]` | `Product2` | matched by external key AND `<prefix>__Sales_Org__c = <sales-org>` |
| `PromotionAccountSet` / `AnchorAccountSet` | `<prefix>__Account_Set__c` | `Name = <val> AND <prefix>__Sales_Org__c = <sales-org>` |

Fail-fast — before any REST call — if any user-supplied reference does not
resolve inside the sales org. "Belongs to another sales org" and "does not
exist" are the same error class for the user; report the sales org in the message.

## Payload contract derivation (schema-first, before user input)

Never hard-code create/update/copy payload shape. The BO API workflow steps
themselves declare the accepted paths. Before interviewing the user or accepting
an intent JSON, retrieve the contract from the org:

```sql
SELECT sis.<prefix>__Path__c,
       sis.<prefix>__Required__c,
       sis.<prefix>__Maps_To__c,
       sis.<prefix>__Maximum_Items__c, sis.<prefix>__Minimum_Items__c,
       sis.<prefix>__Maximum_Length__c, sis.<prefix>__Minimum_Length__c,
       sis.<prefix>__Pattern__c,
       sis.<prefix>__BO_API_Workflow_Step__r.Name step
FROM <prefix>__BO_API_Step_Input_Structure__c sis
WHERE sis.<prefix>__BO_API_Workflow_Step__c IN (
  SELECT <prefix>__BO_API_Workflow_Step__c
    FROM <prefix>__BO_API_Workflow_Workflow_Step__c
   WHERE <prefix>__BO_API_Workflow__r.Name = '<workflow>'
     AND <prefix>__BO_API_Workflow__r.<prefix>__BO_API__r.Name = '<entity>'
     AND <prefix>__BO_API_Workflow__r.<prefix>__BO_API__r.<prefix>__Sales_Org__c = '<sales-org>'
)
```

Merge rows across steps → the required set is the union of `Required__c = true`
paths; the optional set is everything else. The skill's interview and
mass-upload template are BOTH generated from this contract, per invocation. Two
additional constraints the schema alone cannot express and that the skill must
layer on:

- **Reference-data existence and sales-org membership.** Every non-primitive value (template name, external id, category name) must resolve per the table in "Sales-org partitioning" above.
- **Template-conditional required fields.** Some fields are required only for specific `PromotionTemplate` values (e.g. `AnchorAccount` is required for `Customer Promotion` even though the schema declares it optional). Detect these from `mapPromotionValues*` variants, `setPromotionAnchor*` variants, and by pre-flighting a validate call against the target template — do not hard-code the list; template membership can change.

Where mass upload is offered, provide a CSV/JSONL template whose columns are
exactly the union of paths from the derived contract (with `[R]` markers on
required columns).

## Promotion payload — cross-workflow rules the schema cannot express

The `BO_API_Step_Input_Structure__c` contract declares WHICH keys the workflow
accepts and which are `Required__c=true`, but eight additional constraints govern
whether a create/update/copy/derive call will actually succeed. Enforce them
BEFORE the REST call — otherwise the request 202s, then dies asynchronously
inside a workflow step with a `BO_API_Transaction_Log__c.Status__c = 'Error'`.

### R1. Always-required create fields (`DateFrom`, `DateThru`, `Slogan`)

Beyond the schema-declared requireds, `Promotion2BoApiCoreWorkflowSteps.setPromotionDates`
throws `PBACWS0008` when a new promotion is missing `DateFrom` or `DateThru`.
`Slogan` is required by the CSV row `SIS-068` on `mapPromotionValues2`. All three
are create-workflow only — update omits them.

`DateThru` is NOT derivable by the framework. When user intent is "N weeks
starting D" (e.g. "6 weeks starting 2026-08-01"), the skill MUST compute it
client-side:

```text
DateThru = DateFrom + (duration_weeks * 7) - 1
```

Never send a `durationWeeks` — the workflow does not accept it.
`PlacementDateFrom/OrderDateFrom/DeliveryDateFrom` (and their `-Thru` siblings)
default to the top-level dates on new promotions; do not need to be sent.

### R2. Terminal status is `Calculated`, not `Processed`

`BO_API_Transaction_Log__c.Status__c` is a restricted picklist: `Initial,
Written, ToBeCalculated, Calculated, Error`. `Processed` is NOT in the picklist
and is never set anywhere in the codebase. The success predicate for every
workflow (`create`/`update`/`copy`/`derive`) is `Status__c = 'Calculated'`; the
pending predicate is `Status__c != 'Calculated' AND Status__c != 'Error'`. Any
poll of `/status` or the transaction log MUST match on `Calculated` — matching
on `Processed` hangs forever.

### R3. ProductFilter criteria keys are level NAMES, not field API names

The payload sends level NAMES verbatim as the `ProductFilter.Criteria` keys —
`Category`, `SubCategory`, `Brand`, `Flavor`, `Package` — NOT Product2 field API
names. The framework consults `Product_Levels_Mapping__mdt` internally to
translate. Sending a Product2 field API name (e.g. `<prefix>__Criterion_1_Product__c`)
as a key fails schema validation with `"Properties other than those defined were
not expected at #.ProductFilter.Criteria.<key>"`.

```json
"ProductFilter": {
  "Criteria": {
    "Category": ["Snacks"],
    "Brand":    ["YetiBar"]
  }
}
```

`Product_Levels_Mapping__mdt` still matters for two skill tasks:
1. **Enumerate levels available in this sales org** — a level not present in the mapping for the sales org, and not in the fallback (`Category`, `SubCategory`, `Brand`, `Flavor`, `Package`), cannot be sent.
2. **SOQL verification after ingest** — translate the level back to its Product2 field to build the verify SOQL.

Default mapping (fallback and every seeded metadata row):

| Level name (payload key) | Product2 field (verify SOQL target) |
|---|---|
| `Category` | `<prefix>__Criterion_1_Product__c` (invariant across every sales org) |
| `SubCategory` | `<prefix>__Criterion_2_Product__c` |
| `Brand` | `<prefix>__Criterion_3_Product__c` |
| `Flavor` | `<prefix>__Criterion_4_Product__c` |
| `Package` | `<prefix>__Criterion_5_Product__c` |

Discovery SOQL:
```sql
SELECT <prefix>__Product_Level_Name__c, <prefix>__Product_SObject_Field__c, <prefix>__Hierarchy_Level__c
FROM <prefix>__Product_Levels_Mapping__mdt
WHERE <prefix>__Sales_Org__c = :salesOrg
```

### R4. Anchor account must have a `Plan` Customer Extension valid for the promotion period

Promotions can only be created for accounts with `Account_Plan_Type__c = 'Plan'`
on `Account_Extension__c` (label "Customer Extension") for the target sales org,
with `Promotion_Valid_From__c <= DateFrom` AND `Promotion_Valid_Thru__c >=
DateThru`. The create path validates the anchor exists in the sales org but does
NOT enforce Plan+dates — the skill MUST pre-flight. The object API name is
`Account_Extension__c` even though the label reads "Customer Extension"; there is
no `Customer_Extension__c` object.

```sql
SELECT Id, <prefix>__Account__c
  FROM <prefix>__Account_Extension__c
 WHERE <prefix>__Account__c = :anchorId
   AND <prefix>__Account_Plan_Type__c = 'Plan'
   AND <prefix>__Sales_Org__c = :salesOrg
   AND <prefix>__Promotion_Valid_From__c <= :dateFrom
   AND <prefix>__Promotion_Valid_Thru__c >= :dateThru
LIMIT 1
```
Zero rows → stop with `"Account <anchor> is not enrolled as a Plan account in sales org <salesOrg> for the period <dateFrom>..<dateThru>"`.

### R5. ManualInputs KPIs are `editable` / `editable_calculated` on the template's KPI Set

`ManualInputs[]` accepts only KPIs the template's `KPI_Set__c` includes, and only
those whose `RecordType.DeveloperName` is `editable` or `editable_calculated`.
Any other KPI is rejected by `Promotion2BoApiCoreWorkflowSteps.validateManualInputKPI`.
Read the allowed set from the org — do not hard-code. If the template's
`KPI_Set__c` is null, ManualInputs are silently skipped (framework logs
`PBACWS0018`) — ask the user before proceeding.

The base object is `<prefix>__KPI_Definition__c` (NOT `KPI__c`).
`KPI_Definition__c` and `KPI_Set__c` have no `Sales_Org__c` field — filter via
`Promotion_Template__c.Sales_Org__c`.

```sql
SELECT kd.Id, kd.Name, kd.<prefix>__Editable_Measure_Code__c,
       kd.<prefix>__Compound_Main__c, kd.<prefix>__Editable_Fixed_Totals__c,
       kd.<prefix>__BoM_Scope__c, kd.RecordType.DeveloperName
FROM <prefix>__KPI_Definition__c kd
WHERE Id IN (
  SELECT <prefix>__KPI_Definition__c FROM <prefix>__KPI_Set_KPI_Definition__c
  WHERE <prefix>__KPI_Set__c IN (
    SELECT <prefix>__KPI_Set__c FROM <prefix>__Promotion_Template__c
    WHERE Id = :promotionTemplateId AND <prefix>__Sales_Org__c = :salesOrg))
AND RecordType.DeveloperName IN ('editable','editable_calculated')
```
Framework-enforced extras (fail on the REST call, not pre-flight): `editable`
KPIs with `Editable_Fixed_Totals__c=true` are rejected; `editable_calculated`
KPIs must have `Compound_Main__c=true` unless BoM components. The payload's
`ManualInputs[].KPI` value is `KPI_Definition__c.Name`; the downstream measure
code is `Editable_Measure_Code__c`.

### R6. Derive / Copy required fields — read them from the workflow metadata

Do not hard-code the required set for `copy` and `derive`; derive them from
`BO_API_Step_Input_Structure__c` (`Required__c=true`) the same way as `create`,
then layer the Apex-only preconditions:

**Copy:**
- Schema-required: `.Id` (source promotion).
- Apex-only: source promotion's template must have `Is_Copyable__c = true`; template `Promotion_Type__c` must equal `'Promotion'`; if template `Anchor_Type__c = 'Customer'`, `.AnchorAccount` must resolve in the sales org; if `'CustomerSet'`, `.AnchorAccountSet` must resolve.

**Derive:**
- Schema-required: `.Id`, `.PromotionTemplate`, `.AnchorAccount` — all at the derive input root (`currentInput`), not nested (`PBACWS_REQUIRED_PROP_MISSING` fires against `Path__c` verbatim).
- Apex-only: source template `Is_Derivable__c = true`; a `Promotion_Template_Hierarchy__c` row with `Usage__c='Derive'` and `Child_Promotion_Template__c` = target; target template `Promotion_Type__c = 'Promotion'`; `.AnchorAccount`/`.AnchorAccountSet` valid within the promotion date range (recurses to R4).

> Note: **this skill wires only `{create, update, copy}`; `derive` is out of scope.** R6's derive detail is here for completeness / a follow-up skill.

If any Apex-only precondition is not derivable from the org, treat the field as mandatory in the interview.

### R7. Tactic templates must be linked to the promotion template AND share its sales org

`Tactics[*].TacticTemplate` must resolve to a `Tactic_Template__c` in the target
sales org AND be linked to the chosen `PromotionTemplate` via the
`Promotion_Template_Tactic_Template__c` junction (no `Sales_Org__c` of its own;
Name is auto-number `PTTT-{0000}`) — filter through both parents:

```sql
SELECT Id
FROM <prefix>__Promotion_Template_Tactic_Template__c
WHERE <prefix>__Promotion_Template__r.Name = :promotionTemplateName
  AND <prefix>__Promotion_Template__r.<prefix>__Sales_Org__c = :salesOrg
  AND <prefix>__Tactic_Template__r.Name = :tacticTemplateName
  AND <prefix>__Tactic_Template__r.<prefix>__Sales_Org__c = :salesOrg
LIMIT 1
```
Zero rows → stop with `"Tactic template <tt> is not linked to promotion template <pt> in sales org <salesOrg>"`.

### R8. PromotionTemplate must be `Promotion_Type__c = 'Promotion'` — reject Sellable/Retail templates

`Promotion2BoApiCoreCommon.cls:867-875` throws `CPC0009` when the resolved
`PromotionTemplate.Promotion_Type__c != 'Promotion'`. Sellable/Retail templates
(`New Item Introduction`, `Selectable Promotion`, `Distributor Promotion`,
`Regional Promotion`, `Consumer Promotion`, `Campaign Promotion`) carry a
different type and belong to the retail sellable-promotion path.

On create the failure surfaces as an off-platform `WriteError` with a misleading
message (`Invalid JSON! /productfilter must be object`, HTTP 400 from the
Hyperforce CGCPS validator) — it blames `/productfilter` but the actual defect is
the template type. The user-facing error does NOT name the template type, so the
skill MUST fail-fast on template type before ingest.

```sql
SELECT Id, Name, <prefix>__Promotion_Type__c
  FROM <prefix>__Promotion_Template__c
 WHERE Name IN :templateNames
   AND <prefix>__Sales_Org__c = :salesOrg
```
Reject any row where `Promotion_Type__c != 'Promotion'` with:
`"Promotion template <name> has Promotion_Type__c='<type>'; this workflow only supports templates with Promotion_Type__c='Promotion'. Sellable Promotions belong to the retail path."`

## Wire-format quirks

- `POST /promotions/initialize` deserializes lowercase `salesorg` / `nrofitems`. Always emit lowercase.
- `BO_API_Workflow_Workflow_Step__c.Enabled__c` is not honored at runtime. To disable a step, DELETE the junction; do not flip the boolean.
- Success matches `Status__c = 'Calculated'` (R2). `Processed` is not a valid status; polling for it will hang.

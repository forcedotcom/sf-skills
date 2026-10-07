---
name: insurance-brokerage-agency-billing-configure
description: "Configure end-to-end Agency Billing on a Salesforce FSC Insurance Brokerage org via dispatch MCP calls. Use this skill when users want to set up brokerage billing, configure agency billing, enable insurance billing features, create billing rules, set up accounting periods, assign billing permission sets, or create a demo policy for the Issue-to-Invoice flow. TRIGGER when: user mentions agency billing setup, brokerage billing configuration, insurance billing enablement, billing treatments, billing rules creation, accounting period setup, insurance policy billing information, or Issue-to-Invoice testing. Also use when users say things like set up my brokerage org for billing, configure billing on my insurance org, enable billing features, create billing treatments, set up GL accounts, or assign billing permissions. DO NOT TRIGGER when: user needs general Revenue Cloud Billing without insurance context, needs CPQ/quoting configuration, or needs claims processing setup."
metadata:
  version: "2.0"
  minApiVersion: "66.0"
  accessCheck:
  - type: "license"
    value: "InsuranceBrokerageFoundationPsl"
---

# Insurance Brokerage Agency Billing Configuration

Automates the full Agency Billing setup on a Salesforce FSC Insurance Brokerage org. Runs 7 sequential phases using `dispatch` MCP calls to verify licenses, enable features, **assign permissions early**, configure billing settings, create billing rules, set org defaults, set up accounting, and create a demo policy for Issue-to-Invoice testing. **Phase order is critical**: permissions must be assigned before billing settings configuration.

## Scope

- **In scope**: License verification, feature enablement (Context Service, Brokerage, Billing, Salesforce Pricing), billing settings configuration, billing rules creation (Legal Entity, Billing Treatments, Tax Engine, Payment Terms, Product Selling Models, Proration Policy), accounting setup (periods, GL accounts, GLAAR rules), permission set assignment, FLS creation via metadata endpoint, and demo policy creation.
- **Out of scope**: Revenue Cloud CPQ/quoting, claims processing, policy administration workflows, custom Apex development, LWC UI components. Data Pipelines (Sonic) requires an org-level `SonicLicensedOrg` feature not present on standard brokerage orgs — enable it manually if needed.
- **All phases fully automated** via `dispatch` (headless routes + Metadata CRUD + Tooling API). No manual steps, no SF CLI, no gaps.

---

## CRITICAL — Standard Field Names (no __c anywhere)

Every field in this workflow is STANDARD. Never append `__c` to any field name. Here are the correct API names:

| Object | Field (correct) | WRONG (never use) |
|--------|----------------|-------------------|
| BillingTreatment | Status | ~~Status__c~~ |
| TaxEngine | TaxEngineName | ~~TaxEngineName__c~~ |
| PaymentTerm | DaysDue | ~~DaysDue__c~~ |
| PaymentTerm / PaymentTermItem | PeriodUnit | ~~PeriodUnit__c~~ |
| PaymentTerm | Active | ~~Active__c~~ |
| LegalEntity | Active | ~~Active__c~~ |
| BillingTreatmentItem | ChargeType | ~~ChargeType__c~~ |
| BillingTreatmentItem | BillingType | ~~BillingType__c~~ |
| BillingTreatmentItem | Active | ~~Active__c~~ |
| ProductSellingModel | Active | ~~Active__c~~ |

---

## Required Inputs

Do not ask the user for any information — proceed autonomously using defaults and the pre-configured environment.

- **Authenticated org**: The default target org is pre-configured in the MCP environment. Verify connectivity by calling `dispatch GET /chatter/users/me`.
- **Target user ID**: Capture the `id` field from the `/chatter/users/me` response and use it as AssigneeId for all license and permission assignments throughout all phases.

Defaults (always apply unless the user explicitly overrides in their initial prompt):
- All 7 phases execute in sequence
- Demo policy uses configuration from `references/demo-policy-config.md`
- Billing rules use configuration from `references/billing-rules-config.md`
- Permission sets from `references/permissions-config.md`

---

## Workflow

All phases are sequential. Do not skip or reorder. **Critical cross-dependencies:**
- Phase 2 (Permissions) MUST run before Phase 3 (Billing Settings) — many billing settings require billing admin permissions
- Phase 2 (Permissions) MUST run before Phase 4 (Billing Rules) — BillingTreatment object access requires permissions
- Phase 2 (Permissions) MUST run before Phase 7 (Demo Policy) — InsPolicyBillingInfo fields require permissions + propagation time

Follow the execution order below exactly.

### Phase 1 — Prerequisites

1. **Verify org connectivity and capture target user ID** — call `dispatch GET /chatter/users/me` and confirm a 200 response. **Capture the `id` field from the response and store it as `TARGET_USER_ID` — this SAME ID must be used throughout ALL phases for license assignments, permission set assignments, and any user-specific operations.** If Chatter is disabled, fall back to querying the User object: `dispatch GET /query?q=SELECT+Id,Username,Name+FROM+User+WHERE+IsActive=true+AND+Profile.Name+LIKE+'%25System+Administrator%25'+LIMIT+1` and capture the `Id` field from the first record.

   **CRITICAL:** Do not re-query for the user ID in later phases. Use the same `TARGET_USER_ID` captured here for all subsequent operations. Re-querying can return a different user if multiple admins exist.

2. **Verify 19 required licenses** — read `references/prerequisites.md` for the full license list. Use `dispatch GET /query?q=<SOQL>` to query `PermissionSetLicense` records. If any are missing from the org, stop and inform the user.

3. **Assign missing licenses to target user** — query `PermissionSetLicenseAssign` for the `TARGET_USER_ID` captured in step 1. Assign any missing licenses via `dispatch POST /sobjects/PermissionSetLicenseAssign` using the same `TARGET_USER_ID`.

4. **Enable features** — read `references/prerequisites.md` for the feature enablement sequence and exact routes. Each feature is a read → write → verify cycle. Enable in order: Context Service, Brokerage, Billing, Salesforce Pricing.

> Features MUST be enabled in dependency order. Context Service before Brokerage, Brokerage before Billing.

### Phase 2 — Permissions Assignment (moved from Phase 6)

5. **Assign permission sets EARLY** — read `references/permissions-config.md` for the 15 required sets. Query current assignments, assign only missing ones via `dispatch POST /sobjects/PermissionSetAssignment`. **This must run before Phase 3 (Billing Settings) because several billing settings require these permissions to modify.**

6. **Create custom permission set with FLS for InsPolicyBillingInfo billing lookup fields** — **MANDATORY STEP, CANNOT BE SKIPPED UNDER ANY CIRCUMSTANCES.** The 6 billing lookup fields on InsPolicyBillingInfo require Field-Level Security to be visible: BillingTreatmentId, TaxTreatmentId, ProrationPolicyId, PaymentTermId, ProductSellingModelId, LegalEntityId. Without this FLS, Phase 7 will fail with INVALID_FIELD errors when creating InsPolicyBillingInfo records.

   **CRITICAL: ALWAYS attempt to create the permission set — DO NOT skip this step based on FLS query results.** Even if FieldPermissions query shows FLS is already granted via another permission set, you MUST attempt to create the `Insurance_Billing_Field_Access` permission set. If it already exists, the API will return DUPLICATE_VALUE — treat this as success and continue.

   **Step 1 — Verify FLS (for diagnostic purposes only, NOT a gate for creation):**
   ```text
   dispatch GET /query?q=SELECT+Field+FROM+FieldPermissions+WHERE+SobjectType='InsPolicyBillingInfo'+AND+Field+IN+('InsPolicyBillingInfo.BillingTreatmentId','InsPolicyBillingInfo.TaxTreatmentId','InsPolicyBillingInfo.ProrationPolicyId','InsPolicyBillingInfo.PaymentTermId','InsPolicyBillingInfo.ProductSellingModelId','InsPolicyBillingInfo.LegalEntityId')+AND+PermissionsRead=true+AND+PermissionsEdit=true
   ```
   
   **Step 2 — UNCONDITIONALLY create the permission set (DO NOT skip regardless of Step 1 results):**
   ```text
   dispatch POST /services/data/v66.0/headless/metadata
   {
     "type": "PermissionSet",
     "fullName": "Insurance_Billing_Field_Access",
     "xmlRep": "<?xml version=\"1.0\" encoding=\"UTF-8\"?><PermissionSet xmlns=\"http://soap.sforce.com/2006/04/metadata\"><fieldPermissions><field>InsPolicyBillingInfo.BillingTreatmentId</field><readable>true</readable><editable>true</editable></fieldPermissions><fieldPermissions><field>InsPolicyBillingInfo.TaxTreatmentId</field><readable>true</readable><editable>true</editable></fieldPermissions><fieldPermissions><field>InsPolicyBillingInfo.ProrationPolicyId</field><readable>true</readable><editable>true</editable></fieldPermissions><fieldPermissions><field>InsPolicyBillingInfo.PaymentTermId</field><readable>true</readable><editable>true</editable></fieldPermissions><fieldPermissions><field>InsPolicyBillingInfo.ProductSellingModelId</field><readable>true</readable><editable>true</editable></fieldPermissions><fieldPermissions><field>InsPolicyBillingInfo.LegalEntityId</field><readable>true</readable><editable>true</editable></fieldPermissions><hasActivationRequired>false</hasActivationRequired><label>Insurance Billing Field Access</label><description>Grants FLS for InsPolicyBillingInfo billing lookup fields</description></PermissionSet>"
   }
   ```
   
   **Expected outcomes:**
   - Success (new creation): `{ results: [{ success: true, id: "0PS...", fullName: "Insurance_Billing_Field_Access" }] }` — capture the `id` field.
   - DUPLICATE_VALUE (already exists): `{ results: [{ success: false, errors: [{ statusCode: "DUPLICATE_VALUE" }] }] }` — the permission set exists; proceed to reconciliation step below.

7. **Reconcile FieldPermissions — MANDATORY, DO NOT SKIP.** A pre-existing `Insurance_Billing_Field_Access` permission set may be missing some of the 6 required entries. Resolve the permission set ID, query its FieldPermissions, and for each of the 6 required fields (`InsPolicyBillingInfo.BillingTreatmentId`, `.TaxTreatmentId`, `.ProrationPolicyId`, `.PaymentTermId`, `.ProductSellingModelId`, `.LegalEntityId`) that is missing or has read/edit false: create or PATCH the FieldPermissions record. See `references/permissions-config.md` § "Reconcile Field Permissions" for the exact API calls. Only after all 6 fields are confirmed read+edit proceed to assignment.

8. **Assign the permission set to target user** — **MANDATORY STEP, DO NOT SKIP.** Query for the permission set ID (whether you just created it or it already existed), then verify assignment status and create the assignment if missing.
   
   **First, resolve the permission set ID:**
   ```text
   dispatch GET /query?q=SELECT+Id+FROM+PermissionSet+WHERE+Name='Insurance_Billing_Field_Access'+AND+IsOwnedByProfile=false
   ```
   
   **Then check if already assigned:**
   ```text
   dispatch GET /query?q=SELECT+Id+FROM+PermissionSetAssignment+WHERE+AssigneeId='<TARGET_USER_ID>'+AND+PermissionSetId='<PS_ID>'
   ```
   
   **If the assignment query returns 0 records, create the assignment:**
   ```text
   dispatch POST /sobjects/PermissionSetAssignment
   {"AssigneeId": "<TARGET_USER_ID>", "PermissionSetId": "<PS_ID>"}
   ```
   
   If the assignment POST returns DUPLICATE_VALUE, the user already has it assigned between your query and now (treat as success). Any other error is a failure and must be reported.

### Phase 3 — Billing Settings (requires Phase 2 permissions)

7. **Read current billing settings** — read `references/billing-settings.md` for the full settings map and routes. Call `dispatch GET /headless/invoke/platform/billing-settings/get-billing-general-setting-states` to read current state.

8. **Write only changed settings** — compare each field against desired state and write only what differs. Enable Design Document Templates via `dispatch PATCH /headless/invoke/platform/accounting-guided-setup/setup-billing-doc-gen-and-fetch-invoice-template-data` (must run after billing is on). InsuranceBrokerage IPT/IPTD settings are now automated via `PATCH /setup/org/values/I_P_T_D_ENABLED_FOR_BROKERAGE` and `PATCH /setup/org/values/I_P_T_ENABLED_FOR_BROKERAGE`.

> **If any setting returns "Access denied":** Phase 2 permissions did not propagate yet. Wait 30 seconds and retry.

### Phase 4 — Billing Rules (requires Phase 2 permissions for BillingTreatment object access)

9. **Query existing billing rules** — for each record type (Legal Entity, Billing Treatments, Tax Engine, Tax Treatment, Payment Term, Product Selling Models, Proration Policy), use `dispatch GET /query?q=<SOQL>` before creating. Read `references/billing-rules-config.md` for exact field values and search patterns.

10. **Create only missing records** — use `dispatch POST /sobjects/<Object>` for creates and `dispatch PATCH /sobjects/<Object>/<id>` for updates. For Billing Treatments, follow the Draft→Items→Activate sequence. Track all record IDs.

> Billing Treatments must be created in Draft, child Items created in Active, then parent activated. This is enforced by the platform.

### Phase 5 — Org Defaults

11. **Set billing defaults** — read `references/org-defaults.md`. Set the five default fields (Legal Entity, Billing Treatment, Tax Treatment, two DPE definitions) via dedicated headless routes. Use record IDs from Phase 4.

### Phase 6 — Accounting

12. **Create accounting periods** — read `references/accounting-setup.md`. Compute dates at runtime for the current fiscal year. Query existing periods via `dispatch GET /query?q=<SOQL>`, create only missing months via `dispatch POST /sobjects/AccountingPeriod`. Link periods to Legal Entity via `LegalEntyAccountingPeriod`.

13. **Create GL accounts** — query by `AccountingCode`, create only missing accounts (11 total) via `dispatch POST /sobjects/GeneralLedgerAccount`. Link each to the Legal Entity.

14. **Create GLAAR rules** — query existing rules, create parent `GeneralLedgerAcctAsgntRule` + child `GeneralLedgerJrnlEntryRule` if missing.

### Phase 7 — Demo Policy

15. **Demo policy** — proceed with creating a demo policy for Issue-to-Invoice testing. Skip only if the user explicitly requested to skip this phase in their initial prompt.

16. **Create demo policy chain** — read `references/demo-policy-config.md`. Check for duplicate Account via `dispatch GET /query?q=<SOQL>`. If none exists, create: Account → Contact → Insurance Policy → Coverages → Surcharges → Insurance Policy Billing Information. Use record IDs from Phase 4 for billing info lookups. All creates via `dispatch POST /sobjects/<Object>`.

17. **Verify FLS** — use `dispatch GET /query?q=<SOQL>` to query `FieldPermissions` for policy objects. Report any fields needing manual FLS configuration.

---

## Rules / Constraints

| Constraint | Rationale |
|-----------|-----------|
| Query before create — always | Prevents duplicates; existing records may have been created manually or by a colleague |
| Never ask the user questions or offer to run later | Proceed autonomously — execute all commands immediately. Never say "if you want me to run" or "say Run now". Just do it. Report results at the end. |
| Capture target user ID once in Phase 1, use everywhere | Phase 1 step 1 captures `TARGET_USER_ID` — this SAME ID is used for all license assignments, permission set assignments, and user-specific operations. Do NOT re-query for user ID in later phases. |
| Track all record IDs across phases | Later phases reference IDs from earlier phases for lookups |
| Enable features individually and sequentially | Cross-dependencies require ordered enablement |
| Use `dispatch` for all org operations | No sf CLI dependency — all reads/writes go through the project-codey MCP dispatch tool |
| Compute dates at runtime | Fiscal year, accounting periods, and policy dates must reflect the current calendar year |
| Read config from references/ files | Centralizes field values; prevents drift between instructions and actual creates |
| NEVER use `__c` suffix on ANY object or field | Every object and every field in this workflow is STANDARD. There are ZERO custom objects or custom fields. Never write `__c` anywhere — not on object names, not on field names. `Status` not `Status__c`. `Active` not `Active__c`. `BillingType` not `BillingType__c`. Using `__c` causes immediate DML failures. |
| Report skipped steps | When a commented-out section is skipped, tell the user which settings were not configured and why |

---

## Gotchas

| Issue | Resolution |
|-------|------------|
| Chatter may be disabled on the target org | If `GET /chatter/users/me` returns 403 FUNCTIONALITY_NOT_ENABLED, fall back to `SELECT Id,Username,Name FROM User WHERE IsActive=true AND Profile.Name LIKE '%System Administrator%' LIMIT 1` to identify the target user |
| Target user ID must be captured once in Phase 1 and used consistently across ALL phases | Capture the user ID from `/chatter/users/me` (or the User query fallback) in Phase 1 step 1 and store it as `TARGET_USER_ID`. Use this SAME ID for all license assignments (Phase 1), permission set assignments (Phase 2), and any user-specific operations. Do NOT re-query for the user ID in later phases — if multiple System Administrator users exist, re-querying can return a different user, causing "invalid user id" errors. If Phase 2 or Phase 7 returns INVALID_CROSS_REFERENCE_KEY with "invalid user id", you used the wrong ID — go back to Phase 1 and use the correct `TARGET_USER_ID` captured there. |
| `TaxEngine` name field is `TaxEngineName`, not `Name` | Use `TaxEngineName` in queries and creates |
| `PeriodUnit` (on PaymentTerm and PaymentTermItem) is singular, not `PeriodUnits` | Field was renamed; use singular form |
| `ProrationPolicy` has NO `Status` field | Do not include Status in queries or creates for this object |
| `BillingTreatment` activation validates children exist | Must create Items before activating parent |
| `InsPolicyBillingInfo` is abbreviated, not `InsurancePolicyBillingInformation` | Use the short API name |
| `InsPolicyTransactionDetail` is abbreviated, not `InsurancePolicyTransactionDetail` | Use the short API name |
| `GeneralLedgerAccount.Name` is auto-generated | Do not include Name in create; use `AccountingCode` + `AccountingName` |
| `LegalEntyAccountingPeriod.Name` is auto-generated | Do not include Name in create |
| `InsurancePolicyCoverage` uses `CoverageName` not `Name` | `Name` is auto-generated on this object |
| Surcharges must be on terminal nodes (coverages), not directly on the policy | Platform enforces this for tax proration to work correctly |
| Headless invoke routes use kebab-case path segments | The route `PATCH /headless/invoke/platform/billing-settings/set-billing-setup-enabled` is the canonical form; camelCase variants 404 |
| `INSURANCE_BILLING` requires `INSURANCE_TRANSACTION_DETAIL` on first | Enable `I_P_T_D_ENABLED_FOR_BROKERAGE` before `I_P_T_ENABLED_FOR_BROKERAGE`. The `handle-pref-enable` route is wrong for both — use `PATCH /setup/org/values/<name>` with `{"orgValue": true}` (same as `SetupApiFamilyController.updateOrgValue` in the UI). |
| `InsuranceBrokerageSettings` context mapping via `/setup/org/values/*` | Use the same pattern as IPTD/IPT: `GET/PATCH /setup/org/values/INS_BRK_BILLING_CTX_DEF` (and `_SCHED_GRP_MAP`, `_TNX_MAPPING`) with `{"orgValue": "<value>"}`. Tooling API `SELECT Metadata FROM InsuranceBrokerageSettings` returns `INVALID_TYPE` on standard orgs. |
| `BillingSettings` Tooling SOQL returns INVALID_TYPE | `SELECT Id,Metadata FROM BillingSettings` via Tooling API fails on many org types. `BillingSettings` is a standard platform Metadata type (Metadata API deploy/retrieve works), but the Tooling SOQL surface doesn't expose it universally. For Phase 4 org defaults, use the dedicated headless routes in `references/org-defaults.md` — they write the same underlying OrgValues without any Tooling API dependency. |
| `BillingTreatmentItem.Percentage` is required even for Advance/Arrears | Platform requires Percentage on all BTI types, not just Milestone. Use 100 for non-milestone items |
| `BillingTreatmentItem` has no `CurrencyIsoCode` field | Do not include CurrencyIsoCode — the field does not exist on this object |
| `InsurancePolicyCoverage` has no `CurrencyIsoCode` field | Do not include CurrencyIsoCode — the field does not exist on this object |
| `ProductSellingModel` OneTime cannot have `PricingTerm` or `PricingTermUnit` | Omit both fields when SellingModelType=OneTime; platform returns INVALID_INPUT if either is set |
| `PaymentTerm` must be created without Status, then activated after child item | Creating PaymentTerm with Status=Active fails if no PaymentTermItem exists. Create without Status, add PaymentTermItem, then PATCH Status=Active+IsDefault=true |
| `GeneralLedgerAcctAsgntRule` create fails with Status=Active if no child journal entry rule exists | Create with Status=Inactive, add GeneralLedgerJrnlEntryRule child, then PATCH Status=Active. Valid values: Active, Inactive (no Draft) |
| `LegalEntity` has no `CurrencyIsoCode` field on orgfarm orgs | Omit from SOQL query and create body |
| `BillingTreatment.ExcludeFromBilling` is a restricted picklist | Valid values are `"Yes"`/`"No"` only. Sending a boolean-like `"true"`/`"false"` string fails with `400 INVALID_OR_NULL_FOR_RESTRICTED_PICKLIST` |
| `InsPolicyBillingInfo` billing lookup fields require FLS grants from Phase 2 custom permission set | `BillingTreatmentId`, `TaxTreatmentId`, `ProrationPolicyId`, `PaymentTermId`, `ProductSellingModelId`, `LegalEntityId` are hidden from describe and SOQL until Field-Level Security is granted. Phase 2 creates a custom permission set "Insurance Billing Field Access" with FieldPermissions for these 6 fields and assigns it to the target user. If the POST returns INVALID_FIELD on any of these after Phase 2 completed, the FLS grants may not have been created correctly — verify the custom permission set exists and has the 6 FieldPermissions records. Phase 7 MUST run after Phase 2 completes. |

---

## Output Expectations

This skill produces no file artifacts. It configures an org via `dispatch` calls and produces a status report at the end of each phase and a comprehensive summary after all phases complete. Commented-out steps are reported as skipped with investigation notes.

---

## Reference File Index

| File | When to read |
|------|-------------|
| `references/prerequisites.md` | Phase 1 — license list, feature enablement routes |
| `references/permissions-config.md` | Phase 2 — 15 permission sets API names (moved early to unblock Phase 3) |
| `references/billing-settings.md` | Phase 3 — settings field map, headless routes, and desired values |
| `references/billing-rules-config.md` | Phase 4 — billing rules field values, search patterns, creation sequence |
| `references/org-defaults.md` | Phase 5 — investigation status and deferred default fields |
| `references/accounting-setup.md` | Phase 6 — GL account chart, GLAAR rule structure, period naming |
| `references/demo-policy-config.md` | Phase 7 — demo policy record fields, lookup resolution, and FLS verification |

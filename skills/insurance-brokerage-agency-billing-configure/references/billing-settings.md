# Phase 2: Billing Settings

## Read Current State

```text
dispatch GET /headless/invoke/platform/billing-settings/get-billing-general-setting-states
```

Returns a map of all current billing setting states. Compare each key against the desired values below and write only settings that differ.

---

## Billing Settings

### Transaction Journal Creation

**Key in read response:** `TxnJournalCreationEnabled`
**Desired:** `true`

```text
dispatch PATCH /headless/invoke/platform/billing-settings/set-txn-journal-creation-enabled
{"TxnJournalCreationEnabled": true}
```

---

### Payment Schedules and Items Creation

**Key in read response:** `PaymentScheduleAutomationEnabled`
**Desired:** `true`

```text
dispatch PATCH /headless/invoke/platform/billing-settings/set-payment-schedule-automation-enabled
{"paymentScheduleAutomation": true}
```

---

### Convert Negative Invoice Lines to Credit Memo Lines

**Key in read response:** `ApplyConvertedNegIL`
**Desired:** `true`

```text
dispatch PATCH /headless/invoke/platform/billing-settings/set-apply-converted-neg-il
{"applyConvertedNegIL": true}
```

---

### Credit Memo Application to Posted Invoices

**Key in read response:** `PaymentApplicationToInvEnabled`
**Desired:** `true`

```text
dispatch PATCH /headless/invoke/platform/billing-settings/set-payment-application-to-inv-enabled
{"PaymentApplicationToInvEnabled": true}
```

---

### Invoice PDF Generation + Invoice Email Delivery (Tooling API)

These two fields live on the `BillingSettings` Metadata type. No headless route exists — use the Tooling API read/mutate/write-back pattern (same approach as `InsuranceBrokerageSettings`).

**Read current state (captures the full blob — required for the PATCH):**
```text
dispatch GET /tooling/query?q=SELECT+Id,Metadata+FROM+BillingSettings
```

Returns one record with `Id` and a `Metadata` object containing all billing settings fields.

**Write (must send the full Metadata blob — partial writes wipe omitted fields):**

Take the `Metadata` object from the read response, set the two invoice fields to `true`, then PATCH the entire blob back:

```text
dispatch PATCH /tooling/sobjects/BillingSettings/<id>
{
  "Metadata": {
    "<all other fields from read, unchanged>": "...",
    "enableInvoicePdfGeneration": true,
    "enableInvoiceEmailDelivery": true
  }
}
```

**Verify:** re-read `SELECT Metadata FROM BillingSettings` and confirm both fields are `true`.

---

### Billing Context Definition

**Desired:** `BillingContext__stdctx`

```text
dispatch PATCH /headless/invoke/platform/billing-settings/set-billing-ctx-def-org-value-and-get-mapping
{"selectedContextDefinition": "BillingContext__stdctx"}
```

---

### Billing Context Source Mapping

**Desired:** `OrderEntitiesMapping`

**First, get available mapping options** (returned by the context definition setter):
```text
dispatch PATCH /headless/invoke/platform/billing-settings/set-billing-ctx-def-org-value-and-get-mapping
{"selectedContextDefinition": "BillingContext__stdctx"}
```

This returns the available mappings. Then set the source mapping:

```text
dispatch PATCH /headless/invoke/platform/billing-tax-configurations/set-billing-cxt-def-mapping-org-value
{"selectedMapping": "OrderEntitiesMapping"}
```

---

### Intra Context Custom Mapping

**Desired:** `BSGEntitiesMapping`

```text
dispatch PATCH /headless/invoke/platform/billing-settings/set-billing-intra-cxt-def-mapping-org-value
{"selectedIntraContextCustomMapping": "BSGEntitiesMapping"}
```

---

### Rule-Based Credit and Payment Application Order

**Desired:** `{"first":"Payments","rules":["EM","EA","OI","HI"]}`
- `first: Payments` — apply payments before credit memos
- `EM` = Exact Match, `EA` = Exact Account, `OI` = Oldest Invoice, `HI` = Highest Invoice

```text
dispatch PATCH /headless/invoke/platform/billing-settings/set-rules-based-application-order-org-value
{"rulesBasedApplicationOrder": "{\"first\":\"Payments\",\"rules\":[\"EM\",\"EA\",\"OI\",\"HI\"]}"}
```

---

## InsuranceBrokerage Settings

> **Must run after Billing is enabled (Phase 1 Step 3).** The `InsuranceSettingsPageController` returns `NOT_IMPLEMENTED` until billing setup is on.

### Generate Insurance Policy Transaction Details (iptdEnabledForBrokerage)

**Read current state:**
```text
dispatch GET /setup/org/values/I_P_T_D_ENABLED_FOR_BROKERAGE
```
Returns `{ booleanValue: boolean }`.

**Enable (must run BEFORE InsuranceBilling):**
```text
dispatch PATCH /setup/org/values/I_P_T_D_ENABLED_FOR_BROKERAGE
{"orgValue": true}
```

**Verify:** re-read, confirm `booleanValue = true`.

> NOT via `handle-pref-enable` — that route's write guard checks `InsuranceBrokerageSettings` Metadata type which may not be present. Use `setup/org/values` instead (the same path the UI calls via `SetupApiFamilyController.updateOrgValue`).

---

### Generate Insurance Policy Transactions (iptEnabledForBrokerage)

**Read current state:**
```text
dispatch GET /setup/org/values/I_P_T_ENABLED_FOR_BROKERAGE
```
Returns `{ booleanValue: boolean }`.

**Enable (requires I_P_T_D_ENABLED_FOR_BROKERAGE to be on first):**
```text
dispatch PATCH /setup/org/values/I_P_T_ENABLED_FOR_BROKERAGE
{"orgValue": true}
```

**Verify:** re-read, confirm `booleanValue = true`.

---

### Context Mapping Fields

These three context mapping fields use the same `/setup/org/values/*` pattern as IPTD and IPT above (backed by `SetupApiFamilyController.updateOrgValue`).

#### insBrkBillingCtxDef

**Read current state:**
```text
dispatch GET /setup/org/values/INS_BRK_BILLING_CTX_DEF
```
Returns `{ booleanValue, dateValue, numberValue, stringValue }`.

**Set (if not already correct):**
```text
dispatch PATCH /setup/org/values/INS_BRK_BILLING_CTX_DEF
{"orgValue": "InsBillingTransactionContext__stdctx"}
```

**Verify:** re-read, confirm `stringValue = "InsBillingTransactionContext__stdctx"`.

---

#### insBrkBillingCtxSchedGrpMap

**Read current state:**
```text
dispatch GET /setup/org/values/INS_BRK_BILLING_CTX_SCHED_GRP_MAP
```

**Set (if not already correct):**
```text
dispatch PATCH /setup/org/values/INS_BRK_BILLING_CTX_SCHED_GRP_MAP
{"orgValue": "BSGEntitiesMapping"}
```

**Verify:** re-read, confirm `stringValue = "BSGEntitiesMapping"`.

---

#### insBrkBillingCtxTnxMapping

**Read current state:**
```text
dispatch GET /setup/org/values/INS_BRK_BILLING_CTX_TNX_MAPPING
```

**Set (if not already correct):**
```text
dispatch PATCH /setup/org/values/INS_BRK_BILLING_CTX_TNX_MAPPING
{"orgValue": "InsBillingTransactionMapping"}
```

**Verify:** re-read, confirm `stringValue = "InsBillingTransactionMapping"`.

> **Note:** The Tooling API path (`SELECT Metadata FROM InsuranceBrokerageSettings`) returns `INVALID_TYPE` on standard orgfarm orgs. These `/setup/org/values/*` routes are the correct headless path and work universally.

---

## Design Document Templates

**Must run after billing is enabled (Phase 1, Step 3).** The `BillingGettingStartedController` is only available once billing setup is on.

**Read current state:**
```text
dispatch GET /headless/invoke/platform/document-generation-setting/get-init-data
```
Returns `{ canUserAccessDocGenSettingsUI, nameSpacePrefix }`.

**Check if already enabled:**
```text
dispatch GET /headless/invoke/platform/document-generation-setting/fetch-doc-gen-setting-records
```
Returns count of existing DocGen setting records. If `0`, the feature is not yet enabled.

**Enable via billing setup route** (after billing is on):
```text
dispatch PATCH /headless/invoke/platform/accounting-guided-setup/setup-billing-doc-gen-and-fetch-invoice-template-data
{"BillingDocGenEnabled": true}
```

> This route was validated in the route corpus. On the probe org it returned `NOT_IMPLEMENTED` because billing was not yet enabled — this is expected. Run this step after Phase 1 Step 3 (billing enablement) completes.

**Verify:** re-call `GET /headless/invoke/platform/document-generation-setting/fetch-doc-gen-setting-records` and confirm count > 0.

# Phase 4: Org Defaults

All five org defaults are set via dedicated headless routes on `BillingGettingStartedController` — no Tooling API required.

> **Run after Phase 3.** You need the record IDs for Legal Entity, Billing Treatment, and Tax Treatment from Phase 3.

> **Note:** `BillingSettings` is a standard platform Metadata type accessible via Metadata API deploy/retrieve, but `SELECT Id,Metadata FROM BillingSettings` via Tooling API SOQL is not supported on all org types (returns INVALID_TYPE on orgfarm). Use the headless routes below instead — they write the same underlying OrgValues and are the correct headless path.

---

## Step 1: Default Legal Entity

```text
dispatch PATCH /headless/invoke/platform/billing-invoice-configurations/set-default-legal-entity-org-value
{"defaultLegalEntity": "<LEGAL_ENTITY_ID>"}
```

---

## Step 2: Default Billing Treatment

```text
dispatch PATCH /headless/invoke/platform/currency-conversion-guided-setup/set-default-billing-treatment-org-value
{"defaultBillingTreatment": "<ADVANCE_BT_ID>"}
```

---

## Step 3: Default Tax Treatment

```text
dispatch PATCH /headless/invoke/platform/billing-settings/set-default-tax-treatment-org-value
{"defaultTaxTreatment": "<TAX_TREATMENT_ID>"}
```

---

## Step 4: DPE Template — GL Account Period Summary

```text
dispatch PATCH /headless/invoke/platform/billing-prerequisites/set-default-leap-sum-dpetemplate-name-org-value
{"defaultLeapSumDPETemplate": "CreateGLAccountingPeriodSummaryRecord"}
```

---

## Step 5: DPE Template — Accounting Period Closure/Reopen

```text
dispatch PATCH /headless/invoke/platform/billing-prerequisites/set-default-leap-reop-dpetemplate-name-org-value
{"defaultLeapReopDPETemplate": "LegalEntityAccountingPeriodClosureBillingSuite"}
```

---

## Field Reference

| Setting | Route segment | Field | Value source |
|---------|--------------|-------|--------------|
| Default Legal Entity | `billing-invoice-configurations/set-default-legal-entity-org-value` | `defaultLegalEntity` | LegalEntity record Id from Phase 3 |
| Default Billing Treatment | `currency-conversion-guided-setup/set-default-billing-treatment-org-value` | `defaultBillingTreatment` | Advance BT record Id from Phase 3 |
| Default Tax Treatment | `billing-settings/set-default-tax-treatment-org-value` | `defaultTaxTreatment` | TaxTreatment record Id from Phase 3 |
| DPE: GL Period Summary | `billing-prerequisites/set-default-leap-sum-dpetemplate-name-org-value` | `defaultLeapSumDPETemplate` | `CreateGLAccountingPeriodSummaryRecord` |
| DPE: AP Closure/Reopen | `billing-prerequisites/set-default-leap-reop-dpetemplate-name-org-value` | `defaultLeapReopDPETemplate` | `LegalEntityAccountingPeriodClosureBillingSuite` |

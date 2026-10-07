# Phase 1: Prerequisites — Licenses & Feature Enablement

## Target User

Identify the authenticated user before any license or permission operations:

```text
dispatch GET /chatter/users/me
```

Returns `{ id, username, displayName, ... }`. Capture `id` as the target user ID (`<targetUserId>`) for all subsequent license and permission set assignment calls in this workflow.

---

## Required PermissionSetLicenses (19 total)

Query all at once:

```text
dispatch GET /query?q=SELECT+Id,DeveloperName,MasterLabel,Status+FROM+PermissionSetLicense+WHERE+DeveloperName+IN+('InsuranceBrokerageFoundationPsl','InsBrokerageCmsnMgmtPsl','InsBrokeragePolicyManagementPsl','InsBillingIntegrationPsl','ContextServiceAdminPsl','ContextServiceRuntimePsl','CorePricingRunTime','BREDesigner','BRERuntime','CSVDataImportPsl','RevLifecycleMgmtBillingPsl','BillingAdvancedPsl','ProductCatalogManagementAdministratorPsl','SonicEmbeddedStorePsl','UsageDesignTimePsl','UsageRunTimePsl','DataPipelinesAddOnPsl','FSCInsurancePsl','DocGenDesignerPsl')
```

| # | MasterLabel | DeveloperName |
|---|-------------|---------------|
| 1 | Insurance Brokerage | InsuranceBrokerageFoundationPsl |
| 2 | Insurance Brokerage Commission Management | InsBrokerageCmsnMgmtPsl |
| 3 | Insurance Brokerage Policy Management | InsBrokeragePolicyManagementPsl |
| 4 | Insurance Billing Integration | InsBillingIntegrationPsl |
| 5 | Context Service Admin | ContextServiceAdminPsl |
| 6 | Context Service Runtime | ContextServiceRuntimePsl |
| 7 | Salesforce Pricing Run Time | CorePricingRunTime |
| 8 | Business Rules Engine Designer | BREDesigner |
| 9 | Business Rules Engine Runtime | BRERuntime |
| 10 | CSV Basic Data Import | CSVDataImportPsl |
| 11 | Billing | RevLifecycleMgmtBillingPsl |
| 12 | Billing Advanced | BillingAdvancedPsl |
| 13 | Product Catalog Management Administrator | ProductCatalogManagementAdministratorPsl |
| 14 | Data Pipelines Base User | SonicEmbeddedStorePsl |
| 15 | Usage Management Design Time | UsageDesignTimePsl |
| 16 | Usage Management Run Time | UsageRunTimePsl |
| 17 | Data Pipelines Add On User Settings | DataPipelinesAddOnPsl |
| 18 | FSC Insurance | FSCInsurancePsl |
| 19 | DocGen Designer | DocGenDesignerPsl |

If any are missing from the org, stop and tell the user which licenses need provisioning.

---

## License Assignment Check

Query assignments for the target user:

```text
dispatch GET /query?q=SELECT+PermissionSetLicense.DeveloperName+FROM+PermissionSetLicenseAssign+WHERE+AssigneeId='<targetUserId>'+AND+PermissionSetLicense.DeveloperName+IN+('InsuranceBrokerageFoundationPsl','InsBrokerageCmsnMgmtPsl','InsBrokeragePolicyManagementPsl','InsBillingIntegrationPsl','ContextServiceAdminPsl','ContextServiceRuntimePsl','CorePricingRunTime','BREDesigner','BRERuntime','CSVDataImportPsl','RevLifecycleMgmtBillingPsl','BillingAdvancedPsl','ProductCatalogManagementAdministratorPsl','SonicEmbeddedStorePsl','UsageDesignTimePsl','UsageRunTimePsl','DataPipelinesAddOnPsl','FSCInsurancePsl','DocGenDesignerPsl')
```

For each missing license, assign it:

```text
dispatch POST /sobjects/PermissionSetLicenseAssign
{"AssigneeId": "<targetUserId>", "PermissionSetLicenseId": "<licenseId>"}
```

---

## Feature Enablement

Each feature is an independent **read current state → write → verify (re-read)** cycle. Enable in the order below — dependencies are strict.

### 1. Context Service

**Read:**
```text
dispatch GET /connect/contextservice/access/contextServiceEnabled/contextServiceEnabled
```
Returns `{ isEnabled: boolean, uniqueIdentifier: "contextServiceEnabled" }`.

**Enable (if `isEnabled` is false):**
```text
dispatch PUT /connect/contextservice/access/contextServiceEnabled/contextServiceEnabled
{"isEnabled": true}
```

**Verify:** re-read. Confirm `isEnabled` is `true`.

> NOT writable via `/setup/org/preferences/` — use the Context Service Connect endpoint only.

---

### 2. Brokerage (requires Context Service to be on first)

**Read:**
```text
dispatch GET /setup/org/preferences/InsBrokerageEnabled
```
Returns `{ isPreferenceEnabled: boolean }`.

**Enable (if `isPreferenceEnabled` is false):**
```text
dispatch PATCH /setup/org/preferences/InsBrokerageEnabled
{"desiredState": true}
```

**Verify:** re-read. Confirm `isPreferenceEnabled` is `true`.

> Enabling Brokerage triggers server-side seeding of default brokerage metadata records.

---

### 3. Billing (requires Brokerage to be on first)

**Read:**
```text
dispatch GET /headless/invoke/platform/billing-settings/get-billing-general-setting-states
```
Inspect `BillingEnabled` key in the returned map.

**Enable (if `BillingEnabled` is false):**
```text
dispatch PATCH /headless/invoke/platform/billing-settings/set-billing-setup-enabled
{"billingOrgPrefValue": true}
```

**Verify:** re-read. Confirm `BillingEnabled` is `true`.

---

### 4. Salesforce Pricing

**Read:**
```text
dispatch GET /setup/org/preferences/CorePricingPreference
```
Returns `{ isPreferenceEnabled: boolean }`.

**Enable (if `isPreferenceEnabled` is false):**
```text
dispatch PATCH /setup/org/preferences/CorePricingPreference
{"desiredState": true}
```

**Verify:** re-read. Confirm `isPreferenceEnabled` is `true`.

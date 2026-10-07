# Phase 3: Billing Rules Configuration

For every record: query broadly first using `dispatch GET /query?q=<SOQL>`, then create only what is missing. Proceed autonomously without asking.

All creates: `dispatch POST /sobjects/<Object>` with a JSON body.
All updates: `dispatch PATCH /sobjects/<Object>/<recordId>` with a JSON body.

---

## 1. Legal Entity

**Object:** `LegalEntity`

**Search:**
```text
dispatch GET /query?q=SELECT+Id,Name,CompanyName,Description,Status+FROM+LegalEntity+WHERE+Status='Active'
```

If any active entities exist, use the first one found. Do not add CurrencyIsoCode to this query — LegalEntity has no such field on orgfarm orgs, and including it fails the query with 400 INVALID_FIELD.

**Create (if none found):**
```text
dispatch POST /sobjects/LegalEntity
{"Name": "US Legal Entity", "CompanyName": "Agency Sync Brokerages", "Description": "Primary US legal entity for Agency Billing", "Status": "Active"}
```

---

## 2. Billing Treatments (3 types)

**Object:** `BillingTreatment` + child `BillingTreatmentItem`

**Search all:**
```text
dispatch GET /query?q=SELECT+Id,Name,Status,ExcludeFromBilling,IsMilestoneBilling,(SELECT+Id,Name,Status,ProcessingOrder,Type,Percentage,BillingType,MilestoneType,MilestoneStartDate,MilestoneStartDateOffset,MilestoneStartDateOffsetUnit+FROM+BillingTreatmentItems)+FROM+BillingTreatment+WHERE+Status='Active'
```

**Match criteria:**
- Advance: `IsMilestoneBilling=false`, Name contains "Advance", child BTI with `BillingType='Advance'`
- Arrears: `IsMilestoneBilling=false`, Name contains "Arrear", child BTI with `BillingType='Arrears'`
- Milestone 60-20-20: `IsMilestoneBilling=true`, 3 child BTIs with percentages 60/20/20

**Creation sequence (MUST follow this order):**
1. Create BillingTreatment in `Status='Draft'`
2. Create all BillingTreatmentItems in `Status='Active'`
3. Update BillingTreatment to `Status='Active'`

### Advance

Parent:
```text
dispatch POST /sobjects/BillingTreatment
{"Name": "Advance Billing Treatment", "ExcludeFromBilling": "No", "IsMilestoneBilling": false, "Status": "Draft"}
```

Item (Percentage is required even for Advance/Arrears types; CurrencyIsoCode is NOT a field on this object):
```text
dispatch POST /sobjects/BillingTreatmentItem
{"Name": "Advance Billing Treatment Item", "Status": "Active", "Type": "Percentage", "Percentage": 100, "BillingType": "Advance", "BillingTreatmentId": "<BT_ID>"}
```

Activate:
```text
dispatch PATCH /sobjects/BillingTreatment/<BT_ID>
{"Status": "Active"}
```

### Arrears

Parent:
```text
dispatch POST /sobjects/BillingTreatment
{"Name": "Arrear Billing Treatment", "ExcludeFromBilling": "No", "IsMilestoneBilling": false, "Status": "Draft"}
```

Item:
```text
dispatch POST /sobjects/BillingTreatmentItem
{"Name": "Arrear Billing Treatment Item", "Status": "Active", "Type": "Percentage", "Percentage": 100, "BillingType": "Arrears", "BillingTreatmentId": "<BT_ID>"}
```

Activate:
```text
dispatch PATCH /sobjects/BillingTreatment/<BT_ID>
{"Status": "Active"}
```

### Milestone 60-20-20

Parent:
```text
dispatch POST /sobjects/BillingTreatment
{"Name": "Hybrid 60-20-20", "ExcludeFromBilling": "No", "IsMilestoneBilling": true, "Status": "Draft"}
```

Items (3) — no CurrencyIsoCode on this object:
```text
dispatch POST /sobjects/BillingTreatmentItem
{"Name": "60% Milestone", "Status": "Active", "ProcessingOrder": 1, "Type": "Percentage", "Percentage": 60, "BillingType": "None", "MilestoneType": "Date", "MilestoneStartDate": "OrderProductActivation", "MilestoneStartDateOffset": 10, "MilestoneStartDateOffsetUnit": "Days", "BillingTreatmentId": "<BT_ID>"}
```

```text
dispatch POST /sobjects/BillingTreatmentItem
{"Name": "20% Milestone - Second", "Status": "Active", "ProcessingOrder": 2, "Type": "Percentage", "Percentage": 20, "BillingType": "None", "MilestoneType": "Date", "MilestoneStartDate": "OrderProductActivation", "MilestoneStartDateOffset": 2, "MilestoneStartDateOffsetUnit": "Months", "BillingTreatmentId": "<BT_ID>"}
```

```text
dispatch POST /sobjects/BillingTreatmentItem
{"Name": "20% Milestone - Third", "Status": "Active", "ProcessingOrder": 3, "Type": "Percentage", "Percentage": 20, "BillingType": "None", "MilestoneType": "Date", "MilestoneStartDate": "OrderProductActivation", "MilestoneStartDateOffset": 3, "MilestoneStartDateOffsetUnit": "Months", "BillingTreatmentId": "<BT_ID>"}
```

Activate:
```text
dispatch PATCH /sobjects/BillingTreatment/<BT_ID>
{"Status": "Active"}
```

---

## 3. Tax Engine

**Object:** `TaxEngine` (name field is `TaxEngineName`, NOT `Name`)

**Search:**
```text
dispatch GET /query?q=SELECT+Id,TaxEngineName,Type,Status+FROM+TaxEngine+WHERE+Type='InsuranceTaxProration'+AND+Status='Active'
```

**Create:**
```text
dispatch POST /sobjects/TaxEngine
{"TaxEngineName": "Insurance Tax Proration Engine", "Type": "InsuranceTaxProration", "Status": "Active"}
```

---

## 4. Tax Treatment

**Object:** `TaxTreatment`

**Search:**
```text
dispatch GET /query?q=SELECT+Id,Name,Status,IsTaxable,TaxEngineId+FROM+TaxTreatment+WHERE+IsTaxable=true+AND+Status='Active'
```

**Create:**
```text
dispatch POST /sobjects/TaxTreatment
{"Name": "Passthrough Tax", "Status": "Active", "IsTaxable": true, "TaxEngineId": "<TAX_ENGINE_ID>"}
```

---

## 5. Payment Term + Item

**Object:** `PaymentTerm` + child `PaymentTermItem`

**Search:**
```text
dispatch GET /query?q=SELECT+Id,Name,IsDefault,Status,(SELECT+Id,Name,Type,PaymentTimeframe,Period,PeriodUnit+FROM+PaymentTermItems)+FROM+PaymentTerm+WHERE+Status='Active'
```

**Create parent (Status and IsDefault must be set AFTER child item exists):**
```text
dispatch POST /sobjects/PaymentTerm
{"Name": "Net 10"}
```

**Create item** (Type is `Period-Based`, PeriodUnit is singular):
```text
dispatch POST /sobjects/PaymentTermItem
{"Type": "Period-Based", "PaymentTimeframe": "Standard", "Period": 10, "PeriodUnit": "Days", "PaymentTermId": "<PT_ID>"}
```

**Activate parent after item exists:**
```text
dispatch PATCH /sobjects/PaymentTerm/<PT_ID>
{"Status": "Active", "IsDefault": true}
```

> Platform enforces: cannot save PaymentTerm with Status=Active until a child PaymentTermItem exists. Create parent without Status, add child, then PATCH to Active+IsDefault.

> **Org prerequisite:** PaymentTerm is only writable when billing features are enabled (Phase 1 Step 3). On orgs without billing, the sObject describe returns `createable: false` — this is expected and does not indicate a gap in the skill.

---

## 6. Product Selling Models (5 records)

**Object:** `ProductSellingModel`

**Search all:**
```text
dispatch GET /query?q=SELECT+Id,Name,SellingModelType,PricingTerm,PricingTermUnit,Status+FROM+ProductSellingModel+ORDER+BY+Name
```

**Match by SellingModelType + PricingTermUnit (fuzzy on Name):**

| SellingModelType | PricingTermUnit | Default Name |
|-----------------|-----------------|--------------|
| OneTime | Months | One time |
| TermDefined | Months | Term Defined - Monthly |
| TermDefined | Quarterly | Term Defined - Quarterly |
| TermDefined | Semi-Annual | Term Defined - Semi Annual |
| TermDefined | Annual | Term Defined - Annual |

**Create pattern (TermDefined types):**
```text
dispatch POST /sobjects/ProductSellingModel
{"Name": "<NAME>", "SellingModelType": "<TYPE>", "PricingTerm": 1, "PricingTermUnit": "<UNIT>", "Status": "Active"}
```

**Create pattern (OneTime — no PricingTerm or PricingTermUnit):**
```text
dispatch POST /sobjects/ProductSellingModel
{"Name": "One time", "SellingModelType": "OneTime", "Status": "Active"}
```

> Platform enforces: OneTime selling models cannot have PricingTerm or PricingTermUnit set. Omit both fields.

---

## 7. Proration Policy

**Object:** `ProrationPolicy` (has NO Status field)

**Search:**
```text
dispatch GET /query?q=SELECT+Id,Name,RemainderStrategy,ArePartialPeriodsAllowed,ProrationPolicyType+FROM+ProrationPolicy
```

**Match:** `RemainderStrategy='AddToLast'` AND `ArePartialPeriodsAllowed=false`

**Create:**
```text
dispatch POST /sobjects/ProrationPolicy
{"Name": "No Partial Proration Add to Last", "RemainderStrategy": "AddToLast", "ArePartialPeriodsAllowed": false, "ProrationPolicyType": "StandardTimePeriods"}
```

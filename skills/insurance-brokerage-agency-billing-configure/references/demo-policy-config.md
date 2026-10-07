# Phase 7: Demo Policy Configuration

All creates use `dispatch POST /sobjects/<Object>` with a JSON body.
All queries use `dispatch GET /query?q=<SOQL>`.

---

## Duplicate Check

Before creating any records, query for an existing Account with the same name:

```text
dispatch GET /query?q=SELECT+Id,Name+FROM+Account+WHERE+Name='Pinnacle+Ridge+Insurance+Group'
```

If found, reuse the existing Account instead of creating a duplicate.

---

## Record Creation Chain

Create in this exact order (each depends on the previous):

1. Account
2. Contact (linked to Account)
3. Insurance Policy (linked to Account via NameInsuredId)
4. Coverages (linked to Policy)
5. Surcharges (linked to Policy AND Coverage)
6. Insurance Policy Billing Information (linked to Policy, Contact, and all Phase 3 records)

---

## Default Demo Data

### Account

```text
dispatch POST /sobjects/Account
{"Name": "Pinnacle Ridge Insurance Group", "BillingStreet": "100 Main Street", "BillingCity": "San Francisco", "BillingState": "CA", "BillingPostalCode": "94105", "BillingCountry": "US", "ShippingStreet": "100 Main Street", "ShippingCity": "San Francisco", "ShippingState": "CA", "ShippingPostalCode": "94105", "ShippingCountry": "US"}
```

---

### Contact

```text
dispatch POST /sobjects/Contact
{"FirstName": "Sarah", "LastName": "Mitchell", "Title": "VP of Risk Management", "Email": "sarah.mitchell@pinnacleridge.example.com", "Phone": "415-555-0142", "AccountId": "<ACCOUNT_ID>"}
```

---

### Insurance Policy

Compute dates at runtime:
- `EffectiveFromDate`: January 1 of current year
- `EffectiveToDate`: December 31 of current year

```text
dispatch POST /sobjects/InsurancePolicy
{"Name": "PRI-CGL-2026-001", "PolicyName": "Commercial General Liability", "PolicyType": "General Liability", "Status": "In Force", "EffectiveFromDate": "<CURRENT_YEAR>-01-01", "EffectiveToDate": "<CURRENT_YEAR>-12-31", "NameInsuredId": "<ACCOUNT_ID>"}
```

---

### Coverages (2)

Coverage 1 — Bodily Injury (no CurrencyIsoCode on InsurancePolicyCoverage):
```text
dispatch POST /sobjects/InsurancePolicyCoverage
{"CoverageName": "Bodily Injury Liability", "StandardPremiumAmount": 45000, "InsurancePolicyId": "<POLICY_ID>"}
```

Coverage 2 — Property Damage:
```text
dispatch POST /sobjects/InsurancePolicyCoverage
{"CoverageName": "Property Damage Liability", "StandardPremiumAmount": 30000, "InsurancePolicyId": "<POLICY_ID>"}
```

---

### Surcharges (3 — on coverages, NOT directly on policy)

On Bodily Injury:
```text
dispatch POST /sobjects/InsurancePolicySurcharge
{"Name": "State Premium Tax - BI", "SurchargeAmount": 2250, "Type": "Tax", "ApplicableObjectType": "InsurancePolicyCoverage", "InsurancePolicyId": "<POLICY_ID>", "InsurancePolicyCoverageId": "<BI_COVERAGE_ID>"}
```

```text
dispatch POST /sobjects/InsurancePolicySurcharge
{"Name": "Municipal Assessment - BI", "SurchargeAmount": 450, "Type": "Tax", "ApplicableObjectType": "InsurancePolicyCoverage", "InsurancePolicyId": "<POLICY_ID>", "InsurancePolicyCoverageId": "<BI_COVERAGE_ID>"}
```

On Property Damage:
```text
dispatch POST /sobjects/InsurancePolicySurcharge
{"Name": "State Premium Tax - PD", "SurchargeAmount": 1500, "Type": "Tax", "ApplicableObjectType": "InsurancePolicyCoverage", "InsurancePolicyId": "<POLICY_ID>", "InsurancePolicyCoverageId": "<PD_COVERAGE_ID>"}
```

---

### Insurance Policy Billing Information

> **Phase 2 must complete before this step.** The billing lookup fields (`BillingTreatmentId`, `TaxTreatmentId`, `ProrationPolicyId`, `PaymentTermId`, `ProductSellingModelId`, `LegalEntityId`) are hidden from describe and SOQL until the billing permission sets are assigned. If the POST returns INVALID_FIELD on any of these, go back and complete Phase 2 first.

Resolve all lookups from Phase 3 record IDs:
```text
dispatch POST /sobjects/InsPolicyBillingInfo
{"BillDayOfMonth": 15, "InsurancePolicyId": "<POLICY_ID>", "BillToContactId": "<CONTACT_ID>", "BillingTreatmentId": "<ADVANCE_BT_ID>", "TaxTreatmentId": "<TAX_TREATMENT_ID>", "ProrationPolicyId": "<PRORATION_POLICY_ID>", "PaymentTermId": "<PAYMENT_TERM_ID>", "ProductSellingModelId": "<MONTHLY_PSM_ID>", "LegalEntityId": "<LEGAL_ENTITY_ID>"}
```

---

## Verification

After all records are created:

```text
dispatch GET /query?q=SELECT+Id,Name,PolicyName,PolicyType,Status,EffectiveFromDate,EffectiveToDate,(SELECT+Id,CoverageName,StandardPremiumAmount+FROM+InsurancePolicyCoverages),(SELECT+Id,Name,SurchargeAmount,Type+FROM+InsurancePolicySurcharges)+FROM+InsurancePolicy+WHERE+Id='<POLICY_ID>'
```

```text
dispatch GET /query?q=SELECT+Id,BillDayOfMonth,BillingTreatmentId,TaxTreatmentId,ProrationPolicyId,PaymentTermId,ProductSellingModelId,LegalEntityId+FROM+InsPolicyBillingInfo+WHERE+InsurancePolicyId='<POLICY_ID>'
```

## Expected Totals

- Total premium: $75,000 (45,000 + 30,000)
- Total tax/surcharges: $4,200 (2,250 + 450 + 1,500)
- Grand total: $79,200

## Next Steps (manual, tell the user)

1. Navigate to the policy and click "Issue"
2. After issuance, go to Insurance Policy Transaction and click "Send to Billing"
3. Generate invoices from Account page or Billing Schedule Group
4. Process payments and review journal entries

# Phase 6: Permissions & FLS

## Permission Sets (15 total)

| # | Label | API Name |
|---|-------|----------|
| 1 | Billing Admin | RevenueLifecycleManagementBillingAdmin |
| 2 | Basic CSV Data Import | SimpleCsvDataImport |
| 3 | Context Service Admin | ContextServiceAdminPsl |
| 4 | Insurance Billing Integration | InsuranceBillingIntegration |
| 5 | Billing Operations User | RevenueLifecycleManagementBillingOperations |
| 6 | Collections and Recovery Admin | CollectionsAndRecoveryAdmin |
| 7 | Generate Invoices From Billing Schedule API | RevenueLifecycleManagementBillingCreateInvoiceFromBillingScheduleApi |
| 8 | Data Pipelines Base User | AnalyticsStoreUser |
| 9 | Payment Admin | BillingAdvancedPaymentAdministrator |
| 10 | DocGen Designer | DocGenDesigner |
| 11 | Payment Operations User | BillingAdvancedPaymentOperations |
| 12 | Tax Admin | RevenueLifecycleManagementBillingTaxAdmin |
| 13 | DocGen User | DocGenUser |
| 14 | Accounts Receivables Admin | RevenueLifecycleManagementAccountingAdmin |
| 15 | FSC Insurance | FSCInsurance |

---

## Check Existing Assignments

Use the target user ID captured in Phase 1 (`<TARGET_USER_ID>`).

```text
dispatch GET /query?q=SELECT+PermissionSet.Name,PermissionSet.Label+FROM+PermissionSetAssignment+WHERE+AssigneeId='<TARGET_USER_ID>'+AND+PermissionSet.Name+IN+('RevenueLifecycleManagementBillingAdmin','SimpleCsvDataImport','ContextServiceAdminPsl','InsuranceBillingIntegration','RevenueLifecycleManagementBillingOperations','CollectionsAndRecoveryAdmin','RevenueLifecycleManagementBillingCreateInvoiceFromBillingScheduleApi','AnalyticsStoreUser','BillingAdvancedPaymentAdministrator','DocGenDesigner','BillingAdvancedPaymentOperations','RevenueLifecycleManagementBillingTaxAdmin','DocGenUser','RevenueLifecycleManagementAccountingAdmin','FSCInsurance')
```

---

## Assign Missing Permission Sets

For each missing permission set, first resolve its Id by name, then create the assignment.

**Step 1 — Resolve PermissionSet Id:**
```text
dispatch GET /query?q=SELECT+Id+FROM+PermissionSet+WHERE+Name='<apiName>'+AND+IsOwnedByProfile=false
```

**Step 2 — Create assignment:**
```text
dispatch POST /sobjects/PermissionSetAssignment
{"AssigneeId": "<TARGET_USER_ID>", "PermissionSetId": "<PS_ID>"}
```

If assignment fails (e.g., missing license), log the error and continue with remaining sets.

---

## Field-Level Security for InsPolicyBillingInfo

**MANDATORY STEP — CANNOT BE SKIPPED.** The 6 billing lookup fields on InsPolicyBillingInfo require Field-Level Security to be visible. Without this, Phase 7 will fail with INVALID_FIELD when creating InsPolicyBillingInfo records.

**CRITICAL: The permission set creation is UNCONDITIONALLY MANDATORY.** Even if FLS is already granted via another permission set, you MUST attempt to create the `Insurance_Billing_Field_Access` permission set. The creation may return a DUPLICATE error (which is acceptable and means it already exists), but you MUST NOT skip the creation attempt based on the FLS query results alone.

### Verify FLS Exists (For Diagnostic Purposes Only)

Query FieldPermissions to confirm FLS status (this is for verification, NOT a gate for creation):

```text
dispatch GET /query?q=SELECT+Field+FROM+FieldPermissions+WHERE+SobjectType='InsPolicyBillingInfo'+AND+Field+IN+('InsPolicyBillingInfo.BillingTreatmentId','InsPolicyBillingInfo.TaxTreatmentId','InsPolicyBillingInfo.ProrationPolicyId','InsPolicyBillingInfo.PaymentTermId','InsPolicyBillingInfo.ProductSellingModelId','InsPolicyBillingInfo.LegalEntityId')+AND+PermissionsRead=true+AND+PermissionsEdit=true
```

**DO NOT** use this query to decide whether to skip creation. Proceed to creation regardless of the result.

### Create Custom Permission Set with FLS (ALWAYS — NO EXCEPTIONS)

**UNCONDITIONALLY create the permission set.** Do NOT skip based on FLS query results. If the permission set already exists, the API will return a DUPLICATE error — treat this as success and continue to the assignment step.

```text
dispatch POST /services/data/v66.0/headless/metadata
{
  "type": "PermissionSet",
  "fullName": "Insurance_Billing_Field_Access",
  "xmlRep": "<?xml version=\"1.0\" encoding=\"UTF-8\"?><PermissionSet xmlns=\"http://soap.sforce.com/2006/04/metadata\"><fieldPermissions><field>InsPolicyBillingInfo.BillingTreatmentId</field><readable>true</readable><editable>true</editable></fieldPermissions><fieldPermissions><field>InsPolicyBillingInfo.TaxTreatmentId</field><readable>true</readable><editable>true</editable></fieldPermissions><fieldPermissions><field>InsPolicyBillingInfo.ProrationPolicyId</field><readable>true</readable><editable>true</editable></fieldPermissions><fieldPermissions><field>InsPolicyBillingInfo.PaymentTermId</field><readable>true</readable><editable>true</editable></fieldPermissions><fieldPermissions><field>InsPolicyBillingInfo.ProductSellingModelId</field><readable>true</readable><editable>true</editable></fieldPermissions><fieldPermissions><field>InsPolicyBillingInfo.LegalEntityId</field><readable>true</readable><editable>true</editable></fieldPermissions><hasActivationRequired>false</hasActivationRequired><label>Insurance Billing Field Access</label><description>Grants FLS for InsPolicyBillingInfo billing lookup fields</description></PermissionSet>"
}
```

**Expected responses:**
1. **Success (new creation):**
```json
{
  "results": [
    {
      "success": true,
      "id": "0PS...",
      "fullName": "Insurance_Billing_Field_Access",
      "errors": []
    }
  ]
}
```

2. **DUPLICATE_VALUE (already exists) — treat as success:**
```json
{
  "results": [
    {
      "success": false,
      "fullName": "Insurance_Billing_Field_Access",
      "errors": [{"statusCode": "DUPLICATE_VALUE", "message": "..."}]
    }
  ]
}
```

**In both cases, proceed to the reconciliation step.** Do NOT treat DUPLICATE_VALUE as an error — it means the permission set already exists, which is acceptable.

### Reconcile Field Permissions (MANDATORY — DO NOT SKIP)

**CRITICAL: When a pre-existing permission set is found (DUPLICATE_VALUE), verify it has all 6 required FieldPermissions.** A pre-existing `Insurance_Billing_Field_Access` permission set might be missing some of the required fields, which would cause Phase 7 InsPolicyBillingInfo creation to fail with INVALID_FIELD.

**First, resolve the permission set ID:**

```text
dispatch GET /query?q=SELECT+Id+FROM+PermissionSet+WHERE+Name='Insurance_Billing_Field_Access'+AND+IsOwnedByProfile=false
```

**Then query existing FieldPermissions:**

```text
dispatch GET /query?q=SELECT+Id,Field,PermissionsRead,PermissionsEdit+FROM+FieldPermissions+WHERE+ParentId='<PS_ID>'+AND+SobjectType='InsPolicyBillingInfo'+AND+Field+IN+('InsPolicyBillingInfo.BillingTreatmentId','InsPolicyBillingInfo.TaxTreatmentId','InsPolicyBillingInfo.ProrationPolicyId','InsPolicyBillingInfo.PaymentTermId','InsPolicyBillingInfo.ProductSellingModelId','InsPolicyBillingInfo.LegalEntityId')
```

**For each of the 6 required fields, check the result:**
- If the field exists with `PermissionsRead=true` and `PermissionsEdit=true`, no action needed
- If the field exists but either permission is false, PATCH the FieldPermissions record to enable both
- If the field is missing entirely, CREATE a new FieldPermissions record

**To create missing FieldPermissions (repeat for each missing field):**

```text
dispatch POST /sobjects/FieldPermissions
{
  "ParentId": "<PS_ID>",
  "SobjectType": "InsPolicyBillingInfo",
  "Field": "InsPolicyBillingInfo.<FieldName>",
  "PermissionsRead": true,
  "PermissionsEdit": true
}
```

**To fix incomplete FieldPermissions (if read or edit is false):**

```text
dispatch PATCH /sobjects/FieldPermissions/<FP_ID>
{
  "PermissionsRead": true,
  "PermissionsEdit": true
}
```

After reconciliation completes, proceed to assignment.

### Assign Permission Set to Target User

**MANDATORY STEP — DO NOT SKIP.** Verify assignment status and create the assignment if missing.

**Then check if already assigned:**

```text
dispatch GET /query?q=SELECT+Id+FROM+PermissionSetAssignment+WHERE+AssigneeId='<TARGET_USER_ID>'+AND+PermissionSetId='<PS_ID>'
```

**If the assignment query returns 0 records, create the assignment:**

```text
dispatch POST /sobjects/PermissionSetAssignment
{"AssigneeId": "<TARGET_USER_ID>", "PermissionSetId": "<PS_ID>"}
```

If the assignment POST returns `400 DUPLICATE_VALUE`, the user already has the permission set assigned between your query and now (treat as success). Any other error is a failure and must be reported.

### Required Fields

| Field | Type | Required |
|-------|------|----------|
| BillingTreatmentId | Lookup(BillingTreatment) | Read + Edit |
| TaxTreatmentId | Lookup(TaxTreatment) | Read + Edit |
| ProrationPolicyId | Lookup(ProrationPolicy) | Read + Edit |
| PaymentTermId | Lookup(PaymentTerm) | Read + Edit |
| ProductSellingModelId | Lookup(ProductSellingModel) | Read + Edit |
| LegalEntityId | Lookup(LegalEntity) | Read + Edit |

### Notes

- The `/services/data/v66.0/headless/metadata` endpoint requires the `FileBasedMetadataCrud` org entitlement. If missing, the call returns `500 METADATA_CRUD_ERROR`.
- PermissionSet is allowlisted for full CRUD (create, read, update, delete) via the metadata endpoint.
- The `xmlRep` field must be a complete PermissionSet XML document following the Metadata API schema.
- Field permissions use the format `<SobjectType>.<FieldName>` (e.g., `InsPolicyBillingInfo.BillingTreatmentId`).

---

## Field-Level Security

Check FLS via standard SOQL.

### Required FLS (Read + Edit for System Administrator)

**InsurancePolicy:** OriginalPolicyId, PolicyStage, StandardCommissionAmount, TermCommissionAmount

**InsurancePolicyCoverage:** OriginalCoverageId, StandardCommissionAmount, TermCommissionAmount

**InsurancePolicyAsset:** OriginalAssetId, StandardCommissionAmount, TermCommissionAmount

**InsurancePolicyParticipant:** OriginalParticipantId, StandardCommissionAmount, TermCommissionAmount

### Query FLS

```text
dispatch GET /query?q=SELECT+Field,PermissionsRead,PermissionsEdit+FROM+FieldPermissions+WHERE+Parent.Profile.Name='System+Administrator'+AND+SobjectType='<OBJECT>'+AND+Field+IN+('<OBJECT>.<FIELD1>','<OBJECT>.<FIELD2>')
```

### Object-Level CRUD (full access needed)

Objects: InsurancePolicyCoverage, InsurancePolicyAsset, InsurancePolicyParticipant, InsurancePolicySurcharge, InsurancePolicyTransaction, InsPolicyTransactionDetail, InsPolicyBillingInfo

```text
dispatch GET /query?q=SELECT+SobjectType,PermissionsRead,PermissionsCreate,PermissionsEdit,PermissionsDelete+FROM+ObjectPermissions+WHERE+Parent.Profile.Name='System+Administrator'+AND+SobjectType+IN+('InsurancePolicyCoverage','InsurancePolicyAsset','InsurancePolicyParticipant','InsurancePolicySurcharge','InsurancePolicyTransaction','InsPolicyTransactionDetail','InsPolicyBillingInfo')
```

If fields are missing access after permission set assignment, provide manual steps (Setup > Object Manager > Field > Set FLS).

---
name: platform-custom-field-generate
description: "Use this skill when users need to create, generate, or validate Salesforce Custom Field metadata. Trigger when users mention custom fields, field types, Roll-up Summary fields, Master-Detail relationships, Lookup relationships, formula fields, picklists, dependent (controlling) picklists, referencing a value set from a field, or scoping/limiting picklist values for a specific record type. Also use when users encounter field deployment errors, especially around Roll-up Summary format, Master-Detail constraints, formula issues, or a record type that won't deploy without a business process. Use this skill for custom field metadata work, field generation, and field troubleshooting. DO NOT TRIGGER for creating or customizing the value set itself — defining a new GlobalValueSet, or modifying a StandardValueSet catalog like Industry or Lead Source — use platform-value-set-generate instead; this skill covers the field that references a value set, not the value set definition."
metadata:
  version: "1.0"
  minApiVersion: "51.0"
---

# Salesforce Custom Field Generator and Validator

## Overview

Generates and validates Salesforce CustomField metadata XML, with special handling for the **highest-failure-rate types** — Roll-Up Summary and Master-Detail. The agent must verify the constraints below before outputting XML to prevent Metadata API deployment errors.

---

## 1. Universal Mandatory Attributes

Every generated field must include these tags:

| Attribute | Requirement | Notes |
|-----------|-------------|-------|
| `<fullName>` | Required | **Field** name only: derive from `<label>` — capitalize each word, replace spaces with `_`, append `__c`. Must start with a letter. E.g., label `Total Contract Value` → `Total_Contract_Value__c`. ⚠️ This rule is for the FIELD name. **Picklist VALUE `<fullName>` is different — keep it exactly as the user spelled it, spaces and all, no `__c`** (e.g. `Closed Won`, NOT `Closed_Won`). See [`references/advanced-picklists.md`](references/advanced-picklists.md) (ref §3). |
| `<label>` | Required | The UI name (Title Case) |
| `<description>` | Always include | Explain the business reason *why* this field exists. |
| `<inlineHelpText>` | Always include | Actionable end-user guidance that adds value beyond the label (e.g., "Enter the value in USD including tax", not "The amount"). |

`<description>` and `<inlineHelpText>` are mandatory outputs even though the Metadata API does not enforce them — omitting them produces low-quality metadata.

**File path (SFDX source format):** save each field as `force-app/main/default/objects/<Object>/fields/<FieldName>__c.field-meta.xml`, where `<Object>` is the object's API name (`Account`, `Opportunity`, or a custom `Inventory_Item__c`). A correct XML at the wrong path is never seen by the Metadata API.

### External ID Configuration

**Trigger:** If the user mentions "integration," "importing data," "external system ID," or "unique key from [System Name]," set `<externalId>true</externalId>`.

**Applicable Types:** Text, Number, Email

---

## 2. Precision, Scale, and Length Rules

To ensure deployment success, follow these mathematical constraints:

### Precision vs. Scale Rules

- `precision` is the total digits; `scale` is the decimal digits
- **Rule:** `precision ≤ 18` AND `scale ≤ precision`
- **Calculation:** Digits to the left of decimal = `precision - scale`

### The "Fixed 255" Rule

**TextArea: always include `<length>255</length>` exactly** — this literal value is required by the Metadata API and **omitting it fails deployment**, even though the UI exposes no length control. Unlike every other type where `length` is a value you calculate, TextArea's is a fixed constant.

### Visible Lines

Mandatory for Long/Rich text and Multi-select picklists to control UI height.

---

## 3. Field Data Types

### 3.1 Simple Attribute Types

| Type | `<type>` Value | Required Attributes |
|------|----------------|---------------------|
| Auto Number | `AutoNumber` | `displayFormat` (must include `{0}`), `startingNumber` |
| Checkbox | `Checkbox` | Default `defaultValue` to `false` |
| Date | `Date` | No precision/length required |
| Date/Time | `DateTime` | No precision/length required |
| Email | `Email` | Built-in format validation |
| Lookup Relationship | `Lookup` | `referenceTo`, `relationshipName`, `deleteConstraint` |
| Master-Detail Relationship | `MasterDetail` | `referenceTo`, `relationshipName`, `relationshipOrder` |
| Number | `Number` | `precision`, `scale` |
| Currency | `Currency` | Default precision: 18, scale: 2 |
| Percent | `Percent` | Default precision: 5, scale: 2 |
| Phone | `Phone` | Standardizes phone number formatting |
| Picklist | `Picklist` | `valueSet` containing EITHER `valueSetDefinition` (inline) OR `valueSetName` (reference); `restricted` (see "Picklist `restricted` default" below; advanced cases in §3.4) |
| Text | `Text` | `length` (Max 255) |
| Text Area | `TextArea` | `<length>255</length>` |
| Text (Long) | `LongTextArea` | `length`, `visibleLines` (default 3) |
| Text (Rich) | `Html` | `length`, `visibleLines` (default 25) |
| Time | `Time` | Stores time only (no date) |
| URL | `Url` | Validates for protocol and format |

### 3.2 Computed & Multi-Value Types

| Type | `<type>` Value | Required Attributes |
|------|----------------|---------------------|
| Formula | Result type (e.g., `Number`) | `formula`, `formulaTreatBlanksAs` |
| Roll-Up Summary | `Summary` | See Section 5 for complete requirements |
| Multi-Select Picklist | `MultiselectPicklist` | `valueSet`, `visibleLines` (default 4) |

### 3.3 Specialized Types

| Type | `<type>` Value | Required Attributes |
|------|----------------|---------------------|
| Geolocation | `Location` | `scale`, `displayLocationInDecimal` |

### Picklist `restricted` default

**Always set `<restricted>true</restricted>`** inside `<valueSet>` unless the user explicitly says the picklist should accept custom values not in the admin-defined list (e.g. "unrestricted"/"open"). Restricted sets are capped at 1,000 total values (active + inactive). Minimal inline shape:

```xml
<valueSet>
  <restricted>true</restricted>
  <valueSetDefinition>
    <sorted>false</sorted>
    <value><fullName>Option_A</fullName><default>false</default><label>Option A</label></value>
  </valueSetDefinition>
</valueSet>
```

### 3.4 Advanced Picklists

The inline `<valueSetDefinition>` above is the simple case. Full rules and worked ✅/❌
examples for everything below are in
[`references/advanced-picklists.md`](references/advanced-picklists.md) — load it for any
non-trivial picklist. Section numbers in parentheses below (e.g. "ref §1") point to that
reference file, not to this skill. The hard rules:

- **Value-set reference (ref §1).** A `<valueSet>` holds EITHER `<valueSetName>` (reference) OR
  `<valueSetDefinition>` (inline) — **never both**. Reference by the **bare** developer name —
  Standard set `Industry`, GlobalValueSet `Priority_Levels` with **NO `__gvs`** and no `__c`
  (the `__gvs` suffix is org-storage display only; the Metadata API uses the bare name). A
  value-set-backed field is `<restricted>true</restricted>`. Creating the value set is the
  `platform-value-set-generate` skill's job; this one only references it.
- **Value-name fidelity (ref §3).** A picklist value's `<fullName>`/`<label>` keep the user's exact
  text **including spaces** (`Closed Won`, never `Closed_Won`). The space→`_` + `__c` rule is for
  the FIELD name only.
- **Dependent picklists (ref §2).** Use the **modern API 38.0+** form: `<controllingField>` +
  one `<valueSettings>` (`<controllingFieldValue>`+`<valueName>`) per pair; never the legacy
  `<picklist>`/`<picklistValues>`/`<controllingFieldValues>` tags. **Both** controlling and
  dependent fields MUST be `<restricted>true</restricted>`, even if the request doesn't say so.
- **Enhanced value attributes (ref §3).** `<value>` entries also accept `<color>` (hex, leading
  `#`), `<isActive>` (`false` retires a value), and a value-level `<description>`.
- **Scoping a picklist to a record type (ref §5).** Per-record-type value visibility lives on the
  **RecordType** (`<picklistValues>`), not the field. The RecordType file carries its own
  `<fullName>` (bare developer name). **First decide if the object needs a BusinessProcess:**
  only **Opportunity / Lead / Case / Solution** require one — they won't deploy without a
  `<businessProcess>` (`Required field is missing: businessProcess`), even when only a custom
  picklist is filtered. There you emit **two coupled files**: the `businessProcesses/<Name>.businessProcess-meta.xml`
  file AND a matching `<businessProcess><Name></businessProcess>` inside the `<RecordType>` (after
  `<active>`, before `<picklistValues>`; the `<fullName>` in the BP file is **bare**, never
  object-qualified). **Custom objects (`*__c`) and all other standard objects (Account, Contact, …)
  need NO BusinessProcess — emit the RecordType alone; do not invent one.** **Scope limit:**
  picklist-value visibility per record type only — NOT general record-type authoring (compact
  layouts, page layouts, branding).

---

## 4. Master-Detail Relationship Rules CRITICAL

Master-Detail fields have **strict attribute restrictions** that differ from Lookup fields. Violating these rules causes deployment failures.

### Forbidden Attributes on Master-Detail Fields

**NEVER include these attributes on Master-Detail fields:**

| Forbidden Attribute | Why | What Happens |
|---------------------|-----|--------------|
| `<required>` | Master-Detail is ALWAYS required by design | Deployment error |
| `<deleteConstraint>` | Master-Detail ALWAYS cascades deletes | Deployment error |
| `<lookupFilter>` | Only supported on Lookup fields | Deployment error |

### Master-Detail vs Lookup Comparison

| Attribute | Master-Detail | Lookup |
|-----------|---------------|--------|
| `<required>` | ❌ FORBIDDEN | ✅ Optional |
| `<deleteConstraint>` | ❌ FORBIDDEN (always CASCADE) | ✅ Required (`SetNull`, `Restrict`, `Cascade`) |
| `<lookupFilter>` | ❌ FORBIDDEN | ✅ Optional |
| `<relationshipOrder>` | ✅ Required (0 or 1) | ❌ Not applicable |
| `<reparentableMasterDetail>` | ✅ Optional | ❌ Not applicable |
| `<writeRequiresMasterRead>` | ✅ Optional | ❌ Not applicable |

### INCORRECT — Master-Detail with forbidden attributes:

```xml
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
  <fullName>Account__c</fullName>
  <type>MasterDetail</type>
  <referenceTo>Account</referenceTo>
  <relationshipName>Contacts</relationshipName>
  <relationshipOrder>0</relationshipOrder>
  <required>true</required>                     <!-- WRONG: remove -->
  <deleteConstraint>Cascade</deleteConstraint>  <!-- WRONG: remove -->
  <lookupFilter>...</lookupFilter>              <!-- WRONG: remove entire block -->
</CustomField>
```

**Errors:** `Master-Detail Relationship Fields Cannot be Optional or Required` · `Can not specify 'deleteConstraint' for a CustomField of type MasterDetail` · `Lookup filters are only supported on Lookup Relationship Fields`

### CORRECT — Master-Detail field:

```xml
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
  <fullName>Account__c</fullName>
  <label>Account</label>
  <description>Links this record to its parent Account</description>
  <type>MasterDetail</type>
  <referenceTo>Account</referenceTo>
  <relationshipLabel>Child Records</relationshipLabel>
  <relationshipName>ChildRecords</relationshipName>
  <relationshipOrder>0</relationshipOrder>
  <reparentableMasterDetail>false</reparentableMasterDetail>
  <writeRequiresMasterRead>false</writeRequiresMasterRead>
  <!-- NO required, deleteConstraint, or lookupFilter -->
</CustomField>
```

### CORRECT — Lookup field (with optional attributes):

```xml
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
  <fullName>Related_Account__c</fullName>
  <label>Related Account</label>
  <description>Optional link to a related Account</description>
  <type>Lookup</type>
  <referenceTo>Account</referenceTo>
  <relationshipLabel>Related Records</relationshipLabel>
  <relationshipName>RelatedRecords</relationshipName>
  <required>false</required>
  <deleteConstraint>SetNull</deleteConstraint>
  <lookupFilter>
    <active>true</active>
    <filterItems>
      <field>Account.Type</field>
      <operation>equals</operation>
      <value>Customer</value>
    </filterItems>
    <isOptional>false</isOptional>
  </lookupFilter>
</CustomField>
```

### Additional Master-Detail Rules

- **Relationship Order:** First Master-Detail on object = `0`, second = `1`
- **Relationship Name:** Must be a plural PascalCase string (e.g., `Travel_Bookings`)
- **Junction Objects:** Use two Master-Detail fields for standard many-to-many (enables Roll-ups)
- **Limit:** Maximum 2 Master-Detail relationships per object. Use Lookup for additional relationships.

---

## 5. Roll-Up Summary Field Rules CRITICAL

Roll-up Summary fields have the **highest deployment failure rate**. Follow these rules exactly.

### Required Elements for Roll-Up Summary

| Element | Requirement | Format |
|---------|-------------|--------|
| `<type>` | Required | Always `Summary` |
| `<summaryOperation>` | Required | `count`, `sum`, `min`, or `max` |
| `<summaryForeignKey>` | Required | `ChildObject__c.MasterDetailField__c` |
| `<summarizedField>` | Conditional | Required for `sum`, `min`, `max`. NOT for `count` |

### Forbidden Elements on Roll-Up Summary

**NEVER include these attributes on Roll-Up Summary fields:**

| Forbidden Attribute | Why |
|---------------------|-----|
| `<precision>` | Summary inherits from summarized field |
| `<scale>` | Summary inherits from summarized field |
| `<required>` | Not applicable to Summary fields |
| `<length>` | Not applicable to Summary fields |

### Format Rules for summaryForeignKey and summarizedField

**CRITICAL:** Both `summaryForeignKey` and `summarizedField` MUST use the fully qualified format:

```text
ChildObjectAPIName__c.FieldAPIName__c
```

**Decision Logic:**
- `summaryForeignKey` = `ChildObject__c.MasterDetailFieldOnChild__c`
- `summarizedField` = `ChildObject__c.FieldToSummarize__c`

### INCORRECT — Roll-Up Summary with common errors:

```xml
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
  <fullName>Total_Amount__c</fullName>
  <label>Total Amount</label>
  <type>Summary</type>
  <precision>18</precision>           <!-- WRONG: Remove - inherited from source -->
  <scale>2</scale>                    <!-- WRONG: Remove - inherited from source -->
  <summaryOperation>sum</summaryOperation>
  <summaryForeignKey>Order__c</summaryForeignKey>        <!-- WRONG: Missing field name -->
  <summarizedField>Amount__c</summarizedField>           <!-- WRONG: Missing object name -->
</CustomField>
```

**Errors:**
- `Can not specify 'precision' for a CustomField of type Summary`
- `Must specify the name in the CustomObject.CustomField format (e.g. Account.MyNewCustomField)`

### CORRECT — Roll-Up Summary (SUM operation):

```xml
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
  <fullName>Total_Amount__c</fullName>
  <label>Total Amount</label>
  <description>Sum of all line item amounts</description>
  <inlineHelpText>Automatically calculated from child line items</inlineHelpText>
  <type>Summary</type>
  <summaryOperation>sum</summaryOperation>
  <summarizedField>Order_Line_Item__c.Amount__c</summarizedField>
  <summaryForeignKey>Order_Line_Item__c.Order__c</summaryForeignKey>
  <!-- NO precision, scale, required, or length -->
</CustomField>
```

**COUNT:** identical structure to SUM but **omit `<summarizedField>` entirely** (and keep `<summaryForeignKey>`). **MIN / MAX:** identical to SUM — just `<summaryOperation>min</summaryOperation>` or `max`, with `<summarizedField>` pointing at the field to find the minimum/maximum of. The Quick Reference table below covers all four.

### Roll-Up Summary Quick Reference

| Operation | summarizedField Required? | Use Case |
|-----------|---------------------------|----------|
| `count` | NO | Count number of child records |
| `sum` | YES | Add up numeric values |
| `min` | YES | Find smallest value |
| `max` | YES | Find largest value |

### Roll-Up Summary Prerequisites

- Roll-Up Summary fields can ONLY be created on the **parent** object in a Master-Detail relationship
- The child object MUST have a Master-Detail field pointing to this parent
- The summarized field must exist on the child object

---

## 6. Formula Field Rules

### Formula Result Types

A Formula is not a type itself. The `<formula>` tag is added to a field whose `<type>` is set to the **result data type**:
- `Checkbox`, `Currency`, `Date`, `DateTime`, `Number`, `Percent`, `Text`

### Formula XML Generation Rules

- The contents of the `<formula>` tag MUST be wrapped in a `<![CDATA[ ... ]]>` section. This prevents the XML parser from interpreting formula operators (like `&`, `<`, `>`) as XML markup.
- If the formula text itself contains the literal sequence `]]>`, escape it by breaking the CDATA block: e.g., `<![CDATA[Text_Field__c & "]]]]><![CDATA[>"]]>`
- NEVER use an attribute or tag named `returnType`. This does not exist in the Metadata API. The `<type>` tag defines the return data type of the formula result.

### formulaTreatBlanksAs Rule

**Decision Logic:**
- IF formula result type = `Number`, `Currency`, or `Percent` → set `<formulaTreatBlanksAs>BlankAsZero</formulaTreatBlanksAs>`
- IF formula result type = `Text`, `Date`, or `DateTime` → set `<formulaTreatBlanksAs>BlankAsBlank</formulaTreatBlanksAs>`

### INCORRECT — Using Formula as type:

```xml
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
  <fullName>Calculated_Value__c</fullName>
  <type>Formula</type>  <!-- WRONG: Formula is not a valid type -->
  <returnType>Number</returnType>  <!-- WRONG: returnType does not exist in Metadata API -->
  <formula>Field1__c + Field2__c</formula>  <!-- WRONG: Missing CDATA wrapper -->
</CustomField>
```

### CORRECT — Formula field:

```xml
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
  <fullName>Calculated_Value__c</fullName>
  <label>Calculated Value</label>
  <description>Sum of Field1 and Field2</description>
  <type>Number</type>  <!-- Result type, not "Formula" -->
  <precision>18</precision>
  <scale>2</scale>
  <formula><![CDATA[Field1__c + Field2__c]]></formula>
  <formulaTreatBlanksAs>BlankAsZero</formulaTreatBlanksAs>
</CustomField>
```

### Formula Field Dependencies & Functions

- Formula fields that reference other fields fail deployment if the referenced field doesn't exist or hasn't deployed yet — deploy referenced fields first.
- Use `ISPICKVAL()` (not `==`) for picklist comparisons.
- For the full formula-function reference (TEXT/VALUE/CASE/DAY/MONTH/DATEVALUE/ISCHANGED type rules), defer to the `platform-validation-rule-generate` skill, which owns formula-function correctness.

---

## 7. Common Deployment Errors

| Error Message | Cause | Fix |
|---------------|-------|-----|
| `ConversionError: Invalid XML tags or unable to find matching parent xml file for CustomField` | XML comments placed before the root `<CustomField>` element | Remove XML comments (`<!-- ... -->`) that appear before `<CustomField>` in the `.field-meta.xml` file |
| `Field [FieldName] does not exist. Check spelling.` | Referenced field does not exist or has not been deployed yet | Verify the referenced field exists and is deployed before this field |
| `DUPLICATE_DEVELOPER_NAME` | Field fullName already exists on the object | Use a unique business-driven name |
| `MAX_RELATIONSHIPS_EXCEEDED` | More than 2 Master-Detail or 15 Lookup fields on the object | Use Lookup for 3rd+ Master-Detail; review Lookup count |
| Reserved keyword error | Using `Order__c`, `Group__c`, etc. | Rename to `Status_Order__c`, etc. |
| `Value set must reference a value set name or define a value set, but not both` | `<valueSet>` has both `<valueSetName>` and `<valueSetDefinition>` | Keep exactly one (see Section 3.4) |
| `duplicate value found: [X] is defined multiple times` | Two `<value>` entries share a `<fullName>` | Make every picklist value `<fullName>` unique |
| `Invalid fullName` on a picklist value | Value `<fullName>` starts with a digit or contains hyphens | Start with a letter; no hyphens, no leading digit. Spaces ARE allowed — do NOT underscore them (see §3.4 value-name fidelity) |
| `Element ...picklist is not allowed` | Deprecated ≤37.0 dependent-picklist syntax (`<picklist>`/`<picklistValues>`/`<controllingFieldValues>`) | Use the modern `valueSettings`/`controllingFieldValue`/`valueName` form (Section 3.4) |

---

## 8. Verification Checklist

Before generating CustomField XML, verify:

### Universal Checks
- [ ] Does `<fullName>` use valid format and end in `__c`?
- [ ] Are `<description>` and `<inlineHelpText>` both populated and meaningful?
- [ ] Is `<label>` in Title Case?
- [ ] Are there no XML comments (`<!-- ... -->`) before the root `<CustomField>` element? (Comments before the root element break SDR's parser)

### Master-Detail Field Checks CRITICAL
- [ ] Is `<required>` attribute ABSENT? (Master-Detail is always required)
- [ ] Is `<deleteConstraint>` attribute ABSENT? (Master-Detail always cascades)
- [ ] Is `<lookupFilter>` block ABSENT? (Only for Lookup fields)
- [ ] Is `<relationshipOrder>` set to `0` or `1`?
- [ ] Is parent object's `<sharingModel>` set to `ControlledByParent`?

### Lookup Field Checks
- [ ] Is `<deleteConstraint>` set to `SetNull`, `Restrict`, or `Cascade`?
- [ ] Is `<relationshipName>` in plural PascalCase?

### Picklist Field Checks
- [ ] Does each `<valueSet>` contain EITHER `<valueSetName>` OR `<valueSetDefinition>` — never both?
- [ ] For a value-set reference: is `<restricted>true</restricted>` set?
- [ ] For a StandardValueSet reference: is the name the bare enum with NO `__c` (e.g. `Industry`)?
- [ ] For a GlobalValueSet reference: is the name the **bare** developer name with NO `__gvs` suffix?
- [ ] For dependent picklists: is `<controllingField>` set, with one `<valueSettings>` (`<controllingFieldValue>` + `<valueName>`) per pair?
- [ ] For dependent picklists: is the deprecated `<picklist>`/`<picklistValues>`/`<controllingFieldValues>` form ABSENT?
- [ ] Are all picklist value `<fullName>` values unique, start with a letter, and free of hyphens? (spaces are allowed — do NOT replace them with underscores, per the §3.4 value-name fidelity rule)

### Roll-Up Summary Field Checks CRITICAL
- [ ] Is `<precision>` attribute ABSENT?
- [ ] Is `<scale>` attribute ABSENT?
- [ ] Is `<summaryForeignKey>` in format `ChildObject__c.MasterDetailField__c`?
- [ ] For SUM/MIN/MAX: Is `<summarizedField>` in format `ChildObject__c.FieldName__c`?
- [ ] For COUNT: Is `<summarizedField>` ABSENT?
- [ ] Does the child object have a Master-Detail field to this parent?

### Formula Field Checks
- [ ] Is `<type>` set to result type (NOT "Formula")?
- [ ] Is `<formula>` content wrapped in `<![CDATA[ ... ]]>`?
- [ ] Is `<returnType>` attribute ABSENT? (does not exist in Metadata API)
- [ ] Is `<formulaTreatBlanksAs>` set to `BlankAsZero` for numeric results or `BlankAsBlank` for text/date results?
- [ ] Do all referenced fields exist and deploy before this field?

### Numeric Field Checks
- [ ] Is `scale ≤ precision`?
- [ ] Is `precision ≤ 18`?

### Text Area Checks
- [ ] For TextArea: Is `<length>255</length>` explicitly included?
- [ ] For LongTextArea/Html: Is `<visibleLines>` set?

### Relationship Limit Checks
- [ ] Are there 2 or fewer Master-Detail relationships on the object?
- [ ] Are there 15 or fewer Lookup relationships on the object?

### Naming Checks
- [ ] Is the API name free of reserved words (`Order`, `Group`, `Select`, etc.)?
- [ ] Is the API name unique on this object?

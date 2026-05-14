<!-- Parent: building-omnistudio-omniscript/SKILL.md -->

# OmniScript Element Type Reference

> **Applies to**: OmniStudio OmniScripts (OmniProcessType='OmniScript')
> **Companion**: See `best-practices.md` for design patterns and usage guidance

Each OmniScript element is stored as an `OmniProcessElement` child record. The `ElementType` field identifies the type, and the `PropertySetConfig` field contains a JSON blob with all configuration.

---

## Table of Contents

1. [Container Elements](#1-container-elements)
2. [Input Elements](#2-input-elements)
3. [Display Elements](#3-display-elements)
4. [Action Elements](#4-action-elements)
5. [Logic Elements](#5-logic-elements)
6. [Common PropertySetConfig Properties](#6-common-propertysetconfig-properties)

---

## 1. Container Elements

### Step

Top-level container representing a page/screen in the OmniScript wizard. All other elements are children of a Step.

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `label` | String | Yes | Display label shown in the step chart |
| `chartLabel` | String | No | Shortened label for the step chart indicator |
| `show` | Object | No | Conditional visibility expression |
| `knowledgeOptions` | Object | No | Knowledge article sidebar configuration |
| `validationRequired` | Boolean | No | Require all child validations to pass before advancing |
| `allowSaveForLater` | Boolean | No | Enable save & resume on this Step |
| `errorMessage` | String | No | Custom message when Step validation fails |
| `instruction` | String | No | Help text displayed at the top of the Step |
| `cancelLabel` | String | No | Custom label for the Cancel button |
| `nextLabel` | String | No | Custom label for the Next button |
| `previousLabel` | String | No | Custom label for the Previous button |
| `completeLabel` | String | No | Custom label for the final Submit button |
| `showPersistentComponent` | Array | No | Components visible across Steps (e.g., summary sidebar) |

```json
{
  "label": "Contact Information",
  "chartLabel": "Contact",
  "validationRequired": true,
  "instruction": "Please provide your contact details.",
  "nextLabel": "Continue to Service Details",
  "show": {
    "group": {
      "operator": "AND",
      "rules": [
        { "field": "HasContactInfo", "condition": "=", "data": "false" }
      ]
    }
  }
}
```

**Level**: 0 (always top-level)
**Order**: Determines the Step sequence in the wizard

---

### Conditional Block

Groups elements that appear or disappear together based on a condition.

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `conditionType` | String | Yes | `"group"` for complex conditions, `"simpleFormula"` for formula |
| `show` | Object | Yes | Condition expression (same syntax as Step `show`) |
| `label` | String | No | Display label for the block |

```json
{
  "conditionType": "group",
  "show": {
    "group": {
      "operator": "AND",
      "rules": [
        { "field": "CustomerType", "condition": "=", "data": "Business" }
      ]
    }
  }
}
```

**Level**: 1+ (child of a Step)

---

### Loop Block

Iterates over a data array and renders its child elements for each item.

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `loopData` | String | Yes | JSON path to the data array (e.g., `%LineItems%`) |
| `label` | String | No | Display label |
| `repeat` | String | No | Merge field referencing array length or explicit count |
| `allowAdd` | Boolean | No | Allow user to add items to the loop |
| `allowDelete` | Boolean | No | Allow user to remove items from the loop |
| `minItems` | Number | No | Minimum required items |
| `maxItems` | Number | No | Maximum allowed items |

```json
{
  "loopData": "%OrderLines%",
  "allowAdd": true,
  "allowDelete": true,
  "minItems": 1,
  "maxItems": 20,
  "label": "Order Line Items"
}
```

**Level**: 1+ (child of a Step)

---

### Edit Block

Provides inline editing of tabular data with row-level add/edit/delete.

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `editFields` | Array | Yes | Fields available for editing |
| `dataSource` | String | Yes | JSON path to the data array |
| `label` | String | No | Table heading |
| `columns` | Array | No | Column definitions (label, field, width) |
| `allowAdd` | Boolean | No | Allow adding rows |
| `allowDelete` | Boolean | No | Allow deleting rows |

```json
{
  "dataSource": "%ContactList%",
  "editFields": ["FirstName", "LastName", "Email", "Phone"],
  "columns": [
    { "label": "First Name", "field": "FirstName", "width": "25%" },
    { "label": "Last Name", "field": "LastName", "width": "25%" },
    { "label": "Email", "field": "Email", "width": "30%" },
    { "label": "Phone", "field": "Phone", "width": "20%" }
  ],
  "allowAdd": true,
  "allowDelete": true
}
```

**Level**: 1+ (child of a Step)

---

## 2. Input Elements

### Common Input Properties

All input elements share these base properties:

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `label` | String | Yes | Field label displayed to the user |
| `required` | Boolean | No | Whether the field must have a value |
| `readOnly` | Boolean | No | Display value without allowing edit |
| `defaultValue` | Mixed | No | Default value on load |
| `placeholder` | String | No | Placeholder text in the empty field |
| `helpText` | String | No | Tooltip or help text |
| `show` | Object | No | Conditional visibility expression |
| `accessibleInPreview` | Boolean | No | Include in review/confirmation Step |
| `hide` | Boolean | No | Hide from display (still in data JSON) |
| `debounce` | Number | No | Milliseconds to debounce input changes |
| `maskValue` | Boolean | No | Mask the displayed value (for sensitive data) |

---

### Text

Single-line text input.

| Property | Type | Description |
|----------|------|-------------|
| `pattern` | String | Regex pattern for validation |
| `patternErrorMessage` | String | Error shown when pattern fails |
| `minLength` | Number | Minimum character count |
| `maxLength` | Number | Maximum character count |
| `inputType` | String | HTML input type override (`text`, `email`, `tel`, `url`) |

```json
{
  "label": "First Name",
  "required": true,
  "placeholder": "Enter your first name",
  "minLength": 2,
  "maxLength": 80,
  "pattern": "^[a-zA-Z\\s'-]+$",
  "patternErrorMessage": "Name may only contain letters, spaces, hyphens, and apostrophes."
}
```

---

### Text Area

Multi-line text input.

| Property | Type | Description |
|----------|------|-------------|
| `rows` | Number | Number of visible text rows |
| `maxLength` | Number | Maximum character count |
| `richText` | Boolean | Enable rich text editing |

```json
{
  "label": "Description",
  "rows": 4,
  "maxLength": 32000,
  "placeholder": "Describe the issue in detail..."
}
```

---

### Number

Numeric input with formatting.

| Property | Type | Description |
|----------|------|-------------|
| `min` | Number | Minimum value |
| `max` | Number | Maximum value |
| `step` | Number | Increment step |
| `format` | String | Display format (e.g., `"0,0.00"`) |
| `precision` | Number | Decimal precision |

```json
{
  "label": "Quantity",
  "required": true,
  "min": 1,
  "max": 9999,
  "step": 1,
  "format": "0,0",
  "defaultValue": 1
}
```

---

### Currency

Currency input with locale formatting.

| Property | Type | Description |
|----------|------|-------------|
| `currencyCode` | String | ISO currency code (e.g., `"USD"`) |
| `min` | Number | Minimum value |
| `max` | Number | Maximum value |
| `precision` | Number | Decimal precision |

```json
{
  "label": "Requested Amount",
  "required": true,
  "currencyCode": "USD",
  "min": 0.01,
  "max": 1000000,
  "precision": 2
}
```

---

### Date

Date picker input.

| Property | Type | Description |
|----------|------|-------------|
| `dateFormat` | String | Display format (e.g., `"MM/DD/YYYY"`) |
| `minDate` | String | Earliest selectable date (`"TODAY"`, `"-30"`, `"2025-01-01"`) |
| `maxDate` | String | Latest selectable date (`"TODAY"`, `"+365"`) |

```json
{
  "label": "Requested Start Date",
  "required": true,
  "dateFormat": "MM/DD/YYYY",
  "minDate": "TODAY",
  "maxDate": "+365"
}
```

---

### Date/Time

Combined date and time picker.

| Property | Type | Description |
|----------|------|-------------|
| `dateFormat` | String | Date display format |
| `timeFormat` | String | Time display format (`"HH:mm"`, `"hh:mm A"`) |
| `minDate` | String | Earliest selectable date |
| `maxDate` | String | Latest selectable date |

```json
{
  "label": "Appointment Date & Time",
  "dateFormat": "MM/DD/YYYY",
  "timeFormat": "hh:mm A"
}
```

---

### Time

Time-only picker.

| Property | Type | Description |
|----------|------|-------------|
| `timeFormat` | String | Time display format |
| `minuteInterval` | Number | Interval for minute selection (e.g., 15, 30) |

```json
{
  "label": "Preferred Time",
  "timeFormat": "hh:mm A",
  "minuteInterval": 15
}
```

---

### Checkbox

Boolean toggle input.

| Property | Type | Description |
|----------|------|-------------|
| `defaultValue` | Boolean | Initial checked state |
| `checkLabel` | String | Label displayed next to the checkbox |

```json
{
  "label": "Terms and Conditions",
  "checkLabel": "I agree to the terms and conditions",
  "required": true,
  "defaultValue": false
}
```

---

### Radio

Radio button group for single selection.

| Property | Type | Description |
|----------|------|-------------|
| `options` | Array | Static options `[{ "name": "label", "value": "val" }]` |
| `optionSource` | Object | Data-driven options from a DataRaptor or data JSON |
| `orientation` | String | `"horizontal"` or `"vertical"` |

```json
{
  "label": "Contact Preference",
  "required": true,
  "orientation": "vertical",
  "options": [
    { "name": "Email", "value": "Email" },
    { "name": "Phone", "value": "Phone" },
    { "name": "Mail", "value": "Mail" }
  ]
}
```

---

### Select

Dropdown selection input.

| Property | Type | Description |
|----------|------|-------------|
| `options` | Array | Static options `[{ "name": "label", "value": "val" }]` |
| `optionSource` | Object | Data-driven options configuration |
| `multiselect` | Boolean | Allow multiple selections (use Multi-select element instead) |

```json
{
  "label": "State",
  "required": true,
  "options": [
    { "name": "California", "value": "CA" },
    { "name": "New York", "value": "NY" },
    { "name": "Texas", "value": "TX" }
  ]
}
```

---

### Multi-select

Multiple item selection input.

| Property | Type | Description |
|----------|------|-------------|
| `options` | Array | Static options |
| `optionSource` | Object | Data-driven options configuration |
| `maxSelections` | Number | Maximum number of selections allowed |
| `minSelections` | Number | Minimum number of selections required |

```json
{
  "label": "Interested Products",
  "options": [
    { "name": "Product A", "value": "ProdA" },
    { "name": "Product B", "value": "ProdB" },
    { "name": "Product C", "value": "ProdC" }
  ],
  "maxSelections": 3
}
```

---

### Type Ahead

Search/autocomplete input that queries a data source as the user types.

| Property | Type | Description |
|----------|------|-------------|
| `dataSource` | String | DataRaptor bundle or IP to query |
| `searchField` | String | Field to search against |
| `displayField` | String | Field to display in results |
| `valueField` | String | Field to store as the selected value |
| `minCharacters` | Number | Minimum characters before search fires |
| `maxResults` | Number | Maximum results to display |
| `debounce` | Number | Milliseconds to debounce search requests |
| `inputMap` | Object | Additional parameters to pass to the data source |

```json
{
  "label": "Search Account",
  "dataSource": "DR_SearchAccounts",
  "searchField": "Name",
  "displayField": "Name",
  "valueField": "Id",
  "minCharacters": 3,
  "maxResults": 10,
  "debounce": 300,
  "inputMap": {
    "RecordType": "Customer"
  }
}
```

---

### Email

Email input with built-in format validation.

| Property | Type | Description |
|----------|------|-------------|
| `placeholder` | String | Placeholder text |
| `pattern` | String | Override regex (default email pattern is built-in) |

```json
{
  "label": "Email Address",
  "required": true,
  "placeholder": "name@example.com"
}
```

---

### Telephone

Phone number input with optional masking.

| Property | Type | Description |
|----------|------|-------------|
| `mask` | String | Input mask pattern (e.g., `"(999) 999-9999"`) |
| `placeholder` | String | Placeholder text |

```json
{
  "label": "Phone Number",
  "mask": "(999) 999-9999",
  "placeholder": "(555) 123-4567"
}
```

---

### URL

URL input with built-in format validation.

| Property | Type | Description |
|----------|------|-------------|
| `placeholder` | String | Placeholder text |
| `pattern` | String | Override regex for URL validation |

```json
{
  "label": "Website",
  "placeholder": "https://www.example.com"
}
```

---

### Password

Masked text input for sensitive values.

| Property | Type | Description |
|----------|------|-------------|
| `minLength` | Number | Minimum password length |
| `maxLength` | Number | Maximum password length |
| `pattern` | String | Complexity regex |
| `patternErrorMessage` | String | Error when pattern fails |

```json
{
  "label": "Temporary PIN",
  "required": true,
  "minLength": 6,
  "maxLength": 6,
  "pattern": "^\\d{6}$",
  "patternErrorMessage": "PIN must be exactly 6 digits."
}
```

---

### Range

Slider input for selecting a value within a range.

| Property | Type | Description |
|----------|------|-------------|
| `min` | Number | Minimum value |
| `max` | Number | Maximum value |
| `step` | Number | Increment step |
| `showValue` | Boolean | Display the selected value |

```json
{
  "label": "Satisfaction Rating",
  "min": 1,
  "max": 10,
  "step": 1,
  "showValue": true,
  "defaultValue": 5
}
```

---

### Signature

Signature capture pad for e-signatures.

| Property | Type | Description |
|----------|------|-------------|
| `penColor` | String | Drawing color (hex or name) |
| `backgroundColor` | String | Pad background color |
| `width` | Number | Pad width in pixels |
| `height` | Number | Pad height in pixels |
| `clearLabel` | String | Label for the clear button |

```json
{
  "label": "Customer Signature",
  "required": true,
  "penColor": "#000000",
  "backgroundColor": "#FFFFFF",
  "width": 400,
  "height": 150,
  "clearLabel": "Clear Signature"
}
```

---

### File

File upload input.

| Property | Type | Description |
|----------|------|-------------|
| `maxFileSize` | Number | Maximum file size in bytes |
| `allowedExtensions` | String | Comma-separated allowed extensions |
| `maxFiles` | Number | Maximum number of files |
| `uploadLabel` | String | Custom upload button label |

```json
{
  "label": "Supporting Documents",
  "maxFileSize": 5242880,
  "allowedExtensions": "pdf,jpg,png,docx",
  "maxFiles": 5,
  "uploadLabel": "Upload Document"
}
```

---

## 3. Display Elements

### Text Block

Static content display. Supports HTML and merge fields.

| Property | Type | Description |
|----------|------|-------------|
| `textContent` | String | HTML content to display |
| `HTMLTemplateId` | String | Reference to an HTML template |
| `sanitize` | Boolean | Sanitize HTML content |

```json
{
  "textContent": "<p>Welcome, <strong>%FirstName%</strong>. Please review the following information.</p>",
  "sanitize": true
}
```

---

### Headline

Section heading element.

| Property | Type | Description |
|----------|------|-------------|
| `text` | String | Heading text |
| `level` | Number | Heading level (1-6, maps to h1-h6) |

```json
{
  "text": "Account Details",
  "level": 2
}
```

---

### Aggregate

Calculated summary display based on data in the OmniScript JSON.

| Property | Type | Description |
|----------|------|-------------|
| `aggregateExpression` | String | Calculation expression |
| `format` | String | Display format |
| `dataType` | String | Result data type (`"number"`, `"currency"`, `"percent"`) |

```json
{
  "label": "Total Amount",
  "aggregateExpression": "SUM(%OrderLines:Amount%)",
  "format": "$0,0.00",
  "dataType": "currency"
}
```

---

### Disclosure

Expandable/collapsible content section.

| Property | Type | Description |
|----------|------|-------------|
| `label` | String | Clickable section header |
| `defaultExpanded` | Boolean | Initial expand state |

```json
{
  "label": "Additional Information",
  "defaultExpanded": false
}
```

---

### Image

Image display element.

| Property | Type | Description |
|----------|------|-------------|
| `imageURL` | String | URL to the image |
| `altText` | String | Alternative text for accessibility |
| `width` | String | Display width (px or %) |
| `height` | String | Display height (px or %) |

```json
{
  "imageURL": "/resource/CompanyLogo",
  "altText": "Company Logo",
  "width": "200px"
}
```

---

### Chart

Data visualization element.

| Property | Type | Description |
|----------|------|-------------|
| `chartType` | String | Chart type (`"bar"`, `"pie"`, `"line"`, `"donut"`) |
| `dataSource` | String | JSON path to chart data |
| `labelField` | String | Field for chart labels |
| `valueField` | String | Field for chart values |
| `title` | String | Chart title |

```json
{
  "chartType": "pie",
  "dataSource": "%CoverageBreakdown%",
  "labelField": "CoverageType",
  "valueField": "Amount",
  "title": "Coverage Distribution"
}
```

---

## 4. Action Elements

### DataRaptor Extract Action

Executes a DataRaptor Extract to pull data from Salesforce.

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `bundle` | String | Yes | DataRaptor Extract bundle name |
| `inputMap` | Object | No | Input parameters mapped from data JSON |
| `outputMap` | Object | No | Output mapping to data JSON keys |
| `executionConditionFormula` | String | No | Formula to conditionally execute |
| `showError` | Boolean | No | Display error on failure |
| `errorMessage` | String | No | Custom error message |
| `responseJSONPath` | String | No | Path to extract from response |
| `sendOnlyIfNotEmpty` | Boolean | No | Skip if input values are empty |

```json
{
  "bundle": "DR_ExtractAccountDetails",
  "inputMap": {
    "AccountId": "%SelectedAccountId%"
  },
  "outputMap": {
    "AccountName": "AccountName",
    "BillingStreet": "BillingStreet",
    "BillingCity": "BillingCity",
    "BillingState": "BillingState",
    "BillingPostalCode": "BillingPostalCode"
  },
  "executionConditionFormula": "IF(%SelectedAccountId% != '', true, false)",
  "showError": true,
  "errorMessage": "Unable to retrieve account details. Please try again."
}
```

---

### DataRaptor Load Action

Executes a DataRaptor Load to write data to Salesforce.

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `bundle` | String | Yes | DataRaptor Load bundle name |
| `inputMap` | Object | No | Input parameters from data JSON |
| `executionConditionFormula` | String | No | Conditional execution formula |
| `showError` | Boolean | No | Display error on failure |
| `errorMessage` | String | No | Custom error message |

```json
{
  "bundle": "DR_CreateServiceRequest",
  "inputMap": {
    "AccountId": "%SelectedAccountId%",
    "Subject": "%RequestSubject%",
    "Description": "%RequestDescription%",
    "Priority": "%RequestPriority%"
  },
  "showError": true,
  "errorMessage": "Failed to create the service request. Please contact support."
}
```

---

### Integration Procedure Action

Calls a server-side Integration Procedure.

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `ipMethod` | String | Yes | IP identifier (`"Type_SubType"` format) |
| `inputMap` | Object | No | Input parameters from data JSON |
| `outputMap` | Object | No | Output mapping to data JSON keys |
| `remoteOptions` | Object | No | Execution options (chainable, preTransform, postTransform) |
| `executionConditionFormula` | String | No | Conditional execution formula |
| `showError` | Boolean | No | Display error on failure |
| `errorMessage` | String | No | Custom error message |
| `remoteTimeout` | Number | No | Timeout in milliseconds |
| `responseJSONPath` | String | No | Path to extract from response |
| `preTransformBundle` | String | No | DataRaptor to transform input before sending |
| `postTransformBundle` | String | No | DataRaptor to transform output after receiving |

```json
{
  "ipMethod": "Eligibility_CheckMember",
  "inputMap": {
    "MemberId": "%MemberId%",
    "ServiceDate": "%RequestedDate%"
  },
  "outputMap": {
    "IsEligible": "EligibilityResult",
    "PlanName": "MemberPlan",
    "CopayAmount": "EstimatedCopay"
  },
  "remoteOptions": {
    "preTransformBundle": "DR_TransformEligibilityInput",
    "postTransformBundle": "DR_TransformEligibilityOutput"
  },
  "remoteTimeout": 30000,
  "showError": true,
  "errorMessage": "Eligibility check failed. Please verify member ID and try again."
}
```

---

### Remote Action

Calls an Apex @RemoteAction method or REST endpoint.

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `remoteClass` | String | Yes | Apex class name |
| `remoteMethod` | String | Yes | Method name |
| `inputMap` | Object | No | Input parameters |
| `outputMap` | Object | No | Output mapping |
| `remoteOptions` | Object | No | Execution options |
| `showError` | Boolean | No | Display error on failure |

```json
{
  "remoteClass": "CustomEligibilityService",
  "remoteMethod": "checkEligibility",
  "inputMap": {
    "memberId": "%MemberId%"
  },
  "outputMap": {
    "result": "EligibilityResult"
  },
  "showError": true
}
```

---

### Navigate Action

Navigates to another page, OmniScript, or URL.

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `targetType` | String | Yes | `"OmniScript"`, `"URL"`, `"Record"`, `"FlexCard"` |
| `targetId` | String | Conditional | Record ID or OmniScript Type_SubType_Language |
| `URL` | String | Conditional | Target URL (when targetType is `"URL"`) |
| `params` | Object | No | Parameters to pass to the target |
| `openInNewTab` | Boolean | No | Open in a new browser tab |

```json
{
  "targetType": "OmniScript",
  "targetId": "ServiceRequest_FollowUp_English",
  "params": {
    "CaseId": "%CreatedCaseId%",
    "AccountId": "%SelectedAccountId%"
  }
}
```

---

### Email Action

Sends an email using a Salesforce email template.

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `emailTemplateId` | String | Yes | Email template ID or developer name |
| `recipientMap` | Object | No | Recipient field mappings |
| `senderAddress` | String | No | Override sender address |

```json
{
  "emailTemplateId": "ServiceRequestConfirmation",
  "recipientMap": {
    "toAddress": "%ContactEmail%",
    "whatId": "%CreatedCaseId%"
  }
}
```

---

### DocuSign Envelope Action

Triggers a DocuSign envelope for e-signature.

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `templateId` | String | Yes | DocuSign template ID |
| `recipientMap` | Object | Yes | Signer mappings |
| `prefillTabs` | Object | No | Pre-populated tab values |

```json
{
  "templateId": "abc123-template-id",
  "recipientMap": {
    "signer1": {
      "name": "%CustomerName%",
      "email": "%CustomerEmail%"
    }
  }
}
```

---

## 5. Logic Elements

### Set Values

Assigns values to data JSON keys. Used for data transformation, defaults, and computed values.

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `elementValueMap` | Object | Yes | Key-value pairs to set in the data JSON |
| `executionConditionFormula` | String | No | Conditional execution |

```json
{
  "elementValueMap": {
    "FullName": "CONCAT(%FirstName%, ' ', %LastName%)",
    "SubmissionDate": "TODAY()",
    "Status": "Submitted",
    "RequestId": "CONCAT('SR-', %CaseNumber%)"
  }
}
```

---

### Validation

Validates data using a formula expression. Blocks Step advancement when validation fails.

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `validationFormula` | String | Yes | Formula that must evaluate to `true` to pass |
| `errorMessage` | String | Yes | Error displayed when validation fails |

```json
{
  "validationFormula": "%EndDate% > %StartDate%",
  "errorMessage": "End date must be after the start date."
}
```

Multiple conditions example:
```json
{
  "validationFormula": "AND(%Age% >= 18, %Age% <= 120)",
  "errorMessage": "Age must be between 18 and 120."
}
```

---

### Formula

Calculates a value using a formula expression and stores the result in the data JSON.

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `expression` | String | Yes | Formula expression |
| `dataType` | String | No | Result type (`"number"`, `"text"`, `"boolean"`, `"date"`) |
| `decimalPlaces` | Number | No | Decimal precision for number results |

```json
{
  "label": "TotalWithTax",
  "expression": "%SubTotal% * (1 + %TaxRate% / 100)",
  "dataType": "number",
  "decimalPlaces": 2
}
```

---

### Submit Action

Final submission action that processes collected data. Typically the last element in the last Step.

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `postMessage` | String | No | Success message displayed after submission |
| `postSuccessMessage` | String | No | Message shown on the post-submit screen |
| `preTransformBundle` | String | No | DataRaptor to transform data before submission |
| `postTransformBundle` | String | No | DataRaptor to transform data after submission |
| `submitLabel` | String | No | Custom label for the submit button |
| `validationRequired` | Boolean | No | Re-validate all Steps before submitting |
| `redirectPageName` | String | No | Page to redirect after submission |
| `redirectTemplateUrl` | String | No | URL template for redirect |

```json
{
  "postMessage": "Your service request has been submitted successfully.",
  "preTransformBundle": "DR_PrepareSubmission",
  "postTransformBundle": "DR_ProcessResponse",
  "submitLabel": "Submit Request",
  "validationRequired": true,
  "redirectTemplateUrl": "/case/%CreatedCaseId%"
}
```

---

## 6. Common PropertySetConfig Properties

These properties apply across multiple element types.

### Conditional Visibility (`show`)

Controls whether an element is rendered.

```json
{
  "show": {
    "group": {
      "operator": "AND",
      "rules": [
        { "field": "CustomerType", "condition": "=", "data": "Business" },
        { "field": "AnnualRevenue", "condition": ">", "data": "1000000" }
      ]
    }
  }
}
```

**Operators**: `AND`, `OR`
**Conditions**: `=`, `!=`, `>`, `<`, `>=`, `<=`, `contains`, `starts with`, `ends with`, `is null`, `is not null`

### Nested Groups

```json
{
  "show": {
    "group": {
      "operator": "OR",
      "rules": [
        { "field": "Status", "condition": "=", "data": "Active" },
        {
          "group": {
            "operator": "AND",
            "rules": [
              { "field": "Status", "condition": "=", "data": "Pending" },
              { "field": "HasApproval", "condition": "=", "data": "true" }
            ]
          }
        }
      ]
    }
  }
}
```

### Merge Fields

Reference data JSON values in element configuration using `%FieldName%` syntax.

| Syntax | Description |
|--------|-------------|
| `%FieldName%` | Direct reference to a data JSON key |
| `%Step1:FieldName%` | Qualified reference with Step prefix |
| `%LoopBlock:CurrentItem:FieldName%` | Reference within a Loop Block iteration |
| `%ParentOmni:FieldName%` | Reference to parent OmniScript data (when embedded) |
| `%UserInfo:FirstName%` | Current user information |

### Layout Properties

| Property | Type | Description |
|----------|------|-------------|
| `colSize` | Number | Column width (1-12 grid system) |
| `offset` | Number | Column offset (1-12) |
| `horizontalAlign` | String | `"left"`, `"center"`, `"right"` |
| `verticalAlign` | String | `"top"`, `"middle"`, `"bottom"` |

### Data Binding

| Property | Type | Description |
|----------|------|-------------|
| `JSONPath` | String | Custom JSON path for storing the element value |
| `responseJSONPath` | String | Path to extract from action response |
| `inputMap` | Object | Maps data JSON values to action input parameters |
| `outputMap` | Object | Maps action output to data JSON keys |

---

## Quick Reference: Element Type to OmniProcessElement.ElementType

| Display Name | ElementType Value | Category |
|-------------|-------------------|----------|
| Step | `Step` | Container |
| Conditional Block | `Conditional Block` | Container |
| Loop Block | `Loop Block` | Container |
| Edit Block | `Edit Block` | Container |
| Text | `Text` | Input |
| Text Area | `Text Area` | Input |
| Number | `Number` | Input |
| Currency | `Currency` | Input |
| Date | `Date` | Input |
| Date/Time | `Date/Time` | Input |
| Time | `Time` | Input |
| Checkbox | `Checkbox` | Input |
| Radio | `Radio` | Input |
| Select | `Select` | Input |
| Multi-select | `Multi-select` | Input |
| Type Ahead | `Type Ahead` | Input |
| Email | `Email` | Input |
| Telephone | `Telephone` | Input |
| URL | `URL` | Input |
| Password | `Password` | Input |
| Range | `Range` | Input |
| Signature | `Signature` | Input |
| File | `File` | Input |
| Text Block | `Text Block` | Display |
| Headline | `Headline` | Display |
| Aggregate | `Aggregate` | Display |
| Disclosure | `Disclosure` | Display |
| Image | `Image` | Display |
| Chart | `Chart` | Display |
| DataRaptor Extract Action | `DataRaptor Extract Action` | Action |
| DataRaptor Load Action | `DataRaptor Load Action` | Action |
| Integration Procedure Action | `Integration Procedure Action` | Action |
| Remote Action | `Remote Action` | Action |
| Navigate Action | `Navigate Action` | Action |
| Email Action | `Email Action` | Action |
| DocuSign Envelope Action | `DocuSign Envelope Action` | Action |
| Set Values | `Set Values` | Logic |
| Validation | `Validation` | Logic |
| Formula | `Formula` | Logic |
| Submit Action | `Submit Action` | Logic |

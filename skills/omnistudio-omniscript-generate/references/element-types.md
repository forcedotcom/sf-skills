<!-- Parent: omnistudio-omniscript-generate/SKILL.md -->

# OmniScript Element Type Reference

> **Applies to**: OmniStudio OmniScripts (OmniProcessType='OmniScript')
> **Companion**: See `best-practices.md` for design patterns and usage guidance

Each OmniScript element is stored as an `OmniProcessElement` child record. The `Type` field identifies the type, and the `PropertySetConfig` field contains a JSON blob with all configuration.

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

### Block (conditional view)

In OmniScripts, a group of elements that appear or disappear together is a `Block` element (Type `Block`) with a `show` condition. (`Conditional Block` is an Integration Procedure element.)

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `show` | Object | Yes | Condition expression (same syntax as Step `show`) |
| `conditionType` | String | No | What happens when `show` is false: `"Hide if False"` (default), `"Readonly if False"`, `"Optional if False"` |
| `label` | String | No | Display label for the block |
| `collapse` | Boolean | No | Render as a collapsible section |

```json
{
  "label": "Business Details",
  "conditionType": "Hide if False",
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

### Block (repeat)

Repeats its child elements for each item of an array in the data JSON. In OmniScripts this is a `Block` element with `repeat: true` (`Loop Block` is an Integration Procedure element). The array is the data JSON node whose key equals the Block's element name.

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `repeat` | Boolean | Yes | `true` to repeat the Block per array item |
| `repeatClone` | Boolean | No | When the user adds an item, clone the values of the previous item |
| `repeatLimit` | Number | No | Maximum number of items the user can add |
| `repeatLimitMin` | Number | No | Minimum number of items |
| `addLabel` / `removeLabel` | String | No | Labels for the add/remove controls |
| `label` | String | No | Display label |

```json
{
  "label": "Order Line Items",
  "repeat": true,
  "repeatClone": false,
  "repeatLimit": 20
}
```

Inside a repeat Block, reference the current item's fields with `|n` (e.g. `%Step1:OrderLines|n:Amount%`).

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
| `help` | Boolean | No | Show a help icon |
| `helpText` | String | No | Tooltip or help text (shown when `help` is true) |
| `show` | Object | No | Conditional visibility expression |
| `accessibleInFutureSteps` | Boolean | No | Keep the element's value accessible to later Steps |
| `hide` | Boolean | No | Hide from display (still in data JSON) |
| `debounceValue` | Number | No | Milliseconds to debounce input changes |
| `mask` | String | No | Input mask pattern |
| `conditionType` | String | No | Effect of `show` when false: `"Hide if False"`, `"Readonly if False"`, `"Optional if False"` |
| `controlWidth` | Number | No | Column width (1-12 grid) |

---

### Text

Single-line text input.

| Property | Type | Description |
|----------|------|-------------|
| `pattern` | String | Regex pattern for validation |
| `ptrnErrText` | String | Error shown when pattern fails |
| `minLength` | Number | Minimum character count |
| `maxLength` | Number | Maximum character count |

```json
{
  "label": "First Name",
  "required": true,
  "placeholder": "Enter your first name",
  "minLength": 2,
  "maxLength": 80,
  "pattern": "^[a-zA-Z\\s'-]+$",
  "ptrnErrText": "Name may only contain letters, spaces, hyphens, and apostrophes."
}
```

---

### Text Area

Multi-line text input.

| Property | Type | Description |
|----------|------|-------------|
| `maxLength` | Number | Maximum character count |
| `minLength` | Number | Minimum character count |

```json
{
  "label": "Description",
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
| `dateFormat` | String | Display format (e.g., `"d MMM yyyy"`, `"MM-dd-yyyy"`) |
| `modelDateFormat` | String | Format stored in the data JSON (e.g., `"yyyy-MM-dd"`) |
| `dateType` | String | Data type stored (`"string"` or `"date"`) |
| `minDate` | String | Earliest selectable date |
| `maxDate` | String | Latest selectable date |

```json
{
  "label": "Requested Start Date",
  "required": true,
  "dateType": "string",
  "modelDateFormat": "yyyy-MM-dd",
  "dateFormat": "d MMM yyyy",
  "minDate": "",
  "maxDate": ""
}
```

---

### Date/Time (Local)

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
| `options` | Array | Static options `[{ "name": "<stored value>", "value": "<display label>" }]` (`name` is saved to the data JSON, `value` is shown) |
| `optionSource` | Object | Options from a picklist: `{ "type": "SObject", "source": "Object__c.Field__c" }` (or `"image"`, or `""` for static) |
| `horizontalMode` | Boolean | Lay options out horizontally |

```json
{
  "label": "Contact Preference",
  "required": true,
  "horizontalMode": false,
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
| `options` | Array | Static options `[{ "name": "<stored value>", "value": "<display label>" }]` (`name` is saved to the data JSON, `value` is shown) |
| `optionSource` | Object | Options from a picklist: `{ "type": "SObject", "source": "Object__c.Field__c" }` (or `""` for static) |
| `controllingField` | Object | Dependent picklist: `{ "element": "<ElementName>", "type": "SObject", "source": "Object__c.ControllingField__c" }` |

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
| `options` | Array | Static options `[{ "name": "<stored value>", "value": "<display label>" }]` |
| `optionSource` | Object | Options from a picklist: `{ "type": "SObject", "source": "Object__c.Field__c" }` (or `""` for static) |
| `controllingField` | Object | Dependent picklist configuration (same as Select) |

```json
{
  "label": "Interested Products",
  "options": [
    { "name": "Product A", "value": "ProdA" },
    { "name": "Product B", "value": "ProdB" },
    { "name": "Product C", "value": "ProdC" }
  ]
}
```

---

### Type Ahead Block

Search/autocomplete input (Type `Type Ahead Block`). Matches are taken either from a node in the data JSON or from a child action element (DataRaptor Extract / IP / Remote Action) placed inside the block.

| Property | Type | Description |
|----------|------|-------------|
| `typeAheadKey` | String | Field of each result object to search and display |
| `useDataJson` | Boolean | Search a list already in the data JSON instead of calling an action |
| `dataJsonPath` | String | Data JSON path to the list (when `useDataJson` is true) |
| `minSearchLength` | Number | Minimum characters before search fires |
| `callFrequency` | Number | Milliseconds between search calls |
| `enableLookup` | Boolean | Show as a lookup (list all options on click) |
| `disableDataFilter` | Boolean | Do not filter results client-side |
| `editMode` / `hideEditButton` | Boolean | Allow editing the selected value |

```json
{
  "label": "Search Account",
  "typeAheadKey": "Name",
  "useDataJson": true,
  "dataJsonPath": "AccountList",
  "minSearchLength": 3,
  "callFrequency": 300,
  "enableLookup": false
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
| `ptrnErrText` | String | Error when pattern fails |

```json
{
  "label": "Temporary PIN",
  "required": true,
  "minLength": 6,
  "maxLength": 6,
  "pattern": "^\\d{6}$",
  "ptrnErrText": "PIN must be exactly 6 digits."
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
| `fileSizeLimit` | Number | Maximum file size (MB) |
| `minFileSizeLimit` | Number | Minimum file size (MB) |
| `fileExtension` | String | Comma-separated allowed extensions (e.g. `".pdf,.docx"`) |
| `allowMultiple` | Boolean | Allow multiple files |
| `uploadContDoc` | Boolean | Upload as ContentDocument |
| `contentParentId` | Array | Records to link the uploaded files to |

```json
{
  "label": "Supporting Documents",
  "fileSizeLimit": 5,
  "fileExtension": ".pdf,.jpg,.png,.docx",
  "allowMultiple": true,
  "uploadContDoc": true
}
```

---

## 3. Display Elements

### Text Block

Static content display. Supports HTML and merge fields.

| Property | Type | Description |
|----------|------|-------------|
| `text` | String | HTML content to display |
| `HTMLTemplateId` | String | Reference to an HTML template |
| `sanitize` | Boolean | Sanitize HTML content |
| `dataJSON` | Boolean | Display the data JSON (debug) |

```json
{
  "text": "<p>Welcome, <strong>%FirstName%</strong>. Please review the following information.</p>",
  "sanitize": false
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

## 4. Action Elements

### DataRaptor Extract Action

Executes a DataRaptor Extract to pull data from Salesforce.

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `bundle` | String | Yes | DataRaptor Extract bundle name |
| `dataRaptor Input Parameters` | Array | No | Input parameters: `[{ "element": "<data JSON path>", "inputParam": "<DR input key>" }]` |
| `responseJSONPath` | String | No | Path to extract from response |
| `responseJSONNode` | String | No | Data JSON node to store the response under |
| `ignoreCache` | Boolean | No | Bypass the response cache |
| `show` | Object | No | Run only when the condition is true |
| `enableDefaultAbort` | Boolean | No | Show the default abort option on failure |
| `failureAbortMessage` | String | No | Message shown when the user aborts after a failure |
| `errorMessage` | Object | No | `{ "custom": [], "default": null }` |
| `validationRequired` | String | No | `"Step"`, `"Submit"` or `"None"` |

```json
{
  "bundle": "DR_ExtractAccountDetails",
  "dataRaptor Input Parameters": [
    { "element": "SelectedAccountId", "inputParam": "AccountId" }
  ],
  "responseJSONPath": "",
  "responseJSONNode": "",
  "show": {
    "group": { "operator": "AND", "rules": [ { "field": "SelectedAccountId", "condition": "<>", "data": null } ] }
  },
  "enableDefaultAbort": false,
  "failureAbortMessage": "Are you sure?",
  "errorMessage": { "custom": [], "default": null },
  "validationRequired": "Step"
}
```

---

### DataRaptor Post Action

Executes a DataRaptor Load to write data to Salesforce (Type `DataRaptor Post Action`).

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `bundle` | String | Yes | DataRaptor Load bundle name |
| `sendJSONPath` | String | No | Data JSON path to send (empty = whole data JSON) |
| `sendJSONNode` | String | No | Key to wrap the sent JSON under |
| `show` | Object | No | Run only when the condition is true |
| `enableDefaultAbort` / `failureAbortMessage` / `errorMessage` | — | No | Failure handling (see DataRaptor Extract Action) |

```json
{
  "bundle": "DR_CreateServiceRequest",
  "sendJSONPath": "ServiceRequestStep",
  "sendJSONNode": "",
  "errorMessage": { "custom": [], "default": null }
}
```

### DataRaptor Transform Action

Reshapes the data JSON with a Transform Data Mapper.

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `bundle` | String | Yes | DataRaptor Transform bundle name |
| `sendJSONPath` / `sendJSONNode` | String | No | What to send |
| `responseJSONPath` / `responseJSONNode` | String | No | Where to store the result |

---

### Integration Procedure Action

Calls a server-side Integration Procedure.

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `integrationProcedureKey` | String | Yes | IP identifier (`"Type_SubType"` format) |
| `extraPayload` | Object | No | Extra input key-values (merge fields allowed) |
| `sendOnlyExtraPayload` | Boolean | No | Send only `extraPayload` instead of the whole data JSON |
| `sendJSONPath` / `sendJSONNode` | String | No | Send a sub-node of the data JSON / wrap it under a key |
| `responseJSONPath` | String | No | Path to extract from response |
| `responseJSONNode` | String | No | Data JSON node to store the response under |
| `remoteOptions` | Object | No | Execution options (`chainable`, `useFuture`, `preTransformBundle`, `postTransformBundle`) |
| `preTransformBundle` / `postTransformBundle` | String | No | DataRaptor to transform input before sending / output after receiving |
| `remoteTimeout` | Number | No | Timeout in milliseconds |
| `useContinuation` | Boolean | No | Use Apex continuation for long-running calls |
| `show` | Object | No | Run only when the condition is true |
| `enableDefaultAbort` / `failureAbortMessage` / `errorMessage` | — | No | Failure handling |

```json
{
  "integrationProcedureKey": "Eligibility_CheckMember",
  "extraPayload": {
    "MemberId": "%MemberId%",
    "ServiceDate": "%RequestedDate%"
  },
  "sendOnlyExtraPayload": true,
  "responseJSONPath": "",
  "responseJSONNode": "EligibilityResult",
  "remoteOptions": {
    "preTransformBundle": "DR_TransformEligibilityInput",
    "postTransformBundle": "DR_TransformEligibilityOutput",
    "useFuture": false,
    "chainable": false
  },
  "remoteTimeout": 30000,
  "enableDefaultAbort": false,
  "failureAbortMessage": "Are you sure?",
  "errorMessage": { "custom": [], "default": null }
}
```

---

### Remote Action

Calls a method on an Apex class that implements `Callable` or `omnistudio.VlocityOpenInterface(2)`.

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `remoteClass` | String | Yes | Apex class name |
| `remoteMethod` | String | Yes | Method (action) name |
| `extraPayload` | Object | No | Extra input key-values |
| `sendOnlyExtraPayload` | Boolean | No | Send only `extraPayload` instead of the whole data JSON |
| `responseJSONPath` / `responseJSONNode` | String | No | Where to store the result |
| `remoteOptions` | Object | No | Options passed to the class as `options` |
| `enableDefaultAbort` / `failureAbortMessage` / `errorMessage` | — | No | Failure handling |

```json
{
  "remoteClass": "CustomEligibilityService",
  "remoteMethod": "checkEligibility",
  "extraPayload": {
    "memberId": "%MemberId%"
  },
  "sendOnlyExtraPayload": true,
  "responseJSONNode": "EligibilityResult",
  "remoteOptions": {},
  "errorMessage": { "custom": [], "default": null }
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
| `elementValueMap` | Object | Yes | Key-value pairs to set in the data JSON. Prefix a value with `=` to evaluate it as a formula |
| `show` | Object | No | Run only when the condition is true |

```json
{
  "elementValueMap": {
    "FullName": "=CONCATENATE(%FirstName%, \" \", %LastName%)",
    "SubmissionDate": "=TODAY()",
    "Status": "Submitted",
    "RequestId": "=CONCATENATE(\"SR-\", %CaseNumber%)"
  }
}
```

---

### Validation

Validates data using a condition group. Blocks Step advancement when validation fails.

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `validateExpression` | Object | Yes | Condition group (same syntax as `show`) that must be true to pass |
| `messages` | Array | Yes | `[{ "value": true, "type": "Success"\|"Warning", "text": "", "active": false }, { "value": false, "type": "Requirement", "text": "<error message>", "active": true }]` |
| `hideLabel` | Boolean | No | Hide the element label |

```json
{
  "validateExpression": {
    "group": {
      "operator": "AND",
      "rules": [
        { "field": "EndDate", "condition": ">", "data": "%StartDate%" }
      ]
    }
  },
  "messages": [
    { "value": true, "type": "Success", "text": "", "active": false },
    { "value": false, "type": "Requirement", "text": "End date must be after the start date.", "active": true }
  ],
  "hideLabel": true
}
```

Multiple conditions example (both must hold):
```json
{
  "validateExpression": {
    "group": {
      "operator": "AND",
      "rules": [
        { "field": "Age", "condition": ">=", "data": "18" },
        { "field": "Age", "condition": "<=", "data": "120" }
      ]
    }
  },
  "messages": [
    { "value": true, "type": "Success", "text": "", "active": false },
    { "value": false, "type": "Requirement", "text": "Age must be between 18 and 120.", "active": true }
  ]
}
```

### Set Errors

Attaches error messages to specific elements (blocks advancing while shown).

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `elementErrorMap` | Object | Yes | `{ "<ElementName>": "<error message>" }` |
| `show` | Object | No | When the errors should be set |

---

### Formula

Calculates a value using a formula expression and stores the result in the data JSON. For the supported functions see `formula-functions.md`.

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `expression` | String | Yes | Formula expression |
| `dataType` | String | No | Result type (e.g. `"Text"`, `"Boolean"`; leave unset for numbers) |
| `mask` | String | No | Display mask for numeric results |
| `hide` | Boolean | No | Hide the formula from the UI (value still in data JSON) |

```json
{
  "label": "TotalWithTax",
  "expression": "%SubTotal% * (1 + %TaxRate% / 100)",
  "hide": true
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
**Conditions**: `=`, `<>` (not equal), `>`, `<`, `>=`, `<=`. To test for blank use `"data": null` with `=` / `<>`.

**`conditionType`** controls what happens when the condition is false: `"Hide if False"` (default), `"Readonly if False"`, `"Optional if False"`.

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
| `%Step1:Block1:FieldName%` | Full path through Step / Block names |
| `%Step1:RepeatBlock\|n:FieldName%` | Current item inside a repeat Block (`\|n`) |
| `%List\|1:FieldName%` | Array element by 1-based index (`\|1`, `\|2`, …) — not `[0]` |
| `%userId%`, `%ContextId%` | Built-in runtime values (running user Id; record Id passed to the OmniScript) |

### Layout Properties

| Property | Type | Description |
|----------|------|-------------|
| `controlWidth` | Number | Column width (1-12 grid system) |

### Data Binding

| Property | Type | Description |
|----------|------|-------------|
| `sendJSONPath` / `sendJSONNode` | String | What part of the data JSON an action sends, and the key to wrap it under |
| `extraPayload` | Object | Extra key-values sent by IP / Remote Actions |
| `responseJSONPath` | String | Path to extract from action response |
| `responseJSONNode` | String | Data JSON node where the action response is stored |

---

## Quick Reference: Element Type to OmniProcessElement.Type

| Display Name | Type Value | Category |
|-------------|-------------------|----------|
| Step | `Step` | Container |
| Block | `Block` | Container |
| Action Block | `Action Block` | Container |
| Edit Block | `Edit Block` | Container |
| Text | `Text` | Input |
| Text Area | `Text Area` | Input |
| Number | `Number` | Input |
| Currency | `Currency` | Input |
| Date | `Date` | Input |
| Date/Time | `Date/Time (Local)` | Input |
| Time | `Time` | Input |
| Checkbox | `Checkbox` | Input |
| Radio | `Radio` | Input |
| Select | `Select` | Input |
| Multi-select | `Multi-select` | Input |
| Type Ahead | `Type Ahead Block` | Input |
| Email | `Email` | Input |
| Telephone | `Telephone` | Input |
| URL | `URL` | Input |
| Password | `Password` | Input |
| Range | `Range` | Input |
| Signature | `Signature` | Input |
| File | `File` | Input |
| Text Block | `Text Block` | Display |
| Line Break | `Line Break` | Display |
| Custom Lightning Web Component | `Custom Lightning Web Component` | Display |
| OmniScript (embedded) | `OmniScript` | Container |
| Headline | `Headline` | Display |
| Aggregate | `Aggregate` | Display |
| Disclosure | `Disclosure` | Display |
| Image | `Image` | Display |
| DataRaptor Extract Action | `DataRaptor Extract Action` | Action |
| DataRaptor Transform Action | `DataRaptor Transform Action` | Action |
| DataRaptor Post Action (Load) | `DataRaptor Post Action` | Action |
| Integration Procedure Action | `Integration Procedure Action` | Action |
| Remote Action | `Remote Action` | Action |
| Navigate Action | `Navigate Action` | Action |
| Email Action | `Email Action` | Action |
| DocuSign Envelope Action | `DocuSign Envelope Action` | Action |
| Set Values | `Set Values` | Logic |
| Validation | `Validation` | Logic |
| Set Errors | `Set Errors` | Logic |
| Formula | `Formula` | Logic |

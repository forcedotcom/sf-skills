---
name: field-service-data-capture-reference-configure
description: "Build, edit, and deploy Salesforce Data Capture Flows (processType DataCaptureFlow) — Field Service mobile / offline forms. Use when authoring flow-meta.xml with runtime_service_fieldservice:dc* components, Repeater loops (.AllItems), master-detail child record persistence, visual polish (gradient banners, progress bars, callouts), supporting objects with FLS/permsets, debugging DataCaptureFlow deploy errors, or troubleshooting why a deployed form doesn't appear on the FSL Mobile Forms tab (DDC/WorkPlan OWD + AssignedResource sharing prerequisites)."
user-invocable: false
metadata:
  version: "1.0"
  domains: ["Field Service"]
  cliTools:
    - tool: ["python3"]
      semver: ">=3.9.0"
    - tool: ["sf"]
      semver: ">=2.0.0"
---

# Salesforce Data Capture Flow Skill

Build, edit, and deploy Salesforce Flows with `processType: DataCaptureFlow` (Field Service mobile / offline forms).

---

## Required metadata (every flow)

```xml
<processType>DataCaptureFlow</processType>
<areMetricsLoggedToDataCloud>false</areMetricsLoggedToDataCloud>
<environments>Offline</environments>
<!-- NO <apiVersion> tag -->
```

Optional `IsLlmTargetable` custom property — if you include it, it must be a JSON string, not a boolean:

```xml
<customProperties>
    <name>IsLlmTargetable</name>
    <value><stringValue>{&quot;value&quot;:&quot;false&quot;}</stringValue></value>
</customProperties>
```

The `<booleanValue>false</booleanValue>` form deploys but blocks activation — error: `The value of the IsLlmTargetable custom property's value field must be a string in JSON format`. Omitting the property entirely is also fine.

Required input variables:
```xml
<variables><name>recordId</name><dataType>String</dataType><isInput>true</isInput><isOutput>false</isOutput><isCollection>false</isCollection></variables>
<variables><name>parentRecordId</name><dataType>String</dataType><isInput>true</isInput><isOutput>false</isOutput><isCollection>false</isCollection></variables>
<variables><name>parentObjectType</name><dataType>String</dataType><isInput>true</isInput><isOutput>false</isOutput><isCollection>false</isCollection></variables>
```

---

## XML structure rules

Salesforce's Flow schema enforces grouping — all elements of the same type must appear in a single contiguous block. Deploy fails with `Element X is duplicated at this location` when violated.

Group order doesn't matter, but within each group elements must be adjacent:
- all `<choices>` together
- all `<dynamicChoiceSets>` together
- all `<screens>` together
- all `<decisions>` together
- all `<recordLookups>` together
- all `<recordCreates>` together
- all `<recordUpdates>` together
- all `<loops>` together
- all `<assignments>` together
- all `<variables>` together

Connector references determine execution order, not XML order.

---

## Component reference

All extensions: prefix `runtime_service_fieldservice:`

| Component | Extension | fieldType |
|-----------|-----------|-----------|
| Short Text | `dcTextInput` | `ComponentInstance` |
| Long Text | `dcLongText` | `ComponentInstance` |
| Email | `dcEmail` | `ComponentInstance` |
| Phone | `dcPhone` | `ComponentInstance` |
| Name | `dcName` | `ComponentInstance` |
| Numeric | `dcNumeric` | `ComponentInstance` |
| Counter | `dcCounter` | `ComponentInstance` |
| Date | `dcDate` | `ComponentInstance` |
| Date & Time | `dcDateTime` | `ComponentInstance` |
| Checkbox | `dcCheckbox` | `ComponentInstance` |
| Toggle | `dcToggle` | `ComponentInstance` |
| Address / GPS | `dcAddress` | `ComponentInstance` |
| Lookup | `dcLookup` | `ComponentInstance` |
| Static image | `dcFileView` | `ComponentInstance` |
| Upload image (mobile) | `dcUpImage` | `ComponentInstance` |
| Upload file (mobile) | `dcUpFile` | `ComponentInstance` |
| Signature (mobile) | `dcSignature` | `ComponentInstance` |
| Picklist single | `dcPicklist` | `ComponentChoice` |
| Picklist multi | `dcPicklist` | `ComponentMultiChoice` |
| Radio buttons | `dcRbGroup` | `ComponentChoice` |
| Checkbox group | `dcCbGroup` | `ComponentMultiChoice` |
| Matrix | `dcMatrix` | `ComponentMultiChoice` |
| Display text | *(none)* | `DisplayText` |
| Section | *(none)* | `RegionContainer` + `Region` |
| Repeater | *(none)* | `Repeater` |

Note: `<fieldType>Range</fieldType>` is NOT a valid slider fieldType in DataCaptureFlow (despite "Range/Slider" appearing in Builder UI lists). Sliders aren't available as pure metadata in this process type — use `dcNumeric` or `dcCounter`. `forceContent:repeater` (Lightning generic) ≠ `<fieldType>Repeater</fieldType>` (FSL offline). They share a concept, not XML.

### Setting the label

| fieldType | How |
|-----------|-----|
| `ComponentInstance` | `<inputParameters><name>label</name><value><stringValue>…</stringValue></value></inputParameters>` |
| `ComponentChoice` / `ComponentMultiChoice` | `<fieldText>Label</fieldText>` |
| `DisplayText` | `<fieldText>HTML</fieldText>` |

All ComponentInstance extensions (including `dcAddress` and `dcToggle`) accept the `label` inputParameter — no wrapping DisplayText needed.

### Required flag

Every input field needs `<isRequired>true/false</isRequired>` at field level. That single flag is sufficient for every `dc*` component — no extra `required` / `isRequired` inputParameter is needed.

`dcLookup` additionally accepts an `isRequired` inputParameter (boolean), but the field-level `<isRequired>` drives enforcement.

`dcCheckbox` and `dcToggle` accept `<isRequired>true</isRequired>` syntactically but don't enforce it at runtime.

### Every input field must also have

```xml
<inputsOnNextNavToAssocScrn>UseStoredValues</inputsOnNextNavToAssocScrn>
<storeOutputAutomatically>true</storeOutputAutomatically>
<styleProperties>
    <verticalAlignment><stringValue>top</stringValue></verticalAlignment>
    <width><stringValue>12</stringValue></width>
</styleProperties>
```

**Exception:** `<fieldType>Repeater</fieldType>` explicitly rejects `storeOutputAutomatically` (`"the storeOutputAutomatically field isn't supported"`). Repeater output is always available as `.AllItems` — no opt-in needed.

---

## Screen rules

Every screen needs ALL THREE of these or the Next/Finish button won't render:
- `<allowFinish>true</allowFinish>` (even on non-final screens)
- `<showFooter>true</showFooter>`
- `<nextOrFinishButtonLabel>Next</nextOrFinishButtonLabel>`

Plus:
- First element after `<start>` must always be a `<screens>` element
- All `<screens>` elements must be grouped together in the XML

---

## Repeater — iterating rows and creating child records

The Repeater's output collection is exposed as `.AllItems`. Confirmed working on API v66.

```xml
<!-- On the screen: -->
<fields>
    <name>MyRepeater</name>
    <fieldType>Repeater</fieldType>
    <!-- NO storeOutputAutomatically on the Repeater itself -->
    <fields>
        <name>Row_PartName</name>
        <extensionName>runtime_service_fieldservice:dcTextInput</extensionName>
        <fieldType>ComponentInstance</fieldType>
        <storeOutputAutomatically>true</storeOutputAutomatically>
        <!-- … -->
    </fields>
    <fields>
        <name>Row_PartQty</name>
        <extensionName>runtime_service_fieldservice:dcCounter</extensionName>
        <fieldType>ComponentInstance</fieldType>
        <storeOutputAutomatically>true</storeOutputAutomatically>
        <!-- … -->
    </fields>
    <isRequired>false</isRequired>
</fields>

<!-- At end of flow: -->
<loops>
    <name>Loop_Parts</name>
    <collectionReference>MyRepeater.AllItems</collectionReference>   <!-- ← THE KEY -->
    <iterationOrder>Asc</iterationOrder>
    <nextValueConnector>
        <targetReference>Create_Part</targetReference>
    </nextValueConnector>
</loops>
<recordCreates>
    <name>Create_Part</name>
    <object>CustomFormPart__c</object>
    <connector>
        <targetReference>Loop_Parts</targetReference>   <!-- loops back -->
    </connector>
    <inputAssignments>
        <field>PartName__c</field>
        <value>
            <elementReference>Loop_Parts.Row_PartName.value</elementReference>
            <!-- ↑ LOOP name + nested field name + .value -->
        </value>
    </inputAssignments>
    <inputAssignments>
        <field>Quantity__c</field>
        <value>
            <elementReference>Loop_Parts.Row_PartQty.value</elementReference>
        </value>
    </inputAssignments>
    <storeOutputAutomatically>true</storeOutputAutomatically>
</recordCreates>
```

**Don'ts:**
- `<collectionReference>MyRepeater</collectionReference>` → `Element "MyRepeater" doesn't exist`
- `<collectionReference>MyRepeater.items</collectionReference>` → generic server error
- `<collectionReference>MyRepeater.data</collectionReference>` → generic server error
- Inside the loop body, `MyRepeater.Row_PartName.value` won't work — must use the **loop's name**, not the repeater's name.

**Cross-row validation does NOT compile.** Formula refs like `r_GR4.AllItems[$Items].field.value` and `r_GR4.AllItems[$Items - 1].field.value` fail with *Syntax error*. Per-row validation works via plain `fieldName.value` inside the nested field's own `validationRule`. For cross-row rules, use a post-screen `loops + decisions`.

**Other Repeater accessors don't resolve today.** Only `.AllItems` works. `AddedItems`, `PrepopulatedItems`, `RemovedItems` all fail deploy with `doesn't exist`.

### Prepopulating a Repeater from an existing collection

Bind an existing SObject collection to the Repeater so it renders one pre-filled row per source record. The user can then edit, add, or remove rows before submit.

Pattern: `recordLookups` (get source collection, `getFirstRecordOnly=false`, `storeOutputAutomatically=true`) → screen with `Repeater` bound via the `collection` inputParameter → nested fields use `SourceCollection[$EachItem].FieldApiName` as their `value` default.

```xml
<recordLookups>
    <name>Get_Source</name>
    <object>ServiceResource</object>
    <getFirstRecordOnly>false</getFirstRecordOnly>
    <storeOutputAutomatically>true</storeOutputAutomatically>
    <connector><targetReference>Screen_Repeater</targetReference></connector>
    <!-- optional <limit>, <filters> … -->
</recordLookups>

<!-- On the screen: -->
<fields>
    <name>accountRepeater</name>
    <fieldType>Repeater</fieldType>
    <inputParameters>
        <name>collection</name>                                <!-- ← binds source rows -->
        <value><elementReference>Get_Source</elementReference></value>
    </inputParameters>
    <fields>
        <name>account_info</name>
        <fieldType>DisplayText</fieldType>
        <fieldText>&lt;p&gt;Id: {!Get_Source[$EachItem].Id}&lt;/p&gt;</fieldText>
        <!-- DisplayText inside the Repeater merges via SourceCollection[$EachItem].Field -->
    </fields>
    <fields>
        <name>name</name>
        <extensionName>runtime_service_fieldservice:dcTextInput</extensionName>
        <fieldType>ComponentInstance</fieldType>
        <inputParameters>
            <name>label</name>
            <value><stringValue>Name</stringValue></value>
        </inputParameters>
        <inputParameters>
            <name>value</name>
            <value><elementReference>Get_Source[$EachItem].Name</elementReference></value>
            <!-- ↑ prepopulates the editable field with the source record's value -->
        </inputParameters>
        <isRequired>true</isRequired>
        <storeOutputAutomatically>true</storeOutputAutomatically>
        <inputsOnNextNavToAssocScrn>UseStoredValues</inputsOnNextNavToAssocScrn>
        <styleProperties>…</styleProperties>
    </fields>
    <isRequired>false</isRequired>
    <styleProperties>…</styleProperties>
</fields>
```

Key points:
- The binding inputParameter is named `collection`, not `value` or `source`.
- Inside the Repeater, reference a source row via `SourceCollectionName[$EachItem].FieldApiName` — use the **record-lookup's name**, not the Repeater's name. Works in both `DisplayText.fieldText` (as `{!Get_Source[$EachItem].Id}`) and in component `value` defaults (as `<elementReference>Get_Source[$EachItem].Name</elementReference>`).
- `$EachItem` is the per-row iterator Salesforce injects while rendering the Repeater. It only resolves inside Repeater-nested fields.
- Downstream loops still iterate `Repeater_Name.AllItems` as normal — prepopulation changes the input, not the output accessor.
- Prepopulated rows appear as regular `.AllItems` entries after submit; there is no `PrepopulatedItems` / `AddedItems` split (those accessors fail deploy).

### Displaying Repeater entries to the user (post-Repeater Loop screen)

To show the user what they captured (e.g. review / confirmation / per-row detail), put a Loop **after** the Repeater screen whose body connects to a display screen; the display screen then connects back to the Loop. The end connector of the Loop moves on to the next step.

```xml
<loops>
    <name>Loop_Through_Repeater</name>
    <collectionReference>accountRepeater.AllItems</collectionReference>
    <iterationOrder>Asc</iterationOrder>
    <nextValueConnector>
        <targetReference>Repeater_Output_Screen</targetReference>   <!-- body = display screen -->
    </nextValueConnector>
    <!-- <noMoreValuesConnector> → next step after the review is done -->
</loops>

<screens>
    <name>Repeater_Output_Screen</name>
    <connector><targetReference>Loop_Through_Repeater</targetReference></connector>   <!-- back to loop -->
    <fields>
        <name>display_info</name>
        <fieldType>DisplayText</fieldType>
        <fieldText>&lt;p&gt;Source Id: {!Loop_Through_Repeater.UniqueField__Id}&lt;/p&gt;
&lt;p&gt;Name: {!Loop_Through_Repeater.name.value}&lt;/p&gt;
&lt;p&gt;Type: {!Loop_Through_Repeater.description.value}&lt;/p&gt;</fieldText>
        <styleProperties>…</styleProperties>
    </fields>
    <allowFinish>true</allowFinish>
    <showFooter>true</showFooter>
    <nextOrFinishButtonLabel>Next</nextOrFinishButtonLabel>
</screens>
```

Accessor rules inside the loop body:
- User-captured values — `{!LoopName.nestedFieldName.value}` (same `.value` / `.selectedChoiceValues` / `.isActive` / etc. accessors as elsewhere).
- Source record Id for **prepopulated** rows — `{!LoopName.UniqueField__Id}`. This is a synthetic field the Repeater exposes on each iteration; it only carries a value for rows that came from the bound `collection` (new rows the user added will be blank).
- Use the **loop's name**, not the Repeater's name, inside the loop body — same rule as the canonical `.AllItems` + Create pattern above.

This loop-over-`.AllItems` display pattern composes with the Create/Update patterns: one loop for rendering a review screen, a later loop (or the same one, if ordering permits) for CUD. Remember the CUD rule — nothing (screens, gets, decisions) may sit between sequential CUD nodes, so any review loop must fully complete before the CUD chain starts.

---

## CUD rules (hard platform constraints)

- **A Decision can choose which CUD chain starts** (e.g. Create vs Update branches of a save-mode decision). But **once a CUD chain begins, no Decision may appear between sequential CUD nodes** — deploy fails with `Append multiple Create, Update, or Delete operations only at the end of the flow, in any order`.
  - Workaround for "create only if filled" → always-create (accept blank rows), or move the conditional logic before the CUD chain begins.
- **All CUDs at end of flow.** No Get Records or screens after any CUD. No subflows containing CUD.
- **Assignment-after-CUD inside a loop was bugged in v260.** Fixed in v262 / API 66. Safe to use now.

---

## Counter params

```xml
<inputParameters><name>min</name><value><numberValue>1.0</numberValue></value></inputParameters>
<inputParameters><name>max</name><value><numberValue>10.0</numberValue></value></inputParameters>
<inputParameters><name>step</name><value><numberValue>1.0</numberValue></value></inputParameters>
<inputParameters><name>minCustomErrorMessage</name><value><stringValue>…</stringValue></value></inputParameters>
<inputParameters><name>maxCustomErrorMessage</name><value><stringValue>…</stringValue></value></inputParameters>
```

## Date params

```xml
<inputParameters><name>minDate</name><value><elementReference>$Flow.CurrentDate</elementReference></value></inputParameters>
<inputParameters><name>maxDate</name><value><dateValue>2027-12-31</dateValue></value></inputParameters>
```

## Picklist compact mode

Only use `isCompact=true` when ALL labels ≤8 characters AND ≤5 options.

## Lookup params

```xml
<inputParameters><name>objectApiName</name><value><stringValue>Asset</stringValue></value></inputParameters>
<inputParameters><name>searchedFields</name><value><stringValue>Name, SerialNumber</stringValue></value></inputParameters>
<inputParameters><name>isMultiSelection</name><value><booleanValue>true</booleanValue></value></inputParameters>
<inputParameters><name>recordIdCollection</name><value><elementReference>v_Ids</elementReference></value></inputParameters>
```

### `recordIdCollection` — scoping the searchable set

- **Builder label:** *Record IDs Collection*. **XML attribute:** `recordIdCollection` (singular `recordId` + `Collection` suffix). `recordIds` fails deploy with `We can't find this input attribute: "recordIds"`.
- **It is a scoping filter, not a default pre-selection.** Constrains the lookup to only search within the provided String collection of Ids.
- **Only takes effect when `isMultiSelection=true`.** In single-select mode it is silently ignored — the user sees the full unfiltered object.
- Canonical pattern: `recordLookups` (scoped subset) → `loops` + `assignments` (build String collection of Ids) → screen with `dcLookup recordIdCollection=v_Ids`. Works offline against Briefcase-primed data; target < 1s over ~60k records.
- Output in multi-select mode is `{!Lookup.recordIds}` (String collection); visibility rules and DML that previously used `{!Lookup.recordId}` (singular) must iterate the collection or take the first element.

### `dcLookup` displayed label

`dcLookup` has **no input parameter** for the displayed field (no `displayField`/`primaryField`). The label in search results and the selected chip is driven by the object's **Primary Compact Layout** — first field in that layout wins. To change it: Setup → Object Manager → *Object* → Compact Layouts → reorder → assign as Primary (org-wide change). `searchedFields` controls matching, not display.

Flow-local alternative: swap `dcLookup` for `dcPicklist` backed by a `dynamicChoiceSets` with `<displayField>` / `<valueField>`.

## Address with GPS

```xml
<inputParameters><name>useCoordinates</name><value><booleanValue>true</booleanValue></value></inputParameters>
```

## Matrix

```xml
<inputParameters><name>questions</name><value><stringValue>["Q1","Q2","Q3"]</stringValue></value></inputParameters>
```

Escape `&` as `&amp;` inside the JSON string.

## 2-column section

```xml
<fields>
    <name>MySection</name>
    <fieldText>Section Header</fieldText>
    <fieldType>RegionContainer</fieldType>
    <fields>
        <name>MySection_Col1</name>
        <fieldType>Region</fieldType>
        <fields><!-- components here --></fields>
        <inputParameters><name>width</name><value><stringValue>6</stringValue></value></inputParameters>
        <isRequired>false</isRequired>
    </fields>
    <fields>
        <name>MySection_Col2</name>
        <fieldType>Region</fieldType>
        <fields><!-- components here --></fields>
        <inputParameters><name>width</name><value><stringValue>6</stringValue></value></inputParameters>
        <isRequired>false</isRequired>
    </fields>
    <isRequired>false</isRequired>
    <regionContainerType>SectionWithHeader</regionContainerType>
    …styleProperties…
</fields>
```

## Visibility rule

```xml
<visibilityRule>
    <conditionLogic>and</conditionLogic>
    <conditions>
        <leftValueReference>componentName.value</leftValueReference>
        <operator>GreaterThan</operator>
        <rightValue><numberValue>0.0</numberValue></rightValue>
    </conditions>
</visibilityRule>
```

Property accessors: `.value` (input components, including `dcCheckbox`), `.selectedChoiceValues` (choice components), `.isActive` (toggle), `.firstName` / `.lastName` (Name component), `.recordId` / `.recordIds` (Lookup single / multi).

The same accessors are also used inside `recordCreates` / `recordUpdates` `inputAssignments` — e.g. `<elementReference>new_Reading.value</elementReference>`.

### Conditionally-hidden required fields — use `validationRule`, not `isRequired`

Never mark a field `isRequired=true` if it's behind a `visibilityRule`. The required check still fires while the field is hidden, so users can't proceed. Instead, set the field `isRequired=false` and wrap the rule:

```text
IF(TriggerField.selectedChoiceValues = "Yes",
   AND(NOT(ISBLANK(value)), value >= 0, value <= 100000),
   TRUE)
```

### Canonical Decision IsNull pattern

`IsNull` takes a `booleanValue` on the right, NOT a null literal:

```xml
<conditions>
    <leftValueReference>v_ParentId</leftValueReference>
    <operator>IsNull</operator>
    <rightValue>
        <booleanValue>false</booleanValue>   <!-- true = is null, false = is not null -->
    </rightValue>
</conditions>
```

---

## Calculation timing (CRITICAL)

Calculated values **cannot display on the same screen that collects the inputs** — calculations run only after the user taps Next. Pattern:

```text
Screen N (collect inputs) → recordLookups / assignments / decisions → Screen N+1 (display results)
```

Screen N's connector must point to the calculation element, NOT to Screen N+1. All decision branches must eventually converge on Screen N+1.

---

## DisplayText formula limitations (mobile runtime)

`DisplayText` in DataCaptureFlow has **severely limited formula support** compared to standard flows — complex formulas deploy fine and preview in Builder but fail at runtime with `Error while resolving default value reference`.

**Fails at runtime:**
- `IF(Toggle.isActive, "YES", "NO")` — any IF/CASE on component properties
- `TEXT(CASE(...))`, `ADDMONTHS(...)`, nested date math
- Mixing multiple component refs + formulas in one `fieldText`

**Works:**
- Simple single variable: `{!var_RiskScore}`
- Simple component ref: `{!MyPicklist.selectedChoiceValues}`, `{!MyNumeric.value}`
- Global vars: `{!$Flow.CurrentDate}`, `{!$User.FirstName}`

Pattern: pre-calculate in an `<assignments>` element → store in a variable → reference that variable in DisplayText.

### Global variables as input `value` defaults

| Default binding | Variable | Works? |
|-----------------|----------|--------|
| `dcTextInput` | `$User.Username` | ✅ |
| `dcTextInput` | `$User.Name` | ❌ type mismatch error |
| `dcDateTime` | `$Flow.InterviewStartTime` | ✅ |
| `dcDate` | `$Flow.CurrentDate` | ✅ |

---

## Record Choice Set (`dynamicChoiceSets`) — mobile offline gotcha

`<outputAssignments>` inside a `dynamicChoiceSets` deploys fine but **does NOT reliably populate the target variables at runtime** in mobile offline DataCaptureFlow. Downstream screens render blank.

Correct pattern: keep the choice set minimal (`displayField`, `valueField`, `filters`, `object`, `dataType`). After the selection screen, route through a `recordLookups` filtered by `Id = {!picklistName.selectedChoiceValues}` and put extra fields into variables via the lookup's `outputAssignments`. Fits calculation-timing rule naturally (lookup sits between selection screen and display screen).

```xml
<recordLookups>
    <name>gr_SelectedChild</name>
    <filters>
        <field>Id</field>
        <operator>EqualTo</operator>
        <value><elementReference>pl_Child.selectedChoiceValues</elementReference></value>
    </filters>
    <getFirstRecordOnly>true</getFirstRecordOnly>
    <object>Child__c</object>
    <outputAssignments>
        <assignToReference>v_SelectedValue</assignToReference>
        <field>Reading_Value__c</field>
    </outputAssignments>
</recordLookups>
```

---

## Visual polish patterns (verified render in mobile runtime)

Colors from the Lightning Design System: `#2E844A` (green), `#0176D3` (blue), `#FE9339` (orange), `#C9C7C5` (neutral).

### Hero banner
```html
<div style="background: linear-gradient(135deg, #2E844A 0%, #0176D3 100%); color: white; padding: 20px; border-radius: 10px; text-align: center;">
  <p style="margin: 0; font-size: 22px;"><strong>🔧 Site Visit Report</strong></p>
  <p style="margin: 4px 0 0 0; font-size: 13px;">Subtitle</p>
</div>
```

### Progress bar (per screen)
```html
<p><b>Step X of N – 📍 Section Title</b></p>
<div style="width: 100%; height: 8px; background-color: #C9C7C5; border-radius: 4px; margin: 5px 0;">
  <div style="width: PERCENT%; height: 100%; background: linear-gradient(90deg, #2E844A 0%, #0176D3 100%); border-radius: 4px;"></div>
</div>
```
Separator between counter and title MUST be en dash `–` (U+2013), not hyphen.

### Callout boxes
```html
<!-- Info (blue) -->
<div style="background-color: #EAF5FE; border-left: 4px solid #0176D3; padding: 10px 14px; border-radius: 4px;">
  <p style="margin: 0; color: #014486; font-size: 13px;"><b>ℹ️ Info:</b> …</p>
</div>
<!-- Warning (orange) -->
<div style="background-color: #FFF4E6; border-left: 4px solid #FE9339; padding: 10px 14px; border-radius: 4px;">
  <p style="margin: 0; color: #704D00; font-size: 13px;"><b>⚠️ Heads up:</b> …</p>
</div>
<!-- Success (green) -->
<div style="background-color: #E8F5E9; border-left: 4px solid #2E844A; padding: 10px 14px; border-radius: 4px;">
  <p style="margin: 0; color: #1B5E20; font-size: 13px;"><b>✅ Ready:</b> …</p>
</div>
```

### Review card (merge fields from prior screens)
```html
<div style="border: 1px solid #DDDBDA; border-radius: 8px; padding: 14px 16px; background-color: #FAFAF9;">
  <p style="margin: 0 0 8px 0; color: #0176D3; font-size: 14px;"><b>📍 Section</b></p>
  <p style="margin: 2px 0;"><b>Name:</b> {!Input_SiteName.value}</p>
  <p style="margin: 2px 0;"><b>Contact:</b> {!Input_Contact.firstName} {!Input_Contact.lastName}</p>
  <p style="margin: 2px 0;"><b>Priority:</b> {!Input_Priority.selectedChoiceValues}</p>
  <p style="margin: 2px 0;"><b>After-hours:</b> {!Input_Toggle.isActive}</p>
</div>
```

All HTML must be XML-escaped in `<fieldText>`: `&` → `&amp;`, `"` → `&quot;`, `<` → `&lt;`, `>` → `&gt;`.

---

## Deploying supporting objects alongside the flow

Custom object + field deploys **do not auto-grant FLS/CRUD** on the System Administrator profile. Flows running as the admin still can't read/write the new fields. Ship a PermissionSet and assign it:

```xml
<!-- MyObject_Access.permissionset-meta.xml -->
<PermissionSet xmlns="http://soap.sforce.com/2006/04/metadata">
    <label>My Object Access</label>
    <license>Salesforce</license>
    <hasActivationRequired>false</hasActivationRequired>
    <objectPermissions>
        <allowCreate>true</allowCreate><allowDelete>true</allowDelete>
        <allowEdit>true</allowEdit><allowRead>true</allowRead>
        <modifyAllRecords>true</modifyAllRecords><viewAllRecords>true</viewAllRecords>
        <object>MyObject__c</object>
    </objectPermissions>
    <fieldPermissions><field>MyObject__c.MyField__c</field><editable>true</editable><readable>true</readable></fieldPermissions>
    <tabSettings><tab>MyObject__c</tab><visibility>Visible</visibility></tabSettings>
</PermissionSet>
```

Assign after deploy: `sf org assign permset --name MyObject_Access --target-org <alias>`

### CustomObject gotchas

- Master-detail children need `<sharingModel>ControlledByParent</sharingModel>`, else `Must specify a sharing model value`.
- Sfdx retrieve may pull `actionOverrides` for actions that aren't standard (`Automation`, `Details`). Strip them before re-deploy, else `X is not a standard action and cannot be overridden`.
- Text fields > 255 chars must be `<type>LongTextArea</type>`. `Text` max length is 255.
- A PermissionSet that references a `required=true` field deploys cleanly, but if FLS is set in a separate file, `You cannot deploy to a required field` fires. Flip the field to `required=false` or handle required-ness in the flow instead.

### Custom tab

Lets users list records from the App Launcher:

```xml
<!-- MyObject__c.tab-meta.xml -->
<CustomTab xmlns="http://soap.sforce.com/2006/04/metadata">
    <customObject>true</customObject>
    <motif>Custom53: Form</motif>
</CustomTab>
```

Then add `<tabSettings>` to the permset (as shown above).

---

## Mobile prerequisites — required for Forms tab to render on FSL Mobile

A flow that deploys cleanly and shows up on desktop will **silently fail on FSL Mobile** with `"No forms available. Try Again"` if the org isn't set up to share DDC + WorkPlan records with the assigned technician. Verified 2026-05-28: a fully-validated form (Sewerage Further Work Request) was invisible on iOS Field Service for the assigned tech until all four fixes below were in place. The same blocker hid the SDO's pre-shipped Job Safety Assessment form.

Why it's silent: FSL Mobile uses the UI API endpoint `/services/data/v67.0/ui-api/related-list-records/{woId}/DynamicDataCaptures`, which **enforces sharing rules**. SOQL queries as a sysadmin bypass sharing, so desktop validation never surfaces the issue. The endpoint returns `INSUFFICIENT_ACCESS` to the tech, the iOS app catches the error, and renders an empty state with a "Try Again" button.

### 1. DynamicDataCapture + WorkPlan OWD must be Public Read/Write

Default platform OWD is **Private** for both objects. Override in object metadata:

```xml
<!-- objects/DynamicDataCapture/DynamicDataCapture.object-meta.xml -->
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
    <sharingModel>ReadWrite</sharingModel>
    <externalSharingModel>ReadWrite</externalSharingModel>
</CustomObject>
```

```xml
<!-- objects/WorkPlan/WorkPlan.object-meta.xml -->
<CustomObject xmlns="http://soap.sforce.com/2006/04/metadata">
    <sharingModel>ReadWrite</sharingModel>
    <externalSharingModel>ReadWrite</externalSharingModel>
</CustomObject>
```

`WorkStep` inherits via `ControlledByParent` and doesn't need a separate change.

### 2. FieldServiceSettings must share SAs and parent WOs with assigned resources

Many SDO orgs ship with these `false`. Without them, the AssignedResource never gets shared access to the WO, even though they show on the SA's resource list.

```xml
<!-- settings/FieldService.settings-meta.xml -->
<FieldServiceSettings xmlns="http://soap.sforce.com/2006/04/metadata">
    <doesShareSaWithAr>true</doesShareSaWithAr>
    <doesShareSaParentWoWithAr>true</doesShareSaParentWoWithAr>
</FieldServiceSettings>
```

### 3. Re-save existing AssignedResources after the settings flip

The settings change only applies to **new** AssignedResource rows. Existing rows need a touch-update to trigger sharing recalc:

```bash
sf apex run --target-org <alias> <<'APEX'
List<AssignedResource> ars = [
    SELECT Id FROM AssignedResource
    WHERE ServiceResource.RelatedRecord.Username = :techUsername
];
update ars;
APEX
```

### 4. Tech must sign out and sign back in

FSL Mobile caches the sharing snapshot at login. Pull-to-refresh does not pick up new sharing — only a fresh auth token will. Tell the user to **sign out completely** of the FSL Mobile app, then sign back in. After that, the Forms tab fetch succeeds and DDC records render.

### What is NOT the cause (don't waste time on these)

- **Layout related-list naming** — `<relatedList>DynamicDataCapture</relatedList>` (singular) is the correct XML form. The UI API uses plural `DynamicDataCaptures` separately. Don't try to align them.
- **Field-level security on `PausedFlowInterviewId`** — granted by default to all profiles.
- **Object permissions on DynamicDataCapture** — granted by default to Standard User and SDO-Service profiles.
- **Permset stack** — `SDO_SFS_All_Permissions` (or any equivalent FSL permset) is sufficient. No extra permset needed for the Forms tab.
- **API version override in Advanced Settings** — production iOS hardcodes `v67.0`; only DEBUG builds dynamically discover.
- **Briefcase / offline priming** — irrelevant when device has internet connectivity. The Forms tab fetches live, not from priming cache.

---

## Prohibited patterns — deploy errors and fixes

| Wrong | Correct | Deploy error (exact) |
|-------|---------|----------------------|
| `dcRadioButtons` | `dcRbGroup` | `extension not found` |
| `dcSection` | `RegionContainer` | `extension not found` |
| `minimumDate` / `maximumDate` | `minDate` / `maxDate` | `input attribute not found` |
| `multiSelection` on Lookup | `isMultiSelection` | `input attribute not found` |
| `disabled` / `readOnly` on Lookup | `isDisabled` / `isReadonly` (lowercase o) | `input attribute not found` |
| `<apiVersion>` tag on flow | Omit entirely | `You can't specify the field API Version` |
| `extensionName` on Repeater itself | Only on nested fields | `extensionName isn't supported` |
| `InputField` fieldType | `ComponentInstance` + extensionName | Field type rejected |
| `<fieldText>` on `ComponentInstance` | Use `label` inputParameter | `A required input parameter is missing: 'label'` |
| `placeholder` inputParameter on `dc*` | Not supported — bake into label text | `We can't find this input attribute: "placeholder"` |
| `min`/`max` on `dcNumeric` | Valid only on `dcCounter` | `We can't find this input attribute: "min"` |
| `<fieldType>Range</fieldType>` (slider) | Not valid in DataCaptureFlow | `'Range' is not a valid value for the enum 'FlowScreenFieldType'` |
| `storeOutputAutomatically` on Repeater | Omit (collection is always `.AllItems`) | `the storeOutputAutomatically field isn't supported` |
| `collectionReference=Repeater_Name` in loop | `Repeater_Name.AllItems` | `Element "X" doesn't exist. Specify an existing collection element` |
| Loop body: `Repeater_Name.field.value` | `Loop_Name.field.value` (loop's name, not repeater's) | Invalid reference |
| Cross-row validation: `AllItems[$Items - 1]` | Use post-screen loops + decisions | Formula `Syntax error` |
| Decision between CUD nodes | Sequential CUDs, no branches | `Append multiple Create, Update, or Delete operations only at the end of the flow` |
| Get Records after CUD | Move gets to before CUD | Flow structure rejected |
| `Step X of Y - Topic` (hyphen) | `Step X of Y – Topic` (en dash U+2013) | Validator counts 0 progress indicators |
| `<start>` → recordLookups / decisions | `<start>` → `<screens>` (intro screen first) | Mobile offline fails to render |
| `<actionCalls>` | Remove; use DisplayText for notifications | Action elements not allowed |
| `helpText` inputParameter | Bake into label text | `input attribute not found` |
| `IsLlmTargetable` as `<booleanValue>` (optional property, but if present) | `<stringValue>{&quot;value&quot;:&quot;false&quot;}</stringValue>` or omit the property entirely | Activation error: `The value of the IsLlmTargetable custom property's value field must be a string in JSON format` |
| `recordIds` inputParameter on Lookup | `recordIdCollection` (singular Id + Collection) | `We can't find this input attribute: "recordIds"` |
| `recordIdCollection` with single-select Lookup | Set `isMultiSelection=true` (scoping ignored otherwise) | No error — silently unfiltered at runtime |
| `<outputAssignments>` inside `dynamicChoiceSets` | Post-selection `recordLookups` with `outputAssignments` | No deploy error — variables stay blank on downstream screens |
| `IF`/`CASE`/date math in `DisplayText` | Pre-calculate in Assignment, reference simple variable | `Error while resolving default value reference` at runtime |
| `$User.Name` as `value` default on dcTextInput | `$User.Username` | `field integrity exception… type for input parameter "Value" doesn't match` |
| Missing `nextOrFinishButtonLabel` on screen | Add `<nextOrFinishButtonLabel>Next</nextOrFinishButtonLabel>` | Next/Finish button not visible |
| Calling AutoLaunched subflow from DataCaptureFlow | Inline the logic, or call only another DataCaptureFlow | `This flow can't reference [FlowName] because the referenced flow type is Autolaunched Flow` |
| `isRequired=true` on field behind `visibilityRule` | Set `isRequired=false`; use `validationRule` IF(trigger, rule, TRUE) | User blocked from proceeding on hidden field |

---

## Deployment

```bash
# Single file
sf project deploy start -d force-app/main/default/flows/MyFlow.flow-meta.xml \
  --target-org <alias> --wait 60 --json

# Multi-dir (use repeated -d, NOT comma-separated)
sf project deploy start \
  -d force-app/main/default/objects \
  -d force-app/main/default/permissionsets \
  -d force-app/main/default/tabs \
  --target-org <alias> --wait 60 --json
```

Extract errors:
```bash
... --json 2>&1 | python3 -c "
import sys, json
d = json.load(sys.stdin)
r = d.get('result', {})
print('Status:', r.get('status'))
for f in r.get('details', {}).get('componentFailures', []):
    print('ERROR:', f.get('fullName'), '-', f.get('problem'))
"
```

---

## Reference examples

Bundled alongside this skill at `examples/` — these are **human / IDE reference files for hand-authoring locally; they are not fetched at agent runtime.** The rules inlined in this skill body above are authoritative at runtime; the example files illustrate those same rules in a complete, deploy-ready flow for a person reading the bundle:

- `Data_Capture_All_Components.flow-meta.xml` — every component in deployment-ready XML
- `DataCapture_Showcase.flow-meta.xml` — full end-to-end flow: multi-screen form, continue-editing recordLookup, Repeater → Loop → child records via `.AllItems`, Create-or-Update CUD chain driven by a Decision, visual polish (banner, progress, callouts, review cards). The most complete worked example of the XML format; if you have the bundle open, use it to cross-check structure against the rules above.
- `Repeater_with_prepopulation.flow-meta.xml` — validated worked example of the prepopulated-Repeater pattern: `recordLookups` (ServiceResource) → Repeater bound via `collection` inputParameter with nested field `value` defaults using `SourceCollection[$EachItem].FieldApiName` → post-Repeater Loop over `.AllItems` feeding a display screen that reads `{!LoopName.nestedField.value}` and `{!LoopName.UniqueField__Id}`. Mirrors the prepopulation + post-Repeater display rules documented above.
- `DataCapture_Repeater_with_data_showcase.flow` (in the org, not committed) — `.AllItems` loop spike; also documents non-working cross-row validation formula syntaxes

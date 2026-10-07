# Known deploy errors and fixes

These were encountered in real migration runs. All are handled automatically by `transform_flow.py` unless noted.

| Deploy error | Root cause | Fix |
|---|---|---|
| `You can't specify the field API Version` | `<apiVersion>` tag present | Removed by transformer |
| `Element variables is duplicated at this location` | Legacy flow has `ParentRecordId` (capital P); transformer adds `parentRecordId` (lowercase) | Case-insensitive dedup — updates existing var to `isInput=true` instead of adding |
| `Element inputParameters is duplicated at this location` | Two separate `<inputParameters>` blocks on same field with other elements between them | Reorder field children so all `<inputParameters>` are contiguous — done by transformer |
| `Flows of type "Data Capture Flow" can't include "RadioButtons"` | `RadioButtons` fieldType not valid in DC | Converted to `ComponentChoice` + `dcRbGroup` by transformer |
| `Flows of type "Data Capture Flow" can't include "MultiSelectCheckboxes"` | Same | Converted to `ComponentMultiChoice` + `dcCbGroup` |
| `Outputs aren't supported for fieldType "ComponentChoice"` | `<dataType>` or `<defaultValue>` present on a ComponentChoice field | Removed by transformer |
| `extensionName is required when fieldType is ComponentChoice` | `extensionName` was removed trying to fix above | Transformer keeps `extensionName` = `dcPicklist`/`dcRbGroup`/`dcCbGroup` on ComponentChoice |
| `extensionName isn't supported` on Repeater | `extensionName` set on the Repeater element itself | Removed by transformer; only valid on nested fields inside the Repeater |
| `Data Capture Flows can't use API entities that don't show up in the UI` | `recordCreates` targeting a platform event object | Removed by transformer; predecessors redirected to successor |
| `The field "X" isn't compatible with the LightningComponentOutput element "Y"` | `<defaultValue>` on a ComponentInstance field | Removed by transformer; use `value` inputParameter instead |
| `In a Decision Outcome, a condition doesn't support "X" Equals` | Decision condition references a screen component name bare (without `.value`) | Transformer appends `.value` |
| `Append multiple Create, Update, or Delete operations only at the end of the flow` | CUD node has a non-CUD successor | Graph restructurer hoists the non-CUD successor before first screen |
| `A loop that contains CUD elements can't include other elements except Assignments` | Screen inside a loop body | Cannot be auto-fixed — requires Repeater redesign |
| `invalid cross reference id` | Connector target references a removed node | Dangling connectors removed by transformer |
| `The flow X doesn't exist` (subflow reference) | Subflow name updated to `_DC` suffix but that flow isn't deployed yet | Resolved by dependency ordering: run `discover_subflow_tree.py` (Step 3b) to get the leaves-first order, transform in that order, and bundle-validate (`validate_flow.sh --bundle`) so intra-tree refs resolve |
| `A required input parameter is missing: 'label'` | `ComponentInstance` field is missing the `label` inputParameter | Transformer moves label from `<fieldText>` to `label` inputParameter |
| `We can't find this input attribute: "placeholder"` | `placeholder` not supported in DC | Stripped by transformer — bake text into label |
| `We can't find this input attribute: "helpText"` | `helpText` not supported in DC | Stripped by transformer — bake text into label |
| `We can't find this input attribute: "min"` / `"max"` on dcNumeric | `min`/`max` only valid on `dcCounter`, not `dcNumeric` | Stripped by transformer; switch to `dcCounter` if numeric constraints are needed |
| `We can't find this input attribute: "minimumDate"` / `"maximumDate"` | Correct attributes are `minDate` / `maxDate` | Replaced by transformer |
| `We can't find this input attribute: "multiSelection"` | Correct attribute is `isMultiSelection` | Replaced by transformer |
| `We can't find this input attribute: "disabled"` / `"readOnly"` on Lookup | Correct: `isDisabled` / `isReadonly` (lowercase `o`) | Replaced by transformer |
| `We can't find this input attribute: "recordIds"` on Lookup | Correct: `recordIdCollection` | Replaced by transformer |
| `'Range' is not a valid value for the enum 'FlowScreenFieldType'` | Slider (`Range`) not valid in DataCaptureFlow | Flagged by transformer as SKIPPED — replace manually with `dcNumeric` or `dcCounter` |
| `This flow can't reference [X] because the referenced flow type is Autolaunched Flow` | Calling an AutoLaunched subflow from DataCaptureFlow | Not auto-fixable; inline the logic or convert subflow to DataCaptureFlow |
| `storeOutputAutomatically field isn't supported` on Repeater | `storeOutputAutomatically` must not be on the Repeater itself | Transformer omits it on the Repeater; only nested fields inside the Repeater get it |
| `Element X is duplicated at this location` (non-inputParameters) | XML elements of same type are not in a contiguous block | Reorder the XML so all same-type elements are grouped |
| `Error while resolving default value reference` *(runtime — not deploy)* | Complex formula in `DisplayText` (`IF`, `CASE`, date math) | Transformer warns; pre-calculate in Assignment → reference simple variable in DisplayText |
| `isRequired=true` blocks hidden field *(runtime — not deploy)* | Required check fires even when field is hidden behind `visibilityRule` | Transformer warns; manually clear `isRequired` and add `validationRule` |
| `outputAssignments` in `dynamicChoiceSets` populates blank *(runtime — not deploy)* | `outputAssignments` inside choice sets deploys but does NOT populate variables at mobile runtime | Replace with post-selection `recordLookups` using `outputAssignments` |
| `We can't find this input attribute: "required"` on `dcCheckbox` / `dcToggle` | These boolean-backed components don't expose a `required` input attribute — unlike other `ComponentInstance` types, they don't need one to enforce required-ness | Transformer skips the `required` inputParameter injection for `dcCheckbox`/`dcToggle` extensions; `<isRequired>` is still set |

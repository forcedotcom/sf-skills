<!-- Parent: building-omnistudio-omniscript/SKILL.md -->

# OmniScript Best Practices

> **Applies to**: OmniStudio OmniScripts (OmniProcessType='OmniScript')
> **Companion**: See `element-types.md` for PropertySetConfig reference per element type

---

## Table of Contents

1. [Step Design Patterns](#1-step-design-patterns)
2. [Data Prefill Strategies](#2-data-prefill-strategies)
3. [Validation Patterns](#3-validation-patterns)
4. [Navigation Patterns](#4-navigation-patterns)
5. [Performance Optimization](#5-performance-optimization)
6. [Embedding vs Linking OmniScripts](#6-embedding-vs-linking-omniscripts)
7. [Naming Conventions](#7-naming-conventions)
8. [Error Handling](#8-error-handling)
9. [Testing Strategies](#9-testing-strategies)
10. [Security Considerations](#10-security-considerations)

---

## 1. Step Design Patterns

### Wizard-Style (Multi-Step Sequential)

The default and most common pattern. Each Step represents a phase of the process, with linear forward progression.

**When to use:**
- Guided intake forms (service requests, applications, enrollments)
- Multi-phase data collection where later steps depend on earlier inputs
- Processes that benefit from chunking to reduce cognitive load

**Design rules:**
- Limit each Step to 7-10 input elements (cognitive load threshold)
- Group related fields together within a Step
- Place data-fetching actions (DataRaptor Extract, IP Action) at the beginning of the Step they serve
- Use descriptive Step labels that orient the user (e.g., "Contact Information", "Review & Submit")
- The final Step should be a review/confirmation screen

**Example structure:**
```
Step 1: "Account Selection"    -> Type Ahead (account search) + DataRaptor Extract (prefill)
Step 2: "Service Details"      -> Select, Text, Date inputs for the request
Step 3: "Attachments"          -> File upload + Text Area for notes
Step 4: "Review & Submit"      -> Text Blocks displaying collected data + Submit Action
```

### Single-Page (All Elements Visible)

All elements rendered on a single Step with no navigation between pages.

**When to use:**
- Simple forms with 5 or fewer inputs
- Quick-action modals launched from FlexCards
- Inline editing scenarios

**Design rules:**
- Use a single Step element containing all inputs
- Omit navigation buttons (no Next/Previous needed)
- Keep the total element count low to avoid scroll fatigue
- Consider whether a FlexCard with inline editing would be simpler

### Conditional Branching

Steps are shown or hidden based on user input or data conditions.

**When to use:**
- Processes where the path varies by user selection (e.g., "New" vs "Existing" customer)
- Compliance workflows where certain sections only apply to specific scenarios
- Multi-product intake where product type determines required fields

**Design rules:**
- Use the `show` property on Steps with conditional expressions
- Reference data JSON values using merge field syntax: `%ShowStep3%` or `{ShowStep3}`
- Set controlling values early in the flow (Step 1 or data prefill)
- Test all permutations of the conditional paths
- Document the branching logic in Step descriptions

```json
{
  "show": {
    "group": {
      "operator": "AND",
      "rules": [
        {
          "field": "CustomerType",
          "condition": "=",
          "data": "New"
        }
      ]
    }
  }
}
```

### Hub-and-Spoke

A central Step allows navigation to sub-sections, each completing independently.

**When to use:**
- Complex case management with multiple independent sections
- Forms where the user may complete sections in any order
- Processes requiring non-linear data entry

**Design rules:**
- Central hub Step with Navigate Actions to each spoke
- Each spoke completes and returns to the hub
- Track section completion status in the data JSON
- Display completion indicators on the hub Step

---

## 2. Data Prefill Strategies

### DataRaptor Extract Prefill

Use DataRaptor Extract Actions at the beginning of a Step to populate elements with existing Salesforce data.

**Best practice:**
- Place the Extract Action as the first element in the Step (lowest Order value)
- Configure `executionConditionFormula` to skip the fetch if data already exists
- Map Extract output keys to match element names for automatic binding
- Filter the Extract query to return only the needed fields

```json
{
  "bundle": "DR_ExtractAccountDetails",
  "inputMap": {
    "AccountId": "%SelectedAccountId%"
  },
  "outputMap": {
    "AccountName": "AccountName",
    "BillingAddress": "BillingAddress"
  }
}
```

### Integration Procedure Prefill

Use IP Actions for complex prefill that requires server-side logic, aggregation, or external API calls.

**Best practice:**
- Set `remoteOptions.preTransformBundle` if data needs shaping before display
- Use `executionConditionFormula` to avoid re-fetching on back navigation
- Cache results in the data JSON so subsequent Steps can reference them without additional calls

### Contextual Prefill (Launch Parameters)

OmniScripts can receive data when launched from FlexCards, Lightning pages, or URLs.

**Best practice:**
- Document all expected launch parameters in the OmniScript description
- Validate that required parameters are present; show an error Step if missing
- Use Set Values elements to normalize parameter formats before processing

### Save & Resume Prefill

When "Save for Later" is enabled, the OmniScript restores the full data JSON on resume.

**Best practice:**
- Configure `saveNameTemplate` for meaningful save identifiers
- Set `saveExpireInDays` to prevent stale saved instances
- Test that all elements re-render correctly from saved JSON
- Handle edge cases where referenced data may have changed between save and resume

---

## 3. Validation Patterns

### Element-Level Validation

Configure validation directly on input elements via PropertySetConfig.

| Property | Purpose | Example |
|----------|---------|---------|
| `required` | Field must have a value | `"required": true` |
| `pattern` | Regex pattern match | `"pattern": "^[A-Z]{2}\\d{6}$"` |
| `min` / `max` | Numeric range | `"min": 1, "max": 100` |
| `minLength` / `maxLength` | Text length range | `"minLength": 5, "maxLength": 255` |
| `minDate` / `maxDate` | Date range | `"minDate": "TODAY", "maxDate": "+30"` |

### Validation Elements

Use Validation elements for cross-field and business rule validation.

**Best practice:**
- Place Validation elements at the end of a Step, before the navigation connector
- Write clear, user-actionable error messages
- Reference multiple fields in the validation formula for cross-field checks
- Group related validations in a single Validation element when possible

```json
{
  "validationFormula": "%EndDate% > %StartDate%",
  "errorMessage": "End date must be after the start date."
}
```

### Step-Level Validation

Prevent the user from advancing to the next Step until all validations pass.

**Best practice:**
- Combine `required` properties on inputs with Validation elements for complex rules
- Use the Step's `validationRequired` property to enforce completion
- Display inline validation messages near the field, not only at the top of the page

### Server-Side Validation

Use Integration Procedure Actions for validations that require database lookups or external checks.

**Best practice:**
- Display a loading indicator during server-side validation
- Handle timeout and error responses gracefully
- Cache validation results to avoid redundant server calls on back-navigation

---

## 4. Navigation Patterns

### Standard Linear Navigation

Default back/forward progression through Steps.

**Configuration:**
- `allowSaveForLater`: Enable save & resume functionality
- `cancelAction`: Define behavior when user clicks Cancel (redirect URL or close modal)
- `showStepChart`: Display step progress indicator
- `stepChartPlacement`: Position the step chart (top, left, right)

### Conditional Step Skipping

Skip Steps that are not relevant based on collected data.

**Best practice:**
- Use the `show` property on Steps rather than Navigate Actions for conditional paths
- The OmniScript engine automatically skips hidden Steps during forward navigation
- Test that skipped Steps do not contribute invalid data to the JSON

### Custom Navigation Buttons

Override default Next/Previous with Navigate Actions for non-linear flows.

**Best practice:**
- Maintain a consistent button layout across Steps
- Label navigation buttons with the destination Step name, not generic "Next"
- Disable the Previous button on the first Step
- Consider whether non-linear navigation will confuse the user

### Cancel and Exit

**Best practice:**
- Prompt for confirmation before discarding entered data
- Offer "Save for Later" alongside Cancel when appropriate
- Redirect to a meaningful page after cancellation (not a blank screen)

---

## 5. Performance Optimization

### Lazy Loading Elements

Configure action elements to execute only when their containing Step becomes visible.

**Best practice:**
- Set `executionConditionFormula` on DataRaptor Extract and IP Actions
- Use Step-level activation triggers rather than OmniScript-level `onLoad` actions
- Prefetch only the data needed for the first Step on initial load

### Conditional Visibility vs Conditional Rendering

| Approach | Behavior | Performance Impact |
|----------|----------|--------------------|
| `show` on elements | Element is not rendered in DOM | Lower memory, faster rendering |
| CSS visibility | Element is rendered but hidden | Higher memory, same load time |

**Best practice:**
- Use the `show` property for elements that may not be needed at all
- Avoid rendering large data tables or Loop Blocks that the user may never see

### Data Volume in Loop Blocks

Loop Blocks render elements for each item in a data array. Large arrays degrade performance.

**Best practice:**
- Limit the data array to 50 items or fewer for interactive Loop Blocks
- Implement server-side pagination via Integration Procedures for large datasets
- Use Type Ahead elements instead of Loop Blocks when the user needs to search/select from a large list

### Minimize Action Element Count

Each action element (DataRaptor, IP, Remote Action) represents a server round-trip.

**Best practice:**
- Combine multiple data fetches into a single Integration Procedure where possible
- Fetch all data needed for a Step in one action, not one action per field
- Use Set Values to derive calculated fields client-side instead of calling the server

### Image and Static Content

**Best practice:**
- Host images on a CDN or Salesforce Static Resource rather than embedding base64 in Text Blocks
- Minimize HTML complexity in Text Block elements
- Use the Image element type instead of `<img>` tags in Text Blocks

---

## 6. Embedding vs Linking OmniScripts

### Embedding (Child OmniScript)

An OmniScript rendered inside another OmniScript as a reusable sub-process.

**When to embed:**
- The sub-process is a self-contained unit reused across multiple parent OmniScripts
- The parent needs data from the child's interaction (child data merges into parent JSON)
- The user should not leave the parent context

**Design rules:**
- Pass required data from parent to child via `prefillJSON` mapping
- Configure the child to suppress its own navigation when embedded
- Test data merge behavior: child data is added to the parent JSON under the child element's name
- Avoid embedding more than 2 levels deep (parent -> child -> grandchild is the practical limit)
- Watch for name collisions between parent and child data JSON keys

### Linking (Navigate Action)

A Navigate Action redirects to a separate OmniScript in a new context.

**When to link:**
- The processes are independent and do not share a data context
- The user is transitioning from one workflow to a different one
- The target OmniScript is also used standalone (not just as a sub-component)

**Design rules:**
- Pass context data via URL parameters or the Navigate Action's `params` property
- The linked OmniScript starts fresh with its own data JSON
- Handle the return navigation (redirect back to the originating page if needed)

### Decision Matrix

| Factor | Embed | Link |
|--------|-------|------|
| Data sharing needed | Yes | No |
| Reused as standalone | Sometimes | Yes |
| User stays in context | Yes | No |
| Performance concern | Adds to page weight | Separate page load |
| Depth > 2 levels | Avoid | Preferred |

---

## 7. Naming Conventions

### OmniScript Type/SubType

- **Type**: Business domain or process category. Use `PascalCase`. Examples: `ServiceRequest`, `MemberEnrollment`, `ClaimProcessing`
- **SubType**: Specific variation or action. Use `PascalCase`. Examples: `CreateNew`, `UpdateAddress`, `FileAppeal`
- **Language**: Use standard locale codes. Default: `English`

### Element Names

- Use `PascalCase` for all element names
- Prefix action elements with their type: `DRExtract_AccountInfo`, `IP_ValidateEligibility`, `Nav_ReturnToCase`
- Name Steps with the section they represent: `Step_ContactInfo`, `Step_ReviewSubmit`
- Name input elements descriptively: `FirstName`, `PreferredContactMethod`, `RequestedStartDate`

### Data JSON Keys

- Match element names for automatic binding
- Use consistent casing throughout the OmniScript
- Avoid special characters, spaces, and reserved words in key names
- Document the data JSON schema for complex OmniScripts

---

## 8. Error Handling

### Action Element Errors

Every DataRaptor, Integration Procedure, and Remote Action element should handle failures.

**Best practice:**
- Set `showError: true` and provide a meaningful `errorMessage` in PropertySetConfig
- Use `responseJSONPath` to extract specific error details from the response
- Implement a fallback Step that displays when critical actions fail
- Log errors server-side via an IP Action for monitoring

### User Input Errors

**Best practice:**
- Show inline error messages immediately on invalid input (not only on Step advance)
- Use red visual indicators and position error text near the offending field
- Provide specific guidance on how to fix the error (not just "Invalid input")

### Network and Timeout Errors

**Best practice:**
- Configure `remoteTimeout` on IP Actions for long-running operations
- Display a loading indicator during server calls
- Offer a retry option when transient errors occur
- If the OmniScript cannot continue, display a clear message with a support contact

---

## 9. Testing Strategies

### Manual Testing Checklist

- [ ] Walk through all Steps with valid data (happy path)
- [ ] Attempt to advance with missing required fields
- [ ] Enter invalid data for each validated input
- [ ] Exercise all conditional branches (show/hide Steps and elements)
- [ ] Test with prefilled vs empty launch parameters
- [ ] Test Save for Later and Resume
- [ ] Verify data is correctly submitted/saved
- [ ] Test Cancel behavior and confirmation prompt
- [ ] Check rendering on mobile viewport
- [ ] Verify with different user profiles/permission sets

### Integration Testing

- [ ] Verify all DataRaptor Extract Actions return expected data
- [ ] Verify all DataRaptor Load Actions create/update records correctly
- [ ] Verify all IP Actions execute and return expected responses
- [ ] Test with integration failures (disable a DataRaptor, verify error handling)
- [ ] Test with large data volumes in Loop Blocks

### Cross-Browser and Device Testing

- [ ] Desktop: Chrome, Firefox, Safari, Edge
- [ ] Mobile: iOS Safari, Android Chrome
- [ ] Tablet: verify responsive layout breakpoints
- [ ] Community/Experience Cloud: verify guest and authenticated rendering

---

## 10. Security Considerations

### Data Exposure

- OmniScript data JSON is client-side. Sensitive data (SSNs, passwords, tokens) should be processed server-side in Integration Procedures and never stored in the client JSON.
- Use `maskValue` on sensitive input elements to prevent shoulder-surfing.
- Strip sensitive fields from the data JSON before the Submit Action using Set Values.

### Access Control

- OmniScript visibility is controlled by the page or component it is placed on, not by the OmniScript itself.
- Ensure Integration Procedures enforce record-level and field-level security (FLS).
- Do not rely on hiding Steps or elements as a security mechanism; the data JSON can be inspected client-side.

### Input Sanitization

- Validate all user input before passing to DataRaptor Load or IP Actions.
- Use `pattern` (regex) on text inputs to restrict input format.
- Server-side IPs should validate input independently; do not trust client-side validation alone.

---

## 11. Common Troubleshooting

| Symptom | Cause | Resolution |
|---------|-------|------------|
| OmniScript not rendering | OmniScript is inactive or element hierarchy is broken | Check `IsActive=true` on the OmniProcess record; verify all Steps (Level=0) and child elements are correctly parented |
| Data not prefilling | DataRaptor Extract output mapping mismatch or wrong JSON path | Verify DataRaptor Extract output key names exactly match element names; check JSON path syntax in outputMap |
| IP action failing silently | Integration Procedure input shape mismatch or IP is inactive | Test the IP independently with the same inputMap payload; verify IP is active; check `showError: true` is set on the action element |
| Steps not showing | Conditional visibility expression on the Step evaluates incorrectly | Review the `show` expression on the Step element; log data JSON values to verify the controlling field is set |

---

## Key Takeaways

1. **Keep Steps focused**: 7-10 elements maximum per Step. Split complex processes into more Steps rather than cramming elements.
2. **Prefill early, validate often**: Load data at the start of each Step and validate before allowing progression.
3. **Error handling is not optional**: Every server call needs a failure path. Every required input needs validation.
4. **Performance is a design constraint**: Lazy-load data, limit Loop Block iterations, and minimize server round-trips.
5. **Embed sparingly, link freely**: Embedding couples OmniScripts tightly. Reserve it for genuine sub-processes.
6. **Security is server-side**: The client JSON is not a trust boundary. Sensitive logic belongs in Integration Procedures.

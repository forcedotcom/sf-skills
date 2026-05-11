---
name: generating-lightning-component
description: "Generate Salesforce Lightning Web Components (LWC) and supporting component bundle files. Use when the user asks to create, build, scaffold, generate, implement, refactor, or review an LWC, Lightning Web Component, UI component, Flow screen component LWC, Lightning App Builder component, Experience Cloud component, Agentforce-capable component, or any lwc/**/*.js, .html, .css, .js-meta.xml bundle. Also trigger for @wire, Lightning Data Service, Apex/GraphQL data access from LWC, Lightning Message Service, SLDS styling, accessibility, or Jest tests. Do NOT trigger for Apex-only implementation, Flow XML generation, Aura components, Visualforce, Lightning app metadata, or unrelated Salesforce metadata."
---

# Generating Lightning Components

## Goal

Generate production-ready Salesforce Lightning Web Components (LWC) with the correct bundle structure, metadata exposure, data access pattern, accessibility, styling, security, and test approach.

This skill uses the **PICKLES Framework** as the architectural checklist for LWC design:

- **P**rototype — clarify the user journey and expected UI states before writing code.
- **I**ntegrate — choose the correct data access pattern.
- **C**omposition — split the component into sensible parent/child boundaries.
- **K**inetics — define events, interactions, loading states, and state transitions.
- **L**ibraries — prefer Salesforce platform APIs, base Lightning components, and LDS before custom code.
- **E**xecution — optimise rendering, lifecycle usage, and browser performance.
- **S**ecurity — enforce CRUD/FLS, sharing, LWS-safe JavaScript, and safe error handling.

**Attribution:** PICKLES Framework by **David Picksley**. Reference: https://www.salesforceben.com/the-ideal-framework-for-architecting-salesforce-lightning-web-components/

## When to Use This Skill

Use this skill when the task involves:

- Creating or modifying a Lightning Web Component bundle.
- Creating files under `force-app/main/default/lwc/{componentName}/`.
- Generating `.js`, `.html`, `.css`, `.js-meta.xml`, or Jest test files for an LWC.
- Exposing an LWC to Lightning App Builder, Record Pages, Home Pages, Experience Cloud, Flow screens, or Agentforce.
- Building UI that reads or writes Salesforce data.
- Using Lightning Data Service, UI API, Apex, GraphQL, Lightning Message Service, or platform events from an LWC.
- Creating accessible, SLDS-aligned, responsive component markup.
- Creating Jest tests for an LWC.

Do not use this skill for:

- Apex-only classes or triggers. Delegate to `generating-apex`.
- Apex test classes. Delegate to `generating-apex-test`.
- Flow XML generation. Delegate to `generating-flow`.
- Aura components or Visualforce pages.
- Lightning App metadata generation without an LWC bundle.

## Required Inputs

Gather or infer the following before authoring:

- Component purpose and user outcome.
- Target surface:
  - `lightning__RecordPage`
  - `lightning__AppPage`
  - `lightning__HomePage`
  - `lightning__Tab`
  - `lightning__FlowScreen`
  - `lightning__ExperiencePage`
  - `lightning__Agentforce`
  - other supported target
- Component API name in camelCase.
- Whether the component needs a public property exposed through `.js-meta.xml`.
- Data source:
  - no Salesforce data
  - Lightning Data Service / UI API
  - Apex controller
  - GraphQL wire adapter
  - Lightning Message Service
  - external service through Apex
- Required UX states:
  - initial
  - loading
  - populated
  - empty
  - error
  - saving
  - success
- Whether Jest tests are required.
- Any existing project conventions, shared components, utility modules, or styling rules.

If the user gives a clear request, generate immediately. Do not ask unnecessary follow-up questions. Make a sensible default and document it in the report.

## Component Bundle Deliverables

Default bundle path:

```text
force-app/main/default/lwc/{componentName}/
```

Generate the relevant files:

```text
{componentName}.html
{componentName}.js
{componentName}.js-meta.xml
{componentName}.css                # only when styling is needed
__tests__/{componentName}.test.js   # when tests are requested or expected
```

Optional supporting files:

```text
{componentName}.svg
{componentName}.json
utils.js
constants.js
```

Do not generate unused files. Keep the bundle minimal.

## Workflow

All steps are sequential. Do not skip validation just because the component looks simple.

### Phase 1 — Design with PICKLES

1. **Prototype**
   - Restate the component goal in one sentence.
   - Identify the target user and the expected interaction.
   - List the required UI states.

2. **Integrate**
   - Choose the smallest correct data access pattern.
   - Prefer platform-native data APIs before custom Apex.
   - Use Apex only when business logic, aggregation, complex SOQL, DML orchestration, callouts, or security-wrapped server behaviour is required.

3. **Composition**
   - Decide whether this should be one component or a parent/child set.
   - Split child components only when they have a distinct responsibility or reuse value.
   - Keep public APIs narrow and explicit.

4. **Kinetics**
   - Define the event contract before coding.
   - Prefer parent-child events for local communication.
   - Use Lightning Message Service only for cross-DOM or unrelated component communication.
   - Include loading, disabled, empty, and error states.

5. **Libraries**
   - Prefer Lightning base components over custom HTML controls.
   - Prefer Lightning Data Service/UI API for simple record operations.
   - Use SLDS utility classes and styling hooks rather than hardcoded styling.

6. **Execution**
   - Avoid unnecessary work in lifecycle hooks.
   - Avoid setting reactive state in `renderedCallback()` unless guarded.
   - Debounce user input for search/filter behaviours.
   - Avoid large DOM renders; paginate or virtualise when needed.

7. **Security**
   - Do not expose unsafe HTML.
   - Do not trust client-side validation alone.
   - Ensure Apex used by the component enforces sharing, CRUD/FLS, and safe error handling.
   - Avoid hardcoded IDs, secrets, object assumptions, and user-specific values.

### Phase 2 — Author

Create the component files using these rules.

#### JavaScript Rules

- Use `LightningElement` from `lwc`.
- Use `@api` only for true public component properties.
- Do not mutate `@api` input values directly.
- Use private state for internal mutations.
- Use getters for derived template state.
- Use `@wire` for reactive read-only data.
- Use imperative Apex or UI API functions for explicit actions, saves, and DML.
- Store wired results if `refreshApex()` is required.
- Always handle both `data` and `error` paths.
- Normalise errors into user-safe strings.
- Avoid `console.log()` in generated production code.
- Avoid global DOM queries. Query only within `this.template`.
- Clean up timers, subscriptions, and listeners in `disconnectedCallback()`.

#### HTML Rules

- Use Lightning base components where available.
- Use `lwc:if`, `lwc:elseif`, and `lwc:else`; do not use legacy `if:true` / `if:false`.
- Every `for:each` item must have a stable key. Never use array index as the key.
- Include accessible labels, alternative text, assistive text, and ARIA attributes where needed.
- Do not place complex logic in the template when a getter is clearer.
- Include visible error and empty states.

#### CSS Rules

- Do not hardcode brand colours unless the user explicitly requests it.
- Prefer SLDS classes, design tokens, and styling hooks.
- Keep CSS scoped to the component.
- Do not use brittle selectors against Salesforce-owned DOM.
- Support responsive layout where the component can appear in narrow regions.

#### Metadata Rules

Every LWC bundle must include `{componentName}.js-meta.xml`.

- Set `isExposed` based on whether the component is intended for builder/runtime placement.
- Include only the targets the user needs.
- For `lightning__RecordPage`, include supported objects when known.
- Expose configurable properties only when useful for admins/builders.
- Use a current project API version unless the repository convention says otherwise.

Default metadata shape:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<LightningComponentBundle xmlns="http://soap.sforce.com/2006/04/metadata">
    <apiVersion>66.0</apiVersion>
    <isExposed>true</isExposed>
    <masterLabel>Component Label</masterLabel>
    <description>Short description of the component.</description>
    <targets>
        <target>lightning__RecordPage</target>
    </targets>
</LightningComponentBundle>
```

### Phase 3 — Test

When generating or modifying meaningful logic, create or update Jest tests.

Test at least:

- component renders successfully
- loading state
- populated state
- empty state
- error state
- user interaction/event dispatch
- Apex/wire/UI API success and error paths, where applicable

Jest file location:

```text
force-app/main/default/lwc/{componentName}/__tests__/{componentName}.test.js
```

Testing rules:

- Clean up the DOM after each test.
- Mock Apex, UI API, LDS, GraphQL, and LMS boundaries.
- Await render cycles after state changes.
- Assert user-visible behaviour rather than private implementation details.
- Do not rely on Salesforce org data.

### Phase 4 — Validate

Before reporting completion, attempt the relevant validation commands.

Preferred commands:

```bash
npm test -- --runInBand {componentName}.test.js
sf project deploy start --source-dir force-app/main/default/lwc/{componentName} --dry-run
```

If the project has custom scripts, use the repository convention instead.

If validation tools are unavailable, state that clearly in the report and explain what was not run.

## Data Access Decision Matrix

| Need | Preferred Pattern | Notes |
|---|---|---|
| Display one record | Lightning Data Service / UI API | Use `getRecord` or record form base components. |
| Simple create/edit/view form | Base record form components | Prefer `lightning-record-form`, `lightning-record-edit-form`, or `lightning-record-view-form`. |
| Reactive read-only data | `@wire` | Use LDS, UI API, GraphQL, or cacheable Apex. |
| User-triggered save/action | Imperative call | Use UI API or Apex depending on complexity. |
| Complex SOQL/business logic | Apex | Apex must enforce sharing, CRUD/FLS, and safe errors. |
| Related graph-shaped data | GraphQL wire adapter | Useful for related records and reducing over-fetching. |
| Cross-page/component communication | Lightning Message Service | Use only when parent-child events are insufficient. |
| External API | Apex callout via Named Credential | Never call external services with secrets from client JavaScript. |

## Event Rules

Use the smallest event scope that works.

Preferred event:

```javascript
this.dispatchEvent(new CustomEvent('select', {
    detail: { recordId: this.recordId }
}));
```

Rules:

- Event names must be lowercase and not prefixed with `on`.
- Use primitive or copied object data in `detail`.
- Avoid `bubbles: true, composed: true` unless the event must cross component boundaries.
- Document public event contracts in the component comments or final report.

## Apex Boundary Rules

When Apex is required:

- Create or update the Apex via `generating-apex`.
- The Apex class must use a sharing declaration.
- Read-only methods used with `@wire` must be `@AuraEnabled(cacheable=true)`.
- Mutating methods must not be cacheable.
- Apex must enforce CRUD/FLS.
- Apex must return DTOs/wrappers when that is cleaner than exposing raw SObjects.
- Apex must throw user-safe `AuraHandledException` messages for expected UI errors.
- Apex tests are required and must be handled by `generating-apex-test`.

## Accessibility Rules

Hard-stop if generated markup would violate these basics:

- Interactive elements must be keyboard accessible.
- Icon-only buttons must have alternative text or assistive text.
- Inputs must have labels.
- Loading states must be communicated.
- Error messages must be visible and associated with the relevant UI where possible.
- Modal/dialog patterns must manage focus correctly.
- Do not use colour alone to communicate meaning.

## Security Rules

Hard-stop if the component would require unsafe behaviour:

- Do not use `lwc:dom="manual"` unless the user explicitly needs it and the risk is explained.
- Do not inject unsanitised HTML.
- Do not store credentials, tokens, secrets, or API keys in the component.
- Do not bypass CRUD/FLS by moving sensitive decisions into client-side JavaScript.
- Do not hardcode IDs.
- Do not expose sensitive implementation errors to users.
- Do not use unsupported browser globals or libraries that conflict with Lightning Web Security.

## Naming Conventions

| Item | Convention | Example |
|---|---|---|
| Component folder | camelCase | `accountSummaryCard` |
| JavaScript class | PascalCase | `AccountSummaryCard` |
| Public property | camelCase | `recordId` |
| HTML attribute | kebab-case | `record-id` |
| Event name | lowercase | `recordselect` |
| CSS class | kebab-case | `summary-card` |
| Jest file | `{component}.test.js` | `accountSummaryCard.test.js` |

## Output Expectations

When finished, report in this order:

```text
LWC work:
Component:
Files:
Pattern:
PICKLES:
Targets:
Data:
Events:
Accessibility:
Security:
Testing:
Validation:
Next step:
```

The report must be specific. Do not say "tests pass" unless tests were actually run.

## Cross-Skill Integration

| Need | Delegate To | Reason |
|---|---|---|
| Apex controller/service | `generating-apex` | Server-side logic and security. |
| Apex tests | `generating-apex-test` | Required Apex coverage and test-fix loop. |
| Flow XML generation | `generating-flow` | Declarative automation metadata. |
| Flow screen component wrapper | This skill + `generating-flow` if a Flow must also be generated | LWC owns UI; Flow owns orchestration. |
| Lightning app metadata | `generating-lightning-app` | App container metadata. |
| Deploy component bundle | deployment skill if available | Org rollout and validation. |

## Examples

### Example 1 — Record Page Summary Component

User request:

```text
Create an LWC for an Account record page that shows open Opportunities and lets the user refresh the list.
```

Expected approach:

- Target: `lightning__RecordPage`
- Data: cacheable Apex or GraphQL, depending on project conventions
- UI states: loading, populated, empty, error
- Event: none unless parent communication is required
- Tests: mock data success/error and refresh interaction

### Example 2 — Flow Screen Component

User request:

```text
Create a Flow screen LWC that lets a user select a Care Home and outputs the selected Account Id.
```

Expected approach:

- Target: `lightning__FlowScreen`
- Public `@api` output property for selected record Id
- Use UI API or Apex depending on search/filtering needs
- Include keyboard-accessible selection behaviour
- Jest test event/output behaviour

### Example 3 — App Builder Configurable Component

User request:

```text
Create an LWC admin can place on a Home Page with a configurable title and max number of records.
```

Expected approach:

- Target: `lightning__HomePage`
- Expose `@api title` and `@api maxRecords`
- Define both properties in `.js-meta.xml`
- Validate defaults in JavaScript
- Test configured and default states

---
name: generating-lightning-component
description: >
  Generate, modify, review, harden, and test Salesforce Lightning Web Components (LWC).
  Use when the user asks to create, build, scaffold, edit, refactor, review, or test an
  LWC component bundle, or when work touches lwc/**/*.js, .html, .css, .js-meta.xml,
  __tests__/*.test.js, wire service, Lightning Data Service, UI API, Apex integration,
  GraphQL integration, Lightning Message Service, SLDS styling, accessibility,
  performance, Flow screen components, Experience Cloud components, Lightning App Builder
  exposure, or Agentforce-discoverable UI components.
  Do NOT trigger for Apex-only implementation, Apex test classes, Flow XML generation,
  Aura components, Visualforce pages, or deployment-only work.
license: MIT
metadata:
  version: "1.0.0"
  primary_source: "Jaganpro/sf-skills skills/sf-lwc"
  original_author: "Jag Valaiyapathy"
  contributors:
    - "David Picksley, ThirdEye Consulting — PICKLES Framework"
  scoring: "165 points across 8 categories, adapted from sf-lwc"
---

# generating-lightning-component: Lightning Web Components Development

Use this skill when the user needs **Lightning Web Components**: LWC bundles, wire patterns, Apex or GraphQL integration, Lightning Data Service, UI API, Lightning Message Service, SLDS styling, accessibility, performance work, Flow screen LWCs, Experience Cloud LWCs, or Jest unit tests.

This skill is primarily adapted from the `sf-lwc` skill by **Jag Valaiyapathy** and uses the **PICKLES Framework** by **David Picksley, Third Eye Consulting** as the core architecture method for planning robust LWCs.

## Attribution

This skill is based primarily on:

- **`sf-lwc` by Jag Valaiyapathy**  
  Source: `https://github.com/Jaganpro/sf-skills/tree/main/skills/sf-lwc`

It incorporates and preserves attribution for:

- **PICKLES Framework by David Picksley, Third Eye Consulting**  
  Reference: `https://www.salesforceben.com/the-ideal-framework-for-architecting-salesforce-lightning-web-components/`

Additional inspiration and reference sources from the original `sf-lwc` skill include official Salesforce documentation, LWC Recipes, SLDS guidance, James Simone's LWC/Jest patterns, Saurabh Samir's LWC directive work, and the source skill's own reference map.

## When This Skill Owns the Task

Use this skill when the work involves any of the following:

- `force-app/main/default/lwc/**`
- `lwc/**/*.js`
- `lwc/**/*.html`
- `lwc/**/*.css`
- `lwc/**/*.js-meta.xml`
- `lwc/**/__tests__/*.test.js`
- component scaffolding and bundle design
- Lightning App Builder component exposure
- Record Page, App Page, Home Page, Tab, Flow Screen, Experience Cloud, or Agentforce-discoverable component targets
- `@api`, `@wire`, decorators, reactive state, lifecycle hooks, or template directives
- Lightning Data Service, UI API, Apex, GraphQL, LMS, or external data via Apex
- SLDS 2, styling hooks, design tokens, dark mode readiness, responsive UI, or accessibility
- Jest tests for Lightning Web Components
- LWC performance, rendering behaviour, event contracts, or state management

Delegate elsewhere when the user is:

- writing Apex controllers, services, selectors, or business logic first → `generating-apex`
- writing Apex tests → `generating-apex-test`
- building Flow XML or declarative automation rather than an LWC screen component → `generating-flow`
- creating Lightning App metadata without LWC code → `generating-lightning-app`
- creating Flexipage metadata only → `generating-flexipage`
- deploying metadata only → deployment-specific skill if available
- creating custom objects, fields, tabs, permissions, list views, or validation rules → the matching metadata generation skill
- building Aura components or Visualforce pages → do not use this skill

## Required Context to Gather First

Ask for or infer:

- component purpose and target user outcome
- component API name in camelCase
- target surface:
  - `lightning__RecordPage`
  - `lightning__AppPage`
  - `lightning__HomePage`
  - `lightning__Tab`
  - `lightning__FlowScreen`
  - `lightning__ExperiencePage`
  - other supported target in the current org/project
- whether the component must run in Flow, App Builder, Experience Cloud, mobile, console, or dashboard contexts
- data source:
  - none/static
  - Lightning Data Service
  - UI API
  - Apex
  - GraphQL
  - Lightning Message Service
  - external system via Apex
- public properties to expose through `.js-meta.xml`
- events the component must emit or handle
- required UI states:
  - initial
  - loading
  - populated
  - empty
  - error
  - saving
  - success
  - disabled
- accessibility and styling expectations
- whether Jest tests are required
- relevant repository conventions, shared components, utility modules, local scripts, and API version

If the user gives enough detail to proceed, do not block on unnecessary questions. Make a sensible assumption, state it in the final report, and generate the component.

## Default Bundle Shape

Default bundle path:

```text
force-app/main/default/lwc/{componentName}/
```

Generate only the files required for the task:

```text
{componentName}.html
{componentName}.js
{componentName}.js-meta.xml
{componentName}.css
__tests__/{componentName}.test.js
```

Optional files:

```text
{componentName}.svg
constants.js
utils.js
fixtures.js
```

Do not generate unused files. Keep the component bundle focused.

## Recommended Workflow

### 1. Choose the right architecture with PICKLES

Use the **PICKLES** mindset before generating code:

```text
P → Prototype    │ Validate the user journey, UI states, and shape of the component
I → Integrate    │ Choose the right data source: LDS, UI API, Apex, GraphQL, LMS, or API
C → Composition  │ Structure parent/child components and communication boundaries
K → Kinetics     │ Define interactions, events, loading states, and state transitions
L → Libraries    │ Prefer platform APIs, base Lightning components, and SLDS
E → Execution    │ Optimise rendering, lifecycle hooks, data volume, and browser behaviour
S → Security     │ Enforce permissions, FLS, safe errors, LWS-safe code, and data protection
```

### 2. Choose the right data access pattern

| Need | Default pattern | Notes |
|---|---|---|
| Display one record | Lightning Data Service / `getRecord` | Prefer LDS/UI API before Apex. |
| Simple CRUD form | Base record form components | Use `lightning-record-form`, `lightning-record-edit-form`, or `lightning-record-view-form` when they meet the UX need. |
| Reactive read-only data | `@wire` | Use LDS, UI API, GraphQL, or cacheable Apex. |
| User-triggered save/action | Imperative UI API or Apex | Use for explicit button clicks, mutations, and DML paths. |
| Complex server query | Apex `@AuraEnabled(cacheable=true)` | For complex SOQL, aggregation, business rules, or DTO shaping. |
| Related graph data | GraphQL wire adapter | Useful for related records and pagination where supported. |
| Cross-DOM communication | Lightning Message Service | Use only when parent-child events are not enough. |
| External API | Apex callout via Named Credential | Never put secrets, tokens, or external credentials in client JavaScript. |

### 3. Start from a pattern when useful

Use known component patterns when appropriate:

- basic display component
- record summary card
- data table
- search/filter component
- modal/dialog
- Flow screen input/output component
- GraphQL component
- Lightning Message Service publisher/subscriber
- async notification component
- TypeScript-enabled component when the project supports it
- Jest test scaffolding

Do not copy a pattern blindly. Adapt it to the actual target surface, data model, and user journey.

### 4. Generate the component bundle

#### JavaScript rules

- Import `LightningElement` from `lwc`.
- Use `@api` only for true public component properties.
- Do not mutate `@api` input values directly.
- Use private state for internal mutations.
- Use getters for derived template state.
- Use `@wire` for reactive read-only data.
- Store wired results only when needed, such as for `refreshApex()`.
- Use imperative Apex or UI API functions for explicit actions, saves, and DML.
- Always handle both `data` and `error` paths.
- Normalise errors into user-safe strings.
- Avoid `console.log()` in production code.
- Avoid broad DOM queries. Query only inside `this.template`.
- Clean up timers, subscriptions, and listeners in `disconnectedCallback()`.
- Avoid setting reactive state inside `renderedCallback()` unless the operation is guarded against rerender loops.
- Debounce user input for search/filter behaviours.
- Prefer small pure helper functions for transformation logic.

#### HTML rules

- Use Lightning base components where available.
- Use SLDS utility classes for layout and spacing.
- Use current LWC template directives such as `lwc:if`, `lwc:elseif`, and `lwc:else`; avoid legacy `if:true` / `if:false` in new code.
- Every `for:each` item must have a stable key. Never use the array index as the key.
- Keep complex logic out of the template. Move it to getters.
- Include accessible labels, alternative text, assistive text, and ARIA attributes where needed.
- Include visible loading, empty, error, and success states.
- Do not rely on colour alone to communicate meaning.

#### CSS rules

- Prefer SLDS classes, design tokens, and styling hooks.
- Avoid hardcoded colours unless the user explicitly requests them.
- Keep CSS scoped to the component.
- Do not target Salesforce-owned internal DOM.
- Support narrow containers and responsive layouts.
- Build with SLDS 2 and dark mode readiness where the project supports it.

#### Metadata rules

Every LWC bundle must include `{componentName}.js-meta.xml`.

- Match the repository's configured API version. If no convention exists, use the current API version supported by the target org.
- Set `isExposed` based on whether the component is intended for builder/runtime placement.
- Include only the targets the user needs.
- For `lightning__RecordPage`, include supported objects when known.
- Expose configurable properties only when useful for admins/builders.
- Do not invent unsupported targets or capabilities.
- Only include Agentforce-specific targets/capabilities when the current project/org metadata supports them.

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

If the repo uses a different API version, follow the repo.

### 5. Validate for frontend quality

Before reporting completion, check:

- component structure
- naming consistency
- data access pattern
- error handling
- loading/empty/success/error states
- SLDS 2 and dark mode readiness
- accessibility
- event contract
- performance and rerender safety
- security and Lightning Web Security compatibility
- Jest coverage when required
- metadata targets and exposed properties
- local preview/deploy readiness

### 6. Hand off supporting backend, metadata, or deploy work

Use the matching skill when the LWC needs non-LWC work:

- Apex controller/service → `generating-apex`
- Apex test classes → `generating-apex-test`
- Flow XML/orchestration → `generating-flow`
- Flexipage placement → `generating-flexipage`
- Lightning app metadata → `generating-lightning-app`
- custom object/field/tab/permission/list view/validation metadata → matching metadata generation skill
- deployment → deployment-specific skill if available

## High-Signal Rules

- Prefer platform base components over reinventing controls.
- Prefer LDS/UI API/base record form components for straightforward record UI.
- Use `@wire` for reactive read-only use cases.
- Use imperative calls for explicit actions and DML paths.
- Use Apex only when business logic, complex queries, aggregation, external callouts, or server-side security enforcement are required.
- Keep component communication explicit and minimal.
- Use parent-child events for local communication.
- Use Lightning Message Service only for cross-DOM or unrelated component communication.
- Do not introduce inaccessible custom UI.
- Do not hardcode IDs, secrets, tokens, colours, object names, or user-specific values unless the user explicitly requires it.
- Do not bypass server-side security by moving sensitive decisions into client JavaScript.
- Do not use `lwc:dom="manual"` unless explicitly needed and the risk is explained.
- Do not inject unsanitised HTML.
- Do not expose raw exception details to users.
- Do not claim tests pass unless tests were actually run.

## Event Contract Rules

Use the smallest event scope that works.

Preferred local event shape:

```javascript
this.dispatchEvent(new CustomEvent('recordselect', {
    detail: { recordId: this.recordId }
}));
```

Rules:

- Event names must be lowercase.
- Do not prefix custom event names with `on`.
- Use primitives or copied object data in `detail`.
- Avoid `bubbles: true` and `composed: true` unless the event must cross component boundaries.
- Document public event contracts in the final report.

## Apex Boundary Rules

When Apex is required:

- Delegate Apex generation to `generating-apex`.
- Apex must use an explicit sharing declaration.
- Read-only methods used with `@wire` must be `@AuraEnabled(cacheable=true)`.
- Mutating methods must not be cacheable.
- Apex must enforce CRUD/FLS.
- Apex should return DTOs/wrappers where this is cleaner than exposing raw SObjects.
- Expected UI errors should be converted into user-safe messages.
- Apex tests are required and should be handled by `generating-apex-test`.

## Accessibility Rules

Hard-stop if the generated component would violate these basics:

- Interactive elements must be keyboard accessible.
- Icon-only buttons must have alternative text or assistive text.
- Inputs must have labels.
- Loading states must be communicated.
- Error messages must be visible.
- Modal/dialog patterns must manage focus correctly.
- Colour must not be the only indicator of status.
- Tables must use appropriate headers and accessible labels.
- Toasts or inline messages must explain what happened and what the user can do next.

## Security Rules

Hard-stop if the request requires unsafe behaviour:

- no client-side secrets
- no unsafe HTML injection
- no unsanitised `lwc:dom="manual"` usage
- no hidden permission bypass
- no hardcoded sensitive IDs
- no raw stack traces shown to users
- no unsupported browser globals that conflict with Lightning Web Security
- no third-party libraries unless they are LWS-compatible and genuinely needed

## Testing Rules

When generating or modifying meaningful logic, create or update Jest tests.

Test at least:

- component renders successfully
- loading state
- populated state
- empty state
- error state
- user interaction
- event dispatch
- wire success and error paths
- Apex/UI API/GraphQL boundary mocks where applicable
- Flow input/output behaviour for Flow screen components

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
- Do not claim Jest passed unless the command was run.

## Local Development Server Preview

Where the project and Salesforce CLI support Local Dev, preview LWC components locally with hot reload:

```bash
# Preview LWC components in isolation
sf lightning dev component --target-org <target-org-alias>

# Preview a Lightning Experience app locally
sf lightning dev app --target-org <target-org-alias>

# Preview an Experience Cloud site locally
sf lightning dev site --target-org <target-org-alias>
```

Local Dev commands can be long-running preview processes and may require an active org connection for data and Apex callouts. If the command is unavailable in the user's CLI, state that clearly and use the repository's existing validation approach instead.

## Validation Commands

Prefer repository scripts when available. Otherwise use the closest relevant commands:

```bash
npm test -- --runInBand {componentName}.test.js
sf project deploy start --source-dir force-app/main/default/lwc/{componentName} --dry-run
```

If validation tools are unavailable, state what could not be run.

## 165-Point Quality Score

Use this score as a review aid. Do not pretend it is mathematically objective; it is a structured quality checklist adapted from the source `sf-lwc` skill.

| Category | Points | Focus |
|---|---:|---|
| Component Structure | 25 | file organisation, naming, bundle shape, metadata |
| Data Layer | 25 | wire service, LDS/UI API/Apex/GraphQL choice, error handling |
| UI/UX | 25 | SLDS 2, responsiveness, empty/loading/error/success states, dark mode readiness |
| Accessibility | 20 | WCAG, labels, ARIA, keyboard navigation, focus management |
| Testing | 20 | Jest coverage, mocks, async render patterns |
| Performance | 20 | lazy loading, debouncing, rerender safety, lifecycle discipline |
| Events | 15 | explicit event contracts, LMS only when appropriate |
| Security | 15 | FLS, CRUD, sharing, LWS-safe JavaScript, safe errors |

Score meaning:

| Score | Meaning |
|---:|---|
| 150+ | production-ready LWC bundle |
| 125–149 | strong component with minor polish left |
| 100–124 | functional but review recommended |
| < 100 | significant improvement needed |

## Advanced and Release-Specific Features

The source `sf-lwc` skill references modern and release-specific LWC capabilities such as TypeScript support, advanced directives, GraphQL mutations, and Agentforce discovery.

Use these only when the current project, API version, Salesforce org, and official documentation support them.

Do not introduce release-specific syntax or metadata just because it exists in a reference. Verify before use.

Potential advanced areas:

- TypeScript-enabled LWC projects
- GraphQL wire adapter and GraphQL mutations
- dynamic event/directive patterns where supported
- SLDS 2 uplift and dark mode readiness
- Agentforce-discoverable UI capabilities where metadata supports them

## Reference Map

When generating or reviewing an LWC, consider these reference categories from the original `sf-lwc` skill and its README/CREDITS.

### Official Salesforce Documentation

- Lightning Web Components Developer Guide
- Lightning Component Library
- Component bundle metadata / `.js-meta.xml`
- Wire service
- Lightning Data Service and UI API
- Apex wire methods
- GraphQL API for Salesforce
- Lightning Message Service
- Lightning Web Security
- Jest testing for Lightning Web Components
- SLDS and SLDS styling hooks
- Salesforce CLI and Local Dev

### Community and Example Sources

- `sf-lwc` skill by Jag Valaiyapathy
- PICKLES Framework by David Picksley, Third Eye Consulting
- LWC Recipes by Salesforce Trailhead Apps
- James Simone's advanced LWC and Jest patterns
- Saurabh Samir's LWC directive and dynamic attribute patterns

### Original `sf-lwc` Reference Categories

- component patterns
- SLDS design guide
- LWC best practices
- scoring and testing
- Jest testing
- accessibility guide
- performance guide
- state management
- template anti-patterns
- LMS guide
- Flow integration guide
- advanced features
- async notification patterns
- triangle pattern
- assets and templates

Do not create broken local links to reference files unless those files are being included in the target repository. If this skill is submitted as a single `SKILL.md`, keep the reference map descriptive or link to stable external sources.

## Cross-Skill Integration

| Need | Delegate to | Reason |
|---|---|---|
| Apex controller or service | `generating-apex` | backend logic, DTOs, CRUD/FLS, callouts |
| Apex test class | `generating-apex-test` | Apex-side coverage and test-fix loops |
| Flow screen orchestration | `generating-flow` | declarative Flow metadata |
| Flexipage placement | `generating-flexipage` | page layout/container metadata |
| Lightning app metadata | `generating-lightning-app` | app container metadata |
| Custom object/field/tab/list view/permission/validation rule | matching metadata generation skill | supporting Salesforce metadata |
| Deploy component bundle | deployment skill if available | org rollout and validation |
| Agentforce-specific implementation | `developing-agentforce` where relevant | agent/action/discovery concerns beyond the LWC bundle |
| UI bundle frontend/app/site work | UI bundle skills where relevant | non-standard bundle delivery path |

## Output Format

When finishing LWC work, report in this order:

```text
LWC work:
Component:
Pattern:
Files:
Targets:
Data access:
Events:
PICKLES:
Quality score:
Accessibility:
Security:
Testing:
Validation:
Assumptions:
Next step:
```

The report must be specific. Do not say "tests pass" unless tests were actually run.

## Example Requests

Use this skill for requests like:

```text
Create a data table LWC for Account records with search and pagination.
```

```text
Build a Flow screen component that outputs the selected Care Home Account Id.
```

```text
Refactor this LWC to use LDS instead of Apex.
```

```text
Add Jest tests for this LWC's loading, data, empty, and error states.
```

```text
Make this component SLDS 2 ready and accessible.
```

```text
Create a Lightning Message Service publisher/subscriber component pair.
```

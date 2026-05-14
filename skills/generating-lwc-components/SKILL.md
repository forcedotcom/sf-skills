---
name: generating-lwc-components
description: >
  Lightning Web Components with PICKLES methodology and 165-point scoring.
  TRIGGER when: user creates/edits LWC components, touches lwc/**/*.js, .html,
  .css, .js-meta.xml files, or asks about wire service, SLDS, or Jest LWC tests.
  DO NOT TRIGGER when: Apex classes (use generating-apex), Aura components, or Visualforce.
license: MIT
metadata:
  version: "1.1"
---

# generating-lwc-components: Lightning Web Components Development

Use this skill when the user needs **Lightning Web Components**: LWC bundles, wire patterns, Apex/GraphQL integration, SLDS 2 styling, accessibility, performance work, or Jest unit tests.

## When This Skill Owns the Task

Use `generating-lwc-components` when the work involves:
- `lwc/**/*.js`, `.html`, `.css`, `.js-meta.xml`
- component scaffolding and bundle design
- wire service, Apex integration, GraphQL integration
- SLDS 2, dark mode, and accessibility work
- Jest unit tests for LWC

Delegate elsewhere when the user is:
- writing Apex controllers or business logic first → [generating-apex](../generating-apex/SKILL.md)
- building Flow XML rather than an LWC screen component → [generating-flow](../generating-flow/SKILL.md)
- deploying metadata → [deploying-metadata](../deploying-metadata/SKILL.md)

---

## Required Context to Gather First

Ask for or infer:
- component purpose and target surface
- data source: LDS, Apex, GraphQL, LMS, or external system via Apex
- whether the user needs tests
- whether the component must run in Flow, App Builder, Experience Cloud, or dashboard contexts
- accessibility and styling expectations

---

## Recommended Workflow

### 1. Choose the right architecture
Use the **PICKLES** mindset:
- prototype
- integrate the right data source
- compose component boundaries
- define interaction model
- use platform libraries
- optimize execution
- enforce security

### 2. Choose the right data access pattern
| Need | Default pattern |
|---|---|
| single-record UI | LDS / `getRecord` |
| simple CRUD form | base record form components |
| complex server query | Apex `@AuraEnabled(cacheable=true)` |
| related graph data | GraphQL wire adapter |
| cross-DOM communication | Lightning Message Service |

### 3. Start from an asset when useful
Use provided assets for:
- basic component bundles
- datatables
- modal patterns
- Flow screen components
- GraphQL components
- LMS message channels
- Jest tests
- TypeScript-enabled components

### 4. Validate for frontend quality
Check:
- accessibility
- SLDS 2 / dark mode compliance
- event contracts
- performance / rerender safety
- Jest coverage when required

### 5. Hand off supporting backend or deploy work
Use:
- [generating-apex](../generating-apex/SKILL.md) for controllers / services
- [deploying-metadata](../deploying-metadata/SKILL.md) for deployment
- [running-apex-tests](../running-apex-tests/SKILL.md) only for Apex-side test loops, not Jest

---

## High-Signal Rules

- prefer platform base components over reinventing controls
- use `@wire` for reactive read-only use cases; imperative calls for explicit actions and DML paths
- do not introduce inaccessible custom UI
- avoid hardcoded colors; use SLDS 2-compatible styling hooks / variables
- avoid rerender loops in `renderedCallback()`
- keep component communication patterns explicit and minimal

---

## Output Format

When finishing, report in this order:
1. **Component(s) created or updated**
2. **Data access pattern chosen**
3. **Files changed**
4. **Accessibility / styling / testing notes**
5. **Next implementation or deploy step**

Suggested shape:

```text
LWC work: <summary>
Pattern: <wire / apex / graphql / lms / flow-screen>
Files: <paths>
Quality: <a11y, SLDS2, dark mode, Jest>
Next step: <deploy, add controller, or run tests>
```

---

## Local Development Server

Preview LWC components locally with hot reload — no deployment needed. Run the commands in `scripts/local-dev-preview.sh` to start a local dev session for a component, app, or Experience Cloud site.

Local Dev commands install just-in-time on first run. They are long-running processes that open a browser with live preview. Changes to `.js`, `.html`, and `.css` files auto-reload instantly. Requires an active org connection for data and Apex callouts.

---

## Cross-Skill Integration

| Need | Delegate to | Reason |
|---|---|---|
| Apex controller or service | [generating-apex](../generating-apex/SKILL.md) | backend logic |
| embed in Flow screens | [generating-flow](../generating-flow/SKILL.md) | declarative orchestration |
| deploy component bundle | [deploying-metadata](../deploying-metadata/SKILL.md) | org rollout |
| create supporting metadata (message channels, objects) | [deploying-metadata](../deploying-metadata/SKILL.md) | metadata deployment |

---

## Reference File Index

### Start here
- [references/component-patterns.md](references/component-patterns.md) — component architecture patterns and bundle design
- [references/slds-design-guide.md](references/slds-design-guide.md) — SLDS 2 styling, dark mode, CSS hooks
- [references/lwc-best-practices.md](references/lwc-best-practices.md) — high-signal rules and anti-patterns
- [references/scoring-and-testing.md](references/scoring-and-testing.md) — 165-point scoring rubric across 8 categories
- [references/jest-testing.md](references/jest-testing.md) — Jest unit test patterns and async rendering helpers
- [references/slds-blueprints.json](references/slds-blueprints.json) — machine-readable SLDS component blueprints
- [references/cli-commands.md](references/cli-commands.md) — SF CLI commands for LWC development

### Accessibility / performance / state
- [references/accessibility-guide.md](references/accessibility-guide.md) — WCAG, ARIA, keyboard navigation patterns
- [references/performance-guide.md](references/performance-guide.md) — lazy loading, debouncing, rerender safety
- [references/state-management.md](references/state-management.md) — reactive state patterns and LMS
- [references/template-anti-patterns.md](references/template-anti-patterns.md) — common HTML template mistakes to avoid

### Integration / advanced features
- [references/lms-guide.md](references/lms-guide.md) — Lightning Message Service patterns
- [references/flow-integration-guide.md](references/flow-integration-guide.md) — Flow screen component design
- [references/advanced-features.md](references/advanced-features.md) — Spring '26 features: TypeScript, lwc:on, GraphQL mutations
- [references/async-notification-patterns.md](references/async-notification-patterns.md) — toast, notifications, async flows
- [references/triangle-pattern.md](references/triangle-pattern.md) — parent-child-sibling communication triangle

### Asset templates
- [assets/basic-component/basicComponent.js](assets/basic-component/basicComponent.js) — wire service, error/loading states, event dispatching
- [assets/datatable-component/datatableComponent.js](assets/datatable-component/datatableComponent.js) — datatable with inline editing
- [assets/flow-screen-component/flowScreenComponent.js](assets/flow-screen-component/flowScreenComponent.js) — Flow screen with input/output properties
- [assets/form-component/formComponent.js](assets/form-component/formComponent.js) — form validation and DML patterns
- [assets/graphql-component/graphqlComponent.js](assets/graphql-component/graphqlComponent.js) — GraphQL wire adapter with cursor-based pagination
- [assets/jest-test/componentName.test.js.example](assets/jest-test/componentName.test.js.example) — Jest test template (copy and rename, remove `.example` suffix)
- [assets/message-channel/lmsPublisher.js](assets/message-channel/lmsPublisher.js) — LMS publisher pattern
- [assets/message-channel/lmsSubscriber.js](assets/message-channel/lmsSubscriber.js) — LMS subscriber pattern
- [assets/modal-component/modalComponent.js](assets/modal-component/modalComponent.js) — modal with focus trap and ESC handling
- [assets/record-picker/recordPicker.js](assets/record-picker/recordPicker.js) — record picker with search
- [assets/state-store/store.js](assets/state-store/store.js) — reactive state store for cross-component state
- [assets/typescript-component/typescriptComponent.ts](assets/typescript-component/typescriptComponent.ts) — TypeScript-enabled component (Spring '26)
- [assets/workspace-api/workspaceComponent.js](assets/workspace-api/workspaceComponent.js) — workspace API for tab and focus management
- [assets/apex-controller/LwcController.cls](assets/apex-controller/LwcController.cls) — Apex controller with `@AuraEnabled(cacheable=true)` patterns

### Scripts
- [scripts/local-dev-preview.sh](scripts/local-dev-preview.sh) — local dev server commands for component, app, and site preview

---

## Score Guide

| Score | Meaning |
|---|---|
| 150+ | production-ready LWC bundle |
| 125–149 | strong component with minor polish left |
| 100–124 | functional but review recommended |
| < 100 | needs significant improvement |

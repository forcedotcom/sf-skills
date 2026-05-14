# generating-lwc-components

Lightning Web Components development skill with PICKLES architecture methodology, 165-point scoring, SLDS 2 compliance, and dark mode support. Build modern Salesforce UIs.

## Features

- **Component Scaffolding**: Generate complete LWC bundles (JS, HTML, CSS, meta.xml)
- **PICKLES Architecture**: Structured methodology for robust components
- **165-Point Scoring**: Validation across 8 categories (SLDS 2 + Dark Mode)
- **Wire Service Patterns**: @wire decorators for Apex & GraphQL
- **Jest Testing**: Comprehensive unit test generation
- **Spring '26 Features**: TypeScript, lwc:on, Complex Expressions

## Quick Start

### 1. Invoke the skill

```
Skill: generating-lwc-components
Request: "Create a data table component for Account records"
```

### 2. Answer requirements questions

The skill will ask about:
- Component purpose
- Data source (LDS, Apex, GraphQL)
- Target (App Page, Record Page, Flow Screen)
- Accessibility requirements

### 3. Review generated component

The skill generates:
- JavaScript controller with decorators
- HTML template with SLDS styling
- CSS with styling hooks (dark mode ready)
- meta.xml configuration
- Jest test file

## PICKLES Framework

```
P → Prototype    │ Validate ideas with wireframes & mock data
I → Integrate    │ Choose data source (LDS, Apex, GraphQL, API)
C → Composition  │ Structure component hierarchy & communication
K → Kinetics     │ Handle user interactions & event flow
L → Libraries    │ Leverage platform APIs & base components
E → Execution    │ Optimize performance & lifecycle hooks
S → Security     │ Enforce permissions, FLS, and data protection
```

## Scoring System (165 Points)

| Category | Points | Focus |
|----------|--------|-------|
| Component Structure | 25 | File organization, naming |
| Data Layer | 25 | Wire service, error handling |
| UI/UX | 25 | SLDS 2, responsiveness, dark mode |
| Accessibility | 20 | WCAG, ARIA, keyboard navigation |
| Testing | 20 | Jest coverage, async patterns |
| Performance | 20 | Lazy loading, debouncing |
| Events | 15 | Component communication |
| Security | 15 | FLS, permissions |

## Templates

| Template | Use Case |
|----------|----------|
| `basic-component/` | Simple component starter |
| `graphql-component/` | GraphQL data binding |
| `flow-screen-component/` | Flow screen integration |
| `typescript-component/` | TypeScript support (Spring '26) |

## Cross-Skill Integration

| Related Skill | When to Use |
|---------------|-------------|
| generating-apex | Create @AuraEnabled controllers |
| generating-flow | Embed in Flow screens |
| generating-metadata | Create Lightning Message Channels |
| deploying-sf-metadata | Deploy component to org |

## Spring '26 Features (API 66.0)

- **lwc:on directive**: Dynamic event binding from JavaScript
- **GraphQL Mutations**: executeMutation for create/update/delete
- **Complex Expressions**: JS expressions in templates (Beta)
- **TypeScript Support**: @salesforce/lightning-types package
- **Agentforce Discovery**: lightning__agentforce capability

## Documentation

- [Best Practices](references/lwc-best-practices.md)
- [Flow Integration](references/flow-integration-guide.md)
- [Accessibility Guide](references/accessibility-guide.md)
- [Jest Testing](references/jest-testing.md)

## Jest Configuration for SFDX Projects

If your project uses Jest, scope discovery to your Salesforce source so example assets in agent folders are not picked up during `npm test`.

```javascript
const { jestConfig } = require('@salesforce/sfdx-lwc-jest/config');

module.exports = {
    ...jestConfig,
    roots: ['<rootDir>/force-app'],
    testPathIgnorePatterns: [
        '<rootDir>/node_modules/',
        '<rootDir>/.sfdx/',
        '<rootDir>/.agents/',
        '<rootDir>/.cursor/',
        '<rootDir>/.claude/',
        '<rootDir>/.pi/'
    ]
};
```

Example test assets in this skill now ship with a `.example` suffix. Copy them into your project and rename them before running Jest.

## Requirements

- sf CLI v2
- Node.js 18+ (for Jest tests)
- Target Salesforce org
- API Version 66.0+ (Spring '26)

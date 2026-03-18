---
description: React-specific patterns and Salesforce data access for SFDX web apps
paths:
  - "**/webapplications/**/*"
---

# React Web App (SFDX)

For layout, navigation, and generation rules, see **webapp.md**.

## Routing (React Router)

Use a **single** router package for the app. When using `createBrowserRouter` and `RouterProvider` from `react-router`, all routing imports MUST come from **`react-router`** — not from `react-router-dom`.

## Component Library + Styling (MANDATORY)

- Use **shadcn/ui** for UI components: `import { Button } from '@/components/ui/button';`
- Use **Tailwind CSS** utility classes

## Module & Platform Restrictions

React apps must NOT import Salesforce platform modules like `lightning/*` or `@wire` (LWC-only)

## Data Access (CRITICAL)

For all Salesforce data access (GraphQL, REST, Chatter, Connect, Apex REST, UI API, Einstein LLM), invoke the **`accessing-data`** skill (`.a4drules/skills/accessing-data/`). It enforces Data SDK usage, GraphQL-first preference, optional chaining, and documents when to use `sdk.fetch` via the `fetching-rest-api` skill.

### GraphQL (Preferred)

For queries and mutations, invoke the **`using-graphql`** skill (`.a4drules/skills/using-graphql/`). It covers schema exploration, query patterns, codegen, type generation, and guardrails.

### UI API (Fallback)

When GraphQL cannot cover the use case, use `sdk.fetch?.()` for UI API endpoints. See the **`fetching-rest-api`** skill (`.a4drules/skills/fetching-rest-api/`) for full REST API documentation.

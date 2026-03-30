---
name: building-ui-bundle-app
description: "Build complete Salesforce React UI bundle applications from natural language descriptions. Use this skill when a user requests a full React app, UI bundle app, web app on Salesforce, or describes a scenario requiring scaffolding, features, data access, UI pages, and deployment of a React application hosted on Salesforce. Orchestrates all UI bundle skills in proper dependency order to produce a deployable application. Triggers on: build a React app, create a UI bundle, build me an app, full-stack Salesforce React app, create a web app on Salesforce."
metadata:
  version: "1.0"
  related-skills: generating-ui-bundle-metadata, generating-ui-bundle-features, using-ui-bundle-salesforce-data, generating-ui-bundle-ui, implementing-ui-bundle-agentforce-conversation-client, implementing-ui-bundle-file-upload, deploying-ui-bundle, generating-experience-react-site
---

# Building a UI Bundle App

## Overview

Build a complete, deployable Salesforce React UI bundle application from a natural language description by orchestrating specialized UI bundle skills in correct dependency order. Each skill **MUST** be explicitly loaded before executing its phase.

## When to Use This Skill

**Use when:**

- User requests a "React app", "UI bundle", "web app", or "full-stack app" on Salesforce
- User says "build an app", "create an application" and the context implies a React frontend
- The work produces a complete UI bundle with scaffolding, features, data access, and UI — not a single component in isolation

**Examples that should trigger this skill:**

- "Build a React app for managing customer cases with Salesforce data"
- "Create a UI bundle for an employee directory with search and navigation"
- "I need a full-stack React app with authentication, data tables, and file uploads"
- "Build a coffee shop ordering app on Salesforce"

**Do NOT use when:**

- Creating a single page or component (use `generating-ui-bundle-ui`)
- Only installing a feature (use `generating-ui-bundle-features`)
- Only setting up data access (use `using-ui-bundle-salesforce-data`)
- Only deploying an existing app (use `deploying-ui-bundle`)
- Building a Lightning Experience app with custom objects and metadata (use `generating-lightning-app`)
- Troubleshooting or debugging an existing UI bundle

---

## Skill Registry

| Phase | Skill Name | When to Load |
|-------|-----------|--------------|
| 1 — Scaffolding | `generating-ui-bundle-metadata` | **Always** — creates the UI bundle and configures metadata |
| 2 — Features | `generating-ui-bundle-features` | **Always** — installs pre-built features (auth, shadcn, search, navigation) |
| 3 — Data Access | `using-ui-bundle-salesforce-data` | **When app needs Salesforce data** — sets up GraphQL/REST data layer |
| 4 — UI | `generating-ui-bundle-ui` | **Always** — builds pages, components, layout, navigation |
| 5a — Agentforce Chat | `implementing-ui-bundle-agentforce-conversation-client` | **Only if requested** — adds Agentforce chat widget |
| 5b — File Upload | `implementing-ui-bundle-file-upload` | **Only if requested** — adds file upload functionality |
| 6 — Deployment | `deploying-ui-bundle` | **Always** — deploys to Salesforce org |
| 7 — Experience Site | `generating-experience-react-site` | **Only if requested** — creates Digital Experience site infrastructure |

### Usage Rules

**SKILL RULE**: You **MUST** load each skill by invoking it (e.g., via the Skill tool) before executing its phase. Do NOT generate code or configuration for a phase without loading the skill first.

**ORDER RULE**: Execute phases in the numbered order above. Later phases depend on earlier phases completing successfully.

**OPTIONAL PHASE RULE**: Phases marked "only if requested" are skipped unless the user's requirements indicate them. All other phases are mandatory.

---

## Dependency Graph & Build Order

### Phase 1: Scaffolding (Foundation)

```
UI Bundle scaffold (sf ui-bundle generate)
    ↓
Bundle metadata (uibundle-meta.xml, ui-bundle.json)
    ↓
CSP Trusted Sites (if external domains needed)
```

**Skill to load:** `generating-ui-bundle-metadata`

Creates the UI bundle directory structure, meta XML, and optional routing/headers config. All subsequent phases require the scaffold to exist.

### Phase 2: Features (Capabilities)

```
Install dependencies (npm install)
    ↓
Search and install features (auth, shadcn, search, navigation, GraphQL)
    ↓
Integrate example files into target files
```

**Skill to load:** `generating-ui-bundle-features`

Installs pre-built, tested feature packages. Always check for an existing feature before building from scratch. Features provide the foundation that UI components build on top of.

### Phase 3: Data Access (Backend Wiring)

```
Acquire schema (npm run graphql:schema)
    ↓
Look up entity schema (graphql-search.sh)
    ↓
Generate queries/mutations
    ↓
Integrate with React components
```

**Skill to load:** `using-ui-bundle-salesforce-data`

Sets up the data layer using `@salesforce/sdk-data`. GraphQL is preferred for record operations; REST for Connect, Apex, or UI API endpoints.

### Phase 4: UI (Frontend)

```
Layout and navigation (appLayout.tsx)
    ↓
Pages (routed views)
    ↓
Components (widgets, forms, tables)
    ↓
Headers and footers
```

**Skill to load:** `generating-ui-bundle-ui`

Builds the React UI. References the data layer from Phase 3 and the features from Phase 2. Must replace all boilerplate and placeholder content.

### Phase 5: Integrations (Optional)

```
Agentforce chat widget (if requested)
File upload API (if requested)
```

**Skills to load (only if requested):**
- `implementing-ui-bundle-agentforce-conversation-client` — for chat/agent widgets
- `implementing-ui-bundle-file-upload` — for file upload functionality

These are independent and can be executed in parallel if both are needed.

### Phase 6: Deployment

```
Org authentication
    ↓
Build UI bundle (npm run build)
    ↓
Deploy metadata
    ↓
Assign permissions
    ↓
Import data (if data plan exists)
    ↓
Fetch GraphQL schema and run codegen
```

**Skill to load:** `deploying-ui-bundle`

Follows the canonical 7-step deployment sequence. Must deploy metadata before fetching schema.

### Phase 7: Experience Site (Optional)

```
Resolve site properties (siteName, appDevName, etc.)
    ↓
Generate site metadata (Network, CustomSite, DigitalExperience)
    ↓
Deploy site infrastructure
```

**Skill to load (only if requested):** `generating-experience-react-site`

Creates the Digital Experience site that hosts the UI bundle. Only needed when the user wants a public-facing or authenticated site URL.

---

## Execution Workflow

### STEP 1: Requirements Analysis & Planning

**Actions:**

1. Parse the user's natural language request
2. Identify the app name and purpose
3. Extract pages and navigation structure
4. Identify data entities and Salesforce objects needed
5. Detect feature requirements (authentication, search, file upload, chat)
6. Determine if an Experience Site is needed
7. Identify external domains for CSP registration

**Output: Build Plan**

```
UI Bundle App Build Plan: [App Name]

SCAFFOLDING:
- App name: [PascalCase name]
- Routing: [SPA rewrites, trailing slash config]
- External domains: [domains needing CSP registration]

FEATURES:
- [list of features to install: auth, shadcn, search, navigation, etc.]

DATA ACCESS:
- Objects: [Salesforce objects to query/mutate]
- Queries: [list of GraphQL queries needed]
- REST endpoints: [Apex REST or Connect API calls, if any]

UI:
- Layout: [description of app shell/navigation]
- Pages: [list of pages with routes]
- Components: [key components per page]
- Design direction: [aesthetic/style intent]

INTEGRATIONS (if applicable):
- Agentforce chat: [yes/no, agent ID if known]
- File upload: [yes/no, record linking pattern]

DEPLOYMENT:
- Target org: [org alias if known]
- Experience Site: [yes/no, site name if applicable]

SKILL LOAD ORDER:
1. generating-ui-bundle-metadata
2. generating-ui-bundle-features
3. using-ui-bundle-salesforce-data (if data access needed)
4. generating-ui-bundle-ui
5. implementing-ui-bundle-agentforce-conversation-client (if chat requested)
6. implementing-ui-bundle-file-upload (if file upload requested)
7. deploying-ui-bundle
8. generating-experience-react-site (if site requested)
```

### STEP 2: Per-Phase Execution

Execute each phase sequentially. Complete all steps within a phase before moving to the next. For each phase:

| Step | What to do | Why |
|------|-----------|-----|
| **① Load skill** | Invoke the skill (e.g., via the Skill tool) for this phase | Gives you the current rules, patterns, constraints, and implementation guides |
| **② Execute** | Follow the loaded skill's workflow to generate code/config | The skill defines HOW to do the work correctly |
| **③ Verify** | Run lint and build from the UI bundle directory | Catch errors before moving to the next phase |
| **④ Checkpoint** | Confirm phase completion before proceeding | Ensures dependencies are satisfied for the next phase |

**Do NOT skip ① (loading the skill).** Even if you remember the skill's content, skills evolve. Always load the current version.

---

**Phase 1 — Scaffolding**
- ① Load skill: Invoke `generating-ui-bundle-metadata`
- ② Execute: Run `sf ui-bundle generate`, configure meta XML, ui-bundle.json, and CSP trusted sites
- ③ Verify: Confirm directory structure and metadata files exist
- ④ Checkpoint: UI bundle scaffold is ready → proceed to Phase 2

**Phase 2 — Features**
- ① Load skill: Invoke `generating-ui-bundle-features`
- ② Execute: Install dependencies, search and install features, integrate example files
- ③ Verify: Run `npm run build` to confirm features integrate cleanly
- ④ Checkpoint: Features installed → proceed to Phase 3

**Phase 3 — Data Access** (skip if no Salesforce data needed)
- ① Load skill: Invoke `using-ui-bundle-salesforce-data`
- ② Execute: Fetch schema, look up entities, generate queries/mutations, wire into components
- ③ Verify: Run `npx eslint` on files with GraphQL queries
- ④ Checkpoint: Data layer ready → proceed to Phase 4

**Phase 4 — UI**
- ① Load skill: Invoke `generating-ui-bundle-ui`
- ② Execute: Build layout, pages, components, navigation. Replace all boilerplate.
- ③ Verify: Run lint and build — 0 errors required
- ④ Checkpoint: UI complete → proceed to Phase 5

**Phase 5 — Integrations** (skip if not requested)
- ① Load skill(s): Invoke `implementing-ui-bundle-agentforce-conversation-client` and/or `implementing-ui-bundle-file-upload`
- ② Execute: Follow each skill's workflow to add the integration
- ③ Verify: Run lint and build
- ④ Checkpoint: Integrations complete → proceed to Phase 6

**Phase 6 — Deployment**
- ① Load skill: Invoke `deploying-ui-bundle`
- ② Execute: Follow the 7-step deployment sequence (auth, build, deploy, permissions, data, schema, final build)
- ③ Verify: Confirm deployment succeeds and app is accessible
- ④ Checkpoint: App deployed → proceed to Phase 7 if needed

**Phase 7 — Experience Site** (skip if not requested)
- ① Load skill: Invoke `generating-experience-react-site`
- ② Execute: Resolve properties, generate site metadata, deploy
- ③ Verify: Confirm site URL is accessible
- ④ Checkpoint: Site live → build complete

### STEP 3: Final Summary

After all phases complete, present a build summary:

```
UI Bundle App Build Complete: [App Name]

PHASES COMPLETED:
✓ Phase 1: Scaffolding — [app name] UI bundle created
✓ Phase 2: Features — [list of features installed]
✓ Phase 3: Data Access — [list of entities wired up]
✓ Phase 4: UI — [count] pages, [count] components
✓ Phase 5: Integrations — [list or "none"]
✓ Phase 6: Deployment — deployed to [org]
✓ Phase 7: Experience Site — [site URL or "skipped"]

FILES GENERATED:
[list key files and their paths]

NEXT STEPS:
[any manual steps the user should take]
```

---

## Validation

Before presenting the build as complete, verify:

- [ ] **Scaffold exists**: UI bundle directory with valid meta XML and ui-bundle.json
- [ ] **Dependencies installed**: `node_modules/` exists and `package.json` has expected packages
- [ ] **Build passes**: `npm run build` produces `dist/` with no errors
- [ ] **Lint passes**: `npx eslint src/` reports 0 errors
- [ ] **No boilerplate**: All placeholder text, default titles, and template content has been replaced
- [ ] **Navigation works**: `appLayout.tsx` has real nav items matching created pages
- [ ] **Data layer wired**: Components use `@salesforce/sdk-data` (if data access phase was executed)
- [ ] **CSP registered**: All external domains have CSP Trusted Site metadata (if applicable)

---

## Error Handling

### Category 1: Stop and Ask User

- App purpose is too vague to determine pages or data needs
- User wants features that conflict (e.g., "no authentication" + "show user-specific data")
- Target org is unknown and deployment is requested

### Category 2: Log Warning, Continue

- A feature install has minor conflicts (resolve and continue)
- Optional integration setup encounters non-blocking issues
- Build has non-error warnings

---

## Best Practices

### 1. Always Follow Phase Order

Never build UI before installing features. Never deploy before building. Dependencies are strict.

### 2. Always Load Skills

Even for simple apps, load each skill. Skills contain validated patterns that prevent subtle errors.

### 3. Check for Existing Features First

Before building any capability from scratch (auth, search, navigation), search available features. A tested package is better than custom code.

### 4. Replace All Boilerplate

Every generated app must feel purpose-built. Replace "React App" titles, "Vite + React" placeholders, and all default content with real app-specific text and branding.

### 5. Design with Intent

Follow the design thinking and frontend aesthetics guidance from `generating-ui-bundle-ui`. Every app should have a clear visual direction — not generic defaults.

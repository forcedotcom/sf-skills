---
name: experience-ui-bundle-app-coordinate
description: "MUST activate when the user wants to build, create, or generate a React application, React app, web application, single-page application (SPA), or frontend application — even if no project files exist yet. MUST also activate when the project contains a uiBundles/*/src/ directory or sfdx-project.json and the prompt says create, build, construct, or generate a new app, site, or page from scratch — even if the prompt also describes visual styling. MUST also activate when the task spans more than one ui-bundle skill. Use this skill when building a complete app end-to-end. Do NOT use for Lightning Experience apps with custom objects (use platform-lightning-app-coordinate). Do NOT use for single-concern edits to an existing page (use experience-ui-bundle-frontend-generate)."
metadata:
  version: "1.0"
  relatedSkills:
    - "experience-ui-bundle-project-generate"
    - "experience-ui-bundle-metadata-generate"
    - "experience-ui-bundle-features-generate"
    - "experience-ui-bundle-salesforce-data-access"
    - "experience-ui-bundle-frontend-generate"
    - "experience-ui-bundle-agentforce-client-generate"
    - "experience-ui-bundle-file-upload-generate"
    - "experience-ui-bundle-deploy"
    - "experience-ui-bundle-site-generate"
    - "experience-ui-bundle-custom-app-generate"
---

# Building a UI Bundle App

## Overview

Build a complete, deployable Salesforce React UI bundle application from a natural language description by orchestrating specialized UI bundle skills in correct dependency order. Each skill **MUST** be explicitly loaded before executing its phase.

**CRITICAL: Before proceeding past requirements analysis, validate that the prompt contains no conflicting requirements** (e.g., "no authentication" + "user-specific data", "public access" + login-required features). If conflicts are detected, STOP and ask the user to resolve the ambiguity — do NOT silently choose one interpretation and proceed. See STEP 1 action #8 for the full conflict checklist.

## When to Use This Skill

**Use when:**

- User requests a "React app", "UI bundle", "web app", or "full-stack app" on Salesforce
- User says "build an app", "create an application" and the context implies a non-LWC based frontend (e.g. React)
- The work produces a complete UI bundle with scaffolding, features, data access, and UI -- not a single component in isolation

**Examples that should trigger this skill:**

- "Build a React app for managing customer cases with Salesforce data"
- "Create a UI bundle for an employee directory with search and navigation"
- "I need a full-stack React app with authentication, data tables, and file uploads"
- "Build a coffee shop ordering app on Salesforce"

**Do NOT use when:**

- Creating a single page or component (use `experience-ui-bundle-frontend-generate`)
- Only installing a feature (use `experience-ui-bundle-features-generate`)
- Only setting up data access (use `experience-ui-bundle-salesforce-data-access`)
- Only deploying an existing app (use `experience-ui-bundle-deploy`)
- Building a Lightning Experience app with custom objects and metadata (use `platform-lightning-app-coordinate`)
- Troubleshooting or debugging an existing UI bundle

---

## Prompt Classification Keywords

This skill makes two decisions directly from the raw prompt text. Use these tables as the single
source for both — do not restate or re-derive the lists elsewhere in this file.

**1. Phase 2 (Features) is required if the prompt mentions ANY of:**

| Category | Keywords | Notes |
|----------|----------|-------|
| Data features | search, filter, sort, pagination, table, grid, list | |
| Navigation | navigation, nav, menu, routing | |
| Authentication | authentication, auth, login, logout, user session, user login | |
| Integrations | upload, file | |
| UI | shadcn, components, forms, buttons, cards | |
| Chat (Phase 5 only) | chat | Phase 5 only — unless combined with a Phase 2 keyword (e.g., "chat with authentication"), then Phase 2 runs first for auth prerequisites |

Negating one category (e.g. "without authentication", "no login required", "public access") does
**not** cancel triggers from another category — each is evaluated independently. Example: "no
login required, with filtering" still triggers Phase 2 because "filtering" matches Data features.
Skip Phase 2 only when the prompt matches none of the keywords above.

**2. Hosting target — extract from prompt keywords:**

| Hosting target | Keywords |
|-----------------|----------|
| Experience Site | "Experience Site", "Community", "external users", "public users", "guest users" |
| Custom Application | "Custom Application", "internal users", "Lightning app" |

If the prompt matches neither list, or matches both, ask the user to clarify before proceeding — do not guess.

---

## Dependency Graph & Build Order

### Phase 0: Template Offer & Bootstrap (Prerequisites)

```text
Offer prebuilt starter template (experience-ui-bundle-project-generate)
    v
If template chosen: scaffold via sf template generate project -- Phase 1 skipped
    v
If declined: run scripts/check-sfdx-project.sh
    v
If missing: create sfdx-project.json
    v
Verify project directory initialized
```

Offers a faster, less error-prone starting point before building from scratch. If no template is used, ensures an SFDX project exists before attempting to generate a UI bundle — without this, `sf template generate ui-bundle` will fail with a hard error. Always check first — do not assume the project structure exists.

**Action:** Load `experience-ui-bundle-project-generate` and offer the two starter templates. If declined, run `scripts/check-sfdx-project.sh` and report any errors it returns. If the script reports an error, create the missing `sfdx-project.json` before proceeding.

### Phase 1: Scaffolding (Foundation)

```text
Determine hosting target (Experience Site / Custom Application)
    v
UI Bundle scaffold (sf template generate ui-bundle --template reactbasic)
    v
Install dependencies (npm install)
    v
Bundle metadata (uibundle-meta.xml with <target>, ui-bundle.json)
    v
CSP Trusted Sites (if external domains needed)
```

Creates the UI bundle directory structure, meta XML (including hosting target), and optional routing/headers config. **CRITICAL**: Hosting target must be determined FIRST because the metadata skill requires `<target>` in Phase 1. All subsequent phases require the scaffold to exist.

### Phase 2: Features (Required if prompt mentions feature keywords — see "Prompt Classification Keywords" above)

```text
Search project code (src/) for existing implementations
    v
Install dependencies (npm install)
    v
Search, describe, and install features (auth, shadcn, search, navigation, GraphQL)
    v
Resolve conflicts (two-pass: --on-conflict error, then --conflict-resolution)
    v
Integrate __examples__ files into target files (verify build succeeds), then delete them
```

Installs pre-built, tested feature packages. See "Prompt Classification Keywords" above for the full trigger keyword list and negative-phrasing handling — these features provide the foundation that UI components build on top of.

Only skip this phase if the app is truly a minimal "hello world" with no interactive features (no trigger keywords present at all).

### Phase 3: Data Access (Backend Wiring)

```text
Ground every entity/field against the org (per experience-ui-bundle-salesforce-data-access)
    v
Generate queries/mutations FROM the verified names (never from guessed fields)
    v
Generate types (npm run graphql:codegen) and wire into components
    v
Validate and test (npx eslint, ask user before testing mutations)
```

Sets up the data layer using the **`@salesforce/platform-sdk`** Data SDK (`createDataSDK().graphql`).
GraphQL is preferred for record operations; REST for Connect, Apex, or UI API endpoints. **The
`experience-ui-bundle-salesforce-data-access` skill owns the grounding + authoring workflow — load it and follow
it; do not substitute a local-schema grep or guessed field names.** Grounding happens against the
**live org**, so it does not require a local `schema.graphql` to be present.

### Phase 4: UI (Frontend)

```text
Layout, navigation, header, and footer (appLayout.tsx)
    v
Pages (routed views)
    v
Components (widgets, forms, tables)
```

Builds the React UI. References the data layer from Phase 3 and the features from Phase 2. Must replace all boilerplate and placeholder content.

### Phase 5: Integrations (Optional)

```text
Agentforce chat widget (if requested)
File upload API (if requested)
```

These are independent and can be executed in parallel if both are needed.

### Phase 6: Deployment

```text
Org authentication
    v
Pre-deploy UI bundle build (npm install + npm run build)
    v
Deploy metadata
    v
Post-deploy configuration (permissions, profiles, named credentials, connected apps, custom settings, flow activation)
    v
Import data (if data plan exists)
    v
Fetch GraphQL schema and run codegen
*(Re-fetches schema from the deployed org -- required because the remote schema may differ from the local one used in Phase 3. Guard against an empty or stale result -- Salesforce Edge caching can briefly serve the pre-deploy schema; re-fetch/retry before trusting it as empty and before running codegen)*
    v
Final UI bundle build (rebuilds with the deployed schema)
```

Follows the canonical 7-step deployment sequence. Must deploy metadata before fetching schema. Must assign permissions before schema fetch.

### Phase 7: Hosting Target Infrastructure

Deploy the hosting target infrastructure determined in Phase 1. Choose **one** of the following based on the app's audience:

#### Phase 7a: Experience Site (External)

```text
Resolve site properties (siteName, appDevName, etc.)
    v
Generate site metadata (Network, CustomSite, DigitalExperience)
    v
Deploy site infrastructure
```

Creates the Digital Experience site that hosts the UI bundle. Use when the user wants a public-facing or authenticated site URL for external users. **Note**: The `<target>ExperienceSite</target>` was already set in meta XML during Phase 1.

#### Phase 7b: Custom Application (Internal)

```text
Resolve app properties (appName, appNamespace, appLabel)
    v
Generate CustomApplication metadata (applications/*.app-meta.xml)
    v
Deploy custom application
```

Creates a Custom Application entry in the Lightning App Launcher. Use when the app is for internal users accessing it within Lightning Experience. **Note**: The `<target>CustomApplication</target>` was already set in meta XML during Phase 1.

---

## Execution Workflow

### STEP 0: Offer a Prebuilt Template (before scaffolding from scratch)

**Before** analyzing requirements or scaffolding, check whether a prebuilt starter template fits —
it is faster and less error-prone than building from scratch.

- **Load skill: Invoke `experience-ui-bundle-project-generate`.** It offers two minimal React starter
  projects (internal / employee-facing and external / customer-facing) and, if the user picks one,
  generates it into the project directory with `sf template generate project`.
- **If the user chooses a template:** the scaffolding phase (Phase 1) is effectively done. Skip
  straight to populating/customizing the project — continue at the phase that matches what they
  want to change (typically Phase 4 UI, or Phase 3 data access), then Phase 6 deployment.
- **If the user declines** (wants to start from scratch, or none fit): proceed normally to STEP 1.

Do not skip this step silently — always offer the choice at the start of a from-scratch app build.

### STEP 1: Requirements Analysis & Planning

**Actions:**

1. Parse the user's natural language request
2. Identify the app name and purpose
3. Extract pages and navigation structure
4. Identify data entities and Salesforce objects needed
5. Detect feature requirements (authentication, search, file upload, chat)
6. Determine hosting target (Experience Site OR Custom Application) — see "Prompt Classification Keywords" above; if ambiguous, ask user to clarify before proceeding
7. Identify external domains for CSP registration
8. **Check for conflicting requirements** — STOP and ask user if any of the following conflicts are detected:
   - "No authentication" OR "public/guest access" AND "user-specific data" OR "show current user's data" OR "My [Entity]" view
   - "External users" AND "Custom Application" (Custom Apps are internal-only)
   - "Public access" AND features requiring login (file upload, user profile, personalization)

> **The plan MUST contain an explicit grounding step before any query authoring.** Do not list
> guessed object/field names as settled facts and defer verification to codegen. The data-access
> portion of the plan must read: "verify these entities/fields against the org (via
> `experience-ui-bundle-salesforce-data-access`), then author queries from the verified names." A plan that
> authors queries first and codegens later is the failure mode that produces guessed fields and
> hand-stubbed types — do not emit it.

**Before proceeding to Output (Build Plan), validate:**

- [ ] **No conflicting requirements detected** — if conflicts exist (see action #8 above), STOP and report:
  ```text
  ERROR: Conflicting requirements detected:
  - [describe the specific conflict, e.g., "The prompt requires 'no authentication' while also requiring a 'My Cases' view scoped to the current user's identity"]
  
  RESOLUTION NEEDED: Please clarify:
  - [specific question, e.g., "Should the app require login (removing the 'no authentication' requirement), or should all data be public (removing the user-scoped view)?"]
  ```
  **Do NOT proceed to build plan generation or any phase execution until this conflict is resolved.**

**Output: Build Plan**

```text
UI Bundle App Build Plan: [App Name]

SCAFFOLDING:
- App name: [PascalCase name]
- Hosting target: [Experience Site / Custom Application] **REQUIRED**
- Routing: [SPA rewrites, trailing slash config]
- External domains: [domains needing CSP registration]

FEATURES:
- [list of features to install: auth, shadcn, search, navigation, etc.]

DATA ACCESS:
- Objects: [Salesforce objects to query/mutate]
- Grounding: [verify each object + its fields against the org via experience-ui-bundle-salesforce-data-access BEFORE authoring — list the objects/fields to confirm, not assumed-correct names]
- Queries: [GraphQL queries to author FROM the verified names]
- REST endpoints: [only where GraphQL/uiapi genuinely cannot cover it — not as a fallback for fields that were hard to verify]

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

SKILL LOAD ORDER:
0. experience-ui-bundle-project-generate (offer a prebuilt template first; if chosen, Phase 1 scaffolding is skipped; if declined, run the Bootstrap check for an existing SFDX project -- no skill load required)
1. experience-ui-bundle-metadata-generate (determines hosting target FIRST)
2. experience-ui-bundle-features-generate (if features needed)
3. experience-ui-bundle-salesforce-data-access (if data access needed)
4. experience-ui-bundle-frontend-generate
5a. experience-ui-bundle-agentforce-client-generate (if chat requested)
5b. experience-ui-bundle-file-upload-generate (if file upload requested)
6. experience-ui-bundle-deploy
7a. experience-ui-bundle-site-generate (if Experience Site requested -- external users)
7b. experience-ui-bundle-custom-app-generate (if Custom Application requested -- internal users)
```

### STEP 2: Per-Phase Execution

Execute each phase sequentially. Complete all steps within a phase before moving to the next. For each phase:

| Step | What to do | Why |
|------|-----------|-----|
| **1. Load skill** | Invoke the skill (e.g., via the Skill tool) for this phase | Gives you the current rules, patterns, constraints, and implementation guides |
| **2. Execute** | Follow the loaded skill's workflow to generate code/config | The skill defines HOW to do the work correctly |
| **3. Verify** | Run lint and build from the UI bundle directory | Catch errors before moving to the next phase |
| **4. Checkpoint** | Confirm phase completion before proceeding | Ensures dependencies are satisfied for the next phase |

**CRITICAL: Do NOT skip step 1 (loading the skill).** Even if you remember the skill's content, skills evolve. Always load the current version. **Skipping or reordering phases produces broken, non-deployable apps.** Phase dependencies are strict and cannot be violated.

---

**Phase 0 -- Template Offer & Bootstrap** (always, before scaffolding)
- 1. Load skill: Invoke `experience-ui-bundle-project-generate`
- 2. Execute: Offer the two starter templates; if the user picks one, generate it into the project dir with `sf template generate project`
- 3. Decision: If a template was used, the project is scaffolded (including a valid SFDX project structure) — skip Phase 1 and continue at the phase matching the user's customization (usually Phase 4 UI). If declined, proceed to the Bootstrap check below.
- 4. Bootstrap (no skill load required, only if no template was used): Run `scripts/check-sfdx-project.sh` and report any errors it returns. If the script reports an error, create the SFDX project structure (`sf project generate` or manually create sfdx-project.json).
- 5. Checkpoint: SFDX project ready -- proceed to Phase 1

**Phase 1 -- Scaffolding** (skip if a template was generated in Phase 0)
- 1. Load skill: Invoke `experience-ui-bundle-metadata-generate`
- 2. Execute: Determine hosting target (Experience Site / Custom Application) FIRST. Run `sf template generate ui-bundle --template reactbasic`, install dependencies (`npm install`), configure meta XML (with `<target>`), ui-bundle.json, and CSP trusted sites.
- 3. Verify: Confirm directory structure and metadata files exist with hosting target specified
- 4. Checkpoint: UI bundle scaffold is ready -- proceed to Phase 2

**Phase 2 -- Features** (Required if prompt mentions feature keywords — see "Prompt Classification Keywords" above)
- 1. Load skill: Invoke `experience-ui-bundle-features-generate`
- 2. Execute: Install dependencies, search and install features, integrate example files
- 3. Verify: Run `npm run build` to confirm features integrate cleanly
- **Trigger conditions**: See "Prompt Classification Keywords" above for the full keyword list (by category) and how negative phrasing is handled -- negating one category does not cancel triggers from another.

**Phase 3 -- Data Access** (skip if no Salesforce data needed)
- 1. Load skill: Invoke `experience-ui-bundle-salesforce-data-access`
- 2. Execute: Check preconditions (authenticated org, npm dependencies installed). Fetch schema (`npm run graphql:schema`), guard against empty schema. Look up entities, generate queries/mutations, wire into components.
- 3. Verify: Run `npx eslint` on files with GraphQL queries. Verify schema is non-empty.
- 4. Checkpoint: Data layer ready -- proceed to Phase 4

**Phase 4 -- UI** (ALWAYS REQUIRED - CANNOT BE SKIPPED)
- 1. Load skill: Invoke `experience-ui-bundle-frontend-generate`
- 2. Execute: Build layout, pages, components, navigation. Replace all boilerplate.
   - If Phase 2 was skipped: Generate UI components from scratch without feature templates
   - If Phase 3 was skipped: Use mock data or static content for display
   - Phase 4 MUST execute even if prior phases were skipped
- 3. Verify: Run lint and build -- 0 errors required
- 4. Checkpoint: UI complete -- proceed to Phase 5 if integrations needed, or stop here if building only

⚠️ **CRITICAL**: Phase 4 generates the actual React user interface. Skipping it results in a UI bundle with only metadata and no user-facing pages or components. ALWAYS execute Phase 4 for every UI bundle build.

**Phase 5 -- Integrations** (skip if not requested)
- 1. Load skill(s): Invoke `experience-ui-bundle-agentforce-client-generate` (5a) and/or `experience-ui-bundle-file-upload-generate` (5b). If both are needed, they are independent and can be executed in parallel.
- 2. Execute: Follow each skill's workflow to add the integration
- 3. Verify: Run lint and build
- 4. Checkpoint: Integrations complete -- proceed to Phase 6

**Phase 6 -- Deployment**
- 1. Load skill: Invoke `experience-ui-bundle-deploy`
- 2. Execute: Check preconditions (authenticated org, successful build). Follow the 7-step deployment sequence (auth, build, deploy, permissions, data, schema, final build). When available, prefer using a project-level `scripts/org-setup.mjs` automation script over re-deriving the deployment flow each run. Guard the post-deploy schema re-fetch against an empty/stale result (Edge caching) before running final codegen -- retry rather than trusting an empty schema.
- 3. Verify: Confirm deployment succeeds, app is accessible, and the re-fetched schema is non-empty
- 4. Checkpoint: App deployed -- proceed to Phase 7 if hosting target deployment is needed

**Phase 7a -- Experience Site** (skip if not requested or if Custom Application chosen)
- 1. Load skill: Invoke `experience-ui-bundle-site-generate`
- 2. Execute: Resolve properties, generate site metadata, deploy
- 3. Verify: Confirm site URL is accessible (hosting target already verified by `scripts/check-hosting-target.sh` in trigger evaluation)
- 4. Checkpoint: Site live -- build complete
- **Trigger conditions**: Run `scripts/check-hosting-target.sh` and check output for "ExperienceSite" OR prompt matches an Experience Site keyword in "Prompt Classification Keywords" above
- **Note**: The `<target>ExperienceSite</target>` was already set in meta XML during Phase 1 -- do not add it again

**Phase 7b -- Custom Application** (skip if not requested or if Experience Site chosen)
- 1. Load skill: Invoke `experience-ui-bundle-custom-app-generate`
- 2. Execute: Resolve app properties, generate CustomApplication metadata
- 3. Verify: Confirm app appears in App Launcher (hosting target already verified by `scripts/check-hosting-target.sh` in trigger evaluation)
- 4. Checkpoint: App registered -- build complete
- **Trigger conditions**: Run `scripts/check-hosting-target.sh` and check output for "CustomApplication" OR prompt matches a Custom Application keyword in "Prompt Classification Keywords" above
- **Note**: The `<target>CustomApplication</target>` was already set in meta XML during Phase 1 -- do not add it again

### STEP 2.5: Phase Completion Validation

Before proceeding to STEP 3 (Final Summary), validate that all required phases were executed:

**Critical Validation (MUST pass):**
- [ ] **Phase 0 (Template Offer & Bootstrap) executed**: If no template was used, run `scripts/check-sfdx-project.sh`. If it returns non-zero, STOP and report error:
  ```text
  ERROR: No SFDX project detected. Phase 0 (Bootstrap) is REQUIRED before scaffolding.
  Run `sf project generate` (or create sfdx-project.json) before invoking
  `sf template generate ui-bundle`.
  ```
  If a template was used in Phase 0, this check is satisfied by the template's own scaffolding — skip re-running the script.

- [ ] **Phase 1 hosting target resolved**: Run `scripts/check-hosting-target.sh`. If it returns non-zero, STOP and report error:
  ```text
  ERROR: Hosting target was not resolved in Phase 1. A UI bundle without a <target> in its
  meta XML will not be visible in the org. Determine Experience Site vs Custom Application
  (see "Prompt Classification Keywords" above; ask the user if ambiguous) before proceeding
  past Phase 1 -- do not defer this to Phase 7 and do not record "none"/"skipped".
  ```

- [ ] **Phase 4 (Frontend) executed**: If Phase 4 was NOT executed, STOP and report error:
  ```text
  ERROR: Phase 4 (UI/Frontend generation) is REQUIRED for all UI bundle apps.
  Cannot complete build without generating the React user interface.
  Please review the phase execution logic and ensure Phase 4 is always executed.
  ```

- [ ] **Phase 7 hosting infrastructure deployed**: If neither Phase 7a nor Phase 7b was executed, STOP and report error:
  ```text
  ERROR: Hosting target infrastructure (Phase 7a Experience Site or Phase 7b Custom
  Application) was not deployed. The app was built but is not reachable by any user.
  Exactly one of Phase 7a/7b must run -- it is never optional or "skipped".
  ```

**Warning Validation (log warnings, but can proceed):**
- [ ] **Phase 2 execution**: If Phase 2 was skipped but the prompt matches any keyword in "Prompt Classification Keywords" above (data features, navigation, authentication, integrations, or UI category):
  ```text
  WARNING: Phase 2 (Features) was skipped but prompt contains feature keywords.
  This may indicate a trigger detection failure. Generated UI may be missing
  required feature functionality. Consider re-running with Phase 2 included.
  ```

- [ ] **Phase 3 execution**: If Phase 3 was skipped but prompt mentions Salesforce objects, "GraphQL", "data", or "query":
  ```text
  WARNING: Phase 3 (Data Access) was skipped but prompt mentions Salesforce data.
  Generated UI may not connect to backend correctly. Verify data access is working.
  ```

**Proceed to STEP 3 only if all Critical Validation checks pass (Phase 0, hosting target, Phase 4, Phase 7).**

### STEP 3: Final Summary

After all phases complete, present a build summary:

```text
UI Bundle App Build Complete: [App Name]

PHASES COMPLETED:
[x] Phase 0: Template Offer & Bootstrap -- [template used: <name> / declined; SFDX project verified/created]
[x] Phase 1: Scaffolding -- [app name] UI bundle created with hosting target [Experience Site / Custom Application]
[x] Phase 2: Features -- [list of features installed, or "skipped"]
[x] Phase 3: Data Access -- [list of entities wired up]
[x] Phase 4: UI -- [count] pages, [count] components
[x] Phase 5: Integrations -- [list or "none"]
[x] Phase 6: Deployment -- deployed to [org]
[x] Phase 7: Hosting Target -- [Experience Site URL / Custom Application name] **(never "skipped" -- Phase 1 requires a target, so exactly one of 7a/7b always runs)**

FILES GENERATED:
[list key files and their paths]

NEXT STEPS:
[any manual steps the user should take]
```

---

## Validation

Before presenting the build as complete, verify:

- [ ] **Scaffold exists**: UI bundle directory with valid meta XML and ui-bundle.json
- [ ] **Hosting target resolved and deployed**: Meta XML contains `<target>ExperienceSite</target>` or `<target>CustomApplication</target>` (never left unset), and the matching Phase 7a or 7b infrastructure was generated and deployed -- not skipped
- [ ] **Dependencies installed**: `node_modules/` exists and `package.json` has expected packages
- [ ] **Build passes**: `npm run build` produces `dist/` with no errors
- [ ] **Dist content exists**: `dist/` contains index.html, JS/CSS bundles, and assets (not just an empty directory)
- [ ] **Lint passes**: `npx eslint src/` reports 0 errors
- [ ] **No boilerplate**: All placeholder text, default titles, and template content has been replaced
- [ ] **Navigation works**: `appLayout.tsx` has real nav items matching created pages
- [ ] **Data layer wired**: Components use the `@salesforce/platform-sdk` Data SDK (`createDataSDK().graphql`), with all entities/fields grounded against the org — not guessed (if data access phase was executed)
- [ ] **CSP registered**: All external domains have CSP Trusted Site metadata (if applicable)

---

## Error Handling

### Category 1: Stop and Ask User

- App purpose is too vague to determine pages or data needs
- User wants features that conflict (e.g., "no authentication" + "show user-specific data")
- Hosting target cannot be determined (ask: "Is this for internal users (Custom Application) or external users (Experience Site)?")
- Target org is unknown and deployment is requested

### Category 2: Log Warning, Continue

- A feature install has minor conflicts (resolve and continue)
- Optional integration setup encounters non-blocking issues
- Build has non-error warnings

---

## Best Practices

### 1. Always Follow Phase Order

Never build UI before installing features. Never deploy before building. Dependencies are strict.

### 2. Replace All Boilerplate

Every generated app must feel purpose-built. Replace "React App" titles, "Vite + React" placeholders, and all default content with real app-specific text and branding.

### 3. Design with Intent

Follow the design thinking and frontend aesthetics guidance from `experience-ui-bundle-frontend-generate`. Every app should have a clear visual direction -- not generic defaults.

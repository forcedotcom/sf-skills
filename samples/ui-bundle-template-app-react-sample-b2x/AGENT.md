# Agent guide: Salesforce UI Bundle development

This project is a **Salesforce DX (SFDX) project** containing a **React UI Bundle**. The UI Bundle is a standalone Vite + React SPA that runs inside the Salesforce platform. Use this file when working in this project.

## Resolving paths

Read `sfdx-project.json` at the project root. Take the first `packageDirectories[].path` value and append `/main/default` to get `<sfdx-source>`. The UI Bundle directory is:

```
<sfdx-source>/uiBundles/<appName>/
```

Replace `<appName>` with the actual folder name found under `uiBundles/`. The source path is **not** always `force-app` — always resolve it from `sfdx-project.json`.

## Project layout

```
<project-root>/
├── sfdx-project.json
├── package.json                         # SFDX root scripts 
├── scripts/
│   ├── org-setup.mjs                    # One-time org setup (deploy, schema, build)
│   └── graphql-search.sh               # Schema entity lookup
├── config/
│   └── project-scratch-def.json
│
└── <sfdx-source>/
    ├── uiBundles/
    │   └── <appName>/                   # ← React UI Bundle (primary workspace)
    │       ├── <appName>.uibundle-meta.xml
    │       ├── ui-bundle.json
    │       ├── index.html
    │       ├── package.json
    │       ├── vite.config.ts / tsconfig.json
    │       ├── vitest.config.ts / playwright.config.ts
    │       ├── codegen.yml / .graphqlrc.yml
    │       └── src/                     # All application code lives here
    │
    ├── classes/                          # Apex classes (optional)
    ├── objects/                          # Custom objects and fields (optional)
    ├── permissionsets/                   # Permission sets (optional)
    ├── cspTrustedSites/                 # CSP trusted site definitions (optional)
    ├── layouts/                          # Object layouts (optional)
    ├── triggers/                         # Apex triggers (optional)
    └── data/                            # Sample data for import (optional)
```

## UI Bundle source structure

All application code lives inside the UI Bundle's `src/` directory:

```
src/
├── app.tsx                  # Entry point — creates the browser router
├── appLayout.tsx            # Shell layout (header, navigation, Outlet, footer)
├── routes.tsx               # Single route registry for the entire app
├── navigationMenu.tsx       # Navigation component
├── router-utils.tsx         # Router helpers
├── lib/utils.ts             # Utility functions (cn, etc.)
├── styles/global.css        # Tailwind global styles
├── api/                     # GraphQL operations, clients, data services
├── assets/                  # Static SVGs, images
├── components/
│   ├── ui/                  # Shared primitives (shadcn-style: button, card, input, etc.)
│   ├── layout/              # Layout components (header, footer, sidebar)
│   └── <feature>/           # Feature-specific components
├── features/                # Feature modules (auth, search, etc.)
├── hooks/                   # Custom React hooks
├── pages/                   # Page components (one per route)
├── public/                  # Static assets served as-is
└── utils/                   # Shared utilities
```

### Key files

| File | Role |
|------|------|
| `app.tsx` | Creates `BrowserRouter`; do not add UI here |
| `appLayout.tsx` | Source of truth for navigation, header, footer, and page shell |
| `routes.tsx` | Single route registry; all pages are children of the layout route |
| `<appName>.uibundle-meta.xml` | Salesforce deploy descriptor (`masterLabel`, `version`, `isActive`) |
| `ui-bundle.json` | Runtime config (`outputDir`, routing) |

## Two package.json contexts

### 1. Project root

Used for SFDX metadata tooling. Scripts here target LWC/Aura, not the React app.

| Command | Purpose |
|---------|---------|
| `npm run test` | LWC Jest (passWithNoTests) |
| `npm run prettier` | Format metadata files |
| `npm run prettier:verify` | Check Prettier |

**One-time org setup:** `node scripts/org-setup.mjs --target-org <alias>` runs login, deploy, permset assignment, data import, GraphQL schema/codegen, UI Bundle build, and optionally the dev server. Use `--help` for all flags.

### 2. UI Bundle directory (primary workspace)

**ALL dev, build, lint, and test commands MUST be run from inside the UI Bundle directory (`<sfdx-source>/uiBundles/<appName>/`). Never run them from the project root.**

Resolve the correct path from `sfdx-project.json` before running any command. Do not hardcode the path.

| Command | Purpose |
|---------|---------|
| `npm run dev` | Start Vite dev server |
| `npm run build` | TypeScript check + Vite production build |
| `npm run lint` | ESLint for the React app |
| `npm run test` | Vitest unit tests |
| `npm run preview` | Preview production build |
| `npm run graphql:codegen` | Generate GraphQL types from schema |
| `npm run graphql:schema` | Fetch GraphQL schema from org |

**After every task, without exception:**
1. Run `npm run build` from the UI Bundle directory — must pass with zero errors.
2. Run `npm run lint` from the UI Bundle directory — must pass with zero errors.
3. Run `npm run dev` to start the dev server so the user can verify the result.

Do not consider a task complete until all three steps have been run successfully.
## Development conventions

### UI

- **Component library:** shadcn/ui primitives in `src/components/ui/`. Always use these over raw HTML equivalents. **Before importing any component, verify both the file exists in `src/components/ui/` AND the named export exists within that file.** Never assume a component or export is available — read the file to confirm the exact exports before importing.
- **Styling:** Tailwind CSS only. No inline `style={{}}`. Use `cn()` from `@/lib/utils` for conditional classes.
- **Icons:** Lucide React.
- **Path alias:** `@/*` maps to `src/*`. Use it for all imports.
- **TypeScript:** No `any`. Use proper types, generics, or `unknown`.
- **Components:** Accept `className?: string` prop. Extract shared state to custom hooks in `src/hooks/`.
- **React apps must not** import Salesforce platform modules (`lightning/*`, `@wire`, LWC APIs).

### Routing

- React Router with `createBrowserRouter`. Route definitions live exclusively in `routes.tsx`.
- All page routes are children of the layout route (which renders `appLayout.tsx`).
- Default-export one component per page file.
- The catch-all `path: '*'` route must always be last.
- Navigation uses absolute paths (`/dashboard`). Non-router imports use dot-relative paths (`./utils`).
- Navigation visibility is driven by `handle.showInNavigation` on route definitions.

### Layout and navigation

- `appLayout.tsx` owns the header, navigation menu, footer, and `<Outlet />`.
- To modify header or footer, edit `appLayout.tsx` and create components in `src/components/layout/`.
- To add a page, add a route in `routes.tsx` and create the page component — do not modify `appLayout.tsx` or `app.tsx` for page additions.

### Data access (Salesforce)

**Before writing any code that connects to Salesforce, you MUST invoke the `using-ui-bundle-salesforce-data` skill. Do not write any data access code without consulting it first.**

This applies to: GraphQL queries/mutations, REST calls, SDK initialization, custom hooks that fetch data, or any code that imports from `@salesforce/sdk-data`.

- **All data access uses the Data SDK** (`@salesforce/sdk-data`) via `createDataSDK()`.
- **Never** use `fetch()` or `axios` directly for Salesforce data.
- **GraphQL is preferred** for record operations (`sdk.graphql`). Use `sdk.fetch` only when GraphQL cannot cover the case (UI API REST, Apex REST, Connect REST, Einstein LLM).
- Use optional chaining: `sdk.graphql?.()`, `sdk.fetch?.()`.
- Apply the `@optional` directive to all record fields for field-level security resilience.
- Verify field and object names via `scripts/graphql-search.sh` before writing queries.
- Use `__SF_API_VERSION__` global for API version in REST calls.
- **Blocked APIs:** Enterprise REST query endpoint (`/query` with SOQL), `@AuraEnabled` Apex, Chatter API.

#### Permitted APIs

| API | Method | Endpoints / Use Case |
|-----|--------|----------------------|
| GraphQL | `sdk.graphql` | All record queries and mutations via `uiapi { }` namespace |
| UI API REST | `sdk.fetch` | `/services/data/v{ver}/ui-api/records/{id}` |
| Apex REST | `sdk.fetch` | `/services/apexrest/{resource}` |
| Connect REST | `sdk.fetch` | `/services/data/v{ver}/connect/...` |
| Einstein LLM | `sdk.fetch` | `/services/data/v{ver}/einstein/llm/prompt/generations` |

Any endpoint not listed above is not permitted.

#### GraphQL non-negotiable rules

1. **Schema is the single source of truth** — every entity and field name must be confirmed via the schema search script before use. Never guess.
2. **`@optional` on all record fields** — FLS causes entire queries to fail if any field is inaccessible. Apply to every scalar, parent, and child relationship field.
3. **Correct mutation syntax** — mutations wrap under `uiapi(input: { allOrNone: true/false })`, not bare `uiapi { ... }`.
4. **Explicit `first:` in every query** — omitting it silently defaults to 10 records. Always include `pageInfo { hasNextPage endCursor }` for paginated queries.
5. **SOQL-derived execution limits** — max 10 subqueries per request, max 5 levels of child-to-parent traversal, max 1 level parent-to-child, max 2,000 records per subquery.
6. **HTTP 200 does not mean success** — Salesforce returns HTTP 200 even on failure. Always check the `errors` array in the response body.

#### GraphQL inline queries
Must use the `gql` template tag from `@salesforce/sdk-data` — plain template strings bypass `@graphql-eslint` schema validation. For complex queries, use external `.graphql` files with codegen.

#### Current user info
Use GraphQL (`uiapi { currentUser { Id Name { value } } }`), not Chatter (`/chatter/users/me`).

#### Schema file (`schema.graphql`)

The `schema.graphql` file at the SFDX project root is the source of truth for all entity and field name lookups. It is 265K+ lines — never open or parse it directly. Use the schema search script instead.

- **Generate/refresh:** Run `npm run graphql:schema` from the UI bundle directory
- **When to regenerate:** After any metadata deployment that changes objects, fields, or permission sets
- **Custom objects** only appear in the schema after metadata deployment AND permission set assignment
- **After regenerating:** Always re-run `npm run graphql:codegen` and `npm run build` (schema changes may affect generated types)

### CSP trusted sites

Any external domain the app calls (APIs, CDNs, fonts) must have a `.cspTrustedSite-meta.xml` file under `<sfdx-source>/cspTrustedSites/`. Unregistered domains are blocked at runtime. Each subdomain needs its own entry. URLs must be HTTPS with no trailing slash, no path, and no wildcards.

## Building and launching the app

All build, dev, and test commands run from the UI Bundle directory. Before running any command, read the UI Bundle's `package.json` to confirm available scripts — do not assume script names.

Typical scripts found in the UI Bundle:

| Command | Purpose |
|---------|---------|
| `npm run build` | TypeScript check + Vite production build |
| `npm run dev` | Start Vite dev server |
| `npm run lint` | ESLint |
| `npm run test` | Vitest unit tests |
| `npm run graphql:codegen` | Generate GraphQL types |
| `npm run graphql:schema` | Fetch GraphQL schema from org |

If dependencies have not been installed yet, run `npm install` in the UI Bundle directory first. Alternatively, run `npm run sf-project-setup` from the project root — it resolves the UI Bundle directory automatically and runs install, build, and dev in sequence.

**After any JavaScript or TypeScript change, run `npm run build` to validate the change.** If the build fails, read the error output, identify the cause, fix it, and run `npm run build` again. Do not move on until the build passes.

## Deploying

**Deployment order matters.** Metadata (objects, permission sets) must be deployed before fetching the GraphQL schema. After any metadata deployment that changes objects, fields, or permissions, re-run schema fetch and codegen.

**Deployment steps:**

1. Authenticate to the target org
2. Build the UI Bundle (`npm run build` in the UI Bundle directory)
3. Deploy metadata (`sf project deploy start --source-dir <packageDir> --target-org <alias>`)

```bash
# Deploy UI Bundle only
sf project deploy start --source-dir <sfdx-source>/ui-bundles --target-org <alias>

# Deploy all metadata
sf project deploy start --source-dir <packageDir> --target-org <alias>
```

**Do not open the app after deployment.** Do not run `sf org open`, do not guess the runtime URL, and do not construct paths like `/s/<appName>`. Deployment is complete when the `sf project deploy start` command succeeds.

## Post-deployment org setup

These steps apply after a fresh deployment to configure the org. They are not part of routine deployment.

1. Assign permission sets
2. Import data (only with user confirmation)
3. Fetch GraphQL schema + run codegen (`npm run graphql:schema && npm run graphql:codegen`)
4. Rebuild the UI Bundle (`npm run build` — schema changes may affect generated types)

## Skills

Before starting any task, check whether a relevant skill exists. If one does, invoke it before writing any code or making any implementation decision. Skills are the authoritative source for patterns, constraints, and code examples.

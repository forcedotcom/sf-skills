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
│   ├── setup-cli.mjs                    # One-command setup (deploy, schema, build)
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

## Web application source structure

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

**One-command setup:** `node scripts/setup-cli.mjs --target-org <alias>` runs login, deploy, permset assignment, data import, GraphQL schema/codegen, UI Bundle build, and optionally the dev server. Use `--help` for all flags.

### 2. Web app directory (primary workspace)

**Always `cd` into the UI Bundle directory for dev/build/lint/test:**

| Command | Purpose |
|---------|---------|
| `npm run dev` | Start Vite dev server |
| `npm run build` | TypeScript check + Vite production build |
| `npm run lint` | ESLint for the React app |
| `npm run test` | Vitest unit tests |
| `npm run preview` | Preview production build |
| `npm run graphql:codegen` | Generate GraphQL types from schema |
| `npm run graphql:schema` | Fetch GraphQL schema from org |

**Before completing any change:** run `npm run build` and `npm run lint` from the UI Bundle directory. Both must pass with zero errors.

## Development conventions

### UI

- **Component library:** shadcn/ui primitives in `src/components/ui/`. Always use these over raw HTML equivalents.
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

- **All data access uses the Data SDK** (`@salesforce/sdk-data`) via `createDataSDK()`.
- **Never** use `fetch()` or `axios` directly for Salesforce data.
- **GraphQL is preferred** for record operations (`sdk.graphql`). Use `sdk.fetch` only when GraphQL cannot cover the case (UI API REST, Apex REST, Connect REST, Einstein LLM).
- Use optional chaining: `sdk.graphql?.()`, `sdk.fetch?.()`.
- Apply the `@optional` directive to all record fields for field-level security resilience.
- Verify field and object names via `scripts/graphql-search.sh` before writing queries.
- Use `__SF_API_VERSION__` global for API version in REST calls.
- **Blocked APIs:** Enterprise REST query endpoint (`/query` with SOQL), `@AuraEnabled` Apex, Chatter API.

### CSP trusted sites

Any external domain the app calls (APIs, CDNs, fonts) must have a `.cspTrustedSite-meta.xml` file under `<sfdx-source>/cspTrustedSites/`. Unregistered domains are blocked at runtime. Each subdomain needs its own entry. URLs must be HTTPS with no trailing slash, no path, and no wildcards.

## Deploying

**Deployment order matters.** Metadata (objects, permission sets) must be deployed before fetching the GraphQL schema. After any metadata deployment that changes objects, fields, or permissions, re-run schema fetch and codegen.

**Recommended sequence:**

1. Authenticate to the target org
2. Build the UI Bundle (`npm run build` in the UI Bundle directory)
3. Deploy metadata (`sf project deploy start --source-dir <packageDir> --target-org <alias>`)
4. Assign permission sets
5. Import data (only with user confirmation)
6. Fetch GraphQL schema + run codegen (`npm run graphql:schema && npm run graphql:codegen`)
7. Rebuild the UI Bundle (schema changes may affect generated types)

**Or use the one-command setup:** `node scripts/setup-cli.mjs --target-org <alias>`

```bash
# Deploy UI Bundle only
sf project deploy start --source-dir <sfdx-source>/ui-bundles --target-org <alias>

# Deploy all metadata
sf project deploy start --source-dir <packageDir> --target-org <alias>
```

## Skills

Check for available skills before implementing any of the following:

| Area | When to consult |
|------|----------------|
| UI generation | Building pages, components, modifying header/footer/layout |
| Salesforce data access | Reading/writing records, GraphQL queries, REST calls |
| Metadata and deployment | Scaffolding apps, configuring CSP, deployment sequencing |
| Feature installation | Before building something from scratch — check if a pre-built feature exists |
| File upload | Adding file upload with Salesforce ContentVersion |
| Agentforce conversation | Adding or modifying the Agentforce chat widget |

Skills are the authoritative source for detailed patterns, constraints, and code examples in each area. This file provides project-level orientation; skills provide implementation depth.

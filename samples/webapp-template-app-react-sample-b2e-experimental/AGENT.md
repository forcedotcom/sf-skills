# Agent guide: SFDX project with React web app

This project is a **Salesforce DX (SFDX) project** containing a **React web application**. The SFDX source path is defined in `sfdx-project.json` (`packageDirectories[].path`); the web app lives under `<sfdx-source>/webapplications/<appName>/`. Use this file when working in this directory.

## SFDX Source Path

The source path prefix is **not** always `force-app`. Read `sfdx-project.json` at the project root, take the first `packageDirectories[].path` value, and append `/main/default` to get `<sfdx-source>`. All paths below use this placeholder.

## Project layout

- **Project root**: this directory — SFDX project root. Contains `sfdx-project.json`, the SFDX source directory, and (optionally) LWC/Aura.
- **React web app**: `<sfdx-source>/webapplications/<appName>/`  
  - Replace `<appName>` with the actual app folder name (e.g. `base-react-app`, or the name chosen when the app was generated).
  - Entry: `src/App.tsx`  
  - Routes: `src/routes.tsx`  
  - API/GraphQL: `src/api/` (e.g. `graphql.ts`, `graphql-operations-types.ts`, `utils/`)

Path convention: **webapplications** (lowercase).

## Two package.json contexts

### 1. Project root (this directory)

Used for SFDX metadata (LWC, Aura, etc.). Scripts here are for the base SFDX template:

| Command | Purpose |
|---------|---------|
| `npm run lint` | ESLint for `aura/` and `lwc/` |
| `npm run test` | LWC Jest (passWithNoTests) |
| `npm run prettier` | Format supported metadata files |
| `npm run prettier:verify` | Check Prettier |

**One-command setup:** From project root run `node scripts/setup-cli.mjs --target-org <alias>` to run login (if needed), deploy, optional permset/data import, GraphQL schema/codegen, web app build, and optionally the dev server. Use `node scripts/setup-cli.mjs --help` for options (e.g. `--skip-login`, `--skip-data`, `--webapp-name`).

Root **does not** run the React app. The root `npm run build` is a no-op for the base SFDX project.

### 2. React web app (where you do most work)

**Always `cd` into the web app directory for dev/build/lint/test:**

```bash
cd <sfdx-source>/webapplications/<appName>
```

| Command | Purpose |
|---------|---------|
| `npm run dev` | Start Vite dev server |
| `npm run build` | TypeScript (`tsc -b`) + Vite build |
| `npm run lint` | ESLint for the React app |
| `npm run test` | Vitest |
| `npm run preview` | Preview production build |
| `npm run graphql:codegen` | Generate GraphQL types |
| `npm run graphql:schema` | Fetch GraphQL schema |

**Before finishing changes:** run `npm run build` and `npm run lint` from the web app directory; both must succeed.

## Agent rules (.a4drules/)

Markdown rules at the project root under **.a4drules/** define platform constraints:

- **`.a4drules/webapp-ui.md`** — Salesforce Web Application UI (scaffold with `sf webapp generate`, no LWC/Aura for new UI).
- **`.a4drules/webapp-data.md`** — Salesforce data access (Data SDK only, supported APIs, GraphQL workflow, `scripts/graphql-search.sh` for schema lookup).

When rules refer to "web app directory" or `<sfdx-source>/webapplications/<appName>/`, resolve `<sfdx-source>` from `sfdx-project.json` and use the **actual app folder name** for this project.

## Deploying

**Deployment order:** Metadata (objects, permission sets) must be deployed before GraphQL schema fetch. After any metadata deployment, re-run `npm run graphql:schema` and `npm run graphql:codegen` from the webapp dir. **One-command setup:** `node scripts/setup-cli.mjs --target-org <alias>` runs deploy → permset → schema → codegen in the correct order.

From **this project root** (resolve the actual SFDX source path from `sfdx-project.json`):

```bash
# Build the React app first (replace <sfdx-source> and <appName> with actual values)
cd <sfdx-source>/webapplications/<appName> && npm i && npm run build && cd -

# Deploy web app only (replace <sfdx-source> with actual path, e.g. force-app/main/default)
sf project deploy start --source-dir <sfdx-source>/webapplications --target-org <alias>

# Deploy all metadata (use the top-level package directory, e.g. force-app)
sf project deploy start --source-dir <packageDir> --target-org <alias>
```

## Conventions (quick reference)

- **UI**: shadcn/ui + Tailwind. Import from `@/components/ui/...`.
- **Entry**: Keep `App.tsx` and routes in `src/`; add features as new routes or sections, don't replace the app shell but you may modify it to match the requested design.
- **Data (Salesforce)**: Follow `.a4drules/webapp-data.md` for all Salesforce data access. Use the Data SDK (`createDataSDK()` + `sdk.graphql` or `sdk.fetch`) — never use `fetch` or `axios` directly. GraphQL is preferred; use `sdk.fetch` when GraphQL is not sufficient.

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

## Agent skills (.a4drules/skills/)

This project includes **.a4drules/skills/** at the project root. Follow them when generating or editing code.

- **Creating Webapp** (`.a4drules/skills/creating-webapp/`): First steps, skills-first protocol, React/TypeScript constraints, deployment order, navigation, aesthetics, and code quality.
- **Building React Components** (`.a4drules/skills/building-react-components/`): Component/page/header-footer workflow, TypeScript standards, and mandatory lint+build verification.
- **Accessing Data** (`.a4drules/skills/accessing-data/`): Use for all Salesforce data fetches. Enforces Data SDK usage (`createDataSDK()` + `sdk.graphql` or `sdk.fetch`); GraphQL preferred, fetch when GraphQL is not sufficient.
- **Fetching REST API** (`.a4drules/skills/fetching-rest-api/`): Use when implementing Chatter, Connect REST, Apex REST, UI API REST, or Einstein LLM calls via `sdk.fetch`.
- **Using GraphQL** (`.a4drules/skills/using-graphql/`): Use when implementing Salesforce GraphQL queries or mutations. Sub-skills: `exploring-graphql-schema`, `generating-graphql-read-query`, `generating-graphql-mutation-query`.
- **Deploying to Salesforce** (`.a4drules/skills/deploying-to-salesforce/`): Use when deploying metadata, fetching GraphQL schema, or generating deploy/setup commands. Enforces deploy → permset → schema → codegen order; schema refetch after metadata deployment.

When rules refer to "web app directory" or `<sfdx-source>/webapplications/<appName>/`, resolve `<sfdx-source>` from `sfdx-project.json` and use the **actual app folder name** for this project.

## Deploying

**Deployment order:** Metadata (objects, permission sets) must be deployed before GraphQL schema fetch. After any metadata deployment, re-run `npm run graphql:schema` and `npm run graphql:codegen` from the webapp dir. **One-command setup:** `node scripts/setup-cli.mjs --target-org <alias>` runs deploy → permset → schema → codegen in the correct order. Invoke the `deploying-to-salesforce` skill for full guidance.

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
- **Data (Salesforce)**: Invoke the `accessing-data` skill for all Salesforce data fetches. The skill enforces use of the Data SDK (`createDataSDK()` + `sdk.graphql` or `sdk.fetch`) — never use `fetch` or `axios` directly. GraphQL is preferred; use `sdk.fetch` when GraphQL is not sufficient (e.g., Chatter, Connect REST). For GraphQL implementation, invoke the `using-graphql` skill.

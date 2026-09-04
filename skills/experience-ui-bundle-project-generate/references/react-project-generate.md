# React UI Bundle Starter Templates

Reference for the **React** path of `experience-ui-bundle-project-generate`. Pick the `--template` flag that fits the user's audience, then return to Step 2 of `SKILL.md`.

## Template options

| Template | `--template` flag | Best for |
|----------|-------------------|----------|
| Internal starter | `reactinternalapp` | Starter for internal, employee-facing Salesforce apps (e.g. support consoles, ops dashboards, internal admin apps) — users are already-authenticated employees. Includes agent chat container. No login flow or public access. |
| External starter | `reactexternalapp` | Starter for customer/partner-facing Salesforce apps/sites (e.g. portals, communities, storefront, public sites). Includes agent chat container. Full auth support (login, registration, reset, profile) — external users sign in with their own accounts. |

## What the bundle contains

The generated UI bundle under `force-app/main/default/uiBundles/$NAME/` is a **React/Vite** app:

- React + Vite toolchain, TypeScript, `vite.config.ts`.
- shadcn/ui primitives (`src/components/ui/`), Tailwind.
- `.tsx` pages/components; app entry `src/App.tsx`, pages under `src/pages/`.
- GraphQL client (`src/api/graphqlClient.ts`) + codegen (`codegen.yml`), `useAsyncData` data util.
- `ui-bundle.json`, `*.uibundle-meta.xml`, project config, `README.md`.
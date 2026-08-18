# Angular UI Bundle Starter Templates

Reference for the **Angular** path of `experience-ui-bundle-project-generate`. Pick the `--template` flag that fits the user's audience, then return to Step 2 of `SKILL.md`.

## Template options

| Template | `--template` flag | Best for |
|----------|-------------------|----------|
| Internal starter | `angularinternalapp` | Starter for internal, employee-facing Salesforce apps (e.g. support consoles, ops dashboards, internal admin apps) — users are already-authenticated employees. Includes agent chat container. No login flow or public access. |
| External starter | `angularexternalapp` | Starter for customer/partner-facing Salesforce apps/sites (e.g. portals, communities, storefront, public sites). Includes agent chat container. Full auth support (login, registration, reset, profile) — external users sign in with their own accounts. |

## What the bundle contains

The generated UI bundle under `force-app/main/default/uiBundles/$NAME/` is an **Angular** app (Angular 21.2.x):

- **Build:** Angular CLI driven by `angular.json` with the `@angular/build:application` builder (esbuild-based). Salesforce platform integration is wired through the `@salesforce/angular-plugin-ui-bundle` esbuild plugin (via `@angular-builders/custom-esbuild`) — registered in `angular.json` `plugins[]` / `middlewares[]`, which handle API-version substitution, the org proxy, and Live Preview / `SFDC_ENV` / base-href injection.
- **Components:** standalone components + signals + native control flow (`@if`/`@for`); each component is a `.component.ts` + `.component.html` pair (`templateUrl`).
- **App wiring:** entry `src/main.ts`; `src/app/app.component.ts` + `.html`; `src/app/app.config.ts` (`APP_BASE_HREF` + `SFDC_ENV.basePath`); `src/app/app.routes.ts`. Pages under `src/pages/` (e.g. `home/`, `not-found/`) as component/template pairs.
- **UI library:** 16 shared primitives + layout on **Angular Material M3** (`mat.theme()`) + **CDK 21.2.x**, styled with **shadcn design tokens** (remap the `--mat-sys-*` variables) and **Tailwind 4.0**.
- **Data layer:** injectable GraphQL client `src/api/graphql-client.service.ts`. GraphQL type codegen is optional and manual (not chained to the build).
- **Metadata & config:** `ui-bundle.json`, `*.uibundle-meta.xml`, `tsconfig.*`, `eslint.config.js`, `README.md`.

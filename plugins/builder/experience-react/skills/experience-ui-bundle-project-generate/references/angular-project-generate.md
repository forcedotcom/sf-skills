# Angular UI Bundle Starter Templates

Reference for the **Angular** path of `experience-ui-bundle-project-generate`. Pick the `--template` flag that fits the user's audience, then return to Step 2 of `SKILL.md`.

## Template options

| Template | `--template` flag | Best for |
|----------|-------------------|----------|
| Internal starter | `angularinternalapp` | Starter for internal, employee-facing Salesforce apps (e.g. support consoles, ops dashboards, internal admin apps) — users are already-authenticated employees. Includes agent chat container. No login flow or public access. |
| External starter | `angularexternalapp` | Starter for customer/partner-facing Salesforce apps/sites (e.g. portals, communities, storefront, public sites). Includes agent chat container. Full auth support (login, registration, reset, profile) — external users sign in with their own accounts. |

## What the bundle contains

The generated UI bundle under `force-app/main/default/uiBundles/$NAME/` is an **Angular** app (Angular 21.2.x) built on **spartan-ng**:

- **Build:** Angular CLI driven by `angular.json` with the `@angular/build:application` builder (esbuild-based). Salesforce platform integration is wired through the `@salesforce/angular-plugin-ui-bundle` esbuild plugin (via `@angular-builders/custom-esbuild`), which handles API-version substitution, the org proxy, and Live Preview / `SFDC_ENV` / base-href injection.
- **Components:** standalone components + signals + native control flow (`@if`/`@for`); each component is a `.ts` + `.html` pair, named without a `.component` infix (e.g. `home.ts` + `home.html`).
- **App wiring:** entry `src/main.ts`; `src/app/app.ts` + `src/app/app.html`; `src/app/app.config.ts` (`APP_BASE_HREF` + `SFDC_ENV.basePath`); `src/app/app.routes.ts`. Pages under `src/app/pages/` (e.g. `home/`, `login/`, `account-search/`, `not-found/`).
- **UI library:** **spartan-ng** — `hlm-*` "Helm" primitives under `src/app/shared/` (alert, button, calendar, card, dialog, dropdown-menu, field, input, label, pagination, popover, select, separator, skeleton, spinner…), each folder exporting an `index.ts`. Configured via `components.json`; built on `@spartan-ng/brain` + `@spartan-ng/cli` + **Tailwind 4** (`src/styles.css`). Not Angular Material — there is no `theme.scss`. `src/app/components/` holds only `layout/app-layout` plus small `ui/` helpers.
- **Data layer:** injectable GraphQL data client `src/app/api/data-client.service.ts` (plus `user-profile.service.ts`, generated `graphql-operations-types.ts`, and typed operations under `src/app/api/account/`). GraphQL type codegen is optional and manual (not chained to the build).
- **Metadata & config:** `ui-bundle.json`, `$NAME.uibundle-meta.xml`, `tsconfig.*`, `eslint.config.js`, `playwright.config.ts`, `README.md`.
- **External (customer-facing) markers:** the external template also emits `networks/$NAME.network-meta.xml` + `sites/$NAME.site-meta.xml` and a full `src/app/features/authentication/` feature (login, register, forgot/reset/change-password, profile) — these distinguish the external starter from the internal one.
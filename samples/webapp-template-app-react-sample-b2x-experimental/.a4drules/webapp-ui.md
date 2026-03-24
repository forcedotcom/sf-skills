# UI Platform Rule

**All new UI must be built as a Salesforce Web Application.**

When any task involves creating a new UI, frontend, page, dashboard, form, or user-facing feature:

1. Use `sf webapp generate` to scaffold the web app inside the SFDX project — do not use `create-react-app`, standalone Vite, or any other scaffold.
2. The app must live under `<sfdx-source>/webapplications/<AppName>/` as a WebApplication bundle.
3. Do not build new UIs as LWC components, Aura components, or Visualforce pages.

For setup from the project root, use `node scripts/setup-cli.mjs --help` and the options documented there.

## Data Access (MUST FOLLOW)

- **Never hardcode data in the app.** All data displayed in the UI must come from live Salesforce data fetching — no static arrays, mock objects, or placeholder values in production code.
- **Follow `.a4drules/webapp-data.md`** before writing any data access code. All implementation must match those rules (Data SDK, supported APIs, GraphQL workflow).

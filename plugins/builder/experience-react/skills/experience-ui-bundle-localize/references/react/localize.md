# React reference — Localize a React UI Bundle

Framework-specific companion to `SKILL.md` for the **React** path. `SKILL.md` owns the
neutral workflow + guardrail spine (Step 0 routing, preconditions, the five steps, and
the guardrails); this file owns everything React/i18next-specific: the runtime library,
the call convention, the wiring shape, and the depth docs.

## Library & call convention

A React UI Bundle can't use `@salesforce/label/*` the way LWC does — those imports
resolve at compile time inside the platform's compiler, which your standalone React
bundle doesn't go through. Instead the app **fetches labels at runtime** through the
Salesforce GraphQL UI API and hands them to **i18next** (via `react-i18next`) to render.

```tsx
import { useTranslation } from "react-i18next";

function WelcomeBanner() {
  const { t } = useTranslation("c"); // "c" = custom label namespace
  return <h1>{t("Welcome_Text")}</h1>; // renders "Welcome" or "Bienvenido" per user's language
}
```

- **Call site:** `t("Key")` (from `useTranslation("c")`).
- **Files scanned for user-facing strings / call sites:** `.tsx` / `.jsx`.
- **Import to add** when a component first calls `t()`:
  `import { useTranslation } from "react-i18next";` and `const { t } = useTranslation("c");`.

## Step 2 (Extract) — React specifics

Replace the JSX literal with a `t()` call and add the import:

```tsx
// Before: <h1>Welcome</h1>
// After:  <h1>{t("Welcome_Text")}</h1>
```

## Step 4 (Wire) — React specifics

Install the i18n dependencies (tell the user to run, from the UI bundle dir):

```bash
npm install i18next react-i18next i18next-chained-backend i18next-localstorage-backend
```

Then scaffold `src/i18n/index.ts` (the `initI18n()` that wires
`@salesforce/platform-sdk/i18n` into i18next) and `src/i18n/label-manifest.ts`, and call
`initI18n()` once at boot in the entry file (usually `src/index.tsx`) before mounting the
app. Full init code and the B2E vs B2C `SalesforceBackend` configuration are in
[i18n-setup.md](./i18n-setup.md).

## Scripts

Run them from the UI bundle dir (they scan `src/` relative to the current directory). The
first three are framework-neutral and live in the skill's shared `scripts/` folder;
`check-i18n-wired.sh` is React-specific (i18next `backendOptions` detection) and ships here
in the React reference folder.

| Script | Purpose |
|--------|---------|
| [`check-org-api-version.sh`](../../scripts/check-org-api-version.sh) | Precondition 4 — org supports API v68.0+ |
| [`detect-bundle-type.sh`](../../scripts/detect-bundle-type.sh) | Precondition 5 — classify B2E / B2C / internal |
| [`check-manifest-registered.sh --framework react`](../../scripts/check-manifest-registered.sh) | Step 3 — every `t("Key")` is registered in the manifest (`--framework react` selects the `.tsx/.jsx` + `t()` grammar) |
| [`check-i18n-wired.sh`](./check-i18n-wired.sh) | Step 4 — `initI18n()` defined, called at boot, manifest passed into `backendOptions` |

## Depth docs

Framework-neutral (shared with Angular), in [`../common/`](../common/):
- [platform-sdk-i18n.md](../common/platform-sdk-i18n.md) — the shared runtime engine: the Labels GraphQL query, `fetchI18nContext`, the manifest format, batching, and fallback
- [label-xml.md](../common/label-xml.md) — Custom Labels and translation metadata XML shapes; the `namespace:Key` rules
- [verifying.md](../common/verifying.md) — serve URL, locale flip, and verifying labels render
- [gotchas.md](../common/gotchas.md) — the silent-fail traps: unregistered manifest keys, API-version bake-in, stale label cache

React-specific (this folder):
- [i18n-setup.md](./i18n-setup.md) — the two files you write: the i18next init and the label manifest
- [interpolation.md](./interpolation.md) — positional `{0}/{1}` placeholder interpolation in labels

# i18n Setup: the two files you write

You write two files to set up i18n in a React UI Bundle. The Platform SDK provides the runtime plumbing (detector, backend, context fetch); you just wire it into i18next.

---

## File 1: `src/i18n/index.ts` (the init wiring)

This is the only "glue" you write. It connects the SDK's i18n pieces to i18next.

```typescript
import { createDataSDK } from "@salesforce/platform-sdk";
import {
  createSalesforceDetector,
  fetchI18nContext,
  SalesforceBackend,
} from "@salesforce/platform-sdk/i18n";
import i18next from "i18next";
import ChainedBackend from "i18next-chained-backend";
import LocalStorageBackend from "i18next-localstorage-backend";
import { initReactI18next } from "react-i18next";
import { labelManifest } from "./label-manifest";

export async function initI18n() {
  const dataSDK = await createDataSDK();
  const ctx = await fetchI18nContext(dataSDK);

  // Tell the browser the user's language + text direction (RTL support).
  document.documentElement.dir = ctx.dir;
  document.documentElement.lang = ctx.lang;

  await i18next
    .use(ChainedBackend)
    .use(createSalesforceDetector(dataSDK))
    .use(initReactI18next)
    .init({
      fallbackLng: "en", // untranslated keys fall back to the English base value
      defaultNS: "c", // "c" = your org's custom-label namespace
      backend: {
        backends: [LocalStorageBackend, SalesforceBackend],
        backendOptions: [
          { expirationTime: 86400000 }, // cache labels in localStorage for a day
          { dataSDK, labelManifest }, // fetch the rest over GraphQL
        ],
      },
      interpolation: {
        // escapeValue: false is correct for React: React already escapes JSX
        // output. Do NOT feed interpolated label output into
        // dangerouslySetInnerHTML; that bypasses React's escaping and, with this
        // setting, is an XSS vector when a label interpolates user-controlled
        // text. Render labels as normal JSX (`{t(...)}`).
        escapeValue: false,
        prefix: "{", // Salesforce labels interpolate with {0}, {1}, …
        suffix: "}",
      },
    });
}
```

**Call it once at boot**, before mounting your app:

```typescript
// src/index.tsx
import { initI18n } from "./i18n";

initI18n().then(() => {
  // mount app here
  root.render(<App />);
});
```

---

## File 2: `src/i18n/label-manifest.ts` (the list of labels your app uses)

This tells i18next which labels to fetch at boot.

```typescript
export const labelManifest = [
  "c:Welcome_Text",
  "c:Save_Button",
  "c:Save_Failed_Message",
  // one entry per label, "namespace:Key"
];
```

**Format:** `"<namespace>:<Key>"`
- `c` = custom labels in your org
- `Key` = the `<fullName>` from your `CustomLabels.labels-meta.xml`

The manifest is how i18next knows what to fetch. An **unregistered key fails silently**: it renders as its own literal name (e.g., `"Welcome_Text"` instead of "Welcome") with no console warning. Always keep the manifest in sync with your `t()` calls.

---

## Dependencies

Install these first (Step 4 of the main workflow):

```bash
npm install i18next react-i18next i18next-chained-backend i18next-localstorage-backend
```

Use `@salesforce/platform-sdk` **≥11.42.1**. The `@salesforce/platform-sdk/i18n` subpath (`SalesforceBackend`, `createSalesforceDetector`, `fetchI18nContext`) has existed since 11.4.1, and 11.7.0 added `reloadI18nContext` for refreshing the cached label context. 11.42.1 is the validated floor because it carries the fix that batches a namespace into 100-name-or-fewer queries. Without it, a manifest of more than 100 labels in one namespace hits the `uiapi.platform.labels` limit and the whole namespace read fails. Keep the SDK's siblings (`@salesforce/vite-plugin-ui-bundle`, `@salesforce/ui-bundle`) on the same version.

Known-good companion versions:
- `i18next` **^24.2.2**
- `react-i18next` **^15.5.1**
- `i18next-chained-backend` **^4.6.2**
- `i18next-localstorage-backend` **^4.2.0**

---

## What you DON'T write

The Platform SDK ships with:
- `createSalesforceDetector`: reads the user's language from the org
- `SalesforceBackend`: fetches labels over GraphQL
- `fetchI18nContext`: gets language, locale, text direction, currency

If you see an older example that vendors `salesforce-detector.ts` or `salesforce-backend.ts` into `src/`, it predates the SDK's i18n export. You no longer copy those files in; just import from `@salesforce/platform-sdk/i18n`.

---

## How it works at boot

1. Bundle loads, `initI18n()` runs
2. `createDataSDK()` initializes the SDK
3. `fetchI18nContext()` queries the org for the user's language/locale/direction
4. `SalesforceBackend` reads the manifest and issues a GraphQL query per namespace:
   ```graphql
   query LoadLabels {
     uiapi {
       platform {
         labels(namespace: "c", names: ["Welcome_Text", "Save_Button", ...]) {
           name
           value
           resolvedLocale
         }
       }
     }
   }
   ```
5. Platform returns labels at the user's resolved locale
6. i18next caches them (in memory + localStorage)
7. React mounts; components call `t()`; lookups hit the cache

The two backends chain: `LocalStorageBackend` serves cached labels (24-hour expiry), and `SalesforceBackend` fetches misses over GraphQL. This makes subsequent loads fast.

---

## Namespace note

`defaultNS: "c"` means components can call `t("Welcome_Text")` instead of `t("c:Welcome_Text")`; the namespace is implicit. If you're loading labels from multiple namespaces (e.g., framework-shipped labels like `LightningDatatable`), you'd specify the namespace in the `useTranslation` hook:

```typescript
const { t } = useTranslation("c"); // custom labels
const { t: tFw } = useTranslation("LightningDatatable"); // framework labels
```

For most bundles, a single `"c"` namespace is all you need.

---

## Related

- [label-xml.md](label-xml.md): the Custom Labels metadata XML shape
- [interpolation.md](interpolation.md): how `{0}/{1}` placeholders work
- [verifying.md](verifying.md): the serve/verify flow
- [gotchas.md](gotchas.md): silent-fail traps to avoid

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

  // B2E: the session language is the display language.
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
          { dataSDK, labelManifest }, // B2E: shipped BASE_VALUE fallback
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

The example above is the **B2E** configuration. Do not set `labelFallback` for B2E: the shipped `SalesforceBackend` default is `BASE_VALUE`.

For a **B2C** bundle, change only the Salesforce backend options entry:

```typescript
backendOptions: [
  { expirationTime: 86400000 },
  {
    dataSDK,
    labelManifest,
    labelFallback: "USER_DEFAULT",
  },
],
```

`USER_DEFAULT` is required for B2C so fallback follows the guest/site language context. Do not copy this override into B2E wiring.

For B2C, also set the document language and direction from the route-selected display language, not `ctx.dir`. The GraphQL i18n context direction reflects the guest session profile and can stay `ltr` after the site switches to an RTL language. Reuse the resolved language from the site's language-switcher integration:

```typescript
const resolvedLang =
  (globalThis as { SFDC_ENV?: { language?: string } }).SFDC_ENV?.language || ctx.lang;
document.documentElement.dir = i18next.dir(resolvedLang);
document.documentElement.lang = resolvedLang.replace(/_/g, "-");
```

Before using this configuration, have an org admin confirm that `GraphQLApiOrgPrefForGuestUsers` is already enabled. This workflow must never enable it. Without the preference, unauthenticated GraphQL label requests return HTTP 403; see dependency W-23854208.

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

## B2C language context

A B2C site's configured languages and language-specific URLs are the source of truth. At boot, the site route supplies `SFDC_ENV.language`; the SDK detector uses that value to resolve labels. A language switcher must navigate to the target language URL and perform a full page reload. An in-place i18next language change is insufficient because the SDK context and localStorage-backed labels are established at boot.

For local preview, use the site entry of the Vite plugin and pass the site's supported language codes, with the default first:

```typescript
import siteUiBundlePlugin from "@salesforce/vite-plugin-ui-bundle/site";

export default defineConfig({
  plugins: [siteUiBundlePlugin({ languages: ["en_US", "es", "ar"] })],
});
```

The site plugin injects `SFDC_ENV.language` per request and serves non-default hyphenated language routes such as `/es` or `/en-US`; the default language has no prefix. Verify the injected language before judging label output. The authenticated org user's Language setting is not a substitute for the guest site's language context.

---

## Dependencies

Install these first (Step 4 of the main workflow):

```bash
npm install i18next react-i18next i18next-chained-backend i18next-localstorage-backend
```

Use aligned `@salesforce/platform-sdk`, `@salesforce/vite-plugin-ui-bundle`, and `@salesforce/ui-bundle` packages at **≥11.49.3**. Platform SDK 11.45.0 introduced the `labelFallback` option and shipped `BASE_VALUE` default, but the B2C local-preview entry `@salesforce/vite-plugin-ui-bundle/site` first appears in the 11.49.x line. Version 11.49.3 is therefore the common floor for this B2C-capable workflow. Earlier history: the i18n subpath existed in 11.4.1, 11.7.0 added `reloadI18nContext`, and 11.42.1 added namespace batching for the 100-name labels-query limit.

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
3. `fetchI18nContext()` queries the org for language/locale/direction (B2C uses the site route's `SFDC_ENV.language`)
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

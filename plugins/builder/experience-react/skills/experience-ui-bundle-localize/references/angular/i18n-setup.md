# i18n Setup: the two files you write (Angular / ngx-translate)

You write two files to set up i18n in an Angular UI Bundle: a **custom `TranslateLoader`** that
fetches Custom Labels over GraphQL, and the **label manifest**. The Platform SDK provides the
runtime plumbing (context fetch, the GraphQL surface); ngx-translate provides the pipe/service.
The shared engine — the Labels query, manifest format, batching, and fallback — is documented
once in [`../common/platform-sdk-i18n.md`](../common/platform-sdk-i18n.md); this file only covers
the Angular wiring.

> **Why a custom loader?** React drops the shipped `SalesforceBackend` straight into i18next.
> ngx-translate loads translations through a `TranslateLoader` instead, so you implement one
> that issues the **same** `uiapi.platform.labels` query. `SalesforceBackend` is i18next-shaped
> (it implements i18next's `read()` contract), so it isn't reused directly here.

---

## File 1: `src/i18n/salesforce-translate-loader.ts` (the label loader)

This is the only "glue" you write. `getTranslation(lang)` returns an `Observable` of a flat
`{ key: value }` map for that language — exactly what ngx-translate expects.

```typescript
import { Injectable } from "@angular/core";
import type { TranslateLoader } from "@ngx-translate/core";
import { createDataSDK } from "@salesforce/platform-sdk";
import { from, Observable } from "rxjs";
import { labelManifest } from "./label-manifest";

const LABELS_QUERY = `
  query Labels($ns: String!, $names: [String!]!, $locale: String, $fallback: LabelFallback) {
    uiapi {
      platform {
        labels(namespace: $ns, names: $names, locale: $locale, fallback: $fallback) {
          name
          value
          resolvedLocale
          wasFallback
        }
      }
    }
  }`;

const MAX_NAMES_PER_QUERY = 100; // uiapi.platform.labels rejects > 100 names per call
// B2E: keep "BASE_VALUE" (the shipped default). B2C: use "USER_DEFAULT" (see below).
const LABEL_FALLBACK = "BASE_VALUE";

@Injectable({ providedIn: "root" })
export class SalesforceTranslateLoader implements TranslateLoader {
  getTranslation(lang: string): Observable<Record<string, string>> {
    return from(this.loadLabels(lang));
  }

  private async loadLabels(lang: string): Promise<Record<string, string>> {
    const dataSDK = await createDataSDK();
    if (!dataSDK.graphql) throw new Error("Data SDK GraphQL surface unavailable");
    // Hoist to a local const: TypeScript drops the `!dataSDK.graphql` narrowing inside the
    // async batch closures below, so referencing `dataSDK.graphql.query` there re-widens to
    // possibly-undefined (TS18048). The local const keeps the narrowed type.
    const graphql = dataSDK.graphql;

    // Group "namespace:Key" manifest entries by namespace.
    const byNamespace = new Map<string, string[]>();
    for (const entry of labelManifest) {
      const idx = entry.indexOf(":");
      const ns = idx === -1 ? "c" : entry.slice(0, idx);
      const name = idx === -1 ? entry : entry.slice(idx + 1);
      (byNamespace.get(ns) ?? byNamespace.set(ns, []).get(ns)!).push(name);
    }

    const result: Record<string, string> = {};
    // Fetch each namespace, chunked into <=100-name batches, all in parallel.
    await Promise.all(
      [...byNamespace].flatMap(([ns, names]) => {
        const unique = [...new Set(names)];
        const batches: string[][] = [];
        for (let i = 0; i < unique.length; i += MAX_NAMES_PER_QUERY) {
          batches.push(unique.slice(i, i + MAX_NAMES_PER_QUERY));
        }
        return batches.map(async (batch) => {
          const res = await graphql.query<any>({
            operationName: "Labels",
            query: LABELS_QUERY,
            variables: { ns, names: batch, locale: lang, fallback: LABEL_FALLBACK },
          });
          const labels = res?.data?.uiapi?.platform?.labels ?? [];
          for (const label of labels) {
            if (label?.value != null) {
              // Default "c" labels use the bare key; other namespaces keep the prefix.
              const key = ns === "c" ? label.name : `${ns}:${label.name}`;
              result[key] = label.value;
            }
          }
        });
      }),
    );
    return result;
  }
}
```

Notes:
- `dataSDK.graphql.query` **never rejects** — transport/GraphQL errors arrive on `res.errors`.
  Inspect it if you want to surface a hard failure; the example simply treats missing data as
  "no labels for this batch."
- ngx-translate has a single flat key space per language (no namespace concept). Default `c`
  labels are keyed by bare name (`{{ 'Welcome_Text' | translate }}`); non-`c` namespaces keep
  their prefix (`{{ 'LightningDatatable:sort' | translate }}`). Most bundles use only `c`.
- `createDataSDK()` is called here per language load. To avoid re-initializing it, wrap it in a
  root-provided service and inject that into the loader and the boot initializer below.

### B2C variant

For a **B2C** bundle, set the fallback to follow the guest/site language context:

```typescript
const LABEL_FALLBACK = "USER_DEFAULT"; // B2C only — do NOT use for B2E
```

Before using B2C wiring, have an org admin confirm `GraphQLApiOrgPrefForGuestUsers` is already
enabled. This workflow must never enable it. Without the preference, unauthenticated GraphQL
label requests return HTTP 403 (dependency W-23854208).

---

## File 2: `src/i18n/label-manifest.ts` (the list of labels your app uses)

Identical format to every framework — a flat `"namespace:Key"` array (see
[`../common/platform-sdk-i18n.md`](../common/platform-sdk-i18n.md) and
[`../common/label-xml.md`](../common/label-xml.md)):

```typescript
export const labelManifest = [
  "c:Welcome_Text",
  "c:Save_Button",
  "c:Save_Failed_Message",
  // one entry per label, "namespace:Key"
];
```

An **unregistered key fails silently**: it renders as its own literal name (e.g. `"Welcome_Text"`
instead of "Welcome") with no console warning. Keep the manifest in sync with your `translate`
call sites — `check-manifest-registered.sh --framework angular` verifies this.

---

## Wiring: `src/app/app.config.ts`

Register ngx-translate with the custom loader in the standalone providers, and set the app's
`{0}/{1}` interpolation parser (see [interpolation.md](./interpolation.md)):

```typescript
import { ApplicationConfig, provideAppInitializer, inject } from "@angular/core";
import {
  provideTranslateService,
  TranslateLoader,
  TranslateService,
} from "@ngx-translate/core";
import { createDataSDK } from "@salesforce/platform-sdk";
import { fetchI18nContext } from "@salesforce/platform-sdk/i18n";
import { firstValueFrom } from "rxjs";
import { SalesforceTranslateLoader } from "../i18n/salesforce-translate-loader";

export const appConfig: ApplicationConfig = {
  providers: [
    // …your existing providers (provideRouter(routes), etc.)
    provideTranslateService({
      loader: { provide: TranslateLoader, useClass: SalesforceTranslateLoader },
      // Fallback language when a key isn't loaded for the active language.
      // v16+ renamed this option `defaultLanguage` → `fallbackLang`; older majors use
      // `defaultLanguage`. Match your installed @ngx-translate/core.
      fallbackLang: "en",
      // parser: { provide: TranslateParser, useClass: PositionalParser }, // see interpolation.md
    }),

    // Boot: read the org locale context, set <html> dir/lang, load the active language,
    // and block bootstrap until labels are ready.
    provideAppInitializer(async () => {
      const translate = inject(TranslateService);
      const dataSDK = await createDataSDK();
      const ctx = await fetchI18nContext(dataSDK);

      // B2E: the session language is the display language.
      document.documentElement.dir = ctx.dir;
      document.documentElement.lang = ctx.lang;

      await firstValueFrom(translate.use(ctx.lang)); // triggers the loader for that language
    }),
  ],
};
```

`main.ts` stays as generated (`bootstrapApplication(App, appConfig)`); the app initializer runs
and resolves before the root component renders, so labels are present on first paint.

### B2C: display language from the site route

For B2C, drive the document language from the **route-selected** display language, not `ctx.dir`
— the GraphQL i18n context direction reflects the guest session profile and can stay `ltr` after
the site switches to an RTL language:

```typescript
const resolvedLang =
  (globalThis as { SFDC_ENV?: { language?: string } }).SFDC_ENV?.language || ctx.lang;
document.documentElement.lang = resolvedLang.replace(/_/g, "-");
await firstValueFrom(translate.use(resolvedLang));
```

A B2C language switcher must **navigate to the target language URL and perform a full page
reload** — changing `translate.use(...)` in place leaves the boot-time SDK context and cached
labels stale. Confirm the route and `SFDC_ENV.language` agree.

---

## Dependencies

Install ngx-translate (Step 4 of the main workflow), choosing a `@ngx-translate/core` release
compatible with the bundle's Angular version (the standalone `provideTranslateService` API is
v16+; Angular 21 bundles use the current major):

```bash
npm install @ngx-translate/core
```

Keep the `@salesforce/platform-sdk`, `@salesforce/ui-bundle`, and Angular build-plugin siblings
aligned at **≥11.49.3** (see [`../common/platform-sdk-i18n.md`](../common/platform-sdk-i18n.md)
for the version-floor rationale).

---

## What you DON'T write

The Platform SDK ships the runtime engine — you do **not** re-implement locale detection or the
context fetch:
- `fetchI18nContext` / `reloadI18nContext`: language, locale, direction, currency, time zone
- `createDataSDK`: the GraphQL surface your loader queries
- `createI18nFormatters`: Intl date/number/currency formatters

You **do** write the `TranslateLoader` (the Angular analog of React's `SalesforceBackend`),
because ngx-translate loads through that contract. See
[`../common/platform-sdk-i18n.md`](../common/platform-sdk-i18n.md) for the query it issues.

---

## Related

- [../common/platform-sdk-i18n.md](../common/platform-sdk-i18n.md): the shared runtime engine
- [../common/label-xml.md](../common/label-xml.md): the Custom Labels metadata XML shape
- [interpolation.md](./interpolation.md): how `{0}/{1}` placeholders work with ngx-translate
- [../common/verifying.md](../common/verifying.md): the serve/verify flow
- [../common/gotchas.md](../common/gotchas.md): silent-fail traps to avoid

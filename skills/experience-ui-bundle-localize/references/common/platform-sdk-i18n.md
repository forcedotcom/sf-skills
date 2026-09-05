# The Platform SDK i18n engine (framework-neutral)

The runtime plumbing that resolves Salesforce Custom Labels for a UI Bundle is **the same
regardless of framework**. It ships in `@salesforce/platform-sdk` (the `/i18n` subpath) and is
what both the React (i18next) and Angular (ngx-translate) paths build on. This file documents
that shared engine once; each framework reference only covers how it wires the engine into its
own i18n library.

A UI Bundle can't use compile-time `@salesforce/label/*` imports the way LWC does (those resolve
inside the platform compiler your standalone bundle skips). Instead the app **fetches labels at
runtime** over the Salesforce GraphQL UI API and hands them to a standard i18n library to render.

---

## What the SDK gives you (you don't write these)

From `@salesforce/platform-sdk` (package root):

- `createDataSDK()` → returns a `DataSDK` whose `.graphql.query(...)` surface talks to the org.
  Its `query` **never rejects**; transport/GraphQL errors come back on `result.errors`.

From `@salesforce/platform-sdk/i18n`:

- `fetchI18nContext(dataSDK)` — reads the user's locale context (below). **Memoized** for the page.
- `reloadI18nContext(dataSDK)` — clears that memo and re-fetches (for in-session locale changes).
- `createSalesforceDetector(dataSDK)` — an i18next-shaped language detector whose `detect()`
  returns the cached context's `lang`. (React consumes this directly; Angular reads `ctx.lang`
  from `fetchI18nContext` instead and calls `TranslateService.use(lang)`.)
- `SalesforceBackend` — an **i18next backend plugin** that fetches labels over GraphQL. React
  plugs it straight into i18next. Angular does **not** use it; its custom `TranslateLoader`
  re-implements the same GraphQL fetch (same query, same batching) against ngx-translate's
  `Observable` contract.
- `createI18nFormatters(ctx)` — Intl wrappers (`formatDate`, `formatNumber`, `formatCurrency`).

You write only two thin files per app: the **init/loader wiring** (framework-specific) and the
**label manifest** (framework-neutral format, below).

---

## The label fetch: `uiapi.platform.labels`

Both frameworks issue the same GraphQL query to resolve labels for a language + namespace:

```graphql
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
}
```

- `ns` — the namespace (`c` for your org's custom labels; also e.g. `LightningDatatable`).
- `names` — the label API names in that namespace (no `ns:` prefix here).
- `locale` — the target language (the user's `lang`, or a B2C site language).
- `fallback` — a `LabelFallback` enum value (below).

The result is assembled into a plain `Record<string, string>` of `{ [label.name]: label.value }`.
**Labels whose `value` is null are skipped** (not added to the map), so an unresolved key falls
through to the i18n library's key-name fallback.

### Manifest → namespaces → batches

The **label manifest** is a flat array of `"namespace:key"` strings you maintain by hand:

```typescript
// src/i18n/label-manifest.ts
export const labelManifest = [
  "c:Welcome_Text",
  "c:Save_Button",
  "LightningDatatable:sort",
];
```

The backend/loader:
1. Splits each entry on the first `:` and **groups by namespace** (`{ c: [...], LightningDatatable: [...] }`).
2. For each namespace + language, **dedupes** the names and **chunks them into batches of at most
   100** (`uiapi.platform.labels` rejects a single call with > 100 names).
3. Fires the batches **in parallel** and merges the results. The load is **all-or-nothing per
   namespace**: if any batch rejects, the whole namespace read fails (no half-populated namespace).

A manifest with 500 `c:*` keys becomes 5 batched queries under the hood; your manifest stays flat.

### `LabelFallback` — pick by bundle type

```typescript
type LabelFallback = "BASE_VALUE" | "USER_DEFAULT" | "NONE";   // default: BASE_VALUE
```

- **B2E** — keep the `BASE_VALUE` default (a registered key with no translation for the active
  language resolves to its English base value; `wasFallback: true`).
- **B2C** — set `labelFallback: "USER_DEFAULT"` so fallback follows the guest/site language context.
- Never apply the B2C override to B2E.

(When re-running the query by hand in DevTools, `$fallback` must be declared in the operation
signature **and** passed to the `labels(...)` field — a `fallback` key in the variables block alone
is silently dropped and the server defaults to `USER_DEFAULT`.)

---

## The locale context: `fetchI18nContext`

A separate, small GraphQL query reads the user's locale context. It runs on every boot (it is
**not** cached in localStorage — only memoized in module memory for the page lifetime):

```graphql
query I18nDetect {
  uiapi { platform { i18n { lang locale dir currency timeZone } } }
}
```

```typescript
interface I18nContext { lang; locale; dir; currency; timeZone; }
```

- `lang` — the **translation** axis (`en_US`, `es`, `de`) → picks which label translations load.
- `locale` — the **formatting** axis (`de_DE`, `fr_CA`) → feeds `Intl` formatters. Region-only;
  it does **not** flip label text.
- `dir` — `"ltr"` / `"rtl"` (set `document.documentElement.dir` at boot).

At boot each framework: `await fetchI18nContext(dataSDK)`, then sets `document.documentElement.dir`
and `.lang`, and tells its i18n library which language to use. `reloadI18nContext(dataSDK)` is the
only way to pick up an in-session locale change (a fresh `fetchI18nContext` returns the memo).

### Formatting: `createI18nFormatters(ctx)`

Returns `{ formatDate, formatNumber, formatCurrency }` bound to `ctx.locale` (BCP-47),
`ctx.currency`, and `ctx.timeZone`, wrapping `Intl.*`. Note it formats off `ctx.locale` (region),
**not** `ctx.lang` (translation). Positional `{0}/{1}` interpolation does **not** format values —
pass an already-formatted string as the placeholder value if you need locale-aware numbers/dates.

---

## Runtime floor & dependency alignment

- The `platform.labels` runtime path for UI Bundles ships in **Salesforce Release 264 / API v68.0**.
  A `sourceApiVersion` in `sfdx-project.json` records what you *declared*, not what the org
  *supports* — query the org's actual max API version before wiring (`check-org-api-version.sh`,
  precondition 4). Below v68.0 a localized bundle renders blank or shows raw key names.
- Keep the Platform SDK, UI Bundle, and build-plugin siblings aligned and **≥ 11.49.3**.

---

## How each framework consumes this engine

| Concern | React (i18next) | Angular (ngx-translate) |
|---|---|---|
| Label fetch | `SalesforceBackend` (shipped) in a chained backend | custom `TranslateLoader.getTranslation(lang)` issuing the same query |
| Language pick | `createSalesforceDetector(dataSDK)` | read `ctx.lang`, call `TranslateService.use(lang)` |
| Cache | `i18next-localstorage-backend` (`i18next_res_*`, 24h) | in-memory on `TranslateService` (reload refetches) |
| Interpolation | `interpolation: { prefix:"{", suffix:"}" }` for `{0}/{1}` | custom `TranslateParser`/compiler for `{0}/{1}` |

See your framework reference's `i18n-setup.md` for the exact wiring, and [gotchas.md](gotchas.md)
for the silent-fail traps this engine can produce.

---

## Related

- [label-xml.md](label-xml.md): the Custom Labels + translations metadata this engine resolves
- [verifying.md](verifying.md): build/deploy/verify labels across locales
- [gotchas.md](gotchas.md): unregistered keys, API-version bake-in, stale cache, B2C 403
- your framework reference's `i18n-setup.md` / `interpolation.md`: the framework-specific wiring

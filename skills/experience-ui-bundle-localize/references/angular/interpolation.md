# Interpolation: `{0}`, `{1}` placeholders with ngx-translate

Salesforce Custom Labels use **positional interpolation**: `{0}`, `{1}`, `{N}` placeholders that
get replaced with runtime values. This is the same syntax used by Apex `String.format`, LWC
`@salesforce/label`, and the React path — so one label works across all of them. The
placeholder convention itself is framework-neutral (see
[`../common/label-xml.md`](../common/label-xml.md)); this file covers the **Angular render**.

---

## The gotcha: ngx-translate defaults to `{{param}}`, not `{0}`

Out of the box, ngx-translate interpolates **named** placeholders in double braces
(`{{name}}`). Salesforce labels use **positional single-brace** placeholders (`{0}`). To bridge
them, register a small custom `TranslateParser` that substitutes `{0}`, `{1}`, … This is the
Angular analog of React's i18next `interpolation: { prefix: "{", suffix: "}" }` config.

### `src/i18n/positional-translate-parser.ts`

```typescript
import { Injectable } from "@angular/core";
import { TranslateDefaultParser } from "@ngx-translate/core";

@Injectable()
export class PositionalTranslateParser extends TranslateDefaultParser {
  override interpolate(
    expr: string | ((...args: unknown[]) => string),
    params?: Record<string, unknown>,
  ): string | undefined {
    if (typeof expr !== "string") return super.interpolate(expr, params);
    if (!params) return expr;
    // Replace {0}, {1}, … with params["0"], params["1"], …; leave unmatched ones as-is.
    return expr.replace(/\{(\d+)\}/g, (match, index) =>
      params[index] != null ? String(params[index]) : match,
    );
  }
}
```

Register it in `provideTranslateService(...)` (see [i18n-setup.md](./i18n-setup.md)):

```typescript
import { TranslateParser } from "@ngx-translate/core";

provideTranslateService({
  loader: { provide: TranslateLoader, useClass: SalesforceTranslateLoader },
  parser: { provide: TranslateParser, useClass: PositionalTranslateParser },
  defaultLanguage: "en",
});
```

---

## Passing values

Params are an object keyed by the **placeholder number as a string** (`"0"`, `"1"`). A plain
`{ 0: … }` literal works — JS object keys are strings.

```html
<!-- Label: "Hello, {0}" -->
<h1>{{ 'Greeting' | translate:{ '0': userName } }}</h1>
<!-- → "Hello, Tosin" -->

<!-- Label: "Failed to save {0}: {1}" -->
<p>{{ 'Save_Failed' | translate:{ '0': objectName, '1': reason } }}</p>
```

```typescript
// imperative form
this.translate.instant("Save_Failed", { 0: "Account", 1: "Permission denied" });
// → "Failed to save Account: Permission denied"

this.translate.get("Record_Count", { 0: 42, 1: 100 }).subscribe(/* … */);
// label "Showing {0} of {1} records" → "Showing 42 of 100 records"
```

Order in the object doesn't matter; the placeholder **number** binds. The same placeholder can
appear more than once (`"User {0} cannot edit {0}'s own profile"`) — every `{0}` is replaced.

---

## Translations must preserve placeholders

The placeholders stay as `{0}`, `{1}` in every translation; they can move (grammar may reorder
them) but the **numbers must match**:

```xml
<!-- English -->  <value>Failed to save {0}: {1}</value>
<!-- Spanish -->  <label>Error al guardar {0}: {1}</label>
```

---

## Numeric / date values are not locale-formatted

Interpolation is a string replace — `{ 0: 1234.5 }` renders JS's default `toString`, not
`1.234,5`. For locale-aware output, format first and pass the **formatted string**:

```typescript
const formatted = new Intl.NumberFormat(ctx.locale).format(count);
this.translate.instant("Record_Count", { 0: formatted, 1: total });
```

The Platform SDK's `createI18nFormatters(ctx)` gives you `formatDate` / `formatNumber` /
`formatCurrency` bound to `ctx.locale` (see [`../common/platform-sdk-i18n.md`](../common/platform-sdk-i18n.md)).

---

## Failure modes

- **Missing placeholder value** — `instant("Greeting", { 0: "Tosin" })` on label
  `"Hello, {0} from {1}"` renders `"Hello, Tosin from {1}"` (the unmatched placeholder leaks).
  No error; always pass every placeholder the label expects.
- **Missing label entirely** — `instant("Nonexistent_Key")` renders the literal key string.
  That's the **unregistered manifest key** trap (see [`../common/gotchas.md`](../common/gotchas.md)):
  the label was never fetched, so there's nothing to interpolate.

---

## Pluralization

Unlike i18next, ngx-translate has **no built-in plural suffixing**. Two options:

1. **Separate labels + manual selection** (portable, matches the React label set): author
   `Item_Count_one` / `Item_Count_other`, register both, and pick the key in code from
   `new Intl.PluralRules(ctx.lang).select(count)`:
   ```typescript
   const form = new Intl.PluralRules(ctx.lang).select(count); // "one" | "other" | …
   this.translate.instant(`Item_Count_${form}`, { 0: count });
   ```
2. **ICU MessageFormat** via `@ngx-translate/message-format-compiler` — install it and register
   its compiler in `provideTranslateService({ compiler: … })` if you want ICU `{count, plural, …}`
   syntax inside label values. This changes the label authoring format, so coordinate with the
   translation team.

Languages with more plural forms (Russian, Polish, Arabic) need the extra label variants
(`_zero`, `_few`, `_many`).

---

## Why positional (`{0}`) instead of named?

**Portability.** The same Custom Label metadata is consumed by Apex (`String.format`), LWC
(`@salesforce/label` with `{0}/{1}`), and both UI Bundle frameworks. Positional placeholders let
one authored/translated string serve all of them; a named format would fork the label per
framework and per translator. The custom parser above is what lets Angular join that convention.

---

## Related

- [../common/label-xml.md](../common/label-xml.md): authoring labels with placeholders
- [i18n-setup.md](./i18n-setup.md): where the parser is registered
- [../common/platform-sdk-i18n.md](../common/platform-sdk-i18n.md): the shared runtime engine
- [../common/verifying.md](../common/verifying.md): testing interpolated labels
- [../common/gotchas.md](../common/gotchas.md): silent-fail traps

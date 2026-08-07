# Interpolation: how `{0}`, `{1}` placeholders work

Salesforce Custom Labels use **positional interpolation**: `{0}`, `{1}`, `{N}` placeholders that get replaced with runtime values at render time. This is the same substitution syntax used by Apex `String.format` and LWC `@salesforce/label`, so one label works across all three frameworks.

---

## TLDR

It's a string-replace. i18next finds every `{0}`, `{1}`, `{N}` in the cached label content and substitutes the value at that key from the second argument of `t()`.

---

## Basic example

**Label:**
```xml
<labels>
  <fullName>Greeting</fullName>
  <value>Hello, {0}</value>
</labels>
```

**Component:**
```typescript
const { t } = useTranslation("c");
const userName = "Tosin";
return <h1>{t("Greeting", { 0: userName })}</h1>;
// → "Hello, Tosin"
```

---

## How it works

1. At boot, the Platform SDK's `SalesforceBackend` fetches the label content from the org via GraphQL
2. i18next caches it: `{ "c:Greeting": "Hello, {0}" }`
3. At render time, the component calls `t("Greeting", { 0: "Tosin" })`
4. i18next's interpolator does:
   ```javascript
   template = "Hello, {0}";
   template.replace("{0}", "Tosin");
   // → "Hello, Tosin"
   ```
5. The resulting string renders to the DOM

The configuration that makes this work is in `src/i18n/index.ts`:

```typescript
interpolation: {
  escapeValue: false,
  prefix: "{",   // scan for {X} placeholders
  suffix: "}",
},
```

i18next ships with `{{name}}`-style named interpolation by default. We override it to use Salesforce's `{0}` positional style so one label works across Apex, LWC, and React.

---

## Multiple placeholders

**Label:**
```xml
<value>Failed to save {0}: {1}</value>
```

**Component:**
```typescript
t("Save_Failed", { 0: "Account", 1: "Permission denied" });
// → "Failed to save Account: Permission denied"
```

Order in the object doesn't matter; the placeholder **number** is what binds:

```typescript
t("Save_Failed", { 1: "Permission denied", 0: "Account" }); // same result
```

---

## Same placeholder used twice

Salesforce labels sometimes reuse the same positional placeholder:

**Label:**
```xml
<value>User {0} cannot edit {0}'s own profile</value>
```

**Component:**
```typescript
t("Profile_Edit_Error", { 0: "tosin" });
// → "User tosin cannot edit tosin's own profile"
```

This is common when sentence structure differs across languages and the same value appears in different grammatical roles.

---

## Numeric and date values

Placeholders accept any JavaScript value. The value's `toString()` is what gets interpolated:

```typescript
// Numbers
t("Record_Count", { 0: 42, 1: 100 });
// label: "Showing {0} of {1} records" → "Showing 42 of 100 records"

// Dates (default JS toString, not localized)
t("Last_Modified", { 0: new Date() });
// label: "Last modified {0}" → "Last modified Mon Jul 07 2026 14:23:00 GMT-0700"
```

**Note:** This does **not** apply locale-aware formatting (e.g., `1.000,00` for German number formatting). For that, you'd use `Intl.NumberFormat` / `Intl.DateTimeFormat` separately and pass the **formatted string** as the placeholder value:

```typescript
const formattedCount = new Intl.NumberFormat(locale).format(count);
t("Record_Count", { 0: formattedCount, 1: total });
```

The Platform SDK's `fetchI18nContext()` gives you `ctx.locale` and `ctx.currency` for feeding `Intl` formatters.

---

## Translations must preserve placeholders

**English:**
```xml
<value>Failed to save {0}: {1}</value>
```

**Spanish translation:**
```xml
<label>Error al guardar {0}: {1}</label>
```

The placeholders stay as `{0}`, `{1}`; they can move (grammar might flip the order), but the **numbers must match**. If the Spanish translation says `{A}` or drops `{1}`, the substitution breaks.

This is why Translation Workbench is valuable: it shows translators the placeholders and warns if they're missing.

---

## Failure modes

### Missing placeholder value

**Label:** `"Hello, {0} from {1}"`

**Call:**
```typescript
t("Greeting", { 0: "Tosin" }); // forgot {1}
// → "Hello, Tosin from {1}" (literal placeholder leaks)
```

There's no runtime error or console warning; the unsubstituted placeholder just renders as-is. This is a visual bug, not a crash.

**Fix:** Always pass every placeholder the label expects. PR review catches this today (no build-time validation yet).

### Missing label entirely

```typescript
t("Nonexistent_Key");
// → "Nonexistent_Key" (literal key string)
```

This is the **unregistered manifest key** trap (see [gotchas.md](gotchas.md)): the label wasn't fetched, so i18next has nothing to interpolate.

---

## Worked examples by complexity

### 1. No interpolation (most labels)

**Label:** `"Welcome"`

**Call:** `t("Welcome_Text")`

**Result:** `"Welcome"`

Most labels are just lookups, no placeholders.

---

### 2. Single value

**Label:** `"You have {0} items"`

**Call:** `t("Item_Count", { 0: 5 })`

**Result:** `"You have 5 items"`

---

### 3. Error with context

**Label:** `"{0} failed at step {1} for record {2}: {3}"`

**Call:**
```typescript
t("Pipeline_Error", {
  0: "OnboardingPipeline",
  1: err.step,
  2: record.name,
  3: err.message,
});
```

**Result:** `"OnboardingPipeline failed at step ValidateAccount for record Acme Corp: Missing tax ID"`

One label, reusable across pipelines. Translated once. Engineers in any framework call it the same way.

---

### 4. Pluralization (leveraging i18next on top of positional)

i18next has native pluralization support. For Salesforce labels, you author separate labels for each plural form:

**Labels:**
```xml
<labels>
  <fullName>Item_Count_one</fullName>
  <value>You have {0} item</value>
</labels>
<labels>
  <fullName>Item_Count_other</fullName>
  <value>You have {0} items</value>
</labels>
```

**Manifest:**
```typescript
export const labelManifest = [
  "c:Item_Count_one",
  "c:Item_Count_other",
];
```

**Component:**
```typescript
t("Item_Count", { 0: count, count: count });
// count = 1 → "You have 1 item"
// count = 5 → "You have 5 items"
```

i18next reads the `count` arg and picks the `_one` or `_other` suffix per the English plural rules. The `0` arg drives substitution. The suffixes must be **lowercase** (`_one`, `_other`): i18next derives them from the browser's `Intl.PluralRules` categories, which are lowercase, and appends them verbatim to the key. A PascalCase `_One` label would never be found, and the label would render as its literal key name.

Languages with more plural forms (Russian, Polish, Arabic) need more label variants, `_zero`, `_few`, `_many`, etc. Author them as separate Custom Labels with the appropriate lowercase suffixes.

---

## Why positional (`{0}`) instead of named (`{name}`)?

**Portability.** Salesforce has three UI frameworks:
- Apex (backend): `String.format(label, [arg0, arg1])`
- LWC: `@salesforce/label/c.Save_Failed` with `{0}/{1}`
- React UI Bundles: `t("Save_Failed", { 0: ..., 1: ... })`

All three use the same Custom Labels metadata. If React used `{name}` syntax, the same logical string would need to be authored **twice**, once for Apex/LWC with `{0}`, once for React with `{name}`. Translators would maintain two formats. Engineers couldn't reuse strings across frameworks.

With the bridge (`prefix: "{", suffix: "}"`), **one Custom Label serves all three**. Portability is the win.

---

## What the bridge doesn't do (not in MVP)

- **Date/number formatting**: `{ 0: new Date() }` produces JS's default `toString`, not localized formatting. Wiring up `Intl.DateTimeFormat` / `Intl.NumberFormat` via i18next's `interpolation.format` callback is a separate design decision (not in the MVP scope).
- **Type safety**: nothing checks that `Save_Failed` actually has 2 placeholders at build time. A build-time extractor could close this gap (future work).
- **Escape for literal `{0}` in content**: i18next has escape options if labels genuinely need to contain literal curly braces. Edge case.

---

## Visual flow

```text
┌─────────────────────────────────────────────────┐
│ 1. Custom Label (authored in Salesforce):      │
│    "Failed to save {0}: {1}"                    │
└─────────────────────────────────────────────────┘
                       ↓
              GraphQL fetch at boot
                       ↓
┌─────────────────────────────────────────────────┐
│ 2. Cached in i18next memory:                    │
│    { 'c:Save_Failed': "Failed to save {0}: {1}" }│
└─────────────────────────────────────────────────┘
                       ↓
            Component calls t('Save_Failed',
                              { 0: 'Account',
                                1: 'Permission denied' })
                       ↓
┌─────────────────────────────────────────────────┐
│ 3. i18next's interpolator does:                │
│    template = "Failed to save {0}: {1}"         │
│    template.replace('{0}', 'Account')           │
│            .replace('{1}', 'Permission denied') │
└─────────────────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────┐
│ 4. Output:                                      │
│    "Failed to save Account: Permission denied"  │
└─────────────────────────────────────────────────┘
```

---

## Related

- [i18n-setup.md](i18n-setup.md): the init file where the `prefix`/`suffix` are configured
- [label-xml.md](label-xml.md): how to author labels with placeholders
- [verifying.md](verifying.md): testing interpolated labels
- [gotchas.md](gotchas.md): silent-fail traps

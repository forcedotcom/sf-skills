# Gotchas: the three silent-fail traps

These are localization-specific problems that fail **silently** (no console warning, no error, just wrong text). If your app loads but labels are wrong, start here.

---

## 1. Unregistered manifest key → renders as literal key name

**Symptom:** You see the literal string `Welcome_Text` on screen instead of "Welcome."

**Cause:** The key isn't in your `label-manifest.ts`. The app only fetches labels that are listed in the manifest, so an unregistered key is **never requested**, and i18next, finding nothing in its cache, renders the **literal key string** back to you as a fallback.

**No console warning. No error.** It fails silently. This is the most common localization bug.

**Example:**

```typescript
// src/i18n/label-manifest.ts
export const labelManifest = [
  "c:Save_Button",
  // forgot "c:Welcome_Text"
];
```

```typescript
// component
const { t } = useTranslation("c");
return <h1>{t("Welcome_Text")}</h1>; // renders "Welcome_Text" (literal string)
```

**Fix:** Add the missing key to `label-manifest.ts`:

```typescript
export const labelManifest = [
  "c:Save_Button",
  "c:Welcome_Text", // ← add this
];
```

**Why it's silent:** i18next is a general-purpose library. It doesn't know your labels come from Salesforce. When a key isn't in its cache, the fallback behavior (per i18next's design) is to render the key string, because in some apps, that's a valid debugging signal. In our case, it's just a trap.

**Prevention:** Always keep manifest entry count equal to label count (Step 3 completion criterion in the workflow). PR review catches mismatches today.

**Deeper detail:** The manifest is read by `SalesforceBackend` at boot. It groups entries by namespace (all `c:*` together, all `LightningDatatable:*` together) and issues a GraphQL query per namespace:

```graphql
query LoadLabels {
  uiapi {
    platform {
      labels(namespace: "c", names: ["Save_Button", ...]) {
        name
        value
        resolvedLocale
      }
    }
  }
}
```

If `Welcome_Text` isn't in the manifest, it isn't in the `names` array, so the server never returns it. i18next's cache is empty for that key, and the `t()` call falls back to rendering the key name.

Within a namespace, `SalesforceBackend` also splits the names into batches of at most **100** and fires the queries in parallel, because `uiapi.platform.labels` rejects a call with more than 100 names. This is automatic: a manifest with hundreds of `c:*` keys works with no extra config on your part. See the "Large manifest" note under Related problems.

---

## 2. API-version bake-in → blank page after deploy

**Symptom:** The app worked locally (or on a different org), but after deploying to a new org it boots to a **blank page** (white screen, no obvious error in the console).

**Cause:** You built the app while pointed at a **different org** than the one you deployed to, and the API versions don't match. The build plugin reads your default org's API version and stamps it into the bundle's JavaScript:

```javascript
// baked into the built JS
const endpoint = `https://<org>/services/data/v65.0/graphql`;
```

If you built while pointed at a v65.0 org and deploy to a v63.0 org, the bundle tries to call `/services/data/v65.0/graphql`, an endpoint that org doesn't have. The GraphQL call **404s**, the i18n context fetch (`fetchI18nContext()`) throws, and the app crashes during boot before React even mounts. You see a blank page.

**Fix:** Before building, set the deploy target org as default so the versions match:

```bash
sf config set target-org=<your-deploy-target-alias>
npm run build
sf project deploy start --source-dir force-app --target-org <same-alias>
```

**Check an org's API version:**

```bash
sf org display --target-org <alias>
```

Look for `"API Version"` in the output (e.g., `63.0`).

**Prevention:** Always run `sf config set target-org=<deploy-target>` **before** `npm run build`. The workflow (Step 1 of verifying) calls this out, but it's easy to forget when iterating.

**Why it's silent:** The 404 happens in the SDK's GraphQL fetch, which throws a generic network error. The stack trace points at `fetchI18nContext`, but doesn't say "wrong API version"; you have to infer it from the 404. A mismatch of one minor version (e.g., v63 → v64) usually works (backward-compatible); a mismatch of two or more (v63 → v65) reliably breaks.

**Not the same as the version floor:** The bake-in above is a *mismatch* problem (two orgs, different versions). Separate from it is a hard floor: runtime label resolution over GraphQL for UI Bundles works from **API v68.0 (the 264 release)** onward. The `platform.labels` field appears in the schema at v67.0, but the end-to-end feature is functional for UI Bundles at 264.4 / v68.0; on an org below that, a localized bundle renders blank or shows raw key names. This is why precondition 4 queries the org's actual maximum API version (via `check-org-api-version.sh`) before starting, rather than trusting the `sourceApiVersion` declared in `sfdx-project.json`: that field records what you declared, not what the org supports, so an org that old can't run this pattern even when the file check passes. Confirm an org's ceiling with `sf org display --target-org <alias>` (the `API Version` row) or by opening `/services/data/` and checking the highest `vNN.0` listed.

**Version floor is not the same as release timing:** The precondition blocks orgs older than v68.0, but it cannot distinguish patch releases within v68 (264.3 vs 264.4 both report v68.0). If this skill is deployed to orgs mid-rollout (on 264.3, before 264.4 is live), it can still produce non-functional localized bundles. That is a release-coordination concern handled by when the skill ships, not by this check.

---

## 3. Stale localStorage cache → old translations persist

**Symptom:** You changed a translation (edited the `translation-meta.xml` or updated it in Translation Workbench), confirmed the new value is in the org, redeployed, but the app **still shows the old text** on reload.

**Cause:** Your `src/i18n/index.ts` chains two backends:

```typescript
backend: {
  backends: [LocalStorageBackend, SalesforceBackend],
  backendOptions: [
    { expirationTime: 86400000 }, // 24 hours
    { dataSDK, labelManifest },
  ],
},
```

On load, i18next reads labels from **localStorage first** (the `LocalStorageBackend`), and only falls through to the GraphQL fetch (the `SalesforceBackend`) on a **cache miss**. Labels are cached per language+namespace under keys like:

- `i18next_res_en-c` (English custom labels)
- `i18next_res_es-c` (Spanish custom labels)
- `i18next_res_fr-c` (French custom labels)

Each has an `expirationTime` of **24 hours** (86400000 milliseconds). Until that entry expires, your app serves the cached copy and **never refetches**, so a fresh org value doesn't appear.

**What you see in DevTools:**
- **Network tab** shows the i18n **context/detect** query on every reload (this is how the SDK reads the user's language).
- But it shows **no labels query**, because the labels are served from localStorage, not the network.
- This makes it look like "the network is fine, so why is the text stale?" But the network is fine *for the context fetch*; the labels never hit the network at all.

**Fix:** Clear the cached labels, then reload:

1. **DevTools → Application → Local Storage** → find your org's origin (e.g., `https://<org>.my.salesforce.app`)
2. Delete the `i18next_res_*` keys (or **Clear site data** to wipe everything)
3. Reload the app

The next load misses the cache, refetches the labels over GraphQL, and shows the current value.

**This is expected behavior, not a bug.** The cache is what makes labels fast after first load (no GraphQL roundtrip on every boot). In production, a translation change takes up to `expirationTime` to roll out to all users; during development, you manually clear the cache to see edits immediately.

**Prevention:** When testing translation changes, habitually clear localStorage before reloading. Or lower `expirationTime` in the init file during development (e.g., 60000 = 1 minute), but remember to raise it back for production.

**Why the GraphQL calls you DO see aren't label refetches:** The context query runs on every boot to detect the user's current language. It's a separate, small query:

```graphql
query I18nContext {
  uiapi {
    platform {
      i18n {
        lang
        locale
        dir
        currency
      }
    }
  }
}
```

That's not cached. The **labels** query (the big one with all your label names) is what's cached, and it only fires on a cache miss.

---

## Summary table

| Symptom | Cause | Fix |
|---|---|---|
| Label renders as its own key name (`"Welcome_Text"`) | Unregistered manifest key | Add the key to `label-manifest.ts` |
| Blank page after deploy | API-version mismatch (built against different org) | `sf config set target-org=<deploy-target>` before building |
| Old translation persists after update | Stale localStorage cache | Clear `i18next_res_*` keys in DevTools, reload |

---

## Related problems (not silent-fail, but localization-adjacent)

### Deploy rejected: "Not available for deploy for this organization"

**Cause:** You're deploying a `<locale>.translation-meta.xml` for a language that isn't activated yet.

**Fix:** Setup → Translation Workbench → Translation Settings → Add the language, then re-deploy.

English never needs activation.

---

### Label shows in English when it should be translated (but not as a literal key)

**Symptom:** The text is correct, just not translated (e.g., you see "Welcome" when you expected "Bienvenido").

**Cause (most likely):** The translation file is missing that label, or its `<name>` doesn't match the `<fullName>` in `CustomLabels`. i18next falls back to the English base value (via `fallbackLng: "en"`), which is correct behavior; it just means that one key wasn't translated.

**Other causes:**
- The user's **Language** (not Locale) isn't set to the language you translated.
- The translation file wasn't deployed (missing from `force-app/main/default/translations/`).

**Check:** Setup → Translation Workbench → Translate → pick the language and the label. Is the translation there? If not, author it and re-deploy.

---

### Logged-in user sees their own language instead of the org default

**Symptom:** In a B2X site (or any authenticated context), a logged-in user whose **Language** is French sees French text for a label you only authored in the org-default language (English), **even when the app requests English**. A guest user switching languages works fine; only the logged-in user with a different Language setting hits it.

**Cause:** the server's label **fallback strategy**. When the app asks for a locale that has no explicit translation for a label, the server decides what to return. Its default strategy, `USER_DEFAULT`, resolves in this order: requested locale → that locale's language-fallback chain → **the logged-in user's own language** → the base/master value. Because the user's language comes *before* the base value, a French user gets French, not the English default.

**Fix on the documented floor (11.42.1):** `SalesforceBackend` does not yet override the server's default, so the query resolves with `USER_DEFAULT` and a logged-in user with a different Language can still see their own language instead of the base value. To get the org default on this version, author an explicit org-default translation for the label, or debug the raw query with `fallback: BASE_VALUE` (shown below) to confirm the value you expect.

> **Coming in a later SDK release:** a change that makes `SalesforceBackend` request `fallback: BASE_VALUE` is merged (2026-07-29) but not yet published, so it is not in 11.42.1. Once the release that carries it ships, the backend skips straight to the org-default value when a translation is missing, and you no longer need an explicit English translation just to work around this. Until then, treat the behavior above as current.

**If you're debugging the raw labels query** (e.g., re-running it in DevTools): `fallback` must be declared in the operation signature (`$fallback: LabelFallback`) **and** passed to the `labels(...)` field. A `fallback` key in the variables block alone is silently dropped and the server falls back to `USER_DEFAULT`. It takes the `LabelFallback` enum (`USER_DEFAULT` / `BASE_VALUE` / `NONE`), not a locale string like `"en"`:

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

with `"fallback": "BASE_VALUE"` in the variables.

---

### Large manifest: no per-query limit to manage yourself

**Symptom / worry:** You have hundreds of labels in one namespace and wonder whether you have to split the manifest or cap it.

**You don't.** `uiapi.platform.labels` rejects any single call with more than 100 names, but `SalesforceBackend` handles this for you: it dedupes the names, splits each namespace into batches of at most 100, and issues those queries in parallel, then merges the results. A manifest with 500 `c:*` keys becomes 5 batched queries under the hood; your code and manifest stay flat.

The load is **all-or-nothing per namespace**: if any batch fails, the whole namespace's read rejects (you don't get a half-populated namespace). If you're watching the Network tab, a large manifest is why you may see several `Labels` queries fire at once rather than one.

---

## Related

- [i18n-setup.md](i18n-setup.md): the init file (where `expirationTime` is configured)
- [label-xml.md](label-xml.md): Custom Labels + translations metadata
- [interpolation.md](interpolation.md): `{0}/{1}` placeholders
- [verifying.md](verifying.md): the serve/verify flow

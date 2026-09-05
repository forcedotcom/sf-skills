# Gotchas: the three silent-fail traps

These are localization-specific problems that fail **silently** (no console warning, no error, just wrong text). If your app loads but labels are wrong, start here.

---

## 1. Unregistered manifest key → renders as literal key name

**Symptom:** You see the literal string `Welcome_Text` on screen instead of "Welcome."

**Cause:** The key isn't in your `label-manifest.ts`. The app only fetches labels that are listed in the manifest, so an unregistered key is **never requested**, and the i18n library, finding nothing in its cache, renders the **literal key string** back to you as a fallback.

**No console warning. No error.** It fails silently. This is the most common localization bug.

**Example:**

```typescript
// src/i18n/label-manifest.ts
export const labelManifest = [
  "c:Save_Button",
  // forgot "c:Welcome_Text"
];
```

```text
// component calls the translation function with an unregistered key:
translate("Welcome_Text")   // renders "Welcome_Text" (literal string)
```

**Fix:** Add the missing key to `label-manifest.ts`:

```typescript
export const labelManifest = [
  "c:Save_Button",
  "c:Welcome_Text", // ← add this
];
```

**Why it's silent:** the i18n library (i18next, ngx-translate) is general-purpose. It doesn't know your labels come from Salesforce. When a key isn't in its cache, the fallback behavior (by design) is to render the key string, because in some apps that's a valid debugging signal. In our case, it's just a trap.

**Prevention:** Always keep manifest entry count equal to label count (Step 3 completion criterion in the workflow). PR review catches mismatches today.

**Deeper detail:** The manifest is read by the label backend at boot (React's shipped `SalesforceBackend`, or Angular's custom `TranslateLoader`). It groups entries by namespace (all `c:*` together, all `LightningDatatable:*` together) and issues a GraphQL query per namespace:

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

If `Welcome_Text` isn't in the manifest, it isn't in the `names` array, so the server never returns it. The library's cache is empty for that key, and the translation call falls back to rendering the key name.

Within a namespace, the label backend also splits the names into batches of at most **100** and fires the queries in parallel, because `uiapi.platform.labels` rejects a call with more than 100 names. This is automatic: a manifest with hundreds of `c:*` keys works with no extra config on your part. See the "Large manifest" note under Related problems.

---

## 2. API-version bake-in → blank page after deploy

**Symptom:** The app worked locally (or on a different org), but after deploying to a new org it boots to a **blank page** (white screen, no obvious error in the console).

**Cause:** You built the app while pointed at a **different org** than the one you deployed to, and the API versions don't match. The build plugin reads your default org's API version and stamps it into the bundle's JavaScript:

```javascript
// baked into the built JS
const endpoint = `https://<org>/services/data/v65.0/graphql`;
```

If you built while pointed at a v65.0 org and deploy to a v63.0 org, the bundle tries to call `/services/data/v65.0/graphql`, an endpoint that org doesn't have. The GraphQL call **404s**, the i18n context fetch (`fetchI18nContext()`) throws, and the app crashes during boot before it mounts. You see a blank page.

**Fix:** Before building, set the deploy target org as default so the versions match:

```bash
sf config set target-org=<your-deploy-target-alias>
npm run build
sf project deploy start \
  --source-dir force-app/main/default/uiBundles/<your-bundle> \
  --source-dir force-app/main/default/labels/CustomLabels.labels-meta.xml \
  --source-dir force-app/main/default/translations/<locale>.translation-meta.xml \
  --target-org <same-alias>
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

## 3. Stale label cache → old translations persist

**Symptom:** You changed a translation (edited the `translation-meta.xml` or updated it in Translation Workbench), confirmed the new value is in the org, redeployed, but the app **still shows the old text** on reload.

**Cause:** The i18n setup caches fetched labels so it doesn't hit GraphQL on every boot. Until that cache is invalidated, the app serves the cached copy and **never refetches**, so a fresh org value doesn't appear. The cache layer is **framework-specific**:

- **React / i18next** persists labels to **localStorage** via `i18next-localstorage-backend`, chained in front of the network backend: `backends: [LocalStorageBackend, SalesforceBackend]`. Labels are keyed per language+namespace as `i18next_res_<lang>-<ns>` (e.g. `i18next_res_en-c`, `i18next_res_es-c`) with an `expirationTime` (default 24h / 86400000 ms). This survives reloads until it expires.
- **Angular / ngx-translate** caches the resolved translations **in memory** on the `TranslateService` for the page session; the custom `TranslateLoader` re-issues the GraphQL query on the next `TranslateService.use(lang)` or a full page reload. A reload refetches (no persistent layer unless you add one).

**What you see in DevTools (React case):**
- **Network tab** shows the i18n **context/detect** query on every reload (this is how the SDK reads the user's language).
- But it shows **no labels query**, because the labels are served from localStorage, not the network.
- This makes it look like "the network is fine, so why is the text stale?" But the network is fine *for the context fetch*; the labels never hit the network at all.

**Fix:** Invalidate the cache, then reload:

- **React / i18next:** DevTools → Application → Local Storage → your org's origin (e.g. `https://<org>.my.salesforce.app`) → delete the `i18next_res_*` keys (or **Clear site data**), then reload.
- **Angular / ngx-translate:** a full page reload refetches; if you added a persistent cache layer, clear it too (**Clear site data**).

The next load misses the cache, refetches the labels over GraphQL, and shows the current value.

**This is expected behavior, not a bug.** The cache is what makes labels fast after first load (no GraphQL roundtrip on every boot). In production, a React translation change takes up to `expirationTime` to roll out to all users; during development, you manually clear the cache to see edits immediately.

**Prevention:** When testing translation changes, habitually clear the cache before reloading. In React you can also lower `expirationTime` in the init file during development (e.g., 60000 = 1 minute), then raise it back for production.

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
| Old translation persists after update | Stale label cache | Clear the i18n cache (React: `i18next_res_*` in localStorage) and reload |

---

## Related problems (not silent-fail, but localization-adjacent)

### Deploy rejected: "Not available for deploy for this organization"

**Cause:** You're deploying a `<locale>.translation-meta.xml` for a language that isn't activated yet.

**Fix:** Setup → Translation Workbench → Translation Settings → Add the language, then re-deploy.

English never needs activation.

---

### Label shows in English when it should be translated (but not as a literal key)

**Symptom:** The text is correct, just not translated (e.g., you see "Welcome" when you expected "Bienvenido").

**Cause (most likely):** The translation file is missing that label, or its `<name>` doesn't match the `<fullName>` in `CustomLabels`. The Platform SDK's GraphQL request returns a fallback according to `labelFallback` (`BASE_VALUE` for B2E, explicit `USER_DEFAULT` for B2C), so correct English text usually means that one key wasn't translated.

**Other causes:**
- The user's **Language** (not Locale) isn't set to the language you translated.
- The translation file wasn't deployed (missing from `force-app/main/default/translations/`).

**Check:** Setup → Translation Workbench → Translate → pick the language and the label. Is the translation there? If not, author it and re-deploy.

---

### B2C guest labels request returns HTTP 403

**Symptom:** The B2C site loads, but a signed-out visitor's labels GraphQL request returns HTTP 403. The same request can work for an authenticated user.

**Cause:** `GraphQLApiOrgPrefForGuestUsers` is not enabled. Guest access to the GraphQL label path is an org-admin prerequisite tracked by W-23854208.

**Fix:** Ask an org admin to confirm and enable the preference through the supported administration process. This localization workflow must never provision or change it. Stop until the prerequisite is satisfied.

### B2C language switch leaves old-language labels

**Symptom:** The URL or switcher displays a new site language, but labels remain in the previous language.

**Cause:** B2C language context is established at boot from the language-specific route through `SFDC_ENV.language`. An in-place language change does not rebuild the SDK context, and cached labels (React's `i18next_res_*` localStorage entries) may continue serving the old language.

**Fix:** Make the switcher navigate to the configured language URL and perform a full page reload. Confirm the route and `SFDC_ENV.language` agree. During development, clear the i18n cache (React: `i18next_res_*`) before retesting.

### Choose fallback by bundle type

The label fetch supports `labelFallback`. Preserve its `BASE_VALUE` default for B2E (React: omit the option; Angular: pass `BASE_VALUE`). For B2C only, configure `labelFallback: "USER_DEFAULT"` so fallback follows the guest/site language context. Do not apply the B2C override to B2E.

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

B2B remains unsupported. Do not infer B2B support from the B2C guidance or apply these steps to a B2B site.

---

### Large manifest: no per-query limit to manage yourself

**Symptom / worry:** You have hundreds of labels in one namespace and wonder whether you have to split the manifest or cap it.

**You don't.** `uiapi.platform.labels` rejects any single call with more than 100 names, but the label backend handles this for you (React's `SalesforceBackend`, or Angular's custom loader implementing the same logic): it dedupes the names, splits each namespace into batches of at most 100, and issues those queries in parallel, then merges the results. A manifest with 500 `c:*` keys becomes 5 batched queries under the hood; your code and manifest stay flat.

The load is **all-or-nothing per namespace**: if any batch fails, the whole namespace's read rejects (you don't get a half-populated namespace). If you're watching the Network tab, a large manifest is why you may see several `Labels` queries fire at once rather than one.

---

## Related

- [label-xml.md](label-xml.md): Custom Labels + translations metadata
- [verifying.md](verifying.md): the serve/verify flow
- `platform-sdk-i18n.md` (this folder): the shared runtime engine (Labels query, batching, fallback)
- your framework reference's `i18n-setup.md`: the init file (where the cache is configured)
- your framework reference's `interpolation.md`: `{0}/{1}` placeholders

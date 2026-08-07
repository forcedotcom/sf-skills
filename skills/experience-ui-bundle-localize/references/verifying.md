# Verifying: serve, deploy, and test labels across locales

How to build, deploy, open, and verify that labels render correctly in multiple languages.

---

## Overview

Verification has five steps:
1. **Build** the app (API version bakes in, point at the deploy target org first)
2. **Deploy** the bundle + labels + translations in one shot
3. **Open** the app at the correct URL (on the `lightning.force.com` domain)
4. **Flip** the user's Language setting to the translated language
5. **Reload** and confirm the labels render in the new language

---

## Step 1: Build the app

**Before building**, set the target org so the API version matches:

```bash
sf config set target-org=<your-org-alias>
```

**Why this matters:** The build plugin reads your **default org's** API version and stamps it into the bundle's JavaScript (`services/data/v{N}/graphql`). If you build while pointed at a v65.0 org and deploy to a v63.0 org, the bundle calls a GraphQL endpoint that org doesn't have, the call **404s, the i18n context fetch throws, and the app boots to a blank page** with no obvious error.

Then build:

```bash
npm run build
```

(Run from the UI bundle directory, `force-app/main/default/uiBundles/<your-bundle>/`.)

The built output lands in `dist/` under the bundle directory. The deploy pushes the built JS, not your TypeScript source.

---

## Step 2: Activate languages in the org (before deploy)

For every non-English language you're deploying, **activate it first** in the org:

**Setup → Translation Workbench → Translation Settings → Add**

Pick the languages (e.g., Spanish, French, German) and Save.

**Why:** Deploying a `<locale>.translation-meta.xml` for an inactive language fails with:
```text
Not available for deploy for this organization
```

English (`en_US`) needs no activation; it's always available.

---

## Step 3: Deploy the bundle + labels + translations

Deploy the entire `force-app` tree (bundle, labels, translations) in one command:

```bash
sf project deploy start --source-dir force-app --target-org <your-org-alias>
```

**Run from the SFDX project root** (not from inside the bundle directory). `--source-dir force-app` deploys everything under that folder:
- `labels/CustomLabels.labels-meta.xml` (English base labels)
- `translations/<locale>.translation-meta.xml` (translated labels)
- `uiBundles/<your-bundle>/dist/` (the built app)

You do **not** need a `package.xml` or any manifest entry; the CLI discovers the metadata automatically.

**Point at `force-app`, not `uiBundles/`, or your labels and translations won't go up.**

---

## Step 4: Open the app

UI Bundles serve at a fixed LWR route:

```text
https://<your-org>.lightning.force.com/lwr/application/ai/<namespace>-<bundleName>
```

**Parts:**
- `<your-org>`: your org's My Domain (e.g., `mycompany-dev-ed`)
- `<namespace>`: the bundle's namespace (usually `c` for custom)
- `<bundleName>`: the bundle's name (lowercased; the framework lowercases `appName` at lookup, so camelCase silently 404s)

**Example:** `https://mycompany-dev-ed.lightning.force.com/lwr/application/ai/c-freshi18n`

The `/lwr/application/ai/` segment is a fixed LWR route prefix; it's the same for every UI Bundle and isn't something you configure.

**Enhanced-domain orgs (scratch orgs are enhanced by default) redirect:** Type the `lightning.force.com` URL above, and the browser **redirects** to the standalone-app host:

```text
https://<your-org>--<namespace>.<instance>.my.salesforce.app/lwr/application/ai/<namespace>-<bundleName>
```

That's expected: a UI Bundle is a standalone **LWR** app, not part of Lightning Experience, so it serves from the `.my.salesforce.app` app host. The `lightning.force.com` URL is fine to type (it forwards); just don't be surprised when the address bar ends on `.my.salesforce.app`.

**If you see a blank page:**
- You're probably on the raw `my.salesforce.com` (API/session) host; switch to `lightning.force.com` and let it redirect.
- Or the API version is baked in wrong (built against a different org), see Step 1.
- Or the bundle name is camelCased in the URL (the framework lowercases it; use all lowercase).

See [gotchas.md](gotchas.md) for the full list of blank-page causes.

---

## Step 5: Change the user's Language

To test translations, you need to change the **Language** setting (not Locale, see the note below).

**Setup → My Settings → Language & Time Zone → Language** → pick the language you translated (e.g., Spanish) → Save.

**Reload the app.** Labels should now render in the selected language.

---

## Language vs Locale (common confusion)

Salesforce has two separate settings:
- **Language** drives **translations**: the text the user sees (`en_US`, `es`, `de`, `fr`)
- **Locale** drives **formatting only**: dates, numbers, currency (`en_US`, `de_DE`, `fr_CA`)

A user can have Language = English, Locale = French: English text, French number formatting.

When you test localization, **change the Language**, not the Locale. Changing Locale won't flip label text.

---

## Troubleshooting: labels don't flip

### 1. Label shows in English when it should be translated

**Possible causes:**
- The language isn't activated (Step 2), though you'd have hit the deploy rejection if that were it.
- The translation file is missing that label, or its `<name>` doesn't match the `<fullName>` in `CustomLabels`.
- The user's **Language** isn't what you think; confirm it's set to the language you translated (not Locale).

**Check:** Go to Setup → Translation Workbench → Translate → pick the language and the label. Is the translation there? If not, author it and re-deploy.

**Fallback behavior:** If a key is in the manifest but untranslated for the active language, i18next renders the **English base value** (via `fallbackLng: "en"` in the init). That's correct behavior; it just means that one key wasn't translated yet.

---

### 2. Label shows as its own key name

You see the literal string `Welcome_Text` on screen instead of "Welcome."

**Cause:** The key isn't in your `label-manifest.ts`. The app only fetches labels listed in the manifest, so an unregistered key is **never requested**, and i18next, finding nothing, renders the key string. **No console warning, no error**; it fails silently.

**Fix:** Add the `"c:Key"` entry to `label-manifest.ts` (Step 3 of the workflow). This is the most common localization bug; if a label looks wrong, check the manifest first.

See [gotchas.md](gotchas.md) for the full explanation.

---

### 3. You changed a translation but the app still shows the old text

You edited a label in the Translation Workbench (or redeployed a `translation-meta.xml`), confirmed the new value is in the org, but the app keeps rendering the **previous** value on reload.

**Cause:** The label cache. Your `src/i18n/index.ts` chains two backends, `[LocalStorageBackend, SalesforceBackend]`, so on load i18next reads labels from **localStorage first** and only falls through to GraphQL on a cache miss. Labels are cached per language+namespace under keys like `i18next_res_de-c` (DevTools → Application → Local Storage), with a 24-hour `expirationTime`. Until that entry expires, your app serves the cached copy and never refetches.

**Fix:** Clear the cached labels, then reload:
- **DevTools → Application → Local Storage** → delete the `i18next_res_*` keys
- Or **Clear site data** to wipe everything

The next load misses the cache, refetches over GraphQL, and shows the current value.

**This is expected behavior, not a bug.** The cache is what makes labels fast after first load. In production, a translation change takes up to `expirationTime` (24 hours) to roll out; during development, clear the cache to see edits immediately.

See [gotchas.md](gotchas.md) for the full explanation.

---

### 4. A user on a regional Language (e.g., `en_GB`) sees English base text, not their locale's translation

This is expected, not a bug, **as long as you only authored the base (`en_US`) translation.**

Asked with `fallback: BASE_VALUE`, the GraphQL server returns the label's base value for a regional Language it has no explicit translation for: `resolvedLocale` comes back as the base (`en_US`) with `wasFallback: true`. The server does **not** map `en_GB → en_US` region-aware; it just honors the base-value fallback. On the documented SDK floor (11.42.1) the backend does not yet request `BASE_VALUE`, so it resolves with the server default (`USER_DEFAULT`): a guest or org-default user still lands on the base value, but see the related note below for the logged-in case. The base-value request ships in a later SDK release (see [gotchas.md](gotchas.md)).

**Fix (only if you want region-specific text):** Author a translation for that exact regional Language (`en_GB.translation-meta.xml`). Otherwise the base value is the intended, correct result.

**Related:** if instead a *logged-in* user sees **their own** language (not the org default) for an untranslated label, that's the fallback-strategy case, see [gotchas.md](gotchas.md) ("Logged-in user sees their own language instead of the org default"). On 11.42.1 that is the expected behavior, since the backend still uses `USER_DEFAULT`; author an explicit org-default translation to avoid it. The `BASE_VALUE` fallback that prevents it arrives in a later SDK release.

---

## Verification checklist

Use this to confirm everything works:

- [ ] Built against the correct org (API version matches deploy target)
- [ ] Every translated language is activated in the org
- [ ] Deployed `force-app` (bundle + labels + translations in one shot)
- [ ] Opened at `lightning.force.com/lwr/application/ai/<namespace>-<bundleName>` (redirected to `.my.salesforce.app` is fine)
- [ ] Changed user's **Language** (not Locale) to the translated language
- [ ] Reloaded, labels render in the new language
- [ ] If labels are stale, cleared `i18next_res_*` from localStorage

---

## Quick reference: commands

| Command | Run from | Purpose |
|---|---|---|
| `sf config set target-org=<alias>` | Anywhere | Set default org (API version bakes in on next build) |
| `npm run build` | UI bundle dir | Build the app |
| `sf project deploy start --source-dir force-app --target-org <alias>` | Project root | Deploy bundle + labels + translations |
| `sf project retrieve start --metadata Translations:<locale>` | Project root | Pull translations authored in Translation Workbench |

---

## Related

- [i18n-setup.md](i18n-setup.md): the init file + manifest
- [label-xml.md](label-xml.md): Custom Labels + translations metadata
- [interpolation.md](interpolation.md): `{0}/{1}` placeholders
- [gotchas.md](gotchas.md): silent-fail traps (unregistered keys, stale cache, API-version mismatch)

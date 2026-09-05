# Verifying: serve, deploy, and test labels across locales

How to build, deploy, open, and verify that labels render correctly in multiple languages.

---

## Overview

Authenticated B2E verification has five steps:
1. **Build** the app (API version bakes in, point at the deploy target org first)
2. **Deploy** the bundle + labels + translations in one shot
3. **Open** the app at the correct URL (on the `lightning.force.com` domain)
4. **Flip** the user's Language setting to the translated language
5. **Reload** and confirm the labels render in the new language

B2C verification uses the site-configured languages and language-specific URLs instead of the authenticated user's Language setting. Follow the B2C section after deployment.

### What this skill produces vs. what's left for you / other skills

When asked "what's left to deploy," answer with these — do **not** invent new metadata types:

- **This skill already wrote** the deployable metadata: `CustomLabels.labels-meta.xml` (English base)
  and `translations/<locale>.translation-meta.xml` (the `Translations` type — **not**
  `CustomObjectTranslation`; see [label-xml.md](label-xml.md)), plus the i18n wiring and manifest.
- **Manual/admin prerequisite (not a deployable file this skill emits):** activate each non-English
  language in Translation Workbench (Step 2) — otherwise the deploy is rejected. There is no
  "language settings" file for this skill to generate.
- **Delegated to other skills:** Experience Cloud **site languages** / `sfdc_cms__languageSettings`
  → `experience-ui-bundle-site-generate`; the **deploy** itself → `experience-ui-bundle-deploy`.

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

Before deploying, inspect the local diff and construct exact source paths for the target bundle, `CustomLabels.labels-meta.xml`, and only the locale files changed by this task. Show the actual metadata diff/components, not only the filenames; if either shared label file contains unrelated changes, stop or get explicit approval for those changes too. Show the resolved target org (`sf org display --target-org <alias>`) and wait for explicit confirmation. Then deploy the approved paths, for example:

```bash
sf project deploy start \
  --source-dir force-app/main/default/uiBundles/<your-bundle> \
  --source-dir force-app/main/default/labels/CustomLabels.labels-meta.xml \
  --source-dir force-app/main/default/translations/<locale>.translation-meta.xml \
  --target-org <your-org-alias>
```

**Run from the SFDX project root** (not from inside the bundle directory). The approved source paths deploy only:
- `labels/CustomLabels.labels-meta.xml` (English base labels)
- `translations/<locale>.translation-meta.xml` (translated labels)
- `uiBundles/<your-bundle>/dist/` (the built app)

You do **not** need a `package.xml` or any manifest entry; the CLI discovers the selected metadata automatically.

Repeat `--source-dir` for each approved locale file. Do not replace these paths with the broad `force-app`, `labels`, or `translations` directories unless the user explicitly intends to deploy every metadata change in them.

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

This step is for **B2E only**. For B2C, use the site language route below.

---

## B2C: verify a guest site language

1. In the site administration experience, configure at least two supported languages. Translation Workbench activation and translation metadata remain required, but they do not by themselves add a language to the site.
2. Confirm an org admin has already enabled `GraphQLApiOrgPrefForGuestUsers` (W-23854208). Never enable it as part of this workflow. Without it, a guest's GraphQL label request returns HTTP 403.
3. If the configured language or deployed metadata requires publishing, treat publication as a separate go-live mutation. Resolve the site's `Network.Name` from the target site (prefer matching its `UrlPathPrefix`), show that community name and target org, and wait for explicit user confirmation immediately before running `sf community publish --name "<network-name>" --target-org <org-alias>`. A metadata deployment is not publication approval. Track the returned background operation to completion before guest verification; if propagation is still in progress, report that instead of treating stale output as a localization failure.
4. Open the published site as a signed-out guest through its language-specific URL. Confirm the boot environment exposes the same language in `SFDC_ENV.language`.
5. Confirm translated labels render and the labels GraphQL request succeeds for the guest.
6. Use the site's language switcher. It must navigate to the target language URL and cause a **full page reload**; changing the i18n library's language in place leaves the boot-time SDK context and cached resources stale.
7. Confirm the new route and `SFDC_ENV.language` agree, then verify the translated labels again.

For a localized local preview, supply an explicit configured language in the preview URL/route. Do not use the authenticated org user's Language as evidence for guest behavior. If a recent translation or route change appears stale, clear your i18n library's cached labels and reload each language URL (the exact cache keys are in your framework reference's `gotchas.md`).

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

**Fallback behavior:** If a registered key is untranslated for the active language, the Platform SDK's GraphQL request resolves it according to `labelFallback`: B2E uses `BASE_VALUE`; B2C explicitly uses `USER_DEFAULT`. Your i18n library's own language fallback (i18next's `fallbackLng`, ngx-translate's `fallbackLang` — `defaultLanguage` in ngx-translate majors before v16) applies only if no resource is loaded for the detected language; it does not define Salesforce label-resolution semantics.

---

### 2. Label shows as its own key name

You see the literal string `Welcome_Text` on screen instead of "Welcome."

**Cause:** The key isn't in your `label-manifest.ts`. The app only fetches labels listed in the manifest, so an unregistered key is **never requested**, and the i18n library, finding nothing, renders the key string. **No console warning, no error**; it fails silently.

**Fix:** Add the `"c:Key"` entry to `label-manifest.ts` (Step 3 of the workflow). This is the most common localization bug; if a label looks wrong, check the manifest first.

See [gotchas.md](gotchas.md) for the full explanation.

---

### 3. You changed a translation but the app still shows the old text

You edited a label in the Translation Workbench (or redeployed a `translation-meta.xml`), confirmed the new value is in the org, but the app keeps rendering the **previous** value on reload.

**Cause:** The label cache. To avoid a GraphQL roundtrip on every boot, the i18n setup caches fetched labels client-side (typically in `localStorage`) per language+namespace, with an expiration window (commonly 24 hours). Until that entry expires, your app serves the cached copy and never refetches — so a fresh org value doesn't appear.

**Fix:** Clear the cached labels, then reload (**DevTools → Application → Local Storage** → delete the cached label entries, or **Clear site data** to wipe everything). The next load misses the cache, refetches over GraphQL, and shows the current value. The **exact cache keys and where they live are framework-specific** — see your framework reference's `gotchas.md` (e.g. React/i18next uses `i18next_res_*`).

**This is expected behavior, not a bug.** The cache is what makes labels fast after first load. In production, a translation change takes up to the expiration window to roll out; during development, clear the cache to see edits immediately.

See your framework reference's `gotchas.md` for the full explanation.

---

### 4. A user on a regional Language (e.g., `en_GB`) sees English base text, not their locale's translation

This is expected, not a bug, **as long as you only authored the base (`en_US`) translation.**

For B2E, the label fetch default is `BASE_VALUE`. The GraphQL server returns the label's base value for a regional Language with no explicit translation: `resolvedLocale` comes back as the base (`en_US`) with `wasFallback: true`. The server does **not** map `en_GB → en_US` region-aware; it honors the base-value fallback.

**Fix (only if you want region-specific text):** Author a translation for that exact regional Language (`en_GB.translation-meta.xml`). Otherwise the base value is the intended, correct result.

For B2C, the skill explicitly configures `labelFallback: "USER_DEFAULT"`; test fallback through the guest site's configured language URL rather than by changing an authenticated user's Language.

---

## Verification checklist

Use this to confirm everything works:

- [ ] Built against the correct org (API version matches deploy target)
- [ ] Every translated language is activated in the org
- [ ] Deployed only the target bundle + labels + translations directories
- [ ] Opened at `lightning.force.com/lwr/application/ai/<namespace>-<bundleName>` (redirected to `.my.salesforce.app` is fine)
- [ ] Changed user's **Language** (not Locale) to the translated language
- [ ] Reloaded, labels render in the new language
- [ ] If labels are stale, cleared the i18n library's cached labels from localStorage (see your framework `gotchas.md`)
- [ ] B2C: site languages are configured/published and the language URL matches `SFDC_ENV.language`
- [ ] B2C: any site publication received separate explicit confirmation for the named site and org
- [ ] B2C: signed-out guest labels GraphQL succeeds (no HTTP 403)
- [ ] B2C: language switcher performs a full reload and localized local preview was checked
- [ ] B2B was excluded; this workflow does not support B2B sites

---

## Quick reference: commands

| Command | Run from | Purpose |
|---|---|---|
| `sf config set target-org=<alias>` | Anywhere | Set default org (API version bakes in on next build) |
| `npm run build` | UI bundle dir | Build the app |
| `sf project deploy start --source-dir force-app/main/default/uiBundles/<bundle> --source-dir force-app/main/default/labels/CustomLabels.labels-meta.xml --source-dir force-app/main/default/translations/<locale>.translation-meta.xml --target-org <alias>` | Project root | Deploy the approved target bundle + exact label metadata paths |
| `sf community publish --name "<network-name>" --target-org <alias>` | Project root | Publish the B2C site, only after resolving `Network.Name` and separate explicit confirmation |
| `sf project retrieve start --metadata Translations:<locale>` | Project root | Pull translations authored in Translation Workbench |

---

## Related

- [label-xml.md](label-xml.md): Custom Labels + translations metadata
- [gotchas.md](gotchas.md): silent-fail traps (unregistered keys, stale cache, API-version mismatch)
- `platform-sdk-i18n.md` (this folder): the shared runtime engine (Labels query, fallback)
- your framework reference's `i18n-setup.md`: the init file + manifest
- your framework reference's `interpolation.md`: `{0}/{1}` placeholders

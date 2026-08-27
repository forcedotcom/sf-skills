---
name: experience-ui-bundle-localize
description: "MUST activate to localize / internationalize a uiBundles/*/src/ React project: extract hardcoded user-facing strings into Custom Labels, wire i18next over the Platform SDK GraphQL backend, add labels for another language, or troubleshoot label rendering across locales. Triggers: user-facing string literals in .tsx/.jsx, a CustomLabels.labels-meta.xml, a src/i18n/ directory or label-manifest.ts, t(…) calls, or requests to 'translate / localize / internationalize / support another language.' Scope: authenticated B2E UI Bundles and B2C site bundles. Use experience-ui-bundle-site-generate instead for site language configuration or sfdc_cms__languageSettings. DO NOT TRIGGER for B2B site bundles, building app shell/UI or styling, reading/writing/refreshing records (use experience-ui-bundle-salesforce-data-access), generating a new bundle (use experience-ui-bundle-frontend-generate), deploying (use experience-ui-bundle-deploy), or authoring translations in Translation Workbench."
metadata:
  version: "1.0"
  domains: ["Experience"]
  minApiVersion: "68.0"
  relatedSkills:
    - "experience-ui-bundle-deploy"
    - "experience-ui-bundle-frontend-generate"
    - "experience-ui-bundle-salesforce-data-access"
    - "experience-ui-bundle-site-generate"
  cliTools:
    - tool: ["jq"]
      semver: ">=1.6"
    - tool: ["npm"]
      semver: ">=7.0.0"
    - tool: ["sf"]
      semver: ">=2.0.0"
---

# Localize a React UI Bundle

Localize a React UI Bundle: extract user-facing strings into Salesforce Custom Labels, wire i18next over the Platform SDK GraphQL backend, and verify labels across locales.

This file is the **workflow + guardrail spine**. Depth lives in linked docs:

- **[references/i18n-setup.md](references/i18n-setup.md)**: the two files you write: the i18next init and the label manifest
- **[references/label-xml.md](references/label-xml.md)**: Custom Labels and translation metadata XML shapes; the `namespace:Key` rules
- **[references/interpolation.md](references/interpolation.md)**: positional `{0}/{1}` placeholder interpolation in labels
- **[references/verifying.md](references/verifying.md)**: serve URL, locale flip, and verifying labels render
- **[references/gotchas.md](references/gotchas.md)**: the three silent-fail traps: unregistered manifest keys, API-version bake-in, stale label cache

## The one-paragraph mental model

A React UI Bundle can't use `@salesforce/label/*` the way LWC does, those imports resolve at compile time inside the platform's compiler, which your standalone React bundle doesn't go through. Instead, your app **fetches labels at runtime** through the Salesforce GraphQL UI API and hands them to **i18next** (a standard React i18n library) to render. The Platform SDK provides the runtime plumbing for this, a detector that reads the user's language, a backend that fetches labels over GraphQL, and a context fetch. You write two thin files: a short init that wires the SDK pieces into i18next, and a manifest listing which labels your app uses. The rest is authoring the labels themselves as Salesforce Custom Labels metadata.

```typescript
import { useTranslation } from "react-i18next";

function WelcomeBanner() {
  const { t } = useTranslation("c"); // "c" = custom label namespace
  return <h1>{t("Welcome_Text")}</h1>; // renders "Welcome" or "Bienvenido" per user's language
}
```

---

## Step 0: Route the task

| The task is… | Go to |
|---|---|
| Bundle doesn't exist yet | **experience-ui-bundle-frontend-generate** skill |
| Deploying the app with its labels | **experience-ui-bundle-deploy** skill |
| Configuring site languages or `sfdc_cms__languageSettings` | **experience-ui-bundle-site-generate** skill |
| Localizing an existing bundle | **Workflow below** |

---

## Preconditions: verify before editing

| # | Requirement | Verify | If missing |
|---|---|---|---|
| 1 | It's a `uiBundles/*/src/` React project | Project structure matches | Not a UI Bundle → route to the correct skill |
| 2 | Platform SDK, UI Bundle, and Vite plugin siblings installed and aligned (≥11.49.3) | `package.json` in the UI bundle dir | Tell user to align and upgrade them; cannot proceed |
| 3 | You can identify where the app mounts | Read the entry file (usually `src/index.tsx`) | No clear mount point → ask user to point it out |
| 4 | Target org actually supports API v68.0+ (runtime label GraphQL for UI Bundles ships in Release 264) | Run the runtime org-release check below | Org's max API version is below v68.0 (Release 262 or older) → cannot proceed; retarget a Release 264+ org or upgrade the org |
| 5 | The bundle is authenticated B2E or the request/context explicitly identifies a B2C site, not B2B | Run the bundle-type detection below and use the request/context for site product identity | Explicit B2B → reject; site type not explicit → ask the user and stop until confirmed; B2C also requires precondition 6 |
| 6 | For B2C only, an admin has enabled `GraphQLApiOrgPrefForGuestUsers` | Ask the admin to confirm the org preference is already enabled | Do not enable it; explain that guest GraphQL returns HTTP 403 without it and stop (dependency: W-23854208) |

**Runtime org-release check (precondition 4).** The `platform.labels` GraphQL path that resolves labels at runtime for UI Bundles ships in Salesforce Release 264 (API v68.0 or higher). A `sourceApiVersion` in `sfdx-project.json` records what you declared, not what the org supports, so a newer CLI pointed at an older org can pass a static file check and then fail at runtime. Query the org's actual maximum API version before wiring anything:

```bash
bash <skill-dir>/scripts/check-org-api-version.sh <org-alias-or-username>
```

Exit `0` → the org supports v68.0+, proceed. Exit `1` → the org is too old or unreachable; do not write i18n wiring or labels, report the version mismatch to the user and stop. (`sf api request rest` inside the script keeps authentication at the CLI transport layer, so no access token enters context.)

**Bundle-type detection (precondition 5).** The bundle's type decides which localization branch applies. Pass the full path to the bundle dir; the script derives the metadata root from it, so the current directory does not matter:

```bash
bash <skill-dir>/scripts/detect-bundle-type.sh <path-to-uiBundles/<name>/ dir>
```

Act on the exit-code contract: `0` → authenticated app (B2E or in-core internal), use the B2E branch; `10` → bound public site app-container candidate, meaning metadata proves site binding and guest access but **not** B2C versus B2B; `11` → bound non-public/unsupported site, stop; `12` → both CustomApplication and one site binding exist, ask which runtime context is the localization target; `13` → multiple matching Experience site bindings, show the reported site names and ask which site/runtime context is the target; `2` → unbound/unknown, report the script output and stop rather than guessing.

For exit `10`, route by explicit request/context: if it says **B2C**, confirm precondition 6 and use the B2C branch; if it says **B2B**, reject it; if product type is not explicit, ask the user whether the site is B2C or B2B and stop until confirmed. For exits `12` and `13`, require the user to choose the runtime context (and site for exit `13`), then apply that branch's fallback and prerequisites. Never infer B2C from `DigitalExperienceConfig`, `appSpace`, `appContainer`, or `AUTHENTICATED_WITH_PUBLIC_ACCESS_ENABLED`; the authentication value means guest access is enabled.

For B2C, only an org admin may enable `GraphQLApiOrgPrefForGuestUsers`; never provision or change it. Without it, guest label requests return HTTP 403. Track availability through W-23854208.

If a precondition isn't met, stop: report the specific block to the user and record a plan item to return once it's resolved. Do not add i18n wiring or TODO markers to a B2B or unknown bundle.

---

## Workflow: the five steps

Each step has a **completion criterion** and a **confirm-before-continue** pause.

### Step 1: Detect

**Goal:** Scan `.tsx`/`.jsx` files for user-facing hardcoded strings.

**What to scan:**
- String literals inside JSX tags: `<h1>Welcome</h1>` → candidate
- String props shown to users: `placeholder="Enter name"` → candidate
- User-facing accessible text: `aria-label`, `aria-describedby`, `alt` → candidate (a screen-reader user hears these, so they must localize too)

**What to skip:**
- Import statements
- Object keys / property names
- `data-*` attributes (machine-readable)
- Test IDs (`data-testid`, `id` attributes)
- Text already wrapped in `t()` calls
- Console logs, error messages thrown to developers (not user-facing)
- Class names, file paths, technical constants

**Action:**
1. Scan the `src/` directory for `.tsx` and `.jsx` files
2. Extract candidates, showing file path + line number for each
3. Show the list to the developer

**Completion criterion:**
Developer confirms the list (or edits it to remove false positives).

**Pause:** "I found N user-facing strings across M components. Here's the list: [show file:line + string]. Look right? [confirm / edit the list / skip some]"

---

### Step 2: Extract

**Goal:** For each confirmed string, add a Custom Label and replace the JSX literal with a `t()` call.

**Action for each string:**
1. **Propose a key name**, format: `<Context>_<Role>` (e.g., `"Welcome"` → `Welcome_Text`, `"Save"` → `Save_Button`, `"Failed to save"` → `Save_Failed_Message`). Follow naming: PascalCase words, underscores between parts, descriptive enough to be unique.
2. **Add the label** to `force-app/main/default/labels/CustomLabels.labels-meta.xml`:
   ```xml
   <labels>
     <fullName>Welcome_Text</fullName>
     <language>en_US</language>
     <protected>false</protected>
     <shortDescription>Welcome banner heading</shortDescription>
     <value>Welcome</value>
   </labels>
   ```
   (Full XML structure: [references/label-xml.md](references/label-xml.md))
3. **Replace the string** in the component with `{t("Key")}`:
   ```tsx
   // Before: <h1>Welcome</h1>
   // After:  <h1>{t("Welcome_Text")}</h1>
   ```
4. **Add the import** if not present: `import { useTranslation } from "react-i18next";` and `const { t } = useTranslation("c");` at the top of the component function.

**Completion criterion:**
Every confirmed string has both a `CustomLabels` entry and a `t()` call in its original location.

**Pause:** "For each string I'll add a Custom Label and replace the JSX with t(). Here are the proposed keys: [show string → namespace:Key mapping]. Apply these edits? [y / review each]"

---

### Step 3: Register

**Goal:** Add each key to the label manifest so i18next knows to fetch it.

**Action:**
1. Add each key to the manifest array in `src/i18n/label-manifest.ts`:
   ```typescript
   export const labelManifest = [
     "c:Welcome_Text",
     "c:Save_Button",
     "c:Save_Failed_Message",
   ];
   ```
   If the file doesn't exist yet, Step 4 scaffolds it; the completion check below reports its absence, so don't test for the file by hand.

**Completion criterion:**
Run `check-manifest-registered.sh` from the UI bundle dir (it scans `src/` relative to the current directory) and report any errors it returns. It owns the deterministic inspection: it cross-checks every `t("Key")` call site against the manifest and treats a missing `label-manifest.ts` (when `t()` calls exist) as a failure. A key that's called but not registered renders as its own literal name at runtime with no error, the silent-fail trap this guards.

```bash
cd <path-to-uiBundles/<name>/ dir>   # scripts scan src/ relative to here
bash <skill-dir>/scripts/check-manifest-registered.sh
```

Branch on the exit code: `0`, every key is registered (or there are no `t()` calls to gate), proceed. `1`, the manifest is missing or the listed keys aren't in it; scaffold or add them (Step 4 scaffolds the file) and re-run. `64`, usage error, the source dir doesn't exist (wrong cwd or bad argument); this is **not** a "keys missing" result, do not scaffold or register, fix the path and re-run.

**Pause:** "Added N entries to label-manifest.ts. check-manifest-registered.sh passed: [confirm]."

---

### Step 4: Wire

**Goal:** Ensure the i18next init exists; scaffold it if the app has no i18n yet.

Configure `SalesforceBackend` by bundle type: preserve the shipped `BASE_VALUE` default for B2E; for B2C only, set `labelFallback: "USER_DEFAULT"`. See [references/i18n-setup.md](references/i18n-setup.md) for both configurations and B2C language context.

**Check:**
Run `check-i18n-wired.sh` from the UI bundle dir (it scans `src/` relative to the current directory) and report what it returns. The script owns the whole deterministic inspection: it looks for an init file defining `initI18n()` and a boot-time call to it, and when those exist it also reports whether the label manifest is imported and actually passed into the backend config. Do not re-derive any of this by reading files yourself.

```bash
cd <path-to-uiBundles/<name>/ dir>   # scripts scan src/ relative to here
bash <skill-dir>/scripts/check-i18n-wired.sh
```

Branch on the **exit code** (the printed message names the specific file/symbol for your report, but the decision is the code):
- Exit `0` → fully wired, the manifest is passed into the backend; go to "If i18n already exists" below and just add new keys.
- Exit `1` → no `initI18n()` exists; scaffold the whole setup via "If no i18n setup exists yet".
- Exit `2` → the init already exists but isn't called at boot; do **not** re-scaffold or overwrite it. Add only the boot-time `initI18n()` call in the entry file (step 4 of "If no i18n setup exists yet"), then re-run.
- Exit `3` → wired at boot but the script **could not confirm** the manifest is passed into the backend. It scans the whole `src` tree, but this last check is a textual heuristic: the manifest may be wired through a variable, spread, or helper the script can't see, so treat exit 3 as "verify before editing," not "definitely broken." Open the file the message names and confirm the manifest really isn't in `backendOptions`. Only if it genuinely dangles, do what the message names: if the manifest is imported but unused, pass it into the existing `backendOptions` without clobbering it; if there's no `backendOptions`/`SalesforceBackend` config at all, add that backend block to the existing init (see [references/i18n-setup.md](references/i18n-setup.md)). Never re-scaffold the init file or duplicate wiring that already works.
- Exit `64` → usage error: the source dir doesn't exist (wrong cwd or bad argument). This is **not** a "no init" result; do not scaffold. Fix the path (run from the UI bundle dir, or pass its `src` path) and re-run.

**If no i18n setup exists yet:**
1. Install dependencies (tell the user to run):
   ```bash
   npm install i18next react-i18next i18next-chained-backend i18next-localstorage-backend
   ```
2. Create `src/i18n/index.ts` with the init wiring (full code: [references/i18n-setup.md](references/i18n-setup.md))
3. Create `src/i18n/label-manifest.ts` with an empty array (Step 3 will populate it)
4. Call `initI18n()` once at boot in the entry file (before mounting the app):
   ```typescript
   import { initI18n } from "./i18n";
   
   initI18n().then(() => {
     // mount app
   });
   ```

**If i18n already exists:**
Act on the message `check-i18n-wired.sh` already printed (above): if it reports the manifest wired, just add new keys to it; if it reports a reconcile is needed, do exactly what its message names (import the manifest and/or pass it into the backend config) without clobbering existing wiring.

**Completion criterion:**
`initI18n()` exists and is called once at boot; the manifest is wired into the backend.

**Pause:** "i18next setup [exists / created]. initI18n() is called at boot: [confirm]."

---

### Step 5: Verify

**Goal:** Guide the developer to verify labels render in a second language.

**Action:** Follow the branch-specific procedure in [references/verifying.md](references/verifying.md).

For **B2E**, activate a second language, author or retrieve its translation metadata, build against the target org, deploy only the target bundle and label metadata, then change the authenticated user's Language and reload. The exact commands and URLs are in [references/verifying.md](references/verifying.md).

For **B2C**, verify configured site languages, URL routing, `SFDC_ENV.language`, the full-reload language switcher, localized local preview, guest GraphQL access, and cache clearing as detailed in [references/verifying.md](references/verifying.md).

Deploying the bundle, labels, and translations does not publish the Experience site. Treat `sf community publish` as a separate go-live mutation: show the exact site and target org, then wait for explicit user confirmation immediately before running it.

**If it doesn't render:**
Check the three gotchas in [references/gotchas.md](references/gotchas.md):
- Unregistered manifest key (Step 3 missed a label)
- API-version mismatch (built against a different org)
- Stale localStorage cache (clear `i18next_res_*` keys in DevTools)
- B2C guest GraphQL 403 (`GraphQLApiOrgPrefForGuestUsers` is not admin-enabled)
- B2C route, site language, and `SFDC_ENV.language` disagree

**Completion criterion:**
Labels render in ≥2 locales, or the blocking gotcha is identified.

**Pause:** "To verify: activate a second language in Translation Workbench, author a translation (I can scaffold the XML), build/deploy, and reload. Want me to scaffold the translation file for [language]? [y / I'll do it manually]"

---

## Edge cases: handle gracefully

- **Already-localized code**: detect existing `t()` usage / a populated manifest; offer to *add to* the setup rather than re-scaffold everything.
- **No strings found**: report cleanly and stop; do not invent work.
- **App has no i18n setup yet**: Step 4 scaffolds the two files first before Step 3 can register anything.
- **Partial setup** (manifest exists but init missing, or vice-versa), reconcile what's present; never clobber existing wiring.
- **B2B site**: explicitly reject it. B2C support does not imply B2B support.

---

## Guardrails: never regress these

1. **Never machine-translate deployable metadata.** Scaffold one well-formed `<Translations>` document with a closed `<customLabels>` block per label and XML-escaped English source text. Preserve placeholders and parse both metadata files before completion. Translators replace scaffold values by hand or through Translation Workbench; never call an MT API for them.
2. **Never register a key that has no label.** Manifest entry count must equal label count (Step 3 criterion). An unregistered key renders as its own literal name with no console warning. It's the most common localization bug.
3. **Never clobber existing i18n wiring.** If Step 4 finds an existing `initI18n()`, reconcile (add the manifest import if missing) rather than replace the whole file.
4. **Every file must be customer-safe.** No `webapps`, core-only paths, or internal infrastructure references anywhere. Write as if for an external customer in an SFDX project.
5. **Never publish a B2C site implicitly.** Metadata deployment and site publication are separate. Run `sf community publish` only after showing the site and org and receiving explicit confirmation for that publication.

---

## Commands & layout

```text
<project-root>/                          ← SFDX project root
└── force-app/main/default/
    ├── labels/CustomLabels.labels-meta.xml          ← English base labels
    ├── translations/<locale>.translation-meta.xml   ← one per translated language
    └── uiBundles/<your-bundle>/
        ├── package.json
        └── src/
            ├── i18n/
            │   ├── index.ts              ← init wiring (you write this once)
            │   └── label-manifest.ts     ← list of labels to fetch (you maintain this)
            └── components/               ← components call t()
```

| Command | Run from | Purpose |
|---|---|---|
| `npm install i18next react-i18next i18next-chained-backend i18next-localstorage-backend` | UI bundle dir | Install i18n dependencies (Step 4) |
| `npm run build` | UI bundle dir | Build the app (API version bakes in, set target-org first) |
| See `references/verifying.md` | Project root | Review and deploy the exact target bundle + changed label metadata to an explicit org |
| `sf project retrieve start --metadata Translations:<locale>` | Project root | Pull translations authored in Translation Workbench |

---

## Pre-flight checklist: completion criteria for the whole run

- [ ] Every confirmed string has both a `CustomLabels` entry and a `t()` call
- [ ] `label-manifest.ts` entry count == label count (no unregistered keys)
- [ ] `initI18n()` present and called once at boot
- [ ] B2C only: guest GraphQL preference confirmed, `USER_DEFAULT` configured, and site language route matches `SFDC_ENV.language`
- [ ] B2E only: no `labelFallback` override; the `BASE_VALUE` default is preserved
- [ ] Labels render in ≥2 locales (or the blocking gotcha is named)
- [ ] No hand-written machine translations landed in `*-meta.xml` (only scaffold-and-guide)
- [ ] Both metadata files parse as XML; the translation scaffold has one `<Translations>` root and one closed block per label
